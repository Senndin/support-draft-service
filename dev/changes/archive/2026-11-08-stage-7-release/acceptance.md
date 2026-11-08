# stage-7-release

## Межі

<!-- Scope -->

Людина оцінює README як інструкцію (чи можна за ним запустити сервіс, налаштувати LLM і зрозуміти рішення) і відтворює навантажувальний прогін у своєму оточенні.
Тести перевіряють розрахунок затримок, але не якість документа і не реальне навантаження на зібраний стек.

## Сценарії

<!-- Scenarios -->

### 1. README як інструкція

<!-- Scenario -->

**Покриває:**

- [`webhook-sender`](/dev/specs/webhook-sender/spec.md): Звіт про затримки

**Передумови:** немає.

**Кроки:**

1. Прочитати `README.md` від початку до кінця.
2. Виконати команди розділу «Швидкий старт» (`cp .env.example .env` пропустити, якщо `.env` уже є) і відкрити три посилання з нього.
3. Виконати `uv run python -m scripts.send_webhooks --count 20 --dup-rate 0`.

**Очікується:**

- README зрозумілий: архітектура, запуск, налаштування LLM (Ollama, хмарний провайдер, режим без ключа), тести, навантаження, рішення й обмеження, деплой.
- `/health`, `/ui` і `/mock/helpdesk/replies` відкриваються.
- Скрипт друкує `sent: 20`, `202: 20` і рядок `latency ms: p50=… p99=… max=…`.

**Прибирання:** немає.

**Результат:**

- [failed] посилання й скрипт працюють (`sent: 20`, `202: 20`, `latency ms: p50=19 p99=47 max=48`), але README недостатньо готовий для публікації на GitHub і показу роботодавцю
  - Root cause: README написаний як внутрішня інструкція — без короткої презентації проєкту, ключових інженерних результатів, скриншотів UI, змісту, структури репозиторію та опису AI-first процесу розробки -- `README.md:1`
  - Reproducing test: немає автоматичного — оцінка документа людиною (цей сценарій)
  - Fix: переписати вступ і структуру README під публічну вітрину: опис, ключові результати, скриншоти, зміст, структура, процес розробки -- `README.md:1`
  - Specification impact: code-only
- [passed] повторна оцінка після переписування README (`2724a7f`): опис, ключові результати, скриншоти UI, таблиця вимог ТЗ, структура репозиторію й AI-first процес — готово до публікації

### 2. Навантажувальний прогін

<!-- Scenario -->

**Покриває:**

- [`webhook-intake`](/dev/specs/webhook-intake/spec.md): Одночасні дублі
- [`webhook-sender`](/dev/specs/webhook-sender/spec.md): Прогін із дублями

**Передумови:** стек піднятий; у `.env` `LLM_API_KEY=` і `STUB_DELAY_MIN_S=0`, `STUB_DELAY_MAX_S=0`, потім `docker compose up -d --force-recreate api worker`.

**Кроки:**

1. `docker compose exec -T db psql -U postgres -d support -c "truncate tickets restart identity"`
2. `uv run python -m scripts.send_webhooks --count 500 --dup-rate 0.2 --concurrency 50`
3. `docker compose exec -T db psql -U postgres -d support -c "select count(*) as rows, count(distinct event_id) as unique_events from tickets"`

**Очікується:**

- Скрипт друкує `sent: 600`, `202: 600`, без `error`, і `p99` у рядку затримок менше `2000`.
- `rows = 500` і `unique_events = 500`.
- Числа близькі до таблиці «Навантажувальний прогін» у README.

**Прибирання:** `docker compose stop worker && docker compose exec -T db psql -U postgres -d support -c "truncate tickets restart identity"`; повернути в `.env` `LLM_API_KEY=ollama`, `STUB_DELAY_MIN_S=5`, `STUB_DELAY_MAX_S=30`; `docker compose up -d --force-recreate api worker`.

**Результат:**

- [passed] `sent: 600`, `202: 600`, без помилок, `latency ms: p50=58 p99=129 max=133`; `rows = 500`, `unique_events = 500` — збігається з таблицею в README
