# Book Club Tracker — Project Plan

## Overview
A web app for a 4-person book club to track books read, log individual ratings/comments, and browse reading history. Each member has their own login. Data is stored online/shared across devices.

---

## 1. Requirements

### Functional Requirements

**Auth**
- 4 member accounts, created via invite-only self-registration (not open signup, not manually seeded by an admin directly)
- Login/logout with sessions
- Passwords hashed — never stored in plaintext

**Books**
- Add a book: title, author, cover image (manual URL or auto-fetched), date added, who added it
- Edit/delete a book
- Status: to-read / currently reading / finished / abandoned
- Optional: "picked by" (whose turn/choice this book was)

**Ratings**
- Each member can rate a finished book (pick a scale — see decisions below) + optional written comment
- A member can edit only *their own* rating (no delete — see decisions below)
- Book detail view shows all 4 members' ratings side by side + average

**Views**
- Book list: sortable/filterable by status, average rating, date
- Book detail: full info + all ratings/comments
- Optional: member profile/stats page — including letting a member change their own `display_name` later (it defaults to their `username` at registration time, not collected as a separate field on the registration form)

### Non-Functional Requirements
- Mobile-friendly (people will rate books from their phones)
- Fast page loads (small data scale, so this should be easy)
- Data durability — don't lose reading history
- Low/no cost to run at this scale

### Decisions to Make Before Coding
1. ~~Can anyone edit any book's metadata, or only the person who added it?~~ **Decided: the member who picked it (`Book.picked_by`) or an admin (`Member.is_admin`) can edit it.** Not `added_by` — whoever's turn/choice the book was is the one who can correct its metadata, plus admin override. Route logic: `current_user.id == book.picked_by_id or current_user.is_admin`. Since `picked_by` is nullable, a book with no `picked_by` set can only be edited by an admin. **Deletion uses the same permission, but the route additionally refuses (flashes an error) if the book has any `Rating` rows** — preserves rating history the same way decision 2 does, while still allowing cleanup of a genuine mistake (e.g. duplicate entry) before anyone's rated it.
2. ~~Can a member delete their own rating, or only edit it?~~ **Decided: edit only, no delete.** Preserves a complete reading history (ties to the "don't lose reading history" non-functional requirement below) — a rating can be changed to a different score/comment, but never removed once submitted.
3. ~~Manually seed the 4 accounts vs. build a signup flow?~~ **Decided: invite-only self-registration.** Neither pure manual seeding nor open signup — you (as admin) generate a unique one-time invite link per person via a `flask` CLI command; each person visits their own link once to set their own username/display name/password. See the `Invite` model in the Data Model section below.
4. ~~Rating scale: 1–5, 1–10, half-star increments?~~ **Decided: 1–5, half-star increments (0.5 steps)**, enforced via a DB check constraint and/or form validation.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Framework | **Flask** | Familiar language, plenty for this scale |
| Database | **Postgres via Neon** | Free tier with no hard expiration (unlike Render's free Postgres, which is deleted after 30 days) — data survives app redeploys since it's hosted separately from the app container |
| ORM | **SQLAlchemy** (via Flask-SQLAlchemy) | Standard pairing with Flask |
| Migrations | **Flask-Migrate** | Schema changes over time |
| Auth | **Flask-Login** + Werkzeug's built-in password hashing | No need for a heavier auth library at this scale |
| Forms | **Flask-WTF** | Validation + CSRF protection |
| Frontend | **Jinja2 templates** + Tailwind CSS (CLI build, compiled to a static file) | Server-rendered, no separate frontend framework needed |
| Hosting | **Google Cloud Run** | Free tier (2M requests/month, scales to zero) comfortably covers a 4-person app; Docker-based deploy — see `docs/deployment.md` |
| Book metadata (optional) | **Open Library API** | Free, no API key required, auto-fills cover/author |

**Key decision, resolved during deployment prep:** SQLite vs. Postgres — went with **Postgres via Neon**. SQLite would have meant zero external setup, but needs a host with persistent disk, which Cloud Run's containers don't provide across redeploys. Checked Cloud SQL (GCP-native Postgres) too, but its ~$30+/month baseline is disproportionate at this scale next to Neon's free tier. See `docs/deployment.md` for the full rationale and setup steps.

**Key decision:** Tailwind CLI build vs. Play CDN (`<script src="cdn.tailwindcss.com">`) — the CDN script generates CSS client-side at runtime (extra JS execution, a flash of unstyled content, no purging of unused classes). Since "mobile-friendly" is an explicit requirement and mobile devices are more sensitive to that overhead (slower CPUs, variable network), use the Tailwind CLI to compile a small static CSS file ahead of time instead. One-time setup (`npm install tailwindcss @tailwindcss/cli` + a build command), no ongoing complexity. Tailwind v4 dropped `tailwind.config.js` in favor of CSS-first config (`@import "tailwindcss";`) and auto-detects template files, so there's no `content`/purge config to maintain either.

**Key decision:** Commit the compiled `app/static/css/output.css` to git rather than gitignoring it — the production Docker image (see `Dockerfile`) has no Node/Tailwind build stage, so committing the compiled CSS means the deployed app serves real styles without needing `npm install`/a Tailwind build to run at deploy time. `node_modules/` itself is still gitignored (large, fully reproducible from `package.json`). Revisit this if a proper build pipeline gets added to deployment later.

---

## 3. Data Model (rough sketch)

- **Member**: id, username, password_hash, display_name, is_admin (boolean, default False — not used yet; added ahead of the future admin-portal work below to avoid a separate migration later)
- **Invite**: id, token (unique, random URL-safe string — the value embedded in the invite link), created_at, expires_at (nullable — no forced expiration for now), used_at (nullable — null means still valid/unredeemed, set once someone registers through it)
- **Book**: id, title, author, cover_url, created_at (date added), added_by (FK → Member, required), picked_by (FK → Member, optional — whose turn/choice this book was), status (to-read / currently reading / finished / abandoned), reading_start_date, reading_end_date
- **Rating**: id, book_id (FK → Book), member_id (FK → Member), score (1–5, half-star increments), comment, created_at (date rated) — unique constraint on (book_id, member_id): one rating per member per book
- **Meeting** *(optional, later)*: id, book_id (FK → Book), date, notes

**Note on Invite:** deliberately a separate model from `Member`, not extra nullable fields bolted onto it — keeps `Member.username`/`password_hash` non-nullable and means an unredeemed invite is never a half-formed member row. Invites are created via a `flask` CLI command (only you have server access to run it), not through any web route; the only public-facing piece is the registration form that redeems a given token.

**Note:** `added_by` and `picked_by` are deliberately separate fields — `added_by` is the required "who entered this book into the tracker" field from the functional requirements above, while `picked_by` is the optional "whose turn it was" field. `status` is an explicit column (not derived from the reading dates) specifically so "abandoned" has a clean representation independent of whether start/end dates are set.

---

## 4. Task Breakdown

### Phase 0 — Setup
- [x] Init Flask project structure (app factory pattern recommended)
- [x] Set up SQLAlchemy + choose DB (SQLite to start, or Postgres)
- [x] Set up Flask-Migrate for schema migrations
- [x] Base Jinja template + Tailwind CLI build setup (compiled static CSS, not the Play CDN script)

### Phase 1 — Auth
- [x] Define `Member` model with hashed passwords
- [x] Set up Flask-Login (user loader, login/logout routes)
- [x] Login page + form (Flask-WTF)
- [x] `Invite` model
- [x] `flask create-invite` CLI command (generates a token, prints the link)
- [x] Invite-redemption route (`/auth/register/<token>`) + form — validates token exists/unused/unexpired, creates the `Member`, stamps `used_at`
- [x] `@login_required` on protected routes

### Phase 2 — Core CRUD
- [x] `Book` and `Rating` models + relationships
- [x] Add book route + form
- [x] Book list route/template
- [x] Book detail route/template (shows all ratings)
- [x] Edit/delete book routes
- [x] Add/edit rating route (scoped to current_user) — no delete route, per decision 2 above (edit-only, upserts in place rather than separate add/edit endpoints)

### Phase 3 — Views & Polish
- [x] Sorting/filtering query params on book list — filter by status, sort by status/average rating/reading start date (default), via `?status=...&sort=...` on `GET /books/` (`app/books/routes.py`); status filter is SQL-side, all three sort options are Python-side (`average_rating` is a computed property, and "status" needs reading-progress order, not alphabetical — see code comments). `created_at` ("date added") is deliberately not offered as a sort option — it's DB record-keeping metadata, not something with frontend value.
- [x] Average rating calculation (`Book.average_rating` property)
- [x] Status badges/styling — styled via the `status_badge` macro (`app/templates/_macros.html`), keyed off `BookStatus`; see `docs/design-system.md`
- [x] Half-star rating display — rendered via the `star_rating` macro (overlaid SVG stars, proportional fill), not the raw float anymore
- [x] Conditionally render optional fields — `reading_start_date`/`reading_end_date` are now displayed on the detail page (omitted when unset, same pattern as the existing `picked_by` handling)
- [x] Mobile-responsive pass — all auth/books templates restyled with Tailwind (cards, responsive grid on the book list, etc.); see `docs/design-system.md` for the full per-file breakdown

### Phase 4 — Nice-to-Haves
- [x] Open Library API integration for auto-fill (cover/author). ISBN lookup or a title/author fuzzy search (`GET /books/api/lookup` in `app/books/routes.py`) fills title/author/cover/isbn; a "Show more covers" picker per search candidate (`GET /books/api/lookup/covers`) fetches the matched work's other editions, filtered to English-language editions with real cover art (Open Library exposes no per-edition popularity signal to sort by — confirmed directly against the live API), each paired with its own edition's ISBN so picking an alternate cover can't leave a mismatched ISBN behind. Covers are requested at Open Library's `L` size preset for sharper rendering than the default `M`. Both fetches show an inline loading spinner; the add/edit form also gained a Cancel button and the app gained a site-wide page-navigation loading bar (`app/static/js/main.js`) for slower deployed-server round trips — see `CLAUDE.md`'s "Open Library auto-fill"/"Open Library cover picker" notes for the technical detail.
- [ ] Stats page (who rates highest/lowest, most active reviewer)
- [ ] "Picked by" / rotation tracking
- [ ] Voting/nomination system for the next book
- [ ] Comments/discussion thread per book
- [ ] Export to CSV/shareable summary
- [x] **Stretch**: JS interactivity for things a server round-trip is overkill for. **Decided: vanilla JS (native ES modules, no bundler), organized one file per blueprint (`app/static/js/{auth,books,admin}.js`) plus a `main.js` manifest** — see `docs/js-architecture.md` for the full convention and current status. (Originally considered Alpine.js for this; vanilla JS was chosen instead to keep the file-per-blueprint structure explicit and dependency-free.) The navbar's account menu and the book list's filter menu are both dropdowns built on a shared `initDropdown()` helper (`app/static/js/utils.js`) with Escape-to-close, focus management, and mutual exclusivity — this superseded the original "mobile nav toggle" idea, which became moot once the nav collapsed to a single dropdown trigger. `auth.js` now wires up the login page's inline invite/reset token-entry forms; `admin.js` handles the Safari date-clear button and the admin portal's copy-to-clipboard buttons. Freeform modals and inline form-validation messaging (beyond WTForms' own error rendering) haven't been built.
- [x] **Stretch**: Admin portal for generating invite links from the web app instead of the `flask create-invite` CLI command. `/admin/invites` (list/generate/revoke, with an optional expiration date) and `/admin/members` (generate a one-time password-reset link per member) — both gated by an `admin_required` decorator checking `current_user.is_admin` (`app/admin/routes.py`). Went further than originally scoped here: revoking is a hard delete (no `revoked_at`/soft-revoke column was added), and building this surfaced the fact that there was no account-recovery path at all, which led to the password-reset feature below.
- [x] **Not in original plan**: Admin-generated password reset, since there's no email integration to build a self-service "forgot password" flow on top of. A `PasswordReset` model (`app/models.py`) mirrors `Invite`'s token/expiry/used-at shape but is tied to an existing `Member` and always expires in a fixed 24 hours (not admin-configurable, unlike invites). `/auth/reset-password/<token>` (`app/auth/routes.py`) validates and lets the member set their own new password — the admin never sees or chooses it.
- [x] **Not in original plan**: Book detail prev/next navigation, ordered by `reading_start_date` (same criterion the book list already defaults to sorting by) — an in-flow "‹ Newer" / "Older ›" text-link row above the book content (`app/templates/books/detail.html`), not scoped to whatever filter/sort was active on the list page the user came from.
- [x] **Not in original plan**: Book list default view surfaces Currently Reading book(s) first (`?sort=reading_first`, now the default), with the rest ordered To Be Read → Finished → Abandoned. Currently Reading cards get an amber-border highlight (`book_card` macro's `highlighted` param) regardless of which sort is active; explicitly picking a different sort from the dropdown behaves exactly as it did before this was added.

---

## Notes
This is being built as an educational project — the plan above is a reference/checklist, not a full implementation guide. Work through each phase in order, and it's fine to research each unfamiliar piece (Flask-Login, SQLAlchemy relationships, etc.) as you hit it rather than upfront.
