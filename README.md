# Opportunity Engine (MVP)

Auto-updating jobs + scholarships aggregator with unobtrusive ad slots baked in.

## What's built
- Flask app (app factory pattern) with SQLAlchemy models for Job + Scholarship
- Job scraper wrapping [JobSpy](https://github.com/speedyapply/JobSpy) (LinkedIn, Indeed, Google Jobs, ZipRecruiter)
- Scholarship scraper pulling from public RSS feeds (Opportunity Desk, Scholars4Dev — add more in `app/scrapers/scholarship_scraper.py`)
- Update agent (`app/scrapers/update_agent.py`) — the "run it and it refreshes the site" piece. Dedupes by external_id, marks stale listings inactive, optionally pings Telegram
- SEO basics: sitemap.xml, robots.txt, per-listing meta descriptions
- Ad slots pre-placed in templates (commented out — uncomment + add your AdSense publisher ID once approved)
- render.yaml for one-click-ish free deploy to Render (web service + cron job + free Postgres)

## Local setup
```bash
pip install -r requirements.txt
python run.py
```
Visit http://localhost:5000

## Populate listings
```bash
python -m app.scrapers.update_agent
```
This scrapes both sources and inserts into the DB. Run it manually first to see the site with real data.

## Deploy to Render (free)
1. Push this repo to GitHub
2. In Render dashboard: New → Blueprint → connect your repo (it'll read `render.yaml` automatically)
3. Render provisions: free web service + free Postgres + a cron job that runs the update agent every 6 hours
4. Once live, manually trigger the cron job once (or wait for the schedule) to populate real listings

## Next steps (not yet built)
- LLM step to clean/summarize scraped descriptions and extract scholarship deadlines from RSS text
- Telegram bot distribution channel (hook already in update_agent.py — just set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars)
- AdSense application (apply once there's real content live — approval takes 1-4 weeks)
- More scholarship RSS sources
- Domain name + custom domain setup on Render
