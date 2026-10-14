"""Lifecycle supervisor for the local Ollama process.

Deliberately has no GUI imports so it can be tested headless.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)


def _with_parent_death_signal(command: list[str]) -> list[str]:
    """Ask the Linux kernel to SIGTERM the child if this process dies.

    Covers SIGKILL of the parent, which no Python cleanup code can catch.
    """
    if not sys.platform.startswith("linux"):
        return command
    if shutil.which("setpriv") is None:
        logger.warning("setpriv not found; child may outlive a SIGKILLed parent")
        return command
    return ["setpriv", "--pdeathsig", "SIGTERM", *command]


class OllamaSupervisor:
    """Starts Ollama only if needed, and stops only the process it started."""

    def __init__(
        self,
        command: Sequence[str],
        is_healthy: Callable[[], bool],
        stop_timeout: float = 5.0,
        die_with_parent: bool = True,
        max_restarts: int = 3,
        extra_env: dict[str, str] | None = None,
    ) -> None:
        self._command: list[str] = list(command)
        self._is_healthy = is_healthy
        self._stop_timeout = stop_timeout
        self._die_with_parent = die_with_parent
        self._max_restarts = max_restarts
        self._extra_env: dict[str, str] = {
            "OLLAMA_FLASH_ATTENTION": "1",
            "OLLAMA_KV_CACHE_TYPE": "q8_0",
            "OLLAMA_NUM_PARALLEL": "1",
            "OLLAMA_IGPU_ENABLE": "1",
            "OLLAMA_ORIGINS": "*",
        }
        if extra_env:
            self._extra_env.update(extra_env)
        self._restarts = 0
        self._job: int | None = None  # Windows Job Object handle
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def pid(self) -> int | None:
        """PID of the child we started, or None."""
        return self._process.pid if self._process is not None else None

    @property
    def owns_process(self) -> bool:
        """True while a child we started is still running."""
        return self._process is not None and self._process.poll() is None

    def start(self) -> bool:
        """Spawn the child if none of ours is running and Ollama is not healthy.

        Returns True only if a new process was spawned.
        """
        if self.owns_process:
            return False
        if self._is_healthy():
            return False
        # Fixed argument list, no shell. The child stays in our session on
        # purpose, so it is not detached from the app's lifetime.
        command = (
            _with_parent_death_signal(self._command)
            if self._die_with_parent
            else self._command
        )
        import os
        child_env = os.environ.copy()
        for k, v in self._extra_env.items():
            child_env.setdefault(k, v)
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=child_env,
        )
        if self._die_with_parent and sys.platform == "win32":
            self._attach_to_job(self._process)
        return True

    def _attach_to_job(self, process: subprocess.Popen[bytes]) -> None:
        """Windows: tie the child to a kill-on-close Job Object (best effort)."""
        try:
            import win_job

            if self._job is None:
                self._job = win_job.create_kill_on_close_job()
            win_job.assign_pid(self._job, process.pid)
        except OSError as exc:
            logger.warning("could not attach child to a Job Object: %s", exc)

    def _close_job(self) -> None:
        if self._job is None:
            return
        job, self._job = self._job, None
        try:
            import win_job

            win_job.close_job(job)
        except OSError as exc:
            logger.warning("could not close Job Object: %s", exc)

    def check(self) -> bool:
        """Restart the child if it exited on its own. Returns True if restarted.

        Call periodically from the main thread. Does nothing after stop() and
        gives up after max_restarts so a broken Ollama is not respawned forever.
        """
        process = self._process
        if process is None or process.poll() is None:
            return False
        self._process = None  # poll() already reaped the dead child
        if self._restarts >= self._max_restarts:
            logger.error("ollama exited again; giving up after %d restarts", self._restarts)
            return False
        if self.start():
            self._restarts += 1
            logger.warning("ollama exited unexpectedly; restarted (%d)", self._restarts)
            return True
        return False

    def stop(self) -> None:
        """Terminate the child we started (if any) and reap it."""
        process = self._process
        if process is None:
            self._close_job()
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self._stop_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        self._process = None
        self._close_job()
