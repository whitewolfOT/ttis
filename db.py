import sqlite3
from pathlib import Path
from typing import List

from schemas import TariffMeasure

DB_PATH = Path("tunisia_trade.db")


def get_conn(db_path=DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def ensure_schema(conn) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tariff_measures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hs_code TEXT NOT NULL,
            origin_country TEXT NOT NULL,
            duty_type TEXT NOT NULL,
            tax_type TEXT NOT NULL,
            rate REAL NOT NULL,
            agreement_name TEXT,
            measure_type TEXT,
            valid_from TEXT,
            valid_to TEXT,
            source_url TEXT,
            legal_basis TEXT,
            UNIQUE(hs_code, origin_country, duty_type, tax_type, agreement_name)
        );
        CREATE TABLE IF NOT EXISTS agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT,
            valid_from TEXT,
            valid_to TEXT
        );
        CREATE TABLE IF NOT EXISTS agreement_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agreement_name TEXT NOT NULL,
            country_iso2 TEXT NOT NULL,
            UNIQUE(agreement_name, country_iso2)
        );
    """)
    conn.commit()


def upsert_measures(conn, measures: list) -> int:
    sql = """
        INSERT OR IGNORE INTO tariff_measures
            (hs_code, origin_country, duty_type, tax_type, rate, agreement_name, valid_from, valid_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = [
        (m.hs_code, m.origin_country, m.duty_type, m.tax_type,
         m.rate, m.agreement_name, m.valid_from, m.valid_to)
        for m in measures
    ]
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def load_hs_index(conn) -> list:
    cur = conn.execute(
        "SELECT hs_code, '' as description, rate FROM tariff_measures WHERE duty_type='MFN' AND tax_type='DD'"
    )
    return [{"hs_code": r[0], "description": r[1], "vat_rate": r[2]} for r in cur.fetchall()]
