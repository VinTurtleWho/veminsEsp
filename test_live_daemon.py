#!/usr/bin/env python3
"""
test_live_daemon.py - Live Perception Verification Tool for VEMINS ESP

Connects to the daemon (stateless memory transport on 127.0.0.1:9999) using the
proven Perception V3 Python pipeline (DaemonMemoryReader + ProductionPerceptionOrchestrator).
"""

import time
import sys
from perception.memory_reader import DaemonMemoryReader
from perception.orchestrator import ProductionPerceptionOrchestrator
from perception.models import WorldSnapshot

def main():
    host = "127.0.0.1"
    port = 9999

    print("================================================================")
    print("           VEMINS ESP - LIVE PERCEPTION VERIFIER                ")
    print("   [Stateless Daemon Memory Reader + Python Perception V3]      ")
    print("================================================================")
    print(f"[+] Connecting to daemon transport at {host}:{port}...")

    reader = DaemonMemoryReader(host=host, port=port, timeout=2.0)
    if not reader.connect():
        print(f"[-] Connection failed to {host}:{port}")
        print("\nEnsure the daemon is running in the VM:")
        print("  su -c \"/data/local/tmp/agent_daemon &\" or \"/data/local/tmp/vemins_daemon &\"")
        sys.exit(1)

    info = reader.get_info()
    print(f"[✓] Connected successfully to daemon!")
    print(f"    • Daemon Version : {info.get('version', 'N/A')}")
    print(f"    • Target MLBB PID: {info.get('pid', 'N/A')}")
    print(f"    • liblogic Base  : 0x{info.get('liblogic_base', 0):x}")

    orchestrator = ProductionPerceptionOrchestrator(reader)
    print("\n[+] Polling Live WorldSnapshot via Perception V3 Orchestrator...")
    print("----------------------------------------------------------------")

    for i in range(10):
        try:
            snapshot: WorldSnapshot = orchestrator.get_world_snapshot()
            status_desc = orchestrator.last_discovery_status

            print(f"\n--- Frame #{i+1} (Seq: {snapshot.sequence_id}, FrameTime: {snapshot.frame_time_ms}ms) ---")
            print(f"  • Match State     : InMatch={snapshot.in_match} (State={snapshot.battle_state}) | {status_desc}")

            if snapshot.local_player:
                lp = snapshot.local_player
                print(f"  • Local Hero (Self): Hero ID {lp.hero_id} (Camp {lp.camp}) @ ({lp.pos_x:.1f}, {lp.pos_y:.1f}) | HP: {lp.hp}/{lp.hp_max}")
            else:
                print("  • Local Hero (Self): None (Waiting for active match)")

            print(f"  • Enemy Heroes    : {len(snapshot.enemies)}")
            for idx, e in enumerate(snapshot.enemies):
                print(f"    [{idx+1}] Hero ID {e.hero_id} @ ({e.pos_x:.1f}, {e.pos_y:.1f}) | HP: {e.hp}/{e.hp_max} | Level: {e.level}")

            print(f"  • Allied Heroes   : {len(snapshot.allies)}")
            print(f"  • Active Minions  : {len(snapshot.soldiers)}")
            print(f"  • Jungle Monsters : {len(snapshot.monsters)}")
            print(f"  • Active Turrets  : {len(snapshot.towers)}")

        except Exception as e:
            print(f"[-] Error reading snapshot on frame {i+1}: {e}")

        time.sleep(1.0)

    reader.close()
    print("\n[✓] Live perception test finished.")

if __name__ == "__main__":
    main()
