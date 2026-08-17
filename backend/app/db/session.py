from collections.abc import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_database_exists() -> None:
    admin_password = quote_plus(settings.db_password)
    admin_url = (
        f"postgresql+psycopg://{settings.db_user}:{admin_password}"
        f"@{settings.db_host}:{settings.db_port}/postgres"
    )
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": settings.db_name},
        ).scalar_one_or_none()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{settings.db_name}"'))

    admin_engine.dispose()


def init_db() -> None:
    import app.models.document  # noqa: F401
    from app.db.base import Base

    if not settings.database_url:
        ensure_database_exists()

    with engine.begin() as connection:
        try:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "pgvector is not enabled on this database. "
                "If you're using Supabase, enable the 'vector' extension in "
                "Dashboard > Database > Extensions, then restart the app."
            ) from exc
        Base.metadata.create_all(bind=connection)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
