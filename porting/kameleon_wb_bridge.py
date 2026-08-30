#!/usr/bin/env python3
"""
Kameleon Whiteboard Bridge
Connects kameleon_xournalpp (Lua plugin) to Kameleon Presenter WebSocket server.

IPC via two named FIFOs:
  /tmp/kameleon_wb_send  — Lua writes JSON lines → bridge reads → sends to KP
  /tmp/kameleon_wb_recv  — bridge writes JSON lines → Lua reads → applies strokes

Run manually or launched by the KameleonSync Lua plugin.
Usage: kameleon_wb_bridge.py [--host HOST] [--port PORT] [--board-id BOARD_ID]

Protocol messages sent/received:
  {"type":"wb","board_id":"...","action":"stroke","data":{...}}
  {"type":"wb","board_id":"...","action":"clear"}
  {"type":"wb","board_id":"...","action":"undo"}
"""

import asyncio
import json
import os
import sys
import stat
import argparse
import signal
import logging

logging.basicConfig(level=logging.INFO,
                    format='[wb-bridge] %(levelname)s %(message)s')
log = logging.getLogger('wb-bridge')

SEND_FIFO = '/tmp/kameleon_wb_send'
RECV_FIFO = '/tmp/kameleon_wb_recv'


def ensure_fifo(path: str):
    if os.path.exists(path):
        if not stat.S_ISFIFO(os.stat(path).st_mode):
            os.remove(path)
            os.mkfifo(path, 0o600)
    else:
        os.mkfifo(path, 0o600)


async def run(host: str, port: int, board_id: str):
    try:
        import websockets
    except ImportError:
        log.error('websockets library not installed — run: pip3 install websockets')
        sys.exit(1)

    ensure_fifo(SEND_FIFO)
    ensure_fifo(RECV_FIFO)

    log.info(f'Connecting to ws://{host}:{port}')

    async with websockets.connect(
        f'ws://{host}:{port}',
        ping_interval=20, ping_timeout=60,
        max_size=4 * 1024 * 1024,
    ) as ws:
        log.info('Connected to KP')

        # Introduce ourselves
        await ws.send(json.dumps({
            'type': 'hello',
            'device_name': 'kameleon_xournalpp',
        }))

        # Open recv fifo for writing (non-blocking)
        recv_fd = os.open(RECV_FIFO, os.O_WRONLY | os.O_NONBLOCK)
        recv_file = os.fdopen(recv_fd, 'w')

        async def forward_to_kp():
            """Read JSON lines from send FIFO and forward to KP WS."""
            loop = asyncio.get_event_loop()
            # Open send fifo in non-blocking mode
            fd = os.open(SEND_FIFO, os.O_RDONLY | os.O_NONBLOCK)
            f = os.fdopen(fd, 'r')
            buf = ''
            try:
                while True:
                    await asyncio.sleep(0.05)
                    try:
                        chunk = f.read(4096)
                        if chunk:
                            buf += chunk
                            while '\n' in buf:
                                line, buf = buf.split('\n', 1)
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    msg = json.loads(line)
                                    msg.setdefault('board_id', board_id)
                                    await ws.send(json.dumps(msg))
                                    log.debug(f'→ KP: {msg.get("action")}')
                                except json.JSONDecodeError as e:
                                    log.warning(f'Bad JSON from plugin: {e}')
                    except BlockingIOError:
                        pass
                    except OSError:
                        break
            finally:
                f.close()

        async def forward_from_kp():
            """Read wb messages from KP and write to recv FIFO."""
            try:
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if msg.get('type') != 'wb':
                        continue
                    # Don't echo back our own strokes
                    if msg.get('peer_id') in ('teacher',):
                        line = json.dumps(msg) + '\n'
                        try:
                            recv_file.write(line)
                            recv_file.flush()
                            log.debug(f'← KP: {msg.get("action")}')
                        except OSError:
                            pass
            except Exception as e:
                log.warning(f'WS closed: {e}')

        await asyncio.gather(
            forward_to_kp(),
            forward_from_kp(),
        )


def main():
    ap = argparse.ArgumentParser(description='Kameleon WB Bridge')
    ap.add_argument('--host',     default='localhost')
    ap.add_argument('--port',     type=int, default=9000)
    ap.add_argument('--board-id', default='')
    args = ap.parse_args()

    signal.signal(signal.SIGINT,  lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    try:
        asyncio.run(run(args.host, args.port, args.board_id))
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    except Exception as e:
        log.error(f'Fatal: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
