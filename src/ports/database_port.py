from abc import ABC, abstractmethod
from typing import List, Dict
from src.domain.model.bill import Bill

class DatabasePort(ABC):
    @abstractmethod
    def save_bills(self, bills: List[Bill]) -> int: pass
    @abstractmethod
    def bill_exists(self, bill_hash: str) -> bool: pass
    @abstractmethod
    def ensure_supply_exists(self, supply_number: str) -> bool: pass
    @abstractmethod
    def get_seasonal_baselines(self, supply_number: str) -> Dict: pass
    @abstractmethod
    def log_anomaly(self, bill_id: int, anomaly_type: str, severity: float, baseline: float): pass
    @abstractmethod
    def update_seasonal_baselines(self): pass