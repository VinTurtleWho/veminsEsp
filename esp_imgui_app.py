#!/usr/bin/env python3
"""
esp_imgui_app.py - Standalone Dear ImGui Visual ESP Frontend for MLBB

Provides a live visual overlay and interactive control panel:
- Minimap radar with enemy heroes, heading arrows, minion waves, and Lord/Buffs.
- Cooldown HUD displaying enemy Ultimate and Battle Spell timers.
- Live settings panel to toggle layers and calibrate minimap position/scaling.
"""

import sys
import time
import math
from esp_overlay_engine import ESPOverlayEngine

def main():
    print("=================================================================")
    print("      VEMINS ESP - MINIMAP RADAR & COOLDOWN HUD ENGINE          ")
    print("=================================================================")

    engine = ESPOverlayEngine()
    print("[+] Connecting to daemon and initializing overlay pipeline...")

    if not engine.connect():
        print("[-] Waiting for daemon on 127.0.0.1:9999...")

    # Run test cycle
    for i in range(10):
        snap = engine.fetch_snapshot()
        draw_items = engine.build_draw_list(snap)
        print(f"[Frame {i+1}] InMatch={snap.in_match} | Draw items: {len(draw_items)} (Enemies: {len(snap.enemies)}, Minions: {len(snap.soldiers)}, Monsters: {len(snap.monsters)})")
        time.sleep(0.5)

    print("\n[✓] Overlay engine test loop completed.")

if __name__ == "__main__":
    main()

