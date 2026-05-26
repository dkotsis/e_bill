# -*- coding: utf-8 -*-
"""
=============================================================================
Project:        Electricity Bill Importer PRO
File:           src/classes.py
Description:    Defines core data structures and dataclasses (e.g., bill)
                to ensure type safety and data consistency across all modules.
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


# Standard library imports
from dataclasses import dataclass
from datetime import datetime

# ============================================================ #


@dataclass
class bill:
    supply_number: str = ""
    provider: str = ""
    bill_number: str = ""
    issue_date: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    consumption: float = 0.0
    compet_charge: float = 0.0
    regul_charge: float = 0.0
    bill_type: str = ""
    bill_hash: str = ""  # For duplicate detection
    expected_charge: float = 0.0  # For anomaly detection
    is_audit_failure: bool = False  # Flag for audit failures
    audit_notes: str = ""  # For manual review comments

    def is_valid(self) -> bool:
        return self.compet_charge > 0.0



class GuiBridge:
    def __init__(self, console, file_progress, invoice_progress, status_label, root, stats_scroll, f_label, i_label):
        # The 8 arguments expected from gui.py:
        self.console = console
        self.file_p = file_progress
        self.inv_p = invoice_progress
        self.status = status_label
        self.root = root
        self.stats_scroll = stats_scroll
        self.f_label = f_label
        self.i_label = i_label
        
        # Internal dictionary to store the dynamic UI labels for each provider
        self.stats_labels = {} 

    def log(self, message, level="info"):
        """
        Directly maps the requested level to the tags defined in gui.py.
        """
        # Mapping to your existing gui.py tags:
        # 'ok'      -> #00E676 (Green)
        # 'anomaly' -> #AFAF1C (Amber/Yellow)
        # 'error'   -> #ff4444 (Red)
        # 'skip'    -> #1DC4EE (Blue)
        
        self.root.after(0, lambda: self.console.insert("end", f"{message}\n", level))
        self.root.after(0, lambda: self.console.see("end"))

    def update_status(self, text, color="white"):
        self.root.after(0, lambda: self.status.configure(text=text, text_color=color))

    def update_progress(self, file_val=None, file_text=None, inv_val=None, inv_text=None):
        if file_val is not None:
            self.root.after(0, lambda: self.file_p.set(file_val))
        if file_text is not None:
            self.root.after(0, lambda: self.f_label.configure(text=file_text))
        if inv_val is not None:
            self.root.after(0, lambda: self.inv_p.set(inv_val))
        if inv_text is not None:
            self.root.after(0, lambda: self.i_label.configure(text=inv_text))

    def update_stats(self, provider, kwh, eur):
        """Creates or updates the provider frames in the right sidebar."""
        def _ui_action():
            import customtkinter as ctk
            if provider not in self.stats_labels:
                # Create the UI box for a new provider on the fly
                frame = ctk.CTkFrame(self.stats_scroll, corner_radius=8)
                frame.pack(fill="x", padx=5, pady=4)
                ctk.CTkLabel(frame, text=f"🔌 {provider}", font=("Arial", 13, "bold")).pack()
                
                k_lbl = ctk.CTkLabel(frame, text="0 kWh", font=("Arial", 11))
                k_lbl.pack()
                a_lbl = ctk.CTkLabel(frame, text="0.0000 €/kWh", font=("Arial", 11, "bold"), text_color="#46F71A")
                a_lbl.pack()
                
                self.stats_labels[provider] = {"k_lbl": k_lbl, "a_lbl": a_lbl, "kwh": 0.0, "eur": 0.0}

            # Update the values
            d = self.stats_labels[provider]
            d["kwh"] += kwh
            d["eur"] += eur
            avg = d["eur"] / d["kwh"] if d["kwh"] > 0 else 0
            
            d["k_lbl"].configure(text=f"Total: {d['kwh']:,.0f} kWh")
            d["a_lbl"].configure(text=f"Avg: {avg:.4f} €/kWh")

        self.root.after(0, _ui_action)

