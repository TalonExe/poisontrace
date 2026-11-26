from contextlib import closing
from hashlib import sha256
from pathlib import Path
import sqlite3
from uuid import uuid4

from cryptography.fernet import InvalidToken


class RecoveryLedger:
    def __init__(self, path, database, cipher, *, create=False):
        self.path = Path(path)
        self.database = Path(database)
        self.cipher = cipher
        if create:
            self.initialize()
        with self.connect() as ledger, closing(sqlite3.connect(self.database.as_uri() + "?mode=rw", uri=True)) as store:
            installation = store.execute("SELECT installation, verifier FROM recovery_identity").fetchone()
            identity = ledger.execute("SELECT installation FROM identity").fetchone()
            if installation is None or identity != installation[:1]:
                raise ValueError("recovery ledger does not belong to this installation")
            try:
                verified = cipher.decrypt(installation[1])
            except InvalidToken:
                raise ValueError("incorrect application encryption key") from None
            if verified != identity[0].encode():
                raise ValueError("invalid recovery identity")
            self.identity = identity[0]

    def connect(self):
        return closing(sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True))

    def initialize(self):
        with closing(sqlite3.connect(self.database)) as store, store:
            store.execute("BEGIN IMMEDIATE")
            store.execute("CREATE TABLE IF NOT EXISTS recovery_identity (installation TEXT NOT NULL, verifier BLOB NOT NULL)")
            if store.execute("SELECT 1 FROM recovery_identity").fetchone():
                return
            installation = uuid4().hex
            with self.path.open("xb"):
                pass
            with self.connect() as ledger, ledger:
                ledger.execute("CREATE TABLE identity (installation TEXT NOT NULL)")
                ledger.execute("INSERT INTO identity VALUES (?)", (installation,))
                ledger.execute("CREATE TABLE revoked (digest TEXT PRIMARY KEY)")
                ledger.execute("CREATE TABLE expired (kind TEXT NOT NULL, identifier TEXT NOT NULL, PRIMARY KEY(kind,identifier))")
                ledger.execute("CREATE TABLE scenario_deletions (revision INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL)")
            store.execute("INSERT INTO recovery_identity VALUES (?, ?)", (installation, self.cipher.encrypt(installation.encode())))

    def scenario_revision(self):
        with self.connect() as ledger:
            return ledger.execute("SELECT coalesce(max(revision),0) FROM scenario_deletions").fetchone()[0]

    def delete_scenario(self, filename):
        with self.connect() as ledger, ledger:
            ledger.execute("INSERT INTO scenario_deletions(filename) VALUES (?)", (filename,))

    def reconcile_scenarios(self, directory, revision):
        if revision > self.scenario_revision():
            raise ValueError("recovery ledger predates the archive")
        with self.connect() as ledger:
            filenames = ledger.execute("SELECT DISTINCT filename FROM scenario_deletions WHERE revision>?", (revision,)).fetchall()
        for (filename,) in filenames:
            if Path(filename).name != filename or not filename.endswith(".yaml"):
                raise ValueError("invalid scenario deletion entry")
            (directory / filename).unlink(missing_ok=True)

    def revoke(self, ciphertext):
        with self.connect() as ledger, ledger:
            ledger.execute("INSERT OR IGNORE INTO revoked VALUES (?)", (sha256(ciphertext).hexdigest(),))

    def revoked(self):
        with self.connect() as ledger:
            return {row[0] for row in ledger.execute("SELECT digest FROM revoked")}

    def reconcile_credentials(self):
        revoked = self.revoked()
        with closing(sqlite3.connect(self.database)) as store, store:
            store.execute("BEGIN IMMEDIATE")
            store.executemany("DELETE FROM credentials WHERE credential_id=?", (
                (identifier,) for identifier, token in store.execute("SELECT credential_id, encrypted_secret FROM credentials").fetchall()
                if sha256(token).hexdigest() in revoked
            ))
            try:
                for (token,) in store.execute("SELECT encrypted_secret FROM credentials"):
                    self.cipher.decrypt(token)
            except InvalidToken:
                raise ValueError("incorrect application encryption key or unreadable credential") from None
