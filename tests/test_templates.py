"""Rendered-HTML checks. Most route tests assert on template context, but some rules live in
the templates themselves -- detail.html re-implements _can_manage inline, the rating card's
edit/delete buttons are gated by `own=True`, and destructive forms rely on data-confirm --
so these guard against the template drifting from the route."""
import pytest

from app.models import Invite
from conftest import login, make_book, make_member, make_rating


def html(resp):
    return resp.get_data(as_text=True)


# --- permission-gated controls -------------------------------------------------------------

@pytest.mark.parametrize("viewer,can_manage", [("picker", True), ("admin", True), ("other", False)])
def test_book_manage_controls_match_can_manage(client, viewer, can_manage):
    picker = make_member("picker")
    users = {"picker": picker, "admin": make_member("admin", is_admin=True), "other": make_member("other")}
    book = make_book(picker)
    login(client, users[viewer])

    page = html(client.get(f"/books/{book.id}"))
    assert (f'href="/books/{book.id}/edit"' in page) is can_manage
    assert (f'action="/books/{book.id}/delete"' in page) is can_manage


def test_only_own_rating_card_has_edit_and_delete(client):
    alice, bob = make_member("alice"), make_member("bob")
    book = make_book(alice)
    make_rating(book, bob, 3.0)
    login(client, alice)

    page = html(client.get(f"/books/{book.id}"))
    assert 'aria-label="Delete your rating"' not in page  # bob's card, viewed by alice

    make_rating(book, alice, 4.0)
    page = html(client.get(f"/books/{book.id}"))
    assert page.count('aria-label="Delete your rating"') == 1
    assert page.count('aria-label="Edit your rating"') == 1


def test_destructive_forms_ask_for_confirmation(client):
    admin = make_member("admin", is_admin=True)
    book = make_book(admin)
    make_rating(book, admin, 4.0)
    Invite.create()
    login(client, admin)

    detail = html(client.get(f"/books/{book.id}"))
    invites = html(client.get("/admin/invites"))
    for page, action in [
        (detail, f"/books/{book.id}/delete"),
        (detail, f"/books/{book.id}/rating/delete"),
        (invites, "/revoke"),
    ]:
        form_tag = next(tag for tag in page.split("<form")[1:] if action in tag.split(">")[0])
        assert "data-confirm=" in form_tag.split(">")[0], action


# --- escaping ------------------------------------------------------------------------------

PAYLOAD = "<script>alert(1)</script>"


def test_user_content_is_escaped(client):
    alice = make_member("alice", display_name=PAYLOAD)
    book = make_book(alice, name=PAYLOAD, author=PAYLOAD)
    make_rating(book, alice, 4.0, comment=PAYLOAD)
    login(client, alice)

    for url in ["/books/", "/books/?view=grid", f"/books/{book.id}", "/members/", f"/members/{alice.id}"]:
        page = html(client.get(url))
        assert PAYLOAD not in page, url
        assert "&lt;script&gt;" in page, url
