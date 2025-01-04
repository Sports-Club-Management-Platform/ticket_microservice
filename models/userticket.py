from typing import Optional
from typing import List
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import String, Integer, Boolean, Float, ARRAY, Text

from db.database import Base


class UserTicket(Base):
    __tablename__ = "user_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    ticket_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(String(500), nullable=False)
    updated_at = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(String(500), nullable=True)
