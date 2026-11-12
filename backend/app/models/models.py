"""SQLAlchemy ORM Models for MachineSense Multi-Tenant Architecture.

Defines the Organization, User, Machine, and Analysis (AnalysisHistory) models
providing multi-tenant tenant isolation, identity authentication, and telemetry storage.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from sqlalchemy import Column, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, and_
from sqlalchemy.orm import relationship


def utc_now() -> datetime:
    """Return current UTC datetime (replaces deprecated utcnow)."""
    return datetime.now(timezone.utc)

# Support root directory resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.app.database.database import Base
except ImportError:
    try:
        from app.database.database import Base
    except ImportError:
        from ..database.database import Base


class Organization(Base):
    """Tenant organization entity isolating machines, users, and analysis history."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    machines = relationship("Machine", back_populates="organization")
    analyses = relationship("Analysis", back_populates="organization")

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        """Serialize organization to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    """User account entity associated with a tenant organization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationship back to tenant organization
    organization = relationship("Organization", back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

    def to_dict(self):
        """Serialize user to dictionary (excluding sensitive password hash)."""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "organization_id": self.organization_id,
            "organization_name": self.organization.name if self.organization else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Machine(Base):
    """Registered industrial machine entity scoped by tenant organization."""

    __tablename__ = "machines"
    __table_args__ = (
        UniqueConstraint("machine_code", "organization_id", name="uix_org_machine"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_code = Column(String(50), nullable=False, index=True)
    machine_type = Column(String(50), nullable=False, default="bearing")
    name = Column(String(100), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    analyses = relationship(
        "Analysis",
        back_populates="machine",
        lazy="dynamic",
        primaryjoin="and_(Machine.machine_code == Analysis.machine_code, Machine.organization_id == Analysis.organization_id)",
        overlaps="analyses,machine",
    )
    organization = relationship("Organization", back_populates="machines")

    def __repr__(self):
        return f"<Machine(code='{self.machine_code}', type='{self.machine_type}', org_id={self.organization_id})>"


class Analysis(Base):
    """Persisted diagnosis analysis record scoped by tenant organization."""

    __tablename__ = "analyses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["machine_code", "organization_id"],
            ["machines.machine_code", "machines.organization_id"],
            name="fk_analyses_machine_org",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String(20), unique=True, nullable=False, index=True)
    machine_code = Column(String(50), nullable=False, index=True)
    machine_type = Column(String(50), nullable=True)
    condition = Column(String(20), nullable=False)  # normal, anomaly, fault
    fault_type = Column(String(50), nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(20), nullable=True)
    features_json = Column(Text, nullable=True)  # JSON-serialized feature dict
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    machine = relationship(
        "Machine",
        back_populates="analyses",
        primaryjoin="and_(Analysis.machine_code == Machine.machine_code, Analysis.organization_id == Machine.organization_id)",
        foreign_keys=[machine_code, organization_id],
        overlaps="analyses,machine",
    )
    organization = relationship("Organization", back_populates="analyses", overlaps="analyses,machine")

    def __repr__(self):
        return f"<Analysis(id='{self.analysis_id}', condition='{self.condition}', score={self.score})>"

    def to_dict(self):
        """Serialize analysis record to dictionary with full telemetry metrics."""
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "machine_id": self.machine_code,
            "machine_type": self.machine_type,
            "condition": self.condition,
            "status": self.condition,  # Compatibility alias
            "fault_type": self.fault_type,
            "score": self.score,
            "organization_id": self.organization_id,
            "model": {
                "name": self.model_name,
                "version": self.model_version,
            },
            "features": json.loads(self.features_json) if self.features_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Compatibility alias for AnalysisHistory
AnalysisHistory = Analysis
