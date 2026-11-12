"""Database Configuration for MachineSense.

Configures SQLAlchemy engine and session factory with support for
environment-driven DATABASE_URL (e.g., PostgreSQL for production/multi-tenant)
and automatic fallback to local SQLite for zero-config development.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from .env file if present
load_dotenv()

# Project root and database directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Read DATABASE_URL with fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.strip():
    DATABASE_URL = "sqlite:///./sql_app.db"

# Handle legacy 'postgres://' URLs provided by Heroku/Render/AWS
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite requires check_same_thread=False when used with FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


Base = declarative_base()


def init_db():
    """Create all database tables if they don't already exist and ensure schema integrity.

    Ensures ORM models (Organization, User, Machine, Analysis) are registered on Base.metadata.
    """
    try:
        from backend.app.models.models import Organization, User, Machine, Analysis  # noqa: F401
    except ImportError:
        try:
            from app.models.models import Organization, User, Machine, Analysis  # noqa: F401
        except ImportError:
            from ..models.models import Organization, User, Machine, Analysis  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # SQLite schema migration helper: safely ensure organization_id and composite foreign keys
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            for table_name in ["machines", "analyses"]:
                try:
                    res = conn.execute(text(f"PRAGMA table_info({table_name});")).fetchall()
                    col_names = [row[1] for row in res]
                    if col_names and "organization_id" not in col_names:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN organization_id INTEGER;"))
                        conn.commit()
                except Exception:
                    pass

            # Ensure analyses table uses composite foreign key (machine_code, organization_id)
            try:
                res = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='analyses';")).fetchone()
                if res and 'FOREIGN KEY(machine_code) REFERENCES machines (machine_code)' in res[0]:
                    conn.execute(text("PRAGMA foreign_keys = OFF;"))
                    conn.execute(text("ALTER TABLE analyses RENAME TO analyses_old;"))
                    for idx in ["ix_analyses_analysis_id", "ix_analyses_machine_code", "ix_analyses_organization_id", "ix_analyses_created_at"]:
                        try:
                            conn.execute(text(f"DROP INDEX IF EXISTS {idx};"))
                        except Exception:
                            pass
                    conn.execute(text("""
                        CREATE TABLE analyses (
                            id INTEGER NOT NULL, 
                            analysis_id VARCHAR(20) NOT NULL, 
                            machine_code VARCHAR(50) NOT NULL, 
                            machine_type VARCHAR(50), 
                            condition VARCHAR(20) NOT NULL, 
                            fault_type VARCHAR(50), 
                            score FLOAT NOT NULL, 
                            model_name VARCHAR(100), 
                            model_version VARCHAR(20), 
                            features_json TEXT, 
                            organization_id INTEGER NOT NULL, 
                            created_at DATETIME, 
                            PRIMARY KEY (id), 
                            FOREIGN KEY(organization_id) REFERENCES organizations (id),
                            FOREIGN KEY(machine_code, organization_id) REFERENCES machines (machine_code, organization_id)
                        );
                    """))
                    conn.execute(text("CREATE UNIQUE INDEX ix_analyses_analysis_id ON analyses (analysis_id);"))
                    conn.execute(text("CREATE INDEX ix_analyses_machine_code ON analyses (machine_code);"))
                    conn.execute(text("CREATE INDEX ix_analyses_organization_id ON analyses (organization_id);"))
                    conn.execute(text("CREATE INDEX ix_analyses_created_at ON analyses (created_at);"))
                    conn.execute(text("""
                        INSERT OR IGNORE INTO analyses (id, analysis_id, machine_code, machine_type, condition, fault_type, score, model_name, model_version, features_json, organization_id, created_at)
                        SELECT id, analysis_id, machine_code, machine_type, condition, fault_type, score, model_name, model_version, features_json, organization_id, created_at FROM analyses_old;
                    """))
                    conn.execute(text("DROP TABLE analyses_old;"))
                    conn.commit()
            except Exception:
                pass


def get_db():
    """FastAPI dependency yielding an isolated database session with guaranteed closure.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
