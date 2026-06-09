import sqlite3
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search import search_hs


def load_seed(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    seed = os.path.join(os.path.dirname(__file__), "fixtures", "seed.sql")
    with open(seed) as f:
        conn.executescript(f.read())
    conn.commit()
    return conn


def test_solar_matches_854140(tmp_path):
    conn = load_seed(tmp_path)
    results = search_hs(conn, "solar")
    codes = [r.hs_code for r in results]
    assert "854140" in codes


def test_empty_query_returns_empty(tmp_path):
    conn = load_seed(tmp_path)
    assert search_hs(conn, "") == []


def test_no_match_returns_empty(tmp_path):
    conn = load_seed(tmp_path)
    results = search_hs(conn, "zzzzz_no_match_xyz")
    assert results == []
