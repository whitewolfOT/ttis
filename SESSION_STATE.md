# SESSION_STATE — TTIS

## What works now (post Sprint 3)
- schemas.py — LandedCost gains freight_min/max, landed_min/max, working_capital_cost, currency_flag, supplier_risk
- db.py — 4 new tables: export_tariffs, freight_benchmarks, duty_suspensions, antidumping_measures; hs_details added via load_pickle.py
- freight.py — multi-mode benchmarks (FCL/LCL/air/land), min/mid/max ranges, own-quote override, land corridor flags, currency flags, supplier risk flags
- calc.py — working capital cost, freight ranges, landed_min/landed_max, full financing_rate param
- macmap_scraper.py — login + on-demand scraper (75 reporters) — BLOCKED by network egress policy
- poc_macmap.py — manual validation script ready; requires machine with unrestricted egress
- exporter.py — get_export_markets, get_competitor_comparison — STUBS (MacMap blocked)
- dashboard.py — 6 tabs: Sourcing | Legal Paths | Export Markets | Working Capital | Break-Even | Flags
- freight_loader.py — loads 46 benchmark rows into freight_benchmarks table
- load_pickle.py — one-off loader: imports 17,508 HS codes (692,397 tariff_measures rows + 17,508 hs_details rows) from scrape_progress.pkl
- tests/ — 24 passing (resolver ×6, calc ×7, search ×3, scraper ×6, exporter ×3)

## What does NOT work yet
- export_tariffs: empty until MacMap scraper run with real credentials from unrestricted network
- duty_suspensions: empty — Sprint 4 (APII scrape)
- antidumping_measures: empty — Sprint 4
- Flags tab: Import/Export regime data present (from pickle); anti-dumping and duty suspension pending Sprint 4
- Free zone tab: placeholder text only
- PDF export: Sprint 4
- User accounts / saved scenarios: Sprint 4
- Market size data for export ranking: Sprint 4

## MacMap scraper status
BLOCKED — www.macmap.org and cdn.playwright.dev both return 403 (not in network allowlist).
Resolution: run poc_macmap.py from a machine with unrestricted egress, or investigate
WITS API / WTO bulk download as alternatives in Sprint 4.

## Notes from Sprint 1
- resolver.py ancestor lookup extended to match DB rows MORE specific than query (LIKE clause).

## Notes from Sprint 2
- scraper.py accepts _page= injection for test isolation.
- dashboard.py CKD tab replaced by new tabs in Sprint 3.

## Notes from Sprint 3
- load_pickle.py: 11-digit HS codes kept as-is; other_taxes stored with tax_type=short code;
  pref_rates loaded directly (group codes 97→EU-27, 98→EFTA expanded); valid_to=2030-12-31.
- calc.py: legacy weight/volume kwargs preserved for backward compat with existing tests.
- freight.py: estimate_freight now returns dict; mid_usd used as primary value in calc.py.
- Break-even cache keyed by (hs, origin, exw_rounded, mode).

## Last commit
feat: six-tab dashboard, freight overhaul, working capital, schemas (Sprint 3 Steps 3-6)

## Next step to resume (Sprint 4)
1. If MacMap unblocked: run poc_macmap.py, then implement get_export_markets fully
2. APII duty suspension scraper → populate duty_suspensions table
3. Anti-dumping measures loader
4. PDF export (landed cost report)
5. Market size data integration for export market ranking
