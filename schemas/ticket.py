from dataclasses import dataclass
from typing import Optional

from fastapi import Form, UploadFile
from pydantic import BaseModel


class Ticket(BaseModel):
    game_id: int
    name: str
    description: str
    active: bool # Available to buy
    price: float # In euros

class TicketCreate(Ticket):
    # image: UploadFile
    stock: int # Number of tickets available


class TicketUpdate(BaseModel):
    # For now ticket update doesn't include price
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    stock: Optional[int] = None

class TicketInDB(Ticket):
    id: int
    stripe_price_id: str
    stripe_image_url: str

