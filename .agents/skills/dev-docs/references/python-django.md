# Example: a Python project with Django apps

An illustration of one project's documentation conventions. It is not a rule for every project -- follow the format, language, and layout the project actually documents.

The project writes Google-style docstrings, keeps documentation text in Ukrainian with technical terms in English, and builds its documentation site with MkDocs.
Summary lines are descriptive third person ("Повертає…", "Створює…"), as Google style prescribes -- not the imperative mood of PEP 257.
A module's high-level documentation is extracted from its `__init__.py`; documentation for individual functions, classes, and methods is extracted from their own files.

Google style guide: <https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings>

## Module Overview in `__init__.py`

```python
"""Управління навчальними дисциплінами.

Відповідає за створення, редагування та публікацію дисциплін у навчальних планах.

Public API:
    Discipline — основна модель дисципліни.
    DisciplineService — сервіс для бізнес-логіки дисциплін.
    get_active_disciplines() — повертає список активних дисциплін поточного семестру.

Примітки:
    - Потребує налаштованого сигналу post_save для оновлення кешу навчального плану.
"""
```

## Architecture Decision Records in `__init__.py`

This project records module-level decisions in the same `__init__.py` docstring, under a `Decisions:` section, rather than in separate ADR files.

```python
"""Управління навчальними дисциплінами.

Відповідає за створення, редагування та публікацію дисциплін у навчальних планах.

Public API:
    Discipline — основна модель дисципліни.
    DisciplineService — сервіс для бізнес-логіки дисциплін.
    get_active_disciplines() — повертає список активних дисциплін поточного семестру.

Note:
    Потребує налаштованого сигналу post_save для оновлення кешу навчального плану.

Decisions:
    Сервісний шар винесено в окремий підпакет services/, а не в models.py,
    щоб уникнути циклічних імпортів між моделями та бізнес-логікою.
    Наслідок: усі зовнішні виклики бізнес-логіки проходять через DisciplineService.

    Кешування активних дисциплін виконується через Django cache framework,
    а не на рівні queryset, оскільки список змінюється рідко (раз на семестр)
    і читається дуже часто. Наслідок: при зміні дисципліни потрібно явно
    інвалідувати кеш через сигнал post_save.
"""
```

## Functions

```python
def fetch_user(user_id: int, include_deleted: bool = False) -> User | None:
    """Отримує користувача за ID з бази даних.

    Читає запис користувача, за потреби включаючи м’яко видалених користувачів.
    Повертає None, якщо відповідного користувача не існує.

    Args:
        user_id: Унікальний ідентифікатор користувача.
        include_deleted: Якщо True, повертає також м’яко видалених користувачів. Типово False.

    Returns:
        Об’єкт User, якщо знайдено, інакше None.

    Raises:
        DatabaseError: Якщо не вдається підключитися до бази даних.

    Example:
        >>> user = fetch_user(123)
        >>> user.email
        'user@example.com'
    """
```

## Classes

```python
class RateLimiter:
    """Обмежувач частоти запитів на основі токен-бакету для API-кінцевих точок.

    Реалізує алгоритм токен-бакету, який дозволяє короткі всплески при
    дотриманні середньої частоти обмеження. Токени регенерують із фіксованою
    швидкістю до максимуму.

    Attrs:
        rate: Кількість токенів, доданих за секунду.
        capacity: Максимальна кількість токенів у бакеті.

    Example:
        >>> limiter = RateLimiter(rate=10, capacity=100)
        >>> if limiter.acquire():
        ...     process_request()
    """

    def __init__(self, rate: float, capacity: int) -> None:
        """Ініціалізує обмежувач частоти запитів.

        Args:
            rate: Кількість токенів, що додаються за секунду.
            capacity: Максимальний розмір бакету.
        """
```

## Modules

```python
"""Аутентифікація користувача та управління сеансами.

Цей модуль надає утиліти аутентифікації, включаючи хешування паролей,
генерацію токенів та валідацію сеансів. Він інтегрується з моделлю User
та вимагає Redis для зберігання сеансів.

Typical usage example:
    from auth import authenticate, create_session

    user = authenticate(email, password)
    if user:
        session = create_session(user)
"""
```

## Short Docstrings

```python
def is_valid_email(email: str) -> bool:
    """Перевіряє, чи електронна адреса відповідає дійсному формату."""
```

## Inline Comments

```python
# GOOD: Explain why, not what
# Використовуємо бінарний пошук, оскільки список завжди відсортований і може містити 100k+ елементів
index = bisect.bisect_left(sorted_items, target)

# GOOD: Clarify non-obvious behavior
# Stripe вимагає суму в центах, а не в доларах
amount_cents = int(dollars * 100)

# GOOD: Document workarounds
# HACK: Затримка, щоб уникнути стану гонитви в застарілому API (див. issue #1234)
time.sleep(0.1)

# ПОГАНО: Повторення коду
# Збільшити лічильник на 1
counter += 1

# ПОГАНО: Очевидно з контексту
# Перевірити, чи користувач відсутній
if user is None:
```

## Endpoint Documentation

```python
@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Створює новий обліковий запис користувача.

    Створює користувача з вказаними email та ім’ям. Асинхронно надсилає
    вітальний лист. Повертає 409, якщо email уже існує.

    Args:
        user: Дані для створення користувача з email та ім’ям.

    Returns:
        Створений користувач із згенерованим ID і часовими мітками.

    Raises:
        HTTPException: 409, якщо email уже зареєстрований.
    """
```

## Schema Field Documentation

```python
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    """Тіло запиту для створення нового користувача."""

    email: str = Field(
        ...,
        description="User's email address",
        example="user@example.com",
    )
    name: str = Field(
        ...,
        description="User's display name",
        example="Jane Smith",
        min_length=1,
        max_length=100,
    )

class UserResponse(BaseModel):
    """Дані користувача, що повертаються API."""

    id: int = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User's email address")
    name: str = Field(..., description="User's display name")
    created_at: datetime = Field(..., description="Account creation timestamp")
```
