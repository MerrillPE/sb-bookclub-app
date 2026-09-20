from datetime import datetime, timezone
from functools import wraps

from flask import (
    Blueprint, abort, flash, redirect, render_template, url_for
)

from flask_login import login_required, current_user

from app.models import Invite, Member, PasswordReset
from app.extensions import db
from app.admin.forms import CreateInviteForm, RevokeInviteForm, GenerateResetForm


bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.route("/invites", methods=["GET", "POST"])
@login_required
@admin_required
def invites():
    form = CreateInviteForm()

    if form.validate_on_submit():
        expires_at = None
        if form.expires_at.data:
            expires_at = datetime.combine(form.expires_at.data, datetime.max.time()).replace(tzinfo=timezone.utc)
        Invite.create(expires_at=expires_at)
        flash("Invite created.")
        return redirect(url_for("admin.invites"))

    all_invites = Invite.query.order_by(Invite.created_at.desc()).all()
    all_invites.sort(key=lambda i: i.status_label != "Pending")
    return render_template(
        "admin/invites.html",
        form=form,
        revoke_form=RevokeInviteForm(),
        invites=all_invites,
    )


@bp.route("/invites/<int:invite_id>/revoke", methods=["POST"])
@login_required
@admin_required
def revoke_invite(invite_id):
    if not RevokeInviteForm().validate_on_submit():
        abort(400)
    invite = Invite.query.get_or_404(invite_id)
    if invite.used_at is not None:
        flash("Can't revoke an invite that's already been used.")
        return redirect(url_for("admin.invites"))
    db.session.delete(invite)
    db.session.commit()
    return redirect(url_for("admin.invites"))


@bp.route("/members")
@login_required
@admin_required
def members():
    all_members = Member.query.order_by(Member.display_name).all()
    pending_resets = {}
    for r in PasswordReset.query.filter_by(used_at=None).order_by(PasswordReset.created_at.desc()).all():
        if not r.is_expired:
            pending_resets.setdefault(r.member_id, r)
    return render_template(
        "admin/members.html",
        members=all_members,
        reset_form=GenerateResetForm(),
        pending_resets=pending_resets,
    )


@bp.route("/members/<int:member_id>/reset", methods=["POST"])
@login_required
@admin_required
def generate_reset(member_id):
    if not GenerateResetForm().validate_on_submit():
        abort(400)
    member = Member.query.get_or_404(member_id)
    PasswordReset.query.filter_by(member_id=member.id, used_at=None).delete()
    PasswordReset.create(member)
    flash(f"Reset link generated for {member.display_name}.")
    return redirect(url_for("admin.members"))
