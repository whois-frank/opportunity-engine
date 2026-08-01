"""
Scholarship sources don't have a clean unified API like JobSpy does for jobs,
so this pulls from public RSS feeds. Add/remove feeds in SOURCES as you find
good ones. Install: pip install feedparser
"""
import hashlib
from datetime import datetime

SOURCES = {
    "opportunity_desk": "https://opportunitydesk.org/feed/",
    "scholars4dev": "https://www.scholars4dev.com/feed/",
}


def _make_external_id(source, link):
    return hashlib.sha256(f"{source}:{link}".encode()).hexdigest()[:32]


def scrape_scholarships():
    import feedparser  # lazy import so app boots without it installed

    results = []
    for source_name, feed_url in SOURCES.items():
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            link = entry.get("link")
            if not link:
                continue
            title = entry.get("title", "Untitled opportunity")
            # crude relevance filter: only keep entries that look scholarship-related
            if "scholarship" not in title.lower() and "fellowship" not in title.lower() and "grant" not in title.lower():
                continue
            summary = entry.get("summary", "")[:2000]
            published = entry.get("published_parsed")
            results.append({
                "external_id": _make_external_id(source_name, link),
                "title": title,
                "provider": source_name,
                "country": None,  # left for later NLP/LLM extraction
                "deadline": None,  # left for later NLP/LLM extraction from summary
                "source": source_name,
                "url": link,
                "description": summary,
            })
    return results


if __name__ == "__main__":
    results = scrape_scholarships()
    print(f"Scraped {len(results)} scholarships")
    for s in results[:5]:
        print(s["title"], "-", s["url"])
