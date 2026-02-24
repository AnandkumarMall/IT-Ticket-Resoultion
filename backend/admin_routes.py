"""
admin_routes.py
---------------
Admin (Support Engineer) facing endpoints.

GET  /admin/tickets           — View all tickets
GET  /admin/escalated         — View escalated tickets
PUT  /admin/tickets/{id}      — Update ticket status
POST /admin/resolution        — Add manual resolution to a ticket
GET  /admin/analytics         — Dashboard analytics
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from database import get_connection
from analytics_service import get_analytics

router = APIRouter(prefix="/admin", tags=["Admin"])


# ===========================================================================
#  PYDANTIC MODELS
# ===========================================================================

class TicketStatusUpdate(BaseModel):
    status: str  # "In Progress" | "Resolved" | "Closed"


class ResolutionCreateRequest(BaseModel):
    ticket_id:       int
    resolution_text: str
    resolved_date:   Optional[str] = None  # ISO string; defaults to now


# ===========================================================================
#  ROUTES
# ===========================================================================

@router.get("/tickets")
def get_all_tickets():
    """Return all tickets ordered by creation date (newest first)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC"
        ).fetchall()
        return {"tickets": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/escalated")
def get_escalated_tickets():
    """Return all tickets flagged for escalation (escalation_flag = 1)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM tickets
            WHERE escalation_flag = 1
            ORDER BY created_at DESC
            """
        ).fetchall()
        return {"escalated_tickets": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.put("/tickets/{ticket_id}")
def update_ticket_status(ticket_id: int, body: TicketStatusUpdate):
    """
    Admin updates the ticket status.
    Allowed values: 'In Progress', 'Resolved', 'Closed'
    """
    allowed = {"In Progress", "Resolved", "Closed", "Open", "Pending"}
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status must be one of: {', '.join(allowed)}",
        )

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

        conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (body.status, ticket_id),
        )
        conn.commit()
        return {
            "ticket_id": ticket_id,
            "new_status": body.status,
            "message":   "Ticket status updated successfully.",
        }
    finally:
        conn.close()


@router.post("/resolution", status_code=status.HTTP_201_CREATED)
def add_resolution(body: ResolutionCreateRequest):
    """
    Admin manually adds a resolution for a ticket.
    Inserts into the RESOLUTIONS table and marks ticket as 'Resolved'.
    """
    conn = get_connection()
    try:
        # Validate ticket existence
        ticket = conn.execute(
            "SELECT id FROM tickets WHERE id = ?", (body.ticket_id,)
        ).fetchone()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {body.ticket_id} not found.",
            )

        resolved_date = body.resolved_date or datetime.utcnow().isoformat()

        # Insert resolution record
        conn.execute(
            """
            INSERT INTO resolutions (ticket_id, resolution_text, resolved_date)
            VALUES (?, ?, ?)
            """,
            (body.ticket_id, body.resolution_text, resolved_date),
        )

        # Automatically mark the ticket as Resolved
        conn.execute(
            "UPDATE tickets SET status = 'Resolved' WHERE id = ?",
            (body.ticket_id,),
        )

        conn.commit()
        return {
            "message":   "Resolution added and ticket marked as Resolved.",
            "ticket_id": body.ticket_id,
        }
    finally:
        conn.close()


@router.get("/analytics")
def admin_analytics():
    """
    Returns aggregated analytics for the admin dashboard:
    - Total tickets, Open vs Resolved, Most common category,
      Escalation count, Average resolution time.
    """
    data = get_analytics()
    return {"analytics": data}
