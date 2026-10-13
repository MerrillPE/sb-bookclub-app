from datetime import date

import pytest
from flask import g, request_started, request_tearing_down, template_rendered
from sqlalchemy import DateTime, event
from sqlalchemy.orm import Session

from app import create_app
from app.extensions import db
from app.models import Book, BookStatus, Member, Rating


def _forget_cached_user(sender, **extra):
    # The fixtures below hold one app context open for the whole test, and the test client
    # reuses it for every request -- so Flask-Login's per-request user cache (g._login_user)
    # would otherwise carry over between requests, and even between clients. Clearing it makes
    # each request load its user from its own session cookie, like a real request would.
    g.pop("_login_user", None)


def _discard_uncommitted(sender, **extra):
    # Same shared-context problem, for the database: the test and every request share one
    # db.session, so a route that changed data but forgot db.session.commit() would still
    # look right to the test's assertions. In production that change dies with the request's
    # session -- rolling back here makes the test see what the database actually kept.
    db.session.rollback()


def _make_app(**overrides):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
    }
    config.update(overrides)
    app = create_app(test_config=config)
    request_started.connect(_forget_cached_user, app)
    request_tearing_down.connect(_discard_uncommitted, app)
    return app


@pytest.fixture
def app():
    app = _make_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def csrf_app():
    app = _make_app(WTF_CSRF_ENABLED=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def block_open_library(monkeypatch):
    """No test may reach the real Open Library -- tests that need it patch requests.get themselves."""
    def _blocked(*args, **kwargs):
        raise AssertionError("Unexpected outbound HTTP call in tests")
    monkeypatch.setattr("app.books.routes.requests.get", _blocked)


@event.listens_for(Session, "before_flush")
def _reject_aware_datetimes(session, flush_context, instances):
    """Enforce the naive-UTC convention (see _naive_utcnow in app/models.py). SQLite silently
    drops tzinfo, so without this an aware datetime would only misbehave on Postgres."""
    for obj in list(session.new) + list(session.dirty):
        for column in obj.__table__.columns:
            if isinstance(column.type, DateTime):
                value = getattr(obj, column.key, None)
                assert value is None or value.tzinfo is None, (
                    f"{type(obj).__name__}.{column.key} is timezone-aware; use _naive_utcnow()"
                )


@pytest.fixture
def captured_templates(app):
    """List of (template_name, context) for every template rendered during the test."""
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template.name, context))

    template_rendered.connect(record, app)
    yield recorded
    template_rendered.disconnect(record, app)


# --- factories -----------------------------------------------------------------------------

def make_member(username, password="password123", is_admin=False, display_name=None):
    member = Member(username=username, display_name=display_name or username, is_admin=is_admin)
    member.set_password(password)
    db.session.add(member)
    db.session.commit()
    return member


def make_book(picked_by=None, name="A Book", author="Some Author", status=BookStatus.FINISHED,
              start=None, added_by=None):
    added_by = added_by or picked_by or make_member(f"adder{Member.query.count()}")
    book = Book(
        name=name,
        author=author,
        status=status,
        picked_by_id=picked_by.id if picked_by else None,
        added_by_id=added_by.id,
        reading_start_date=start,
    )
    db.session.add(book)
    db.session.commit()
    return book


def make_rating(book, member, score, comment=None):
    rating = Rating(book_id=book.id, member_id=member.id, score=score, comment=comment)
    db.session.add(rating)
    db.session.commit()
    return rating


def login(client, member, password="password123"):
    return client.post("/auth/login", data={"username": member.username, "password": password})


def d(year, month=1, day=1):
    return date(year, month, day)
