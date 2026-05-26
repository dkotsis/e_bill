# src/domain/anomaly/consumption_detector.py
from dataclasses import dataclass
from datetime import timedelta
from collections import defaultdict
import numpy as np
from src.domain.model.bill import Bill

@dataclass
class ConsumptionAnomalyResult:
    is_anomaly: bool
    actual_daily: float
    baseline_daily: float
    pct_diff: float
    z_score: float
    risk_score: int
    confidence: float

def get_season(month: int) -> str:
    mapping = {12:'Winter', 1:'Winter', 2:'Winter', 
               3:'Spring', 4:'Spring', 5:'Spring',
               6:'Summer', 7:'Summer', 8:'Summer', 
               9:'Autumn', 10:'Autumn', 11:'Autumn'}
    return mapping.get(month, 'Unknown')

def detect_consumption_anomaly(bill: Bill, baselines: dict) -> ConsumptionAnomalyResult:
    if not bill.period_start or not bill.period_end or bill.consumption <= 0:
        return ConsumptionAnomalyResult(False, 0, 0, 0, 0, 0, 0)

    # Calculate exact duration span
    total_days = (bill.period_end - bill.period_start).days
    if total_days <= 0:
        return ConsumptionAnomalyResult(False, 0, 0, 0, 0, 0, 0)

    actual_daily = bill.consumption / total_days

    # 1. Day Allocation Framework (FIXED BOUNDARY TO REMOVE INDEX INFLATION)
    season_days = defaultdict(int)
    curr = bill.period_start
    while curr < bill.period_end:  # Changed '<=' to '<' to avoid extracting an extra ghost day
        season_days[get_season(curr.month)] += 1
        curr += timedelta(days=1)

    # Calculate historical baseline allocations based on seasonal metrics
    weighted_sum = total_weight = 0.0
    active_stds = []

    for season, days in season_days.items():
        stats = baselines.get(season)
        if stats and stats.get('AvgDailyConsumption', 0) > 0:
            weighted_sum += stats['AvgDailyConsumption'] * days
            total_weight += days
            if stats.get('StdDeviation', 0) > 0:
                active_stds.append(stats['StdDeviation'])

    # If no baseline context exists for these specific seasons yet, exit safely
    if total_weight == 0:
        return ConsumptionAnomalyResult(False, actual_daily, 0, 0, 0, 0, 0.3)

    baseline_daily = weighted_sum / total_weight
    pct_diff = abs(actual_daily - baseline_daily) / baseline_daily if baseline_daily > 0 else 0

    # Determine historical standard deviation profile safely
    if active_stds:
        base_std = np.mean(active_stds)
    else:
        base_std = baseline_daily * 0.15 # 15% fallback tolerance matrix

    # 2. FALSE POSITIVE PROTECTION: Enforce a standard deviation lower floor limit
    safe_std = max(base_std, baseline_daily * 0.10) # Protects against hypersensitive statistical triggers
    z_score = (actual_daily - baseline_daily) / safe_std

    # High confidence alerts require a clear 35%+ baseline breach and a significant Z-score spread
    is_anomaly = (pct_diff > 0.35) and (abs(z_score) > 2.0)
    risk_score = min(100, int(abs(z_score) * 20)) if is_anomaly else 0

    # 3. CONFIDENCE PENALTY DEGRADATION
    # If a bill is short/standard (<=45 days), confidence remains high (0.95)
    # If the bill is a long-span/clearance bill, degrade confidence down to 0.30 to signify smoothing
    confidence = 0.95 if total_days <= 45 else 0.30

    return ConsumptionAnomalyResult(
        is_anomaly=is_anomaly,
        actual_daily=round(actual_daily, 2),
        baseline_daily=round(baseline_daily, 2),
        pct_diff=round(pct_diff, 4),
        z_score=round(z_score, 2),
        risk_score=risk_score,
        confidence=confidence
    )