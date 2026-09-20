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
- A member can edit/delete only *their own* rating
- Book detail view shows all 4 members' ratings side by side + average

**Views**
- Book list: sortable/filterable by status, average rating, date
- Book detail: full info + all ratings/comments
- Optional: member profile/stats page

### Non-Functional Requirements
- Mobile-friendly (people will rate books from their phones)
- Fast page loads (small data scale, so this should be easy)
- Data durability — don't lose reading history
- Low/no cost to run at this scale

### Decisions to Make Before Coding
1. Can anyone edit any book's metadata, or only the person who added it? *(suggested: anyone, keep it simple)*
2. Can a member delete their own rating, or only edit it?
3. ~~Manually seed the 4 accounts vs. build a signup flow?~~ **Decided: invite-only self-registration.** Neither pure manual seeding nor open signup — you (as admin) generate a unique one-time invite link per person via a `flask` CLI command; each person visits their own link once to set their own username/display name/password. See the `Invite` model in the Data Model section below.
4. ~~Rating scale: 1–5, 1–10, half-star increments?~~ **Decided: 1–5, half-star increments (0.5 steps)**, enforced via a DB check constraint and/or form validation.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Framework | **Flask** | Familiar language, plenty for this scale |
| Database | **SQLite** to start (or Postgres via Supabase/Neon if you want it hosted separately) | SQLite is fine for 4 users; watch for hosts with ephemeral disks if you go this route |
| ORM | **SQLAlchemy** (via Flask-SQLAlchemy) | Standard pairing with Flask |
| Migrations | **Flask-Migrate** | Schema changes over time |
| Auth | **Flask-Login** + Werkzeug's built-in password hashing | No need for a heavier auth library at this scale |
| Forms | **Flask-WTF** | Validation + CSRF protection |
| Frontend | **Jinja2 templates** + Tailwind CSS (CLI build, compiled to a static file) | Server-rendered, no separate frontend framework needed |
| Hosting | **Render** or **Railway** | Flask-friendly, easy free/cheap tiers, can host Postgres alongside if needed |
| Book metadata (optional) | **Open Library API** | Free, no API key required, auto-fills cover/author |

**Key decision:** SQLite vs. Postgres — SQLite means zero external setup (data is just a file), but needs a host with persistent disk. Postgres (via Supabase/Neon free tier) avoids that concern from day one at the cost of slightly more setup.

**Key decision:** Tailwind CLI build vs. Play CDN (`<script src="cdn.tailwindcss.com">`) — the CDN script generates CSS client-side at runtime (extra JS execution, a flash of unstyled content, no purging of unused classes). Since "mobile-friendly" is an explicit requirement and mobile devices are more sensitive to that overhead (slower CPUs, variable network), use the Tailwind CLI to compile a small static CSS file ahead of time instead. One-time setup (`npm install tailwindcss @tailwindcss/cli` + a build command), no ongoing complexity. Tailwind v4 dropped `tailwind.config.js` in favor of CSS-first config (`@import "tailwindcss";`) and auto-detects template files, so there's no `content`/purge config to maintain either.

**Key decision:** Commit the compiled `app/static/css/output.css` to git rather than gitignoring it — there's no build step configured on Render/Railway yet, so committing the compiled CSS means the deployed app serves real styles without needing `npm install`/a Tailwind build to run on the host. `node_modules/` itself is still gitignored (large, fully reproducible from `package.json`). Revisit this if a proper build pipeline gets added to deployment later.

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
- [ ] Init Flask project structure (app factory pattern recommended)
- [ ] Set up SQLAlchemy + choose DB (SQLite to start, or Postgres)
- [ ] Set up Flask-Migrate for schema migrations
- [ ] Base Jinja template + Tailwind CLI build setup (compiled static CSS, not the Play CDN script)

### Phase 1 — Auth
- [x] Define `Member` model with hashed passwords
- [x] Set up Flask-Login (user loader, login/logout routes)
- [ ] Login page + form (Flask-WTF)
- [x] `Invite` model
- [ ] `flask create-invite` CLI command (generates a token, prints the link)
- [ ] Invite-redemption route (`/auth/register/<token>`) + form — validates token exists/unused/unexpired, creates the `Member`, stamps `used_at`
- [ ] `@login_required` on protected routes

### Phase 2 — Core CRUD
- [ ] `Book` and `Rating` models + relationships
- [ ] Add book route + form
- [ ] Book list route/template
- [ ] Book detail route/template (shows all ratings)
- [ ] Edit/delete book routes
- [ ] Add/edit/delete rating routes (scoped to current_user)

### Phase 3 — Views & Polish
- [ ] Sorting/filtering query params on book list
- [ ] Average rating calculation (model property or query aggregate)
- [ ] Status badges/styling — `BookStatus` is stored by enum *name* (e.g. `TO_BE_READ`), not a human-readable string; templates need a label mapping rather than printing the raw name/value directly
- [ ] Half-star rating display — `Rating.score` is a Float in 0.5 increments; render as full/half star icons rather than a raw number
- [ ] Conditionally render optional fields — `picked_by`, `reading_start_date`, `reading_end_date` are all nullable; templates need graceful "not set" states (e.g. a to-read book has no reading dates yet, not every book has a picked_by)
- [ ] Mobile-responsive pass

### Phase 4 — Nice-to-Haves
- [ ] Open Library API integration for auto-fill (cover/author)
- [ ] Stats page (who rates highest/lowest, most active reviewer)
- [ ] "Picked by" / rotation tracking
- [ ] Voting/nomination system for the next book
- [ ] Comments/discussion thread per book
- [ ] Export to CSV/shareable summary
- [ ] **Stretch**: JS interactivity for things a server round-trip is overkill for — mobile nav toggle, modals, inline form validation, etc. (Alpine.js is a natural fit alongside Tailwind — lightweight, no build step of its own, declarative like Tailwind's utility classes)
- [ ] **Stretch**: Admin portal for generating invite links from the web app instead of the `flask create-invite` CLI command. `Member.is_admin` already exists for this (added early, unused until this lands) — the portal work itself (an admin-only view, route protection checking `current_user.is_admin`, a form to create/list/revoke invites) is not started

---

## Notes
This is being built as an educational project — the plan above is a reference/checklist, not a full implementation guide. Work through each phase in order, and it's fine to research each unfamiliar piece (Flask-Login, SQLAlchemy relationships, etc.) as you hit it rather than upfront.
