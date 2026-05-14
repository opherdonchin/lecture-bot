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


def _spec_validation_system_prompt(generator_prompt_text: str) -> str:
    return (
        "You validate tutor specifications before they are saved into the document archive.\n\n"
        "Use the authoritative contract rules from the generator instructions below, but perform validation only.\n"
        "Do not generate a private artifact schema. Do not generate a runtime tutor prompt. Do not rewrite the spec.\n\n"
        "Return exactly these Markdown sections, in this order:\n\n"
        "### Conformance failures\n"
        "Use bullet points for required tutor-spec contract failures. Use None. if there are no failures.\n\n"
        "### Backend incompatibilities\n"
        "Use bullet points for conflicts with the backend runtime contract. Use None. if there are no incompatibilities.\n\n"
        "### Recommended omissions\n"
        "Use bullet points for recommended-but-absent spec material only. Use None. if there are no recommended omissions.\n\n"
        "Generator instructions to apply as validation criteria:\n\n"
        f"{generator_prompt_text}"
    )


def _prompt_generation_system_prompt(generator_prompt_text: str) -> str:
    return (
        "You generate a runtime tutor prompt and private artifact JSON Schema from an already validated tutor specification.\n\n"
        "The specification has already been validated against the contracts. Use the generator instructions below for "
        "faithful generation, backend compatibility, runtime output shape, and private artifact schema requirements. "
        "Do not ask for another spec. Do not produce commentary outside the required sections.\n\n"
        "Return exactly these Markdown sections, in this order:\n\n"
        "### Conformance failures\n"
        "Use None. unless generation reveals a blocking required-contract issue missed during validation.\n\n"
        "### Backend incompatibilities\n"
        "Use None. unless generation reveals a blocking backend-contract issue missed during validation.\n\n"
        "### Recommended omissions\n"
        "Use bullet points for non-blocking recommended omissions. Use None. if there are none.\n\n"
        "### Private artifact schema\n"
        "Return one fenced json code block containing the per-turn private_artifact JSON Schema.\n\n"
        "### Runtime tutor prompt\n"
        "Return one fenced code block containing the runtime tutor prompt.\n\n"
        "Generator instructions:\n\n"
        f"{generator_prompt_text}"
    )


def _prompt_validation_system_prompt() -> str:
    return (
        "You validate an uploaded runtime tutor prompt before it is saved into the document archive.\n\n"
        "The prompt must be checked against the active tutor specification, the tutor specification contract, "
        "and the backend runtime contract. Do not rewrite the prompt. Do not generate a replacement prompt.\n\n"
        "A valid prompt must faithfully operationalize the active tutor specification and must obey the backend "
        "runtime interface exactly. In particular, check that it requires JSON-only output; treats updated_state "
        "as a sparse delta rather than full replacement; limits updated_state to the exact tutor-updatable keys; "
        "keeps backend-owned fields read-only; does not put private artifacts in student-facing text or updated_state; "
        "does not invent topic IDs, grades, reports, persistence, routing, lifecycle control, or unsupported runtime "
        "inputs; and respects backend timing/lifecycle ownership.\n\n"
        "Return exactly these Markdown sections, in this order:\n\n"
        "### Validation failures\n"
        "Use bullet points for prompt defects that prevent saving. Use None. if there are no failures.\n\n"
        "### Recommended notes\n"
        "Use bullet points for non-blocking concerns or review notes. Use None. if there are none."
    )


def _build_prompt_validation_user_message(
    spec_contract_text: str,
    backend_contract_text: str,
    spec_text: str,
    prompt_text: str,
) -> str:
    return (
        "# 1. Tutor Specification Contract\n\n"
        f"{spec_contract_text}\n\n"
        "---\n\n"
        "# 2. Backend-Tutor Runtime Contract\n\n"
        f"{backend_contract_text}\n\n"
        "---\n\n"
        "# 3. Active Tutor Specification\n\n"
        f"{spec_text}\n\n"
        "---\n\n"
        "# 4. Candidate Runtime Tutor Prompt\n\n"
        f"{prompt_text}\n"
    )


def _call_openai_messages(messages: list[dict[str, str]]) -> str:
    settings = config_module.get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key, timeout=120.0, max_retries=0)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def _call_openai(system_prompt: str, user_message: str) -> str:
    return _call_openai_messages([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ])


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


def parse_validation_output(raw_output: str) -> dict:
    conformance_failures = _bullet_items(_section_text(raw_output, "Conformance failures"))
    backend_incompatibilities = _bullet_items(_section_text(raw_output, "Backend incompatibilities"))
    recommended_omissions = _bullet_items(_section_text(raw_output, "Recommended omissions"))
    return {
        "ok": not conformance_failures and not backend_incompatibilities,
        "conformance_failures": conformance_failures,
        "backend_incompatibilities": backend_incompatibilities,
        "recommended_omissions": recommended_omissions,
    }


def parse_prompt_validation_output(raw_output: str) -> dict:
    failures = _bullet_items(_section_text(raw_output, "Validation failures"))
    notes = _bullet_items(_section_text(raw_output, "Recommended notes"))
    return {"ok": not failures, "validation_failures": failures, "recommended_notes": notes}


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


def _unique_version_key(db: sqlalchemy_orm.Session, document_type: str) -> str:
    while True:
        version_key = _make_version_key()
        doc_id = helpers.make_document_id(document_type, version_key)
        if db.get(models.ArchiveDocumentModel, doc_id) is None:
            return version_key


def _active_docs_for_prompt(db: sqlalchemy_orm.Session) -> tuple[dict[str, models.ArchiveDocumentModel] | None, str | None]:
    docs: dict[str, models.ArchiveDocumentModel] = {}
    missing: list[str] = []
    for doc_type in ("tutor_spec", "tutor_artifact_schema", "tutor_generator_prompt", "tutor_spec_contract", "backend_contract"):
        doc = helpers.get_active_document(db, doc_type)
        if doc is None:
            missing.append(doc_type)
        else:
            docs[doc_type] = doc
    if missing:
        return None, f"No active document(s) in archive: {', '.join(missing)}"
    return docs, None


def spec_is_validated_against_active_contracts(
    db: sqlalchemy_orm.Session,
    doc: models.ArchiveDocumentModel,
) -> bool:
    if doc.document_type != "tutor_spec":
        return False
    links = helpers.parse_linked_documents(doc.linked_documents_json)
    for contract_type in ("tutor_spec_contract", "backend_contract"):
        active_id = helpers.get_active_document_id(db, contract_type)
        if active_id is None or links.get(contract_type) != active_id:
            return False
    return True


def list_validated_specs(db: sqlalchemy_orm.Session) -> list[dict]:
    docs = (
        db.query(models.ArchiveDocumentModel)
        .filter(models.ArchiveDocumentModel.document_type == "tutor_spec")
        .order_by(models.ArchiveDocumentModel.active.desc(), models.ArchiveDocumentModel.created_at.desc())
        .all()
    )
    result = []
    for doc in docs:
        if not spec_is_validated_against_active_contracts(db, doc):
            continue
        result.append({
            "document_id": doc.document_id,
            "title": doc.title,
            "version_key": doc.version_key,
            "active": doc.active,
            "created_at": doc.created_at,
        })
    return result


def validate_spec_against_contracts(db: sqlalchemy_orm.Session, spec_text: str) -> dict:
    active_docs, missing_error = _get_required_active_docs(db)
    if missing_error:
        return {"ok": False, "error": missing_error}
    assert active_docs is not None

    generator_doc = active_docs["tutor_generator_prompt"]
    system_prompt = _spec_validation_system_prompt(generator_doc.content_text)
    user_message = _build_user_message(
        active_docs["tutor_spec_contract"].content_text,
        active_docs["backend_contract"].content_text,
        spec_text,
    )
    try:
        parsed = parse_validation_output(_call_openai(system_prompt, user_message))
    except openai.AuthenticationError as exc:
        return {"ok": False, "error": f"OpenAI authentication error: {exc}"}
    except openai.APIError as exc:
        return {"ok": False, "error": f"OpenAI API error: {exc}"}
    parsed["context_docs"] = {doc_type: doc.document_id for doc_type, doc in active_docs.items()}
    return parsed


def save_validated_spec(
    db: sqlalchemy_orm.Session,
    spec_text: str,
    spec_title: str,
) -> models.ArchiveDocumentModel:
    active_docs, missing_error = _get_required_active_docs(db)
    if missing_error:
        raise ValueError(missing_error)
    assert active_docs is not None

    version_key = _unique_version_key(db, "tutor_spec")
    links = {
        "tutor_spec_contract": active_docs["tutor_spec_contract"].document_id,
        "backend_contract": active_docs["backend_contract"].document_id,
    }
    doc = _insert_doc(
        db,
        "tutor_spec",
        version_key,
        title=spec_title or f"Tutor Specification {version_key}",
        content_text=spec_text,
        content_format="markdown",
        linked_documents_json=json.dumps(links),
        run_id="manual-upload",
    )
    db.commit()
    return doc


def activate_tutor_spec(
    db: sqlalchemy_orm.Session,
    document_id: str,
    *,
    repo_root: pathlib.Path = REPO_ROOT,
) -> tuple[bool, str]:
    doc = db.get(models.ArchiveDocumentModel, document_id)
    if doc is None:
        return False, "Document not found."
    if doc.document_type != "tutor_spec":
        return False, "Document is not a tutor_spec."
    if not spec_is_validated_against_active_contracts(db, doc):
        return False, "Tutor spec is not validated against the active contracts."

    spec_path = repo_root / "docs" / "tutor_specification.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(doc.content_text, encoding="utf-8")
    db.query(models.ArchiveDocumentModel).filter(
        models.ArchiveDocumentModel.document_type == "tutor_spec",
        models.ArchiveDocumentModel.active.is_(True),
    ).update({"active": False})
    doc.active = True
    db.commit()
    return True, "Tutor specification activated. Generate or upload a prompt, then restart the student app after activating it."


def generate_prompt_preview(db: sqlalchemy_orm.Session, spec_document_id: str) -> dict:
    spec_doc = db.get(models.ArchiveDocumentModel, spec_document_id)
    if spec_doc is None or spec_doc.document_type != "tutor_spec":
        return {"ok": False, "error": "Tutor specification document not found."}
    if not spec_is_validated_against_active_contracts(db, spec_doc):
        return {"ok": False, "error": "Tutor specification is not validated against the active contracts."}

    active_docs, missing_error = _get_required_active_docs(db)
    if missing_error:
        return {"ok": False, "error": missing_error}
    assert active_docs is not None
    if not spec_is_validated_against_active_contracts(db, spec_doc):
        return {"ok": False, "error": "Tutor specification is not validated against the active contracts."}

    generator_doc = active_docs["tutor_generator_prompt"]
    user_message = _build_user_message(
        active_docs["tutor_spec_contract"].content_text,
        active_docs["backend_contract"].content_text,
        spec_doc.content_text,
    )
    try:
        raw_output = _call_openai(_prompt_generation_system_prompt(generator_doc.content_text), user_message)
        parsed = parse_generator_output(raw_output)
    except (openai.AuthenticationError, openai.APIError, GenerationOutputError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        return {"ok": False, "error": f"Could not generate prompt: {exc}"}
    if parsed["status"] == "failed":
        return {"ok": False, "status": "failed", **parsed}
    return {
        "ok": True,
        "spec_document_id": spec_doc.document_id,
        "spec_title": spec_doc.title,
        "tutor_prompt": parsed["tutor_prompt"],
        "tutor_artifact_schema": parsed["tutor_artifact_schema"],
        "recommended_omissions": parsed["recommended_omissions"],
    }


def save_generated_prompt_preview(
    db: sqlalchemy_orm.Session,
    spec_document_id: str,
    tutor_prompt_text: str,
    schema_text: str,
    *,
    activate: bool = False,
) -> dict:
    spec_doc = db.get(models.ArchiveDocumentModel, spec_document_id)
    if spec_doc is None or spec_doc.document_type != "tutor_spec":
        return {"ok": False, "error": "Tutor specification document not found."}

    active_docs, missing_error = _get_required_active_docs(db)
    if missing_error:
        return {"ok": False, "error": missing_error}
    assert active_docs is not None
    try:
        schema_obj = json.loads(schema_text)
        jsonschema.Draft202012Validator.check_schema(schema_obj)
    except (json.JSONDecodeError, jsonschema.SchemaError) as exc:
        return {"ok": False, "error": f"Generated private artifact schema is invalid: {exc}"}

    version_key = _unique_version_key(db, "tutor_prompt")
    schema_doc = _insert_doc(
        db,
        "tutor_artifact_schema",
        version_key,
        title=f"Tutor Artifact Schema {version_key}",
        content_text=json.dumps(schema_obj, ensure_ascii=False, indent=2),
        content_format="json",
        linked_documents_json=json.dumps({"backend_contract": active_docs["backend_contract"].document_id}),
        run_id="manual-preview-save",
    )
    prompt_links = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": active_docs["tutor_generator_prompt"].document_id,
        "tutor_spec_contract": active_docs["tutor_spec_contract"].document_id,
        "backend_contract": active_docs["backend_contract"].document_id,
    }
    prompt_doc = _insert_doc(
        db,
        "tutor_prompt",
        version_key,
        title=f"{spec_doc.title} - Tutor Prompt",
        content_text=tutor_prompt_text,
        content_format="markdown",
        linked_documents_json=json.dumps(prompt_links),
        run_id="manual-preview-save",
    )
    db.commit()
    activation = None
    if activate:
        ok, message = admin_documents.activate_tutor_prompt(db, prompt_doc.document_id)
        activation = {"ok": ok, "message": message}
        if not ok:
            return {"ok": False, "error": message, "tutor_prompt_document_id": prompt_doc.document_id}
    return {
        "ok": True,
        "tutor_prompt_document_id": prompt_doc.document_id,
        "tutor_artifact_schema_document_id": schema_doc.document_id,
        "activation": activation,
    }


def validate_prompt_against_active_spec(db: sqlalchemy_orm.Session, prompt_text: str) -> dict:
    active_docs, missing_error = _active_docs_for_prompt(db)
    if missing_error:
        return {"ok": False, "error": missing_error}
    assert active_docs is not None
    messages = [
        {"role": "system", "content": _prompt_validation_system_prompt()},
        {
            "role": "user",
            "content": _build_prompt_validation_user_message(
                active_docs["tutor_spec_contract"].content_text,
                active_docs["backend_contract"].content_text,
                active_docs["tutor_spec"].content_text,
                prompt_text,
            ),
        },
    ]
    try:
        parsed = parse_prompt_validation_output(_call_openai_messages(messages))
    except openai.AuthenticationError as exc:
        return {"ok": False, "error": f"OpenAI authentication error: {exc}"}
    except openai.APIError as exc:
        return {"ok": False, "error": f"OpenAI API error: {exc}"}
    parsed["context_docs"] = {doc_type: doc.document_id for doc_type, doc in active_docs.items()}
    return parsed


def save_validated_prompt(
    db: sqlalchemy_orm.Session,
    prompt_text: str,
    prompt_title: str,
    *,
    activate: bool = False,
) -> dict:
    active_docs, missing_error = _active_docs_for_prompt(db)
    if missing_error:
        return {"ok": False, "error": missing_error}
    assert active_docs is not None
    version_key = _unique_version_key(db, "tutor_prompt")
    prompt_links = {
        "tutor_spec": active_docs["tutor_spec"].document_id,
        "tutor_artifact_schema": active_docs["tutor_artifact_schema"].document_id,
        "tutor_generator_prompt": active_docs["tutor_generator_prompt"].document_id,
        "tutor_spec_contract": active_docs["tutor_spec_contract"].document_id,
        "backend_contract": active_docs["backend_contract"].document_id,
    }
    prompt_doc = _insert_doc(
        db,
        "tutor_prompt",
        version_key,
        title=prompt_title or f"Tutor Prompt {version_key}",
        content_text=prompt_text,
        content_format="markdown",
        linked_documents_json=json.dumps(prompt_links),
        run_id="manual-upload",
    )
    db.commit()
    activation = None
    if activate:
        ok, message = admin_documents.activate_tutor_prompt(db, prompt_doc.document_id)
        activation = {"ok": ok, "message": message}
        if not ok:
            return {"ok": False, "error": message, "tutor_prompt_document_id": prompt_doc.document_id}
    return {"ok": True, "tutor_prompt_document_id": prompt_doc.document_id, "activation": activation}


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
        raw_output = _call_openai(_prompt_generation_system_prompt(generator_doc.content_text), user_message)
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
        linked_documents_json=json.dumps({
            "tutor_spec_contract": spec_contract_doc.document_id,
            "backend_contract": backend_contract_doc.document_id,
        }),
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
