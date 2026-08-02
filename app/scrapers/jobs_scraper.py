"""
Wraps the JobSpy library (https://github.com/speedyapply/JobSpy) to pull
listings from multiple boards in one call. Returns a normalized list of
dicts ready to be upserted into the Job model.

Install: pip install python-jobspy
"""
import hashlib
from datetime import datetime

# Expand coverage by searching multiple terms/locations instead of just one.
# Kept intentionally short (not dozens of combos) since each query re-runs
# scraping across all 4 job sites - more queries = more time + memory per run.
SEARCH_QUERIES = [
    {"search_term": "remote", "location": "Nigeria"},
    {"search_term": "developer", "location": "Nigeria"},
    {"search_term": "customer service", "location": "Nigeria"},
    {"search_term": "remote", "location": "Lagos"},
]


def _make_external_id(site, url):
    return hashlib.sha256(f"{site}:{url}".encode()).hexdigest()[:32]


def _safe_str(value, default=""):
    """JobSpy/pandas returns missing fields as NaN (a float), not None or
    empty string. Slicing or calling string methods on NaN crashes with
    confusing errors like 'float object is not subscriptable'. This
    normalizes any missing/NaN value to a safe default string."""
    if value is None:
        return default
    try:
        import pandas as pd
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value)


def scrape_jobs(search_term="remote", location="Nigeria", results_wanted=15, sites=None):
    """
    Returns a list of normalized job dicts:
    {external_id, title, company, location, is_remote, salary, source, url, description, date_posted}

    results_wanted default kept low (15) since JobSpy + pandas can push
    memory usage past free-tier hosting limits (e.g. Render's 512MB) when
    scraping multiple sites at once.
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
        url = _safe_str(row.get("job_url"))
        if not url:
            continue
        site = _safe_str(row.get("site"), "unknown")
        location_str = _safe_str(row.get("location"))
        jobs.append({
            "external_id": _make_external_id(site, url),
            "title": _safe_str(row.get("title"), "Untitled role"),
            "company": _safe_str(row.get("company"), "Unknown"),
            "location": location_str,
            "is_remote": bool(row.get("is_remote")) if not _is_missing(row.get("is_remote")) else "remote" in location_str.lower(),
            "salary": _format_salary(row),
            "source": site,
            "url": url,
            "description": _safe_str(row.get("description"))[:5000],
            "date_posted": row.get("date_posted") if not _is_missing(row.get("date_posted")) else datetime.utcnow(),
        })

    del df  # free the dataframe explicitly rather than waiting for GC
    return jobs


def scrape_jobs_multi(queries=None):
    """
    Runs multiple search queries one at a time, YIELDING results after each
    query completes rather than collecting everything into one big list.
    This lets the caller commit each batch to the DB and free memory before
    the next query starts scraping - important on low-RAM free hosting.
    """
    import gc

    queries = queries or SEARCH_QUERIES
    for q in queries:
        try:
            results = scrape_jobs(search_term=q["search_term"], location=q["location"])
        except Exception as e:
            print(f"  Query {q} failed: {e}")
            results = []
        yield results
        gc.collect()


def _is_missing(value):
    if value is None:
        return True
    try:
        import pandas as pd
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _format_salary(row):
    lo, hi = row.get("min_amount"), row.get("max_amount")
    if _is_missing(lo) or _is_missing(hi):
        return None
    try:
        return f"{int(lo):,} - {int(hi):,} {_safe_str(row.get('currency'))}".strip()
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    results = scrape_jobs()
    print(f"Scraped {len(results)} jobs")
    for j in results[:5]:
        print(j["title"], "-", j["company"], "-", j["url"])
