# stage-2-webhooks

## Межі

<!-- Scope -->

Людина перевіряє вебхук і скрипт-імітатор на живому стеку в Docker: справжній `uvicorn` за портом `8000`, PostgreSQL у контейнері, запити з хоста.
`pytest` ганяє ці сценарії через ASGI-транспорт на тестовій БД, але не бачить роботи зібраного образу й compose-мережі.

## Сценарії

<!-- Scenarios -->

### 1. Нова подія і дубль через curl

<!-- Scenario -->

**Покриває:**

- [`webhook-intake`](/dev/specs/webhook-intake/spec.md): Нова подія
- [`webhook-intake`](/dev/specs/webhook-intake/spec.md): Послідовний дубль
- [`webhook-intake`](/dev/specs/webhook-intake/spec.md): Відсутнє поле

**Передумови:** у корені репозиторію є `.env` (`cp .env.example .env`); стек піднятий: `docker compose up --build -d`.

**Кроки:**

1. `curl -i -X POST localhost:8000/webhooks/helpdesk -H 'Content-Type: application/json' -d '{"event_id":"acc-1","ticket_id":"T-1","customer_email":"a@example.com","message":"Привіт","reply_url":"http://api:8000/mock/helpdesk/tickets/T-1/replies"}'`
2. Повторити крок 1, замінивши `"Привіт"` на `"Інший текст"`.
3. `curl -i -X POST localhost:8000/webhooks/helpdesk -H 'Content-Type: application/json' -d '{"ticket_id":"T-1"}'`
4. `docker compose exec -T db psql -U postgres -d support -c "select event_id, status, message from tickets where event_id = 'acc-1'"`

**Очікується:**

- Кроки 1 і 2 повертають `HTTP/1.1 202 Accepted` і `{"status":"accepted"}`.
- Крок 3 повертає `HTTP/1.1 422 Unprocessable Entity`.
- Крок 4 показує рівно один рядок: `acc-1 | received | Привіт`.

**Прибирання:** `docker compose exec -T db psql -U postgres -d support -c "delete from tickets where event_id = 'acc-1'"`

**Результат:**

- [passed]

### 2. Прогін скрипта з дублями

<!-- Scenario -->

**Покриває:**

- [`webhook-sender`](/dev/specs/webhook-sender/spec.md): Прогін із дублями
- [`webhook-sender`](/dev/specs/webhook-sender/spec.md): Звіт про відповіді
- [`webhook-intake`](/dev/specs/webhook-intake/spec.md): Одночасні дублі

**Передумови:** стек зі сценарію 1 піднятий.

**Кроки:**

1. `docker compose exec -T db psql -U postgres -d support -tc "select count(*) from tickets"` — запам'ятати число `N`.
2. `uv run python -m scripts.send_webhooks --count 20 --dup-rate 0.5 --concurrency 10`
3. Повторити крок 1.

**Очікується:**

- Скрипт виводить `sent: 30` і `202: 30`, рядка `error` немає.
- Після прогону в таблиці `N + 20` рядків.

**Прибирання:** `docker compose down` (або залишити стек для наступних етапів).

**Результат:**

- [passed]
