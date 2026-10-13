import pytest

from app.extensions import db
from app.models import Book, BookStatus, Rating
from conftest import d, login, make_book, make_member, make_rating


@pytest.fixture
def alice(client):
    alice = make_member("alice")
    login(client, alice)
    return alice


def context_for(captured_templates, name):
    return next(ctx for tmpl, ctx in reversed(captured_templates) if tmpl == name)


BOOK_FORM = {"title": "Dune", "author": "Frank Herbert", "status": "TO_BE_READ", "picked_by": ""}


# --- add / edit / delete -------------------------------------------------------------------

def test_add_book_member_is_always_picker(client, alice):
    bob = make_member("bob")
    resp = client.post("/books/add", data={**BOOK_FORM, "picked_by": str(bob.id)})
    book = Book.query.one()
    assert resp.headers["Location"] == f"/books/{book.id}"
    assert book.name == "Dune"
    assert book.picked_by_id == alice.id
    assert book.added_by_id == alice.id
    assert book.status == BookStatus.TO_BE_READ


@pytest.mark.parametrize("picked", ["bob", None])
def test_add_book_admin_chooses_picker(client, picked):
    admin = make_member("admin", is_admin=True)
    bob = make_member("bob")
    login(client, admin)
    client.post("/books/add", data={**BOOK_FORM, "picked_by": str(bob.id) if picked else ""})
    assert Book.query.one().picked_by_id == (bob.id if picked else None)


def test_add_book_requires_title_and_author(client, alice):
    resp = client.post("/books/add", data={**BOOK_FORM, "title": "", "author": ""})
    assert resp.status_code == 200
    assert Book.query.count() == 0


def test_edit_form_prefills_mismatched_fields(client, alice, captured_templates):
    # Guards the WTForms obj= gotcha: title<-name, status<-enum name, picked_by<-picked_by_id.
    book = make_book(alice, name="Dune", status=BookStatus.CURRENTLY_READING)
    client.get(f"/books/{book.id}/edit")
    form = context_for(captured_templates, "books/form.html")["form"]
    assert form.title.data == "Dune"
    assert form.status.data == "CURRENTLY_READING"
    assert form.picked_by.data == alice.id


def test_picker_can_edit(client, alice):
    book = make_book(alice, name="Dune")
    client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, "title": "Dune Messiah", "status": "FINISHED"})
    db.session.refresh(book)
    assert book.name == "Dune Messiah"
    assert book.status == BookStatus.FINISHED


def test_admin_can_edit_others_book(client):
    bob = make_member("bob")
    book = make_book(bob)
    login(client, make_member("admin", is_admin=True))
    client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, "picked_by": str(bob.id)})
    db.session.refresh(book)
    assert book.name == "Dune"
    assert book.picked_by_id == bob.id


def test_non_picker_cannot_edit(client, alice):
    book = make_book(make_member("bob"))
    assert client.get(f"/books/{book.id}/edit").status_code == 403
    assert client.post(f"/books/{book.id}/edit", data=BOOK_FORM).status_code == 403


def test_edit_missing_book_404(client, alice):
    assert client.get("/books/999/edit").status_code == 404


def test_delete_book(client, alice):
    book = make_book(alice)
    resp = client.post(f"/books/{book.id}/delete")
    assert resp.headers["Location"] == "/books/"
    assert Book.query.count() == 0


def test_cannot_delete_book_with_ratings(client, alice):
    book = make_book(alice)
    make_rating(book, alice, 4.0)
    resp = client.post(f"/books/{book.id}/delete", follow_redirects=True)
    assert b"has ratings" in resp.data
    assert Book.query.count() == 1


def test_non_picker_cannot_delete(client, alice):
    book = make_book(make_member("bob"))
    assert client.post(f"/books/{book.id}/delete").status_code == 403
    assert Book.query.count() == 1


# --- ratings -------------------------------------------------------------------------------

def test_rating_upsert(client, alice):
    book = make_book(alice, status=BookStatus.FINISHED)
    client.post(f"/books/{book.id}", data={"score": "4.0", "comment": "Great"})
    client.post(f"/books/{book.id}", data={"score": "2.5", "comment": "On reflection, meh"})
    rating = Rating.query.one()
    assert rating.score == 2.5
    assert rating.comment == "On reflection, meh"


def test_cannot_rate_unfinished_book(client, alice):
    book = make_book(alice, status=BookStatus.CURRENTLY_READING)
    resp = client.post(f"/books/{book.id}", data={"score": "4.0"}, follow_redirects=True)
    assert b"only be submitted for finished books" in resp.data
    assert Rating.query.count() == 0


def test_rating_comment_max_length(client, alice):
    book = make_book(alice)
    client.post(f"/books/{book.id}", data={"score": "4.0", "comment": "x" * 501})
    assert Rating.query.count() == 0


def test_rating_rejects_out_of_range_score(client, alice):
    book = make_book(alice)
    client.post(f"/books/{book.id}", data={"score": "6.0"})
    assert Rating.query.count() == 0


def test_delete_own_rating(client, alice):
    book = make_book(alice)
    make_rating(book, alice, 4.0)
    client.post(f"/books/{book.id}/rating/delete")
    assert Rating.query.count() == 0


def test_delete_rating_only_touches_own(client, alice):
    bob = make_member("bob")
    book = make_book(bob)
    make_rating(book, bob, 4.0)
    assert client.post(f"/books/{book.id}/rating/delete").status_code == 404
    assert Rating.query.count() == 1


# --- detail page context -------------------------------------------------------------------

def test_prev_next_navigation(client, alice, captured_templates):
    oldest = make_book(alice, name="Oldest", start=d(2020))
    middle = make_book(alice, name="Middle", start=d(2022))
    newest = make_book(alice, name="Newest", start=d(2024))

    expected = {oldest: (middle, None), middle: (newest, oldest), newest: (None, middle)}
    for book, (newer, older) in expected.items():
        client.get(f"/books/{book.id}")
        ctx = context_for(captured_templates, "books/detail.html")
        assert (ctx["newer_book"], ctx["older_book"]) == (newer, older), book.name


def test_detail_distribution_and_unrated_members(client, alice, captured_templates):
    bob, carol = make_member("bob"), make_member("carol")
    admin = make_member("admin", is_admin=True)
    book = make_book(alice)
    make_rating(book, alice, 4.5)
    make_rating(book, bob, 4.0)
    make_rating(book, admin, 1.0)

    client.get(f"/books/{book.id}")
    ctx = context_for(captured_templates, "books/detail.html")
    assert ctx["distribution"] == [(5, 0), (4, 2), (3, 0), (2, 0), (1, 1)]
    assert ctx["unrated_members"] == [carol]
    assert ctx["rated_member_count"] == 2


def test_detail_missing_book_404(client, alice):
    assert client.get("/books/999").status_code == 404


# --- list page -----------------------------------------------------------------------------

def test_empty_club_shows_welcome(client, alice):
    assert b"Add your first book" in client.get("/books/").data


def test_default_list_is_sectioned_shelf(client, alice, captured_templates):
    current = make_book(alice, name="Current", status=BookStatus.CURRENTLY_READING)
    tbr = make_book(alice, name="Next", status=BookStatus.TO_BE_READ)
    done = make_book(alice, name="Done", status=BookStatus.FINISHED, start=d(2024))

    client.get("/books/")
    ctx = context_for(captured_templates, "books/list.html")
    assert ctx["sections"]["current"] == [current]
    assert ctx["sections"]["up_next"] == [tbr]
    assert ctx["sections"]["history"] == [(2024, [done])]
    assert ctx["stats"]["finished"] == 1


@pytest.mark.parametrize("query", ["?status=FINISHED", "?sort=rating", "?view=grid"])
def test_explicit_filter_or_sort_renders_flat_grid(client, alice, captured_templates, query):
    make_book(alice, status=BookStatus.FINISHED)
    client.get(f"/books/{query}")
    assert context_for(captured_templates, "books/list.html")["sections"] is None


def test_status_filter(client, alice, captured_templates):
    make_book(alice, name="Done", status=BookStatus.FINISHED)
    make_book(alice, name="Next", status=BookStatus.TO_BE_READ)
    client.get("/books/?status=TO_BE_READ")
    assert [b.name for b in context_for(captured_templates, "books/list.html")["books"]] == ["Next"]


def test_bogus_status_filter_is_ignored(client, alice, captured_templates):
    make_book(alice, name="Done", status=BookStatus.FINISHED)
    resp = client.get("/books/?status=NOPE")
    assert resp.status_code == 200
    assert len(context_for(captured_templates, "books/list.html")["books"]) == 1


# --- column-length limits ------------------------------------------------------------------
# SQLite ignores String(n) limits, but production Postgres raises on an over-length value --
# so the form has to reject it first, or the user gets a 500 instead of a validation error.

TOO_LONG = [
    ("title", 121), ("author", 121), ("cover_url", 256), ("isbn", 21),
]


@pytest.mark.parametrize("field,length", TOO_LONG)
def test_add_book_rejects_over_length_fields(client, alice, field, length):
    resp = client.post("/books/add", data={**BOOK_FORM, field: "x" * length})
    assert resp.status_code == 200
    assert Book.query.count() == 0


@pytest.mark.parametrize("field,length", TOO_LONG)
def test_edit_book_rejects_over_length_fields(client, alice, field, length):
    book = make_book(alice, name="Dune")
    resp = client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, field: "x" * length})
    assert resp.status_code == 200
    db.session.refresh(book)
    assert book.name == "Dune"


def test_book_fields_accept_max_length(client, alice):
    client.post("/books/add", data={
        **BOOK_FORM, "title": "t" * 120, "author": "a" * 120, "cover_url": "c" * 255, "isbn": "1" * 20,
    })
    assert Book.query.one().name == "t" * 120


# --- edit / delete edge cases --------------------------------------------------------------

def test_edit_book_member_cannot_reassign_picker(client, alice):
    bob = make_member("bob")
    book = make_book(alice)
    client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, "picked_by": str(bob.id)})
    db.session.refresh(book)
    assert book.picked_by_id == alice.id


def test_failed_edit_keeps_submitted_values(client, alice, captured_templates):
    # The GET-only prefill in edit_book() must not clobber what the user just submitted.
    book = make_book(alice, name="Dune")
    resp = client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, "title": "Dune Messiah", "author": ""})
    assert resp.status_code == 200
    assert context_for(captured_templates, "books/form.html")["form"].title.data == "Dune Messiah"
    db.session.refresh(book)
    assert book.name == "Dune"


def test_admin_can_delete_others_book(client):
    book = make_book(make_member("bob"))
    login(client, make_member("admin", is_admin=True))
    client.post(f"/books/{book.id}/delete")
    assert Book.query.count() == 0


def test_delete_missing_book_404(client, alice):
    assert client.post("/books/999/delete").status_code == 404


def test_rating_requires_score(client, alice):
    book = make_book(alice)
    resp = client.post(f"/books/{book.id}", data={"score": "", "comment": "No score"})
    assert resp.status_code == 200
    assert Rating.query.count() == 0


def test_rating_survives_unfinishing_book_and_can_still_be_deleted(client, alice):
    book = make_book(alice, status=BookStatus.FINISHED)
    make_rating(book, alice, 4.0)
    client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, "status": "CURRENTLY_READING"})
    assert Rating.query.count() == 1
    client.post(f"/books/{book.id}/rating/delete")
    assert Rating.query.count() == 0


def test_prev_next_with_undated_books_visits_every_book(client, alice, captured_templates):
    # Undated books all sort as date.min -- walking "older" from the newest must still reach
    # every book exactly once, with no skips or cycles.
    books = [make_book(alice, name=f"Undated {i}") for i in range(3)] + [make_book(alice, name="Dated", start=d(2024))]
    client.get(f"/books/{books[-1].id}")
    seen = [books[-1]]
    while (older := context_for(captured_templates, "books/detail.html")["older_book"]) is not None:
        seen.append(older)
        client.get(f"/books/{older.id}")
    assert sorted(b.id for b in seen) == sorted(b.id for b in books)


# --- reading dates -------------------------------------------------------------------------

def test_end_date_before_start_date_rejected(client, alice):
    resp = client.post("/books/add", data={**BOOK_FORM, "reading_start_date": "2026-03-10", "reading_end_date": "2026-03-09"})
    assert resp.status_code == 200
    assert b"End date can&#39;t be before the start date" in resp.data
    assert Book.query.count() == 0


def test_edit_end_date_before_start_date_rejected(client, alice):
    book = make_book(alice, start=d(2026, 3, 10))
    client.post(f"/books/{book.id}/edit", data={**BOOK_FORM, "reading_start_date": "2026-03-10", "reading_end_date": "2026-03-01"})
    db.session.refresh(book)
    assert book.reading_end_date is None


@pytest.mark.parametrize("start,end", [
    ("2026-03-10", "2026-03-10"),  # finished the same day
    ("2026-03-10", "2026-04-01"),
    ("", "2026-04-01"),            # end date alone has nothing to compare against
    ("2026-03-10", ""),
])
def test_valid_reading_dates_accepted(client, alice, start, end):
    client.post("/books/add", data={**BOOK_FORM, "reading_start_date": start, "reading_end_date": end})
    assert Book.query.count() == 1
