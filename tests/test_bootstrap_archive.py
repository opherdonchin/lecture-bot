import json
import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.archive_helpers as helpers
import app.db as db_module
import app.models as models
from scripts.bootstrap_archive import bootstrap_archive


SPEC_CONTRACT = "# Spec Contract\n\nThis is the spec contract."
BACKEND_CONTRACT = "# Backend Contract\n\nThis is the backend contract."
GENERATOR_PROMPT = "# Generator Prompt\n\nGenerate a tutor."
TUTOR_SPEC = "# Tutor Spec\n\nThis is the tutor specification."
ARTIFACT_SCHEMA = json.dumps({"type": "object", "properties": {}})
TUTOR_PROMPT = "# Tutor Prompt\n\nYou are a tutor."
REPAIR_PROMPT = "# Repair Prompt\n\nRepair this spec."


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db_module.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repo_root(tmp_path):
    docs = tmp_path / "docs"
    prompts = tmp_path / "prompts"
    docs.mkdir()
    prompts.mkdir()

    (docs / "tutor_specification_contract.md").write_text(SPEC_CONTRACT, encoding="utf-8")
    (docs / "backend_tutor_contract.md").write_text(BACKEND_CONTRACT, encoding="utf-8")
    (docs / "tutor_specification.md").write_text(TUTOR_SPEC, encoding="utf-8")
    (prompts / "tutor_generator_prompt.md").write_text(GENERATOR_PROMPT, encoding="utf-8")
    (prompts / "tutor_prompt_private_artifact_schema.json").write_text(ARTIFACT_SCHEMA, encoding="utf-8")
    (prompts / "tutor_prompt.md").write_text(TUTOR_PROMPT, encoding="utf-8")
    (prompts / "spec_repair_prompt.md").write_text(REPAIR_PROMPT, encoding="utf-8")

    return tmp_path


def test_bootstrap_imports_expected_documents(db, repo_root):
    summary = bootstrap_archive(db, repo_root, version_key="2026-05-01")

    imported = summary["imported"]
    assert len(imported) == 7
    types_imported = {doc_id.split("_", 1)[1].rsplit("_", 1)[0] for doc_id in imported}
    expected_types = {
        "tutor_spec_contract",
        "backend_contract",
        "tutor_generator_prompt",
        "tutor_spec",
        "tutor_artifact_schema",
        "tutor_prompt",
        "spec_repair_prompt",
    }
    for t in expected_types:
        assert any(t in doc_id for doc_id in imported), f"Expected {t} to be imported"


def test_bootstrap_idempotent(db, repo_root):
    first = bootstrap_archive(db, repo_root, version_key="2026-05-01")
    second = bootstrap_archive(db, repo_root, version_key="2026-05-01")

    assert len(first["imported"]) == 7
    assert len(second["imported"]) == 0
    assert len(second["skipped"]) == 7

    count = db.query(models.ArchiveDocumentModel).count()
    assert count == 7


def test_bootstrap_all_documents_active(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    docs = db.query(models.ArchiveDocumentModel).all()
    for doc in docs:
        assert doc.active, f"{doc.document_id} should be active"


def test_bootstrap_sha256_correct(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    doc = db.get(models.ArchiveDocumentModel, "doc_tutor_spec_contract_2026-05-01")
    assert doc is not None
    assert doc.content_sha256 == helpers.sha256_of_text(SPEC_CONTRACT)


def test_bootstrap_content_format_markdown(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    doc = db.get(models.ArchiveDocumentModel, "doc_tutor_prompt_2026-05-01")
    assert doc is not None
    assert doc.content_format == "markdown"


def test_bootstrap_content_format_json(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    doc = db.get(models.ArchiveDocumentModel, "doc_tutor_artifact_schema_2026-05-01")
    assert doc is not None
    assert doc.content_format == "json"


def test_bootstrap_tutor_prompt_linked_documents(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    doc = db.get(models.ArchiveDocumentModel, "doc_tutor_prompt_2026-05-01")
    assert doc is not None
    links = helpers.parse_linked_documents(doc.linked_documents_json)
    assert "tutor_spec" in links
    assert "tutor_artifact_schema" in links
    assert "tutor_generator_prompt" in links
    assert "tutor_spec_contract" in links
    assert "backend_contract" in links


def test_bootstrap_tutor_spec_linked_to_contract(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    doc = db.get(models.ArchiveDocumentModel, "doc_tutor_spec_2026-05-01")
    assert doc is not None
    links = helpers.parse_linked_documents(doc.linked_documents_json)
    assert "tutor_spec_contract" in links
    assert links["tutor_spec_contract"] == "doc_tutor_spec_contract_2026-05-01"


def test_bootstrap_provenance_recorded(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    doc = db.get(models.ArchiveDocumentModel, "doc_tutor_prompt_2026-05-01")
    assert doc is not None
    provenance = json.loads(doc.provenance_json)
    assert "source_path" in provenance
    assert "bootstrap_version_key" in provenance
    assert provenance["bootstrap_version_key"] == "2026-05-01"


def test_bootstrap_skips_missing_files(db, tmp_path):
    docs = tmp_path / "docs"
    prompts = tmp_path / "prompts"
    docs.mkdir()
    prompts.mkdir()
    # Only write two files
    (docs / "tutor_specification_contract.md").write_text(SPEC_CONTRACT, encoding="utf-8")
    (docs / "backend_tutor_contract.md").write_text(BACKEND_CONTRACT, encoding="utf-8")

    summary = bootstrap_archive(db, tmp_path, version_key="2026-05-01")
    assert len(summary["imported"]) == 2
    assert len(summary["skipped"]) == 0


def test_bootstrap_dry_run_does_not_write(db, repo_root):
    summary = bootstrap_archive(db, repo_root, version_key="2026-05-01", dry_run=True)
    assert len(summary["imported"]) == 7
    count = db.query(models.ArchiveDocumentModel).count()
    assert count == 0


def test_bootstrap_sha256_match_skips_even_with_different_id(db, repo_root):
    bootstrap_archive(db, repo_root, version_key="2026-05-01")
    # Second run with different version key but same file content
    summary = bootstrap_archive(db, repo_root, version_key="2026-05-02")
    assert len(summary["imported"]) == 0
    assert len(summary["skipped"]) == 7
