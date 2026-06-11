import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session
from api.config import settings

if not settings.POSTGRES_URI:
    raise ValueError("POSTGRES_URI not found in environment variables")

# The engine handles the connection logic for SQLModel
# pool_pre_ping=True is useful for serverless DBs like Neon to handle cold starts/timeouts
engine = create_engine(settings.POSTGRES_URI, echo=False, pool_pre_ping=True)

def get_session():
    """
    Provides a database session for querying.
    """
    with Session(engine) as session:
        yield session