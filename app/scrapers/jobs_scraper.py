"""
Wraps the JobSpy library (https://github.com/speedyapply/JobSpy) to pull
listings from multiple boards in one call. Returns a normalized list of
dicts ready to be upserted into the Job model.

Install: pip install python-jobspy
"""
import hashlib
from datetime import datetime


def _make_external_id(site, url):
    return hashlib.sha256(f"{site}:{url}".encode()).hexdigest()[:32]


def scrape_jobs(search_term="remote", location="Nigeria", results_wanted=40, sites=None):
    """
    Returns a list of normalized job dicts:
    {external_id, title, company, location, is_remote, salary, source, url, description, date_posted}
    """
    from jobspy import scrape_jobs as jobspy_scrape  # lazy import so app boots without it installed

    sites = sites or ["indeed", "linkedin", "zip_recruiter", "google"]

    df = jobspy_scrape(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        country_indeed="Nigeria",
    )

    jobs = []
    for _, row in df.iterrows():
        url = row.get("job_url") or ""
        if not url:
            continue
        site = row.get("site", "unknown")
        jobs.append({
            "external_id": _make_external_id(site, url),
            "title": row.get("title") or "Untitled role",
            "company": row.get("company") or "Unknown",
            "location": row.get("location") or "",
            "is_remote": bool(row.get("is_remote")) if "is_remote" in row else "remote" in (row.get("location") or "").lower(),
            "salary": _format_salary(row),
            "source": site,
            "url": url,
            "description": (row.get("description") or "")[:5000],
            "date_posted": row.get("date_posted") if row.get("date_posted") else datetime.utcnow(),
        })
    return jobs


def _format_salary(row):
    lo, hi = row.get("min_amount"), row.get("max_amount")
    if lo and hi:
        return f"{int(lo):,} - {int(hi):,} {row.get('currency', '')}".strip()
    return None


if __name__ == "__main__":
    results = scrape_jobs()
    print(f"Scraped {len(results)} jobs")
    for j in results[:5]:
        print(j["title"], "-", j["company"], "-", j["url"])
