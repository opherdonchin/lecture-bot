import datetime
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.archive_helpers as helpers
import app.db as db_module
import app.models as models


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db_module.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


def _make_doc(db, document_type, version_key, active=False, linked=None, content="text"):
    doc = models.ArchiveDocumentModel(
        document_id=helpers.make_document_id(document_type, version_key),
        document_type=document_type,
        version_key=version_key,
        title=f"{document_type} {version_key}",
        content_text=content,
        content_format="markdown",
        linked_documents_json=json.dumps(linked) if linked else None,
        content_sha256=helpers.sha256_of_text(content),
        active=active,
    )
    db.add(doc)
    db.commit()
    return doc


# --- make_document_id ---

def test_make_document_id_basic():
    assert helpers.make_document_id("tutor_prompt", "2026-05-01") == "doc_tutor_prompt_2026-05-01"


def test_make_document_id_with_suffix():
    doc_id = helpers.make_document_id("tutor_spec", "2026-05-01_v2")
    assert doc_id == "doc_tutor_spec_2026-05-01_v2"


# --- make_version_key ---

def test_make_version_key_no_suffix():
    date = datetime.date(2026, 5, 1)
    assert helpers.make_version_key(date) == "2026-05-01"


def test_make_version_key_with_suffix():
    date = datetime.date(2026, 5, 1)
    assert helpers.make_version_key(date, suffix="v2") == "2026-05-01_v2"


def test_make_version_key_empty_suffix_treated_as_none():
    date = datetime.date(2026, 5, 1)
    assert helpers.make_version_key(date, suffix="") == "2026-05-01"


# --- sha256_of_text ---

def test_sha256_is_hex_string():
    h = helpers.sha256_of_text("hello")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_sha256_deterministic():
    assert helpers.sha256_of_text("hello") == helpers.sha256_of_text("hello")


def test_sha256_differs_for_different_text():
    assert helpers.sha256_of_text("hello") != helpers.sha256_of_text("world")


# --- parse_linked_documents ---

def test_parse_linked_documents_none():
    assert helpers.parse_linked_documents(None) == {}


def test_parse_linked_documents_empty_string():
    assert helpers.parse_linked_documents("") == {}


def test_parse_linked_documents_valid():
    js = json.dumps({"tutor_spec": "doc_tutor_spec_2026-05-01"})
    assert helpers.parse_linked_documents(js) == {"tutor_spec": "doc_tutor_spec_2026-05-01"}


# --- get_active_document / get_active_document_id ---

def test_get_active_document_returns_none_when_empty(db):
    assert helpers.get_active_document(db, "tutor_prompt") is None


def test_get_active_document_returns_active(db):
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", active=True)
    result = helpers.get_active_document(db, "tutor_prompt")
    assert result is not None
    assert result.document_id == doc.document_id


def test_get_active_document_ignores_inactive(db):
    _make_doc(db, "tutor_prompt", "2026-05-01", active=False)
    assert helpers.get_active_document(db, "tutor_prompt") is None


def test_get_active_document_id_returns_none_when_none(db):
    assert helpers.get_active_document_id(db, "tutor_prompt") is None


def test_get_active_document_id_returns_id(db):
    doc = _make_doc(db, "tutor_spec_contract", "2026-05-01", active=True)
    assert helpers.get_active_document_id(db, "tutor_spec_contract") == doc.document_id


# --- compatible_with_active_contracts ---

def test_compatible_no_contract_links(db):
    doc = _make_doc(db, "tutor_spec", "2026-05-01", active=True)
    assert helpers.compatible_with_active_contracts(doc, db) is True


def test_compatible_contract_matches_active(db):
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-01", active=True)
    backend_contract = _make_doc(db, "backend_contract", "2026-05-01", active=True)
    linked = {
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True, linked=linked)
    assert helpers.compatible_with_active_contracts(doc, db) is True


def test_compatible_contract_mismatch(db):
    _make_doc(db, "tutor_spec_contract", "2026-05-01", active=True)
    linked = {"tutor_spec_contract": "doc_tutor_spec_contract_old"}
    doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", linked=linked)
    assert helpers.compatible_with_active_contracts(doc, db) is False


def test_compatible_no_active_contract(db):
    linked = {"tutor_spec_contract": "doc_tutor_spec_contract_2026-05-01"}
    doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", linked=linked)
    assert helpers.compatible_with_active_contracts(doc, db) is False


# --- is_activatable ---

def _setup_full_active_contracts(db):
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-01", active=True)
    backend_contract = _make_doc(db, "backend_contract", "2026-05-01", active=True)
    return spec_contract, backend_contract


def _make_schema_doc(db, content=None):
    content = content or json.dumps({"type": "object"})
    return _make_doc(db, "tutor_artifact_schema", "2026-05-01", active=True, content=content)


def test_is_activatable_not_tutor_prompt(db):
    doc = _make_doc(db, "tutor_spec", "2026-05-01")
    ok, reasons = helpers.is_activatable(doc, db)
    assert not ok
    assert any("not a tutor_prompt" in r for r in reasons)


def test_is_activatable_missing_links(db):
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked={})
    ok, reasons = helpers.is_activatable(doc, db)
    assert not ok
    missing = [r for r in reasons if "missing required link" in r]
    assert len(missing) >= 5


def test_is_activatable_no_active_contracts(db):
    schema_doc = _make_schema_doc(db)
    spec_doc = _make_doc(db, "tutor_spec", "2026-05-01", active=True)
    gen_doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True)
    linked = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": gen_doc.document_id,
        "tutor_spec_contract": "doc_tutor_spec_contract_2026-05-01",
        "backend_contract": "doc_backend_contract_2026-05-01",
    }
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked=linked)
    ok, reasons = helpers.is_activatable(doc, db)
    assert not ok
    assert any("no active tutor_spec_contract" in r for r in reasons)
    assert any("no active backend_contract" in r for r in reasons)


def test_is_activatable_contract_mismatch(db):
    spec_contract = _make_doc(db, "tutor_spec_contract", "2026-05-01", active=True)
    backend_contract = _make_doc(db, "backend_contract", "2026-05-01", active=True)
    schema_doc = _make_schema_doc(db)
    spec_doc = _make_doc(db, "tutor_spec", "2026-05-01", active=True)
    gen_doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True)
    linked = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": gen_doc.document_id,
        "tutor_spec_contract": "doc_tutor_spec_contract_OLD",
        "backend_contract": backend_contract.document_id,
    }
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked=linked)
    ok, reasons = helpers.is_activatable(doc, db)
    assert not ok
    assert any("tutor_spec_contract" in r and "does not match active" in r for r in reasons)


def test_is_activatable_generator_contract_mismatch_names_documents(db):
    spec_contract, backend_contract = _setup_full_active_contracts(db)
    old_spec_contract = _make_doc(db, "tutor_spec_contract", "2026-04-01")
    schema_doc = _make_schema_doc(db)
    spec_doc = _make_doc(db, "tutor_spec", "2026-05-01", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    })
    gen_doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True, linked={
        "tutor_spec_contract": old_spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    })
    linked = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": gen_doc.document_id,
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked=linked)

    ok, reasons = helpers.is_activatable(doc, db)

    assert not ok
    assert any(gen_doc.document_id in r for r in reasons)
    assert any(old_spec_contract.document_id in r and spec_contract.document_id in r for r in reasons)


def test_is_activatable_linked_tutor_spec_not_found(db):
    spec_contract, backend_contract = _setup_full_active_contracts(db)
    schema_doc = _make_schema_doc(db)
    gen_doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    })
    linked = {
        "tutor_spec": "doc_tutor_spec_MISSING",
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": gen_doc.document_id,
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked=linked)
    ok, reasons = helpers.is_activatable(doc, db)
    assert not ok
    assert any("not found in archive" in r for r in reasons)


def test_is_activatable_invalid_schema_json(db):
    spec_contract, backend_contract = _setup_full_active_contracts(db)
    schema_doc = _make_doc(db, "tutor_artifact_schema", "2026-05-01", active=True, content="not json {{{")
    spec_doc = _make_doc(db, "tutor_spec", "2026-05-01", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
    })
    gen_doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    })
    linked = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": gen_doc.document_id,
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked=linked)
    ok, reasons = helpers.is_activatable(doc, db)
    assert not ok
    assert any("does not parse as valid JSON" in r for r in reasons)


def test_is_activatable_happy_path(db):
    spec_contract, backend_contract = _setup_full_active_contracts(db)
    schema_doc = _make_schema_doc(db)
    spec_doc = _make_doc(db, "tutor_spec", "2026-05-01", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
    })
    gen_doc = _make_doc(db, "tutor_generator_prompt", "2026-05-01", active=True, linked={
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    })
    linked = {
        "tutor_spec": spec_doc.document_id,
        "tutor_artifact_schema": schema_doc.document_id,
        "tutor_generator_prompt": gen_doc.document_id,
        "tutor_spec_contract": spec_contract.document_id,
        "backend_contract": backend_contract.document_id,
    }
    doc = _make_doc(db, "tutor_prompt", "2026-05-01", linked=linked)
    ok, reasons = helpers.is_activatable(doc, db)
    assert ok
    assert reasons == []
