# Books blueprint

## Permissions
- **Edit/delete a book**: `_can_manage(book)`, which is `current_user.id == book.picked_by_id or current_user.is_admin` (whoever picked it, or an admin). Delete also refuses if the book has any ratings, to preserve reading history. When a non-admin saves a book, `picked_by` is forced to themselves; only admins can choose someone else.
- **`BookForm` validation**: a reading end date before the start date is rejected (same-day is fine). Field lengths mirror the columns; see `.claude/rules/forms-and-csrf.md`.
- **Ratings are strictly self-scoped**: there's no admin override. `own=True` on the `rating_card` macro gates both the edit and delete buttons.

## Views
- **`book_detail()`** is a combined GET/POST view that *upserts* the current member's `Rating`: it updates the existing row for `(book_id, current_user.id)` or creates one. Ratings can only be submitted for Finished books; other statuses show a status-specific placeholder instead of the review area. The view also passes:
  - `newer_book`/`older_book` for prev/next links, computed via the same `_sort_books()` the list uses
  - `distribution`: whole-star buckets 5..1 (a 4.5 counts as 4)
  - `unrated_members` and `rated_member_count`, both excluding admins
- **`delete_rating()`** (`POST /<book_id>/rating/delete`) deletes the current member's own rating, looked up by `(book_id, current_user.id)` rather than a rating id, since the unique constraint allows at most one. Score and comment share the row, so there's no "delete just the comment."
- **`edit_book()`** passes `book=book` to `books/form.html` but `add_book()` doesn't. That's how the template tells the two modes apart: Cancel goes back to the detail page in edit mode and to the list in add mode.

## Book list (`index()`)
- The default sort is `?sort=reading_first`: `_sort_books()` stable-sorts by start date, then by `_LIST_STATUS_ORDER` (Currently Reading, To Be Read, Finished, Abandoned). Explicit "Start date" / "Status" / "Average rating" sorts behave as plain sorts.
- The default view (`reading_first`, no status filter, no `?view=grid`) is sectioned as a bookshelf, in this order:
  - a club-stats masthead (`_club_stats()`)
  - a "Now reading" feature per Currently Reading book
  - "Up next" (To Be Read) face-out
  - Finished/Abandoned books as spines, one shelf per start year (`_group_by_year()`)
- Any explicit filter or sort, or the "Covers" toggle (`?view=grid`), renders the flat `book_card` grid instead, with Currently Reading books highlighted. An empty club gets an "Add your first book" welcome state.

## Open Library lookup (`/books/api/lookup`, `/books/api/lookup/covers`)
These are the app's only outbound HTTP calls; the client side is in `app/static/js/books.js`.
- **Lookup**:
  - Both the ISBN path and the title/author path use `search.json`. The older `api/books` endpoint 404s.
  - An ISBN must pass `_is_valid_isbn()` before any request is made, and a result only counts as a match if that ISBN appears in the doc's `isbn` list, because `search.json` treats `isbn` as a loose search term.
  - A title/author search returns up to 5 candidates, since there's no single right edition.
- **Author**: `_open_library_candidate()` takes only `author_name[0]`. `search.json` merges author names across every edition of a work with no role tags, so illustrators and translators would otherwise leak in. A genuine second author gets dropped, which is acceptable for an autofill the user reviews.
- **Failure handling**:
  - Responses are always `200`, with exactly one of `{"match"}`, `{"candidates"}` or `{"error"}`.
  - Network failures and "not found" collapse into the same generic error. Exceptions are logged with `current_app.logger.warning` and never shown to the client.
  - Requests time out after 5s, so Open Library being slow or down never blocks manual entry.
- **User-Agent**: Open Library asks for an identifiable `User-Agent`. Its contact part comes from the `OPEN_LIBRARY_CONTACT` env var rather than being hardcoded.
- **Covers**:
  - Cover images use Open Library's `L` size (301×500); `M` looks soft at the app's display sizes.
  - `search.json` groups results by work, so a candidate's default cover is an arbitrary edition. The covers endpoint fetches `/works/{work_key}/editions.json` (limit 200) and keeps English editions (or ones with no language tag) that have real cover art, returning up to 12.
  - The public API has no edition-level popularity signal, so this is the best proxy available.
  - Each cover is paired with its *own* edition's ISBN (ISBN-13, falling back to ISBN-10), so picking a cover never mismatches it with another edition's ISBN.
- **Input validation**: the client-supplied `work_key` must match `/works/OL\d+W` before it's put into the outbound URL.
- Picking a result always overwrites the title/author/cover/ISBN fields; there's no "fill blanks only" mode.
