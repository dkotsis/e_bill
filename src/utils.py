# -*- coding: utf-8 -*-
# src/utils.py

"""
=============================================================================
Project:        Electricity Bill Importer PRO
File:           src/utils.py
Description:    Provides shared utility functions, including Greek-format
                numeric parsing, cryptographic hashing for duplicate detection,
                and date transformations.
=============================================================================
Legal:          Proprietary software. Unauthorized copying, distribution, 
                or modification is strictly prohibited.
                Internal use only for ANEDIK KRITIKOS SA.

__author__      = "D. T. Kotsis"
__copyright__   = "Copyright 2026, ANEDIK KRITIKOS SA"
__date__        = "08/05/2026"
__deprecated__  = False
__email__       = "d.kotsis@anedik.com.gr"
__license__     = "Proprietary - ANEDIK Internal Use Only"
__maintainer__  = "D. T. Kotsis"
__status__      = "Production"
__version__     = "4.3.0"
=============================================================================
"""

# ============================================================
# Standard library imports
# ============================================================
import re
import os
import pandas as pd
import hashlib
from datetime import datetime

# ============================================================
# Local imports
# ============================================================
from src.classes import bill




# ============================================================
#  Text / numeric helpers
# ============================================================


def format_greek_display(value: float, decimals: int = 4) -> str:
    """Format for screen display: 1.234.567,8912 €"""
    s = f"{value:,.{decimals}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def format_greek_save(value: float, decimals: int = 4) -> str:
    """Format for file saving: 1234567,8912"""
    s = f"{value:,.{decimals}f}"
    s = s.replace(",", "").replace(".", ",")
    return s


def parse_amount(value) -> float:
    """
    Correct conversion of amounts from Greek Excel.
    Takes into account that pandas might have already converted to float.
    """
    if value is None or pd.isna(value):
        return 0.0

    # If already a number (int or float) → return directly
    if isinstance(value, (int, float)):
        return float(value)

    # If string
    s = str(value).strip()

    if not s or s.lower() in ["nan", "nat", "none", ""]:
        return 0.0

    # Main case: Greek format with comma as decimal
    if "," in s:
        s = s.replace(".", "")  # remove thousand separators
        s = s.replace(",", ".")  # comma → dot
    else:
        # If no comma, might be "1556.3" from pandas
        # Remove only spaces, not dots
        s = s.replace(" ", "")

    try:
        return float(s)
    except ValueError:
        print(f"[WARN] Unable to convert amount: '{value}' (type: {type(value)})")
        return 0.0


def parse_date(value):
    """
    Converts Excel values to datetime.
    Covers: Timestamps, Strings and special NRG format (DDMMYYYY).
    """
    if value is None or pd.isna(value) or value == "":
        return None

    # 1. If already a datetime object (e.g., from HERON)
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.to_pydatetime() if hasattr(value, "to_pydatetime") else value

    # 2. Convert to clean string (remove .0 if coming as float from Excel)
    val_str = str(value).strip().split(".")[0]

    # If the string is less than 8 digits (e.g., 1052024 instead of 01052024)
    # add a leading zero
    if val_str.isdigit() and len(val_str) == 7:
        val_str = "0" + val_str

    # --- SPECIAL NRG HANDLING: DDMMYYYY (8 digits) ---
    if val_str.isdigit() and len(val_str) == 8:
        try:
            day = int(val_str[:2])
            month = int(val_str[2:4])
            year = int(val_str[4:])
            return datetime(year, month, day)
        except ValueError:
            pass

    # 3. Try standard formats (if has slashes or dashes)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue

    return None



# ============================================================
#  Bill dataclass and related utilities
# ============================================================


def detect_provider(text: str) -> str:
    """Detect the electricity provider from raw PDF text."""
    if "NRG" in text or "nrg.gr" in text.lower():
        return "NRG"
    if "ΗΡΩΝ" in text or "heron.gr" in text.lower() or "HERON" in text.upper():
        return "ΗΡΩΝ"
    return "ΑΓΝΩΣΤΟΣ"


def generate_hash(log: bill) -> str:
    """Generate unique hash for duplicate detection"""
    key = f"{log.supply_number}|{log.bill_number or ''}|{str(log.issue_date)}|{log.compet_charge}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def clean_supply_number(raw: str) -> str:
    """Strip non-digits from a supply number and return the first 9 digits."""
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))
    return digits[:9]




# ============================================================
#  Directory helpers
# ============================================================


def get_root_dir() -> str:
    """Return the project root directory (one level above src/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_log_dir() -> str:
    log_dir = os.path.join(get_root_dir(), "Process Logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_anomaly_dir() -> str:
    anomaly_dir = os.path.join(get_root_dir(), "Anomaly Reports")
    os.makedirs(anomaly_dir, exist_ok=True)
    return anomaly_dir




# ============================================================
#  Other helpers
# ============================================================


def classify_anomaly(risk, confidence):
    if risk >= 75:
        if confidence >= 0.75:
            return "🔴 URGENT", "critical"
        return "🟠 SUSPICIOUS", "high"
    elif risk >= 55:
        if confidence >= 0.50:
            return "🟡 HIGH", "high"
        return "🟢 REVIEW", "warn"
    elif risk >= 35:
        if confidence >= 0.50:
            return "⚪ REVIEW", "warn"
        return "WEAK", "weak"
    else:
        if confidence >= 0.50:
            return "NORMAL", "ok"
        return "LOW", "skip"
    

    