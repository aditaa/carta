# Admin, Settings, and Status

Carta Arcanum keeps administrative work inside the app so production servers can
stay simple: code lives in Git, local runtime configuration lives in environment
files or editable application settings, and user or ownership state lives in the
database.

## Access Model

- Superusers can see the full settings area, application status, audit log,
  all users, all house memberships, and all kingdom memberships.
- House admins can see house administration links for each house where they
  have an active admin membership. They can manage users in those houses,
  invite existing users into those houses, remove users from those houses, and
  re-enable disabled users in those houses.
- Kingdom admins have the same scoped workflow for kingdoms.
- A user can be both a house admin and a kingdom admin. The navigation keeps
  those areas separate because house and kingdom administration are different
  workflows.
- Standard users see only the account-level links they need, including in-app
  invitations and password management.

ACL visibility and edit rights are intentionally separate. Read-only house or
kingdom members can see shared records in their scope, but edit/delete actions
are limited to editable memberships, the user's own records, or superusers.
This distinction is enforced in the backend for buildings and holdings, and the
UI hides action controls for read-only records.

Users are never hard-deleted from the admin screens. Disabling a user marks the
account inactive and preserves audit history, memberships, holdings, and other
references. A scoped admin or superuser can re-enable a disabled user when that
user is still inside their management scope.

## User Management

Open `Settings -> User Access` as a superuser, or use the house or kingdom admin
navigation as a scoped admin.

User management supports:

- creating users;
- filtering and paging large user lists;
- editing display names and denizen profile status;
- applying role presets;
- fine-grained Django permission selection for superusers;
- assigning house and kingdom ACL memberships;
- disabling and re-enabling users;
- changing managed user passwords;
- preserving all historical rows instead of deleting users.

Only superusers can grant platform-level flags, groups, or Django permissions.
House and kingdom admins can manage only memberships within organizations where
they are active admins.

## Invitations

Invitations are entirely in-app. They are not sent by email.

Admins invite an existing active user to a house or kingdom. The invite appears
on that user's `Invitations` page after sign-in. The user can accept or decline
the invite. The inviting admin can cancel a pending invite while it remains in
their management scope.

Carta prevents duplicate pending invites and prevents a user from accepting a
second active house or a second active kingdom membership. Users can belong to
one house and one kingdom at a time.

## Password Management

Every authenticated user can change their own password from `Password`.

Scoped admins can reset passwords for users they manage. Superusers can reset
any user's password. The public self-service password reset views are available
for deployments that configure email sending.

## Application Status

Open `Settings -> Application Status` as a superuser. The status page shows
green checks when a subsystem is healthy and red checks with detail when
attention is needed.

The page includes checks for:

- Django runtime configuration;
- database access;
- installer lock state;
- current rules file;
- email backend configuration;
- restart-needed state;
- slow-query monitor status;
- Git checkout status;
- changed tracked files.

Git is treated as the source of truth for application code. If tracked files
differ from Git, the status page shows the changed paths and provides restore
actions for a single file or all changed tracked files.

## Editable Settings

Editable application settings include the displayed site name, maintenance
notice, restart command, restart-needed flag, and email configuration. These
settings live in the database so ordinary upgrades do not overwrite them.

Email can be configured for a local console backend, SMTP relay, provider SMTP
service, or another Django email backend. Use the email test button on the
status page after changing email settings.

## Upgrades

The production install defaults to the `stable` release branch. Test installs
can change the release branch setting to `main`, which is the development
branch, from `Settings -> Application Status`. The upgrade button appears only
for superusers and only when an upgrade is available on the configured branch.

An upgrade resets tracked code files back to Git, fetches remotes, switches to
the configured release branch, fast-forwards from origin, installs dependencies,
runs migrations, collects static files, and runs the configured restart command
when present.

Pull requests targeting `stable` are guarded by the Stable Release Gate workflow.
Stable release PRs must be ready for review and must come from `main`,
`release/*`, or `hotfix/*`. Make that gate a required branch protection check on
GitHub before relying on it as an enforcement mechanism.

Before upgrading a live install, keep a normal database and environment backup.
The upgrade workflow does not remove `.env`, `.env.local`, `installer.lock`, or
database data.

## Audit Log

The audit log records administrative and security-sensitive actions such as
settings changes, user creation, disabling or enabling users, password resets,
membership changes, invitation changes, Git restore actions, and upgrades.
Audit detail pages are superuser-only.

## Query Monitoring

Set `CARTA_SLOW_QUERY_MS` to log database queries that exceed that threshold
during web requests. For example, `CARTA_SLOW_QUERY_MS=250` logs queries slower
than 250 ms to the `carta.slow_queries` logger. Leave it unset or set it to `0`
to disable slow-query logging.

This is meant to catch heavy queries that only appear after real player usage
creates larger datasets. Treat slow-query logs as leads for future service-level
profiling, indexes, pagination, or query shape changes.
