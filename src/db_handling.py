# -*- coding: utf-8 -*-
"""
=============================================================================
Project:        Electricity Bill Importer PRO
File:           src/db_handling.py
Description:    Database abstraction layer for Microsoft Access. Manages 
                ODBC connections, schema enforcement, record insertion, 
                duplicate detection, and historical baseline retrieval 
                for seasonal consumption tracking.
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
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict


try:
    import pyodbc
except ImportError:
    sys.exit("❌ Missing pyodbc library. pip install pyodbc")

# Local imports
from src.classes import bill
from src.utils import generate_hash

# ============================================================ #



# ------------------------------------------------------------------ #
#  SQL statements                                                    #
# ------------------------------------------------------------------ #

CREATE_BILLS_TABLE_SQL = """
CREATE TABLE Bills (
    BillID           AUTOINCREMENT PRIMARY KEY,
    SupplyNumber    TEXT(50),
    Provider TEXT(100),
    BillNumber    TEXT(50),
    BillType         TEXT(30),
    IssueDate    DATETIME,
    PeriodStart   DATETIME,
    PeriodEnd     DATETIME,
    Consumption  DOUBLE,
    CompetCharge   CURRENCY,
    RegulCharge    CURRENCY,
    BillHash VARCHAR(64),
    ExpectedCharge DOUBLE,
    IsAuditFailure BIT,
    IsStatisticalAnomaly BIT,
    IsHistoricalAnomaly BIT,
    AuditNote LONGTEXT
)
"""

CREATE_SUPPLIES_TABLE_SQL = """
CREATE TABLE Supplies (
    SupplyNumber TEXT(50) PRIMARY KEY,
    SiteID TEXT(50),
    Site TEXT(100),
    Address   TEXT(255),
    City   TEXT(255),
    Region   TEXT(255),
    SupplyType TEXT(50),
    Active  BIT,
    Notes     MEMO
)
"""

CREATE_ANOMALIES_TABLE_SQL = """
CREATE TABLE Anomalies (
    AnomalyID               AUTOINCREMENT PRIMARY KEY,
    BillID           TEXT(50),
    AnomalyType      TEXT(50),
    Severity         DOUBLE,
    BaselineValue    DOUBLE,
    DetectionDate       DATETIME,
    Status           TEXT(20),
    Is_False_Positive BIT,
    FOREIGN KEY (BillID) REFERENCES Bills(BillNumber)
)
"""

CREATE_METER_TELEMETRY_TABLE_SQL = """
CREATE TABLE MeterTelemetry (
    SupplyNumber TEXT(50),
    ReadingTimestamp DATETIME,
    ActualKwh DOUBLE,
    PRIMARY KEY (SupplyNumber, ReadingTimestamp)
)
"""


INSERT_ANOMALY_SQL = """
INSERT INTO Anomalies (
    BillID, AnomalyType, Severity, BaselineValue, DetectionDate, Status, Is_False_Positive
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""

INSERT_BILL_SQL = """
INSERT INTO Bills
    (SupplyNumber, Provider, BillNumber, BillType, IssueDate, PeriodStart, PeriodEnd,
     Consumption, CompetCharge, RegulCharge, BillHash, ExpectedCharge, IsAuditFailure, IsHistoricalAnomaly,IsStatisticalAnomaly, AuditNote)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

BASELINE_QUERY_SQL = """
SELECT
    AVG(Consumption / (DATEDIFF('d', PeriodStart, PeriodEnd)+1)) AS avg_kwh_day,
    AVG(CompetCharge / Consumption)                              AS avg_price
FROM Bills
WHERE SupplyNumber = ? AND MONTH(PeriodStart) = ? AND Consumption > 0
"""


# ------------------------------------------------------------------ #
#  Connection                                                        #
# ------------------------------------------------------------------ #


# src/db_handling.py

def get_db_path(db_dir, db_name):
    return os.path.join(db_dir, db_name)


def connect_access(db_dir: str, db_name: str):
    """Open a pyodbc connection to the MS Access database."""
    db_path = get_db_path(db_dir, db_name)
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database not found:\n{db_path}\n\n"
            f"Place '{db_name}' in the db/ folder."
        )

    drivers = [d for d in pyodbc.drivers() if "Access" in d]
    if not drivers:
        raise RuntimeError("Microsoft Access ODBC driver not found.")

    conn_str = (
        f"DRIVER={{{drivers[0]}}};DBQ={os.path.abspath(db_path)};ExtendedAnsiSQL=1;"
    )
    return pyodbc.connect(conn_str, autocommit=False)


# ------------------------------------------------------------------ #
#  Schema management                                                 #
# ------------------------------------------------------------------ #


def ensure_tables(conn):
    """Checks if required tables exist and creates them if necessary."""
    cursor = conn.cursor()
    tables = [t.table_name for t in cursor.tables(tableType='TABLE')]
    
    if 'Bills' not in tables:
        print("  [DB] Creating table: Bills...")
        cursor.execute(CREATE_BILLS_TABLE_SQL)
        conn.commit()

    if 'MeterTelemetry' not in tables:
        print("  [DB] Creating table: MeterTelemetry...")
        cursor.execute(CREATE_METER_TELEMETRY_TABLE_SQL)
        conn.commit()
    
    if 'Supplies' not in tables:
        print("  [DB] Creating table: Supplies...")
        cursor.execute(CREATE_SUPPLIES_TABLE_SQL)
        conn.commit()

    if 'Anomalies' not in tables:
        print("  [DB] Creating table: Anomalies...")
        try:
            cursor.execute(CREATE_ANOMALIES_TABLE_SQL)
            conn.commit()
        except Exception as e:
            print(f"  [DB WARN] Could not create Anomalies table: {e}")


# ------------------------------------------------------------------ #
#  Supply helpers                                                    #
# ------------------------------------------------------------------ #


def supply_exists(cursor, supply_num: str) -> bool:
    cursor.execute("SELECT COUNT(*) FROM Supplies WHERE SupplyNumber = ?", supply_num)
    return cursor.fetchone()[0] > 0


def add_new_supply(cursor, supply_num: str) -> None:
    try:
        cursor.execute("INSERT INTO Supplies (SupplyNumber) VALUES (?)", supply_num)
        cursor.connection.commit()
        print(f"  [NEW SUPPLY] New supply added: {supply_num}")
    except Exception as e:
        print(f"  [ERROR] Failed to add supply: {e}")


def get_supply_baseline(
    cursor, supply_num: str, month: int
) -> tuple[float | None, float | None]:
    """Return (avg_kwh_per_day, avg_price_per_kwh) for a supply/month pair from historical data."""
    cursor.execute(BASELINE_QUERY_SQL, (supply_num, month))
    row = cursor.fetchone()
    if row and row[0]:
        return row[0], row[1]
    return None, None


# ------------------------------------------------------------------ #
#  Anomaly Helper Logic                                              #
# ------------------------------------------------------------------ #

def get_seasonal_baseline_dict(conn, supply_number):

    cursor = conn.cursor()

    baselines = {}

    try:

        sql = """
            SELECT
                SeasonType,
                AvgDailyConsumption,
                StdDeviation,
                SampleSize,
                ThresholdPercentage
            FROM SeasonalBaselines
            WHERE SupplyNumber = ?
        """

        cursor.execute(sql, (supply_number,))

        rows = cursor.fetchall()

        for row in rows:

            baselines[row[0]] = {
                'AvgDailyConsumption': float(row[1] or 0),
                'StdDeviation': float(row[2] or 0),
                'SampleSize': float(row[3] or 0),
                'ThresholdPercentage': float(row[4] or 0.35)
            }

    except Exception as e:

        print(
            f"⚠️ [DB WARN] "
            f"Baseline lookup failed "
            f"for {supply_number}: {e}"
        )

    return baselines

def log_anomaly_to_db(conn, bill_id, anomaly_type, severity, baseline):
    """
    Records a detected anomaly in the 'Anomalies' table.
    - anomaly_type: 'Price' or 'Consumption'
    - severity: Percentage deviation (float)
    - baseline: The reference value used for comparison
    """
    cursor = conn.cursor()
    try:
        sql = """
            INSERT INTO Anomalies (BillID, AnomalyType, Severity, BaselineValue, DetectionDate)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (bill_id, anomaly_type, severity, baseline, datetime.now())
        cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        print(f"❌ [DB ERROR] Failed to log anomaly for Bill ID {bill_id}: {e}")


# ------------------------------------------------------------------ #
#  Insertion                                                         #
# ------------------------------------------------------------------ #


def save_invoices(conn, invoices, log_fn=None):
    """Saves only new and validated bills to the database, skipping existing ones."""
    cursor = conn.cursor()
    inserted_count = 0
    skipped_duplicates = 0
    
    for bill in invoices:
        try:
            sql = """
                INSERT INTO Bills (
                    SupplyNumber,
                    Provider, 
                    BillNumber,
                    BillType,
                    IssueDate,  
                    PeriodStart,
                    PeriodEnd,
                    Consumption, 
                    CompetCharge,
                    RegulCharge,
                    BillHash,
                    ExpectedCharge,
                    IsAuditFailure,
                    IsHistoricalAnomaly,
                    IsStatisticalAnomaly,
                    AuditNote
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?, ?, ?, ?)
            """
            
            # 1. Added bill.issue_date to params
            params = (
                bill.supply_number,
                bill.provider, 
                bill.bill_number,
                bill.bill_type,
                bill.issue_date,   
                bill.period_start, 
                bill.period_end, 
                bill.consumption,
                bill.compet_charge, 
                bill.regul_charge, 
                bill.bill_hash,
                bill.expected_charge,
                bill.is_audit_failure,
                bill.is_historical_anomaly,
                bill.is_statistical_anomaly,
                bill.audit_note
            )
            
            cursor.execute(sql, params)
            
            # Fetch the ID for anomaly logging later
            cursor.execute("SELECT @@IDENTITY")
            bill.db_id = cursor.fetchone()[0]
            inserted_count += 1
            
        except Exception as e:
            if log_fn:
                log_fn(f"⚠️ [DB ERROR] Bill {bill.bill_number}: {e}", "error")
    
    conn.commit()
    if log_fn and inserted_count > 0:
        log_fn(f"💾 Saved {inserted_count} new bills to database.")

def log_anomaly_to_db(conn, bill_id, anomaly_type, severity, baseline):
    """
    Records a detected anomaly in the 'Anomalies' table.
    """
    cursor = conn.cursor()
    try:
        sql = """
            INSERT INTO Anomalies (BillID, AnomalyType, Severity, BaselineValue, DetectionDate)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (bill_id, anomaly_type, severity, baseline, datetime.now())
        cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        print(f"❌ [DB ERROR] Failed to log anomaly for Bill ID {bill_id}: {e}")

def ensure_supply_exists(conn, supply_number):
    """
    Checks if a supply number exists in the Supplies table.
    If not, creates a basic record to satisfy referential integrity.
    Returns True if a new record was created, False otherwise.
    """
    cursor = conn.cursor()
    # Check for existence
    cursor.execute("SELECT Count(*) FROM Supplies WHERE SupplyNumber = ?", (supply_number,))
    exists = cursor.fetchone()[0] > 0
    
    if not exists:
        try:
            # Register only the supply number as requested
            cursor.execute("INSERT INTO Supplies (SupplyNumber) VALUES (?)", (supply_number,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ [DB ERROR] Could not register new supply {supply_number}: {e}")
    return False

def bill_exists(cursor, bill_hash):
    """Checks if the bill hash is already registered in the database."""
    cursor.execute("SELECT Count(*) FROM Bills WHERE BillHash = ?", (bill_hash,))
    return cursor.fetchone()[0] > 0


def update_seasonal_baselines(conn, default_threshold=0.35):
    """
    Rebuilds SeasonalBaselines using:

    - weighted seasonal contribution
    - invoice-level observations
    - weighted mean/std deviation
    - effective sample size

    This avoids:
    - fake sample inflation
    - variance collapse
    - multi-season distortion
    """

    import numpy as np
    from collections import defaultdict
    from datetime import timedelta, datetime

    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Ensure table exists
    # ---------------------------------------------------------

    tables = [t.table_name for t in cursor.tables(tableType='TABLE')]
    if 'SeasonalBaselines' in tables:
        cursor.execute("DELETE FROM SeasonalBaselines")
    else:
        cursor.execute("""
            CREATE TABLE SeasonalBaselines (
                SupplyNumber TEXT(50),
                SeasonType TEXT(20),
                AvgDailyConsumption DOUBLE,
                StdDeviation DOUBLE,
                SampleSize DOUBLE,
                ThresholdPercentage DOUBLE,
                LastUpdated DATETIME
            )
        """)
    conn.commit()

    # ---------------------------------------------------------
    # Season mapping
    # ---------------------------------------------------------

    seasons = {
        12: 'Winter', 1: 'Winter', 2: 'Winter',
        3: 'Spring', 4: 'Spring', 5: 'Spring',
        6: 'Summer', 7: 'Summer', 8: 'Summer',
        9: 'Autumn', 10: 'Autumn', 11: 'Autumn'
    }

    # ---------------------------------------------------------
    # History container
    # history[supply][season] = [
    #     (daily_avg, weight),
    #     ...
    # ]
    # ---------------------------------------------------------

    history = defaultdict(
        lambda: defaultdict(list)
    )

    # ---------------------------------------------------------
    # Load bills
    # ---------------------------------------------------------

    sql_select = """
        SELECT
            SupplyNumber,
            PeriodStart,
            PeriodEnd,
            Consumption
        FROM Bills
        WHERE
            (UCASE(TRIM(BillType)) LIKE '%ΕΚΚΑΘΑΡΙΣΤΙΚΟΣ%' OR UCASE(TRIM(BillType)) LIKE '%EKKATHARISTIKOS%')
            AND Consumption > 0
            AND DateDiff('d', PeriodStart, PeriodEnd) <= 45
    """

    cursor.execute(sql_select)

    rows = cursor.fetchall()

    # ---------------------------------------------------------
    # Build weighted observations
    # ---------------------------------------------------------

    for sup_no, start_date, end_date, kwh in rows:

        if not start_date or not end_date:
            continue

        total_days = (end_date - start_date).days + 1

        if total_days <= 0:
            continue

        daily_avg = float(kwh) / total_days

        # ---------------------------------------------
        # Count overlap days per season
        # ---------------------------------------------

        season_day_counts = defaultdict(int)

        curr_date = start_date

        while curr_date <= end_date:

            season_name = seasons.get(curr_date.month)

            if season_name:
                season_day_counts[season_name] += 1

            curr_date += timedelta(days=1)

        # ---------------------------------------------
        # Add weighted contribution
        # ---------------------------------------------

        for season_name, overlap_days in season_day_counts.items():

            seasonal_weight = overlap_days / total_days

            history[sup_no][season_name].append(
                (daily_avg, seasonal_weight)
            )

    # ---------------------------------------------------------
    # Insert weighted statistics
    # ---------------------------------------------------------

    insert_sql = """
        INSERT INTO SeasonalBaselines (
            SupplyNumber,
            SeasonType,
            AvgDailyConsumption,
            StdDeviation,
            SampleSize,
            ThresholdPercentage,
            LastUpdated
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    for sup_no, seasonal_data in history.items():

        for season_name, observations in seasonal_data.items():

            if not observations:
                continue

            values = np.array([
                x[0] for x in observations
            ])

            weights = np.array([
                x[1] for x in observations
            ])

            # -----------------------------------------
            # Effective sample size
            # -----------------------------------------

            effective_n = float(np.sum(weights))

            if effective_n <= 0:
                continue

            # -----------------------------------------
            # Weighted mean
            # -----------------------------------------

            weighted_mean = np.average(
                values,
                weights=weights
            )

            # -----------------------------------------
            # Weighted variance
            # -----------------------------------------

            weighted_variance = np.average(
                (values - weighted_mean) ** 2,
                weights=weights
            )

            weighted_std = np.sqrt(
                max(weighted_variance, 0)
            )

            # -----------------------------------------
            # Robust std floor
            # -----------------------------------------

            min_std = weighted_mean * 0.05

            weighted_std = max(
                weighted_std,
                min_std
            )

            # -----------------------------------------
            # Insert
            # -----------------------------------------

            cursor.execute(insert_sql, (
                sup_no,
                season_name,
                round(float(weighted_mean), 4),
                round(float(weighted_std), 4),
                round(float(effective_n), 2),
                default_threshold,
                datetime.now()
            ))

    conn.commit()

    return len(history)



def get_contractual_reference(cursor, provider, target_date):
    """
    Fetches DAM, Losses, and Margin for a specific date.
    Uses the 'Top 1' logic for Margins as you specified.
    """
    # 1. Fetch DAM (Lookup by first of the month)
    month_start = target_date.replace(day=1)
    cursor.execute("SELECT DAM FROM tblDAM WHERE [date] = ?", (month_start,))
    dam_row = cursor.fetchone()
    
    # 2. Fetch Losses (Lookup by year)
    cursor.execute("SELECT losses FROM Losses WHERE [year] = ?", (target_date.year,))
    loss_row = cursor.fetchone()
    
    # 3. Fetch Most Recent Margin (The 'Effective' margin logic)
    cursor.execute("""
        SELECT TOP 1 Margin FROM Margins 
        WHERE Provider = ? AND [Date] <= ? 
        ORDER BY [Date] DESC
    """, (provider, target_date))
    margin_row = cursor.fetchone()
    
    return (
        dam_row[0] if dam_row else None,
        loss_row[0] if loss_row else 0.0,
        margin_row[0] if margin_row else 0.0
    )



