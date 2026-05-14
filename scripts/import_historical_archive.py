"""
Import historical tutor prompt and tutor specification archives into archive_documents.

Idempotent: running more than once will not create duplicate rows.

Usage:
    python scripts/import_historical_archive.py
    python scripts/import_historical_archive.py --dry-run
    python scripts/import_historical_archive.py --repo-root /path/to/lecture-bot
"""
import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import sqlalchemy.orm as sqlalchemy_orm

import app.archive_helpers as helpers
import app.db as db_module
import app.models as models  # noqa: F401 - registers models with Base


ARCHIVE_SOURCES = (
    {
        "document_type": "tutor_prompt",
        "archive_dir": pathlib.Path("prompts/archive/tutor_prompts"),
        "history_file": "tutor_prompt_history.md",
        "title_prefix": "Tutor Prompt",
    },
    {
        "document_type": "tutor_spec",
        "archive_dir": pathlib.Path("docs/archive/tutor_specification"),
        "history_file": "tutor_specification_history.md",
        "title_prefix": "Tutor Specification",
    },
)


def _build_import_items(repo_root: pathlib.Path) -> list[dict]:
    items: list[dict] = []

    for source in ARCHIVE_SOURCES:
        archive_dir = repo_root / source["archive_dir"]
        if not archive_dir.exists():
            continue

        for source_path in sorted(archive_dir.glob("*.md")):
            if source_path.name == source["history_file"]:
                continue

            version_key = source_path.stem
            document_type = source["document_type"]
            content_text = source_path.read_text(encoding="utf-8")
            items.append({
                "document_id": helpers.make_document_id(document_type, version_key),
                "document_type": document_type,
                "version_key": version_key,
                "title": f"{source['title_prefix']} {version_key}",
                "content_text": content_text,
                "content_format": "markdown",
                "content_sha256": helpers.sha256_of_text(content_text),
                "source_path": str(source_path),
            })

    return items


def _existing_document_id(
    db: sqlalchemy_orm.Session,
    item: dict,
) -> str | None:
    existing_by_id = db.get(models.ArchiveDocumentModel, item["document_id"])
    if existing_by_id is not None:
        return existing_by_id.document_id

    existing_by_sha = (
        db.query(models.ArchiveDocumentModel)
        .filter(
            models.ArchiveDocumentModel.document_type == item["document_type"],
            models.ArchiveDocumentModel.content_sha256 == item["content_sha256"],
        )
        .order_by(models.ArchiveDocumentModel.active.desc(), models.ArchiveDocumentModel.created_at.desc())
        .first()
    )
    if existing_by_sha is not None:
        return existing_by_sha.document_id

    return None


def import_historical_archive(
    db: sqlalchemy_orm.Session,
    repo_root: pathlib.Path,
    dry_run: bool = False,
) -> dict:
    """
    Import historical archived tutor prompts and specs as inactive documents.

    Returns a summary dict with keys:
      - imported: list of document_ids newly inserted
      - skipped: list of document_ids already present or duplicated by content
    """
    items = _build_import_items(repo_root)

    imported: list[str] = []
    skipped: list[str] = []

    for item in items:
        existing_doc_id = _existing_document_id(db, item)
        if existing_doc_id is not None:
            skipped.append(existing_doc_id)
            continue

        doc_id = item["document_id"]
        if dry_run:
            imported.append(doc_id)
            continue

        provenance = {"source_path": item["source_path"], "historical_import": True}
        doc = models.ArchiveDocumentModel(
            document_id=doc_id,
            document_type=item["document_type"],
            version_key=item["version_key"],
            title=item["title"],
            content_text=item["content_text"],
            content_format=item["content_format"],
            linked_documents_json=None,
            content_sha256=item["content_sha256"],
            active=False,
            provenance_json=json.dumps(provenance, ensure_ascii=False),
        )
        db.add(doc)
        imported.append(doc_id)

    if not dry_run:
        db.commit()

    return {"imported": imported, "skipped": skipped}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import historical archive_documents from filesystem archives.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without writing.")
    parser.add_argument(
        "--repo-root",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="Override repository root (default: parent of this script's directory).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_module.Base.metadata.create_all(bind=db_module.engine)
    db = db_module.SessionLocal()
    try:
        summary = import_historical_archive(
            db,
            repo_root=args.repo_root.resolve(),
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
