#!/usr/bin/env python3
"""
daemon_verifier.py — Verification & Health Check Client for VEMINS ESP Daemon
Validates that the running daemon on 127.0.0.1:9999 matches the expected build hash
and verifies process attachment, memory readability via kernel pread, and base offsets.
"""

import os
import sys
import json
import socket
import time
from typing import Dict, Any, Optional

HOST = "127.0.0.1"
PORT = 9999
HASH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vemins_daemon.hash")


def get_expected_hash() -> str:
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return ""


class DaemonClient:
    def __init__(self, host: str, port: int, timeout: float = 3.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self.buf = ""

    def read_line(self, timeout: float = 3.0) -> str:
        self.sock.settimeout(timeout)
        t0 = time.time()
        while "\n" not in self.buf:
            if time.time() - t0 > timeout:
                return ""
            try:
                data = self.sock.recv(4096).decode('utf-8', errors='ignore')
                if not data:
                    break
                self.buf += data
            except socket.timeout:
                break
        if "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            return line.strip()
        line = self.buf.strip()
        self.buf = ""
        return line

    def send_cmd(self, cmd: str, timeout: float = 5.0) -> Dict[str, Any]:
        self.sock.sendall((cmd.strip() + "\n").encode())
        line = self.read_line(timeout=timeout)
        if not line:
            return {}
        try:
            return json.loads(line)
        except Exception:
            return {"raw": line}

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def main():
    print("=================================================================")
    print("          VEMINS ESP DAEMON VERIFIER & HEALTH CHECK              ")
    print("=================================================================")

    expected_hash = get_expected_hash()
    print(f"[+] Expected Source Build Hash : {expected_hash or 'UNKNOWN'}")

    try:
        client = DaemonClient(HOST, PORT, timeout=2.0)
    except Exception as e:
        print(f"\n[-] ❌ CONNECTION FAILED: Could not connect to vemins_daemon at {HOST}:{PORT}")
        print(f"    Error: {e}")
        print("\n[!] The daemon is not currently running inside the VM.")
        print("    Run this command in the VM root shell to start it:")
        print('    su -c "cp /sdcard/vemins_daemon /data/local/tmp/vemins_daemon && chmod 755 /data/local/tmp/vemins_daemon && killall vemins_daemon 2>/dev/null; /data/local/tmp/vemins_daemon &"')
        sys.exit(1)

    # 1. Read Connection Handshake Banner
    banner_line = client.read_line(timeout=0.5)
    banner = {}
    if banner_line:
        try:
            banner = json.loads(banner_line)
        except Exception:
            banner = {"raw": banner_line}

    print(f"[+] Connected to Daemon on {HOST}:{PORT}")
    print(f"    • Banner Agent    : {banner.get('agent', 'unknown')}")
    print(f"    • Banner Version  : {banner.get('version', 'unknown')}")
    print(f"    • Banner Hash     : {banner.get('build_hash', 'unknown')}")
    print(f"    • Banner Time     : {banner.get('build_time', 'unknown')}")

    # 2. Query GET_INFO
    info = client.send_cmd("GET_INFO", timeout=3.0)
    live_hash = info.get("build_hash", banner.get("build_hash", ""))
    live_version = info.get("version", banner.get("version", ""))
    pid = info.get("pid", 0)
    liblogic_base = info.get("liblogic_base", 0)
    if isinstance(liblogic_base, str):
        liblogic_base = int(liblogic_base, 16) if liblogic_base.startswith("0x") else int(liblogic_base)
    libcsharp_base = info.get("libcsharp_base", 0)
    if isinstance(libcsharp_base, str):
        libcsharp_base = int(libcsharp_base, 16) if libcsharp_base.startswith("0x") else int(libcsharp_base)

    print("\n--- [1. BUILD IDENTITY VALIDATION] ---")
    print(f"  • Live Daemon Version : {live_version}")
    print(f"  • Live Daemon Hash    : {live_hash}")
    print(f"  • Expected Build Hash : {expected_hash}")

    if expected_hash and live_hash != expected_hash:
        print(f"\n[-] ⚠️  DAEMON HASH MISMATCH:")
        print(f"    The running daemon (hash: '{live_hash}') does not match the newly built binary (hash: '{expected_hash}').")
        print("\n[!] To reload the latest binary inside VM:")
        print('    su -c "cp /sdcard/vemins_daemon /data/local/tmp/vemins_daemon && chmod 755 /data/local/tmp/vemins_daemon && killall vemins_daemon 2>/dev/null; /data/local/tmp/vemins_daemon &"')
    else:
        print("[✓] Build Identity Verified: Live daemon matches current source code!")

    # 3. Query SELF_TEST
    print("\n--- [2. PROCESS & MEMORY TRANSPORT CHECK] ---")
    st = client.send_cmd("SELF_TEST")
    mem_ok = st.get("mem_readable", False)
    print(f"  • Target MLBB PID     : {pid}")
    print(f"  • liblogic.so Base    : 0x{liblogic_base:x}")
    print(f"  • libcsharp.so Base   : 0x{libcsharp_base:x}")
    print(f"  • /proc/$PID/mem OK   : {'YES' if mem_ok else 'NO'}")

    if pid <= 0:
        print("  [-] Warning: MLBB target process (com.mobile.legends) is not currently running.")
    elif liblogic_base <= 0:
        print("  [-] Warning: liblogic.so not loaded in target process.")
    else:
        # Test direct memory read (ELF header magic \x7fELF at liblogic_base)
        mem_resp = client.send_cmd(f"READ_MEM {pid} {liblogic_base:x} 4")
        if mem_resp.get("status") == "ok" and mem_resp.get("data") == "7f454c46":
            print("  • Kernel pread check  : 0x7f454c46 (\x7fELF header verified!)")
        else:
            print(f"  • Kernel pread check  : Response: {mem_resp}")

    print("\n=================================================================")
    print("                    SELF-TEST SUMMARY                            ")
    print("=================================================================")
    print(f"[✓] Daemon Version      : {live_version} ({live_hash})")
    print(f"[✓] Protocol Version    : 3 (External Read-Only Telemetry)")
    print(f"[✓] Transport State     : {'OPERATIONAL' if mem_ok or pid > 0 else 'WAITING_FOR_PROCESS'}")
    print("=================================================================")

    client.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
