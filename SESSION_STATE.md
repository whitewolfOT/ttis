# SESSION_STATE — TTIS

## What works now
- schemas.py — all four dataclasses; importable
- db.py — get_conn, ensure_schema, upsert_measures, load_hs_index
- fallback.py — 12 TariffMeasure rows (6 HS × DD+TVA)
- agreements.py — 4 agreements (EU, Turkey, Agadir, PAFTA), populate_preferential (idempotent)
- resolver.py — enumerate_paths, resolve_duty, get_hs_ancestors; prefix-in/prefix-out matching
- freight.py — estimate_freight, ORIGIN_LABELS, FREIGHT_FCL, LEAD_DAYS (20 origins)
- calc.py — calc_landed (full formula, all incoterms, FODEC/TCL flags)
- search.py — search_hs (rapidfuzz partial_ratio)
- scraper.py — scrape_mfn_full (Playwright + lxml/BS4, checkpoint/resume, _page injection for tests)
- dashboard.py — build_dashboard() returning six-tab ipywidgets UI; all logic delegated to engine modules
- tests/ — 18 passing (resolver ×6, calc ×3, search ×3, scraper ×6)

## What does NOT work yet
- Preferential logic — FTA exclusions/phase-outs not populated (DEFERRED)
- CKD tab — uses hardcoded 50% parts-duty assumption (DEFERRED)
- Saved scenarios — in-memory only, no persistence (DEFERRED)
- Full scrape not validated against live portal (requires Playwright + Chromium install)

## Notes from Sprint 1
- resolver.py ancestor lookup extended to match DB rows that are MORE specific than
  the query code (e.g. query="8541" finds DB row "854140") via LIKE clause.

## Notes from Sprint 2
- scraper.py accepts _page= injection parameter so tests never hit live portal
- dashboard.py CKD tab is a stub (parts_rate = finished_rate × 0.5); labelled DEFERRED

## Last commit
feat: extract scraper and dashboard (Sprint 2)

## Next step to resume (Sprint 3)
- Validate scraper against live portal (max_chapters=1 manual smoke test)
- Populate FTA exclusion/phase-out data in agreements.py
- Implement scenario persistence (SQLite or JSON) for Saved Scenarios tab
- Expand CKD tab with real BOM-level analysis
