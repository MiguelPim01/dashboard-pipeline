from __future__ import annotations

from enum import Enum


class ReportCriticsEnum(str, Enum):
    NON_CRITICAL = "NON_CRITICAL"
    CRITICAL_GOV = "CRITICAL_GOV"
    CRITICAL_COP = "CRITICAL_COP"
    NEGATIONISM = "NEGATIONISM"
