# stage-5-operator-ui

## 1. Backend: Phase 1 – Setup

- [ ] 1.1 Додати залежності `jinja2` і `python-multipart` (`uv add`), поле `operator_password: str = ""` у `Settings` і `OPERATOR_PASSWORD=` у `.env.example`; тест: `Settings().operator_password == ""` без змінної, тест `.env.example` лишається зеленим.

## 2. Backend: Phase 2 – Operator UI

- [ ] 2.1 Реалізувати `GET /ui` у `app/ui/routes.py` (роутер `prefix="/ui"`, шаблони `base.html`, `list.html`): таблиця до 200 звернень новіші зверху, колонки статус / `ticket_id` / email / повідомлення / чернетка / статті з URL, посилання на картку, фільтр `?status=` з формою, `meta refresh 10`; підключити роутер у `app/main.py`; тести: рядок `draft_ready` з назвою й URL статті, фільтр ховає інші статуси, `meta refresh` присутній.
- [ ] 2.2 Реалізувати `GET /ui/tickets/{id}` (`ticket.html`): повідомлення, статус, статті, форма з `textarea name="final_message"` і кнопками Approve/Reject лише для `draft_ready`, `404` для неіснуючого; тести: `textarea` з чернеткою і обидві кнопки для `draft_ready`, без кнопок для `approved`, `404`.

## 3. Backend: Phase 3 – Moderation and Auth

- [ ] 3.1 Реалізувати `POST /ui/tickets/{id}/approve` (форма `final_message`) і `POST /ui/tickets/{id}/reject` через `decide()` з атомарним `UPDATE ... WHERE status='draft_ready' RETURNING id`: `303` на картку, `409` з `conflict.html`, `404`, `422` для порожнього тексту; approve зберігає `final_message` і `idempotency_key=uuid4()`; тести: approve з правкою, reject, порожній текст, approve після reject → `409`, неіснуючий → `404`.
- [ ] 3.2 Реалізувати `require_operator` (HTTP Basic, `secrets.compare_digest`) як залежність роутера `/ui`; тести: без пароля `401` з `WWW-Authenticate: Basic`, з паролем `200`, порожній `OPERATOR_PASSWORD` — `200` без автентифікації, `/webhooks/helpdesk` і `/health` доступні без неї.

## 4. Documentation

- [ ] 4.1 Оновити `AGENTS.md` (адреса UI `localhost:8000/ui`, `OPERATOR_PASSWORD`) і додати рішення етапу 5 у `docs/decisions.md`.

## 5. Functional Tests

- [ ] 5.1 Написати end-to-end тести для сценаріїв `operator-ui`: «Звернення з чернеткою в списку», «Фільтр draft_ready», «Картка з чернеткою», «Неіснуюче звернення».
- [ ] 5.2 Написати end-to-end тести для сценаріїв `moderation`: «Підтвердження з правкою», «Порожній текст», «Відхилення», «Два паралельні approve», «Approve після reject».
- [ ] 5.3 Написати end-to-end тести для сценаріїв `operator-auth`: «Без пароля відмова», «З паролем доступ», «Захист вимкнено», «Вебхук без автентифікації».
