"""Runs evals/cases.json against a live instance of the API and reports the score.

For each case: creates a real task via POST /tasks, judges it via
POST /tasks/{id}/priority, compares the returned priority to the expected
one, then deletes the task again. This hits the real model -- eight calls
against your daily quota per run.

Usage:
    BASE_URL=http://localhost:8001 python evals/run_evals.py
"""

import json
import os
import sys
from pathlib import Path

import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
CASES_PATH = Path(__file__).parent / "cases.json"


def main() -> None:
    cases = json.loads(CASES_PATH.read_text())
    results = []

    for case in cases:
        title = case["title"]
        expected = case["expected_priority"]

        created = requests.post(f"{BASE_URL}/tasks", json={"title": title})
        created.raise_for_status()
        task_id = created.json()["id"]

        try:
            judged = requests.post(f"{BASE_URL}/tasks/{task_id}/priority")
            if judged.status_code != 200:
                results.append({
                    "title": title, "expected": expected, "actual": None,
                    "ok": False, "detail": judged.text,
                })
                continue

            body = judged.json()
            actual = body["priority"]
            results.append({
                "title": title, "expected": expected, "actual": actual,
                "ok": actual == expected, "reasoning": body.get("reasoning"),
            })
        finally:
            requests.delete(f"{BASE_URL}/tasks/{task_id}")

    passed = sum(1 for r in results if r["ok"])
    total = len(results)

    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"[{mark}] {r['title']!r} -> expected={r['expected']} actual={r.get('actual')}")
        if not r["ok"]:
            print(f"       {r.get('detail') or r.get('reasoning')}")

    print(f"\nScore: {passed}/{total} ({passed / total:.0%})")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
