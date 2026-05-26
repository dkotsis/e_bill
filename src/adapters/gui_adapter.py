# src/adapters/gui_adapter.py
from typing import List
from src.ports.reporter_port import ReporterPort
from src.domain.model.bill import Bill

# Temporary import from old code
from src.classes import GuiBridge


class GuiReporterAdapter(ReporterPort):
    def __init__(self, bridge: GuiBridge):
        self.bridge = bridge

    def log(self, message: str, level: str = "info"):
        """Forward log calls to GuiBridge"""
        self.bridge.log(message, level)

    def report_file_summary(self, filename: str, bills: List[Bill], anomalies: List):
        if not hasattr(self, '_reported_files'):
            self._reported_files = set()
        
        if filename in self._reported_files:
            return
        self._reported_files.add(filename)


    def report_final_summary(self, stats: dict):
        """Handle final batch summary"""
        try:
            from src.reporting import get_final_summary_text
            summary_text = get_final_summary_text(**stats)
            self.log("\n" + "="*70, "info")
            self.log(summary_text, "info")
            self.log("="*70 + "\n", "info")
        except Exception as e:
            self.log(f"⚠️ Could not generate final summary: {e}", "warn")