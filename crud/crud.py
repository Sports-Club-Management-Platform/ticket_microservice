from fastapi import HTTPException

from fastapi import Depends
from sqlalchemy.orm import Session

from typing import List

from db.database import get_db
from models.ticket import Ticket as TicketModel, Ticket
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketUpdate, UserTicketInDB

def post_ticket(db: Session, ticket: TicketCreate, stripe_prod_id: str):
    """
    Create a ticket.

    :param db: Database session
    :param ticket: Ticket to create
    :return: Ticket created
    """
    ticked_dict = ticket.model_dump(exclude={'image'})
    ticked_dict['stripe_prod_id'] = stripe_prod_id
    ticket_db = TicketModel(**ticked_dict)
    db.add(ticket_db)
    db.commit()
    db.refresh(ticket_db)
    return ticket_db

def update_ticket(db: Session, ticket: Ticket, ticket_update: TicketUpdate):
    """
    Create a ticket.

    :param db: Database session
    :param ticket: Ticket database model
    :param ticket_update: Ticket data to update
    :return: Ticket updated
    """
    ticket_update_parameters = ticket_update.model_dump(exclude_none=True)
    for field_name, field_value in ticket_update_parameters.items():
        setattr(ticket, field_name, field_value)
    db.commit()
    db.refresh(ticket)
    return ticket


def buy_ticket(db: Session, ticket: UserTicketCreate):
    """
    Buy a ticket.

    :param db: Database session
    :param ticket: Ticket to buy
    :return: Ticket bought
    """
    ticket_db = UserTicketModel(**ticket.dict())
    db.add(ticket_db)
    db.commit()
    db.refresh(ticket_db)
    return ticket_db


def get_tickets_by_user_id(db: Session, user_id: int):
    """
    Get tickets for a specific user ID.

    :param db: Database session
    :param user_id: ID of the user
    :return: List of tickets ID for the user
    """
    return db.query(UserTicketModel).filter(UserTicketModel.user_id == user_id).all()

def get_ticket_by_id(db: Session, ticket_id: int):
    """
    Get a ticket by ID.

    :param db: Database session
    :param ticket_id: ID of the ticket
    :return: Ticket
    """
    return db.query(TicketModel).filter(TicketModel.id == ticket_id).first()

def get_tickets_by_game_id(db: Session, game_id: int):
    """
    Get tickets by game ID.

    :param db: Database session
    :param game_id: ID of the game
    :return: List of tickets for the game
    """
    return db.query(TicketModel).filter(TicketModel.game_id == game_id).all()


##########################
### FOR DEBUG PURPOSES ###
##########################
def get_tickets(db: Session, skip: int = 0, limit: int = 100):
    """
    Get all tickets.

    :param db: Database session
    :param skip: Skip
    :param limit: Limit
    :return: List of tickets
    """
    return db.query(TicketModel).offset(skip).limit(limit).all()