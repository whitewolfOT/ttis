"""
MacMap on-demand scraper for export tariff data.

Architecture: cache-on-demand. Never bulk-scrape.
- User queries HS6 → check export_tariffs table
- Cache miss + credentials provided → scrape MacMap × all reporters → store → return
- Cache hit → return from DB directly

Do NOT call this with max_chapters=None or bulk-loop all HS codes.
"""
import asyncio
import re
import time
import warnings
from datetime import date
from typing import Optional

import requests

MACMAP_URL = "https://www.macmap.org"
TUNISIA_PARTNER = "788"

REPORTER_COUNTRIES = {
    # Europe
    "251": "FR", "276": "DE", "380": "IT", "724": "ES", "826": "GB",
    "528": "NL", "056": "BE", "040": "AT", "620": "PT", "300": "GR",
    "752": "SE", "208": "DK", "246": "FI", "372": "IE", "442": "LU",
    # MENA
    "818": "EG", "504": "MA", "012": "DZ", "434": "LY", "400": "JO",
    "682": "SA", "784": "AE", "414": "KW", "048": "BH", "634": "QA",
    "512": "OM", "275": "PS", "422": "LB",
    # Asia
    "156": "CN", "356": "IN", "392": "JP", "410": "KR", "704": "VN",
    "792": "TR", "360": "ID", "458": "MY", "764": "TH",
    # Americas
    "840": "US", "076": "BR", "124": "CA", "484": "MX",
    # Africa
    "024": "AO", "204": "BJ", "120": "CM", "384": "CI", "231": "ET",
    "266": "GA", "288": "GH", "324": "GN", "404": "KE", "430": "LR",
    "450": "MG", "454": "MW", "466": "ML", "478": "MR", "480": "MU",
    "508": "MZ", "516": "NA", "562": "NE", "566": "NG", "646": "RW",
    "686": "SN", "694": "SL", "710": "ZA", "728": "SS", "736": "SD",
    "748": "SZ", "834": "TZ", "768": "TG", "800": "UG", "894": "ZM",
    "716": "ZW", "132": "CV", "174": "KM", "678": "ST",
}

_API_BASE = "https://www.macmap.org/api/custom-duties-by-year"


async def login_macmap(email: str, password: str) -> dict:
    """
    Log into MacMap via Playwright. Return cookies as dict.
    Raises RuntimeError if login fails or credentials are empty.
    """
    if not email or not password:
        raise RuntimeError("login_macmap: MACMAP_EMAIL and MACMAP_PASSWORD must be set")

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--no-sandbox"], headless=True)
        page = await browser.new_page()

        await page.goto(MACMAP_URL, timeout=60000)
        await page.wait_for_timeout(2000)

        # Find and click sign-in link
        signin = await page.query_selector("a[href*='signin'], a[href*='login'], button:has-text('Sign'), a:has-text('Sign')")
        if not signin:
            await browser.close()
            raise RuntimeError("login_macmap: could not find sign-in element on MacMap homepage")

        await signin.click()
        await page.wait_for_timeout(2000)

        # Fill credentials
        await page.fill("input[type='email'], input[name='email']", email)
        await page.fill("input[type='password'], input[name='password']", password)
        await page.press("input[type='password']", "Enter")
        await page.wait_for_timeout(4000)

        # Check for authenticated state
        url = page.url
        if "error" in url.lower() or "invalid" in url.lower():
            await browser.close()
            raise RuntimeError(f"login_macmap: login failed — landed at {url}")

        cookies_list = await page.context.cookies()
        cookies = {c["name"]: c["value"] for c in cookies_list}
        await browser.close()

    if not cookies:
        raise RuntimeError("login_macmap: no cookies returned after login")

    return cookies


def fetch_export_tariffs_for_hs6(
    hs6: str,
    cookies: dict,
    reporters: dict = None,
    year: int = 2026,
    delay: float = 0.2,
) -> list[dict]:
    """
    For one HS6 code, query MacMap API for all reporter countries.
    Uses requests.Session with provided cookies (faster than Playwright).

    Returns list of dicts:
      {reporter_code, reporter_iso2, reporter_name, hs6, rate,
       tariff_regime, agreement_id, year, scraped_at}

    Handles:
      - Empty response  → skip silently
      - HTML redirect   → RuntimeError("session expired")
      - 429 rate-limit  → warns and skips remaining reporters
    """
    if reporters is None:
        reporters = REPORTER_COUNTRIES

    session = requests.Session()
    for name, value in cookies.items():
        session.cookies.set(name, value)

    session.headers.update({
        "Accept": "application/json",
        "Referer": MACMAP_URL,
    })

    results = []
    today = str(date.today())

    for reporter_code, reporter_iso2 in reporters.items():
        # MacMap product code is HS6 padded to 10 digits with trailing zeros
        product_code = hs6.ljust(10, "0")[:10]
        url = (
            f"{_API_BASE}"
            f"?reporter={reporter_code}"
            f"&partner={TUNISIA_PARTNER}"
            f"&product={product_code}"
            f"&year={year}"
        )

        try:
            resp = session.get(url, timeout=15)
        except requests.RequestException as e:
            warnings.warn(f"fetch_export_tariffs_for_hs6: request error for {reporter_code}: {e}")
            continue

        if resp.status_code == 429:
            warnings.warn(f"fetch_export_tariffs_for_hs6: rate-limited (429) at reporter {reporter_code} — stopping")
            break

        if resp.status_code != 200:
            warnings.warn(f"fetch_export_tariffs_for_hs6: HTTP {resp.status_code} for reporter {reporter_code}")
            continue

        # Detect HTML redirect (session expired)
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type:
            raise RuntimeError("fetch_export_tariffs_for_hs6: session expired — re-login required")

        try:
            payload = resp.json()
        except ValueError:
            warnings.warn(f"fetch_export_tariffs_for_hs6: non-JSON response for {reporter_code}")
            continue

        # Normalise response — MacMap may return dict or list
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("results") or []
            if not items and "rate" in payload:
                items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        for item in items:
            rate = item.get("rate") or item.get("duty_rate") or item.get("appliedRate")
            try:
                rate_float = float(re.sub(r"[^0-9.]", "", str(rate))) if rate is not None else None
            except (ValueError, TypeError):
                rate_float = None

            results.append({
                "reporter_code": reporter_code,
                "reporter_iso2": reporter_iso2,
                "reporter_name": item.get("reporterName") or item.get("reporter") or reporter_iso2,
                "hs6": hs6,
                "rate": rate_float,
                "tariff_regime": item.get("tariffRegime") or item.get("regime"),
                "agreement_id": item.get("agreementId") or item.get("agreement"),
                "year": year,
                "scraped_at": today,
            })

        time.sleep(delay)

    return results
