# src/infrastructure/config.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:
    APP_TITLE: str = "Electricity Bill Importer PRO v4.3"
    DB_DIR: Path = Path("db")
    DB_NAME: str = "Electricity_Bills.accdb"
    
    # Anomaly & Audit
    DEVIATION_TOLERANCE: float = 0.08
    ISOLATION_CONTAMINATION: float = 0.05
    Z_SCORE_THRESHOLD: float = 2.5
    PCT_DIFF_THRESHOLD: float = 0.20
    MIN_RECORDS_FOR_ANOMALY: int = 5
    
    # Filtering
    CONSUMPTION_THRESHOLD: float = 10.0
    CHARGE_THRESHOLD: float = 5.0

    def get_db_path(self) -> Path:
        return self.DB_DIR / self.DB_NAME


DEFAULT_CONFIG = AppConfig()