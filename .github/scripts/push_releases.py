"""Push GitHub release metadata to the WordPress site."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

REPO = os.environ["REPO"]
WP_URL = os.environ["WP_URL"].rstrip("/")
WP_TOKEN = os.environ["WP_TOKEN"]
BUST_CACHE_FIRST = os.environ.get("BUST_CACHE_FIRST", "false").lower() == "true"
GH_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {
    "Content-Type": "application/json",
    "X-OGR-Token": WP_TOKEN,
}
GH_API_HEADERS: dict[str, str] = {
    "Accept": "application/vnd.github+json",
}
if GH_TOKEN:
    GH_API_HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"


def open_request(req: urllib.request.Request, timeout: int) -> Any:
    """Open a request, preserving POST data across temporary redirects."""
    redirects: list[str] = []
    for _ in range(5):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in {307, 308}:
                raise
            location = exc.headers.get("Location")
            if not location:
                raise
            next_url = urllib.parse.urljoin(req.full_url, location)
            parsed = urllib.parse.urlparse(next_url)
            redirects.append(f"{exc.code} {parsed.path or '/'}")
            req = urllib.request.Request(
                next_url,
                data=req.data,
                headers=dict(req.header_items()),
                method=req.get_method(),
            )
    chain = " -> ".join(redirects) if redirects else "none"
    msg = f"Too many redirects while pushing release metadata: {chain}"
    raise RuntimeError(msg)


def gh_json(endpoint: str, allow_missing: bool = False) -> Any:
    url = f"https://api.github.com/{endpoint}"
    request = urllib.request.Request(url, headers=GH_API_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if allow_missing and exc.code == 404:
            return None
        raise


def fetch_payload() -> dict[str, Any]:
    latest = gh_json(f"repos/{REPO}/releases/latest", allow_missing=True)
    all_releases = gh_json(f"repos/{REPO}/releases?per_page=20", allow_missing=True)
    if not isinstance(all_releases, list):
        all_releases = []
    return {
        "repo": REPO,
        "releases": all_releases[:20],
        "latest": latest if isinstance(latest, dict) and latest.get("tag_name") else None,
    }


def push_releases(payload: dict[str, Any]) -> dict[str, Any]:
    """Transmit release payload to the WordPress endpoint."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{WP_URL}/wp-json/ogr/v1/push-releases",
        data=data,
        headers=HEADERS,
        method="POST",
    )
    with open_request(req, timeout=30) as response:
        return json.load(response)


def bust_cache() -> dict[str, Any]:
    """Hit the optional bust-cache endpoint so the next push lands on fresh data."""
    req = urllib.request.Request(
        f"{WP_URL}/wp-json/ogr/v1/bust-cache",
        data=b"{}",
        headers=HEADERS,
        method="POST",
    )
    with open_request(req, timeout=20) as response:
        return json.load(response)


def main() -> None:
    payload = fetch_payload()

    def attempt() -> dict[str, Any]:
        return push_releases(payload)

    for attempt_num in range(2):
        try:
            result = attempt()
            print(f"Pushed {result['count']} releases for {result['repo']}")
            return
        except Exception:
            if attempt_num == 0:
                message = "First push attempt failed."
            else:
                message = "Second push attempt failed."
            print(message)
            if attempt_num == 0:
                if BUST_CACHE_FIRST:
                    print("Cache nudge enabled. Hitting bust-cache before retry...")
                    bust_result = bust_cache()
                    print("Cache nudge response:", bust_result)
                print("Retrying once in 10s...")
                time.sleep(10)
                continue
            raise


if __name__ == "__main__":
    main()
