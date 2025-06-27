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

# Base directory where config and logs are stored
BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

# Directory with bundled resources (when packaged by PyInstaller)
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

CONFIG_PATH = BASE_DIR / "config.yaml"
APP_PATH = RESOURCE_DIR / "app.py"
ICON_PATH = RESOURCE_DIR / "application attributes" / "MASS-ALLIGATOR-ICON.png"

SERVER_FLAG = "--server"

server_proc = None

if SERVER_FLAG in sys.argv:
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", str(APP_PATH), "--server.headless", "true"]
    stcli.main()
    sys.exit()


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
        cmd = [sys.executable, sys.argv[0], SERVER_FLAG]
        server_proc = subprocess.Popen(cmd, cwd=str(BASE_DIR))
        logging.info("Server started")


def stop_server():
    global server_proc
    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except Exception:
            server_proc.kill()
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
    try:
        if os.name == "nt":
            os.startfile(CONFIG_PATH)
        else:
            import webbrowser
            if not webbrowser.open(CONFIG_PATH.as_uri()):
                subprocess.Popen(["xdg-open", str(CONFIG_PATH)])
    except Exception as e:
        logging.error("Failed to open config: %s", e)


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


def load_icon():
    if ICON_PATH.exists():
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass
    ico_fallback = RESOURCE_DIR / "application attributes" / "MASS-ALLIGATOR-ICON.ico"
    if ico_fallback.exists():
        try:
            return Image.open(ico_fallback)
        except Exception:
            pass
    return Image.new("RGBA", (64, 64), "white")


def create_tray():
    image = load_icon()

    def running():
        return server_proc and server_proc.poll() is None

    menu = pystray.Menu(
        pystray.MenuItem("Open", open_window),
        pystray.MenuItem(
            "Start server",
            lambda icon, item: start_server(),
            enabled=lambda item: not running(),
        ),
        pystray.MenuItem(
            "Stop server",
            lambda icon, item: stop_server(),
            enabled=lambda item: running(),
        ),
        pystray.MenuItem("Settings", show_settings),
        pystray.MenuItem("Quit", quit_app),
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
