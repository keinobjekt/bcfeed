"""
Simple GUI wrapper to run the Bandcamp release dashboard generator with
date pickers and a built-in embed proxy.
"""

from __future__ import annotations

import argparse
import datetime
import threading
import webbrowser
import sys
import json
import shutil
from pathlib import Path
from tkinter import Tk, StringVar, IntVar, Button, Label, Entry, Frame, messagebox, filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from embed_proxy import app as proxy_app, start_proxy_server
from pipeline import gather_releases_with_cache
from dashboard import write_release_dashboard
from util import get_data_dir
from session_store import get_full_release_cache

MULTITHREADING = True
PROXY_PORT = 5050
DATA_DIR = get_data_dir()
SETTINGS_PATH = DATA_DIR / "gui_settings.json"
CREDENTIALS_PATH = DATA_DIR / "credentials.json"
TOKEN_PATH = DATA_DIR / "token.pickle"


def find_free_port(preferred: int = 5050) -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", preferred))
            return preferred
        except OSError:
            s.bind(("", 0))
            return s.getsockname()[1]
MAX_RESULTS_HARD = 2000
OUTPUT_DIR = Path("output")


def load_settings():
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_credentials() -> bool:
    """
    Ensure credentials.json is present in the data directory.
    If missing and prompt_on_missing is True, ask the user to locate it.
    """
    has_credentials = CREDENTIALS_PATH.exists()

    path = filedialog.askopenfilename(
        title="Load client_secret_XXXXXXXX.json",
        filetypes=[("JSON files", "*.json")],
    )
    if not path and not has_credentials:
        messagebox.showwarning("Credentials required", "No credentials file selected. Gmail will not work until you load it.")
        return False
    if path:
        try:
            # Remove any existing credentials/token so we always replace with the selected file
            shutil.copy(Path(path), CREDENTIALS_PATH)
            messagebox.showinfo("Loaded", "Credentials loaded.")
            if TOKEN_PATH.exists():
                TOKEN_PATH.unlink()
            return True
        except Exception as exc:
            messagebox.showerror("Error loading credentials", str(exc))
            return False


def save_settings(settings: dict):
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)


def reload_credentials():
    load_credentials()


def start_proxy_thread():
    port = find_free_port(PROXY_PORT)
    server, thread = start_proxy_server(port)
    return server, thread, port

def launch_from_cache(proxy_port: int, preload_embeds: bool, *, log=print, launch_browser: bool = True):
    """
    Generate dashboard from all cached releases (no Gmail fetch).
    """
    output_path = DATA_DIR / "output.html"
    releases = get_full_release_cache()
    if not releases:
        log("No cached releases found.")
    output_file = write_release_dashboard(
        releases=releases,
        output_path=output_path,
        title="bcfeed",
        fetch_missing_ids=preload_embeds,
        embed_proxy_url=f"http://localhost:{proxy_port}/embed-meta",
        log=log,
    )
    if launch_browser:
        webbrowser.open_new_tab(output_file.resolve().as_uri())
    return output_file


def main():
    root = Tk()
    root.title("bcfeed")
    root.resizable(False, False)
    style = ttk.Style(root)
    style.configure("Run.TButton", padding=(8, 4))
    style.configure("Action.TButton", padding=(8, 4))

    today = datetime.date.today()
    two_months_ago = today - datetime.timedelta(days=60)
    settings = load_settings()

    start_date_var = StringVar(value=settings.get("start_date") or two_months_ago.strftime("%Y/%m/%d"))
    end_date_var = StringVar(value=settings.get("end_date") or today.strftime("%Y/%m/%d"))

    # Custom layout for date rows to fit compact buttons around the entry
    date_button_sets = []
    date_frame = Frame(root)
    date_frame.grid(row=0, column=0, columnspan=3, padx=6, pady=4, sticky="w")
    for col in range(1, 8):
        date_frame.grid_columnconfigure(col, minsize=34)

    def layout_date_row(label_text: str, var: StringVar, row: int, is_start: bool):
        left_configs = [("<1m", -30), ("<1w", -7), ("<1d", -1)]
        right_configs = [(">1d", 1), (">1w", 7), (">1m", 30)]

        Label(date_frame, text=label_text).grid(row=row, column=0, padx=4, sticky="w")

        def make_btn(col: int, label: str, days: int):
            delta = datetime.timedelta(days=days)
            btn = Button(
                date_frame,
                text=label,
                width=0,  # let the text size drive width
                padx=1,
                pady=0,
                font=("TkDefaultFont", 8),
                command=lambda v=var, d=delta: adjust_date(v, is_start, d) if days !=0 else v.set(today.strftime("%Y/%m/%d")),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="w")
            date_button_sets.append((btn, delta, is_start))

        col = 1
        for label, days in left_configs:
            make_btn(col, label, days)
            col += 1

        Entry(date_frame, textvariable=var, width=12).grid(row=row, column=4, padx=4, pady=2, sticky="w")
        col = 5
        for label, days in right_configs:
            make_btn(col, label, days)
            col += 1
        if is_start:
            btn = Button(
                date_frame,
                text="Same as end",
                width=12,
                padx=1,
                pady=0,
                font=("TkDefaultFont", 8),
                command=lambda: var.set(end_date_var.get()),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="w")
            date_button_sets.append((btn, datetime.timedelta(days=0), is_start))
        else:
            btn = Button(
                date_frame,
                text="Same as start",
                width=12,
                padx=1,
                pady=0,
                font=("TkDefaultFont", 8),
                command=lambda: var.set(start_date_var.get()),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="w")
            date_button_sets.append((btn, datetime.timedelta(days=0), is_start))

    def parse_date_var(var: StringVar, fallback: datetime.date) -> datetime.date:
        try:
            return datetime.datetime.strptime(var.get(), "%Y/%m/%d").date()
        except Exception:
            return fallback

    def can_adjust(is_start: bool, delta: datetime.timedelta) -> bool:
        start_dt = parse_date_var(start_date_var, two_months_ago)
        end_dt = parse_date_var(end_date_var, today)
        new_start = start_dt + delta if is_start else start_dt
        new_end = end_dt + delta if not is_start else end_dt
        if new_start > new_end:
            return False
        if new_start > today or new_end > today:
            return False
        return True

    def adjust_date(var: StringVar, is_start: bool, delta: datetime.timedelta):
        if not can_adjust(is_start, delta):
            return
        current = parse_date_var(var, today if is_start else two_months_ago)
        new_date = current + delta
        if new_date > today:
            new_date = today
        var.set(new_date.strftime("%Y/%m/%d"))

    layout_date_row("Start date (YYYY/MM/DD)", start_date_var, 0, True)
    layout_date_row("End date (YYYY/MM/DD)", end_date_var, 1, False)

    def parse_date_var(var: StringVar, fallback: datetime.date) -> datetime.date:
        try:
            return datetime.datetime.strptime(var.get(), "%Y/%m/%d").date()
        except Exception:
            return fallback

    def can_adjust(is_start: bool, delta: datetime.timedelta) -> bool:
        start_dt = parse_date_var(start_date_var, two_months_ago)
        end_dt = parse_date_var(end_date_var, today)
        new_start = start_dt + delta if is_start else start_dt
        new_end = end_dt + delta if not is_start else end_dt
        if new_start > new_end:
            return False
        if new_start > today or new_end > today:
            return False
        return True

    def adjust_date(var: StringVar, is_start: bool, delta: datetime.timedelta):
        if not can_adjust(is_start, delta):
            return
        current = parse_date_var(var, today if is_start else two_months_ago)
        new_date = current + delta
        # clamp to today
        if new_date > today:
            new_date = today
        var.set(new_date.strftime("%Y/%m/%d"))

    def refresh_date_buttons(*_):
        for btn, delta, is_start in date_button_sets:
            btn_state = "normal" if can_adjust(is_start, delta) else "disabled"
            btn.config(state=btn_state)

    start_date_var.trace_add("write", refresh_date_buttons)
    end_date_var.trace_add("write", refresh_date_buttons)
    refresh_date_buttons()

    proxy_thread = None
    proxy_server = None
    proxy_port = PROXY_PORT
    def save_current_settings(*_args):
        save_settings(
            {
                "start_date": start_date_var.get(),
                "end_date": end_date_var.get(),
                "preload_embeds": bool(preload_embeds_var.get())
            }
        )

    # Toggle defaults and actions
    # (Preload Bandcamp players option moved to browser UI)

    # Run / Reload credentials buttons
    actions_frame = Frame(root)
    actions_frame.grid(row=4, column=0, columnspan=3, padx=8, pady=6, sticky="e")

    download_btn = ttk.Button(actions_frame, text="Download", width=14, style="Action.TButton", command=lambda: on_download())
    download_btn.grid(row=0, column=0, padx=(0, 6), sticky="e")

    launch_btn = ttk.Button(actions_frame, text="Launch", width=14, style="Action.TButton", command=lambda: on_launch())
    launch_btn.grid(row=1, column=0, padx=(0, 6), pady=(4, 0), sticky="e")

    reload_credentials_btn = ttk.Button(actions_frame, text="Reload credentials", width=14, style="Action.TButton", command=reload_credentials)
    reload_credentials_btn.grid(row=1, column=1, pady=(4, 0), sticky="e")

    # Status box
    status_box = ScrolledText(root, width=80, height=12, state="disabled")
    status_box.grid(row=5, column=0, columnspan=3, padx=8, pady=8, sticky="nsew")

    class GuiLogger:
        def __init__(self, callback):
            self.callback = callback

        def write(self, msg):
            if msg.strip():
                self.callback(msg.rstrip())

        def flush(self):
            pass

    def append_log(msg):
        if isinstance(msg, bytes):
            try:
                msg = msg.decode("utf-8", errors="replace")
            except Exception:
                msg = str(msg)
        else:
            msg = str(msg)
        status_box.configure(state="normal")
        status_box.insert("end", msg + "\n")
        status_box.see("end")
        status_box.configure(state="disabled")

    def log(msg: str):
        # marshal to UI thread
        root.after(0, append_log, msg)

    def _ensure_proxy():
        nonlocal proxy_thread, proxy_port
        if proxy_thread is None or not proxy_thread.is_alive():
            proxy_server, proxy_thread, proxy_port = start_proxy_thread()
        return proxy_port

    # Persist settings whenever inputs change
    for var in (start_date_var, end_date_var):
        var.trace_add("write", save_current_settings)

    def _validate_inputs():
        max_results = MAX_RESULTS_HARD
        try:
            # validate dates
            for val in (start_date_var.get(), end_date_var.get()):
                datetime.datetime.strptime(val, "%Y/%m/%d")
        except ValueError:
            messagebox.showerror("Error", "Dates must be in YYYY/MM/DD format")
            return None
        return max_results

    def on_download():
        nonlocal proxy_thread, proxy_port
        max_results = _validate_inputs()
        if max_results is None:
            return

        should_preload = False  # no embed preloads on download-only
        _ensure_proxy()

        def worker():
            try:
                original_stdout = sys.stdout
                logger = GuiLogger(log)
                sys.stdout = logger
                
                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"Starting cache refresh...")
                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"")
                log(f"Running query from {start_date_var.get()} to {end_date_var.get()} with max {max_results} (proxy port {proxy_port}, preload {'on' if should_preload else 'off'})")
                
                try:
                    gather_releases_with_cache(start_date_var.get(), end_date_var.get(), max_results, batch_size=20, cache_only=False, log=log)
                    log("Download complete; cache updated.")
                    log("")
                    root.after(0, lambda: messagebox.showinfo("Done", "Download complete; cache updated."))
                finally:
                    sys.stdout = original_stdout
            except Exception as exc:
                log(f"Error: {exc}")
                root.after(0, lambda exc=exc: messagebox.showerror("Error", str(exc)))

        if MULTITHREADING:
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()

    def on_launch():
        nonlocal proxy_thread, proxy_port
        should_preload = False  # browser UI controls preload behaviour for embeds
        _ensure_proxy()

        def worker():
            try:
                original_stdout = sys.stdout
                logger = GuiLogger(log)
                sys.stdout = logger

                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"Launching dashboard from cache...")
                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"")
                log(f"Building page from cached releases (proxy port {proxy_port}, preload {'on' if should_preload else 'off'})")

                try:
                    launch_from_cache(proxy_port, should_preload, log=log, launch_browser=True)
                    log("Dashboard generated from cache and opened in browser.")
                    log("")
                    root.after(0, lambda: messagebox.showinfo("Done", "Dashboard generated from cache and opened in browser."))
                finally:
                    sys.stdout = original_stdout
            except Exception as exc:
                log(f"Error: {exc}")
                root.after(0, lambda exc=exc: messagebox.showerror("Error", str(exc)))

        if MULTITHREADING:
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()
            
    from tkinter import Checkbutton  # localized import to avoid polluting top
    def on_close():
        nonlocal proxy_server, proxy_thread
        try:
            if proxy_server:
                proxy_server.shutdown()
            if proxy_thread and proxy_thread.is_alive():
                proxy_thread.join(timeout=1)
        finally:
            root.destroy()

    if not CREDENTIALS_PATH.exists():
        # Prompt for credentials on first launch if missing
        root.after(50, lambda: load_credentials())

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
