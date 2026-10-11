"""A SIGKILLed parent must not leave the supervised child behind (Linux)."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from proc_helpers import alive

SRC = Path(__file__).resolve().parents[1] / "src"

# Runs in a separate throwaway parent process that we SIGKILL from the test.
HELPER = f"""
import sys, time
sys.path.insert(0, {str(SRC)!r})
from ollama_supervisor import OllamaSupervisor
sup = OllamaSupervisor(
    [sys.executable, "-c", "import time; time.sleep(60)"],
    is_healthy=lambda: False,
)
sup.start()
print(sup.pid, flush=True)
time.sleep(60)
"""


def _alive(pid: int) -> bool:
    return alive(pid)


def _wait_until_started(pid: int, timeout: float = 3.0) -> None:
    """Wait until setpriv has set the parent-death option and exec'd the command."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            comm = Path(f"/proc/{pid}/comm").read_text().strip()
        except FileNotFoundError:
            return
        if comm != "setpriv":
            return
        time.sleep(0.01)
    raise AssertionError("child never finished starting")


@pytest.mark.skipif(sys.platform not in ("linux", "win32"), reason="Linux and Windows only")
def test_child_dies_when_parent_is_sigkilled() -> None:
    parent = subprocess.Popen(
        [sys.executable, "-c", HELPER], stdout=subprocess.PIPE, text=True
    )
    child_pid: int | None = None
    try:
        assert parent.stdout is not None
        child_pid = int(parent.stdout.readline())
        assert _alive(child_pid)
        _wait_until_started(child_pid)

        parent.kill()  # SIGKILL: no cleanup code can run in the parent
        parent.wait()

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and _alive(child_pid):
            time.sleep(0.05)
        assert not _alive(child_pid), "child survived its parent being SIGKILLed"
    finally:
        if child_pid is not None and _alive(child_pid):
            os.kill(child_pid, getattr(signal, "SIGKILL", signal.SIGTERM))  # never leak
