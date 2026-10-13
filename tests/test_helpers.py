from datetime import date

import pytest

from app.books.routes import (
    _club_stats, _group_by_year, _is_valid_isbn, _open_library_candidate, _sort_books,
)
from app.members.routes import _others_average
from app.models import BookStatus
from conftest import d, make_book, make_member, make_rating


@pytest.mark.parametrize("isbn,valid", [
    ("0306406152", True),
    ("080442957X", True),
    ("080442957x", True),
    ("9780306406157", True),
    ("0306406153", False),      # bad ISBN-10 checksum
    ("9780306406158", False),   # bad ISBN-13 checksum
    ("030640615", False),       # wrong length
    ("97803064061X7", False),   # X only allowed at the end of an ISBN-10
    ("abcdefghij", False),
])
def test_is_valid_isbn(isbn, valid):
    assert _is_valid_isbn(isbn) is valid


@pytest.fixture
def books(app):
    alice, bob = make_member("alice"), make_member("bob")
    old = make_book(alice, name="Old", status=BookStatus.FINISHED, start=d(2023))
    new = make_book(alice, name="New", status=BookStatus.FINISHED, start=d(2025))
    current = make_book(alice, name="Current", status=BookStatus.CURRENTLY_READING, start=d(2026))
    tbr = make_book(alice, name="Undated", status=BookStatus.TO_BE_READ)
    dnf = make_book(alice, name="Dnf", status=BookStatus.ABANDONED, start=d(2024))
    make_rating(old, alice, 5.0)
    make_rating(new, alice, 2.0)
    make_rating(new, bob, 3.0)
    return {"old": old, "new": new, "current": current, "tbr": tbr, "dnf": dnf}


def names(books):
    return [b.name for b in books]


def test_sort_by_start_date_puts_undated_last(books):
    assert names(_sort_books(list(books.values()), "start_date")) == ["Current", "New", "Dnf", "Old", "Undated"]


def test_unknown_sort_falls_back_to_start_date(books):
    all_books = list(books.values())
    assert _sort_books(all_books, "bogus") == _sort_books(all_books, "start_date")


def test_sort_by_status_follows_enum_order(books):
    statuses = [b.status for b in _sort_books(list(books.values()), "status")]
    order = list(BookStatus)
    assert statuses == sorted(statuses, key=order.index)


def test_sort_by_rating_unrated_last(books):
    assert names(_sort_books(list(books.values()), "rating"))[:2] == ["Old", "New"]


def test_reading_first_groups_by_status_then_date(books):
    assert names(_sort_books(list(books.values()), "reading_first")) == ["Current", "Undated", "New", "Old", "Dnf"]


def test_group_by_year(books):
    ordered = _sort_books(list(books.values()), "start_date")
    groups = _group_by_year(ordered)
    assert [(year, names(bs)) for year, bs in groups] == [
        (2026, ["Current"]), (2025, ["New"]), (2024, ["Dnf"]), (2023, ["Old"]), (None, ["Undated"]),
    ]


def test_club_stats_empty():
    assert _club_stats([]) == {"finished": 0, "since": None, "avg_rating": None, "top_rated": None}


def test_club_stats(books):
    stats = _club_stats(list(books.values()))
    assert stats["finished"] == 2
    assert stats["since"] == 2023
    assert stats["avg_rating"] == pytest.approx((5.0 + 2.5) / 2)
    assert stats["top_rated"] is books["old"]


def test_open_library_candidate_takes_first_author_only():
    candidate = _open_library_candidate({
        "title": "Watchmen", "author_name": ["Alan Moore", "Dave Gibbons"], "cover_i": 42,
        "isbn": ["111", "222"], "key": "/works/OL1W", "first_publish_year": 1987,
    })
    assert candidate == {
        "title": "Watchmen", "author": "Alan Moore", "year": 1987,
        "cover_url": "https://covers.openlibrary.org/b/id/42-L.jpg",
        "isbn": "111", "work_key": "/works/OL1W",
    }


def test_open_library_candidate_handles_missing_fields_and_fallback_isbn():
    candidate = _open_library_candidate({"isbn": ["111"]}, fallback_isbn="978-0")
    assert candidate["cover_url"] == ""
    assert candidate["author"] == ""
    assert candidate["isbn"] == "978-0"


def test_others_average_excludes_own_score(books):
    new = books["new"]
    alice_rating = next(r for r in new.ratings if r.member.username == "alice")
    assert _others_average(alice_rating) == 3.0
    assert _others_average(books["old"].ratings[0]) is None


def test_nice_date_filter(app):
    nice_date = app.jinja_env.filters["nice_date"]
    assert nice_date(date(2026, 9, 3)) == "Sep 3, 2026"
    assert nice_date(None) == ""


def test_title_seed_filter(app):
    title_seed = app.jinja_env.filters["title_seed"]
    assert title_seed("ab") == ord("a") + ord("b")
    assert title_seed(None) == 0
