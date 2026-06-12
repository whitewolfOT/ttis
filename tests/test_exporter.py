import sqlite3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exporter import get_export_markets, get_competitor_comparison


def load_seed(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    seed = os.path.join(os.path.dirname(__file__), "fixtures", "seed.sql")
    with open(seed) as f:
        conn.executescript(f.read())
    conn.commit()
    return conn


def test_exporter_importable():
    from exporter import get_export_markets, get_competitor_comparison, AFRICAN_ISO2
    assert callable(get_export_markets)
    assert callable(get_competitor_comparison)
    assert "TN" in AFRICAN_ISO2


def test_get_export_markets_empty_when_no_data(tmp_path):
    conn = load_seed(tmp_path)
    results = get_export_markets(conn, "854140")
    assert results == []


def test_get_competitor_comparison_stub(tmp_path):
    conn = load_seed(tmp_path)
    result = get_competitor_comparison(conn, "854140", "CN", "FR")
    assert "tunisia_rate" in result
    assert "has_advantage" in result
    assert result["has_advantage"] is False
