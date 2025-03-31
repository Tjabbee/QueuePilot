import os
import datetime
import io
import contextlib

import tkinter as tk
from tkinter import ttk, scrolledtext

from sites.abbostader import run_ab_bostader
from sites.hemvist import run_hemvist

# Mappa site-namn till funktioner
SITE_FUNCTIONS = {
    # AUTOSITES
    "Nynasbo": run_nynasbo,
    "Byggvesta": run_byggvesta,
    "AB Bostäder": run_ab_bostader,
    "Karlstad Bostads AB": run_kbab,
    "Örebro Bostäder": run_obo,
    "Hemvist": run_hemvist
}

# Se till att logs-mappen finns
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Filnamn baserat på dagens datum


def get_today_log_path():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{today}.log")

# Logga med tidsstämpel


def write_log(output: str):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    lines = output.strip().splitlines()
    with open(get_today_log_path(), "a", encoding="utf-8") as f:
        for line in lines:
            f.write(f"[{timestamp}] {line}\n")

        f.write("**************************************************\n")

class App:
    def __init__(self, tk_root):
        self.root = tk_root
        self.root.title("Housing Queue Auto Login")

        ttk.Label(self.root, text="Select site:").pack(pady=5)

        self.site_var = tk.StringVar()
        self.site_combo = ttk.Combobox(
            self.root, textvariable=self.site_var, values=list(SITE_FUNCTIONS.keys()))
        self.site_combo.current(0)
        self.site_combo.pack(pady=5)

        self.run_button = ttk.Button(
            self.root, text="Run Selected Site", command=self.run_selected_site)
        self.run_button.pack(pady=5)

        self.run_all_button = ttk.Button(
            self.root, text="Run All Sites", command=self.run_all_sites)
        self.run_all_button.pack(pady=5)

        self.output = scrolledtext.ScrolledText(
            self.root, width=70, height=20, state='disabled')
        self.output.pack(padx=10, pady=10)

        # Visa senaste logg vid start
        self.load_existing_log()

    def load_existing_log(self):
        log_path = get_today_log_path()
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.output.configure(state='normal')
                self.output.insert(tk.END, content + "\n")
                self.output.configure(state='disabled')
                self.output.see(tk.END)

    def run_selected_site(self):
        self.clear_output()
        site = self.site_var.get()
        func = SITE_FUNCTIONS.get(site)

        if not func:
            self.log(f"Unknown site selected: {site}")
            return

        self.log(f"▶ Running {site}...\n")
        self._run_and_log(func)

    def run_all_sites(self):
        self.clear_output()
        self.log("▶ Running all configured sites...\n")
        for site, func in SITE_FUNCTIONS.items():
            self.log(f"\n--- {site} ---")
            self._run_and_log(func)

    def _run_and_log(self, func):
        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
            func()
            output = buf.getvalue()

        self.log(output)
        write_log(output)

    def log(self, text):
        self.output.configure(state='normal')
        self.output.insert(tk.END, text + "\n")
        self.output.configure(state='disabled')
        self.output.see(tk.END)

    def clear_output(self):
        self.output.configure(state='normal')
        self.output.delete("1.0", tk.END)
        self.output.configure(state='disabled')


if __name__ == "__main__":
    tk_root = tk.Tk()
    app = App(tk_root)
    tk_root.mainloop()
