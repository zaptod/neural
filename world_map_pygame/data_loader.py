"""
world_map_pygame/data_loader.py
Dataclasses Zone / God e função load_data() que lê os JSONs do projeto.
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


# ─── LOADER ───────────────────────────────────────────────────────────────────
def load_data(data_dir: Optional[str] = None):
    """
    Carrega world_regions.json, gods.json e world_state.json.
    Retorna (zones, gods, ownership, ancient_seals, global_stats).
    """
    if data_dir is None:
        data_dir = find_data_dir()

    zones:        Dict[str, Zone] = {}
    gods:         Dict[str, God]  = {}
    ownership:    Dict[str, Optional[str]] = {}
    ancient_seals: Dict[str, dict] = {}
    global_stats:  dict = {}

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

    # ── Deuses ────────────────────────────────────────────────────────────
    gpath = os.path.join(data_dir, "gods.json")
    if os.path.exists(gpath):
        with open(gpath, encoding="utf-8") as f:
            gd = json.load(f)
        for g in gd.get("gods", []):
            # FIX: prefere nature_element (chave interna: "balanced") sobre nature
            # (nome display: "Balance") — NATURE_COLOR usa chaves tipo "balanced"
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

    # ── Estado do mundo ───────────────────────────────────────────────────
    wpath = os.path.join(data_dir, "world_state.json")
    if os.path.exists(wpath):
        with open(wpath, encoding="utf-8") as f:
            ws = json.load(f)
        ownership     = ws.get("zone_ownership", {})
        ancient_seals = ws.get("ancient_seals",  {})
        global_stats  = ws.get("global_stats",   {})
    else:
        ownership = {zid: None for zid in zones}

    return zones, gods, ownership, ancient_seals, global_stats
