# VEMINS // ESP — Operator Quick Start Guide

This guide covers building, installing, and configuring the VeminsESP floating overlay and root telemetry daemon.

---

## 1. Prerequisites
* **Android Device or Virtual Machine (VM)**: Android 8.0+ (ARM64-v8a).
* **Root Access**: Root permissions (`su`) are required for the standalone daemon to read `/proc/$PID/mem`.
* **Overlay Permission**: `SYSTEM_ALERT_WINDOW` ("Display over other apps").

---

## 2. Building the Project

### A. Build the Native Daemon (`vemins_daemon`)
In your Termux or Linux environment:
```bash
cd /data/data/com.termux/files/home/veminsEsp
./build_vemins_daemon.sh
```
* **Output**: `vemins_daemon` binary automatically staged to `vemins_overlay_app/app/src/main/assets/bin/vemins_daemon` and `/sdcard/vemins_daemon`.

### B. Build the Android Overlay App (`veminsEsp.apk`)
```bash
cd /data/data/com.termux/files/home/veminsEsp/vemins_overlay_app
./build_apk.sh
```
* **Output**: Production-signed APK generated at `veminsEsp.apk` and copied to `/storage/emulated/0/veminsEsp.apk`.

---

## 3. Installation & First Launch

1. Install **`veminsEsp.apk`** from your device's Downloads folder.
2. Open the **VEMINS ESP** app.
3. If prompted, tap **"GRANT OVERLAY PERMISSION"** to authorize drawing over other apps.
4. Tap **"START OVERLAY"** on the master control card:
   - The floating **Apex 'V' trigger puck** will appear docked to your screen edge.
   - The app will automatically launch and supervise the embedded root telemetry daemon.

---

## 4. In-Game HUD Calibration

Once in a practice match or classic game:

### Quick Presets (1-Tap Setup)
Tap the floating **'V' puck** to open the in-game Mod Menu, then select one of the top preset chips:
* **`[STD 1080P]`**: Standard 16:9 / 18:9 1080p displays (Minimap: `X=75, Y=15, Size=320`).
* **`[45° DIAMOND]`**: Rotates the minimap radar 45° to match isometric diamond perspective.
* **`[NOTCH SAFE]`**: Insets the minimap to avoid camera cutouts and notch bezels (`X=110, Y=20`).
* **`[ULTRAWIDE]`**: Expanded scale for 20:9 / 21:9 wide-aspect gaming phones.

### Fine-Tuning with Stepper Sliders
* Use the **`[-]`** and **`[+]`** micro-step buttons on any slider row to adjust coordinates pixel-by-pixel until the overlay radar box aligns with the in-game minimap.
* Tap **"SAVE CONFIG"** in the **SYSTEM** tab to persist your settings across app restarts.

---

## 5. In-Game Controls & Gestures

| Gesture / Action | Result |
| :--- | :--- |
| **Single Tap Puck** | Expands or collapses the Floating Mod Menu. |
| **Double Tap Puck** | Toggles **Stealth Ghost Mode** (5% opacity, stream/tournament safe). |
| **Drag Puck** | Repositions the trigger puck along the left or right screen bezel (magnetic snap). |
| **Drag Menu Header** | Repositions the entire Mod Menu window across your screen. |

---

## 6. Standalone VM Setup (Optional)

If running the overlay inside a virtual Android environment (e.g. VMOS / F1VM / Twoyi):
1. Copy `vemins_daemon` to the VM:
   ```bash
   su -c "cp /sdcard/vemins_daemon /data/local/tmp/vemins_daemon && chmod 755 /data/local/tmp/vemins_daemon"
   ```
2. Start the daemon in background:
   ```bash
   su -c "/data/local/tmp/vemins_daemon &"
   ```
3. Open **VeminsESP** in the VM — it will instantly connect to `127.0.0.1:9999` and begin streaming telemetry.
