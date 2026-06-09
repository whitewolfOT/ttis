from schemas import TariffMeasure
from db import ensure_schema

AGREEMENTS: dict = {
    "EU-Tunisia Association": {
        "type": "FTA",
        "valid_from": "2020-01-01",
        "members": ["AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR",
                    "HR","HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO",
                    "SE","SI","SK"],
    },
    "Turkey-Tunisia FTA": {
        "type": "FTA",
        "valid_from": "2025-01-01",
        "members": ["TR"],
    },
    "Agadir Agreement": {
        "type": "FTA",
        "valid_from": "2007-03-27",
        "members": ["MA", "EG", "JO"],
    },
    "PAFTA": {
        "type": "FTA",
        "valid_from": "1998-01-01",
        "members": ["DZ","LY","MR","SD","SO","DJ","KM","YE","IQ","KW","SA","AE",
                    "QA","BH","OM","SY","LB","PS"],
    },
}


def populate_preferential(conn) -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "SELECT DISTINCT hs_code FROM tariff_measures WHERE duty_type='MFN' AND tax_type='DD'"
    )
    hs_codes = [r[0] for r in cur.fetchall()]

    rows = []
    for ag_name, ag in AGREEMENTS.items():
        for origin in ag["members"]:
            for hs in hs_codes:
                rows.append((hs, origin, "PREF", "DD", 0.0, ag_name,
                              ag["valid_from"], None))

    sql = """
        INSERT OR IGNORE INTO tariff_measures
            (hs_code, origin_country, duty_type, tax_type, rate, agreement_name, valid_from, valid_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn.executemany(sql, rows)
    conn.commit()
    return conn.execute(
        "SELECT COUNT(*) FROM tariff_measures WHERE duty_type='PREF'"
    ).fetchone()[0]
