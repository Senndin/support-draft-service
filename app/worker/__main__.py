"""Воркер: `python -m app.worker`.

Запускає цикл генерації чернеток (етап 4); цикл надсилання (етап 6) додасться
поруч і зупинятиметься тією ж подією `stop` (SIGTERM/SIGINT).
"""

import asyncio
import logging
import signal

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import SessionLocal
from app.worker import generation

log = logging.getLogger("worker")


async def main(factory: async_sessionmaker = SessionLocal) -> None:
    """Працює, доки не надійде SIGTERM або SIGINT; потім штатно завершує цикли."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    log.info("worker started")
    try:
        async with httpx.AsyncClient() as client:
            await generation.run(factory, client, stop)
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)
    log.info("worker stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
