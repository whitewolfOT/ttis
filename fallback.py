from schemas import TariffMeasure

FALLBACK_MEASURES: list = [
    TariffMeasure("854140", "TN", "MFN", "DD",  25.0,  valid_from="2025-01-01"),
    TariffMeasure("854140", "TN", "MFN", "TVA", 19.0,  valid_from="2025-01-01"),
    TariffMeasure("870321", "TN", "MFN", "DD",  30.0,  valid_from="2025-01-01"),
    TariffMeasure("870321", "TN", "MFN", "TVA", 19.0,  valid_from="2025-01-01"),
    TariffMeasure("010121", "TN", "MFN", "DD",  15.0,  valid_from="2025-01-01"),
    TariffMeasure("010121", "TN", "MFN", "TVA", 19.0,  valid_from="2025-01-01"),
    TariffMeasure("850760", "TN", "MFN", "DD",  10.0,  valid_from="2025-01-01"),
    TariffMeasure("850760", "TN", "MFN", "TVA", 19.0,  valid_from="2025-01-01"),
    TariffMeasure("847130", "TN", "MFN", "DD",   8.0,  valid_from="2025-01-01"),
    TariffMeasure("847130", "TN", "MFN", "TVA", 19.0,  valid_from="2025-01-01"),
    TariffMeasure("401110", "TN", "MFN", "DD",  12.0,  valid_from="2025-01-01"),
    TariffMeasure("401110", "TN", "MFN", "TVA", 19.0,  valid_from="2025-01-01"),
]


def get_fallback() -> list:
    return list(FALLBACK_MEASURES)
