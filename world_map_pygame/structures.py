"""
world_map_pygame/structures.py
Procedural structure placement and pixel-art building generation.

Each zone gets structures placed based on its lore, nature, and type.
Buildings are small pixel-art sprites (8-20px) generated procedurally.
"""
import math
import random
import pygame
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from .config import (
    WORLD_W, WORLD_H, TEX_W, TEX_H,
    STRUCTURE_TYPES, NATURE_BUILDING_PALETTE,
    NATURE_COLOR, scaled,
)


# ─── DATA MODEL ──────────────────────────────────────────────────────────────

@dataclass
class Structure:
    """A single structure placed within a zone."""
    struct_type: str          # "fortress", "city", "village", etc.
    name: str                 # Display name
    world_x: float            # Position in world coords
    world_y: float
    size: int = 12            # Sprite size in pixels
    importance: int = 1       # 1=minor, 2=medium, 3=major (affects LOD visibility)
    lore: str = ""            # Short description

    @property
    def tex_pos(self) -> Tuple[int, int]:
        """Position in texture coords."""
        return (
            int(self.world_x / WORLD_W * TEX_W),
            int(self.world_y / WORLD_H * TEX_H),
        )


@dataclass
class SubDistrict:
    """A named sub-area within a zone, visible at LOD 4."""
    name: str
    world_x: float
    world_y: float
    radius: float = 60.0      # Approximate radius in world coords
    description: str = ""
    structures: List[Structure] = field(default_factory=list)


# ─── ZONE STRUCTURE DEFINITIONS ──────────────────────────────────────────────
# Maps zone_id to a list of structure templates.
# Each template: (type, name, offset_x, offset_y, importance, lore)
# offsets are relative to zone centroid, in world coords

ZONE_STRUCTURES: Dict[str, list] = {
    # ── The Northern Seas ──────────────────────────────────────────────────
    "shattered_peak": [
        ("ruins", "Sunken Observatory", -60, -20, 3, "Half-submerged tower, once tracked stellar tides."),
        ("outpost", "Fog Watchers' Buoy", 40, 10, 1, "Anchored scouts who chart the shallows."),
        ("tower", "Barnacle Spire", -20, 30, 2, "A coral-crusted pillar rising from the seabed."),
    ],
    "ashen_wastes": [
        ("ruins", "Storm-Wrack Reef", 0, -15, 3, "Ship bones piled on underwater rocks."),
        ("outpost", "Driftwood Outpost", -70, 20, 1, "Floating platform lashed together from wreckage."),
        ("village", "Sea Nomad Camp", 50, -10, 1, "Boat-dwellers who follow the currents."),
    ],
    "dead_crown": [
        ("fortress", "Bleached Rock Fort", 0, 0, 3, "A fortress on the only rock above water."),
        ("ruins", "Drowned Gateway", -50, 20, 2, "Stone arch visible at low tide."),
        ("tower", "Gull Tower", 40, -15, 1, "Seabird colony on a crumbling pillar."),
    ],

    # ── The Emerald Coast ─────────────────────────────────────────────────
    "elderwood_grove": [
        ("port", "Saltsong Harbor", 0, 0, 3, "The bay's only safe anchorage."),
        ("village", "Cliff Hamlet", -40, 30, 2, "Homes carved into the sea cliffs."),
        ("temple", "Tidekeeper's Shrine", 30, -20, 2, "Offerings to calm the waves."),
    ],
    "thornwall": [
        ("outpost", "Windmere Watch", 10, 0, 3, "Coastal lookout over the grasslands."),
        ("village", "Dune Hamlet", -30, 20, 1, "Thatched roofs among the beach grass."),
        ("outpost", "Shoreline Post", 20, -25, 1, "Patrols where sand meets green."),
    ],
    "misty_highlands": [
        ("temple", "Mist Shrine", 0, 10, 3, "Hidden in the coastal forest. Prayers dissolve into fog."),
        ("village", "Canopy Village", -30, -15, 1, "Tree-houses above the waterline."),
        ("tower", "Shore Beacon", 25, 20, 2, "Guides ships past the forested coast."),
    ],

    # ── The Worldspine ─────────────────────────────────────────────────────
    "iron_gate": [
        ("fortress", "Canopy Fortress", 0, 0, 3, "A stronghold hidden beneath the endless forest."),
        ("city", "Greenhollow Town", -50, 20, 2, "A settlement carved from the living forest."),
        ("outpost", "Treetop Lookout", 30, -30, 1, "Eyes above the canopy."),
        ("market", "Timber Market", 40, 15, 1, "Trade in rare woods and forest herbs."),
    ],
    "anvil_plains": [
        ("fortress", "Stormcrest Keep", 0, -10, 3, "A fortress hammered into the mountain rock."),
        ("village", "Snowmelt Camp", -40, 20, 1, "Shelters where the snowline begins."),
        ("outpost", "Peak Watchtower", 50, -5, 1, "Overlooks the range from a windswept ridge."),
    ],
    "warriors_rest": [
        ("fortress", "Titan's Hall", 0, 0, 3, "Ancient hall carved into the highest peaks."),
        ("temple", "Glacier Shrine", -35, 25, 2, "A frozen altar where offerings never melt."),
        ("village", "Summit Camp", 40, -10, 1, "The highest settlement in Aethermoor."),
        ("outpost", "Ridge Watch", -15, -25, 1, "Guards the mountain passes below."),
    ],

    # ── The Eastern Reach ─────────────────────────────────────────────────
    "char_fields": [
        ("port", "Dawn Harbor", 0, 0, 3, "Easternmost port, first to greet the sunrise."),
        ("ruins", "Coral Lighthouse", -40, 15, 2, "Ancient beacon crusted with sea growth."),
        ("outpost", "Eastern Buoy", 35, -10, 1, "Marker for ships approaching the continent."),
    ],
    "cinder_pit": [
        ("fortress", "Ironwood Bastion", 0, 10, 3, "Fortress built from iron-hard forest timber."),
        ("village", "Ridgewood Camp", -30, -15, 2, "Settlement where forest meets mountain."),
        ("tower", "Canopy Spire", 25, 20, 2, "Tower rising above the forest crown."),
    ],
    "dragonfault": [
        ("outpost", "Steppe Garrison", 0, 0, 3, "Military outpost overlooking the golden grass."),
        ("sacred", "Wind Altar", -40, 20, 2, "A stone circle where the steppe wind is worshipped."),
        ("village", "Grassrunner Camp", 30, -15, 1, "Nomadic herders of the amber hills."),
    ],

    # ── The Abyssal Deep ──────────────────────────────────────────────────
    "bleached_path": [
        ("ruins", "Whale-Bone Arch", 0, 0, 3, "A colossal rib cage arching above the waves."),
        ("tower", "Depth Beacon", -25, 20, 2, "Warns ships of the shelf's edge."),
        ("outpost", "Tide Watcher Raft", 30, -10, 1, "Anchored platform charting the deep."),
    ],
    "grave_hollow": [
        ("sacred", "The Void Maw", 0, 0, 3, "Where the ocean floor drops into blackness."),
        ("ruins", "Drowned Pillars", -35, 15, 2, "Stone columns visible far beneath the water."),
        ("outpost", "Abyss Marker", 20, -20, 1, "A buoy that drifts but never sinks."),
    ],
    "widows_pass": [
        ("ruins", "Ghost Fleet", 0, 0, 3, "Ships that sailed here and stopped forever."),
        ("sacred", "Still-Water Altar", -25, 15, 2, "An offering stone floating on motionless water."),
        ("outpost", "Silent Vigil", 20, -10, 1, "The loneliest watch in Aethermoor."),
    ],

    # ── The Summit Throne ─────────────────────────────────────────────────
    "slum_district": [
        ("sacred", "The Crown Peak", -30, 0, 3, "The highest point in Aethermoor. Where Caleb fell."),
        ("ruins", "The Precipice", 30, -15, 3, "Where Caleb was cast down. The God War began."),
        ("outpost", "Summit Camp", -10, 25, 1, "Harsh shelters clinging to the peak."),
        ("village", "Wind-Scoured Huts", 40, 15, 1, "The only settlement daring to exist this high."),
        ("tower", "Sky Needle", -40, -20, 1, "A spire of stone reaching into the clouds."),
    ],
    "merchant_quarter": [
        ("fortress", "Skyreach Citadel", 0, 0, 3, "A fortress on the high plateau above the clouds."),
        ("outpost", "Cloud Watch", -40, 15, 2, "Observation post with views to every horizon."),
        ("village", "Plateau Settlement", 35, -10, 2, "Hardy folk who live in thin air."),
        ("temple", "Wind Temple", 20, 25, 1, "Prayers carried directly to the gods by altitude."),
    ],
    "high_citadel": [
        ("fortress", "The Granite Bastion", 0, 0, 3, "A natural fortress of sheer mountain walls."),
        ("outpost", "Stone Gate", -35, 20, 2, "Mountain pass fortified with cut granite."),
        ("temple", "Echo Hall", 30, -15, 2, "Carved into the mountainside. Every whisper returns."),
        ("tower", "Bastion Tower", 40, 15, 1, "Tallest structure on the mountain slopes."),
    ],

    # ── The Tidal Reach ──────────────────────────────────────────────────
    "drowned_shore": [
        ("port", "Driftwood Harbor", 0, 0, 3, "A grey-sand beach where wreckage accumulates."),
        ("ruins", "Storm-Beaten Ruins", -30, 20, 2, "Half-buried foundations under grey sand."),
        ("village", "Beachcomber Camp", 25, -15, 1, "Scavengers who live off the storm's gifts."),
    ],
    "salt_flats": [
        ("ruins", "Pearl Pillars", 0, 0, 3, "Crystal formations rising from white sand below the shallows."),
        ("outpost", "Shoal Beacon", -25, 15, 1, "Marks the edge of navigable water."),
        ("sacred", "Tideless Stone", 25, -10, 2, "A rock where the water never rises or falls."),
    ],
    "deep_current": [
        ("ruins", "The Lost Anchorage", 0, 0, 3, "Chains descend into the water but hold nothing."),
        ("sacred", "Current Stone", -20, 15, 2, "An ancient marker the riptides bend around."),
        ("outpost", "Warning Buoy", 20, -10, 2, "Painted red. The last thing captains see."),
    ],

    # ── The Southern Wilds ────────────────────────────────────────────────
    "gilded_road": [
        ("port", "Moonrise Pier", 0, 0, 3, "A silver-lit pier where southern ships dock."),
        ("ruins", "Tidal Shrine", -30, 15, 2, "Half-sunken temple to a forgotten sea god."),
        ("outpost", "Bay Watch", 30, -10, 1, "Lantern post guiding nighttime arrivals."),
    ],
    "dusthaven": [
        ("city", "Darkwood Outpost", 0, 0, 3, "The only clearing in the impenetrable thicket."),
        ("sacred", "Root Altar", -30, 15, 2, "A living shrine of twisted ancient roots."),
        ("temple", "Canopy Temple", 25, -10, 1, "Built high among the oldest branches."),
        ("village", "Undergrowth Camp", 35, 20, 1, "Shelters woven from the forest itself."),
    ],
    "old_crossing": [
        ("sacred", "Coral Throne", 0, 0, 3, "A vast coral formation shaped like a seat of power."),
        ("ruins", "Luminous Reef", -25, 15, 2, "Bioluminescent reef that glows beneath the surface."),
        ("outpost", "Reef Marker", 20, -15, 1, "Navigation post above the coral shelf."),
    ],

    # ── The Forbidden Depths (Seal Zones) ──────────────────────────────────
    "dread_hollow": [
        ("temple", "The Dread Hollow", 0, 0, 3, "The water churns without wind above this seal."),
        ("sacred", "Nightmare Pool", -20, 10, 2, "Look into the shallows and see your death."),
    ],
    "twilight_nexus": [
        ("temple", "The Twilight Nexus", 0, 0, 3, "Where coast meets forest and light bleeds into dark."),
        ("sacred", "Scale of Judgment", -15, 10, 2, "A stone that tips between land and sea."),
    ],
    "golden_abyss": [
        ("temple", "The Golden Abyss", 0, 0, 3, "The water glows gold from below. Something watches."),
        ("sacred", "Offering Mound", 15, 10, 2, "Treasures dropped into the golden glow."),
    ],
}

# ─── SUB-DISTRICT DEFINITIONS ────────────────────────────────────────────────
ZONE_SUBDISTRICTS: Dict[str, list] = {
    "slum_district": [
        ("Pico do Exílio", -60, -20, 50, "Where Caleb was cast from the summit."),
        ("Borda do Precipício", 50, -10, 40, "The edge where everything began."),
        ("Acampamento dos Ventos", -10, 30, 45, "Wind-battered shelters near the peak."),
    ],
    "merchant_quarter": [
        ("Platô dos Vigilantes", -50, -15, 55, "Observation point above the clouds."),
        ("Passagem do Céu", 20, 0, 60, "The skyward passage between plateaus."),
        ("Ninho da Águia", 40, 25, 35, "Eagle nests among the crags."),
    ],
    "high_citadel": [
        ("Portão de Granito", -30, -10, 50, "The mountain's natural gateway."),
        ("Salão dos Ecos", 25, 0, 45, "Chamber where whispers carry forever."),
        ("Terraço de Pedra", 0, 25, 40, "Flat stone terrace overlooking the descent."),
    ],
    "iron_gate": [
        ("Clareira Oculta", 0, -20, 50, "A hidden clearing in the endless canopy."),
        ("Raízes Antigas", -50, 15, 40, "Where the oldest roots intertwine."),
        ("Trilha do Dossel", 40, 5, 35, "Path running above the forest floor."),
    ],
    "warriors_rest": [
        ("Crista do Titã", 0, -15, 55, "The ridge of the highest peaks."),
        ("Vale Glacial", -40, 15, 45, "A frozen valley between summits."),
        ("Passo da Névoa", 35, 10, 40, "Mountain pass wreathed in cloud."),
    ],
    "dusthaven": [
        ("Coração do Bosque", 0, 0, 55, "The darkest center of the thicket."),
        ("Clareira das Raízes", -35, 20, 40, "A rare break in the canopy."),
        ("Trilha Sombria", 30, -10, 40, "Path through permanent twilight."),
    ],
}


# ─── PIXEL-ART SPRITE GENERATOR ──────────────────────────────────────────────

class PixelArtGenerator:
    """Procedural pixel-art sprite generator for map structures."""

    _cache: Dict[Tuple[str, str, int], pygame.Surface] = {}

    @classmethod
    def generate(cls, struct_type: str, nature: str, size: int,
                 seed: int = 0) -> pygame.Surface:
        """Generate a pixel-art sprite for a structure type and nature."""
        key = (struct_type, nature, size, seed)
        if key in cls._cache:
            return cls._cache[key]

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        palette = NATURE_BUILDING_PALETTE.get(nature,
                    NATURE_BUILDING_PALETTE["balanced"])
        rng = random.Random(seed)

        gen_func = getattr(cls, f"_gen_{struct_type}", cls._gen_default)
        gen_func(surf, size, palette, rng, nature)

        cls._cache[key] = surf
        return surf

    @staticmethod
    def _gen_fortress(surf, sz, pal, rng, nature):
        """Castle/fortress: central tower with side walls."""
        # Base wall
        w = sz - 2
        h = int(sz * 0.6)
        y0 = sz - h - 1
        pygame.draw.rect(surf, pal[0], (1, y0, w, h))
        # Battlements
        for bx in range(1, w, 3):
            bw = min(2, w - bx)
            pygame.draw.rect(surf, pal[1], (bx, y0 - 2, bw, 2))
        # Central tower
        tw = max(3, sz // 3)
        th = int(sz * 0.85)
        tx = (sz - tw) // 2
        ty = sz - th
        pygame.draw.rect(surf, pal[2], (tx, ty, tw, th))
        # Tower top (pointed)
        pts = [(tx, ty), (tx + tw // 2, ty - 3), (tx + tw, ty)]
        pygame.draw.polygon(surf, pal[3], pts)
        # Window
        pygame.draw.rect(surf, (40, 35, 25, 200),
                        (tx + tw // 2, ty + th // 3, 1, 2))
        # Shadow
        pygame.draw.line(surf, (0, 0, 0, 60), (1, sz - 1), (w, sz - 1))

    @staticmethod
    def _gen_city(surf, sz, pal, rng, nature):
        """City: cluster of buildings with varying heights."""
        num_b = rng.randint(3, 5)
        bx = 1
        for _ in range(num_b):
            bw = rng.randint(2, max(3, sz // num_b))
            bh = rng.randint(sz // 3, sz - 2)
            by = sz - bh - 1
            if bx + bw > sz - 1:
                break
            c = pal[rng.randint(0, len(pal) - 1)]
            pygame.draw.rect(surf, c, (bx, by, bw, bh))
            # Roof
            pygame.draw.line(surf, pal[min(3, len(pal) - 1)],
                           (bx, by), (bx + bw, by))
            # Window dots
            if bw >= 3 and bh >= 4:
                wy = by + 2
                while wy < sz - 3:
                    pygame.draw.rect(surf, (255, 220, 120, 180),
                                    (bx + bw // 2, wy, 1, 1))
                    wy += 3
            bx += bw + rng.randint(0, 1)
        # Ground line
        pygame.draw.line(surf, (0, 0, 0, 80), (0, sz - 1), (sz - 1, sz - 1))

    @staticmethod
    def _gen_village(surf, sz, pal, rng, nature):
        """Village: small houses with pitched roofs."""
        num = rng.randint(2, 3)
        for i in range(num):
            bw = rng.randint(3, max(4, sz // num))
            bh = rng.randint(2, sz // 2)
            bx = i * (sz // num) + rng.randint(0, 2)
            by = sz - bh - 1
            if bx + bw > sz:
                break
            c = pal[rng.randint(0, min(2, len(pal) - 1))]
            pygame.draw.rect(surf, c, (bx, by, bw, bh))
            # Pitched roof
            pts = [(bx - 1, by), (bx + bw // 2, by - 2), (bx + bw, by)]
            rc = pal[min(3, len(pal) - 1)]
            pygame.draw.polygon(surf, rc, pts)
        pygame.draw.line(surf, (0, 0, 0, 60), (0, sz - 1), (sz - 1, sz - 1))

    @staticmethod
    def _gen_ruins(surf, sz, pal, rng, nature):
        """Ruins: broken walls and rubble."""
        # Broken walls
        for _ in range(rng.randint(3, 6)):
            wx = rng.randint(0, sz - 3)
            wh = rng.randint(2, sz // 2)
            ww = rng.randint(1, 3)
            wy = sz - wh - rng.randint(0, 2)
            c = tuple(max(0, v - rng.randint(0, 30)) for v in pal[0])
            pygame.draw.rect(surf, c, (wx, wy, ww, wh))
        # Rubble dots
        for _ in range(rng.randint(4, 8)):
            rx = rng.randint(1, sz - 2)
            ry = rng.randint(sz // 2, sz - 2)
            c = pal[rng.randint(0, len(pal) - 1)]
            surf.set_at((rx, ry), (*c, 180))

    @staticmethod
    def _gen_temple(surf, sz, pal, rng, nature):
        """Temple: columns with triangular roof."""
        # Platform
        pw = sz - 2
        pygame.draw.rect(surf, pal[0], (1, sz - 2, pw, 2))
        # Columns
        col_h = int(sz * 0.55)
        for cx in [sz // 4, sz * 3 // 4]:
            pygame.draw.rect(surf, pal[1], (cx, sz - 2 - col_h, 1, col_h))
        # Triangular roof
        ry = sz - 2 - col_h
        pts = [(0, ry), (sz // 2, ry - 4), (sz - 1, ry)]
        pygame.draw.polygon(surf, pal[2], pts)
        # Glow dot in center
        gc = NATURE_COLOR.get(nature, (200, 180, 140))
        cx_c, cy_c = sz // 2, sz - 2 - col_h // 2
        pygame.draw.circle(surf, (*gc, 160), (cx_c, cy_c), max(1, sz // 8))

    @staticmethod
    def _gen_market(surf, sz, pal, rng, nature):
        """Market: stalls with cloth roofs."""
        num = rng.randint(2, 3)
        for i in range(num):
            sw = max(3, sz // num - 1)
            sx_p = i * (sz // num) + 1
            sh = rng.randint(sz // 3, sz // 2)
            sy = sz - sh - 1
            # Posts
            pygame.draw.line(surf, pal[0], (sx_p, sy), (sx_p, sz - 1))
            pygame.draw.line(surf, pal[0], (sx_p + sw - 1, sy), (sx_p + sw - 1, sz - 1))
            # Roof cloth (colored based on nature)
            rc = NATURE_COLOR.get(nature, (200, 170, 80))
            pygame.draw.rect(surf, (*rc, 180), (sx_p - 1, sy - 1, sw + 1, 2))
        pygame.draw.line(surf, (0, 0, 0, 60), (0, sz - 1), (sz - 1, sz - 1))

    @staticmethod
    def _gen_outpost(surf, sz, pal, rng, nature):
        """Outpost: small watchtower with flag."""
        tw = max(2, sz // 3)
        th = int(sz * 0.7)
        tx = (sz - tw) // 2
        ty = sz - th
        pygame.draw.rect(surf, pal[0], (tx, ty, tw, th))
        # Platform at top
        pygame.draw.rect(surf, pal[1], (tx - 1, ty, tw + 2, 1))
        # Flag
        fx = tx + tw
        pygame.draw.line(surf, pal[2], (fx, ty - 3), (fx, ty))
        fc = NATURE_COLOR.get(nature, (200, 170, 80))
        pygame.draw.rect(surf, fc, (fx + 1, ty - 3, 2, 2))

    @staticmethod
    def _gen_sacred(surf, sz, pal, rng, nature):
        """Sacred site: stone circle with glow."""
        cx, cy = sz // 2, sz // 2
        r = sz // 2 - 1
        # Stone circle
        gc = NATURE_COLOR.get(nature, (100, 180, 100))
        pygame.draw.circle(surf, (*gc, 40), (cx, cy), r)
        # Stones
        for angle_d in range(0, 360, 45):
            a = math.radians(angle_d)
            sx_s = int(cx + math.cos(a) * (r - 1))
            sy_s = int(cy + math.sin(a) * (r - 1))
            pygame.draw.rect(surf, pal[0], (sx_s, sy_s, 2, 2))
        # Center glow
        pygame.draw.circle(surf, (*gc, 160), (cx, cy), max(1, r // 3))

    @staticmethod
    def _gen_port(surf, sz, pal, rng, nature):
        """Port: dock with boat shape."""
        # Dock
        dw = sz - 2
        pygame.draw.rect(surf, pal[0], (1, sz // 2, dw, 2))
        # Posts
        for px in range(2, dw, 3):
            pygame.draw.line(surf, pal[1], (px, sz // 2), (px, sz - 1))
        # Boat hull
        bx = sz // 4
        by = sz // 2 - 2
        pts = [(bx, by), (bx + sz // 3, by - 2), (bx + sz // 2, by)]
        pygame.draw.polygon(surf, pal[2], pts)
        # Mast
        mx = bx + sz // 4
        pygame.draw.line(surf, pal[3], (mx, by - 2), (mx, by - 5))

    @staticmethod
    def _gen_mine(surf, sz, pal, rng, nature):
        """Mine: cave entrance with supports."""
        cx = sz // 2
        # Ground
        pygame.draw.rect(surf, pal[0], (0, sz - 2, sz, 2))
        # Cave entrance (arch)
        ew = max(4, sz // 2)
        eh = max(3, sz // 3)
        ex = cx - ew // 2
        ey = sz - 2 - eh
        pygame.draw.rect(surf, (30, 25, 20, 200), (ex, ey, ew, eh))
        # Support beams
        pygame.draw.line(surf, pal[1], (ex, ey), (ex, sz - 2))
        pygame.draw.line(surf, pal[1], (ex + ew - 1, ey), (ex + ew - 1, sz - 2))
        pygame.draw.line(surf, pal[2], (ex, ey), (ex + ew - 1, ey))
        # Cart
        pygame.draw.rect(surf, pal[3], (ex - 3, sz - 3, 3, 2))

    @staticmethod
    def _gen_tower(surf, sz, pal, rng, nature):
        """Watchtower: narrow tall structure."""
        tw = max(3, sz // 3)
        th = int(sz * 0.8)
        tx = (sz - tw) // 2
        ty = sz - th
        pygame.draw.rect(surf, pal[0], (tx, ty, tw, th))
        # Pointed top
        pts = [(tx - 1, ty), (tx + tw // 2, ty - 3), (tx + tw, ty)]
        pygame.draw.polygon(surf, pal[1], pts)
        # Window
        wx = tx + tw // 2
        for wy in range(ty + 3, sz - 3, 4):
            pygame.draw.rect(surf, (255, 220, 120, 150), (wx, wy, 1, 1))
        # Shadow
        pygame.draw.line(surf, (0, 0, 0, 50), (tx + tw, ty), (tx + tw, sz - 1))

    @staticmethod
    def _gen_default(surf, sz, pal, rng, nature):
        """Fallback: simple rectangular building."""
        bw = sz - 4
        bh = int(sz * 0.5)
        bx = 2
        by = sz - bh - 1
        pygame.draw.rect(surf, pal[0], (bx, by, bw, bh))
        pygame.draw.line(surf, pal[1], (bx, by), (bx + bw, by))


# ─── STRUCTURE MANAGER ────────────────────────────────────────────────────────

class StructureManager:
    """
    Manages all structures in the world.
    Handles placement, sprite generation, and LOD-based rendering.
    Validates that structures are placed on land (above SEA_LEVEL).
    """

    def __init__(self, zones: dict, heightmap=None):
        self.zones = zones
        self.heightmap = heightmap  # (TEX_H, TEX_W) float32
        self.structures: Dict[str, List[Structure]] = {}  # zone_id → structures
        self.subdistricts: Dict[str, List[SubDistrict]] = {}  # zone_id → subdistricts
        self._sprites: Dict[str, Dict[str, pygame.Surface]] = {}  # zone_id → {name: sprite}
        self._icon_sprites: Dict[str, pygame.Surface] = {}  # struct_type → icon sprite
        self._initialized = False

    def _is_land(self, wx: float, wy: float) -> bool:
        """Check if a world position is on land based on heightmap."""
        if self.heightmap is None:
            return True  # no heightmap, assume land
        from .config import SEA_LEVEL
        tx = int(max(0, min(TEX_W - 1, wx / WORLD_W * TEX_W)))
        ty = int(max(0, min(TEX_H - 1, wy / WORLD_H * TEX_H)))
        return float(self.heightmap[ty, tx]) >= SEA_LEVEL

    def _find_land_near(self, wx: float, wy: float, max_tries: int = 20,
                        step: float = 15.0) -> Tuple[float, float]:
        """Find the nearest land position spiraling outward from (wx, wy)."""
        if self._is_land(wx, wy):
            return wx, wy
        rng = random.Random(hash((wx, wy)) & 0xFFFFFFFF)
        for i in range(max_tries):
            angle = rng.uniform(0, math.pi * 2)
            dist = step * (1 + i * 0.5)
            nx = wx + math.cos(angle) * dist
            ny = wy + math.sin(angle) * dist
            nx = max(10, min(WORLD_W - 10, nx))
            ny = max(10, min(WORLD_H - 10, ny))
            if self._is_land(nx, ny):
                return nx, ny
        # Fallback: use zone centroid (should always be land)
        return wx, wy

    def initialize(self):
        """Generate all structures and sprites. Call once after zones are loaded."""
        if self._initialized:
            return

        for zone_id, zone in self.zones.items():
            defs = ZONE_STRUCTURES.get(zone_id, [])
            structs = []
            sprites = {}

            for i, (stype, name, ox, oy, importance, lore) in enumerate(defs):
                cx, cy = zone.centroid
                # Add some jitter for variety
                seed = hash(f"{zone_id}_{i}") & 0xFFFFFFFF
                rng = random.Random(seed)
                jx = rng.uniform(-5, 5)
                jy = rng.uniform(-5, 5)

                world_x = cx + ox + jx
                world_y = cy + oy + jy

                # Validate land placement
                world_x, world_y = self._find_land_near(world_x, world_y)

                st = Structure(
                    struct_type=stype,
                    name=name,
                    world_x=world_x,
                    world_y=world_y,
                    size=rng.randint(*STRUCTURE_TYPES.get(stype, {}).get(
                        "size_range", (8, 12))),
                    importance=importance,
                    lore=lore,
                )
                structs.append(st)

                # Generate sprite
                sprite = PixelArtGenerator.generate(
                    stype, zone.base_nature, st.size, seed)
                sprites[name] = sprite

            self.structures[zone_id] = structs
            self._sprites[zone_id] = sprites

            # Sub-districts (also validate land placement)
            subdefs = ZONE_SUBDISTRICTS.get(zone_id, [])
            subs = []
            for sname, sox, soy, srad, sdesc in subdefs:
                cx, cy = zone.centroid
                swx, swy = self._find_land_near(cx + sox, cy + soy)
                subs.append(SubDistrict(
                    name=sname,
                    world_x=swx,
                    world_y=swy,
                    radius=srad,
                    description=sdesc,
                ))
            self.subdistricts[zone_id] = subs

        # Generate icon sprites for LOD 2 (structure icons at centroids)
        for stype, cfg in STRUCTURE_TYPES.items():
            sz = 12
            self._icon_sprites[stype] = PixelArtGenerator.generate(
                stype, "balanced", sz, hash(stype) & 0xFFFF)

        self._initialized = True

    def get_zone_structures(self, zone_id: str,
                            min_importance: int = 1) -> List[Structure]:
        """Get structures for a zone, optionally filtered by importance."""
        structs = self.structures.get(zone_id, [])
        if min_importance > 1:
            return [s for s in structs if s.importance >= min_importance]
        return structs

    def get_sprite(self, zone_id: str, struct_name: str) -> Optional[pygame.Surface]:
        """Get the pixel-art sprite for a specific structure."""
        return self._sprites.get(zone_id, {}).get(struct_name)

    def get_icon(self, struct_type: str) -> Optional[pygame.Surface]:
        """Get the icon sprite for a structure type."""
        return self._icon_sprites.get(struct_type)

    def get_subdistricts(self, zone_id: str) -> List[SubDistrict]:
        """Get sub-districts for a zone."""
        return self.subdistricts.get(zone_id, [])
