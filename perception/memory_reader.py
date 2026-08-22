"""
Memory Reader Interface & Implementations.
Provides complete abstraction between raw memory acquisition and entity parsing.
"""

from abc import ABC, abstractmethod
import json
import socket
from typing import Dict, Optional, Tuple

class MemoryReader(ABC):
    """Abstract interface for reading raw bytes from game process memory."""

    @abstractmethod
    def read_bytes(self, address: int, size: int) -> bytes:
        """Reads 'size' raw bytes from 'address'."""
        pass

    @abstractmethod
    def get_info(self, force_refresh: bool = False) -> Dict[str, any]:
        """Returns process and module metadata."""
        pass

    def refresh_process_info(self, force: bool = False) -> bool:
        """Refreshes target process PID and base addresses from the environment."""
        return True


class DaemonMemoryReader(MemoryReader):
    """Acquires memory via TCP socket connection to agent_daemon."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9999, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._file = None
        self._pid: int = 0
        self._liblogic_base: int = 0
        self._libcsharp_base: int = 0
        self._last_refresh_time: float = 0.0
        self._refresh_cooldown: float = 1.0  # Rate-limit GET_INFO to once per second
        self._consecutive_read_errors: int = 0

        self._daemon_version: str = ""
        self._daemon_build_hash: str = ""
        self._daemon_build_time: str = ""
        self._daemon_capabilities: list = []

    def connect(self) -> bool:
        try:
            self.close()
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            self._file = self._sock.makefile("r")
            # Consume handshake banner sent by native daemon upon accept
            banner_line = self._file.readline()
            if banner_line:
                try:
                    banner = json.loads(banner_line)
                    self._daemon_version = banner.get("version", "")
                    self._daemon_build_hash = banner.get("build_hash", "")
                    self._daemon_build_time = banner.get("build_time", "")
                except Exception:
                    pass
            return self.refresh_process_info(force=True)
        except Exception:
            self.close()
            return False

    def refresh_process_info(self, force: bool = False) -> bool:
        """
        Re-queries the native daemon for the current MLBB PID and liblogic.so base address.
        Rate-limited to prevent socket flooding during process startup/transitions.
        """
        import time
        now = time.time()
        if not force and (now - self._last_refresh_time) < self._refresh_cooldown:
            return self._pid > 0

        if not self._sock or not self._file:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self.timeout)
                self._sock.connect((self.host, self.port))
                self._file = self._sock.makefile("r")
            except Exception:
                self.close()
                return False

        try:
            self._sock.sendall(b"GET_INFO\n")
            line = self._file.readline()
            if not line:
                self.close()
                return False
            info = json.loads(line)
            if info.get("status") == "ok":
                old_pid = self._pid
                self._pid = int(info.get("pid", 0))
                base_raw = info.get("liblogic_base", 0)
                if isinstance(base_raw, str):
                    self._liblogic_base = int(base_raw, 16) if base_raw.startswith("0x") else int(base_raw)
                else:
                    self._liblogic_base = int(base_raw)
                csharp_raw = info.get("libcsharp_base", 0)
                if isinstance(csharp_raw, str):
                    self._libcsharp_base = int(csharp_raw, 16) if csharp_raw.startswith("0x") else int(csharp_raw)
                else:
                    self._libcsharp_base = int(csharp_raw)
                self._daemon_version = info.get("version", self._daemon_version)
                self._daemon_build_hash = info.get("build_hash", self._daemon_build_hash)
                self._consecutive_read_errors = 0
                return self._pid > 0
            return False
        except Exception:
            self.close()
            return False

    def get_info(self) -> dict:
        return {
            "pid": self._pid,
            "liblogic_base": self._liblogic_base,
            "libcsharp_base": self._libcsharp_base,
            "version": self._daemon_version,
            "build_hash": self._daemon_build_hash,
            "build_time": self._daemon_build_time,
            "capabilities": self._daemon_capabilities
        }

    def read_bytes(self, address: int, size: int) -> bytes:
        if address < 0x10000000 or address >= 0x8000000000 or size <= 0:
            return b""

        # Automatic 4KB chunking for large buffer requests
        if size > 4096:
            buf = bytearray()
            for chunk_off in range(0, size, 4096):
                chunk_len = min(4096, size - chunk_off)
                c_bytes = self.read_bytes(address + chunk_off, chunk_len)
                if not c_bytes:
                    break
                buf.extend(c_bytes)
            return bytes(buf)

        # Lazy connect / refresh if disconnected or PID is 0
        if not self._sock or not self._file:
            if not self.connect():
                return b""

        if self._pid == 0:
            if not self.refresh_process_info(force=True):
                return b""

        try:
            cmd = f"READ_MEM {self._pid} {address:x} {size}\n".encode()
            self._sock.sendall(cmd)
            line = self._file.readline()
            if not line:
                self.close()
                self._consecutive_read_errors += 1
                return b""

            resp = json.loads(line)
            if resp.get("status") == "ok":
                self._consecutive_read_errors = 0
                return bytes.fromhex(resp.get("data", ""))

            # Handle read failure (e.g. target process died or PID changed)
            self._consecutive_read_errors += 1
            if self._consecutive_read_errors >= 2:
                old_pid = self._pid
                if self.refresh_process_info():
                    if self._pid > 0 and self._pid != old_pid:
                        # Retry once with newly acquired PID
                        retry_cmd = f"READ_MEM {self._pid} {address:x} {size}\n".encode()
                        self._sock.sendall(retry_cmd)
                        retry_line = self._file.readline()
                        if retry_line:
                            retry_resp = json.loads(retry_line)
                            if retry_resp.get("status") == "ok":
                                return bytes.fromhex(retry_resp.get("data", ""))
            return b""
        except Exception:
            self.close()
            self._consecutive_read_errors += 1
            return b""

    def scan_hero(self) -> Dict[str, any]:
        """Queries the native daemon hero scanner."""
        if not self._sock or self._pid == 0:
            return {}
        try:
            self._sock.sendall(f"SCAN_HERO {self._pid}\n".encode())
            return json.loads(self._file.readline())
        except Exception:
            return {}

    def scan_battle_mgr(self, hero_hint: int = 0) -> Dict[str, any]:
        """Queries the native daemon LogicBattleManager scanner."""
        if not self._sock or self._pid == 0:
            return {}
        try:
            self._sock.sendall(f"SCAN_BATTLE_MGR {self._pid} {hero_hint:x}\n".encode())
            line = self._file.readline()
            return json.loads(line) if line else {}
        except Exception:
            return {}

    def read_class_name(self, address: int) -> str:
        """Reads IL2CPP class name for an object or class descriptor."""
        if not self._sock or self._pid == 0 or address < 0x10000000 or address >= 0x8000000000:
            return ""
        try:
            self._sock.sendall(f"READ_CLASS_NAME {self._pid} {address:x}\n".encode())
            resp = json.loads(self._file.readline())
            return resp.get("class_name", "")
        except Exception:
            return ""

    def self_test(self) -> Dict[str, any]:
        """Queries the native daemon to perform an end-to-end self-test against target process."""
        if not self._sock or self._pid == 0:
            return {"status": "error", "msg": "not_connected_or_no_pid"}
        try:
            self._sock.sendall(b"SELF_TEST\n")
            line = self._file.readline()
            return json.loads(line) if line else {}
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    def get_info(self, force_refresh: bool = False) -> Dict[str, any]:
        if force_refresh or self._pid == 0:
            self.refresh_process_info(force=force_refresh)
        return {
            "pid": self._pid,
            "liblogic_base": self._liblogic_base,
            "libcsharp_base": self._libcsharp_base,
            "connected": self._sock is not None,
            "version": self._daemon_version,
            "build_hash": self._daemon_build_hash,
            "build_time": self._daemon_build_time,
            "capabilities": self._daemon_capabilities
        }

    def close(self):
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


class MockMemoryReader(MemoryReader):
    """In-memory mock memory reader for deterministic unit testing without a live game."""

    def __init__(self):
        self._memory_map: Dict[int, bytearray] = {}
        self._pid: int = 99999
        self._liblogic_base: int = 0x737158e000
        self._connected: bool = True

    def set_process_info(self, pid: int, liblogic_base: int):
        """Sets the process PID and base address in the mock."""
        self._pid = pid
        self._liblogic_base = liblogic_base

    def simulate_process_restart(self, new_pid: int, new_liblogic_base: int, clear_memory: bool = False):
        """Simulates a game process restart with a new PID and ASLR-relocated base."""
        self._pid = new_pid
        self._liblogic_base = new_liblogic_base
        if clear_memory:
            self._memory_map.clear()

    def write_mock_bytes(self, address: int, data: bytes):
        """Sets up fake memory bytes at a specific virtual address."""
        self._memory_map[address] = bytearray(data)

    def read_bytes(self, address: int, size: int) -> bytes:
        for base_addr, buf in self._memory_map.items():
            if base_addr <= address < base_addr + len(buf):
                offset = address - base_addr
                return bytes(buf[offset:offset + size])
        return b""

    def refresh_process_info(self, force: bool = False) -> bool:
        return self._pid > 0

    def read_class_name(self, address: int) -> str:
        """Mock class name resolver."""
        return "LogicPlayer" if address >= 0x10000000 else ""

    def get_info(self, force_refresh: bool = False) -> Dict[str, any]:
        return {
            "pid": self._pid,
            "liblogic_base": self._liblogic_base,
            "connected": self._connected,
            "is_mock": True
        }
