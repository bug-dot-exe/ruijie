# Ruijie Captive Portal Advanced Helper

![Ruijie](https://img.shields.io/badge/Ruijie-Bypass-red)
![WiFiDog](https://img.shields.io/badge/Protocol-WiFiDog-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen)

An advanced offensive security tool designed to bypass **Ruijie Captive Portals** by exploiting the WiFiDog authentication protocol. This script automates discovery, brute-forces vouchers concurrently, and maintains a persistent connection through adaptive monitoring.

## ⚡ Key Features

*   **Asynchronous Brute-Force Engine**: Leverages `asyncio` and `aiohttp` to check 120+ voucher codes concurrently. Find a valid code in seconds, not minutes.
*   **Instant Auto-Reconnect**: Background ping monitor detects connection drops and triggers an immediate re-authentication sequence using cached credentials.
*   **One-Click Bypass**: Streamlined inline prompt allows for a full "Setup + Monitor" sequence without requiring any CLI flags.
*   **Intelligent Persistence**: Automatically saves and replays successful sessions and vouchers (`.session_url`, `.saved_code`).
*   **Protocol Precision**: Matches the exact WiFiDog implementation used by high-end Ruijie hardware (lowercase parameters, GET/POST fallbacks).
*   **Live Dashboard**: Real-time terminal UI showing internet status, bypass performance, and connectivity logs.

## 🚀 Installation

### Linux / macOS
```bash
git clone https://github.com/bug-dot-exe/ruijie.git
cd ruijie
pip install -r requirements.txt
python3 run.py
```

### Termux (Android)
```bash
pkg update && pkg install python git
git clone https://github.com/bug-dot-exe/ruijie.git
cd ruijie
pip install -r requirements.txt
python run.py
```

## 🛠️ Usage

### 1. Streamlined Mode (No Flags)
Simply run the script. It will prompt you for the best action:
```bash
python3 run.py
```
> **Select [1]** to automatically discover the network, brute-force the voucher, and start the keep-alive monitor.

### 2. Automated Mode (CLI Flags)
For non-interactive or scripted use:
```bash
# Full Auto: Setup + Start Monitor
python3 run.py -s -f

# Force Monitor with a specific code
python3 run.py -f -c 123456

# High-Speed Brute Force (20 concurrent threads)
python3 run.py -s -f -w 20
```

## 📖 Configuration

The tool supports environment variables for advanced setup:
*   `RUIJIE_GATEWAY`: Override the gateway IP (default: `192.168.60.1`).
*   `RUIJIE_PORT`: Override the gateway port (default: `2060`).
*   `RUIJIE_ACCESS_CODE`: Set a default voucher code for brute-force prioritization.
*   `RUIJIE_AUTH_WORKERS`: Number of concurrent auth attempts.

Example:
```bash
RUIJIE_GATEWAY=172.16.0.1 python3 run.py -s -f
```

## ⚠️ Requirements
*   **Python 3.10+**
*   `requests`
*   `aiohttp` (required for high-speed concurrent brute force)

## 🛡️ Disclaimer
This tool is for educational purposes and authorized security testing only. Use it only on networks you own or have explicit permission to test.
