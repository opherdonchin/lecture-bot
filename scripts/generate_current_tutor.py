"""
Generate a runtime tutor prompt from docs/tutor_specification.md.

By default this records generated documents in the archive but leaves the live
runtime files unchanged. Pass --activate to replace the current tutor prompt,
private artifact schema, and tutor specification after generation succeeds.
"""
import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app.admin_generation as admin_generation
import app.db as db_module
import app.models  # noqa: F401
from scripts.bootstrap_archive import bootstrap_archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a tutor prompt from the current tutor specification.")
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Replace the live tutor prompt/schema/spec if generation and validation succeed.",
    )
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Do not first import current repo documents into archive_documents.",
    )
    parser.add_argument(
        "--spec-title",
        default="Current Tutor Specification",
        help="Title to store for the generated tutor specification archive document.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_module.Base.metadata.create_all(bind=db_module.engine)
    db = db_module.SessionLocal()
    try:
        bootstrap_summary = None
        if not args.no_bootstrap:
            bootstrap_summary = bootstrap_archive(db, REPO_ROOT)
        result = admin_generation.run_generation_from_current_spec(
            db,
            repo_root=REPO_ROOT,
            spec_title=args.spec_title,
            activate=args.activate,
        )
    finally:
        db.close()

    if bootstrap_summary is not None:
        print("Bootstrap:")
        print(json.dumps(bootstrap_summary, indent=2))
    print("Generation:")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
