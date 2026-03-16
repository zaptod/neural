"""
NEURAL FIGHTS — Match Stats Collector v14.0
=============================================
Lightweight in-memory collector that accumulates per-fighter combat metrics
during a match and flushes them to BattleDB when the fight ends.

Designed to have near-zero overhead: dict increments only, no allocations in hot path.

Usage in sim_combat.py:
    from data.match_stats import MatchStatsCollector

    # At fight start:
    self.stats_collector = MatchStatsCollector()
    self.stats_collector.register("Caleb")
    self.stats_collector.register("Bjorn")

    # During combat (hot path — just dict increments):
    self.stats_collector.record_hit("Caleb", "Bjorn", damage=15.3, critico=True)
    self.stats_collector.record_skill("Caleb", "Bola de Fogo", mana_cost=15)

    # At fight end:
    summary = self.stats_collector.get_summary()
    self.stats_collector.flush_to_db(match_id=42)
"""

import logging
import time
from typing import Dict, List, Optional

_log = logging.getLogger("match_stats")


class MatchStatsCollector:
    """Accumulates combat metrics during a single match."""

    def __init__(self):
        self._fighters: Dict[str, dict] = {}
        self._events: List[dict] = []
        self._start_time: float = time.monotonic()
        self._frame: int = 0

    def register(self, name: str):
        """Register a fighter at match start."""
        self._fighters[name] = {
            "damage_dealt": 0.0,
            "damage_taken": 0.0,
            "hits_landed": 0,
            "hits_received": 0,
            "attacks_attempted": 0,
            "crits_landed": 0,
            "skills_cast": 0,
            "skills_detail": {},   # {skill_name: count}
            "mana_spent": 0.0,
            "blocks": 0,
            "dodges": 0,
            "deaths": 0,
            "kills": 0,
            "max_combo": 0,
            "current_combo": 0,
        }

    def set_frame(self, frame: int):
        """Update current frame counter (call once per update tick)."""
        self._frame = frame

    # ── Hot-path recorders (dict increments only) ─────────────────────────────

    def record_hit(self, attacker: str, defender: str, damage: float,
                   critico: bool = False, elemento: str = ""):
        """Record a successful hit."""
        a = self._fighters.get(attacker)
        d = self._fighters.get(defender)
        if a:
            a["damage_dealt"] += damage
            a["hits_landed"] += 1
            if critico:
                a["crits_landed"] += 1
            a["current_combo"] += 1
            if a["current_combo"] > a["max_combo"]:
                a["max_combo"] = a["current_combo"]
        if d:
            d["damage_taken"] += damage
            d["hits_received"] += 1
            d["current_combo"] = 0  # Reset defender's combo on hit

        self._events.append({
            "frame": self._frame, "type": "hit",
            "attacker": attacker, "defender": defender,
            "damage": round(damage, 1), "crit": critico, "elem": elemento,
        })

    def record_attack_attempt(self, attacker: str):
        """Record an attack attempt (hit or miss)."""
        a = self._fighters.get(attacker)
        if a:
            a["attacks_attempted"] += 1

    def record_skill(self, caster: str, skill_name: str, mana_cost: float = 0.0):
        """Record a skill cast."""
        c = self._fighters.get(caster)
        if c:
            c["skills_cast"] += 1
            c["mana_spent"] += mana_cost
            c["skills_detail"][skill_name] = c["skills_detail"].get(skill_name, 0) + 1

        self._events.append({
            "frame": self._frame, "type": "skill",
            "caster": caster, "skill": skill_name, "cost": round(mana_cost, 1),
        })

    def record_block(self, blocker: str):
        """Record a successful block."""
        b = self._fighters.get(blocker)
        if b:
            b["blocks"] += 1

    def record_dodge(self, dodger: str):
        """Record a successful dodge/evasion."""
        d = self._fighters.get(dodger)
        if d:
            d["dodges"] += 1

    def record_death(self, victim: str, killer: str = ""):
        """Record a kill/death."""
        v = self._fighters.get(victim)
        if v:
            v["deaths"] += 1
        if killer:
            k = self._fighters.get(killer)
            if k:
                k["kills"] += 1

        self._events.append({
            "frame": self._frame, "type": "death",
            "victim": victim, "killer": killer,
        })

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """Return a summary of all fighter stats."""
        elapsed = time.monotonic() - self._start_time
        result = {}
        for name, stats in self._fighters.items():
            accuracy = (stats["hits_landed"] / max(stats["attacks_attempted"], 1))
            dps = stats["damage_dealt"] / max(elapsed, 1.0)
            result[name] = {
                **stats,
                "accuracy": round(accuracy, 3),
                "dps": round(dps, 1),
                "fight_duration": round(elapsed, 1),
            }
            # Clean up internal tracking field
            del result[name]["current_combo"]
        return result

    def get_events(self) -> List[dict]:
        """Return all recorded events."""
        return list(self._events)

    # ── Persistence ───────────────────────────────────────────────────────────

    def flush_to_db(self, match_id: int):
        """Write all events to BattleDB for the given match_id."""
        try:
            from data.battle_db import BattleDB
            db = BattleDB.get()
            if self._events:
                batch = [
                    (match_id, e["frame"], e["type"], e)
                    for e in self._events
                ]
                db.insert_events_batch(batch)
            _log.debug("Flushed %d events for match %d", len(self._events), match_id)
        except Exception as e:
            _log.debug("Failed to flush stats: %s", e)
