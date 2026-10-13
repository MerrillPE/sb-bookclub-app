---
paths:
  - "app/templates/**"
  - "app/static/src/**"
---

# Styling conventions

- **Semantic color tokens, not raw palette classes.** Every themed color is a CSS custom property in `app/static/src/input.css`, defined once under `:root` (light, "paper and ink") and once under `.dark` (lamplit). Each is aliased into `@theme` as `--color-*`, so Tailwind generates ordinary utilities (`bg-page-bg`, `text-text-secondary`, `border-border-subtle`, ...). Retuning a color is a one-line edit in `input.css`, never a template sweep. Don't reach for raw `amber-*`/`stone-*` for themed colours.
- **The tokens** are: `page-bg`, `surface`/`surface-muted`, `nav-bg`/`nav-fg`, `border-subtle`/`border-strong`, `text-primary`/`text-secondary`, `btn-primary`/`btn-primary-hover`/`btn-primary-fg`, `btn-danger`/`btn-danger-hover`, `input-bg`, `accent`/`accent-soft`, `star`, and `--wood`/`--wood-light`/`--wood-dark` for shelves.
  - `btn-primary-fg` exists for contrast: dark-mode primary buttons use dark text.
  - `nav-bg`/`nav-fg` are just `page-bg`/`text-primary`. The navbar deliberately blends into the page, separated only by a `border-border-subtle` hairline.
- **Dark mode is class-based**: `@custom-variant dark (&:where(.dark, .dark *));`. `.dark` also sets `color-scheme: dark` so native date pickers and selects follow the theme. The toggle and the no-flash initial theme are described in `app/static/js/CLAUDE.md`.
- **Small accent pieces** (status badges, flash banners) aren't tokenized; they get hand-written `dark:` overrides at each call site.
- **Type**: headings use **Fraunces** (`font-serif`) and body text uses **Inter** (`font-sans`). Both load from a single Google Fonts `<link>` in `base.html`.
- **Component classes** (`@layer components` in `input.css`):
  - `.btn` with `.btn-primary`, `.btn-secondary` or `.btn-danger-quiet`. Destructive actions use the quiet outlined style, not solid red.
  - `.field-input`, `.link-quiet`, `.card`, `.eyebrow`, `.section-title`
  - Utilities still override these for one-offs, e.g. `btn btn-primary px-3`.
- **Rebuild the CSS** after changing classes or `input.css` (command in the root CLAUDE.md). `output.css` is committed, so a missed rebuild ships stale styles.
