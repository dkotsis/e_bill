# -*- coding: utf-8 -*-
"""
=============================================================================
Project:        Electricity Bill Importer PRO
File:           src/gui.py
=============================================================================
"""

import sys
import threading
import io
import os
from PIL import Image

import customtkinter as ctk
from tkinter import filedialog

from src.classes import GuiBridge

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_run_processing_fn = None

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def print_branding_header(textbox: ctk.CTkTextbox) -> None:
    logo = """
    =================================================================================
    #   #    ######  ###   ######  #### #    #  #######  ######        #####      #    
    #   #   #     #   #      #      #   #   #   #     #  #     #      #     #    # #   
    #  #    #     #   #      #      #   #  #    #     #  #            #         #   #  
    ###     ######    #      #      #   ###     #     #   #####        #####   #     # 
    #  #    #   #     #      #      #   #  #    #     #        #            #  ####### 
    #   #   #    #    #      #      #   #   #   #     #  #     #      #     #  #     # 
    #    #  #     #  ###     #     ###  #    #  #######   #####        #####   #     # 
                                                                                    
    ANEDIK KRITIKOS SA - ENERGY SECTOR             
    ==================================================================================
    """
    notice = (
        "🔒 PROPRIETARY MANAGEMENT SYSTEMS\n"
        "Version 4.3.0 | Production Release (2026)\n"
        "Designed by: D. T. Kotsis (d.kotsis@anedik.com.gr)\n"
        "Notice: Unauthorized copying or distribution is strictly prohibited.\n"
        "--------------------------------------------------------------------\n\n"
    )
    textbox.insert("end", logo, "info")
    textbox.insert("end", notice, "weak")
    textbox.see("end")

def set_processing_function(fn) -> None:
    global _run_processing_fn
    _run_processing_fn = fn

def start_gui(config: dict) -> None:
    root = ctk.CTk()
    root.title(config.get("APP_TITLE", "Electricity Bill Importer PRO v4.3"))

    w, h = 1400, 960
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    path_var = ctk.StringVar()
    dry_run_var = ctk.BooleanVar(value=True)

    report_per_bill = ctk.BooleanVar(value=True)
    report_file_summary = ctk.BooleanVar(value=True)
    report_final_summary = ctk.BooleanVar(value=True)
    report_anomalies = ctk.BooleanVar(value=True)
    report_historical = ctk.BooleanVar(value=True)
    
    stop_flag = {"value": False}

    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # Header section with cropped spiral logo icon
    header = ctk.CTkFrame(root)
    header.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
    
    title_container = ctk.CTkFrame(header, fg_color="transparent")
    title_container.pack(side="left", padx=10)
    
    ctk.CTkLabel(title_container, text="Electricity Bill Importer PRO", 
                 font=ctk.CTkFont(size=26, weight="bold")).pack(side="left")

    try:
        img_source = "image_f3c9d0.png" if os.path.exists("image_f3c9d0.png") else "image_f2e4b3.png"
        if os.path.exists(img_source):
            full_img = Image.open(img_source)
            logo_box = (282, 40, 318, 76) 
            cropped_logo = full_img.crop(logo_box)
            ctk_logo = ctk.CTkImage(light_image=cropped_logo, dark_image=cropped_logo, size=(32, 32))
            
            logo_label = ctk.CTkLabel(title_container, image=ctk_logo, text="")
            logo_label.pack(side="left", padx=(12, 0))
    except Exception:
        pass

    ctk.CTkButton(header, text="🌗 Mode", width=80, command=lambda: ctk.set_appearance_mode("light" if ctk.get_appearance_mode()=="Dark" else "dark")).pack(side="right", padx=10)

    # Path frame
    path_frame = ctk.CTkFrame(root)
    path_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
    ctk.CTkEntry(path_frame, textvariable=path_var, height=40).pack(fill="x", padx=10, pady=5)
    
    btns_sub = ctk.CTkFrame(path_frame, fg_color="transparent")
    btns_sub.pack(pady=5)
    ctk.CTkButton(btns_sub, text="📄 Single Excel File", width=190, command=lambda: path_var.set(filedialog.askopenfilename())).pack(side="left", padx=10)
    ctk.CTkButton(btns_sub, text="📁 Folder with Excel files", width=190, command=lambda: path_var.set(filedialog.askdirectory())).pack(side="left", padx=10)
    
    chk_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
    chk_frame.pack(fill="x", padx=15, pady=5)
    
    ctk.CTkCheckBox(chk_frame, text="Dry Run (Simulation)", variable=dry_run_var).pack(side="left", padx=10)
    ctk.CTkCheckBox(chk_frame, text="Log Per Bill", variable=report_per_bill).pack(side="left", padx=10)
    ctk.CTkCheckBox(chk_frame, text="File Summaries", variable=report_file_summary).pack(side="left", padx=10)
    ctk.CTkCheckBox(chk_frame, text="Final Summary", variable=report_final_summary).pack(side="left", padx=10)
    ctk.CTkCheckBox(chk_frame, text="Price Anomalies Detection", variable=report_anomalies).pack(side="left", padx=10)
    ctk.CTkCheckBox(chk_frame, text="Historical Baseline Analysis", variable=report_historical).pack(side="left", padx=10)

    # Dashboard progress variables
    progress_frame = ctk.CTkFrame(root)
    progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
    status_label = ctk.CTkLabel(progress_frame, text="Ready", font=ctk.CTkFont(size=14))
    status_label.pack()
    
    file_progress_label = ctk.CTkLabel(progress_frame, text="📁 File Progress: 0/0", font=ctk.CTkFont(size=12))
    file_progress_label.pack(anchor="w", padx=15, pady=(10, 2))
    file_progress = ctk.CTkProgressBar(progress_frame, height=20, mode="determinate")
    file_progress.pack(fill="x", padx=15, pady=(0, 5))
    file_progress.set(0.0)
    
    invoice_progress_label = ctk.CTkLabel(progress_frame, text="📄 Invoice Progress: 0/0", font=ctk.CTkFont(size=12))
    invoice_progress_label.pack(anchor="w", padx=15, pady=(5, 2))
    page_progress = ctk.CTkProgressBar(progress_frame, height=20, progress_color="#ffaa00", mode="determinate")
    page_progress.pack(fill="x", padx=15, pady=(0, 5))
    page_progress.set(0.0)

    main_area = ctk.CTkFrame(root, fg_color="transparent")
    main_area.grid(row=3, column=0, sticky="nsew", padx=20, pady=5)
    main_area.grid_columnconfigure(0, weight=4) 
    main_area.grid_columnconfigure(1, weight=1) 
    main_area.grid_rowconfigure(0, weight=1)

    console = ctk.CTkTextbox(main_area, font=ctk.CTkFont(family="Consolas", size=13))
    console.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    console.tag_config("ok", foreground="#00E676")
    console.tag_config("skip", foreground="#1DC4EE")
    console.tag_config("anomaly", foreground="#AFAF1C")
    console.tag_config("double", foreground="#f3f04e")
    console.tag_config("warn", foreground="#ffaa00")
    console.tag_config("info", foreground="#b69be9")
    console.tag_config("error", foreground="#ff4444")
    console.tag_config("critical", foreground="#FF1744")
    console.tag_config("high", foreground="#FF9100")
    console.tag_config("weak", foreground="#B0BEC5")

    print_branding_header(console)
    
    stats_frame = ctk.CTkFrame(main_area)
    stats_frame.grid(row=0, column=1, sticky="nsew")
    ctk.CTkLabel(stats_frame, text="📊 Live Statistics", font=ctk.CTkFont(size=23, weight="bold")).pack(pady=(10, 10))

    stats_scroll = ctk.CTkScrollableFrame(stats_frame, fg_color="transparent")
    stats_scroll.pack(fill="both", expand=True, padx=5, pady=0)

    btn_frame = ctk.CTkFrame(root)
    btn_frame.grid(row=4, column=0, pady=20)

    pause_event = threading.Event()
    pause_event.set()

    def launch():
        path = path_var.get()
        if not path: 
            return

        btn_start.configure(state="disabled", fg_color="#555555", text="⚡ PROCESSING...")
        btn_stop.configure(state="normal", text="⏸ PAUSE PROCESSING", fg_color="#D32F2F")
        status_label.configure(text="STATUS: PROCESSING...", text_color="#00bb77")
        
        file_progress.set(0.0)
        page_progress.set(0.0)

        console.configure(state="normal")
        console.delete("1.0", "end")
        
        for widget in stats_scroll.winfo_children():
            widget.destroy()

        print_branding_header(console)

        bridge = GuiBridge(
            console, file_progress, page_progress, status_label, root,
            stats_scroll, file_progress_label, invoice_progress_label
        )
        bridge.console = console  # Link console explicitly to bridge for safe thread logs
        bridge.btn_start = btn_start
        bridge.btn_stop = btn_stop
        bridge.status_label = status_label
        
        root.active_bridge = bridge
        
        settings = {
            "dry_run": dry_run_var.get(),
            "config": config,
            "reports": {
                "per_bill": report_per_bill.get(),
                "file_summary": report_file_summary.get(),
                "final": report_final_summary.get(),
                "anomalies": report_anomalies.get(),
                "historical": report_historical.get()
            }
        }

        pause_event.set()
        stop_flag["value"] = False

        if _run_processing_fn:
            _run_processing_fn(path, bridge, settings, pause_event)

    def toggle_pause():
        if pause_event.is_set():
            pause_event.clear()
            status_label.configure(text="STATUS: PAUSED", text_color="#ffaa00")
            btn_stop.configure(text="▶ RESUME PROCESSING", fg_color="#00bb77")
        else:
            pause_event.set()
            status_label.configure(text="STATUS: PROCESSING...", text_color="#00bb77")
            btn_stop.configure(text="⏸ PAUSE PROCESSING", fg_color="#D32F2F")

    # Start button initializes as disabled
    btn_start = ctk.CTkButton(btn_frame, text="▶ START PROCESSING", fg_color="#555555", state="disabled", height=55,
                  font=ctk.CTkFont(size=15, weight="bold"), command=launch)
    btn_start.grid(row=0, column=0, padx=15)

    btn_stop = ctk.CTkButton(btn_frame, text="⏸ PAUSE PROCESSING", fg_color="#555555", height=55,
                 font=ctk.CTkFont(size=15, weight="bold"), state="disabled", command=toggle_pause)
    btn_stop.grid(row=0, column=1, padx=15)

    # Variable listener trace to toggle START PROCESSING conditionally
    def on_path_changed(*args):
        if path_var.get().strip():
            btn_start.configure(state="normal", fg_color="#00bb77")
        else:
            btn_start.configure(state="disabled", fg_color="#555555")

    path_var.trace_add("write", on_path_changed)

    root.mainloop()