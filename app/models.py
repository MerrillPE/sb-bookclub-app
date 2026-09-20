from datetime import datetime, timezone
import enum
import secrets

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class BookStatus(enum.Enum):
    TO_BE_READ = "to_be_read"
    CURRENTLY_READING = "currently_reading"
    FINISHED = "finished"
    ABANDONED = "abandoned"

class Member(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    ratings = db.relationship("Rating", back_populates="member")
    
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)
        
    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)
    
    def __repr__(self):
        return f"Member {self.username}"
    
@login_manager.user_loader
def load_user(user_id):
    return Member.query.get(int(user_id))

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Invite token={self.token} used={self.used_at is not None}>"

#TODO: In future may pull name/author/cover from some API based on ISBN
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    cover_url = db.Column(db.String(255))
    added_by_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    picked_by_id = db.Column(db.Integer, db.ForeignKey("member.id")) # Allow to be set by admin for another member
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reading_start_date = db.Column(db.Date)
    reading_end_date = db.Column(db.Date)
    status = db.Column(db.Enum(BookStatus, create_constraint=True, name="ck_book_status"), nullable=False, default=BookStatus.TO_BE_READ)
    
    
    added_by = db.relationship("Member", foreign_keys=[added_by_id])
    picked_by = db.relationship("Member", foreign_keys=[picked_by_id])
    ratings = db.relationship("Rating", back_populates="book")

    @property
    def average_rating(self):
        if not self.ratings:
            return None
        return sum(r.score for r in self.ratings) / len(self.ratings)

    @property
    def status_label(self):
        return self.status.value.replace("_", " ").title()

    def __repr__(self):
        return f"<Book {self.name}>"

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    member = db.relationship("Member", back_populates="ratings")
    book = db.relationship("Book", back_populates="ratings")
    
    __table_args__ = (
        db.UniqueConstraint("book_id", "member_id", name="one_review_per_member_per_book"),
        db.CheckConstraint("score >= 1.0 AND score <= 5.0 AND (score * 2) = CAST(score * 2 AS INTEGER)", name="score_range"), # Score must be 1-5 in 0.5 increments
    )
    
    def __repr__(self):
        return f"<Rating member={self.member_id} book={self.book_id} score={self.score}>"
    
#TODO: Add meeting object to track meeting dates associated with given book