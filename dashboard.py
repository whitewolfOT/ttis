"""
Jupyter ipywidgets dashboard — six tabs.
All business logic delegated to engine modules; no inline duty calculations here.

Tab order: Sourcing | Legal Paths | Export Markets | Working Capital | Break-Even | Flags
"""
import warnings
from pathlib import Path

import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go

from db import get_conn, ensure_schema, DB_PATH
from resolver import enumerate_paths, resolve_duty
from calc import calc_landed
from search import search_hs
from freight import (
    ORIGIN_LABELS, LEAD_DAYS, estimate_freight, USD_TO_TND,
    MODE_SEA_FCL, MODE_SEA_LCL, MODE_AIR, MODE_LAND,
)
from exporter import get_export_markets, get_competitor_comparison, AFRICAN_ISO2

# Break-even cache: key (hs, origin, exw_rounded) → LandedCost
_BREAKEVEN_CACHE: dict = {}

_MODE_OPTIONS = [
    ("Sea FCL (container)", MODE_SEA_FCL),
    ("Sea LCL (per CBM)",   MODE_SEA_LCL),
    ("Air (per kg)",        MODE_AIR),
    ("Land (truck)",        MODE_LAND),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_conn(db_path=None):
    """Open a new connection each call (ipywidgets threading requirement)."""
    path = Path(db_path) if db_path else DB_PATH
    conn = get_conn(path)
    ensure_schema(conn)
    return conn


def _origin_options():
    return [(label, iso) for iso, label in sorted(ORIGIN_LABELS.items(), key=lambda x: x[1])]


# ---------------------------------------------------------------------------
# Tab 1 — Sourcing comparison
# ---------------------------------------------------------------------------

def _build_sourcing_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="200px"))
    exw_input = widgets.FloatText(value=100.0, description="EXW (USD):", layout=widgets.Layout(width="180px"))
    incoterm_sel = widgets.Dropdown(
        options=["EXW", "FOB", "CIF"],
        value="EXW",
        description="Incoterm:",
        layout=widgets.Layout(width="160px"),
    )
    mode_sel = widgets.Dropdown(
        options=_MODE_OPTIONS,
        value=MODE_SEA_FCL,
        description="Freight:",
        layout=widgets.Layout(width="200px"),
    )
    fodec_chk = widgets.Checkbox(value=True, description="FODEC (1%)")
    tcl_chk = widgets.Checkbox(value=False, description="TCL (0.2%)")
    run_btn = widgets.Button(description="Calculate", button_style="primary")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs = hs_input.value.strip()
        exw = exw_input.value
        with out:
            rows = []
            for label, iso in _origin_options():
                try:
                    lc = calc_landed(
                        hs, iso, exw,
                        incoterm=incoterm_sel.value,
                        freight_mode=mode_sel.value,
                        fodec=fodec_chk.value,
                        tcl=tcl_chk.value,
                        db_path=db_path,
                    )
                    rows.append((label, iso, lc))
                except Exception as e:
                    warnings.warn(f"Sourcing calc failed for {iso}: {e}")

            if not rows:
                print("No results — is the DB populated?")
                return

            rows.sort(key=lambda r: r[2].landed)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[r[0] for r in rows],
                y=[r[2].landed for r in rows],
                marker_color=["green" if r[2].duty_rate == 0 else "steelblue" for r in rows],
                text=[f"${r[2].landed:.0f}" for r in rows],
                textposition="outside",
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[r[2].landed_max - r[2].landed for r in rows],
                    arrayminus=[r[2].landed - r[2].landed_min for r in rows],
                ),
            ))
            fig.update_layout(
                title=f"Landed Cost Comparison — HS {hs} | EXW={exw} USD",
                xaxis_title="Origin",
                yaxis_title="Landed Cost (USD)",
                height=440,
            )
            fig.show()

            print(f"\n{'Origin':<30} {'Duty%':>7} {'Freight':>9} {'CIF':>9} "
                  f"{'Landed':>10} {'Min':>9} {'Max':>9} {'Currency':<10} {'Risk'}")
            print("-" * 105)
            for label, iso, lc in rows:
                risk = f"⚠ {lc.supplier_risk}" if lc.supplier_risk == "HIGH" else ""
                print(f"{label:<30} {lc.duty_rate:>6.1f}% {lc.freight:>9.2f} {lc.cif:>9.2f} "
                      f"{lc.landed:>10.2f} {lc.landed_min:>9.2f} {lc.landed_max:>9.2f} "
                      f"{lc.currency_flag:<10} {risk}")

    run_btn.on_click(on_run)
    row1 = widgets.HBox([hs_input, exw_input, incoterm_sel, mode_sel])
    row2 = widgets.HBox([fodec_chk, tcl_chk, run_btn])
    return widgets.VBox([row1, row2, out])


# ---------------------------------------------------------------------------
# Tab 2 — Legal Paths (duty waterfall)
# ---------------------------------------------------------------------------

def _build_legal_paths_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="200px"))
    origin_sel = widgets.Dropdown(
        options=_origin_options(),
        value="CN",
        description="Origin:",
        layout=widgets.Layout(width="220px"),
    )
    exw_input = widgets.FloatText(value=100.0, description="EXW (USD):", layout=widgets.Layout(width="180px"))
    run_btn = widgets.Button(description="Resolve", button_style="info")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs = hs_input.value.strip()
        origin = origin_sel.value
        exw = exw_input.value
        with out:
            conn = _fresh_conn(db_path)
            paths = enumerate_paths(conn, hs, origin)
            conn.close()
            if not paths:
                print(f"No measures found for HS {hs} / {origin}")
                return

            winner = paths[0]
            print(f"Best path: {winner.duty_type} @ {winner.rate}% "
                  f"(specificity={winner.specificity}, agreement={winner.agreement_name})\n")
            print(f"{'Rank':<5} {'Type':<8} {'Rate':>7} {'HS Match':<12} {'Agreement'}")
            print("-" * 60)
            for p in paths:
                print(f"{p.rank:<5} {p.duty_type:<8} {p.rate:>6.1f}% {p.hs_code:<12} {p.agreement_name or '—'}")

            # Waterfall using real calc values
            try:
                lc = calc_landed(hs, origin, exw, db_path=db_path)
                wf_labels   = ["EXW", "Freight", "Duty", "FODEC/TCL", "VAT", "Landed"]
                wf_values   = [lc.exw, lc.freight, lc.duty_amt,
                               lc.fodec + lc.tcl, lc.vat_amt, lc.landed]
                wf_measures = ["absolute", "relative", "relative", "relative", "relative", "total"]
                fig = go.Figure(go.Waterfall(
                    orientation="v",
                    measure=wf_measures,
                    x=wf_labels,
                    y=wf_values,
                    connector={"line": {"color": "rgb(63,63,63)"}},
                ))
                fig.update_layout(
                    title=f"Cost Build-up — HS {hs} from {origin} | EXW={exw} USD",
                    showlegend=False,
                    height=360,
                )
                fig.show()
            except Exception as e:
                print(f"(Waterfall skipped: {e})")

    run_btn.on_click(on_run)
    controls = widgets.HBox([hs_input, origin_sel, exw_input, run_btn])
    return widgets.VBox([controls, out])


# ---------------------------------------------------------------------------
# Tab 3 — 🌍 Export Markets (stub — MacMap blocked)
# ---------------------------------------------------------------------------

def _build_export_markets_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="200px"))
    africa_chk = widgets.Checkbox(value=False, description="Africa only")
    advantage_slider = widgets.IntSlider(
        value=0, min=0, max=20, step=1,
        description="Min advantage %:",
        layout=widgets.Layout(width="340px"),
    )
    email_input = widgets.Text(
        value="", description="MacMap email:",
        placeholder="your@email.com",
        layout=widgets.Layout(width="280px"),
    )
    pw_input = widgets.Password(
        value="", description="Password:",
        layout=widgets.Layout(width="240px"),
    )
    run_btn = widgets.Button(description="Find Markets", button_style="success")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs6 = hs_input.value.strip()[:6]
        with out:
            conn = _fresh_conn(db_path)
            results = get_export_markets(
                conn, hs6,
                macmap_email=email_input.value.strip() or None,
                macmap_password=pw_input.value or None,
                africa_only=africa_chk.value,
            )
            conn.close()

            if not results:
                print("No export data yet.")
                print()
                print("MacMap scraping is currently blocked by the network egress policy.")
                print("To fetch data, run poc_macmap.py from a machine with unrestricted")
                print("internet access, then re-run with your MacMap credentials above.")
                print()
                print("Sprint 4 will investigate WITS API / WTO bulk download as alternatives.")
                return

            filtered = [r for r in results if (r.get("tariff_advantage") or 0) >= advantage_slider.value]
            if africa_chk.value:
                filtered = [r for r in filtered if r.get("reporter_iso2") in AFRICAN_ISO2]

            print(f"{'Country':<30} {'Duty%':>7} {'Regime':<20} {'vs MFN':>8} {'AfCFTA':<8} {'Currency'}")
            print("-" * 85)
            for r in filtered[:50]:
                afcfta = "🟡" if r.get("reporter_iso2") in AFRICAN_ISO2 else ""
                print(f"{r.get('reporter_name',''):<30} {r.get('tariff_rate',0):>6.1f}% "
                      f"{r.get('tariff_regime',''):.<20} {r.get('tariff_advantage',0):>7.1f}% "
                      f"{afcfta:<8}")
            print()
            print("🟡 AfCFTA: Tunisia signed but not yet ratified. Rates shown are current applied rates.")

    run_btn.on_click(on_run)
    row1 = widgets.HBox([hs_input, africa_chk, run_btn])
    row2 = widgets.HBox([advantage_slider])
    row3 = widgets.HBox([email_input, pw_input])
    return widgets.VBox([row1, row2, row3, out])


# ---------------------------------------------------------------------------
# Tab 4 — 💰 Working Capital
# ---------------------------------------------------------------------------

def _build_working_capital_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="200px"))
    origins_sel = widgets.SelectMultiple(
        options=_origin_options(),
        value=["CN", "TR", "FR", "IN"],
        description="Origins:",
        layout=widgets.Layout(width="260px", height="140px"),
    )
    value_input = widgets.FloatText(value=10000.0, description="Shipment USD:", layout=widgets.Layout(width="200px"))
    rate_slider = widgets.FloatSlider(
        value=10.0, min=5.0, max=25.0, step=0.5,
        description="Financing %:",
        readout_format=".1f",
        layout=widgets.Layout(width="340px"),
    )
    mode_sel = widgets.Dropdown(
        options=_MODE_OPTIONS,
        value=MODE_SEA_FCL,
        description="Freight mode:",
        layout=widgets.Layout(width="220px"),
    )
    run_btn = widgets.Button(description="Calculate", button_style="primary")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs = hs_input.value.strip()
        exw = value_input.value
        fin_rate = rate_slider.value / 100.0
        with out:
            rows = []
            for iso in origins_sel.value:
                label = ORIGIN_LABELS.get(iso, iso)
                try:
                    lc = calc_landed(
                        hs, iso, exw,
                        freight_mode=mode_sel.value,
                        financing_rate=fin_rate,
                        db_path=db_path,
                    )
                    rows.append((label, iso, lc))
                except Exception as e:
                    warnings.warn(f"WC calc failed for {iso}: {e}")

            if not rows:
                print("No results.")
                return

            rows.sort(key=lambda r: r[2].landed + r[2].working_capital_cost)

            print(f"\n{'Origin':<30} {'Transit':>8} {'Freight':>9} {'Duty':>9} "
                  f"{'Financing':>10} {'True Cost':>11}")
            print("-" * 82)
            for label, iso, lc in rows:
                true_cost = lc.landed + lc.working_capital_cost
                print(f"{label:<30} {lc.lead_days:>7}d {lc.freight:>9.2f} {lc.duty_amt:>9.2f} "
                      f"{lc.working_capital_cost:>10.2f} {true_cost:>11.2f}")

            if len(rows) >= 2:
                cheapest = rows[0]
                dearest  = rows[-1]
                save_total = (dearest[2].landed + dearest[2].working_capital_cost) - \
                             (cheapest[2].landed + cheapest[2].working_capital_cost)
                save_fin   = dearest[2].working_capital_cost - cheapest[2].working_capital_cost
                day_diff   = dearest[2].lead_days - cheapest[2].lead_days
                print(f"\nSourcing from {cheapest[0]} saves ${save_total:.2f} vs {dearest[0]} "
                      f"per shipment, including ${save_fin:.2f} in financing savings over "
                      f"{day_diff} days transit difference.")

            # Bar chart: total true cost
            fig = go.Figure(go.Bar(
                x=[r[0] for r in rows],
                y=[r[2].landed + r[2].working_capital_cost for r in rows],
                text=[f"${r[2].landed + r[2].working_capital_cost:.0f}" for r in rows],
                textposition="outside",
                marker_color="coral",
            ))
            fig.update_layout(
                title=f"True Total Cost (freight + duty + financing) — HS {hs}",
                yaxis_title="USD",
                height=380,
            )
            fig.show()

    run_btn.on_click(on_run)
    row1 = widgets.HBox([hs_input, value_input, mode_sel])
    row2 = widgets.HBox([origins_sel, widgets.VBox([rate_slider, run_btn])])
    return widgets.VBox([row1, row2, out])


# ---------------------------------------------------------------------------
# Tab 5 — ⚡ Break-Even
# ---------------------------------------------------------------------------

def _build_breakeven_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="200px"))
    origins_sel = widgets.SelectMultiple(
        options=_origin_options(),
        value=["CN", "TR", "FR"],
        description="Origins:",
        layout=widgets.Layout(width="260px", height="120px"),
    )
    exw_min_input = widgets.FloatText(value=50.0,  description="EXW min:", layout=widgets.Layout(width="160px"))
    exw_max_input = widgets.FloatText(value=500.0, description="EXW max:", layout=widgets.Layout(width="160px"))
    steps_slider  = widgets.IntSlider(
        value=10, min=5, max=20, step=1,
        description="Steps:",
        layout=widgets.Layout(width="280px"),
    )
    mode_sel = widgets.Dropdown(
        options=_MODE_OPTIONS,
        value=MODE_SEA_FCL,
        description="Freight mode:",
        layout=widgets.Layout(width="220px"),
    )
    run_btn = widgets.Button(description="Calculate", button_style="warning")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs      = hs_input.value.strip()
        exw_lo  = exw_min_input.value
        exw_hi  = exw_max_input.value
        n_steps = steps_slider.value
        f_mode  = mode_sel.value
        origins = list(origins_sel.value)

        # Cap at 20 × 20 = 400 calcs
        if len(origins) * n_steps > 400:
            origins = origins[:20]
            n_steps = min(n_steps, 400 // max(len(origins), 1))

        with out:
            if exw_hi <= exw_lo:
                print("EXW max must be greater than EXW min.")
                return

            step_size = (exw_hi - exw_lo) / (n_steps - 1) if n_steps > 1 else 1
            exw_points = [round(exw_lo + i * step_size, 2) for i in range(n_steps)]

            fig = go.Figure()
            series: dict = {}

            for iso in origins:
                label = ORIGIN_LABELS.get(iso, iso)
                landed_vals = []
                for exw in exw_points:
                    cache_key = (hs, iso, round(exw, 1), f_mode)
                    if cache_key in _BREAKEVEN_CACHE:
                        lc = _BREAKEVEN_CACHE[cache_key]
                    else:
                        try:
                            lc = calc_landed(hs, iso, exw, freight_mode=f_mode, db_path=db_path)
                            _BREAKEVEN_CACHE[cache_key] = lc
                        except Exception as e:
                            warnings.warn(f"Break-even calc failed {iso} exw={exw}: {e}")
                            lc = None
                    landed_vals.append(lc.landed if lc else None)

                series[iso] = landed_vals
                fig.add_trace(go.Scatter(
                    x=exw_points, y=landed_vals,
                    mode="lines+markers",
                    name=label,
                ))

            # Annotate crossover points between first two origins
            if len(origins) >= 2:
                iso_a, iso_b = origins[0], origins[1]
                vals_a, vals_b = series[iso_a], series[iso_b]
                for i in range(len(exw_points) - 1):
                    if None in (vals_a[i], vals_b[i], vals_a[i+1], vals_b[i+1]):
                        continue
                    if (vals_a[i] - vals_b[i]) * (vals_a[i+1] - vals_b[i+1]) < 0:
                        cross_exw = round((exw_points[i] + exw_points[i+1]) / 2, 1)
                        label_a = ORIGIN_LABELS.get(iso_a, iso_a)
                        label_b = ORIGIN_LABELS.get(iso_b, iso_b)
                        cheaper = label_a if vals_a[i+1] < vals_b[i+1] else label_b
                        fig.add_vline(x=cross_exw, line_dash="dot", line_color="gray")
                        fig.add_annotation(
                            x=cross_exw, y=max(vals_a[i], vals_b[i]),
                            text=f"{cheaper} cheaper below ${cross_exw}",
                            showarrow=True, arrowhead=2, font=dict(size=10),
                        )

            fig.update_layout(
                title=f"Break-Even Analysis — HS {hs}",
                xaxis_title="EXW Price (USD)",
                yaxis_title="Landed Cost (USD)",
                height=440,
                hovermode="x unified",
            )
            fig.show()

    run_btn.on_click(on_run)
    row1 = widgets.HBox([hs_input, mode_sel])
    row2 = widgets.HBox([origins_sel, widgets.VBox([exw_min_input, exw_max_input, steps_slider, run_btn])])
    return widgets.VBox([row1, row2, out])


# ---------------------------------------------------------------------------
# Tab 6 — 🚨 Flags
# ---------------------------------------------------------------------------

def _build_flags_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="220px"))
    run_btn = widgets.Button(description="Check Flags", button_style="danger")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs = hs_input.value.strip()
        with out:
            conn = _fresh_conn(db_path)

            # 1. Import / Export Regime
            row = conn.execute(
                "SELECT import_regime, export_regime FROM hs_details WHERE hs_code=?", (hs,)
            ).fetchone()
            print("── 1. Import / Export Regime ─────────────────────────")
            if row:
                print(f"  Import : {row[0] or 'Unknown'}")
                print(f"  Export : {row[1] or 'Unknown'}")
            else:
                print("  No regime data found for this HS code.")

            # 2. Anti-dumping / Safeguard
            print()
            print("── 2. Anti-dumping / Safeguard ───────────────────────")
            ad_rows = conn.execute(
                "SELECT origin_country, measure_type, additional_rate, valid_to, legal_reference "
                "FROM antidumping_measures WHERE hs_code=?", (hs,)
            ).fetchall()
            if ad_rows:
                for r in ad_rows:
                    print(f"  {r[1]} on {r[0]}: +{r[2]}% until {r[3]} [{r[4]}]")
            else:
                print("  No active measures recorded. Data pending (Sprint 4).")

            # 3. Duty Suspension
            print()
            print("── 3. Duty Suspension ────────────────────────────────")
            susp = conn.execute(
                "SELECT legal_basis, notes FROM duty_suspensions WHERE hs_code=?", (hs,)
            ).fetchone()
            if susp:
                print(f"  ✅ This HS code may qualify for duty suspension under {susp[0]}.")
                if susp[1]:
                    print(f"     {susp[1]}")
            else:
                print("  Duty suspension data pending (Sprint 4).")

            # 4. Free Zone
            print()
            print("── 4. Free Zone ──────────────────────────────────────")
            print("  🏭 Free zone analysis (Bizerte ZFBA and others) coming in Sprint 4.")
            print("     Relevant for manufacturers with >30% re-export or value-add activity.")

            conn.close()

    run_btn.on_click(on_run)
    return widgets.VBox([widgets.HBox([hs_input, run_btn]), out])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_dashboard(db_path=None):
    """Construct and return the six-tab ipywidgets dashboard."""
    tab = widgets.Tab()
    tab.children = [
        _build_sourcing_tab(db_path),
        _build_legal_paths_tab(db_path),
        _build_export_markets_tab(db_path),
        _build_working_capital_tab(db_path),
        _build_breakeven_tab(db_path),
        _build_flags_tab(db_path),
    ]
    titles = ["Sourcing", "Legal Paths", "Export Markets", "Working Capital", "Break-Even", "Flags"]
    for i, title in enumerate(titles):
        tab.set_title(i, title)
    return tab


if __name__ == "__main__":
    dashboard = build_dashboard()
    display(dashboard)
