import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # Use Postgres if DATABASE_URL is set (Render), otherwise local SQLite
    db_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    db.init_app(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    @app.before_request
    def track_page_view():
        from flask import request
        from app.models import PageView
        # Skip tracking for static assets and admin/API routes
        path = request.path
        if path.startswith("/static") or path.startswith("/admin") or path in ("/sitemap.xml", "/robots.txt"):
            return
        try:
            db.session.add(PageView(path=path, referrer=request.referrer))
            db.session.commit()
        except Exception:
            db.session.rollback()  # never let tracking break the actual page

    with app.app_context():
        db.create_all()

    return app
