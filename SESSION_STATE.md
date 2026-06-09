# SESSION_STATE — Tunisia Tariff Intelligence System (TTIS)

## What works now (pre-Sprint 1 baseline)

All logic exists in a single Jupyter notebook (8 cells). The system is functionally correct
but not yet structured as importable Python modules. Key capabilities:

- MFN scraper (Playwright + BeautifulSoup, checkpoint/resume) — Cell 3
- SQLite schema with `tariff_measures`, `agreements`, `agreement_members` — Cell 4/5
- Fallback dataset: 6 HS codes with realistic MFN duties — Cell 3
- Deterministic resolver: `enumerate_paths` + `resolve_duty` (SUSP > PREF > QUOTA > MFN) — Cell 6
- Landed-cost calculator: EXW/FOB/CIF incoterms, FODEC, TCL, VAT — Cell 8
- Fuzzy product search (rapidfuzz) — Cell 8
- Jupyter dashboard: Sourcing tab + Legal Paths tab (reduced from original 6-tab spec) — Cell 8
- 20 origins with density-based freight and lead-time estimates — Cell 8

## What does NOT work yet

- No `tests/` directory — zero automated tests
- No module structure — all code in notebook cells, not importable
- Scraper: only scrapes first 10 chapters (max_chapters=10); full run requires max_chapters=None (~30 min)
- Preferential logic: 0% duty hardcoded for all HS codes; FTA exclusions/phase-outs not modelled
- Freight model: linear/density-based; not suitable for precise logistics planning
- CKD tab: assumes parts duty = 50% of finished duty; no BOM-level analysis
- Saved scenarios: in-memory only; not persisted to disk
- Dashboard has only 2 tabs (Sourcing, Legal Paths); full 6-tab spec not yet re-implemented

## Last commit

None yet — no git repo initialised.

## Next step to resume

**Sprint 1** — Extract notebook cells into `ttis/` module structure per SPRINT_1.md.
Start with Step 0 pre-flight, then build schemas.py first (no exceptions).
