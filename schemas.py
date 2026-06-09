from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TariffMeasure:
    hs_code: str
    origin_country: str
    duty_type: str
    tax_type: str
    rate: float
    agreement_name: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


@dataclass
class ResolvedPath:
    rank: int
    hs_code: str
    origin_country: str
    duty_type: str
    rate: float
    agreement_name: Optional[str]
    specificity: int


@dataclass
class LandedCost:
    origin: str
    agreement: str
    lead_days: int
    exw: float
    freight: float
    cif: float
    duty_rate: float
    duty_amt: float
    fodec: float
    tcl: float
    vat_rate: float
    vat_amt: float
    landed: float
    landed_tnd: float


@dataclass
class HsMatch:
    hs_code: str
    description: str
    mfn_rate: float
    score: float
