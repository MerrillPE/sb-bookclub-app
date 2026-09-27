import os
from flask import Flask, redirect, url_for

from flask_login import current_user

from app.extensions import db, migrate, login_manager
from app.config import Config

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(test_config)
        
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    from app import models # noqa: F401
    
    os.makedirs(app.instance_path, exist_ok=True)
    
    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("books.index"))
        return redirect(url_for("auth.login"))
    
    from app import auth
    app.register_blueprint(auth.bp)
    
    from app import books
    app.register_blueprint(books.bp)

    from app import admin
    app.register_blueprint(admin.bp)

    from app import members
    app.register_blueprint(members.bp)

    @app.template_filter("nice_date")
    def nice_date(value):
        # "Sep 3, 2026" -- built by hand rather than strftime("%-d"), which is glibc-only and
        # raises ValueError on Windows.
        return f"{value:%b} {value.day}, {value.year}" if value else ""

    @app.template_filter("title_seed")
    def title_seed(value):
        # Stable per-title number used to pick a generated cover/spine's colour and size.
        # Keyed on the title (not the row id) so the add-book form's live preview -- which has
        # no id yet -- can compute the same value client-side (see titleSeed() in books.js).
        return sum(ord(c) for c in (value or ""))

    @app.cli.command("create-invite")
    def create_invite():
        from app.models import Invite
        invite = Invite.create()
        print(f"Invite token: {invite.token}")
        print(f"Registration link: /auth/register/{invite.token}")

    return app