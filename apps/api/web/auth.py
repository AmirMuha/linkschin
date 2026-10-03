"""Authentication and authorization utilities for operator endpoints."""

from __future__ import annotations

import os
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from passlib.context import CryptContext

import db

# Cryptographically random runtime secret if not explicitly configured in environment
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 86400  # 24 hours

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
security_bearer = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against argon2/bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash password using Argon2."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    """Generate signed JWT Bearer token."""
    to_encode = data.copy()
    expire = time.time() + expires_in
    to_encode.update({"exp": expire, "iat": time.time()})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_operator(username: str, password: str) -> dict | None:
    """Authenticate operator against SQLite operator_users table or explicit env credentials."""
    user = db.get_operator_user(username)
    if user:
        if verify_password(password, user["password_hash"]):
            return {"username": user["username"], "role": user["role"]}
        return None

    # Bootstrap operator from explicit environment variables only
    env_user = os.environ.get("OPERATOR_USERNAME")
    env_pass = os.environ.get("OPERATOR_PASSWORD")
    if env_user and env_pass and username == env_user and password == env_pass:
        hashed = hash_password(password)
        db.create_operator_user(username, hashed, role="admin")
        return {"username": username, "role": "admin"}

    return None


async def get_current_operator(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)]
) -> dict:
    """FastAPI dependency requiring valid operator JWT Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get_operator_user(username)
    if not user and username != DEFAULT_OPERATOR_USER:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"username": username, "role": payload.get("role", "operator")}
