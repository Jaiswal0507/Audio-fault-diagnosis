"""
Authentication & JWT helper functions for MachineSense backend.
Uses passlib (bcrypt) for password hashing and jose for JWT tokens.
"""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# Support root directory resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.app.database.database import get_db
    from backend.app.models.models import User
except ImportError:
    try:
        from app.database.database import get_db
        from app.models.models import User
    except ImportError:
        from ..database.database import get_db
        from ..models.models import User

from dotenv import load_dotenv

# Ensure .env is discovered across different execution working directories
for _candidate_dir in [Path.cwd(), PROJECT_ROOT, Path(__file__).resolve().parent.parent.parent]:
    _env_file = _candidate_dir / ".env"
    if _env_file.exists():
        load_dotenv(dotenv_path=_env_file)
        break
else:
    load_dotenv()

# Enforce strictly that secrets are loaded from environment / .env, never hardcoded in source
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY missing in environment variables.")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 bearer token extractor
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a salted bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate salted bcrypt hash from plain-text password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a cryptographically signed JWT access token.

    Args:
        data (Dict[str, Any]): Claims to encode into the token payload (e.g., 'sub', 'org_id').
        expires_delta (Optional[timedelta]): Custom token expiration duration.

    Returns:
        str: Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to extract and authenticate the current user from Bearer JWT.

    Args:
        token (str): JWT Bearer token supplied in Authorization header.
        db (Session): Database session.

    Returns:
        User: Authenticated User ORM entity.

    Raises:
        HTTPException: If token is invalid, expired, or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user

