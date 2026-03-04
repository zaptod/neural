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
    # ── The Void Ridge ────────────────────────────────────────────────────
    "shattered_peak": [
        ("ruins", "Broken Observatory", -60, -20, 3, "Once tracked the movements of gods."),
        ("outpost", "Storm Watchers' Camp", 40, 10, 1, "Scouts brave enough to watch the void."),
        ("tower", "Void Spire", -20, 30, 2, "A twisted tower crackling with void energy."),
    ],
    "ashen_wastes": [
        ("ruins", "The Charnel", 0, -15, 3, "Bones of a forgotten army."),
        ("outpost", "Ashen Outpost", -70, 20, 1, "Barely standing against the wind."),
        ("village", "Dustwalker Camp", 50, -10, 1, "Nomads who breathe ash."),
    ],
    "dead_crown": [
        ("fortress", "Crown Ruins", 0, 0, 3, "Broken throne of a dead kingdom."),
        ("ruins", "Shattered Gate", -50, 20, 2, "The kingdom's last defense."),
        ("tower", "Silent Tower", 40, -15, 1, "No sound escapes its walls."),
    ],

    # ── The Verdant Reach ─────────────────────────────────────────────────
    "elderwood_grove": [
        ("sacred", "The Heartwood", 0, 0, 3, "Oldest tree in Aethermoor."),
        ("village", "Root Town", -40, 30, 2, "Built within the roots of giants."),
        ("temple", "Druid's Circle", 30, -20, 2, "Stones older than memory."),
    ],
    "thornwall": [
        ("fortress", "Thorn Gate", 10, 0, 3, "Living thorns form the walls."),
        ("village", "Briar Hamlet", -30, 20, 1, "Hidden behind the wall of thorns."),
        ("outpost", "Ranger Post", 20, -25, 1, "Eyes of the forest watch here."),
    ],
    "misty_highlands": [
        ("temple", "Fog Shrine", 0, 10, 3, "Prayers dissolve into mist."),
        ("village", "Highland Settlement", -30, -15, 1, "They navigate by sound alone."),
        ("tower", "Beacon Tower", 25, 20, 2, "Lit only when danger is near."),
    ],

    # ── The Iron Heartlands ───────────────────────────────────────────────
    "iron_gate": [
        ("fortress", "The Iron Gate", 0, 0, 3, "The great northern passage."),
        ("city", "Gatekeep Town", -50, 20, 2, "Merchants and soldiers."),
        ("outpost", "Northern Watchtower", 30, -30, 1, "First to see invaders."),
        ("market", "Gate Market", 40, 15, 1, "Trading post for travelers."),
    ],
    "anvil_plains": [
        ("fortress", "Battle Arena", 0, -10, 3, "Where champions are forged."),
        ("village", "Smith's Rest", -40, 20, 1, "Blacksmiths serve the war machine."),
        ("outpost", "Scout Ridge", 50, -5, 1, "Overlooks the entire plain."),
    ],
    "warriors_rest": [
        ("city", "Champions' Hall", 0, 0, 3, "Hall of legendary fighters."),
        ("temple", "Memorial Shrine", -35, 25, 2, "Names of every fallen warrior."),
        ("village", "Veteran's Village", 40, -10, 1, "Retired warriors live here."),
        ("market", "Arms Market", -15, -25, 1, "Best weapons in the heartlands."),
    ],

    # ── The Ember Barrens ─────────────────────────────────────────────────
    "char_fields": [
        ("ruins", "Burned Citadel", 0, 0, 3, "A fortress consumed by its own fire."),
        ("mine", "Carbon Mine", -40, 15, 2, "Digging through ancient ash."),
        ("outpost", "Ember Watch", 35, -10, 1, "Guards against fire storms."),
    ],
    "cinder_pit": [
        ("mine", "The Deep Forge", 0, 10, 3, "A forge powered by the earth's wound."),
        ("ruins", "Slag Hill", -30, -15, 2, "Ruins melted into the rock."),
        ("tower", "Flame Spire", 25, 20, 2, "Burns eternally atop the pit."),
    ],
    "dragonfault": [
        ("ruins", "Impact Crater", 0, 0, 3, "Whatever fell here left a scar forever."),
        ("sacred", "Dragon Bones", -40, 20, 2, "Petrified remains of something massive."),
        ("outpost", "Fault Watch", 30, -15, 1, "Monitors seismic activity."),
    ],

    # ── The Bone Marches ──────────────────────────────────────────────────
    "bleached_path": [
        ("ruins", "Bone Road", 0, 0, 3, "Paved with the bones of fleeing refugees."),
        ("tower", "Death Beacon", -25, 20, 2, "Warns travelers to turn back."),
        ("outpost", "Last Hope Camp", 30, -10, 1, "Final rest before the darkness."),
    ],
    "grave_hollow": [
        ("temple", "Silent Crypt", 0, 0, 3, "Even prayers don't echo here."),
        ("ruins", "Hollow Graves", -35, 15, 2, "Graves that were emptied from below."),
        ("village", "Mourner's Den", 20, -20, 1, "Those who refuse to leave the dead."),
    ],
    "widows_pass": [
        ("city", "Widow's Fortress", 0, 0, 3, "City of war widows. None are welcome."),
        ("market", "Black Market", -25, 15, 2, "Trade in forbidden goods."),
        ("tower", "Widow's Watch", 20, -10, 1, "Guards against male intruders."),
    ],

    # ── The Crown Districts ───────────────────────────────────────────────
    "slum_district": [
        ("city", "The Slums", -30, 0, 3, "Where Caleb was born and left to die."),
        ("ruins", "The Abyss Edge", 30, -15, 3, "Where Caleb was thrown. The God War began."),
        ("market", "Rat Market", -10, 25, 1, "Stolen goods and desperate trades."),
        ("village", "Beggar's Row", 40, 15, 1, "The poorest street in Aethermoor."),
        ("tower", "Broke Tower", -40, -20, 1, "Leaning, crumbling, still standing."),
    ],
    "merchant_quarter": [
        ("city", "Grand Bazaar", 0, 0, 3, "Heart of trade in all Aethermoor."),
        ("market", "Gold Exchange", -40, 15, 2, "Where fortunes are made and lost."),
        ("city", "Merchant Guildhall", 35, -10, 2, "Power behind the throne."),
        ("temple", "Coin Temple", 20, 25, 1, "They worship commerce here."),
    ],
    "high_citadel": [
        ("fortress", "The High Citadel", 0, 0, 3, "Throne of a dead king."),
        ("city", "Royal Quarter", -35, 20, 2, "Where nobility once lived."),
        ("temple", "Hall of Memory", 30, -15, 2, "Records of all Aethermoor's history."),
        ("tower", "Crown Tower", 40, 15, 1, "Tallest point in the districts."),
    ],

    # ── The Tidal Expanse ─────────────────────────────────────────────────
    "drowned_shore": [
        ("port", "Shipwreck Harbor", 0, 0, 3, "A coast where ships go to die."),
        ("ruins", "Tidal Ruins", -30, 20, 2, "Submerged at high tide."),
        ("village", "Fisher's End", 25, -15, 1, "Last fishing village."),
    ],
    "salt_flats": [
        ("ruins", "Salt Pillars", 0, 0, 3, "Crystallized formations that hum."),
        ("outpost", "Flat Beacon", -25, 15, 1, "Visible for miles across the white."),
        ("mine", "Salt Works", 25, -10, 2, "Mining cursed salt."),
    ],
    "deep_current": [
        ("port", "Current's Edge", 0, 0, 3, "Port on the edge of the whirlpool."),
        ("ruins", "Drowner's Rest", -20, 15, 2, "Bones from below wash up here."),
        ("sacred", "Tidal Stone", 20, -10, 2, "An ancient marker. The water obeys it."),
    ],

    # ── The Golden Reaches ────────────────────────────────────────────────
    "gilded_road": [
        ("market", "Golden Mile", 0, 0, 3, "Every stone worth more than a life."),
        ("city", "Toll Town", -30, 15, 2, "You pay to walk, breathe, and leave."),
        ("outpost", "Road Guard Post", 30, -10, 1, "Protecting the wealthy from the poor."),
    ],
    "dusthaven": [
        ("city", "Dusthaven Crossroads", 0, 0, 3, "Built on debt. Everyone owes something."),
        ("market", "Debt Exchange", -30, 15, 2, "Buy and sell debts here."),
        ("temple", "Creditor's Shrine", 25, -10, 1, "Pray your debts are forgiven."),
        ("village", "Debtor's Quarter", 35, 20, 1, "Those who couldn't pay."),
    ],
    "old_crossing": [
        ("sacred", "The First Bargain", 0, 0, 3, "Where the first human bargained with a god."),
        ("ruins", "Broken Altar", -25, 15, 2, "The deal is still unpaid."),
        ("village", "Crossing Settlement", 20, -15, 1, "Built near the sacred site."),
    ],

    # ── The Sunken Archive (Seal Zones) ───────────────────────────────────
    "seal_of_fear": [
        ("temple", "Seal of Fear", 0, 0, 3, "The ground breathes here."),
        ("sacred", "Nightmare Pool", -20, 10, 2, "Reflections show your death."),
    ],
    "seal_of_balance": [
        ("temple", "Seal of Balance", 0, 0, 3, "Cracked. Light and dark bleed out."),
        ("sacred", "Scale of Judgment", -15, 10, 2, "Weighs all who approach."),
    ],
    "seal_of_greed": [
        ("temple", "Seal of Greed", 0, 0, 3, "Mountain of offerings. Still watching."),
        ("sacred", "Offering Mound", 15, 10, 2, "Mortals left gifts to appease it."),
    ],
}

# ─── SUB-DISTRICT DEFINITIONS ────────────────────────────────────────────────
ZONE_SUBDISTRICTS: Dict[str, list] = {
    "slum_district": [
        ("Rua dos Condenados", -60, -20, 50, "Where criminals and outcasts gather."),
        ("Beco do Abismo", 50, -10, 40, "Near where Caleb fell."),
        ("Praça da Fome", -10, 30, 45, "Center of the slum's desperation."),
    ],
    "merchant_quarter": [
        ("Distrito dos Ourives", -50, -15, 55, "Goldsmiths and jewelers."),
        ("Via do Comércio", 20, 0, 60, "Main trading avenue."),
        ("Beco dos Ladrões", 40, 25, 35, "Thieves prey on merchants."),
    ],
    "high_citadel": [
        ("Pátio Real", -30, -10, 50, "Royal courtyard."),
        ("Torres da Memória", 25, 0, 45, "Archives of world history."),
        ("Jardim Morto", 0, 25, 40, "Dead garden of the last queen."),
    ],
    "iron_gate": [
        ("Praça da Guerra", 0, -20, 50, "War council meets here."),
        ("Barracas do Norte", -50, 15, 40, "Northern barracks."),
        ("Passagem de Ferro", 40, 5, 35, "The gate itself."),
    ],
    "warriors_rest": [
        ("Arena dos Campeões", 0, -15, 55, "Combat arena."),
        ("Vila dos Veteranos", -40, 15, 45, "Retired warriors."),
        ("Feira de Armas", 35, 10, 40, "Weapons market."),
    ],
    "dusthaven": [
        ("Cruzamento Central", 0, 0, 55, "The main crossroads."),
        ("Vila dos Devedores", -35, 20, 40, "Debtor's quarter."),
        ("Mercado de Dívidas", 30, -10, 40, "Debt exchange."),
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
    """

    def __init__(self, zones: dict):
        self.zones = zones
        self.structures: Dict[str, List[Structure]] = {}  # zone_id → structures
        self.subdistricts: Dict[str, List[SubDistrict]] = {}  # zone_id → subdistricts
        self._sprites: Dict[str, Dict[str, pygame.Surface]] = {}  # zone_id → {name: sprite}
        self._icon_sprites: Dict[str, pygame.Surface] = {}  # struct_type → icon sprite
        self._initialized = False

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

                st = Structure(
                    struct_type=stype,
                    name=name,
                    world_x=cx + ox + jx,
                    world_y=cy + oy + jy,
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

            # Sub-districts
            subdefs = ZONE_SUBDISTRICTS.get(zone_id, [])
            subs = []
            for sname, sox, soy, srad, sdesc in subdefs:
                cx, cy = zone.centroid
                subs.append(SubDistrict(
                    name=sname,
                    world_x=cx + sox,
                    world_y=cy + soy,
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
