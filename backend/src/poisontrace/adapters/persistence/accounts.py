"""SQLite account records; shared setup and transaction semantics match existing storage."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from poisontrace.application.accounts import AuthUser
from poisontrace.adapters.persistence.support import initialize_database


_USER_COLUMNS = "id, username, display_name, role, status, created_at, last_login_at"


class SqliteAccountStore:
    def __init__(self, database: Path) -> None:
        self.database = database
        initialize_database(database)

    @contextmanager
    def transaction(self):
        with sqlite3.connect(self.database) as connection:
            yield _SqliteAccountRecords(connection)


class _SqliteAccountRecords:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def find_credentials(self, username: str) -> tuple[AuthUser, str] | None:
        row = self._db.execute(f"SELECT {_USER_COLUMNS}, passcode_hash FROM users WHERE username = ?", (username,)).fetchone()
        return (AuthUser(*row[:7]), row[7]) if row else None

    def get(self, user_id: int) -> AuthUser | None:
        row = self._db.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?", (user_id,)).fetchone()
        return AuthUser(*row) if row else None

    def create(self, username: str, display_name: str, role: str, passcode_hash: str, *, ignore_existing: bool = False) -> AuthUser:
        insertion = "INSERT OR IGNORE" if ignore_existing else "INSERT"
        try:
            self._db.execute(f"{insertion} INTO users (username, display_name, role, status, passcode_hash) VALUES (?, ?, ?, 'active', ?)",
                             (username, display_name, role, passcode_hash))
        except sqlite3.IntegrityError as exc:
            raise ValueError("username already exists") from exc
        row = self._db.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE username = ?", (username,)).fetchone()
        return AuthUser(*row)

    def touch_login(self, user_id: int) -> None:
        self._db.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))

    def add_session(self, token_hash: str, user_id: int) -> None:
        self._db.execute("INSERT INTO auth_sessions (token_hash, user_id) VALUES (?, ?)", (token_hash, user_id))

    def session_user(self, token_hash: str) -> AuthUser | None:
        row = self._db.execute("SELECT u.id, u.username, u.display_name, u.role, u.status, u.created_at, u.last_login_at FROM users u JOIN auth_sessions s ON s.user_id = u.id WHERE s.token_hash = ?", (token_hash,)).fetchone()
        return AuthUser(*row) if row else None

    def delete_session(self, token_hash: str) -> None:
        self._db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))

    def list_users(self, username_pattern: str, display_name_pattern: str) -> list[AuthUser]:
        rows = self._db.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE username LIKE ? OR display_name LIKE ? ORDER BY username", (username_pattern, display_name_pattern)).fetchall()
        return [AuthUser(*row) for row in rows]

    def active_superadmin_count(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM users WHERE role = 'superadmin' AND status = 'active'").fetchone()[0]

    def update(self, user_id: int, display_name: str, role: str, status: str) -> AuthUser:
        self._db.execute("UPDATE users SET display_name = ?, role = ?, status = ? WHERE id = ?", (display_name, role, status, user_id))
        row = self._db.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?", (user_id,)).fetchone()
        return AuthUser(*row)
