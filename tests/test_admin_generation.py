import json
import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.admin_documents as admin_documents
import app.admin_generation as admin_generation
import app.archive_helpers as helpers
import app.db as db_module
import app.models as models
import app.prompt_loader as prompt_loader


_BACKEND_CONTRACT_TEXT = f"**Contract version: {prompt_loader.BACKEND_CONTRACT_VERSION}.**\n\nbackend contract"
_PACKAGE_CONTRACT_ID = "doc_lecture_package_contract_pml-brief-1"
_DECLARED_PROMPT = (
    f"Backend contract: {prompt_loader.BACKEND_CONTRACT_VERSION}\n\n"
    "Lecture package contract: pml-brief-1\n\n"
    "You are a tutor."
)


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


def _make_active_package_contract(db):
    return _make_doc(
        db,
        "lecture_package_contract",
        "pml-brief-1",
        active=True,
        content="# Lecture package contract `pml-brief-1`\n\nThe contract text.",
    )


def _make_active_generation_docs(db):
    _make_active_package_contract(db)
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-11", active=True, content="spec contract")
    backend_contract = _make_doc(db, "backend_contract", "2026-05-11", active=True, content=_BACKEND_CONTRACT_TEXT)
    generator = _make_doc(
        db,
        "tutor_generator_prompt",
        "2026-05-11",
        active=True,
        linked={
            "tutor_spec_contract": spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
<private_artifact_schema>
{"type":"object","additionalProperties":false}
</private_artifact_schema>

### Runtime tutor prompt
<runtime_tutor_prompt>
Return JSON only.
</runtime_tutor_prompt>
"""

    parsed = admin_generation.parse_generator_output(raw)

    assert parsed["status"] == "success"
    assert parsed["recommended_omissions"] == ["Add more examples."]
    assert json.loads(parsed["tutor_artifact_schema"]) == {
        "type": "object",
        "additionalProperties": False,
    }
    assert parsed["tutor_prompt"] == "Return JSON only."


def test_parse_generator_output_keeps_declaration_and_tagged_format():
    prompt = (
        "Backend contract: 0.6.1\n\n"
        "Reply as:\n<assistant_message>\n...\n</assistant_message>\n"
        '{"updated_state": {}}'
    )
    raw = f"""### Conformance failures
None.

### Backend incompatibilities
None.

### Recommended omissions
None.

### Private artifact schema
<private_artifact_schema>
{{"type":"object"}}
</private_artifact_schema>

### Runtime tutor prompt
<runtime_tutor_prompt>
{prompt}
</runtime_tutor_prompt>
"""

    parsed = admin_generation.parse_generator_output(raw)

    assert parsed["tutor_prompt"] == prompt
    assert prompt_loader.declared_backend_contract(parsed["tutor_prompt"]) == "0.6.1"


def _make_spec(db, spec_contract, backend_contract):
    return _make_doc(db, "tutor_spec", "saved", linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
        "lecture_package_contract": _PACKAGE_CONTRACT_ID,
    })


def test_generation_refused_without_active_package_contract():
    db = _session()
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-11", active=True)
    backend_contract = _make_doc(db, "backend_contract", "2026-05-11", active=True, content=_BACKEND_CONTRACT_TEXT)
    _make_doc(db, "tutor_generator_prompt", "2026-05-11", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
        "lecture_package_contract": _PACKAGE_CONTRACT_ID,
    })

    result = admin_generation.run_generation(db, "current spec", "Spec Title")

    assert result["ok"] is False
    assert "No active document(s) in archive: lecture_package_contract" in result["error"]


def test_generation_refused_when_generator_links_no_contracts():
    db = _session()
    _make_active_package_contract(db)
    _make_doc(db, "tutor_spec_contract", "2026-05-11", active=True)
    _make_doc(db, "backend_contract", "2026-05-11", active=True, content=_BACKEND_CONTRACT_TEXT)
    _make_doc(db, "tutor_generator_prompt", "2026-05-11", active=True)

    result = admin_generation.run_generation(db, "current spec", "Spec Title")

    assert result["ok"] is False
    assert "does not link to" in result["error"]


def test_generation_refused_when_generator_does_not_link_the_package_contract():
    db = _session()
    spec_contract, backend_contract, generator = _make_active_generation_docs(db)
    generator.linked_documents_json = json.dumps({
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    })

    result = admin_generation.run_generation(db, "current spec", "Spec Title")

    assert result["ok"] is False
    assert "does not link to: lecture_package_contract" in result["error"]


def test_a_new_package_contract_invalidates_the_generator_like_a_new_backend_contract():
    db = _session()
    _make_active_generation_docs(db)
    db.get(models.ArchiveDocumentModel, _PACKAGE_CONTRACT_ID).active = False
    _make_doc(db, "lecture_package_contract", "pml-brief-2", active=True, content="# Lecture package contract `pml-brief-2`")

    result = admin_generation.run_generation(db, "current spec", "Spec Title")

    assert result["ok"] is False
    assert "lecture_package_contract" in result["error"]
    assert "does not match active" in result["error"]


def test_generate_prompt_preview_sends_package_contract_before_the_specification(monkeypatch):
    db = _session()
    spec_contract, backend_contract, _generator = _make_active_generation_docs(db)
    spec = _make_spec(db, spec_contract, backend_contract)
    sent = {}

    def fake_call(_system_prompt, user_message):
        sent["user_message"] = user_message
        return "### Conformance failures\nNone.\n\n### Backend incompatibilities\nNone.\n\n### Recommended omissions\nNone."

    monkeypatch.setattr(admin_generation, "_call_openai", fake_call)
    admin_generation.generate_prompt_preview(db, spec.document_id)

    message = sent["user_message"]
    assert message.index("The contract text.") < message.index("# Tutor Specification\n")


def test_save_generated_prompt_links_active_package_contract():
    db = _session()
    spec_contract, backend_contract, _generator = _make_active_generation_docs(db)
    spec = _make_spec(db, spec_contract, backend_contract)

    result = admin_generation.save_generated_prompt_preview(db, spec.document_id, "prompt", '{"type":"object"}')

    doc = db.get(models.ArchiveDocumentModel, result["tutor_prompt_document_id"])
    assert helpers.parse_linked_documents(doc.linked_documents_json)["lecture_package_contract"] == _PACKAGE_CONTRACT_ID


def _active_spec_and_schema(db):
    spec_contract, backend_contract, _generator = _make_active_generation_docs(db)
    _make_doc(db, "tutor_spec", "active", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
        "lecture_package_contract": _PACKAGE_CONTRACT_ID,
    })
    _make_doc(db, "tutor_artifact_schema", "active", active=True, content='{"type":"object"}', content_format="json")


def test_uploaded_prompt_refused_without_declarations(monkeypatch):
    db = _session()
    _active_spec_and_schema(db)
    monkeypatch.setattr(admin_generation, "_call_openai_messages", lambda _messages: "should not be called")

    validated = admin_generation.validate_prompt_against_active_spec(db, "You are a tutor.")

    assert validated["ok"] is False
    assert any("backend contract" in failure for failure in validated["validation_failures"])
    assert any("lecture package contract" in failure for failure in validated["validation_failures"])


def test_uploaded_prompt_refused_when_it_declares_another_package_contract():
    db = _session()
    _active_spec_and_schema(db)
    prompt = _DECLARED_PROMPT.replace("pml-brief-1", "pml-brief-2")

    validated = admin_generation.validate_prompt_against_active_spec(db, prompt)

    assert validated["ok"] is False
    assert any("pml-brief-2" in failure for failure in validated["validation_failures"])


def test_generator_prompt_asks_for_the_current_contract():
    generator = pathlib.Path("prompts/tutor_generator_prompt.md").read_text(encoding="utf-8")

    assert "<assistant_message>" in generator
    assert "`Backend contract: `" in generator
    assert "`Lecture package contract: `" in generator
    assert "pml-brief-1" not in generator
    assert "JSON only" not in generator
    assert "JSON-only" not in generator
    # The version comes from the contract the generator is given, not from its own text.
    assert prompt_loader.BACKEND_CONTRACT_VERSION not in generator


def _generator_output(prompt_block: str, schema_block: str = '<private_artifact_schema>\n{"type":"object"}\n</private_artifact_schema>') -> str:
    return (
        "### Conformance failures\nNone.\n\n### Backend incompatibilities\nNone.\n\n### Recommended omissions\nNone.\n\n"
        f"### Private artifact schema\n{schema_block}\n\n### Runtime tutor prompt\n{prompt_block}\n"
    )


@pytest.mark.parametrize("prompt", [
    "Line one.\nReply like this:\n```text\n<assistant_message>\nhi\n</assistant_message>\n```\nLine last.",
    "Line one.\n### TIMING\nLine last.",
    "Line one.\n```text\nx\n```\nmore\n### TIMING\nLine last.",
    "Line one.\n````\n```text\nx\n```\n````\nLine last.",
    "Line one.\n### Conformance failures\n- not a real failure\nLine last.",
])
def test_parse_generator_output_keeps_the_whole_prompt_whatever_it_contains(prompt):
    raw = _generator_output(f"<runtime_tutor_prompt>\n{prompt}\n</runtime_tutor_prompt>")

    parsed = admin_generation.parse_generator_output(raw)

    assert parsed["status"] == "success"
    assert parsed["tutor_prompt"] == prompt


@pytest.mark.parametrize("prompt_block", [
    "```\nA prompt in the old form.\n```",
    "<runtime_tutor_prompt>\nNo closing tag.",
    "No opening tag.\n</runtime_tutor_prompt>",
    "</runtime_tutor_prompt>\nBackwards.\n<runtime_tutor_prompt>",
    "<runtime_tutor_prompt>\nOne.\n</runtime_tutor_prompt>\n<runtime_tutor_prompt>\nTwo.\n</runtime_tutor_prompt>",
    "<runtime_tutor_prompt>\n</runtime_tutor_prompt>",
])
def test_parse_generator_output_refuses_a_malformed_prompt_block(prompt_block):
    with pytest.raises(admin_generation.GenerationOutputError):
        admin_generation.parse_generator_output(_generator_output(prompt_block))


def test_parse_generator_output_refuses_a_missing_schema_block():
    raw = _generator_output("<runtime_tutor_prompt>\nA prompt.\n</runtime_tutor_prompt>", schema_block='```json\n{}\n```')

    with pytest.raises(admin_generation.GenerationOutputError):
        admin_generation.parse_generator_output(raw)


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
        "package contract text",
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
    backend_contract = _make_doc(db, "backend_contract", "2026-05-11", active=True, content=_BACKEND_CONTRACT_TEXT)
    _make_active_package_contract(db)
    old_spec_contract = _make_doc(db, "tutor_spec_contract", "2026-04-01", content="old spec contract")
    _make_doc(
        db,
        "tutor_generator_prompt",
        "2026-05-11",
        active=True,
        linked={
            "tutor_spec_contract": old_spec_contract.document_id,
            "backend_contract": backend_contract.document_id,
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
    assert "<private_artifact_schema>" in prompt
    assert "<runtime_tutor_prompt>" in prompt
    assert "generator rules" in prompt


def test_prompt_validation_prompt_uses_active_spec_and_contracts():
    prompt = admin_generation._prompt_validation_system_prompt()
    user_message = admin_generation._build_prompt_validation_user_message(
        "spec contract",
        "backend contract",
        "package contract",
        "active spec",
        "candidate prompt",
    )

    assert "validate an uploaded runtime tutor prompt" in prompt
    assert "updated_state as a sparse delta" in prompt
    assert "<assistant_message>" in prompt
    assert "JSON-only" not in prompt
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
<private_artifact_schema>
{"type":"object","additionalProperties":false}
</private_artifact_schema>

### Runtime tutor prompt
<runtime_tutor_prompt>
generated prompt
</runtime_tutor_prompt>
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
        "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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

    result = admin_generation.save_validated_prompt(db, _DECLARED_PROMPT, "Uploaded Prompt")

    assert result["ok"] is True
    prompt_doc = db.get(models.ArchiveDocumentModel, result["tutor_prompt_document_id"])
    links = helpers.parse_linked_documents(prompt_doc.linked_documents_json)
    assert links == {
        "tutor_spec": spec.document_id,
        "tutor_artifact_schema": schema.document_id,
        "tutor_generator_prompt": generator.document_id,
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
        "lecture_package_contract": _PACKAGE_CONTRACT_ID,
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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
        },
        content="saved spec",
    )
    paths = {
        "tutor_prompt": tmp_path / "tutor_prompt.md",
        "tutor_artifact_schema": tmp_path / "schema.json",
        "tutor_spec": tmp_path / "tutor_specification.md",
    }
    monkeypatch.setattr(admin_documents, "canonical_document_paths", lambda: paths)

    result = admin_generation.save_generated_prompt_preview(
        db,
        spec.document_id,
        _DECLARED_PROMPT,
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
    assert paths["tutor_prompt"].read_text(encoding="utf-8") == _DECLARED_PROMPT


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
            "lecture_package_contract": _PACKAGE_CONTRACT_ID,
        },
        content=_DECLARED_PROMPT,
    )
    paths = {
        "tutor_prompt": tmp_path / "tutor_prompt.md",
        "tutor_artifact_schema": tmp_path / "schema.json",
        "tutor_spec": tmp_path / "tutor_specification.md",
    }
    monkeypatch.setattr(admin_documents, "canonical_document_paths", lambda: paths)

    ok, message = admin_documents.activate_tutor_prompt(db, prompt.document_id)

    assert ok is True
    assert "activated" in message
    assert paths["tutor_prompt"].read_text(encoding="utf-8") == _DECLARED_PROMPT
    assert paths["tutor_artifact_schema"].read_text(encoding="utf-8") == '{"type":"object"}'
    assert paths["tutor_spec"].read_text(encoding="utf-8") == "generated spec"
    assert db.get(models.ArchiveDocumentModel, prompt.document_id).active is True
