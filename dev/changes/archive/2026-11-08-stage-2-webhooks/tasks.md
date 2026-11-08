# stage-2-webhooks

## 1. Backend: Phase 1 – Model

- [x] 1.1 Додати модель `Ticket` в `app/models.py` з колонками, дефолтами, `UNIQUE(event_id)` та індексом `(status, next_attempt_at)` за `design.md`; тест: `Ticket.__table__` має унікальне обмеження на `event_id`, дефолт `status` — `received`, `attempts` — `0`.

## 2. DB Migrations

- [x] 2.1 Написати вручну ревізію Alembic `create_tickets` поверх `325acc2e9ced`: `op.create_table("tickets", ...)` за моделлю `Ticket` і `op.create_index` на `(status, next_attempt_at)`; `downgrade` видаляє індекс і таблицю.

## 3. Backend: Phase 2 – Webhook

- [x] 3.1 Відкрити порт `db` у `docker-compose.yml` (`"${DB_PORT:-5432}:5432"`), додати `get_session()` в `app/db.py` і `tests/conftest.py` з фікстурами: `db_engine` (сесійна; створює БД `support_test` за `TEST_DATABASE_URL`, проганяє `alembic upgrade head`, без PostgreSQL — `pytest.skip("PostgreSQL недоступний: docker compose up -d db")`), `client` (`httpx.AsyncClient` на ASGI-застосунку з перевизначеним `get_session` і `TRUNCATE tickets` перед тестом); тест: фікстура піднімає схему — у `support_test` є таблиця `tickets`.
- [x] 3.2 Визначити контракт `POST /webhooks/helpdesk`: тіло `WebhookEvent` (`event_id`, `ticket_id`, `customer_email`, `message` — непорожні рядки після `strip`; `reply_url` — `AnyHttpUrl`), відповідь `202 {"status": "accepted"}`, невалідне тіло — `422`; реалізувати його в `app/api/webhooks.py` через `insert(Ticket).on_conflict_do_nothing(index_elements=["event_id"])` і підключити роутер у `app/main.py`; тести: нова подія → `202` і рядок зі статусом `received`; послідовний дубль з іншим `message` → `202`, один рядок з початковим `message`; відсутній `event_id`, порожній `message` і невалідний `reply_url` → `422` без запису.

## 4. Tooling

- [x] 4.1 Реалізувати `scripts/send_webhooks.py` за `design.md`: `build_events(count, dup_rate, reply_base) -> list[dict]`, `send_all(events, url, concurrency, transport=None) -> collections.Counter`, `main()` з прапорцями `--url`, `--count`, `--dup-rate`, `--concurrency`, `--reply-base` і виводом `sent: N` та `<статус>: <кількість>`; тести: `build_events(20, 0.5, ...)` дає 30 подій з 20 унікальними `event_id` і `reply_url` виду `{reply_base}/mock/helpdesk/tickets/{ticket_id}/replies`; `send_all` через `httpx.MockTransport`, що кидає `httpx.ConnectError`, рахує `"error"` і не переривається.

## 5. Documentation

- [x] 5.1 Оновити `AGENTS.md` (повний прогін тестів потребує `docker compose up -d db`; `DB_PORT`, `TEST_DATABASE_URL`; запуск `scripts/send_webhooks.py`) і додати рішення етапу 2 в `docs/decisions.md`.

## 6. Functional Tests

- [x] 6.1 Написати end-to-end тести для сценаріїв «Нова подія», «Послідовний дубль», «Одночасні дублі» (10 запитів через `asyncio.gather` → усі `202`, один рядок) і «Відсутнє поле» (`webhook-intake`) на справжньому PostgreSQL.
- [x] 6.2 Написати end-to-end тест для сценарію «Відповідь без зовнішніх викликів» (`webhook-intake`): під час запиту вихідні з'єднання `httpx.AsyncHTTPTransport.handle_async_request` заборонені (підміна, що кидає помилку), відповідь `202` за < 0.5 с.
- [x] 6.3 Написати end-to-end тест для сценаріїв «Прогін із дублями» і «Звіт про відповіді» (`webhook-sender`): `send_all` через `httpx.ASGITransport` на застосунку з тестовою БД — `--count 20 --dup-rate 0.5` дає 20 рядків, а лічильник `{202: 30}`.
