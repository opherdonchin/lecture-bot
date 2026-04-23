import sys as sys_module
import pathlib as pathlib_

workspace_root = pathlib_.Path(__file__).parent.parent
sys_module.path.insert(0, str(workspace_root))

import app.db as db_module
import app.models  # noqa: F401 — registers all models with Base


def _ensure_sqlite_schema_updates() -> None:
    if not db_module.engine.url.drivername.startswith("sqlite"):
        return
    with db_module.engine.begin() as conn:
        session_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(sessions)").fetchall()
        }
        if "private_artifact_schema_json" not in session_columns:
            conn.exec_driver_sql(
                "ALTER TABLE sessions ADD COLUMN private_artifact_schema_json TEXT"
            )


if __name__ == "__main__":
    # Ensure data directory exists for SQLite database
    data_dir = workspace_root / "data"
    data_dir.mkdir(exist_ok=True)

    db_module.Base.metadata.create_all(bind=db_module.engine)
    _ensure_sqlite_schema_updates()
    print("Database initialized.")
