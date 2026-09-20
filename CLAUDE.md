# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Phases 0–2 of `docs/sb-bookclub-app-plan.md`'s task breakdown are complete: app factory setup, full invite-based auth, and full book/rating CRUD all work end-to-end. Phase 3 (styling/polish) and Phase 4 (nice-to-haves) have not been started. See `docs/sb-bookclub-app-plan.md` for the full checklist and `.scratch/` for step-by-step build notes (gitignored, personal reference only).

## Commands

- Run the dev server: `flask run` (reads `FLASK_APP`/`FLASK_DEBUG` from `.env` automatically via python-dotenv)
- Apply schema changes: `flask db migrate -m "..."` then `flask db upgrade`
- Generate a member invite link: `flask create-invite` (prints a token/path; prepend the host to visit it)
- Rebuild Tailwind CSS after editing templates or classes: `npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --minify` (swap `--minify` for `--watch` during active template work — compiled CSS is committed to git, so forgetting to rebuild means styling changes silently don't appear)
- No automated test suite exists yet. No linter/formatter is configured (pylint/black were discussed but never installed).

## Architecture

**App factory + blueprints**: `app/__init__.py`'s `create_app()` wires config, three extensions (`db`, `migrate`, `login_manager` — all instantiated unbound in `app/extensions.py`, then `.init_app()`'d here to avoid circular imports with `models.py`), imports `app/models.py` once (required so Alembic's autogenerate can see the model classes — they're otherwise never imported anywhere in the factory's chain), and registers two blueprints: `auth` (`app/auth/`) and `books` (`app/books/`). Each blueprint package has `routes.py` (the `Blueprint` object + views) and `forms.py` (Flask-WTF forms); `__init__.py` just re-exports `bp` from `routes.py`.

**Models** (`app/models.py`): `Member` (has `is_admin`, currently unused by any route — reserved for a future admin portal, see plan doc Phase 4), `Invite` (one-time registration tokens, created only via the `flask create-invite` CLI command, never through a web route), `Book`, `Rating`, and the `BookStatus` enum. `Book`'s title column is named `name`, not `title` — a naming mismatch from early development that was never renamed; forms/routes map between them (`Book(name=form.title.data, ...)`), it's intentional-by-inertia, not a bug.

**Auth is invite-only self-registration**, not manual seeding: `flask create-invite` creates an `Invite` row (token auto-generated via `secrets.token_urlsafe`), and `/auth/register/<token>` validates it (exists, unused, unexpired) before letting someone create their own `Member`. `display_name` defaults to `username` at registration — there's no separate field for it; changing it later is an unbuilt Phase 3 feature.

**Book edit/delete permission**: `current_user.id == book.picked_by_id or current_user.is_admin` (helper: `_can_manage()` in `app/books/routes.py`) — the person whose turn it was to pick the book, or an admin. Delete additionally refuses if the book has any ratings, to preserve reading history. Ratings themselves have no delete route at all (by design) — `book_detail()` is a combined GET/POST view that *upserts*: looks up any existing `Rating` for `(book_id, current_user.id)` and updates it in place, or creates one if none exists.

**WTForms gotcha worth knowing before adding more form fields**: `SomeForm(obj=some_model)` pre-fills fields by matching attribute names on the object. This breaks silently (no error, just wrong pre-filled value) whenever a form field's name doesn't line up 1:1 with a plain column — e.g. `BookForm.status` needs `book.status.name` (the object holds an enum member, the field expects the enum's string name), `BookForm.picked_by` needs `book.picked_by_id` (the object's matching-named attribute is a relationship returning a `Member`, not the FK int the field expects), and `BookForm.title` needs `book.name` (different attribute names entirely, per the mismatch above). `edit_book()` in `app/books/routes.py` overrides all three explicitly, guarded by `if request.method == "GET":` so the override doesn't clobber a real POST submission. Follow this pattern for any new form field backed by an enum, a relationship, or a differently-named column.

**CSRF on non-FlaskForm actions**: Flask-WTF's CSRF protection is per-form-instance (validated via `form.validate_on_submit()`), not a blanket app-wide check — there's no global `CSRFProtect(app)` registered. A plain `<form method="POST">` with no Flask-WTF form behind it (e.g. a bare delete button) gets **no** CSRF protection. The pattern used for the book delete button (`DeleteForm` in `app/books/forms.py` — a fieldless `FlaskForm` that exists purely to carry a token) is the template to follow for any future action-only button.

## Data Model

- **Member**: id, username, password_hash, display_name, is_admin
- **Invite**: id, token (unique), created_at, expires_at (nullable, unused so far), used_at (nullable — null means still valid)
- **Book**: id, name (displayed/referred to as "title"), author, cover_url, added_by_id (FK, required), picked_by_id (FK, nullable), created_at, reading_start_date, reading_end_date, status (`BookStatus` enum, has a DB-level `CHECK` constraint)
- **Rating**: id, book_id (FK), member_id (FK), score (float, 1.0–5.0 in 0.5 steps, DB-level `CHECK` constraint), comment, created_at — unique constraint on `(book_id, member_id)`

All decisions from the plan doc's "Decisions to Make Before Coding" are resolved — see that file for the reasoning, not repeated here.

## Development Approach

This is an educational project. `docs/sb-bookclub-app-plan.md`'s Task Breakdown is the authoritative checklist of what's done vs. remaining — check it before assuming a feature doesn't exist.
