"""Process helpers shared by the lifecycle tests (Linux and Windows)."""
from __future__ import annotations

import os
import sys


def alive(pid: int) -> bool:
    """True if a process with this PID is running.

    On POSIX os.kill(pid, 0) is only an existence check; on Windows it would
    terminate the process, so Windows asks the OS for the exit code instead.
    """
    if sys.platform == "win32":
        return _alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _alive_windows(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    query_limited = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
    still_active = 259
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetExitCodeProcess.restype = wintypes.BOOL
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = k32.OpenProcess(query_limited, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == still_active
    finally:
        k32.CloseHandle(handle)
