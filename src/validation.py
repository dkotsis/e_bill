# src/validation.py

from src.classes import bill
from src.db_handling import bill_exists

def bill_validation(
                    inv: bill,
                    conn,
                    temp_cursor,
                    bill_hash,
                    config  # <--- This is the 5th argument we were missing!
                    ):
    """Business rules for skipping specific invoice types."""
    
    # 1. Skip ENANTI bills
    if "ΕΝΑΝΤΙ" in (inv.bill_type or "").upper():
        return "UN", "skip", True, False, False, "Skipped: ΕΝΑΝΤΙ bill type"
    
    # 2. Skip Zero/Negative consumption or charges
    if inv.consumption <= 0 or inv.compet_charge <= 0:
        return "SK", "skip", True, False, False, "Skipped: Zero consumption/charge"
    
    # 3. Skip Database Duplicates
    if conn and bill_exists(temp_cursor, bill_hash):
        return "DB", "skip", True, False, True, "Skipped: Duplicate in database"
    
    # 4. Filter Low values (using the config passed from main.py)
    # We use .get() to provide a safe default if the key is missing in the settings
    c_threshold = config.get("consumption_threshold", 0)
    e_threshold = config.get("charge_threshold", 0)
    
    if inv.consumption < c_threshold and inv.compet_charge < e_threshold:
        return "FL", "filter_low", True, True, False, "Filtered: Below thresholds"

    # 5. Success
    return "OK", "ok", False, False, False, "Processed: Valid invoice"