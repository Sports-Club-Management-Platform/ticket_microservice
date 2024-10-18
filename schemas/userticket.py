from pydantic import BaseModel
from typing import Optional

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
