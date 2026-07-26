from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.database.base import Base

settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")
connect_args = (
    {"check_same_thread": False}
    if is_sqlite
    else {"connect_timeout": settings.database_connect_timeout_seconds}
)
pool_options = (
    {}
    if is_sqlite
    else {
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout_seconds,
        "pool_recycle": settings.database_pool_recycle_seconds,
    }
)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
    **pool_options,
)
SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session]:
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def dispose_engine() -> None:
    engine.dispose()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
