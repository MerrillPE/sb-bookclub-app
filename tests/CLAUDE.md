# Tests

**pytest** runs against in-memory SQLite via `create_app(test_config=...)`. Fixtures and plain factory helpers (`make_member`, `make_book`, `make_rating`, `login`, `d`) are in `conftest.py`; there's no factory_boy. Route tests mostly assert on the template context through the `captured_templates` fixture rather than scraping HTML. `csrf_app` is a CSRF-enabled variant, used by `test_csrf.py`.

Guards that apply to every test (in `conftest.py`):
- An autouse fixture makes any real Open Library call fail. Tests that need Open Library monkeypatch `app.books.routes.requests.get` with canned responses; see `test_open_library.py`.
- A `before_flush` listener fails on any timezone-aware value in a `DateTime` column. It enforces the naive-UTC convention (`.claude/rules/datetimes.md`), which SQLite alone would silently hide.
- `_forget_cached_user` (a `request_started` handler) clears Flask-Login's cached `g._login_user` before every request. The `app` fixture holds one app context open for the whole test and the test client reuses it, so otherwise a logged-in user would leak into later requests, and even into other clients.
- `_discard_uncommitted` (a `request_tearing_down` handler) rolls back the shared `db.session` at the end of each request. Without it, a route that forgot `db.session.commit()` would still pass, because the test would read the uncommitted change from the same session. Test setup that needs to persist must commit; the factories already do.
- `pyproject.toml` turns `DeprecationWarning` (including SQLAlchemy's `LegacyAPIWarning`) into errors.

Rendered-HTML checks live in `test_templates.py`: permission-gated buttons, `data-confirm`, and output escaping, none of which the context-based route tests can see. App-level routes, the `create-invite` CLI and DB URI normalization are covered in `test_app.py`. CI fails below 95% branch coverage.

`test_migrations.py` (marked `slow`) runs the full Alembic chain on a fresh database and fails if the models have drifted from the migrations.

**Vitest** (`tests/js/`) covers the side-effect-free helpers in `app/static/js/shelf.js`. DOM wiring (confirm dialogs, token panels, star picker, inline edit) is tested in `js/dom.test.js` under happy-dom, enabled per file with a `// @vitest-environment` comment. Page scripts wire themselves up on import, so each test sets `document.body` first and re-imports after `vi.resetModules()`. `fixtures/spine_cases.json` is read by both `js/shelf.test.js` and `test_spine_parity.py`; see `.claude/rules/spine-parity.md`.
