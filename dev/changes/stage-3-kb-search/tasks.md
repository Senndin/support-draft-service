# stage-3-kb-search

## 1. Content

- [ ] 1.1 Написати 8 статей ReportFlow у `kb/articles/*.md` (українською, front-matter `slug`, `title`, `url`): `export-pdf`, `payment-billing`, `account-access`, `slack-integration`, `csv-import`, `team-roles`, `cancel-subscription`, `notifications`.

## 2. Backend: Phase 1 – Model

- [ ] 2.1 Додати модель `KbArticle` в `app/models.py` (`slug` UNIQUE, `search_vector` — `Computed("to_tsvector('simple', title || ' ' || body)", persisted=True)`, GIN-індекс); тест: унікальність `slug`, `search_vector` — computed, індекс використовує `gin`.

## 3. DB Migrations

- [ ] 3.1 Написати ревізію Alembic `create_kb_articles` поверх `3021c65eeb7b`: `CREATE EXTENSION IF NOT EXISTS pg_trgm`, таблиця `kb_articles`, GIN-індекс `ix_kb_articles_search_vector`; `downgrade` — у зворотному порядку.

## 4. Backend: Phase 2 – Seed and Search

- [ ] 4.1 Реалізувати `scripts/seed_kb.py`: `load_articles(directory: Path) -> list[dict]` (ключі `slug`, `title`, `url`, `body`; без поля — `ValueError` з назвою файлу й поля), `seed(session, articles) -> None` (upsert за `slug`), `main()`; додати фікстуру `kb` у `tests/conftest.py`; тести: розбір front-matter, помилка без `slug`, повторний `seed` не дублює, змінений `title` оновлюється.
- [ ] 4.2 Реалізувати контракт `app/services/kb.py`: `to_query(text: str) -> str` і `async search(session: AsyncSession, query: str, limit: int = 3) -> list[KbArticle]` (FTS → fallback `word_similarity > 0.3`); тести: `to_query` відкидає короткі слова й обрізає до 5 символів, запит «Не можу експортувати звіт у PDF» → першою `export-pdf`, `limit=1` → одна стаття, опечатка → `slack-integration`, «qwxzv» → `[]`.

## 5. Infrastructure

- [ ] 5.1 Змінити команду сервісу `migrate` у `docker-compose.yml` на `sh -c "alembic upgrade head && python -m scripts.seed_kb"`; перевірити: після `docker compose up --build -d` у `kb_articles` 8 рядків.

## 6. Documentation

- [ ] 6.1 Оновити `AGENTS.md` (тестові дані: статті `kb/articles`, сід `uv run python -m scripts.seed_kb`) і додати рішення етапу 3 у `docs/decisions.md`.

## 7. Functional Tests

- [ ] 7.1 Написати end-to-end тести для сценаріїв «Експорт у PDF», «Ліміт», «Опечатка», «Нерелевантний запит» (`kb-search`) і «Повторний сід», «Оновлення статті», «Стаття без slug» (`kb-seed`) на тестовій БД.
