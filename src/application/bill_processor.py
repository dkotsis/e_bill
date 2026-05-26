# src/application/bill_processor.py
from typing import List
from datetime import datetime
from src.domain.model.bill import Bill
from src.ports.database_port import DatabasePort
from src.ports.parser_port import ParserPort
from src.ports.reporter_port import ReporterPort
from src.domain.anomaly.detector import AnomalyDetector
from src.domain.anomaly.price_audit import calculate_expected_charge
from src.utils import generate_hash
from src.reporting import format_bill_log_line

class BillProcessor:
    def __init__(self, db_port: DatabasePort, parser: ParserPort,
                 reporter: ReporterPort, config, is_dry_run: bool = True):
        self.db = db_port
        self.parser = parser
        self.reporter = reporter
        self.config = config
        self.is_dry_run = is_dry_run
        self.anomaly_detector = AnomalyDetector(config)

    def process_file(self, file_path: str, pause_event=None, gui_queue=None, report_flags=None):
        if report_flags is None:
            report_flags = {}

        bills = self.parser.parse(file_path)
        valid_bills = []          
        audit_passed_bills = []   
        anomalies = []            
        new_supplies_found = []   
        
        stats = {"un": 0, "sk": 0, "fl": 0, "db": 0, "audit_fail": 0, "hist_anom": 0, "stat_anom": 0}
        file_total_kwh = file_total_charge = file_total_regulated = 0.0
        
        if gui_queue:
            gui_queue.put({"type": "log", "text": f"▶️ Processing: {file_path}", "color": "info"})

        total_bills = len(bills) if bills else 0

        if gui_queue:
            gui_queue.put({"type": "page_progress", "val": 0.0, "text": f"📄 Invoice Progress: 0/{total_bills}"})

        for idx, bill in enumerate(bills, 1):
            if pause_event:
                pause_event.wait()

            bill.bill_hash = generate_hash(bill)
            if not bill.is_valid():
                continue

            bill.expected_charge = 0.0
            bill.audit_note = "Passed structural verification"
            bill.is_audit_failure = False
            bill.is_statistical_anomaly = False
            bill.is_historical_anomaly = False

            if self.db and hasattr(self.db, 'ensure_supply_exists'):
                is_new = self.db.ensure_supply_exists(bill.supply_number)
                if is_new:
                    new_supplies_found.append(bill.supply_number)

            if "ΕΝΑΝΤΙ" in (getattr(bill, "bill_type", "") or "").upper():
                stats["un"] += 1
                if report_flags.get("per_bill", True) and gui_queue:
                    gui_queue.put({"type": "log", "text": format_bill_log_line(bill, status="UN"), "color": "skip"})
                continue

            if bill.consumption <= 0 or bill.compet_charge <= 0:
                stats["sk"] += 1
                if report_flags.get("per_bill", True) and gui_queue:
                    gui_queue.put({"type": "log", "text": format_bill_log_line(bill, status="SK"), "color": "skip"})
                continue

            c_thresh = getattr(self.config, 'CONSUMPTION_THRESHOLD', 10)
            m_thresh = getattr(self.config, 'CHARGE_THRESHOLD', 5)
            if bill.consumption <= c_thresh or bill.compet_charge <= m_thresh:
                stats["fl"] += 1
                if report_flags.get("per_bill", True) and gui_queue:
                    gui_queue.put({"type": "log", "text": format_bill_log_line(bill, status="FL"), "color": "warn"})
                continue

            if self.db and self.db.bill_exists(bill.bill_hash):
                stats["db"] += 1
                if report_flags.get("per_bill", True) and gui_queue:
                    gui_queue.put({"type": "log", "text": format_bill_log_line(bill, status="DB"), "color": "double"})
                continue

            display_status = "OK"
            final_color = "ok"  
            audit_notes = []

            if self.db and self.db.cursor:
                expected = calculate_expected_charge(bill, self.db.cursor)
                bill.expected_charge = expected

                diff = bill.compet_charge - expected
                p_tolerance = getattr(self.config, 'DEVIATION_TOLERANCE', 0.08)

                if expected > 0 and abs(diff) > (expected * p_tolerance):
                    final_color = "critical"  
                    bill.is_audit_failure = True
                    stats["audit_fail"] += 1
                    audit_notes.append("Price Audit Fail")
                    
                    anomalies.append({
                        "filename": file_path, "provider": bill.provider, "bill_no": bill.bill_number,
                        "supply_no": bill.supply_number, "type": "PRICE", "class_type": "AUDIT FAIL",
                        "charged_val": bill.compet_charge, "avg_file_price": expected, "pct_dev": diff / expected,
                        "consumption": bill.consumption
                    })
                else:
                    audit_notes.append("Price Audit Passed.")
                    audit_passed_bills.append(bill)

                if report_flags.get("historical", True) and hasattr(self.db, 'get_seasonal_baselines'):
                    baselines = self.db.get_seasonal_baselines(bill.supply_number)
                    avg_hist_consumption = baselines.get('avg_consumption', 0) if baselines else 0
                    c_tolerance = getattr(self.config, 'CONSUMPTION_TOLERANCE', 0.50)

                    if avg_hist_consumption > 0:
                        c_diff = abs(bill.consumption - avg_hist_consumption)
                        if c_diff > (avg_hist_consumption * c_tolerance):
                            bill.is_historical_anomaly = True
                            stats["hist_anom"] += 1
                            audit_notes.append("Consumption Anomaly")
                            
                            days = 30
                            if getattr(bill, 'period_start', None) and getattr(bill, 'period_end', None):
                                try:
                                    delta = bill.period_end - bill.period_start
                                    if delta.days > 0: days = delta.days
                                except Exception: pass
                                
                            anomalies.append({
                                "filename": file_path, "provider": bill.provider, "bill_no": bill.bill_number,
                                "supply_no": bill.supply_number, "type": "CONSUMPTION", "class_type": "HISTORICAL DEVIATION",
                                "pct_dev": c_diff / avg_hist_consumption,
                                "bill_daily_consumption": bill.consumption / days,
                                "base_daily_consumption": avg_hist_consumption / days
                            })

                bill.audit_note = " | ".join(audit_notes)
            
            valid_bills.append(bill)

            if report_flags.get("per_bill", True) and gui_queue:
                gui_queue.put({"type": "log", "text": format_bill_log_line(bill, status=display_status), "color": final_color})

            if hasattr(self.reporter, 'bridge') and self.reporter.bridge:
                try: self.reporter.bridge.update_stats(bill.provider, bill.consumption, bill.compet_charge)
                except Exception: pass

            file_total_kwh += bill.consumption
            file_total_charge += bill.compet_charge
            file_total_regulated += getattr(bill, 'regul_charge', 0.0)

            if total_bills > 0 and gui_queue:
                gui_queue.put({
                    "type": "page_progress",
                    "val": float(idx) / float(total_bills),
                    "text": f"📄 Invoice Progress: {idx}/{total_bills}"
                })

        # Machine Learning Statistical Engine Run
        if len(audit_passed_bills) >= 5:
            try:
                price_anoms = self.anomaly_detector.detect_price(audit_passed_bills)
                for pa in price_anoms:
                    b = pa.get('bill')
                    if b:
                        b.is_statistical_anomaly = True
                        stats["stat_anom"] += 1
                        
                        anomalies.append({
                            "filename": file_path, "provider": b.provider, "bill_no": b.bill_number,
                            "supply_no": b.supply_number, "type": "PRICE", "class_type": "STATISTICAL DEVIATION",
                            "charged_val": b.compet_charge, "consumption": b.consumption,
                            "pct_dev": pa.get('pct_dev', 0.0),
                            "z_score": pa.get('z_score', 3.0),
                            "confidence": pa.get('confidence', 0.95)
                        })
            except Exception as e:
                if gui_queue: gui_queue.put({"type": "log", "text": f"⚠️ Statistical model warning: {e}", "color": "warn"})

        if new_supplies_found and gui_queue:
            gui_queue.put({"type": "log", "text": f"📋 New unique supplies verified: {', '.join(new_supplies_found)}", "color": "info"})

        if valid_bills and self.db:
            self.db.save_bills(valid_bills)

        if gui_queue:
            gui_queue.put({
                "type": "report_file_summary",
                "file_path": file_path,
                "valid_bills": valid_bills,
                "anomalies": anomalies,
                "stats_counters": stats,
                "flags": report_flags,
                "file_totals": {
                    "kwh": file_total_kwh,
                    "compet": file_total_charge,
                    "regulated": file_total_regulated
                }
            })

        return {
            "processed": len(valid_bills), "anomalies": len(anomalies),
            "kwh": file_total_kwh, "charge": file_total_charge, "regulated": file_total_regulated,
            "stats_counters": stats
        }