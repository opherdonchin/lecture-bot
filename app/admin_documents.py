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


def doc_row(doc: models.ArchiveDocumentModel, db: sqlalchemy_orm.Session) -> dict:
    compatible = helpers.compatible_with_active_contracts(doc, db)
    if doc.document_type == "tutor_prompt":
        activatable, blocking = helpers.is_activatable(doc, db)
    else:
        activatable, blocking = False, []
    return {
        "document_id": doc.document_id,
        "document_type": doc.document_type,
        "version_key": doc.version_key,
        "title": doc.title,
        "active": doc.active,
        "compatible": compatible,
        "activatable": activatable,
        "blocking_reasons": blocking,
        "links": helpers.parse_linked_documents(doc.linked_documents_json),
        "created_at": doc.created_at,
    }


def document_summary(doc: models.ArchiveDocumentModel, db: sqlalchemy_orm.Session) -> dict:
    row = doc_row(doc, db)
    row["provenance"] = json.loads(doc.provenance_json) if doc.provenance_json else None
    return row


def list_all_documents(db: sqlalchemy_orm.Session) -> dict[str, list[dict]]:
    docs = (
        db.query(models.ArchiveDocumentModel)
        .order_by(
            models.ArchiveDocumentModel.document_type,
            models.ArchiveDocumentModel.created_at.desc(),
        )
        .all()
    )
    grouped: dict[str, list[dict]] = {}
    for doc in docs:
        grouped.setdefault(doc.document_type, []).append(doc_row(doc, db))
    return grouped


def list_tutor_prompts(db: sqlalchemy_orm.Session) -> list[dict]:
    docs = (
        db.query(models.ArchiveDocumentModel)
        .filter(models.ArchiveDocumentModel.document_type == "tutor_prompt")
        .order_by(models.ArchiveDocumentModel.created_at.desc())
        .all()
    )
    return [doc_row(doc, db) for doc in docs]


def get_document_detail(db: sqlalchemy_orm.Session, document_id: str) -> dict | None:
    doc = db.get(models.ArchiveDocumentModel, document_id)
    if doc is None:
        return None
    row = document_summary(doc, db)
    row["description"] = doc.description
    row["content_text"] = doc.content_text
    row["content_format"] = doc.content_format
    row["content_sha256"] = doc.content_sha256
    row["updated_at"] = doc.updated_at

    linked_docs = {}
    for link_type, link_id in row["links"].items():
        linked_doc = db.get(models.ArchiveDocumentModel, link_id)
        linked_docs[link_type] = {
            "document_id": link_id,
            "found": linked_doc is not None,
            "title": linked_doc.title if linked_doc else None,
        }
    row["linked_docs"] = linked_docs
    return row


def _doc_to_export_dict(doc: models.ArchiveDocumentModel, file_path: str) -> dict:
    return {
        "document_id": doc.document_id,
        "document_type": doc.document_type,
        "version_key": doc.version_key,
        "title": doc.title,
        "content_sha256": doc.content_sha256,
        "content_format": doc.content_format,
        "active": doc.active,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "linked_documents_json": doc.linked_documents_json,
        "provenance_json": doc.provenance_json,
        "file": file_path,
    }


def build_assembled_tutor(
    db: sqlalchemy_orm.Session,
    prompt_document_id: str,
) -> dict | None:
    """
    Build the full document graph for a tutor_prompt, suitable for export.

    Returns a dict with 'tutor_prompt_document_id' and 'documents' (keyed by
    document_type). Each document entry points to its file path in the export
    zip's documents/ folder. Content is not embedded here; it lives in that file.
    Returns None if the prompt document is not found.
    """
    prompt_doc = db.get(models.ArchiveDocumentModel, prompt_document_id)
    if prompt_doc is None:
        return None

    ext = "json" if prompt_doc.content_format == "json" else "md"
    documents: dict[str, dict] = {
        "tutor_prompt": _doc_to_export_dict(
            prompt_doc, f"documents/{prompt_doc.document_id}.{ext}"
        )
    }

    for link_type, link_id in helpers.parse_linked_documents(prompt_doc.linked_documents_json).items():
        linked_doc = db.get(models.ArchiveDocumentModel, link_id)
        if linked_doc is None:
            documents[link_type] = {"document_id": link_id, "not_found": True}
        else:
            link_ext = "json" if linked_doc.content_format == "json" else "md"
            documents[link_type] = _doc_to_export_dict(
                linked_doc, f"documents/{linked_doc.document_id}.{link_ext}"
            )

    return {"tutor_prompt_document_id": prompt_document_id, "documents": documents}


def collect_export_documents(
    db: sqlalchemy_orm.Session,
    prompt_document_ids: list[str],
) -> tuple[dict[str, dict], dict[str, dict]]:
    """
    Given a list of prompt document IDs, return:
      - assembled: {prompt_doc_id: assembled_tutor_dict}
      - docs: {document_id: (ArchiveDocumentModel, file_path_in_zip)}

    Documents are deduplicated across all prompts.
    """
    assembled: dict[str, dict] = {}
    docs: dict[str, tuple[models.ArchiveDocumentModel, str]] = {}

    for prompt_doc_id in prompt_document_ids:
        graph = build_assembled_tutor(db, prompt_doc_id)
        if graph is None:
            continue
        assembled[prompt_doc_id] = graph

        # Collect all referenced documents (including the prompt itself)
        for _link_type, entry in graph["documents"].items():
            if entry.get("not_found"):
                continue
            doc_id = entry["document_id"]
            if doc_id in docs:
                continue
            doc = db.get(models.ArchiveDocumentModel, doc_id)
            if doc is not None:
                docs[doc_id] = (doc, entry["file"])

    return assembled, docs


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

    # Write canonical runtime files
    CANONICAL_DOCUMENT_PATHS["tutor_prompt"].write_text(doc.content_text, encoding="utf-8")
    CANONICAL_DOCUMENT_PATHS["tutor_artifact_schema"].write_text(schema_doc.content_text, encoding="utf-8")
    CANONICAL_DOCUMENT_PATHS["tutor_spec"].write_text(spec_doc.content_text, encoding="utf-8")

    # Update active flag: deactivate others, activate this one
    db.query(models.ArchiveDocumentModel).filter(
        models.ArchiveDocumentModel.document_type == "tutor_prompt",
        models.ArchiveDocumentModel.active.is_(True),
    ).update({"active": False})
    doc.active = True
    db.commit()

    return True, "Tutor prompt activated. Restart the student app to apply."
