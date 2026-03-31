import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.config as config_module


class Base(sqlalchemy_orm.DeclarativeBase):
    pass


settings = config_module.get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

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