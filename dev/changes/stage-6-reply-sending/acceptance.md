# stage-6-reply-sending

## Межі

<!-- Scope -->

Людина перевіряє доставку відповіді на живому стеку: повний шлях від Approve в UI до відповіді в моку хелпдеску, а також поведінку при збоях мока (`5xx` і «повільних» відповідях) за справжніх мережевих таймаутів.
Тести ганяють надсилання через ASGI-транспорт, де таймаути імітуються обгорткою; справжній таймаут `httpx` між контейнерами `worker` і `api` вони не бачать.

## Сценарії

<!-- Scenarios -->

### 1. Від Approve до відповіді в хелпдеску

<!-- Scenario -->

**Покриває:**

- [`reply-sending`](/dev/specs/reply-sending/spec.md): Успішне надсилання
- [`helpdesk-mock`](/dev/specs/helpdesk-mock/spec.md): Нова відповідь

**Передумови:** стек піднятий (`docker compose up --build -d`), `MOCK_FAIL_RATE=0`, `MOCK_SLOW_RATE=0` у `.env`; є звернення в `draft_ready` (див. `acceptance.md` етапу 5).

**Кроки:**

1. Відкрити `http://localhost:8000/ui?status=draft_ready`, відкрити картку звернення, натиснути **Approve**.
2. Через 2–3 с оновити картку.
3. Відкрити `http://localhost:8000/mock/helpdesk/replies`.

**Очікується:**

- Картка показує статус `sent`.
- У списку мока є рівно одна відповідь для цього `ticket_id` з текстом, підтвердженим в UI, і непорожнім `idempotency_key`.

**Прибирання:** немає.

**Результат:**

- [ ]

### 2. Нестабільний хелпдеск

<!-- Scenario -->

**Покриває:**

- [`reply-sending`](/dev/specs/reply-sending/spec.md): Два 5xx, потім успіх
- [`reply-sending`](/dev/specs/reply-sending/spec.md): Таймаут, але відповідь прийнята
- [`helpdesk-mock`](/dev/specs/helpdesk-mock/spec.md): Повтор з тим самим ключем
- [`helpdesk-mock`](/dev/specs/helpdesk-mock/spec.md): Повільна відповідь приймається

**Передумови:** у `.env` встановити `MOCK_FAIL_RATE=0.3`, `MOCK_SLOW_RATE=0.3`, `HELPDESK_TIMEOUT_S=2`, `LLM_API_KEY=` і `STUB_DELAY_MIN_S=0`, `STUB_DELAY_MAX_S=0` (швидкі чернетки), потім `docker compose up -d --force-recreate api worker`.

**Кроки:**

1. `uv run python -m scripts.send_webhooks --count 10 --dup-rate 0`
2. Через ~5 с відкрити `http://localhost:8000/ui?status=draft_ready` і підтвердити (**Approve**) усі 10 нових звернень.
3. Почекати ~1 хвилину і виконати: `docker compose exec -T db psql -U postgres -d support -c "select status, count(*), max(attempts) from tickets where ticket_id like 'T-%' group by status"`
4. `curl -s localhost:8000/mock/helpdesk/replies | python3 -c "import json,sys,collections; r=json.load(sys.stdin); c=collections.Counter(x['idempotency_key'] for x in r); print(len(r), 'replies;', sum(v>1 for v in c.values()), 'duplicate keys')"`
5. `docker compose logs worker | grep -E "send attempt|reply sent" | tail -10`

**Очікується:**

- Усі 10 підтверджених звернень у статусі `sent`; у деяких `attempts` > 0 (були повтори).
- Скрипт кроку 4 показує `0 duplicate keys`, а відповідей рівно стільки, скільки звернень надіслано.
- У логах воркера є рядки `send attempt N failed, retry in ...` (`500` або `ReadTimeout`) і `reply sent`.

**Прибирання:** повернути в `.env` `MOCK_FAIL_RATE=0`, `MOCK_SLOW_RATE=0`, `HELPDESK_TIMEOUT_S=10`, `LLM_API_KEY=ollama`, `STUB_DELAY_MIN_S=5`, `STUB_DELAY_MAX_S=30`; `docker compose up -d --force-recreate api worker`.

**Результат:**

- [ ]

### 3. Хелпдеск постійно недоступний

<!-- Scenario -->

**Покриває:**

- [`reply-sending`](/dev/specs/reply-sending/spec.md): Вичерпані спроби надсилання
- [`helpdesk-mock`](/dev/specs/helpdesk-mock/spec.md): Завжди 500

**Передумови:** у `.env` `MOCK_FAIL_RATE=1`, `docker compose up -d --force-recreate api worker`; є звернення в `draft_ready`.

**Кроки:**

1. Підтвердити звернення в UI (**Approve**).
2. Почекати ~2 хвилини (8 спроб із наростаючою затримкою, максимум ~2 хв сумарно) і відкрити його картку.
3. `curl -s localhost:8000/mock/helpdesk/replies` — знайти цей `ticket_id`.

**Очікується:**

- Картка показує статус `send_failed` і «Остання помилка» з `500`.
- У моку немає відповіді для цього `ticket_id`.

**Прибирання:** `MOCK_FAIL_RATE=0` у `.env`, `docker compose up -d --force-recreate api worker`.

**Результат:**

- [ ]
