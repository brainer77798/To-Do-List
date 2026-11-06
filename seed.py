"""
Optional seed script for TaskVault development and demonstration.
Populates realistic sample projects, tasks, checklists, and recurrence rules.

Usage:
    python seed.py
"""

from __future__ import annotations

import sys
from datetime import datetime, date, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from taskvault.database import get_db_session, init_db
from taskvault.security.access_control import SessionManager
from taskvault.services import auth_service, project_service, task_service, recurrence_service
from taskvault.models.base import utc_now


def seed_workspace() -> None:
    print("🌱 Initializing database schema...")
    init_db()

    # Session bypass for seed script
    SessionManager.unlock()

    with get_db_session() as db:
        is_first = auth_service.is_first_run(db_session=db)
        if is_first:
            print("🔑 Initializing workspace credentials...")
            demo_password = "VaultDemoPassword123!"
            auth_service.setup_initial_workspace(
                password=demo_password,
                confirm_password=demo_password,
                enable_recovery=True,
                timezone="America/New_York",
                db_session=db,
            )
            print(f"   Created demo password: {demo_password}")
        else:
            print("ℹ️ Workspace already initialized. Adding demo content...")

        # Create Projects
        print("📁 Creating projects...")
        p1 = project_service.create_project(
            name="🚀 Website Redesign",
            description="Revamp branding, design system, and core landing pages.",
            color="#3B82F6",
            icon="code",
            db_session=db,
        )
        p2 = project_service.create_project(
            name="📊 Financial & Taxes",
            description="Quarterly bookkeeping, invoices, and year-end filing.",
            color="#10B981",
            icon="briefcase",
            db_session=db,
        )
        p3 = project_service.create_project(
            name="🏠 Personal & Health",
            description="Fitness goals, home improvement, and reading list.",
            color="#F59E0B",
            icon="heart",
            db_session=db,
        )

        now = utc_now()
        today = date.today()

        # Create Sample Tasks
        print("📝 Creating sample tasks...")
        # Overdue task
        t_overdue = task_service.create_full_task(
            title="Submit Q3 expense report",
            description="Compile receipts from trip to Chicago and file through portal.",
            status="todo",
            priority="urgent",
            project_id=p2.id,
            category="Finance",
            due_at=now - timedelta(days=2),
            due_date_only=True,
            estimated_minutes=45,
            tag_names=["expenses", "urgent"],
            checklist_texts=["Collect receipts", "Export credit card PDF", "Submit to accounting"],
            db_session=db,
        )

        # Due today tasks
        t_today1 = task_service.create_full_task(
            title="Finalize wireframes for homepage",
            description="Review Figma prototypes with UX team and approve token palette.",
            status="in_progress",
            priority="high",
            project_id=p1.id,
            category="Design",
            due_at=now,
            due_date_only=True,
            planned_for_date=today,
            estimated_minutes=90,
            tag_names=["ui", "design"],
            checklist_texts=["Mobile hero section", "Features grid", "Footer links"],
            db_session=db,
        )

        t_today2 = task_service.create_full_task(
            title="30-minute cardio workout",
            description="Interval run on treadmill followed by stretching.",
            status="todo",
            priority="medium",
            project_id=p3.id,
            category="Health",
            due_at=now,
            due_date_only=True,
            planned_for_date=today,
            estimated_minutes=30,
            tag_names=["fitness"],
            db_session=db,
        )

        # Upcoming tasks
        task_service.create_full_task(
            title="Deploy staging environment to AWS",
            description="Configure Terraform state and verify container health checks.",
            status="todo",
            priority="high",
            project_id=p1.id,
            category="DevOps",
            due_at=now + timedelta(days=3),
            due_date_only=False,
            estimated_minutes=120,
            tag_names=["cloud", "backend"],
            db_session=db,
        )

        task_service.create_full_task(
            title="Schedule annual dental checkup",
            status="todo",
            priority="low",
            project_id=p3.id,
            category="Personal",
            due_at=now + timedelta(days=6),
            due_date_only=True,
            estimated_minutes=15,
            tag_names=["health"],
            db_session=db,
        )

        # Completed task
        task_service.create_full_task(
            title="Setup PostgreSQL database schema and migrations",
            description="Configured Alembic and validated foreign key cascades.",
            status="done",
            priority="urgent",
            project_id=p1.id,
            category="Backend",
            due_at=now - timedelta(days=1),
            estimated_minutes=60,
            tag_names=["database"],
            db_session=db,
        )

        # Recurrence Series
        print("🔄 Creating recurring weekly series...")
        recurrence_service.create_recurrence_series(
            title="Weekly Sprint Retrospective & Planning",
            frequency="weekly",
            interval=1,
            weekdays=[0],  # Monday
            start_date=today,
            priority="high",
            project_id=p1.id,
            category="Management",
            estimated_minutes=45,
            db_session=db,
        )

    SessionManager.lock()
    print("✅ Seed completed successfully! You can now run 'streamlit run app.py' to explore TaskVault.")


if __name__ == "__main__":
    seed_workspace()
