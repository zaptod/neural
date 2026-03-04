"""
World Map — Configuration & Constants  (v6.0 LIVING WORLD)
Massive map, chunk-based rendering, world history, deep unit AI,
auto-civilizations, Noita-depth physics. EVERYTHING lives and breathes.
"""
import os

# ─── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(ROOT_DIR, "data")
NEURAL_DIR  = os.path.join(os.path.dirname(ROOT_DIR), "neural_v3_rework")

# ─── Screen (defaults — overridden at runtime by SCR) ──────────────────────────
SCREEN_W = 1280
SCREEN_H = 900
FPS      = 60

# ─── Map Grid (MASSIVE: 1600×1000 = 1,600,000 tiles) ──────────────────────────
MAP_W = 1600
MAP_H = 1000

# ─── Chunk System (for performance) ───────────────────────────────────────────
CHUNK_SIZE = 64      # tiles per chunk edge
CHUNK_COLS = (MAP_W + CHUNK_SIZE - 1) // CHUNK_SIZE   # 25
CHUNK_ROWS = (MAP_H + CHUNK_SIZE - 1) // CHUNK_SIZE   # 16

# ─── Zoom / Camera ─────────────────────────────────────────────────────────────
ZOOM_LEVELS  = [2, 3, 4, 6, 8, 12, 16]
DEFAULT_ZOOM = 1   # index into ZOOM_LEVELS — start at 3px/tile

# ─── UI ────────────────────────────────────────────────────────────────────────
TOPBAR_H       = 32
BOTTOMBAR_H    = 80
SIDEBAR_W      = 52
UI_BAR_H       = BOTTOMBAR_H
MAP_VIEWPORT_H = SCREEN_H - TOPBAR_H - BOTTOMBAR_H


class SCR:
    """Live screen dimensions — updated on window resize."""
    w          = SCREEN_W
    h          = SCREEN_H
    viewport_h = MAP_VIEWPORT_H

    @classmethod
    def resize(cls, w, h):
        cls.w          = w
        cls.h          = h
        cls.viewport_h = h - TOPBAR_H - BOTTOMBAR_H

# ─── Terrain Generation ───────────────────────────────────────────────────────
TERRAIN_SEED        = 42
MOISTURE_SEED       = 137
TERRAIN_OCTAVES     = 7
TERRAIN_PERSISTENCE = 0.50
TERRAIN_LACUNARITY  = 2.0
TEMPERATURE_SEED    = 201

# ─── Biome Colors — 22 biomes ─────────────────────────────────────────────────
BIOME_COLORS = {
    'deep_ocean':     (15,  18,  50),
    'ocean':          (28,  46,  92),
    'shallow_water':  (48,  78, 128),
    'reef':           (40,  90, 130),
    'river':          (55,  95, 160),
    'beach':          (220, 190, 118),
    'desert':         (196, 156,  80),
    'savanna':        (164, 152,  60),
    'grassland':      (80, 140,  50),
    'forest':         (40,  96,  40),
    'dense_forest':   (22,  60,  28),
    'tropical':       (30,  80,  25),
    'swamp':          (56,  76,  42),
    'tundra':         (140, 150, 140),
    'taiga':          (42,  72,  52),
    'hills':          (128, 112,  78),
    'mountain':       (96,  96, 104),
    'high_mountain':  (136, 136, 144),
    'volcano':        (80,  30,  20),
    'snow':           (216, 228, 232),
    'crystal_field':  (160, 180, 220),
    'corrupted':      (50,  15,  40),
}

# ─── Biome Elevation Thresholds ───────────────────────────────────────────────
ELEV_DEEP_OCEAN = 0.14
ELEV_OCEAN      = 0.21
ELEV_SHALLOW    = 0.26
ELEV_BEACH      = 0.29
ELEV_LOWLAND    = 0.54
ELEV_HIGHLAND   = 0.68
ELEV_MOUNTAIN   = 0.82
ELEV_PEAK       = 0.92

# ─── Moisture Thresholds ──────────────────────────────────────────────────────
MOIST_DRY = 0.20
MOIST_MED = 0.35
MOIST_WET = 0.55

# ─── Temperature Thresholds ───────────────────────────────────────────────────
TEMP_COLD   = 0.25
TEMP_COOL   = 0.40
TEMP_WARM   = 0.65
TEMP_HOT    = 0.80

# ─── Influence System ─────────────────────────────────────────────────────────
INFLUENCE_DEFAULT_RADIUS  = 70
INFLUENCE_MIN_THRESHOLD   = 0.05
INFLUENCE_TINT_STRENGTH   = 0.35
INFLUENCE_WATER_FACTOR    = 0.15

# ─── God Colors ───────────────────────────────────────────────────────────────
GOD_COLORS = {
    'god_balance':   (180, 160, 255),
    'god_fear':      (200,  30,  30),
    'god_greed':     (255, 200,   0),
    'god_nature':    (34,  170,  68),
    'god_fire':      (255, 102,  34),
    'god_ice':       (68,  187, 221),
    'god_darkness':  (85,   34, 170),
    'god_chaos':     (221,  34, 170),
    'god_void':      (34,   85, 102),
}

# ─── Structures ───────────────────────────────────────────────────────────────
STRUCTURE_TYPES = {
    'citadel':    {'size': 7, 'symbol': 'castle'},
    'castle':     {'size': 7, 'symbol': 'castle'},
    'temple':     {'size': 7, 'symbol': 'temple'},
    'tower':      {'size': 5, 'symbol': 'tower'},
    'altar':      {'size': 5, 'symbol': 'altar'},
    'ruin':       {'size': 5, 'symbol': 'ruin'},
    'village':    {'size': 5, 'symbol': 'village'},
    'city':       {'size': 7, 'symbol': 'city'},
    'farm':       {'size': 5, 'symbol': 'farm'},
    'mine':       {'size': 5, 'symbol': 'mine'},
    'port':       {'size': 5, 'symbol': 'port'},
    'wall':       {'size': 3, 'symbol': 'wall'},
    'bridge':     {'size': 3, 'symbol': 'bridge'},
    'workshop':   {'size': 5, 'symbol': 'workshop'},
    'barracks':   {'size': 5, 'symbol': 'barracks'},
    'graveyard':  {'size': 5, 'symbol': 'graveyard'},
}

# ─── Particles ─────────────────────────────────────────────────────────────────
MAX_PARTICLES = 1200

# ─── Material Simulation ──────────────────────────────────────────────────────
SIM_TICKS_PER_SEC = 10

# ─── Minimap ──────────────────────────────────────────────────────────────────
MINIMAP_W      = 240
MINIMAP_H      = 150
MINIMAP_MARGIN = 8

# ─── Weather ──────────────────────────────────────────────────────────────────
WEATHER_TICK_RATE   = 0.5      # weather updates per second
SEASON_LENGTH       = 120.0    # seconds per season
SEASONS             = ['spring', 'summer', 'autumn', 'winter']

# ─── Civilization ─────────────────────────────────────────────────────────────
CIV_TICK_RATE       = 1.0      # civ updates per second
POP_GROWTH_BASE     = 0.002    # per-tick growth rate
POP_MAX_VILLAGE     = 50
POP_MAX_CITY        = 300
RESOURCE_TYPES      = ['food', 'wood', 'stone', 'iron', 'gold', 'mana']

# ─── Units ────────────────────────────────────────────────────────────────────
UNIT_SPEED          = 2.0      # tiles per second

# ─── Army & War System ────────────────────────────────────────────────────────
ARMY_MIN_SIZE       = 3
ARMY_MERGE_RADIUS   = 8
WAR_COOLDOWN        = 300.0    # seconds between wars
PATROL_RADIUS       = 40
RAID_RANGE          = 80

# ─── World History ─────────────────────────────────────────────────────────────
HISTORY_MAX_EVENTS  = 2000
ERA_LENGTH          = 600.0    # seconds per era
ERA_NAMES           = ['Dawn', 'Expansion', 'Conflict', 'Empire', 'Decline', 'Rebirth']

# ─── Auto-Civilization ────────────────────────────────────────────────────────
AUTO_CIV_TICK       = 2.0      # seconds between auto-civ decisions
SETTLE_MIN_DIST     = 30       # min tiles between settlements
EXPAND_FOOD_THRESH  = 40       # food needed to expand (lowered for early game)
WAR_DECLARE_THRESH  = 0.6      # territory ratio threshold for war
UNIT_TYPES = {
    'settler':   {'hp': 30,  'atk': 0,  'spd': 1.5, 'icon': 'settler',  'cost': {'food': 20, 'wood': 10}},
    'warrior':   {'hp': 80,  'atk': 15, 'spd': 2.0, 'icon': 'sword',    'cost': {'food': 10, 'iron': 5}},
    'archer':    {'hp': 50,  'atk': 20, 'spd': 1.8, 'icon': 'bow',      'cost': {'food': 10, 'wood': 8}},
    'mage':      {'hp': 40,  'atk': 30, 'spd': 1.5, 'icon': 'staff',    'cost': {'food': 10, 'mana': 15}},
    'knight':    {'hp': 120, 'atk': 25, 'spd': 3.0, 'icon': 'horse',    'cost': {'food': 20, 'iron': 15}},
    'siege':     {'hp': 200, 'atk': 40, 'spd': 0.8, 'icon': 'catapult', 'cost': {'wood': 30, 'iron': 20}},
    'dragon':    {'hp': 300, 'atk': 50, 'spd': 4.0, 'icon': 'dragon',   'cost': {'mana': 50, 'gold': 30}},
    'undead':    {'hp': 60,  'atk': 12, 'spd': 1.5, 'icon': 'skull',    'cost': {'mana': 8}},
    'golem':     {'hp': 250, 'atk': 35, 'spd': 0.5, 'icon': 'golem',    'cost': {'stone': 30, 'mana': 20}},
    'spirit':    {'hp': 20,  'atk': 25, 'spd': 5.0, 'icon': 'ghost',    'cost': {'mana': 12}},
    'scout':     {'hp': 35,  'atk': 5,  'spd': 4.5, 'icon': 'scout',    'cost': {'food': 5, 'wood': 3}},
    'healer':    {'hp': 30,  'atk': 0,  'spd': 1.8, 'icon': 'healer',   'cost': {'food': 10, 'mana': 10}},
    'berserker': {'hp': 100, 'atk': 40, 'spd': 2.5, 'icon': 'axe',      'cost': {'food': 15, 'iron': 10}},
    'assassin':  {'hp': 40,  'atk': 45, 'spd': 4.0, 'icon': 'dagger',   'cost': {'gold': 15, 'iron': 5}},
    'titan':     {'hp': 500, 'atk': 60, 'spd': 0.3, 'icon': 'titan',    'cost': {'stone': 50, 'mana': 40, 'iron': 30}},
}

# ─── Element Synergy (Noita-depth: chain reactions, cascading effects) ────────
# (mat_a, mat_b) → result_material
ELEMENT_REACTIONS = {
    ('fire', 'water'):     'steam',
    ('fire', 'ice'):       'water',
    ('fire', 'sand_elem'): 'glass',
    ('fire', 'vine'):      'ash',
    ('fire', 'spore'):     'ash',
    ('fire', 'mud'):       'stone',
    ('lava', 'water'):     'obsidian',
    ('lava', 'ice'):       'obsidian',
    ('lava', 'vine'):      'fire',
    ('lava', 'sand_elem'): 'glass',
    ('water', 'ice'):      'ice',
    ('water', 'ash'):      'mud',
    ('water', 'sand_elem'):'mud',
    ('water', 'corrupt'):  'swamp_gas',
    ('acid', 'stone'):     'none',
    ('acid', 'obsidian'):  'none',
    ('acid', 'glass'):     'none',
    ('acid', 'crystal'):   'none',
    ('acid', 'vine'):      'none',
    ('acid', 'mud'):       'swamp_gas',
    ('bless', 'corrupt'):  'crystal',
    ('bless', 'hellfire'): 'fire',
    ('bless', 'spore'):    'vine',
    ('bless', 'swamp_gas'):'steam',
    ('fire', 'corrupt'):   'hellfire',
    ('ice', 'water'):      'ice',
    ('frost', 'fire'):     'water',
    ('frost', 'lava'):     'obsidian',
    ('frost', 'steam'):    'water',
    ('frost', 'vine'):     'ice',
    ('frost', 'mud'):      'ice',
    ('lightning', 'sand_elem'): 'glass',
    ('lightning', 'water'):     'none',
    ('lightning', 'ice'):       'water',
    ('lightning', 'steam'):     'none',
    ('lightning', 'vine'):      'fire',
    ('vine', 'corrupt'):   'spore',
    ('vine', 'mud'):       'vine',
    ('steam', 'ice'):      'frost',
    ('hellfire', 'water'): 'steam',
    ('hellfire', 'ice'):   'steam',
    ('crystal', 'corrupt'):'glass',
    ('crystal', 'fire'):   'glass',
}

# Extra materials from reactions (expanded for Noita-depth chains)
REACTION_MATERIALS = {
    'steam':     {'color': (200, 210, 220), 'sim': True,  'rises': True,  'life': 80},
    'glass':     {'color': (180, 220, 230), 'sim': False, 'life': 0},
    'obsidian':  {'color': (25,   15,  30), 'sim': False, 'life': 0},
    'swamp_gas': {'color': (90,  110,  50), 'sim': True,  'rises': True,  'life': 60, 'toxic': True},
    'crystal':   {'color': (170, 200, 255), 'sim': False, 'life': 0},
    'hellfire':  {'color': (180,  20,  60), 'sim': True,  'spread': 0.20, 'life': 120, 'burns': True},
    'ash':       {'color': (70,   65,  60), 'sim': True,  'falls': True,  'life': 0},
    'mud':       {'color': (90,   70,  45), 'sim': True,  'life': 0,  'flows': True},
    'frost':     {'color': (190, 220, 240), 'sim': True,  'spread': 0.04, 'life': 150},
    'vine':      {'color': (50,  120,  30), 'sim': True,  'spread': 0.06, 'life': 0},
    'spore':     {'color': (130,  90, 140), 'sim': True,  'spread': 0.03, 'life': 200, 'toxic': True},
    'lightning_mat': {'color': (255, 255, 180), 'sim': True, 'life': 8},
    'stone':     {'color': (120, 115, 110), 'sim': False, 'life': 0},
}
