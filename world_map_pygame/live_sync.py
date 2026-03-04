"""
world_map_pygame/live_sync.py
Live JSON polling system for real-time world state updates.

Checks world_state.json and gods.json modification times periodically.
When changes are detected, reloads data and triggers smooth transitions.
"""
import os
import time
from typing import Optional, Dict, Callable

from .config import SYNC_POLL_INTERVAL, SYNC_TRANSITION_SPEED, find_data_dir


class LiveSync:
    """
    Polls JSON files for changes and provides smooth transition support.
    
    Usage:
        sync = LiveSync()
        sync.on_change = my_reload_callback
        
        # In game loop:
        sync.update(dt)
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = find_data_dir()
        self.data_dir = data_dir

        # Files to watch
        self._watch_files = {
            "world_state": os.path.join(data_dir, "world_state.json"),
            "gods": os.path.join(data_dir, "gods.json"),
            "regions": os.path.join(data_dir, "world_regions.json"),
        }

        # Last known modification times
        self._mtimes: Dict[str, float] = {}
        self._update_mtimes()

        # Polling timer
        self._poll_timer = SYNC_POLL_INTERVAL
        self._enabled = True

        # Transition state
        self._transitioning = False
        self._transition_t = 0.0     # 0.0 → 1.0
        self._transition_speed = SYNC_TRANSITION_SPEED

        # Ownership transition (smooth color changes)
        self._old_ownership: Dict[str, Optional[str]] = {}
        self._new_ownership: Dict[str, Optional[str]] = {}

        # Callbacks
        self.on_change: Optional[Callable] = None

        # Change tracking
        self._changes_pending = False
        self._last_change_files: list = []

    def _update_mtimes(self):
        """Record current file modification times."""
        for key, path in self._watch_files.items():
            try:
                self._mtimes[key] = os.path.getmtime(path)
            except OSError:
                self._mtimes[key] = 0.0

    def _check_changes(self) -> list:
        """Check if any watched files have changed. Returns list of changed keys."""
        changed = []
        for key, path in self._watch_files.items():
            try:
                mtime = os.path.getmtime(path)
                if mtime != self._mtimes.get(key, 0):
                    changed.append(key)
            except OSError:
                pass
        return changed

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, val: bool):
        self._enabled = val

    @property
    def transitioning(self) -> bool:
        return self._transitioning

    @property
    def transition_progress(self) -> float:
        """0.0 = old state, 1.0 = new state fully applied."""
        return self._transition_t

    def start_transition(self, old_ownership: dict, new_ownership: dict):
        """Start a smooth ownership transition animation."""
        self._old_ownership = dict(old_ownership)
        self._new_ownership = dict(new_ownership)
        self._transitioning = True
        self._transition_t = 0.0

    def get_blended_ownership(self, base_ownership: dict) -> dict:
        """
        During transition, returns ownership that smoothly changes.
        When transition_t < 0.5, returns old ownership.
        When transition_t >= 0.5, returns new ownership.
        (Actual visual blending is handled by the renderer via alpha.)
        """
        if not self._transitioning:
            return base_ownership

        if self._transition_t < 0.5:
            return self._old_ownership
        return self._new_ownership

    def update(self, dt: float):
        """Call every frame. Polls files and advances transitions."""
        # Advance ownership transition
        if self._transitioning:
            self._transition_t += dt / max(0.1, self._transition_speed)
            if self._transition_t >= 1.0:
                self._transition_t = 1.0
                self._transitioning = False

        # Poll files
        if not self._enabled:
            return

        self._poll_timer -= dt
        if self._poll_timer > 0:
            return
        self._poll_timer = SYNC_POLL_INTERVAL

        changed = self._check_changes()
        if changed:
            self._last_change_files = changed
            self._changes_pending = True
            self._update_mtimes()

            if self.on_change:
                self.on_change(changed)

    def consume_changes(self) -> bool:
        """Check and consume pending change flag. Returns True if changes were detected."""
        if self._changes_pending:
            self._changes_pending = False
            return True
        return False

    @property
    def last_change_files(self) -> list:
        return self._last_change_files
