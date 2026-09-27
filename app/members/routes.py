from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from flask_login import current_user, login_required

from app.extensions import db
from app.members.forms import DisplayNameForm
from app.models import Book, Member


bp = Blueprint("members", __name__, url_prefix="/members")

# Admin accounts are separate club-management logins (seeded before any members join,
# used for invites/password resets and site-wide edits), not reading members -- so they're
# left out of the members section entirely, same as the "Picked by" choices in books/routes.py.


def _by_reading_date(book):
    return book.reading_start_date or date.min


def _others_average(rating):
    """The book's average score from everyone *except* this rating's author, or None if
    nobody else has rated it -- used to compare a member's taste against the rest of the club."""
    others = [r.score for r in rating.book.ratings if r.member_id != rating.member_id]
    return sum(others) / len(others) if others else None


@bp.route("/")
@login_required
def index():
    members = Member.query.filter_by(is_admin=False).order_by(Member.display_name).all()
    books = Book.query.all()
    cards = []
    for member in members:
        picks = sorted((b for b in books if b.picked_by_id == member.id), key=_by_reading_date, reverse=True)
        scores = [r.score for r in member.ratings]
        cards.append({
            "member": member,
            "picks": picks,
            "review_count": len(scores),
            "avg_given": sum(scores) / len(scores) if scores else None,
        })
    return render_template("members/index.html", cards=cards)


@bp.route("/<int:member_id>", methods=["GET", "POST"])
@login_required
def profile(member_id):
    member = Member.query.filter_by(id=member_id, is_admin=False).first_or_404()

    # Only your own profile gets the "Edit name" form.
    form = None
    if member.id == current_user.id:
        form = DisplayNameForm(obj=member)
        if form.validate_on_submit():
            member.display_name = form.display_name.data
            db.session.commit()
            flash("Display name updated.", "success")
            return redirect(url_for("members.profile", member_id=member.id))
    elif request.method == "POST":
        abort(403)

    picks = sorted(Book.query.filter_by(picked_by_id=member.id).all(), key=_by_reading_date, reverse=True)
    reviews = sorted(member.ratings, key=lambda r: (_by_reading_date(r.book), r.created_at), reverse=True)

    scores = [r.score for r in reviews]
    rated_picks = [b.average_rating for b in picks if b.average_rating is not None]
    # Positive = scores more generously than the rest of the club, on the same books.
    deltas = [r.score - avg for r in reviews if (avg := _others_average(r)) is not None]

    return render_template(
        "members/profile.html",
        member=member,
        form=form,
        picks=picks,
        reviews=[(r, _others_average(r)) for r in reviews],
        avg_given=sum(scores) / len(scores) if scores else None,
        picks_avg=sum(rated_picks) / len(rated_picks) if rated_picks else None,
        taste_delta=sum(deltas) / len(deltas) if deltas else None,
    )
