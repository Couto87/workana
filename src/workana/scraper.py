"""Scrape Workana job listings and store them in SQLite."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from html import unescape
from typing import Dict, Iterable, List

import requests
from bs4 import BeautifulSoup

from .db import DEFAULT_DB, connect, init_db, upsert_project

BASE = "https://www.workana.com"
START_URL = os.environ.get(
    "WORKANA_START_URL",
    "https://www.workana.com/jobs?agreement=fixed&language=en%2Cpt%2Ces",
)
MAX_PAGES = int(os.environ.get("WORKANA_MAX_PAGES", "3"))
SLEEP = float(os.environ.get("WORKANA_SLEEP", "1.0"))

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": START_URL,
    "User-Agent": os.environ.get(
        "WORKANA_USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
    ),
}


# Helpers -----------------------------------------------------------------

def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def clean_html_to_text(s: str) -> str:
    if not s:
        return ""
    text = BeautifulSoup(s, "lxml").get_text(" ", strip=True)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_page(url: str) -> Dict:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def skill_list(raw_skills: Iterable[Dict]) -> List[str]:
    skills: List[str] = []
    for sk in raw_skills or []:
        name = (sk.get("anchorText") or "").strip()
        if name:
            skills.append(name)
    return skills


# Public entry point ------------------------------------------------------

def run(db_path: str = DEFAULT_DB) -> int:
    conn = connect(db_path)
    init_db(db_path)

    page_url = START_URL
    new_items = 0

    for page in range(1, MAX_PAGES + 1):
        if "page=" not in page_url:
            sep = "&" if "?" in page_url else "?"
            page_url = f"{page_url}{sep}page={page}"

        data = fetch_page(page_url)
        results = (data.get("results") or {})
        items = results.get("results") or []
        pagination = results.get("pagination") or {}

        for it in items:
            slug = (it.get("slug") or "").strip()
            if not slug:
                continue
            url = f"{BASE}/job/{slug}"
            id_hash = sha(url)

            titulo = clean_html_to_text(it.get("title") or "")
            descricao = clean_html_to_text(it.get("description") or "")
            budget = (it.get("budget") or "").strip()
            posted = (it.get("publishedDate") or it.get("postedDate") or "").strip()
            country = clean_html_to_text(it.get("country") or "")
            skills = ", ".join(skill_list(it.get("skills")))

            upsert_project(
                conn,
                {
                    "workana_id_hash": id_hash,
                    "slug": slug,
                    "url": url,
                    "titulo": titulo[:300],
                    "descricao": descricao[:20000],
                    "budget": budget[:120],
                    "postedDate": posted[:120],
                    "country": country[:120],
                    "skills": skills[:1000],
                    "raw_json": json.dumps(it, ensure_ascii=False),
                },
            )
            new_items += 1

        next_url = ((pagination.get("urls") or {}).get("next")) or ""
        page_url = next_url or START_URL
        time.sleep(SLEEP)

    conn.close()
    return new_items


if __name__ == "__main__":
    added = run()
    print(f"Scraper finalizado. Novos itens: {added}")
