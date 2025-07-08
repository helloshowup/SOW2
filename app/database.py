from sqlmodel import SQLModel, Session, create_engine

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=True)


def get_session():
    """Yield a SQLModel session."""
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Create database tables."""
    SQLModel.metadata.create_all(engine)
