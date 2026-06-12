import warnings
from pathlib import Path

from schemas import LandedCost
from resolver import resolve_duty
from freight import (
    estimate_freight, LEAD_DAYS, USD_TO_TND,
    CURRENCY_FLAG, SUPPLIER_RISK, MODE_SEA_FCL,
)
from db import get_conn, ensure_schema, DB_PATH


def _apply_formula(cif: float, duty_rate: float, fodec: bool, tcl: bool, vat_rate: float) -> tuple:
    """Returns (duty_amt, base, fodec_amt, tcl_amt, vat_amt, landed)."""
    duty_amt  = cif * (duty_rate / 100)
    base      = cif + duty_amt
    fodec_amt = base * 0.01 if fodec else 0.0
    tcl_amt   = (base + fodec_amt) * 0.002 if tcl else 0.0
    vat_amt   = (base + fodec_amt + tcl_amt) * (vat_rate / 100)
    landed    = base + fodec_amt + tcl_amt + vat_amt
    return duty_amt, base, fodec_amt, tcl_amt, vat_amt, landed


def calc_landed(
    hs: str,
    origin: str,
    exw: float,
    weight_kg: float = 500,
    volume_cbm: float = 2.0,
    incoterm: str = "EXW",
    freight_mode: str = MODE_SEA_FCL,
    own_freight_usd: float = None,
    fodec: bool = True,
    tcl: bool = False,
    financing_rate: float = 0.10,
    db_path=None,
    # Legacy parameter aliases (Sprint 1/2 callers)
    weight: float = None,
    volume: float = None,
) -> LandedCost:
    # Support old kwarg names from Sprint 1/2 tests
    if weight is not None:
        weight_kg = weight
    if volume is not None:
        volume_cbm = volume

    path = Path(db_path) if db_path else DB_PATH
    conn = get_conn(path)
    ensure_schema(conn)

    resolved = resolve_duty(conn, hs, origin)

    vat_row = conn.execute(
        "SELECT rate FROM tariff_measures WHERE hs_code=? AND tax_type='TVA' AND duty_type='MFN' LIMIT 1",
        (hs,)
    ).fetchone()
    conn.close()

    duty_rate = resolved.rate if resolved else 0.0
    agreement = resolved.duty_type if resolved else "MFN"
    if resolved is None:
        warnings.warn(f"calc_landed: no duty found for hs={hs} origin={origin}; using 0%")

    vat_rate = vat_row[0] if vat_row else 19.0

    # Freight — new dict-based API
    freight_result = estimate_freight(origin, weight_kg, volume_cbm, freight_mode, own_freight_usd)
    freight_mid = freight_result["mid_usd"]
    freight_min = freight_result["min_usd"]
    freight_max = freight_result["max_usd"]

    def _cif(f: float) -> float:
        if incoterm == "EXW":
            return exw + f
        elif incoterm == "FOB":
            return exw + f * 0.7
        else:
            return exw

    cif     = _cif(freight_mid)
    cif_min = _cif(freight_min)
    cif_max = _cif(freight_max)

    duty_amt, base, fodec_amt, tcl_amt, vat_amt, landed = _apply_formula(
        cif, duty_rate, fodec, tcl, vat_rate
    )
    _, _, _, _, _, landed_min = _apply_formula(cif_min, duty_rate, fodec, tcl, vat_rate)
    _, _, _, _, _, landed_max = _apply_formula(cif_max, duty_rate, fodec, tcl, vat_rate)

    landed_tnd = landed * USD_TO_TND
    lead_days  = freight_result.get("transit_days") or LEAD_DAYS.get(origin, 21)

    working_capital_cost = (cif + duty_amt) * financing_rate * (lead_days / 365)

    return LandedCost(
        origin=origin,
        agreement=agreement,
        lead_days=lead_days,
        exw=exw,
        freight=freight_mid,
        cif=cif,
        duty_rate=duty_rate,
        duty_amt=duty_amt,
        fodec=fodec_amt,
        tcl=tcl_amt,
        vat_rate=vat_rate,
        vat_amt=vat_amt,
        landed=landed,
        landed_tnd=landed_tnd,
        freight_min=freight_min,
        freight_max=freight_max,
        freight_mode=freight_result["mode"],
        landed_min=landed_min,
        landed_max=landed_max,
        working_capital_cost=working_capital_cost,
        currency_flag=CURRENCY_FLAG.get(origin, ""),
        supplier_risk=SUPPLIER_RISK.get(origin, ""),
    )
