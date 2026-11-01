"""
Urban Cascade Simulator — Quick Start Runner
Run this single file to launch both the API server and the Tkinter GUI.
"""

import os
import sys
import threading
import subprocess
import time

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def run_api_server():
    """Start the Flask API server in a background thread."""
    from api_server import app
    print("\n🌐 Starting API server at http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


def run_gui():
    """Start the Tkinter GUI (must run on main thread)."""
    from gui_app import main
    print("🖥  Starting Tkinter GUI...\n")
    main()


if __name__ == "__main__":
    print("=" * 60)
    print("  ⚡ URBAN CASCADE SIMULATOR — Backend Launcher")
    print("  Team Arc Reactors | G H Raisoni Skilltech University")
    print("=" * 60)

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "api":
            print("\nMode: API Server Only")
            run_api_server()
        elif mode == "gui":
            print("\nMode: GUI Only")
            run_gui()
        elif mode == "both":
            print("\nMode: API + GUI (Full Stack)")
            api_thread = threading.Thread(target=run_api_server, daemon=True)
            api_thread.start()
            time.sleep(1)
            run_gui()
        else:
            print(f"\nUnknown mode: {mode}")
            print("Usage: python run.py [api|gui|both]")
    else:
        print("\nUsage:")
        print("  python run.py gui    — Launch Tkinter desktop GUI")
        print("  python run.py api    — Launch Flask API server")
        print("  python run.py both   — Launch both GUI + API server")
        print()
        print("Starting GUI by default...")
        print()
        run_gui()
