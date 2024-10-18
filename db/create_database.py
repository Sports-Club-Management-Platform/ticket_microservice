from models.ticket import Ticket
from models.userticket import UserTicket

from db.database import engine


def create_tables():
    Ticket.metadata.create_all(bind=engine)
    UserTicket.metadata.create_all(bind=engine)

