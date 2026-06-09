# TTIS: Sprint 1 — Notebook-to-Modules Extraction (12-Step Build)

**Read `CLAUDE.md` fully before writing a single line.
Read this document fully. Only then start Step 0.**

---

## Session config

- **Mode:** Token-efficient. No prose, code and results only.
- **Stack:** Pure Python modules + SQLite. No web framework this sprint.
- **Budget guidance:** Stop and ask before any step estimated >10 min.
- **Commit message:** `feat: extract notebook to ttis/ module structure (Phase 0–2)`

---

## Stop-on-error rule

If any step produces an import error, schema mismatch, missing dependency, or unexpected exception:
**STOP. Report the exact error in one line. Do not attempt to fix it. Wait for instructions.**

---

## Context

The system currently lives entirely in a Jupyter notebook (8 cells). This sprint extracts it into
importable Python modules following the structure in `CLAUDE.md`, adds a `tests/` suite with a
seed fixture, and verifies correctness with known-value assertions. The notebook cells are the
authoritative source of business logic — do not add or remove logic; only reorganise.

---

## Step 0 — Pre-flight

```
1. Create directory structure:
   ttis/
   ttis/tests/
   ttis/tests/fixtures/
   ttis/docs/

2. Confirm Python ≥ 3.10: `python --version`. Report version.
3. Confirm dependencies importable (do NOT install; flag if missing):
   - sqlite3   (stdlib)
   - dataclasses (stdlib)
   - rapidfuzz
   - playwright
   - bs4 (beautifulsoup4)
   - lxml
   - pandas
   - plotly
   - ipywidgets

Report each as: CHECK <name>: PASS/FAIL
Stop if any stdlib check fails.
```

---

## Step 1 — `ttis/schemas.py`

**What it does:** Single source of truth for all shared dataclasses.
**Imports:** `dataclasses`, `typing` only. Zero logic.
**Must define exactly:**
- `TariffMeasure` — fields: `hs_code`, `origin_country`, `duty_type`, `tax_type`, `rate`, `agreement_name`, `valid_from`, `valid_to`
- `ResolvedPath` — fields: `rank`, `hs_code`, `origin_country`, `duty_type`, `rate`, `agreement_name`, `specificity`
- `LandedCost` — fields: `origin`, `agreement`, `lead_days`, `exw`, `freight`, `cif`, `duty_rate`, `duty_amt`, `fodec`, `tcl`, `vat_rate`, `vat_amt`, `landed`, `landed_tnd`
- `HsMatch` — fields: `hs_code`, `description`, `mfn_rate`, `score`

All field types exactly as specified in `CLAUDE.md` Shared data contracts section.

**Verification:** `python -c "from ttis.schemas import TariffMeasure, ResolvedPath, LandedCost, HsMatch; print('OK')"`.

**Stop point:** Report PASS/FAIL. Wait before Step 2.

---

## Step 2 — `ttis/db.py`

**What it does:** SQLite connection helper and schema management.
**Imports from:** `ttis.schemas`, `sqlite3`, `pathlib`
**Must implement:**

```python
DB_PATH = Path("tunisia_trade.db")

def get_conn(db_path=DB_PATH) -> sqlite3.Connection:
    """Return a new connection. Never reuse across calls."""

def ensure_schema(conn) -> None:
    """Create tariff_measures, agreements, agreement_members if not exist.
    tariff_measures schema: id, hs_code, origin_country, duty_type, tax_type,
    rate, agreement_name, measure_type, valid_from, valid_to, source_url, legal_basis."""

def upsert_measures(conn, measures: list[TariffMeasure]) -> int:
    """Insert list of TariffMeasure rows. Return count inserted."""

def load_hs_index(conn) -> list[dict]:
    """Return list of {hs_code, description, vat_rate} for all MFN DD rows."""
```

**Verification:** `python -c "from ttis.db import get_conn, ensure_schema; c=get_conn('/tmp/test.db'); ensure_schema(c); print('OK')"`.

**Stop point:** Report PASS/FAIL. Wait before Step 3.

---

## Step 3 — `ttis/fallback.py`

**What it does:** Returns the six hardcoded HS rows used when the scraper returns empty.
**Imports from:** `ttis.schemas`
**Must implement:**

```python
FALLBACK_MEASURES: list[TariffMeasure]  # exactly 6 HS codes, each with DD + TVA rows = 12 TariffMeasure objects

def get_fallback() -> list[TariffMeasure]:
    """Return a fresh copy of FALLBACK_MEASURES."""
```

Fallback data (from notebook): 854140/25%/19%, 870321/30%/19%, 010121/15%/19%,
850760/10%/19%, 847130/8%/19%, 401110/12%/19%.

**Verification:** `python -c "from ttis.fallback import get_fallback; m=get_fallback(); assert len(m)==12; print('OK')"`.

**Stop point:** Report PASS/FAIL. Wait before Step 4.

---

## Step 4 — `ttis/agreements.py`

**What it does:** FTA agreement registry and preferential-row populator.
**Imports from:** `ttis.schemas`, `ttis.db`, `sqlite3`
**Must implement:**

```python
AGREEMENTS: dict[str, dict]
# Structure: { "EU-Tunisia Association": {"type":"FTA","valid_from":"2020-01-01","members":["FR","DE",...]} }
# Must include: EU-Tunisia Association, Turkey-Tunisia FTA, Agadir Agreement, PAFTA (Arab FTA)
# Member lists exactly as in notebook Cell 5.

def populate_preferential(conn) -> int:
    """For every (hs_code, origin) combination in AGREEMENTS, insert a PREF DD row at 0.0%.
    Return total rows inserted."""
```

`populate_preferential` must be idempotent: running it twice must not create duplicate rows.
Use `INSERT OR IGNORE` with a UNIQUE constraint on `(hs_code, origin_country, duty_type, tax_type, agreement_name)`,
or delete existing PREF rows before inserting.

**Verification:** Call on the test DB from Step 2; confirm `populate_preferential` returns > 0 and is idempotent.

**Stop point:** Report PASS/FAIL + row count. Wait before Step 5.

---

## Step 5 — `ttis/resolver.py`

**What it does:** Deterministic duty resolver — single source of truth for tariff lookup.
**Imports from:** `ttis.schemas`, `sqlite3`
**Must implement exactly (logic from notebook Cell 6):**

```python
def get_hs_ancestors(hs_code: str) -> list[str]:
    """Return list of ancestor HS prefixes from most-specific to least: [10,8,6,4,2]-digit."""

def enumerate_paths(conn, hs_code: str, origin_country: str) -> list[ResolvedPath]:
    """Return all applicable measures for hs_code + origin, ordered by:
    1. duty_type priority: SUSP(0) > PREF(1) > QUOTA(2) > MFN(3)
    2. hs_code specificity DESC (longer match wins)
    Only DD rows. Both origin_country=<iso2> AND origin_country='TN' rows qualify."""

def resolve_duty(conn, hs_code: str, origin_country: str) -> ResolvedPath | None:
    """Return the highest-priority path, or None if no measures found."""
```

**Stop point:** `python -c "from ttis.resolver import enumerate_paths, resolve_duty; print('OK')"`. Report PASS/FAIL. Wait before Step 6.

---

## Step 6 — `ttis/freight.py`

**What it does:** Freight cost and lead-time estimates by origin.
**Imports:** stdlib only (no project imports).
**Must implement:**

```python
ORIGIN_LABELS: dict[str, str]   # ISO-2 → display label with flag emoji (20 origins from notebook)
FREIGHT_FCL: dict[str, float]   # ISO-2 → base FCL USD (values from notebook)
LEAD_DAYS: dict[str, int]       # ISO-2 → estimated transit days (values from notebook)
USD_TO_TND: float = 3.12

def estimate_freight(origin: str, weight: float = 500, volume: float = 2.0) -> float:
    """Density-based freight estimate. Never return 0; minimum 200 USD.
    Logic exactly as in notebook Cell 8 `estimate_freight`."""
```

**Verification:** `python -c "from ttis.freight import estimate_freight; assert estimate_freight('CN', 500, 2.0) > 0; print('OK')"`.

**Stop point:** Report PASS/FAIL. Wait before Step 7.

---

## Step 7 — `ttis/calc.py`

**What it does:** Full landed-cost calculator.
**Imports from:** `ttis.schemas`, `ttis.resolver`, `ttis.freight`, `ttis.db`, `sqlite3`
**Must implement exactly (formula from notebook Cell 8, `calc_landed`):**

```python
def calc_landed(
    hs: str,
    origin: str,
    exw: float,
    weight: float = 500,
    volume: float = 2.0,
    incoterm: str = "EXW",
    fodec: bool = True,
    tcl: bool = False,
    db_path = None,
) -> LandedCost:
    """Opens its own DB connection. Calls resolve_duty internally.
    Returns LandedCost. Never raises on missing HS (use 0% duty with warning)."""
```

The full formula is documented in `CLAUDE.md` Landed-cost formula section. Do not deviate.

**Verification:** `python -c "from ttis.calc import calc_landed; print('OK')"`.

**Stop point:** Report PASS/FAIL. Wait before Step 8.

---

## Step 8 — `ttis/search.py`

**What it does:** Fuzzy HS code search against product descriptions.
**Imports from:** `ttis.schemas`, `rapidfuzz`, `sqlite3`
**Must implement:**

```python
def search_hs(
    conn,
    query: str,
    limit: int = 12,
    score_cutoff: int = 30,
) -> list[HsMatch]:
    """Use rapidfuzz.process.extract with fuzz.partial_ratio against
    (description + ' ' + hs_code) strings. Return empty list for empty query."""
```

**Stop point:** `python -c "from ttis.search import search_hs; print('OK')"`. Report PASS/FAIL. Wait before Step 9.

---

## Step 9 — `tests/fixtures/seed.sql`

**What it does:** Minimal SQLite fixture for all tests. No internet required.
**Must insert:**
- MFN DD + TVA rows for: 854140 (25% / 19%), 870321 (30% / 19%), 847130 (8% / 19%)
- PREF DD rows at 0%: (854140, TR), (854140, FR), (870321, MA)
- One SUSP DD row: (854140, CN, 5%) — for priority testing

Use `INSERT OR IGNORE`. All `valid_from/valid_to` within 2025.

**Stop point:** `sqlite3 /tmp/seed_test.db < tests/fixtures/seed.sql && echo OK`. Report PASS/FAIL. Wait before Step 10.

---

## Step 10 — `tests/test_resolver.py`

**What it does:** Unit tests for the resolver using the seed fixture.
**Must include at least 5 assertions:**

1. `resolve_duty(854140, 'TR')` returns PREF at 0% (FTA wins over MFN)
2. `resolve_duty(854140, 'CN')` returns SUSP at 5% (SUSP beats PREF and MFN)
3. `resolve_duty(870321, 'MA')` returns PREF at 0%
4. `resolve_duty(870321, 'IN')` returns MFN at 30% (no FTA for India)
5. `resolve_duty('8541', 'TR')` returns PREF via 4-digit ancestor match (HS specificity fallback)
6. `resolve_duty('9999', 'CN')` returns None (HS not in DB)

Each test loads the seed DB fresh; use `tmp_path` pytest fixture.

**Stop point:** `pytest tests/test_resolver.py -v`. Report: N passed / N failed. Wait before Step 11.

---

## Step 11 — `tests/test_calc.py`

**What it does:** Known-value assertions for `calc_landed`.

**Must include at least 3 assertions using seed data + hardcoded expected values:**

1. `calc_landed('854140', 'CN', exw=100, incoterm='EXW', fodec=True, tcl=False)`
   - `duty_rate == 25.0` (MFN, no PREF for CN unless SUSP overrides — seed has SUSP 5% for CN)
   - `landed > exw` always
2. `calc_landed('854140', 'TR', exw=100)`
   - `duty_rate == 0.0` (PREF)
   - `landed < calc_landed('854140', 'IN', exw=100).landed` (FTA cheaper than MFN)
3. `calc_landed('854140', 'FR', exw=0, weight=0, volume=0)`
   - `freight >= 200` (minimum freight floor)

**Stop point:** `pytest tests/test_calc.py -v`. Report: N passed / N failed. Wait before Step 12.

---

## Step 12 — `tests/test_search.py` + full suite

**What it does:** Smoke tests for search + full suite run.

**Assertions:**
1. `search_hs(conn, 'solar')` returns at least one result with `hs_code == '854140'`
2. `search_hs(conn, '')` returns `[]`
3. `search_hs(conn, 'zzzzz_no_match_xyz')` returns `[]`

After writing these tests, run the full suite.

**Stop point:** `pytest tests/ -q`. Report: N passed, N failed.
If all green, proceed. If any fail, stop and report failing test names + errors.

---

## Step 13 — Update `SESSION_STATE.md`

Create `SESSION_STATE.md` in the repo root:

```markdown
# SESSION_STATE — TTIS

## What works now
- schemas.py — all four dataclasses; importable
- db.py — get_conn, ensure_schema, upsert_measures, load_hs_index
- fallback.py — 12 TariffMeasure rows (6 HS × DD+TVA)
- agreements.py — 4 agreements, populate_preferential (idempotent)
- resolver.py — enumerate_paths, resolve_duty, get_hs_ancestors
- freight.py — estimate_freight, ORIGIN_LABELS, FREIGHT_FCL, LEAD_DAYS
- calc.py — calc_landed (full formula, all incoterms)
- search.py — search_hs (rapidfuzz)
- tests/ — N passing (seed fixture, resolver, calc, search)

## What does NOT work yet
- scraper.py — not extracted from notebook yet (DEFERRED to Sprint 2)
- dashboard.py — not extracted from notebook yet (DEFERRED to Sprint 2)
- Preferential logic — FTA exclusions/phase-outs not populated (DEFERRED)
- CKD tab — uses hardcoded 50% parts-duty assumption (DEFERRED)
- Saved scenarios — in-memory only, no persistence (DEFERRED)

## Last commit
[fill in: git log --oneline -1]

## Next step to resume (Sprint 2)
Extract scraper.py from Cell 3, wire to db.upsert_measures, add scraper smoke test
with max_chapters=1. Then extract dashboard.py from Cell 8.
```

---

## Final commit

```bash
git add -A
git commit -m "feat: extract notebook to ttis/ module structure (Phase 0–2)"
git push
```

Report: commit hash + total test count.

---

## What to bring back to Claude chat

1. Test count (N passing)
2. Any DEFERRED items added to SESSION_STATE.md and why
3. Any errors that were worked around (not just fixed)
4. Any resolver edge case that produced a surprising result
