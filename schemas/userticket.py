from typing import Optional

from pydantic import BaseModel


class UserTicket(BaseModel):
    user_id: str
    ticket_id: int
    unit_amount: float
    created_at: str
    is_active: bool = True
    deactivated_at: Optional[str] = None


class UserTicketCreate(UserTicket):
    quantity: int
    pass

class UserTicketInDB(UserTicket):
    id: str
