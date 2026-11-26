import React, { useEffect, useRef, useState } from "react";
import { AuthenticatedHeader } from "../../components/layout/AuthenticatedHeader";
import "../../components/layout/layout.css";
import { ConfirmationAction } from "../../components/common/ConfirmationAction";
import { PendingButton } from "../../components/common/PendingButton";

const blank = { username: "", display_name: "", passcode: "" };

export function AdminUsers({ api, user, auth, onSignedOut }) {
  const [users, setUsers] = useState(null);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(blank);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  async function load() {
    try {
      setError("");
      setUsers(await api.listUsers(search));
    } catch (e) {
      setError(e.status === 403 ? "403 Forbidden" : e.message);
    }
  }
  useEffect(() => {
    load();
  }, [search]);
  function choose(user) {
    setNotice("");
    setError("");
    setSelected(user);
    setEditing(false);
    setForm({
      username: user.username,
      display_name: user.display_name,
      passcode: "",
    });
  }
  function startCreate() {
    setSelected(null);
    setEditing(true);
    setForm(blank);
    setNotice("");
  }
  async function submit(event) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      if (selected) {
        const updated = await api.updateUser(selected.id, {
          display_name: form.display_name,
        });
        setNotice("Display name saved.");
        setSelected(updated);
      } else {
        const created = await api.createUser(form);
        setNotice("Analyst account created.");
        setSelected(created);
        setForm({ ...created, passcode: "" });
      }
      setEditing(false);
      await load();
    } catch (failure) {
      setError(failure.status === 403 ? "403 Forbidden" : failure.message);
    } finally {
      setSaving(false);
    }
  }
  async function action(account, payload) {
    try {
      const updated = await api.updateUser(account.id, payload);
      setSelected(updated);
      setNotice("Account updated.");
      await load();
    } catch (failure) {
      if (failure.status === 403) setError("403 Forbidden");
      throw failure;
    }
  }
  const nextRole = selected?.role === "analyst" ? "superadmin" : "analyst";
  const nextStatus = selected?.status === "active" ? "disabled" : "active";
  const roleLabel =
    nextRole === "superadmin" ? "Promote to superadmin" : "Demote to analyst";
  const statusLabel =
    nextStatus === "disabled" ? "Disable account" : "Enable account";
  if (error === "403 Forbidden")
    return (
      <main className="login-shell">
        <section className="login-panel">
          <h1>403 Forbidden</h1>
          <p>Your account cannot access user management.</p>
        </section>
      </main>
    );
  return (
    <>
      <AuthenticatedHeader
        user={user}
        auth={auth}
        onSignedOut={onSignedOut}
        subtitle="Administration"
      />
      <main className="admin-shell">
        <header className="admin-heading">
          <div>
            <h1>User management</h1>
            <p>Manage local PoisonTrace accounts and role boundaries.</p>
          </div>
          <button
            className="run-button"
            type="button"
            disabled={saving}
            onClick={startCreate}
          >
            Create analyst
          </button>
        </header>
        {notice && (
          <p className="admin-notice" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="admin-workspace">
          <section className="admin-list-panel" aria-label="User directory">
            <div className="admin-list-toolbar">
              <h2>User directory</h2>
              <span>
                {users?.length ?? "…"} account{users?.length === 1 ? "" : "s"}
              </span>
            </div>
            <label className="admin-search">
              Search users
              <input
                aria-label="Search users"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Username or display name"
              />
            </label>
            {users === null ? (
              <p className="admin-state">Loading users…</p>
            ) : users.length === 0 ? (
              <p className="admin-state">No users match this search.</p>
            ) : (
              <div className="admin-user-list">
                {users.map((user) => (
                  <button
                    className={`admin-user-row ${selected?.id === user.id ? "is-selected" : ""}`}
                    key={user.id}
                    type="button"
                    disabled={saving}
                    onClick={() => choose(user)}
                  >
                    <span>
                      <strong>{user.display_name}</strong>
                      <small>{user.username}</small>
                    </span>
                    <span className={`admin-status ${user.status}`}>
                      {user.status}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </section>
          <section className="admin-detail-panel" aria-label="User details">
            {!editing && !selected ? (
              <div className="admin-state admin-detail-empty">
                <h2>Select an account</h2>
                <p>
                  Choose a user from the directory or create a new analyst
                  account.
                </p>
              </div>
            ) : (
              <form onSubmit={submit}>
                <div className="admin-detail-heading">
                  <div>
                    <h2>
                      {selected ? selected.display_name : "Create analyst"}
                    </h2>
                  </div>
                  {selected && (
                    <span className={`admin-role ${selected.role}`}>
                      {selected.role}
                    </span>
                  )}
                </div>
                <label>
                  Username
                  <input
                    value={form.username}
                    disabled={saving || Boolean(selected)}
                    required
                    onChange={(e) =>
                      setForm({ ...form, username: e.target.value })
                    }
                  />
                </label>
                <label>
                  Display name
                  <input
                    disabled={saving}
                    value={form.display_name}
                    required
                    onChange={(e) =>
                      setForm({ ...form, display_name: e.target.value })
                    }
                  />
                </label>
                {!selected && (
                  <label>
                    Initial passcode
                    <input
                      disabled={saving}
                      type="password"
                      value={form.passcode}
                      required
                      onChange={(e) =>
                        setForm({ ...form, passcode: e.target.value })
                      }
                    />
                  </label>
                )}
                <PendingButton
                  className="run-button"
                  type="submit"
                  pending={saving}
                >
                  {selected ? "Save display name" : "Create analyst"}
                </PendingButton>
                {saving && <p role="status">Saving account…</p>}
                {selected && (
                  <div className="admin-actions">
                    <ConfirmationAction
                      disabled={saving}
                      title={`${roleLabel}: ${selected.display_name}?`}
                      description={`Change the role for ${selected.username}. This ends their current sessions.`}
                      confirmLabel={roleLabel}
                      onConfirm={() => action(selected, { role: nextRole })}
                    >
                      {roleLabel}
                    </ConfirmationAction>
                    <ConfirmationAction
                      disabled={saving}
                      title={`${statusLabel}: ${selected.display_name}?`}
                      description={
                        nextStatus === "disabled"
                          ? `${selected.username} will be signed out and unable to sign in.`
                          : `${selected.username} will be able to sign in again.`
                      }
                      confirmLabel={statusLabel}
                      onConfirm={() => action(selected, { status: nextStatus })}
                    >
                      {statusLabel}
                    </ConfirmationAction>
                  </div>
                )}
              </form>
            )}
            {selected && (
              <PasscodeReset
                key={`${selected.id}:${selected.role}:${selected.status}`}
                account={selected}
                api={api}
                onReset={() =>
                  setNotice(
                    "Passcode reset. All sessions for this analyst were revoked.",
                  )
                }
              />
            )}
          </section>
        </div>
      </main>
    </>
  );
}

function PasscodeReset({ account, api, onReset }) {
  const [open, setOpen] = useState(false);
  const [passcode, setPasscode] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const trigger = useRef(null);
  function cancel() {
    setPasscode("");
    setConfirmation("");
    setError("");
    setOpen(false);
    requestAnimationFrame(() => trigger.current?.focus());
  }
  async function reset(event) {
    event.preventDefault();
    if (pending) return;
    if (passcode !== confirmation) {
      setError("Passcodes do not match.");
      return;
    }
    setError("");
    setPending(true);
    try {
      await api.resetPasscode(account.id, passcode);
      cancel();
      onReset();
    } catch (failure) {
      setPasscode("");
      setConfirmation("");
      setError(failure.message || "Passcode reset failed.");
    } finally {
      setPending(false);
    }
  }
  if (account.role !== "analyst")
    return <p>Superadmin recovery requires the restricted operator command.</p>;
  if (!open)
    return (
      <div className="admin-actions">
        <button ref={trigger} type="button" onClick={() => setOpen(true)}>
          Reset analyst passcode
        </button>
      </div>
    );
  return (
    <form aria-label="Reset analyst passcode" onSubmit={reset}>
      <h3>Reset passcode for {account.display_name}</h3>
      <p>
        This signs the analyst out of every session. Their saved work and
        provider credentials remain private.{" "}
        {account.status === "disabled"
          ? "This account will stay disabled."
          : "Share the new passcode through your approved private channel."}
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {pending && <p role="status">Resetting passcode…</p>}
      <label>
        New passcode
        <input
          type="password"
          autoComplete="new-password"
          maxLength={1024}
          required
          disabled={pending}
          value={passcode}
          onChange={(event) => setPasscode(event.target.value)}
        />
      </label>
      <label>
        Confirm new passcode
        <input
          type="password"
          autoComplete="new-password"
          maxLength={1024}
          required
          disabled={pending}
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
        />
      </label>
      <div className="admin-actions">
        <PendingButton type="submit" pending={pending}>
          Confirm passcode reset
        </PendingButton>
        <button type="button" disabled={pending} onClick={cancel}>
          Cancel reset
        </button>
      </div>
    </form>
  );
}
