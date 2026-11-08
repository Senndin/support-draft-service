"""Воркер: `python -m app.worker`.

Запускає два цикли — генерацію чернеток і надсилання відповідей; обидва
зупиняються однією подією `stop` (SIGTERM/SIGINT).
"""

import asyncio
import logging
import signal

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import SessionLocal
from app.worker import generation, sending

log = logging.getLogger("worker")


async def main(factory: async_sessionmaker = SessionLocal, client: httpx.AsyncClient | None = None) -> None:
    """Працює, доки не надійде SIGTERM або SIGINT; потім штатно завершує цикли.

    `client` — HTTP-клієнт для LLM і хелпдеску (у тестах — з MockTransport).
    """
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    log.info("worker started")
    try:
        async with client or httpx.AsyncClient() as http:
            await asyncio.gather(generation.run(factory, http, stop), sending.run(factory, http, stop))
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)
    log.info("worker stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
