# Tunisia Tariff Intelligence System (TTIS)

A web-scraping + trade analysis engine that collects MFN customs duties from the
Tunisian Tarif Web 2025 portal, normalises them into a tariff-measures schema,
resolves preferential duties from FTA agreements, and renders a six-tab Jupyter
dashboard for landed-cost comparison, legal-path resolution, and CKD analysis.
Input: a product HS code + origin country + EXW price. Output: full landed-cost
breakdown, duty waterfall chart, and ranked list of applicable tariff measures.

---

## Repo structure
```
ttis/
├── schemas.py                  # Canonical dataclasses — single source of truth
├── db.py                       # SQLite helpers: connect, ensure_schema, upsert
├── scraper.py                  # Playwright-based MFN scraper + checkpoint/resume
├── fallback.py                 # Six-row hardcoded dataset used when scraper returns 0 rows
├── agreements.py               # Agreement registry + preferential-row populator
├── resolver.py                 # enumerate_paths() + resolve_duty() — deterministic resolver
├── calc.py                     # calc_landed() — full landed-cost formula
├── search.py                   # Fuzzy HS search (rapidfuzz)
├── freight.py                  # Freight/lead-time estimates by origin
├── dashboard.py                # Jupyter ipywidgets dashboard (all six tabs)
├── tests/
│   ├── test_resolver.py        # Resolver unit tests (MFN / PREF / SUSP priority)
│   ├── test_calc.py            # Landed-cost formula tests (known-value assertions)
│   ├── test_search.py          # Fuzzy search smoke tests
│   └── fixtures/
│       └── seed.sql            # Minimal SQLite fixture for tests (no scraper required)
├── docs/
│   └── MASTER_PLAN.md          # Full architecture rationale (read-only reference)
├── data/
│   └── scrape_checkpoint.json  # Auto-generated; not committed
├── tunisia_trade.db            # Auto-generated; not committed
├── requirements.txt
├── SESSION_STATE.md            # Updated at the end of every sprint
└── CLAUDE.md                   # This file
```

---

## Build order

### Phase 0 — Shared contracts (build FIRST, no exceptions)
- `schemas.py` — all shared dataclasses; zero logic, zero external imports beyond dataclasses/typing
- `db.py` — `get_conn()`, `ensure_schema()`, `upsert_mfn()`, `upsert_pref()` helpers

### Phase 1 — Data layer
- `fallback.py` — six hardcoded rows returned as `list[TariffMeasure]`; must be usable with zero DB
- `scraper.py` — `scrape_mfn_full(max_chapters, resume)` → `list[TariffMeasure]`; checkpoint on every chapter
- `agreements.py` — `AGREEMENTS` registry dict + `populate_preferential(conn)` function

### Phase 2 — Core engine
- `resolver.py` — `enumerate_paths(conn, hs_code, origin)` → `list[ResolvedPath]`; `resolve_duty(...)` → `ResolvedPath`
- `calc.py` — `calc_landed(hs, origin, exw, **kwargs)` → `LandedCost`; calls resolver internally
- `search.py` — `search_hs(query, limit)` → `list[HsMatch]`

### Phase 3 — Dashboard (Jupyter)
- `freight.py` — `estimate_freight(origin, weight, volume)` → `float`; `LEAD_DAYS` dict
- `dashboard.py` — all six tabs wired to engine functions; never embeds business logic directly

### Phase 4 — Tests
- `tests/fixtures/seed.sql` — insert 3 HS codes + MFN + PREF rows covering all resolver branches
- `tests/test_resolver.py` — at least 5 assertions covering SUSP > PREF > MFN priority and HS specificity tie-breaking
- `tests/test_calc.py` — at least 3 known-value assertions (EXW=100, CN, HS 854140 → expected landed)
- `tests/test_search.py` — smoke tests: "solar" matches 854140, empty query returns empty

---

## Shared data contracts

```python
# schemas.py — canonical types; never import from anywhere else
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TariffMeasure:
    hs_code: str
    origin_country: str          # ISO-2; 'TN' = MFN (applies to all non-FTA origins)
    duty_type: str               # 'MFN' | 'PREF' | 'SUSP' | 'QUOTA'
    tax_type: str                # 'DD' (import duty) | 'TVA' (VAT)
    rate: float                  # percentage, e.g. 25.0
    agreement_name: Optional[str] = None
    valid_from: Optional[str] = None   # ISO date string
    valid_to: Optional[str] = None

@dataclass
class ResolvedPath:
    rank: int
    hs_code: str
    origin_country: str
    duty_type: str
    rate: float
    agreement_name: Optional[str]
    specificity: int             # digit-length of hs_code match (2–10)

@dataclass
class LandedCost:
    origin: str
    agreement: str               # duty_type of winning measure
    lead_days: int
    exw: float
    freight: float
    cif: float
    duty_rate: float
    duty_amt: float
    fodec: float
    tcl: float
    vat_rate: float
    vat_amt: float
    landed: float
    landed_tnd: float

@dataclass
class HsMatch:
    hs_code: str
    description: str
    mfn_rate: float
    score: float                 # fuzzy match score 0–100
```

---

## Non-negotiable rules

1. **`schemas.py` has zero logic.** No functions, no imports beyond `dataclasses` and `typing`.
2. **`resolve_duty` and `enumerate_paths` are the single source of truth for duty lookup.** `calc.py` and `dashboard.py` must call them — never reimplement duty logic inline.
3. **Priority order is immutable:** SUSP (0) > PREF (1) > QUOTA (2) > MFN (3). Any change requires a test update first.
4. **HS ancestor lookup always walks 10→8→6→4→2 digits.** The most specific match wins; fallback to shorter prefixes.
5. **`estimate_freight` never returns 0.** If weight=0 and volume=0, use placeholder 200 USD and emit a warning.
6. **Fallback dataset activates only when `scrape_mfn_full` returns an empty list.** Never mix fallback rows with scraped rows in the same DB session.
7. **Tests use `seed.sql` fixture only — never the production DB and never the live portal.**
8. **Stop-on-error:** if any step raises an unexpected exception, stop and report the exact error. Do not attempt self-repair.

---

## Pipeline order
```
Portal (Playwright scrape)
        │
        ▼
TariffMeasure rows (MFN DD + MFN TVA)
        │
        ├─── agreements.py ──► PREF rows (0% DD per FTA origin)
        │
        ▼
SQLite: tariff_measures table
        │
        ▼
resolver.py: enumerate_paths(hs, origin)
        │
        ├─── calc.py: calc_landed(hs, origin, exw) ──► LandedCost
        │
        └─── dashboard.py: Legal Paths tab / Sourcing tab
```

---

## Landed-cost formula

```
CIF  = EXW + freight          (if incoterm=EXW)
     = EXW + freight*0.7      (if incoterm=FOB)
     = EXW                    (if incoterm=CIF, freight=0)

duty_amt  = CIF × (duty_rate / 100)
base      = CIF + duty_amt
fodec_amt = base × 0.01       (if fodec=True, else 0)
tcl_amt   = (base + fodec_amt) × 0.002  (if tcl=True, else 0)
vat_amt   = (base + fodec_amt + tcl_amt) × (vat_rate / 100)
landed    = base + fodec_amt + tcl_amt + vat_amt
landed_tnd = landed × USD_TO_TND        (USD_TO_TND = 3.12)
```

---

## Key technical constraints

- **Playwright:** must run with `--no-sandbox` in Colab / headless environments; `wait_for_timeout(5000)` after each chapter click is the minimum stable delay.
- **BeautifulSoup parser:** use `lxml`, not `html.parser`. The portal HTML is malformed and `lxml` tolerates it; `html.parser` silently drops rows.
- **Checkpoint file:** `scrape_checkpoint.json` stores `{last_chapter: N, total_rows: N}`. On resume, skip chapters with index < `last_chapter`.
- **SQLite threading:** open a new `sqlite3.connect()` per function call in dashboard callbacks; do not share a connection across ipywidgets event handlers.
- **HS normalisation:** strip all non-digit characters; reject codes shorter than 2 digits.
- **Preferential logic:** `origin_country = 'TN'` on an MFN row means "applies to all origins". A PREF row carries the actual ISO-2 origin. The resolver must match `(hs_code IN ancestors) AND (origin_country = ? OR origin_country = 'TN')`.

---

## How to run

```bash
# Install
pip install playwright rapidfuzz pandas numpy plotly ipywidgets beautifulsoup4 lxml nest_asyncio
playwright install chromium

# Tests (no internet required)
pytest tests/ -q
# Expected: 13+ tests passing

# Scrape (Colab/Jupyter)
import asyncio
from scraper import scrape_mfn_full
df = asyncio.run(scrape_mfn_full(max_chapters=10))  # full: max_chapters=None

# Dashboard (Jupyter)
%run dashboard.py
```

---

## Adding a new origin country

1. Add entry to `ORIGIN_LABELS` in `freight.py`
2. Add FCL base rate to `FREIGHT_FCL` dict
3. Add lead days to `LEAD_DAYS` dict
4. If origin has an FTA: add country to `agreements.py` under the correct agreement key
5. Re-run `agreements.populate_preferential(conn)` to insert PREF rows
6. No other files need changing

---

## Adding a new agreement

1. Add a row to `AGREEMENTS` in `agreements.py`: `{name, type, valid_from, member_countries}`
2. Re-run `populate_preferential(conn)`
3. Add a test to `tests/test_resolver.py` asserting the new origin resolves to PREF at 0%

---

## Full design reference

See `docs/MASTER_PLAN.md` for full architecture rationale, data acquisition table,
known portal quirks, and the planned Phase 5 (API layer + React frontend).
