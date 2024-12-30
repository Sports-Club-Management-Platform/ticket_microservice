from dataclasses import dataclass

from fastapi import Form, UploadFile
from pydantic import BaseModel
from typing import Optional

class Ticket(BaseModel):
    game_id: int
    name: str
    description: str
    active: bool # Available to buy
    price: float # In euros

class TicketCreate(Ticket):
    image: UploadFile

class TicketUpdate(BaseModel):
    # For now ticket update doesn't include price
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class TicketInDB(Ticket):
    id: int
    stripe_price_id: str
    stripe_image_url: str

