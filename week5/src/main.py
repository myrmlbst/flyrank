import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from schema import Book

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/myrmlbst/flyrank)"
TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
RETRY_WAIT_SECONDS = 1
MAX_ATTEMPTS = 2
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
START_URL = "https://books.toscrape.com/"
MAX_CATALOGUE_PAGES = 3
PRICE_PATTERN = re.compile(r"[\d.]+")
BROKEN_TEST_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_0000/index.html"


class FetchError(Exception):
    pass


def fetch(url: str, cache_filename: str, stats: dict) -> str:
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        stats["cache_hits"] += 1
        print(f"CACHE HIT {url} ({len(html)} bytes)")
        return html

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.exceptions.Timeout:
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_WAIT_SECONDS)
                continue
            raise FetchError(f"{url} -> timeout after {attempt} attempts")

        if response.status_code == 200:
            response.encoding = "utf-8"
            CACHE_DIR.mkdir(exist_ok=True)
            cache_path.write_text(response.text, encoding="utf-8")
            stats["pages_fetched"] += 1
            print(f"FETCH {url} ({len(response.text)} bytes)")
            time.sleep(REQUEST_DELAY_SECONDS)
            return response.text

        if response.status_code >= 500 and attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS)
            continue

        raise FetchError(f"{url} -> status {response.status_code}")

    raise FetchError(f"{url} -> exhausted retries")


def discover_catalogue_pages(stats: dict, failed_pages: list[dict]) -> list[dict]:
    page_url = START_URL
    books = []
    seen_urls = set()

    for page_number in range(1, MAX_CATALOGUE_PAGES + 1):
        try:
            html = fetch(page_url, f"catalogue-page-{page_number}.html", stats)
        except FetchError as error:
            print(f"FAILED {error}")
            failed_pages.append({"url": page_url, "reason": str(error)})
            stats["failed_pages"] += 1
            break

        soup = BeautifulSoup(html, "html.parser")

        for link in soup.select("article.product_pod h3 a"):
            book_url = urljoin(page_url, link["href"])
            if book_url not in seen_urls:
                seen_urls.add(book_url)
                books.append({"url": book_url, "source_page": page_url})

        next_link = soup.select_one("li.next a")
        if not next_link:
            break
        page_url = urljoin(page_url, next_link["href"])

    print(
        f"catalogue_pages={MAX_CATALOGUE_PAGES} "
        f"discovered={len(books)} unique_urls={len(seen_urls)}"
    )
    return books


def book_cache_filename(book_url: str) -> str:
    segments = [s for s in urlparse(book_url).path.split("/") if s]
    slug = segments[-2] if len(segments) >= 2 else segments[-1]
    return f"book-{slug}.html"


def extract_book(book_url: str, source_page: str, stats: dict) -> dict:
    html = fetch(book_url, book_cache_filename(book_url), stats)
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("div.product_main")

    title = product_main.select_one("h1").get_text(strip=True)
    price_text = product_main.select_one("p.price_color").get_text(strip=True)
    availability_text = " ".join(
        product_main.select_one("p.availability").get_text(strip=True).split()
    )

    rating_p = product_main.select_one("p.star-rating")
    rating_classes = rating_p["class"]
    rating_text = rating_classes[1] if len(rating_classes) > 1 else None

    description_p = soup.select_one("#product_description ~ p")
    description = description_p.get_text(strip=True) if description_p else None

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def extract_all_books(books: list[dict], stats: dict, failed_pages: list[dict]) -> list[dict]:
    raw_records = []
    for book in books:
        try:
            raw_records.append(extract_book(book["url"], book["source_page"], stats))
        except FetchError as error:
            print(f"FAILED {error}")
            failed_pages.append({"url": book["url"], "reason": str(error)})
            stats["failed_pages"] += 1
    return raw_records


def normalize_price(price_text: str) -> float:
    match = PRICE_PATTERN.search(price_text)
    if not match:
        raise ValueError(f"no numeric price found in {price_text!r}")
    return float(match.group())


def validate_and_store(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    seen_urls = set()
    good_records = []
    error_records = []

    for raw in raw_records:
        product_url = raw["product_url"]
        if product_url in seen_urls:
            continue
        seen_urls.add(product_url)

        try:
            price_gbp = normalize_price(raw["price_text"])
            book = Book(**{**raw, "price_gbp": price_gbp})
            good_records.append(book.model_dump())
        except (ValueError, ValidationError) as error:
            error_records.append({"record": raw, "reason": str(error)})

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "books.json").write_text(
        json.dumps(good_records, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(error_records, indent=2), encoding="utf-8"
    )

    return good_records, error_records


def write_run_report(start_time: datetime, stats: dict, good_records: list, error_records: list, failed_pages: list[dict]) -> dict:
    end_time = datetime.now(timezone.utc)
    report = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(good_records),
        "invalid_records": len(error_records),
        "failed_pages": stats["failed_pages"],
        "failed_page_details": failed_pages,
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "run-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inject-broken-url",
        action="store_true",
        help="Append one made-up book URL to prove one bad page can't take down the run.",
    )
    args = parser.parse_args()

    start_time = datetime.now(timezone.utc)
    stats = {"pages_fetched": 0, "cache_hits": 0, "failed_pages": 0}
    failed_pages = []

    books = discover_catalogue_pages(stats, failed_pages)

    if args.inject_broken_url:
        books.append({"url": BROKEN_TEST_URL, "source_page": START_URL})

    raw_records = extract_all_books(books, stats, failed_pages)
    print(f"detail_pages={len(raw_records)}")

    good_records, error_records = validate_and_store(raw_records)
    print(f"valid_records={len(good_records)} invalid_records={len(error_records)}")

    report = write_run_report(start_time, stats, good_records, error_records, failed_pages)
    print(f"failed_pages={report['failed_pages']}")


if __name__ == "__main__":
    main()
