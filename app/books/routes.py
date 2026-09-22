import os
import re
from datetime import date

import requests
from flask import (
    Blueprint, abort, current_app, flash, jsonify, redirect, render_template,
    request, url_for
)

from flask_login import login_required, current_user

from app.models import Book, Rating, Member, BookStatus
from app.extensions import db
from app.books.forms import BookForm, RatingForm, DeleteForm


bp = Blueprint("books", __name__, url_prefix="/books")

_OPEN_LIBRARY_HEADERS = {
    "User-Agent": "sb-bookclub-app/1.0 ({})".format(
        os.environ.get("OPEN_LIBRARY_CONTACT", "no-contact-configured")
    )
}


def _picked_by_choices():
    return [("", "- None -")] + [
        (m.id, m.display_name) for m in Member.query.filter_by(is_admin=False).all()
    ]


def _can_manage(book):
    return current_user.id == book.picked_by_id or current_user.is_admin


_LIST_STATUS_ORDER = [BookStatus.CURRENTLY_READING, BookStatus.TO_BE_READ, BookStatus.FINISHED, BookStatus.ABANDONED]


def _sort_books(all_books, sort):
    if sort == "status":
        order = {s: i for i, s in enumerate(BookStatus)}
        return sorted(all_books, key=lambda b: order[b.status])
    if sort == "rating":
        return sorted(all_books, key=lambda b: b.average_rating or 0, reverse=True)
    if sort == "reading_first":
        order = {s: i for i, s in enumerate(_LIST_STATUS_ORDER)}
        by_date = sorted(all_books, key=lambda b: b.reading_start_date or date.min, reverse=True)
        return sorted(by_date, key=lambda b: order[b.status])  # stable sort preserves date order within each status group
    # "start_date" (default): most recently started first. created_at ("date added") is
    # deliberately not offered as a frontend sort — it's record-keeping metadata (when the
    # row was created), not something a reader cares about; reading_start_date is.
    return sorted(all_books, key=lambda b: b.reading_start_date or date.min, reverse=True)


@bp.route("/")
@login_required
def index():
    status_filter = request.args.get("status", "")
    sort = request.args.get("sort", "reading_first")

    query = Book.query
    if status_filter in BookStatus.__members__:
        query = query.filter_by(status=BookStatus[status_filter])

    all_books = _sort_books(query.all(), sort)

    return render_template(
        "books/list.html",
        books=all_books,
        status_choices=[(s.name, s.value.replace("_", " ").title()) for s in BookStatus],
        selected_status=status_filter,
        selected_sort=sort,
    )


def _is_valid_isbn(digits):
    if len(digits) == 10:
        if not re.fullmatch(r"\d{9}[\dXx]", digits):
            return False
        total = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(digits))
        return total % 11 == 0
    if len(digits) == 13:
        if not digits.isdigit():
            return False
        total = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(digits))
        return total % 10 == 0
    return False


def _open_library_candidate(doc, fallback_isbn=""):
    cover_i = doc.get("cover_i")
    return {
        "title": doc.get("title", ""),
        "author": (doc.get("author_name") or [""])[0],
        "year": doc.get("first_publish_year"),
        "cover_url": f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg" if cover_i else "",
        "isbn": fallback_isbn or (doc.get("isbn") or [""])[0],
        "work_key": doc.get("key"),
    }


@bp.route("/api/lookup")
@login_required
def lookup_book():
    isbn = request.args.get("isbn", "").strip()
    title = request.args.get("title", "").strip()
    author = request.args.get("author", "").strip()

    if not isbn and not title and not author:
        return jsonify({"error": "No match found"})

    normalized_isbn = re.sub(r"[\s-]", "", isbn) if isbn else ""
    if normalized_isbn and not _is_valid_isbn(normalized_isbn):
        return jsonify({"error": "No match found"})

    params = {"limit": 5, "fields": "title,author_name,cover_i,first_publish_year,isbn,key"}
    if normalized_isbn:
        params["isbn"] = normalized_isbn
    else:
        if title:
            params["title"] = title
        if author:
            params["author"] = author

    try:
        resp = requests.get(
            "https://openlibrary.org/search.json",
            params=params,
            headers=_OPEN_LIBRARY_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except (requests.RequestException, ValueError) as exc:
        current_app.logger.warning("Open Library lookup failed: %s", exc)
        return jsonify({"error": "No match found"})

    if normalized_isbn:
        # search.json's isbn param is a loose search term, not an exact filter, so it can
        # return an unrelated "closest match" for a garbage ISBN -- only trust a doc that
        # actually lists the requested ISBN among its editions.
        exact = next((doc for doc in docs if normalized_isbn in doc.get("isbn", [])), None)
        if not exact:
            return jsonify({"error": "No match found"})
        return jsonify({"match": _open_library_candidate(exact, fallback_isbn=isbn)})

    if not docs:
        return jsonify({"error": "No match found"})
    return jsonify({"candidates": [_open_library_candidate(doc) for doc in docs[:5]]})


@bp.route("/api/lookup/covers")
@login_required
def lookup_covers():
    work_key = request.args.get("work", "").strip()
    if not re.fullmatch(r"/works/OL\d+W", work_key):
        return jsonify({"covers": []})

    try:
        resp = requests.get(
            f"https://openlibrary.org{work_key}/editions.json",
            params={"limit": 200},
            headers=_OPEN_LIBRARY_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        entries = resp.json().get("entries", [])
    except (requests.RequestException, ValueError) as exc:
        current_app.logger.warning("Open Library editions lookup failed: %s", exc)
        return jsonify({"covers": []})

    covers = []
    for entry in entries:
        languages = entry.get("languages") or []
        if any(lang.get("key") != "/languages/eng" for lang in languages):
            continue  # explicitly non-English edition
        cover_ids = [c for c in (entry.get("covers") or []) if c and c > 0]
        if not cover_ids:
            continue  # no real cover art
        isbns = entry.get("isbn_13") or entry.get("isbn_10") or []
        covers.append({
            "cover_url": f"https://covers.openlibrary.org/b/id/{cover_ids[0]}-L.jpg",
            "isbn": isbns[0] if isbns else "",
        })
        if len(covers) >= 12:
            break
    return jsonify({"covers": covers})


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_book():
    form = BookForm()
    form.picked_by.choices = _picked_by_choices()

    if form.validate_on_submit():
        picked_by_id = form.picked_by.data if current_user.is_admin else current_user.id
        book = Book(
            name=form.title.data,
            author=form.author.data,
            cover_url=form.cover_url.data,
            isbn=form.isbn.data,
            status=BookStatus[form.status.data],
            picked_by_id=picked_by_id,
            added_by_id=current_user.id,
            reading_start_date=form.reading_start_date.data,
            reading_end_date=form.reading_end_date.data,
        )
        db.session.add(book)
        db.session.commit()
        return redirect(url_for("books.book_detail", book_id=book.id))

    return render_template("books/form.html", form=form)


@bp.route("/<int:book_id>", methods=["GET", "POST"])
@login_required
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    ordered_books = _sort_books(Book.query.all(), "start_date")
    idx = next(i for i, b in enumerate(ordered_books) if b.id == book_id)
    newer_book = ordered_books[idx - 1] if idx > 0 else None
    older_book = ordered_books[idx + 1] if idx < len(ordered_books) - 1 else None
    existing_rating = Rating.query.filter_by(book_id=book_id, member_id=current_user.id).first()
    form = RatingForm(obj=existing_rating)
    delete_form = DeleteForm()

    if request.method == "POST" and book.status != BookStatus.FINISHED:
        flash("Ratings can only be submitted for finished books.")
        return redirect(url_for("books.book_detail", book_id=book_id))

    if form.validate_on_submit():
        if existing_rating:
            existing_rating.score = form.score.data
            existing_rating.comment = form.comment.data
        else:
            new_rating = Rating(
                book_id=book_id,
                member_id=current_user.id,
                score=form.score.data,
                comment=form.comment.data,
            )
            db.session.add(new_rating)
        db.session.commit()
        return redirect(url_for("books.book_detail", book_id=book_id))

    return render_template(
        "books/detail.html",
        book=book,
        form=form,
        delete_form=delete_form,
        existing_rating=existing_rating,
        newer_book=newer_book,
        older_book=older_book,
    )


@bp.route("/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if not _can_manage(book):
        abort(403)

    form = BookForm(obj=book)
    form.picked_by.choices = _picked_by_choices()

    if request.method == "GET":
        form.title.data = book.name
        form.status.data = book.status.name
        form.picked_by.data = book.picked_by_id

    if form.validate_on_submit():
        book.name = form.title.data
        book.author = form.author.data
        book.cover_url = form.cover_url.data
        book.isbn = form.isbn.data
        book.status = BookStatus[form.status.data]
        book.picked_by_id = form.picked_by.data if current_user.is_admin else current_user.id
        book.reading_start_date = form.reading_start_date.data
        book.reading_end_date = form.reading_end_date.data
        db.session.commit()
        return redirect(url_for("books.book_detail", book_id=book.id))

    return render_template("books/form.html", form=form, book=book)


@bp.route("/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    book = Book.query.get_or_404(book_id)
    if not _can_manage(book):
        abort(403)
    if book.ratings:
        flash("Can't delete a book that has ratings")
        return redirect(url_for("books.book_detail", book_id=book.id))
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for("books.index"))


@bp.route("/<int:book_id>/rating/delete", methods=["POST"])
@login_required
def delete_rating(book_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    rating = Rating.query.filter_by(book_id=book_id, member_id=current_user.id).first_or_404()
    db.session.delete(rating)
    db.session.commit()
    return redirect(url_for("books.book_detail", book_id=book_id))
