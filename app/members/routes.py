from datetime import date

from flask import Blueprint, render_template

from flask_login import login_required

from app.models import Book, Member


bp = Blueprint("members", __name__, url_prefix="/members")


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
    members = Member.query.order_by(Member.display_name).all()
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


@bp.route("/<int:member_id>")
@login_required
def profile(member_id):
    member = Member.query.get_or_404(member_id)
    picks = sorted(Book.query.filter_by(picked_by_id=member.id).all(), key=_by_reading_date, reverse=True)
    reviews = sorted(member.ratings, key=lambda r: (_by_reading_date(r.book), r.created_at), reverse=True)

    scores = [r.score for r in reviews]
    rated_picks = [b.average_rating for b in picks if b.average_rating is not None]
    # Positive = scores more generously than the rest of the club, on the same books.
    deltas = [r.score - avg for r in reviews if (avg := _others_average(r)) is not None]

    return render_template(
        "members/profile.html",
        member=member,
        picks=picks,
        reviews=[(r, _others_average(r)) for r in reviews],
        avg_given=sum(scores) / len(scores) if scores else None,
        picks_avg=sum(rated_picks) / len(rated_picks) if rated_picks else None,
        taste_delta=sum(deltas) / len(deltas) if deltas else None,
    )
