#!/usr/bin/env python3
"""
IL2CPP Class Enumerator: Uses the Il2CppImage for Assembly-CSharp
to enumerate all registered classes and find LogicBattleManager.

Also determines the exact static_fields offset in this IL2CPP build.
"""

import socket
import json
import struct
import time

HOST = "127.0.0.1"
PORT = 9999
TIMEOUT = 15.0

class DC:
    def __init__(self):
        self.sock = socket.create_connection((HOST, PORT), timeout=5.0)
        self.sock.settimeout(TIMEOUT)
        self.buf = b""
        self._read_line()
    
    def _read_line(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(8192)
            if not chunk:
                return None
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("utf-8", errors="replace").strip()
    
    def cmd(self, command):
        self.sock.sendall((command + "\n").encode("utf-8"))
        line = self._read_line()
        if line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return {"raw": line}
        return None
    
    def read_mem(self, pid, addr, size):
        resp = self.cmd(f"READ_MEM {pid} 0x{addr:x} {size}")
        if resp and resp.get("status") == "ok":
            return bytes.fromhex(resp.get("data", ""))
        return None
    
    def read_u64(self, pid, addr):
        data = self.read_mem(pid, addr, 8)
        if data and len(data) == 8:
            return struct.unpack("<Q", data)[0]
        return None
    
    def read_u32(self, pid, addr):
        data = self.read_mem(pid, addr, 4)
        if data and len(data) == 4:
            return struct.unpack("<I", data)[0]
        return None
    
    def read_u16(self, pid, addr):
        data = self.read_mem(pid, addr, 2)
        if data and len(data) == 2:
            return struct.unpack("<H", data)[0]
        return None
    
    def read_string(self, pid, addr, maxlen=64):
        data = self.read_mem(pid, addr, maxlen)
        if not data:
            return None
        try:
            end = data.index(0)
            return data[:end].decode("ascii", errors="replace")
        except ValueError:
            return data.decode("ascii", errors="replace")
    
    def read_class_name(self, pid, addr):
        resp = self.cmd(f"READ_CLASS_NAME {pid} 0x{addr:x}")
        if resp and resp.get("status") == "ok":
            return resp.get("class_name", "")
        return None

def is_ptr(v):
    return v is not None and 0x10000000 <= v < 0x800000000000

def main():
    c = DC()
    info = c.cmd("GET_INFO")
    pid = info["pid"]
    liblogic_base = int(info["liblogic_base"], 16)
    print(f"PID: {pid}, liblogic: 0x{liblogic_base:x}")
    
    hero = c.cmd(f"SCAN_HERO {pid}")
    hero_ptr = int(hero["hero_ptr"], 16)
    print(f"Hero: 0x{hero_ptr:x}, Level={hero['level']}")
    
    hero_klass = c.read_u64(pid, hero_ptr)
    print(f"Hero Il2CppClass: 0x{hero_klass:x}")
    
    # ============================================================
    # Step 1: Determine exact Il2CppClass layout for this build
    # ============================================================
    print(f"\n{'='*60}")
    print("Step 1: Determine Il2CppClass layout")
    print(f"{'='*60}")
    
    # We know:
    # +0x00: Il2CppImage* image -> "Assembly-CSharp.dll"
    # +0x10: const char* name -> "LogicPlayer"
    # +0x18: const char* namespaze -> "Battle"
    
    # Let's find parent by looking for another Il2CppClass that has
    # name "LogicFighter" (LogicPlayer extends LogicFighter)
    # parent is typically at +0x30 in some builds or +0x48 in others
    
    print("\n  Searching for parent class (should be LogicFighter)...")
    for off in range(0x20, 0x100, 8):
        ptr = c.read_u64(pid, hero_klass + off)
        if is_ptr(ptr):
            # Check if this pointer leads to an Il2CppClass
            # Il2CppClass should have image at +0x00 and name at +0x10
            sub_image = c.read_u64(pid, ptr)
            if is_ptr(sub_image):
                sub_name_ptr = c.read_u64(pid, ptr + 0x10)
                if is_ptr(sub_name_ptr):
                    sub_name = c.read_string(pid, sub_name_ptr)
                    if sub_name and sub_name[0].isalpha() and len(sub_name) > 2:
                        sub_ns_ptr = c.read_u64(pid, ptr + 0x18)
                        sub_ns = c.read_string(pid, sub_ns_ptr) if is_ptr(sub_ns_ptr) else ""
                        print(f"    +0x{off:02x}: 0x{ptr:x} -> name=\"{sub_name}\", ns=\"{sub_ns}\"")
                        
                        if sub_name == "LogicFighter":
                            print(f"    *** PARENT FOUND at offset +0x{off:02x}! ***")
    
    # ============================================================
    # Step 2: Find static_fields offset
    # ============================================================
    print(f"\n{'='*60}")
    print("Step 2: Find static_fields offset")
    print(f"{'='*60}")
    
    # LogicBattleManager has a static Instance field at static_fields+0x0
    # We need to first find a class we KNOW has static fields,
    # then determine the static_fields offset.
    
    # LogicPlayer doesn't have obvious static fields we can validate.
    # But we can check: Il2CppClass typically stores static_fields
    # after the vtable/methods pointers.
    # Common offsets: 0xb0, 0xb8, 0xc0
    
    # For LogicPlayer, let's check what's at these offsets:
    # We need to find a static field we can validate
    
    # Actually, let's use a DIFFERENT approach:
    # If we can find the Il2CppClass for LogicBattleManager,
    # we can read Instance from static_fields+0x0.
    # But to find Il2CppClass for LogicBattleManager, we need
    # to enumerate classes in the same assembly.
    
    # ============================================================
    # Step 3: Enumerate classes via Il2CppImage
    # ============================================================
    print(f"\n{'='*60}")
    print("Step 3: Enumerate classes via Il2CppImage")
    print(f"{'='*60}")
    
    image_ptr = c.read_u64(pid, hero_klass)
    print(f"\n  Il2CppImage: 0x{image_ptr:x}")
    
    # Il2CppImage structure (varies by version):
    # +0x00: const char* name         -> "Assembly-CSharp.dll"
    # +0x08: const char* nameNoExt    -> "Assembly-CSharp"  
    # +0x10: Il2CppAssembly* assembly
    # +0x18: TypeDefinitionIndex typeStart
    # +0x1c: uint32_t typeCount
    # OR in some versions:
    # +0x18: Il2CppMetadataTypeHandle* typeStart
    # +0x20: uint32_t typeCount
    
    img_data = c.read_mem(pid, image_ptr, 128)
    if img_data:
        print("\n  Il2CppImage raw fields:")
        for off in range(0, 64, 8):
            val = struct.unpack("<Q", img_data[off:off+8])[0]
            lo32 = struct.unpack("<I", img_data[off:off+4])[0]
            hi32 = struct.unpack("<I", img_data[off+4:off+8])[0]
            
            tag = ""
            if is_ptr(val):
                s = c.read_string(pid, val)
                if s and s.isprintable() and len(s) > 1:
                    tag = f' -> "{s}"'
                else:
                    tag = " [ptr]"
            else:
                tag = f" (u32: {lo32}, {hi32})"
            
            print(f"    +0x{off:02x}: 0x{val:016x}{tag}")
    
    # ============================================================
    # Step 4: Use s_Il2CppMetadataRegistration to find all classes
    # ============================================================
    print(f"\n{'='*60}")
    print("Step 4: Try Il2CppClass** array near klass pointer")
    print(f"{'='*60}")
    
    # In IL2CPP, all class descriptors are allocated from the same pool.
    # The hero_klass is at 0x6e061b3038.
    # Other class descriptors should be NEARBY in memory.
    # Let's scan nearby addresses for Il2CppClass descriptors
    # that have name="LogicBattleManager" or similar.
    
    klass_page = hero_klass & ~0xFFF
    print(f"\n  Scanning for Il2CppClass descriptors near hero_klass (0x{hero_klass:x})...")
    
    battle_mgr_klass = None
    
    # Scan ±1MB around the klass pointer in 8-byte steps
    # But that's too many reads. Let's be smarter.
    # Il2CppClass structs are typically ~256 bytes.
    # Let's check every 256 bytes (or try smaller steps near klass)
    
    # Actually, in IL2CPP the classes are stored in an array:
    # s_Il2CppMetadataRegistration.types[]
    # Each entry is a TypeDefinition.
    # The Il2CppClass** for all classes is a flat array.
    
    # Let's just scan by reading class names at offsets from hero_klass
    # The klass descriptors are likely contiguous
    
    # Read a large chunk around hero_klass
    SCAN_RANGE = 0x200000  # 2MB
    STEP = 0x10  # Try every 16 bytes (Il2CppClass might not be 256-aligned)
    
    checked = 0
    found_classes = []
    
    # Since we can't read 2MB at once, let's read in chunks and scan
    # Actually this will be too many READ_MEM calls. Let's be smarter.
    
    # Read 4KB chunks and scan for patterns
    for chunk_off in range(-0x40000, 0x40000, 4096):
        chunk_addr = hero_klass + chunk_off
        if chunk_addr < 0x10000000:
            continue
        
        data = c.read_mem(pid, chunk_addr, 4096)
        if not data:
            continue
        
        # Scan for Il2CppClass signatures:
        # At any offset where we find a pointer-like value at +0x00
        # (which would be the image ptr), and at +0x10 is also a pointer
        # (which would be the name ptr), check if name is "LogicBattleManager"
        
        for off in range(0, len(data) - 0x20, 8):
            img = struct.unpack("<Q", data[off:off+8])[0]
            if img != struct.unpack("<Q", img_data[0:8])[0]:
                # image pointer doesn't match Assembly-CSharp
                continue
            
            # This entry has the same Il2CppImage as hero's class!
            name_val = struct.unpack("<Q", data[off+0x10:off+0x18])[0]
            if not is_ptr(name_val):
                continue
            
            name = c.read_string(pid, name_val)
            if not name or not name[0].isalpha():
                continue
            
            checked += 1
            abs_addr = chunk_addr + off
            
            if "BattleManager" in name:
                ns_val = struct.unpack("<Q", data[off+0x18:off+0x20])[0]
                ns = c.read_string(pid, ns_val) if is_ptr(ns_val) else ""
                print(f"    *** FOUND: 0x{abs_addr:x} -> {ns}.{name} ***")
                found_classes.append((abs_addr, name, ns))
                battle_mgr_klass = abs_addr
            
            # Also log any Battle-related classes
            if name.startswith("Logic") and checked <= 200:
                ns_val = struct.unpack("<Q", data[off+0x18:off+0x20])[0]
                ns = c.read_string(pid, ns_val) if is_ptr(ns_val) else ""
                if ns == "Battle":
                    if len(found_classes) < 30:
                        found_classes.append((abs_addr, name, ns))
    
    print(f"\n  Checked {checked} class candidates in {0x80000 // 4096} pages")
    
    if battle_mgr_klass:
        print(f"\n  === FOUND LogicBattleManager Il2CppClass at 0x{battle_mgr_klass:x} ===")
        
        # Now find static_fields and read Instance
        print("\n  Reading Il2CppClass fields:")
        mgr_klass_data = c.read_mem(pid, battle_mgr_klass, 256)
        if mgr_klass_data:
            # Dump all pointer fields
            for off in range(0, 256, 8):
                val = struct.unpack("<Q", mgr_klass_data[off:off+8])[0]
                if is_ptr(val):
                    # Try reading as static_fields: Instance at +0x0
                    instance = c.read_u64(pid, val)
                    tag = ""
                    if instance and is_ptr(instance):
                        cls = c.read_class_name(pid, instance)
                        if cls and "Battle" in cls:
                            tag = f" -> Instance? cls={cls}"
                        elif cls:
                            tag = f" -> [{cls}]"
                    print(f"    +0x{off:02x}: 0x{val:x}{tag}")
        
        # Try common static_fields offsets
        print("\n  Trying static_fields at common offsets:")
        for sf_off in [0xb0, 0xb8, 0xc0, 0xc8, 0xd0, 0xd8]:
            sf = c.read_u64(pid, battle_mgr_klass + sf_off)
            if is_ptr(sf):
                instance = c.read_u64(pid, sf)
                if is_ptr(instance):
                    cls = c.read_class_name(pid, instance)
                    print(f"    +0x{sf_off:02x}: sf=0x{sf:x} -> Instance=0x{instance:x} [{cls}]")
                    
                    if cls and "Battle" in cls:
                        print(f"\n  *** BATTLE MANAGER INSTANCE FOUND: 0x{instance:x} ***")
                        
                        # Full validation
                        state = c.read_u32(pid, instance + 0x180)
                        frame = c.read_u32(pid, instance + 0x19c)
                        rs = c.read_u64(pid, instance + 0x200)
                        lp = c.read_u64(pid, instance + 0x0a0)
                        dp = c.read_u64(pid, instance + 0x0a8)
                        
                        print(f"    _m_eState (+0x180): {state}")
                        print(f"    m_uiFrameTime (+0x19c): {frame}")
                        print(f"    m_RealSelfPlayer (+0x200): 0x{rs:x}" if rs else "    m_RealSelfPlayer: NULL")
                        print(f"    m_LocalPlayerLogic (+0x0a0): 0x{lp:x}" if lp else "    m_LocalPlayerLogic: NULL")
                        print(f"    m_dicPlayerLogic (+0x0a8): 0x{dp:x}" if dp else "    m_dicPlayerLogic: NULL")
                        
                        if rs:
                            rs_cls = c.read_class_name(pid, rs)
                            print(f"    RealSelfPlayer class: {rs_cls}")
                            print(f"    RealSelfPlayer == hero? {rs == hero_ptr}")
                        if lp:
                            lp_cls = c.read_class_name(pid, lp)
                            print(f"    LocalPlayerLogic class: {lp_cls}")
                            print(f"    LocalPlayerLogic == hero? {lp == hero_ptr}")
    else:
        print("\n  LogicBattleManager Il2CppClass NOT FOUND in scanned range")
        print("  May need to extend scan range or try different approach")
        
        # Print what Battle-related classes we DID find
        if found_classes:
            print(f"\n  Battle-related classes found:")
            for addr, name, ns in found_classes[:20]:
                print(f"    0x{addr:x}: {ns}.{name}")
    
    print(f"\n{'='*60}")
    print("  CLASS ENUMERATION COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
