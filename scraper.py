"""
Playwright-based MFN scraper for the Tunisian Tarif Web 2025 portal.
Produces TariffMeasure rows (MFN DD + MFN TVA) and writes them via db.upsert_measures.
Checkpoint/resume is supported via data/scrape_checkpoint.json.
"""
import asyncio
import json
import re
import warnings
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from db import get_conn, ensure_schema, upsert_measures, DB_PATH
from schemas import TariffMeasure

PORTAL_URL = "https://www.tarif.finances.gov.tn/tarif/tarif2025.php"
CHECKPOINT_PATH = Path("data/scrape_checkpoint.json")
VALID_FROM = "2025-01-01"


def _normalise_hs(raw: str) -> Optional[str]:
    code = re.sub(r"\D", "", raw)
    return code if len(code) >= 2 else None


def _parse_rate(raw: str) -> Optional[float]:
    raw = raw.strip().rstrip("%").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text())
        except Exception:
            pass
    return {"last_chapter": -1, "total_rows": 0}


def _save_checkpoint(last_chapter: int, total_rows: int) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(
        json.dumps({"last_chapter": last_chapter, "total_rows": total_rows})
    )


async def _scrape_chapter(page, chapter_idx: int) -> list:
    """Click chapter at index and parse the resulting table. Returns TariffMeasure list."""
    try:
        chapters = await page.query_selector_all("a.chapitre, .chapter-link, td.chapitre a")
        if chapter_idx >= len(chapters):
            return []
        await chapters[chapter_idx].click()
        await page.wait_for_timeout(5000)
    except Exception as e:
        warnings.warn(f"_scrape_chapter: click failed at index {chapter_idx}: {e}")
        return []

    html = await page.content()
    return _parse_table_html(html)


def _parse_table_html(html: str) -> list:
    """Parse BeautifulSoup table rows into TariffMeasure objects. Uses lxml parser."""
    soup = BeautifulSoup(html, "lxml")
    measures = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        raw_hs = cells[0].get_text(strip=True)
        hs_code = _normalise_hs(raw_hs)
        if not hs_code:
            continue

        # Try to read DD (import duty) and TVA rates from columns
        # Portal layout: col0=HS, col1=description, col2=DD%, col3=TVA%
        dd_raw = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        tva_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""

        dd_rate = _parse_rate(dd_raw)
        tva_rate = _parse_rate(tva_raw)

        if dd_rate is not None:
            measures.append(TariffMeasure(
                hs_code=hs_code,
                origin_country="TN",
                duty_type="MFN",
                tax_type="DD",
                rate=dd_rate,
                valid_from=VALID_FROM,
            ))
        if tva_rate is not None:
            measures.append(TariffMeasure(
                hs_code=hs_code,
                origin_country="TN",
                duty_type="MFN",
                tax_type="TVA",
                rate=tva_rate,
                valid_from=VALID_FROM,
            ))

    return measures


async def scrape_mfn_full(
    max_chapters: Optional[int] = None,
    resume: bool = True,
    db_path=None,
    _page=None,  # injected in tests to avoid live browser
) -> list:
    """
    Scrape MFN duties from the Tunisian Tarif Web 2025 portal.

    Returns list[TariffMeasure]. Also writes rows to SQLite via db.upsert_measures.
    If result is empty, caller should activate fallback dataset (not done here).

    Args:
        max_chapters: limit number of chapters scraped (None = all).
        resume: if True, skip chapters already processed per checkpoint.
        db_path: override DB path (for testing).
        _page: pre-created Playwright page (injected in tests).
    """
    checkpoint = _load_checkpoint() if resume else {"last_chapter": -1, "total_rows": 0}
    start_chapter = checkpoint["last_chapter"] + 1
    all_measures: list = []

    if _page is not None:
        # Test / injection path: skip browser launch
        measures = await _scrape_with_page(_page, start_chapter, max_chapters, checkpoint)
        all_measures.extend(measures)
    else:
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--no-sandbox"], headless=True)
            page = await browser.new_page()
            await page.goto(PORTAL_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            measures = await _scrape_with_page(page, start_chapter, max_chapters, checkpoint)
            all_measures.extend(measures)
            await browser.close()

    if all_measures:
        path = db_path or DB_PATH
        conn = get_conn(path)
        ensure_schema(conn)
        upsert_measures(conn, all_measures)
        conn.close()

    return all_measures


async def _scrape_with_page(page, start_chapter: int, max_chapters: Optional[int], checkpoint: dict) -> list:
    """Drive page scraping loop, updating checkpoint after each chapter."""
    all_measures = []

    # Determine chapter count from page
    chapters = await page.query_selector_all("a.chapitre, .chapter-link, td.chapitre a")
    total_chapters = len(chapters) if chapters else 0

    if max_chapters is not None:
        end_chapter = min(start_chapter + max_chapters, total_chapters)
    else:
        end_chapter = total_chapters

    for idx in range(start_chapter, end_chapter):
        chapter_measures = await _scrape_chapter(page, idx)
        all_measures.extend(chapter_measures)
        _save_checkpoint(idx, checkpoint["total_rows"] + len(all_measures))

    return all_measures
