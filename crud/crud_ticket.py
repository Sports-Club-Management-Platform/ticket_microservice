import json

import pika
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from typing import Dict, List
from datetime import datetime
import requests
import json
from crud.base import CRUDBase
from models.ticket import Ticket
from schemas.ticket import TicketCreate, TicketUpdate, TicketInDB

class CRUDTicket(CRUDBase[TicketInDB, TicketCreate, TicketUpdate]):
    ...

ticket = CRUDTicket(Ticket)