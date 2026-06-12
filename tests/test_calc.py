import sqlite3
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calc import calc_landed


def seed_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    seed = os.path.join(os.path.dirname(__file__), "fixtures", "seed.sql")
    with open(seed) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    return str(db)


def test_susp_rate_cn(tmp_path):
    db = seed_db(tmp_path)
    lc = calc_landed("854140", "CN", exw=100, incoterm="EXW", fodec=True, tcl=False, db_path=db)
    # CN gets SUSP at 5% for 854140
    assert lc.duty_rate == 5.0
    assert lc.landed > lc.exw


def test_pref_rate_tr(tmp_path):
    db = seed_db(tmp_path)
    lc_tr = calc_landed("854140", "TR", exw=100, db_path=db)
    lc_in = calc_landed("854140", "IN", exw=100, db_path=db)
    assert lc_tr.duty_rate == 0.0
    assert lc_tr.landed < lc_in.landed


def test_freight_floor(tmp_path):
    db = seed_db(tmp_path)
    lc = calc_landed("854140", "FR", exw=0, weight=0, volume=0, db_path=db)
    assert lc.freight >= 200


def test_working_capital_proportional_to_lead_days(tmp_path):
    db = seed_db(tmp_path)
    # CN ~28 transit days, MA ~4 transit days — same EXW and HS
    lc_cn = calc_landed("854140", "CN", exw=1000, db_path=db)
    lc_ma = calc_landed("854140", "MA", exw=1000, db_path=db)
    assert lc_cn.lead_days > lc_ma.lead_days
    assert lc_cn.working_capital_cost > lc_ma.working_capital_cost


def test_freight_range_order():
    from freight import FREIGHT_BENCHMARKS
    for mode, origins in FREIGHT_BENCHMARKS.items():
        for iso, bm in origins.items():
            assert bm["min"] <= bm["mid"] <= bm["max"], \
                f"Range order violated: {mode}/{iso} min={bm['min']} mid={bm['mid']} max={bm['max']}"


def test_landed_range(tmp_path):
    db = seed_db(tmp_path)
    lc = calc_landed("854140", "CN", exw=100, db_path=db)
    assert lc.landed_min <= lc.landed <= lc.landed_max
