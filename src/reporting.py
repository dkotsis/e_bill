# src/reporting.py
import os
from datetime import datetime

from src.utils import classify_anomaly

def format_bill_log_line(inv, status="OK"):
    """Creates a uniform log line with fixed-width columns including Issue Date."""
    provider = f"{inv.provider:<12}"[:12]
    bill_num = f"{inv.bill_number:<12}"[:12]
    supply_num = f"{inv.supply_number:<12}"[:12]
    
    if hasattr(inv, 'issue_date') and inv.issue_date:
        if isinstance(inv.issue_date, datetime):
            dt_str = inv.issue_date.strftime("%d/%m/%Y")
        else:
            dt_str = str(inv.issue_date)[:10]
    else:
        dt_str = "N/A"
    issue_date = f"{dt_str:<10}"
    
    consumption = f"{inv.consumption:>9,.1f} kWh"
    amount = f"{inv.compet_charge:>9,.2f} €"
    return f"📄 {provider} | {bill_num} | {supply_num} | {issue_date} | {consumption} | {amount} -> [{status}]"



def print_contract_audit_report(anomalies, log_fn):
    """Generates a highly-compacted grid for contractual pricing audit failures."""
    audit_anoms = [a for a in anomalies if "AUDIT" in str(a.get('class_type', ''))]
    if not audit_anoms:
        return
        
    line_width = 104
    log_fn("\n" + "=" * line_width, "info")
    log_fn("🔴 CONTRACT PRICE AUDIT REPORT (CONTRACTUAL RATE FAILURES)", "info")
    log_fn("=" * line_width, "info")
    
    header = (
        f"{'Provider':<10} | {'Bill #':<11} | {'Supply #':<11} | "
        f"{'Bill Rate':<10} | {'Cont.Rate':<10} | {'± Diff (€)':<11} | {'Dev %':>7}"
    )
    log_fn(header, "info")
    log_fn("-" * line_width, "info")
    
    for a in audit_anoms:
        provider = f"{a.get('provider', ''):<10}"[:10]
        bill_no = f"{a.get('bill_no', ''):<11}"[:11]
        supply_no = f"{a.get('supply_no', ''):<11}"[:11]
        
        charged_val = a.get('charged_val', 0.0)
        expected_val = a.get('avg_file_price', 0.0)
        consumption = a.get('consumption', 1.0)
        if consumption <= 0: 
            consumption = 1.0
            
        bill_unit_price = charged_val / consumption
        contract_unit_price = expected_val / consumption
        
        abs_diff = charged_val - expected_val
        pm_diff_str = f"{'+' if abs_diff >= 0 else ''}{abs_diff:,.2f}"
        pct_dev = a.get('pct_dev', 0.0) * 100.0
        
        log_fn(
            f"{provider} | {bill_no} | {supply_no} | "
            f"{bill_unit_price:>6.4f} € | {contract_unit_price:>6.4f} € | {pm_diff_str:<11} | {pct_dev:>6.1f}%",
            "critical"
        )
    log_fn("=" * line_width + "\n", "info")


def print_statistical_historical_report(anomalies, log_fn):
    """Generates a highly-compacted grid for statistical and historical deviations using strict risk matrix markers."""
    non_audit_anoms = [a for a in anomalies if "AUDIT" not in str(a.get('class_type', ''))]
    if not non_audit_anoms:
        return
        
    line_width = 104
    log_fn("\n" + "=" * line_width, "info")
    log_fn("⚠️ STATISTICAL PRICE VARIANCE & HISTORICAL BASELINES", "info")
    log_fn("=" * line_width, "info")
    
    header = (
        f"{'Provider':<10} | {'Bill #':<11} | {'Supply #':<11} | "
        f"{'Type/Category':<16} | {'Operational Summary Metrics':<29} | {'Status/Color':>11}"
    )
    log_fn(header, "info")
    log_fn("-" * line_width, "info")
    
    for a in non_audit_anoms:
        provider = f"{a.get('provider', ''):<10}"[:10]
        bill_no = f"{a.get('bill_no', ''):<11}"[:11]
        supply_no = f"{a.get('supply_no', ''):<11}"[:11]
        class_type = a.get('class_type', '')
        
        if "STATISTICAL" in class_type:
            # Map statistical attributes out to your specialized logic block
            z_score = abs(a.get('z_score', 0.0))
            confidence = a.get('confidence', 0.95)
            
            # Formulate pseudo-risk percentage value from raw mathematical Z scores
            derived_risk = min(99.0, max(10.0, z_score * 25.0)) 
            status_text, target_color = classify_anomaly(derived_risk, confidence)
            
            consumption = a.get('consumption', 1.0)
            if consumption <= 0: 
                consumption = 1.0
            u_price = a.get('charged_val', 0.0) / consumption
            
            metrics_str = f"Rate: {u_price:.4f} €/kWh"
            type_label = "STATISTICAL"
        else:
            # Historical Daily Calculations
            bill_daily = a.get('bill_daily_consumption', 0.0)
            base_daily = a.get('base_daily_consumption', 0.0)
            daily_diff = bill_daily - base_daily
            pm_diff_str = f"{'+' if daily_diff >= 0 else ''}{daily_diff:,.1f}"
            
            metrics_str = f"Dly:{bill_daily:.1f} Base:{base_daily:.1f} ({pm_diff_str})"
            type_label = "HISTORICAL"
            status_text = "REVIEW"
            target_color = "warn"
            
        log_fn(
            f"{provider} | {bill_no} | {supply_no} | "
            f"{type_label:<16} | {metrics_str:<29} | {status_text:>11}",
            target_color
        )
    log_fn("=" * line_width + "\n", "info")