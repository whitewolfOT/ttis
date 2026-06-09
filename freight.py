USD_TO_TND: float = 3.12

ORIGIN_LABELS: dict = {
    "CN": "🇨🇳 China",
    "TR": "🇹🇷 Turkey",
    "FR": "🇫🇷 France",
    "DE": "🇩🇪 Germany",
    "IT": "🇮🇹 Italy",
    "ES": "🇪🇸 Spain",
    "IN": "🇮🇳 India",
    "KR": "🇰🇷 South Korea",
    "JP": "🇯🇵 Japan",
    "US": "🇺🇸 USA",
    "MA": "🇲🇦 Morocco",
    "DZ": "🇩🇿 Algeria",
    "EG": "🇪🇬 Egypt",
    "SA": "🇸🇦 Saudi Arabia",
    "AE": "🇦🇪 UAE",
    "BR": "🇧🇷 Brazil",
    "MX": "🇲🇽 Mexico",
    "PL": "🇵🇱 Poland",
    "BE": "🇧🇪 Belgium",
    "NL": "🇳🇱 Netherlands",
}

FREIGHT_FCL: dict = {
    "CN": 1800.0,
    "TR":  650.0,
    "FR":  400.0,
    "DE":  420.0,
    "IT":  380.0,
    "ES":  390.0,
    "IN": 1200.0,
    "KR": 1900.0,
    "JP": 2000.0,
    "US": 2200.0,
    "MA":  250.0,
    "DZ":  270.0,
    "EG":  300.0,
    "SA":  500.0,
    "AE":  520.0,
    "BR": 2400.0,
    "MX": 2300.0,
    "PL":  430.0,
    "BE":  410.0,
    "NL":  410.0,
}

LEAD_DAYS: dict = {
    "CN": 35,
    "TR": 10,
    "FR":  7,
    "DE":  7,
    "IT":  6,
    "ES":  7,
    "IN": 25,
    "KR": 28,
    "JP": 30,
    "US": 20,
    "MA":  4,
    "DZ":  4,
    "EG":  7,
    "SA": 10,
    "AE": 10,
    "BR": 30,
    "MX": 25,
    "PL":  8,
    "BE":  7,
    "NL":  7,
}


def estimate_freight(origin: str, weight: float = 500, volume: float = 2.0) -> float:
    if weight <= 0 and volume <= 0:
        import warnings
        warnings.warn(f"estimate_freight: weight=0 and volume=0 for {origin}; using 200 USD floor")
        return 200.0

    base = FREIGHT_FCL.get(origin, 1500.0)
    density = weight / volume if volume > 0 else 300.0
    chargeable = max(weight, volume * 167)  # 167 kg/m³ density breakpoint
    rate_per_kg = base / 1000.0
    freight = chargeable * rate_per_kg
    return max(freight, 200.0)
