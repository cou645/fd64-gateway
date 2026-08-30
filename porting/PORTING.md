# fd64 → trixie porting notes

Scripts pulled from `fd64.sfs` (`/aufs/devbase/01100110/fd64.sfs`, mounted at
`/mnt/fd64sfs`) `usr/local/bin`, `root/Startup`, `etc/init.d` — the ones worth
carrying over to the current Debian Trixie OS as part of the
`fd64-gateway` → `trixie-gateway` rename.

## Host facts checked on this Trixie box (2026-08-28)

| Thing | State | Effect on porting |
|---|---|---|
| init | systemd 257 | replace SysV `.init` with `.service` units |
| `/sys/class/backlight/intel_backlight` | present | `fd-yayos-ctrl` brightness code works unchanged |
| `/sys/class/leds/chromeos::kbd_backlight` | present | kbd-backlight code works unchanged (still a Chromebook) |
| `amixer` + `Master` control | present | `fd-yayos-ctrl` volume/mute work unchanged |
| `net-tools` (`ifconfig`/`iwconfig`/`route`) | present | old net commands still run; `iw` is **missing** |
| `xgamma` | present | gamma code works unchanged |
| `weston`, `cage` | **missing** | `fd-yayos-waydroid start` breaks until one is installed |
| `waydroid` | present | rest of `fd-yayos-waydroid` OK |
| Wi-Fi iface | `wlp0s20f3` (not `wlan2`) | fix any hard-coded iface |

## Per-script assessment

### `yayos-gateway` — the launcher (`root/Startup/`)
Fatdog autostarts `~/Startup/*`. On Trixie this becomes the gateway's systemd
unit (or an Openbox `autostart` entry). Body does: `fuser -k 8772/tcp`,
`rm /run/fd64-gateway.sock`, `modprobe snd-aloop`, `export ALSA_PCMOUT=fdtee`,
`exec python3 /mnt/sda2/YaYOS/fd64-gateway/gateway.py`.
**Convert to** `trixie-gateway.service`:
- `ExecStartPre=/usr/bin/fuser -k 8772/tcp` (ignore failure), `-/bin/rm -f /run/trixie-gateway.sock`, `/sbin/modprobe snd-aloop`
- `Environment=ALSA_PCMOUT=fdtee` — **only if** an `fdtee` PCM exists in `~/.asoundrc` here; otherwise drop it (check before enabling audio streaming)
- `ExecStart=/root/pyqt6-venv/bin/python /aufs/devbase/trixie-gateway/gateway.py --port 8772` (system `python3` is 3.13 and has no `aiohttp`)
- `Restart=on-failure`, `WantedBy=multi-user.target`

### `fd-yayos-ctrl` — system control CLI ⭐ keep
Brightness / kbd-light / volume / mute / gamma / network status, plain sysfs +
`amixer` + `xgamma`. **Runs on this box almost as-is.** Optional cleanups:
- rename to `trixie-ctrl`
- `xgamma` → `xrandr --output <o> --gamma` (xgamma is X-only and unmaintained)
- `ifconfig`/`iwconfig`/`route` → `ip addr` / `iw dev` (needs `apt install iw`) / `ip route`
- header comment says "Fatdog64 / no systemd" — cosmetic, the code doesn't touch init

### `fd-yayos-waydroid` — Waydroid lifecycle ⭐ keep, needs fixes
- `weston --backend=x11-backend.so` → Debian weston 13+ wants `--backend=x11`
  (no `.so`), and **weston isn't installed** — `apt install weston` or switch the
  compositor step to Debian's `waydroid-container.service`
- the raw `waydroid container start &` + `sudo` dance → `systemctl start waydroid-container`
- recall the Waydroid boot-crash fix: container unit needs `Delegate=yes` (see the
  "Waydroid" project memory)
- rename to `trixie-waydroid`

### `kameleon_wb_bridge.py` — Xournal++ ↔ Kameleon Presenter whiteboard bridge ⭐ keep
Pure Python + asyncio + two FIFOs (`/tmp/kameleon_wb_send` / `_recv`). No
Fatdog assumptions. Portable as-is; belongs with the `kameleon-patch` tooling.
Just needs `python3` with `websockets` (use `/root/pyqt6-venv`).

### `stylus-proximity-v2.sh` — disable touch while stylus hovers
`xinput test` on `ELAN90FC:00 04F3:2D73` proximity events. Superseded on this box
by the evdev/uinput proxy daemon (`/root/Desktop/scripts/elan_input_daemon.py` —
see the ELAN USI2 memory), but the xinput approach still works under X11 as a
lightweight fallback. Keep as reference; don't autostart both.

### `rtirq.sh` + `99-rtirq` (init) + `ps-rt.sh` — realtime IRQ tuning for audio
For low-latency SOF / FLOW-8 capture. `ps-rt.sh` (list RT-scheduled procs) is
distro-agnostic — keep. `rtirq.sh` + `99-rtirq`: Debian ships an `rtirq`
package; compare before adopting the custom one. Convert `99-rtirq` (SysV) to
`rtirq.service` if keeping the custom version.

### `track-usage` / `usage-report` — app-usage logging
Generic shell; check for `/mnt/sda2` or Fatdog path assumptions inside, then keep.

## "Binaries" from `fd64.sfs` `/usr/local/bin` — sources ARE on `/aufs/devbase`
| Binary | Source on `/aufs/devbase` |
|---|---|
| `openbox-mcp` | `openbox-mcp/` (`openbox_mcp_server.py`) |
| `flow8-control` | `behringer/flow8-control`, `flow8/`, `Downloads/Flow8Control-main.zip` |
| `flow-8-midi` | `flow-8-midi-1.1.0/` |
| `piper` (+ voices) | `piper-stage/`, `SFS/piper.sfs` |
| `hashtext` / `hashtext-server` | `hashtext/` (already built + installed here) |
| `yayos_admin` | **not found by name** — not checked out on `/aufs/devbase`; likely built inside `yayos-apk` or on `sda2`. `YaYOS/` + `YaY-OS/` are docs/TODO only. |

## Gateway source — three copies on `/aufs/devbase`, pick the base
- **`ai-gateway/`** — the original `yay-gateway` (YaYOS). Lean: only 4 capabilities
  (`system_info, layer_control, brightness, audio`). No init files.
- **`fd64-gateway/`** — the Fatdog64 fork (this dir). **Fuller: 14 capabilities**
  (+ bluetooth, chat_history, desktop_input, lockscreen, firewall, media,
  terminal, webrtc_screen, wm, apps). SysV `.init`.
- `YaYOS-gateway-v2.sfs` — a packaged build (84 MB).
- **Recommendation:** base `trixie-gateway` on **`fd64-gateway/`** (most complete);
  apply the Debian/systemd adaptations below. `ai-gateway/` is only useful as a
  diff reference for the original, cleaner structure.
- Also present: **`nvidia-nim/`** — a separate, substantial NVIDIA-NIM integration
  project (own git repo, uv-managed, `providers/`, `messaging/`, 41 KB
  `ARCHITECTURE.md`). Its `.env` likely has keys. Relevant if `trixie-gateway`'s
  NVIDIA provider path needs more than a plain OpenAI-compatible call.

## Controls script — already ported
`scripts/controls-trixie.sh` (stemsee, 2026-08-07) is the working Trixie
equivalent of `fd-yayos-ctrl`: `yay --indicator` panel with brightness / gamma
(`xgamma -bgamma`) / volume+mic (`amixer -M`) / kbd-light / per-core CPU-freq
(`cpupower`, cores 4–7), plus an app-launcher menu. **Use this, don't re-port
`fd-yayos-ctrl`.** Its menu also documents the real runtime paths on this box:
`/root/pyqt6-venv/bin/python3` runs `/root/chameleon/{kameleon_presenter,Chameleon,
chameleon_accounting,lockscreen}.py`, `/aufs/devbase/logistics4x4-dispatcher/main.py`,
`/aufs/devbase/classroom/teacher/main.py`; gateway launcher expected at
`/root/Startup/yayos-gateway.py`; peer signal at `/root/Startup/peer-signal`.

## `yayos-gateway.py` — does NOT exist anywhere
Checked `fd64.sfs/root/Startup/`, `YaYOS-gateway-v2.sfs`, all of `/aufs/devbase`,
and live `/root/Startup/`. The launcher is **only ever the 436-byte POSIX-sh shim
`yayos-gateway`** (`fuser -k 8772/tcp` → `rm sock` → `modprobe snd-aloop` →
`export ALSA_PCMOUT=fdtee` → `exec python3 …/gateway.py`). The
`/root/Startup/yayos-gateway.py` line in `controls-trixie.sh` is a stale/forward
reference — that file was never written. It's a hint stemsee wants a Python
launcher there; writing it (or a `.service`) is part of this task.

## `YaYOS-gateway-v2.sfs` — the deploy bundle (mounted + inspected)
Layout: `/opt/yayos/gateway/{gateway.py, fd64-gateway.init}`,
`/opt/yayos/python-lib/` (all deps vendored), `/opt/yayos/YaYOS-admin.apk`
(43 MB — the admin client is an **Android APK**, separate from the desktop ELF
`yayos_admin` in `fd64.sfs`), `/etc/modprobe.d/99-yayos.conf`,
`/etc/alsa/conf.d/99-yayos-fdtee.conf`, `/root/Startup/yayos-gateway` (same shim).
- `gateway.py` in the bundle is **byte-identical** to
  `/aufs/devbase/fd64-gateway/gateway.py` → that dir is confirmed source of record.
- `.init` still hardcodes `DAEMON=/mnt/sda2/YaYOS/fd64-gateway/gateway.py`,
  `PYTHON=/usr/bin/python3` — unported.

### Staged here from the bundle
- `gateway-python-deps.txt` — exact runtime deps (aiohttp 3.13.5, **aiortc 1.14.0,
  av 16.1.0, cryptography, pylibsrtp, aioice, dnspython, ifaddr, pyee** + support
  libs). The daemon does WebRTC screen/audio streaming, so `aiortc`+`av` are
  required, not just `aiohttp`. Build `/root/pyqt6-venv` (or a dedicated venv)
  from this list — the vendored `python-lib/` has compiled extensions built for
  py3.11 and won't load on trixie's py3.13.
- `99-yayos.conf` (modprobe: auto-load `snd-aloop`)
- `99-yayos-fdtee.conf` (ALSA `pcm.fdtee` = plug → `type multi` teeing
  `hw:Audio,0` + `hw:Loopback,0` for WebRTC audio capture). **Trixie caveats:**
  rename `hw:Audio,0` to this box's card (`aplay -l`); and trixie runs
  PipeWire/Pulse, so raw-ALSA `hw:` teeing may fight the sound server — test, or
  do the tee at the PipeWire layer instead.
- `YaYOS-gateway-v2-README.txt` — deploy notes: Tailscale URL pattern
  (`http://<tailscale0-ip>:8772`), the Openbox click-to-focus pre-focus
  workaround, the "USB card not named Audio" fix.

## Trixie launcher — write one of:
1. `trixie-gateway.service` (systemd) — `ExecStartPre` = fuser-kill + rm sock +
   modprobe; `ExecStart=/root/pyqt6-venv/bin/python /aufs/devbase/trixie-gateway/gateway.py --port 8772`;
   `Environment=ALSA_PCMOUT=fdtee` only if the ported `.conf` is installed.
2. `/root/Startup/yayos-gateway.py` — the Python launcher `controls-trixie.sh`
   already points at (subprocess-manages the daemon; friendlier for the yay menu).

## Trixie build-system dirs (for the OS side, noted for context)
`fatdog-iso-builder/` (build-iso.sh / build-sfs.sh / build-multi-sfs.sh),
`trixie-systemd/`, `trixie-overlay/` (wlroots layer-shell overlay), `save-trixie/`
(persistence tree), `fatdog-initrd`.

## ⚠️ Secrets in `fd64.sfs`
`root/.yayos/gateway.json` and `root/.yayos/fd64-gateway.json` contain **live API
keys** — Anthropic, OpenAI, DeepSeek, and a **second NVIDIA key
(`nvapi-PWo8…`) pre-configured for `moonshotai/kimi-k2.6`** plus a **second
DeepSeek key** — different from the ones in
`/aufs/devbase/chameleon/api_keys.env`. Redacted copies of the *structure* are
here as `*.json.redacted`. Do not commit the real files; rotate these keys, and
have `trixie-gateway` read them from `~/.config/trixie-gateway/config.json`
(mode 0600), never from anything git-tracked.

The provider-router config shape to reuse:
```
{ "providers": {
    "<name>": { "api_key": "...", "url": "https://…", "default_model": "…" }
}, "capabilities": { "allow_unauthenticated": true|false } }
```
