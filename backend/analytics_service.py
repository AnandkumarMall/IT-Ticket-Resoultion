"""
analytics_service.py
---------------------
Reusable analytics helper functions for admin dashboard.
Uses raw sqlite3 queries only.
"""

from database import get_connection


def get_analytics() -> dict:
    """
    Compute and return admin analytics summary:
      - total_tickets
      - open_tickets
      - resolved_tickets
      - escalated_count
      - most_common_category
      - avg_resolution_time_hours  (from created_at to resolved_date in resolutions)
    """
    conn = get_connection()
    try:
        # --- Total tickets ------------------------------------------------
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]

        # --- Open tickets -------------------------------------------------
        open_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Open'"
        ).fetchone()[0]

        # --- Resolved tickets ---------------------------------------------
        resolved_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'"
        ).fetchone()[0]

        # --- Pending tickets ----------------------------------------------
        pending_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Pending'"
        ).fetchone()[0]

        # --- Escalated tickets -------------------------------------------
        escalated_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE escalation_flag = 1"
        ).fetchone()[0]

        # --- Most common category ----------------------------------------
        cat_row = conn.execute(
            """
            SELECT category, COUNT(*) AS cnt
            FROM tickets
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY cnt DESC
            LIMIT 1
            """
        ).fetchone()
        most_common_category = cat_row["category"] if cat_row else "N/A"

        # --- Average resolution time (hours) -----------------------------
        # Compare ticket created_at with resolution resolved_date
        avg_row = conn.execute(
            """
            SELECT AVG(
                (julianday(r.resolved_date) - julianday(t.created_at)) * 24
            ) AS avg_hours
            FROM resolutions r
            JOIN tickets t ON t.id = r.ticket_id
            WHERE r.resolved_date IS NOT NULL
            """
        ).fetchone()
        avg_resolution_hours = round(avg_row["avg_hours"], 2) if avg_row["avg_hours"] else 0.0

        return {
            "total_tickets":           total,
            "open_tickets":            open_count,
            "resolved_tickets":        resolved_count,
            "pending_tickets":         pending_count,
            "escalated_count":         escalated_count,
            "most_common_category":    most_common_category,
            "avg_resolution_time_hours": avg_resolution_hours,
        }

    finally:
        conn.close()
