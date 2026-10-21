#!/usr/bin/env python3
"""
samsung_sdb.py - Lightweight native Python SDB (Smart Development Bridge) client
for Samsung Smart TVs running Tizen OS.
"""

import socket
import struct
import time
import json
from typing import List, Dict, Optional, Tuple

CMD_CNXN = 0x4E584E43
CMD_OPEN = 0x4E45504F
CMD_OKAY = 0x59414B4F
CMD_WRTE = 0x45545257
CMD_CLSE = 0x45534C43

class SamsungSDB:
    def __init__(self, host: str = "192.168.1.5", port: int = 26101, timeout: float = 4.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.device_id: str = ""

    def connect(self) -> bool:
        """Connect to Samsung TV SDB daemon and perform CNXN handshake."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))

            # Send CNXN frame
            banner = b"host::sdb-client\x00"
            self._send_frame(CMD_CNXN, 0x01000000, 4096, banner)

            resp = self._read_frame()
            if resp and resp[0] == "CNXN":
                self.device_id = resp[3].decode("utf-8", errors="ignore").strip("\x00")
                return True
            return False
        except Exception as e:
            if self.sock:
                self.sock.close()
                self.sock = None
            raise ConnectionError(f"Failed to connect to SDB at {self.host}:{self.port} - {e}")

    def _send_frame(self, cmd: int, a0: int, a1: int, payload: bytes):
        magic = cmd ^ 0xFFFFFFFF
        checksum = sum(payload) & 0xFFFFFFFF
        hdr = struct.pack("<6I", cmd, a0, a1, len(payload), checksum, magic)
        self.sock.sendall(hdr + payload)

    def _read_frame(self) -> Optional[Tuple[str, int, int, bytes]]:
        hdr = b""
        while len(hdr) < 24:
            chunk = self.sock.recv(24 - len(hdr))
            if not chunk:
                return None
            hdr += chunk

        cmd, a0, a1, dlen, dchk, rmag = struct.unpack("<6I", hdr)
        cmd_str = "".join([chr((cmd >> (8 * i)) & 0xFF) for i in range(4)])

        payload = b""
        while len(payload) < dlen:
            chunk = self.sock.recv(dlen - len(payload))
            if not chunk:
                break
            payload += chunk

        return (cmd_str, a0, a1, payload)

    def run_verb(self, verb: str) -> str:
        """Execute a Samsung SDB verb command (prefixed with 0) and capture output."""
        if not self.sock:
            self.connect()

        local_id = 1
        full_cmd = f"shell:{verb}\x00".encode("utf-8")
        self._send_frame(CMD_OPEN, local_id, 0, full_cmd)

        output = b""
        while True:
            try:
                frame = self._read_frame()
                if not frame:
                    break
                cmd, a0, a1, payload = frame
                if cmd == "OKAY":
                    remote_id = a0
                elif cmd == "WRTE":
                    remote_id = a0
                    output += payload
                    self._send_frame(CMD_OKAY, local_id, remote_id, b"")
                elif cmd == "CLSE":
                    break
            except Exception:
                break

        return output.decode("utf-8", errors="ignore").strip()

    def get_duid(self) -> str:
        res = self.run_verb("0 getduid")
        return res.strip()

    def list_apps(self) -> List[Dict[str, str]]:
        raw = self.run_verb("0 vd_applist")
        apps = []
        current = {}
        for line in raw.splitlines():
            line = line.strip("-")
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("-")
                current[k] = v
                if k == "ambient_icon_path":
                    apps.append(current)
                    current = {}
        return apps

    def launch_app(self, app_id: str) -> Tuple[bool, str]:
        res = self.run_verb(f"0 was_execute {app_id}")
        success = "launch start" in res or "resumed" in res
        return success, res

    def kill_app(self, app_id: str) -> Tuple[bool, str]:
        res = self.run_verb(f"0 was_kill {app_id}")
        success = "terminate app failed" not in res
        return success, res

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    with SamsungSDB() as sdb:
        print(f"Connected to {sdb.device_id}")
        print(f"DUID: {sdb.get_duid()}")
        apps = sdb.list_apps()
        print(f"Found {len(apps)} installed apps")
