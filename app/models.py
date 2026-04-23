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
    private_artifact_schema_json: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.Text, nullable=True)


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


class DialogueTurnAuditModel(db_module.Base):
    __tablename__ = "dialogue_turn_audits"

    id: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.ForeignKey("sessions.session_id"), index=True)
    turn_index: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, index=True)
    effective_policy: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(64))
    prompt_template_name: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(128))
    dialogue_model: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.String(128))
    state_before_json: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    recent_messages_json: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    user_message: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    rendered_system_prompt: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.Text)
    timestamp: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow)
    tutor_mode: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.String(64), default="content_answer")
    action_hint_json: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.Text, default="{}")
    challenge_level: sqlalchemy_orm.Mapped[int | None] = sqlalchemy_orm.mapped_column(sa.Integer, default=1)
    current_topic_id: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.String(64), nullable=True)
    target_topic_id: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.String(64), nullable=True)
    ended_with_content_question: sqlalchemy_orm.Mapped[bool | None] = sqlalchemy_orm.mapped_column(sa.Boolean, default=False)
    repetition_complaint: sqlalchemy_orm.Mapped[bool | None] = sqlalchemy_orm.mapped_column(sa.Boolean, default=False)
    switched_topics: sqlalchemy_orm.Mapped[bool | None] = sqlalchemy_orm.mapped_column(sa.Boolean, default=False)


class PrivateArtifactLogModel(db_module.Base):
    __tablename__ = "private_artifact_logs"

    id: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    session_id: sqlalchemy_orm.Mapped[str] = sqlalchemy_orm.mapped_column(sa.ForeignKey("sessions.session_id"), index=True)
    turn_index: sqlalchemy_orm.Mapped[int] = sqlalchemy_orm.mapped_column(sa.Integer, index=True)
    artifact_json: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.Text, nullable=True)
    validation_error: sqlalchemy_orm.Mapped[str | None] = sqlalchemy_orm.mapped_column(sa.Text, nullable=True)
    created_at: sqlalchemy_orm.Mapped[dt_module.datetime] = sqlalchemy_orm.mapped_column(sa.DateTime(timezone=True), default=utcnow)
