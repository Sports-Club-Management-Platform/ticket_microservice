import asyncio
import io
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List

import aio_pika
import stripe
from aio_pika import Message

from auth.JWTBearer import JWTAuthorizationCredentials
from auth.auth import auth
from auth.user_auth import user_info_with_token, get_user_info_from_user_sub
from crud import crud
from db.create_database import create_tables
from db.database import get_db
from fastapi import (APIRouter, Depends, FastAPI, Form, HTTPException,
                     UploadFile)
from sqlalchemy.orm import Session
from auth.auth import jwks, get_current_user
from auth.JWTBearer import JWTAuthorizationCredentials, JWTBearer

from models.ticket import Ticket as TicketModel
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import (
    UserTicketCreate,
    UserTicketInDB,
    UserTicket,
)
from models.userticket import UserTicket as UserTicketModel

router = APIRouter(tags=["Tickets"])

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
stripe.api_key = os.getenv("STRIPE_API_KEY")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
MAX_FILE_SIZE = 2097152  # 2MB - Stripe maximum
ACCEPTED_FILE_MIME_TYPE = ["image/png"]
ACCEPTED_FILE_EXTENSIONS = [".png"]

connection = None
channel = None
exchange = None
queue = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global connection, channel, exchange, queue
    create_tables()
    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange("exchange", type=aio_pika.ExchangeType.TOPIC, durable=True)

    # queues
    tickets_queue = await channel.declare_queue("TICKETS", durable=True)
    payments_queue = await channel.declare_queue("PAYMENTS", durable=True)

    # bind queues
    await tickets_queue.bind(exchange, routing_key="tickets.messages")
    await payments_queue.bind(exchange, routing_key="payments.messages")

    async def rabbitmq_listener():
        async with payments_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    logger.info(f"Received message: {message.body}")
                    # Process the message here
                    await process_message(message.body)
    
    # Run RabbitMQ listener in the background
    task = asyncio.create_task(rabbitmq_listener())
    yield
    # Cleanup
    await channel.close()
    await connection.close()

async def process_message(body):
    message = json.loads(body)
    event = message.get("event")
    if event == "checkout.session.completed":
        ticket = UserTicketCreate(
            user_id=message["user_id"],
            ticket_id=message["ticket_id"],
            quantity=message["quantity"],
            unit_amount=message["unit_amount"],
            created_at=message["created_at"],
        )
        db = next(get_db())
        try:
            await crud.buy_tickets(db, ticket, process_ticket)
        finally:
            db.close()


async def process_ticket(db, user_ticket_db: UserTicketModel):
    user_info = get_user_info_from_user_sub(user_ticket_db.user_id)
    if user_info is None:
        logger.info(f"Found user_info is None for sub {user_ticket_db.user_id}")
    else:
        main_ticket = crud.get_ticket_by_id(db, ticket_id=user_ticket_db.ticket_id)
        await send_message({
            "user_name": user_info["name"],
            "ticket_id": user_ticket_db.id,
            "ticket_name": main_ticket.name,
            "ticket_price": main_ticket.price,
            "to_email": user_info["email"],
        }, "EMAILS")



async def send_message(message: dict, routing_key: str):
    logger.info(f"Sending message: {message} to {routing_key}")
    await exchange.publish(
        message=Message(body=json.dumps(message).encode()),
        routing_key=routing_key
    )

auth = JWTBearer(jwks)


@router.post("/tickets", response_model=TicketInDB, dependencies=[Depends(auth)])
async def create_ticket(
    image: UploadFile,
    game_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    active: bool = Form(...),
    price: float = Form(...),
    stock: int = Form(...), db: Session = Depends(get_db)):
    ticket = TicketCreate(
        game_id=game_id,
        name=name,
        description=description,
        active=active,
        price=price,
        stock=stock,
    )

    # Verify if there is already a created ticket for that game
    if crud.get_ticket_by_game_id(db, game_id) is not None:
        raise HTTPException(status_code=400, detail=f"Ticket already exists for game with id {game_id}")

    _, file_extension = os.path.splitext(image.filename)
    if file_extension not in ACCEPTED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=404,
            detail=f"File extension not supported. Supported file extensions include {ACCEPTED_FILE_EXTENSIONS[0]}",
        )
    if image.content_type not in ACCEPTED_FILE_MIME_TYPE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file MIME type. Supported MIME types include {ACCEPTED_FILE_MIME_TYPE[0]}.",
        )
    if image.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {MAX_FILE_SIZE} bytes.",
        )

    stripe_uploaded_image = stripe.File.create(
        purpose="product_image",
        file=io.BytesIO(image.file.read()),
    )
    stripe_link = stripe.FileLink().create(file=stripe_uploaded_image)
    stripe_product = stripe.Product.create(
        name=ticket.name,
        description=ticket.description,
        active=ticket.active,
        default_price_data={
            "currency": "eur",
            "unit_amount": int(ticket.price * 100),  # In cents
        },
        images=[stripe_link.url],
    )
    stripe_price_id = stripe_product["default_price"]

    created_ticket = crud.post_ticket(
        db, ticket, stripe_product.id, stripe_price_id, stripe_link.url
    )

    # Publish message to MQ for payment microservice
    message = {
        "event": "ticket_created",
        "ticket_id": created_ticket.id,
        "stripe_price_id": stripe_price_id,
        "stock": ticket.stock
    }
    await send_message(message, "tickets.messages")

    return created_ticket


@router.put("/tickets/{ticket_id}", response_model=TicketInDB, dependencies=[Depends(auth)])
async def update_ticket(
    ticket_id: int, ticket_update: TicketUpdate, db: Session = Depends(get_db)
):
    ticket = crud.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=404, detail=f"Ticket with id {ticket_id} not found."
        )
    if len(ticket_update.model_dump(exclude_none=True)) == 0:
        raise HTTPException(
            status_code=400, detail="The content to update the ticket with is empty."
        )
    
    if ticket_update.stock is not None:
        # Publish message to MQ for payment microservice
        message = {
            "event": "ticket_stock_updated",
            "ticket_id": ticket.id,
            "stock": ticket_update.stock
        }
        await send_message(message, "tickets.messages")

    crud.update_ticket(db, ticket, ticket_update)

    stripe.Product.modify(
        ticket.stripe_prod_id,
        name=ticket.name,
        description=ticket.description,
        active=ticket.active,
    )        

    return ticket


@router.post("/tickets/buy", response_model=UserTicketInDB, dependencies=[Depends(auth)])
def buy_ticket_endpoint(ticket: UserTicketCreate, db: Session = Depends(get_db)):
    return crud.buy_tickets(db, ticket)


@router.get("/tickets/user/{user_id}", response_model=List[UserTicketInDB], dependencies=[Depends(auth)])
def get_tickets_by_user_id_endpoint(user_id: int, db: Session = Depends(get_db)):
    return crud.get_tickets_by_user_id(db, user_id)


@router.get("/tickets/{ticket_id}", response_model=TicketInDB, dependencies=[Depends(auth)])
def get_ticket_by_id_endpoint(ticket_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/tickets/game/{game_id}", response_model=TicketInDB, dependencies=[Depends(auth)])
def get_tickets_by_game_id_endpoint(game_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket_by_game_id(db, game_id)
    if ticket is None:
        raise HTTPException(
            status_code=404, detail=f"Ticket not found for game ID {game_id}"
        )
    return ticket


@router.get("/tickets", response_model=List[TicketInDB], dependencies=[Depends(auth)])
def get_tickets_endpoint(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud.get_tickets(db, skip, limit)


@router.put("/tickets/{ticket_id}/validate", response_model=UserTicket, dependencies=[Depends(auth)])
def deactivate_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket_id = ticket_id[:-1]
    ticket = crud.validate_ticket(db, ticket_id)

    return ticket
