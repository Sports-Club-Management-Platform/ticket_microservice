import os
from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from db.database import get_db

from models.ticket import Ticket as TicketModel
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketUpdate, UserTicketInDB
from crud.ticket import buy_ticket, get_tickets_by_user_id, get_ticket_by_id, get_tickets_by_game_id, get_tickets, post_ticket

router = APIRouter(tags=["Tickets"])

@router.post("/tickets", response_model=TicketInDB)
def post_ticket_endpoint(ticket: TicketCreate, db: Session = Depends(get_db)):
    return post_ticket(db, ticket)

@router.post("/tickets/buy", response_model=UserTicketInDB)
def buy_ticket_endpoint(ticket: UserTicketCreate, db: Session = Depends(get_db)):
    return buy_ticket(db, ticket)

@router.get("/tickets/user/{user_id}", response_model=List[UserTicketInDB])
def get_tickets_by_user_id_endpoint(user_id: int, db: Session = Depends(get_db)):
    return get_tickets_by_user_id(db, user_id)

@router.get("/tickets/{ticket_id}", response_model=TicketInDB)
def get_ticket_by_id_endpoint(ticket_id: int, db: Session = Depends(get_db)):
    ticket = get_ticket_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.get("/tickets/game/{game_id}", response_model=List[TicketInDB])
def get_tickets_by_game_id_endpoint(game_id: int, db: Session = Depends(get_db)):
    return get_tickets_by_game_id(db, game_id)

@router.get("/tickets", response_model=List[TicketInDB])
def get_tickets_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_tickets(db, skip, limit)