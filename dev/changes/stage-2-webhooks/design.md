# stage-2-webhooks

## Контекст

<!-- Context -->

Етап 1 дав каркас: FastAPI-застосунок, async engine, Alembic із порожньою ревізією `325acc2e9ced`, compose-стек.
Ця зміна реалізує [`webhook-intake`](/dev/specs/webhook-intake/spec.md) і [`webhook-sender`](/dev/specs/webhook-sender/spec.md): перша таблиця БД, перший робочий ендпоінт і скрипт-імітатор хелпдеску.
Жорсткі обмеження з ROADMAP: відповідь ≤ 2 с, дублі (зокрема одночасні) не створюють записів, жодного звернення не можна втратити.

## Мета

**Цілі:**
<!-- Goals -->

- `POST /webhooks/helpdesk` ідемпотентний на рівні БД, а не застосунку, тож коректний і для одночасних дублів.
- Тест «10 одночасних запитів з одним `event_id` → 1 рядок» проходить на справжньому PostgreSQL.
- `scripts/send_webhooks.py` готовий до навантажувального прогону етапу 7 без змін інтерфейсу.

**Поза межами зміни:**
<!-- Non-Goals -->

- Обробка звернень воркером, генерація чернеток — етап 4.
- Ендпоінт мока `/mock/helpdesk/...` — етап 6; скрипт лише формує `reply_url` на нього.
- Підрахунок p99 у скрипті — етап 7.
- Перевірка підпису вебхука — поза скоупом ROADMAP.

## Рішення

<!-- Decisions -->

**Таблиця `tickets` одразу в повному вигляді.**
Модель `Ticket` в `app/models.py` містить усі колонки розділу 2 ROADMAP: `id` (bigint PK), `event_id` (text, **UNIQUE**), `ticket_id`, `customer_email`, `message`, `reply_url` (text, NOT NULL), `status` (text, NOT NULL, дефолт `received`), `draft`, `final_message` (text, NULL), `article_ids` (`integer[]`, NULL), `attempts` (int, NOT NULL, дефолт `0`), `next_attempt_at` (timestamptz, NOT NULL, дефолт `now()`), `locked_until` (timestamptz, NULL), `last_error` (text, NULL), `idempotency_key` (uuid, NULL), `created_at`, `updated_at` (timestamptz, NOT NULL, дефолт `now()`).
Індекс `(status, next_attempt_at)` для майбутнього захоплення задач воркером.
Альтернатива — додавати колонки на кожному етапі — дає три міграції замість однієї без жодного виграшу: модель уже зафіксована в ROADMAP.
`status` — звичайний `text` без `CHECK`/enum: набір статусів ще розширюватиметься, а переходи контролює код.

**Міграція пишеться вручну.**
Ревізія `create_tickets` поверх `325acc2e9ced`, `op.create_table` + `op.create_index`; `downgrade` видаляє індекс і таблицю.
Autogenerate потребує живої БД і все одно вимагає ручної перевірки.

**Ідемпотентність — `INSERT ... ON CONFLICT (event_id) DO NOTHING`.**

```mermaid
sequenceDiagram
    participant H as Helpdesk
    participant A as api /webhooks/helpdesk
    participant P as PostgreSQL
    H->>A: POST подія (event_id)
    A->>A: валідація pydantic (422 при помилці)
    A->>P: INSERT ... ON CONFLICT (event_id) DO NOTHING
    P-->>A: вставлено 0 або 1 рядок
    A-->>H: 202 {"status": "accepted"}
```

Вставка через `sqlalchemy.dialects.postgresql.insert(Ticket).on_conflict_do_nothing(index_elements=["event_id"])` в одній транзакції.
Унікальний індекс серіалізує одночасні вставки на рівні PostgreSQL; перевірка «SELECT, потім INSERT» відкинута — вона має гонку між двома запитами.
Результат вставки (новий чи дубль) лише логується: відповідь однакова.

**Схема тіла — `WebhookEvent` (pydantic).**
`event_id`, `ticket_id`, `customer_email`, `message` — `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]`; `reply_url` — `AnyHttpUrl`, у БД зберігається як рядок.
Зайві поля ігноруються (дефолт pydantic): хелпдеск може надсилати більше, ніж нам потрібно.
`422` повертає стандартна валідація FastAPI.

**Сесія БД як залежність.**
`app/db.py` отримує `async def get_session()` (yield `SessionLocal()`); роутер `app/api/webhooks.py` бере сесію через `Depends(get_session)`.
У тестах залежність перевизначається на сесію тестової БД — без підміни глобального engine.

**Тестова БД.**
`db` у compose публікує `${DB_PORT:-5432}:5432`, щоб тести з хоста бачили PostgreSQL.
`tests/conftest.py`: сесійна фікстура підключається до `TEST_DATABASE_URL` (дефолт `postgresql+asyncpg://postgres:postgres@localhost:5432/support_test`), створює БД, якщо її немає, і проганяє `alembic upgrade head` (так тести заодно перевіряють міграцію).
Перед кожним DB-тестом — `TRUNCATE tickets`.
Якщо PostgreSQL недоступний, DB-тести пропускаються з повідомленням `docker compose up -d db`; тести етапу 1 і далі працюють без БД.

**Скрипт `scripts/send_webhooks.py`.**
`argparse` з `--url` (дефолт `http://localhost:8000/webhooks/helpdesk`), `--count` (10), `--dup-rate` (0.2), `--concurrency` (10), `--reply-base` (дефолт `http://api:8000` — адреса `api` всередині compose-мережі).
`build_events(count, dup_rate, reply_base) -> list[dict]`: `count` унікальних подій (`event_id` — `uuid4`) плюс `round(count * dup_rate)` копій випадкових подій; список перемішується, тож дублі йдуть упереміш з оригіналами і частина — одночасно.
`send_all(events, url, concurrency, transport=None) -> Counter`: `httpx.AsyncClient` + `asyncio.Semaphore` + `asyncio.gather`; ключ лічильника — HTTP-статус або `"error"` для мережевої помилки.
Вивід: `sent: N`, далі по рядку `<статус>: <кількість>`.
Параметр `transport` дозволяє тестувати скрипт на ASGI-застосунку без мережі.

## Вплив

<!-- Impact -->

- Нові файли: `app/api/webhooks.py`, `migrations/versions/<rev>_create_tickets.py`, `scripts/send_webhooks.py`, `tests/conftest.py`, `tests/test_webhooks.py`, `tests/test_send_webhooks.py`.
- Змінені файли: `app/models.py` (модель `Ticket`), `app/db.py` (`get_session`), `app/main.py` (підключення роутера), `docker-compose.yml` (порт `db`), `AGENTS.md` (тести потребують `docker compose up -d db`), `docs/decisions.md`.
- Нові залежності: немає.
- БД: таблиця `tickets`, унікальний індекс на `event_id`, індекс `(status, next_attempt_at)`.

## Ризики та компроміси

<!-- Risks and Trade-offs -->

- Порт `5432` на хості може бути зайнятий локальним PostgreSQL: порт налаштовується через `DB_PORT`, тести — через `TEST_DATABASE_URL`.
- DB-тести пропускаються без PostgreSQL, тож «зелений» прогін без БД не доводить ідемпотентність: `AGENTS.md` вимагає перед повним прогоном `docker compose up -d db`, а пропуск видно у виводі pytest.
- Дубль з іншим вмістом мовчки ігнорується: хелпдеск за контрактом повторює ту саму подію, тож розбіжність — аномалія, яку достатньо залогувати.
- `DB_PORT` читає лише compose, тому в `.env.example` його немає (тест етапу 1 вимагає, щоб там були рівно поля `Settings`): дефолт `5432` задано в `docker-compose.yml`, а перевизначення описане в `AGENTS.md`.
