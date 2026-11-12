"""
Authentication API endpoints: registration, login, and profile fetching.
"""

import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Support project root and backend directory import resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from backend.app.core.security import (
        create_access_token,
        get_current_user,
        get_password_hash,
        verify_password,
    )
    from backend.app.database.database import get_db
    from backend.app.models.models import Organization, User
except ImportError:
    from app.core.security import (
        create_access_token,
        get_current_user,
        get_password_hash,
        verify_password,
    )
    from app.database.database import get_db
    from app.models.models import Organization, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


# Pydantic request and response schemas

class RegisterRequest(BaseModel):
    """Payload schema for registering a new Organization and Admin User."""
    email: str
    password: str
    organization_name: str


class UserResponse(BaseModel):
    """Public user identity representation."""
    id: int
    email: str
    role: str
    organization_id: int
    organization_name: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Public organization entity representation."""
    id: int
    name: str


class TokenResponse(BaseModel):
    """Standard OAuth2 token response with tenant metadata."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterResponse(BaseModel):
    """Registration response returning created tenant, user, and access token."""
    message: str
    organization: OrganizationResponse
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


# Auth API endpoints

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Organization and Admin User",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Create a new tenant Organization and its primary administrator account.

    Args:
        payload (RegisterRequest): Registration details (email, password, organization_name).
        db (Session): Database session.

    Returns:
        RegisterResponse: Created tenant metadata and initial JWT access token.
    """
    clean_email = payload.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required.",
        )
    clean_org_name = payload.organization_name.strip()

    if not clean_org_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name is required.",
        )

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    try:
        # 1. Create Organization
        organization = Organization(name=clean_org_name)
        db.add(organization)
        db.flush()  # Populates organization.id

        # 2. Create Admin User
        hashed_pwd = get_password_hash(payload.password)
        user = User(
            email=clean_email,
            hashed_password=hashed_pwd,
            role="admin",
            organization_id=organization.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.refresh(organization)

        # 3. Generate initial JWT access token
        access_token = create_access_token(
            data={
                "sub": user.email,
                "org_id": organization.id,
                "role": user.role,
            }
        )

        return RegisterResponse(
            message="Organization and administrator account created successfully.",
            organization=OrganizationResponse(id=organization.id, name=organization.name),
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                organization_id=organization.id,
                organization_name=organization.name,
            ),
            access_token=access_token,
            token_type="bearer",
        )
    except Exception as exc:
        db.rollback()
        logger.error("Registration failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to a system error",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT access token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate credentials against user database and issue signed JWT.

    Args:
        form_data (OAuth2PasswordRequestForm): Form containing username (email) and password.
        db (Session): Database session.

    Returns:
        TokenResponse: Signed JWT access token and user metadata.
    """
    clean_email = (form_data.username or "").strip().lower()
    # print(f"Login attempt for: {clean_email}")
    user = db.query(User).filter(User.email == clean_email).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue JWT token
    access_token = create_access_token(
        data={
            "sub": user.email,
            "org_id": user.organization_id,
            "role": user.role,
        }
    )

    org_name = user.organization.name if user.organization else None

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            organization_id=user.organization_id,
            organization_name=org_name,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        organization_id=current_user.organization_id,
        organization_name=current_user.organization.name if current_user.organization else None,
    )

