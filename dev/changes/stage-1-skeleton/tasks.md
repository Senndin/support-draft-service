# stage-1-skeleton

## 1. Project Setup

- [ ] 1.1 Створити `pyproject.toml` (Python `>=3.14`, залежності з `design.md`, dev-група `pytest`, `pytest-asyncio`, `[tool.pytest.ini_options] asyncio_mode = "auto"`, `testpaths = ["tests"]`), згенерувати `uv.lock`, додати `.gitignore` (`.venv/`, `__pycache__/`, `.env`, `.pytest_cache/`) і порожні пакети `app/`, `app/api/`, `app/worker/`.
- [ ] 1.2 Реалізувати `app/config.py`: клас `Settings(BaseSettings)` з полями й дефолтами з `design.md` та екземпляр `settings = Settings()`; тест `tests/test_config.py` (покриває сценарій «Значення з оточення перекриває дефолт» `service-runtime`): `LLM_RPM=30` в оточенні → `Settings().llm_rpm == 30`, без змінної → `60`.
- [ ] 1.3 Створити `.env.example` з кожною змінною `Settings` (`DATABASE_URL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_S`, `LLM_RPM`, `LLM_CONCURRENCY`, `STUB_DELAY_MIN_S`, `STUB_DELAY_MAX_S`) і значеннями для локального запуску з розділу 3 ROADMAP; тест: множина ключів `.env.example` дорівнює множині полів `Settings` (у верхньому регістрі).

## 2. Backend

- [ ] 2.1 Реалізувати `app/db.py` (`engine`, `SessionLocal`) і `app/models.py` (`Base(DeclarativeBase)`) за `design.md`.
- [ ] 2.2 Реалізувати контракт `GET /health` → `200`, `{"status": "ok"}` у `app/api/health.py` (`router = APIRouter()`) і застосунок `app = FastAPI()` у `app/main.py`, що підключає роутер; тест `tests/test_health.py` через `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.
- [ ] 2.3 Реалізувати воркер-заглушку `app/worker/__main__.py`: `main()` логує старт, чекає `asyncio.Event`, яку встановлюють обробники SIGTERM/SIGINT, логує зупинку й завершується з кодом `0`; тест: `main()` як задача завершується без винятку після `os.kill(os.getpid(), signal.SIGTERM)`.

## 3. DB Migrations

- [ ] 3.1 Ініціалізувати Alembic async-шаблоном (`alembic init -t async migrations`), у `migrations/env.py` брати URL із `settings.database_url` і `target_metadata = Base.metadata`; створити першу порожню ревізію `initial` з `upgrade`/`downgrade` = `pass`.

## 4. Infrastructure

- [ ] 4.1 Створити `Dockerfile` (`python:3.14-slim`, `uv` з `ghcr.io/astral-sh/uv`, `uv sync --frozen --no-dev`, код застосунку, дефолтна команда — `uvicorn app.main:app --host 0.0.0.0 --port 8000`) і `.dockerignore`.
- [ ] 4.2 Створити `docker-compose.yml`: `db` (`postgres:16`, healthcheck `pg_isready`, volume для даних), `migrate` (`alembic upgrade head`, `depends_on: db: service_healthy`), `api` (порт `8000:8000`) і `worker` (`python -m app.worker`) з `depends_on: migrate: service_completed_successfully`, `env_file: .env`, `extra_hosts: host.docker.internal:host-gateway`; перевірити, що `docker compose up --build` піднімає стек і `curl localhost:8000/health` → `200`.

## 5. Documentation

- [ ] 5.1 Заповнити плейсхолдери кореневого `AGENTS.md` (назва й опис проєкту, ключові джерела з `docs/ROADMAP.md`, стек, запуск, тести, міграції, стиль комітів: англійська, без scope, без номерів задач, `Co-authorship trailer: no`); у `CLAUDE.md` залишити `@AGENTS.md` і додати посилання на `docs/ROADMAP.md`.
- [ ] 5.2 Створити `docs/decisions.md` з рішеннями етапу 1 (1–3 рядки на рішення): `uv`, окремий сервіс `migrate`, `/health` без БД, воркер-заглушка.

## 6. Functional Tests

- [ ] 6.1 Написати end-to-end тест для сценарію «Сервіс запущений» (`health-check`): запит `GET /health` до застосунку, зібраного з `app.main`, повертає `200` і `{"status": "ok"}`.
