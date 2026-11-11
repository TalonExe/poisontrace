export function userDisplayName(user) {
  return user?.label || user?.username || "Analyst";
}

export function userInitials(user) {
  return userDisplayName(user)
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export async function signOutAndRedirect(auth, onSignedOut) {
  await auth.signOut();
  onSignedOut();
}
