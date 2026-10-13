# Admin blueprint

Every route is gated by the local `admin_required` decorator, stacked under `@login_required` (non-admins get 403). Pages share `templates/admin/_layout.html` (header + Members/Invites tabs).

- **`/admin/invites`** lists every invite with its computed `Invite.status_label` (Pending/Used/Expired, pending first). An admin can generate an invite, optionally with an expiry date, or revoke an unused one. `CreateInviteForm.validate_expires_at` requires the date to be today or later in UTC; the invite stays valid through the end of that day. The view also sets the date picker's `min` attribute on each request (not a static `render_kw`, since "today" changes), but that only greys out past days in the browser; the validator is the real check. Revoking is a hard delete; there's no `revoked_at` column.
- **`/admin/members`** lists every member and can generate a password-reset link for one. Generating a new link first deletes that member's other unused `PasswordReset` rows, so at most one is ever valid per member.
- Both pages show the token and the full URL side by side with "Copy" buttons (`data-copy-value`, wired in `app/static/js/admin.js`), since either form is useful to hand to someone.
- Action buttons (revoke, generate reset) use fieldless CSRF forms (`RevokeInviteForm`, `GenerateResetForm`); see `.claude/rules/forms-and-csrf.md`.
