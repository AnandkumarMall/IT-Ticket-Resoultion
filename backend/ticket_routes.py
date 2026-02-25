"""
ticket_routes.py
----------------
User-facing ticket endpoints.

POST   /tickets                   — Submit new ticket + get NLP suggestions
POST   /tickets/{id}/feedback     — Mark ticket as helpful or not
GET    /tickets/{id}              — View ticket details + status
GET    /tickets/{id}/resolutions  — All resolutions for a ticket
GET    /user/{user_id}/tickets    — All tickets submitted by a user
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from database import get_connection
from nlp_service import get_top_similar_tickets

router = APIRouter(tags=["Tickets"])


@router.get("/user/{user_id}/tickets")
def get_user_tickets(user_id: int):
    """Return all tickets for a given user, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        return {"tickets": [dict(r) for r in rows]}
    finally:
        conn.close()


# ===========================================================================
#  PYDANTIC MODELS
# ===========================================================================

class TicketCreateRequest(BaseModel):
    user_id:     int
    description: str
    category:    str = ""   # optional; NLP suggestions include detected category
    priority:    str = "Medium"


class FeedbackRequest(BaseModel):
    helpful: bool


# ===========================================================================
#  ROUTES
# ===========================================================================

@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(body: TicketCreateRequest):
    """
    1. Validate that user_id exists.
    2. Call NLP engine to get top-3 similar historical tickets.
    3. Store the new ticket (with top-match similarity score).
    4. Return the 3 suggestions + a friendly message.
    """
    conn = get_connection()
    try:
        # --- Validate user ------------------------------------------------
        user = conn.execute(
            "SELECT id FROM users WHERE id = ?", (body.user_id,)
        ).fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {body.user_id} not found.",
            )

        # --- Run NLP similarity -------------------------------------------
        suggestions = get_top_similar_tickets(body.description, top_k=3)

        # Extract top similarity score (may be 0.0 if no match found)
        top_score = suggestions[0]["similarity_score"] if suggestions else 0.0

        # Use category + priority from top suggestion if not provided
        detected_category = body.category or (
            suggestions[0]["category"] if suggestions else ""
        )
        detected_priority = body.priority or (
            suggestions[0]["priority"] if suggestions else "Medium"
        )

        # --- Persist ticket -----------------------------------------------
        now = datetime.utcnow().isoformat()
        cursor = conn.execute(
            """
            INSERT INTO tickets
                (user_id, description, category, priority, status,
                 similarity_score, created_at)
            VALUES (?, ?, ?, ?, 'Open', ?, ?)
            """,
            (
                body.user_id,
                body.description,
                detected_category,
                detected_priority,
                top_score,
                now,
            ),
        )
        conn.commit()
        ticket_id = cursor.lastrowid

        # --- Auto-save ALL NLP resolutions into RESOLUTIONS table ----------
        # Each suggestion becomes a resolution row so the text is visible
        # everywhere (Admin view, View Ticket, Analytics, etc.)
        for suggestion in suggestions:
            conn.execute(
                """
                INSERT INTO resolutions
                    (ticket_id, resolution_text, resolved_date)
                VALUES (?, ?, NULL)
                """,
                (ticket_id, suggestion["resolution"]),
            )
        conn.commit()

        return {
            "ticket_id": ticket_id,
            "message":   "Top 3 similar historical resolutions",
            "suggestions": suggestions,
        }

    finally:
        conn.close()


@router.post("/tickets/{ticket_id}/feedback")
def submit_feedback(ticket_id: int, body: FeedbackRequest):
    """
    Record user feedback for a ticket suggestion.

    helpful = true  → status = 'Resolved', helpful_count++
    helpful = false → status = 'Pending',  escalation_flag = 1, not_helpful_count++
    """
    conn = get_connection()
    try:
        # --- Validate ticket -----------------------------------------------
        ticket = conn.execute(
            "SELECT id FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found.",
            )

        if body.helpful:
            # Mark ticket resolved
            conn.execute(
                """
                UPDATE tickets
                SET feedback = 1, status = 'Resolved'
                WHERE id = ?
                """,
                (ticket_id,),
            )
            # Increment helpful_count in resolutions (if record exists)
            conn.execute(
                """
                UPDATE resolutions
                SET helpful_count = helpful_count + 1
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            )
            new_status = "Resolved"
            message = "Thank you! Ticket marked as resolved."

        else:
            # Escalate ticket
            conn.execute(
                """
                UPDATE tickets
                SET feedback = 0, status = 'Pending', escalation_flag = 1
                WHERE id = ?
                """,
                (ticket_id,),
            )
            # Increment not_helpful_count in resolutions (if record exists)
            conn.execute(
                """
                UPDATE resolutions
                SET not_helpful_count = not_helpful_count + 1
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            )
            new_status = "Pending"
            message = "Feedback recorded. Ticket escalated for manual review."

        conn.commit()
        return {
            "ticket_id": ticket_id,
            "status":    new_status,
            "message":   message,
        }

    finally:
        conn.close()


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    """
    Fetch full ticket details including any resolution record.
    """
    conn = get_connection()
    try:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found.",
            )

        resolution = conn.execute(
            "SELECT * FROM resolutions WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()

        return {
            "ticket": dict(ticket),
            "resolution": dict(resolution) if resolution else None,
        }

    finally:
        conn.close()


@router.get("/tickets/{ticket_id}/resolutions")
def get_ticket_resolutions(ticket_id: int):
    """
    Return ALL resolution rows for a ticket (NLP + manual).
    Used by the admin dashboard to preview existing suggestions.
    """
    conn = get_connection()
    try:
        ticket = conn.execute(
            "SELECT id FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found.",
            )

        rows = conn.execute(
            "SELECT resolution_text, resolved_date FROM resolutions WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()

        return {
            "ticket_id":   ticket_id,
            "resolutions": [dict(r) for r in rows],
        }

    finally:
        conn.close()
