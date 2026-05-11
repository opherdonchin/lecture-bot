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
