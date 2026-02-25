"""
auth_routes.py
--------------
User and Admin authentication endpoints.

POST /signup       — Register a new user
POST /login        — Authenticate a user
POST /admin/signup — Register a new admin
POST /admin/login  — Authenticate an admin

Passwords are hashed with bcrypt. Plain-text passwords are never stored.
"""

import bcrypt
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from database import get_connection

router = APIRouter(tags=["Authentication"])


# ===========================================================================
#  PASSWORD HELPERS
# ===========================================================================

def _hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password (stored as UTF-8 string)."""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash.
    Returns False (instead of crashing) if the stored value is not a valid
    bcrypt hash — e.g. a legacy plain-text password from before this fix."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, Exception):
        return False


# ===========================================================================
#  PYDANTIC MODELS
# ===========================================================================

class UserSignupRequest(BaseModel):
    name:       str
    email:      EmailStr
    department: str = ""
    password:   str


class UserLoginRequest(BaseModel):
    email:    EmailStr
    password: str


class AdminSignupRequest(BaseModel):
    name:       str
    email:      EmailStr
    department: str = ""
    password:   str


class AdminLoginRequest(BaseModel):
    email:    EmailStr
    password: str


# ===========================================================================
#  USER ROUTES
# ===========================================================================

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def user_signup(body: UserSignupRequest):
    """
    Register a new employee (user) account.
    Passwords are hashed with bcrypt before being stored.
    """
    conn = get_connection()
    try:
        # Check for duplicate email
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (body.email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )

        now = datetime.utcnow().isoformat()
        hashed_pw = _hash_password(body.password)
        conn.execute(
            """
            INSERT INTO users (name, email, department, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.name, body.email, body.department, hashed_pw, now),
        )
        conn.commit()
        return {"message": "User registered successfully."}

    finally:
        conn.close()


@router.post("/login")
def user_login(body: UserLoginRequest):
    """
    Authenticate an employee. Returns basic user info on success.
    Password is verified against the stored bcrypt hash.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, email, department, password FROM users WHERE email = ?",
            (body.email,),
        ).fetchone()

        if not row or not _verify_password(body.password, row["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        return {
            "message": "Login successful.",
            "user": {
                "id":         row["id"],
                "name":       row["name"],
                "email":      row["email"],
                "department": row["department"],
            },
        }
    finally:
        conn.close()


# ===========================================================================
#  ADMIN ROUTES
# ===========================================================================

@router.post("/admin/signup", status_code=status.HTTP_201_CREATED)
def admin_signup(body: AdminSignupRequest):
    """Register a new support-engineer (admin) account. Password is bcrypt-hashed."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM admins WHERE email = ?", (body.email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Admin email already registered.",
            )

        hashed_pw = _hash_password(body.password)
        conn.execute(
            """
            INSERT INTO admins (name, email, department, password)
            VALUES (?, ?, ?, ?)
            """,
            (body.name, body.email, body.department, hashed_pw),
        )
        conn.commit()
        return {"message": "Admin registered successfully."}

    finally:
        conn.close()


@router.post("/admin/login")
def admin_login(body: AdminLoginRequest):
    """Authenticate a support engineer (admin). Verifies bcrypt password hash."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, email, department, password FROM admins WHERE email = ?",
            (body.email,),
        ).fetchone()

        if not row or not _verify_password(body.password, row["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials.",
            )

        return {
            "message": "Admin login successful.",
            "admin": {
                "id":         row["id"],
                "name":       row["name"],
                "email":      row["email"],
                "department": row["department"],
            },
        }
    finally:
        conn.close()
