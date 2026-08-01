"""
Run this to refresh the site with the latest jobs + scholarships.

Usage:
    python -m app.scrapers.update_agent

Wire this to a cron job / Render Cron Job / GitHub Actions schedule to run
automatically (e.g. every 6 hours). It:
  1. Scrapes each source
  2. Upserts new listings (skips ones already in the DB by external_id)
  3. Marks listings no longer seen by the scraper as inactive
"""
import sys
import time
from datetime import datetime

from app import create_app, db
from app.models import Job, Scholarship
from app.scrapers.jobs_scraper import scrape_jobs
from app.scrapers.scholarship_scraper import scrape_scholarships


def update_jobs():
    print(f"[{datetime.utcnow()}] Scraping jobs...")
    try:
        scraped = scrape_jobs()
    except Exception as e:
        print(f"  Job scrape failed: {e}")
        return 0, 0

    seen_ids = set()
    new_count = 0
    for item in scraped:
        seen_ids.add(item["external_id"])
        existing = Job.query.filter_by(external_id=item["external_id"]).first()
        if existing:
            existing.is_active = True
            continue
        db.session.add(Job(**item))
        new_count += 1

    # mark stale listings inactive (not seen in this run, and older than today)
    stale = Job.query.filter(~Job.external_id.in_(seen_ids)).all() if seen_ids else []
    for j in stale:
        j.is_active = False

    db.session.commit()
    print(f"  {new_count} new jobs added, {len(stale)} marked inactive.")
    return new_count, len(stale)


def update_scholarships():
    print(f"[{datetime.utcnow()}] Scraping scholarships...")
    try:
        scraped = scrape_scholarships()
    except Exception as e:
        print(f"  Scholarship scrape failed: {e}")
        return 0, 0

    seen_ids = set()
    new_count = 0
    for item in scraped:
        seen_ids.add(item["external_id"])
        existing = Scholarship.query.filter_by(external_id=item["external_id"]).first()
        if existing:
            existing.is_active = True
            continue
        db.session.add(Scholarship(**item))
        new_count += 1

    stale = Scholarship.query.filter(~Scholarship.external_id.in_(seen_ids)).all() if seen_ids else []
    for s in stale:
        s.is_active = False

    db.session.commit()
    print(f"  {new_count} new scholarships added, {len(stale)} marked inactive.")
    return new_count, len(stale)


def notify_telegram(new_jobs, new_scholarships):
    """Optional: ping a Telegram channel when new listings land. Fill in
    TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as env vars to enable."""
    import os
    import requests

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    if new_jobs == 0 and new_scholarships == 0:
        return

    text = f"🔔 Site updated: {new_jobs} new jobs, {new_scholarships} new scholarships."
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        print(f"  Telegram notify failed: {e}")


def run():
    app = create_app()
    with app.app_context():
        start = time.time()
        new_jobs, _ = update_jobs()
        new_scholarships, _ = update_scholarships()
        notify_telegram(new_jobs, new_scholarships)
        print(f"Done in {time.time() - start:.1f}s")


if __name__ == "__main__":
    sys.exit(run() or 0)
