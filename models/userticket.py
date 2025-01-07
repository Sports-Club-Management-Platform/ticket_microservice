from datetime import datetime
from typing import List, Optional

from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text)

from db.database import Base


class UserTicket(Base):
    __tablename__ = "user_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False)
    ticket_id = Column(String(32), ForeignKey('tickets.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(Float, nullable=False)
    updated_at = Column(String(500), nullable=True, onupdate=datetime.now)