import sqlite3
from rapidfuzz import process, fuzz
from schemas import HsMatch

HS_DESCRIPTIONS: dict = {
    "854140": "Photovoltaic cells; solar panels; diodes; transistors",
    "870321": "Passenger motor vehicles; spark-ignition engine ≤1000cc",
    "010121": "Live horses; pure-bred breeding animals",
    "850760": "Lithium-ion accumulators; batteries",
    "847130": "Portable automatic data processing machines; laptops; notebooks",
    "401110": "New pneumatic tyres of rubber for motor cars",
}


def search_hs(conn, query: str, limit: int = 12, score_cutoff: int = 30) -> list:
    if not query or not query.strip():
        return []

    cur = conn.execute(
        "SELECT DISTINCT hs_code, rate FROM tariff_measures WHERE duty_type='MFN' AND tax_type='DD'"
    )
    db_rows = {r[0]: r[1] for r in cur.fetchall()}
    all_codes = list(db_rows.keys())

    choices = {
        code: f"{HS_DESCRIPTIONS.get(code, '')} {code}"
        for code in all_codes
    }

    if not choices:
        return []

    results = process.extract(
        query,
        choices,
        scorer=fuzz.partial_ratio,
        limit=limit,
        score_cutoff=score_cutoff,
    )

    matches = []
    for _, score, code in results:
        matches.append(HsMatch(
            hs_code=code,
            description=HS_DESCRIPTIONS.get(code, ""),
            mfn_rate=db_rows.get(code, 0.0),
            score=float(score),
        ))
    return matches
