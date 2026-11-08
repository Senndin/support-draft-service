# stage-4-llm-worker

## 1. Backend: Phase 1 – LLM Layer

- [ ] 1.1 Реалізувати `app/services/ratelimit.py`: `RateLimiter(rate: int, period: float)` з `async acquire() -> None` (ковзне вікно); тести: 6 одночасних `acquire` при `RateLimiter(3, 0.5)` — перші 3 миттєво, решта ≥ 0.5 с, у жодному вікні 0.5 с не більше 3.
- [ ] 1.2 Визначити контракт `app/services/llm.py`: `DraftResult(text: str, article_ids: list[int])`, `LLMError`, `async generate_draft(message: str, articles: list[KbArticle], client: httpx.AsyncClient) -> DraftResult`; реалізувати гілку з ключем (промпт із `design.md`, `Authorization: Bearer`, лімітер і семафор) і помилки → `LLMError`; тести через `httpx.MockTransport`: текст із `choices[0].message.content`, `article_ids` переданих статей, заголовок, модель і URL статей у запиті; `500`, таймаут і відповідь без `choices` → `LLMError`.
- [ ] 1.3 Реалізувати гілку без ключа в `generate_draft`: запит без `Authorization` через ті самі обмеження, статус або помилка лише логуються, затримка `uniform(STUB_DELAY_MIN_S, STUB_DELAY_MAX_S)`, статична чернетка з назвами й URL статей або пропозицією оператора без статей; тести: чернетка містить назви й URL, `Authorization` відсутній, `ConnectError` не ламає генерацію, без статей — порожній `article_ids`; при `LLM_CONCURRENCY=2` до провайдера одночасно не більше 2 запитів.

## 2. Backend: Phase 2 – Generation Worker

- [ ] 2.1 Реалізувати в `app/worker/generation.py` `async claim(session: AsyncSession, limit: int) -> list[Ticket]` (`UPDATE ... WHERE id IN (SELECT ... FOR UPDATE SKIP LOCKED) RETURNING`, lease 300 с); тести: захоплює `received` з настанням `next_attempt_at`, не бере майбутній `next_attempt_at`, повторно бере `generating` з протермінованим lease, два одночасні захоплення не перетинаються.
- [ ] 2.2 Реалізувати `async process(factory, ticket: Ticket, client: httpx.AsyncClient) -> None` (KB → `generate_draft` → `draft_ready`) і обробку помилок (`attempts`, `last_error`, backoff `10·2^(attempts−1)` с, після 5-ї — `generation_failed`); тести: успіх записує `draft` і `article_ids`, помилка повертає в `received` з `next_attempt_at` ≈ +10 с, при `attempts=4` — `generation_failed`.
- [ ] 2.3 Реалізувати `async run(factory, client, stop: asyncio.Event) -> None` з захопленням за вільними слотами, опитуванням раз на 1 с і штатною зупинкою (очікування до 25 с, скасування, `release`), підключити його в `app/worker/__main__.py` з одним `httpx.AsyncClient`; тести: `run` обробляє звернення до `draft_ready` і зупиняється за `stop`; при зупинці під час довгої генерації (час очікування зменшено) звернення повертається в `received` з порожнім `locked_until`; оновити `tests/test_worker.py` під БД.

## 3. Documentation

- [ ] 3.1 Оновити `AGENTS.md` (режим без ключа для локальних тестів: `LLM_API_KEY=` і `STUB_DELAY_*=0`) і додати рішення етапу 4 у `docs/decisions.md`.

## 4. Functional Tests

- [ ] 4.1 Написати end-to-end тести для сценаріїв `llm-draft`: «Відповідь провайдера», «Провайдер повертає 500», «Статична чернетка зі статтями», «Провайдер недоступний без ключа», «Статей немає».
- [ ] 4.2 Написати end-to-end тести для сценаріїв `llm-rate-limit`: «Перевищення ліміту», «Паралельні генерації».
- [ ] 4.3 Написати end-to-end тести для сценаріїв `draft-generation`: «Від received до draft_ready», «Два одночасні захоплення», «Повторне захоплення», «Тимчасова помилка», «Вичерпані спроби», «Зупинка під час генерації».
