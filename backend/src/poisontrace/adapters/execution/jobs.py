from contextlib import contextmanager
import ctypes
import multiprocessing
import os
from pathlib import Path
import signal
import sys
import threading


@contextmanager
def executor_lock(database):
    path = Path(str(Path(database).resolve())+'.executor.lock')
    with path.open('a+b') as handle:
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            if handle.seek(0, 2) == 0:
                handle.write(b'0')
                handle.flush()
            yield True
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def worker_main(config, stopping, ready, deadline_seconds):
    if os.name != 'nt':
        os.setsid()
        signal.signal(signal.SIGTERM, lambda *args: os.killpg(os.getpgrp(), signal.SIGKILL))
        if sys.platform.startswith('linux'):
            parent = os.getppid()
            if ctypes.CDLL(None).prctl(1, signal.SIGTERM) != 0 or os.getppid() != parent:
                os.killpg(os.getpgrp(), signal.SIGKILL)
    if not ready.wait(10):
        return
    with executor_lock(config.database) as acquired:
        if not acquired:
            return
        from poisontrace.bootstrap import build_backend, build_local_secrets
        secrets = build_local_secrets(config) if config.secrets_key else None
        backend = build_backend(config, secrets)
        backend.jobs.store.reconcile()
        while not stopping.is_set():
            try:
                claim = backend.jobs.store.claim()
                if claim is None:
                    stopping.wait(0.1)
                    continue
                try:
                    backend.jobs.execute_claim(claim, attempt_context=lambda: attempt_watchdog(deadline_seconds))
                except Exception:
                    backend.jobs.store.fail_claim(claim)
            except Exception:
                stopping.wait(0.25)


@contextmanager
def attempt_watchdog(seconds):
    timer = threading.Timer(seconds, hard_timeout)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


def hard_timeout():
    if os.name == 'nt':
        os._exit(74)
    os.killpg(os.getpgrp(), signal.SIGKILL)


class WindowsProcessTree:
    def __init__(self, pid):
        from ctypes import wintypes
        class BasicLimits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong), ('flags', wintypes.DWORD), ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t), ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('read_operations', 'write_operations', 'other_operations', 'read_bytes', 'write_bytes', 'other_bytes')]
        class ExtendedLimits(ctypes.Structure):
            _fields_ = [('basic', BasicLimits), ('io', IoCounters), ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel, self.handle = kernel, kernel.CreateJobObjectW(None, None)
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000
        process = kernel.OpenProcess(0x0100 | 0x0001, False, pid)
        try:
            if not self.handle or not process or not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(self.handle, process):
                self.close()
                raise RuntimeError('Executor process isolation unavailable')
        finally:
            if process:
                kernel.CloseHandle(process)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class JobExecutor:
    def __init__(self, config, *, deadline_seconds=45):
        self.config, self.deadline_seconds = config, deadline_seconds
        self.stopping = threading.Event()
        self.thread = None
        self.process = None

    def __enter__(self):
        self.thread = threading.Thread(target=self.supervise, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stopping.set()
        self.thread.join(12)
        if self.thread.is_alive():
            raise RuntimeError('Executor did not stop')

    def supervise(self):
        context = multiprocessing.get_context('spawn')
        while not self.stopping.is_set():
            stopping, ready = context.Event(), context.Event()
            process = context.Process(target=worker_main, args=(self.config, stopping, ready, self.deadline_seconds))
            process.start()
            self.process = process
            tree = None
            try:
                if os.name == 'nt':
                    tree = WindowsProcessTree(process.pid)
                ready.set()
                while process.is_alive() and not self.stopping.wait(0.1):
                    pass
                stopping.set()
                process.join(2)
            finally:
                if os.name == 'nt':
                    if tree:
                        tree.close()
                    elif process.is_alive():
                        process.kill()
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        if process.is_alive():
                            process.kill()
                process.join(5)
                process.close()
                self.process = None
            self.stopping.wait(0.5)
