"""Action-only buttons (delete/revoke/reset) rely on fieldless FlaskForms for CSRF protection --
there's no app-wide CSRFProtect, so these are the only thing stopping a cross-site POST."""
import pytest

from app.models import Book, Invite, PasswordReset, Rating
from conftest import make_book, make_member, make_rating


@pytest.fixture
def client(csrf_app):
    return csrf_app.test_client()


def login_without_csrf(client, member):
    # The login form itself is CSRF-protected too, so log in by writing the session directly.
    with client.session_transaction() as session:
        session["_user_id"] = str(member.id)
        session["_fresh"] = True


def test_login_rejects_missing_token(client):
    make_member("alice")
    resp = client.post("/auth/login", data={"username": "alice", "password": "password123"})
    assert resp.status_code == 200  # form re-rendered, not logged in
    with client.session_transaction() as session:
        assert "_user_id" not in session


def test_delete_book_requires_token(client):
    alice = make_member("alice")
    book = make_book(alice)
    login_without_csrf(client, alice)
    assert client.post(f"/books/{book.id}/delete").status_code == 400
    assert Book.query.count() == 1


def test_delete_rating_requires_token(client):
    alice = make_member("alice")
    make_rating(make_book(alice), alice, 4.0)
    login_without_csrf(client, alice)
    assert client.post(f"/books/{Book.query.one().id}/rating/delete").status_code == 400
    assert Rating.query.count() == 1


def test_revoke_invite_requires_token(client):
    login_without_csrf(client, make_member("admin", is_admin=True))
    invite = Invite.create()
    assert client.post(f"/admin/invites/{invite.id}/revoke").status_code == 400
    assert Invite.query.count() == 1


def test_generate_reset_requires_token(client):
    login_without_csrf(client, make_member("admin", is_admin=True))
    alice = make_member("alice")
    assert client.post(f"/admin/members/{alice.id}/reset").status_code == 400
    assert PasswordReset.query.count() == 0
