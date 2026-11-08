"""Воркер: `python -m app.worker`.

Поки що лише чекає на SIGTERM/SIGINT і штатно завершується.
Цикли генерації (етап 4) і надсилання (етап 6) запускатимуться всередині `main()`
і зупинятимуться тією ж подією `stop`.
"""

import asyncio
import logging
import signal

log = logging.getLogger("worker")


async def main() -> None:
    """Працює, доки не надійде SIGTERM або SIGINT."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    log.info("worker started")
    try:
        await stop.wait()
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)
    log.info("worker stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
