import asyncio
import io
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from locale import currency
from typing import List

import aio_pika
import stripe
from aio_pika import Message
from crud import crud
from db.database import get_db
from fastapi import (APIRouter, Depends, FastAPI, File, Form, HTTPException,
                     UploadFile)
from models.ticket import Ticket as TicketModel
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketInDB, TicketUpdate
from schemas.userticket import (UserTicketCreate, UserTicketInDB,
                                UserTicketUpdate)
from sqlalchemy.orm import Session

router = APIRouter(tags=["Tickets"])

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
stripe.api_key = os.getenv("STRIPE_API_KEY")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
MAX_FILE_SIZE = 2097152  # 2MB - Stripe maximum
ACCEPTED_FILE_MIME_TYPE = ["image/png"]
ACCEPTED_FILE_EXTENSIONS = [".png"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global connection, channel, exchange, queue
    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange("exchange", type=aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue("TICKETS", durable=True)
    await queue.bind(exchange, routing_key="TICKETS")

    async def rabbitmq_listener():
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    print("Received message:", message.body)
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
            total_price=message["total_price"],
            created_at=message["created_at"],
        )
        crud.buy_ticket(ticket)

async def send_message(message: dict):
    await exchange.publish(
        Message(body=json.dumps(message).encode()),
        routing_key="TICKETS"
    )


@router.post("/tickets", response_model=TicketInDB)
async def create_ticket(ticket: TicketCreate = Form(), db: Session = Depends(get_db)):
    _, file_extension = os.path.splitext(ticket.image.filename)
    if file_extension not in ACCEPTED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=404,
            detail=f"File extension not supported. Supported file extensions include {ACCEPTED_FILE_EXTENSIONS[0]}",
        )
    if ticket.image.content_type not in ACCEPTED_FILE_MIME_TYPE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file MIME type. Supported MIME types include {ACCEPTED_FILE_MIME_TYPE[0]}.",
        )
    if ticket.image.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {MAX_FILE_SIZE} bytes.",
        )

    stripe_uploaded_image = stripe.File.create(
        purpose="product_image",
        file=io.BytesIO(ticket.image.file.read()),
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
    await send_message(message)

    return created_ticket


@router.put("/tickets/{ticket_id}", response_model=TicketInDB)
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
        await send_message(message)

    crud.update_ticket(db, ticket, ticket_update)

    stripe.Product.modify(
        ticket.stripe_prod_id,
        name=ticket.name,
        description=ticket.description,
        active=ticket.active,
    )        

    return ticket


@router.post("/tickets/buy", response_model=UserTicketInDB)
def buy_ticket_endpoint(ticket: UserTicketCreate, db: Session = Depends(get_db)):
    return crud.buy_ticket(db, ticket)


@router.get("/tickets/user/{user_id}", response_model=List[UserTicketInDB])
def get_tickets_by_user_id_endpoint(user_id: int, db: Session = Depends(get_db)):
    return crud.get_tickets_by_user_id(db, user_id)


@router.get("/tickets/{ticket_id}", response_model=TicketInDB)
def get_ticket_by_id_endpoint(ticket_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/tickets/game/{game_id}", response_model=TicketInDB)
def get_tickets_by_game_id_endpoint(game_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket_by_game_id(db, game_id)
    if ticket is None:
        raise HTTPException(
            status_code=404, detail=f"Ticket not found for game ID {game_id}"
        )
    return ticket


@router.get("/tickets", response_model=List[TicketInDB])
def get_tickets_endpoint(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud.get_tickets(db, skip, limit)
