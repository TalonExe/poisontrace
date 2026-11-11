# ADR 0002: Backend-managed users and role boundaries

## Status

Accepted

## Context

PoisonTrace currently uses a frontend-local demo identity. The product needs a small administrator surface for managing users without allowing role checks to be bypassed by changing browser state. The initial administrative need is user management, while the primary investigation workflow remains an analyst-only workspace.

## Decision

User identity, authentication, account status, and role authorization are backend-managed. The initial roles are `analyst` and `superadmin`. Analysts may use the investigation workspace. Superadmins may use `/admin/users` and may not use analyst routes such as `/sessions`, `/dashboard`, or `/scenarios` in the initial release. Analysts may not use admin routes. Unauthorized authenticated requests return a forbidden result; unauthenticated requests return to login.

The application seeds two clearly labelled development demo accounts, one analyst and one superadmin. Their passcodes are supplied through environment configuration and are stored only as one-way password hashes. Demo labels are presentation metadata, not part of the identity.

Usernames are unique, normalized, and immutable. User records contain an identifier, username, display name, role, account status, creation timestamp, and last-login timestamp. New users are always created as active analysts. A user can become a superadmin only through an explicit promotion action from analyst, and a superadmin can be demoted through an explicit action. The backend prevents disabling or demoting the last active superadmin.

The first admin surface is `/admin/users`, with `/admin` redirecting there for superadmins. It provides a searchable user table and a master/detail create/edit workspace. Superadmins can create users, edit display names, promote or demote users, and enable or disable accounts. User deletion, passcode reset, persistent audit history, and finite session expiry are deferred. Account status is re-checked on protected requests so disabling a user invalidates active access promptly.

## Consequences

The frontend can present role-appropriate navigation, but the backend remains authoritative. The authentication seam must support role-aware login destinations: analysts go to `/sessions`, and superadmins go to `/admin/users`. The system must provide a clear forbidden state rather than silently redirecting an authenticated user across role boundaries. Future administrative features can extend the admin namespace without granting superadmins analyst capabilities by default.
