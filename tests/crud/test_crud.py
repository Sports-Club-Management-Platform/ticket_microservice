import logging
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.mysql import MySqlContainer

from db.database import get_db
from main import app


from models.ticket import Ticket
from models.userticket import UserTicket
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketUpdate, UserTicketInDB
from crud.crud import (
    post_ticket,
    buy_ticket,
    get_tickets_by_user_id,
    get_ticket_by_id,
    get_tickets_by_game_id,
    get_tickets
)

def test_post_ticket():
    mock_db = MagicMock(spec=Session)

    ticket_data = TicketCreate(
        game_id=1,
        name="Championship Finals",
        description="Final match of the championship",
        status=True,
        type="Socio",
        price=150.0
    )

    result = post_ticket(mock_db, ticket_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, Ticket)


def test_buy_ticket():
    mock_db = MagicMock(spec=Session)

    user_ticket_data = UserTicketCreate(
        user_id=1,
        ticket_id=99,
        quantity=2,
        total_price=300.0,
        created_at="2023-10-01T12:00:00",
        updated_at="2023-10-01T12:00:00"
    )

    result = buy_ticket(mock_db, user_ticket_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, UserTicket)

def test_get_tickets_by_user_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().all.return_value = [
        UserTicketInDB(
        id=1,
        user_id=1,
        ticket_id=99,
        quantity=2,
        total_price=300.0,
        created_at="2023-10-01T12:00:00",
        updated_at="2023-10-01T12:00:00"
    ),
        UserTicketInDB(
        id=2,
        user_id=1,
        ticket_id=100,
        quantity=2,
        total_price=100.0,
        created_at="2023-10-01T12:00:00",
        updated_at="2023-10-01T12:00:00"    
    )
    ]

    result = get_tickets_by_user_id(mock_db, user_id=1)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result == [
        UserTicketInDB(
            id=1,
            user_id=1,
            ticket_id=99,
            quantity=2,
            total_price=300.0,
            created_at="2023-10-01T12:00:00",
            updated_at="2023-10-01T12:00:00"
        ),
        UserTicketInDB(
            id=2,
            user_id=1,
            ticket_id=100,
            quantity=2,
            total_price=100.0,
            created_at="2023-10-01T12:00:00",
            updated_at="2023-10-01T12:00:00"
        )
    ]
    assert all(isinstance(ticket, UserTicketInDB) for ticket in result)


def test_get_ticket_by_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().first.return_value = TicketInDB(
        id=99, game_id=1, name="Championship Finals", description="Final match", status=True, type="Socio", price=150.0
    )

    result = get_ticket_by_id(mock_db, ticket_id=99)

    # mock_db.query().filter.assert_called_once()
    # mock_db.query.assert_called_once_with(Ticket)

    assert isinstance(result, TicketInDB)
    assert result.id == 99

def test_get_tickets_by_game_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().all.return_value = [
        TicketInDB(id=99, game_id=1, name="Championship Finals", description="Final match", status=True, type="Socio", price=150.0)
    ]

    result = get_tickets_by_game_id(mock_db, game_id=1)

    # mock_db.query.assert_called_once_with(Ticket)
    # mock_db.query().filter.assert_called_once()

    assert isinstance(result, list)
    assert len(result) == 1
    assert all(isinstance(ticket, TicketInDB) for ticket in result)

def test_get_tickets():
    mock_db = MagicMock(spec=Session)

    mock_db.query().offset().limit().all.return_value = [
        TicketInDB(id=99, game_id=1, name="Championship Finals", description="Final match", status=True, type="Socio", price=150.0),
        TicketInDB(id=100, game_id=2, name="Championship Finals", description="Final match", status=True, type="Socio", price=150.0)
    ]

    result = get_tickets(mock_db, skip=0, limit=100)

    # mock_db.query.assert_called_once_with(Ticket)
    # mock_db.query().offset.assert_called_once_with(0)
    # mock_db.query().offset().limit.assert_called_once_with(100)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ticket, TicketInDB) for ticket in result)
