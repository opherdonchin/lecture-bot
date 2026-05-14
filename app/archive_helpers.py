import datetime
import hashlib
import json

import sqlalchemy.orm as sqlalchemy_orm

import app.models as models

CONTRACT_TYPES: frozenset[str] = models.CONTRACT_TYPES

TUTOR_PROMPT_REQUIRED_LINKS: frozenset[str] = frozenset({
    "tutor_spec",
    "tutor_artifact_schema",
    "tutor_generator_prompt",
    "tutor_spec_contract",
    "backend_contract",
})


def make_document_id(document_type: str, version_key: str) -> str:
    return f"doc_{document_type}_{version_key}"


def make_version_key(date: datetime.date, suffix: str | None = None) -> str:
    base = date.isoformat()
    if suffix:
        return f"{base}_{suffix}"
    return base


def sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_linked_documents(linked_documents_json: str | None) -> dict[str, str]:
    if not linked_documents_json:
        return {}
    return json.loads(linked_documents_json)


def get_active_document(
    db: sqlalchemy_orm.Session,
    document_type: str,
) -> models.ArchiveDocumentModel | None:
    return (
        db.query(models.ArchiveDocumentModel)
        .filter(
            models.ArchiveDocumentModel.document_type == document_type,
            models.ArchiveDocumentModel.active.is_(True),
        )
        .first()
    )


def get_active_document_id(db: sqlalchemy_orm.Session, document_type: str) -> str | None:
    doc = get_active_document(db, document_type)
    return doc.document_id if doc else None


def compatible_with_active_contracts(
    doc: models.ArchiveDocumentModel,
    db: sqlalchemy_orm.Session,
) -> bool:
    """
    True if every contract-type link in doc.linked_documents_json points to the
    currently active document of that type. Documents with no contract links are
    always compatible (including contracts themselves).
    """
    links = parse_linked_documents(doc.linked_documents_json)
    for contract_type in CONTRACT_TYPES:
        if contract_type not in links:
            continue
        active_id = get_active_document_id(db, contract_type)
        if active_id is None:
            return False
        if links[contract_type] != active_id:
            return False
    return True


def is_activatable(
    doc: models.ArchiveDocumentModel,
    db: sqlalchemy_orm.Session,
) -> tuple[bool, list[str]]:
    """
    Return (activatable, blocking_reasons) for a tutor_prompt document.
    Only tutor_prompt documents can be activatable; all others return False.
    """
    reasons: list[str] = []

    if doc.document_type != "tutor_prompt":
        reasons.append("document is not a tutor_prompt")
        return False, reasons

    links = parse_linked_documents(doc.linked_documents_json)

    for required_link in sorted(TUTOR_PROMPT_REQUIRED_LINKS):
        if required_link not in links:
            reasons.append(f"missing required link: {required_link}")

    if reasons:
        return False, reasons

    for contract_type in ("tutor_spec_contract", "backend_contract"):
        active_id = get_active_document_id(db, contract_type)
        if active_id is None:
            reasons.append(f"no active {contract_type} in archive")
        elif links[contract_type] != active_id:
            reasons.append(
                f"linked {contract_type} ({links[contract_type]!r}) "
                f"does not match active ({active_id!r})"
            )

    tutor_spec_id = links.get("tutor_spec")
    if tutor_spec_id:
        tutor_spec = db.get(models.ArchiveDocumentModel, tutor_spec_id)
        if tutor_spec is None:
            reasons.append(f"linked tutor_spec {tutor_spec_id!r} not found in archive")
        elif not compatible_with_active_contracts(tutor_spec, db):
            reasons.append("linked tutor_spec is not compatible with active contracts")

    gen_prompt_id = links.get("tutor_generator_prompt")
    if gen_prompt_id:
        gen_prompt = db.get(models.ArchiveDocumentModel, gen_prompt_id)
        if gen_prompt is None:
            reasons.append(f"linked tutor_generator_prompt {gen_prompt_id!r} not found in archive")
        elif not compatible_with_active_contracts(gen_prompt, db):
            reasons.append("linked tutor_generator_prompt is not compatible with active contracts")

    schema_id = links.get("tutor_artifact_schema")
    if schema_id:
        schema_doc = db.get(models.ArchiveDocumentModel, schema_id)
        if schema_doc is None:
            reasons.append(f"linked tutor_artifact_schema {schema_id!r} not found in archive")
        else:
            try:
                json.loads(schema_doc.content_text)
            except json.JSONDecodeError:
                reasons.append("linked tutor_artifact_schema does not parse as valid JSON")

    return len(reasons) == 0, reasons
