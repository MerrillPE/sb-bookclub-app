import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, migrate, login_manager


bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login")
def login():
    return "Login"