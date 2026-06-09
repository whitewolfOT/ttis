"""
Scraper smoke test — no live portal, no browser.
Uses a mock Playwright page that returns pre-baked HTML.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scraper import scrape_mfn_full, _parse_table_html, _normalise_hs, _parse_rate


# --- unit tests for pure helpers ---

def test_normalise_hs_strips_non_digits():
    assert _normalise_hs("8541.40") == "854140"
    assert _normalise_hs("85 41 40") == "854140"


def test_normalise_hs_rejects_short():
    assert _normalise_hs("8") is None
    assert _normalise_hs("") is None


def test_parse_rate_percent_sign():
    assert _parse_rate("25%") == 25.0
    assert _parse_rate("0") == 0.0
    assert _parse_rate("n/a") is None


def test_parse_table_html_extracts_measures():
    html = """
    <html><body><table>
      <tr><td>854140</td><td>Solar panels</td><td>25%</td><td>19%</td></tr>
      <tr><td>870321</td><td>Motor cars</td><td>30%</td><td>19%</td></tr>
      <tr><td>short</td><td>bad row</td><td></td></tr>
    </table></body></html>
    """
    measures = _parse_table_html(html)
    hs_codes = [m.hs_code for m in measures]
    assert "854140" in hs_codes
    assert "870321" in hs_codes
    # Each valid row produces DD + TVA = 2 measures
    assert len([m for m in measures if m.hs_code == "854140"]) == 2


# --- integration smoke test with mocked page ---

class MockPage:
    """Minimal async mock of a Playwright page that returns zero chapters (immediate exit)."""

    async def query_selector_all(self, selector):
        return []  # no chapters → loop body never executes

    async def content(self):
        return "<html><body></body></html>"

    async def wait_for_timeout(self, ms):
        pass

    async def goto(self, url, **kwargs):
        pass


def test_scrape_mfn_full_mock_no_chapters(tmp_path):
    """With zero chapters on the mock page, scrape_mfn_full must return [] without error."""
    page = MockPage()
    result = asyncio.run(
        scrape_mfn_full(max_chapters=1, resume=False, db_path=str(tmp_path / "t.db"), _page=page)
    )
    assert isinstance(result, list)
    assert result == []


class MockPageOneChapter:
    """Mock page that exposes one chapter and returns a table with two HS codes."""

    _HTML = """
    <html><body><table>
      <tr><td>854140</td><td>Solar</td><td>25%</td><td>19%</td></tr>
      <tr><td>847130</td><td>Laptop</td><td>8%</td><td>19%</td></tr>
    </table></body></html>
    """

    def __init__(self):
        self._chapter = AsyncMock()
        self._chapter.click = AsyncMock()

    async def query_selector_all(self, selector):
        return [self._chapter]

    async def content(self):
        return self._HTML

    async def wait_for_timeout(self, ms):
        pass


def test_scrape_mfn_full_mock_one_chapter(tmp_path):
    """Mock page with one chapter returns expected TariffMeasure rows and writes to DB."""
    page = MockPageOneChapter()
    result = asyncio.run(
        scrape_mfn_full(max_chapters=1, resume=False, db_path=str(tmp_path / "t.db"), _page=page)
    )
    assert len(result) >= 2  # at least DD rows
    hs_codes = {m.hs_code for m in result}
    assert "854140" in hs_codes
    assert "847130" in hs_codes
    # Verify all rows have correct origin + duty_type
    for m in result:
        assert m.origin_country == "TN"
        assert m.duty_type == "MFN"
