import io
import json

import pytest
from fastapi import UploadFile
from datetime import datetime
from fastapi.exceptions import HTTPException
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from db.database import get_db
from main import app
from models.ticket import Ticket as TicketModel
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketInDB
from tests.routers.helpers import DualAccessDict

from routers.ticket import auth
from auth.JWTBearer import JWTAuthorizationCredentials
from dotenv import load_dotenv

client = TestClient(app)


load_dotenv()

@pytest.fixture(scope="module")
def mock_db():
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db


@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    mock_db.reset_mock()

@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=True)  # Not None to simulate existing ticket
@patch(
    "routers.ticket.crud.post_ticket",
    return_value=TicketInDB(
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
@patch(
    "routers.ticket.stripe.Product.create",
    return_value=DualAccessDict(
        id="prod_123", default_price="price_123"
    ),
)
@patch("routers.ticket.stripe.File.create", return_value=DualAccessDict(id='file_123'))
@patch(
    "routers.ticket.stripe.FileLink.create",
    return_value=DualAccessDict(url="https://example.com/image.jpg")
)
def test_post_ticket_for_game_with_ticket(
        mock_file_link, mock_file, mock_product, mock_post_ticket, get_ticket_by_game_id_func, mock_db
):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    with patch("routers.ticket.exchange", MagicMock()) as exchange_mock:
        publish_mock = AsyncMock(return_value=None)
        exchange_mock.publish = publish_mock
        TicketModel(
            id=1,
            game_id=1,
            name="Championship Finals",
            description="Final match",
            active=True,
            price=150.0,
            stripe_prod_id="prod_123",
            stripe_price_id="price_123",
            stripe_image_url="https://example.com/image.jpg",
        ),
        payload = {
            "game_id": 101,
            "name": "Championship Finals",
            "description": "Final match of the championship",
            "active": True,
            "price": 150.0,
            "stock": 10
        }
        files = {"image": ("image.png", io.BytesIO(b"fake_image_data"), "image/png")}

        response = client.post("/tickets", data=payload, files=files, headers=headers)

        assert response.status_code == 400
        assert response.text == '{"detail":"Ticket already exists for game with id 101"}'
        assert mock_file.call_count == 0
        assert mock_product.call_count == 0
        assert mock_post_ticket.call_count == 0
        assert mock_file_link.call_count == 0
        assert get_ticket_by_game_id_func.call_args[0] == (mock_db, 101)


@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=None)  # Mock to simulate no existing ticket
@patch(
    "routers.ticket.crud.post_ticket",
    return_value=TicketInDB(
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
@patch(
    "routers.ticket.stripe.Product.create",
    return_value=DualAccessDict(
        id="prod_123", default_price="price_123"
    ),
)
@patch("routers.ticket.stripe.File.create", return_value=DualAccessDict(id='file_123'))
@patch(
    "routers.ticket.stripe.FileLink.create",
    return_value=DualAccessDict(url="https://example.com/image.jpg")
)
def test_post_ticket_for_game_with_no_ticket(
    mock_file_link, mock_file, mock_product, mock_post_ticket, get_ticket_by_game_id_func, mock_db
):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    with patch("routers.ticket.exchange", MagicMock()) as exchange_mock:
        publish_mock = AsyncMock(return_value=None)
        exchange_mock.publish = publish_mock
        TicketModel(
            id=1,
            game_id=1,
            name="Championship Finals",
            description="Final match",
            active=True,
            price=150.0,
            stripe_prod_id="prod_123",
            stripe_price_id="price_123",
            stripe_image_url="https://example.com/image.jpg",
        ),
        payload = {
            "game_id": 101,
            "name": "Championship Finals",
            "description": "Final match of the championship",
            "active": True,
            "price": 150.0,
            "stock": 10
        }
        files = {"image": ("image.png", io.BytesIO(b"fake_image_data"), "image/png")}

        response = client.post("/tickets", data=payload, files=files, headers=headers)

        assert response.status_code == 200
        mock_file_link.assert_called_once()
        mock_file.assert_called_once()
        mock_product.assert_called_once()
        mock_post_ticket.assert_called_once()
        assert publish_mock.call_count == 1
        _, kwargs = publish_mock.call_args
        assert kwargs.get('routing_key') == "tickets.messages"
        assert kwargs.get('message').body == json.dumps({
            "event": "ticket_created",
            "ticket_id": 1,
            "stripe_price_id": "price_123",
            "stock": 10
        }).encode()
        assert get_ticket_by_game_id_func.call_args[0] == (mock_db, 101)


# Teste para extensão de arquivo inválida
@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=None)
def test_create_ticket_invalid_extension(get_ticket_by_game_id_func, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    payload = {
        "game_id": "101",
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": "true",
        "price": "150.0",
        "stock": 10
    }
    files = {
        "image": ("image.txt", b"fake_image_data", "image/png")
    }  # Extensão inválida

    response = client.post("/tickets", data=payload, files=files, headers=headers)

    assert get_ticket_by_game_id_func.call_args[0] == (mock_db, 101)
    assert response.status_code == 404
    assert response.json() == {
        "detail": "File extension not supported. Supported file extensions include .png"
    }


# Teste para tipo MIME inválido
@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=None)
def test_create_ticket_invalid_mime_type(get_ticket_by_game_id_func, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    payload = {
        "game_id": "101",
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": "true",
        "price": "150.0",
        "stock": 10
    }
    files = {"image": ("image.png", b"fake_image_data", "image/jpeg")}  # MIME inválido

    response = client.post("/tickets", data=payload, files=files, headers=headers)

    assert get_ticket_by_game_id_func.call_args[0] == (mock_db, 101)
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid file MIME type. Supported MIME types include image/png."
    }



# Teste para tamanho de arquivo excedido
@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=None)
def test_create_ticket_file_too_large(get_ticket_by_game_id_func, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    payload = {
        "game_id": "101",
        "name": "Championship Finals",
        "description": "Final match of the championship",
        "active": "true",
        "price": "150.0",
        "stock": 10
    }
    # Simulando um arquivo maior que o limite
    large_file = b"0" * (2097153)  # 2MB + 1 byte
    files = {"image": ("image.png", large_file, "image/png")}

    response = client.post("/tickets", data=payload, files=files, headers=headers)

    assert get_ticket_by_game_id_func.call_args[0] == (mock_db, 101)
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
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )

    headers = {"Authorization": "Bearer token"}


    with patch("routers.ticket.exchange", MagicMock()) as exchange_mock:
        publish_mock = AsyncMock(return_value=None)
        exchange_mock.publish = publish_mock

        payload = {"name": "New Name", "description": "Updated description", "stock": 10}
        ticket_id = 1

        # Mock para refletir mudanças feitas durante a atualização
        mock_ticket = mock_get_ticket_by_id.return_value
        mock_ticket.name = "New Name"
        mock_ticket.description = "Updated description"

        response = client.put(f"/tickets/{ticket_id}", json=payload, headers=headers)

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

        # Stock é updated em outro microserviço - verificar que mensagem foi enviada
        assert publish_mock.call_count == 1
        _, kwargs = publish_mock.call_args
        assert kwargs.get('routing_key') == "tickets.messages"
        assert kwargs.get('message').body == json.dumps({
            "event": "ticket_stock_updated",
            "ticket_id": ticket_id,
            "stock": 10
        }).encode()



# Teste para erro em atualização de ticket
@patch("routers.ticket.crud.get_ticket_by_id", return_value=None)
def test_update_ticket_not_found(mock_get_ticket_by_id, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    payload = {"name": "New Name"}
    ticket_id = 999

    response = client.put(f"/tickets/{ticket_id}", json=payload, headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket with id 999 not found."}
    mock_get_ticket_by_id.assert_called_once_with(mock_db, ticket_id)


# Testes para outras rotas
@patch("routers.ticket.crud.get_ticket_by_id", return_value=None)
def test_get_ticket_by_id_not_found(mock_get_ticket_by_id, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    ticket_id = 999
    response = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


@patch("routers.ticket.crud.get_ticket_by_game_id", return_value=None)
def test_get_tickets_by_game_id_not_found(mock_get_tickets_by_game_id, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    game_id = 999
    response = client.get(f"/tickets/game/{game_id}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found for game ID 999"}


@patch("routers.ticket.crud.get_tickets", return_value=[])
def test_get_tickets_no_results(mock_get_tickets, mock_db):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    response = client.get("/tickets", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@patch("routers.ticket.crud.validate_ticket")
def test_deactivate_ticket_success(mock_validate_ticket, mock_db):
    """Teste para desativar um ticket com sucesso."""

    mock_ticket = UserTicketInDB(  # Agora usamos um schema Pydantic para garantir o formato correto
        id='1',
        user_id='12b-12b-12b',
        ticket_id=99,
        unit_amount=300.0,
        created_at="2023-10-01T12:00:00",
        is_active=False,
        deactivated_at=str(datetime.now()),
    )

    mock_validate_ticket.return_value = mock_ticket

    response = client.put("/tickets/1234/validate")

    assert response.status_code == 200

    response_data = response.json()

    # Adicionamos um print para debug (caso necessário)
    print("Response JSON:", response_data)

    # Agora verificamos se as chaves existem antes de acessá-las
    assert "is_active" in response_data
    assert "deactivated_at" in response_data

    assert response_data["is_active"] is False
    assert response_data["deactivated_at"] is not None

    mock_validate_ticket.assert_called_once_with(mock_db, '123')


@patch(
    "routers.ticket.crud.validate_ticket",
    side_effect=HTTPException(status_code=404, detail="Ticket with id 99 not found."),
)
def test_deactivate_ticket_not_found(mock_validate_ticket, mock_db):
    """Teste para tentar desativar um ticket inexistente."""
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    response = client.put("/tickets/99/validate", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket with id 99 not found."}

    mock_validate_ticket.assert_called_once_with(mock_db, '9')


@patch(
    "routers.ticket.crud.validate_ticket",
    side_effect=HTTPException(
        status_code=400, detail="Ticket with id 2 is already deactivated."
    ),
)
def test_deactivate_ticket_already_deactivated(mock_validate_ticket, mock_db):
    """Teste para tentar desativar um ticket já desativado."""
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )
    headers = {"Authorization": "Bearer token"}

    response = client.put("/tickets/22/validate", headers=headers)

    assert response.status_code == 400
    assert response.json() == {"detail": "Ticket with id 2 is already deactivated."}

    mock_validate_ticket.assert_called_once_with(mock_db, '2')

