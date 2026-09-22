from pathlib import Path

import requests

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/myrmlbst/flyrank)"
TIMEOUT_SECONDS = 10
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


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
    return response.text


def main():
    fetch("https://books.toscrape.com/", "catalogue-page-1.html")


if __name__ == "__main__":
    main()
