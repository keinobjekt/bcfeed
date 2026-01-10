"""
Simple GUI wrapper to run the Bandcamp release dashboard generator with
date pickers and a built-in embed proxy.
"""

from __future__ import annotations

import threading
import webbrowser
import sys
from tkinter import Tk, Frame, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from server import start_server

SERVER_PORT = 5050


def find_free_port(preferred: int = 5050) -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", preferred))
            return preferred
        except OSError:
            s.bind(("", 0))
            return s.getsockname()[1]
def start_server_thread():
    port = find_free_port(SERVER_PORT)
    server, thread = start_server(port)
    return server, thread, port

def launch_dashboard(server_port: int, *, launch_browser: bool = True):
    """
    Start the server and open the static dashboard, which will load releases from the server.
    """
    if launch_browser:
        webbrowser.open_new_tab(f"http://localhost:{server_port}/dashboard")
    return None


def main():
    root = Tk()
    root.title("bcfeed")
    root.resizable(False, False)
    style = ttk.Style(root)
    style.configure("Run.TButton", padding=(8, 4))
    style.configure("Action.TButton", padding=(8, 4))

    server_thread = None
    server_instance = None
    server_port = SERVER_PORT

    # Toggle defaults and actions

    # Run / Clear credentials buttons
    actions_frame = Frame(root)
    actions_frame.grid(row=0, column=0, padx=8, pady=(8, 4), sticky="w")

    launch_btn = ttk.Button(actions_frame, text="Launch", width=14, style="Action.TButton", command=lambda: on_launch())
    launch_btn.grid(row=0, column=0, padx=(0, 6), sticky="w")

    # Status box
    status_box = ScrolledText(root, width=80, height=12, state="disabled")
    status_box.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")

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

    def _ensure_server():
        nonlocal server_thread, server_port, server_instance
        if server_thread is None or not server_thread.is_alive():
            server_instance, server_thread, server_port = start_server_thread()
        return server_port

    def on_launch():
        nonlocal server_thread, server_port
        _ensure_server()

        def worker():
            try:
                original_stdout = sys.stdout
                logger = GuiLogger(log)
                sys.stdout = logger

                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"Launching bcfeed...")
                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"")
                log(f"Server port: {server_port}")

                try:
                    launch_dashboard(server_port, launch_browser=True)
                    log("Dashboard generated.")
                    log("Keep the app running while using bcfeed in your browser. Click 'Launch' to open the dashboard again if needed.")
                    log("")
                    
                finally:
                    sys.stdout = original_stdout
            except Exception as exc:
                log(f"Error: {exc}")
                root.after(0, lambda exc=exc: messagebox.showerror("Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
            
    def on_close():
        nonlocal server_instance, server_thread
        try:
            if server_instance:
                server_instance.shutdown()
            if server_thread and server_thread.is_alive():
                server_thread.join(timeout=1)
        finally:
            root.destroy()

    # Auto-launch on start
    root.after(100, on_launch)
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
