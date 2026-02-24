"""
auth_routes.py
--------------
User and Admin authentication endpoints.

POST /signup   — Register a new user
POST /login    — Authenticate a user
POST /admin/signup — Register a new admin
POST /admin/login  — Authenticate an admin
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from database import get_connection

router = APIRouter(tags=["Authentication"])


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
    Passwords are stored as plain text here; hash them in production.
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
        conn.execute(
            """
            INSERT INTO users (name, email, department, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.name, body.email, body.department, body.password, now),
        )
        conn.commit()
        return {"message": "User registered successfully."}

    finally:
        conn.close()


@router.post("/login")
def user_login(body: UserLoginRequest):
    """
    Authenticate an employee. Returns basic user info on success.
    In production, return a JWT token here.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, email, department FROM users WHERE email = ? AND password = ?",
            (body.email, body.password),
        ).fetchone()

        if not row:
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
    """Register a new support-engineer (admin) account."""
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

        conn.execute(
            """
            INSERT INTO admins (name, email, department, password)
            VALUES (?, ?, ?, ?)
            """,
            (body.name, body.email, body.department, body.password),
        )
        conn.commit()
        return {"message": "Admin registered successfully."}

    finally:
        conn.close()


@router.post("/admin/login")
def admin_login(body: AdminLoginRequest):
    """Authenticate a support engineer (admin)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, email, department FROM admins WHERE email = ? AND password = ?",
            (body.email, body.password),
        ).fetchone()

        if not row:
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
