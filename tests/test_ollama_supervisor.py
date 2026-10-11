"""Lifecycle tests for the Ollama supervisor (no GUI, no network, no real Ollama)."""
from __future__ import annotations

import os
import sys
from collections.abc import Iterator

import pytest

from ollama_supervisor import OllamaSupervisor

# A harmless stand-in for "ollama serve": sleeps for a minute.
SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)  # signal 0 = existence check only
    except ProcessLookupError:
        return False
    return True


@pytest.fixture
def supervisor() -> Iterator[OllamaSupervisor]:
    sup = OllamaSupervisor(SLEEPER, is_healthy=lambda: False)
    yield sup
    sup.stop()  # never leak a child, even if a test fails


def test_spawns_child_when_not_healthy(supervisor: OllamaSupervisor) -> None:
    assert supervisor.start() is True
    assert supervisor.pid is not None
    assert _alive(supervisor.pid)
    assert supervisor.owns_process


def test_does_not_spawn_when_already_healthy() -> None:
    sup = OllamaSupervisor(SLEEPER, is_healthy=lambda: True)
    assert sup.start() is False
    assert sup.pid is None
    assert not sup.owns_process


def test_second_start_does_not_spawn_again(supervisor: OllamaSupervisor) -> None:
    supervisor.start()
    first_pid = supervisor.pid
    assert supervisor.start() is False
    assert supervisor.pid == first_pid


def test_stop_terminates_and_reaps_child(supervisor: OllamaSupervisor) -> None:
    supervisor.start()
    pid = supervisor.pid
    assert pid is not None
    supervisor.stop()
    assert not _alive(pid)
    assert not supervisor.owns_process


def test_stop_without_start_is_harmless(supervisor: OllamaSupervisor) -> None:
    supervisor.stop()
