import time, logging, re, os
from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests
import socketio

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

USERNAME         = os.getenv("IVASMS_USER", "powerxdeveloper@gmail.com")
PASSWORD         = os.getenv("IVASMS_PASS", "Khang1.com")
TELEGRAM_TOKEN   = os.getenv("TG_TOKEN",    "8784790380:AAGX5vI90BLUnSGATdhzVuH9YeBqBGEveWs")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID",  "-1003886766454")
LOGIN_URL        = "https://www.ivasms.com/login"
LIVE_URL         = "https://www.ivasms.com/portal/live/my_sms"
SOCKETIO_URL     = "https://www.ivasms.com:2087"

session  = cf_requests.Session(impersonate="chrome120")
_cookies = {}
seen     = set()

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

def extract_otp(text):
    m = re.search(r'\b(\d{3}[-\s]\d{3})\b', text)
    if m: return m.group(1)
    m = re.search(r'\bG-(\d{4,8})\b', text)
    if m: return "G-" + m.group(1)
    m = re.search(r'(?:code|otp|pin|verif|confirm|passcode|token|kod|رمز|كود)[^0-9]{0,20}(\d{4,8})', text, re.IGNORECASE)
    if m: return m.group(1)
    m = re.search(r'[:=]\s*(\d{4,8})\b', text)
    if m: return m.group(1)
    m = re.search(r'#(\d{4,8})\b', text)
    if m: return m.group(1)
    for x in re.findall(r'\b(\d{4,8})\b', text):
        if not re.match(r'^(19|20)\d{2}$', x): return x
    return None

FLAGS = {
    "af":"🇦🇫","al":"🇦🇱","dz":"🇩🇿","ar":"🇦🇷","am":"🇦🇲","au":"🇦🇺","at":"🇦🇹","az":"🇦🇿",
    "bh":"🇧🇭","bd":"🇧🇩","by":"🇧🇾","be":"🇧🇪","bo":"🇧🇴","br":"🇧🇷","bg":"🇧🇬","kh":"🇰🇭",
    "ca":"🇨🇦","cl":"🇨🇱","cn":"🇨🇳","co":"🇨🇴","hr":"🇭🇷","cz":"🇨🇿","dk":"🇩🇰","eg":"🇪🇬",
    "et":"🇪🇹","fi":"🇫🇮","fr":"🇫🇷","de":"🇩🇪","gh":"🇬🇭","gr":"🇬🇷","hu":"🇭🇺","in":"🇮🇳",
    "id":"🇮🇩","ir":"🇮🇷","iq":"🇮🇶","ie":"🇮🇪","il":"🇮🇱","it":"🇮🇹","jp":"🇯🇵","jo":"🇯🇴",
    "kz":"🇰🇿","ke":"🇰🇪","kw":"🇰🇼","my":"🇲🇾","mx":"🇲🇽","ma":"🇲🇦","mm":"🇲🇲","np":"🇳🇵",
    "nl":"🇳🇱","ng":"🇳🇬","no":"🇳🇴","om":"🇴🇲","pk":"🇵🇰","ps":"🇵🇸","pe":"🇵🇪","ph":"🇵🇭",
    "pl":"🇵🇱","pt":"🇵🇹","qa":"🇶🇦","ro":"🇷🇴","ru":"🇷🇺","sa":"🇸🇦","rs":"🇷🇸","sg":"🇸🇬",
    "za":"🇿🇦","kr":"🇰🇷","es":"🇪🇸","lk":"🇱🇰","se":"🇸🇪","ch":"🇨🇭","tw":"🇹🇼","th":"🇹🇭",
    "tn":"🇹🇳","tr":"🇹🇷","ua":"🇺🇦","ae":"🇦🇪","gb":"🇬🇧","us":"🇺🇸","uz":"🇺🇿","vn":"🇻🇳","ye":"🇾🇪",
}

_last_sent = 0
def send_tg(iso, number, cli, otp):
    global _last_sent
    diff = time.time() - _last_sent
    if diff < 0.5: time.sleep(0.5 - diff)
    flag   = FLAGS.get(iso.lower(), "🌍")
    masked = (lambda n: n[:3]+"****"+n[-3:] if len(n)>=8 else n)(re.sub(r'\D','',number))
    msg = (f"<b>┊°°°✅ 𝐋𝐈𝐕𝐄 𝐎𝐓𝐏 ✅°°°┊</b>\n"
           f"<blockquote>{flag} <b>#{iso.upper()}</b>  <code>+{masked}</code>\n"
           f"🟢 <b>#CLI</b>  {cli.upper()}</blockquote>")
    markup = {"inline_keyboard": [
        [{"text": f"🔑  {otp}  🔑", "copy_text": {"text": otp}}],
        [{"text": "📞 NUMBERS", "url": "https://t.me/dp_numbers"},
         {"text": "🔰 BACKUP",  "url": "https://t.me/powerotpbackup"}]
    ]}
    for _ in range(5):
        try:
            r = cf_requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg,
                      "parse_mode": "HTML", "reply_markup": markup}, timeout=15)
            if r.status_code == 200:
                _last_sent = time.time()
                log.info(f"🚀 SENT | +{masked} | OTP={otp} | {cli} {flag}")
                return
            elif r.status_code == 429:
                time.sleep(r.json().get("parameters",{}).get("retry_after",10)+2)
        except Exception as e:
            log.error(f"TG: {e}"); time.sleep(3)

def handle(data):
    try:
        number  = re.sub(r'\D','', str(data.get("number","") or data.get("test_number","")))
        message = str(data.get("message",""))
        cli     = str(data.get("cli","") or data.get("sender","") or "Unknown")
        iso     = str(data.get("country_iso","xx"))
        if not number or not message: return
        otp = extract_otp(message)
        if not otp: return
        key = f"{number}:{otp}"
        if key in seen: return
        seen.add(key)
        log.info(f"⚡ LIVE | +{number} | OTP={otp} | {cli} | {iso.upper()}")
        send_tg(iso, number, cli, otp)
    except Exception as e:
        log.error(f"handle: {e}")

sio = socketio.Client(logger=False, engineio_logger=False,
                      reconnection=True, reconnection_attempts=0, reconnection_delay=5)

@sio.event
def connect():
    log.info("✅ Socket.IO Connected!")

@sio.event
def disconnect():
    log.warning("⚠ Disconnected — reconnecting...")

# ── SIRF LIVE PAGE EVENT ──
# send_message = live SMS
# send_message_test = test page (IGNORE)
# send_message_max_Limit = limit info (IGNORE)
@sio.on("send_message")
def on_live(data):
    log.info(f"📨 LIVE SMS: {str(data)[:200]}")
    handle(data)

# ── START ──
log.info("="*50)
log.info("  IvaSMS LIVE OTP Bot")
log.info("  Sirf: /portal/live/my_sms")
log.info("="*50)

if not do_login(): exit(1)

cookie_str = "; ".join([f"{k}={v}" for k, v in _cookies.items()])

sio.connect(SOCKETIO_URL, socketio_path="socket.io",
    headers={"Cookie": cookie_str, "Referer": LIVE_URL, "Origin": "https://www.ivasms.com"},
    transports=["websocket","polling"], wait_timeout=15)

log.info("🟢 Live — waiting for SMS...")
sio.wait()
