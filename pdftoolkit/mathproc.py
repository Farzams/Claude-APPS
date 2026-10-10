"""Runs math operations in a separate process, so a hard integral can be stopped without freezing the app."""
from __future__ import annotations

import multiprocessing as mp
import threading


def _serve(conn):
    import mathcore
    try:                      # warm up the heavy imports once
        import sympy  # noqa: F401
        import numpy  # noqa: F401
    except Exception:
        pass
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            break
        if msg is None:
            break
        name, kw = msg
        try:
            conn.send(("ok", mathcore.run(name, **kw)))
        except BaseException as e:      # report, never die: the app decides what to do
            conn.send(("err", f"{type(e).__name__}: {e}"))


class MathWorker:
    """One long-lived child process; restarted after a timeout."""

    def __init__(self):
        self._proc = None
        self._conn = None
        self._lock = threading.Lock()

    def start(self):
        if self._proc is not None and self._proc.is_alive():
            return
        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe()
        self._proc = ctx.Process(target=_serve, args=(child,), daemon=True)
        self._proc.start()
        child.close()
        self._conn = parent

    def stop(self):
        try:
            if self._conn:
                self._conn.send(None)
        except Exception:
            pass
        if self._proc is not None and self._proc.is_alive():
            self._proc.terminate()
        self._proc = self._conn = None

    def run(self, name: str, kw: dict, timeout: float = 60.0):
        """Blocking call (use from a worker thread). Raises TimeoutError, or RuntimeError with the message."""
        with self._lock:
            self.start()
            self._conn.send((name, kw))
            if not self._conn.poll(timeout):
                self.stop()
                raise TimeoutError(f"No answer within {int(timeout)} s. The problem may be too hard for exact methods.")
            status, payload = self._conn.recv()
        if status == "err":
            raise RuntimeError(payload)
        return payload


WORKER = MathWorker()
