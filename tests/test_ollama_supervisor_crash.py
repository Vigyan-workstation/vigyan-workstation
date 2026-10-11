"""A crashed child is detected and restarted, with a cap on retries."""
from __future__ import annotations

import os
import signal
import sys
import time
from collections.abc import Callable, Iterator

import pytest

from ollama_supervisor import OllamaSupervisor

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]
CRASHER = [sys.executable, "-c", "pass"]  # exits immediately


def _wait_for(fn: Callable[[], bool], timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fn():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def supervisor() -> Iterator[OllamaSupervisor]:
    sup = OllamaSupervisor(SLEEPER, is_healthy=lambda: False)
    yield sup
    sup.stop()


def test_crash_is_detected_and_child_restarted(supervisor: OllamaSupervisor) -> None:
    supervisor.start()
    first_pid = supervisor.pid
    assert first_pid is not None
    os.kill(first_pid, getattr(signal, "SIGKILL", signal.SIGTERM))  # simulate a crash
    assert _wait_for(supervisor.check), "crash was never detected"
    assert supervisor.pid not in (None, first_pid)
    assert supervisor.owns_process


def test_restarts_are_capped() -> None:
    sup = OllamaSupervisor(
        CRASHER, is_healthy=lambda: False, max_restarts=1, die_with_parent=False
    )
    sup.start()
    restarts = 0
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if sup.check():
            restarts += 1
        time.sleep(0.05)
    sup.stop()
    assert restarts == 1


def test_stop_does_not_trigger_restart(supervisor: OllamaSupervisor) -> None:
    supervisor.start()
    supervisor.stop()
    assert supervisor.check() is False
    assert supervisor.pid is None
