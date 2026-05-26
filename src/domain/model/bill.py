# src/domain/model/bill.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Bill:
    supply_number: str = ""
    provider: str = ""
    bill_number: str = ""
    issue_date: Optional[datetime] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    period_days: int = 0
    consumption: float = 0.0
    compet_charge: float = 0.0
    regul_charge: float = 0.0
    bill_type: str = ""
    bill_hash: str = ""

    # For anomaly detection
    expected_charge: float = 0.0
    is_audit_failure: bool = False
    is_historical_anomaly: bool = False
    anomaly_notes: str = ""

    def is_valid(self) -> bool:
        return self.consumption > 0 and self.compet_charge > 0

    def total_days(self) -> int:
        """Fixed and robust total days calculation"""
        if not self.period_start or not self.period_end:
            return 0
        
        try:
            # Ensure they are datetime objects
            start = self.period_start
            end = self.period_end
            
            # Handle if they are pandas Timestamp or have .date()
            if hasattr(start, 'date'):
                start = start.date()
            if hasattr(end, 'date'):
                end = end.date()
            
            delta = end - start
            days = delta.days + 1
            return max(days, 1)  # at least 1 day
        except Exception as e:
            print(f"ERROR in total_days for bill {self.bill_number}: {e}")
            return 0

    def daily_consumption(self) -> float:
        days = self.total_days()
        return self.consumption / days if days > 0 else 0.0