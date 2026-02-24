"""
main.py
-------
FastAPI application entry point for the IT Ticket Resolution Suggestion Engine.

Registers all routers, enables CORS, and initialises the SQLite database
on startup.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from auth_routes import router as auth_router
from ticket_routes import router as ticket_router
from admin_routes import router as admin_router

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="IT Ticket Resolution Suggestion Engine",
    description=(
        "Sprint 2 Backend: NLP-powered ticket resolution suggestions, "
        "feedback loop, admin management & analytics. "
        "No LLM — pure TF-IDF cosine similarity."
    ),
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins during development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Restrict to specific frontend origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database initialisation — runs once at startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()
    print("[APP] Application started. Database ready.")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)    # /signup, /login, /admin/signup, /admin/login
app.include_router(ticket_router)  # /tickets, /tickets/{id}, /tickets/{id}/feedback
app.include_router(admin_router)   # /admin/tickets, /admin/escalated, /admin/analytics ...


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "IT Ticket Resolution Suggestion Engine",
        "version": "2.0.0",
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
