"""End-to-end: сценарій «Сервіс запущений» (health-check) на справжньому процесі uvicorn."""

import socket
import subprocess
import sys
import time

import httpx


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_running_service_answers_health():
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)])
    try:
        # чекаємо, поки сервер почне приймати з'єднання
        for _ in range(50):
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/health")
                break
            except httpx.ConnectError:
                time.sleep(0.1)
        else:
            raise AssertionError("uvicorn не стартував за 5 с")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        proc.terminate()
        proc.wait(timeout=5)
