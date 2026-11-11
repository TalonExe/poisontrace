import React from "react";
import {
  signOutAndRedirect,
  userDisplayName,
  userInitials,
} from "../../utils/userArea";

export function AuthenticatedHeader({
  user,
  auth,
  onSignedOut,
  subtitle,
  leadingAction,
  className = "",
}) {
  const displayName = userDisplayName(user);
  return (
    <header className={`authenticated-header ${className}`.trim()}>
      <div className="brand">
        {leadingAction}
        <span className="logo">P</span>
        <div>
          <strong>PoisonTrace</strong>
          <small>{subtitle}</small>
        </div>
      </div>
      <div className="authenticated-user">
        <span className="avatar" aria-hidden="true">
          {userInitials(user)}
        </span>
        <div className="authenticated-user-copy">
          <strong>{displayName}</strong>
        </div>
        <button
          className="text-button sign-out-button"
          onClick={() => signOutAndRedirect(auth, onSignedOut)}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
