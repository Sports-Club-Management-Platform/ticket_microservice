from typing import List, Optional

from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Float, Integer,
                        String, Text)

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
    stripe_price_id = Column(String(32), nullable=False)
    stripe_image_url = Column(String(512), nullable=False)
    