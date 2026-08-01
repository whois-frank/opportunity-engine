from flask import Blueprint, render_template, Response, request
from app.models import Job, Scholarship

main_bp = Blueprint("main", __name__)


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


@main_bp.route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nSitemap: " + request.url_root + "sitemap.xml", mimetype="text/plain")
