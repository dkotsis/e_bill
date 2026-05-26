# main.py
import os
import glob
import queue
import threading
from src.infrastructure.config import DEFAULT_CONFIG
from src.adapters.database_adapter import AccessDatabaseAdapter
from src.adapters import database_adapter
from src.adapters.excel_parser_adapter import ExcelParserAdapter
from src.adapters.gui_adapter import GuiReporterAdapter
from src.application.bill_processor import BillProcessor
from src.classes import GuiBridge
from src.gui import start_gui, set_processing_function
from src.db_handling import connect_access, ensure_tables
from src.reporting import print_contract_audit_report, print_statistical_historical_report

gui_queue = queue.Queue()

def print_ui_console_log(bridge, text, color="info"):
    if hasattr(bridge, 'console') and bridge.console:
        bridge.console.configure(state="normal")
        bridge.console.insert("end", str(text) + "\n", color)
        bridge.console.see("end")
        bridge.console.configure(state="disabled")

def poll_queue(root_window, reporter_instance):
    bridge = getattr(root_window, 'active_bridge', None)
    
    if bridge and reporter_instance:
        try:
            while True:
                msg = gui_queue.get_nowait()
                msg_type = msg.get("type")
                
                if msg_type == "log":
                    print_ui_console_log(bridge, msg["text"], msg["color"])

                elif msg_type == "report_file_summary":
                    report_flags = msg.get("flags", {})
                    if report_flags.get("file_summary", True):
                        try:
                            file_path = msg["file_path"]
                            valid_bills = msg["valid_bills"]
                            anomalies = msg["anomalies"]
                            stats_counters = msg["stats_counters"]
                            file_totals = msg["file_totals"]
                            
                            fname = os.path.basename(file_path)
                            skipped_count = (stats_counters.get("un", 0) + stats_counters.get("sk", 0) + 
                                             stats_counters.get("db", 0) + stats_counters.get("fl", 0))
                            total_checked = len(valid_bills) + skipped_count

                            print_ui_console_log(bridge, "\n" + "==================================================", "info")
                            print_ui_console_log(bridge, f"📊 FILE SUMMARY REPORT: {fname}", "info")
                            print_ui_console_log(bridge, "==================================================", "info")
                            print_ui_console_log(bridge, f" Total Checked Documents       : {total_checked}", "info")
                            print_ui_console_log(bridge, f" Stored/Buffer-Valid Records   : {len(valid_bills)}", "ok")
                            print_ui_console_log(bridge, f" Skipped/Filtered Invoices     : {skipped_count}", "skip")
                            print_ui_console_log(bridge, f" Aggregate Consumption Volume   : {file_totals.get('kwh', 0.0):,.2f} kWh", "info")
                            print_ui_console_log(bridge, f" Total Competitive Cost        : {file_totals.get('compet', 0.0):,.2f} €", "ok")
                            print_ui_console_log(bridge, f" Total Regulated Cost          : {file_totals.get('regulated', 0.0):,.2f} €", "info")
                            print_ui_console_log(bridge, "--------------------------------------------------", "info")
                            print_ui_console_log(bridge, " DETAILED FLAGGED ANOMALIES BREAKDOWN:", "info")
                            print_ui_console_log(bridge, f"   ↳ 🔴 Price Audit Failures        : {stats_counters.get('audit_fail', 0)}", "critical" if stats_counters.get('audit_fail', 0) > 0 else "info")
                            print_ui_console_log(bridge, f"   ↳ 🟡 Historical Consumption Anom : {stats_counters.get('hist_anom', 0)}", "warn" if stats_counters.get('hist_anom', 0) > 0 else "info")
                            print_ui_console_log(bridge, f"   ↳ 🟣 Statistical Model Anomalies  : {stats_counters.get('stat_anom', 0)}", "warn" if stats_counters.get('stat_anom', 0) > 0 else "info")
                            print_ui_console_log(bridge, "==================================================\n", "info")
                            
                            if report_flags.get("anomalies", True) and len(anomalies) > 0:
                                def log_w(t, c): print_ui_console_log(bridge, t, c)
                                print_contract_audit_report(anomalies, log_w)
                                print_statistical_historical_report(anomalies, log_w)
                                
                        except Exception as re: print(f"File summary display error: {re}")

                elif msg_type == "report_final_summary":
                    report_flags = msg.get("flags", {})
                    if report_flags.get("final", True):
                        try:
                            stats = msg["stats"]
                            stats_counters = msg.get("stats_counters", {})
                            
                            print_ui_console_log(bridge, "\n" + "==================================================", "info")
                            print_ui_console_log(bridge, "🏁 BATCH IMMIGRATION SUMMARY OVERVIEW", "info")
                            print_ui_console_log(bridge, "==================================================", "info")
                            print_ui_console_log(bridge, f" Total Excel Source Files Read : {stats.get('files_count', 0)}", "info")
                            print_ui_console_log(bridge, f" Total Checked Documents       : {stats.get('total_inv', 0)}", "info")
                            print_ui_console_log(bridge, f" Stored/Buffer-Valid Records   : {stats.get('valid', 0)}", "ok")
                            print_ui_console_log(bridge, f" Skipped/Filtered Invoices     : {stats.get('skipped', 0)}", "skip")
                            print_ui_console_log(bridge, f" Aggregate Consumption Volume   : {stats.get('kwh', 0.0):,.2f} kWh", "info")
                            print_ui_console_log(bridge, f" Total Competitive Cost        : {stats.get('compet', 0.0):,.2f} €", "ok")
                            print_ui_console_log(bridge, f" Total Regulated Cost          : {stats.get('regul', 0.0):,.2f} €", "info")
                            print_ui_console_log(bridge, "--------------------------------------------------", "info")
                            print_ui_console_log(bridge, " DETAILED FLAGGED ANOMALIES BREAKDOWN:", "info")
                            print_ui_console_log(bridge, f"   ↳ 🔴 Price Audit Failures        : {stats_counters.get('audit_fail', 0)}", "critical" if stats_counters.get('audit_fail', 0) > 0 else "info")
                            print_ui_console_log(bridge, f"   ↳ 🟡 Historical Consumption Anom : {stats_counters.get('hist_anom', 0)}", "warn" if stats_counters.get('hist_anom', 0) > 0 else "info")
                            print_ui_console_log(bridge, f"   ↳ 🟣 Statistical Model Anomalies  : {stats_counters.get('stat_anom', 0)}", "warn" if stats_counters.get('stat_anom', 0) > 0 else "info")
                            print_ui_console_log(bridge, "==================================================\n", "info")
                        except Exception as re: print(f"Final summary validation error: {re}")

                elif msg_type == "file_progress":
                    if hasattr(bridge, 'file_p') and bridge.file_p: bridge.file_p.set(float(msg["val"]))
                    if hasattr(bridge, 'f_label') and bridge.f_label: bridge.f_label.configure(text=msg["text"])
                elif msg_type == "page_progress":
                    if hasattr(bridge, 'inv_p') and bridge.inv_p: bridge.inv_p.set(float(msg["val"]))
                    if hasattr(bridge, 'i_label') and bridge.i_label: bridge.i_label.configure(text=msg["text"])
                elif msg_type == "clear_stats":
                    if hasattr(bridge, 'stats_scroll') and bridge.stats_scroll:
                        for widget in bridge.stats_scroll.winfo_children(): widget.destroy()
                elif msg_type == "processing_complete":
                    if hasattr(bridge, 'btn_start') and bridge.btn_start: bridge.btn_start.configure(state="normal", fg_color="#00bb77", text="▶ START PROCESSING")
                    if hasattr(bridge, 'btn_stop') and bridge.btn_stop: bridge.btn_stop.configure(state="disabled", fg_color="#555555", text="⏸ PAUSE PROCESSING")
                    if hasattr(bridge, 'status_label') and bridge.status_label: bridge.status_label.configure(text="Ready", text_color="#ffffff")
                            
                gui_queue.task_done()
        except queue.Empty: pass
    
    if root_window:
        try: root_window.update_idletasks()
        except Exception: pass
        root_window.after(30, lambda: poll_queue(root_window, reporter_instance))

def run_processing_worker(path, bridge: GuiBridge, settings, pause_event, reporter_instance):
    config = DEFAULT_CONFIG
    conn = None
    total_kwh = total_charge = total_processed = 0
    report_flags = settings.get("reports", {})

    try:
        gui_queue.put({"type": "clear_stats"})
        is_dry_run = settings.get("dry_run", True)
        
        conn = connect_access(str(config.DB_DIR), config.DB_NAME)
        ensure_tables(conn)

        db_port = AccessDatabaseAdapter(conn) if conn else None
        parser = ExcelParserAdapter()
        processor = BillProcessor(db_port, parser, reporter_instance, config, is_dry_run=is_dry_run)

        if os.path.isfile(path): files = [path]
        else: files = glob.glob(os.path.join(path, "*.[xX][lL][sS]*"))

        total_files = len(files) if files else 1
        total_un = total_sk = total_fl = total_db = total_audit_fail = total_hist_anom = total_stat_anom = 0
        total_regulated = 0.0

        gui_queue.put({"type": "file_progress", "val": 0.0, "text": f"📁 File Progress: 0/{total_files}"})

        for idx, file_path in enumerate(files, 1):
            if pause_event: pause_event.wait()
            result = processor.process_file(file_path, pause_event, gui_queue, report_flags)
            
            total_processed += result["processed"]
            total_kwh += result["kwh"]
            total_charge += result["charge"]
            total_regulated += result.get("regulated", 0.0)
            
            r_stats = result.get("stats_counters", {})
            total_un += r_stats.get("un", 0)
            total_sk += r_stats.get("sk", 0)
            total_fl += r_stats.get("fl", 0)
            total_db += r_stats.get("db", 0)
            total_audit_fail += r_stats.get("audit_fail", 0)
            total_hist_anom += r_stats.get("hist_anom", 0)
            total_stat_anom += r_stats.get("stat_anom", 0)

            gui_queue.put({"type": "file_progress", "val": float(idx) / float(total_files), "text": f"📁 File Progress: {idx}/{total_files}"})

        final_stats = {
            "files_count": total_files,
            "total_inv": total_processed + total_un + total_sk + total_fl + total_db,
            "valid": total_processed, "skipped": total_un + total_sk + total_db + total_fl,
            "kwh": total_kwh, "compet": total_charge, "regul": total_regulated  
        }
        
        gui_queue.put({
            "type": "report_final_summary", 
            "stats": final_stats, 
            "stats_counters": {"audit_fail": total_audit_fail, "hist_anom": total_hist_anom, "stat_anom": total_stat_anom}, 
            "flags": report_flags
        })

        if is_dry_run:
            if conn: conn.rollback()
            gui_queue.put({"type": "log", "text": "ℹ️ Dry Run complete. All file transaction stages discarded.", "color": "info"})
        else:
            # -----------------------------------------------------------------
            # 1. TRIGGER BASELINE COMPILATION (USING THE ADAPTER CONTEXT)
            # -----------------------------------------------------------------
            try:
                gui_queue.put({"type": "log", "text": "🔄 Processing Complete! Compiling historical seasonal baselines...", "color": "info"})
                
                # CHANGED: Feed 'conn' directly into the call signature to satisfy the override!
                records_updated = database_adapter.update_seasonal_baselines(conn)
                
                if records_updated:
                    gui_queue.put({"type": "log", "text": f"📊 Computed and cached statistics across {records_updated} supply metrics.", "color": "ok"})
                else:
                    gui_queue.put({"type": "log", "text": "📊 Baselines compiled successfully.", "color": "ok"})
                    
            except Exception as baseline_err:
                gui_queue.put({"type": "log", "text": f"⚠️ Baseline Calculation Postponed: {baseline_err}", "color": "warn"})

            # -----------------------------------------------------------------
            # 2. GLOBAL BATCH COMMIT
            # -----------------------------------------------------------------
            if conn: 
                conn.commit()
            gui_queue.put({"type": "log", "text": "✅ All records successfully saved, baselines compiled, and committed to MS Access!", "color": "ok"})

    except Exception as e:
        gui_queue.put({"type": "log", "text": f"❌ Core processing worker exception occurred: {e}", "color": "critical"})
    finally:
        if conn: conn.close()
        # MUST BE SENT: This restores progress bar states and unlocks the UI panels
        gui_queue.put({"type": "processing_complete"})

def run_processing_entrypoint(path, bridge: GuiBridge, settings, pause_event):
    bridge.root.active_bridge = bridge
    reporter_instance = GuiReporterAdapter(bridge)
    bridge.root.after(40, lambda: poll_queue(bridge.root, reporter_instance))
    
    threading.Thread(target=run_processing_worker, args=(path, bridge, settings, pause_event, reporter_instance), daemon=True).start()

class ConfigProxy:
    def __init__(self, obj): self._obj = obj
    def __getattr__(self, name): return getattr(self._obj, name)
    def get(self, key, default=None): return getattr(self._obj, key, default)

if __name__ == "__main__":
    set_processing_function(run_processing_entrypoint)
    start_gui(ConfigProxy(DEFAULT_CONFIG))