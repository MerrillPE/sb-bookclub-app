from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.models import BookStatus


# Catch picked_by field left empty to keep coerce from failing
def _coerce_picked_by(value):
    if value in (None, "", "None"):
        return None
    return int(value)

class BookForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    author = StringField("Author", validators=[DataRequired()])
    cover_url = StringField("Cover URL")
    isbn = StringField("ISBN", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[(s.name, s.value.replace("_", " ").title()) for s in BookStatus],
        validators=[DataRequired()]
    )
    picked_by = SelectField("Picked By", coerce=_coerce_picked_by, validators=[Optional()])
    reading_start_date = DateField("Start Date", validators=[Optional()])
    reading_end_date = DateField("End Date", validators=[Optional()])
    submit = SubmitField("Save Book")

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