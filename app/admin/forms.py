from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import Optional


class CreateInviteForm(FlaskForm):
    expires_at = DateField("Expires on (optional)", validators=[Optional()])
    submit = SubmitField("Generate Invite")

class RevokeInviteForm(FlaskForm):
    """No fields needed -- exists purely to give the revoke button a CSRF token."""
    submit = SubmitField("Revoke")

class GenerateResetForm(FlaskForm):
    """No fields needed -- exists purely to give the reset button a CSRF token."""
    submit = SubmitField("Send Reset Link")
