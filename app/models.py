import datetime as dt_module

import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.db as db_module


def utcnow() -> dt_module.datetime:
    return dt_module.datetime.now(dt_module.timezone.utc)


class SessionModel(db_module.Base):
    __tablename__ = "sessions"

    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(36), primary_key=True)
    student_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(64), index=True)
    lecture_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(128), index=True)
    started_at: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow)
    ended_at: sqlalchemy_orm.Mapped[dt_module.datetime | None] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), nullable=True)
    current_grade: sqlalchemy_orm.Mapped[float | None] = sqlalchemy_orm.mapped_column(sa.Float, nullable=True)


class MessageModel(db_module.Base):
    __tablename__ = "messages"

    id: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.ForeignKey("sessions.session_id"), index=True)
    role: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(32))
    content: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    timestamp: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow)


class SessionStateModel(db_module.Base):
    __tablename__ = "session_state"

    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.ForeignKey("sessions.session_id"), primary_key=True)
    state_json: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    updated_at: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GradeEventModel(db_module.Base):
    __tablename__ = "grade_events"

    id: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.ForeignKey("sessions.session_id"), index=True)
    event_type: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(32))
    grade: sqlalchemy_orm.Mapped[float] = sqlalchemy_orm.mapped_column(sa.Float)
    timestamp: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow)
    payload_json: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.Text, nullable=True)


class ClassificationLogModel(db_module.Base):
    __tablename__ = "classification_logs"

    id: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.ForeignKey("sessions.session_id"), index=True)
    message_id: sqlalchemy_orm.Mapped[int | None] = sqlalchemy_orm.mapped_column(sa.Integer, nullable=True)
    turn_index: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer)
    classifier_json: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    policy_decision_json: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    timestamp: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow)