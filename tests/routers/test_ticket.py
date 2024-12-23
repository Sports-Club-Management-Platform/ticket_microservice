import io
import pytest
from fastapi import UploadFile
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from db.database import get_db
from main import app
from models.ticket import Ticket as TicketModel
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketInDB

client = TestClient(app)


@pytest.fixture(scope="module")
def mock_db():
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db


@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    mock_db.reset_mock()


@patch(
    "routers.ticket.crud.post_ticket",
    return_value=TicketInDB(
        id=1,
        stripe_prod_id="prod_123",
        stripe_price_id="price_123",
        stripe_image_url="https://example.com/image.jpg",
        game_id=101,
        name="Championship Finals",
        description="Final match",
        active=True,
        price=150.0,
    ),
)
@patch(
    "routers.ticket.stripe.FileLink.create",
    return_value=MagicMock(url="https://example.com/image.jpg"),
)
@patch("routers.ticket.stripe.File.create", return_value={"id": "file_123"})
@patch(
    "routers.ticket.stripe.FileLink.create",
    return_value={"url": "https://example.com/image.jpg"},
)
def test_post_ticket(
    mock_file_link, mock_file, mock_product, mock_post_ticket, mock_db
):
    payload = {
        "game_id": 101,
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": True,
        "price": 150.0,
    }
    files = {"image": ("image.png", io.BytesIO(b"fake_image_data"), "image/png")}

    response = client.post("/tickets", data=payload, files=files)

    assert response.status_code == 200
    mock_file.assert_called_once()
    mock_product.assert_called_once()
    mock_post_ticket.assert_called_once()


# Teste para extensão de arquivo inválida
def test_create_ticket_invalid_extension():
    payload = {
        "game_id": "101",
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": "true",
        "price": "150.0",
    }
    files = {
        "image": ("image.txt", b"fake_image_data", "image/png")
    }  # Extensão inválida

    response = client.post("/tickets", data=payload, files=files)

    assert response.status_code == 404
    assert response.json() == {
        "detail": "File extension not supported. Supported file extensions include .png"
    }


# Teste para tipo MIME inválido
def test_create_ticket_invalid_mime_type():
    payload = {
        "game_id": "101",
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": "true",
        "price": "150.0",
    }
    files = {"image": ("image.png", b"fake_image_data", "image/jpeg")}  # MIME inválido

    response = client.post("/tickets", data=payload, files=files)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid file MIME type. Supported MIME types include image/png."
    }


# Teste para tamanho de arquivo excedido
def test_create_ticket_file_too_large():
    payload = {
        "game_id": "101",
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": "true",
        "price": "150.0",
    }
    # Simulando um arquivo maior que o limite
    large_file = b"0" * (2097153)  # 2MB + 1 byte
    files = {"image": ("image.png", large_file, "image/png")}

    response = client.post("/tickets", data=payload, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "File too large. Max size is 2097152 bytes."}


@patch(
    "routers.ticket.crud.get_ticket_by_id",
    return_value=MagicMock(
        id=1,
        stripe_price_id="price_123",
        stripe_image_url="https://example.com/image.jpg",
        game_id=101,
        name="Championship Finals",
        description="Final match",
        active=True,
        price=150.0,
    ),
)
@patch("routers.ticket.crud.update_ticket", return_value=None)
@patch("routers.ticket.stripe.Product.modify")
def test_update_ticket(mock_modify, mock_update_ticket, mock_get_ticket_by_id, mock_db):
    payload = {"name": "New Name", "description": "Updated description"}
    ticket_id = 1

    # Mock para refletir mudanças feitas durante a atualização
    mock_ticket = mock_get_ticket_by_id.return_value
    mock_ticket.name = "New Name"
    mock_ticket.description = "Updated description"

    response = client.put(f"/tickets/{ticket_id}", json=payload)

    # Verifique o código de status e o conteúdo da resposta
    assert response.status_code == 200
    response_data = response.json()

    # Validação dos campos do TicketInDB
    assert response_data == {
        "id": 1,
        "game_id": 101,
        "name": "New Name",
        "description": "Updated description",
        "active": True,
        "price": 150.0,
        "stripe_price_id": "price_123",
        "stripe_image_url": "https://example.com/image.jpg",
    }

    # Verifique chamadas dos mocks
    mock_get_ticket_by_id.assert_called_once_with(mock_db, ticket_id)
    mock_update_ticket.assert_called_once()


# Teste para erro em atualização de ticket
@patch("routers.ticket.crud.get_ticket_by_id", return_value=None)
def test_update_ticket_not_found(mock_get_ticket_by_id, mock_db):
    payload = {"name": "New Name"}
    ticket_id = 999

    response = client.put(f"/tickets/{ticket_id}", json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket with id 999 not found."}
    mock_get_ticket_by_id.assert_called_once_with(mock_db, ticket_id)


# Testes para outras rotas
@patch("routers.ticket.crud.get_ticket_by_id", return_value=None)
def test_get_ticket_by_id_not_found(mock_get_ticket_by_id, mock_db):
    ticket_id = 999
    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=None)
def test_get_tickets_by_game_id_not_found(mock_get_tickets_by_game_id, mock_db):
    game_id = 999
    response = client.get(f"/tickets/game/{game_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found for game ID 999"}


@patch("routers.ticket.crud.get_tickets", return_value=[])
def test_get_tickets_no_results(mock_get_tickets, mock_db):
    response = client.get("/tickets")
    assert response.status_code == 200
    assert response.json() == []
