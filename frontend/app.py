"""
app.py
------
Flask frontend for the IT Ticket Resolution Suggestion Engine.
Connects to the FastAPI backend at http://localhost:8000.

Roles:
  User  → Raise tickets, view AI suggestions, give feedback, check status
  Admin → View all/escalated tickets, add resolutions, view analytics

Run with:
    python app.py
"""

import requests
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)

app = Flask(__name__)
app.secret_key = "it_ticket_engine_secret_key_2024"

BASE_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def api_post(endpoint: str, payload: dict):
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=10)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to backend (FastAPI not running on port 8000)."}, 503
    except Exception as e:
        return {"detail": str(e)}, 500


def api_get(endpoint: str):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to backend (FastAPI not running on port 8000)."}, 503
    except Exception as e:
        return {"detail": str(e)}, 500


def api_put(endpoint: str, payload: dict):
    try:
        r = requests.put(f"{BASE_URL}{endpoint}", json=payload, timeout=10)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to backend (FastAPI not running on port 8000)."}, 503
    except Exception as e:
        return {"detail": str(e)}, 500


def login_required(role=None):
    """Check session for login + optional role."""
    if not session.get("logged_in"):
        flash("Please log in to continue.", "warning")
        return redirect(url_for("login"))
    if role and session.get("role") != role:
        flash(f"Access denied. {role} account required.", "danger")
        return redirect(url_for("index"))
    return None


# ---------------------------------------------------------------------------
# PUBLIC ROUTES
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard") if session.get("role") == "User" else url_for("admin"))

    if request.method == "POST":
        action = request.form.get("action")  # "login" or "signup"
        role   = request.form.get("role", "User")  # "User" or "Admin"

        if action == "login":
            email    = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            if not email or not password:
                flash("Please fill in all fields.", "warning")
                return render_template("login.html")

            endpoint = "/login" if role == "User" else "/admin/login"
            resp, code = api_post(endpoint, {"email": email, "password": password})

            if code == 200:
                profile = resp.get("user") or resp.get("admin", {})
                session["logged_in"]  = True
                session["role"]       = role
                session["user_id"]    = profile.get("id")
                session["user_name"]  = profile.get("name", "Unknown")
                session["user_email"] = profile.get("email", email)
                flash(f"Welcome back, {session['user_name']}! 👋", "success")
                return redirect(url_for("dashboard") if role == "User" else url_for("admin"))
            else:
                flash(resp.get("detail", "Login failed."), "danger")

        elif action == "signup":
            name       = request.form.get("name", "").strip()
            email_s    = request.form.get("signup_email", "").strip()
            department = request.form.get("department", "").strip()
            password_s = request.form.get("signup_password", "").strip()
            confirm    = request.form.get("confirm_password", "").strip()

            if not all([name, email_s, password_s, confirm]):
                flash("Please fill in all required fields.", "warning")
            elif password_s != confirm:
                flash("Passwords do not match.", "danger")
            else:
                endpoint = "/signup" if role == "User" else "/admin/signup"
                payload  = {"name": name, "email": email_s,
                             "department": department, "password": password_s}
                resp, code = api_post(endpoint, payload)
                if code == 201:
                    flash("Account created! Please log in.", "success")
                else:
                    flash(resp.get("detail", "Signup failed."), "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# USER ROUTES
# ---------------------------------------------------------------------------

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    guard = login_required(role="User")
    if guard:
        return guard

    suggestions    = session.pop("suggestions", [])
    last_ticket_id = session.pop("last_ticket_id", None)
    feedback_done  = session.pop("feedback_done", False)

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        category    = request.form.get("category", "Other")
        priority    = request.form.get("priority", "Medium")

        if not description:
            flash("Please describe your issue before submitting.", "warning")
        else:
            payload = {
                "user_id":     session["user_id"],
                "description": description,
                "category":    category,
                "priority":    priority,
            }
            resp, code = api_post("/tickets", payload)
            if code == 201:
                session["last_ticket_id"] = resp["ticket_id"]
                session["suggestions"]    = resp.get("suggestions", [])
                session["feedback_done"]  = False
                flash(f"Ticket #{resp['ticket_id']} created! Here are your AI suggestions.", "success")
            else:
                flash(resp.get("detail", "Failed to create ticket."), "danger")
        return redirect(url_for("dashboard"))

    # Fetch all tickets for this user (for status tab list)
    ut_resp, _ = api_get(f"/user/{session['user_id']}/tickets")
    user_tickets = ut_resp.get("tickets", []) if isinstance(ut_resp, dict) else []

    return render_template(

        "dashboard_user.html",
        suggestions=suggestions,
        last_ticket_id=last_ticket_id,
        feedback_done=feedback_done,
        user_tickets=user_tickets,
        categories=["Network", "Hardware", "Software", "Email",
                    "VPN", "Printer", "Access", "Security", "Other"],
        priorities=["Low", "Medium", "High"],
    )


@app.route("/feedback/<int:ticket_id>", methods=["POST"])
def feedback(ticket_id):
    guard = login_required(role="User")
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    helpful = request.json.get("helpful", True)
    resp, code = api_post(f"/tickets/{ticket_id}/feedback", {"helpful": helpful})
    if code == 200:
        session["feedback_done"] = True
        return jsonify({"ok": True, "message": resp.get("message", ""), "status": resp.get("status", "")})
    return jsonify({"ok": False, "error": resp.get("detail", "Error")}), code


@app.route("/ticket/<int:ticket_id>")
def ticket_status(ticket_id):
    guard = login_required()
    if guard:
        return guard

    resp, code = api_get(f"/tickets/{ticket_id}")
    if code == 200:
        return render_template("ticket_status.html",
                               ticket=resp.get("ticket"),
                               resolution=resp.get("resolution"))
    flash(resp.get("detail", "Ticket not found."), "danger")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# ADMIN ROUTES
# ---------------------------------------------------------------------------

@app.route("/admin")
def admin():
    guard = login_required(role="Admin")
    if guard:
        return guard

    # Fetch all data for admin dashboard
    tickets_resp,   _ = api_get("/admin/tickets")
    escalated_resp, _ = api_get("/admin/escalated")
    analytics_resp, _ = api_get("/admin/analytics")

    tickets   = tickets_resp.get("tickets", [])           if isinstance(tickets_resp, dict) else []
    escalated = escalated_resp.get("escalated_tickets", []) if isinstance(escalated_resp, dict) else []
    analytics = analytics_resp.get("analytics", {})        if isinstance(analytics_resp, dict) else {}

    return render_template(
        "dashboard_admin.html",
        tickets=tickets,
        escalated=escalated,
        analytics=analytics,
    )


@app.route("/admin/update-status", methods=["POST"])
def admin_update_status():
    guard = login_required(role="Admin")
    if guard:
        return redirect(url_for("login"))

    ticket_id  = request.form.get("ticket_id", type=int)
    new_status = request.form.get("status", "")
    resp, code = api_put(f"/admin/tickets/{ticket_id}", {"status": new_status})
    if code == 200:
        flash(f"Ticket #{ticket_id} updated to '{new_status}'.", "success")
    else:
        flash(resp.get("detail", "Update failed."), "danger")
    return redirect(url_for("admin") + "#all-tickets")


@app.route("/api/ticket/<int:ticket_id>/resolutions")
def api_ticket_resolutions(ticket_id):
    """Return existing resolutions for a ticket as JSON (admin preview)."""
    guard = login_required(role="Admin")
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    resp, code = api_get(f"/tickets/{ticket_id}")
    if code != 200:
        return jsonify({"error": resp.get("detail", "Ticket not found.")}), code

    resolution = resp.get("resolution")
    resolutions = [resolution] if resolution else []
    return jsonify({"ticket_id": ticket_id, "resolutions": resolutions})


@app.route("/admin/add-resolution", methods=["POST"])
def admin_add_resolution():
    guard = login_required(role="Admin")
    if guard:
        return redirect(url_for("login"))

    ticket_id = request.form.get("ticket_id", type=int)
    res_text  = request.form.get("resolution_text", "").strip()
    if not res_text:
        flash("Resolution text cannot be empty.", "warning")
        return redirect(url_for("admin") + "#add-resolution")
    resp, code = api_post("/admin/resolution",
                          {"ticket_id": ticket_id, "resolution_text": res_text})
    if code == 201:
        flash(f"Resolution added for Ticket #{ticket_id} and marked Resolved.", "success")
    else:
        flash(resp.get("detail", "Failed to add resolution."), "danger")
    return redirect(url_for("admin") + "#add-resolution")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("  IT Ticket Resolution Engine — Flask Frontend")
    print("  Running on  : http://127.0.0.1:5000")
    print("  Backend API : http://127.0.0.1:8000")
    print("=" * 55)
    app.run(debug=True, port=5000)
