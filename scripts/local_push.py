"""
Run this ON YOUR OWN MACHINE (Kali, full internet access) to scrape jobs +
scholarships, then push the results to your hosted site's /admin/ingest
endpoint. Use this when your host (e.g. PythonAnywhere free tier) has
restricted outbound internet and can't scrape directly.

Setup:
    export SITE_URL="https://yourusername.pythonanywhere.com"
    export UPDATE_SECRET_KEY="the same key set on your hosted site"
    python scripts/local_push.py

Schedule it locally with cron, e.g. every 6 hours:
    0 */6 * * * cd /path/to/opportunity-engine && /path/to/venv/bin/python scripts/local_push.py >> /tmp/push_agent.log 2>&1
"""
import os
import sys

# Allow running this script directly without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from app.scrapers.jobs_scraper import scrape_jobs
from app.scrapers.scholarship_scraper import scrape_scholarships


def main():
    site_url = os.environ.get("SITE_URL")
    secret_key = os.environ.get("UPDATE_SECRET_KEY")

    if not site_url or not secret_key:
        print("ERROR: set SITE_URL and UPDATE_SECRET_KEY environment variables first.")
        sys.exit(1)

    print("Scraping jobs...")
    try:
        jobs = scrape_jobs()
    except Exception as e:
        print(f"  Job scrape failed: {e}")
        jobs = []
    print(f"  Got {len(jobs)} jobs")

    print("Scraping scholarships...")
    try:
        scholarships = scrape_scholarships()
    except Exception as e:
        print(f"  Scholarship scrape failed: {e}")
        scholarships = []
    print(f"  Got {len(scholarships)} scholarships")

    # date_posted / dates aren't JSON-serializable as datetime objects, so stringify
    for j in jobs:
        if j.get("date_posted"):
            j["date_posted"] = str(j["date_posted"])
    for s in scholarships:
        if s.get("deadline"):
            s["deadline"] = str(s["deadline"])

    payload = {"key": secret_key, "jobs": jobs, "scholarships": scholarships}

    endpoint = site_url.rstrip("/") + "/admin/ingest"
    print(f"Pushing to {endpoint}...")
    resp = requests.post(endpoint, json=payload, timeout=60)

    if resp.status_code == 200:
        print("Success:", resp.json())
    else:
        print(f"Failed ({resp.status_code}):", resp.text)


if __name__ == "__main__":
    main()
