YaYOS Gateway SFS Module — v2
==============================
Gateway: aiohttp server on port 8772 (Tailscale LAN)
Phone app: install /opt/yayos/YaYOS-admin.apk via ADB or file manager

QUICK START
-----------
1. Load this SFS (place alongside fatdog64.sfs or drag into PuppyManager)
2. Run /root/Startup/yayos-gateway  (auto-runs at startup on fd64)
3. Install YaYOS-admin.apk on Android phones
4. Open the app and set gateway URL to http://<tailscale-ip>:8772

FEATURES
--------
- Media control (play/pause/stop/skip/volume via yay)
- Screen streaming (WebRTC H.264, fullscreen with zoom/pan on phone)
- Touch-to-mouse control (tap=click, hold=right-click, pinch=zoom view)
- PC audio streaming to phone via ALSA loopback + WebRTC
- Terminal execution, app launcher, brightness/volume, Bluetooth, firewall

AUDIO STREAMING
---------------
Audio is streamed via WebRTC alongside video. Requires snd-aloop + ALSA routing.
The startup script sets ALSA_PCMOUT=fdtee so audio played by yay goes to both
the USB speaker and the loopback capture device for streaming.
If your USB audio card is not named "Audio", edit:
  /etc/alsa/conf.d/99-yayos-fdtee.conf  → change hw:Audio,0 to match (aplay -l)

CLICK FIX
---------
Openbox (click-to-focus) grabs button-1 on unfocused windows. The gateway
pre-focuses the target window before each click so button-1 reaches the app.
This is why single-tap works on all applications, including yay controls.

GATEWAY URL (Tailscale)
-----------------------
Find your Tailscale IP:  ip addr show tailscale0
App gateway setting:     http://<that-ip>:8772

Python deps bundled under /opt/yayos/python-lib — no pip required.
