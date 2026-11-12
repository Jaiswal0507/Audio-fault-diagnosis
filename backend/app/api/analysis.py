"""Analysis API Routes for MachineSense.

This module defines endpoints for ingesting machine audio recordings,
triggering DSP/ML diagnosis, persisting results, and returning analysis data.
Strict JWT Bearer authentication and multi-tenant organization isolation are enforced.
"""

import json
import logging
from pathlib import Path
import shutil
import soundfile as sf
import sys
import tempfile
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

# Support project root and backend directory import resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logger = logging.getLogger(__name__)

try:
    from backend.app.services.diagnosis_service import DiagnosisService
    from backend.app.database.database import get_db, init_db
    from backend.app.models.models import Machine, Analysis, User
    from backend.app.core.security import get_current_user
except ImportError:
    from app.services.diagnosis_service import DiagnosisService
    from app.database.database import get_db, init_db
    from app.models.models import Machine, Analysis, User
    from app.core.security import get_current_user

router = APIRouter(tags=["Analysis"])
diagnosis_service = DiagnosisService()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # Strict 10 MB limit
MAX_DURATION_SECONDS = 30.0  # Maximum audio length limit (seconds)


def _persist_analysis(db: Session, result: Dict[str, Any], organization_id: int) -> None:
    """Save analysis result to the database, auto-creating machine if needed, scoped by tenant organization."""
    try:
        machine_code = str(result.get("machine_id", "UNKNOWN")).strip()
        machine_type = str(result.get("machine_type", "bearing")).strip().lower()

        # Upsert machine record scoped by organization
        machine = (
            db.query(Machine)
            .filter(
                Machine.machine_code == machine_code,
                Machine.organization_id == organization_id,
            )
            .first()
        )
        if machine:
            if machine.machine_type.lower() != machine_type:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Machine type conflict: machine '{machine_code}' is registered as '{machine.machine_type}', but requested '{machine_type}'.",
                )
        else:
            machine = Machine(
                machine_code=machine_code,
                machine_type=machine_type,
                organization_id=organization_id,
            )
            db.add(machine)
            db.flush()

        # Create analysis record with non-null organization_id
        model_info = result.get("model", {})
        features = result.get("features", {})
        condition = result.get("status") or result.get("condition") or "normal"

        analysis = Analysis(
            analysis_id=result.get("analysis_id", ""),
            machine_code=machine_code,
            machine_type=machine_type,
            condition=condition,
            fault_type=result.get("fault_type"),
            score=float(result.get("score", 0.0)),
            model_name=model_info.get("name"),
            model_version=model_info.get("version"),
            features_json=json.dumps(features) if features else None,
            organization_id=organization_id,
        )
        db.add(analysis)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Database persistence failed for analysis %s: %s", result.get("analysis_id"), exc)
        raise exc


@router.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_audio(
    file: UploadFile = File(..., description="Acoustic recording file (.wav, .mp3, etc.)"),
    machine_id: str = Form(..., description="Unique machine identifier (e.g. 'MCH-001')"),
    machine_type: Optional[str] = Form(None, description="Optional machine type (e.g. 'bearing', 'pump')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ingest audio file, execute DSP extraction and ML inference, persist and return diagnosis report.

    Requires Bearer JWT authentication; analyses and machines are strictly scoped to the user's organization.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{ext}'. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # 1. Enforce strict 10 MB file size limit upfront if provided
    if file.size is not None and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowable limit of 10 MB ({file.size / (1024 * 1024):.2f} MB uploaded).",
        )

    # Secure temporary file creation with streaming size guard
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_path = Path(tmp_file.name)
            total_read = 0
            chunk_size = 1024 * 1024  # 1 MB chunk
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_read += len(chunk)
                if total_read > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size exceeds maximum allowable limit of 10 MB.",
                    )
                tmp_file.write(chunk)

        # 2. Enforce audio duration check (max 30.0 seconds)
        try:
            audio_info = sf.info(str(tmp_path))
            if audio_info.duration > MAX_DURATION_SECONDS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Audio duration ({audio_info.duration:.2f}s) exceeds maximum allowed limit of {MAX_DURATION_SECONDS} seconds.",
                )
        except HTTPException:
            raise
        except Exception:
            # Non-standard or corrupt audio headers fall through to DSP processing for accurate 422 reporting
            pass

        # Extract machine_type and execute diagnosis pipeline in background threadpool (prevent event loop blocking)
        raw_machine_type = (machine_type or "").strip()
        clean_machine_id = machine_id.strip() if machine_id else "MCH-001"

        # Explicitly check for machine_type conflict before running heavy ML pipeline
        existing_machine = (
            db.query(Machine)
            .filter(
                Machine.machine_code == clean_machine_id,
                Machine.organization_id == current_user.organization_id,
            )
            .first()
        )
        if existing_machine and raw_machine_type:
            if existing_machine.machine_type.lower() != raw_machine_type.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Machine type conflict: machine '{clean_machine_id}' is already registered as '{existing_machine.machine_type}', but requested '{raw_machine_type}'.",
                )
        try:
            result = await run_in_threadpool(
                diagnosis_service.analyze_audio,
                filepath=tmp_path,
                machine_type=raw_machine_type,
                machine_id=clean_machine_id,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Associate tenant organization metadata
        result["organization_id"] = current_user.organization_id

        # Persist analysis to database in background threadpool
        persisted = False
        try:
            await run_in_threadpool(
                _persist_analysis,
                db=db,
                result=result,
                organization_id=current_user.organization_id,
            )
            persisted = True
        except HTTPException:
            raise
        except Exception as db_err:
            logger.exception("Failed to persist analysis to database: %s", db_err)
            persisted = False

        result["persisted"] = persisted
        return result

    except HTTPException:
        raise

    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Audio processing error: {exc}")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal diagnosis engine error: {exc}"
        )
    finally:
        # Guarantee cleanup of temporary file
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
