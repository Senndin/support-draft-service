# stage-4-llm-worker

## Межі

<!-- Scope -->

Людина перевіряє генерацію чернеток на живому стеку: з локальною Ollama (осмислена чернетка українською з посиланнями — ROADMAP вимагає ручної перевірки) і в режимі без ключа, а також штатну зупинку воркера під час генерації.
Тести покривають логіку на моках провайдера, але не оцінюють якість тексту справжньої моделі й не бачать поведінки зібраного образу в compose.

## Сценарії

<!-- Scenarios -->

### 1. Чернетка від Ollama

<!-- Scenario -->

**Покриває:**

- [`llm-draft`](/dev/specs/llm-draft/spec.md): Відповідь провайдера
- [`draft-generation`](/dev/specs/draft-generation/spec.md): Від received до draft_ready

**Передумови:** Ollama запущена на хості з моделлю, вказаною в `.env` (`LLM_MODEL`, напр. `qwen3.5:4b`), `LLM_API_KEY=ollama`, `LLM_BASE_URL=http://host.docker.internal:11434/v1`; стек піднятий: `docker compose up --build -d`.

**Кроки:**

1. `curl -s -X POST localhost:8000/webhooks/helpdesk -H 'Content-Type: application/json' -d '{"event_id":"acc4-1","ticket_id":"T-41","customer_email":"a@example.com","message":"Не можу експортувати звіт у PDF, кнопка неактивна","reply_url":"http://api:8000/mock/helpdesk/tickets/T-41/replies"}'`
2. Почекати до 2 хвилин і виконати: `docker compose exec -T db psql -U postgres -d support -c "select status, attempts, article_ids, draft from tickets where event_id = 'acc4-1'"`
3. `docker compose logs worker | tail -20`

**Очікується:**

- Статус `draft_ready`, `article_ids` непорожній.
- Чернетка написана українською, по суті відповідає на питання про експорт у PDF і посилається на статтю бази знань.
- У логах воркера є `draft ready` для цього звернення, без трейсбеків.

**Прибирання:** немає.

**Результат:**

- [failed] звернення `acc4-1` двічі впало з `LLMError: ReadTimeout` (`attempts=2`, статус `generating`): модель `qwen3.5:4b` за замовчуванням міркує тисячі токенів (5005 на коротке питання) і не вкладається в `LLM_TIMEOUT_S=60`; з `reasoning_effort: none` та сама модель відповідає за 2 с
  - Root cause: `_call_provider` надсилає лише `model` і `messages`, тож режимом міркувань не можна керувати через оточення, і моделі з міркуванням за замовчуванням не вкладаються в `LLM_TIMEOUT_S`; окремо порожній `choices[0].message.content` приймається як чернетка -- `app/services/llm.py:68`, `app/services/llm.py:108`
  - Reproducing test: при `llm_reasoning_effort="none"` тіло запиту містить `reasoning_effort: none`, при порожньому — не містить; відповідь з порожнім `content` дає `LLMError` -- `tests/test_llm.py:67`
  - Fix: поле `llm_reasoning_effort` у `Settings` і `LLM_REASONING_EFFORT=` у `.env.example`; `reasoning_effort` у тілі запиту, лише якщо задано; порожній `content` → `LLMError` -- `app/config.py:15`, `app/services/llm.py:68`, `app/services/llm.py:108`
  - Specification impact: declared: dev/specs/llm-draft/spec.md
- [passed] повторний прогін після виправлення `86268b8`, виконано агентом на прохання користувача: з `LLM_REASONING_EFFORT=none` звернення `acc4-1b` → `draft_ready` з першої спроби за кілька секунд, чернетка українською з посиланням на `export-pdf`, у логах `draft ready` без трейсбеків

### 2. Режим без ключа

<!-- Scenario -->

**Покриває:**

- [`llm-draft`](/dev/specs/llm-draft/spec.md): Статична чернетка зі статтями
- [`llm-draft`](/dev/specs/llm-draft/spec.md): Провайдер недоступний без ключа

**Передумови:** стек піднятий.

**Кроки:**

1. У `.env` встановити `LLM_API_KEY=` (порожньо), залишити `STUB_DELAY_MIN_S=5`, `STUB_DELAY_MAX_S=30`.
2. `docker compose up -d worker` (перестворить воркер з новим `.env`).
3. `curl -s -X POST localhost:8000/webhooks/helpdesk -H 'Content-Type: application/json' -d '{"event_id":"acc4-2","ticket_id":"T-42","customer_email":"a@example.com","message":"Як скасувати підписку?","reply_url":"http://api:8000/mock/helpdesk/tickets/T-42/replies"}'`
4. Через 30–40 с: `docker compose exec -T db psql -U postgres -d support -c "select status, draft from tickets where event_id = 'acc4-2'"`
5. `docker compose logs worker | grep "без ключа"`

**Очікується:**

- Статус `draft_ready`; чернетка — статичний шаблон із назвою й URL статті про скасування підписки.
- У логах рядок `LLM без ключа відповів <статус> (ігноруємо)` або `LLM без ключа недоступний ... (ігноруємо)` — реальний запит був зроблений.

**Прибирання:** повернути `LLM_API_KEY=ollama` у `.env` і виконати `docker compose up -d worker`.

**Результат:**

- [passed] виконано агентом на прохання користувача: звернення `acc4-2c` → `draft_ready` зі статичним шаблоном (назви й URL `cancel-subscription`, `payment-billing`), у логах `LLM без ключа відповів 200 (ігноруємо)`

### 3. Зупинка воркера під час генерації

<!-- Scenario -->

**Покриває:**

- [`draft-generation`](/dev/specs/draft-generation/spec.md): Зупинка під час генерації
- [`service-runtime`](/dev/specs/service-runtime/spec.md): Воркер працює до зупинки

**Передумови:** стек піднятий у режимі без ключа зі сценарію 2, але з `STUB_DELAY_MIN_S=40` і `STUB_DELAY_MAX_S=40` у `.env` (`docker compose up -d worker` після зміни).

**Кроки:**

1. `curl -s -X POST localhost:8000/webhooks/helpdesk -H 'Content-Type: application/json' -d '{"event_id":"acc4-3","ticket_id":"T-43","customer_email":"a@example.com","message":"Не приходить лист для скидання пароля","reply_url":"http://api:8000/mock/helpdesk/tickets/T-43/replies"}'`
2. Через 3 с переконатися, що статус `generating`: `docker compose exec -T db psql -U postgres -d support -tc "select status from tickets where event_id = 'acc4-3'"`
3. `docker compose stop worker`
4. Повторити запит кроку 2 зі стовпцями `status, locked_until, attempts`.
5. `docker compose logs worker | tail -5`

**Очікується:**

- Зупинка триває ~25 с, у логах `stopping: waiting for 1 generation(s)`, `releasing 1 unfinished ticket(s)`, `worker stopped`, без трейсбеку.
- Після зупинки звернення має статус `received`, порожній `locked_until`, `attempts = 0`.

**Прибирання:** повернути в `.env` `LLM_API_KEY=ollama`, `STUB_DELAY_MIN_S=5`, `STUB_DELAY_MAX_S=30`; `docker compose up -d worker` (звернення `acc4-3` буде оброблене).

**Результат:**

- [passed] виконано агентом на прохання користувача: `docker compose stop worker` тривав 25.4 с, у логах `stopping: waiting for 1 generation(s)`, `releasing 1 unfinished ticket(s)`, `worker stopped` без трейсбеку; `acc4-3` → `received`, `locked_until` порожній, `attempts = 0`
