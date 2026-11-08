"""Клієнт хелпдеску: надсилання відповіді клієнту на `reply_url`.

Один `Idempotency-Key` на всі спроби — хелпдеск, що його поважає, не покаже клієнту дубль.
"""

import httpx

from app.config import settings

RETRYABLE_STATUSES = {408, 429}


class SendError(Exception):
    """Відповідь не доставлено; `retryable` — чи має сенс повторити."""

    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


async def send_reply(client: httpx.AsyncClient, url: str, message: str, idempotency_key: str) -> None:
    """`POST url` з `{"message": ...}`; `SendError` при таймауті, мережевій помилці чи не-2xx."""
    try:
        response = await client.post(
            url,
            json={"message": message},
            headers={"Idempotency-Key": idempotency_key},
            timeout=settings.helpdesk_timeout_s,
        )
    except httpx.HTTPError as exc:
        raise SendError(f"{type(exc).__name__}: {exc}", retryable=True) from exc
    if response.is_success:
        return
    retryable = response.status_code >= 500 or response.status_code in RETRYABLE_STATUSES
    raise SendError(f"хелпдеск відповів {response.status_code}: {response.text[:200]}", retryable=retryable)
