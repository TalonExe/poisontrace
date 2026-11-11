export const SESSION_STORAGE_KEY = "poisontrace.synthetic.sessions";
export const defaultSession = {
  id: "session-1",
  name: "Authentication alert study",
  model: "gemini",
  credentialId: "",
  scenario: "Authentication alert",
  updated: "just now",
};

export function loadSessions(storage) {
  try {
    return JSON.parse(storage.getItem(SESSION_STORAGE_KEY)) || [defaultSession];
  } catch {
    return [defaultSession];
  }
}

export function createSession(now = Date.now()) {
  return {
    id: `session-${now}`,
    name: "New investigation session",
    model: "gemini",
    credentialId: "",
    scenario: "Authentication alert",
    updated: "just now",
  };
}

export function saveSession(sessions, draft) {
  if (!draft.name.trim()) return sessions;
  return sessions.map((session) =>
    session.id === draft.id
      ? { ...draft, name: draft.name.trim(), updated: "just now" }
      : session,
  );
}

export function deleteSession(sessions, id) {
  const remaining = sessions.filter((session) => session.id !== id);
  return remaining.length ? remaining : [defaultSession];
}
