from typing import Optional

from pydantic import BaseModel


class UserTicket(BaseModel):
    user_id: str
    ticket_id: int
    quantity: int
    total_price: float
    created_at: float
    updated_at: Optional[str] = None

class UserTicketCreate(UserTicket):
    pass

class UserTicketUpdate(UserTicket):
    ticket_id: Optional[int] = None
    quantity: Optional[int] = None
    total_price: Optional[float] = None
    created_at: Optional[float] = None
    updated_at: Optional[str] = None

class UserTicketInDB(UserTicket):
    id: int
