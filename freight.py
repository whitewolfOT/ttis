import warnings

USD_TO_TND: float = 3.12

# Unchanged from Sprint 1/2
ORIGIN_LABELS: dict = {
    "CN": "🇨🇳 China",
    "TR": "🇹🇷 Turkey",
    "FR": "🇫🇷 France",
    "DE": "🇩🇪 Germany",
    "IT": "🇮🇹 Italy",
    "ES": "🇪🇸 Spain",
    "IN": "🇮🇳 India",
    "KR": "🇰🇷 South Korea",
    "JP": "🇯🇵 Japan",
    "US": "🇺🇸 USA",
    "MA": "🇲🇦 Morocco",
    "DZ": "🇩🇿 Algeria",
    "EG": "🇪🇬 Egypt",
    "SA": "🇸🇦 Saudi Arabia",
    "AE": "🇦🇪 UAE",
    "BR": "🇧🇷 Brazil",
    "MX": "🇲🇽 Mexico",
    "PL": "🇵🇱 Poland",
    "BE": "🇧🇪 Belgium",
    "NL": "🇳🇱 Netherlands",
    "LY": "🇱🇾 Libya",
    "JO": "🇯🇴 Jordan",
    "VN": "🇻🇳 Vietnam",
}

LEAD_DAYS: dict = {
    "CN": 35,
    "TR": 10,
    "FR":  7,
    "DE":  7,
    "IT":  6,
    "ES":  7,
    "IN": 25,
    "KR": 28,
    "JP": 30,
    "US": 20,
    "MA":  4,
    "DZ":  4,
    "EG":  7,
    "SA": 10,
    "AE": 10,
    "BR": 30,
    "MX": 25,
    "PL":  8,
    "BE":  7,
    "NL":  7,
    "LY":  3,
    "JO":  6,
    "VN": 26,
}

# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------
MODE_SEA_FCL = "sea_fcl"
MODE_SEA_LCL = "sea_lcl"
MODE_AIR     = "air"
MODE_LAND    = "land"
MODE_OWN     = "own"
MODE_ALL     = "all"

# ---------------------------------------------------------------------------
# Land-accessible origins from Tunisia
# ---------------------------------------------------------------------------
LAND_ACCESSIBLE: dict = {
    "LY": {"route": "Direct border",              "extra_days": 0},
    "DZ": {"route": "Direct border",              "extra_days": 0},
    "MA": {"route": "Via Algeria",                "extra_days": 2},
    "EG": {"route": "Via Libya",                  "extra_days": 3},
    "NG": {"route": "Trans-African Highway",      "extra_days": 10},
    "GH": {"route": "Trans-African Highway",      "extra_days": 12},
    "SN": {"route": "Via Algeria/Mauritania",     "extra_days": 8},
    "CI": {"route": "Trans-African Highway",      "extra_days": 14},
    "CM": {"route": "Trans-African Highway",      "extra_days": 16},
}

# ---------------------------------------------------------------------------
# Currency flags
# ---------------------------------------------------------------------------
CURRENCY_FLAG: dict = {
    "CN": "USD/CNY", "TR": "TRY",  "MA": "MAD",  "EG": "EGP",
    "IT": "EUR",     "DE": "EUR",  "FR": "EUR",  "ES": "EUR",
    "NL": "EUR",     "BE": "EUR",  "IN": "INR",  "US": "USD",
    "JP": "JPY",     "KR": "KRW", "VN": "USD",  "BR": "BRL",
    "JO": "JOD",     "SA": "SAR", "AE": "AED",  "LY": "LYD",
    "PL": "PLN",     "DZ": "DZD",
}

# ---------------------------------------------------------------------------
# Supplier concentration risk
# ---------------------------------------------------------------------------
SUPPLIER_RISK: dict = {
    "CN": "HIGH",
    "TW": "HIGH",
    "RU": "HIGH",
}

# ---------------------------------------------------------------------------
# Freight benchmarks
# Source: Freightos FBX index + shipping line rate cards, June 2026
# Confidence: MEDIUM (market rates, not door-to-door quotes)
# ---------------------------------------------------------------------------
FREIGHT_BENCHMARKS: dict = {
    MODE_SEA_FCL: {
        "CN": {"min": 2800, "mid": 3500, "max": 4500, "days": 28},
        "TR": {"min":  600, "mid":  850, "max": 1200, "days":  5},
        "MA": {"min":  500, "mid":  700, "max":  900, "days":  4},
        "EG": {"min":  600, "mid":  900, "max": 1200, "days":  4},
        "IT": {"min":  600, "mid":  900, "max": 1200, "days":  3},
        "DE": {"min":  900, "mid": 1300, "max": 1700, "days":  7},
        "FR": {"min":  800, "mid": 1100, "max": 1400, "days":  5},
        "ES": {"min":  550, "mid":  800, "max": 1050, "days":  4},
        "NL": {"min":  900, "mid": 1200, "max": 1500, "days":  7},
        "BE": {"min":  900, "mid": 1200, "max": 1500, "days":  7},
        "IN": {"min": 1800, "mid": 2200, "max": 2800, "days": 18},
        "US": {"min": 3500, "mid": 4500, "max": 5500, "days": 18},
        "JP": {"min": 3200, "mid": 4000, "max": 5000, "days": 32},
        "KR": {"min": 2800, "mid": 3600, "max": 4500, "days": 30},
        "VN": {"min": 2500, "mid": 3200, "max": 4000, "days": 26},
        "BR": {"min": 4000, "mid": 5000, "max": 6500, "days": 22},
        "JO": {"min":  800, "mid": 1100, "max": 1400, "days":  6},
        "SA": {"min": 1000, "mid": 1400, "max": 1800, "days":  8},
        "AE": {"min": 1200, "mid": 1600, "max": 2100, "days": 10},
        "LY": {"min":  400, "mid":  600, "max":  800, "days":  3},
    },
    MODE_AIR: {
        "CN": {"min": 3.5, "mid": 5.0, "max": 7.0, "days": 3},
        "TR": {"min": 1.5, "mid": 2.5, "max": 3.5, "days": 1},
        "MA": {"min": 1.2, "mid": 2.0, "max": 3.0, "days": 1},
        "EG": {"min": 1.5, "mid": 2.5, "max": 3.5, "days": 1},
        "IT": {"min": 1.2, "mid": 2.0, "max": 2.8, "days": 1},
        "DE": {"min": 1.5, "mid": 2.5, "max": 3.5, "days": 1},
        "FR": {"min": 1.3, "mid": 2.2, "max": 3.0, "days": 1},
        "ES": {"min": 1.2, "mid": 2.0, "max": 2.8, "days": 1},
        "IN": {"min": 2.5, "mid": 3.5, "max": 5.0, "days": 2},
        "US": {"min": 4.0, "mid": 6.0, "max": 8.0, "days": 2},
        "JP": {"min": 4.0, "mid": 6.0, "max": 8.0, "days": 3},
        "KR": {"min": 3.5, "mid": 5.5, "max": 7.5, "days": 3},
        "AE": {"min": 2.0, "mid": 3.0, "max": 4.5, "days": 1},
        "SA": {"min": 2.0, "mid": 3.0, "max": 4.5, "days": 1},
    },
    MODE_SEA_LCL: {
        "CN": {"min":  55, "mid":  75, "max": 100, "days": 35},
        "TR": {"min":  25, "mid":  40, "max":  55, "days":  8},
        "MA": {"min":  20, "mid":  35, "max":  50, "days":  6},
        "IT": {"min":  25, "mid":  40, "max":  55, "days":  5},
        "DE": {"min":  30, "mid":  45, "max":  60, "days": 10},
        "FR": {"min":  28, "mid":  42, "max":  58, "days":  8},
        "ES": {"min":  22, "mid":  38, "max":  52, "days":  6},
        "IN": {"min":  40, "mid":  60, "max":  80, "days": 22},
    },
    MODE_LAND: {
        "LY": {"min":  800, "mid": 1200, "max": 1600, "days":  2},
        "DZ": {"min":  900, "mid": 1300, "max": 1700, "days":  3},
        "MA": {"min": 1500, "mid": 2000, "max": 2800, "days":  5},
        "EG": {"min": 1800, "mid": 2400, "max": 3200, "days":  6},
    },
}

# Kept for backward compatibility with tests/calc.py that call estimate_freight
# returning a plain float. The new primary API is estimate_freight returning dict.
# Legacy callers receive mid_usd as a float via the wrapper below.
_FREIGHT_FCL_LEGACY: dict = {k: v["mid"] for k, v in FREIGHT_BENCHMARKS[MODE_SEA_FCL].items()}


def estimate_freight(
    origin: str,
    weight_kg: float = 500,
    volume_cbm: float = 2.0,
    mode: str = MODE_SEA_FCL,
    own_quote_usd: float = None,
) -> "dict | list":
    """
    Returns dict (single mode) or list of dicts (MODE_ALL).

    Dict structure:
      {mode, min_usd, mid_usd, max_usd, transit_days, notes, is_own_quote}

    Rules:
    - own_quote_usd overrides all estimates when provided (any mode).
    - MODE_LAND excluded for origins not in LAND_ACCESSIBLE.
    - MODE_AIR calculated on weight_kg (rate per kg).
    - MODE_SEA_LCL calculated on volume_cbm (rate per CBM).
    - MODE_SEA_FCL is a flat container rate.
    - Floor: mid_usd never below 200 USD.
    """
    if own_quote_usd is not None:
        return {
            "mode": MODE_OWN,
            "min_usd": own_quote_usd,
            "mid_usd": own_quote_usd,
            "max_usd": own_quote_usd,
            "transit_days": LEAD_DAYS.get(origin, 21),
            "notes": "Own quote",
            "is_own_quote": True,
        }

    if mode == MODE_ALL:
        results = []
        for m in (MODE_SEA_FCL, MODE_SEA_LCL, MODE_AIR, MODE_LAND):
            if m == MODE_LAND and origin not in LAND_ACCESSIBLE:
                continue
            results.append(estimate_freight(origin, weight_kg, volume_cbm, m))
        return results

    return _calc_single(origin, weight_kg, volume_cbm, mode)


def _calc_single(origin: str, weight_kg: float, volume_cbm: float, mode: str) -> dict:
    if weight_kg <= 0 and volume_cbm <= 0:
        warnings.warn(
            f"estimate_freight: weight=0 and volume=0 for {origin}; using 200 USD floor"
        )

    if mode == MODE_LAND and origin not in LAND_ACCESSIBLE:
        warnings.warn(f"estimate_freight: land mode not available for {origin}; falling back to sea_fcl")
        mode = MODE_SEA_FCL

    benchmarks = FREIGHT_BENCHMARKS.get(mode, {})
    bm = benchmarks.get(origin)

    if bm is None:
        # Fallback: derive from FCL mid if known, else generic
        fcl_bm = FREIGHT_BENCHMARKS[MODE_SEA_FCL].get(origin)
        if fcl_bm:
            base_mid = fcl_bm["mid"]
            factor = {"sea_fcl": 1.0, "sea_lcl": 0.04, "air": 0.004, "land": 0.9}.get(mode, 1.0)
            mid = max(base_mid * factor, 200)
            return {
                "mode": mode,
                "min_usd": round(mid * 0.8, 2),
                "mid_usd": round(mid, 2),
                "max_usd": round(mid * 1.3, 2),
                "transit_days": LEAD_DAYS.get(origin, 21),
                "notes": f"Estimated from FCL benchmark (no direct {mode} data for {origin})",
                "is_own_quote": False,
            }
        mid = 200.0
        return {
            "mode": mode,
            "min_usd": 200.0,
            "mid_usd": 200.0,
            "max_usd": 300.0,
            "transit_days": LEAD_DAYS.get(origin, 21),
            "notes": f"No benchmark data for {origin}/{mode} — floor applied",
            "is_own_quote": False,
        }

    # Scale by shipment size for weight/volume-sensitive modes
    if mode == MODE_AIR:
        # rate per kg; floor 200 USD
        chargeable = max(weight_kg, 1.0)
        min_usd = max(bm["min"] * chargeable, 200.0)
        mid_usd = max(bm["mid"] * chargeable, 200.0)
        max_usd = max(bm["max"] * chargeable, 200.0)
    elif mode == MODE_SEA_LCL:
        # rate per CBM; floor 200 USD
        chargeable = max(volume_cbm, 1.0)
        min_usd = max(bm["min"] * chargeable, 200.0)
        mid_usd = max(bm["mid"] * chargeable, 200.0)
        max_usd = max(bm["max"] * chargeable, 200.0)
    else:
        # FCL and LAND: flat container/truck rate
        min_usd = max(float(bm["min"]), 200.0)
        mid_usd = max(float(bm["mid"]), 200.0)
        max_usd = max(float(bm["max"]), 200.0)

    land_note = ""
    if mode == MODE_LAND:
        info = LAND_ACCESSIBLE.get(origin, {})
        land_note = f" | Route: {info.get('route', 'unknown')}"

    return {
        "mode": mode,
        "min_usd": round(min_usd, 2),
        "mid_usd": round(mid_usd, 2),
        "max_usd": round(max_usd, 2),
        "transit_days": bm["days"],
        "notes": f"Freightos FBX / rate cards, June 2026{land_note}",
        "is_own_quote": False,
    }
