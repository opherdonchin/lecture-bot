import json as j
import logging
import pathlib
import uuid as uuid_module

import sqlalchemy.orm as sqlalchemy_orm

import app.archive_helpers as archive_helpers
import app.bot_engine as bot_engine
import app.config as config_module
import app.models as models
import app.prompt_loader as prompt_loader

_log = logging.getLogger(__name__)
_TUTOR_PROMPT_FILE = pathlib.Path(__file__).parent.parent / "prompts" / "tutor_prompt.md"


def _resolve_prompt_document_id(db: sqlalchemy_orm.Session) -> str | None:
    """
    Identify which archive document the live prompt file corresponds to.

    SHA-256 of the file content is the primary lookup (it reflects what the
    model will actually see). The active flag is checked as a consistency
    guard. A warning is logged whenever they disagree.
    """
    try:
        content = _TUTOR_PROMPT_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    sha = archive_helpers.sha256_of_text(content)

    sha_doc = (
        db.query(models.ArchiveDocumentModel)
        .filter(
            models.ArchiveDocumentModel.document_type == "tutor_prompt",
            models.ArchiveDocumentModel.content_sha256 == sha,
        )
        .first()
    )
    active_doc = (
        db.query(models.ArchiveDocumentModel)
        .filter(
            models.ArchiveDocumentModel.document_type == "tutor_prompt",
            models.ArchiveDocumentModel.active.is_(True),
        )
        .first()
    )

    sha_id = sha_doc.document_id if sha_doc else None
    active_id = active_doc.document_id if active_doc else None

    if sha_id != active_id:
        _log.warning(
            "tutor_prompt identity mismatch: sha256 match=%r active=%r",
            sha_id,
            active_id,
        )

    return sha_id


def build_initial_state(lecture_package: dict, topics_sampled: list) -> dict:
    return {
        "topics_sampled": bot_engine._unique_topic_ids(topics_sampled),
        "topics_covered": [],
        "mastery": {},
        "best_mastery": {},
        "evidence_notes": {},
        "current_topic_id": None,
        "tutor_comment": "",
        "current_grade": 0.0,
        "timeout_warning_sent": False,
        "turn_count": 0,
    }


def create_session(db: sqlalchemy_orm.Session, student_id: str, lecture_id: str, lecture_package: dict) -> models.SessionModel:
    tutor_prompt_template = bot_engine.get_tutor_prompt_template(lecture_package)
    session = models.SessionModel(
        session_id=str(uuid_module.uuid4()),
        student_id=student_id,
        lecture_id=lecture_id,
        current_grade=0.0,
        private_artifact_schema_json=prompt_loader.load_private_artifact_schema_json(tutor_prompt_template),
        prompt_document_id=_resolve_prompt_document_id(db),
    )
    db.add(session)
    db.flush()

    # Prefer lecture_config topics when present; fall back to rubric parsing.
    topic_defs = bot_engine.resolve_topic_defs(lecture_package)
    count = config_module.get_settings().sampled_topic_count
    topics_sampled = bot_engine.sample_session_topics(topic_defs, session.session_id, count=count)

    state = models.SessionStateModel(
        session_id=session.session_id,
        state_json=j.dumps(build_initial_state(lecture_package, topics_sampled), ensure_ascii=False),
    )
    db.add(state)
    db.flush()
    return session


def append_message(db: sqlalchemy_orm.Session, session_id: str, role: str, content: str) -> None:
    db.add(models.MessageModel(session_id=session_id, role=role, content=content))


def load_state(db: sqlalchemy_orm.Session, session_id: str) -> dict:
    row = db.query(models.SessionStateModel).filter(models.SessionStateModel.session_id == session_id).first()
    if not row:
        raise ValueError(f"No state found for session {session_id}")
    return j.loads(row.state_json)


def save_state(db: sqlalchemy_orm.Session, session_id: str, state: dict) -> None:
    row = db.query(models.SessionStateModel).filter(models.SessionStateModel.session_id == session_id).first()
    if not row:
        raise ValueError(f"No state found for session {session_id}")
    row.state_json = j.dumps(state, ensure_ascii=False)
