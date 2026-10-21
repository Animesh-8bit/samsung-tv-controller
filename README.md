#  Samsung Smart TV Mac Controller

An Apple-grade, high-performance remote controller application engineered for macOS to control Samsung Smart TVs (Tizen OS) over the local network. 

Runs as a native standalone desktop application with zero browser chrome, instant tactile audio feedback, live video seek scrubbing, and keyboard hotkeys.

---

## ✨ Features

- **macOS Desktop App (`Samsung TV Controller.app`)**:
  - Installed directly to `~/Applications` with high-resolution Apple icon.
  - Launchable from **Spotlight** (`Cmd + Space` ➔ *Samsung TV Controller*) or pinned to the **macOS Dock**.
  - Automatically manages the local background service; self-healing and self-starting on launch.
- **Universal Video Seek Bar & Media Scrubber**:
  - **Interactive Scrubber Bar**: Drag or click along the timeline to scrub video forward or backward with live delta preview badges.
  - **Quick Step Skips**: One-click **`⏪ 10s`**, **`10s ⏩`**, **`⏪ 30s`**, and **`30s ⏩`** pills.
  - **Universal Streaming Support**: Works across all commercial streaming apps (Amazon Prime Video, Netflix, YouTube, JioHotstar, SonyLIV, MX Player) by dispatching adaptive step pulses that trigger the TV's native on-screen seek bar.
  - **Dual-Mode UPnP Sync**: Automatically queries the TV's UPnP `AVTransport` (port 9197) to track true `RelTime` and `TrackDuration` when media is played via DLNA, USB, or local player.
- **App Dock & Instant Hotkeys**:
  - Dedicated 1-click launch buttons and single-key physical keyboard hotkeys:
    - **Netflix** ➔ Press **`N`**
    - **YouTube** ➔ Press **`Y`**
    - **Amazon Prime Video** ➔ Press **`A`**
    - **JioHotstar** ➔ Press **`J`**
    - **Samsung Internet Browser** ➔ Press **`I`** or **`B`**
    - **Spotify** ➔ Press **`S`**
- **Elastic & Resizable Non-Scrollable UI**:
  - Layout automatically scales with `clamp()` math to any window dimension without showing scrollbars or allowing mouse-wheel page bounce.
- **Hover Tooltips Engine**:
  - Instant floating macOS-style tooltip cards on hover detailing button functions, TV actions, and physical keyboard shortcut pills.
- **Backdrop-Dismissible Drawers**:
  - Settings, Numeric Keypad, and Text Entry drawers dismiss cleanly on **`Esc`**, clicking outside on the blurred backdrop, or the top-right **`✕`** close button.
- **Wake-on-LAN & Standby Power**:
  - Powers off the TV over secure WebSocket (`KEY_POWER`).
  - Wakes up the TV from sleep/standby via Wake-on-LAN magic packets (`wakeonlan`).
- **Text Typing & URL Launcher**:
  - Type text on your Mac keyboard and inject it directly into search fields or on-screen keyboards on the TV.
  - Open any web URL directly in the Samsung TV's web browser.
- **Automated LAN Discovery**:
  - Broadcasts SSDP `M-SEARCH` packets to discover all Samsung Smart TVs on the local subnet with IP, MAC, model, and OS detection.

---

## ⌨️ Mac Keyboard Shortcuts

| Key | Remote Action | Description |
| :--- | :--- | :--- |
| **`[`** | **Seek -10s** | Skip video backward 10 seconds |
| **`]`** | **Seek +10s** | Skip video forward 10 seconds |
| **`<`** or **`{`** | **Seek -30s** | Skip video backward 30 seconds |
| **`>`** or **`}`** | **Seek +30s** | Skip video forward 30 seconds |
| **`Space`** | **Play / Pause** | Toggle media playback |
| **`↑` `↓` `←` `→`** | **D-Pad Directionals** | Navigate menus, cursor, and guide |
| **`Enter`** | **Select / OK** | Confirm on-screen selection |
| **`Esc`** / **`Backspace`** | **Return / Back** | Go back (or dismiss open drawers) |
| **`+`** / **`=`** | **Volume Up** | Increase TV volume level |
| **`-`** | **Volume Down** | Decrease TV volume level |
| **`M`** | **Mute Toggle** | Mute or un-mute audio |
| **`H`** | **Home** | Open TV Smart Hub home launcher |
| **`P`** | **Power Toggle** | Wake TV (WOL) or put into standby |
| **`0`–`9`** | **Number Keys** | Direct channel tuning |
| **`N`** | **Netflix** | Launch Netflix app |
| **`Y`** | **YouTube** | Launch YouTube app |
| **`A`** | **Prime Video** | Launch Amazon Prime Video |
| **`J`** | **JioHotstar** | Launch JioHotstar app |
| **`I`** / **`B`** | **Internet** | Launch Samsung Web Browser |
| **`S`** | **Spotify** | Launch Spotify Music |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│               Samsung TV Controller.app                │
│       (macOS Chrome Window --app="http://127.0.0.1:5588")│
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / REST & WebSockets
                            ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Local Server (Port 5588)            │
│  • REST API endpoints: /api/key, /api/seek, /api/power  │
│  • Static asset server: index.html, style.css, app.js  │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
        Port 8002 (WSS)            Port 9197 (UPnP)
               │                          │
               ▼                          ▼
┌───────────────────────────┐ ┌──────────────────────────┐
│ Samsung SmartView WS API  │ │  UPnP AVTransport 1.0   │
│ • Token-authenticated     │ │  • Real-time timestamps  │
│ • Remote Key Dispatch     │ │  • Total track duration  │
│ • Touch-event bypass      │ │  • Absolute time seeking │
└───────────────────────────┘ └──────────────────────────┘
               │                          │
               └────────────┬─────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│           Samsung Smart TV (Tizen OS)                  │
│       • Local IP: 192.168.1.x / MAC: WOL Enabled       │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
- **macOS 11.0 (Big Sur) or newer**
- **Python 3.10+**
- **Google Chrome** (for standalone borderless app window mode)
- Samsung Smart TV connected to the same Wi-Fi / Local Network

### 2. Clone the Repository
```bash
git clone https://github.com/Animesh-8bit/samsung-tv-controller.git
cd samsung-tv-controller
```

### 3. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Install the macOS Application
Run the automated installer to register `Samsung TV Controller.app` into your `~/Applications` folder:
```bash
chmod +x install_mac_app.sh
./install_mac_app.sh
```

### 5. First Run & TV Pairing
1. Launch the app from **Spotlight** (`Cmd + Space` ➔ *Samsung TV Controller*) or run:
   ```bash
   ./start.sh
   ```
2. On your TV screen, an authorization prompt will appear: **"Allow SamsungTvRemote to connect?"**
3. Select **Allow** using your physical remote. The pairing token will be securely saved to `tv_token.txt`.

---

## ⚙️ Configuration

A default template is provided in `config.example.json`. The application automatically generates `config.json` on first run:

```json
{
  "ip": "192.168.1.5",
  "mac": "68:FC:CA:33:88:DA",
  "port": 8002,
  "name": "SamsungTvRemote",
  "token_file": "tv_token.txt",
  "sdb_port": 26101
}
```

* **`ip`**: Local IPv4 address of the Samsung Smart TV.
* **`mac`**: Physical MAC address of the TV's Wi-Fi or Ethernet card (used for Wake-on-LAN).
* **`port`**: Secure WebSocket port (`8002` for modern Tizen TVs; `8001` for legacy non-SSL models).
* **`token_file`**: Path to the file where the authentication token is persisted.

---

## 🛠️ CLI Utilities (`cli.py`)

You can also control your TV directly from your terminal:

```bash
# Check TV connection status & power state
./.venv/bin/python3 cli.py status

# Send remote keys
./.venv/bin/python3 cli.py key KEY_VOLUP
./.venv/bin/python3 cli.py key KEY_MUTE

# Power control
./.venv/bin/python3 cli.py power toggle
./.venv/bin/python3 cli.py power on

# Launch streaming apps
./.venv/bin/python3 cli.py app netflix
./.venv/bin/python3 cli.py app youtube
./.venv/bin/python3 cli.py app prime

# Scan LAN for Samsung Smart TVs
./.venv/bin/python3 cli.py discover
```

---

## 🌐 REST API Reference

The local server runs on `http://127.0.0.1:5588`:

| Method | Endpoint | Payload Example | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/status` | — | Returns TV online state, model, IP, and power status |
| `POST` | `/api/key` | `{"key": "KEY_VOLUP"}` | Dispatches a single remote key command |
| `POST` | `/api/keys` | `{"keys": ["KEY_RIGHT", "KEY_ENTER"], "delay": 0.1}` | Sends an ordered sequence of keys |
| `POST` | `/api/seek` | `{"seconds": 30}` | Relative or UPnP seek across streaming services |
| `GET` | `/api/media/status` | — | Queries UPnP AVTransport for real-time position |
| `POST` | `/api/power` | `{"action": "toggle"}` | Wakes TV via WOL or toggles power |
| `POST` | `/api/app` | `{"app_id": "3201910019365"}` | Launches an installed app by ID |
| `POST` | `/api/browser` | `{"url": "https://google.com"}` | Opens URL in the TV's web browser |
| `POST` | `/api/text` | `{"text": "Search query"}` | Injects typed text into active TV input field |
| `POST` | `/api/discover` | — | Scans local subnet via SSDP M-SEARCH |
| `GET` | `/api/config` | — | Returns active network configuration |
| `POST` | `/api/config` | `{"ip": "192.168.1.10", "mac": "..."}` | Updates connection settings |

---

## 🔍 Troubleshooting

#### 1. TV Disconnects when Streaming Apps (Prime Video / Netflix) Open
* **Root Cause**: Streaming apps issue touch-mode initialization events (`ms.remote.touchEnable`/`ms.remote.touchDisable`) upon launch. Standard WebSocket client libraries mistake these for connection failures and abort.
* **Solution**: Our controller patches the handshake event loop in `core/controller.py` to gracefully bypass non-connect events, keeping the WebSocket connection open and responsive.

#### 2. TV Does Not Turn On via Remote
* Ensure your TV's **"Power On with Mobile"** and **"IP Remote"** settings are enabled in:
  `Settings ➔ General ➔ Network ➔ Expert Settings ➔ Power On with Mobile: ON`.
* Verify that the TV's MAC address is configured correctly in `config.json`.

#### 3. LAN Discovery Says "No TVs Found"
* On macOS, BSD socket rules require SSDP UDP sockets to be bound to `("", 0)` so ephemeral reply packets are not dropped by the local packet filter.
* Ensure your Mac and Samsung TV are on the same Wi-Fi subnet (e.g. not separated by Guest Wi-Fi isolation).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
