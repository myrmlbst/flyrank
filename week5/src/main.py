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
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
START_URL = "https://books.toscrape.com/"
MAX_CATALOGUE_PAGES = 3
PRICE_PATTERN = re.compile(r"[\d.]+")


def fetch(url: str, cache_filename: str) -> str:
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT {url} ({len(html)} bytes)")
        return html

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise RuntimeError(f"fetch failed: {url} -> status {response.status_code}")
    response.encoding = "utf-8"

    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    print(f"FETCH {url} ({len(response.text)} bytes)")
    time.sleep(REQUEST_DELAY_SECONDS)
    return response.text


def discover_catalogue_pages():
    page_url = START_URL
    books = []
    seen_urls = set()

    for page_number in range(1, MAX_CATALOGUE_PAGES + 1):
        html = fetch(page_url, f"catalogue-page-{page_number}.html")
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


def extract_book(book_url: str, source_page: str) -> dict:
    html = fetch(book_url, book_cache_filename(book_url))
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


def main():
    books = discover_catalogue_pages()

    raw_records = [extract_book(book["url"], book["source_page"]) for book in books]
    print(f"detail_pages={len(raw_records)}")

    good_records, error_records = validate_and_store(raw_records)
    print(f"valid_records={len(good_records)} invalid_records={len(error_records)}")


if __name__ == "__main__":
    main()
