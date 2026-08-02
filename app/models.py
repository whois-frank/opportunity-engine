from datetime import datetime
from app import db


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(255), unique=True, nullable=False, index=True)  # dedupe key
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    location = db.Column(db.String(255))
    is_remote = db.Column(db.Boolean, default=False)
    salary = db.Column(db.String(100))
    source = db.Column(db.String(50))  # e.g. "linkedin", "indeed"
    url = db.Column(db.String(1000), nullable=False)
    description = db.Column(db.Text)
    summary = db.Column(db.Text)  # short blurb, can be LLM-generated later
    date_posted = db.Column(db.DateTime)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # flip False when scraper no longer sees it

    def __repr__(self):
        return f"<Job {self.title} @ {self.company}>"


class PageView(db.Model):
    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500))
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    referrer = db.Column(db.String(500))


class Scholarship(db.Model):
    __tablename__ = "scholarships"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    provider = db.Column(db.String(255))
    country = db.Column(db.String(100))
    deadline = db.Column(db.Date)
    source = db.Column(db.String(50))
    url = db.Column(db.String(1000), nullable=False)
    description = db.Column(db.Text)
    summary = db.Column(db.Text)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Scholarship {self.title}>"
