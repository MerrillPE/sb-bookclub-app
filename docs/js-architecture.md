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

## Status

Structure only, as of this doc's writing — `main.js`/`auth.js`/`books.js` exist as stubs with no behavior yet. Real interactivity (mobile nav toggle, etc.) is Phase 4 work; it drops into the existing files rather than requiring another `base.html` pass.
