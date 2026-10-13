import pytest

from app.extensions import db
from conftest import login, make_book, make_member, make_rating


@pytest.fixture
def alice(client):
    alice = make_member("alice")
    login(client, alice)
    return alice


def context_for(captured_templates, name):
    return next(ctx for tmpl, ctx in reversed(captured_templates) if tmpl == name)


def test_directory_excludes_admins(client, alice, captured_templates):
    make_member("admin", is_admin=True)
    client.get("/members/")
    cards = context_for(captured_templates, "members/index.html")["cards"]
    assert [c["member"].username for c in cards] == ["alice"]


def test_directory_card_stats(client, alice, captured_templates):
    first, second = make_book(alice, name="One"), make_book(alice, name="Two")
    make_rating(first, alice, 4.0)
    make_rating(second, alice, 3.0)
    client.get("/members/")
    card = context_for(captured_templates, "members/index.html")["cards"][0]
    assert len(card["picks"]) == 2
    assert card["review_count"] == 2
    assert card["avg_given"] == 3.5


def test_admin_profile_is_404(client, alice):
    admin = make_member("admin", is_admin=True)
    assert client.get(f"/members/{admin.id}").status_code == 404


def test_rename_own_display_name_strips_whitespace(client, alice):
    resp = client.post(f"/members/{alice.id}", data={"display_name": "  Alice A.  "})
    assert resp.status_code == 302
    db.session.refresh(alice)
    assert alice.display_name == "Alice A."


def test_blank_display_name_rejected(client, alice):
    resp = client.post(f"/members/{alice.id}", data={"display_name": "   "})
    assert resp.status_code == 200
    db.session.refresh(alice)
    assert alice.display_name == "alice"


def test_cannot_rename_someone_else(client, alice):
    bob = make_member("bob")
    assert client.post(f"/members/{bob.id}", data={"display_name": "Hacked"}).status_code == 403
    db.session.refresh(bob)
    assert bob.display_name == "bob"


def test_profile_hides_edit_form_for_others(client, alice, captured_templates):
    bob = make_member("bob")
    client.get(f"/members/{bob.id}")
    assert context_for(captured_templates, "members/profile.html")["form"] is None


def test_taste_delta_positive_for_generous_scorer(client, alice, captured_templates):
    bob = make_member("bob")
    first, second = make_book(bob, name="One"), make_book(bob, name="Two")
    make_rating(first, alice, 5.0)
    make_rating(first, bob, 3.0)
    make_rating(second, alice, 4.0)
    make_rating(second, bob, 3.0)

    client.get(f"/members/{alice.id}")
    ctx = context_for(captured_templates, "members/profile.html")
    assert ctx["taste_delta"] == 1.5
    assert ctx["avg_given"] == 4.5

    client.get(f"/members/{bob.id}")
    ctx = context_for(captured_templates, "members/profile.html")
    assert ctx["taste_delta"] == -1.5
    assert ctx["picks_avg"] == pytest.approx((4.0 + 3.5) / 2)


def test_taste_delta_none_without_overlap(client, alice, captured_templates):
    make_rating(make_book(alice), alice, 4.0)
    client.get(f"/members/{alice.id}")
    assert context_for(captured_templates, "members/profile.html")["taste_delta"] is None
