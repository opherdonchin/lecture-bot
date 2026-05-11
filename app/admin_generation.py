from __future__ import annotations

import datetime
import json
import pathlib
import re
import uuid

import jsonschema
import openai
import sqlalchemy.orm as sqlalchemy_orm

import app.admin_documents as admin_documents
import app.archive_helpers as helpers
import app.config as config_module
import app.models as models


REPO_ROOT = pathlib.Path(__file__).parent.parent
CURRENT_SPEC_PATH = REPO_ROOT / "docs" / "tutor_specification.md"


class GenerationOutputError(ValueError):
    pass


def _make_version_key() -> str:
    return f"{datetime.date.today().isoformat()}_{uuid.uuid4().hex[:6]}"


def _get_required_active_docs(
    db: sqlalchemy_orm.Session,
) -> tuple[dict[str, models.ArchiveDocumentModel] | None, str | None]:
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
        "# 2. Backend-Tutor Runtime Contract\n\n"
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
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def _section_text(raw_output: str, heading: str) -> str:
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*$"
        r"(?P<body>.*?)"
        r"(?=^###\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(raw_output)
    if not match:
        return ""
    return match.group("body").strip()


def _is_none_section(section: str) -> bool:
    cleaned = section.strip()
    return cleaned in {"", "None", "None."}


def _bullet_items(section: str) -> list[str]:
    if _is_none_section(section):
        return []
    items = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            items.append(stripped[2:].strip())
        elif stripped:
            items.append(stripped)
    return items


def _first_fenced_block(section: str, language: str | None = None) -> str:
    lang_pattern = re.escape(language) if language else r"[A-Za-z0-9_-]*"
    pattern = re.compile(
        rf"```{lang_pattern}\s*\n(?P<body>.*?)\n```",
        re.DOTALL,
    )
    match = pattern.search(section)
    if not match:
        raise GenerationOutputError("Expected a fenced code block in generator output.")
    return match.group("body").strip()


def parse_generator_output(raw_output: str) -> dict:
    conformance_failures = _bullet_items(_section_text(raw_output, "Conformance failures"))
    backend_incompatibilities = _bullet_items(_section_text(raw_output, "Backend incompatibilities"))
    recommended_omissions = _bullet_items(_section_text(raw_output, "Recommended omissions"))

    if conformance_failures or backend_incompatibilities:
        return {
            "status": "failed",
            "conformance_failures": conformance_failures,
            "backend_incompatibilities": backend_incompatibilities,
            "recommended_omissions": recommended_omissions,
            "tutor_artifact_schema": None,
            "tutor_prompt": None,
        }

    schema_section = _section_text(raw_output, "Private artifact schema")
    prompt_section = _section_text(raw_output, "Runtime tutor prompt")
    if not schema_section or not prompt_section:
        raise GenerationOutputError("Generator output is missing the schema or runtime prompt section.")

    schema_text = _first_fenced_block(schema_section, "json")
    tutor_prompt = _first_fenced_block(prompt_section)
    return {
        "status": "success",
        "conformance_failures": [],
        "backend_incompatibilities": [],
        "recommended_omissions": recommended_omissions,
        "tutor_artifact_schema": schema_text,
        "tutor_prompt": tutor_prompt,
    }


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

    assert active_docs is not None
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
        parsed = parse_generator_output(raw_output)
    except openai.AuthenticationError as exc:
        error_text = f"OpenAI authentication error: {exc}"
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}
    except openai.APIError as exc:
        error_text = f"OpenAI API error: {exc}"
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}
    except (GenerationOutputError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        error_text = f"Could not validate generator output: {exc}"
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, raw_output_json=locals().get("raw_output"), error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}

    if parsed["status"] == "failed":
        _save_run(
            db, run_id, "failed", spec_text, spec_title,
            generator_doc, spec_contract_doc, backend_contract_doc,
            raw_output_json=raw_output,
        )
        return {
            "ok": False,
            "run_id": run_id,
            "status": "failed",
            "conformance_failures": parsed["conformance_failures"],
            "backend_incompatibilities": parsed["backend_incompatibilities"],
            "recommended_omissions": parsed["recommended_omissions"],
        }

    tutor_prompt_text = parsed["tutor_prompt"] or ""
    schema_text = parsed["tutor_artifact_schema"] or ""
    if not tutor_prompt_text or not schema_text:
        error_text = "Generator succeeded but returned an empty tutor prompt or private artifact schema."
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, raw_output_json=raw_output, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}

    try:
        schema_obj = json.loads(schema_text)
        jsonschema.Draft202012Validator.check_schema(schema_obj)
    except (json.JSONDecodeError, jsonschema.SchemaError) as exc:
        error_text = f"Generated private artifact schema is invalid: {exc}"
        _save_run(db, run_id, "error", spec_text, spec_title, generator_doc, spec_contract_doc, backend_contract_doc, raw_output_json=raw_output, error_text=error_text)
        return {"ok": False, "run_id": run_id, "error": error_text}

    created_ids: list[str] = []
    spec_doc = _insert_doc(
        db, "tutor_spec", version_key,
        title=spec_title or f"Tutor Spec {version_key}",
        content_text=spec_text,
        content_format="markdown",
        linked_documents_json=json.dumps({"tutor_spec_contract": spec_contract_doc.document_id}),
        run_id=run_id,
    )
    created_ids.append(spec_doc.document_id)

    schema_doc = _insert_doc(
        db, "tutor_artifact_schema", version_key,
        title=f"Tutor Artifact Schema {version_key}",
        content_text=json.dumps(schema_obj, ensure_ascii=False, indent=2),
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
        title=f"{spec_title} - Tutor Prompt" if spec_title else f"Tutor Prompt {version_key}",
        content_text=tutor_prompt_text,
        content_format="markdown",
        linked_documents_json=json.dumps(prompt_links),
        run_id=run_id,
    )
    created_ids.append(prompt_doc.document_id)

    _save_run(
        db, run_id, "success", spec_text, spec_title,
        generator_doc, spec_contract_doc, backend_contract_doc,
        output_document_ids=created_ids,
        raw_output_json=raw_output,
    )

    return {
        "ok": True,
        "run_id": run_id,
        "status": "success",
        "recommended_omissions": parsed["recommended_omissions"],
        "created_document_ids": created_ids,
        "tutor_prompt_document_id": prompt_doc.document_id,
    }


def run_generation_from_current_spec(
    db: sqlalchemy_orm.Session,
    *,
    repo_root: pathlib.Path = REPO_ROOT,
    spec_title: str = "Current Tutor Specification",
    activate: bool = False,
) -> dict:
    spec_path = repo_root / "docs" / "tutor_specification.md"
    spec_text = spec_path.read_text(encoding="utf-8")
    result = run_generation(db, spec_text=spec_text, spec_title=spec_title)
    if not result.get("ok") or not activate:
        return result

    ok, message = admin_documents.activate_tutor_prompt(db, result["tutor_prompt_document_id"])
    result["activation"] = {"ok": ok, "message": message}
    if not ok:
        result["ok"] = False
        result["error"] = message
    return result
