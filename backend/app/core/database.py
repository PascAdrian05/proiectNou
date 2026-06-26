from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


# Use stronger database settings for data persistence
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={"connect_timeout": 30}
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
