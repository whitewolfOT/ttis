# TTIS: Sprint 3 — Global Export Intelligence + Freight Overhaul

**Read CLAUDE.md fully. Read SESSION_STATE.md fully. Confirm understanding before writing any code.**

---

## Vision reminder

This is not a duty calculator. It is a trade intelligence platform for Tunisian importers
and exporters. Every feature must answer a real business question:
- Importer: "Where should I source this product and what will it really cost me?"
- Exporter: "Where can I sell this and where does Tunisia have a tariff advantage?"

---

## Session config

- **Mode:** Token-efficient. No prose, code and results only.
- **Stack:** Python modules + SQLite + Jupyter ipywidgets. No web framework this sprint.
- **Commit message:** `feat: export intelligence, freight overhaul, working capital (Sprint 3)`

---

## Stop-on-error rule

If any step raises an unexpected exception, stop, report exact error in one line,
do not attempt to fix it, wait for instructions.

---

## Critical architecture decisions (read before writing any code)

### 1. MacMap: on-demand with cache, NOT bulk pre-scrape

DO NOT bulk scrape 17,508 HS codes × 80 countries = 1.4M requests (~78 hours).

The correct architecture:
- User queries an HS6 in the Export Markets tab
- System checks if export_tariffs already has data for that HS6
- Cache hit → return instantly from DB
- Cache miss → scrape MacMap for that HS6 × all reporters (~15 seconds), store, return

This fills the cache organically based on real usage. A user who needs 20 products
gets 20 × 80 = 1,600 requests (~5 minutes total, spread across sessions).

### 2. Prove MacMap scraping works BEFORE building the full exporter tab

Step 2 is a proof-of-concept that MUST pass before Steps 5-6 are written.
If MacMap blocks the scraper, the exporter tab falls back to a "data not available"
message and Sprint 4 addresses it differently.

### 3. Freight metadata from day one

Every freight benchmark must store: source, effective_date, confidence_level.
Hardcoded is fine for MVP but structured hardcoding only.

### 4. Break-even chart: cache calculations

The break-even chart computes landed cost at N EXW points × M origins.
Cache results in a dict keyed by (hs, origin, exw) to avoid recomputation on re-render.

### 5. Free zone tab: placeholder only

Free zone analysis requires: re-export %, transformation level, investor status.
These inputs don't exist yet. Mark as placeholder with explanation. Do not build rules.

### 6. Supplier risk + currency: flags only this sprint

Add as simple flag columns in the output, not full models:
- supplier_risk: "HIGH" if single-country dependency >80% of global supply
- currency_flag: "EUR" | "USD" | "TRY" | "CNY" per origin

---

## Context — what exists

Sprint 1+2 modules at repo root: schemas.py, db.py, fallback.py, agreements.py,
resolver.py, freight.py, calc.py, search.py, scraper.py, dashboard.py.
18 tests passing. DB has 17,508 Tunisian import HS codes, 213,058 preferential rows.
Dashboard has 2 working tabs: Sourcing, Legal Paths.

---

## New DB tables (add to db.py ensure_schema)

```sql
CREATE TABLE IF NOT EXISTS export_tariffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hs6 TEXT,
    reporter_code TEXT,
    reporter_name TEXT,
    reporter_iso2 TEXT,
    rate REAL,
    tariff_regime TEXT,
    agreement_id TEXT,
    year INTEGER,
    scraped_at DATE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_export_tariffs
    ON export_tariffs(hs6, reporter_code, year);

CREATE TABLE IF NOT EXISTS freight_benchmarks (
    origin_iso2 TEXT,
    mode TEXT,
    min_usd REAL,
    mid_usd REAL,
    max_usd REAL,
    transit_days INTEGER,
    source TEXT,
    effective_date DATE,
    confidence TEXT,
    PRIMARY KEY (origin_iso2, mode)
);

CREATE TABLE IF NOT EXISTS duty_suspensions (
    hs_code TEXT PRIMARY KEY,
    description TEXT,
    legal_basis TEXT,
    beneficiary TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS antidumping_measures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_code TEXT,
    origin_country TEXT,
    measure_type TEXT,
    additional_rate REAL,
    valid_from DATE,
    valid_to DATE,
    legal_reference TEXT
);
```

---

## Step 0 — Pre-flight

```
1. pytest tests/ -q — must be 18+ passing. Stop if failures.
2. python3 -c "from resolver import resolve_duty; print('OK')"
3. python3 -c "import sqlite3; c=sqlite3.connect('tunisia_trade.db'); print(c.execute('SELECT COUNT(*) FROM tariff_measures').fetchone())"
```

Report: pytest N passed | resolver OK | DB N rows. Stop if any fail.

---

## Step 1 — Update `db.py` with new tables

Add the four CREATE TABLE statements above to `ensure_schema()`.
Schema only — no data inserted.

**Verification:**
```bash
python3 -c "
from db import get_conn, ensure_schema
c = get_conn('/tmp/t3.db')
ensure_schema(c)
tables = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
assert 'export_tariffs' in tables
assert 'freight_benchmarks' in tables
assert 'duty_suspensions' in tables
assert 'antidumping_measures' in tables
print('PASS:', tables)
"
```

**Stop point:** Report PASS/FAIL. Wait before Step 2.

---

## Step 2 — MacMap proof-of-concept (CRITICAL GATE)

**This step must pass before Steps 5-6 are written.**
If this step fails or is blocked, skip to Step 3 and note in SESSION_STATE.

**File:** `macmap_scraper.py`

**Part A — Login and extract cookies:**

```python
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

async def login_macmap(email: str, password: str) -> dict:
    """
    Log into MacMap via Playwright. Return cookies as dict.
    Navigate to macmap.org → find sign-in → fill credentials → wait for
    authenticated page → extract all cookies.
    Raise RuntimeError if login fails.
    """

async def fetch_export_tariffs_for_hs6(
    hs6: str,
    cookies: dict,
    reporters: dict = REPORTER_COUNTRIES,
    year: int = 2026,
    delay: float = 0.2,
) -> list[dict]:
    """
    For one HS6 code, query MacMap API for all reporter countries.
    Uses requests.Session with provided cookies (faster than Playwright).
    API: GET /api/custom-duties-by-year?reporter={code}&partner=788&product={hs6}0000&year={year}
    Returns list of parsed tariff rows.
    Handles: empty response, HTML redirect (session expired), rate limit (429).
    """
```

**Part B — Proof-of-concept test (run interactively, not in pytest):**

```python
# poc_macmap.py — run this manually to validate before scaling
import asyncio
import os
from macmap_scraper import login_macmap, fetch_export_tariffs_for_hs6

EMAIL = os.environ.get("MACMAP_EMAIL", "")
PASSWORD = os.environ.get("MACMAP_PASSWORD", "")

async def test_poc():
    print("Step 1: Login...")
    cookies = await login_macmap(EMAIL, PASSWORD)
    print(f"  Got {len(cookies)} cookies")

    print("Step 2: Fetch 1 HS6 × 3 countries...")
    results = await fetch_export_tariffs_for_hs6(
        "010121",  # live horses
        cookies,
        reporters={"251": "FR", "840": "US", "818": "EG"},
        delay=0.5,
    )
    print(f"  Got {len(results)} rows")
    for r in results:
        print(f"  {r['reporter_name']}: {r['rate']}% ({r['tariff_regime']})")

    print("Step 3: Check session still valid after 60s gap...")
    import time; time.sleep(60)
    results2 = await fetch_export_tariffs_for_hs6(
        "847130", cookies,
        reporters={"251": "FR"},
        delay=0.5,
    )
    print(f"  Session valid: {len(results2) > 0}")

asyncio.run(test_poc())
```

Create `poc_macmap.py` with this content.

**Verification:**
```bash
python3 -c "from macmap_scraper import login_macmap, fetch_export_tariffs_for_hs6, REPORTER_COUNTRIES; print(len(REPORTER_COUNTRIES), 'reporters — import OK')"
```

**DECISION GATE:**
- If `poc_macmap.py` runs successfully → proceed to Steps 3-6 as written
- If MacMap blocks login or API → add to SESSION_STATE: "MacMap scraping blocked — exporter tab shows placeholder, Sprint 4 to investigate alternative (WITS API / WTO bulk download)"
- Do NOT attempt to work around anti-bot measures

**Stop point:** Report: import PASS/FAIL + poc result (success/blocked/untested). Wait before Step 3.

---

## Step 3 — `freight.py` overhaul

Replace `estimate_freight` with multi-mode, range-based version.
Keep `ORIGIN_LABELS`, `LEAD_DAYS`, `USD_TO_TND` unchanged.

```python
MODE_SEA_FCL = "sea_fcl"
MODE_SEA_LCL = "sea_lcl"
MODE_AIR     = "air"
MODE_LAND    = "land"
MODE_OWN     = "own"
MODE_ALL     = "all"

# Land-accessible origins from Tunisia (direct border or viable corridor)
LAND_ACCESSIBLE = {
    "LY": {"route": "Direct border", "extra_days": 0},
    "DZ": {"route": "Direct border", "extra_days": 0},
    "MA": {"route": "Via Algeria", "extra_days": 2},
    "EG": {"route": "Via Libya", "extra_days": 3},
    "NG": {"route": "Trans-African Highway", "extra_days": 10},
    "GH": {"route": "Trans-African Highway", "extra_days": 12},
    "SN": {"route": "Via Algeria/Mauritania", "extra_days": 8},
    "CI": {"route": "Trans-African Highway", "extra_days": 14},
    "CM": {"route": "Trans-African Highway", "extra_days": 16},
}

# Currency flags per origin
CURRENCY_FLAG = {
    "CN": "USD/CNY", "TR": "TRY", "MA": "MAD", "EG": "EGP",
    "IT": "EUR", "DE": "EUR", "FR": "EUR", "ES": "EUR", "NL": "EUR",
    "BE": "EUR", "IN": "INR", "US": "USD", "JP": "JPY", "KR": "KRW",
    "VN": "USD", "BR": "BRL", "JO": "JOD", "SA": "SAR", "AE": "AED",
    "LY": "LYD",
}

# Supplier concentration risk flag
# HIGH = product heavily concentrated in one country globally
SUPPLIER_RISK = {
    "CN": "HIGH",   # dominant supplier for most manufactured goods
    "TW": "HIGH",   # semiconductors
    "RU": "HIGH",   # certain raw materials
}

FREIGHT_BENCHMARKS = {
    # Sea FCL 20ft container port-to-port USD, transit days
    # Source: Freightos FBX index + shipping line rate cards, June 2026
    # Confidence: MEDIUM (market rates, not door-to-door quotes)
    MODE_SEA_FCL: {
        "CN": {"min": 2800, "mid": 3500, "max": 4500, "days": 28},
        "TR": {"min": 600,  "mid": 850,  "max": 1200, "days": 5},
        "MA": {"min": 500,  "mid": 700,  "max": 900,  "days": 4},
        "EG": {"min": 600,  "mid": 900,  "max": 1200, "days": 4},
        "IT": {"min": 600,  "mid": 900,  "max": 1200, "days": 3},
        "DE": {"min": 900,  "mid": 1300, "max": 1700, "days": 7},
        "FR": {"min": 800,  "mid": 1100, "max": 1400, "days": 5},
        "ES": {"min": 550,  "mid": 800,  "max": 1050, "days": 4},
        "NL": {"min": 900,  "mid": 1200, "max": 1500, "days": 7},
        "BE": {"min": 900,  "mid": 1200, "max": 1500, "days": 7},
        "IN": {"min": 1800, "mid": 2200, "max": 2800, "days": 18},
        "US": {"min": 3500, "mid": 4500, "max": 5500, "days": 18},
        "JP": {"min": 3200, "mid": 4000, "max": 5000, "days": 32},
        "KR": {"min": 2800, "mid": 3600, "max": 4500, "days": 30},
        "VN": {"min": 2500, "mid": 3200, "max": 4000, "days": 26},
        "BR": {"min": 4000, "mid": 5000, "max": 6500, "days": 22},
        "JO": {"min": 800,  "mid": 1100, "max": 1400, "days": 6},
        "SA": {"min": 1000, "mid": 1400, "max": 1800, "days": 8},
        "AE": {"min": 1200, "mid": 1600, "max": 2100, "days": 10},
        "LY": {"min": 400,  "mid": 600,  "max": 800,  "days": 3},
    },
    # Air freight per kg port-to-port USD
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
    # Sea LCL per CBM USD
    MODE_SEA_LCL: {
        "CN": {"min": 55,  "mid": 75,  "max": 100, "days": 35},
        "TR": {"min": 25,  "mid": 40,  "max": 55,  "days": 8},
        "MA": {"min": 20,  "mid": 35,  "max": 50,  "days": 6},
        "IT": {"min": 25,  "mid": 40,  "max": 55,  "days": 5},
        "DE": {"min": 30,  "mid": 45,  "max": 60,  "days": 10},
        "FR": {"min": 28,  "mid": 42,  "max": 58,  "days": 8},
        "ES": {"min": 22,  "mid": 38,  "max": 52,  "days": 6},
        "IN": {"min": 40,  "mid": 60,  "max": 80,  "days": 22},
    },
    # Land per truck (~20 tons) USD — only where corridor exists
    MODE_LAND: {
        "LY": {"min": 800,  "mid": 1200, "max": 1600, "days": 2},
        "DZ": {"min": 900,  "mid": 1300, "max": 1700, "days": 3},
        "MA": {"min": 1500, "mid": 2000, "max": 2800, "days": 5},
        "EG": {"min": 1800, "mid": 2400, "max": 3200, "days": 6},
    },
}

def estimate_freight(
    origin: str,
    weight_kg: float = 500,
    volume_cbm: float = 2.0,
    mode: str = MODE_SEA_FCL,
    own_quote_usd: float = None,
) -> dict | list:
    """
    Returns dict (single mode) or list of dicts (MODE_ALL).
    Dict structure: {mode, min_usd, mid_usd, max_usd, transit_days, notes, is_own_quote}
    Never returns 0 — floor is 200 USD.
    Own quote overrides all estimates when provided.
    Land mode excluded for origins not in LAND_ACCESSIBLE.
    Air calculated on weight_kg; LCL on volume_cbm; FCL flat rate.
    """
```

**Verification:**
```bash
python3 -c "
from freight import estimate_freight, MODE_ALL, MODE_SEA_FCL, MODE_AIR
r = estimate_freight('CN', 1000, 5, MODE_SEA_FCL)
assert r['min_usd'] < r['mid_usd'] < r['max_usd'], 'range order'
assert r['transit_days'] > 0
all_modes = estimate_freight('CN', 1000, 5, MODE_ALL)
assert isinstance(all_modes, list) and len(all_modes) >= 2
own = estimate_freight('CN', 1000, 5, own_quote_usd=2500)
assert own['is_own_quote'] == True and own['mid_usd'] == 2500
floor = estimate_freight('CN', 0, 0, MODE_SEA_FCL)
assert floor['mid_usd'] >= 200
print('PASS')
"
```

**Stop point:** Report PASS/FAIL. Wait before Step 4.

---

## Step 4 — Update `schemas.py` and `calc.py`

### schemas.py additions

Add to `LandedCost`:
```python
freight_min: float
freight_max: float
freight_mode: str
landed_min: float
landed_max: float
working_capital_cost: float
currency_flag: str
supplier_risk: str
```

### calc.py changes

Update `calc_landed` signature:
```python
def calc_landed(
    hs: str,
    origin: str,
    exw: float,
    weight_kg: float = 500,
    volume_cbm: float = 2.0,
    incoterm: str = "EXW",
    freight_mode: str = "sea_fcl",
    own_freight_usd: float = None,
    fodec: bool = True,
    tcl: bool = False,
    financing_rate: float = 0.10,
    db_path=None,
) -> LandedCost:
```

Working capital formula:
```python
# Financing cost on CIF+duty for the duration of transit
working_capital_cost = (cif + duty_amt) * financing_rate * (lead_days / 365)
```

Landed min/max uses freight_min/freight_max:
```python
cif_min = exw + freight_result['min_usd']  (adjusted for incoterm)
cif_max = exw + freight_result['max_usd']
# recalculate duty_amt, landed for min and max
landed_min = ... (using cif_min)
landed_max = ... (using cif_max)
```

**Stop point:** `pytest tests/test_calc.py -v`. Report N passed. Wait before Step 5.

---

## Step 5 — `exporter.py`

Only build this if Step 2 POC PASSED. If MacMap was blocked, create a stub file
with the function signatures returning empty lists and a docstring explaining the
dependency.

```python
def get_export_markets(
    conn,
    hs6: str,
    macmap_email: str = None,
    macmap_password: str = None,
    top_n: int = 50,
    africa_only: bool = False,
) -> list[dict]:
    """
    1. Check export_tariffs table for this hs6
    2. Cache miss: if credentials provided, scrape MacMap for this hs6 × all reporters
       Store results in DB. Then query.
    3. Cache hit: return from DB directly.
    Returns list of dicts sorted by tariff_rate ASC:
    {reporter_iso2, reporter_name, tariff_rate, tariff_regime,
     agreement_id, has_preference, mfn_rate, tariff_advantage,
     afcfta_flag, market_size_flag}
    """

def get_competitor_comparison(
    conn,
    hs6: str,
    competitor_iso2: str,
    reporter_iso2: str,
) -> dict:
    """
    Compare duty Tunisia faces vs competitor in a given market.
    Returns {tunisia_rate, competitor_rate, advantage, has_advantage}
    """

# African countries for AfCFTA flagging
AFRICAN_ISO2 = {
    "AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM","CD","CG","CI",
    "DJ","EG","ET","GA","GH","GN","GW","KE","LS","LR","LY","MG","MW",
    "ML","MR","MU","MA","MZ","NA","NE","NG","RW","ST","SN","SL","SO",
    "ZA","SS","SD","SZ","TZ","TG","TN","UG","ZM","ZW",
}
```

**Stop point:** `python3 -c "from exporter import get_export_markets; print('OK')"`. Report PASS/FAIL. Wait before Step 6.

---

## Step 6 — Update `dashboard.py` — six tabs

Add four tabs to existing Sourcing + Legal Paths.

### Break-even cache

```python
_BREAKEVEN_CACHE = {}  # key: (hs, origin, exw_rounded) → LandedCost
```

### Tab 3: 🌍 Export Markets

```
Inputs:
- HS code (from shared search panel)
- Africa only toggle (checkbox)
- Min tariff advantage filter (IntSlider 0–20%)
- MacMap credentials (Text widgets, password masked) — only shown if needed

On "Find Markets" click:
- Call get_export_markets(conn, hs6, email, password)
- If returns empty: show "No export data yet. Enter MacMap credentials to fetch."
- If returns data: show ranked table
  Country | Duty rate | Regime | vs MFN | AfCFTA | Currency

Note below table:
"🟡 AfCFTA: Tunisia signed but not yet ratified. Rates shown are current applied rates."
```

### Tab 4: 💰 Working Capital

```
Inputs:
- Origins (multi-select, shared with Sourcing tab)
- Shipment value USD (FloatText, default 10000)
- Financing rate % (FloatSlider 5–25%, default 10)
- Freight mode (Dropdown: Sea FCL | Sea LCL | Air | Land)

On "Calculate" click:
Show table per origin:
Origin | Transit days | Freight mid | Duty amt | Financing cost | Total true cost

Key insight (auto-generated text):
"Sourcing from [cheapest] saves $X vs [most expensive] per shipment,
 including $Y in financing savings over [N] days transit difference."

Bar chart: Total true cost per origin (freight + duty + financing)
```

### Tab 5: ⚡ Break-Even

```
Inputs:
- Origins (multi-select)
- EXW min (FloatText default 50)
- EXW max (FloatText default 500)
- Steps (IntSlider 5–20, default 10)
- Freight mode (Dropdown)

On "Calculate" click:
- Compute landed cost at each EXW point for each origin
- Use _BREAKEVEN_CACHE to avoid recomputation
- Line chart: X=EXW, Y=landed cost, one line per origin
- Annotate crossover points: "TR cheaper than CN below $X EXW"

Performance limit: max 20 origins × 20 steps = 400 calcs.
If user selects more, warn and cap.
```

### Tab 6: 🚨 Flags

```
For selected HS code, show four sections:

1. Import Regime
   Value from hs_details.import_regime / export_regime
   "Libre ✅" | "Restricted ⚠️" | "Prohibited 🚫"

2. Anti-dumping / Safeguard
   Query antidumping_measures table.
   If empty table: "No active measures recorded. Data pending (Sprint 4)."
   If rows exist: show origin, rate, expiry, legal reference.

3. Duty Suspension
   Query duty_suspensions table.
   If empty: "Duty suspension data pending (Sprint 4)."
   If match: "✅ This HS code may qualify for duty suspension under [legal basis].
              Estimated saving: {rate}% on import duty."

4. Free Zone
   PLACEHOLDER ONLY — do not build rules yet.
   Static text: "🏭 Free zone analysis (Bizerte ZFBA and others) coming in Sprint 4.
                 Relevant for manufacturers with >30% re-export or value-add activity."
```

**Tab order:** Sourcing | Legal Paths | Export Markets | Working Capital | Break-Even | Flags

**Verification:**
```bash
python3 -c "
from dashboard import build_dashboard
d = build_dashboard()
assert len(d.children) == 6, f'Expected 6 tabs, got {len(d.children)}'
print('PASS: 6 tabs')
"
```

**Stop point:** Report PASS/FAIL + tab count. Wait before Step 7.

---

## Step 7 — `freight_loader.py` + tests

### freight_loader.py

```python
def load_freight_benchmarks(db_path=None) -> int:
    """Insert/replace FREIGHT_BENCHMARKS into freight_benchmarks table.
    Returns row count inserted."""
```

Run it: `python3 freight_loader.py`

### New tests

Add to `tests/test_calc.py`:
```python
def test_working_capital_proportional_to_lead_days():
    # China (28 days) should have higher WC cost than Morocco (4 days)
    # at same EXW and freight

def test_freight_range_order():
    # min <= mid <= max for all origins and modes in FREIGHT_BENCHMARKS

def test_landed_range():
    # landed_min <= landed <= landed_max
```

Add `tests/test_exporter.py`:
```python
def test_get_export_markets_empty_when_no_data():
    # Returns [] when export_tariffs is empty

def test_get_competitor_comparison_advantage():
    # Insert two rows, verify advantage calculation

def test_exporter_importable():
    from exporter import get_export_markets, get_competitor_comparison
```

**Stop point:** `pytest tests/ -q`. Report N passed / N failed. Wait before Step 8.

---

## Step 8 — Update `SESSION_STATE.md`

```markdown
## What works now (post Sprint 3)
- db.py — 4 new tables: export_tariffs, freight_benchmarks, duty_suspensions, antidumping_measures
- freight.py — multi-mode benchmarks (FCL/LCL/air/land), ranges, own-quote override,
  land corridor flags, currency flags, supplier risk flags
- calc.py — working capital cost, freight ranges, landed_min/landed_max
- macmap_scraper.py — [PASS: login + on-demand scraper] OR [BLOCKED: stub only]
- exporter.py — get_export_markets (on-demand cache), get_competitor_comparison
- dashboard.py — 6 tabs: Sourcing | Legal Paths | Export Markets |
                          Working Capital | Break-Even | Flags
- freight_loader.py — benchmark loader
- tests/ — N passing

## What does NOT work yet
- export_tariffs: empty until MacMap scraper run with real credentials
- duty_suspensions: empty — Sprint 4 (APII scrape)
- antidumping_measures: empty — Sprint 4
- Free zone tab: placeholder text only
- PDF export: Sprint 4
- User accounts / saved scenarios: Sprint 4
- Market size data for export ranking: Sprint 4

## MacMap scraper status
[PASS / BLOCKED — fill in after poc_macmap.py test]

## Last commit
[fill in: git log --oneline -1]

## Next step to resume (Sprint 4)
If MacMap blocked: investigate WITS API / WTO bulk download as alternative.
Otherwise: APII duty suspension scraper, anti-dumping measures loader,
PDF export, market size integration.
```

---

## Final commit

```bash
git add -A
git commit -m "feat: export intelligence, freight overhaul, working capital (Sprint 3)"
git push
```

Report: commit hash + test count.

---

## What to bring back to Claude chat

1. Test count (N passing)
2. MacMap POC result: PASS / BLOCKED / UNTESTED
3. Tab count in dashboard (should be 6)
4. Any freight benchmark that seems obviously wrong
5. SESSION_STATE.md contents
