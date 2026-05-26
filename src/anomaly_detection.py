from __future__ import annotations
# -*- coding: utf-8 -*-
"""
=============================================================================
Project:        Electricity Bill Importer PRO
File:           src/anomaly_detection.py
Description:    Machine Learning module utilizing the Isolation Forest 
                algorithm to detect outliers in electricity pricing and 
                consumption. It performs seasonal analysis and calculates 
                statistical risk scores to identify billing errors.
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



# Standard Library Imports
from dataclasses import dataclass
from typing import Callable
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import IsolationForest

# Local imports
from src.classes import bill
from src.utils import format_greek_display, format_greek_save

# ============================================================ #

# ------------------------------------------------------------------ #
#  Result types -  STRUCTURE                                         #
# ------------------------------------------------------------------ #

@dataclass
class AnomalyRecord:
    logar: bill
    price_per_kwh: float
    kwh_per_day: float
    flag: str  # "PRICE" | "KWH/DAY"

@dataclass
class AnomalyResult:
    anomalies: list[AnomalyRecord]
    total_records: int

# ------------------------------------------------------------------ #
#  Anomaly Detection Logic                                           #
# ------------------------------------------------------------------ #

def get_days_per_season(start_date, end_date):
    """
    Splits the bill duration into days per season.
    Seasons: Winter (Dec-Feb), Spring (Mar-May), Summer (Jun-Aug), Autumn (Sep-Nov)
    """
    # Mapping months to season names
    season_map = {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Autumn", 10: "Autumn", 11: "Autumn"
    }
    
    days_per_season = {"Winter": 0, "Spring": 0, "Summer": 0, "Autumn": 0}
    
    current_date = start_date
    while current_date <= end_date:
        season = season_map[current_date.month]
        days_per_season[season] += 1
        current_date += timedelta(days=1)
        
    return days_per_season


def build_feature_records(invoices):
    """
    Prepares numerical features for the Isolation Forest batch analysis.
    Focuses on the Unit Price (Competitive Charge / Consumption).
    """
    records = []
    for inv in invoices:
        if inv.consumption > 0:
            unit_price = inv.compet_charge / inv.consumption
            records.append({
                'bill_obj': inv,
                'feature_vector': [unit_price]
            })
    return records

def detect_anomalies(feature_records, contamination=0.05, log_fn=None):
    """
    Batch detection for Price Anomalies using Isolation Forest.
    """
    if not feature_records:
        return []

    X = np.array([item['feature_vector'] for item in feature_records])
    
    # Isolation Forest Model
    clf = IsolationForest(contamination=contamination, random_state=42)
    preds = clf.fit_predict(X)
    
    # Calculate median for baseline reporting
    median_price = np.median(X)
    anomalies_found = []

    for i, pred in enumerate(preds):
        if pred == -1:  # Outlier detected
            item = feature_records[i]
            bill = item['bill_obj']
            current_val = item['feature_vector'][0]
            
            severity = (current_val - median_price) / median_price if median_price > 0 else 0
            
            anomalies_found.append({
                'bill_obj': bill,
                'severity': severity,
                'baseline': median_price
            })
            
            if log_fn:
                log_fn(f"⚠️ [PRICE ANOMALY] Bill {bill.bill_number}: {current_val:.4f} €/kWh "
                       f"(Batch Median: {median_price:.4f})", "error")

    return anomalies_found



# In src/anomaly_detection.py or a dedicated peer_audit.py
def calculate_batch_z_scores(invoices: list[bill]):
    """Computes exact Z-scores for unit prices across a homogenous provider batch."""
    prices = [inv.compet_charge / inv.consumption for inv in invoices if inv.consumption > 0]
    if len(prices) < 5:  # Not enough data for statistical validity
        return []
        
    mean_p = np.mean(prices)
    std_p = np.std(prices) if np.std(prices) > 0 else 0.0001
    
    anomalies = []
    for inv in invoices:
        if inv.consumption <= 0: continue
        u_price = inv.compet_charge / inv.consumption
        z = (u_price - mean_p) / std_p
        
        if abs(z) > 2.5:  # High-confidence outlier threshold
            anomalies.append({
                'bill_obj': inv,
                'z_score': z,
                'confidence': 0.90 if len(prices) > 30 else 0.60,
                'charged_val': inv.compet_charge,
                'consumption': inv.consumption
            })
    return anomalies

