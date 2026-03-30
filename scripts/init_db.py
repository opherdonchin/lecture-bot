import sys
from pathlib import Path

# Add parent directory to path so we can import app module
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))

from app.db import Base, engine

if __name__ == "__main__":
    # Ensure data directory exists for SQLite database
    data_dir = workspace_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")