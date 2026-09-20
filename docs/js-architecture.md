# JavaScript Architecture

Currently there's no JavaScript anywhere in this app — no `app/static/js/`, no `<script>` tag in any template, no JS runtime dependency in `package.json` beyond Tailwind's own build tooling. This doc defines the convention for when JS gets added (starting with Phase 4's stretch items — mobile nav toggle, modals, inline validation — per `docs/sb-bookclub-app-plan.md`), so it's decided once rather than improvised page by page.

## The convention

Closest existing analogue: the old Rails asset-pipeline pattern — one file per controller, plus an `application.js` manifest that requires them all. There's no strict formal design-pattern name for this; it's an asset-organization convention, not a GoF pattern.

```
app/static/js/
  main.js    # entry point / manifest — the only <script> tag base.html ever needs
  auth.js    # mirrors app/auth/ — auth blueprint's JS hooks
  books.js   # mirrors app/books/ — books blueprint's JS hooks
```

`main.js` statically imports every blueprint file:

```js
import "./auth.js";
import "./books.js";
```

`base.html` loads only `main.js`, once, right before `</body>`:

```html
<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>
```

## Why this shape

- **No bundler.** Native ES modules (`type="module"`), consistent with the project's existing no-build-step philosophy — Tailwind CLI compiles CSS ahead of time and is committed to git; nothing analogous is needed for JS at this scale (see `CLAUDE.md`'s "Commit the compiled `output.css`" key decision for the same reasoning applied to CSS).
- **One script tag, forever.** `main.js` loads on every page. As new blueprints or features get added, they just get a new `import` line in `main.js` — no per-template `{% block scripts %}` bookkeeping to maintain.
- **Self-guarding modules, not page namespacing.** Since `main.js` always loads every blueprint file regardless of which page is active, each file's code must check for its own DOM hook before doing anything, e.g.:
  ```js
  const toggle = document.querySelector("[data-mobile-nav-toggle]");
  if (toggle) {
    // wire up the listener
  }
  ```
  A page/body-class namespacing scheme (e.g. `<body class="books-detail">` + a router-style dispatcher) was considered and rejected — it's more infrastructure than the 2–3 small Phase 4 features warrant. Revisit if the JS surface grows substantially.
- **Vanilla JS, not Alpine.js.** Alpine.js was the plan doc's original Phase 4 suggestion (declarative `x-data`/`x-on` attributes, no build step). Vanilla JS was chosen instead specifically to keep the one-file-per-blueprint structure explicit and dependency-free — see `docs/sb-bookclub-app-plan.md`'s Phase 4 section for the current (updated) note.

## Exception: site-wide chrome lives directly in `main.js`

The "one file per blueprint" convention above assumes every piece of behavior is owned by exactly one blueprint. The navbar isn't — it's in `base.html`, rendered on every page regardless of blueprint, so it doesn't belong in `auth.js` or `books.js` any more than the other. Its behavior (the user-menu dropdown) is initialized directly in `main.js` instead, right below the `import` lines. `main.js` already loads on every page, so this is the natural home for anything that's genuinely site-wide rather than blueprint-specific. `auth.js`/`books.js` stay reserved for behavior actually specific to those blueprints' own pages.

## Exception: shared low-level helpers live in `utils.js`

A second, narrower exception: `app/static/js/utils.js` exports small reusable functions (currently just `initDropdown(toggleSelector, menuSelector)`) that more than one file needs. This isn't page-owned behavior like the `main.js` exception above — it's a plain helper, imported wherever it's needed (`main.js` for the navbar's account menu, `books.js` for the book list's filter menu). It exists specifically to avoid copy-pasting the same toggle logic into every file that wants a dropdown; if a third, unrelated kind of shared helper shows up later, it can live here too rather than each getting its own single-purpose file.

`initDropdown()` handles, for every dropdown it's called on: click-to-toggle, close-on-click-outside, Escape-to-close (with focus returned to the trigger), and focus-on-open (moves to the first focusable element inside the panel). It also tracks every dropdown it's initialized for in a module-level registry, so opening one automatically closes any other that's open — mutual exclusivity across the whole app, not just within one dropdown, falls out of all dropdowns sharing this one function rather than each reimplementing it.

## Status

`main.js` initializes the navbar's user-menu dropdown (`base.html`'s `[data-user-menu-toggle]`/`[data-user-menu]`). `books.js` has its first real behavior too: the book list's filter dropdown (`[data-filter-toggle]`/`[data-filter-menu]`). Both call the shared `initDropdown()` helper from `utils.js` rather than each implementing the toggle logic themselves. `auth.js` is still a stub — no auth-blueprint-specific interactivity has landed yet. Further Phase 4 features (modals, inline validation) drop into the relevant blueprint file when they come up.
