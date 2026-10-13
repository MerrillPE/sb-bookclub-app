---
paths:
  - "app/**/*.py"
  - "tests/**/*.py"
  - "migrations/**"
---

# Datetimes: naive UTC everywhere

`created_at`/`expires_at`/`used_at` are plain `db.DateTime` columns (no `timezone=True`). Always write and compare them as timezone-*naive* UTC via `_naive_utcnow()` in `app/models.py` (`datetime.now(timezone.utc).replace(tzinfo=None)`).

- **Never `datetime.utcnow()`**: it's deprecated as of Python 3.12.
- **Never store or compare a timezone-aware datetime against these columns.** Comparing naive with aware raises `TypeError: can't compare offset-naive and offset-aware datetimes`. Storing an aware value works by accident on SQLite (which drops tzinfo), but on production Postgres the result depends on the session timezone. Postgres `TIMESTAMP WITHOUT TIME ZONE` is naive by column type, so `_naive_utcnow()` round-trips identically on both databases.
- Building a datetime from a form date (e.g. an invite's expiry): use `datetime.combine(...)` and don't attach `tzinfo`.
- The test suite enforces this: a `before_flush` listener in `tests/conftest.py` fails any test that flushes an aware datetime.
