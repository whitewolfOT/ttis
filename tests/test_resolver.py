import sqlite3
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resolver import resolve_duty, enumerate_paths


def load_seed(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    seed = os.path.join(os.path.dirname(__file__), "fixtures", "seed.sql")
    with open(seed) as f:
        conn.executescript(f.read())
    conn.commit()
    return conn


def test_pref_wins_over_mfn(tmp_path):
    conn = load_seed(tmp_path)
    r = resolve_duty(conn, "854140", "TR")
    assert r is not None
    assert r.duty_type == "PREF"
    assert r.rate == 0.0


def test_susp_wins_over_pref_and_mfn(tmp_path):
    conn = load_seed(tmp_path)
    r = resolve_duty(conn, "854140", "CN")
    assert r is not None
    assert r.duty_type == "SUSP"
    assert r.rate == 5.0


def test_pref_for_morocco(tmp_path):
    conn = load_seed(tmp_path)
    r = resolve_duty(conn, "870321", "MA")
    assert r is not None
    assert r.duty_type == "PREF"
    assert r.rate == 0.0


def test_mfn_for_non_fta_origin(tmp_path):
    conn = load_seed(tmp_path)
    r = resolve_duty(conn, "870321", "IN")
    assert r is not None
    assert r.duty_type == "MFN"
    assert r.rate == 30.0


def test_ancestor_hs_lookup(tmp_path):
    conn = load_seed(tmp_path)
    r = resolve_duty(conn, "8541", "TR")
    assert r is not None
    assert r.duty_type == "PREF"
    assert r.rate == 0.0


def test_unknown_hs_returns_none(tmp_path):
    conn = load_seed(tmp_path)
    r = resolve_duty(conn, "9999", "CN")
    assert r is None
