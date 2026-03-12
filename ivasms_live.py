import time, logging, re, os
from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests
import socketio

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger(__name__)

USERNAME     = os.getenv("IVASMS_USER", "powerxdeveloper@gmail.com")
PASSWORD     = os.getenv("IVASMS_PASS", "Khang1.com")
LOGIN_URL    = "https://www.ivasms.com/login"
LIVE_URL     = "https://www.ivasms.com/portal/live/my_sms"
SOCKETIO_URL = "https://www.ivasms.com:2087"

session  = cf_requests.Session(impersonate="chrome120")
_cookies = {}

def do_login():
    global _cookies
    resp = session.get(LOGIN_URL, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    inp  = soup.find("input", {"name": "_token"})
    csrf = inp["value"] if inp else ""
    r2   = session.post(LOGIN_URL,
           data={"_token": csrf, "email": USERNAME, "password": PASSWORD},
           headers={"Referer": LOGIN_URL, "Origin": "https://www.ivasms.com",
                    "Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    if "logout" in r2.text.lower() or "dashboard" in r2.text.lower():
        _cookies = dict(session.cookies)
        log.info("✅ Login OK!")
        return True
    log.error("❌ Login failed!")
    return False

sio = socketio.Client(logger=False, engineio_logger=False,
                      reconnection=True, reconnection_attempts=0, reconnection_delay=5)

@sio.event
def connect():
    log.info("✅ Connected! Ab SMS bhejo — event pakad lega")

@sio.event
def disconnect():
    log.warning("⚠ Disconnected...")

# ── HAR EK EVENT PAKDO ──
@sio.on("*")
def catch_all(event, data):
    log.info("=" * 60)
    log.info(f">>> EVENT: {event}")
    if isinstance(data, dict):
        for k, v in data.items():
            log.info(f"    {k} = {str(v)[:300]}")
    else:
        log.info(f"    DATA = {str(data)[:500]}")
    log.info("=" * 60)

if not do_login(): exit(1)

cookie_str = "; ".join([f"{k}={v}" for k, v in _cookies.items()])

sio.connect(SOCKETIO_URL, socketio_path="socket.io",
    headers={"Cookie": cookie_str, "Referer": LIVE_URL, "Origin": "https://www.ivasms.com"},
    transports=["websocket","polling"], wait_timeout=15)

log.info("🟢 Waiting — SMS bhejo aur log dekho!")
sio.wait()
