from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


def _strip(value):
    return value.strip() if value else value


class DisplayNameForm(FlaskForm):
    # Deliberately not unique -- @username is what tells two same-named members apart.
    display_name = StringField(
        "Display name",
        filters=[_strip],
        validators=[DataRequired(), Length(max=80)],
        render_kw={"maxlength": 80},
    )
    submit = SubmitField("Save")
