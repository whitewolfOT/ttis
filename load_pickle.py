"""
One-off loader: scrape_progress.pkl → tunisia_trade.db

Inserts:
  - MFN DD rows (one per HS code)
  - MFN TVA rows (one per HS code)
  - OTHER tax rows (RPD, DSV, DC, etc.) — tax_type = short code from name
  - PREF DD rows from pref_rates (per HS × per country, group codes expanded)
  - hs_details rows (description, import_regime, export_regime, dd_assiette)

Group codes expanded:
  '97'  → EU-27 member ISO-2 list
  '98'  → EFTA (CH, NO, IS, LI)

Rate parsing:
  "3 %"         → 3.0  (percentage)
  "0.100 dinars" → 0.1  (specific amount; legal_basis stores full value string)

All rows: valid_from='2025-01-01', valid_to='2030-12-31'
"""

import pickle
import re
import sqlite3
from pathlib import Path

PICKLE_PATH = Path("/root/.claude/uploads/bb7292d3-92db-5741-b392-1a6e18b394c3/3d55a379-scrape_progress.pkl")
DB_PATH = Path("tunisia_trade.db")
VALID_FROM = "2025-01-01"
VALID_TO   = "2030-12-31"

# ---------------------------------------------------------------------------
# ISO numeric → ISO-2 map  (all 17 unique codes found in pickle)
# ---------------------------------------------------------------------------
COUNTRY_CODE_MAP: dict[str, str] = {
    "12":  "DZ",   # ALGERIE
    "120": "CM",   # CAMEROUN
    "288": "GH",   # GHANA
    "400": "JO",   # JORDANIE
    "404": "KE",   # KENYA
    "414": "KW",   # KOWEIT
    "480": "MU",   # MAURICE
    "504": "MA",   # MAROC
    "646": "RW",   # RUANDA
    "756": "CH",   # SUISSE  (used for EFTA group as lead country)
    "792": "TR",   # TURQUIE
    "818": "EG",   # EGYPTE
    "826": "GB",   # ROYAUME UNI
    "834": "TZ",   # TANZANIE
    "888": "PS",   # PALESTINE
    # Group codes — expanded below
    "97":  None,   # GROUPE PAYS UNION EUROP  → EU_MEMBERS
    "98":  None,   # GROUPE PAYS AELE         → EFTA_MEMBERS
}

# EU-27 ISO-2 list
EU_MEMBERS = [
    "AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR",
    "HR","HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO",
    "SE","SI","SK",
]
# EFTA members
EFTA_MEMBERS = ["CH", "NO", "IS", "LI"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_tax_code(name: str) -> str:
    """
    Extract short tax code from full name string.
    'RPD/IMPOR REDEV.PREST.DOUA/IM' → 'RPD/IMPOR'
    'D.S.V. DROIT SANIT.VETERINA'   → 'DSV'
    'DC/ALC DRT CONSOM.ALCOOL'       → 'DC/ALC'
    """
    token = name.split()[0]
    # Normalise 'D.S.V.' → 'DSV'
    token = token.replace(".", "")
    # Strip trailing slashes
    token = token.strip("/")
    return token


def _parse_rate(value: str) -> tuple[float, str | None]:
    """
    Returns (rate_float, legal_basis_or_None).
    '3 %'          → (3.0,  None)
    '0.100 dinars' → (0.1,  '0.100 dinars')
    """
    value = value.strip()
    pct_match = re.match(r"^([\d.]+)\s*%$", value)
    if pct_match:
        return float(pct_match.group(1)), None
    num_match = re.match(r"^([\d.]+)\s+", value)
    if num_match:
        return float(num_match.group(1)), value
    return 0.0, value


def _expand_country(code: str) -> list[str]:
    """Return list of ISO-2 codes for a numeric code (expands group codes)."""
    if code == "97":
        return EU_MEMBERS
    if code == "98":
        return EFTA_MEMBERS
    iso2 = COUNTRY_CODE_MAP.get(code)
    return [iso2] if iso2 else []


# ---------------------------------------------------------------------------
# Schema (adds hs_details; rest handled by existing ensure_schema)
# ---------------------------------------------------------------------------

def ensure_full_schema(conn: sqlite3.Connection) -> None:
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
        CREATE TABLE IF NOT EXISTS hs_details (
            hs_code TEXT PRIMARY KEY,
            description TEXT,
            import_regime TEXT,
            export_regime TEXT,
            dd_assiette TEXT
        );
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load(pickle_path: Path = PICKLE_PATH, db_path: Path = DB_PATH) -> None:
    print(f"Loading {pickle_path} ...")
    with open(pickle_path, "rb") as f:
        data: dict = pickle.load(f)
    print(f"  Entries in pickle: {len(data):,}")

    conn = sqlite3.connect(db_path)
    ensure_full_schema(conn)

    tm_rows: list[tuple] = []    # tariff_measures
    det_rows: list[tuple] = []   # hs_details

    for entry in data.values():
        hs = entry["hs_code"]

        # --- MFN DD ---
        dd_rate = entry.get("dd_rate")
        if dd_rate is not None:
            tm_rows.append((
                hs, "TN", "MFN", "DD", float(dd_rate),
                None, None, VALID_FROM, VALID_TO, None, entry.get("dd_assiette"),
            ))

        # --- MFN TVA ---
        tva_rate = entry.get("tva_rate")
        if tva_rate is not None:
            tm_rows.append((
                hs, "TN", "MFN", "TVA", float(tva_rate),
                None, None, VALID_FROM, VALID_TO, None, None,
            ))

        # --- OTHER taxes ---
        for tax in entry.get("other_taxes", []):
            tax_code = _extract_tax_code(tax["name"])
            rate_val, legal_basis = _parse_rate(tax["value"])
            # Store assiette in agreement_name slot for context (freeform text field)
            assiette = tax.get("assiette", "")
            tm_rows.append((
                hs, "TN", "OTHER", tax_code, rate_val,
                assiette or None, None, VALID_FROM, VALID_TO, None, legal_basis,
            ))

        # --- PREF DD rows ---
        for pref in entry.get("pref_rates", []):
            iso2_list = _expand_country(str(pref["country_code"]))
            for iso2 in iso2_list:
                tm_rows.append((
                    hs, iso2, "PREF", "DD", float(pref["rate"]),
                    pref["country_name"], None, VALID_FROM, VALID_TO, None, None,
                ))

        # --- hs_details ---
        det_rows.append((
            hs,
            entry.get("description"),
            entry.get("import_regime"),
            entry.get("export_regime"),
            entry.get("dd_assiette"),
        ))

    print(f"  tariff_measures rows to insert: {len(tm_rows):,}")
    print(f"  hs_details rows to insert:      {len(det_rows):,}")

    # Batch insert tariff_measures
    conn.executemany("""
        INSERT OR IGNORE INTO tariff_measures
            (hs_code, origin_country, duty_type, tax_type, rate,
             agreement_name, measure_type, valid_from, valid_to, source_url, legal_basis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tm_rows)
    conn.commit()

    # Batch insert hs_details
    conn.executemany("""
        INSERT OR REPLACE INTO hs_details
            (hs_code, description, import_regime, export_regime, dd_assiette)
        VALUES (?, ?, ?, ?, ?)
    """, det_rows)
    conn.commit()

    # --- Final counts ---
    print()
    print("Final row counts in DB:")
    for table in ("tariff_measures", "hs_details"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n:,}")

    print()
    print("tariff_measures breakdown:")
    for row in conn.execute("""
        SELECT duty_type, tax_type, COUNT(*) as n
        FROM tariff_measures
        GROUP BY duty_type, tax_type
        ORDER BY duty_type, tax_type
    """).fetchall():
        print(f"  {row[0]:<8} {row[1]:<12} {row[2]:>10,}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    load()
