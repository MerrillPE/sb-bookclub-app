---
paths:
  - "app/**/forms.py"
  - "app/**/routes.py"
  - "app/templates/**"
---

# Forms, CSRF and destructive actions

**WTForms `obj=` pre-fill gotcha.** `SomeForm(obj=model)` pre-fills fields by matching attribute names. It silently gives the wrong value whenever a field doesn't map 1:1 to a plain column. In `BookForm`:
- `status` needs `book.status.name`, because the model holds an enum member.
- `picked_by` needs `book.picked_by_id`, because `book.picked_by` is the related `Member`, not the FK int.
- `title` needs `book.name`, a different attribute name entirely.

`edit_book()` in `app/books/routes.py` sets all three explicitly inside `if request.method == "GET":` so the override never clobbers a real POST. Do the same for any new field backed by an enum, a relationship or a differently-named column.

**Mirror `String(n)` column limits in the form.** SQLite ignores `String(n)`, but production Postgres raises an error on an over-length value, which shows up as a 500. Any form field backed by a sized column needs a matching `Length(max=n)` plus `render_kw={"maxlength": n}`, as `BookForm` and `RatingForm.comment` do. Local SQLite testing won't catch a missing limit.

**CSRF is per form, not app-wide.** There's no global `CSRFProtect(app)`; protection comes from `form.validate_on_submit()`. A bare `<form method="POST">` with no Flask-WTF form behind it has **no** CSRF protection. For action-only buttons (delete, revoke, ...), use a fieldless `FlaskForm` that exists only to carry the token, as `DeleteForm` (`app/books/forms.py`) and `RevokeInviteForm`/`GenerateResetForm` (`app/admin/forms.py`) do. In the view, `abort(400)` if it doesn't validate. `tests/test_csrf.py` checks each of these.

**Confirm before destructive actions.** Add `data-confirm="..."` to the `<form>`; `main.js` gates submission behind `window.confirm()`. Book delete, invite revoke and rating delete all use this.
