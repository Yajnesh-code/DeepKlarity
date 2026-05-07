import json
import re
from typing import Any

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class ScrapeError(RuntimeError):
    pass


def scrape_recipe_page(url: str) -> dict[str, Any]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 403:
            raise ScrapeError(
                "This recipe website blocked the scraper request. "
                "Try another recipe URL or use a site that allows server-side scraping."
            )
        response.raise_for_status()
    except ScrapeError:
        raise
    except requests.RequestException as exc:
        raise ScrapeError(f"Could not fetch URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "form"]):
        tag.decompose()

    recipe_json = _extract_recipe_json_ld(response.text)
    title = (
        (recipe_json or {}).get("name")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
        or (soup.title.get_text(" ", strip=True) if soup.title else "Untitled recipe")
    )
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text) < 200 and not recipe_json:
        raise ScrapeError("The page did not contain enough readable recipe content.")

    return {
        "url": url,
        "title_hint": title,
        "text": text[:14000],
        "json_ld": recipe_json or {},
    }


def _extract_recipe_json_ld(html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        recipe = _find_recipe(payload)
        if recipe:
            return recipe
    return None


def _find_recipe(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list):
        for item in value:
            found = _find_recipe(item)
            if found:
                return found
    if isinstance(value, dict):
        kind = value.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if any(str(item).lower() == "recipe" for item in kinds):
            return value
        graph = value.get("@graph")
        if graph:
            return _find_recipe(graph)
    return None
