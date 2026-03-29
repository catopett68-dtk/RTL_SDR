#!/usr/bin/env python3
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import re
import time

class DMRVfoScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("DMR VFO Hunter v4.0")
        self.root.geometry("600x750")
        self.root.configure(bg="#2c3e50")

        self.scanning = False
        self.proc_rtl = None
        self.proc_dsd = None

        # --- Overskrift ---
        tk.Label(root, text="DMR BÅNDSCANNER", font=("Arial", 18, "bold"), bg="#2c3e50", fg="#ecf0f1").pack(pady=10)

        # --- Innstillingsramme ---
        settings_frame = tk.LabelFrame(root, text=" Konfigurasjon ", bg="#2c3e50", fg="#bdc3c7", padx=10, pady=10)
        settings_frame.pack(padx=20, fill="x")

        # Frekvens-felt
        tk.Label(settings_frame, text="Fra (MHz):", bg="#2c3e50", fg="#ecf0f1").grid(row=0, column=0, sticky="w")
        self.freq_start = tk.Entry(settings_frame, font=("Courier", 12), width=10)
        self.freq_start.insert(0, "438.000")
        self.freq_start.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(settings_frame, text="Til (MHz):", bg="#2c3e50", fg="#ecf0f1").grid(row=0, column=2, sticky="w", padx=10)
        self.freq_end = tk.Entry(settings_frame, font=("Courier", 12), width=10)
        self.freq_end.insert(0, "439.000")
        self.freq_end.grid(row=0, column=3, padx=5, pady=5)

        # --- USB Device Rullgardin (Dropdown) ---
        tk.Label(settings_frame, text="Velg USB Enhet:", bg="#2c3e50", fg="#ecf0f1").grid(row=1, column=0, sticky="w")

        self.device_options = ["0", "1", "2", "3"] # Standardvalg
        self.selected_device = tk.StringVar(root)
        self.selected_device.set("1") # Setter Device 1 som standard for deg

        self.device_menu = tk.OptionMenu(settings_frame, self.selected_device, *self.device_options)
        self.device_menu.config(width=5, bg="#34495e", fg="white", highlightthickness=0)
        self.device_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # --- Kontrollknapper ---
        btn_frame = tk.Frame(root, bg="#2c3e50")
        btn_frame.pack(pady=15)

        self.audio_btn = tk.Button(btn_frame, text="SETT OPP LYD", command=self.setup_audio, bg="#34495e", fg="white", width=12)
        self.audio_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = tk.Button(btn_frame, text="START SCAN", command=self.toggle_scan, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), width=12)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(btn_frame, text="TØM LOGG", command=lambda: self.log_area.delete('1.0', tk.END), bg="#7f8c8d", fg="white")
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # --- Sanntids Display ---
        self.freq_display = tk.Label(root, text="---.--- MHz", font=("Courier", 28, "bold"), bg="#1a1a1a", fg="#3498db")
        self.freq_display.pack(pady=10, padx=20, fill="x")

        # --- Tale-Logg ---
        self.log_area = scrolledtext.ScrolledText(root, height=12, bg="#1a1a1a", fg="#2ecc71", font=("Courier New", 10))
        self.log_area.pack(padx=20, pady=10, fill="both", expand=True)

        self.status_var = tk.StringVar(value="Klar")
        tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor="w", bg="#34495e", fg="#bdc3c7").pack(side=tk.BOTTOM, fill="x")

    def setup_audio(self):
        subprocess.run(["sudo", "modprobe", "snd-aloop"], stderr=subprocess.DEVNULL)
        self.status_var.set("Lydmodul forsøkt aktivert")

    def toggle_scan(self):
        if not self.scanning:
            self.scanning = True
            self.start_btn.config(text="STOPP", bg="#e74c3c")
            threading.Thread(target=self.vfo_logic, daemon=True).start()
        else:
            self.scanning = False
            self.stop_all()
            self.start_btn.config(text="START SCAN", bg="#27ae60")

    def stop_all(self):
        if self.proc_rtl: self.proc_rtl.terminate()
        if self.proc_dsd: self.proc_dsd.terminate()

    def vfo_logic(self):
        try:
            start = float(self.freq_start.get())
            end = float(self.freq_end.get())
            dev = self.selected_device.get() # Henter valget fra rullgardinen
            curr = start

            while self.scanning:
                if curr > end: curr = start

                self.freq_display.config(text=f"{curr:.4f}")
                self.status_var.set(f"Skanner på Device {dev}...")

                # Start RTL og DSD
                rtl_cmd = ["rtl_fm", "-d", dev, "-f", f"{curr}M", "-s", "60k", "-g", "45", "-l", "0"]
                dsd_cmd = ["dsd", "-i", "-", "-o", "pa:1"]

                self.proc_rtl = subprocess.Popen(rtl_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.proc_dsd = subprocess.Popen(dsd_cmd, stdin=self.proc_rtl.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                start_time = time.time()
                found_voice = False

                # Sjekk frekvensen i 3 sekunder
                while time.time() - start_time < 3:
                    if not self.scanning: break
                    line = self.proc_dsd.stdout.readline()
                    if not line: break

                    if any(x in line for x in ["Voice", "Group", "Private"]):
                        found_voice = True
                        tg = re.search(r'TG=(\d+)', line)
                        cc = re.search(r'CC=(\d+)', line)
                        t_val = tg.group(1) if tg else "?"
                        c_val = cc.group(1) if cc else "?"

                        self.log_area.insert(tk.END, f"[TALE] {curr:.4f} MHz | TG:{t_val} | CC:{c_val}\n")
                        self.log_area.see(tk.END)
                        start_time = time.time() # Nullstill timer ved tale

                self.stop_all()
                if not found_voice:
                    curr += 0.0125

        except Exception as e:
            print(f"Feil: {e}")
            self.scanning = False

if __name__ == "__main__":
    root = tk.Tk()
    app = DMRVfoScanner(root)
    root.mainloop()
