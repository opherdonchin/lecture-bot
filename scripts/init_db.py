import sys as sys_module
import pathlib as pathlib_

workspace_root = pathlib_.Path(__file__).parent.parent
sys_module.path.insert(0, str(workspace_root))

import app.db as db_module
import app.models  # noqa: F401 — registers all models with Base

if __name__ == "__main__":
    # Ensure data directory exists for SQLite database
    data_dir = workspace_root / "data"
    data_dir.mkdir(exist_ok=True)

    db_module.Base.metadata.create_all(bind=db_module.engine)
    print("Database initialized.")