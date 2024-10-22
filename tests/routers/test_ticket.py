import os
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from db.database import get_db
from main import app

from models.ticket import Ticket
from models.userticket import UserTicket
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketUpdate, UserTicketInDB


client = TestClient(app)

@pytest.fixture(scope="module")
def mock_db():
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db

@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    mock_db.reset_mock()


ticket_data = {
    "id": 1,
    "game_id": 101,
    "name": "Championship Finals",
    "description": "Final match of the championship",
    "status": True,
    "type": "Socio",
    "price": 150.0
}

user_ticket_data = {
    "id": 1,
    "user_id": 1,
    "ticket_id": 1,
    "quantity": 2,
    "total_price": 300.0,
    "created_at": "2023-10-01T12:00:00",
    "updated_at": "2023-10-01T12:00:00"
}

@patch("routers.ticket.post_ticket", return_value=TicketInDB(**ticket_data))
def test_post_ticket(mock_post_ticket, mock_db):
    response = client.post("/tickets", json=ticket_data)
    
    assert response.status_code == 200
    assert response.json() == ticket_data
    mock_post_ticket.assert_called_once_with(mock_db, TicketCreate(**ticket_data))

@patch("routers.ticket.buy_ticket", return_value=UserTicketInDB(**user_ticket_data))
def test_buy_ticket(mock_buy_ticket, mock_db):
    response = client.post("/tickets/buy", json=user_ticket_data)

    assert response.status_code == 200
    assert response.json() == user_ticket_data
    mock_buy_ticket.assert_called_once_with(mock_db, UserTicketCreate(**user_ticket_data))

@patch("routers.ticket.get_tickets_by_user_id", return_value=[UserTicketInDB(**user_ticket_data)])
def test_get_tickets_by_user_id(mock_get_tickets_by_user_id, mock_db):
    user_id = 1
    response = client.get(f"/tickets/user/{user_id}")

    assert response.status_code == 200
    assert response.json() == [user_ticket_data]
    mock_get_tickets_by_user_id.assert_called_once_with(mock_db, user_id)

@patch("routers.ticket.get_ticket_by_id", return_value=TicketInDB(**ticket_data))
def test_get_ticket_by_id(mock_get_ticket_by_id, mock_db):
    ticket_id = 1
    response = client.get(f"/tickets/{ticket_id}")

    assert response.status_code == 200
    assert response.json() == ticket_data
    mock_get_ticket_by_id.assert_called_once_with(mock_db, ticket_id)

@patch("routers.ticket.get_ticket_by_id", return_value=None)
def test_get_ticket_by_id_not_found(mock_get_ticket_by_id, mock_db):
    ticket_id = 999
    response = client.get(f"/tickets/{ticket_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}
    mock_get_ticket_by_id.assert_called_once_with(mock_db, ticket_id)

@patch("routers.ticket.get_tickets_by_game_id", return_value=[TicketInDB(**ticket_data)])
def test_get_tickets_by_game_id(mock_get_tickets_by_game_id, mock_db):
    game_id = 123
    response = client.get(f"/tickets/game/{game_id}")

    assert response.status_code == 200
    assert response.json() == [ticket_data]
    mock_get_tickets_by_game_id.assert_called_once_with(mock_db, game_id)

@patch("routers.ticket.get_tickets", return_value=[TicketInDB(**ticket_data)])
def test_get_tickets(mock_get_tickets):
    response = client.get("/tickets")

    assert response.status_code == 200
    assert response.json() == [ticket_data]
    mock_get_tickets.assert_called_once()