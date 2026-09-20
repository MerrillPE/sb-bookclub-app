import os
from flask import Flask, render_template

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
        return render_template("base.html")
    
    from app import auth
    app.register_blueprint(auth.bp)
    
    from app import books
    app.register_blueprint(books.bp)
    
    return app