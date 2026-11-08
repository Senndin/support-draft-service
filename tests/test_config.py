"""Тести завантаження налаштувань з оточення (сценарій «Значення з оточення перекриває дефолт»)."""

from app.config import Settings


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("LLM_RPM", "30")
    assert Settings().llm_rpm == 30


def test_default_without_env(monkeypatch):
    monkeypatch.delenv("LLM_RPM", raising=False)
    assert Settings().llm_rpm == 60


def test_env_example_lists_every_setting():
    """`.env.example` містить рівно ті змінні, які читає `Settings`."""
    with open(".env.example") as f:
        keys = {line.split("=", 1)[0].strip() for line in f if "=" in line and not line.lstrip().startswith("#")}
    assert keys == {name.upper() for name in Settings.model_fields}
