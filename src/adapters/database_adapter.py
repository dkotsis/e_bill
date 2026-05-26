import pyodbc
from typing import List, Dict
from src.ports.database_port import DatabasePort
from src.domain.model.bill import Bill
from src.db_handling import (save_invoices, bill_exists, ensure_supply_exists,
                           get_seasonal_baseline_dict, log_anomaly_to_db,
                           update_seasonal_baselines)



class AccessDatabaseAdapter(DatabasePort):
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

    def save_bills(self, bills: List[Bill]) -> int:
        return save_invoices(self.conn, bills)

    def bill_exists(self, bill_hash: str) -> bool:
        return bill_exists(self.cursor, bill_hash)

    def ensure_supply_exists(self, supply_number: str) -> bool:
        return ensure_supply_exists(self.conn, supply_number)

    def get_seasonal_baselines(self, supply_number: str) -> Dict:
        return get_seasonal_baseline_dict(self.conn, supply_number)

    def log_anomaly(self, bill_id: int, anomaly_type: str, severity: float, baseline: float):
        log_anomaly_to_db(self.conn, bill_id, anomaly_type, severity, baseline)

    def update_seasonal_baselines(self):
        update_seasonal_baselines(self.conn)
    
