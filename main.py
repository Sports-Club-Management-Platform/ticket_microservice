from contextlib import asynccontextmanager

from db.create_database import create_tables
from db.database import SessionLocal
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import ticket
from routers.ticket import lifespan
from starlette import status

app = FastAPI(
    lifespan=lifespan,
    title="ClubSync Ticket_Microservice API",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "ClubSync",
    },
    root_path="/tickets/v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
)
def get_health():
    return {"status": "ok"}


app.include_router(ticket.router)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    response = await call_next(request)
    request.state.db.close()
    return response
