"""
CLI entrypoint to run the Bandcamp release dashboard generator and server.
"""

from __future__ import annotations

import argparse
import time
import sys
import webbrowser

from server import start_server_thread

SERVER_PORT = 5050


def launch_dashboard(server_port: int, *, launch_browser: bool = True):
    """
    Start the server and open the static dashboard, which will load releases from the server.
    """
    if launch_browser:
        webbrowser.open_new_tab(f"http://localhost:{server_port}/dashboard")
    return None


def main():
    parser = argparse.ArgumentParser(description="Run the bcfeed local server and open the dashboard.")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Preferred port for the local server.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the dashboard in a browser.")
    args = parser.parse_args()

    server_instance, server_thread, server_port = start_server_thread(args.port)
    launch_dashboard(server_port, launch_browser=not args.no_browser)

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Launching bcfeed...")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("")
    print(f"Server port: {server_port}")
    print("Dashboard is available at: http://localhost:{port}/dashboard".format(port=server_port))
    print("Keep this process running while using bcfeed in your browser.")
    print("Press Ctrl+C to stop.")

    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server_instance.shutdown()
        server_thread.join(timeout=1)


if __name__ == "__main__":
    main()
