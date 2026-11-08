# ROADMAP — Support Draft Service (AI-first Backend Engineer)

> Вхідний документ для Claude Code. Описує **що** будуємо, **в якому порядку** і **як перевірити**, що етап готовий.
> Бюджет часу: **~3 години** чистої роботи. Не розширювати скоуп понад описане тут.

---

## 0. Як працювати з цим файлом (для Claude Code)

1. Читай цей файл повністю перед кожним етапом. Працюй **строго по одному етапу**.
2. Перед реалізацією етапу створюй артефакти в `specs/NN-<slug>/` (формат задає SDD-скіл, який буде доданий у проєкт пізніше). Якщо скіла ще немає — мінімум: `spec.md` (що + критерії приймання з цього файлу) і `tasks.md` (чекліст).
3. **Критерії приймання етапу — це контракт.** Специфікація може їх уточнювати, але не додавати нових фіч.
4. Після завершення етапу: прогнати тести → коміт (Conventional Commits, `feat: ...`, `fix: ...`). Історія комітів «як є», **без squash**.
5. Коментарі в коді — українською. Код — максимально простий, без зайвих абстракцій.
6. Якщо щось у задачі неоднозначне — фіксуй рішення в `docs/decisions.md` (1–3 рядки на рішення), а не питай.

---

## 1. Задача коротко

Сервіс обробляє звернення в підтримку і готує чернетку відповіді для оператора за допомогою LLM:

1. **Отримання** — хелпдеск шле звернення на `POST /webhooks/helpdesk`.
2. **Генерація** — пошук релевантних статей у базі знань → LLM генерує чернетку з посиланнями на статті.
3. **Модерація** — оператор у веб-UI бачить список звернень із чернетками, підтверджує або відхиляє.
4. **Надсилання** — підтверджена відповідь іде клієнту через `POST <reply_url>` хелпдеску.

Плюс: `GET /health` → `200 {"status": "ok"}`.

### Жорсткі обмеження (з ТЗ)

| Обмеження | Що з цього випливає |
|---|---|
| Вебхук має відповісти **≤ 2 с**, інакше повтор | Вебхук тільки зберігає подію в БД і одразу повертає `202`. Жодного LLM у запиті. |
| Та сама подія може прийти кілька разів, **зокрема одночасно** | `UNIQUE(event_id)` + `INSERT ... ON CONFLICT DO NOTHING`. Дубль → теж `202`. |
| Пік **500 звернень / 10 хв**, втрачати не можна | Черга = таблиця в PostgreSQL (durable). Воркер забирає задачі через `SELECT ... FOR UPDATE SKIP LOCKED`. |
| LLM-виклик **5–30 с**, ліміт **60 RPM** на весь сервіс | Асинхронний воркер з паралельністю (семафор) + глобальний rate limiter. |
| Хелпдеск іноді дає 5xx / таймаут; клієнт **не має отримати відповідь двічі** | Стейт-машина `approved → sending → sent`, ретраї з backoff, заголовок `Idempotency-Key` (мок його поважає), атомарні переходи статусів. |
| Працювати **без API-ключа** | Реальний запит до провайдера все одно робиться, але відповідь підміняється статичною з затримкою 5–30 с. |

### Стек (фіксований)

- Python 3.14, **FastAPI**, SQLAlchemy 2.0 (async) + asyncpg, Alembic
- **PostgreSQL 16**
- UI: Jinja2-шаблони, звичайні HTML-форми (без JS-фреймворків)
- HTTP-клієнт: `httpx` (async)
- Тести: `pytest` + `pytest-asyncio`
- Залежності: `uv` (або pip — на вибір, але один спосіб)
- Запуск: `docker compose up`

**Без Redis / Celery / брокерів.** Черга в Postgres — свідоме рішення: менше рухомих частин, транзакційність «з коробки», навантаження (~1 подія/с у піку) для Postgres дрібниця.

---

## 2. Архітектура

```
Helpdesk (mock) ──POST /webhooks/helpdesk──▶  api  ──INSERT ON CONFLICT──▶  PostgreSQL
                                                                              │  tickets (= черга)
                                               worker: generation loop  ◀─────┤  kb_articles
                                                 ├─ пошук у KB (Postgres FTS)  │
                                                 └─ LLM (rate limit 60 RPM)    │
Operator ──▶ api: UI (/ui) ── approve/reject ──────────────────────────────▶  │
                                               worker: sending loop     ◀─────┘
                                                 └─ POST reply_url (Idempotency-Key, retries)
```

### Сервіси в `docker-compose.yml`

| Сервіс | Що робить |
|---|---|
| `db` | PostgreSQL 16 з healthcheck |
| `api` | FastAPI: вебхук, `/health`, UI оператора, **мок хелпдеску** (роутер `/mock/helpdesk/...`) |
| `worker` | Той самий образ, команда `python -m app.worker`: два асинхронні цикли — генерація і надсилання |
| `migrate` | Одноразовий `alembic upgrade head` + сід бази знань (або те саме в entrypoint `api`) |

Мок хелпдеску живе в тому ж застосунку як окремий роутер — так простіше і для локального запуску, і для деплою (один сервіс замість двох).

### Модель даних (мінімум)

**`tickets`** — і звернення, і черга задач:

- `id`, `event_id` (**UNIQUE**), `ticket_id`, `customer_email`, `message`, `reply_url`
- `status`: `received → generating → draft_ready → approved → sending → sent`; бічні: `rejected`, `generation_failed`, `send_failed`
- `draft` (text), `final_message` (text), `article_ids` (int[] або jsonb)
- `attempts` (int), `next_attempt_at`, `locked_until` (lease, щоб задача повернулась у чергу після падіння воркера), `last_error`
- `idempotency_key` (uuid, генерується при approve), `created_at`, `updated_at`

**`kb_articles`**: `id`, `slug`, `title`, `body`, `url`, `search_vector` (tsvector, generated column).

### Ключові рішення

- **Ідемпотентність вебхука:** `INSERT ... ON CONFLICT (event_id) DO NOTHING` — коректно і для одночасних дублів.
- **Захоплення задач воркером:** `UPDATE ... SET status='generating', locked_until=now()+interval ... WHERE id IN (SELECT id ... FOR UPDATE SKIP LOCKED LIMIT n) RETURNING *`. Протерміновані lease повертаються в обробку.
- **Approve/Reject:** атомарний `UPDATE ... WHERE id=:id AND status='draft_ready'`. Подвійний клік / дві вкладки → друга операція нічого не змінює.
- **Надсилання:** один `Idempotency-Key` на тікет на всі ретраї. Таймаут/5xx → ретрай з експоненційним backoff + jitter (макс. ~8 спроб) → `send_failed`. 4xx (крім 408/429) — не ретраїмо. Чесне обмеження в README: справжній exactly-once можливий лише якщо хелпдеск підтримує ідемпотентні ключі; без цього — at-least-once з мінімізацією дублів.
- **Rate limit:** in-process async limiter (60 запитів / 60 с) + семафор `LLM_CONCURRENCY`. Воркер один → in-process достатньо. При масштабуванні на кілька воркерів — ліміт у Postgres (зафіксувати як trade-off у README).
- **Пропускна здатність:** пік 50/хв < 60 RPM, але при 30 с на виклик потрібно ~25 паралельних запитів → `LLM_CONCURRENCY=25` для хмарного провайдера. Якщо провайдер має менший ліміт (напр. 30 RPM) — черга росте, але нічого не губиться.
- **Пошук у KB:** PostgreSQL full-text search (`to_tsvector('simple', ...)`, `ts_rank`) + fallback на `pg_trgm` similarity, топ-3 статті. Для 5–10 статей ембеддинги/pgvector — оверкіл (згадати в README як шлях розвитку).

---

## 3. Налаштування LLM

Один клієнт під **OpenAI-сумісний API** (`POST {LLM_BASE_URL}/chat/completions`). Провайдер змінюється лише env-змінними — коду це не стосується.

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama            # порожньо → режим без ключа (див. нижче)
LLM_MODEL=qwen2.5:7b-instruct
LLM_TIMEOUT_S=60
LLM_RPM=60
LLM_CONCURRENCY=4
STUB_DELAY_MIN_S=5            # для тестів можна ставити 0
STUB_DELAY_MAX_S=30
```

### 3.1 Локально: Ollama на MacBook M3 Pro (18 GB)

**Важливо:** Docker Desktop на macOS не має доступу до GPU (Metal), тому Ollama запускається **нативно на хості**, а контейнери ходять до неї через `host.docker.internal`.

```bash
# 1. Модель для генерації (добре з українською, ~4.7 GB, комфортно поруч із Docker)
ollama pull gemma-4-e4b-it:q4_k_m
# швидкий smoke-тест (слабша українська, але дуже швидка)
ollama pull llama3.2:3b

# 2. Дозволити паралельні запити і тримати модель у пам'яті
launchctl setenv OLLAMA_NUM_PARALLEL 4
launchctl setenv OLLAMA_KEEP_ALIVE 30m
# перезапустити Ollama.app

# 3. Перевірити OpenAI-сумісний ендпоінт
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma-4-e4b-it:q4_k_m","messages":[{"role":"user","content":"Привіт"}]}'
```

У `docker-compose.yml` для `api` і `worker`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"   # потрібно на Linux, на macOS не завадить
```

Нотатки:
- `qwen2.5-coder:14b` не брати: це кодова модель і вона важка (~9 GB) поруч із Docker на 18 GB.
- Якщо `connection refused` з контейнера — `launchctl setenv OLLAMA_HOST 0.0.0.0` і перезапуск Ollama.
- Локально тримати `LLM_CONCURRENCY=2–4`: Ollama на ноуті не витягне 25 паралельних запитів, це нормально — черга просто довша.
- Опційно: Ollama на другому ПК (RTX 3060, 12 GB VRAM) у локальній мережі → `LLM_BASE_URL=http://<ip-пк>:11434/v1`.

### 3.2 Деплой: безкоштовний хмарний API

Ollama на хостингу не буде, тому для публічного деплою — провайдер з безкоштовним тиром і OpenAI-сумісним API:

| Провайдер | `LLM_BASE_URL` | Модель (приклад) | Примітка |
|---|---|---|---|
| **Groq** (рекомендовано) | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Дуже швидкий; free-ліміт ~30 RPM → `LLM_RPM=30` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash` | Free tier лише Flash-моделі |
| OpenRouter | `https://openrouter.ai/api/v1` | моделі з суфіксом `:free` | Жорсткі денні ліміти без поповнення балансу |

Актуальні ліміти перевірити в консолі провайдера в момент реєстрації — вони змінюються. Значення `LLM_RPM` ставити за фактичним лімітом ключа, але не вище 60.

### 3.3 Режим без API-ключа (обов'язковий за ТЗ)

Якщо `LLM_API_KEY` порожній:

1. Сервіс **все одно робить реальний HTTP-запит** до `LLM_BASE_URL` (без `Authorization`; очікувано отримає 401 — логуємо статус, результат ігноруємо). Запит проходить через той самий rate limiter.
2. Чекає `random.uniform(STUB_DELAY_MIN_S, STUB_DELAY_MAX_S)`.
3. Повертає **статичну** відповідь-шаблон, у яку підставлені знайдені статті (назва + URL).
4. Далі система працює з нею так само, як з реальною: та сама структура результату, той самий статус `draft_ready`.

Реалізація — одна функція `generate_draft(message, articles) -> DraftResult` з двома гілками всередині, без ієрархії класів.

### 3.4 Промпт (каркас)

- System: «Ти агент підтримки продукту <назва>. Відповідай мовою клієнта, коротко, лише на основі наданих статей. Обов'язково додай посилання на використані статті. Якщо статті не покривають питання — чесно скажи і запропонуй звернутись до оператора.»
- User: текст звернення + топ-3 статті у форматі `[id] title — url \n body`.
- Посилання в чернетці мають відповідати статтям, які реально передані (перевірка в тесті на рівні stub-режиму).

---

## 4. Етапи

Таймінг орієнтовний; сума ~3 год 15 хв.

### Етап 1 — Каркас і інфраструктура · ~20 хв

**Скоуп**
- Структура проєкту (див. розділ 5), `pyproject.toml`, `Dockerfile`, `docker-compose.yml` (`db`, `api`, `worker`, міграції), `.env.example`.
- `app/config.py` на pydantic-settings, async engine/session.
- Alembic ініціалізовано, перша (порожня) міграція.
- `GET /health` → `200 {"status": "ok"}`.
- `CLAUDE.md` (коротко: стек, команди, конвенції, посилання на `ROADMAP.md`), `.gitignore`.

**Готово, коли**
- `docker compose up` піднімає всі сервіси без помилок, `curl localhost:8000/health` → 200.
- `pytest` запускається (хоча б 1 тест на `/health`).

### Етап 2 — Прийом вебхуків · ~25 хв

**Скоуп**
- Модель `Ticket` + міграція.
- `POST /webhooks/helpdesk`: валідація тіла (pydantic), `INSERT ... ON CONFLICT (event_id) DO NOTHING`, відповідь `202 {"status": "accepted"}` для нових і дублів.
- Мок хелпдеску, частина 1: `scripts/send_webhooks.py` — шле N подій, частину з дублями, частину одночасно (`asyncio.gather`); `reply_url` вказує на мок усередині `api`.

**Готово, коли**
- Тест: 10 одночасних запитів з одним `event_id` → 1 рядок у БД, усі відповіді 202.
- Тест: вебхук відповідає швидко (не чекає жодних зовнішніх викликів).

### Етап 3 — База знань і пошук · ~20 хв

**Скоуп**
- 5–10 коротких статей про вигаданий продукт (згенерувати AI) у `kb/articles/*.md` з front-matter (`slug`, `title`). Тематика має покривати типові звернення (експорт у PDF, оплата, доступ, інтеграції тощо).
- Модель `KbArticle` + міграція з generated `tsvector` і GIN-індексом; `pg_trgm`.
- Сід-скрипт (ідемпотентний upsert за `slug`), запускається при старті.
- `app/services/kb.py`: `search(query, limit=3) -> list[KbArticle]` (FTS → fallback trigram).

**Готово, коли**
- Тест: запит «Не можу експортувати звіт у PDF» повертає статтю про експорт першою.
- Повторний сід не дублює статті.

### Етап 4 — LLM-шар і воркер генерації · ~45 хв

**Скоуп**
- `app/services/llm.py`: OpenAI-сумісний клієнт на `httpx`, режим без ключа (розділ 3.3), обробка таймаутів/помилок.
- `app/services/ratelimit.py`: async limiter `LLM_RPM`/хв + семафор `LLM_CONCURRENCY`.
- `app/worker/`: цикл генерації — захоплення задач через `SKIP LOCKED` з lease, пошук у KB → LLM → `draft_ready`; помилки → `attempts++`, `next_attempt_at` з backoff, після N спроб → `generation_failed`.
- Graceful shutdown (SIGTERM): дочекатися поточних задач або відпустити lease.

**Готово, коли**
- Тест (stub-режим з нульовою затримкою): тікет `received` → `draft_ready`, у чернетці є URL знайдених статей.
- Тест: limiter не пропускає більше `LLM_RPM` викликів за вікно.
- Тест: задача з протермінованим lease підхоплюється повторно.
- Вручну: з Ollama генерується осмислена чернетка українською.

### Етап 5 — UI оператора і модерація · ~25 хв

**Скоуп**
- `GET /ui` — таблиця звернень (статус, ticket_id, email, повідомлення, чернетка, статті), фільтр за статусом, автооновлення `<meta http-equiv="refresh" content="10">`.
- Картка тікета: textarea з чернеткою (оператор може поправити текст перед підтвердженням), кнопки **Approve** / **Reject**.
- `POST /ui/tickets/{id}/approve` і `/reject`: атомарний перехід зі статусу `draft_ready`; при approve зберегти `final_message` і згенерувати `idempotency_key`.
- Опційно: HTTP Basic Auth через env `OPERATOR_PASSWORD` (потрібно для публічного деплою).

**Готово, коли**
- Тест: два паралельні approve одного тікета → один успішний перехід.
- Вручну: повний цикл у браузері від `draft_ready` до `approved`/`rejected`.

### Етап 6 — Надсилання відповіді і мок хелпдеску · ~30 хв

**Скоуп**
- Мок, частина 2 (`app/mock_helpdesk/`): `POST /mock/helpdesk/tickets/{ticket_id}/replies` → `201`; конфіг через env: `MOCK_FAIL_RATE` (частка 5xx), `MOCK_SLOW_RATE` (частка відповідей із затримкою більше за таймаут клієнта). Дедуплікація за `Idempotency-Key`. `GET /mock/helpdesk/replies` — список отриманих відповідей для перевірки.
- Цикл надсилання у воркері: захоплення `approved` через `SKIP LOCKED` → `sending` → `POST reply_url` з `Idempotency-Key` і таймаутом → `sent` | ретрай з backoff | `send_failed`.

**Готово, коли**
- Тест: мок повертає 5xx двічі, потім 201 → статус `sent`, у моку рівно **одна** відповідь.
- Тест: мок «зависає» (таймаут клієнта), але запит фактично прийнято → ретрай з тим самим ключем → у моку одна відповідь.

### Етап 7 — Перевірка під навантаженням, README, деплой · ~30 хв

**Скоуп**
- Навантажувальний прогін: `scripts/send_webhooks.py --count 500 --dup-rate 0.2 --concurrency 50` → перевірити: усі унікальні `event_id` у БД, жодного дубля, p99 відповіді вебхука < 2 с. Результати коротко — у README.
- `README.md`: що це, архітектура (схема з розділу 2), запуск (`cp .env.example .env && docker compose up`), налаштування LLM (Ollama / хмарний провайдер / без ключа), як прогнати тести і навантажувальний скрипт, ключові рішення і trade-offs, що б покращив з більшим часом.
- `docs/decisions.md` — зібрати рішення з усіх етапів.
- Деплой (дуже бажано): будь-який хостинг, що вміє Docker + Postgres (Render / Railway / Koyeb або дешевий VPS з `docker compose up`). LLM — Groq або Gemini (розділ 3.2), увімкнути `OPERATOR_PASSWORD`. Публічні посилання на вебхук і `/ui` — у README.

**Готово, коли**
- Чиста машина: `git clone` → `docker compose up` → працює за інструкцією з README.
- Усі тести зелені.
- Агентна конфігурація (`CLAUDE.md`, `specs/`, `docs/`, `.claude/`) закомічена.

---

## 5. Структура проєкту

```
.
├── app/
│   ├── main.py              # FastAPI app, підключення роутерів
│   ├── config.py            # pydantic-settings
│   ├── db.py                # engine, session
│   ├── models.py            # Ticket, KbArticle
│   ├── api/
│   │   ├── health.py
│   │   └── webhooks.py
│   ├── ui/
│   │   ├── routes.py
│   │   └── templates/
│   ├── services/
│   │   ├── kb.py            # пошук по базі знань
│   │   ├── llm.py           # клієнт + режим без ключа
│   │   ├── ratelimit.py
│   │   └── helpdesk.py      # клієнт надсилання відповіді
│   ├── worker/
│   │   └── __main__.py      # цикли генерації та надсилання
│   └── mock_helpdesk/
│       └── routes.py
├── kb/articles/*.md
├── migrations/              # Alembic
├── scripts/
│   ├── seed_kb.py
│   └── send_webhooks.py
├── tests/
├── specs/                   # SDD-артефакти по етапах
├── docs/decisions.md
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── CLAUDE.md
├── ROADMAP.md
└── README.md
```

---

## 6. Поза скоупом (не робити)

- Redis, Celery, Kafka та інші брокери.
- Ембеддинги / pgvector / векторні БД.
- Автентифікація користувачів, ролі (крім опційного Basic Auth).
- Дизайн UI, JS-фреймворки, SPA.
- Перевірка підпису вебхука, мультитенантність, метрики/Prometheus.
- Будь-які фічі, яких немає в ТЗ, — максимум згадка в README у розділі «Що далі».
