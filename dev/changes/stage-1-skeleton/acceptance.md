# stage-1-skeleton

## Межі

<!-- Scope -->

Людина перевіряє, що стек піднімається через `docker compose` у її власному оточенні (Docker Desktop, чистий клон), що повторні міграції не ламаються і що воркер штатно зупиняється.
`pytest` цього не бачить: тести запускають застосунок без Docker і без PostgreSQL.

## Сценарії

<!-- Scenarios -->

### 1. Підйом стеку на чистому клоні

<!-- Scenario -->

**Покриває:**

- [`service-runtime`](/dev/specs/service-runtime/spec.md): Підйом стеку на чистій машині
- [`health-check`](/dev/specs/health-check/spec.md): Сервіс запущений

**Передумови:** запущений Docker; порт `8000` хоста вільний.

**Кроки:**

1. `git clone <шлях-до-репозиторію> /tmp/ai-sup-check && cd /tmp/ai-sup-check`
2. `cp .env.example .env`
3. `docker compose up --build -d`
4. `docker compose ps -a`
5. `curl -i localhost:8000/health`

**Очікується:**

- `docker compose ps -a` показує `db`, `api` і `worker` у стані `running`, а `migrate` — `exited (0)`.
- `curl` повертає `HTTP/1.1 200 OK` і тіло `{"status":"ok"}`.

**Прибирання:** не зупиняти стек, якщо далі йдуть сценарії 2 і 3; після них — `docker compose down -v && rm -rf /tmp/ai-sup-check`.

**Результат:**

- [passed]

### 2. Повторний запуск міграцій

<!-- Scenario -->

**Покриває:**

- [`service-runtime`](/dev/specs/service-runtime/spec.md): Повторний запуск міграцій

**Передумови:** стек зі сценарію 1 піднятий.

**Кроки:**

1. `docker compose run --rm migrate; echo "exit=$?"`
2. `docker compose exec -T db psql -U postgres -d support -tc "select version_num from alembic_version"`

**Очікується:**

- Команда завершується з `exit=0`, без трейсбеку.
- `alembic_version` містить один рядок `325acc2e9ced`.

**Прибирання:** немає.

**Результат:**

- [passed]

### 3. Воркер штатно зупиняється

<!-- Scenario -->

**Покриває:**

- [`service-runtime`](/dev/specs/service-runtime/spec.md): Воркер працює до зупинки

**Передумови:** стек зі сценарію 1 піднятий.

**Кроки:**

1. `docker compose stop worker`
2. `docker compose logs worker`
3. `docker compose ps -a worker`

**Очікується:**

- У логах є `worker started`, потім `worker stopped`, без трейсбеку.
- `worker` у стані `exited (0)`.

**Прибирання:** `docker compose down -v && cd - && rm -rf /tmp/ai-sup-check`.

**Результат:**

- [passed]
