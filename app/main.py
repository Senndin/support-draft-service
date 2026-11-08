"""FastAPI-застосунок: підключення роутерів. Запуск: `uvicorn app.main:app`."""

from fastapi import FastAPI

from app.api import health, webhooks
from app.ui import routes as ui

app = FastAPI(title="Support Draft Service")
app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(ui.router)
