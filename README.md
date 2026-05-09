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
```

Example:

```bash
RUIJIE_GATEWAY=192.168.1.1 RUIJIE_PORT=2060 python3 run.py
```

If `RUIJIE_PHONE_NUMBER` is empty, the tool sends a random 16-character value like the old `star` build did.

Change these values if your Ruijie deployment uses different gateway IPs, ports, paths, or voucher parameters.

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
- Try opening any HTTP site in a browser to trigger the portal redirect, then run the tool again.
- On Termux, run `python -m pip install --upgrade pip requests urllib3` if dependencies fail.

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
