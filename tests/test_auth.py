from datetime import timedelta

import pytest

from app.extensions import db
from app.models import Invite, Member, PasswordReset, _naive_utcnow
from conftest import login, make_member


def logged_in_user_id(client):
    with client.session_transaction() as session:
        return session.get("_user_id")


# --- login ---------------------------------------------------------------------------------

def test_login_success_redirects_home(client):
    alice = make_member("alice")
    resp = login(client, alice)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"
    assert logged_in_user_id(client) == str(alice.id)


def test_login_wrong_password(client):
    alice = make_member("alice")
    resp = client.post("/auth/login", data={"username": "alice", "password": "nope"})
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data
    assert logged_in_user_id(client) is None


def test_login_page_redirects_when_already_logged_in(client):
    login(client, make_member("alice"))
    assert client.get("/auth/login").status_code == 302


@pytest.mark.parametrize("url", [
    "/books/", "/books/add", "/members/", "/admin/invites", "/auth/logout",
    "/books/api/lookup?title=Dune", "/books/api/lookup/covers?work=/works/OL1W",
])
def test_login_required(client, url):
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/auth/login")


# --- register ------------------------------------------------------------------------------

REGISTRATION = {"username": "newbie", "password": "password123", "confirm_password": "password123"}


def test_register_with_unknown_token(client):
    resp = client.get("/auth/register/no-such-token", follow_redirects=True)
    assert b"Invalid invite link" in resp.data


def test_register_with_used_token(client):
    invite = Invite.create()
    invite.used_at = _naive_utcnow()
    db.session.commit()
    resp = client.get(f"/auth/register/{invite.token}", follow_redirects=True)
    assert b"already been used" in resp.data


def test_register_with_expired_token(client):
    invite = Invite.create(expires_at=_naive_utcnow() - timedelta(minutes=1))
    resp = client.get(f"/auth/register/{invite.token}", follow_redirects=True)
    assert b"has expired" in resp.data


def test_register_success(client):
    invite = Invite.create()
    resp = client.post(f"/auth/register/{invite.token}", data=REGISTRATION)
    assert resp.status_code == 302

    member = Member.query.filter_by(username="newbie").one()
    assert member.display_name == "newbie"
    assert member.check_password("password123")
    assert db.session.get(Invite, invite.id).used_at is not None
    assert logged_in_user_id(client) == str(member.id)


def test_register_token_cannot_be_reused(client):
    invite = Invite.create()
    client.post(f"/auth/register/{invite.token}", data=REGISTRATION)
    client.get("/auth/logout")
    resp = client.post(f"/auth/register/{invite.token}", data={**REGISTRATION, "username": "second"})
    assert resp.status_code == 302
    assert Member.query.filter_by(username="second").first() is None


@pytest.mark.parametrize("overrides,message", [
    ({"username": "alice"}, b"Username is already taken"),
    ({"confirm_password": "different1"}, b"Passwords must match"),
    ({"password": "short", "confirm_password": "short"}, b"at least 8"),
])
def test_register_validation_errors(client, overrides, message):
    make_member("alice")
    invite = Invite.create()
    resp = client.post(f"/auth/register/{invite.token}", data={**REGISTRATION, **overrides})
    assert resp.status_code == 200
    assert message in resp.data
    assert db.session.get(Invite, invite.id).used_at is None


# --- password reset ------------------------------------------------------------------------

RESET = {"password": "brand-new-pw", "confirm_password": "brand-new-pw"}


def test_reset_with_unknown_token(client):
    resp = client.get("/auth/reset-password/nope", follow_redirects=True)
    assert b"Invalid password reset link" in resp.data


def test_reset_with_used_token(client):
    reset = PasswordReset.create(make_member("alice"))
    reset.used_at = _naive_utcnow()
    db.session.commit()
    resp = client.get(f"/auth/reset-password/{reset.token}", follow_redirects=True)
    assert b"already been used" in resp.data


def test_reset_with_expired_token(client):
    reset = PasswordReset.create(make_member("alice"))
    reset.expires_at = _naive_utcnow() - timedelta(seconds=1)
    db.session.commit()
    resp = client.get(f"/auth/reset-password/{reset.token}", follow_redirects=True)
    assert b"has expired" in resp.data


def test_reset_success(client):
    alice = make_member("alice", password="old-password")
    reset = PasswordReset.create(alice)
    resp = client.post(f"/auth/reset-password/{reset.token}", data=RESET)
    assert resp.status_code == 302
    assert logged_in_user_id(client) == str(alice.id)

    db.session.refresh(alice)
    assert alice.check_password("brand-new-pw")
    assert not alice.check_password("old-password")
    assert db.session.get(PasswordReset, reset.id).used_at is not None


def test_login_does_not_leak_to_other_clients(app, client):
    # Guards conftest's _forget_cached_user: without it, a client with no session cookie
    # would be treated as whoever logged in last.
    login(client, make_member("alice"))
    assert client.get("/books/").status_code == 200
    assert app.test_client().get("/books/").status_code == 302


def test_login_unknown_username(client):
    resp = client.post("/auth/login", data={"username": "ghost", "password": "password123"})
    assert b"Invalid username or password" in resp.data
    assert logged_in_user_id(client) is None


def test_logout_ends_session(client):
    login(client, make_member("alice"))
    client.get("/auth/logout")
    assert logged_in_user_id(client) is None
    assert client.get("/books/").status_code == 302


@pytest.mark.parametrize("data,message", [
    ({"password": "brand-new-pw", "confirm_password": "different-pw"}, b"Passwords must match"),
    ({"password": "short", "confirm_password": "short"}, b"at least 8"),
])
def test_reset_validation_errors_leave_token_usable(client, data, message):
    alice = make_member("alice", password="old-password")
    reset = PasswordReset.create(alice)
    resp = client.post(f"/auth/reset-password/{reset.token}", data=data)
    assert resp.status_code == 200
    assert message in resp.data
    assert db.session.get(PasswordReset, reset.id).used_at is None
    db.session.refresh(alice)
    assert alice.check_password("old-password")
