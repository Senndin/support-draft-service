"""Тести опційного Basic Auth для `/ui`."""

import pytest

from app.config import settings
from tests.test_webhooks import event


@pytest.fixture
def password(monkeypatch):
    monkeypatch.setattr(settings, "operator_password", "s3cret")


async def test_ui_requires_password(client, password):
    r = await client.get("/ui")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Basic"
    assert (await client.get("/ui", auth=("operator", "wrong"))).status_code == 401
    assert (await client.post("/ui/tickets/1/reject")).status_code == 401


async def test_ui_with_password(client, password):
    assert (await client.get("/ui", auth=("anyone", "s3cret"))).status_code == 200


async def test_ui_open_without_password(client, monkeypatch):
    monkeypatch.setattr(settings, "operator_password", "")
    assert (await client.get("/ui")).status_code == 200


async def test_webhook_and_health_stay_open(client, password):
    assert (await client.post("/webhooks/helpdesk", json=event(event_id="auth-1"))).status_code == 202
    assert (await client.get("/health")).status_code == 200
