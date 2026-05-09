# Ruijie Captive Portal Helper

Ruijie is a pure-Python terminal tool. It keeps the captive-portal workflow, device ID generation, terminal status screen, voucher request, and WiFiDog auth loop.

Use this only on networks you own, administer, or are explicitly allowed to test.

## What It Does

- Detects captive-portal redirects and gateway parameters.
- Discovers the Ruijie cloud `sessionId` and local gateway address.
- Requests voucher login through `portal-as.ruijienetworks.com`.
- Attempts local WiFiDog auth with `token` and `phoneNumber`, matching the old `star` flow.
- Monitors connectivity with `connectivitycheck.gstatic.com/generate_204`.
- Shows a live terminal dashboard with current portal and internet status.
- Stores only local runtime/session helper files.

## Requirements

- Python 3.10 or newer
- `requests`
- `aiohttp`
- Linux, Termux, or another POSIX-like shell

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Run On Linux

```bash
git clone https://github.com/bug-dot-exe/ruijie.git
cd ruijie
python3 -m pip install -r requirements.txt
python3 run.py
```

## Run On Termux

```bash
pkg update
pkg install python git
git clone https://github.com/bug-dot-exe/ruijie.git
cd ruijie
python -m pip install -r requirements.txt
python run.py
```

If Termux asks for storage or network permissions, allow the normal network access required by Python. Root is not required.

The default startup opens a small menu:

```text
[1] Setup / discover Ruijie session
[2] Start internet auth monitor
[3] Show cached session
[4] Set voucher/access code
[0] Exit
```

Run option `1` first while connected to the Ruijie Wi-Fi. Use option `4` if your access code is not the default `admin1`. Then run option `2`.

You can also run the same flow with flags:

```bash
python run.py -s
python run.py -f -c YOUR_ACCESS_CODE
python run.py -s -f -c YOUR_ACCESS_CODE
```

Flags:

```text
-s, --setup          discover and save .session_url/.ip
-f, --force          start auth monitor without the menu
-c, --code CODE      voucher/access code for this run
-w, --workers N      concurrent WiFiDog auth attempts
--show-session       print cached .session_url/.ip
--no-menu            disable the interactive menu
```

For non-interactive startup:

```bash
RUIJIE_MENU=0 python run.py
```

## Activation Key

No activation key is needed in this version.

## Network Configuration

The default portal values are defined near the top of `core.py` and can also be changed with environment variables:

```python
TURBO_STABLE_NODE = os.environ.get("RUIJIE_GATEWAY", "192.168.60.1")
DEFAULT_GW_PORT = os.environ.get("RUIJIE_PORT", "2060")
RUIJIE_PORTAL_HOST = os.environ.get("RUIJIE_PORTAL_HOST", "portal-as.ruijienetworks.com")
RUIJIE_SETUP_PROBE_URL = os.environ.get("RUIJIE_SETUP_PROBE_URL", "http://192.168.0.1")
VOUCHER_PATH = os.environ.get("RUIJIE_VOUCHER_PATH", "/api/auth/voucher/?lang=en_US")
WIFIDOG_AUTH_PATH = os.environ.get("RUIJIE_WIFIDOG_AUTH_PATH", "/wifidog/auth")
DEFAULT_ACCESS_CODE = os.environ.get("RUIJIE_ACCESS_CODE", "admin1")
DEFAULT_PHONE_NUMBER = os.environ.get("RUIJIE_PHONE_NUMBER", "")
AUTH_WORKERS = int(os.environ.get("RUIJIE_AUTH_WORKERS", "10"))
```

Example:

```bash
RUIJIE_GATEWAY=192.168.1.1 RUIJIE_PORT=2060 python3 run.py
```

If `RUIJIE_PHONE_NUMBER` is empty, the tool sends a random 16-character value like the old `star` build did.

`RUIJIE_AUTH_WORKERS` controls the bounded concurrent WiFiDog auth retry burst. The default is `10`, matching the old `star` request pattern.

Change these values if your Ruijie deployment uses different gateway IPs, ports, paths, or voucher parameters.

This repo does not include voucher brute forcing or saved-code replay. Use option `4` or `RUIJIE_ACCESS_CODE=...` with a code you are allowed to use.

## Files Created

The tool may create:

```text
~/.turbo_runtime
.session_url
.ip
```

`.turbo_runtime` stores the last trusted network time used by the local clock rollback check. `.session_url` and `.ip` cache the discovered Ruijie session URL and gateway IP. None of these files is an activation key.

## Troubleshooting

If the tool does not authenticate:

- Confirm you are connected to the captive-portal Wi-Fi network first.
- Confirm the gateway IP and port match your network.
- If the phone says "no internet", that is normal before login; the tool now falls back to the local gateway directly.
- Find the gateway on Termux with `ip route | grep default`.
- Open `http://192.168.0.1` or any HTTP site once in a browser if `.session_url` is not discovered.
- If discovery still fails, run with `RUIJIE_SETUP_PROBE_URL=http://<your-router-ip> python run.py`.
- Confirm your voucher/access code is correct. The default is `admin1`; override it with `RUIJIE_ACCESS_CODE=...`.
- If Termux cannot install `aiohttp`, the tool falls back to normal `requests` auth attempts.
- Try opening any HTTP site in a browser to trigger the portal redirect, then run the tool again.
- On Termux, run `python -m pip install --upgrade pip requests urllib3 aiohttp` if dependencies fail.

## Test

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
python3 -m py_compile core.py run.py tests/test_core.py
```

## Project Layout

```text
core.py              Main implementation
run.py               Small launcher
requirements.txt     Python dependencies
tests/               Unit tests for key helper logic
```
