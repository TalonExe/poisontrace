from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build_identity(root):
    base = root / 'frontend/dist'
    if not (base/'index.html').is_file():
        raise RuntimeError('Intended frontend build is missing')
    files = {}
    for path in sorted(base.rglob('*')):
        if path.is_symlink():
            raise ValueError('Build outputs must not be symbolic links')
        if path.is_file():
            files[path.relative_to(base).as_posix()] = digest(path.read_bytes())
    return dict(files=files, sha256=digest(json.dumps(files, sort_keys=True).encode()))


@contextmanager
def exclusive_file(path):
    if os.name == 'nt':
        from ctypes import wintypes
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        handle = kernel.CreateFileW(str(path), 0xC0000000, 0, None, 3, 0, None)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError(ctypes.get_last_error(), 'Exclusive debug-log access unavailable')
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
        with os.fdopen(descriptor, 'r+b') as stream:
            yield stream
    else:
        import fcntl
        with path.open('r+b') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield stream


class DebugLogs:
    def __init__(self, root, artifact):
        self.root, self.artifact = root, artifact
        self.entries = {}
        for name in ('debug.log', 'frontend/debug.log'):
            path = root / name
            if path.is_symlink():
                raise ValueError('Debug logs must not be symbolic links')
            entry = path.read_bytes() if path.exists() else b''
            self.entries[name] = (path.exists(), entry)
            (artifact / ('entry-' + name.replace('/', '-'))).write_bytes(entry)

    def restore(self):
        records = {}
        for name, (existed, entry) in self.entries.items():
            path = self.root / name
            record = dict(entry_sha256=digest(entry), entry_bytes=len(entry), restored=False)
            records[name] = record
            try:
                if not path.exists():
                    record['restored'] = not existed
                    continue
                if path.is_symlink():
                    raise ValueError('Debug log became a symbolic link')
                with exclusive_file(path) as stream:
                    current = stream.read()
                    record.update(observed_sha256=digest(current), observed_bytes=len(current))
                    if current != entry:
                        archive = self.artifact / ('complete-' + name.replace('/', '-') + '-' + uuid4().hex + '.log')
                        with archive.open('xb') as target:
                            target.write(current)
                            target.flush()
                            os.fsync(target.fileno())
                        record['archive'] = str(archive)
                        if not current.startswith(entry):
                            raise ValueError('Debug-log entry prefix changed; current file and archive preserved')
                        stream.seek(0)
                        stream.truncate(len(entry))
                        stream.flush()
                        os.fsync(stream.fileno())
                    record['restored'] = True
            except Exception as error:
                record['error'] = str(error)
        return records


@contextmanager
def run_lock(root):
    path = root / '.scratch/verification.lock'
    path.parent.mkdir(exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('Another verification run owns this checkout') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + root.as_posix(), *args], cwd=root)


def source_identity(root):
    paths = []
    for directory in ('backend/src', 'backend/tests', 'backend/scenarios', 'scripts', 'frontend/src', 'frontend/e2e', 'frontend/public'):
        base = root / directory
        if base.exists():
            paths.extend(p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                         and p.suffix not in ('.pyc', '.pyo', '.log', '.db') and not p.name.startswith('.env'))
    for directory in (root, root/'frontend'):
        if directory.exists():
            paths.extend(p for p in directory.iterdir() if p.is_file() and
                         (p.suffix in ('.toml', '.yaml', '.js', '.mjs', '.json', '.html') or p.name in
                          ('requirements-runtime.lock', 'Dockerfile', '.dockerignore', '.gitignore', 'AGENTS.md', 'CONTAINER.md')))
    files = {}
    for path in sorted(set(paths)):
        if path.is_symlink():
            raise ValueError('Verification input must not be a symbolic link: ' + str(path))
        files[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    identity = dict(files=files, sha256=digest(json.dumps(files, sort_keys=True).encode()))
    if (root / '.git').exists():
        identity.update(head=git(root, 'rev-parse', 'HEAD').decode().strip(),
                        branch=git(root, 'branch', '--show-current').decode().strip(),
                        status=git(root, 'status', '--porcelain=v1', '-uall').decode())
    return identity
