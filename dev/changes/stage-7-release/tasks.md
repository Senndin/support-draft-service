# stage-7-release

## 1. Tooling

- [x] 1.1 Додати в `scripts/send_webhooks.py` вимір затримок: `send_all(...) -> tuple[Counter, list[float]]`, `latency_summary(durations: list[float]) -> str | None` (рядок `latency ms: p50=… p99=… max=…` через `statistics.quantiles`), друк у `main()`; оновити наявні виклики `send_all` у тестах; тести: `latency_summary([])` → `None`, для відомого набору — очікувані p50/p99/max, `p50 ≤ p99 ≤ max`, мережеві помилки не потрапляють у затримки.

## 2. Infrastructure

- [x] 2.1 Прив'язати порт `db` у `docker-compose.yml` до `127.0.0.1` (`"127.0.0.1:${DB_PORT:-5432}:5432"`); перевірити: тести з хоста проходять, `docker compose port db 5432` показує `127.0.0.1`.

## 3. Load Check

- [x] 3.1 Виконати навантажувальний прогін за `design.md` (режим без ключа, `STUB_DELAY_*=0`, чиста `tickets`, `--count 500 --dup-rate 0.2 --concurrency 50`) і зафіксувати: вивід скрипта, `count(*)`, `count(distinct event_id)`, p99; повернути `.env` у попередній стан.

## 4. Documentation

- [x] 4.1 Написати `README.md` за розділами з `design.md`, з результатами прогону задачі 3.1 і інструкцією деплою на VPS.
- [x] 4.2 Додати у `docs/decisions.md` вступ і зміст за етапами; в `AGENTS.md` — посилання на `README.md` у ключових джерелах.

## 5. Functional Tests

- [x] 5.1 Написати end-to-end тести для сценаріїв «Звіт про затримки» і «Без відповідей немає затримок» (`webhook-sender`).
