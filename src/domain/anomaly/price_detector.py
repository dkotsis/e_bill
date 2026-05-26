# src/domain/anomaly/price_detector.py
import numpy as np
from sklearn.ensemble import IsolationForest
from src.domain.model.bill import Bill
from typing import List, Dict


def detect_price_anomalies(bills: List[Bill], contamination: float = 0.05) -> List[Dict]:
    if len(bills) < 5:
        return []

    features = np.array([[b.compet_charge / b.consumption] for b in bills if b.consumption > 0])
    if len(features) < 5:
        return []

    clf = IsolationForest(contamination=contamination, random_state=42)
    predictions = clf.fit_predict(features)
    median_price = float(np.median(features))

    anomalies = []
    for i, pred in enumerate(predictions):
        if pred == -1:
            bill = bills[i]
            current_price = features[i][0]
            severity = (current_price - median_price) / median_price if median_price > 0 else 0

            anomalies.append({
                "bill": bill,
                "type": "PRICE",
                "severity": round(severity, 4),
                "baseline": round(median_price, 4),
                "current": round(current_price, 4)
            })
    return anomalies