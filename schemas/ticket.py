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
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    price: Optional[float] = None

class TicketInDB(Ticket):
    id: int
    stripe_prod_id: str

