"""Налаштування сервісу. Усі значення читаються зі змінних оточення (без урахування регістру)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфігурація застосунку; повний перелік змінних — у `.env.example`."""

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/support"

    # LLM: OpenAI-сумісний API; порожній ключ вмикає режим без ключа (див. ROADMAP, 3.3)
    llm_base_url: str = "http://host.docker.internal:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:7b-instruct"
    llm_timeout_s: float = 60
    # reasoning_effort для моделей з міркуванням (напр. "none" для qwen3.5); порожньо — не надсилається
    llm_reasoning_effort: str = ""
    llm_rpm: int = 60
    llm_concurrency: int = 4
    stub_delay_min_s: float = 5
    stub_delay_max_s: float = 30


settings = Settings()
