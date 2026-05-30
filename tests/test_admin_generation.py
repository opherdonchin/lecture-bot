import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.admin_documents as admin_documents
import app.admin_generation as admin_generation
import app.archive_helpers as helpers
import app.db as db_module
import app.models as models


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db_module.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def _make_doc(db, document_type, version_key, *, active=False, linked=None, content="text", content_format="markdown"):
    doc = models.ArchiveDocumentModel(
        document_id=helpers.make_document_id(document_type, version_key),
        document_type=document_type,
        version_key=version_key,
        title=f"{document_type} {version_key}",
        content_text=content,
        content_format=content_format,
        linked_documents_json=json.dumps(linked) if linked else None,
        content_sha256=helpers.sha256_of_text(content),
        active=active,
    )
    db.add(doc)
    db.commit()
    return doc


def _make_active_generation_docs(db):
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-11", active=True, content="spec contract")
    backend_contract = _make_doc(db, "backend_contract", "2026-05-11", active=True, content="backend contract")
    generator = _make_doc(
        db,
        "tutor_generator_prompt",
        "2026-05-11",
        active=True,
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="generator prompt",
    )
    return spec_contract, backend_contract, generator


def test_parse_generator_output_success_markdown_sections():
    raw = """### Conformance failures
None.

### Backend incompatibilities
None.

### Recommended omissions
- Add more examples.

### Private artifact schema
```json
{"type":"object","additionalProperties":false}
```

### Runtime tutor prompt
```
Return JSON only.
```
"""

    parsed = admin_generation.parse_generator_output(raw)

    assert parsed["status"] == "success"
    assert parsed["recommended_omissions"] == ["Add more examples."]
    assert json.loads(parsed["tutor_artifact_schema"]) == {
        "type": "object",
        "additionalProperties": False,
    }
    assert parsed["tutor_prompt"] == "Return JSON only."


def test_parse_generator_output_failed_sections_do_not_require_prompt():
    raw = """### Conformance failures
- Missing A3.

### Backend incompatibilities
None.

### Recommended omissions
None.
"""

    parsed = admin_generation.parse_generator_output(raw)

    assert parsed["status"] == "failed"
    assert parsed["conformance_failures"] == ["Missing A3."]
    assert parsed["tutor_prompt"] is None


def test_parse_validation_output_accepts_bold_none_markers():
    raw = """### Conformance failures
**None.**

### Backend incompatibilities
**None.**

### Recommended omissions
**None.**
"""

    parsed = admin_generation.parse_validation_output(raw)

    assert parsed["ok"] is True
    assert parsed["conformance_failures"] == []
    assert parsed["backend_incompatibilities"] == []
    assert parsed["recommended_omissions"] == []


def test_parse_validation_output_does_not_block_explicitly_non_blocking_backend_notes():
    raw = """### Conformance failures
**None.**

### Backend incompatibilities
**Backend runtime input assumptions exceed the contract:** the specification repeatedly relies on `grade_impact_deltas` being available via `current_tutoring_state`, but the backend contract defines `grade_impact_deltas` as a backend-computed field inside `current_tutoring_state` and also lists the current injected runtime inputs without naming it separately. This is not fatal by itself; however, the specification also frames graded-mode behavior around “available runtime state provides no positive grade-impact opportunity through `grade_impact_deltas`,” making that field operationally central. Because the backend contract does provide it inside `current_tutoring_state`, this is **not** a blocking incompatibility.
**None.**

### Recommended omissions
**None.**
"""

    parsed = admin_generation.parse_validation_output(raw)

    assert parsed["ok"] is True
    assert parsed["backend_incompatibilities"] == []


def test_parse_validation_output_still_blocks_backend_incompatibilities():
    raw = """### Conformance failures
None.

### Backend incompatibilities
- The specification requires an unsupported runtime input named `foo`.

### Recommended omissions
None.
"""

    parsed = admin_generation.parse_validation_output(raw)

    assert parsed["ok"] is False
    assert parsed["backend_incompatibilities"] == [
        "The specification requires an unsupported runtime input named `foo`."
    ]


def test_parse_validation_output_accepts_explicit_blocking_labels():
    raw = """### Validation status
BLOCKED

### Conformance failures
Blocking issues: yes
- [blocking] Missing required specification section A3.

### Backend incompatibilities
Blocking issues: yes
- [non-blocking] The spec mentions `grade_impact_deltas`, but the backend provides it inside `current_tutoring_state`.
- [blocking] The specification requires a separate runtime input named `foo`.

### Recommended omissions
Blocking issues: no
- [non-blocking] Add more examples.
"""

    parsed = admin_generation.parse_validation_output(raw)

    assert parsed["ok"] is False
    assert parsed["conformance_failures"] == ["Missing required specification section A3."]
    assert parsed["backend_incompatibilities"] == [
        "The specification requires a separate runtime input named `foo`."
    ]
    assert parsed["recommended_omissions"] == ["Add more examples."]


def test_parse_validation_output_passes_with_only_explicit_non_blocking_items():
    raw = """### Validation status
PASS

### Conformance failures
Blocking issues: no
None.

### Backend incompatibilities
Blocking issues: no
- [non-blocking] The spec mentions `grade_impact_deltas`, but the backend provides it inside `current_tutoring_state`.

### Recommended omissions
Blocking issues: no
- [non-blocking] Add more examples.
"""

    parsed = admin_generation.parse_validation_output(raw)

    assert parsed["ok"] is True
    assert parsed["backend_incompatibilities"] == []
    assert parsed["recommended_omissions"] == ["Add more examples."]


def test_spec_validation_prompt_is_validation_only_and_uses_contract_sections():
    prompt = admin_generation._spec_validation_system_prompt("generator rules")
    user_message = admin_generation._build_user_message(
        "spec contract text",
        "backend contract text",
        "candidate spec text",
    )

    assert "validation only" in prompt.lower()
    assert "Do not generate a private artifact schema" in prompt
    assert "### Validation status" in prompt
    assert "PASS or BLOCKED" in prompt
    assert "### Conformance failures" in prompt
    assert "### Backend incompatibilities" in prompt
    assert "[blocking]" in prompt
    assert "[non-blocking]" in prompt
    assert "### Recommended omissions" in prompt
    assert "generator rules" in prompt
    assert "spec contract text" in user_message
    assert "backend contract text" in user_message
    assert "candidate spec text" in user_message


def test_validate_spec_rejects_stale_active_generator_prompt(monkeypatch):
    db = _session()
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-11", active=True, content="spec contract")
    backend_contract = _make_doc(db, "backend_contract", "2026-05-11", active=True, content="backend contract")
    old_spec_contract = _make_doc(db, "tutor_spec_contract", "2026-04-01", content="old spec contract")
    _make_doc(
        db,
        "tutor_generator_prompt",
        "2026-05-11",
        active=True,
        linked={
            "tutor_spec_contract": old_spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="generator prompt",
    )
    monkeypatch.setattr(admin_generation, "_call_openai", lambda _system, _user: "should not be called")

    result = admin_generation.validate_spec_against_contracts(db, "candidate spec")

    assert result["ok"] is False
    assert "Active tutor_generator_prompt is not compatible" in result["error"]
    assert old_spec_contract.document_id in result["error"]
    assert spec_contract.document_id in result["error"]


def test_prompt_generation_prompt_requires_schema_and_prompt_sections():
    prompt = admin_generation._prompt_generation_system_prompt("generator rules")

    assert "already validated tutor specification" in prompt
    assert "### Private artifact schema" in prompt
    assert "### Runtime tutor prompt" in prompt
    assert "fenced json code block" in prompt
    assert "generator rules" in prompt


def test_prompt_validation_prompt_uses_active_spec_and_contracts():
    prompt = admin_generation._prompt_validation_system_prompt()
    user_message = admin_generation._build_prompt_validation_user_message(
        "spec contract",
        "backend contract",
        "active spec",
        "candidate prompt",
    )

    assert "validate an uploaded runtime tutor prompt" in prompt
    assert "updated_state as a sparse delta" in prompt
    assert "### Validation failures" in prompt
    assert "### Recommended notes" in prompt
    assert "spec contract" in user_message
    assert "backend contract" in user_message
    assert "active spec" in user_message
    assert "candidate prompt" in user_message


def test_run_generation_stores_generated_docs(monkeypatch):
    db = _session()
    _make_active_generation_docs(db)
    raw = """### Conformance failures
None.

### Backend incompatibilities
None.

### Recommended omissions
None.

### Private artifact schema
```json
{"type":"object","additionalProperties":false}
```

### Runtime tutor prompt
```
generated prompt
```
"""
    monkeypatch.setattr(admin_generation, "_call_openai", lambda _system, _user: raw)

    result = admin_generation.run_generation(db, "current spec", "Spec Title")

    assert result["ok"] is True
    assert len(result["created_document_ids"]) == 3
    prompt_doc = db.get(models.ArchiveDocumentModel, result["tutor_prompt_document_id"])
    assert prompt_doc.content_text == "generated prompt"
    assert prompt_doc.active is False


def test_save_validated_spec_links_active_contracts():
    db = _session()
    spec_contract, backend_contract, _generator = _make_active_generation_docs(db)

    doc = admin_generation.save_validated_spec(db, "new spec", "Uploaded Spec")

    assert doc.document_type == "tutor_spec"
    assert doc.content_text == "new spec"
    links = helpers.parse_linked_documents(doc.linked_documents_json)
    assert links == {
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    assert doc.active is False


def test_list_validated_specs_requires_active_contract_links():
    db = _session()
    spec_contract, backend_contract, _generator = _make_active_generation_docs(db)
    valid = _make_doc(
        db,
        "tutor_spec",
        "valid",
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
    )
    _make_doc(db, "tutor_spec", "historical-without-links")
    _make_doc(
        db,
        "tutor_spec",
        "stale-contract",
        linked={
            "tutor_spec_contract": "doc_tutor_spec_contract_old",
            "backend_contract": backend_contract.document_id,
        },
    )

    specs = admin_generation.list_validated_specs(db)

    assert [spec["document_id"] for spec in specs] == [valid.document_id]


def test_activate_tutor_spec_marks_only_spec_active(tmp_path):
    db = _session()
    spec_contract, backend_contract, _generator = _make_active_generation_docs(db)
    old_spec = _make_doc(
        db,
        "tutor_spec",
        "old",
        active=True,
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="old spec",
    )
    new_spec = _make_doc(
        db,
        "tutor_spec",
        "new",
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="new spec",
    )

    ok, message = admin_generation.activate_tutor_spec(db, new_spec.document_id, repo_root=tmp_path)

    assert ok is True
    assert "activated" in message
    assert (tmp_path / "docs" / "tutor_specification.md").read_text(encoding="utf-8") == "new spec"
    assert db.get(models.ArchiveDocumentModel, old_spec.document_id).active is False
    assert db.get(models.ArchiveDocumentModel, new_spec.document_id).active is True


def test_save_validated_prompt_links_active_spec_and_contracts():
    db = _session()
    spec_contract, backend_contract, generator = _make_active_generation_docs(db)
    spec = _make_doc(
        db,
        "tutor_spec",
        "active",
        active=True,
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="active spec",
    )
    schema = _make_doc(
        db,
        "tutor_artifact_schema",
        "active",
        active=True,
        linked={"backend_contract": backend_contract.document_id},
        content='{"type":"object"}',
        content_format="json",
    )

    result = admin_generation.save_validated_prompt(db, "uploaded prompt", "Uploaded Prompt")

    assert result["ok"] is True
    prompt_doc = db.get(models.ArchiveDocumentModel, result["tutor_prompt_document_id"])
    links = helpers.parse_linked_documents(prompt_doc.linked_documents_json)
    assert links == {
        "tutor_spec": spec.document_id,
        "tutor_artifact_schema": schema.document_id,
        "tutor_generator_prompt": generator.document_id,
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    assert prompt_doc.active is False


def test_save_generated_prompt_preview_can_activate(tmp_path, monkeypatch):
    db = _session()
    spec_contract, backend_contract, generator = _make_active_generation_docs(db)
    spec = _make_doc(
        db,
        "tutor_spec",
        "saved",
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="saved spec",
    )
    paths = {
        "tutor_prompt": tmp_path / "tutor_prompt.md",
        "tutor_artifact_schema": tmp_path / "schema.json",
        "tutor_spec": tmp_path / "tutor_specification.md",
    }
    monkeypatch.setattr(admin_documents, "CANONICAL_DOCUMENT_PATHS", paths)

    result = admin_generation.save_generated_prompt_preview(
        db,
        spec.document_id,
        "generated prompt",
        '{"type":"object"}',
        activate=True,
    )

    assert result["ok"] is True
    prompt_doc = db.get(models.ArchiveDocumentModel, result["tutor_prompt_document_id"])
    links = helpers.parse_linked_documents(prompt_doc.linked_documents_json)
    assert links["tutor_spec"] == spec.document_id
    assert links["tutor_generator_prompt"] == generator.document_id
    assert links["tutor_spec_contract"] == spec_contract.document_id
    assert links["backend_contract"] == backend_contract.document_id
    assert prompt_doc.active is True
    assert paths["tutor_prompt"].read_text(encoding="utf-8") == "generated prompt"


def test_activate_tutor_prompt_writes_canonical_files(tmp_path, monkeypatch):
    db = _session()
    spec_contract, backend_contract, generator = _make_active_generation_docs(db)
    spec = _make_doc(
        db,
        "tutor_spec",
        "generated",
        linked={"tutor_spec_contract": spec_contract.document_id},
        content="generated spec",
    )
    schema = _make_doc(
        db,
        "tutor_artifact_schema",
        "generated",
        linked={"backend_contract": backend_contract.document_id},
        content='{"type":"object"}',
        content_format="json",
    )
    prompt = _make_doc(
        db,
        "tutor_prompt",
        "generated",
        linked={
            "tutor_spec": spec.document_id,
            "tutor_artifact_schema": schema.document_id,
            "tutor_generator_prompt": generator.document_id,
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
        },
        content="generated prompt",
    )
    paths = {
        "tutor_prompt": tmp_path / "tutor_prompt.md",
        "tutor_artifact_schema": tmp_path / "schema.json",
        "tutor_spec": tmp_path / "tutor_specification.md",
    }
    monkeypatch.setattr(admin_documents, "CANONICAL_DOCUMENT_PATHS", paths)

    ok, message = admin_documents.activate_tutor_prompt(db, prompt.document_id)

    assert ok is True
    assert "activated" in message
    assert paths["tutor_prompt"].read_text(encoding="utf-8") == "generated prompt"
    assert paths["tutor_artifact_schema"].read_text(encoding="utf-8") == '{"type":"object"}'
    assert paths["tutor_spec"].read_text(encoding="utf-8") == "generated spec"
    assert db.get(models.ArchiveDocumentModel, prompt.document_id).active is True
