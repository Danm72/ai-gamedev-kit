"""Tiny client for the game's TCP bridge (newline-delimited JSON).

CLI: python3 bridge_client.py <cmd> ['{"json": "args"}']
     python3 bridge_client.py --wait-ready <port> [--pid <game pid>] [--timeout <s>]
       (exit 0 = the game answered a ping, 3 = the game process exited first, 4 = timeout)
"""
import json
import os
import select
import socket
import sys
import threading
import time

DEFAULT_PORT = int(os.environ.get("BRIDGE_PORT", "9177"))


class BridgeError(RuntimeError):
    pass


class Bridge:
    def __init__(self, host="127.0.0.1", port=DEFAULT_PORT, timeout=90.0):
        self.host, self.port, self.timeout = host, port, timeout
        self._sock = None
        self._file = None
        self._id = 0
        self._lock = threading.Lock()

    def _connect(self):
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._file = self._sock.makefile("rw", encoding="utf-8", newline="\n")

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._file = None

    def call(self, cmd, **args):
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._sock is None:
                        self._connect()
                    self._id += 1
                    self._file.write(json.dumps({"id": self._id, "cmd": cmd, "args": args}) + "\n")
                    self._file.flush()
                    line = self._file.readline()
                    if not line:
                        raise ConnectionError("bridge closed the connection")
                    break
                except (OSError, ConnectionError):
                    self.close()
                    if attempt == 2:
                        raise BridgeError(
                            f"game bridge not reachable on {self.host}:{self.port}; is the game running?"
                        )
        msg = json.loads(line)
        if not msg.get("ok"):
            raise BridgeError(msg.get("error", "unknown bridge error"))
        return msg["result"]


def wait_ready(port, timeout_s, alive=None, host="127.0.0.1"):
    """Waits until the game on port answers a ping. Returns (True, "ok"), (False, "exited") or (False, "timeout").

    The start budget timeout_s can be long: it covers a first import, or a queue on a remote box.
    It holds 1 connection: a forwarding proxy (for example an SSH tunnel to a remote box) can accept at once
    and hold the client until the game listens. So it reconnects only when the connection is refused
    (the game is not listening yet) or closed. alive() -> False when the game process has exited; then it
    returns at once. Every wait is 2 s or less.
    """
    deadline = time.time() + timeout_s
    sock, buf = None, b""
    try:
        while time.time() < deadline:
            if alive is not None and not alive():
                return False, "exited"
            if sock is None:
                try:
                    sock = socket.create_connection((host, port), timeout=2)
                    sock.sendall(b'{"id": 1, "cmd": "ping", "args": {}}\n')
                    buf = b""
                except OSError:
                    sock = None
                    time.sleep(1)
                    continue
            if not select.select([sock], [], [], 2)[0]:
                continue
            try:
                chunk = sock.recv(65536)
            except OSError:
                chunk = b""
            buf += chunk
            if b"\n" in buf:
                try:
                    if json.loads(buf.split(b"\n", 1)[0]).get("ok"):
                        return True, "ok"
                except ValueError:
                    pass
            elif chunk:
                continue
            sock.close()
            sock = None
            time.sleep(1)
        return False, "timeout"
    finally:
        if sock is not None:
            sock.close()


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--wait-ready":
    opts = dict(zip(sys.argv[3::2], sys.argv[4::2]))
    pid = int(opts["--pid"]) if opts.get("--pid") else None
    ok, why = wait_ready(int(sys.argv[2]), float(opts.get("--timeout", "1800")),
                         alive=(lambda: _pid_alive(pid)) if pid else None)
    sys.exit(0 if ok else (3 if why == "exited" else 4))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    a = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    print(json.dumps(Bridge().call(sys.argv[1], **a), indent=1))
