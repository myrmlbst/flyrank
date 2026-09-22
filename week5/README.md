# Week 5: The Polite Scraper

## 0. Target Classification

- **Site:** [books.toscrape.com](https://books.toscrape.com), run by [toscrape.com](https://toscrape.com), a "Web Scraping Sandbox." Its own page describes it as "a fictional bookstore that desperately wants to be scraped... a safe place for beginners learning web scraping." That sentence is the permission this assignment relies on.
- **Scope:** the first 3 catalogue pages only (`page-1.html` through `page-3.html`), and the ~60 individual book pages linked from them. No other pages, and no other site, are touched.
- **robots.txt result:** `GET https://books.toscrape.com/robots.txt` → **404 Not Found**. No robots file found. A missing file is not permission, permission here comes from the site's own stated purpose as a public scraping sandbox, not from the absence of a robots.txt.

I will not reuse this code on another site without checking its rules and terms first.
