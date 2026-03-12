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
_room    = ""

def do_login():
    global _cookies, _room
    # Login
    resp = session.get(LOGIN_URL, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    inp  = soup.find("input", {"name": "_token"})
    csrf = inp["value"] if inp else ""
    r2   = session.post(LOGIN_URL,
           data={"_token": csrf, "email": USERNAME, "password": PASSWORD},
           headers={"Referer": LOGIN_URL, "Origin": "https://www.ivasms.com",
                    "Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    if "logout" not in r2.text.lower():
        log.error("❌ Login failed!")
        return False
    _cookies = dict(session.cookies)
    log.info("✅ Login OK!")

    # ── Live page fetch karke JS scan karo ──
    log.info("🔍 Live page JS scan kar raha hun...")
    live = session.get(LIVE_URL, timeout=20)
    soup2 = BeautifulSoup(live.text, "html.parser")

    for script in soup2.find_all("script"):
        src = script.get("src","")
        js  = script.string or ""

        # External JS fetch karo
        if src:
            try:
                url = ("https://www.ivasms.com"+src) if src.startswith("/") else src
                js  = session.get(url, timeout=10).text
            except:
                continue

        if not js: continue

        # Socket/emit/room related lines dhundho
        for line in js.splitlines():
            l = line.strip()
            if any(k in l for k in ["socket","emit(","on(","join","room","channel","live","my_sms","send_message"]):
                log.info(f"  JS: {l[:250]}")

        # Room ya user ID nikalo
        for pat in [r'room["\s:=]+(["\'][\w]+["\'])', r'join["\s:(]+(["\'][\w]+["\'])',
                    r'channel["\s:=]+(["\'][\w]+["\'])', r'user_id\s*[:=]\s*(\d+)',
                    r'termination_id\s*[:=]\s*(\d+)']:
            m = re.search(pat, js)
            if m:
                log.info(f"  ★ FOUND: {m.group(0)}")
                _room = m.group(1).strip("'\"")

    log.info(f"  Room/ID detected: '{_room}'")
    return True

sio = socketio.Client(logger=False, engineio_logger=False,
                      reconnection=True, reconnection_attempts=0, reconnection_delay=5)

@sio.event
def connect():
    log.info("✅ Socket.IO Connected!")
    # Room join karne ki koshish
    for r in [_room, "live", "my_sms", USERNAME]:
        if r:
            sio.emit("join", r)
            sio.emit("join", {"room": r})
            log.info(f"  📤 join: {r}")

@sio.event
def disconnect():
    log.warning("⚠ Disconnected...")

IGNORE = {"send_message_test", "send_message_max_Limit"}

@sio.on("*")
def catch_all(event, data):
    if event in IGNORE:
        return
    log.info("=" * 55)
    log.info(f">>> EVENT: [{event}]")
    if isinstance(data, dict):
        for k, v in data.items():
            log.info(f"    {k} = {str(v)[:300]}")
    else:
        log.info(f"    DATA = {str(data)[:400]}")
    log.info("=" * 55)

if not do_login(): exit(1)

cookie_str = "; ".join([f"{k}={v}" for k, v in _cookies.items()])
sio.connect(SOCKETIO_URL, socketio_path="socket.io",
    headers={"Cookie": cookie_str, "Referer": LIVE_URL, "Origin": "https://www.ivasms.com"},
    transports=["websocket","polling"], wait_timeout=15)

log.info("🟢 Ab live page par SMS bhejo — event log hoga!")
sio.wait()
