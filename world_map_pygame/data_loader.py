"""
world_map_pygame/data_loader.py
Dataclasses Zone / God / AncientGod e função load_data().

Retorna: (zones, gods, ownership, ancient_seals, global_stats, event_log, ancient_gods)
"""
import os, json
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple

from .config import find_data_dir


# ─── DATACLASSES ──────────────────────────────────────────────────────────────

@dataclass
class Zone:
    zone_id:           str
    zone_name:         str
    lore:              str
    vertices:          list          # [[x,y], ...] world-units
    centroid:          list          # [cx, cy]
    neighboring_zones: list
    ancient_seal:      bool
    base_nature:       str
    region_id:         str
    region_name:       str
    crack_level:       int  = 0
    max_cracks:        int  = 5
    sealed_god:        Optional[str] = None


@dataclass
class God:
    god_id:           str
    god_name:         str
    nature:           str
    color_primary:    str  = "#00d9ff"
    follower_count:   int  = 0
    owned_zones:      list = field(default_factory=list)
    lore_description: str  = ""

    def rgb(self) -> Tuple[int, int, int]:
        h = self.color_primary.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


@dataclass
class AncientGod:
    """Deus antigo selado — lido da seção ancient_gods do gods.json."""
    god_id:       str
    god_name:     str
    nature:       str
    color_primary: str = "#ffffff"
    color_secondary: str = "#888888"
    seal_zone:    Optional[str] = None
    crack_level:  int  = 0
    status:       str  = "sleeping"   # sleeping | stirring | awakened | broken
    lore_description: str = ""

    def rgb(self) -> Tuple[int, int, int]:
        h = self.color_primary.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def to_dict(self) -> dict:
        """Formato compatível com EventLog._derive (acessa campos por chave)."""
        return {
            "god_id":       self.god_id,
            "god_name":     self.god_name,
            "nature":       self.nature,
            "color_primary": self.color_primary,
            "seal_zone":    self.seal_zone,
            "crack_level":  self.crack_level,
            "status":       self.status,
            "lore_description": self.lore_description,
        }


# ─── LOADER ───────────────────────────────────────────────────────────────────

def load_data(data_dir: Optional[str] = None):
    """
    Carrega world_regions.json, gods.json e world_state.json.
    Retorna:
      (zones, gods, ownership, ancient_seals, global_stats, event_log, ancient_gods)
    """
    if data_dir is None:
        data_dir = find_data_dir()

    zones:        Dict[str, Zone]        = {}
    gods:         Dict[str, God]         = {}
    ancient_gods: Dict[str, AncientGod]  = {}
    ownership:    Dict[str, Optional[str]] = {}
    ancient_seals: Dict[str, dict]       = {}
    global_stats:  dict                  = {}

    # ── Regiões / Zonas ───────────────────────────────────────────────────
    rpath = os.path.join(data_dir, "world_regions.json")
    if os.path.exists(rpath):
        with open(rpath, encoding="utf-8") as f:
            rd = json.load(f)
        for reg in rd.get("regions", []):
            for zd in reg.get("zones", []):
                z = Zone(
                    zone_id   = zd["zone_id"],
                    zone_name = zd["zone_name"],
                    lore      = zd.get("lore", ""),
                    vertices  = zd["vertices"],
                    centroid  = zd["centroid"],
                    neighboring_zones = zd.get("neighboring_zones", []),
                    ancient_seal = zd.get("ancient_seal", False),
                    base_nature  = zd.get("base_nature",
                                          reg.get("base_nature", "unclaimed")),
                    region_id   = reg["region_id"],
                    region_name = reg["region_name"],
                    crack_level = zd.get("crack_level", 0),
                    max_cracks  = zd.get("max_cracks",  5),
                    sealed_god  = zd.get("sealed_god"),
                )
                zones[z.zone_id] = z
    else:
        print(f"[WARN] world_regions.json não encontrado em {data_dir}")

    # ── Deuses (regulares + antigos) ──────────────────────────────────────
    gpath = os.path.join(data_dir, "gods.json")
    if os.path.exists(gpath):
        with open(gpath, encoding="utf-8") as f:
            gd = json.load(f)

        # Deuses regulares
        for g in gd.get("gods", []):
            raw_nature = g.get("nature_element", g.get("nature", "balanced"))
            god = God(
                god_id        = g["god_id"],
                god_name      = g["god_name"],
                nature        = raw_nature.lower(),
                color_primary = g.get("color_primary", "#00d9ff"),
                follower_count= g.get("follower_count", 0),
                owned_zones   = g.get("owned_zones", []),
                lore_description = g.get("lore_description", ""),
            )
            gods[god.god_id] = god

        # Deuses antigos (selados)
        for ag in gd.get("ancient_gods", []):
            raw_nature = ag.get("nature_element", ag.get("nature", "ancient"))
            ancient = AncientGod(
                god_id       = ag["god_id"],
                god_name     = ag["god_name"],
                nature       = raw_nature.lower(),
                color_primary  = ag.get("color_primary",   "#ffffff"),
                color_secondary= ag.get("color_secondary", "#888888"),
                seal_zone    = ag.get("seal_zone"),
                crack_level  = ag.get("crack_level", 0),
                status       = ag.get("status", "sleeping"),
                lore_description = ag.get("lore_description", ""),
            )
            ancient_gods[ancient.god_id] = ancient

    # ── Estado do mundo ───────────────────────────────────────────────────
    wpath = os.path.join(data_dir, "world_state.json")
    if os.path.exists(wpath):
        with open(wpath, encoding="utf-8") as f:
            ws = json.load(f)
        ownership     = ws.get("zone_ownership",  {})
        ancient_seals = ws.get("ancient_seals",   {})
        global_stats  = ws.get("global_stats",    {})
        raw_events    = ws.get("world_events",     [])
    else:
        ownership  = {zid: None for zid in zones}
        raw_events = []

    # Sincroniza crack_level/status dos ancient_gods com ancient_seals do state
    for ag_id, ag in ancient_gods.items():
        if ag.seal_zone and ag.seal_zone in ancient_seals:
            sd = ancient_seals[ag.seal_zone]
            ag.crack_level = sd.get("crack_level", ag.crack_level)
            ag.status      = sd.get("status",      ag.status)

    # ── EventLog ──────────────────────────────────────────────────────────
    from .world_events import EventLog
    ag_dicts = {k: v.to_dict() for k, v in ancient_gods.items()}
    event_log = EventLog(raw_events, zones, gods, ownership, ancient_seals, ag_dicts)

    return zones, gods, ownership, ancient_seals, global_stats, event_log, ancient_gods
