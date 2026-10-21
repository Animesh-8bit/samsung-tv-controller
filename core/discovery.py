"""
SSDP / UPnP Discovery for Samsung Smart TVs on the Local Network
"""

import socket
import urllib.request
import json
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Any, Optional

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 2

SSDP_MSG = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    f"MX: {SSDP_MX}\r\n"
    "ST: ssdp:all\r\n"
    "\r\n"
)


def discover_samsung_tvs(timeout: float = 3.0) -> List[Dict[str, Any]]:
    """
    Broadcasts SSDP M-SEARCH query to locate Samsung TVs on local network.
    Returns list of discovered TV devices with their metadata.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)
    sock.bind(("", 0))

    discovered_ips = set()
    tvs = []

    try:
        sock.sendto(SSDP_MSG.encode("utf-8"), (SSDP_ADDR, SSDP_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(65507)
                ip = addr[0]
                if ip in discovered_ips:
                    continue

                text = data.decode("utf-8", errors="ignore")
                if "samsung" in text.lower() or "dial-multiscreen" in text.lower():
                    discovered_ips.add(ip)
                    tv_info = inspect_tv(ip)
                    if tv_info:
                        tvs.append(tv_info)
            except socket.timeout:
                break
            except Exception:
                pass
    finally:
        sock.close()

    return tvs


def inspect_tv(ip: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Queries TV REST API at port 8001 to get detailed specifications.
    """
    url = f"http://{ip}:8001/api/v2/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MacTVRemote"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            dev = data.get("device", {})
            return {
                "ip": ip,
                "name": dev.get("name", f"Samsung TV ({ip})"),
                "model": dev.get("model", ""),
                "model_name": dev.get("modelName", ""),
                "mac": dev.get("wifiMac", ""),
                "power_state": dev.get("PowerState", "unknown"),
                "os": dev.get("OS", "Tizen"),
                "token_auth": dev.get("TokenAuthSupport", "true") == "true",
                "duid": dev.get("duid", "")
            }
    except Exception:
        # Fallback if port 8001 REST API is not responding or blocked
        return {
            "ip": ip,
            "name": f"Samsung TV ({ip})",
            "model": "Unknown",
            "model_name": "Samsung Smart TV",
            "mac": "",
            "power_state": "unknown",
            "os": "Tizen",
            "token_auth": True,
            "duid": ""
        }


if __name__ == "__main__":
    print("Scanning for Samsung Smart TVs...")
    results = discover_samsung_tvs(3.0)
    print(f"Found {len(results)} TV(s):")
    for tv in results:
        print(f"  • {tv['name']} ({tv['model_name']}) at {tv['ip']} [MAC: {tv['mac']}]")
