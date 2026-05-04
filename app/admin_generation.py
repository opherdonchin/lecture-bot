from __future__ import annotations

import datetime
import json
import uuid

import openai
import sqlalchemy.orm as sqlalchemy_orm

import app.archive_helpers as helpers
import app.config as config_module
import app.models as models


def _make_version_key() -> str:
    return f"{datetime.date.today().isoformat()}_{uuid.uuid4().hex[:6]}"


def _get_required_active_docs(
    db: sqlalchemy_orm.Session,
) -> tuple[dict | None, str | None]:
    docs: dict[str, models.ArchiveDocumentModel] = {}
    missing: list[str] = []
    for doc_type in ("tutor_spec_contract", "backend_contract", "tutor_generator_prompt"):
        doc = helpers.get_active_document(db, doc_type)
        if doc is None:
            missing.append(doc_type)
        else:
            docs[doc_type] = doc
    if missing:
        return None, f"No active document(s) in archive: {', '.join(missing)}"
    return docs, None


def get_generation_context(db: sqlalchemy_orm.Session) -> dict:
    """Return info about what docs will be used, for displaying on the generate form."""
    result = {}
    for doc_type in ("tutor_spec_contract", "backend_contract", "tutor_generator_prompt"):
        doc = helpers.get_active_document(db, doc_type)
        result[doc_type] = {
            "document_id": doc.document_id if doc else None,
            "title": doc.title if doc else None,
            "found": doc is not None,
        }
    return result


def _build_user_message(
    spec_contract_text: str,
    backend_contract_text: str,
    spec_text: str,
) -> str:
    return (
        "# 1. Tutor Specification Contract\n\n"
        f"{spec_contract_text}\n\n"
        "---\n\n"
        "# 2. Backend–Tutor Runtime Contract\n\n"
        f"{backend_contract_text}\n\n"
        "---\n\n"
        "# 3. Tutor Specification\n\n"
        f"{spec_text}\n"
    )


def _call_openai(system_prompt: str, user_message: str) -> str:
    settings = config_module.get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key, timeout=120.0, max_retries=0)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return response.choices[0].message.content


def _insert_doc(
    db: sqlalchemy_orm.Session,
    document_type: str,
    version_key: str,
    title: str,
    content_text: str,
    content_format: str,
    linked_documents_json: str | None,
    run_id: str,
) -> models.ArchiveDocumentModel:
    doc_id = helpers.make_document_id(document_type, version_key)
    doc = models.ArchiveDocumentModel(
        document_id=doc_id,
        document_type=document_type,
        version_key=version_key,
        title=title,
        content_text=content_text,
        content_format=content_format,
        linked_documents_json=linked_documents_json,
        content_sha256=helpers.sha256_of_text(content_text),
        active=False,
        provenance_json=json.dumps({"source": "generation", "run_id": run_id}),
    )
    db.add(doc)
    db.flush()
    return doc


def _save_run(
    db: sqlalchemy_orm.Session,
    run_id: str,
    status: str,
    spec_text: str,
    spec_title: str,
    generator_doc: models.ArchiveDocumentModel | None,
    spec_contract_doc: models.ArchiveDocumentModel | None,
    backend_contract_doc: models.ArchiveDocumentModel | None,
    output_document_ids: list[str] | None = None,
    raw_output_json: str | None = None,
    error_text: str | None = None,
) -> models.TutorGenerationRunModel:
    run = models.TutorGenerationRunModel(
        run_id=run_id,
        status=status,
        input_spec_text=spec_text,
        input_spec_title=spec_title,
        generator_document_id=generator_doc.document_id if generator_doc else None,
        spec_contract_document_id=spec_contract_doc.document_id if spec_contract_doc else None,
        backend_contract_document_id=backend_contract_doc.document_id if backend_contract_doc else None,
        output_document_ids_json=json.dumps(output_document_ids) if output_document_ids else None,
        raw_output_json=raw_output_json,
        error_text=error_text,
    )
    db.add(run)
    db.commit()
    return run


def run_generation(
    db: sqlalchemy_orm.Session,
    spec_text: str,
    spec_title: str,
) -> dict:
    """
    Run the full generation workflow. Returns a result dict with keys:
      ok, run_id, status, and type-specific fields.
    """
    run_id = str(uuid.uuid4())
    version_key = _make_version_key()

    active_docs, missing_error = _get_required_active_docs(db)
    if missing_error:
        _save_run(db, run_id, "error", spec_text, spec_title, None, None, None, error_text=missing_error)
        return {"ok": False, "run_id": run_id, "error": missing_error}

    generator_doc = active_docs["tutor_generator_prompt"]
    spec_contract_doc = active_docs["tutor_spec_contract"]
    backend_contract_doc = active_docs["backend_contract"]

    user_message = _build_user_message(
        spec_contract_doc.content_text,
        backend_contract_doc.content_text,
        spec_text,
    )

    try:
        raw_output = _call_openai(generator_doc.content_text, user_message)
        parsed = json.loads(raw_output)
    except openai.AuthenticationError as exc:
        error_text = f"OpenAI authentication error: {exc}"
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}
    except openai.APIError as exc:
        error_text = f"OpenAI API error: {exc}"
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}
    except json.JSONDecodeError as exc:
        error_text = f"Could not parse model output as JSON: {exc}"
        raw = locals().get("raw_output")
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, raw_output_json=raw, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}

    status = parsed.get("status", "failed")
    conformance_failures = parsed.get("conformance_failures") or []
    backend_incompatibilities = parsed.get("backend_incompatibilities") or []
    recommended_omissions = parsed.get("recommended_omissions") or []

    if status == "failed" or conformance_failures or backend_incompatibilities:
        _save_run(
            db, run_id, "failed", spec_text, spec_title,
            generator_doc, spec_contract_doc, backend_contract_doc,
            raw_output_json=json.dumps(parsed, ensure_ascii=False),
        )
        return {
            "ok": False,
            "run_id": run_id,
            "status": "failed",
            "conformance_failures": conformance_failures,
            "backend_incompatibilities": backend_incompatibilities,
            "recommended_omissions": recommended_omissions,
        }

    tutor_prompt_text = parsed.get("tutor_prompt") or ""
    schema_text = parsed.get("tutor_artifact_schema") or ""
    repaired_spec = parsed.get("tutor_spec")

    if not tutor_prompt_text or not schema_text:
        error_text = "Model returned ok/repaired status but tutor_prompt or tutor_artifact_schema is missing."
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc,
                  raw_output_json=json.dumps(parsed, ensure_ascii=False), error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}

    try:
        json.loads(schema_text)
    except json.JSONDecodeError:
        error_text = "Model returned an invalid JSON string for tutor_artifact_schema."
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc,
                  raw_output_json=json.dumps(parsed, ensure_ascii=False), error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}

    # Insert archive documents
    created_ids: list[str] = []
    today = datetime.date.today().isoformat()

    final_spec_text = repaired_spec if (status == "repaired" and repaired_spec) else spec_text
    spec_doc = _insert_doc(
        db, "tutor_spec", version_key,
        title=f"{spec_title}" if spec_title else f"Tutor Spec {version_key}",
        content_text=final_spec_text,
        content_format="markdown",
        linked_documents_json=json.dumps({"tutor_spec_contract": spec_contract_doc.document_id}),
        run_id=run_id,
    )
    created_ids.append(spec_doc.document_id)

    schema_doc = _insert_doc(
        db, "tutor_artifact_schema", version_key,
        title=f"Tutor Artifact Schema {version_key}",
        content_text=schema_text,
        content_format="json",
        linked_documents_json=json.dumps({"backend_contract": backend_contract_doc.document_id}),
        run_id=run_id,
    )
    created_ids.append(schema_doc.document_id)

    prompt_links = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": generator_doc.document_id,
        "tutor_spec_contract": spec_contract_doc.document_id,
        "backend_contract": backend_contract_doc.document_id,
    }
    prompt_doc = _insert_doc(
        db, "tutor_prompt", version_key,
        title=f"{spec_title} — Tutor Prompt" if spec_title else f"Tutor Prompt {version_key}",
        content_text=tutor_prompt_text,
        content_format="markdown",
        linked_documents_json=json.dumps(prompt_links),
        run_id=run_id,
    )
    created_ids.append(prompt_doc.document_id)

    _save_run(
        db, run_id, status, spec_text, spec_title,
        generator_doc, spec_contract_doc, backend_contract_doc,
        output_document_ids=created_ids,
        raw_output_json=json.dumps(parsed, ensure_ascii=False),
    )

    return {
        "ok": True,
        "run_id": run_id,
        "status": status,
        "recommended_omissions": recommended_omissions,
        "created_document_ids": created_ids,
        "tutor_prompt_document_id": prompt_doc.document_id,
    }
