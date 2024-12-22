from typing import Optional
from typing import List
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import String, Integer, Boolean, Float, ARRAY, Text

from db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, nullable=False)
    name = Column(String(200), index=True, nullable=False)
    description = Column(String(500), nullable=True)
    active = Column(Boolean, nullable=False)
    price = Column(Float, nullable=False)
    stripe_prod_id = Column(String(32), nullable=False)
    