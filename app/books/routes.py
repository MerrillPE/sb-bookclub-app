from datetime import date

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for
)

from flask_login import login_required, current_user

from app.models import Book, Rating, Member, BookStatus
from app.extensions import db
from app.books.forms import BookForm, RatingForm, DeleteForm


bp = Blueprint("books", __name__, url_prefix="/books")


def _picked_by_choices():
    return [("", "- None -")] + [
        (m.id, m.display_name) for m in Member.query.filter_by(is_admin=False).all()
    ]


def _can_manage(book):
    return current_user.id == book.picked_by_id or current_user.is_admin


def _sort_books(all_books, sort):
    if sort == "status":
        order = {s: i for i, s in enumerate(BookStatus)}
        return sorted(all_books, key=lambda b: order[b.status])
    if sort == "rating":
        return sorted(all_books, key=lambda b: b.average_rating or 0, reverse=True)
    # "start_date" (default): most recently started first. created_at ("date added") is
    # deliberately not offered as a frontend sort — it's record-keeping metadata (when the
    # row was created), not something a reader cares about; reading_start_date is.
    return sorted(all_books, key=lambda b: b.reading_start_date or date.min, reverse=True)


@bp.route("/")
@login_required
def index():
    status_filter = request.args.get("status", "")
    sort = request.args.get("sort", "start_date")

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
    existing_rating = Rating.query.filter_by(book_id=book_id, member_id=current_user.id).first()
    form = RatingForm(obj=existing_rating)
    delete_form = DeleteForm()

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

    return render_template("books/detail.html", book=book, form=form, delete_form=delete_form)


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
        book.status = BookStatus[form.status.data]
        book.picked_by_id = form.picked_by.data if current_user.is_admin else current_user.id
        book.reading_start_date = form.reading_start_date.data
        book.reading_end_date = form.reading_end_date.data
        db.session.commit()
        return redirect(url_for("books.book_detail", book_id=book.id))

    return render_template("books/form.html", form=form)


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
