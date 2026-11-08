# stage-6-reply-sending

## 1. Backend: Phase 1 – Helpdesk Mock

- [ ] 1.1 Додати в `Settings` і `.env.example` `helpdesk_timeout_s: float = 10`, `mock_fail_rate: float = 0`, `mock_slow_rate: float = 0`; тест `.env.example` лишається зеленим, дефолти перевірено.
- [ ] 1.2 Реалізувати мок `app/mock_helpdesk/routes.py` за `design.md`: `POST /mock/helpdesk/tickets/{ticket_id}/replies` → `201` з `{id, ticket_id, message, idempotency_key, received_at}`, дедуплікація за `Idempotency-Key`, `MOCK_FAIL_RATE` → `500` без збереження, `MOCK_SLOW_RATE` → збереження, потім затримка `2 × HELPDESK_TIMEOUT_S`; `GET /mock/helpdesk/replies`; функція `reset()` для тестів; підключити роутер у `app/main.py`; тести: нова відповідь, повтор з ключем — той самий `id` і одна відповідь, без ключа — дві, `MOCK_FAIL_RATE=1` → `500`, `MOCK_SLOW_RATE=1` — відповідь збережена до кінця затримки.

## 2. Backend: Phase 2 – Sending

- [ ] 2.1 Визначити контракт `app/services/helpdesk.py`: `async send_reply(client: httpx.AsyncClient, url: str, message: str, idempotency_key: str) -> None` і `SendError(message, retryable: bool)`; тести через `httpx.MockTransport`: тіло `{"message": ...}`, заголовок `Idempotency-Key`, `2xx` — без винятку, `500`/`408`/`429`/`ReadTimeout`/`ConnectError` → `retryable=True`, `404` → `retryable=False`.
- [ ] 2.2 Винести спільний цикл у `app/worker/loop.py: run_queue(...)` і перевести на нього `generation.run` без зміни поведінки; тести генерації (`run`, зупинка) лишаються зеленими.
- [ ] 2.3 Реалізувати `app/worker/sending.py`: `claim` (`approved` з настанням `next_attempt_at` і `sending` з протермінованим lease, lease 60 с), `process` (→ `sent`; тимчасова помилка → `approved`, `attempts+1`, backoff з jitter; 8-ма спроба або постійна помилка → `send_failed`), `release`, `run` (до 10 одночасно); тести: успіх → `sent`, `500` → `approved` з `attempts=1` і `next_attempt_at` ≤ +1 с, `attempts=7` → `send_failed`, `404` → `send_failed`, протермінований lease захоплюється знову.
- [ ] 2.4 Обнулити `attempts`, `last_error` і поставити `next_attempt_at=now()` при approve (`app/ui/routes.py`); запустити `sending.run` поруч із генерацією в `app/worker/__main__.py`; тести: approve звернення з `attempts=3` дає `attempts=0`; воркер обробляє `approved` до `sent` і зупиняється за SIGTERM.

## 3. Documentation

- [ ] 3.1 Оновити `AGENTS.md` (мок хелпдеску, `MOCK_FAIL_RATE`, `MOCK_SLOW_RATE`, `GET /mock/helpdesk/replies`) і додати рішення етапу 6 у `docs/decisions.md`.

## 4. Functional Tests

- [ ] 4.1 Написати end-to-end тести для сценаріїв `helpdesk-mock`: «Нова відповідь», «Повтор з тим самим ключем», «Завжди 500», «Повільна відповідь приймається».
- [ ] 4.2 Написати end-to-end тести для сценаріїв `reply-sending`: «Успішне надсилання», «Два 5xx, потім успіх», «Таймаут, але відповідь прийнята», «Вичерпані спроби надсилання», «Хелпдеск відповідає 404» — воркер надсилає через `ASGITransport` у справжній мок.
