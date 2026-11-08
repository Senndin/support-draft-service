# stage-3-kb-search

## Межі

<!-- Scope -->

Людина перевіряє, що на живому стеку база знань засівається сервісом `migrate`, а статті читаються як осмислені відповіді підтримки українською.
Тести перевіряють пошук і сід на тестовій БД, але не оцінюють якість текстів статей і не бачать сіду в зібраному образі.

## Сценарії

<!-- Scenarios -->

### 1. Сід при запуску стеку

<!-- Scenario -->

**Покриває:**

- [`kb-seed`](/dev/specs/kb-seed/spec.md): Сід при запуску стеку
- [`kb-seed`](/dev/specs/kb-seed/spec.md): Повторний сід

**Передумови:** у корені є `.env`; Docker запущений.

**Кроки:**

1. `docker compose down -v`
2. `docker compose up --build -d`
3. `docker compose logs migrate | tail -3`
4. `docker compose exec -T db psql -U postgres -d support -tc "select count(*) from kb_articles"`
5. `docker compose run --rm migrate` і повторити крок 4.

**Очікується:**

- У логах `migrate` є рядок `seeded 8 kb articles`, сервіс завершився з кодом `0`.
- Обидва рази крок 4 показує `8`.

**Прибирання:** немає (стек можна залишити для наступних етапів).

**Результат:**

- [ ]

### 2. Якість статей і пошуку

<!-- Scenario -->

**Покриває:**

- [`kb-search`](/dev/specs/kb-search/spec.md): Експорт у PDF

**Передумови:** стек зі сценарію 1 піднятий.

**Кроки:**

1. Переглянути файли `kb/articles/*.md`.
2. Виконати пошук трьох запитів у контейнері `api`:

```bash
docker compose exec -T api python - <<'PY'
import asyncio
from app.db import SessionLocal
from app.services.kb import search
async def main():
    async with SessionLocal() as s:
        for q in ["Не можу експортувати звіт у PDF", "Як скасувати підписку і повернути гроші?", "не приходить лист для скидання пароля"]:
            print(q, "->", [a.slug for a in await search(s, q)])
asyncio.run(main())
PY
```

**Очікується:**

- Статті написані грамотною українською, кожна відповідає на типове звернення своєї теми.
- Для трьох запитів першими йдуть відповідно `export-pdf`, `cancel-subscription` і `account-access`.

**Прибирання:** немає.

**Результат:**

- [ ]
