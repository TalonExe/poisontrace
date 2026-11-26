// Browser preferences are partitioned for usability. The server authorizes data.
// Unscoped local-edition data stays intact and is never assigned to a login.
let account = null;

export function setWorkspaceAccount(user) {
  account = user ? `${user.role}:${user.id ?? user.username}` : null;
}

export function workspaceStorage(storage) {
  const prefix = account ? `poisontrace.account.${account}.` : '';
  return {
    getItem: key => storage.getItem(`${prefix}${key}`),
    setItem: (key, value) => storage.setItem(`${prefix}${key}`, value),
  };
}
