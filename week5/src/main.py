import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/myrmlbst/flyrank)"
TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
START_URL = "https://books.toscrape.com/"
MAX_CATALOGUE_PAGES = 3


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

    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    print(f"FETCH {url} ({len(response.text)} bytes)")
    time.sleep(REQUEST_DELAY_SECONDS)
    return response.text


def discover_catalogue_pages():
    page_url = START_URL
    book_urls = []

    for page_number in range(1, MAX_CATALOGUE_PAGES + 1):
        html = fetch(page_url, f"catalogue-page-{page_number}.html")
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.select("article.product_pod h3 a"):
            book_urls.append(urljoin(page_url, link["href"]))

        next_link = soup.select_one("li.next a")
        if not next_link:
            break
        page_url = urljoin(page_url, next_link["href"])

    unique_urls = list(dict.fromkeys(book_urls))
    print(
        f"catalogue_pages={MAX_CATALOGUE_PAGES} "
        f"discovered={len(book_urls)} unique_urls={len(unique_urls)}"
    )
    return unique_urls


def main():
    discover_catalogue_pages()


if __name__ == "__main__":
    main()
