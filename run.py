import subprocess
import threading
import sys
import os
from pathlib import Path
import logging
import webview
import yaml
import requests
import pystray
from PIL import Image

VERSION = "1.0.0"
UPDATE_URL = "https://example.com/mass-alligator/version.txt"  # placeholder

APP_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

CONFIG_PATH = APP_DIR / "config.yaml"
APP_PATH = APP_DIR / "app.py"
ICON_PATH = APP_DIR / "application attributes" / "MASS-ALLIGATOR-ICON.png"

server_proc = None


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def ensure_config():
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump({}, f)


def start_server():
    global server_proc
    if server_proc is None:
        server_proc = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", str(APP_PATH)
        ])
        logging.info("Server started")


def stop_server():
    global server_proc
    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
        server_proc.wait(timeout=10)
        logging.info("Server stopped")
    server_proc = None


def check_updates():
    try:
        r = requests.get(UPDATE_URL, timeout=3)
        if r.status_code == 200 and r.text.strip() != VERSION:
            logging.info("Update available")
    except Exception as e:
        logging.error("Update check failed: %s", e)


def show_settings(icon, item):
    os.startfile(CONFIG_PATH)


def open_window(icon, item):
    for w in webview.windows:
        w.show()
        w.bring_to_front()


def quit_app(icon, item):
    icon.visible = False
    stop_server()
    for w in webview.windows:
        w.destroy()
    icon.stop()


def create_tray():
    image = Image.open(ICON_PATH)
    menu = pystray.Menu(
        pystray.MenuItem("Open", open_window),
        pystray.MenuItem("Settings", show_settings),
        pystray.MenuItem("Quit", quit_app)
    )
    tray = pystray.Icon("mass-alligator", image, "Mass Alligator", menu)
    return tray


if __name__ == "__main__":
    ensure_config()
    start_server()
    check_updates()
    tray = create_tray()
    threading.Thread(target=tray.run, daemon=True).start()
    webview.create_window("Mass Alligator", "http://localhost:8501", width=1200, height=800)
    webview.start()
    stop_server()
