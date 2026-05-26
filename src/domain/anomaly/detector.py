# src/domain/anomaly/detector.py
from typing import List, Dict
from src.domain.model.bill import Bill
from src.domain.anomaly.price_detector import detect_price_anomalies
from src.domain.anomaly.consumption_detector import detect_consumption_anomaly


class AnomalyDetector:
    def __init__(self, config):
        self.config = config

    def detect_price(self, bills: List[Bill]) -> List[dict]:
        return detect_price_anomalies(bills, self.config.ISOLATION_CONTAMINATION)

    def detect_consumption(self, bill: Bill, baselines: dict):
        return detect_consumption_anomaly(bill, baselines)