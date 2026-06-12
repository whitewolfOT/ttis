"""
Export market intelligence module.

STATUS: STUB — MacMap scraping blocked by environment egress policy.
www.macmap.org returns 403 (not in network allowlist).

Full implementation deferred to Sprint 4. Options to investigate:
  - Run poc_macmap.py from a machine with unrestricted egress
  - WITS API (World Bank): https://wits.worldbank.org/witsapiintro.aspx
  - WTO bulk tariff download: https://tao.wto.org

When MacMap becomes available:
  1. Set MACMAP_EMAIL + MACMAP_PASSWORD env vars
  2. Run poc_macmap.py to validate login + API
  3. Replace stubs with real implementation from SPRINT_3.md spec
"""

# African ISO-2 codes for AfCFTA flagging
# Note: Tunisia signed but has not yet ratified AfCFTA (as of June 2026)
AFRICAN_ISO2: set = {
    "AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM","CD","CG","CI",
    "DJ","EG","ET","GA","GH","GN","GW","KE","LS","LR","LY","MG","MW",
    "ML","MR","MU","MA","MZ","NA","NE","NG","RW","ST","SN","SL","SO",
    "ZA","SS","SD","SZ","TZ","TG","TN","UG","ZM","ZW",
}


def get_export_markets(
    conn,
    hs6: str,
    macmap_email: str = None,
    macmap_password: str = None,
    top_n: int = 50,
    africa_only: bool = False,
) -> list[dict]:
    """
    Return ranked export markets for a given HS6 from Tunisia's perspective.

    Logic (when implemented):
      1. Check export_tariffs table for cached data for this hs6
      2. Cache miss + credentials provided → scrape MacMap × all reporters,
         store in DB, then query
      3. Cache hit → return from DB directly

    Returns list of dicts sorted by tariff_rate ASC:
      {reporter_iso2, reporter_name, tariff_rate, tariff_regime,
       agreement_id, has_preference, mfn_rate, tariff_advantage,
       afcfta_flag, market_size_flag}

    STUB: returns [] until MacMap scraping is unblocked (Sprint 4).
    """
    return []


def get_competitor_comparison(
    conn,
    hs6: str,
    competitor_iso2: str,
    reporter_iso2: str,
) -> dict:
    """
    Compare the duty rate Tunisia faces vs a competitor in a given export market.

    Returns:
      {tunisia_rate, competitor_rate, advantage, has_advantage}

    STUB: returns placeholder dict until export_tariffs is populated (Sprint 4).
    """
    return {
        "tunisia_rate": None,
        "competitor_rate": None,
        "advantage": None,
        "has_advantage": False,
    }
