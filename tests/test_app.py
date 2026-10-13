from app.config import _normalize_db_uri
from app.extensions import db
from app.models import Invite, Member
from conftest import login, make_member


def test_home_redirects_anonymous_to_login(client):
    assert client.get("/").headers["Location"].startswith("/auth/login")


def test_home_redirects_member_to_books(client):
    login(client, make_member("alice"))
    assert client.get("/").headers["Location"] == "/books/"


def test_create_invite_cli(app):
    result = app.test_cli_runner().invoke(args=["create-invite"])
    assert result.exit_code == 0
    invite = Invite.query.one()
    assert f"Invite token: {invite.token}" in result.output
    assert f"/auth/register/{invite.token}" in result.output


def test_normalize_db_uri():
    # Some Postgres hosts hand out postgres:// URLs, which SQLAlchemy 1.4+ rejects.
    assert _normalize_db_uri("postgres://u:p@host/db") == "postgresql://u:p@host/db"
    assert _normalize_db_uri("postgresql://u:p@host/db") == "postgresql://u:p@host/db"
    assert _normalize_db_uri("sqlite:///x.db") == "sqlite:///x.db"
    assert _normalize_db_uri(None) is None


def test_route_that_forgets_to_commit_is_caught(app, client):
    # Guards conftest's _discard_uncommitted: the test and the request share one db.session,
    # so without it an uncommitted change would still be visible to the test's assertions.
    alice = make_member("alice")

    def forgetful_rename():
        db.session.get(Member, alice.id).display_name = "Renamed"  # no commit
        return ""

    app.add_url_rule("/_test/forgetful-rename", view_func=forgetful_rename)
    client.get("/_test/forgetful-rename")
    assert Member.query.filter_by(display_name="Renamed").first() is None
    assert db.session.get(Member, alice.id).display_name == "alice"
