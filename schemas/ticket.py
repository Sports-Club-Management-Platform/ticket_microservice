from pydantic import BaseModel
from typing import Optional

class Ticket(BaseModel):
    game_id: int
    name: str
    description: str
    status: bool # Available to buy
    type: str
    assigned_to: str
    price: float

class TicketCreate(Ticket):
    pass

class TicketUpdate(Ticket):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    type: Optional[str] = None
    assigned_to: Optional[str] = None
    price: Optional[float] = None

class TicketInDB(Ticket):
    id: int

