#!/usr/bin/env python3
"""
Live Diagnostic: Tests daemon connectivity and LogicBattleManager resolution.
Connects to agent_daemon on 127.0.0.1:9999, runs GET_INFO, SCAN_BATTLE_MGR,
and GET_WORLD_SNAPSHOT, and prints all results.
"""

import socket
import json
import sys
import time

HOST = "127.0.0.1"
PORT = 9999
TIMEOUT = 15.0  # generous timeout for scanning

def send_command(sock, cmd):
    """Send a command and read the full response line."""
    print(f"\n{'='*60}")
    print(f">>> SENDING: {cmd}")
    print(f"{'='*60}")
    sock.sendall((cmd + "\n").encode("utf-8"))
    
    # Read response (newline-terminated JSON)
    buf = b""
    start = time.time()
    while time.time() - start < TIMEOUT:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                print("  [!] Connection closed by daemon")
                return None
            buf += chunk
            # Check for complete JSON lines
            if b"\n" in buf:
                lines = buf.split(b"\n")
                # Process all complete lines
                for line in lines[:-1]:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if line_str:
                        try:
                            parsed = json.loads(line_str)
                            print(f"  Response: {json.dumps(parsed, indent=2)}")
                            return parsed
                        except json.JSONDecodeError:
                            print(f"  Raw line: {line_str[:500]}")
                            return {"raw": line_str}
                buf = lines[-1]  # keep remainder
        except socket.timeout:
            continue
    
    # Timeout - print whatever we got
    if buf:
        print(f"  [TIMEOUT] Partial data: {buf[:500]}")
    else:
        print(f"  [TIMEOUT] No data received after {TIMEOUT}s")
    return None

def main():
    print("=" * 60)
    print("  MLBB Live Diagnostic")
    print(f"  Target: {HOST}:{PORT}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 60)

    # Step 1: Connect
    print("\n[1] Connecting to daemon...")
    try:
        sock = socket.create_connection((HOST, PORT), timeout=5.0)
        sock.settimeout(TIMEOUT)
        print(f"  Connected!")
    except Exception as e:
        print(f"  [FATAL] Cannot connect: {e}")
        sys.exit(1)

    # Step 2: Read handshake banner
    print("\n[2] Reading handshake banner...")
    try:
        banner_buf = b""
        start = time.time()
        while time.time() - start < 5.0:
            chunk = sock.recv(4096)
            if not chunk:
                break
            banner_buf += chunk
            if b"\n" in banner_buf:
                break
        
        banner_str = banner_buf.decode("utf-8", errors="replace").strip()
        if banner_str:
            try:
                banner = json.loads(banner_str.split("\n")[0])
                print(f"  Daemon: {banner.get('agent', '?')} v{banner.get('version', '?')}")
                print(f"  Build Hash: {banner.get('build_hash', '?')}")
                print(f"  Protocol: {banner.get('protocol', '?')}")
            except json.JSONDecodeError:
                print(f"  Raw banner: {banner_str[:300]}")
        else:
            print("  [WARN] No banner received")
    except Exception as e:
        print(f"  [WARN] Banner read error: {e}")

    # Step 3: GET_INFO
    print("\n[3] Querying daemon info...")
    info = send_command(sock, "GET_INFO")
    pid = None
    if info and isinstance(info, dict):
        pid = info.get("pid")
        base = info.get("liblogic_base") or info.get("base")
        print(f"\n  PID: {pid}")
        print(f"  liblogic base: {base}")
        if not pid or pid == 0:
            print("  [FATAL] No valid PID - is MLBB running?")
            sock.close()
            sys.exit(1)

    # Step 4: SELF_TEST
    print("\n[4] Running SELF_TEST...")
    selftest = send_command(sock, "SELF_TEST")

    # Step 5: SCAN_HERO
    print("\n[5] Scanning for LogicPlayer (SCAN_HERO)...")
    hero_cmd = f"SCAN_HERO {pid}" if pid else "SCAN_HERO"
    hero = send_command(sock, hero_cmd)
    hero_addr = None
    if hero and isinstance(hero, dict):
        hero_addr = hero.get("address") or hero.get("hero_address") or hero.get("addr")
        status = hero.get("status", "unknown")
        print(f"\n  Scan status: {status}")
        if hero_addr:
            print(f"  Hero address: {hero_addr}")
            hero_id = hero.get("hero_id") or hero.get("m_ID")
            hp = hero.get("hp")
            hp_max = hero.get("hp_max")
            level = hero.get("level")
            camp = hero.get("camp")
            class_name = hero.get("class_name") or hero.get("class")
            print(f"  Class: {class_name}")
            print(f"  Hero ID: {hero_id}, Level: {level}, Camp: {camp}")
            print(f"  HP: {hp} / {hp_max}")
        else:
            print("  [!] No hero found")

    # Step 6: SCAN_BATTLE_MGR
    print("\n[6] Scanning for LogicBattleManager (SCAN_BATTLE_MGR)...")
    if hero_addr:
        mgr_cmd = f"SCAN_BATTLE_MGR {pid} {hero_addr}"
    elif pid:
        mgr_cmd = f"SCAN_BATTLE_MGR {pid}"
    else:
        mgr_cmd = "SCAN_BATTLE_MGR"
    mgr = send_command(sock, mgr_cmd)
    if mgr and isinstance(mgr, dict):
        mgr_addr = mgr.get("mgr_addr") or mgr.get("address") or mgr.get("battle_manager")
        status = mgr.get("status", "unknown")
        print(f"\n  Scan status: {status}")
        if mgr_addr:
            print(f"  BattleManager address: {mgr_addr}")
            print(f"  Battle state: {mgr.get('battle_state', '?')}")
            print(f"  Frame time: {mgr.get('frame_time', '?')}")
            print(f"  Real self player: {mgr.get('real_self_player', '?')}")
            print(f"  Local player logic: {mgr.get('local_player_logic', '?')}")
        else:
            print("  [!] BattleManager NOT FOUND")

    # Step 7: GET_WORLD_SNAPSHOT
    print("\n[7] Requesting full world snapshot (GET_WORLD_SNAPSHOT)...")
    snap = send_command(sock, f"GET_WORLD_SNAPSHOT {pid}" if pid else "GET_WORLD_SNAPSHOT")
    if snap and isinstance(snap, dict):
        status = snap.get("status", "unknown")
        print(f"\n  Snapshot status: {status}")
        if status == "ok":
            # Summarize what we got
            self_hero = snap.get("self_hero", {})
            players = snap.get("players", [])
            turrets = snap.get("turrets", [])
            minions = snap.get("minions", [])
            monsters = snap.get("monsters", [])
            
            print(f"\n  --- SELF HERO ---")
            if self_hero:
                print(f"    Hero ID: {self_hero.get('hero_id', '?')}")
                print(f"    HP: {self_hero.get('hp', '?')} / {self_hero.get('hp_max', '?')}")
                print(f"    Level: {self_hero.get('level', '?')}")
                print(f"    Position: ({self_hero.get('pos_x', '?')}, {self_hero.get('pos_y', '?')})")
                print(f"    Camp: {self_hero.get('camp', '?')}")
                print(f"    Gold: {self_hero.get('gold', '?')}")
                print(f"    Alive: {self_hero.get('alive', '?')}")
            else:
                print(f"    [!] No self hero data")
            
            print(f"\n  --- PLAYERS ({len(players)}) ---")
            for i, p in enumerate(players):
                pid_str = p.get("hero_id", "?")
                camp = p.get("camp", "?")
                hp = p.get("hp", "?")
                hp_max = p.get("hp_max", "?")
                lvl = p.get("level", "?")
                pos = f"({p.get('pos_x', '?')}, {p.get('pos_y', '?')})"
                print(f"    [{i}] Hero {pid_str} Camp={camp} L{lvl} HP={hp}/{hp_max} Pos={pos}")
            
            print(f"\n  --- TURRETS ({len(turrets)}) ---")
            for i, t in enumerate(turrets[:6]):  # show first 6
                print(f"    [{i}] HP={t.get('hp', '?')}/{t.get('hp_max', '?')} Camp={t.get('camp', '?')} Pos=({t.get('pos_x', '?')}, {t.get('pos_y', '?')})")
            if len(turrets) > 6:
                print(f"    ... and {len(turrets) - 6} more")

            print(f"\n  --- MINIONS ({len(minions)}) ---")
            print(f"\n  --- MONSTERS ({len(monsters)}) ---")
            for i, m in enumerate(monsters[:5]):
                print(f"    [{i}] HP={m.get('hp', '?')}/{m.get('hp_max', '?')} Pos=({m.get('pos_x', '?')}, {m.get('pos_y', '?')})")
            
            bt_state = snap.get("battle_state", "?")
            frame_time = snap.get("frame_time", "?")
            print(f"\n  Battle State: {bt_state}")
            print(f"  Frame Time: {frame_time}")
        else:
            print(f"  [!] Snapshot failed: {snap.get('error', snap.get('message', 'unknown'))}")

    # Done
    print("\n" + "=" * 60)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 60)
    sock.close()

if __name__ == "__main__":
    main()
