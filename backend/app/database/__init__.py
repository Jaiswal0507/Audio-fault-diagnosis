"""Database Module for MachineSense.

Exports SQLAlchemy engine, Base, SessionLocal, get_db dependency, and init_db.
"""

from pathlib import Path
import sys

# Support root directory resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.app.database.database import Base, SessionLocal, engine, get_db, init_db
except ImportError:
    try:
        from app.database.database import Base, SessionLocal, engine, get_db, init_db
    except ImportError:
        from .database import Base, SessionLocal, engine, get_db, init_db

__all__ = ["Base", "SessionLocal", "engine", "get_db", "init_db"]
