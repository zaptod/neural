"""
world_map_pygame/world_events.py
Sistema de eventos do mundo (WorldEvent, EventLog).

Tipos de evento:
  ZONE_CONQUERED  — uma zona foi reivindicada por um deus
  ZONE_LOST       — um deus perdeu uma zona
  ZONE_CONTESTED  — dois deuses disputam a mesma zona
  SEAL_CRACKED    — rachaduras apareceram em um selo
  SEAL_STIRRING   — o deus selado está se mexendo
  SEAL_AWAKENED   — o deus selado está acordado, quase livre
  SEAL_BROKEN     — o selo foi destruído
  GOD_ASCENDED    — um deus ganhou poder significativo
  ANCIENT_STIRS   — um deus antigo foi perturbado

EventLog carrega os eventos do world_state.json.
Se a lista estiver vazia, deriva eventos implícitos do estado atual.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ─── Tipos de evento ──────────────────────────────────────────────────────────

class EventType(Enum):
    ZONE_CONQUERED = "zone_conquered"
    ZONE_LOST      = "zone_lost"
    ZONE_CONTESTED = "zone_contested"
    SEAL_CRACKED   = "seal_cracked"
    SEAL_STIRRING  = "seal_stirring"
    SEAL_AWAKENED  = "seal_awakened"
    SEAL_BROKEN    = "seal_broken"
    GOD_ASCENDED   = "god_ascended"
    ANCIENT_STIRS  = "ancient_stirs"


# ─── Config visual por tipo ───────────────────────────────────────────────────
# color: cor do marcador no mapa
# shape: "diamond" | "circle" | "triangle" | "square"
EVENT_VFX: Dict[EventType, dict] = {
    EventType.ZONE_CONQUERED: {"color": (210, 175,  80), "shape": "diamond"},
    EventType.ZONE_LOST:      {"color": (180,  60,  60), "shape": "diamond"},
    EventType.ZONE_CONTESTED: {"color": (255, 200,  50), "shape": "square"},
    EventType.SEAL_CRACKED:   {"color": (160,  80, 220), "shape": "triangle"},
    EventType.SEAL_STIRRING:  {"color": (200, 130, 255), "shape": "triangle"},
    EventType.SEAL_AWAKENED:  {"color": (220,  50,  50), "shape": "triangle"},
    EventType.SEAL_BROKEN:    {"color": (255,  80,  20), "shape": "triangle"},
    EventType.GOD_ASCENDED:   {"color": (200, 220, 255), "shape": "circle"},
    EventType.ANCIENT_STIRS:  {"color": (180, 140, 255), "shape": "triangle"},
}

# Cor de destaque por severidade
SEVERITY_COLOR: Dict[str, tuple] = {
    "low":      (110, 100,  80),
    "medium":   (210, 175,  80),
    "high":     (220, 110,  40),
    "critical": (220,  40,  40),
}

# Label legível por severidade
SEVERITY_LABEL: Dict[str, str] = {
    "low":      "[ LOW ]",
    "medium":   "[ MED ]",
    "high":     "[ HIGH ]",
    "critical": "[CRIT!]",
}

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ─── Dataclass de evento ──────────────────────────────────────────────────────

@dataclass
class WorldEvent:
    event_id:    str
    type:        EventType
    timestamp:   str
    description: str
    severity:    str            # "low" | "medium" | "high" | "critical"
    zone_id:     Optional[str] = None
    god_id:      Optional[str] = None
    ancient_id:  Optional[str] = None


# ─── Log de eventos ───────────────────────────────────────────────────────────

class EventLog:
    """
    Carrega e indexa eventos do mundo.
    Se world_events estiver vazio no JSON, deriva eventos implícitos
    do estado atual (zone_ownership, ancient_seals, ancient_gods).
    """

    def __init__(
        self,
        raw_events: list,
        zones:         dict,
        gods:          dict,
        ownership:     dict,
        ancient_seals: dict,
        ancient_gods:  dict,
    ):
        self.events:   List[WorldEvent]            = []
        self._by_zone: Dict[str, List[WorldEvent]] = {}

        # Parseia eventos do JSON
        for re in raw_events:
            try:
                ev = WorldEvent(
                    event_id    = re["event_id"],
                    type        = EventType(re["type"]),
                    timestamp   = re.get("timestamp", ""),
                    description = re.get("description", ""),
                    severity    = re.get("severity", "low"),
                    zone_id     = re.get("zone_id"),
                    god_id      = re.get("god_id"),
                    ancient_id  = re.get("ancient_id"),
                )
                self.events.append(ev)
            except (KeyError, ValueError):
                pass

        # Se a lista veio vazia, deriva do estado atual
        if not self.events:
            self._derive(zones, gods, ownership, ancient_seals, ancient_gods)

        # Ordena: crítico primeiro
        self.events.sort(key=lambda e: _SEV_ORDER.get(e.severity, 3))

        # Índice por zona
        for ev in self.events:
            if ev.zone_id:
                self._by_zone.setdefault(ev.zone_id, []).append(ev)

    # ── Derivação implícita ────────────────────────────────────────────────
    def _derive(
        self,
        zones, gods, ownership, ancient_seals, ancient_gods: dict
    ):
        """Gera eventos implícitos a partir do estado atual do mundo."""
        _ctr = [0]

        def _id():
            _ctr[0] += 1
            return f"evt_{_ctr[0]:03d}"

        # Conquistas de zona
        for zone_id, god_id in ownership.items():
            if not god_id:
                continue
            god  = gods.get(god_id)
            zone = zones.get(zone_id)
            if not god or not zone:
                continue
            self.events.append(WorldEvent(
                event_id    = _id(),
                type        = EventType.ZONE_CONQUERED,
                timestamp   = "2026-02-24T00:00:00",
                description = f"{god.god_name} claimed {zone.zone_name}",
                severity    = "medium",
                zone_id     = zone_id,
                god_id      = god_id,
            ))

        # Estado dos deuses antigos
        for ag in ancient_gods.values():
            sz     = ag.get("seal_zone")
            status = ag.get("status", "sleeping")
            crack  = ag.get("crack_level", 0)
            name   = ag.get("god_name", "Unknown Ancient")
            ag_id  = ag.get("god_id")

            if status == "awakened":
                self.events.append(WorldEvent(
                    event_id    = _id(),
                    type        = EventType.SEAL_AWAKENED,
                    timestamp   = "2026-02-25T06:00:00",
                    description = f"{name} has awakened — the seal fractures",
                    severity    = "critical",
                    zone_id     = sz,
                    ancient_id  = ag_id,
                ))
            elif status == "stirring":
                self.events.append(WorldEvent(
                    event_id    = _id(),
                    type        = EventType.SEAL_STIRRING,
                    timestamp   = "2026-02-24T18:00:00",
                    description = f"{name} stirs in its prison ({crack} crack(s) open)",
                    severity    = "high",
                    zone_id     = sz,
                    ancient_id  = ag_id,
                ))
            elif crack > 0:
                self.events.append(WorldEvent(
                    event_id    = _id(),
                    type        = EventType.SEAL_CRACKED,
                    timestamp   = "2026-02-23T00:00:00",
                    description = f"The seal binding {name} shows {crack} crack(s)",
                    severity    = "medium",
                    zone_id     = sz,
                    ancient_id  = ag_id,
                ))

    # ── Consultas ──────────────────────────────────────────────────────────

    def for_zone(self, zone_id: str) -> List[WorldEvent]:
        """Todos os eventos de uma zona, ordenados por severidade."""
        return self._by_zone.get(zone_id, [])

    def worst_for_zone(self, zone_id: str) -> Optional[WorldEvent]:
        """O evento mais severo de uma zona, ou None."""
        evs = self._by_zone.get(zone_id)
        if not evs:
            return None
        return min(evs, key=lambda e: _SEV_ORDER.get(e.severity, 3))

    def has_event(self, zone_id: str) -> bool:
        return zone_id in self._by_zone

    @property
    def recent(self) -> List[WorldEvent]:
        """Até 20 eventos mais relevantes (severidade decrescente)."""
        return self.events[:20]

    @property
    def critical_count(self) -> int:
        return sum(1 for e in self.events if e.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for e in self.events if e.severity == "high")
