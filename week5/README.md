# Week 5: The Polite Scraper

A small, polite scraping pipeline for [Books to Scrape](https://books.toscrape.com): fetch → extract → normalize → validate → store → report.

## Target Classification

- **Site:** [books.toscrape.com](https://books.toscrape.com), run by [toscrape.com](https://toscrape.com), a "Web Scraping Sandbox." Its own page describes it as "a fictional bookstore that desperately wants to be scraped... a safe place for beginners learning web scraping." That sentence is the permission this assignment relies on.
- **Scope:** the first 3 catalogue pages only (`page-1.html` through `page-3.html`), and the ~60 individual book pages linked from them. No other pages, and no other site, are touched.
- **robots.txt result:** `GET https://books.toscrape.com/robots.txt` → **404 Not Found**. No robots file found. A missing file is not permission, permission here comes from the site's own stated purpose as a public scraping sandbox, not from the absence of a robots.txt.

I will not reuse this code on another site without checking its rules and terms first.

## Lane & install

Python 3.10+. From `week5/`:

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Run it

```bash
./venv/bin/python src/main.py
```

This fetches (or reads from cache), extracts, normalizes, validates, and writes `output/books.json`, `output/errors.json`, and `output/run-report.json`. Re-running is safe, `output/books.json` always ends up with the same 60 unique records, not duplicates.

To prove one broken page can't take down the run, without hammering the real site:

```bash
./venv/bin/python src/main.py --inject-broken-url
```

This appends one made-up book URL to the list before fetching. That single request goes to the real site and gets a real 404 back (no retry, since 404s aren't retried). Everything else still comes from cache. The run still finishes with 60 good records and `run-report.json` reports `failed_pages: 1`.

## Record schema

Defined with Pydantic in `src/schema.py`:

| Field | Type | Required |
|---|---|---|
| `title` | `str` | yes |
| `product_url` | `str` (must start with `https://`) | yes |
| `price_text` | `str` | yes |
| `price_gbp` | `float` (must be > 0) | yes |
| `availability_text` | `str` | yes |
| `rating_text` | `str \| None` | no |
| `description` | `str \| None` | no |
| `source_page` | `str` (must start with `https://`) | yes |
| `fetched_at` | `str` (ISO 8601 UTC) | yes |

`product_url` is each record's canonical identity. Duplicates are dropped before validation. Records that fail validation are written to `output/errors.json` with the reason; they never reach `output/books.json`.

## Politeness rules

- **User-agent:** `FlyRankInternshipA9/1.0 (+https://github.com/myrmlbst/flyrank)` names the scraper and links back to this repo on every request.
- **Timeout:** every request gives up after 10 seconds.
- **Delay:** at least 0.5s between real requests to the site. Cached pages add no delay and they never leave the machine.
- **Cache:** every page is saved to `cache/` on first fetch and read from there on every later run, so the site is only asked once per page across an entire development session.
- **Retries:** a timeout or `5xx` gets one retry after a short wait. A `404` or `403` is never retried as the answer won't change, and retrying it is just noise on someone else's server.
- **Failure isolation:** each page is fetched independently; one failed page is logged and skipped, it never stops the rest of the run.

## Sample run-report.json

A real run, freshly generated, no injected failures:

```json
{
  "start_time": "2026-09-22T14:35:02Z",
  "duration_seconds": 115.95,
  "pages_fetched": 63,
  "cache_hits": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_page_details": []
}
```

## Why this needed no browser

All of this data (title, price, availability, rating, description) is already present in the HTML the server sends back on the very first response; nothing here is rendered or fetched afterward by client-side JavaScript. A browser would only add startup cost and memory for zero extra data.

## One honest limitation

Selectors are hand-written against the current markup (`div.product_main`, `#product_description ~ p`, etc.). If Books to Scrape ever restructures its HTML, extraction breaks silently field-by-field rather than failing loudly. Tthere's no schema-drift detection here, only post-hoc validation of what was actually extracted.

## Ethics note

Scrape only what's actually needed, and prefer an official API over scraping whenever one exists. It's the arrangement the site owner actually intended. Never bypass a login, a paywall, or a block; if a site says no, that's the end of it, not a puzzle to route around. And treat every site's terms and robots.txt as the first thing to check, not an afterthought. Permission is checked before code is written, not assumed because a request happens to succeed.
