from __future__ import annotations

import json
import pathlib

import sqlalchemy.orm as sqlalchemy_orm

import app.archive_helpers as helpers
import app.models as models


REPO_ROOT = pathlib.Path(__file__).parent.parent

CANONICAL_DOCUMENT_PATHS = {
    "tutor_prompt": REPO_ROOT / "prompts" / "tutor_prompt.md",
    "tutor_artifact_schema": REPO_ROOT / "prompts" / "tutor_prompt_private_artifact_schema.json",
    "tutor_spec": REPO_ROOT / "docs" / "tutor_specification.md",
}


def activate_tutor_prompt(
    db: sqlalchemy_orm.Session,
    document_id: str,
) -> tuple[bool, str]:
    doc = db.get(models.ArchiveDocumentModel, document_id)
    if doc is None:
        return False, "Document not found."

    activatable, blocking = helpers.is_activatable(doc, db)
    if not activatable:
        return False, "Not activatable: " + "; ".join(blocking)

    links = helpers.parse_linked_documents(doc.linked_documents_json)
    schema_doc = db.get(models.ArchiveDocumentModel, links["tutor_artifact_schema"])
    spec_doc = db.get(models.ArchiveDocumentModel, links["tutor_spec"])
    if schema_doc is None or spec_doc is None:
        return False, "Linked generated spec or schema document is missing."

    CANONICAL_DOCUMENT_PATHS["tutor_prompt"].write_text(doc.content_text, encoding="utf-8")
    CANONICAL_DOCUMENT_PATHS["tutor_artifact_schema"].write_text(schema_doc.content_text, encoding="utf-8")
    CANONICAL_DOCUMENT_PATHS["tutor_spec"].write_text(spec_doc.content_text, encoding="utf-8")

    db.query(models.ArchiveDocumentModel).filter(
        models.ArchiveDocumentModel.document_type == "tutor_prompt",
        models.ArchiveDocumentModel.active.is_(True),
    ).update({"active": False})
    doc.active = True
    db.commit()

    return True, "Tutor prompt activated. Restart the student app to apply."


def document_summary(doc: models.ArchiveDocumentModel, db: sqlalchemy_orm.Session) -> dict:
    activatable, blocking = helpers.is_activatable(doc, db) if doc.document_type == "tutor_prompt" else (False, [])
    return {
        "document_id": doc.document_id,
        "document_type": doc.document_type,
        "version_key": doc.version_key,
        "title": doc.title,
        "active": doc.active,
        "compatible": helpers.compatible_with_active_contracts(doc, db),
        "activatable": activatable,
        "blocking_reasons": blocking,
        "links": helpers.parse_linked_documents(doc.linked_documents_json),
        "provenance": json.loads(doc.provenance_json) if doc.provenance_json else None,
    }
