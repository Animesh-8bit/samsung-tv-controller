#!/usr/bin/env python3
"""
Command-Line Interface for Samsung TV Controller
Use directly from Terminal or integrate with Raycast, Alfred, or macOS Shortcuts!
"""

import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, "/Users/admin")

from core.controller import controller
from core.discovery import discover_samsung_tvs

CLI_SHORTCUTS = {
    "volup": "KEY_VOLUP",
    "voldn": "KEY_VOLDOWN",
    "voldown": "KEY_VOLDOWN",
    "mute": "KEY_MUTE",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "ok": "KEY_ENTER",
    "enter": "KEY_ENTER",
    "select": "KEY_ENTER",
    "back": "KEY_RETURN",
    "return": "KEY_RETURN",
    "home": "KEY_HOME",
    "menu": "KEY_MENU",
    "info": "KEY_INFO",
    "exit": "KEY_EXIT",
    "source": "KEY_SOURCE",
    "play": "KEY_PLAY",
    "pause": "KEY_PAUSE",
    "playpause": "KEY_PLAYPAUSE",
    "chup": "KEY_CHUP",
    "chdn": "KEY_CHDOWN",
    "chdown": "KEY_CHDOWN",
    "guide": "KEY_GUIDE",
}

APP_SHORTCUTS = {
    "netflix": "3201907018807",
    "youtube": "111299001912",
    "yt": "111299001912",
    "prime": "3201910019365",
    "amazon": "3201910019365",
    "amazonprime": "3201910019365",
    "primevideo": "3201910019365",
    "hotstar": "3201711015117",
    "jiohotstar": "3201711015117",
    "samsunginternet": "3201907018784",
    "internet": "3201907018784",
    "browser": "3201907018784",
    "spotify": "3201606009684",
    "sonyliv": "3201709014748",
    "mxplayer": "3202210028653"
}


def main():
    if len(sys.argv) < 2:
        print("Usage: samsung-remote <command> [args...]")
        print("\nCommands:")
        print("  power | on | off           - Power control")
        print("  volup | voldn | mute       - Volume control")
        print("  up | down | left | right   - Navigation")
        print("  ok | back | home | menu    - System buttons")
        print("  play | pause | playpause   - Media playback")
        print("  chup | chdn | guide        - Channel control")
        print("  netflix | youtube | prime  - App launchers (also: amazon, hotstar, internet)")
        print("  hotstar | spotify | browser- App launchers (also: jiohotstar, samsunginternet)")
        print("  open <url>                 - Open URL in TV browser")
        print("  text <string>              - Type text on TV")
        print("  key <KEY_NAME>             - Send custom raw key")
        print("  status                     - Show TV connection status")
        print("  discover                   - Scan LAN for Samsung TVs")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "status":
        info = controller.get_info()
        print(f"📺 TV Status:")
        print(f"  • Name:   {info.get('name')}")
        print(f"  • Model:  {info.get('model')}")
        print(f"  • IP:     {info.get('ip')}")
        print(f"  • MAC:    {info.get('mac')}")
        print(f"  • Online: {'🟢 Yes' if info.get('online') else '🔴 Standby/Offline'}")
        print(f"  • Token:  {'✅ Paired' if info.get('token_paired') else '❌ Not Paired'}")
        return

    if cmd == "discover":
        print("🔍 Scanning network for Samsung Smart TVs...")
        tvs = discover_samsung_tvs()
        if not tvs:
            print("No Samsung TVs found.")
        for tv in tvs:
            print(f"  • {tv['name']} ({tv['model_name']}) -> {tv['ip']} [MAC: {tv['mac']}]")
        return

    if cmd in ["power", "toggle"]:
        ok, msg = controller.power_toggle()
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd in ["on", "wake"]:
        ok, msg = controller.power_on()
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd in ["off"]:
        ok, msg = controller.power_off()
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd == "open":
        if len(sys.argv) < 3:
            print("Error: Please provide a URL to open.")
            sys.exit(1)
        url = sys.argv[2]
        ok, msg = controller.open_browser(url)
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd == "text":
        if len(sys.argv) < 3:
            print("Error: Please provide text to type.")
            sys.exit(1)
        text = " ".join(sys.argv[2:])
        ok, msg = controller.send_text(text)
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd == "key":
        if len(sys.argv) < 3:
            print("Error: Please provide key name (e.g., KEY_VOLUP).")
            sys.exit(1)
        raw_key = sys.argv[2]
        ok, msg = controller.send_key(raw_key)
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd in APP_SHORTCUTS:
        app_id = APP_SHORTCUTS[cmd]
        print(f"🚀 Launching {cmd.title()} [{app_id}]...")
        ok, msg = controller.launch_app(app_id)
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if cmd in CLI_SHORTCUTS:
        key = CLI_SHORTCUTS[cmd]
        ok, msg = controller.send_key(key)
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    # Try sending as raw key
    ok, msg = controller.send_key(cmd)
    print(f"{'✅' if ok else '❌'} {msg}")


if __name__ == "__main__":
    main()
