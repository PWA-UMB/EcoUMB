from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_db_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        options: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            options["poolclass"] = StaticPool  # una sola conexión: la BD en memoria se comparte
        return create_engine(url, **options)
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
