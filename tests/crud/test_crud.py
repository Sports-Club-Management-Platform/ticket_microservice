import asyncio
import logging
import sys
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from models.ticket import Ticket as TicketModel
from models.userticket import UserTicket as UserTicketModel
from schemas.ticket import TicketCreate, TicketUpdate
from schemas.userticket import UserTicketCreate
from crud.crud import (
    post_ticket,
    buy_tickets,
    get_tickets_by_user_id,
    get_ticket_by_id,
    get_ticket_by_game_id,
    get_tickets,
    validate_ticket, update_ticket,
)

# Mock asynchronous callback function
async def mock_send_message_callback(db, user_ticket_db):
    pass  # Simulates a no-op async function

# Mock asynchronous callback function with a MagicMock to track calls
mock_send_message_callback2 = AsyncMock()


def test_post_ticket():
    mock_db = MagicMock(spec=Session)
    stripe_prod_id = "prod_123"
    stripe_price_id = "price_123"
    stripe_image_url = "https://example.com/image.jpg"

    ticket_data = TicketCreate(
        game_id=1,
        name="Championship Finals",
        description="Final match of the championship",
        active=True,
        price=150.0,
        stock=10
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
    # stock is not saved here
    assert result.stripe_prod_id == stripe_prod_id
    assert result.stripe_price_id == stripe_price_id
    assert result.stripe_image_url == stripe_image_url

def test_update_ticket():
    mock_db = MagicMock(spec=Session)
    new_name = "Championship Finals 2"
    new_description = "Final match of the championship 2"
    new_active = False
    new_stock = 0 # irrelevant it is not saved in this microservice

    ticket_db = TicketModel(
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

    ticket_update = TicketUpdate(name=new_name, description=new_description, active=new_active, stock=new_stock)

    result = update_ticket(mock_db, ticket_db, ticket_update)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, TicketModel)
    assert result.game_id == 1
    assert result.name == new_name
    assert result.description == new_description
    assert result.active == new_active
    assert result.price == 150.0
    # stock is not saved here

@patch("crud.crud.generate_random_user_ticket_id", return_value='123456789012')
def test_buy_one_ticket_not_repeated_random_id(generate_random_user_ticket_id_func):
    mock_db = MagicMock(spec=Session)
    quantity = 1                                                                    # one ticket
    mock_db.query.return_value.filter.return_value.first.return_value = None        # not repeated

    user_ticket_data = UserTicketCreate(
        user_id='12b-12b-12b',
        ticket_id=99,
        quantity=quantity,
        unit_amount=300.0,
        created_at="2023-10-01T12:00:00",
        is_active=True,
        deactivated_at="",
    )

    asyncio.run(
        buy_tickets(mock_db, user_ticket_data, mock_send_message_callback)
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    generate_random_user_ticket_id_func.assert_called_once_with(12)
    result = mock_db.add.call_args_list[0][0][0]

    assert isinstance(result, UserTicketModel)
    assert result.id == '123456789012'
    assert result.user_id == '12b-12b-12b'
    assert result.ticket_id == 99
    assert result.unit_amount == 300.0
    assert result.created_at == "2023-10-01T12:00:00"
    assert result.is_active is True
    assert result.deactivated_at == ""


@patch("crud.crud.generate_random_user_ticket_id", side_effect=['111111111111', '123456789012'])
def test_buy_one_ticket_repeated_random_id_at_first(generate_random_user_ticket_id_func):
    mock_db = MagicMock(spec=Session)
    quantity = 1                                                                    # one ticket
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        UserTicketModel(id='111111111111'), # repeated
        None                                # not repeated
    ]

    user_ticket_data = UserTicketCreate(
        user_id='12b-12b-12b',
        ticket_id=99,
        quantity=quantity,
        unit_amount=300.0,
        created_at="2023-10-01T12:00:00",
        is_active=True,
        deactivated_at="",
    )

    asyncio.run(
        buy_tickets(mock_db, user_ticket_data, mock_send_message_callback)
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert generate_random_user_ticket_id_func.call_count == 2
    assert generate_random_user_ticket_id_func.call_args_list[0][0][0] == 12
    assert generate_random_user_ticket_id_func.call_args_list[1][0][0] == 12

    result = mock_db.add.call_args_list[0][0][0]
    assert isinstance(result, UserTicketModel)
    assert result.id == '123456789012'
    assert result.user_id == '12b-12b-12b'
    assert result.ticket_id == 99
    assert result.unit_amount == 300.0
    assert result.created_at == "2023-10-01T12:00:00"
    assert result.is_active is True
    assert result.deactivated_at == ""


@patch("crud.crud.generate_random_user_ticket_id", side_effect=['123456789012', '003456789012', '000056789012'])
def test_buy_multiple_tickets_not_repeated_random_id(generate_random_user_ticket_id_func):
    mock_db = MagicMock(spec=Session)
    quantity = 3                                                                    # three ticket
    mock_db.query.return_value.filter.return_value.first.return_value = None        # not repeated

    user_ticket_data = UserTicketCreate(
        user_id='12b-12b-12b',
        ticket_id=99,
        quantity=quantity,
        unit_amount=300.0,
        created_at="2023-10-01T12:00:00",
        is_active=True,
        deactivated_at="",
    )

    asyncio.run(
        buy_tickets(mock_db, user_ticket_data, mock_send_message_callback2)
    )

    assert mock_db.add.call_count == 3
    assert mock_db.commit.call_count == 3
    assert mock_db.refresh.call_count == 3
    assert generate_random_user_ticket_id_func.call_count == 3
    assert generate_random_user_ticket_id_func.call_args_list[0][0][0] == 12
    assert generate_random_user_ticket_id_func.call_args_list[1][0][0] == 12
    assert generate_random_user_ticket_id_func.call_args_list[2][0][0] == 12

    result_1 = mock_db.add.call_args_list[0][0][0]
    assert isinstance(result_1, UserTicketModel)
    assert result_1.id == '123456789012'
    assert result_1.user_id == '12b-12b-12b'
    assert result_1.ticket_id == 99
    assert result_1.unit_amount == 300.0
    assert result_1.created_at == "2023-10-01T12:00:00"
    assert result_1.is_active is True
    assert result_1.deactivated_at == ""
    actual_db, actual_user_ticket = mock_send_message_callback2.call_args_list[0][0]
    assert mock_db == actual_db
    assert result_1 == actual_user_ticket

    result_2 = mock_db.add.call_args_list[1][0][0]
    assert isinstance(result_2, UserTicketModel)
    assert result_2.id == '003456789012'
    assert result_2.user_id == '12b-12b-12b'
    assert result_2.ticket_id == 99
    assert result_2.unit_amount == 300.0
    assert result_2.created_at == "2023-10-01T12:00:00"
    assert result_2.is_active is True
    assert result_2.deactivated_at == ""
    actual_db, actual_user_ticket = mock_send_message_callback2.call_args_list[1][0]
    assert mock_db == actual_db
    assert result_2 == actual_user_ticket

    result_3 = mock_db.add.call_args_list[2][0][0]
    assert isinstance(result_3, UserTicketModel)
    assert result_3.id == '000056789012'
    assert result_3.user_id == '12b-12b-12b'
    assert result_3.ticket_id == 99
    assert result_3.unit_amount == 300.0
    assert result_3.created_at == "2023-10-01T12:00:00"
    assert result_3.is_active is True
    assert result_3.deactivated_at == ""
    actual_db, actual_user_ticket = mock_send_message_callback2.call_args_list[2][0]
    assert mock_db == actual_db
    assert result_3 == actual_user_ticket


def test_get_tickets_by_user_id():
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().all.return_value = [
        UserTicketModel(
            id='123456789012',
            user_id='12b-12b-12b',
            ticket_id=99,
            unit_amount=300.0,
            created_at="2023-10-01T12:00:00",
        ),
        UserTicketModel(
            id='003456789012',
            user_id='12b-12b-12b',
            ticket_id=100,
            unit_amount=150.0,
            created_at="2023-10-02T12:00:00",
        ),
    ]

    result = get_tickets_by_user_id(mock_db, user_id=1)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ticket, UserTicketModel) for ticket in result)
    assert result[0].user_id == '12b-12b-12b'
    assert result[1].user_id == '12b-12b-12b'


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


def test_validate_ticket_success():
    """Teste para validar um ticket com sucesso."""
    mock_db = MagicMock(spec=Session)

    mock_ticket = UserTicketModel(
        id='123456789012',
        user_id='12b-12b-12b',
        ticket_id=99,
        unit_amount=300.0,
        created_at="2023-10-01T12:00:00",
        is_active=True,
        deactivated_at=None,
    )

    mock_db.query().filter().first.return_value = mock_ticket

    result = validate_ticket(mock_db, ticket_id='1')

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_ticket)

    assert isinstance(result, UserTicketModel)
    assert result.is_active is False
    assert result.deactivated_at is not None


def test_validate_ticket_not_found():
    """Teste para tentar validar um ticket inexistente."""
    mock_db = MagicMock(spec=Session)

    mock_db.query().filter().first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        validate_ticket(mock_db, ticket_id='99')

    assert exc_info.value.status_code == 404
    assert "Ticket with id 99 not found." in exc_info.value.detail


def test_validate_ticket_already_deactivated():
    """Teste para tentar validar um ticket já desativado."""
    mock_db = MagicMock(spec=Session)

    mock_ticket = UserTicketModel(
        id='123456789012',
        user_id='12b-12b-12b',
        ticket_id=100,
        unit_amount=150.0,
        created_at="2023-10-02T12:00:00",
        is_active=False,
        deactivated_at="2023-10-05T12:00:00",
    )

    mock_db.query().filter().first.return_value = mock_ticket

    with pytest.raises(HTTPException) as exc_info:
        validate_ticket(mock_db, ticket_id='2')

    assert exc_info.value.status_code == 400
    assert "Ticket with id 2 is already deactivated." in exc_info.value.detail
