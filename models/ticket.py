from typing import Optional
from typing import List
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import String, Integer, Boolean, Float, ARRAY, Text

from db.database import Base


class Ticket(Base):
    __tablename__ = 'tickets' 

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer) 
    name = Column(String)
    description = Column(Text)
    status = Column(Boolean)
    type = Column(String)
    assigned_to = Column(String)
    price = Column(Float)