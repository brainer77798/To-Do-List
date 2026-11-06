# TaskVault — Private Task Manager

**TaskVault** is a modern, password-protected, single-owner productivity and personal task management application built with Python, Streamlit, and SQLAlchemy. It combines the speed of a fast to-do list with comprehensive project organization, daily planning, recurrence rules, Pomodoro focus tracking, and productivity analytics.

---

## 🌟 Key Features

1. **Dedicated Argon2id Security Gate:**
   - Single-owner password lock screen with zero plaintext storage.
   - Persistent failed-attempt protection (rate limiting & progressive lockout) stored in the database.
   - Optional cryptographic recovery code flow.
   - Manual immediate lock and automatic configurable inactivity timeout.
   - Complete data hiding: no tasks, projects, or statistics are rendered before unlocking.

2. **Core Task Management:**
   - 1-click Quick Capture and comprehensive full-detail task forms.
   - Priority levels: Urgent, High, Medium, Low.
   - Due dates with time support, timezone conversions, and date-only preservation.
   - Subtasks (1-level nesting limit to prevent recursion) and interactive checklist items.
   - Soft delete with 30-day Trash restoration and permanent purge.
   - Archiving tasks out of active daily workflows.
   - Task duplication and bulk actions (change priority, move project, mark done, archive, delete).

3. **Views & Organization:**
   - **Dashboard:** At-a-glance command center with metrics, overdue alerts, today's focus, and 7-day completion velocity.
   - **Inbox:** Rapid capture and processing area for uncategorized tasks.
   - **My Day:** Daily workload estimation calculated against your configured daily capacity.
   - **Upcoming:** 7, 14, and 30-day grouped horizon view.
   - **All Tasks:** Multi-filter, full-text search, and sorting.
   - **Board (Kanban):** Columns for To Do, In Progress, and Done with quick status transition actions.
   - **Calendar:** Interactive month-matrix calendar showing task counts and daily task lists.
   - **Projects:** Group tasks with progress meters, descriptions, colors, and icons.
   - **Completed:** Accomplishment history with 1-click reopen capability.
   - **Archive & Trash:** Safety holding areas with batch empty confirmation.

4. **Recurrence Engine:**
   - Preset frequencies: Daily, Weekdays (Mon-Fri), Weekly (custom days), Monthly (with month-end clamping), and Yearly (with leap-year handling).
   - Idempotent generation: completion of an occurrence safely schedules the next occurrence without creating duplicate instances.

5. **Productivity & Focus:**
   - **Focus Mode & Pomodoro Timer:** 25m Focus, 5m Short Break, and 15m Long Break intervals with timestamp-backed countdowns.
   - Task linking: log focused intervals directly to tasks to accumulate actual time spent.
   - Manual time logging for offline work.

6. **Insights & Analytics:**
   - Real-time productivity trends (last 7, 30, or 90 days).
   - Consecutive daily completion streaks.
   - Project time distribution and priority breakdowns.

7. **Data Portability & Backups:**
   - CSV export with spreadsheet formula injection protection.
   - Complete versioned JSON backups (strictly excluding password hashes and credentials).
   - Validated JSON backup restore with Merge and Replace modes.

---

## 🛠️ Technology Stack

- **Frontend & Web Server:** [Streamlit](https://streamlit.io/) (1.40+)
- **Database ORM:** [SQLAlchemy](https://www.sqlalchemy.org/) 2.x
- **Database Engine:** Managed PostgreSQL (production) or SQLite (local development)
- **Database Driver:** `psycopg[binary]`
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Password Hashing:** `argon2-cffi` (OWASP-compliant Argon2id parameters)
- **Date & Recurrence Math:** `python-dateutil` and native `zoneinfo`
- **Analytics & Visualizations:** `plotly` & `pandas`
- **Testing:** `pytest`

---

## 📂 Project Structure

```text
to-do list/
├── app.py                          # Main Streamlit application entrypoint
├── requirements.txt                # Pinned production dependencies
├── alembic.ini                     # Alembic configuration
├── .gitignore                      # Git ignore rules
├── .env.example                    # Sample environment variables
├── .streamlit/
│   ├── config.toml                 # Streamlit theme and server configuration
│   └── secrets.example.toml        # Sample Streamlit secrets template
├── migrations/                     # Alembic migration scripts
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py   # Complete initial database schema
├── taskvault/
│   ├── config.py                   # Configuration and secret loading
│   ├── database.py                 # SQLAlchemy engine, session factory, pooling
│   ├── models/                     # SQLAlchemy models (Task, Project, Settings, etc.)
│   ├── repositories/               # Pure database queries and persistence
│   ├── services/                   # Business logic, auth, recurrence, backups
│   ├── security/                   # Argon2id hashing, rate limiting, session manager
│   ├── ui/                         # Streamlit UI presentation layer
│   │   ├── styles.py               # Theme and custom CSS styling
│   │   ├── components.py           # Reusable metric cards, headers, alerts
│   │   ├── task_cards.py           # Interactive task item cards
│   │   ├── task_forms.py           # Quick-add and full edit modal forms
│   │   ├── auth_screen.py          # Lock screen and first-run wizard
│   │   ├── navigation.py           # Sidebar navigation and view switcher
│   │   └── views/                  # View modules (Dashboard, Today, Board, etc.)
│   └── utils/                      # Date/timezone helpers, formatting, validation
└── tests/                          # Automated test suite (auth, tasks, recurrence, etc.)
```

---

## 🚀 Local Development Setup

### 1. Clone & Set Up Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the Database

By default in development mode, TaskVault uses local SQLite (`taskvault.db`):

```bash
alembic upgrade head
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. On first launch, follow the on-screen wizard to create your master password and save your recovery code.

---

## ☁️ Streamlit Community Cloud Deployment

Follow these steps to deploy TaskVault on Streamlit Community Cloud:

### 1. Set Up Managed PostgreSQL
1. Create a PostgreSQL database on a managed provider such as [Supabase](https://supabase.com/), [Neon](https://neon.tech/), or [Railway](https://railway.app/).
2. Copy the PostgreSQL connection URI. Format:
   ```text
   postgresql+psycopg://username:password@hostname:5432/database_name?sslmode=require
   ```

### 2. Push to GitHub
Commit your project to a private or public GitHub repository. (Ensure `.streamlit/secrets.toml` and `.env` are in `.gitignore`!)

### 3. Deploy App on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app.
2. Select your repository, branch, and set the **Main file path** to `app.py`.
3. Open **Advanced Settings** -> **Secrets** and paste:
   ```toml
   APP_ENV = "production"
   DATABASE_URL = "postgresql+psycopg://username:password@hostname:5432/database_name?sslmode=require"
   ```
4. Click **Deploy**. TaskVault will connect to your managed PostgreSQL database, auto-initialize the schema, and prompt you to create your master password.

> ⚠️ **Important Cloud Persistence Warning:** Streamlit Community Cloud does not guarantee durability of local file storage (the filesystem is ephemeral and resets on container restarts). TaskVault enforces that `APP_ENV="production"` requires a persistent `DATABASE_URL` so you never risk data loss.

---

## 🔒 Security Architecture & Limitations

### What TaskVault's Security Does:
- **Argon2id Password Gate:** Your workspace master password is hashed with `argon2-cffi` using a unique cryptographic salt. Plaintext passwords are never logged or stored.
- **Persistent Rate Limiting:** Failed attempts are recorded in the database. 5 consecutive failures triggers an automatic 15-minute progressive lockout that persists across page refreshes and browser tabs.
- **Recovery Code Verifier:** Recovery codes are hashed before storage; the plaintext recovery code is shown only once at creation time.
- **Zero Data Leakage:** Unauthenticated sessions are blocked at the application root; no tasks, projects, notes, or statistics are rendered while locked.
- **Formula Injection Defense:** CSV exports escape values starting with `=`, `+`, `-`, or `@` to prevent spreadsheet command execution.

### Security Boundaries & Threat Model:
- **Application Access Gate:** TaskVault's password screen protects against casual or unauthorized web access to your workspace.
- **Not End-to-End Encryption:** Task content in the PostgreSQL database is stored in standard relational tables. It does not replace hosting-level access controls or protect against an administrator who has direct access to your hosting dashboard or database credentials.
- **Recommendation:** Protect your Streamlit Cloud account and database provider accounts with two-factor authentication (2FA).

---

## 🧪 Running Tests

TaskVault includes comprehensive automated tests covering authentication, rate limiting, task operations, recurrence edge cases, CSV/JSON backups, and access control.

Run the test suite:
```bash
pytest -v
```

---

## 📄 License

MIT License. Designed and built as an AI-powered personal productivity command center.

