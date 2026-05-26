# -*- coding: utf-8 -*-
"""
=============================================================================
Project:        Electricity Bill Importer PRO
File:           parsers_excel.py
Description:    Data extraction engine for provider-specific Excel files 
                (e.g., NRG, HERON). Uses Pandas to map heterogeneous 
                column structures into standardized 'bill' objects.
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

# Standard library imports
import pandas as pd
from src.classes import bill
from src.utils import parse_amount, parse_date

# ============================================================ #


def detect_provider(df: pd.DataFrame) -> str:
    """
    Provider detection based on the rule:
    If column 'ΚΩΔΙΚΟΣ ΠΟΛΛΑΠΛΟΥ ΛΟΓΑΡΙΑΣΜΟΥ' exists and all values
    are '700000000170', then it is NRG. Otherwise, it is considered HERON.
    """
    column_name = "ΚΩΔΙΚΟΣ ΠΟΛΛΑΠΛΟΥ ΛΟΓΑΡΙΑΣΜΟΥ"
    target_value = "700000000170"

    # 1. Check if the column exists (ignoring surrounding spaces in the name)
    cols = [str(col).strip() for col in df.columns]

    if column_name in cols:
        # Get data from the specific column
        # Convert to string and remove .0 (if pandas read it as float)
        column_data = (
            df[column_name].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        )

        # 2. Check if ALL rows have the target value
        # (Exclude completely empty rows if they exist)
        non_empty_data = column_data[column_data != "nan"]

        if not non_empty_data.empty and all(non_empty_data == target_value):
            return "NRG"

    # If the above conditions aren't met, returns HERON
    return "ΗΡΩΝ"


def parse_nrg_excel(df: pd.DataFrame) -> list[bill]:
    invoices = []
    for idx, row in df.iterrows():
        try:
            log = bill()
            log.provider = "NRG"
            log.issue_date = parse_date(row.get("ΗΜΕΡ.ΕΚΔΟΣΗΣ ΛΟΓΑΡΙΑΣΜΟΥ"))
            log.period_start = parse_date(row.get("ΗΜ.ΝΙΑ ΠΡΟΗΓ.ΚΑΤΑΜΕΤΡΗΣΗΣ"))
            log.period_end = parse_date(row.get("ΗΜ.ΤΕΛ.ΚΑΤΑΜΕΤΡΗΣΗΣ"))

            supply_raw = str(
                row.get("ΠΕΡΙΦΕΡΕΙΑ(1) + ΑΡ.ΠΑΡΟΧΗΣ (8) + ΔΙΑΔΟΧΟ", "")
            ).strip()
            digits = "".join(filter(str.isdigit, supply_raw))
            log.supply_number = digits[:9] if len(digits) >= 9 else digits

            typos_raw = str(row.get("ΤΥΠΟΣ ΛΟΓΑΡΙΑΣΜΟΥ", "")).upper()
            log.bill_type = (
                "ΕΝΑΝΤΙ"
                if "ΕΝΑΝΤ" in typos_raw
                else ("ΕΚΚΑΘΑΡΙΣΤΙΚΟΣ" if "ΕΚΚΑΘ" in typos_raw else typos_raw)
            )

            aa = row.get("Α/Α ΕΚΔΟΣΗΣ ΛΟΓΑΡΙΑΣΜΟΥ")
            log.bill_number = str(aa).strip() if pd.notna(aa) else ""

            log.consumption = parse_amount(
                str(row.get("ΚΑΤΑΝΑΛΩΣΗ ΕΝΕΡΓΕΙΑΣ (ΩΧΒ)", 0))
            )
            log.compet_charge = parse_amount(str(row.get("ΑΞΙΑ ΕΝΕΡΓΕΙΑΣ", 0)))
            log.regul_charge = parse_amount(
                str(row.get("ΣΥΝΟΛΟ ΡΥΘΜΙΖΟΜΕΝΩΝ ΧΡΕΩΣΕΩΝ", 0))
            )

            # CONTINUE REMOVED - Sending all to main
            invoices.append(log)

        except Exception as e:
            print(f"[DEBUG ERROR] Error at line {idx+2}: {e}")
            continue
    return invoices


def parse_heron_excel(df: pd.DataFrame) -> list[bill]:
    invoices = []
    for idx, row in df.iterrows():
        try:
            log = bill()
            log.provider = "ΗΡΩΝ"
            log.issue_date = parse_date(row.get("Ημερομηνία Έκδοσης"))
            log.period_start = parse_date(row.get("Περίοδος κατανάλωσης Από"))
            log.period_end = parse_date(row.get("Περίοδος κατανάλωσης Έως"))

            supply = str(row.get("Αρ. Παροχής", "")).strip()
            log.supply_number = supply[:9] if len(supply) >= 9 else supply
            log.bill_type = str(row.get("Τύπος Τιμολογίου", "")).strip()

            log.consumption = parse_amount(str(row.get("Ενέργεια", 0))) + parse_amount(
                str(row.get("Ενέργεια Νύχτας", 0))
            )
            log.compet_charge = parse_amount(str(row.get("Χρέωση Ενέργειας", 0)))
            log.regul_charge = (
                parse_amount(str(row.get("Δίκτυο Μεταφοράς", 0)))
                + parse_amount(str(row.get("Δίκτυο Διανομής", 0)))
                + parse_amount(str(row.get("ΥΚΩ", 0)))
                + parse_amount(str(row.get("ΕΤΜΕΑΡ", 0)))
                + parse_amount(str(row.get("ΕΦΚ", 0)))
            )

            aa = row.get("Α/Α Λγαριασμού")
            log.bill_number = str(aa).strip() if pd.notna(aa) else ""

            # CONTINUE REMOVED - Sending all to main
            invoices.append(log)

        except Exception as e:
            print(f"[DEBUG ERROR HERON] Error at line {idx+2}: {e}")
            continue
    return invoices


def extract_invoices(excel_path: str) -> list[bill]:
    """Main entry point - supports both HERON and NRG Excel files"""
    df = pd.read_excel(excel_path)
    provider = detect_provider(df)

    
    print(f"[INFO] Provider detected from Excel: {provider}")

    if provider == "ΗΡΩΝ":
        return parse_heron_excel(df)
    elif provider == "NRG":
        return parse_nrg_excel(df)
    else:
        print(f"[WARN] Unknown file type: {provider}")
        return []
