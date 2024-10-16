from pydantic import BaseModel
from typing import Optional

class Ticket(BaseModel):
    game_id: int
    name: str
    description: str
    status: bool # Available to buy
    type: str
    price: float

class TicketCreate(Ticket):
    pass

class TicketUpdate(Ticket):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    type: Optional[str] = None
    price: Optional[float] = None

class TicketInDB(Ticket):
    id: int



class UserTicket(BaseModel):
    user_id: int
    ticket_id: int
    quantity: int
    total_price: float
    created_at: str
    updated_at: str

class UserTicketCreate(UserTicket):
    pass

class UserTicketUpdate(UserTicket):
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    quantity: Optional[int] = None
    total_price: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UserTicketInDB(UserTicket):
    id: int
