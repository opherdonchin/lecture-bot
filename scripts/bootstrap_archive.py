"""
Import current repo tutor documents into archive_documents.

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
import app.models as models  # noqa: F401


def _content_format(path: pathlib.Path) -> str:
    return "json" if path.suffix == ".json" else "markdown"


def _build_import_items(repo_root: pathlib.Path, version_key: str) -> list[dict]:
    docs_dir = repo_root / "docs"
    prompts_dir = repo_root / "prompts"
    candidates = [
        ("tutor_spec_contract", docs_dir / "tutor_specification_contract.md", "Tutor Specification Contract"),
        ("backend_contract", docs_dir / "backend_tutor_contract.md", "Backend-Tutor Runtime Contract"),
        ("tutor_generator_prompt", prompts_dir / "tutor_generator_prompt.md", "Tutor Generator Prompt"),
        ("tutor_spec", docs_dir / "tutor_specification.md", "Tutor Specification"),
        ("tutor_artifact_schema", prompts_dir / "tutor_prompt_private_artifact_schema.json", "Tutor Private Artifact Schema"),
        ("tutor_prompt", prompts_dir / "tutor_prompt.md", "Tutor Prompt"),
    ]

    items = []
    for document_type, source_path, title in candidates:
        if not source_path.exists():
            continue
        content_text = source_path.read_text(encoding="utf-8")
        items.append({
            "document_id": helpers.make_document_id(document_type, version_key),
            "document_type": document_type,
            "version_key": version_key,
            "title": title,
            "content_text": content_text,
            "content_format": _content_format(source_path),
            "content_sha256": helpers.sha256_of_text(content_text),
            "source_path": str(source_path),
        })
    return items


def _build_linked_documents(items: list[dict]) -> dict[str, str | None]:
    by_type = {item["document_type"]: item["document_id"] for item in items}
    result: dict[str, str | None] = {}
    for item in items:
        document_type = item["document_type"]
        links: dict[str, str] = {}
        if document_type == "tutor_prompt":
            for link_type in (
                "tutor_spec",
                "tutor_artifact_schema",
                "tutor_generator_prompt",
                "tutor_spec_contract",
                "backend_contract",
            ):
                if link_type in by_type:
                    links[link_type] = by_type[link_type]
        elif document_type == "tutor_spec" and "tutor_spec_contract" in by_type:
            links["tutor_spec_contract"] = by_type["tutor_spec_contract"]
        elif document_type == "tutor_generator_prompt":
            for link_type in ("tutor_spec_contract", "backend_contract"):
                if link_type in by_type:
                    links[link_type] = by_type[link_type]
        elif document_type == "tutor_artifact_schema" and "backend_contract" in by_type:
            links["backend_contract"] = by_type["backend_contract"]
        result[document_type] = json.dumps(links, ensure_ascii=False) if links else None
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
    if version_key is None:
        version_key = datetime.date.today().isoformat()

    items = _build_import_items(repo_root, version_key)
    linked_map = _build_linked_documents(items)
    imported: list[str] = []
    skipped: list[str] = []

    for item in items:
        item["linked_documents_json"] = linked_map.get(item["document_type"])
        document_type = item["document_type"]

        existing_by_id = db.get(models.ArchiveDocumentModel, item["document_id"])
        if existing_by_id is not None:
            skipped.append(existing_by_id.document_id)
            if not dry_run and not existing_by_id.active:
                _deactivate_type(db, document_type)
                existing_by_id.active = True
            continue

        existing = (
            db.query(models.ArchiveDocumentModel)
            .filter(
                models.ArchiveDocumentModel.document_type == document_type,
                models.ArchiveDocumentModel.content_sha256 == item["content_sha256"],
            )
            .first()
        )
        if existing is not None:
            skipped.append(existing.document_id)
            if not dry_run and not existing.active:
                _deactivate_type(db, document_type)
                existing.active = True
            continue

        if dry_run:
            imported.append(item["document_id"])
            continue

        _deactivate_type(db, document_type)
        db.add(models.ArchiveDocumentModel(
            document_id=item["document_id"],
            document_type=document_type,
            version_key=item["version_key"],
            title=item["title"],
            content_text=item["content_text"],
            content_format=item["content_format"],
            linked_documents_json=item["linked_documents_json"],
            content_sha256=item["content_sha256"],
            active=True,
            provenance_json=json.dumps({
                "source_path": item["source_path"],
                "bootstrap_version_key": version_key,
            }, ensure_ascii=False),
        ))
        imported.append(item["document_id"])

    if not dry_run:
        db.commit()
    return {"imported": imported, "skipped": skipped}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap archive_documents from current repo files.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--version-key", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_module.Base.metadata.create_all(bind=db_module.engine)
    db = db_module.SessionLocal()
    try:
        summary = bootstrap_archive(db, REPO_ROOT, version_key=args.version_key, dry_run=args.dry_run)
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
