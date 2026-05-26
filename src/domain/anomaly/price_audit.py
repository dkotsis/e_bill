# src/domain/anomaly/price_audit.py
from datetime import timedelta, datetime
from src.domain.model.bill import Bill

def calculate_expected_charge(bill: Bill, cursor, supply_type: str = "LV") -> float:
    """
    Calculates the contractually expected competitive charge for an energy bill.
    Uses batch memory-cached lookups to prevent database loop slowdowns and
    respects the timeline thresholds of the 'date_effective' contract rules.
    """
    if not bill.period_start or not bill.period_end or bill.consumption <= 0:
        return 0.0

    total_days = bill.total_days()
    if total_days <= 0:
        return 0.0

    daily_kwh = bill.consumption / total_days
    expected_total = 0.0
    
    # Standardize our voltage target matching your table scheme structure
    v_suffix = "LV" if "LV" in supply_type.upper() else "MV"

    # ---------------------------------------------------------
    # 1. BATCH CACHE EXTRACTION (Pulls the whole bill timeline at once)
    # ---------------------------------------------------------
    try:
        # Pre-fetch DAM data for the range
        start_month = bill.period_start.replace(day=1)
        cursor.execute(
            "SELECT [date], DAM FROM tblDAM WHERE [date] BETWEEN ? AND ?", 
            (start_month, bill.period_end)
        )
        dam_cache = {row[0]: float(row[1]) for row in cursor.fetchall() if row[1] is not None}

        # Pre-fetch Loss Factor data for the range
        start_year = bill.period_start.year
        end_year = bill.period_end.year
        cursor.execute(
            f"SELECT [losses_year], losses_{v_suffix} FROM Losses WHERE [losses_year] BETWEEN ? AND ?", 
            (start_year, end_year)
        )
        loss_cache = {row[0]: float(row[1]) for row in cursor.fetchall() if row[1] is not None}

        # Pre-fetch all historical margin timelines for this provider
        # Pulls date_effective, margin_LV, and margin_MV ordered by effective timeline
        cursor.execute(
            f"SELECT date_effective, margin_LV, margin_MV FROM Margins WHERE provider = ? ORDER BY date_effective ASC",
            (bill.provider,)
        )
        margin_timeline = []
        for row in cursor.fetchall():
            if row[0] is not None:
                # Store tuple: (effective_date, lv_value, mv_value)
                margin_timeline.append((row[0], float(row[1] or 0.0), float(row[2] or 0.0)))

    except Exception as e:
        # Fallback safeguard if custom fields have structural locking bugs
        print(f"❌ [CRITICAL DB REF QUERY ERROR]: {e}")
        return 0.0

    # ---------------------------------------------------------
    # 2. CHRONOLOGICAL TIMELINE ITERATION
    # ---------------------------------------------------------
    current = bill.period_start
    # Boundary fix: Using '<' instead of '<=' safely blocks extra day indexing leaks
    while current < bill.period_end:
        # Find Day-Ahead Market (DAM) Reference value
        month_key = current.replace(day=1)
        dam = dam_cache.get(month_key, 0.0)

        # Find Loss Factor percentage value
        loss = loss_cache.get(current.year, 0.0)

        # Find effective historical contract margin for this specific day
        # Scan timeline array forward to locate the latest valid margin line tier
        active_margin = 0.0
        for effective_date, m_lv, m_mv in margin_timeline:
            if effective_date <= current:
                active_margin = m_lv if v_suffix == "LV" else m_mv
            else:
                # Since the array is sorted ASC, we can break as soon as we cross into future tiers
                break

        # Calculate exact combined unit cost for this single day frame
        # (Formula matches standard Greek market calculation structure: €/MWh converted down to €/kWh)
        unit_price = (dam * (1 + loss) + active_margin) / 1000
        expected_total += daily_kwh * unit_price

        current += timedelta(days=1)

    return round(expected_total, 4)