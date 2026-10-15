"""Own a Windows process tree before its suspended primary thread can run.

Only documented kernel32 APIs are used. The caller must create the process with
CREATE_SUSPENDED, assign it to the job, then resume it. No breakaway is allowed.
"""

import ctypes
from ctypes import wintypes
import os
import time


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IOCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ThreadEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


class _Accounting(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


if os.name == "nt":
    _api = ctypes.WinDLL("kernel32", use_last_error=True)
    _api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _api.CreateJobObjectW.restype = wintypes.HANDLE
    _api.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    _api.SetInformationJobObject.restype = wintypes.BOOL
    _api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _api.AssignProcessToJobObject.restype = wintypes.BOOL
    _api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _api.TerminateJobObject.restype = wintypes.BOOL
    _api.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _api.QueryInformationJobObject.restype = wintypes.BOOL
    _api.CloseHandle.argtypes = [wintypes.HANDLE]
    _api.CloseHandle.restype = wintypes.BOOL
    _api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _api.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
    _api.Thread32First.restype = wintypes.BOOL
    _api.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
    _api.Thread32Next.restype = wintypes.BOOL
    _api.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _api.OpenThread.restype = wintypes.HANDLE
    _api.ResumeThread.argtypes = [wintypes.HANDLE]
    _api.ResumeThread.restype = wintypes.DWORD


def _failure(operation):
    code = ctypes.get_last_error()
    return ctypes.WinError(code, "%s failed: %s" % (operation, ctypes.FormatError(code).strip()))


def _close(handle):
    if not _api.CloseHandle(handle):
        raise _failure("CloseHandle")


class WindowsJob:
    """A noninheritable, unnamed job that kills its processes when closed."""

    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows process jobs are available only on Windows")
        self._handle = _api.CreateJobObjectW(None, None)
        if not self._handle:
            raise _failure("CreateJobObjectW")
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not _api.SetInformationJobObject(
            self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits),
        ):
            error = _failure("SetInformationJobObject")
            _api.CloseHandle(self._handle)
            self._handle = None
            raise error

    def assign(self, process_handle):
        """Assign a process that has not yet resumed from CREATE_SUSPENDED."""
        if not self._handle:
            raise OSError("Windows job is closed")
        if not _api.AssignProcessToJobObject(self._handle, int(process_handle)):
            raise _failure("AssignProcessToJobObject")

    def resume(self, pid):
        """Find and resume the new process's suspended primary thread."""
        if not self._handle:
            raise OSError("Windows job is closed")
        snapshot = _api.CreateToolhelp32Snapshot(0x00000004, 0)  # SNAPTHREAD
        if snapshot == ctypes.c_void_p(-1).value:
            raise _failure("CreateToolhelp32Snapshot")
        try:
            entry = _ThreadEntry()
            entry.dwSize = ctypes.sizeof(entry)
            found = _api.Thread32First(snapshot, ctypes.byref(entry))
            while found:
                if entry.th32OwnerProcessID == pid:
                    thread = _api.OpenThread(0x0002, False, entry.th32ThreadID)
                    if not thread:
                        raise _failure("OpenThread")
                    try:
                        previous = _api.ResumeThread(thread)
                        if previous == 0xFFFFFFFF:
                            raise _failure("ResumeThread")
                        if previous == 1:
                            return
                        if previous > 1:
                            raise OSError("Process primary thread remains suspended")
                    finally:
                        _close(thread)
                # Thread32First may change dwSize; reset it before each call.
                entry.dwSize = ctypes.sizeof(entry)
                found = _api.Thread32Next(snapshot, ctypes.byref(entry))
            error = ctypes.get_last_error()
            if error not in (0, 18):  # ERROR_NO_MORE_FILES
                raise _failure("Thread32First/Thread32Next")
            raise OSError("Cannot find the suspended process primary thread")
        finally:
            _close(snapshot)

    def terminate(self):
        if not self._handle:
            return
        if not _api.TerminateJobObject(self._handle, 1):
            raise _failure("TerminateJobObject")
        # Termination is asynchronous. Wait for descendants too, before their
        # working directories or output handles are removed by the caller.
        deadline = time.monotonic() + 5
        while True:
            accounting = _Accounting()
            if not _api.QueryInformationJobObject(
                self._handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None,
            ):
                raise _failure("QueryInformationJobObject")
            if not accounting.ActiveProcesses:
                return
            if time.monotonic() >= deadline:
                raise OSError("Windows job processes did not finish terminating within 5 seconds")
            time.sleep(0.01)

    def close(self):
        """Close once; closing also terminates any remaining descendants."""
        if self._handle:
            handle = self._handle
            _close(handle)
            self._handle = None
