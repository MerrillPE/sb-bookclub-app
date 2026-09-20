from flask import (
    Blueprint, flash, redirect, render_template, url_for
)

from flask_login import login_user, logout_user, login_required, current_user

from app.models import Member, Invite
from app.extensions import db, login_manager
from app.auth.forms import LoginForm, RegistrationForm

from datetime import datetime, timezone


bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["GET", "POST"])
def login():
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
    
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
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