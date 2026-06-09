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
- tests/ — 12 passing (seed fixture, resolver ×6, calc ×3, search ×3)

## What does NOT work yet
- scraper.py — not extracted from notebook yet (DEFERRED to Sprint 2)
- dashboard.py — not extracted from notebook yet (DEFERRED to Sprint 2)
- Preferential logic — FTA exclusions/phase-outs not populated (DEFERRED)
- CKD tab — uses hardcoded 50% parts-duty assumption (DEFERRED)
- Saved scenarios — in-memory only, no persistence (DEFERRED)

## Notes from Sprint 1
- resolver.py ancestor lookup extended to match DB rows that are MORE specific than
  the query code (e.g. query="8541" finds DB row "854140") via LIKE clause.

## Last commit
feat: extract notebook to ttis/ module structure (Phase 0–2)

## Next step to resume (Sprint 2)
Extract scraper.py from Cell 3, wire to db.upsert_measures, add scraper smoke test
with max_chapters=1. Then extract dashboard.py from Cell 8.
