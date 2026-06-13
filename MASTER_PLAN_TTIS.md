# TTIS: Master Plan — Trade Intelligence Platform

**Document purpose:** Full roadmap from current state to production product.
**Last updated:** June 2026
**Read before writing any sprint.**

---

## What this platform is

A global trade intelligence engine focused on Tunisia.
It answers three questions no existing free tool answers for Tunisia:

1. **What should I import, from where, at what true cost?**
2. **What should I export, to which markets, where does Tunisia have an advantage?**
3. **Should I import finished goods or assemble from parts — and what does that actually cost?**

The platform learns from usage, surfaces opportunities automatically,
and eventually enables direct booking of freight and customs clearance.

---

## Current state (as of Sprint 3)

### What works
- Tunisian import tariffs: 17,508 HS codes, real rates from douane.gov.tn ✅
- Preferential rates: 213,058 real rows scraped from customs portal ✅
- Resolver: SUSP > PREF > QUOTA > MFN, ancestor walk, 24 tests passing ✅
- Landed cost calculator: EXW/FOB/CIF, FODEC, TCL, VAT, working capital ✅
- Freight: multi-mode (FCL/LCL/air/land) with ranges, own-quote override ✅
- Dashboard: 6 tabs in JupyterLab (Sourcing, Legal Paths, Export Markets,
  Working Capital, Break-Even, Flags) ✅
- MacMap scraper: proven working via page.evaluate() ✅

### What is empty / broken
- export_tariffs table: 6 test rows only (needs WITS + MacMap population)
- duty_suspensions: empty (needs APII scrape)
- antidumping_measures: empty (needs Ministry of Commerce data)
- Free zone analysis: placeholder text only
- No opportunity scoring
- No BOM explosion
- No trade flow data (market sizes unknown)
- No natural language product search
- No user accounts, no persistence
- No narrative/recommendation output
- Dashboard is developer tool, not user product

### Data accuracy
- Tunisian import tariffs: CURRENT. WTO TPR (Oct 2025) confirms average MFN
  23.8% in 2025, up from 14.1% in 2016. Our portal scrape reflects this.
- Preferential rates: CURRENT. Scraped directly from 2025 customs portal.
- Export tariffs: NOT POPULATED.
- Freight: ESTIMATED. Reasonable ranges, not live rates.

---

## Data foundation — complete picture

### Layer 1: Tunisian import tariffs (DONE)
- Source: douane.gov.tn/tarifweb2025 (official 2025 portal)
- Content: 17,508 HS codes, DD/TVA/RPD/DSV rates, preferential rates per country
- Accuracy: authoritative, current
- Refresh: annually (re-run scraper each January)
- Status: ✅ in DB

### Layer 2: Export tariffs — what countries charge Tunisian goods (NEEDED)
Primary source: **WITS API (World Bank)** — free, no auth, REST
- URL: https://wits.worldbank.org/API/V1/SDMX/V21/rest/data/DF_WITS_Tariff_TRAINS/
- Coverage: 150+ reporters × all HS6 × MFN + preferential rates
- Lag: typically 2-3 years behind (2022 data available now)
- Advantage: bulk queryable, no scraping, stable
- Limitation: does not reflect very recent tariff changes

Secondary source: **MacMap** (via page.evaluate() scraper)
- Coverage: real-time, most current
- Use case: spot-check WITS data, fill gaps for priority markets
- Not suitable for bulk population (browser session required)

Cross-check: **WTO TTD platform** (ttd.wto.org) — new March 2025
- Bulk download available, covers 150+ economies, updated weekly
- Use for annual refresh and validation

Strategy:
- Use WITS API to bulk-populate export_tariffs for all HS6 × top 50 reporters
- Use MacMap on-demand for current rates on user-queried products
- Refresh WITS annually, MacMap fills the gap for recent changes

### Layer 3: Trade flows — market sizes and trends (NEEDED)
Source: **UN Comtrade API** — free with registration
- Registration: comtradeplus.un.org (free, instant)
- Free tier: 500 calls/day × 100k records/call
- Content: bilateral import/export values + volumes by HS6, all countries, since 1962
- Use: market sizing, growth trends, opportunity scoring
- Python package: pip install comtradeapicall

What to pull for TTIS:
- Tunisia exports by HS6 × destination country × year (2018-2023)
  → shows where Tunisia already sells and what's growing
- World imports by HS6 × year (top 50 importers)
  → shows market size for each product category
- Both needed for opportunity scoring

### Layer 4: Duty suspensions (NEEDED — small dataset)
Source: APII website (apii.com.tn) — one-time scrape
- ~200 HS codes eligible under Code d'Incitation aux Investissements
- Article 21: equipment for new investments — duty suspended
- Article 46: export companies — raw materials duty suspended
- Refresh: annually (budget law changes occasionally)
- Effort: 1-2 hours to scrape and structure

### Layer 5: Anti-dumping and safeguard measures (NEEDED — small dataset)
Source: Journal Officiel de la République Tunisienne (JORT)
- Active measures: mainly Chinese steel (HS 72xx), some textiles, some agriculture
- ~30-50 active measures at any time
- Manual curation is appropriate — too small for automated scraping
- Refresh: quarterly scan of JORT

### Layer 6: BOM / component mapping (NEEDED — most complex)
No public database covers this. Build it:
- Primary method: LLM-powered decomposition (Claude API)
  - Input: product name or HS code
  - Output: list of major components with estimated HS codes and value %
  - Accuracy: ~80% for common manufactured goods, improves with feedback
- Secondary method: curated library for top 100 traded product categories
  - Manual curation for high-value categories (vehicles, electronics, machinery)
  - Stored in bom_components table, referenced by hs_code
- Tertiary: user-provided BOM upload (CSV) for precision work

### Layer 7: Certificates of origin (NEEDED — tiny dataset)
Manual table — 6 agreements × 1-2 cert types each. Never changes.
- EU-Tunisia Association: EUR.1 form or REX (Registered Exporter) declaration
- Turkey-Tunisia FTA: Movement Certificate A.TR or EUR.1
- Agadir Agreement (MA/EG/JO): Pan-Arab Cumulation Certificate
- PAFTA Arab League: Arab Certificate of Origin (Form A)
- AfCFTA: pending ratification — flag only, no cert required yet
- GSP (for exports to non-FTA countries): Form A

### Layer 8: Freight rates (PARTIALLY DONE)
Current: hardcoded benchmarks with min/mid/max ranges
Improvement path:
- Phase 1 (now): ranges from published shipping line rate cards + FBX index
- Phase 2: integrate Freightos FBX weekly index via their free data feed
  (fbx.freightos.com — weekly container rate indices, downloadable)
- Phase 3 (paid tier): live quotes via Freightos API or direct forwarder integration

### Layer 9: Free zones (NEEDED — small dataset)
Tunisia has 3 free zones:
- Bizerte Economic Activity Park (PAEB Bizerte) — operational, north, near port
- Zarzis Economic Activity Park — operational, south, near Libya
- Ben Guerdane — planned, near Libyan border (under development)

Rules for all: exempt from import duty on inputs, VAT suspended, corporate tax
exemption for re-export activities. Local sales limited and subject to normal duties.
Relevant for: any manufacturer importing components, assembling, and re-exporting.

Manual table sufficient — rules don't change frequently.

---

## Intelligence layer — what to compute

### Opportunity scorer
For each (hs6, reporter_country) pair, compute:

```
tariff_advantage = mfn_rate[reporter][hs6] - pref_rate[reporter][tunisia][hs6]
                   (how much cheaper Tunisia is vs non-FTA competitors)

market_size = comtrade_imports[reporter][hs6][latest_year]
              (USD value of what that country imports of this product)

growth_rate = CAGR(comtrade_imports[reporter][hs6], years=5)
              (is this market growing or shrinking?)

opportunity_score = tariff_advantage × log(market_size) × (1 + growth_rate)
```

Pre-compute this for all combinations and store in market_opportunities table.
Refresh when underlying data updates.

### Import optimizer
For a given product + quantity + budget:
1. Resolve duty rate for each candidate origin
2. Compute full landed cost per origin (freight + duty + VAT + working capital)
3. Rank by total true cost
4. Flag: preferential rate available? Certificate required? Anti-dumping active?
5. Produce recommendation: "Source from X — saves $Y vs next best option"

### BOM arbitrage engine
For a given finished product HS code:
1. LLM decomposes into major components (5-15 components)
2. For each component: find HS code, resolve duty rate, find optimal source
3. Compute: sum(component landed costs) + assembly overhead
4. Compare: import finished vs assemble from parts
5. Flag: free zone option (if assembly qualifies, duty on components = 0)
6. Output: "Assembly saves X% if you source parts from Y, Z, W"

### Alert engine (future)
Monitors for:
- Tariff rate changes (new budget law → new duties)
- New anti-dumping measures
- FTA ratification (AfCFTA → 54 new 0% markets)
- Price index changes (commodity shifts that affect opportunity scores)
- New duty suspension eligibility (APII investment approvals)

---

## Product — how it should feel

### Entry points (not tabs)
```
╔══════════════════════════════════════════════╗
║   🇹🇳 Tunisia Trade Intelligence             ║
╠══════════════════════════════════════════════╣
║                                              ║
║   What do you want to do?                   ║
║                                              ║
║   🔵  I'm importing into Tunisia            ║
║       Find the best source + true cost      ║
║                                              ║
║   🟢  I'm exporting from Tunisia            ║
║       Find the best markets + advantages    ║
║                                              ║
║   🟡  Should I assemble or import finished? ║
║       BOM analysis + free zone check        ║
║                                              ║
║   🔴  Show me opportunities                 ║
║       What's hot right now                  ║
║                                              ║
╚══════════════════════════════════════════════╝
```

### Import flow
Step 1: "What are you importing?" → natural language or HS code
Step 2: "Where from / at what price?" → origin(s), EXW, quantity
Step 3: Recommendation card + full breakdown

Recommendation card format:
```
┌─────────────────────────────────────────────┐
│ 🏆 BEST OPTION: Turkey 🇹🇷                  │
│ Landed: $412  |  Duty: 0% MFN  |  5 days   │
│                                             │
│ Compared to China 🇨🇳 ($452 landed):         │
│ Save $40/shipment on duty                   │
│ Save $180/shipment in financing (23 days)   │
│ Total advantage: $220 per shipment          │
│ Over 12 shipments/year: $2,640              │
│                                             │
│ ⚠️  Check: EUR.1 certificate needed        │
│     for EU preference (Italy/France)       │
└─────────────────────────────────────────────┘
```

### Export flow
Step 1: "What are you exporting?" → HS code
Step 2: "Show opportunities" → ranked market list

Output:
```
Top markets for HS 150910 (Olive oil):

🥇 Germany 🇩🇪  — 0% duty (EU FTA) vs 12% for competitors
   Market size: €340M/year | Growing 12% YoY
   Tunisia market share: 8% (underweight — opportunity)
   Action: EUR.1 certificate required

🥈 Saudi Arabia 🇸🇦 — 5% duty (PAFTA)
   Market size: $89M/year | Growing 8% YoY
   Arab Certificate of Origin required

🥉 USA 🇺🇸 — 3.4% duty (MFN — no FTA)
   Market size: $520M/year | Growing 15% YoY
   Note: competitors (Spain, Italy) pay same rate
```

### Assembly/BOM flow
Step 1: "What finished product?" → description or HS code
Step 2: System decomposes into components, shows duty comparison
Step 3: Recommendation: assemble vs import

### Opportunity feed
Auto-generated daily based on data:
- Tariff changes (new budget)
- Growing markets Tunisia isn't in yet
- Products where Tunisia has >10% tariff advantage over competitors
- Free zone assembly opportunities (large duty differential, standard product)

---

## Technical architecture (target state)

```
┌────────────────────────────────────────────────────────┐
│                    DATA PIPELINE                        │
│                                                         │
│  douane.gov.tn → scraper.py → tariff_measures          │
│  WITS API      → wits_loader.py → export_tariffs        │
│  UN Comtrade   → comtrade_loader.py → trade_flows       │
│  MacMap        → macmap_scraper.py → export_tariffs     │
│  APII          → apii_scraper.py → duty_suspensions     │
│  JORT          → manual → antidumping_measures          │
│  Claude API    → bom_exploder.py → bom_components       │
└────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────┐
│                   INTELLIGENCE ENGINE                   │
│                                                         │
│  resolver.py         — duty resolution                  │
│  calc.py             — landed cost + working capital    │
│  exporter.py         — export market ranking            │
│  opportunity.py      — opportunity scoring              │
│  bom_exploder.py     — BOM decomposition                │
│  alert_engine.py     — change detection                 │
└────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────┐
│                       INTERFACES                        │
│                                                         │
│  Jupyter dashboard   — current (developer mode)         │
│  Web app (FastAPI +  — Sprint 7+                        │
│  React frontend)                                        │
│  REST API            — Sprint 8 (for brokers)           │
│  Claude artifact UI  — Sprint 5 prototype               │
└────────────────────────────────────────────────────────┘
```

### Database schema (complete)
```sql
-- EXISTING (Sprint 1-3)
tariff_measures        -- Tunisian import duties (17,508 HS codes)
hs_details             -- Descriptions, import/export regimes
export_tariffs         -- What countries charge Tunisian goods (BUILDING)
freight_benchmarks     -- Mode/origin freight ranges
duty_suspensions       -- CII-eligible HS codes (EMPTY)
antidumping_measures   -- Active measures (EMPTY)

-- SPRINT 4-5
trade_flows            -- Comtrade bilateral volumes by HS6 × year
market_opportunities   -- Pre-computed scores (tariff_adv × market_size × growth)
certificates           -- Certificate of origin by agreement
free_zones             -- Tunisia free zone rules and eligible activities

-- SPRINT 6
bom_components         -- Product → component mapping (LLM-generated + curated)
bom_hs_map             -- Component description → HS6 mapping

-- SPRINT 7+
users                  -- User accounts
scenarios              -- Saved analysis scenarios
alerts                 -- User alert subscriptions
alert_log              -- Triggered alerts history
```

---

## Commercial model

### Free tier
- MFN duty lookup for any Tunisian HS code
- Top 3 origins by landed cost (no preferential rates shown)
- Basic freight estimates (mid-point only, no range)
- Export: tariff rate for top 5 markets

### Pro tier — $49/month per user
- Full preferential rate resolution with certificate guidance
- All 20+ origins with freight ranges
- Working capital analysis
- Break-even charts
- Export: full market ranking with opportunity scores
- Duty suspension checker
- Anti-dumping flags
- PDF export
- 50 saved scenarios

### Enterprise tier — $299/month
- API access (REST)
- Batch processing (upload BOM/product list → full analysis)
- BOM explosion + assembly arbitrage
- Price alerts (tariff changes, rate shifts)
- Multi-user (up to 10 seats)
- White-label option
- Priority support

### Primary target markets
1. Tunisian customs brokers — do this manually today, charge clients for it
2. Import/export trading companies — sourcing decisions, multiple products
3. Procurement managers at Tunisian manufacturers — annual sourcing review
4. Foreign companies entering Tunisian market — initial market entry analysis
5. Investment promotion agencies (APII, FIPA) — investor due diligence tool

---

## Sprint roadmap

### Sprint 4 — Data foundation + WITS integration (NEXT)
Goal: Export Markets tab has real data for 50+ countries

Steps:
1. Write wits_loader.py — pulls tariff data from WITS API for all HS6 × top 50 reporters
   with Tunisia as partner. No auth needed. Overnight run populates export_tariffs.
2. Write comtrade_loader.py — pulls trade flows for Tunisia exports by HS6.
   Requires free Comtrade API key. Populates trade_flows table.
3. Write opportunity.py — computes opportunity_score per (hs6, reporter).
   Populates market_opportunities table.
4. Update exporter.py — reads from populated tables, returns ranked markets
   with tariff advantage, market size, growth rate.
5. Update Export Markets tab — shows real ranked data with opportunity scores.
6. Add recommendation card to Sourcing tab — narrative text output.
7. Add certificates table and certificate guidance to Legal Paths tab.

Deliverable: Demo-able export intelligence for any Tunisian HS code.

### Sprint 5 — BOM exploder v1
Goal: "Should I assemble or import?" answer for top 50 product categories

Steps:
1. Integrate Claude API into bom_exploder.py
   - Input: product name or HS code
   - Output: list of components with HS6 codes and value percentages
2. Wire BOM output to resolver + calc for each component
3. Build assembly cost model (labor + overhead + free zone option)
4. Add BOM/Assembly tab to dashboard
5. Curate top 20 product categories manually (vehicles, electronics, textiles,
   food processing, mechanical equipment)
6. Add duty_suspensions data (APII scrape)
7. Add free_zones table (manual)

Deliverable: Working BOM explosion for common products.

### Sprint 6 — Natural language + UX overhaul
Goal: Non-technical user can use the tool without knowing HS codes

Steps:
1. Add natural language HS search (Claude API) — "LED street lights" → HS 940540
2. Redesign entry point: wizard flows (import/export/assemble/opportunities)
3. Implement recommendation cards with narrative output
4. Add opportunity feed (auto-generated from market_opportunities)
5. Anti-dumping measures (JORT manual curation)
6. Alert engine v1 (monitor tariff_measures for changes on re-scrape)

Deliverable: Tool that feels intelligent, not like a spreadsheet.

### Sprint 7 — Web application
Goal: Standalone web app, no Jupyter required

Steps:
1. FastAPI backend wrapping existing engine modules
2. React frontend (wizard flows + recommendation cards + charts)
3. User authentication (simple JWT)
4. Saved scenarios (PostgreSQL, not SQLite)
5. PDF export
6. Deploy to cloud (Railway or Fly.io — cheap, fast)

Deliverable: Public URL, shareable, no setup required.

### Sprint 8 — Commercial layer
Goal: First paying users

Steps:
1. Stripe integration (free/pro/enterprise tiers)
2. REST API with API key auth (for enterprise tier)
3. Batch processing endpoint
4. Alert subscriptions (email on tariff changes)
5. Analytics (what products are users searching?)
6. onboarding flow for customs brokers

Deliverable: Revenue.

---

## Immediate next actions (before Sprint 4)

1. Test WITS API (5 min):
   curl "https://wits.worldbank.org/API/V1/SDMX/V21/rest/data/DF_WITS_Tariff_TRAINS/A.840.788.010121.MFN/?format=JSON"
   — reporter=840 (USA), partner=788 (Tunisia), product=010121

2. Register for UN Comtrade API (5 min):
   comtradeplus.un.org → create free account → copy API key → add to .env

3. Update macmap_scraper.py with proven working code (already documented)

4. Write SPRINT_4.md

---

## Key risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tunisian portal changes HTML structure | Medium | High | Store raw HTML snapshots on each scrape |
| WITS API data is 2-3 years stale | High | Medium | Use MacMap for spot-checks on key products |
| MacMap changes auth flow | Medium | Medium | Fall back to WITS for bulk, manual for gaps |
| Comtrade API rate limits slow population | Low | Low | 500 calls × 100k rows = sufficient |
| BOM LLM accuracy too low | Medium | Medium | Human review layer for high-value categories |
| Tunisian tariff law changes mid-year | Low | High | Alert engine detects on re-scrape |
| Competitor builds same thing | Low | Medium | Data + Tunisia-specific focus is the moat |

---

## What makes this defensible

1. **Tunisia-specific depth** — no competitor has 17,508 HS codes with real
   preferential rates from the actual portal. Building this for another country
   requires months of work.

2. **BOM explosion** — no free tool does automatic product decomposition
   with duty optimization. This is the feature that generates word-of-mouth.

3. **Opportunity scoring** — combining tariff advantage + market size + growth
   rate into a ranked feed is genuinely novel for SME importers/exporters.
   Bloomberg Terminal does this for large companies. Nothing exists for SMEs.

4. **Compound data advantage** — every user query that triggers a MacMap
   on-demand scrape adds to the local cache. After 6 months of usage,
   the DB covers the most commercially relevant HS codes with current data.
   The platform gets more accurate as more people use it.
