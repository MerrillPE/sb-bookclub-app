# Templates

Styling conventions (color tokens, dark mode, component classes) are in `.claude/rules/styling.md`. Form/CSRF/confirm patterns are in `.claude/rules/forms-and-csrf.md`.

## Shared macros (`_macros.html`)
- `book_cover(book)` renders the cover image, or a typographic cover on a cloth colour from `cover_palette` when `cover_url` is empty. Text is sized with container-query `cqw` units, so one macro works at any size.
- `spine(title, author, seed, href, label, leaning)` renders one shelf spine:
  - width comes from the title's length, so the title fits
  - height and colour come from `seed`
  - `leaning=True` tips the spine over; it's used for Abandoned books, labelled "DNF"
- `book_spine(book)` and `faceout_book(book)` wrap real books, adding a hover/focus popover (`book_popover`).
- The auth pages reuse `spine()` with a fixed list of classics as decoration (`auth/_layout.html`).
- Spine and cover colours are keyed on the book's **title** via the `title_seed` filter; see `.claude/rules/spine-parity.md` before changing anything about it.
- `avatar(member)` uses the same palette, keyed on member id.
- `book_card(book, highlighted)` is the flat-grid card. `highlighted` adds an accent ring and is used for Currently Reading books.
- `rating_card(rating, own, delete_form)`: `own=True` shows the edit and delete buttons.
- `score_field(field)` renders the star-picker. It keeps the real `<select>` as `sr-only` (not `display:none`) so keyboard and screen-reader users get the native control, with an `aria-hidden` star row on top for pointer users. JS details are in `app/static/js/CLAUDE.md`.
- `status_badge` / `invite_status_badge` are colour-coded badges with hand-written `dark:` overrides.

## Layout
- `.shelf` is a flex-wrap row of fixed-height slots (`--slot`), with a wooden plank painted under every row by a repeating background gradient. The planks only line up because every direct child is exactly `--slot` tall, so keep children as single slot wrappers. `.shelf-faceout` is the face-out (covers) variant.
- `base.html` has a `{% block hero %}` outside `<main>`'s max-width for full-bleed headers; the book detail page uses it for a blurred-cover backdrop.
- Admin pages extend `admin/_layout.html`; auth pages extend `auth/_layout.html`.

## Conventions
- **Flash categories**: always pass one, either `flash(msg, "success")` or `flash(msg, "error")`. `base.html` styles each; uncategorised messages fall back to neutral.
- **Dates**: use the `nice_date` filter, never `strftime("%-d")`. `%-d` is glibc-only and raises `ValueError` on Windows.
