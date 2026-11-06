# PRIVATE TASK MANAGER — COMPLETE BUILD SPECIFICATION

**Document purpose:** This file is the complete product, UX, architecture, security, data, implementation, and testing specification for an AI coding agent. The agent must be able to build the application from this document without needing additional product decisions.

**Product type:** Private, password-protected, single-owner productivity and to-do web app.

**Target framework:** Python + Streamlit.

**Primary deployment target:** Streamlit Community Cloud, backed by a managed PostgreSQL database (for example, Supabase Postgres or another hosted PostgreSQL provider).

**Local development:** SQLite may be used as a convenient local database. It must not be the production persistence strategy on Streamlit Community Cloud.

**Default user model:** One owner uses one private workspace. Do not build public registration, team workspaces, or multi-tenant features in the first version. Design the data layer so multi-user support could be added later without a rewrite.

**Product philosophy:** Fast to use, genuinely useful every day, visually polished, dependable, private, and maintainable. Do not add features merely because they sound impressive. Every feature must work end-to-end.

---

# 1. PRODUCT VISION

Build a modern personal task-management application that combines the speed of a simple to-do list with the organization and productivity features of a serious task manager. The app should let the owner capture tasks instantly, organize them into projects, plan the day, track progress, manage recurring responsibilities, and review productivity over time.

The app must open to a password lock screen. After successful unlock, the owner enters a clean dashboard showing what matters now: overdue tasks, today's tasks, upcoming deadlines, progress, and a prominent quick-add action.

The app should feel like a focused personal command center—not a cluttered enterprise project-management platform.

## 1.1 Product goals

1. Make adding a task extremely fast: a basic task should take only a title and one action to save.
2. Make it easy to identify what must be done next.
3. Support both quick personal tasks and larger tasks with projects, subtasks, checklists, deadlines, and notes.
4. Keep tasks saved permanently across browser reloads, sessions, app restarts, and hosted deployments.
5. Protect the workspace with a meaningful server-side password gate and automatic locking.
6. Make it easy to find, filter, edit, complete, archive, restore, export, and back up tasks.
7. Provide useful productivity insights without turning the app into a noisy gamification product.
8. Work well on desktop and remain usable on mobile browsers.

## 1.2 Non-goals for version 1

- No public social feed, followers, likes, or collaboration system.
- No team/member management or complex role permissions.
- No AI task generation or AI chatbot requirement.
- No paid subscription or billing system.
- No native iOS/Android app.
- No guarantee of push notifications or scheduled email delivery while the Streamlit process is asleep.
- No claim of end-to-end encryption. The password gate controls access to the application; it does not make task content unreadable to the database provider or a compromised application server.

---

# 2. PRODUCT NAME AND VISUAL DIRECTION

Use **TaskVault** as the working product name. Keep the name in one central configuration constant so it can be renamed easily.

## 2.1 Visual identity

Create a premium, calm, modern interface inspired by high-quality productivity software. The UI should feel intentional and refined rather than like a default Streamlit demo.

Recommended design direction:

- Dark mode as the default theme, with a proper light mode option.
- Deep charcoal / near-black surfaces, subtle borders, restrained accent color, readable typography.
- A single clear accent color for primary actions and progress indicators.
- Green for completed/success states, amber for due-soon/warnings, red for overdue/urgent states.
- Rounded cards with restrained shadows or borders; avoid excessive gradients and glassmorphism.
- Strong spacing, consistent alignment, and a clear typography hierarchy.
- Use icons consistently, preferably through a supported icon library or Streamlit's built-in icon support.
- Do not use emoji as the only way to communicate task status or priority. Emojis may be optional decoration.

## 2.2 Layout

Desktop layout:

- Fixed or persistent left navigation/sidebar.
- Main content area with page title, a short context line, and primary action.
- Dashboard cards arranged in a responsive grid.
- Tasks shown as clean rows/cards with title, due date, priority, project, and completion control.
- Detail/edit experience should not force the user through a long sequence of pages. Use a dialog, expander, or focused detail view where appropriate.

Mobile layout:

- Sidebar should collapse cleanly.
- Main actions and task controls must remain usable at narrow widths.
- Avoid wide tables that require horizontal scrolling for ordinary task management.
- Use stacked task cards on narrow screens.

## 2.3 Streamlit UI implementation rules

- Use Streamlit's native layout, forms, dialogs, columns, tabs, navigation, and session-state features where appropriate.
- Use `st.navigation` / `st.Page` if supported by the selected Streamlit version; otherwise use the standard multipage mechanism cleanly.
- Use custom CSS only for visual polish and responsive refinements. Do not rely on fragile CSS selectors that break whenever Streamlit changes internal markup.
- Do not put large quantities of raw HTML into the app just to imitate a frontend framework.
- Do not use `unsafe_allow_html=True` to render user-entered task descriptions, notes, tags, or imported content.
- Use forms for multi-field create/edit screens to avoid saving incomplete data on every widget interaction.
- Give every widget a stable, unique key.
- Keep database operations outside the UI-rendering code where practical.

---

# 3. AUTHENTICATION AND APP LOCK

This is a required feature, not a decorative login screen.

## 3.1 First-run setup

On the first launch, if no password has been configured, show a setup screen with:

- Product name and a short privacy message.
- New password field.
- Confirm password field.
- Password strength guidance.
- Optional recovery-code setup/generation.
- A clear **Create private workspace** button.

Password requirements:

- Minimum 12 characters.
- Allow long passphrases and spaces where practical.
- Do not require arbitrary mixtures of uppercase, lowercase, digits, and symbols if the password is already long and strong.
- Reject empty values and a password that does not match confirmation.
- Do not log or display the password.

Generate a cryptographically random recovery code only if the owner opts into recovery. Display it once with a clear warning to store it safely. Store only a secure hash/verifier of the recovery code, never the plaintext recovery code.

## 3.2 Unlock screen

When the app is locked, show only:

- Product name/logo mark.
- A short message such as "Your workspace is locked. Enter your password to continue."
- Password input.
- Unlock button.
- Optional show/hide password control if it can be implemented safely.
- Recovery-code flow if enabled.
- A neutral error message on failure.

Do not render task titles, descriptions, dashboard metrics, project names, settings, or other private data before unlock.

## 3.3 Password storage and verification

Mandatory security rules:

- Never store the password in plaintext.
- Use **Argon2id** through a maintained password-hashing library such as `argon2-cffi`.
- Use a unique random salt per password. Use a library that correctly manages salts and encoded hash parameters.
- Verify passwords using the library's verification function and constant-time-safe behavior.
- Do not use SHA-256, MD5, plain SHA-1, or any fast general-purpose hash as the password-storage algorithm.
- Do not place the actual password or password hash in source code, Git, a public config file, logs, analytics, or an exception message.
- Keep application secrets in Streamlit secrets or environment variables, never in committed source files.
- Benchmark the Argon2id configuration on the hosting environment. Follow current OWASP guidance and choose a practical memory/time cost that does not make the app unusably slow.

## 3.4 Failed-attempt protection

Implement persistent failed-login tracking in the database (not only in `st.session_state`).

Default policy:

- Allow up to 5 failed attempts in a rolling 15-minute window.
- After the limit, temporarily block further attempts for 15 minutes.
- Increase the delay for repeated lockout events, with a reasonable cap (for example, up to 1 hour).
- Reset or age out failed-attempt records after successful authentication according to the chosen policy.
- Use a generic error such as "Unable to unlock. Check your password or try again later." Do not reveal whether a password, recovery code, or account exists.
- Do not let a page refresh reset the persistent failure counter.

The exact rate-limit implementation must be atomic enough to avoid trivial bypasses from multiple browser tabs. If the app is exposed publicly, add infrastructure-level rate limiting where the host supports it.

## 3.5 Session locking

Required controls:

- Manual **Lock now** action in the main navigation/header.
- Automatic inactivity lock with a default of 10 minutes.
- Configurable timeout in Settings: 5, 10, 15, 30, or 60 minutes.
- Lock again when a new browser session is created unless a deliberately implemented secure persistent-auth mechanism is chosen.
- Each browser tab/session must independently pass the app's unlock check.
- On lock, clear sensitive task data from transient session state and return to the lock screen.
- A session must not remain unlocked merely because another session is unlocked.

Implementation note: Streamlit Session State is session-scoped and tied to the browser's WebSocket connection; it is not durable storage. It may be used to hold the current session's unlocked flag and last-activity timestamp, but it must not store the only copy of any task or security configuration. The app must re-check the session's authorization before rendering private pages and before every data-changing action. Handle browser refresh/reconnect behavior safely. If an exact inactivity countdown is needed, use a supported Streamlit fragment/refresh approach and do not let the timer's own reruns count as user activity.

## 3.6 Password change

Settings must include a password-change flow:

1. Enter current password.
2. Enter new password.
3. Confirm new password.
4. Validate and store a new Argon2id hash.
5. Revoke/lock all other active app sessions where the architecture permits. At minimum, require the current session to re-authenticate and ensure newly created sessions require the new password.

Never email or display the old password; it cannot be recovered from a secure hash.

## 3.7 Recovery behavior

If recovery code was enabled:

- Allow recovery-code verification using a secure one-way verifier.
- Require creation of a new password after successful recovery.
- Invalidate the recovery code after use and generate a new one only if the owner explicitly chooses.

If recovery was not enabled, do not invent a secret backdoor or silently reset the password. Explain that the owner must follow the documented administrator/database recovery procedure. Document the risks and steps. Avoid building an insecure "forgot password" button that anyone can abuse.

## 3.8 Security boundary: what this lock does and does not do

The app password is an application access gate. It is not a substitute for hosting-level access control, and it is not end-to-end encryption. A person with administrative access to the hosting account, application server, or database may still be able to access stored task content.

For a public URL containing private personal information, prefer an additional identity-provider/hosting access layer (for example, Streamlit's supported OpenID Connect login or an identity-aware proxy) in front of the app. The app's own password gate can remain as an extra layer. Do not describe the app as "unhackable" or "military-grade."

---

# 4. CORE TASK MANAGEMENT

## 4.1 Task creation

A task must support these fields:

| Field | Required? | Details |
|---|---:|---|
| Title | Yes | Required, trimmed, sensible maximum length (for example 200 characters). |
| Description / notes | No | Multi-line plain text; support longer notes with a safe limit. |
| Status | Yes | To Do, In Progress, Done. |
| Priority | Yes | Low, Medium, High, Urgent. Default Medium. |
| Due date | No | Date picker. |
| Due time | No | Optional time; only meaningful when a due date exists. |
| Project | No | Link to a project. |
| Tags | No | Multiple labels. |
| Category | No | Optional category such as Personal, School, Work, Health, or Custom. |
| Estimated duration | No | Minutes, with quick values such as 5, 15, 30, 60, 90. |
| Actual duration | No | Optional total tracked minutes. |
| Start date | No | Optional planned start date. |
| Parent task | No | Allows subtasks. |
| Recurrence | No | Daily, weekdays, weekly, monthly, yearly, or custom interval. |
| Checklist | No | Small actionable items inside a task. |
| Created timestamp | Automatic | Stored in UTC. |
| Updated timestamp | Automatic | Stored in UTC. |
| Completed timestamp | Automatic | Set on completion; clear or retain history according to status transition policy. |

Quick-add must require only the title. All other fields may be filled in later.

## 4.2 Task actions

Every task should support:

- Mark complete / mark incomplete.
- Change status.
- Edit details.
- Change priority.
- Set or change due date/time.
- Move to another project.
- Add/remove tags.
- Add checklist items.
- Add subtasks.
- Duplicate task.
- Archive task.
- Delete task (soft delete to Trash).
- Restore from Trash.

For destructive actions, show a confirmation or provide a short-lived Undo action. Do not use confirmation dialogs for routine actions such as completing a task.

## 4.3 Task status rules

Use three active statuses:

- **To Do** — not started.
- **In Progress** — currently being worked on.
- **Done** — completed.

Archived and Deleted are storage/lifecycle states, not active workflow statuses. An archived task is hidden from normal active views but remains searchable in Archive. A deleted task enters Trash and can be restored before permanent deletion.

## 4.4 Priority behavior

Use four priority levels:

- Urgent
- High
- Medium
- Low

Use restrained visual distinction. Priority must be represented by text and/or an icon as well as color so the app remains understandable to color-blind users.

## 4.5 Due-date behavior

- Overdue means due date/time is earlier than the current time and task is not Done or Archived.
- Due today means the due date falls on the owner's local calendar date.
- Due soon should use a configurable horizon; default 7 days.
- Tasks with no due date must remain valid and visible in Inbox/All Tasks.
- Store timestamps in UTC and convert them using the owner's configured IANA timezone for display and date calculations.
- Do not silently change a task's due date when the owner changes timezone. Preserve the underlying instant where a time exists; date-only tasks should follow the documented date-only handling strategy.

## 4.6 Subtasks

- A task may have multiple subtasks.
- Subtasks may be independently completed.
- Display parent progress (for example, 3 of 5 subtasks complete).
- Completing a parent task should ask whether to complete all open subtasks or leave them open; choose a safe, explicit behavior.
- A subtask should not be allowed to become its own parent or create circular parent-child relationships.
- Keep nesting to one level in version 1 unless the implementation can support deeper nesting cleanly.

## 4.7 Checklists

Each task can contain a simple checklist of items:

- Add checklist item.
- Check/uncheck item.
- Rename item.
- Reorder items.
- Delete item.
- Show progress count.

Checklist items are distinct from subtasks: checklist items are lightweight steps; subtasks are independently managed tasks.

## 4.8 Bulk actions

Allow selection of multiple tasks and the following bulk actions:

- Mark Done.
- Change priority.
- Move to project.
- Add/remove a tag.
- Archive.
- Delete to Trash.

Bulk operations must validate all task IDs and report success/failure clearly. Do not silently skip errors.

---

# 5. NAVIGATION AND TASK VIEWS

Create the following main navigation destinations.

## 5.1 Dashboard / Home

The dashboard is the default page after unlock. It should show:

- Greeting or neutral heading based on local time (optional).
- Current date.
- Quick-add task input/button.
- Tasks due today.
- Overdue tasks.
- Upcoming tasks (next 7 days).
- Total active tasks.
- Completed tasks today or this week.
- Overall completion/progress metric for the current week.
- Priority breakdown.
- Small productivity chart for the last 7 or 30 days.
- A compact "Next up" list sorted by due date, priority, then creation time.

Do not overwhelm the dashboard with every statistic. Place secondary analytics lower on the page or in a collapsible section.

## 5.2 Inbox

A fast capture area for tasks that have not yet been organized.

- Show tasks without a project and/or tasks explicitly assigned to Inbox.
- Quick add.
- Fast edit of title, priority, and due date.
- Allow the owner to assign tasks to projects later.

## 5.3 My Day / Today

- Show tasks due today plus tasks manually planned for today.
- Separate overdue items from today's items.
- Allow a task to be marked as today's focus without changing its due date.
- Include a clear empty state when no tasks are planned.
- Provide a compact progress indicator.

## 5.4 Upcoming

- Show tasks due over the next 7/14/30 days.
- Allow horizon switching.
- Group by date.
- Highlight tasks that are overdue or approaching their deadline.

## 5.5 All Tasks

A complete searchable task list with:

- Search by title and description.
- Filter by status, priority, project, tag, category, due date, and creation date.
- Sort by due date, priority, created date, updated date, title, or manual order.
- Toggle between list and board views.
- Pagination or sensible incremental rendering for large task collections.
- A clear action to reset filters.

## 5.6 Board / Kanban

Provide columns:

- To Do
- In Progress
- Done

Tasks can be moved between columns using a supported interaction. If drag-and-drop is not reliably supported by the selected Streamlit components, provide clear status selectors or action buttons instead of shipping a broken drag-and-drop imitation.

## 5.7 Calendar

Provide month and week views, with tasks displayed on their due dates.

- Navigate to previous/next month or week.
- Click/select a date to view its tasks.
- Add a task for a selected date.
- Show due time when available.
- Use priority/status indicators.

A calendar component may be used if it is maintained and works reliably with the selected Streamlit version. Otherwise build a simple responsive calendar grid. Calendar events must link back to task details.

## 5.8 Projects

Projects group related tasks.

Each project must support:

- Name.
- Optional description.
- Optional color/icon.
- Created and updated timestamps.
- Active/completed/archived project state.
- Task count.
- Completion percentage.
- Project-specific task view and filters.

Allow create, rename, edit, archive, and delete. Deleting a project must not silently delete its tasks. Ask whether to move its tasks to Inbox or cancel. Archiving a project should preserve its tasks and history.

## 5.9 Tags and categories

- Create, rename, and delete tags.
- A task may have multiple tags.
- Prevent duplicate tag names after case/whitespace normalization.
- Provide tag filters and tag counts.
- Include optional starter categories, but allow customization or disabling.

## 5.10 Completed

- Show recently completed tasks.
- Filter by completion date, project, and tag.
- Allow reopening a completed task.
- Show completion timestamp.
- Keep completed-task data for analytics.

## 5.11 Archive and Trash

Archive:

- List archived tasks.
- Restore task to active tasks.
- Permanently delete if desired.

Trash:

- Soft-deleted tasks remain restorable for 30 days by default.
- Restore task.
- Permanently delete one task.
- Empty Trash with strong confirmation.
- Permanent deletion must remove linked checklist items and other dependent records safely.

---

# 6. RECURRING TASKS

Recurring tasks are a high-value feature and must be implemented carefully.

Supported recurrence presets:

- Every day.
- Weekdays (Monday–Friday).
- Every week on selected weekday(s).
- Every month on a selected day.
- Every year on a selected date.
- Custom interval such as every 2 days or every 3 weeks.

Rules:

- A recurring task is a series/template with a recurrence rule and a next occurrence.
- Completing one occurrence should create or activate the next occurrence according to the recurrence rule.
- Completing an occurrence must not accidentally mark every future occurrence Done.
- Each occurrence must have its own completion timestamp and history.
- Generation must be idempotent: rerunning the app must not create duplicate occurrences.
- Define what happens when an occurrence is missed. Default: create the next occurrence based on the recurrence schedule, not an unlimited backlog of duplicate overdue instances. Offer a setting for whether to keep missed instances or skip them.
- Allow editing only this occurrence or the entire series.
- Allow pausing and ending a series.
- Handle month lengths, leap years, daylight-saving transitions, and timezone changes predictably.

If full recurrence support cannot be completed in one pass, do not fake it. Implement daily, weekly, and monthly recurrence first with tests, then extend the recurrence engine.

---

# 7. PRODUCTIVITY FEATURES

## 7.1 Focus mode

Create a distraction-minimized focus page:

- Select one task to focus on.
- Display the task title, notes, priority, and checklist.
- Hide unnecessary navigation details while focused, while retaining a way to exit.
- Optional focus timer.
- Mark task Done or return it to the task list.

## 7.2 Pomodoro / focus timer

Provide an optional timer with these defaults:

- Focus: 25 minutes.
- Short break: 5 minutes.
- Long break: 15 minutes.
- Long break after 4 completed focus sessions.

Controls:

- Start, pause, resume, reset, skip.
- Select associated task.
- Show remaining time.
- Record completed focus sessions.
- Allow custom focus and break durations in Settings.

Important implementation detail: do not assume a Streamlit Python sleep loop is a reliable browser timer. Use timestamps and supported reruns/fragments so the timer can recover its state after reruns. If the app is closed or asleep, do not claim it continued to run in the background unless a real browser-side implementation proves that behavior.

## 7.3 Time tracking

- Allow manual entry of actual time spent.
- Allow starting/stopping a focus session linked to a task.
- Store session start/end timestamps and duration.
- Show total time spent per task and project.
- Prevent negative or impossible durations.
- Do not automatically start tracking without user intent.

## 7.4 Daily planning

- Allow pinning or selecting tasks for today's focus.
- Allow setting an estimated duration per task.
- Show total estimated workload for the day.
- Warn if planned task time exceeds a user-defined daily capacity.
- Keep this as a planning estimate, not a rigid schedule.

## 7.5 Productivity insights

Create an Insights page with useful, honest metrics:

- Tasks completed per day/week/month.
- Completion trend.
- Completion rate (define denominator clearly; for example, tasks due in the selected period that were completed by period end).
- Overdue task count over time if historical data is available.
- Average completion time only when valid created/completed timestamps exist.
- Time tracked per project/category.
- Priority distribution.
- Most productive day of week, only when enough data exists.

Avoid misleading metrics. Clearly state the selected date range and how a metric is calculated. Do not invent historical task data.

## 7.6 Streaks and goals (optional, restrained)

Optional settings:

- Daily completion goal.
- Weekly completion goal.
- Current completion streak.
- Best streak.

Streaks must not punish the owner or create fake urgency. Allow disabling them. Define how timezones and days with no scheduled tasks are treated.

---

# 8. REMINDERS AND NOTIFICATIONS

## 8.1 In-app reminders (required)

On app open and during active use:

- Show overdue tasks.
- Show tasks due today.
- Show tasks due soon.
- Display a small notification/alert area without blocking the whole app.
- Allow dismissing or snoozing a reminder.
- Avoid repeating the same reminder on every rerun. Store reminder-dismissal/snooze state where necessary.

## 8.2 Email notifications (optional future extension)

Email reminders require a real email provider and a dependable scheduler. Do not pretend that a Streamlit page rerun is a scheduled background worker. Streamlit Community Cloud may hibernate inactive apps, so it cannot by itself guarantee that an email is sent at a precise time while the app is asleep.

If email reminders are implemented:

- Make them opt-in.
- Use a dedicated email service or SMTP credentials stored in secrets.
- Use an external scheduled job/worker (for example, a scheduled serverless function or cron service) for dependable delivery.
- Do not expose SMTP credentials in the UI or source code.
- Log send status without logging private task descriptions unnecessarily.

## 8.3 Browser notifications (optional future extension)

Browser notifications require explicit browser permission and a supported frontend implementation. Do not claim support unless tested in the deployed browser. Explain permission requirements. Do not rely on browser notifications as the only reminder channel.

---

# 9. SEARCH, FILTERING, SORTING, AND QUICK ACTIONS

## 9.1 Global search

Provide a search field accessible from the main interface. Search:

- Task titles.
- Task descriptions/notes.
- Project names.
- Tag names.

Search must be case-insensitive and safe for user input. Use parameterized database queries.

## 9.2 Quick filters

Provide one-click filters:

- All active.
- Due today.
- Overdue.
- High priority.
- Urgent.
- In progress.
- No due date.
- Completed this week.

## 9.3 Sorting

Support:

- Due date ascending/descending.
- Priority (Urgent first).
- Recently created.
- Recently updated.
- Alphabetical title.
- Manual order where practical.

Use stable secondary sort rules so the task list does not jump unpredictably.

## 9.4 Keyboard-friendly behavior

- Make form navigation work with keyboard.
- Enter should submit quick-add where it does not conflict with multiline descriptions.
- Escape should close supported dialogs.
- Provide visible focus states.
- Do not require drag-and-drop for essential functionality.

---

# 10. SETTINGS

Create a Settings page with the following groups.

## 10.1 Appearance

- Dark / Light / System theme if supported.
- Compact / Comfortable task density.
- Show/hide dashboard analytics.

## 10.2 Preferences

- Timezone (IANA identifier such as `America/New_York`).
- Week starts Monday or Sunday.
- Default task priority.
- Default due-soon horizon.
- Default task view (List / Board / Calendar).
- Daily task capacity in minutes.
- Date/time display preference where relevant.

## 10.3 Security

- Change password.
- Configure/change recovery code if supported.
- Automatic lock timeout.
- Lock now.
- View a concise security status (password configured, recovery configured, lock timeout).

## 10.4 Data management

- Export all data.
- Import backup.
- Download CSV task export.
- Download JSON backup.
- Restore from JSON backup with validation and a clear merge/replace choice.
- Clear all data with a high-friction confirmation requiring the owner to type a phrase such as `DELETE ALL DATA`.

## 10.5 About

- App name and version.
- Database connection status without revealing credentials.
- Short privacy statement.
- Documentation/help.

---

# 11. DATA EXPORT, IMPORT, BACKUP, AND RESTORE

## 11.1 CSV export

Allow export of active tasks or all tasks. Include useful fields:

- ID.
- Title.
- Description.
- Status.
- Priority.
- Due date/time.
- Project.
- Tags.
- Category.
- Estimated minutes.
- Actual minutes.
- Created timestamp.
- Updated timestamp.
- Completed timestamp.

CSV must be UTF-8 encoded. Protect against spreadsheet formula injection when exporting user-controlled fields by safely escaping values beginning with formula-trigger characters such as `=`, `+`, `-`, or `@`.

## 11.2 JSON backup

Create a versioned JSON backup format containing:

- Schema/version number.
- Export timestamp.
- Application settings that are safe to export.
- Projects.
- Tasks and subtasks.
- Checklist items.
- Tags and task-tag links.
- Recurrence rules and series references.
- Focus/time-tracking records if implemented.

Do not export the Argon2 password hash, recovery-code verifier, active session state, or database credentials by default.

## 11.3 Import behavior

- Validate JSON schema and version before changing data.
- Reject malformed files with a useful error.
- Preview counts before import.
- Offer **Merge** and **Replace all data** options.
- Merge must handle duplicate IDs safely and avoid duplicate tags/projects.
- Replace must require strong confirmation and run transactionally.
- Do not overwrite the app's security configuration during normal data import.
- Create a backup before a destructive replace operation if the database supports it.

---

# 12. DATABASE AND DATA MODEL

Use a relational database. Production should use managed PostgreSQL. Local development may use SQLite through the same repository/service layer.

Use SQLAlchemy 2.x or an equivalent well-maintained database abstraction. Use migrations (Alembic recommended) for schema changes. Do not scatter raw SQL throughout Streamlit page files.

## 12.1 Required tables

### `app_settings`
One row for the single-owner app configuration.

Fields:

- `id` (primary key; singleton row pattern).
- `password_hash` (Argon2id encoded hash).
- `recovery_code_hash` (nullable secure verifier/hash).
- `timezone` (default `America/New_York`, editable).
- `theme` (default `dark`).
- `lock_timeout_minutes` (default 10).
- `week_starts_on` (default Monday).
- `default_priority` (default Medium).
- `due_soon_days` (default 7).
- `created_at`, `updated_at`.

Never expose the password hash or recovery verifier to the UI.

### `login_attempts`
Fields:

- `id`.
- `attempted_at` (UTC).
- `succeeded` (boolean).
- `source_fingerprint` (optional privacy-conscious, non-reversible or truncated identifier if needed; do not collect invasive device data).
- `blocked_until` (nullable UTC timestamp).

Keep only the minimum information needed for abuse protection. Define a retention cleanup policy.

### `projects`
Fields:

- `id` (UUID primary key).
- `name`.
- `description` (nullable).
- `color` (nullable).
- `icon` (nullable).
- `status` (active/completed/archived).
- `created_at`, `updated_at`, `archived_at`.

### `tasks`
Fields:

- `id` (UUID primary key).
- `title`.
- `description` (nullable).
- `status` (todo/in_progress/done).
- `priority` (low/medium/high/urgent).
- `project_id` (nullable foreign key).
- `parent_task_id` (nullable self-referencing foreign key).
- `category` (nullable).
- `due_at` (nullable UTC timestamp) or a carefully defined date-only field when a date without time must be preserved.
- `start_at` (nullable UTC timestamp).
- `planned_for_date` (nullable local date for My Day planning).
- `estimated_minutes` (nullable integer).
- `actual_minutes` (nullable integer).
- `is_archived` (boolean or archive timestamp).
- `deleted_at` (nullable UTC timestamp for Trash).
- `completed_at` (nullable UTC timestamp).
- `created_at`, `updated_at`.
- `sort_order` (nullable numeric/integer for manual ordering).
- `recurrence_series_id` (nullable foreign key/reference).
- `occurrence_key` (nullable unique key to prevent duplicate generated occurrences).

Add indexes for due date, status, priority, project, deleted/archive state, parent task, and common search patterns as appropriate.

### `tags`
Fields: `id`, `name`, `normalized_name`, `created_at`.

Add a unique constraint on `normalized_name`.

### `task_tags`
Fields: `task_id`, `tag_id`.

Use a composite primary key and foreign keys.

### `checklist_items`
Fields:

- `id`.
- `task_id`.
- `text`.
- `is_completed`.
- `sort_order`.
- `created_at`, `updated_at`.

### `recurrence_series`
Fields:

- `id`.
- `template_task_id` or template fields.
- `frequency`.
- `interval`.
- `weekdays` (JSON/array as supported).
- `day_of_month` (nullable).
- `start_date`.
- `end_date` (nullable).
- `next_occurrence_at`.
- `timezone`.
- `is_paused`.
- `missed_occurrence_policy`.
- `created_at`, `updated_at`.

### `focus_sessions` (if focus/time tracking is implemented)
Fields: `id`, `task_id` (nullable), `started_at`, `ended_at`, `duration_seconds`, `session_type`, `created_at`.

### `activity_log` (optional but useful)
Store minimal events such as task created/completed/archived/restored and password changed. Do not store raw passwords or unnecessarily duplicate private descriptions.

## 12.2 Data rules

- Generate UUIDs for primary identifiers.
- Use UTC for timestamps.
- Use timezone-aware datetime handling.
- Use database transactions for multi-step operations.
- Use foreign keys and appropriate cascade behavior.
- Use parameterized queries / ORM expressions.
- Validate all user-provided values server-side.
- Keep business logic in service modules, not page scripts.
- Never treat Streamlit Session State as persistent storage.

---

# 13. RECOMMENDED TECHNICAL ARCHITECTURE

## 13.1 Stack

Required:

- Python 3.11+ (target a currently supported Python version compatible with hosting).
- Current stable Streamlit release.
- SQLAlchemy 2.x.
- PostgreSQL in production.
- SQLite for local-only development if desired.
- `argon2-cffi` for password hashing.
- Alembic for migrations.
- `python-dateutil` or a well-tested recurrence implementation for date rules.
- `pandas` only where it materially helps with tabular export/analytics.
- `plotly` or Streamlit-native charting for analytics.
- `pytest` for tests.
- `ruff` for linting/format checks.

Use a maintained PostgreSQL driver such as `psycopg`.

Do not add unnecessary packages. Pin tested versions in `requirements.txt` or use a lockfile. Verify the selected versions install successfully on the target Streamlit host.

## 13.2 Application layers

Separate the app into clear layers:

1. **Presentation:** Streamlit pages, reusable UI components, layout, forms.
2. **Services:** task operations, recurrence logic, project/tag management, analytics, backup/import, authentication policy.
3. **Repositories:** database queries and persistence.
4. **Models:** SQLAlchemy models and data validation.
5. **Security:** password hashing, recovery verification, rate limiting, session checks, secret loading.
6. **Configuration:** environment/secrets, database URL, app defaults.

Pages should call service functions rather than directly manipulating database tables.

## 13.3 Suggested project structure

```text
 taskvault/
 ├── app.py
 ├── requirements.txt
 ├── README.md
 ├── .gitignore
 ├── .streamlit/
 │   └── config.toml
 ├── pages/                         # Use only if not using st.navigation
 │   ├── dashboard.py
 │   ├── inbox.py
 │   ├── today.py
 │   ├── upcoming.py
 │   ├── tasks.py
 │   ├── calendar.py
 │   ├── projects.py
 │   ├── insights.py
 │   └── settings.py
 ├── taskvault/
 │   ├── __init__.py
 │   ├── config.py
 │   ├── database.py
 │   ├── models/
 │   │   ├── __init__.py
 │   │   ├── task.py
 │   │   ├── project.py
 │   │   ├── tag.py
 │   │   ├── security.py
 │   │   └── focus.py
 │   ├── repositories/
 │   │   ├── task_repository.py
 │   │   ├── project_repository.py
 │   │   ├── tag_repository.py
 │   │   └── security_repository.py
 │   ├── services/
 │   │   ├── task_service.py
 │   │   ├── project_service.py
 │   │   ├── recurrence_service.py
 │   │   ├── analytics_service.py
 │   │   ├── backup_service.py
 │   │   ├── reminder_service.py
 │   │   └── focus_service.py
 │   ├── security/
 │   │   ├── passwords.py
 │   │   ├── access_control.py
 │   │   └── rate_limit.py
 │   ├── ui/
 │   │   ├── components.py
 │   │   ├── styles.py
 │   │   ├── task_cards.py
 │   │   ├── task_forms.py
 │   │   └── navigation.py
 │   └── utils/
 │       ├── dates.py
 │       ├── validation.py
 │       └── formatting.py
 ├── migrations/
 └── tests/
     ├── conftest.py
     ├── test_auth.py
     ├── test_tasks.py
     ├── test_projects.py
     ├── test_recurrence.py
     ├── test_backup.py
     └── test_access_control.py
```

The exact structure may be improved by the coding agent, but maintain the separation of concerns.

## 13.4 Database configuration

- Read production database connection details from `st.secrets` or environment variables.
- Use a single configuration abstraction so local and hosted environments behave consistently.
- If a production database URL is missing in a hosted environment, show a clear setup error. Do not silently fall back to a temporary SQLite database and risk losing tasks.
- Local development may default to a local SQLite file with a clear notice.
- Use connection pooling settings appropriate for the chosen host. Avoid creating a new database engine on every rerun; cache the engine/connection factory safely with `st.cache_resource` where appropriate.
- Do not cache private task query results globally across users/sessions. Cache only safe resources or use session-aware cache keys and explicit invalidation.

## 13.5 Streamlit execution model

Streamlit reruns the script after many widget interactions. Design the application to work with this behavior:

- Use forms and callbacks deliberately.
- Keep stable widget keys.
- Use session state only for transient UI/session state.
- Never put a database connection, password, task collection, or other sensitive persistent data in an unsafe global variable.
- Avoid unnecessary full database reads on every tiny interaction.
- Use fragments only where they improve performance or timer behavior.
- Make writes idempotent where reruns could otherwise duplicate records.

---

# 14. DEPLOYMENT AND OPERATIONS

## 14.1 Local setup

The repository must include clear instructions for:

1. Creating and activating a Python virtual environment.
2. Installing dependencies.
3. Configuring local environment variables or `.streamlit/secrets.toml`.
4. Initializing database migrations/schema.
5. Running the app with `streamlit run app.py`.
6. Running tests and lint checks.

Provide a `.env.example` or sample secrets template containing placeholders only. Never include real secrets.

## 14.2 Streamlit Community Cloud deployment

Document the steps:

1. Push the project to a GitHub repository.
2. Create a managed PostgreSQL database.
3. Configure database URL and any required application secrets in the Streamlit Community Cloud secrets panel.
4. Deploy the correct entrypoint file.
5. Confirm database connectivity and run migrations safely.
6. Complete first-run password setup.
7. Test unlock, lock, task creation, reload persistence, and backup export on the live deployment.

Important: Community Cloud does not guarantee persistence of local file storage. Use managed PostgreSQL for task data and an external object-storage service for any future uploaded attachments. Never rely on the hosted app's local disk as the only durable copy.

## 14.3 Secrets

- `.streamlit/secrets.toml` must be in `.gitignore`.
- Provide a `.streamlit/secrets.example.toml` with fake placeholder values only if useful.
- Never print secrets in logs or UI.
- Document how to rotate database credentials.
- Keep application secrets separate from the app password.

## 14.4 Backups

- Encourage regular JSON exports from the UI.
- If the selected database provider supports automated backups, document how to enable them.
- Test restore, not just export.
- Do not claim that a backup exists unless it has actually been created and verified.

## 14.5 Reliability and error handling

- Catch expected database/network errors and show a useful, non-sensitive message.
- Log technical details server-side without leaking passwords, session tokens, or full task descriptions.
- Do not swallow exceptions silently.
- Show a database connection indicator on Settings/About.
- Use transaction rollback on failed writes.
- Ensure duplicate submit/rerun events do not create duplicate tasks.
- Provide loading indicators for slow operations.
- Provide clear empty states and error states for every major page.

---

# 15. PRIVACY AND APPLICATION SECURITY CHECKLIST

The coding agent must implement and verify all applicable items:

- [ ] Password is hashed with Argon2id; no plaintext storage.
- [ ] Recovery code is stored only as a secure verifier/hash.
- [ ] Login attempts are rate-limited persistently.
- [ ] Private pages are not rendered until the current session is unlocked.
- [ ] Every data-changing service verifies access before writing.
- [ ] New sessions start locked.
- [ ] Manual and inactivity locking work.
- [ ] Password change invalidates/requires re-authentication as far as supported.
- [ ] Secrets are stored outside version control.
- [ ] Database access uses parameterized queries or ORM methods.
- [ ] User text is not rendered as unsafe HTML.
- [ ] Import files are validated before database writes.
- [ ] Uploads, if added later, have strict size/type limits and safe filenames.
- [ ] CSV exports are protected against formula injection.
- [ ] Destructive actions require confirmation.
- [ ] Backup exports exclude authentication hashes and credentials by default.
- [ ] Database errors do not expose credentials or SQL details to the user.
- [ ] App makes no false claims of end-to-end encryption or guaranteed background notifications.

Threat-model note: a single-owner password gate protects against casual access through the app URL; it does not protect against a malicious hosting administrator, compromised database credentials, server compromise, or someone who has access to the owner's hosting account. Explain this plainly in the README.

---

# 16. ACCESSIBILITY AND USABILITY

- All actions must have readable labels; do not rely on color alone.
- Maintain sufficient text/background contrast.
- Use clear focus indicators and keyboard-operable controls.
- Use descriptive labels for icon-only buttons (tooltips and accessible labels where supported).
- Keep validation messages next to the relevant field.
- Keep forms short and logically grouped.
- Use consistent date/time formatting.
- Support empty states with a clear next action.
- Avoid unnecessary animation.
- Ensure the interface is usable at desktop and mobile viewport widths.
- Make task completion easy to undo or reverse.

---

# 17. PERFORMANCE EXPECTATIONS

- Normal task-list pages should feel responsive for a personal workspace containing several thousand tasks.
- Fetch only the fields and rows required for the current view.
- Add database indexes based on actual query patterns.
- Paginate or limit large search results.
- Avoid loading every historical task into memory for the dashboard.
- Aggregate analytics in the database where practical.
- Do not use `st.cache_data` for sensitive user-specific data without a safe session-aware cache strategy and invalidation.
- Avoid repeated database engine creation on Streamlit reruns.

---

# 18. TESTING REQUIREMENTS

The coding agent must write and run tests. A feature is not complete merely because it appears on screen.

## 18.1 Authentication tests

- First-run setup creates a password hash and never stores plaintext.
- Correct password unlocks the app.
- Incorrect password is rejected.
- Rate limit activates after the configured failed-attempt threshold.
- Rate limit persists across session refreshes.
- Recovery code works only when configured.
- Recovery code becomes invalid after use.
- Password change requires the current password.
- New password works; old password no longer works.
- A new session starts locked.
- Locked sessions cannot call private data services.
- Manual lock returns the current session to the lock screen.
- Inactivity timeout locks the session according to the configured policy.

## 18.2 Task tests

- Create task with title only.
- Create task with all optional fields.
- Reject empty/whitespace-only title.
- Edit a task and update `updated_at`.
- Mark task Done and set `completed_at`.
- Reopen task and apply the documented completion timestamp policy.
- Sort/filter by due date, status, priority, project, and tag.
- Search title and description.
- Create and complete checklist items.
- Create subtasks and prevent circular references.
- Duplicate task without accidentally duplicating identity or invalid links.
- Archive, restore, soft-delete, restore from Trash, and permanently delete.
- Bulk actions operate on selected tasks only.

## 18.3 Project and tag tests

- Create, edit, archive, and delete project.
- Deleting a project does not silently delete tasks.
- Prevent duplicate normalized tag names.
- Assign/remove tags from tasks.
- Project completion percentage is correct.

## 18.4 Date and recurrence tests

- Overdue and due-today logic uses configured timezone.
- Date-only tasks do not shift unexpectedly across timezones.
- Daily, weekday, weekly, and monthly recurrence generate correct next occurrences.
- Repeated reruns do not create duplicate occurrences.
- Month-end and leap-year handling is correct.
- Daylight-saving transitions are tested.
- Pause/end series works.
- Editing one occurrence does not unexpectedly alter the full series.

## 18.5 Backup/import tests

- CSV export contains expected columns and values.
- CSV formula injection is neutralized.
- JSON export includes all supported task/project data.
- JSON export excludes password hash and credentials.
- Invalid JSON is rejected without modifying the database.
- Merge import does not create duplicate tasks/tags/projects.
- Replace import is transactional and requires confirmation in the UI.
- A backup can be restored successfully in a test database.

## 18.6 UI smoke tests

Use Streamlit's testing support where practical. Verify:

- Locked screen renders before authentication.
- Dashboard renders after unlock.
- Navigation destinations load.
- Forms submit and show validation messages.
- Empty states render correctly.
- Mobile layout remains usable at narrow widths.

---

# 19. ACCEPTANCE CRITERIA — DEFINITION OF DONE

The project is complete only when all of the following are true:

1. The app runs locally using the documented command.
2. A first-time owner can create a password and enter the app.
3. The password is stored only as an Argon2id hash.
4. The lock screen hides all task and project data.
5. Failed-attempt protection works and persists.
6. Manual lock and automatic inactivity lock work.
7. Tasks can be created, viewed, edited, completed, reopened, archived, deleted, and restored.
8. Projects, tags, subtasks, and checklists work end-to-end.
9. Dashboard, Inbox, Today, Upcoming, All Tasks, Board, Calendar, Completed, Archive, and Trash views work or are explicitly deferred in the implementation report.
10. Search, filter, sorting, and bulk actions work.
11. Recurrence works for the recurrence patterns claimed by the UI and has tests.
12. Data persists across browser reloads, new sessions, and app restarts through the configured database.
13. Hosted deployment uses managed PostgreSQL or another durable external store, not local ephemeral files as the only data source.
14. JSON backup/export and validated import work.
15. Settings persist correctly.
16. The app is responsive and visually consistent.
17. The README explains setup, secrets, deployment, backups, password recovery, and the limits of the password gate.
18. Automated tests pass.
19. No unfinished controls, fake notifications, mock analytics, placeholder buttons, or dead navigation links remain.
20. The coding agent provides a concise implementation report listing completed features, known limitations, environment variables/secrets required, test results, and deployment instructions.

---

# 20. BUILD PRIORITY — IMPLEMENT IN THIS ORDER

The full target is ambitious. Build it in coherent stages, keeping the app usable after each stage. Do not sacrifice correctness to claim every feature is complete.

## Stage 1 — Secure, persistent core (mandatory)

- App shell and visual theme.
- First-run password setup.
- Argon2id password verification.
- Persistent login rate limiting.
- Session unlock, manual lock, inactivity lock.
- Database layer and migrations.
- Create/edit/complete/reopen/delete/restore tasks.
- Priority, due dates, status, projects, tags.
- Dashboard, Inbox, Today, Upcoming, All Tasks.
- Search, filters, sorting.
- JSON and CSV export.
- Managed PostgreSQL deployment configuration.
- Tests for authentication, authorization, persistence, and task CRUD.

## Stage 2 — Organization and planning

- Subtasks and checklists.
- Board/Kanban view.
- Calendar view.
- Completed, Archive, and Trash pages.
- Bulk actions.
- Recurring tasks with tested recurrence engine.
- Project dashboards and progress.

## Stage 3 — Productivity and insights

- Focus mode.
- Pomodoro timer.
- Time tracking.
- Daily workload planning.
- Analytics and trends.
- Goals/streaks if they remain useful and nonintrusive.

## Stage 4 — Optional integrations

- Email reminders using an external scheduler/worker.
- Browser notifications.
- Cloud attachment storage.
- Optional OIDC/identity-provider login as an additional access layer.
- Optional encrypted-field storage only after a deliberate threat model and key-recovery design.

The AI agent should aim to deliver Stages 1 and 2 fully before spending time on Stage 3 or 4. A reliable task manager with secure access and durable data is better than a flashy app with broken persistence.

---

# 21. REQUIRED README CONTENT

The final repository README must explain:

- What TaskVault does.
- Main features.
- Technology stack.
- Project structure.
- Local installation and run commands.
- How to configure a local database.
- How to set up managed PostgreSQL.
- Required secrets/environment variables.
- How to deploy on Streamlit Community Cloud.
- How first-run password setup works.
- How to change a password and use recovery.
- How automatic locking works.
- How to export and restore backups.
- Important security limitations (the password gate is not end-to-end encryption).
- Important hosting limitation (Community Cloud local filesystem is not guaranteed persistent).
- How to run tests and linting.

Suggested configuration names:

```toml
# Example only. Put real values in the Streamlit secrets panel or local
# .streamlit/secrets.toml. Never commit real secrets.
DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE"
APP_ENV = "production"
```

The application must tolerate the secrets being absent during local first-run development only if a safe documented local SQLite mode is enabled. Production must fail clearly rather than silently writing tasks to a disposable local database.

---

# 22. INSTRUCTIONS TO THE AI CODING AGENT

You are responsible for implementing this entire application from this specification.

Follow these instructions strictly:

1. Read this entire Markdown file before writing code.
2. Treat the requirements marked mandatory and the Stage 1/Stage 2 scope as the implementation contract.
3. Do not merely produce a plan, mockup, or code snippets. Create the complete working project in the repository.
4. Inspect the existing repository before changing files. Preserve useful existing work unless it conflicts with this specification.
5. Build the database schema and migrations before building dependent pages.
6. Implement authentication and authorization before exposing task data.
7. Use Argon2id for password hashing. Never store plaintext passwords.
8. Use managed PostgreSQL for hosted persistence. Never rely on Streamlit Community Cloud local files as the only durable data store.
9. Keep UI, services, repositories, and security logic separated.
10. Build functional controls. No button may be decorative or silently do nothing.
11. Do not use fake sample data in production. Demo data may be provided only through an explicit optional seed command or development mode.
12. Do not claim a feature works unless it has been implemented and tested.
13. Do not implement background email/push reminders by pretending the Streamlit app is always awake.
14. Handle Streamlit reruns correctly and prevent duplicate database writes.
15. Validate data server-side and use safe database query patterns.
16. Add automated tests for critical features and run them.
17. Run lint/type checks where configured and fix material issues.
18. Verify the project starts locally.
19. Write complete setup/deployment/security documentation.
20. If a requirement cannot be implemented reliably, explain the blocker in the final report and do not ship a fake implementation.

## Final response required from the coding agent

When implementation is complete, report:

- What was built.
- Which stages/features are complete.
- Which features are intentionally deferred.
- Exact local run command.
- Exact test command and test results.
- Required production secrets/environment variables.
- Exact Streamlit Community Cloud deployment steps.
- Any known limitations or security caveats.

**Final quality standard:** The result should be a polished, reliable, password-protected personal task manager with durable storage—not merely a to-do list demo with a password field.

---

# 23. REFERENCE DOCUMENTATION

Use current official documentation and security guidance while implementing. Re-check these sources because APIs and recommendations can change.

- Streamlit authentication (OpenID Connect, `st.login`, `st.user`, `st.logout`): https://docs.streamlit.io/develop/concepts/connections/authentication
- Streamlit multipage navigation: https://docs.streamlit.io/develop/concepts/multipage-apps/overview
- Streamlit Session State and its limitations: https://docs.streamlit.io/develop/concepts/architecture/session-state
- Streamlit secrets management: https://docs.streamlit.io/develop/concepts/connections/secrets-management
- Streamlit Community Cloud secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- Streamlit connecting to data / SQLite persistence warning: https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

---

**END OF SPECIFICATION**
