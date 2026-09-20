# Design System — UI Modernization (Phase 3)

This is the visual spec for Phase 3's "styling/polish" work (see `docs/sb-bookclub-app-plan.md`'s Task Breakdown). It exists because, as of this doc's writing, `app/templates/` has essentially no design system to extend — only `base.html`'s navbar carries any Tailwind classes. Everything below is a from-scratch spec, not a description of existing conventions.

Implementation is being done by hand, file by file, following this spec — not generated wholesale — so it doubles as a build checklist. Check items off as you go.

---

## Palette — "warm & literary"

Stock Tailwind v4 colors, no custom `@theme` color tokens needed.

| Purpose | Class |
|---|---|
| Page background | `bg-stone-50` |
| Card background | `bg-white` |
| Headings | `text-stone-900` + `font-serif` |
| Body text | `text-stone-700` |
| Muted/meta text | `text-stone-500` |
| Borders | `border-stone-200` |
| Primary accent (buttons, links) | `bg-amber-700`, hover `bg-amber-800` |
| Destructive (delete) | `bg-rose-600`, hover `bg-rose-700` |
| Navbar | `bg-stone-900` (was `bg-slate-800` — the one pre-existing styled element) |

Status badges (keyed off `BookStatus`):

| `BookStatus` value | Badge classes |
|---|---|
| `to_be_read` | `bg-stone-100 text-stone-600` |
| `currently_reading` | `bg-amber-100 text-amber-800` |
| `finished` | `bg-emerald-100 text-emerald-700` |
| `abandoned` | `bg-rose-100 text-rose-700` |

## Typography

- Body copy: Tailwind's default sans-serif stack (`font-sans`) — no extra request.
- Headings, site title, book titles: **Lora** (serif), weights 400/600/700, loaded via one Google Fonts `<link>` in `base.html`'s `<head>`.
- Map it to Tailwind's `font-serif` utility in `input.css`:
  ```css
  @theme {
    --font-serif: "Lora", serif;
  }
  ```
  This is the idiomatic Tailwind v4 way to do it (CSS-first config) rather than inline `style="font-family: ..."` on every element.

## Icons & star ratings

No icon library dependency. One hand-written SVG star (outline + filled variants), reused via the `star_rating` macro.

**Half-star technique:** overlay two rows of 5 stars inside a `relative` wrapper:
1. Background row — 5 outline stars, `text-stone-300`.
2. Foreground row — 5 filled stars, `text-amber-500`, `absolute inset-0`, wrapped in an element with `style="width: {{ (score / 5 * 100) }}%"` and `overflow-hidden`.

This renders any 0.5-increment score (1.0–5.0) as a proportionally-filled star row without needing a separate "half star" glyph.

## Reusable components — `app/templates/_macros.html`

The same `<p>{{ form.field.label }} {{ form.field() }}</p>` pattern is duplicated across 4 templates today (login, register, book form, rating form) — enough repetition to warrant one shared macros file.

```jinja
{% from "_macros.html" import form_field, status_badge, star_rating %}
```

- **`form_field(field)`** — label + input + error text, consistently styled:
  - label: `block text-sm font-medium text-stone-700`
  - input: `mt-1 block w-full rounded-md border-stone-300 shadow-sm focus:border-amber-600 focus:ring-amber-600 sm:text-sm`
  - error text (if `field.errors`): `mt-1 text-sm text-rose-600`
- **`status_badge(status_value, status_label)`** — `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium` + the color pair from the table above, keyed on `status_value`
- **`star_rating(score)`** — the half-star overlay component described above

Buttons are *not* macro'd — only a handful exist total, so repeating the utility-class string per variant (primary/danger) is fine at this scale. Revisit if more buttons get added later.

Primary button: `inline-flex items-center rounded-md bg-amber-700 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-amber-800`
Danger button (delete): same shape, `bg-rose-600 hover:bg-rose-700`

## Per-file checklist

- [x] **`app/templates/_macros.html`** (new) — `form_field`, `status_badge`, `star_rating`
- [x] **`base.html`** — navbar → `bg-stone-900`; add Lora `<link>` + `@theme --font-serif`; wrap `{% block content %}` in `<main class="max-w-4xl mx-auto px-4 py-8">` (no content wrapper exists today)
- [x] **`auth/login.html`** — centered card (`max-w-sm mx-auto bg-white border border-stone-200 rounded-lg shadow-sm p-6`), fields via `form_field`, primary submit button, styled error box instead of bare `<ul>`
- [x] **`auth/register.html`** — same card treatment as login
- [x] **`books/list.html`** — card grid (`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`); each card: `cover_url` image if set (with a placeholder if not — currently collected, never displayed anywhere), `font-serif` title, `status_badge`, `star_rating` replacing the raw "Avg: X.X" text
- [x] **`books/detail.html`** — header with cover + title/author/`status_badge`/`star_rating`; **add `reading_start_date`/`reading_end_date` display** (collected today, never shown — omitted when unset, same as the existing `picked_by` pattern); Edit = primary button, Delete = danger button; ratings list uses `star_rating`; "Your Rating" form gets the card treatment
- [x] **`books/form.html`** — card treatment, every field via `form_field` including the `status`/`picked_by` selects

All six files above are done. Remaining Phase 3 work (sorting/filtering) is functional, not visual — tracked in `docs/sb-bookclub-app-plan.md` instead, not this checklist.

## Out of scope for this pass

- Sorting/filtering query params (Phase 3 item, but functional not visual)
- Alpine.js/JS interactivity, admin portal, Open Library auto-fill (Phase 4)
- Dark mode (would roughly double every color decision above)

## Modern-convention notes

- Tailwind v4's CSS-first `@theme` config (used above) is the current recommended pattern over the old `tailwind.config.js` — this project's already on it.
- Consider `loading="lazy"` on book cover `<img>` tags — standard practice for below-the-fold images.
- Badge color pairs above (e.g. `amber-800` on `amber-100`) are chosen to be plausibly WCAG-AA-safe, but worth a spot-check with a contrast checker once built.
