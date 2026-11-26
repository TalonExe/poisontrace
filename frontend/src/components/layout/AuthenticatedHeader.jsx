import React from "react";
import { Link } from "@tanstack/react-router";
import { routes } from "../../utils/router";
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
  accountAction,
  className = "",
}) {
  const displayName = userDisplayName(user);
  const dashboard = user?.role === "analyst";
  const Brand = dashboard ? Link : "div";
  return (
    <header className={`authenticated-header ${className}`.trim()}>
      <div className="brand">
        {leadingAction}
        <Brand className="brand-content" {...(dashboard ? { to: routes.activity, "aria-label": "PoisonTrace dashboard" } : {})}>
          <span className="logo">P</span>
          <div>
            <strong>PoisonTrace</strong>
            <small>{subtitle}</small>
          </div>
        </Brand>
      </div>
      <div className="authenticated-user">
        <span className="avatar" aria-hidden="true">
          {userInitials(user)}
        </span>
        <div className="authenticated-user-copy">
          <strong>{displayName}</strong>
        </div>
        {accountAction}
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
