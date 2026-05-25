# CLAUDE.md

Operational guide for AI assistants working in this repository. Read this before making changes.

## Project Overview

**Zdrofit Class Booker** is a Telegram bot that monitors group fitness classes at Zdrofit (Polish gym chain, `zdrofit.perfectgym.pl`) and automatically books or notifies users when slots matching their filters become available.

- **Users** authenticate against the unofficial Zdrofit `ClientPortal2` API with their gym credentials (stored encrypted at rest).
- **Filters** describe what each user wants: club, zone, timetable (class type), trainer, time-of-day, weekdays. Each user may have **multiple filters**, each with independent `auto_booking` and **pause** state.
- **Scheduler** runs hourly (cron `minute=0`), processes all users **concurrently** (thread pool + `asyncio.gather` + semaphore), fetches matching classes per filter, books them (if auto-booking) or sends a Telegram notification.
- Deployed via **Docker** on a **Raspberry Pi**.

## Tech Stack

- **Python 3.10+** (CI/dev runs on 3.11)
- **python-telegram-bot 20.7** — async Telegram framework
- **APScheduler** — `BackgroundScheduler` + `CronTrigger`
- **requests** — synchronous HTTP to Zdrofit API (wrapped in `asyncio.to_thread` for concurrency)
- **SQLite 3** — single-file DB at `data/zdrofit.db`
- **cryptography (Fernet)** — symmetric password encryption
- **python-dotenv** — `.env` config loading
- **unittest** — test framework (do not use pytest-only features)
- **Docker / docker compose** — production deployment

## Architecture

```
main.py                 # Entry point — boots bot + scheduler
config/config.py        # Env vars, club catalog, concurrency limits
src/
  api/
    zdrofit_client.py   # ZdrofitAPIClient: authenticate, get_classes, book, cancel
    filter.py           # FilterMatcher (legacy helpers)
  database/
    models.py           # Dataclasses: User, UserFilter, Booking
    db.py               # Database class — all SQLite ops + migrations
  scheduler/
    class_scheduler.py  # ClassCheckScheduler — concurrent hourly check
  telegram_bot/
    handlers.py         # All Telegram command + callback handlers
    notifications.py    # NotificationSender — outbound user messages
  utils/
    crypto.py           # PasswordEncryptor (Fernet)
    logger.py           # Structured logger with user_id context
    helpers.py          # Misc utilities (datetime formatting, etc.)
tests/                  # unittest suites — keep all of them green
data/                   # Runtime: SQLite DB + Fernet key
logs/                   # Runtime: log files
```

### Key data flow

1. User runs `/login` in Telegram → handler stores encrypted password in `users` table.
2. User configures one or more filters via the `/filters` menu → rows in `user_filters`.
3. Every hour, `ClassCheckScheduler._check_classes_job` runs:
   - Calls `_check_expired_pauses()` first → notifies users whose pauses just ended.
   - Fans out to all users via `asyncio.gather` capped by `Semaphore(MAX_CONCURRENT_USERS)`.
   - Per user: authenticates once, then fetches classes for **all active (non-paused) filters** concurrently.
   - For each match: `book_class` (if `auto_booking`) and/or send notification.
4. Successful bookings are persisted to `bookings` (with `filter_id`, `is_auto_booked`).

### Concurrency model (important)

- All blocking `requests` calls (`authenticate`, `get_classes_by_filter`, `book_class`) are wrapped in `asyncio.to_thread(...)` — never call them directly from coroutines.
- Per-user processing is gated by a `Semaphore(MAX_CONCURRENT_USERS)` (default 10).
- Whole cycle has a hard timeout `SCHEDULER_TIMEOUT` (default 300s).
- The scheduler reuses the bot's main event loop via `asyncio.run_coroutine_threadsafe` — do not spawn a new loop inside handlers.

### Database schema (current)

| Table | Purpose |
|---|---|
| `users` | Telegram ID → encrypted Zdrofit credentials |
| `user_filters` | Multiple filters per user; includes `auto_booking`, `paused_until` |
| `bookings` | Booking history with `filter_id` and `is_auto_booked` flag |

Migrations are **idempotent `ALTER TABLE` blocks** in `Database._init_db()`. A `DROP TABLE IF EXISTS` migration is also used to remove obsolete tables (`available_classes`, `filter_catalog` were cleaned up — do not reintroduce).

## Rules

- **Always run the full test suite** after changes: `python -m unittest discover tests/`. All tests must pass before declaring done.
- **Wrap all blocking I/O** (Zdrofit API, file I/O in handlers) in `asyncio.to_thread` when called from async code.
- **Pass `user_id` to logger** via `extra={'user_id': ...}` — the logger formatter expects it. Use `'system'` for non-user-scoped logs.
- **Never log raw passwords or full Fernet keys.** Mask credentials in debug output (see `authenticate()` for the pattern).
- **Telegram callback prefixes can collide.** When adding handlers, more-specific prefixes must be checked **before** less-specific ones (e.g. `filter_pause_duration_` is checked before `filter_pause_`). This is a known footgun — see `src/telegram_bot/handlers.py` history.
- **Filters can be paused.** Always check `user_filter.is_paused` (or filter at SQL level) before processing in scheduler / displaying as active.
- **Do not assume a single filter per user.** Use `db.get_all_filters(user_id)`; `get_filter()` exists for backward compat (returns first only).
- **Do not break existing migrations.** Adding a column = new `try/except sqlite3.OperationalError` ALTER block. Do not rewrite earlier migration blocks.

## Coding Conventions

- **Type hints** everywhere on public methods; `Optional[T]` over `T = None` in signatures where possible.
- **Dataclasses** for DB models; use `__post_init__` for default `datetime.now()` timestamps.
- **f-strings** for log messages; keep them under ~120 chars.
- **Imports**: stdlib → third-party → `src.*` / `config.*`, separated by blank lines.
- **No new dependencies** without updating `requirements.txt` and explicit user approval.
- **Errors**: catch broad `Exception` at boundaries (handler, API call, DB op), log with context, return a sensible default (`False`, `[]`, `None`). Don't let exceptions bubble into APScheduler or telegram-bot internals.
- **Encryption**: always go through `PasswordEncryptor.encrypt/decrypt`. Never store plaintext.
- **Russian / Polish** strings in user-facing Telegram messages are intentional — do not translate them. Internal logs/comments are English.

## Design System

This is a backend Telegram bot — no UI/CSS. The "design system" is the **Telegram message + InlineKeyboard layout**:

- **Menus** use `InlineKeyboardMarkup` with one logical action per row, emoji prefix for affordance (e.g., `⏸️ Pause Filter`, `🗑️ Delete`, `⬅️ Back`).
- **Status indicators** in messages: `✅` active, `⏸️` paused, `🤖` auto-booking on, `🔔` notify-only.
- **Confirmation flows** (delete, pause) use a two-step prompt with explicit Yes/Cancel buttons.
- **Long lists** (filters, bookings) are formatted as Markdown with `*bold*` headers; do not exceed Telegram's 4096-char message limit — paginate if needed.
- **Date format** for users: `dd.MM.yyyy HH:mm` (see `helpers.format_datetime_display`).

## Content Guidelines

- **Do not invent gym data.** The `AVAILABLE_CLUBS` mapping in `config/config.py` is the single source of truth for club_id ↔ name.
- **Russian UI strings** are the established norm for user-facing menus and are kept as-is.
- **Error messages to users** must be friendly and actionable, never expose stack traces, raw HTTP statuses, or DB errors.
- **Notifications** include: class name, gym, trainer, start time, and (when relevant) which filter triggered the action.

## Commands

```bash
# Activate venv (always first)
source venv/bin/activate

# Run the bot locally
python main.py

# Install / update deps
pip install -r requirements.txt

# Run all tests
python -m unittest discover tests/ -v

# Run a single test module
python -m unittest tests.test_pause_filter -v

# Inspect the SQLite DB
sqlite3 data/zdrofit.db

# Manage DB (custom utility)
python manage_db.py

# Docker — local build & run
sudo docker compose build --no-cache && sudo docker compose up -d
sudo docker compose logs -f zdrofit-bot
sudo docker compose down

# Deploy to Raspberry Pi — typical workflow:
#   1. git push from laptop
#   2. ssh pi@<IP ADDRESS>
#   3. cd ~/tg-zdrofit-class-booker && git pull
#   4. sudo docker compose build && sudo docker compose up -d
```

## Testing and Quality

- **Framework**: `unittest` only. Do not introduce pytest-only fixtures or markers.
- **Location**: `tests/test_*.py`. Each test file targets a feature area (auto_booking, pause_filter, filters, weekday_filter, time_filter, crypto, validation, models, database).
- **Discovery**: `python -m unittest discover tests/` — current baseline is **159 tests, all green**. Do not let this drop.
- **DB tests** use `tempfile.NamedTemporaryFile(suffix='.db')` and clean up in `tearDown`. Follow this pattern.
- **No live API calls** in unit tests. Mock `ZdrofitAPIClient` or the `requests` layer.
- **After any change** to `db.py`, `models.py`, `class_scheduler.py`, or `handlers.py` → run the full suite.
- **Lint mentally**: no unused imports, no commented-out blocks of dead code. Use `mcp_pylance_mcp_s_pylanceInvokeRefactoring` (`source.unusedImports`) when adding/removing code.
- **Prefer stepping through code** to setting many breakpoints if debugging is needed.

## Safety Rules

- Do not rename public API routes unless explicitly requested.
- Do not change database schema without calling it out clearly. Schema changes = a new idempotent ALTER migration in `_init_db()`, never an in-place rewrite of existing migrations.
- Do not modify auth flows (`User`, `PasswordEncryptor`, `/login` handler, Fernet key handling) unless the task requires it. The Fernet key under `data/` must remain stable across restarts — never regenerate it.
- Preserve backward compatibility for shared components: `Database.get_filter(user_id)` returns the *first* filter for legacy callers; do not change its semantics. Same for any method consumed by tests in `tests/test_database.py`.
- Flag major architectural changes before implementing them. Examples that require explicit approval:
  - Switching the HTTP client (e.g., `requests` → `httpx`/`aiohttp`)
  - Switching the DB engine or adopting an ORM
  - Changing the scheduler trigger or concurrency model
  - Adding a message queue, Redis, or any external service
  - Removing or renaming any column on `users`, `user_filters`, or `bookings`
- Do not commit secrets. `.env`, `data/zdrofit.db`, and `data/*.key` are gitignored — keep it that way.
- Do not reintroduce removed dead code: `available_classes` table, `filter_catalog` table, `FilterCatalog` model, `save/get/invalidate_filter_catalog` methods. They were intentionally cleaned up.
- When in doubt about scope, **ask the user** before making sweeping edits across many files.
