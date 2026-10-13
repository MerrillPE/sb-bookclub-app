---
paths:
  - "app/__init__.py"
  - "app/templates/_macros.html"
  - "app/static/js/shelf.js"
  - "app/static/js/books.js"
  - "tests/fixtures/spine_cases.json"
---

# Spine/cover rules are duplicated in Jinja and JS: keep them in sync

A book's cover colour and spine height come from `seed = title_seed(title)`, the sum of the title's code points. Spine width comes from the title's length. The seed is keyed on the **title**, not the row id, so the add/edit form's live preview (`initBookPreview()` in `books.js`, where the book has no id yet) can compute the same result client-side.

The rules exist twice:
- **Python/Jinja**: the `title_seed` filter (`app/__init__.py`), and the `spine` macro's width and height lists and `cover_palette` (`app/templates/_macros.html`). The palette reaches JS via `data-palette`.
- **JS**: `titleSeed()`, `spineWidth()` and `spineHeight()` in `app/static/js/shelf.js`.

If you change one side, change the other. `tests/fixtures/spine_cases.json` holds the expected `{seed, width, height}` per title, and both `tests/test_spine_parity.py` and `tests/js/shelf.test.js` assert against it, so drift fails a suite. Regenerate the fixture's expected values only when changing both sides on purpose.
