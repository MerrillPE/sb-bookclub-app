import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, migrate, login_manager


bp = Blueprint("books", __name__, url_prefix="/books")

@bp.route("/")
def books():
    return "Books"