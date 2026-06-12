"""
MacMap proof-of-concept — run manually (NOT via pytest).

Requires env vars:
  MACMAP_EMAIL=your@email.com
  MACMAP_PASSWORD=yourpassword

Usage:
  MACMAP_EMAIL=x MACMAP_PASSWORD=y python3 poc_macmap.py
"""
import asyncio
import os
import time

from macmap_scraper import login_macmap, fetch_export_tariffs_for_hs6

EMAIL    = os.environ.get("MACMAP_EMAIL", "")
PASSWORD = os.environ.get("MACMAP_PASSWORD", "")


async def test_poc():
    print("Step 1: Login...")
    cookies = await login_macmap(EMAIL, PASSWORD)
    print(f"  Got {len(cookies)} cookies")

    print("Step 2: Fetch 1 HS6 × 3 countries...")
    results = fetch_export_tariffs_for_hs6(
        "010121",
        cookies,
        reporters={"251": "FR", "840": "US", "818": "EG"},
        delay=0.5,
    )
    print(f"  Got {len(results)} rows")
    for r in results:
        print(f"  {r['reporter_name']}: {r['rate']}% ({r['tariff_regime']})")

    print("Step 3: Check session still valid after 60s gap...")
    time.sleep(60)
    results2 = fetch_export_tariffs_for_hs6(
        "847130",
        cookies,
        reporters={"251": "FR"},
        delay=0.5,
    )
    print(f"  Session valid: {len(results2) > 0}")


if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("ERROR: set MACMAP_EMAIL and MACMAP_PASSWORD env vars before running")
        raise SystemExit(1)
    asyncio.run(test_poc())
