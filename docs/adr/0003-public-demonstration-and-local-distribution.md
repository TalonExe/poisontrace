# Public demonstration and local distribution

Status: accepted, 2026-11-03. Deployment requirements are accepted; implementation is pending.

PoisonTrace will support a publicly hosted demonstration with live model execution using each analyst's own provider API key, alongside an open-source local edition. The first hosted release uses operator-issued accounts, private analyst credentials and experiment history, and a curated read-only scenario library. This avoids adding public registration and prevents visitors from modifying each other's benchmark inputs. The local edition retains scenario creation, repair and deletion under ADR 0001.

Provider keys remain encrypted until their owner revokes them. The backend must decrypt a key to call its provider. Owner checks must apply to credential listing, lookup, replacement, testing, revocation and use, and to runs, campaigns and child traces. Role permission alone is insufficient. Backup retention and eventual deletion from backups require an explicit operating policy before launch.

ADR 0002's analyst/superadmin restrictions remain unchanged. Its deferral of finite session expiry describes the local prototype baseline; public release requires revisiting that deferral and verifying bounded sessions before launch. This decision does not implement expiry, grant superadmins analyst access, or select a hosting provider. The current shared research storage must not be described as private multi-user storage.
