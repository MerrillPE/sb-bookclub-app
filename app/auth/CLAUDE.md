# Auth blueprint

**Invite-only self-registration**, not manual seeding. An `Invite` row is created either by `flask create-invite` or by `/admin/invites`; both go through `Invite.create(expires_at=None)` so the creation logic lives in one place. `/auth/register/<token>` checks that the invite exists, is unused and is not expired (`Invite.is_expired`), then lets the visitor create their own `Member` and logs them in.

- **Invite tokens** are 3-word hyphenated passphrases from `app/invite_words.py` (e.g. `cedar-forest-delta`, via `_generate_invite_token()` in `app/models.py`). They're meant to be hand-typed or read aloud, which is why they aren't opaque `secrets.token_urlsafe` strings. `PasswordReset.token` *is* `secrets.token_urlsafe(32)`, because resets are shared as a clickable link.
- **username vs display_name**: `username` is unique and is the login identifier. `display_name` defaults to the username at registration, can be changed from the member's profile, and is deliberately **not** unique (the GitHub/Slack split; the `@username` shown beside it tells two same-named members apart). Migration `b5df0559156b` dropped the old unique constraint on `display_name`, which also prevents a registration crash when a new username matches someone's renamed display name.
- **Login page**: `/auth/login` redirects to `home` if already authenticated. It has two inline "Have a token?" panels (invite / password reset) that redirect client-side (`app/static/js/auth.js`) to `/auth/register/<token>` or `/auth/reset-password/<token>`. The routes' own validation handles bad tokens, so there's no token-lookup endpoint.

**Password reset** (`/auth/reset-password/<token>`, model `PasswordReset`): resets are generated only by admins (`/admin/members`). There's no self-service "forgot password" flow because there's no email integration to build it on. Expiry is fixed at 24 hours (`PasswordReset.create(member)`), unlike an invite's optional, admin-chosen expiry. Validation has the same not-found / used / expired shape as `register()`. Completing a reset updates the existing member's password and logs them in, mirroring `register()`.

Auth pages share `templates/auth/_layout.html`.
