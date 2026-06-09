"""
Jupyter ipywidgets dashboard — six tabs.
All business logic delegated to engine modules; no inline duty calculations here.
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
from freight import ORIGIN_LABELS, LEAD_DAYS, estimate_freight, USD_TO_TND

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
                text=[f"${r[2].landed:.2f}" for r in rows],
                textposition="outside",
            ))
            fig.update_layout(
                title=f"Landed Cost Comparison — HS {hs} | EXW={exw} USD",
                xaxis_title="Origin",
                yaxis_title="Landed Cost (USD)",
                height=420,
            )
            fig.show()

            print(f"\n{'Origin':<30} {'Duty%':>7} {'Freight':>9} {'CIF':>9} {'Landed':>10} {'TND':>10}")
            print("-" * 80)
            for label, iso, lc in rows:
                print(f"{label:<30} {lc.duty_rate:>6.1f}% {lc.freight:>9.2f} {lc.cif:>9.2f} {lc.landed:>10.2f} {lc.landed_tnd:>10.2f}")

    run_btn.on_click(on_run)
    controls = widgets.HBox([hs_input, exw_input, incoterm_sel, fodec_chk, tcl_chk, run_btn])
    return widgets.VBox([controls, out])


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
    run_btn = widgets.Button(description="Resolve", button_style="info")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        hs = hs_input.value.strip()
        origin = origin_sel.value
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

            # Waterfall chart
            labels = ["EXW"]
            values = [100.0]
            measures_chart = ["absolute"]
            labels.append("Freight")
            values.append(20.0)
            measures_chart.append("relative")
            labels.append("Duty")
            values.append(winner.rate)
            measures_chart.append("relative")
            labels.append("VAT")
            values.append(19.0)
            measures_chart.append("relative")
            labels.append("Landed")
            values.append(sum(values[1:]))
            measures_chart.append("total")

            fig = go.Figure(go.Waterfall(
                name="Cost build-up",
                orientation="v",
                measure=measures_chart,
                x=labels,
                y=values,
                connector={"line": {"color": "rgb(63,63,63)"}},
            ))
            fig.update_layout(
                title=f"Duty Waterfall — HS {hs} from {origin}",
                showlegend=False,
                height=360,
            )
            fig.show()

    run_btn.on_click(on_run)
    controls = widgets.HBox([hs_input, origin_sel, run_btn])
    return widgets.VBox([controls, out])


# ---------------------------------------------------------------------------
# Tab 3 — Product Search
# ---------------------------------------------------------------------------

def _build_search_tab(db_path=None):
    query_input = widgets.Text(value="solar", description="Search:", layout=widgets.Layout(width="300px"))
    run_btn = widgets.Button(description="Search", button_style="")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        with out:
            conn = _fresh_conn(db_path)
            results = search_hs(conn, query_input.value.strip())
            conn.close()
            if not results:
                print("No matches.")
                return
            print(f"{'HS Code':<12} {'Score':>7} {'MFN DD%':>8}  Description")
            print("-" * 60)
            for r in results:
                print(f"{r.hs_code:<12} {r.score:>7.1f} {r.mfn_rate:>7.1f}%  {r.description}")

    run_btn.on_click(on_run)
    return widgets.VBox([widgets.HBox([query_input, run_btn]), out])


# ---------------------------------------------------------------------------
# Tab 4 — Single Landed Cost Detail
# ---------------------------------------------------------------------------

def _build_detail_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="HS Code:", layout=widgets.Layout(width="200px"))
    origin_sel = widgets.Dropdown(
        options=_origin_options(),
        value="CN",
        description="Origin:",
        layout=widgets.Layout(width="220px"),
    )
    exw_input = widgets.FloatText(value=100.0, description="EXW (USD):", layout=widgets.Layout(width="180px"))
    incoterm_sel = widgets.Dropdown(options=["EXW", "FOB", "CIF"], value="EXW", description="Incoterm:")
    fodec_chk = widgets.Checkbox(value=True, description="FODEC")
    tcl_chk = widgets.Checkbox(value=False, description="TCL")
    run_btn = widgets.Button(description="Calculate", button_style="primary")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        with out:
            try:
                lc = calc_landed(
                    hs_input.value.strip(),
                    origin_sel.value,
                    exw_input.value,
                    incoterm=incoterm_sel.value,
                    fodec=fodec_chk.value,
                    tcl=tcl_chk.value,
                    db_path=db_path,
                )
            except Exception as e:
                print(f"Error: {e}")
                return

            print(f"Origin        : {ORIGIN_LABELS.get(lc.origin, lc.origin)}")
            print(f"Agreement     : {lc.agreement}")
            print(f"Lead Days     : {lc.lead_days}")
            print(f"EXW           : ${lc.exw:.2f}")
            print(f"Freight       : ${lc.freight:.2f}")
            print(f"CIF           : ${lc.cif:.2f}")
            print(f"Duty Rate     : {lc.duty_rate:.1f}%")
            print(f"Duty Amount   : ${lc.duty_amt:.2f}")
            print(f"FODEC         : ${lc.fodec:.2f}")
            print(f"TCL           : ${lc.tcl:.2f}")
            print(f"VAT Rate      : {lc.vat_rate:.1f}%")
            print(f"VAT Amount    : ${lc.vat_amt:.2f}")
            print(f"Landed (USD)  : ${lc.landed:.2f}")
            print(f"Landed (TND)  : {lc.landed_tnd:.2f}")

    run_btn.on_click(on_run)
    row1 = widgets.HBox([hs_input, origin_sel, exw_input])
    row2 = widgets.HBox([incoterm_sel, fodec_chk, tcl_chk, run_btn])
    return widgets.VBox([row1, row2, out])


# ---------------------------------------------------------------------------
# Tab 5 — Freight & Lead Times
# ---------------------------------------------------------------------------

def _build_freight_tab(db_path=None):
    origin_sel = widgets.Dropdown(
        options=_origin_options(),
        value="CN",
        description="Origin:",
        layout=widgets.Layout(width="220px"),
    )
    weight_input = widgets.FloatText(value=500.0, description="Weight (kg):")
    volume_input = widgets.FloatText(value=2.0, description="Volume (m³):")
    run_btn = widgets.Button(description="Estimate", button_style="")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        with out:
            iso = origin_sel.value
            freight = estimate_freight(iso, weight_input.value, volume_input.value)
            lead = LEAD_DAYS.get(iso, 21)
            print(f"Origin        : {ORIGIN_LABELS.get(iso, iso)}")
            print(f"Freight Est.  : ${freight:.2f}")
            print(f"Lead Days     : {lead}")

    run_btn.on_click(on_run)
    return widgets.VBox([widgets.HBox([origin_sel, weight_input, volume_input, run_btn]), out])


# ---------------------------------------------------------------------------
# Tab 6 — CKD Analysis (stub: parts duty = 50% of finished duty)
# ---------------------------------------------------------------------------

def _build_ckd_tab(db_path=None):
    hs_input = widgets.Text(value="854140", description="Finished HS:", layout=widgets.Layout(width="200px"))
    origin_sel = widgets.Dropdown(
        options=_origin_options(),
        value="CN",
        description="Origin:",
        layout=widgets.Layout(width="220px"),
    )
    exw_input = widgets.FloatText(value=100.0, description="EXW (USD):")
    run_btn = widgets.Button(description="Analyse CKD", button_style="warning")
    out = widgets.Output()

    def on_run(_):
        out.clear_output()
        with out:
            conn = _fresh_conn(db_path)
            finished = resolve_duty(conn, hs_input.value.strip(), origin_sel.value)
            conn.close()

            finished_rate = finished.rate if finished else 0.0
            # Stub: parts duty assumed at 50% of finished duty rate
            parts_rate = finished_rate * 0.5

            print(f"Finished goods duty : {finished_rate:.1f}%")
            print(f"Parts duty (est.)   : {parts_rate:.1f}%  [50% assumption — DEFERRED]")
            print()
            print("CKD BOM-level analysis not yet implemented.")
            print("See SESSION_STATE.md for deferred items.")

    run_btn.on_click(on_run)
    return widgets.VBox([widgets.HBox([hs_input, origin_sel, exw_input, run_btn]), out])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_dashboard(db_path=None):
    """Construct and return the six-tab ipywidgets dashboard."""
    tab = widgets.Tab()
    tab.children = [
        _build_sourcing_tab(db_path),
        _build_legal_paths_tab(db_path),
        _build_search_tab(db_path),
        _build_detail_tab(db_path),
        _build_freight_tab(db_path),
        _build_ckd_tab(db_path),
    ]
    tab.set_title(0, "Sourcing")
    tab.set_title(1, "Legal Paths")
    tab.set_title(2, "Search")
    tab.set_title(3, "Detail")
    tab.set_title(4, "Freight")
    tab.set_title(5, "CKD")
    return tab


if __name__ == "__main__":
    # When run via %run dashboard.py in Jupyter
    dashboard = build_dashboard()
    display(dashboard)
