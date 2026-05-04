"""
One-time script to import current repo files into archive_documents.

Idempotent: running more than once will not create duplicate rows.
Not a permanent admin button — run from the CLI after init_db.py.

Usage:
    python scripts/bootstrap_archive.py
    python scripts/bootstrap_archive.py --dry-run
"""
import argparse
import datetime
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import sqlalchemy.orm as sqlalchemy_orm

import app.archive_helpers as helpers
import app.db as db_module
import app.models as models  # noqa: F401 — registers models with Base


DOCS_DIR = REPO_ROOT / "docs"
PROMPTS_DIR = REPO_ROOT / "prompts"


def _content_format(path: pathlib.Path) -> str:
    return "json" if path.suffix == ".json" else "markdown"


def _build_import_items(
    repo_root: pathlib.Path,
    version_key: str,
) -> list[dict]:
    docs_dir = repo_root / "docs"
    prompts_dir = repo_root / "prompts"

    candidates = [
        {
            "document_type": "tutor_spec_contract",
            "source_path": docs_dir / "tutor_specification_contract.md",
            "title": "Tutor Specification Contract",
        },
        {
            "document_type": "backend_contract",
            "source_path": docs_dir / "backend_tutor_contract.md",
            "title": "Backend–Tutor Runtime Contract",
        },
        {
            "document_type": "tutor_generator_prompt",
            "source_path": prompts_dir / "tutor_generator_prompt.md",
            "title": "Tutor Generator Prompt",
        },
        {
            "document_type": "tutor_spec",
            "source_path": docs_dir / "tutor_specification.md",
            "title": "Tutor Specification",
        },
        {
            "document_type": "tutor_artifact_schema",
            "source_path": prompts_dir / "tutor_prompt_private_artifact_schema.json",
            "title": "Tutor Private Artifact Schema",
        },
        {
            "document_type": "tutor_prompt",
            "source_path": prompts_dir / "tutor_prompt.md",
            "title": "Tutor Prompt",
        },
        {
            "document_type": "spec_repair_prompt",
            "source_path": prompts_dir / "spec_repair_prompt.md",
            "title": "Spec Repair Prompt",
        },
    ]

    items = []
    for c in candidates:
        source_path: pathlib.Path = c["source_path"]
        if not source_path.exists():
            continue
        content_text = source_path.read_text(encoding="utf-8")
        document_type = c["document_type"]
        doc_id = helpers.make_document_id(document_type, version_key)
        items.append({
            "document_id": doc_id,
            "document_type": document_type,
            "version_key": version_key,
            "title": c["title"],
            "content_text": content_text,
            "content_format": _content_format(source_path),
            "content_sha256": helpers.sha256_of_text(content_text),
            "source_path": str(source_path),
        })
    return items


def _build_linked_documents(items: list[dict]) -> dict[str, str | None]:
    """
    Return a mapping of document_type -> linked_documents_json string (or None).
    """
    by_type = {item["document_type"]: item["document_id"] for item in items}

    result: dict[str, str | None] = {}
    for item in items:
        dt = item["document_type"]
        links: dict[str, str] = {}

        if dt == "tutor_prompt":
            for link_type in ("tutor_spec", "tutor_artifact_schema", "tutor_generator_prompt",
                              "tutor_spec_contract", "backend_contract"):
                if link_type in by_type:
                    links[link_type] = by_type[link_type]

        elif dt == "tutor_spec":
            if "tutor_spec_contract" in by_type:
                links["tutor_spec_contract"] = by_type["tutor_spec_contract"]

        elif dt in ("tutor_generator_prompt", "spec_repair_prompt"):
            for link_type in ("tutor_spec_contract", "backend_contract"):
                if link_type in by_type:
                    links[link_type] = by_type[link_type]

        elif dt == "tutor_artifact_schema":
            if "backend_contract" in by_type:
                links["backend_contract"] = by_type["backend_contract"]

        result[dt] = json.dumps(links, ensure_ascii=False) if links else None

    return result


def _deactivate_type(db: sqlalchemy_orm.Session, document_type: str) -> None:
    db.query(models.ArchiveDocumentModel).filter(
        models.ArchiveDocumentModel.document_type == document_type,
        models.ArchiveDocumentModel.active.is_(True),
    ).update({"active": False})


def bootstrap_archive(
    db: sqlalchemy_orm.Session,
    repo_root: pathlib.Path,
    version_key: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Import current repo files into archive_documents. Idempotent.

    Returns a summary dict with keys:
      - imported: list of document_ids newly inserted
      - skipped: list of document_ids already present
    """
    if version_key is None:
        version_key = datetime.date.today().isoformat()

    items = _build_import_items(repo_root, version_key)
    linked_map = _build_linked_documents(items)

    for item in items:
        item["linked_documents_json"] = linked_map.get(item["document_type"])

    imported: list[str] = []
    skipped: list[str] = []

    for item in items:
        doc_id = item["document_id"]
        document_type = item["document_type"]

        existing_by_id = db.get(models.ArchiveDocumentModel, doc_id)
        if existing_by_id is not None:
            skipped.append(doc_id)
            if not dry_run and not existing_by_id.active:
                _deactivate_type(db, document_type)
                existing_by_id.active = True
            continue

        existing_by_sha = (
            db.query(models.ArchiveDocumentModel)
            .filter(
                models.ArchiveDocumentModel.document_type == document_type,
                models.ArchiveDocumentModel.content_sha256 == item["content_sha256"],
            )
            .first()
        )
        if existing_by_sha is not None:
            skipped.append(existing_by_sha.document_id)
            if not dry_run and not existing_by_sha.active:
                _deactivate_type(db, document_type)
                existing_by_sha.active = True
            continue

        if dry_run:
            imported.append(doc_id)
            continue

        provenance = {"source_path": item["source_path"], "bootstrap_version_key": version_key}
        _deactivate_type(db, document_type)
        doc = models.ArchiveDocumentModel(
            document_id=doc_id,
            document_type=document_type,
            version_key=item["version_key"],
            title=item["title"],
            content_text=item["content_text"],
            content_format=item["content_format"],
            linked_documents_json=item["linked_documents_json"],
            content_sha256=item["content_sha256"],
            active=True,
            provenance_json=json.dumps(provenance, ensure_ascii=False),
        )
        db.add(doc)
        imported.append(doc_id)

    if not dry_run:
        db.commit()

    return {"imported": imported, "skipped": skipped}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap archive_documents from current repo files.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without writing.")
    parser.add_argument("--version-key", default=None, help="Override version key (default: today's date).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = db_module.SessionLocal()
    try:
        summary = bootstrap_archive(
            db,
            repo_root=REPO_ROOT,
            version_key=args.version_key,
            dry_run=args.dry_run,
        )
    finally:
        db.close()

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}Imported ({len(summary['imported'])}):")
    for doc_id in summary["imported"]:
        print(f"  + {doc_id}")
    print(f"{prefix}Skipped ({len(summary['skipped'])}):")
    for doc_id in summary["skipped"]:
        print(f"  = {doc_id}")


if __name__ == "__main__":
    main()
