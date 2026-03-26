"""
World Map — Live Sync
File-watcher that detects changes from the combat game.
"""
import os, threading, time
try:
    from .config import DATA_DIR
    from . import data_loader
except ImportError:  # pragma: no cover - direct script fallback
    from config import DATA_DIR
    import data_loader


class LiveSync:
    def __init__(self, on_state_changed=None):
        self.on_state_changed = on_state_changed
        self._running   = False
        self._thread    = None
        self._last_mt   = 0
        self._path      = os.path.join(DATA_DIR, "world_state.json")

    def start(self):
        if self._running:
            return
        self._running = True
        if os.path.exists(self._path):
            self._last_mt = os.path.getmtime(self._path)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[LiveSync] watching for combat-game updates…")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        while self._running:
            try:
                if os.path.exists(self._path):
                    mt = os.path.getmtime(self._path)
                    if mt > self._last_mt:
                        self._last_mt = mt
                        # Retry once on JSON decode error (file may be mid-write)
                        for attempt in range(2):
                            try:
                                st = data_loader.load_world_state()
                                break
                            except (ValueError, KeyError):
                                if attempt == 0:
                                    time.sleep(0.1)
                                    continue
                                raise
                        if self.on_state_changed and st:
                            self.on_state_changed(st)
                        print("[LiveSync] state reloaded.")
            except Exception as e:
                print(f"[LiveSync] error: {e}")
            time.sleep(1.0)
