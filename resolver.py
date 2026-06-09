import sqlite3
from typing import Optional
from schemas import ResolvedPath

DUTY_PRIORITY = {"SUSP": 0, "PREF": 1, "QUOTA": 2, "MFN": 3}


def get_hs_ancestors(hs_code: str) -> list:
    code = "".join(c for c in hs_code if c.isdigit())
    lengths = [10, 8, 6, 4, 2]
    return [code[:n] for n in lengths if len(code) >= n and code[:n]]


def enumerate_paths(conn, hs_code: str, origin_country: str) -> list:
    ancestors = get_hs_ancestors(hs_code)
    if not ancestors:
        return []

    placeholders = ",".join("?" * len(ancestors))
    # Match DB rows that are ancestors of the query OR rows the query is a prefix of
    sql = f"""
        SELECT hs_code, origin_country, duty_type, rate, agreement_name
        FROM tariff_measures
        WHERE duty_type IN ('SUSP','PREF','QUOTA','MFN')
          AND tax_type = 'DD'
          AND (hs_code IN ({placeholders}) OR hs_code LIKE ? || '%')
          AND (origin_country = ? OR origin_country = 'TN')
    """
    query_prefix = "".join(c for c in hs_code if c.isdigit())
    cur = conn.execute(sql, ancestors + [query_prefix, origin_country])
    rows = cur.fetchall()

    paths = []
    for rank_i, (hs, orig, dtype, rate, agname) in enumerate(rows):
        specificity = len(hs)
        paths.append(ResolvedPath(
            rank=rank_i,
            hs_code=hs,
            origin_country=orig,
            duty_type=dtype,
            rate=rate,
            agreement_name=agname,
            specificity=specificity,
        ))

    paths.sort(key=lambda p: (DUTY_PRIORITY.get(p.duty_type, 99), -p.specificity))
    for i, p in enumerate(paths):
        p.rank = i
    return paths


def resolve_duty(conn, hs_code: str, origin_country: str) -> Optional[ResolvedPath]:
    paths = enumerate_paths(conn, hs_code, origin_country)
    return paths[0] if paths else None
