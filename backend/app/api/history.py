"""History API Routes for MachineSense.

Provides endpoints for querying past analysis records by machine with
strict multi-tenant data isolation scoped to the authenticated organization.
"""

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

# Support project root and backend directory import resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from backend.app.database.database import get_db, init_db
    from backend.app.models.models import Analysis, Machine, User
    from backend.app.core.security import get_current_user
except ImportError:
    from app.database.database import get_db, init_db
    from app.models.models import Analysis, Machine, User
    from app.core.security import get_current_user

router = APIRouter(tags=["History"])


@router.get("/machines/{machine_id}/history")
def get_machine_history(
    machine_id: str,
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch past analyses for a specific machine, strictly scoped to the user's tenant organization.

    Args:
        machine_id (str): Machine identifier to filter by (case-insensitive).
        limit (int): Maximum number of records to return (default: 50).
        offset (int): Pagination offset (default: 0).
        current_user (User): Authenticated user dependency.
        db (Session): Database session.

    Returns:
        Dict containing machine_id, total count, organization_id, and list of analysis records.
    """
    clean_id = (machine_id or "").strip()

    # Query analyses for this machine, filtered strictly by organization_id
    query = (
        db.query(Analysis)
        .filter(
            func.lower(Analysis.machine_code) == clean_id.lower(),
            Analysis.organization_id == current_user.organization_id,
        )
        .order_by(Analysis.created_at.desc())
    )

    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return {
        "machine_id": clean_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "organization_id": current_user.organization_id,
        "analyses": [record.to_dict() for record in records],
    }


@router.get("/history")
def get_all_history(
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    condition: Optional[str] = Query(None, description="Filter by condition (normal, anomaly, fault)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch all analysis records strictly scoped to the user's tenant organization.

    Args:
        limit (int): Maximum number of records.
        offset (int): Pagination offset.
        condition (Optional[str]): Filter by diagnosis condition.
        current_user (User): Authenticated user dependency.
        db (Session): Database session.

    Returns:
        Dict containing total count, organization_id, and list of analysis records.
    """
    query = (
        db.query(Analysis)
        .filter(Analysis.organization_id == current_user.organization_id)
        .order_by(Analysis.created_at.desc())
    )

    if condition and condition.strip():
        query = query.filter(func.lower(Analysis.condition) == condition.strip().lower())

    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "organization_id": current_user.organization_id,
        "analyses": [record.to_dict() for record in records],
    }


@router.get("/machines")
def list_machines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List registered machines strictly scoped to the user's tenant organization with analysis counts."""
    machines = (
        db.query(Machine)
        .filter(Machine.organization_id == current_user.organization_id)
        .order_by(Machine.created_at.desc())
        .all()
    )
    result = []
    for m in machines:
        analysis_count = (
            db.query(Analysis)
            .filter(
                Analysis.machine_code == m.machine_code,
                Analysis.organization_id == current_user.organization_id,
            )
            .count()
        )
        latest_analysis = (
            db.query(Analysis)
            .filter(
                Analysis.machine_code == m.machine_code,
                Analysis.organization_id == current_user.organization_id,
            )
            .order_by(Analysis.created_at.desc())
            .first()
        )
        result.append({
            "machine_code": m.machine_code,
            "machine_type": m.machine_type,
            "name": m.name,
            "analysis_count": analysis_count,
            "latest_condition": latest_analysis.condition if latest_analysis else "unknown",
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    return {
        "total": len(result),
        "organization_id": current_user.organization_id,
        "machines": result,
    }
