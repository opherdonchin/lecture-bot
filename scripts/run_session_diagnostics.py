import argparse
import pathlib as pathlib_
import sys as sys_module

workspace_root = pathlib_.Path(__file__).parent.parent
sys_module.path.insert(0, str(workspace_root))

import app.db as db_module
from app.diagnostics import export_session_diagnostics, render_markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run diagnostics on one or more stored sessions.")
    parser.add_argument("session_ids", nargs="+", help="One or more session IDs to diagnose.")
    parser.add_argument(
        "--output-dir",
        help="Directory for JSON and markdown reports. Defaults to exports/diagnostics.",
    )
    args = parser.parse_args()

    output_dir = pathlib_.Path(args.output_dir) if args.output_dir else workspace_root / "exports" / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)

    db = db_module.SessionLocal()
    try:
        for session_id in args.session_ids:
            short_id = session_id.split("-")[0]
            json_path = output_dir / f"session_{short_id}_diagnostics.json"
            md_path = output_dir / f"session_{short_id}_diagnostics.md"
            report = export_session_diagnostics(
                db,
                session_id,
                output_json=json_path,
                output_markdown=md_path,
            )
            print(render_markdown_report(report))
            print(f"Wrote {json_path}")
            print(f"Wrote {md_path}")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
