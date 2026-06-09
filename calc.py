import warnings
from pathlib import Path
from typing import Optional

from schemas import LandedCost
from resolver import resolve_duty
from freight import estimate_freight, LEAD_DAYS, USD_TO_TND
from db import get_conn, ensure_schema, DB_PATH


def calc_landed(
    hs: str,
    origin: str,
    exw: float,
    weight: float = 500,
    volume: float = 2.0,
    incoterm: str = "EXW",
    fodec: bool = True,
    tcl: bool = False,
    db_path=None,
) -> LandedCost:
    path = Path(db_path) if db_path else DB_PATH
    conn = get_conn(path)
    ensure_schema(conn)

    resolved = resolve_duty(conn, hs, origin)
    conn.close()

    if resolved is None:
        warnings.warn(f"calc_landed: no duty found for hs={hs} origin={origin}; using 0%")
        duty_rate = 0.0
        agreement = "MFN"
    else:
        duty_rate = resolved.rate
        agreement = resolved.duty_type

    freight = estimate_freight(origin, weight, volume)

    if incoterm == "EXW":
        cif = exw + freight
    elif incoterm == "FOB":
        cif = exw + freight * 0.7
    else:
        cif = exw

    duty_amt = cif * (duty_rate / 100)
    base = cif + duty_amt
    fodec_amt = base * 0.01 if fodec else 0.0
    tcl_amt = (base + fodec_amt) * 0.002 if tcl else 0.0

    cur_conn = get_conn(path)
    ensure_schema(cur_conn)
    vat_row = cur_conn.execute(
        "SELECT rate FROM tariff_measures WHERE hs_code=? AND tax_type='TVA' AND duty_type='MFN' LIMIT 1",
        (hs,)
    ).fetchone()
    cur_conn.close()
    vat_rate = vat_row[0] if vat_row else 19.0

    vat_amt = (base + fodec_amt + tcl_amt) * (vat_rate / 100)
    landed = base + fodec_amt + tcl_amt + vat_amt
    landed_tnd = landed * USD_TO_TND
    lead_days = LEAD_DAYS.get(origin, 21)

    return LandedCost(
        origin=origin,
        agreement=agreement,
        lead_days=lead_days,
        exw=exw,
        freight=freight,
        cif=cif,
        duty_rate=duty_rate,
        duty_amt=duty_amt,
        fodec=fodec_amt,
        tcl=tcl_amt,
        vat_rate=vat_rate,
        vat_amt=vat_amt,
        landed=landed,
        landed_tnd=landed_tnd,
    )
