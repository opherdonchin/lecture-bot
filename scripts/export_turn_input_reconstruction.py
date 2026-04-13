import argparse
import pathlib as pathlib_
import sys as sys_module

workspace_root = pathlib_.Path(__file__).parent.parent
sys_module.path.insert(0, str(workspace_root))

import app.db as db_module
from app.turn_reconstruction import export_session_turn_inputs_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Export per-turn tutor-input reconstruction for a session.")
    parser.add_argument("session_id", help="Session ID to reconstruct.")
    parser.add_argument(
        "--output",
        help="Output JSON path. Defaults to exports/session_<shortid>_turn_inputs.json",
    )
    args = parser.parse_args()

    short_id = args.session_id.split("-")[0]
    output = pathlib_.Path(args.output) if args.output else workspace_root / "exports" / f"session_{short_id}_turn_inputs.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    db = db_module.SessionLocal()
    try:
        export_session_turn_inputs_json(db, args.session_id, output)
    finally:
        db.close()

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
