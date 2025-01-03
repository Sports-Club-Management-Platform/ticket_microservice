from unittest.mock import MagicMock
from fastapi import UploadFile
from io import BytesIO
from sqlalchemy.orm import Session
from models.ticket import Ticket as TicketModel
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB
from schemas.userticket import UserTicketCreate, UserTicketInDB
from crud.crud import (
    post_ticket,
    buy_ticket,
    get_tickets_by_user_id,
    get_ticket_by_id,
    get_ticket_by_game_id,
    get_tickets,
)


def test_post_ticket():
    mock_db = MagicMock(spec=Session)
    stripe_prod_id = "prod_123"
    stripe_price_id = "price_123"
    stripe_image_url = "https://example.com/image.jpg"

    # Simulação de UploadFile
    mock_image = UploadFile(filename="image.jpg", file=BytesIO(b"fake image data"))

    ticket_data = TicketCreate(
        game_id=1,
        name="Championship Finals",
        description="Final match of the championship",
        active=True,
        price=150.0,
        image=mock_image,
    )

    result = post_ticket(
        mock_db, ticket_data, stripe_prod_id, stripe_price_id, stripe_image_url
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, TicketModel)
    assert result.game_id == 1
    assert result.name == "Championship Finals"
    assert result.active is True
    assert result.price == 150.0
    assert result.stripe_prod_id == stripe_prod_id
    assert result.stripe_price_id == stripe_price_id
    assert result.stripe_image_url == stripe_image_url


def test_buy_ticket():
    mock_db = MagicMock(spec=Session)

    user_ticket_data = UserTicketCreate(
        user_id=1,
        ticket_id=99,
        quantity=2,
        total_price=300.0,
        created_at="2023-10-01T12:00:00",
        updated_at="2023-10-01T12:00:00",
    )

    result = buy_ticket(mock_db, user_ticket_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, UserTicketModel)
    assert result.user_id == 1
    assert result.ticket_id == 99
    assert result.quantity == 2
    assert result.total_price == 300.0
    assert result.created_at == "2023-10-01T12:00:00"
    assert result.updated_at == "2023-10-01T12:00:00"


def test_get_tickets_by_user_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().all.return_value = [
        UserTicketModel(
            id=1,
            user_id=1,
            ticket_id=99,
            quantity=2,
            total_price=300.0,
            created_at="2023-10-01T12:00:00",
            updated_at="2023-10-01T12:00:00",
        ),
        UserTicketModel(
            id=2,
            user_id=1,
            ticket_id=100,
            quantity=1,
            total_price=150.0,
            created_at="2023-10-02T12:00:00",
            updated_at="2023-10-02T12:00:00",
        ),
    ]

    result = get_tickets_by_user_id(mock_db, user_id=1)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ticket, UserTicketModel) for ticket in result)
    assert result[0].user_id == 1
    assert result[1].user_id == 1


def test_get_ticket_by_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().first.return_value = TicketModel(
        id=99,
        game_id=1,
        name="Championship Finals",
        description="Final match",
        active=True,
        price=150.0,
        stripe_prod_id="prod_123",
        stripe_price_id="price_123",
        stripe_image_url="https://example.com/image.jpg",
    )

    result = get_ticket_by_id(mock_db, ticket_id=99)

    assert isinstance(result, TicketModel)
    assert result.id == 99
    assert result.name == "Championship Finals"
    assert result.active is True


def test_get_ticket_by_game_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().first.return_value = TicketModel(
        id=99,
        game_id=1,
        name="Championship Finals",
        description="Final match",
        active=True,
        price=150.0,
        stripe_prod_id="prod_123",
        stripe_price_id="price_123",
        stripe_image_url="https://example.com/image.jpg",
    )

    result = get_ticket_by_game_id(mock_db, game_id=1)

    assert isinstance(result, TicketModel)
    assert result.game_id == 1
    assert result.active is True


def test_get_tickets():
    mock_db = MagicMock(spec=Session)

    mock_db.query().offset().limit().all.return_value = [
        TicketModel(
            id=99,
            game_id=1,
            name="Championship Finals",
            description="Final match",
            active=True,
            price=150.0,
            stripe_prod_id="prod_123",
            stripe_price_id="price_123",
            stripe_image_url="https://example.com/image.jpg",
        ),
        TicketModel(
            id=100,
            game_id=2,
            name="Semi Finals",
            description="Semi-final match",
            active=True,
            price=120.0,
            stripe_prod_id="prod_124",
            stripe_price_id="price_124",
            stripe_image_url="https://example.com/image2.jpg",
        ),
    ]

    result = get_tickets(mock_db, skip=0, limit=10)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ticket, TicketModel) for ticket in result)
    assert result[0].id == 99
    assert result[1].id == 100
