from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.invite_words import INVITE_WORDS
from app.models import BookStatus, Invite, PasswordReset, _generate_invite_token, _naive_utcnow
from conftest import make_book, make_member, make_rating


def test_invite_token_is_three_known_words():
    words = _generate_invite_token().split("-")
    assert len(words) == 3
    assert all(w in INVITE_WORDS for w in words)


def test_invite_without_expiry_is_pending(app):
    invite = Invite.create()
    assert not invite.is_expired
    assert invite.status_label == "Pending"


def test_invite_past_expiry_is_expired(app):
    invite = Invite.create(expires_at=_naive_utcnow() - timedelta(minutes=1))
    assert invite.is_expired
    assert invite.status_label == "Expired"


def test_used_label_wins_over_expired(app):
    invite = Invite.create(expires_at=_naive_utcnow() - timedelta(days=1))
    invite.used_at = _naive_utcnow()
    assert invite.status_label == "Used"


def test_password_reset_expires_in_24_hours(app):
    reset = PasswordReset.create(make_member("alice"))
    delta = reset.expires_at - _naive_utcnow()
    assert timedelta(hours=23, minutes=59) < delta <= timedelta(hours=24)
    assert reset.status_label == "Pending"


def test_password_reset_expired_and_used_labels(app):
    reset = PasswordReset.create(make_member("alice"))
    reset.expires_at = _naive_utcnow() - timedelta(seconds=1)
    assert reset.status_label == "Expired"
    reset.used_at = _naive_utcnow()
    assert reset.status_label == "Used"


def test_password_hashing(app):
    member = make_member("alice", password="correct-horse")
    assert member.password_hash != "correct-horse"
    assert member.check_password("correct-horse")
    assert not member.check_password("wrong")


def test_book_average_rating(app):
    alice, bob = make_member("alice"), make_member("bob")
    book = make_book(alice)
    assert book.average_rating is None
    make_rating(book, alice, 4.0)
    make_rating(book, bob, 3.0)
    assert book.average_rating == 3.5


def test_book_status_helpers(app):
    book = make_book(make_member("alice"), status=BookStatus.CURRENTLY_READING)
    assert book.status_label == "Currently Reading"
    assert not book.is_finished
    book.status = BookStatus.FINISHED
    assert book.is_finished


@pytest.mark.parametrize("score", [0.5, 5.5, 3.25])
def test_rating_score_check_constraint(app, score):
    alice = make_member("alice")
    book = make_book(alice)
    with pytest.raises(IntegrityError):
        make_rating(book, alice, score)
    db.session.rollback()


def test_one_rating_per_member_per_book(app):
    alice = make_member("alice")
    book = make_book(alice)
    make_rating(book, alice, 4.0)
    with pytest.raises(IntegrityError):
        make_rating(book, alice, 3.0)
    db.session.rollback()
