from flask import (
    Blueprint, flash, redirect, render_template, url_for
)

from flask_login import login_user, logout_user, login_required, current_user

from app.models import Member, Invite, PasswordReset
from app.extensions import db, login_manager
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordForm

from datetime import datetime, timezone


bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        member = Member.query.filter_by(username=form.username.data).first()

        if member and member.check_password(form.password.data):
            login_user(member)
            return redirect(url_for("home"))
        flash("Invalid username or password")
    return render_template("auth/login.html", form=form)

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@bp.route("/register/<token>", methods=["GET", "POST"])
def register(token):
    invite = Invite.query.filter_by(token=token).first()
    
    if invite is None:
        flash("Invalid invite link")
        return redirect(url_for("auth.login"))
    
    if invite.used_at is not None:
        flash("Invite has already been used")
        return redirect(url_for("auth.login"))
    
    if invite.is_expired:
        flash("This invite has expired")
        return redirect(url_for("auth.login"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        member = Member(
            username=form.username.data,
            display_name=form.username.data
        )
        member.set_password(form.password.data)
        db.session.add(member)
        
        invite.used_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        login_user(member)
        return redirect(url_for("home"))

    return render_template("auth/register.html", form=form)

@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset = PasswordReset.query.filter_by(token=token).first()

    if reset is None:
        flash("Invalid password reset link")
        return redirect(url_for("auth.login"))

    if reset.used_at is not None:
        flash("This reset link has already been used")
        return redirect(url_for("auth.login"))

    if reset.is_expired:
        flash("This reset link has expired")
        return redirect(url_for("auth.login"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        reset.member.set_password(form.password.data)
        reset.used_at = datetime.now(timezone.utc)
        db.session.commit()

        login_user(reset.member)
        return redirect(url_for("home"))

    return render_template("auth/reset_password.html", form=form)