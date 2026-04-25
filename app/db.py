import pathlib

import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.config as config_module


class Base(sqlalchemy_orm.DeclarativeBase):
    pass


settings = config_module.get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}


def _sqlite_file_path(database_url: str) -> pathlib.Path | None:
    if not database_url.startswith("sqlite:"):
        return None

    database_path = sa.engine.make_url(database_url).database
    if not database_path or database_path == ":memory:":
        return None
    return pathlib.Path(database_path)


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    database_path = _sqlite_file_path(database_url)
    if database_path is None:
        return
    database_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)

engine = sa.create_engine(
    settings.database_url,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sqlalchemy_orm.sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
