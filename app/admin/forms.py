from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import Optional, ValidationError

from app.models import _naive_utcnow


class CreateInviteForm(FlaskForm):
    expires_at = DateField("Expires on (optional)", validators=[Optional()])
    submit = SubmitField("Generate Invite")

    def validate_expires_at(self, field):
        # The invite stays valid through the end of the chosen day (see admin.invites), so
        # today is still in the future; anything earlier would be expired on creation. Compared
        # in UTC, matching how expires_at is stored.
        if field.data and field.data < _naive_utcnow().date():
            raise ValidationError("Expiration date must be in the future.")

class RevokeInviteForm(FlaskForm):
    """No fields needed -- exists purely to give the revoke button a CSRF token."""
    submit = SubmitField("Revoke")

class GenerateResetForm(FlaskForm):
    """No fields needed -- exists purely to give the reset button a CSRF token."""
    submit = SubmitField("Send Reset Link")
