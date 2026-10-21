"""
Unified Samsung Smart TV Controller
Handles WebSocket protocol, Token Auth, Wake-on-LAN, SDB App execution, and Key Dispatch.
"""

import os
import json
import time
import socket
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

import wakeonlan
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import samsungtvws.connection
import samsungtvws.event

# Add touch and background events to ignore list so apps like Prime Video don't disconnect WS
samsungtvws.connection.IGNORE_EVENTS_AT_STARTUP = (
    'ed.edenTV.update',
    'ms.voiceApp.hide',
    'ms.remote.touchEnable',
    'ms.remote.touchDisable',
    'd2d.serviceMessage',
    'ms.channel.ready'
)
samsungtvws.event.IGNORE_EVENTS_AT_STARTUP = samsungtvws.connection.IGNORE_EVENTS_AT_STARTUP

from samsungtvws import SamsungTVWS
from samsungtvws.exceptions import UnauthorizedError, ConnectionFailure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SamsungController")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
DEFAULT_TOKEN_FILE = Path(__file__).resolve().parent.parent / "tv_token.txt"


class SamsungController:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self.lock = threading.Lock()
        self.tv: Optional[SamsungTVWS] = None
        self._is_connected = False
        self._last_active = 0.0

        self.config: Dict[str, Any] = {
            "ip": "192.168.1.5",
            "mac": "68:FC:CA:33:88:DA",
            "port": 8002,
            "name": "SamsungTvRemote",
            "token_file": str(DEFAULT_TOKEN_FILE),
            "sdb_port": 26101
        }
        self.load_config()

    def load_config(self):
        """Loads configuration from JSON file or writes defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
        else:
            self.save_config()

    def save_config(self):
        """Saves current configuration to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update_settings(self, ip: Optional[str] = None, mac: Optional[str] = None, port: Optional[int] = None):
        """Updates connection settings and resets current connection."""
        with self.lock:
            if ip:
                self.config["ip"] = ip.strip()
            if mac:
                self.config["mac"] = mac.strip()
            if port:
                self.config["port"] = int(port)
            self.save_config()
            self._disconnect()

    def _get_tv_client(self) -> SamsungTVWS:
        """Instantiates or reuses SamsungTVWS client instance."""
        if self.tv is None:
            token_path = self.config.get("token_file", str(DEFAULT_TOKEN_FILE))
            self.tv = SamsungTVWS(
                host=self.config["ip"],
                port=self.config["port"],
                name=self.config.get("name", "SamsungTvRemote"),
                token_file=token_path,
                timeout=10,
                key_press_delay=0.0
            )
        return self.tv

    def _disconnect(self):
        """Closes active WebSocket connection."""
        if self.tv:
            try:
                self.tv.close()
            except Exception:
                pass
            self.tv = None
        self._is_connected = False

    def connect(self) -> bool:
        """Establishes WebSocket connection to TV with token verification."""
        with self.lock:
            try:
                client = self._get_tv_client()
                client.open()
                self._is_connected = True
                self._last_active = time.time()
                return True
            except UnauthorizedError:
                logger.warning("Connection unauthorized. Check authorization dialog on TV.")
                self._disconnect()
                return False
            except Exception as e:
                logger.debug(f"Connection attempt failed: {e}")
                self._disconnect()
                return False

    def is_tv_online(self) -> bool:
        """Quickly probes whether TV's network port is reachable."""
        ip = self.config["ip"]
        port = self.config["port"]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8)
        try:
            res = s.connect_ex((ip, port))
            return res == 0
        except Exception:
            return False
        finally:
            s.close()

    def get_info(self) -> Dict[str, Any]:
        """Fetches TV system metadata and current power state."""
        ip = self.config["ip"]
        try:
            client = self._get_tv_client()
            dev_info = client.rest_device_info()
            dev = dev_info.get("device", {})
            return {
                "online": True,
                "power_state": dev.get("PowerState", "on"),
                "name": dev.get("name", "Samsung Smart TV"),
                "model": dev.get("modelName", dev.get("model", "")),
                "ip": ip,
                "mac": self.config.get("mac", dev.get("wifiMac", "")),
                "os": dev.get("OS", "Tizen"),
                "token_paired": os.path.exists(self.config.get("token_file", ""))
            }
        except Exception:
            online = self.is_tv_online()
            return {
                "online": online,
                "power_state": "standby" if not online else "on",
                "name": "Samsung Smart TV",
                "model": "UA32T4380AKXXL",
                "ip": ip,
                "mac": self.config.get("mac", ""),
                "os": "Tizen",
                "token_paired": os.path.exists(self.config.get("token_file", ""))
            }

    def send_key(self, key_name: str) -> Tuple[bool, str]:
        """
        Sends a remote key press command with auto-reconnection and zero delay.
        """
        with self.lock:
            key = key_name.strip()
            if not key.startswith("KEY_"):
                key = f"KEY_{key.upper()}"

            # Try up to 2 times (in case connection was idle/closed by TV)
            for attempt in range(2):
                try:
                    client = self._get_tv_client()
                    client.send_key(key, key_press_delay=0.0)
                    self._is_connected = True
                    self._last_active = time.time()
                    return True, f"Sent {key}"
                except Exception as e:
                    logger.warning(f"Failed to send key on attempt {attempt+1}: {e}")
                    self._disconnect()
                    time.sleep(0.1)

            return False, f"Could not send {key_name} after retry"

    def send_keys_sequence(self, keys: List[str], delay: float = 0.25) -> Tuple[bool, str]:
        """Sends an ordered sequence of keys with interval delay."""
        successes = 0
        for k in keys:
            ok, _ = self.send_key(k)
            if ok:
                successes += 1
            if delay > 0:
                time.sleep(delay)
        return successes == len(keys), f"Sent {successes}/{len(keys)} keys"

    def get_upnp_playback_info(self) -> Dict[str, Any]:
        """Queries UPnP AVTransport1 on TV for real-time media playback & position."""
        url = f"http://{self.config['ip']}:9197/upnp/control/AVTransport1"
        soap_pos = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body><u:GetPositionInfo xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"><InstanceID>0</InstanceID></u:GetPositionInfo></s:Body></s:Envelope>'''
        try:
            import urllib.request
            import xml.etree.ElementTree as ET
            req = urllib.request.Request(
                url,
                data=soap_pos.encode("utf-8"),
                headers={
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "SOAPAction": '"urn:schemas-upnp-org:service:AVTransport:1#GetPositionInfo"'
                }
            )
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                xml_data = resp.read().decode("utf-8")
                root = ET.fromstring(xml_data)
                body = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body")
                if body is not None:
                    resp_el = body.find("{urn:schemas-upnp-org:service:AVTransport:1}GetPositionInfoResponse")
                    if resp_el is not None:
                        rel_time = resp_el.findtext("RelTime", "00:00:00")
                        duration = resp_el.findtext("TrackDuration", "00:00:00")
                        def to_sec(t):
                            try:
                                parts = list(map(int, t.split(":")))
                                return parts[0]*3600 + parts[1]*60 + parts[2] if len(parts)==3 else 0
                            except Exception:
                                return 0
                        dur_s = to_sec(duration)
                        pos_s = to_sec(rel_time)
                        return {
                            "active": dur_s > 0,
                            "rel_time": rel_time,
                            "duration": duration,
                            "position_sec": pos_s,
                            "duration_sec": dur_s
                        }
        except Exception:
            pass
        return {"active": False, "rel_time": "00:00:00", "duration": "00:00:00", "position_sec": 0, "duration_sec": 0}

    def seek_upnp(self, target_time: str) -> Tuple[bool, str]:
        """Performs absolute seek via UPnP AVTransport1."""
        url = f"http://{self.config['ip']}:9197/upnp/control/AVTransport1"
        soap_seek = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body><u:Seek xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
<InstanceID>0</InstanceID>
<Unit>REL_TIME</Unit>
<Target>{target_time}</Target>
</u:Seek></s:Body></s:Envelope>'''
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                data=soap_seek.encode("utf-8"),
                headers={
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "SOAPAction": '"urn:schemas-upnp-org:service:AVTransport:1#Seek"'
                }
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return True, f"Seeked to {target_time}"
        except Exception as e:
            return False, f"UPnP seek failed: {e}"

    def seek(self, seconds: int) -> Tuple[bool, str]:
        """
        Universal seek across all streaming services and media sources.
        - Positive seconds: forward
        - Negative seconds: rewind
        - If UPnP media is active, calculates absolute target and seeks.
        - Otherwise dispatches directional step keys (KEY_RIGHT/KEY_LEFT), which smart TV
          streaming apps (Prime Video, Netflix, YouTube, Hotstar) use to seek.
        """
        upnp_state = self.get_upnp_playback_info()
        if upnp_state.get("active") and upnp_state.get("duration_sec", 0) > 0:
            current_pos = upnp_state.get("position_sec", 0)
            target = max(0, min(upnp_state["duration_sec"], current_pos + seconds))
            target_str = time.strftime('%H:%M:%S', time.gmtime(target))
            ok, msg = self.seek_upnp(target_str)
            if ok:
                return True, f"Seeked to {target_str}"

        # Streaming apps (Prime Video, Netflix, YouTube, Hotstar, Web Browser)
        # 1 step in smart TV apps = ~10s
        steps = max(1, round(abs(seconds) / 10))
        steps = min(12, steps)
        key = "KEY_RIGHT" if seconds > 0 else "KEY_LEFT"
        keys = [key] * steps
        ok, msg = self.send_keys_sequence(keys, delay=0.08)
        direction = "forward" if seconds > 0 else "backward"
        return ok, f"Skipped {direction} {abs(seconds)}s ({steps}x)"


    def power_on(self) -> Tuple[bool, str]:
        """Wakes up the TV via Wake-on-LAN magic packet."""
        mac = self.config.get("mac", "").strip()
        if not mac:
            return False, "MAC address not configured for Wake-on-LAN"
        try:
            wakeonlan.send_magic_packet(mac)
            # Send extra broadcast for robustness
            wakeonlan.send_magic_packet(mac, ip_address="255.255.255.255")
            return True, f"Wake-on-LAN packet sent to {mac}"
        except Exception as e:
            return False, f"WOL failed: {e}"

    def power_off(self) -> Tuple[bool, str]:
        """Powers off TV via KEY_POWER / KEY_POWEROFF."""
        ok, msg = self.send_key("KEY_POWEROFF")
        if not ok:
            ok, msg = self.send_key("KEY_POWER")
        return ok, msg

    def power_toggle(self) -> Tuple[bool, str]:
        """If TV is offline/standby, sends WOL packet. If TV is on, sends KEY_POWER."""
        if not self.is_tv_online():
            return self.power_on()
        else:
            return self.send_key("KEY_POWER")

    def launch_app(self, app_id: str) -> Tuple[bool, str]:
        """
        Launches an application by ID.
        Attempts native WebSocket launch first, falling back to SDB bridge.
        """
        # Try native WebSocket launch
        with self.lock:
            try:
                client = self._get_tv_client()
                client.run_app(app_id)
                self._last_active = time.time()
                return True, f"Launched app {app_id} via WebSocket"
            except Exception as ws_err:
                logger.warning(f"WebSocket app launch failed: {ws_err}. Trying SDB bridge...")

        # Fallback to SDB bridge
        try:
            try:
                from core.samsung_sdb import SamsungSDB
            except ImportError:
                from samsung_sdb import SamsungSDB
            sdb = SamsungSDB(host=self.config["ip"], port=self.config.get("sdb_port", 26101), timeout=3.0)
            with sdb:
                ok, res = sdb.launch_app(app_id)
                return ok, f"Launched app {app_id} via SDB: {res}"
        except Exception as sdb_err:
            return False, f"App launch failed on both WebSocket and SDB: {sdb_err}"

    def open_browser(self, url: str) -> Tuple[bool, str]:
        """Opens the specified URL inside the Samsung TV's web browser."""
        with self.lock:
            try:
                client = self._get_tv_client()
                client.open_browser(url)
                return True, f"Opened {url} in TV Browser"
            except Exception as e:
                return False, f"Failed to open URL: {e}"

    def send_text(self, text: str) -> Tuple[bool, str]:
        """Sends text input into active input field on TV."""
        with self.lock:
            try:
                client = self._get_tv_client()
                client.send_text(text)
                return True, f"Sent text: {text}"
            except Exception as e:
                return False, f"Failed to send text: {e}"


# Singleton instance
controller = SamsungController()

if __name__ == "__main__":
    print("Testing SamsungController...")
    info = controller.get_info()
    print("Status:", info)
    print("Testing Volume Up...")
    ok, msg = controller.send_key("KEY_VOLUP")
    print(f"Result: {ok} ({msg})")
    time.sleep(0.3)
    ok, msg = controller.send_key("KEY_VOLDOWN")
    print(f"Result: {ok} ({msg})")
