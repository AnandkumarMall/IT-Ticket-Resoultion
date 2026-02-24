# 🎫 IT Ticket Resolution Suggestion Engine

> **NLP-powered support desk assistant** that automatically suggests resolutions for incoming IT tickets using TF-IDF cosine similarity — no LLM, no API costs, fully offline.

---

## 📋 Table of Contents
1. [Problem Understanding](#-problem-understanding)
2. [Business Value](#-business-value)
3. [Dataset & Preprocessing](#-dataset--preprocessing)
4. [System Architecture](#-system-architecture)
5. [NLP Engine — Similarity Approach](#-nlp-engine--similarity-approach)
6. [Backend Engineering](#-backend-engineering)
7. [Database Design](#-database-design)
8. [UI & Integration](#-ui--integration)
9. [Ticket Lifecycle](#-ticket-lifecycle)
10. [API Reference](#-api-reference)
11. [Project Structure](#-project-structure)
12. [How to Run](#-how-to-run)
13. [Trade-offs & Design Decisions](#-trade-offs--design-decisions)

---

## 🧩 Problem Understanding

IT support desks receive thousands of repetitive tickets every month. A large portion of these tickets — **VPN failures, WiFi issues, login lockouts, printer errors** — have been solved before. Yet agents spend significant time re-diagnosing and re-typing the same resolutions.

**The core problem:**
> *How can we automatically surface the most relevant past resolution the moment a new ticket arrives — with zero human intervention?*

This system answers that question by treating the resolution suggestion problem as an **information retrieval task**: given a new ticket description, find the most semantically similar historical tickets and return their proven resolutions.

---

## 💼 Business Value

| Metric | Impact |
|---|---|
| ⏱️ **Reduced resolution time** | Common issues resolved in seconds, not hours |
| 🔁 **Reduced repeat work** | Agents no longer re-investigate known problems |
| 📉 **Lower escalation rate** | Users self-serve using AI suggestions before escalating |
| 📊 **Feedback loop** | System learns which suggestions are accepted or rejected |
| 🚀 **No LLM dependency** | Zero API cost, runs fully offline, instant response |

---

## 📦 Dataset & Preprocessing

### Datasets Used

| File | Description | Size |
|---|---|---|
| `data/tickets.csv` | Curated seed dataset — 50 unique IT tickets across 10 categories | 50 rows |
| `data/enterprise_synthetic_tickets.csv` | Synthetically generated enterprise dataset for richer training | ~500+ rows |
| `data/synthatic_data_generator.py` | Script used to generate the enterprise dataset |  |

### Categories Covered

`VPN` · `Email` · `Access` · `Network` · `System` · `Printer` · `Software` · `Hardware` · `Login` · `Other`

### Preprocessing Pipeline

Each ticket description goes through a 5-step NLP cleaning pipeline at both **training** and **inference** time:

```
Raw text
  ↓  Lowercase normalisation
  ↓  Remove non-alphabetic characters
  ↓  Tokenisation (whitespace split)
  ↓  Stop-word removal (NLTK English stopwords, len > 2)
  ↓  WordNet Lemmatisation
  ↓  Rejoin into clean string
```

**Why lemmatisation over stemming?**  
Lemmatisation produces real English words (`running → run`, `printers → printer`), resulting in better TF-IDF vocabulary and higher-quality vectors compared to aggressive stemming.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                        │
│   Flask Frontend (port 5000) ── Streamlit (port 8501)   │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP REST (requests)
┌───────────────────▼─────────────────────────────────────┐
│                  FASTAPI BACKEND (port 8000)             │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ auth_routes  │  │ticket_routes │  │ admin_routes  │  │
│  │ /signup      │  │ /tickets     │  │/admin/tickets │  │
│  │ /login       │  │ /tickets/:id │  │/admin/analytics│ │
│  │ /admin/login │  │ /feedback    │  │/admin/escalated│ │
│  └──────────────┘  └──────┬───────┘  └───────────────┘  │
│                           │ calls                        │
│                  ┌────────▼────────┐                     │
│                  │   nlp_service   │  TF-IDF + Cosine    │
│                  │ get_top_similar │  Similarity Engine  │
│                  └────────┬────────┘                     │
│                           │ reads                        │
│              ┌────────────▼──────────────┐               │
│              │  enterprise_synthetic_    │               │
│              │  tickets.csv (500+ rows)  │               │
│              └───────────────────────────┘               │
│                                                          │
│              ┌────────────────────────────┐              │
│              │   SQLite: ticket_system.db │              │
│              │  users · admins · tickets  │              │
│              │  resolutions               │              │
│              └────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 🤖 NLP Engine — Similarity Approach

### Algorithm: TF-IDF + Cosine Similarity

**TF-IDF** (Term Frequency–Inverse Document Frequency) converts each ticket description into a high-dimensional sparse vector where:
- **TF** rewards words that appear frequently in a ticket
- **IDF** penalises words that appear in almost every ticket (e.g., "error", "not")
- Combined, it highlights the **discriminative keywords** of each ticket

**Cosine Similarity** then measures the angle between two TF-IDF vectors. A score of 1.0 = identical, 0.0 = completely unrelated.

### Matching Pipeline (Inference)

```
New ticket description
      │
      ▼  _clean_text()  [same pipeline as training]
Cleaned query
      │
      ▼  vectorizer.transform()
TF-IDF query vector (1 × vocab_size)
      │
      ▼  cosine_similarity(query_vec, tfidf_matrix)
Raw similarity scores  [1 × N_historical_tickets]
      │
      ▼  Category Boost / Penalty
      │   +25% boost  if category keyword detected in query
      │    -10% penalty otherwise
      │
      ▼  Sort descending, filter threshold ≥ 0.10
Top-3 matching historical tickets + resolutions
```

### Why TF-IDF + Cosine, not an LLM?

| Approach | Latency | Cost | Explainability | Offline? |
|---|---|---|---|---|
| **TF-IDF + Cosine** (ours) | < 50 ms | ₹0 | ✅ High | ✅ Yes |
| Word2Vec / BERT embeddings | 100–500 ms | Medium | Moderate | Partial |
| GPT-4 API | 2–10 s | High | ❌ Low | ❌ No |

For a support desk context, **speed, cost, and explainability** matter more than maximal semantic understanding. TF-IDF is the right baseline.

### Trade-offs & Limitations

- **Vocabulary mismatch**: If a new ticket uses completely different terminology (e.g., jargon), similarity may be low → falls below threshold → no suggestions returned (handled gracefully)
- **Short descriptions**: Very brief tickets produce sparse vectors; resolved by the `min_len > 2` token filter
- **Duplicate suppression**: The vectorizer deduplicates historical descriptions before fitting, preventing trivially identical top results
- **Bigrams**: `ngram_range=(1,2)` captures phrases like "vpn disconnect" and "login failed" as single features, improving recall for compound IT terms

---

## ⚙️ Backend Engineering

Built with **FastAPI** — a modern async Python framework with automatic OpenAPI documentation.

### Module Structure

| File | Responsibility |
|---|---|
| `main.py` | App factory: registers routers, CORS, DB init on startup |
| `database.py` | SQLite layer: `get_connection()`, `init_db()`, WAL mode |
| `nlp_service.py` | Singleton TF-IDF vectorizer; `get_top_similar_tickets()` |
| `ticket_routes.py` | Create ticket, get suggestions, submit feedback, view ticket |
| `admin_routes.py` | List all tickets, escalated tickets, update status, add resolution |
| `analytics_service.py` | SQL aggregations: counts, avg resolution time, category breakdown |
| `auth_routes.py` | User & admin signup/login with email uniqueness validation |

### Key Design Decisions

- **Singleton vectorizer**: `_vectorizer` is instantiated once at module import — no per-request re-fitting
- **WAL journal mode**: SQLite with `PRAGMA journal_mode=WAL` allows concurrent reads during writes
- **Separation of concerns**: Each route file handles one domain; `nlp_service` is decoupled from HTTP concerns
- **No ORM**: Raw `sqlite3` with `row_factory = sqlite3.Row` gives dict-like row access without the overhead of SQLAlchemy

---

## 🗄️ Database Design

```
┌─────────────────────────────────────────────────────┐
│  users                     admins                   │
│  ─────────────────         ──────────────────────   │
│  id (PK)                   id (PK)                  │
│  name                      name                     │
│  email (UNIQUE)            email (UNIQUE)           │
│  department                department               │
│  password                  password                 │
│  created_at                                         │
└───────────┬─────────────────────────────────────────┘
            │ 1:N
┌───────────▼──────────────────────────────────────────┐
│  tickets                                             │
│  ────────────────────────────────────────────────    │
│  id (PK)                                             │
│  user_id (FK → users.id)                             │
│  description       — raw user input                  │
│  category          — NLP-inferred or user-selected   │
│  priority          — Low / Medium / High             │
│  status            — Open / In Progress / Resolved / │
│                       Pending / Closed               │
│  similarity_score  — top cosine score (stored)       │
│  feedback          — NULL / 1 (helpful) / 0 (not)   │
│  escalation_flag   — 0 / 1                           │
│  created_at                                          │
└───────────┬──────────────────────────────────────────┘
            │ 1:N
┌───────────▼──────────────────────────────────────────┐
│  resolutions                                         │
│  ────────────────────────────────────────────────    │
│  id (PK)                                             │
│  ticket_id (FK → tickets.id)                         │
│  resolution_text   — NLP suggestion or manual entry  │
│  helpful_count     — upvotes from feedback           │
│  not_helpful_count — downvotes from feedback         │
│  resolved_date                                       │
└──────────────────────────────────────────────────────┘
```

**Feedback loop**: When a user marks a suggestion as helpful, `status → Resolved`, `helpful_count++`. When marked not helpful, `status → Pending`, `escalation_flag = 1`, `not_helpful_count++`. This creates a **self-improving audit trail**.

---

## 🖥️ UI & Integration

Two independent frontends, both connecting to the same FastAPI backend:

### Flask Frontend *(primary, port 5000)*

A modern **dark glassmorphism** web app built with Flask + Jinja2 + Vanilla CSS + Chart.js.

**User Flow:**
1. Register / Login (User or Admin role)
2. Describe your IT issue — select category & priority
3. Submit → NLP engine returns top-3 suggestions instantly
4. Read each suggestion (collapsible cards with similarity % badge)
5. Mark as **Helpful** (auto-resolves) or **Not Helpful** (auto-escalates)
6. Track ticket status at any time via Ticket ID

**Admin Flow:**
1. Login as Admin
2. View all tickets with full status, priority, escalation indicators
3. See escalated tickets needing manual attention
4. Preview NLP suggestions before writing a manual resolution
5. Add manual resolution → ticket auto-marked Resolved
6. View analytics: totals, category distribution chart, avg resolution time

### Streamlit Frontend *(preserved, port 8501)*

The original prototype frontend — kept intact for compatibility. Provides identical functionality via Streamlit widgets.

### Error Handling

| Scenario | Handling |
|---|---|
| No similar tickets found (unseen issue type) | Returns empty suggestions list; user can still submit ticket for manual review |
| Backend unreachable | Flask shows flash error; all API calls wrapped in try/except |
| Duplicate email signup | 409 Conflict returned; UI shows clear message |
| Invalid ticket ID lookup | 404 returned; UI shows "Ticket not found" |
| Similarity score below threshold (0.10) | Result filtered out; prevents low-confidence suggestions |

---

## 🔄 Ticket Lifecycle

```
User submits description
        │
        ▼
  [OPEN] Ticket created + NLP suggestions generated & stored
        │
        ├─── User marks "Helpful" ──────────────────► [RESOLVED] ✅
        │
        └─── User marks "Not Helpful" ─────────────► [PENDING / ESCALATED] 🚨
                                                              │
                                              Admin reviews & adds manual resolution
                                                              │
                                                        [RESOLVED] / [CLOSED] ✅
```

---

## 📡 API Reference

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/signup` | Register new user |
| POST | `/login` | User login |
| POST | `/admin/signup` | Register admin |
| POST | `/admin/login` | Admin login |

### Tickets (User)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/tickets` | Submit ticket + get NLP suggestions |
| GET | `/tickets/{id}` | Get ticket details + resolution |
| POST | `/tickets/{id}/feedback` | Submit helpful / not helpful |
| GET | `/tickets/{id}/resolutions` | Get all resolutions for a ticket |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/tickets` | List all tickets |
| GET | `/admin/escalated` | List escalated tickets |
| PUT | `/admin/tickets/{id}` | Update ticket status |
| POST | `/admin/resolution` | Add manual resolution |
| GET | `/admin/analytics` | System analytics summary |

---

## 📁 Project Structure

```
IT_Ticket Resoultion - Copy/
│
├── backend/                        # FastAPI backend
│   ├── main.py                     # App entry point, CORS, router registration
│   ├── database.py                 # SQLite connection helper + schema init
│   ├── nlp_service.py              # TF-IDF engine (singleton vectorizer)
│   ├── ticket_routes.py            # /tickets endpoints
│   ├── admin_routes.py             # /admin endpoints
│   ├── auth_routes.py              # /signup, /login endpoints
│   ├── analytics_service.py        # SQL analytics helpers
│   ├── requirements.txt            # Backend dependencies
│   └── ticket_system.db            # SQLite database (auto-created)
│
├── data/
│   ├── tickets.csv                 # 50-row seed dataset (10 categories)
│   ├── enterprise_synthetic_tickets.csv  # Larger synthetic training set
│   └── synthatic_data_generator.py # Dataset generation script
│
├── flask_app/                      # Flask frontend (primary UI)
│   ├── app.py                      # Flask routes + API proxy helpers
│   ├── requirements.txt            # Flask dependencies
│   ├── templates/
│   │   ├── base.html               # Navbar, flash messages, layout
│   │   ├── index.html              # Landing page
│   │   ├── login.html              # Login + signup (role toggle)
│   │   ├── dashboard_user.html     # Raise ticket, AI suggestions, feedback
│   │   ├── dashboard_admin.html    # All tickets, escalated, add resolution, analytics
│   │   └── ticket_status.html      # Single ticket detail view
│   └── static/
│       ├── css/style.css           # Dark glassmorphism design system
│       └── js/main.js              # Tab switching, AJAX feedback, spinners
│
├── frontend/
│   └── app.py                      # Original Streamlit frontend (preserved)
│
└── npl_engine/                     # Notebook prototyping directory
    └── nlp_engine.ipynb            # Original NLP exploration notebook
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.10+
- The `.venv` virtual environment (pre-configured at `Hackhathon/.venv`)

### 1. Start the FastAPI Backend

```bash
# From: IT_Ticket Resoultion - Copy/backend/
& "..\..\..\.venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8000
```

Backend is live at: **http://127.0.0.1:8000**  
Interactive API docs: **http://127.0.0.1:8000/docs**

### 2. Start the Flask Frontend

```bash
# From: IT_Ticket Resoultion - Copy/flask_app/
& "..\..\..\.venv\Scripts\python.exe" app.py
```

Flask app is live at: **http://127.0.0.1:5000**

### 3. (Optional) Start the Streamlit Frontend

```bash
# From: IT_Ticket Resoultion - Copy/frontend/
& "..\..\..\.venv\Scripts\streamlit.exe" run app.py
```

Streamlit app is live at: **http://localhost:8501**

---

## ⚖️ Trade-offs & Design Decisions

| Decision | Rationale |
|---|---|
| **TF-IDF over BERT/LLM** | No API cost, instant inference (<50ms), fully offline, easy to explain |
| **SQLite over PostgreSQL** | Zero infra setup; WAL mode gives adequate concurrency for demo scale |
| **Flask over React** | Jinja2 templates deliver a complete UI with no build step or JS framework complexity |
| **Bigrams (1,2) in TF-IDF** | Phrases like "vpn disconnect" or "wifi driver" are better discriminators than individual words |
| **Threshold = 0.10** | Empirically found to filter noise while accepting useful low-confidence matches for uncommon issues |
| **Category boost (+25%)** | Simple heuristic that improves ranking when the user mentions a known category keyword |
| **Feedback stored in DB** | Creates an audit trail and enables future supervised retraining using user-accepted resolutions |
| **Singleton vectorizer** | Fits TF-IDF once on startup; subsequent requests use the pre-built matrix (O(1) per request) |

---

## 🧑‍💻 Tech Stack

| Layer | Technology |
|---|---|
| **NLP Engine** | scikit-learn (TF-IDF), NLTK (stopwords, lemmatizer), pandas |
| **Backend API** | FastAPI, Uvicorn, Pydantic |
| **Database** | SQLite (raw sqlite3, WAL mode) |
| **Flask Frontend** | Flask 3.0, Jinja2, Vanilla CSS, Vanilla JS, Chart.js |
| **Streamlit Frontend** | Streamlit |
| **Environment** | Python 3.10+, pip venv |

---

*Built for the IT Helpdesk Hackathon — demonstrating that powerful NLP systems don't require expensive LLMs.*
