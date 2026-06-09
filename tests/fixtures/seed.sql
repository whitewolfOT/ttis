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

-- MFN rows
INSERT OR IGNORE INTO tariff_measures (hs_code,origin_country,duty_type,tax_type,rate,valid_from) VALUES
    ('854140','TN','MFN','DD',25.0,'2025-01-01'),
    ('854140','TN','MFN','TVA',19.0,'2025-01-01'),
    ('870321','TN','MFN','DD',30.0,'2025-01-01'),
    ('870321','TN','MFN','TVA',19.0,'2025-01-01'),
    ('847130','TN','MFN','DD',8.0,'2025-01-01'),
    ('847130','TN','MFN','TVA',19.0,'2025-01-01');

-- PREF rows at 0%
INSERT OR IGNORE INTO tariff_measures (hs_code,origin_country,duty_type,tax_type,rate,agreement_name,valid_from) VALUES
    ('854140','TR','PREF','DD',0.0,'Turkey-Tunisia FTA','2025-01-01'),
    ('854140','FR','PREF','DD',0.0,'EU-Tunisia Association','2025-01-01'),
    ('870321','MA','PREF','DD',0.0,'Agadir Agreement','2025-01-01');

-- SUSP row: CN gets suspended duty at 5% (overrides MFN 25%)
INSERT OR IGNORE INTO tariff_measures (hs_code,origin_country,duty_type,tax_type,rate,agreement_name,valid_from) VALUES
    ('854140','CN','SUSP','DD',5.0,NULL,'2025-01-01');
