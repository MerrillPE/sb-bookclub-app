from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Invite, PasswordReset, _naive_utcnow
from conftest import login, make_member


@pytest.fixture
def admin(client):
    admin = make_member("admin", is_admin=True)
    login(client, admin)
    return admin


ADMIN_ROUTES = [
    ("get", "/admin/invites"),
    ("post", "/admin/invites"),
    ("post", "/admin/invites/1/revoke"),
    ("get", "/admin/members"),
    ("post", "/admin/members/1/reset"),
]


@pytest.mark.parametrize("method,url", ADMIN_ROUTES)
def test_non_admin_forbidden(client, method, url):
    login(client, make_member("alice"))
    assert getattr(client, method)(url).status_code == 403


@pytest.mark.parametrize("method,url", ADMIN_ROUTES)
def test_anonymous_redirected_to_login(client, method, url):
    resp = getattr(client, method)(url)
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/auth/login")


def test_create_invite_without_expiry(client, admin):
    client.post("/admin/invites", data={})
    invite = Invite.query.one()
    assert invite.expires_at is None
    assert invite.status_label == "Pending"


def test_create_invite_with_expiry(client, admin):
    expires = date.today() + timedelta(days=3)
    client.post("/admin/invites", data={"expires_at": expires.isoformat()})
    invite = Invite.query.one()
    assert invite.expires_at.date() == expires
    assert invite.expires_at.tzinfo is None  # naive UTC, per the _naive_utcnow() convention
    assert not invite.is_expired


def test_revoke_pending_invite(client, admin):
    invite = Invite.create()
    client.post(f"/admin/invites/{invite.id}/revoke")
    assert Invite.query.count() == 0


def test_cannot_revoke_used_invite(client, admin):
    invite = Invite.create()
    invite.used_at = _naive_utcnow()
    db.session.commit()
    resp = client.post(f"/admin/invites/{invite.id}/revoke", follow_redirects=True)
    assert b"already been used" in resp.data
    assert Invite.query.count() == 1


def test_revoke_missing_invite_404(client, admin):
    assert client.post("/admin/invites/999/revoke").status_code == 404


def test_invite_list_shows_pending_first(client, admin, captured_templates):
    used = Invite.create()
    used.used_at = _naive_utcnow()
    expired = Invite.create(expires_at=_naive_utcnow() - timedelta(days=1))
    pending = Invite.create()
    db.session.commit()

    client.get("/admin/invites")
    _, context = captured_templates[-1]
    assert context["invites"][0] is pending
    assert {i.id for i in context["invites"][1:]} == {used.id, expired.id}


def test_generate_reset_replaces_previous_unused(client, admin):
    alice = make_member("alice")
    first = PasswordReset.create(alice)
    first_token = first.token

    client.post(f"/admin/members/{alice.id}/reset")
    resets = PasswordReset.query.filter_by(member_id=alice.id).all()
    assert len(resets) == 1
    assert resets[0].token != first_token


def test_generate_reset_keeps_used_history(client, admin):
    alice = make_member("alice")
    used = PasswordReset.create(alice)
    used.used_at = _naive_utcnow()
    db.session.commit()

    client.post(f"/admin/members/{alice.id}/reset")
    assert PasswordReset.query.filter_by(member_id=alice.id).count() == 2


def test_members_page_lists_pending_reset(client, admin, captured_templates):
    alice = make_member("alice")
    client.post(f"/admin/members/{alice.id}/reset")
    client.get("/admin/members")
    _, context = captured_templates[-1]
    assert context["pending_resets"][alice.id].member_id == alice.id


def test_generate_reset_for_missing_member_404(client, admin):
    assert client.post("/admin/members/999/reset").status_code == 404
    assert PasswordReset.query.count() == 0


def test_members_page_hides_expired_reset(client, admin, captured_templates):
    alice = make_member("alice")
    reset = PasswordReset.create(alice)
    reset.expires_at = _naive_utcnow() - timedelta(seconds=1)
    db.session.commit()
    client.get("/admin/members")
    _, context = captured_templates[-1]
    assert alice.id not in context["pending_resets"]


@pytest.mark.parametrize("days_ago", [1, 365])
def test_create_invite_rejects_past_expiry(client, admin, days_ago):
    expires = _naive_utcnow().date() - timedelta(days=days_ago)
    resp = client.post("/admin/invites", data={"expires_at": expires.isoformat()})
    assert resp.status_code == 200
    assert b"must be in the future" in resp.data
    assert Invite.query.count() == 0


def test_create_invite_allows_expiry_today(client, admin):
    # The invite stays valid until the end of the chosen day (UTC), so "today" is still future.
    client.post("/admin/invites", data={"expires_at": _naive_utcnow().date().isoformat()})
    invite = Invite.query.one()
    assert not invite.is_expired


@pytest.mark.parametrize("method", ["get", "post"])
def test_expiry_picker_greys_out_past_days(client, admin, method):
    # The min attribute is only a browser hint (CreateInviteForm still validates), but it has
    # to match the server rule -- today in UTC -- including when a failed POST re-renders.
    data = {"expires_at": "2000-01-01"} if method == "post" else None
    page = getattr(client, method)("/admin/invites", data=data).get_data(as_text=True)
    assert f'min="{_naive_utcnow().date().isoformat()}"' in page
