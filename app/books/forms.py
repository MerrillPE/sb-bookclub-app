from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.models import BookStatus


# Catch picked_by field left empty to keep coerce from failing
def _coerce_picked_by(value):
    if value in (None, "", "None"):
        return None
    return int(value)

class BookForm(FlaskForm):
    # Length limits mirror the Book columns -- SQLite ignores String(n), but Postgres raises
    # on an over-length value, so the form has to catch it first (same as RatingForm.comment).
    title = StringField("Title", validators=[DataRequired(), Length(max=120)], render_kw={"maxlength": 120})
    author = StringField("Author", validators=[DataRequired(), Length(max=120)], render_kw={"maxlength": 120})
    cover_url = StringField("Cover URL", validators=[Length(max=255)], render_kw={"maxlength": 255})
    isbn = StringField("ISBN", validators=[Optional(), Length(max=20)], render_kw={"maxlength": 20})
    status = SelectField(
        "Status",
        choices=[(s.name, s.value.replace("_", " ").title()) for s in BookStatus],
        validators=[DataRequired()]
    )
    picked_by = SelectField("Picked By", coerce=_coerce_picked_by, validators=[Optional()])
    reading_start_date = DateField("Start Date", validators=[Optional()])
    reading_end_date = DateField("End Date", validators=[Optional()])
    submit = SubmitField("Save Book")

    def validate_reading_end_date(self, field):
        # Same-day start and end is fine (a short book); only a reversed range is rejected.
        start = self.reading_start_date.data
        if field.data and start and field.data < start:
            raise ValidationError("End date can't be before the start date.")

class RatingForm(FlaskForm):
    score = SelectField(
        "Score",
        choices=[(str(x / 2), str(x / 2)) for x in range(2, 11)], # Populate list of 1-5 ratings with .5 increments
        coerce=float,
        validators=[DataRequired()],
        )
    comment = TextAreaField("Comment", validators=[Length(max=500)], render_kw={"rows": 3, "maxlength": 500})
    submit = SubmitField("Submit Review")

class DeleteForm(FlaskForm):
    """No fields needed -- exists purely to give the delete button a CSRF token."""
    submit = SubmitField("Delete")