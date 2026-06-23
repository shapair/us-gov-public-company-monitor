"""Database engine and session management."""
from sqlmodel import SQLModel, Session, create_engine

from app.config import settings

# Use SQLite fallback if the configured URL explicitly mentions sqlite
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
