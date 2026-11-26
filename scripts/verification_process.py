import ctypes
import os
import signal
import socket
import subprocess
import sys


class WindowsTree:
    def __init__(self, pid):
        from ctypes import wintypes

        class Limits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('minimum', ctypes.c_size_t),
                        ('maximum', ctypes.c_size_t), ('active', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                        ('scheduling', wintypes.DWORD)]

        class Io(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ('reads', 'writes', 'others', 'read_bytes', 'write_bytes', 'other_bytes')]

        class Extended(ctypes.Structure):
            _fields_ = [('basic', Limits), ('io', Io), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t),
                        ('peak_job', ctypes.c_size_t)]

        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000
        process = self.kernel.OpenProcess(0x0100 | 0x0001, False, pid)
        try:
            if not self.handle or not process or not self.kernel.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ) or not self.kernel.AssignProcessToJobObject(self.handle, process):
                self.close()
                raise RuntimeError('Owned process isolation unavailable')
        finally:
            if process:
                self.kernel.CloseHandle(process)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class OwnedProcess:
    def __init__(self, command, *, cwd, env, log):
        self.tree = None
        gate = 'import subprocess,sys; token=sys.stdin.buffer.read(1); sys.exit(subprocess.call(sys.argv[1:]) if token==b"1" else 125)'
        self.process = subprocess.Popen(
            [sys.executable, '-c', gate, *map(str, command)], cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
            start_new_session=os.name != 'nt',
        )
        try:
            if os.name == 'nt':
                self.tree = WindowsTree(self.process.pid)
            self.process.stdin.write(b'1')
            self.process.stdin.close()
        except BaseException:
            self.close()
            raise

    def owns_port(self, port):
        if os.name != 'nt':
            raise RuntimeError('Listener ownership doctor currently requires Windows')
        from ctypes import wintypes
        helper = ctypes.WinDLL('iphlpapi', use_last_error=True)
        size = wintypes.DWORD(0)
        helper.GetExtendedTcpTable(None, ctypes.byref(size), False, socket.AF_INET, 3, 0)
        buffer = ctypes.create_string_buffer(size.value)
        if helper.GetExtendedTcpTable(buffer, ctypes.byref(size), False, socket.AF_INET, 3, 0):
            raise RuntimeError('Cannot read listener ownership')
        count = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD))[0]
        rows = ctypes.cast(ctypes.byref(buffer, ctypes.sizeof(wintypes.DWORD)), ctypes.POINTER(wintypes.DWORD))
        kernel = self.tree.kernel
        kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
        for index in range(count):
            offset = index * 6
            if socket.ntohs(rows[offset + 2] & 0xFFFF) != port:
                continue
            handle = kernel.OpenProcess(0x1000, False, rows[offset + 5])
            member = wintypes.BOOL()
            try:
                if handle and kernel.IsProcessInJob(handle, self.tree.handle, ctypes.byref(member)) and member.value:
                    return True
            finally:
                if handle:
                    kernel.CloseHandle(handle)
        return False

    def close(self):
        if self.tree:
            self.tree.close()
        elif os.name != 'nt':
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=10)
