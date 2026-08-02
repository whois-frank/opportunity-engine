import os
from flask import Blueprint, render_template, Response, request, jsonify
from app import db
from app import db
from app.models import Job, Scholarship, PageView

main_bp = Blueprint("main", __name__)


def _check_key():
    expected_key = os.environ.get("UPDATE_SECRET_KEY")
    provided_key = request.args.get("key") or (request.json or {}).get("key") if request.is_json else request.args.get("key")
    return expected_key and provided_key == expected_key


@main_bp.route("/admin/ingest", methods=["POST"])
def ingest():
    """
    Accepts scraped listings from a LOCAL scraper (e.g. running on your own
    machine with full internet access) and upserts them into the hosted DB.
    Use this when the host itself has restricted outbound internet (e.g.
    PythonAnywhere free tier).

    POST JSON body:
    {
        "key": "YOUR_SECRET",
        "jobs": [ {external_id, title, company, ...}, ... ],
        "scholarships": [ {external_id, title, provider, ...}, ... ]
    }
    """
    expected_key = os.environ.get("UPDATE_SECRET_KEY")
    payload = request.get_json(silent=True) or {}
    if not expected_key or payload.get("key") != expected_key:
        return jsonify({"error": "unauthorized"}), 403

    new_jobs, new_scholarships = 0, 0

    for item in payload.get("jobs", []):
        existing = Job.query.filter_by(external_id=item["external_id"]).first()
        if existing:
            existing.is_active = True
            continue
        db.session.add(Job(**{k: v for k, v in item.items() if hasattr(Job, k)}))
        new_jobs += 1

    for item in payload.get("scholarships", []):
        existing = Scholarship.query.filter_by(external_id=item["external_id"]).first()
        if existing:
            existing.is_active = True
            continue
        db.session.add(Scholarship(**{k: v for k, v in item.items() if hasattr(Scholarship, k)}))
        new_scholarships += 1

    db.session.commit()
    return jsonify({"status": "ok", "new_jobs": new_jobs, "new_scholarships": new_scholarships})


@main_bp.route("/admin/stats")
def stats():
    expected_key = os.environ.get("UPDATE_SECRET_KEY")
    provided_key = request.args.get("key")
    if not expected_key or provided_key != expected_key:
        return jsonify({"error": "unauthorized"}), 403

    from datetime import datetime, timedelta
    from sqlalchemy import func

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    total_views = PageView.query.count()
    today_views = PageView.query.filter(PageView.viewed_at >= today_start).count()
    week_views = PageView.query.filter(PageView.viewed_at >= week_start).count()

    top_pages = (
        db.session.query(PageView.path, func.count(PageView.id).label("views"))
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "total_views": total_views,
        "today_views": today_views,
        "last_7_days_views": week_views,
        "total_jobs": Job.query.count(),
        "total_scholarships": Scholarship.query.count(),
        "top_pages": [{"path": p, "views": v} for p, v in top_pages],
    })


@main_bp.route("/admin/run-update")
def run_update():
    """
    Triggers a LOCAL (in-process) scrape + refresh. Only works if the host
    itself has open outbound internet access (e.g. Render). If your host
    restricts outbound calls (e.g. PythonAnywhere free tier), use the
    /admin/ingest endpoint instead, fed by scripts/local_push.py running on
    your own machine.
    """
    expected_key = os.environ.get("UPDATE_SECRET_KEY")
    provided_key = request.args.get("key")

    if not expected_key or provided_key != expected_key:
        return jsonify({"error": "unauthorized"}), 403

    from app.scrapers.update_agent import update_jobs, update_scholarships, notify_telegram

    new_jobs, _ = update_jobs()
    new_scholarships, _ = update_scholarships()
    notify_telegram(new_jobs, new_scholarships)

    return jsonify({
        "status": "ok",
        "new_jobs": new_jobs,
        "new_scholarships": new_scholarships,
    })


@main_bp.route("/")
def home():
    latest_jobs = Job.query.filter_by(is_active=True).order_by(Job.first_seen_at.desc()).limit(6).all()
    latest_scholarships = Scholarship.query.filter_by(is_active=True).order_by(Scholarship.first_seen_at.desc()).limit(6).all()
    return render_template("index.html", jobs=latest_jobs, scholarships=latest_scholarships)


@main_bp.route("/jobs")
def jobs():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = Job.query.filter_by(is_active=True)
    if q:
        query = query.filter(Job.title.ilike(f"%{q}%"))
    pagination = query.order_by(Job.first_seen_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template("jobs.html", pagination=pagination, q=q)


@main_bp.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template("job_detail.html", job=job)


@main_bp.route("/scholarships")
def scholarships():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = Scholarship.query.filter_by(is_active=True)
    if q:
        query = query.filter(Scholarship.title.ilike(f"%{q}%"))
    pagination = query.order_by(Scholarship.deadline.asc().nullslast()).paginate(page=page, per_page=25, error_out=False)
    return render_template("scholarships.html", pagination=pagination, q=q)


@main_bp.route("/scholarships/<int:sid>")
def scholarship_detail(sid):
    sch = Scholarship.query.get_or_404(sid)
    return render_template("scholarship_detail.html", sch=sch)


@main_bp.route("/sitemap.xml")
def sitemap():
    jobs = Job.query.filter_by(is_active=True).all()
    scholarships = Scholarship.query.filter_by(is_active=True).all()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml.append(f"<url><loc>{request.url_root}</loc></url>")
    xml.append(f"<url><loc>{request.url_root}jobs</loc></url>")
    xml.append(f"<url><loc>{request.url_root}scholarships</loc></url>")
    for j in jobs:
        xml.append(f"<url><loc>{request.url_root}jobs/{j.id}</loc></url>")
    for s in scholarships:
        xml.append(f"<url><loc>{request.url_root}scholarships/{s.id}</loc></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@main_bp.route("/sw.js")
def service_worker():
    """
    Ad network (Monetag/PropellerAds) site-ownership verification file.
    Must be served at the exact root path /sw.js, not under /static/.
    """
    content = """self.options = {
    "domain": "3nbf4.com",
    "zoneId": 11483435
}
self.lary = ""
importScripts('https://3nbf4.com/act/files/service-worker.min.js?r=sw')
"""
    return Response(content, mimetype="application/javascript")


@main_bp.route("/ads.txt")
def ads_txt():
    """
    Ad network verification file. Add one line per network once you have
    your publisher ID, e.g.:
        propellerads.com, PUB_ID_HERE, DIRECT
    Multiple networks can each have their own line here.
    """
    lines = os.environ.get("ADS_TXT_CONTENT", "")
    return Response(lines, mimetype="text/plain")


@main_bp.route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nSitemap: " + request.url_root + "sitemap.xml", mimetype="text/plain")
