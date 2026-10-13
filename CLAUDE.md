# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Phases 0–3 of `docs/sb-bookclub-app-plan.md` are complete (app factory, invite-based auth, book/rating CRUD, styling). Phase 4 is underway: the admin portal, book prev/next navigation, "Currently Reading first" list ordering and Open Library auto-fill are done. A stats page, picked-by rotation, voting/nomination and CSV export are not started. Beyond the checklist, the app has a bookshelf-themed redesign with dark mode, a tap/drag star-picker for ratings, member profiles, and pytest + Vitest suites. Comments exist only as part of a rating, not as a threaded feature. `.scratch/` holds personal build notes (gitignored).

## Commands

- Dev server: `flask run` (reads `FLASK_APP`/`FLASK_DEBUG` from `.env` via python-dotenv)
- Schema changes: `flask db migrate -m "..."` then `flask db upgrade`
- Member invite: `flask create-invite` (prints a token/path; prepend the host). Admins can also use `/admin/invites`, which additionally supports expiry dates and revoking.
- Rebuild Tailwind after editing templates or classes: `npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --minify` (`--watch` while iterating). The compiled CSS is committed, so forgetting to rebuild means styling changes silently don't appear.
- Tests: `pip install -r requirements-dev.txt` once, then `pytest` (`--cov=app` for coverage, `-m "not slow"` skips the migration-chain check); `npm test` for Vitest. Both run on PRs via `.github/workflows/test.yml`, which also enforces a 95% branch-coverage floor (`--cov-branch --cov-fail-under=95`); both jobs (`python`, `js`) are required status checks in the "main branch protection" ruleset, so a failing PR can't merge and therefore can't trigger `deploy.yml`. The ruleset matches checks by job ID — rename a job and you must update the ruleset too.
- Production image: `docker build -t sb-bookclub-app .` then `docker run -e SECRET_KEY=... -e SQLALCHEMY_DATABASE_URI=... -e FLASK_DEBUG=0 -p 8080:8080 sb-bookclub-app`
- Deploys: pushing to `main` deploys code automatically (`.github/workflows/deploy.yml`, Workload Identity Federation). Migrations are deliberately **not** automated: point `SQLALCHEMY_DATABASE_URI` at production Postgres and run `flask db upgrade` from your machine (Cloud Run has no release-phase hook). Full runbook: `docs/deployment.md`.
- No linter/formatter is configured.

## Architecture

**App factory + blueprints**: `create_app()` in `app/__init__.py` wires config and three extensions. `db`, `migrate` and `login_manager` are created unbound in `app/extensions.py` and `.init_app()`'d in the factory, which avoids circular imports with `models.py`. The factory imports `app/models.py` once; Alembic autogenerate needs that to see the models, since nothing else in the factory chain imports them. It registers four blueprints: `auth`, `books`, `admin` and `members`, each a package under `app/` with `routes.py` (the `Blueprint` + views) and `forms.py`. Each package's `__init__.py` just re-exports `bp`.

**Models** (`app/models.py`): `Member`, `Invite`, `PasswordReset`, `Book`, `Rating`, plus the `BookStatus` enum. `Book`'s title column is named `name`, not `title`. That mismatch is left over from early development; forms and routes map between the two (`Book(name=form.title.data, ...)`), and it is not a bug.

**Admin accounts aren't readers**: the admin is a separate club-management login, seeded before members join. Admins are excluded from the members section, the "Picked by" choices (`_picked_by_choices()`), a book's "still to weigh in" list, and member counts. Keep that true for any new member-facing list.

## Data Model

- **Member**: id, username (unique), password_hash, display_name (not unique, member-editable), is_admin
- **Invite**: id, token (unique), created_at, expires_at (nullable; settable from `/admin/invites`), used_at (nullable; null means still valid)
- **PasswordReset**: id, member_id (FK, required), token (unique), created_at, expires_at (fixed 24h after creation, not nullable), used_at (nullable; null means still valid)
- **Book**: id, name (shown as "title"), author, cover_url, isbn (nullable; from the Open Library lookup or typed by hand), added_by_id (FK, required), picked_by_id (FK, nullable), created_at, reading_start_date, reading_end_date, status (`BookStatus` enum, DB-level `CHECK` constraint)
- **Rating**: id, book_id (FK), member_id (FK), score (float, 1.0–5.0 in 0.5 steps, DB-level `CHECK`), comment (`db.String(500)`; `RatingForm.comment` mirrors it with `Length(max=500)` and a `maxlength` attribute, because SQLite silently truncates an over-length string while production Postgres raises an error), created_at. Unique on `(book_id, member_id)`.

All of the plan doc's "Decisions to Make Before Coding" are resolved; the reasoning lives in that file and is not repeated here.

## Where the detailed guidance lives

Area-specific notes load automatically when Claude works in the matching files:

- Nested CLAUDE.md files, one per area: `app/auth/` (invites, registration, password reset), `app/admin/`, `app/books/` (permissions, ratings, list/detail views, Open Library), `app/members/`, `app/templates/` (macros, layouts), `app/static/js/`, `tests/`
- `.claude/rules/` holds conventions that span directories:
  - `styling.md`: color tokens, dark mode, component classes
  - `forms-and-csrf.md`: the WTForms `obj=` gotcha, CSRF on action buttons, confirm dialogs
  - `datetimes.md`: the naive-UTC convention
  - `spine-parity.md`: Jinja and JS spine/colour rules must match
- `docs/js-architecture.md` (JS file layout), `docs/deployment.md` (deploy runbook)

## Development Approach

This is an educational project. The Task Breakdown in `docs/sb-bookclub-app-plan.md` is the authoritative checklist of what's done vs. remaining; check it before assuming a feature doesn't exist.
