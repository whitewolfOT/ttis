"""
Loads FREIGHT_BENCHMARKS from freight.py into the freight_benchmarks table.
Idempotent — uses INSERT OR REPLACE.
"""
from datetime import date

from db import get_conn, ensure_schema, DB_PATH
from freight import FREIGHT_BENCHMARKS, LEAD_DAYS

SOURCE = "Freightos FBX index + shipping line rate cards"
EFFECTIVE_DATE = "2026-06-01"
CONFIDENCE = "MEDIUM"


def load_freight_benchmarks(db_path=None) -> int:
    """Insert/replace FREIGHT_BENCHMARKS into freight_benchmarks table. Returns row count inserted."""
    conn = get_conn(db_path or DB_PATH)
    ensure_schema(conn)

    rows = []
    for mode, origins in FREIGHT_BENCHMARKS.items():
        for origin_iso2, bm in origins.items():
            rows.append((
                origin_iso2,
                mode,
                float(bm["min"]),
                float(bm["mid"]),
                float(bm["max"]),
                int(bm["days"]),
                SOURCE,
                EFFECTIVE_DATE,
                CONFIDENCE,
            ))

    conn.executemany("""
        INSERT OR REPLACE INTO freight_benchmarks
            (origin_iso2, mode, min_usd, mid_usd, max_usd, transit_days,
             source, effective_date, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()

    n = conn.execute("SELECT COUNT(*) FROM freight_benchmarks").fetchone()[0]
    conn.close()
    return n


if __name__ == "__main__":
    n = load_freight_benchmarks()
    print(f"freight_benchmarks: {n} rows loaded")
