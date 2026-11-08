"""Воркер: працює до SIGTERM і завершується штатно (сценарій «Воркер працює до зупинки»)."""

import asyncio
import os
import signal

from app.worker.__main__ import main


async def test_worker_stops_on_sigterm(session_factory):
    task = asyncio.create_task(main(session_factory))
    await asyncio.sleep(0.2)  # даємо main() встановити обробники сигналів
    assert not task.done()
    os.kill(os.getpid(), signal.SIGTERM)
    await asyncio.wait_for(task, timeout=5)
