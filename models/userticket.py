from datetime import datetime
from typing import List, Optional

from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text)

from db.database import Base
import secrets
import string



class UserTicket(Base):
    __tablename__ = "user_tickets"

    id = Column(String(12), primary_key=True, index=True, default=lambda : generate_random_user_ticket_id(12))
    user_id = Column(String(50), nullable=False)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    amount_subtotal = Column(Float, nullable=False)
    created_at = Column(Float, nullable=False)
    updated_at = Column(String(500), nullable=True, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(String(500), nullable=True)

def generate_random_user_ticket_id(id_length: int) -> str:
    secure_chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(secure_chars) for _ in range(id_length))
