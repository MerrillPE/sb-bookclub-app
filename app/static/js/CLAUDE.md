# JavaScript

Layout convention (one file per blueprint, `main.js` as the only `<script>` entry point, native ES modules, no bundler): see `docs/js-architecture.md`. `shelf.js` holds side-effect-free helpers so Vitest can import them (`tests/js/`).

## Site chrome (`main.js`)
Page-wide behaviour lives directly in `main.js`, not in a blueprint file:
- **Confirm dialogs**: `<form data-confirm="...">` gets a `window.confirm()` gate. It's registered *before* the loading bar's submit listener, so a cancelled confirm never flashes the bar.
- **Page-navigation loading bar** (`#page-loading-bar` in `base.html`): a thin top bar on same-origin link clicks and form submits, for real server latency once deployed. It's deliberately different from the small circular spinners the Open Library widget uses (`createSpinner()` in `books.js`), so "this widget is loading" reads differently from "the page is navigating."
- **Theme toggle** (`[data-theme-toggle]`): persists to `localStorage`. The *initial* theme is set by a synchronous inline `<script>` in `base.html`'s `<head>` to avoid a flash of the wrong theme. It's the one page-chrome behaviour that isn't in `main.js`.
- **`data-inline-edit`**: a generic view/panel toggle used by more than one blueprint (rating edit, display-name edit, the login page's token panels).

## Star picker (`books.js` + `score_field` macro)
- The value is computed continuously from the pointer's x-position (`pointerdown`/`pointermove` with `setPointerCapture`, via `scoreFromFraction()` in `shelf.js`) rather than from 5 tap targets, so a tap and a drag use the same code path.
- A `change` listener on the real (sr-only) `<select>` re-syncs the star fill and numeric readout, whether the change came from the pointer or from native keyboard use of the select.
- It replaced a native dropdown because a `<select>` opens the OS's heavyweight picker on mobile, and apps like Letterboxd and Goodreads don't use dropdowns for star ratings.

## Book form (`books.js`)
- `fillBookFields()` overwrites title/author/cover/ISBN when the user picks an Open Library result, but no-ops on falsy values. That way a cover from an edition with no ISBN doesn't blank the ISBN field.
- The alternate-cover picker shows a fixed 6-column grid of uniform `aspect-[2/3]` thumbnails.
- `initBookPreview()` live-renders the cover and spine. It must match the Jinja macros; see `.claude/rules/spine-parity.md`.
