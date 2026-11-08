# Support Draft Service

Сервіс приймає звернення в підтримку з хелпдеску, готує чернетку відповіді через LLM на основі бази знань і після підтвердження оператором надсилає відповідь клієнту.
Тестове завдання AI-first Backend Engineer; бюджет ~3 години, скоуп не розширювати понад `docs/ROADMAP.md`.

## Key sources

Other documents the agent should start from:
@docs/ROADMAP.md — що будуємо, етапи та критерії приймання (працювати строго по одному етапу).
`docs/decisions.md` — зафіксовані рішення (1–3 рядки на рішення); неоднозначності фіксувати там, а не питати.

## Stack

Python 3.14, FastAPI, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PostgreSQL 16, httpx, pydantic-settings.
UI — Jinja2 і звичайні HTML-форми, без JS-фреймворків.
Черга задач — таблиця в PostgreSQL (`SELECT ... FOR UPDATE SKIP LOCKED`); Redis, Celery та інші брокери заборонені.
Залежності — лише `uv`.
Коментарі в коді — українською; код максимально простий, без зайвих абстракцій.

## Running

**Start:** `cp .env.example .env && docker compose up --build` (сервіси `db`, `migrate`, `api`, `worker`)

**Environment variables:** `.env.example` → `.env`

**Address:** `localhost:8000` (`GET /health`)

**Test data:** немає до етапу 3 (сід бази знань запускатиметься сервісом `migrate`)

## Testing

**Runner:** `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`)

**Full run:** `uv run pytest`

**Targeted run:** `uv run pytest tests/test_health.py::test_health_returns_ok`

**Test location:** `tests/test_<module>.py`

**Slow or excluded suites:** немає; сценарії, що потребують Docker (підйом стеку, повторні міграції), перевіряються вручну через `acceptance.md`

## Database migrations

**SQL dialect:** `PostgreSQL 16`

**Database schema:** `app/models.py` (SQLAlchemy-моделі)

**Migration location:** `migrations/versions/` (Alembic)

**Naming and up/down pairs:** `uv run alembic revision -m "<опис>"` → `<revision>_<опис>.py` з функціями `upgrade()` / `downgrade()` в одному файлі

Migrations born inside a change are collected by `dev-apply-change` into `dev/changes/{name}/db-migration.up.sql` and `db-migration.down.sql`.

## Code style

Project guide:
Uncomment the link once the guide exists: it is read by `dev-apply-change`, `dev-refactor`, `dev-docs` and `dev-review`, and through the latter by `dev-verify-change` too.
Without a guide these skills follow the conventions the existing code demonstrates.

## Commit style

**Message language:** `English`

**Types:** `feat, fix, docs, refactor, test, chore, perf, build, ci, style`

**Scope:** `not used`

**Issue number format:** `{type}: {subject}`

**Maximum subject length:** `72`

**Co-authorship trailer:** `no`

Історія комітів «як є», без squash; після кожного етапу — тести, потім коміт.

Example messages:

```text
feat: add dev-commit skill and wire it into the change workflow
fix(sync_specs): report an unresolved bullet instead of crashing
docs: describe commit rules in the root AGENTS.md
chore: archive change dev-commit-skill
```

Only `dev-archive-change` adds a message body — it describes the whole change in CHANGELOG style.
All other skills generate single-line messages; the co-authorship trailer, when the field above asks for it, is the one line added to any of them.
