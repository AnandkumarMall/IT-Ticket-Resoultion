"""
app.py
------
IT Ticket Resolution Suggestion Engine — Streamlit Frontend.

Connects to the FastAPI backend running at http://localhost:8000.

Roles:
  User  → Raise tickets, view AI suggestions, give feedback, check status
  Admin → View all/escalated tickets, add resolutions, view analytics
"""

import streamlit as st
import requests
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"

# Page config — must be the very first Streamlit call
st.set_page_config(
    page_title="IT Ticket Resolution Engine",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — clean, professional look
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Import Google Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stRadio label {
    color: #cbd5e1 !important;
    font-size: 0.95rem;
}

/* Cards */
.card {
    background: #1e293b;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    border: 1px solid #334155;
    color: #e2e8f0;
}
.card-success {
    background: #052e16;
    border: 1px solid #16a34a;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    color: #86efac;
    margin-top: 0.5rem;
}
.card-warning {
    background: #431407;
    border: 1px solid #ea580c;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    color: #fdba74;
    margin-top: 0.5rem;
}
.card-info {
    background: #0c1a3a;
    border: 1px solid #3b82f6;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    color: #93c5fd;
    margin-top: 0.5rem;
}

/* Suggestion card */
.suggestion-card {
    background: #0f172a;
    border-left: 4px solid #6366f1;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    color: #e2e8f0;
}
.score-badge {
    display: inline-block;
    background: #4f46e5;
    color: white;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-left: 8px;
}

/* Page header */
.page-header {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    border-radius: 12px;
    padding: 1.6rem 2rem;
    color: white;
    margin-bottom: 1.5rem;
}
.page-header h1 { color: white; margin: 0; font-size: 1.8rem; }
.page-header p  { color: #c4b5fd; margin: 0.3rem 0 0; }

/* Status badge */
.badge-open     { background:#1d4ed8; color:#bfdbfe; border-radius:6px; padding:2px 10px; font-size:0.8rem; }
.badge-resolved { background:#166534; color:#bbf7d0; border-radius:6px; padding:2px 10px; font-size:0.8rem; }
.badge-pending  { background:#92400e; color:#fde68a; border-radius:6px; padding:2px 10px; font-size:0.8rem; }
.badge-escalated{ background:#7f1d1d; color:#fca5a5; border-radius:6px; padding:2px 10px; font-size:0.8rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION-STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "logged_in": False,
        "role":      None,   # "User" | "Admin"
        "user_id":   None,
        "user_name": None,
        "user_email": None,
        "last_ticket_id": None,
        "last_suggestions": [],
        "feedback_given": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ─────────────────────────────────────────────────────────────────────────────
# API HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def api_post(endpoint: str, payload: dict) -> dict | None:
    """POST JSON to the backend. Returns response dict or None on error."""
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
        else:
            st.error(f"❌ API Error ({r.status_code}): {r.json().get('detail', r.text)}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Make sure FastAPI is running on http://localhost:8000")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None


def api_get(endpoint: str) -> dict | None:
    """GET from the backend. Returns response dict or None on error."""
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"❌ API Error ({r.status_code}): {r.json().get('detail', r.text)}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Make sure FastAPI is running on http://localhost:8000")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None


def api_put(endpoint: str, payload: dict) -> dict | None:
    """PUT JSON to the backend. Returns response dict or None on error."""
    try:
        r = requests.put(f"{BASE_URL}{endpoint}", json=payload, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"❌ API Error ({r.status_code}): {r.json().get('detail', r.text)}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Make sure FastAPI is running on http://localhost:8000")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎫 IT Ticket Engine")
    st.markdown("---")

    if st.session_state.logged_in:
        role_icon = "👤" if st.session_state.role == "User" else "🛡️"
        st.markdown(f"**{role_icon} {st.session_state.user_name}**")
        st.markdown(f"`{st.session_state.role}` · {st.session_state.user_email}")
        st.markdown("---")

    # Navigation options depend on login state + role
    if not st.session_state.logged_in:
        nav_options = ["🏠 Home", "🔐 Login / Signup"]
    elif st.session_state.role == "User":
        nav_options = ["🏠 Home", "📋 User Dashboard"]
    else:
        nav_options = ["🏠 Home", "🛡️ Admin Dashboard"]

    page = st.radio("Navigation", nav_options, label_visibility="collapsed")

    st.markdown("---")
    if st.session_state.logged_in:
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            init_session()
            st.rerun()

    st.markdown(
        "<small style='color:#64748b;'>Backend: localhost:8000</small>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: HOME
# ─────────────────────────────────────────────────────────────────────────────
if "🏠 Home" in page:
    st.markdown("""
    <div class="page-header">
        <h1>🎫 IT Ticket Resolution Engine</h1>
        <p>AI-powered support — TF-IDF similarity matching for instant ticket resolutions</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class="card">
            <h3>🤖 AI Suggestions</h3>
            <p>Submit your IT issue and get the top-3 similar historical resolutions instantly.</p>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="card">
            <h3>📊 Smart Analytics</h3>
            <p>Admins get real-time dashboards: open/resolved counts, categories, escalation stats.</p>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="card">
            <h3>🔁 Feedback Loop</h3>
            <p>User feedback automatically resolves or escalates tickets to the support team.</p>
        </div>""", unsafe_allow_html=True)

    if not st.session_state.logged_in:
        st.info("👈 Use the sidebar to **Login / Signup** and get started.")
    else:
        st.success(f"✅ Logged in as **{st.session_state.user_name}** ({st.session_state.role}). Use the sidebar to navigate.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: LOGIN / SIGNUP
# ─────────────────────────────────────────────────────────────────────────────
elif "🔐 Login / Signup" in page:
    st.markdown("""
    <div class="page-header">
        <h1>🔐 Authentication</h1>
        <p>Login or create a new account to continue</p>
    </div>
    """, unsafe_allow_html=True)

    # Role selector at the top
    role = st.radio("Select Role", ["👤 User", "🛡️ Admin"], horizontal=True)
    selected_role = "User" if "User" in role else "Admin"

    auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])

    # ── LOGIN TAB ──────────────────────────────────────────────
    with auth_tab1:
        st.markdown(f"#### Login as {selected_role}")
        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔑 Login", use_container_width=True)

        if submitted:
            if not email or not password:
                st.warning("Please fill in all fields.")
            else:
                endpoint = "/login" if selected_role == "User" else "/admin/login"
                with st.spinner("Authenticating…"):
                    resp = api_post(endpoint, {"email": email, "password": password})

                if resp:
                    profile = resp.get("user") or resp.get("admin", {})
                    st.session_state.logged_in  = True
                    st.session_state.role       = selected_role
                    st.session_state.user_id    = profile.get("id")
                    st.session_state.user_name  = profile.get("name", "Unknown")
                    st.session_state.user_email = profile.get("email", email)
                    st.success(f"✅ Welcome back, **{st.session_state.user_name}**!")
                    st.rerun()

    # ── SIGNUP TAB ────────────────────────────────────────────
    with auth_tab2:
        st.markdown(f"#### Create {selected_role} Account")
        with st.form("signup_form"):
            name       = st.text_input("Full Name", placeholder="Jane Doe")
            email_s    = st.text_input("Email", placeholder="jane@company.com", key="signup_email")
            department = st.text_input("Department", placeholder="IT / HR / Finance…")
            password_s = st.text_input("Password", type="password", key="signup_pass")
            confirm_s  = st.text_input("Confirm Password", type="password")
            submitted_s = st.form_submit_button("📝 Create Account", use_container_width=True)

        if submitted_s:
            if not all([name, email_s, password_s, confirm_s]):
                st.warning("Please fill in all required fields.")
            elif password_s != confirm_s:
                st.error("Passwords do not match.")
            else:
                endpoint = "/signup" if selected_role == "User" else "/admin/signup"
                payload  = {
                    "name":       name,
                    "email":      email_s,
                    "department": department,
                    "password":   password_s,
                }
                with st.spinner("Creating account…"):
                    resp = api_post(endpoint, payload)
                if resp:
                    st.success("✅ Account created! Please switch to the **Login** tab to sign in.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: USER DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
elif "📋 User Dashboard" in page:
    if not st.session_state.logged_in or st.session_state.role != "User":
        st.warning("🔒 Please login as a **User** to access this page.")
        st.stop()

    st.markdown("""
    <div class="page-header">
        <h1>📋 User Dashboard</h1>
        <p>Raise tickets and track their status</p>
    </div>
    """, unsafe_allow_html=True)

    tab_raise, tab_status = st.tabs(["🆕 Raise a Ticket", "🔍 My Ticket Status"])

    # ── TAB: RAISE A TICKET ──────────────────────────────────
    with tab_raise:
        st.markdown("### Describe Your Issue")

        categories = [
            "Network", "Hardware", "Software", "Email",
            "VPN", "Printer", "Access", "Security", "Other"
        ]
        priorities = ["Low", "Medium", "High"]

        with st.form("raise_ticket_form", clear_on_submit=False):
            description = st.text_area(
                "Issue Description *",
                height=130,
                placeholder="e.g. My laptop cannot connect to the office Wi-Fi after a Windows update…",
            )
            col_c, col_p = st.columns(2)
            with col_c:
                category = st.selectbox("Category", categories)
            with col_p:
                priority = st.selectbox("Priority", priorities, index=1)

            submit_ticket = st.form_submit_button("🚀 Submit Ticket", use_container_width=True)

        if submit_ticket:
            if not description.strip():
                st.warning("⚠️ Please describe your issue before submitting.")
            else:
                payload = {
                    "user_id":     st.session_state.user_id,
                    "description": description.strip(),
                    "category":    category,
                    "priority":    priority,
                }
                with st.spinner("🤖 Analysing your issue with AI…"):
                    resp = api_post("/tickets", payload)

                if resp:
                    st.session_state.last_ticket_id   = resp["ticket_id"]
                    st.session_state.last_suggestions = resp.get("suggestions", [])
                    st.session_state.feedback_given   = False
                    st.success(f"✅ Ticket **#{resp['ticket_id']}** created successfully!")

        # ── Show AI suggestions ──────────────────────────────
        if st.session_state.last_suggestions:
            st.markdown("---")
            st.markdown("### 🤖 Top AI-Suggested Resolutions")
            st.caption(f"Ticket ID: **#{st.session_state.last_ticket_id}**")

            for i, s in enumerate(st.session_state.last_suggestions, 1):
                score_pct = round(s.get("similarity_score", 0) * 100, 1)
                with st.expander(
                    f"💡 Suggestion {i} — {s.get('category', '')}  •  Score: {score_pct}%",
                    expanded=(i == 1),
                ):
                    st.markdown(f"**📄 Historical Issue:**")
                    st.info(s.get("description", "—"))
                    st.markdown(f"**✅ Resolution:**")
                    st.success(s.get("resolution", "No resolution text available."))
                    st.markdown(
                        f"<span class='score-badge'>Similarity: {score_pct}%</span>",
                        unsafe_allow_html=True,
                    )

            # ── Feedback buttons ─────────────────────────────
            if not st.session_state.feedback_given:
                st.markdown("---")
                st.markdown("#### Was this helpful?")
                col_yes, col_no = st.columns(2)

                with col_yes:
                    if st.button("👍 Helpful", use_container_width=True, type="primary"):
                        with st.spinner("Recording feedback…"):
                            fb = api_post(
                                f"/tickets/{st.session_state.last_ticket_id}/feedback",
                                {"helpful": True},
                            )
                        if fb:
                            st.session_state.feedback_given = True
                            st.markdown(
                                "<div class='card-success'>✅ Great! Ticket marked as <strong>Resolved</strong>. Thanks for your feedback!</div>",
                                unsafe_allow_html=True,
                            )
                            st.rerun()

                with col_no:
                    if st.button("👎 Not Helpful", use_container_width=True):
                        with st.spinner("Escalating ticket…"):
                            fb = api_post(
                                f"/tickets/{st.session_state.last_ticket_id}/feedback",
                                {"helpful": False},
                            )
                        if fb:
                            st.session_state.feedback_given = True
                            st.markdown(
                                "<div class='card-warning'>🔔 Ticket <strong>escalated</strong> to the support team for manual review.</div>",
                                unsafe_allow_html=True,
                            )
                            st.rerun()
            else:
                st.markdown(
                    "<div class='card-info'>✅ Feedback recorded. Thank you!</div>",
                    unsafe_allow_html=True,
                )

    # ── TAB: MY TICKET STATUS ────────────────────────────────
    with tab_status:
        st.markdown("### Check Ticket Status")

        ticket_id_input = st.number_input(
            "Enter Ticket ID",
            min_value=1,
            step=1,
            value=st.session_state.last_ticket_id or 1,
        )
        fetch_btn = st.button("🔍 Fetch Ticket", use_container_width=True)

        if fetch_btn:
            with st.spinner("Fetching ticket details…"):
                data = api_get(f"/tickets/{int(ticket_id_input)}")

            if data:
                ticket = data.get("ticket", {})
                resolution = data.get("resolution")

                # Status badge
                status_val = ticket.get("status", "Open")
                badge_class = {
                    "Open": "badge-open",
                    "Resolved": "badge-resolved",
                    "Pending": "badge-pending",
                }.get(status_val, "badge-open")

                st.markdown(
                    f"<h4>Ticket #{ticket.get('id')} &nbsp;"
                    f"<span class='{badge_class}'>{status_val}</span></h4>",
                    unsafe_allow_html=True,
                )

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Priority",  ticket.get("priority", "—"))
                col_b.metric("Category",  ticket.get("category", "—"))
                col_c.metric("Escalated", "Yes 🔴" if ticket.get("escalation_flag") else "No 🟢")

                st.markdown("**Description:**")
                st.info(ticket.get("description", "—"))

                if resolution:
                    st.markdown("**Resolution:**")
                    st.success(resolution.get("resolution_text", "—"))
                else:
                    st.caption("No resolution recorded yet.")

                st.caption(f"Created: {ticket.get('created_at', '—')}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
elif "🛡️ Admin Dashboard" in page:
    if not st.session_state.logged_in or st.session_state.role != "Admin":
        st.warning("🔒 Please login as an **Admin** to access this page.")
        st.stop()

    st.markdown("""
    <div class="page-header">
        <h1>🛡️ Admin Dashboard</h1>
        <p>Manage tickets, add resolutions, and view analytics</p>
    </div>
    """, unsafe_allow_html=True)

    tab_all, tab_esc, tab_res, tab_analytics = st.tabs([
        "📋 All Tickets",
        "🚨 Escalated",
        "➕ Add Resolution",
        "📊 Analytics",
    ])

    # ── TAB: ALL TICKETS ─────────────────────────────────────
    with tab_all:
        st.markdown("### All Support Tickets")
        if st.button("🔄 Refresh", key="refresh_all"):
            st.rerun()

        with st.spinner("Loading tickets…"):
            data = api_get("/admin/tickets")

        if data:
            tickets = data.get("tickets", [])
            if tickets:
                df = pd.DataFrame(tickets)
                # Friendly column order
                cols = ["id", "user_id", "description", "category", "priority",
                        "status", "escalation_flag", "similarity_score", "created_at"]
                cols = [c for c in cols if c in df.columns]
                df = df[cols]
                df.rename(columns={
                    "id": "Ticket ID", "user_id": "User ID",
                    "description": "Description", "category": "Category",
                    "priority": "Priority", "status": "Status",
                    "escalation_flag": "Escalated",
                    "similarity_score": "AI Score",
                    "created_at": "Created",
                }, inplace=True)
                st.dataframe(df, use_container_width=True, height=400)
                st.caption(f"Total: {len(tickets)} ticket(s)")
            else:
                st.info("No tickets found.")

        # Update status sub-section
        st.markdown("---")
        st.markdown("#### ✏️ Update Ticket Status")
        with st.form("update_status_form"):
            upd_id  = st.number_input("Ticket ID", min_value=1, step=1)
            new_status = st.selectbox(
                "New Status",
                ["Open", "In Progress", "Resolved", "Closed", "Pending"],
            )
            upd_submit = st.form_submit_button("Update Status", use_container_width=True)

        if upd_submit:
            with st.spinner("Updating…"):
                resp = api_put(f"/admin/tickets/{int(upd_id)}", {"status": new_status})
            if resp:
                st.success(f"✅ Ticket #{int(upd_id)} status updated to **{new_status}**.")

    # ── TAB: ESCALATED TICKETS ───────────────────────────────
    with tab_esc:
        st.markdown("### 🚨 Escalated Tickets")
        if st.button("🔄 Refresh", key="refresh_esc"):
            st.rerun()

        with st.spinner("Loading escalated tickets…"):
            data = api_get("/admin/escalated")

        if data:
            tickets = data.get("escalated_tickets", [])
            if tickets:
                df = pd.DataFrame(tickets)
                cols = ["id", "user_id", "description", "category", "priority",
                        "status", "created_at"]
                cols = [c for c in cols if c in df.columns]
                df = df[cols]
                df.rename(columns={
                    "id": "Ticket ID", "user_id": "User ID",
                    "description": "Description", "category": "Category",
                    "priority": "Priority", "status": "Status",
                    "created_at": "Created",
                }, inplace=True)
                st.dataframe(df, use_container_width=True, height=350)
                st.warning(f"⚠️ {len(tickets)} ticket(s) need manual attention.")

                # Quick resolve from this tab
                st.markdown("#### ✏️ Update Escalated Ticket Status")
                with st.form("esc_status_form"):
                    esc_id     = st.number_input("Ticket ID", min_value=1, step=1, key="esc_tid")
                    esc_status = st.selectbox("New Status",
                        ["In Progress", "Resolved", "Closed"], key="esc_sel")
                    esc_submit = st.form_submit_button("Update", use_container_width=True)
                if esc_submit:
                    with st.spinner("Updating…"):
                        resp = api_put(f"/admin/tickets/{int(esc_id)}", {"status": esc_status})
                    if resp:
                        st.success(f"✅ Ticket #{int(esc_id)} updated to **{esc_status}**.")
            else:
                st.success("🎉 No escalated tickets at the moment!")

    # ── TAB: ADD RESOLUTION ──────────────────────────────────
    with tab_res:
        st.markdown("### ➕ Add Manual Resolution")
        st.caption("Add a resolution to a ticket. This will also mark the ticket as **Resolved**.")

        with st.form("add_resolution_form"):
            res_ticket_id = st.number_input("Ticket ID *", min_value=1, step=1)
            res_text = st.text_area(
                "Resolution Text *",
                height=150,
                placeholder="Describe the steps taken to resolve this issue…",
            )
            res_submit = st.form_submit_button("✅ Submit Resolution", use_container_width=True)

        if res_submit:
            if not res_text.strip():
                st.warning("Please enter a resolution.")
            else:
                payload = {
                    "ticket_id":       int(res_ticket_id),
                    "resolution_text": res_text.strip(),
                }
                with st.spinner("Saving resolution…"):
                    resp = api_post("/admin/resolution", payload)
                if resp:
                    st.success(
                        f"✅ Resolution added for Ticket #{int(res_ticket_id)} and ticket marked as **Resolved**."
                    )

    # ── TAB: ANALYTICS ───────────────────────────────────────
    with tab_analytics:
        st.markdown("### 📊 System Analytics")
        if st.button("🔄 Refresh", key="refresh_analytics"):
            st.rerun()

        with st.spinner("Loading analytics…"):
            data = api_get("/admin/analytics")

        if data:
            an = data.get("analytics", {})

            # Key metrics row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📬 Total Tickets",    an.get("total_tickets", 0))
            m2.metric("✅ Resolved",          an.get("resolved_count", 0))
            m3.metric("🔓 Open / Pending",    an.get("open_count", 0))
            m4.metric("🚨 Escalated",         an.get("escalation_count", 0))

            st.markdown("---")

            col_l, col_r = st.columns(2)

            with col_l:
                st.markdown("**📁 Most Common Category**")
                st.markdown(
                    f"<div class='card'><h2>{an.get('most_common_category', '—')}</h2></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("**⏱️ Avg Resolution Time**")
                avg_time = an.get("avg_resolution_time")
                if avg_time is not None:
                    st.markdown(
                        f"<div class='card'><h2>{round(avg_time, 2)} hrs</h2></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("No resolved ticket data yet.")

            with col_r:
                # Category breakdown chart (if available)
                cat_counts = an.get("category_counts")
                if cat_counts:
                    st.markdown("**📊 Tickets by Category**")
                    cat_df = pd.DataFrame(
                        list(cat_counts.items()), columns=["Category", "Count"]
                    ).sort_values("Count", ascending=False)
                    st.bar_chart(cat_df.set_index("Category"))
                else:
                    # Fallback: show open vs resolved as bar
                    st.markdown("**📊 Open vs Resolved**")
                    ov_df = pd.DataFrame({
                        "Status": ["Open / Pending", "Resolved"],
                        "Count":  [an.get("open_count", 0), an.get("resolved_count", 0)],
                    })
                    st.bar_chart(ov_df.set_index("Status"))
