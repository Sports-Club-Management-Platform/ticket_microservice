from models.ticket import Ticket

from db.database import engine


def create_tables():
    Ticket.metadata.create_all(bind=engine)
