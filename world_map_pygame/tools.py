"""
World Map — Tools & Brush System  (v4.0 MEGA UPDATE)
Element synergy, expanded materials, advanced god powers, construction tools.
"""
import numpy as np
try:
    from .config import (
        MAP_W, MAP_H, ELEMENT_REACTIONS, REACTION_MATERIALS,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from config import (
        MAP_W, MAP_H, ELEMENT_REACTIONS, REACTION_MATERIALS,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# Tool categories — 10 categories with expanded tools
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_CATEGORIES = [
    {
        'id': 'inspect', 'name': 'Inspect', 'icon': 'eye',
        'color': (180, 180, 200),
        'tools': [
            {'id': 'select',  'name': 'Select',  'desc': 'Click to inspect tile / stronghold'},
            {'id': 'measure', 'name': 'Measure', 'desc': 'See elevation, moisture, temperature'},
        ],
    },
    {
        'id': 'terrain', 'name': 'Terrain', 'icon': 'mountain',
        'color': (130, 180, 90),
        'tools': [
            {'id': 'raise',    'name': 'Raise',     'desc': 'Raise elevation'},
            {'id': 'lower',    'name': 'Lower',     'desc': 'Lower elevation'},
            {'id': 'flatten',  'name': 'Flatten',   'desc': 'Flatten to average height'},
            {'id': 'smooth',   'name': 'Smooth',    'desc': 'Smooth terrain'},
            {'id': 'canyon',   'name': 'Canyon',    'desc': 'Carve deep canyon'},
            {'id': 'plateau',  'name': 'Plateau',   'desc': 'Raise flat plateau'},
            {'id': 'river',    'name': 'River',     'desc': 'Carve river path'},
            {'id': 'volcano_t','name': 'Volcano',   'desc': 'Create volcano peak'},
        ],
    },
    {
        'id': 'elements', 'name': 'Elements', 'icon': 'fire',
        'color': (220, 120, 40),
        'tools': [
            {'id': 'fire',      'name': 'Fire',      'desc': 'Fire — spreads & burns',    'material': 'fire'},
            {'id': 'water',     'name': 'Water',     'desc': 'Water — flows downhill',     'material': 'water'},
            {'id': 'lava',      'name': 'Lava',      'desc': 'Lava — burns, cools to stone','material': 'lava'},
            {'id': 'acid',      'name': 'Acid',      'desc': 'Acid — dissolves terrain',   'material': 'acid'},
            {'id': 'ice_elem',  'name': 'Ice',       'desc': 'Ice — freezes water nearby', 'material': 'ice'},
            {'id': 'sand',      'name': 'Sand',      'desc': 'Sand — falls, settles',      'material': 'sand_elem'},
            {'id': 'lightning', 'name': 'Lightning',  'desc': 'Lightning bolt — zaps',     'material': 'lightning_mat'},
            {'id': 'steam',     'name': 'Steam',      'desc': 'Steam — rises up',          'material': 'steam'},
            {'id': 'hellfire',  'name': 'Hellfire',    'desc': 'Dark fire — spreads fast', 'material': 'hellfire'},
            {'id': 'frost',     'name': 'Frost',      'desc': 'Creeping frost',            'material': 'frost'},
            {'id': 'vine',      'name': 'Vines',      'desc': 'Living vines — spread',    'material': 'vine'},
            {'id': 'spore',     'name': 'Spores',     'desc': 'Toxic spores — poison',    'material': 'spore'},
        ],
    },
    {
        'id': 'nature', 'name': 'Nature', 'icon': 'tree',
        'color': (50, 160, 60),
        'tools': [
            {'id': 'forest_p',  'name': 'Forest',     'desc': 'Plant forest'},
            {'id': 'tropical_p','name': 'Tropical',   'desc': 'Plant tropical jungle'},
            {'id': 'flower',    'name': 'Flowers',    'desc': 'Scatter flowers'},
            {'id': 'mushroom',  'name': 'Mushroom',   'desc': 'Grow mushrooms'},
            {'id': 'corrupt',   'name': 'Corruption', 'desc': 'Spread dark corruption'},
            {'id': 'bless',     'name': 'Blessing',   'desc': 'Purify corruption'},
            {'id': 'crystal_p', 'name': 'Crystal',    'desc': 'Grow crystal formations'},
            {'id': 'swamp_p',   'name': 'Swamp',      'desc': 'Create swampland'},
        ],
    },
    {
        'id': 'build', 'name': 'Build', 'icon': 'hammer',
        'color': (180, 150, 100),
        'tools': [
            {'id': 'village',   'name': 'Village',   'desc': 'Place village (grows over time)'},
            {'id': 'city',      'name': 'City',      'desc': 'Place city (needs village nearby)'},
            {'id': 'farm',      'name': 'Farm',      'desc': 'Place farm (produces food)'},
            {'id': 'mine',      'name': 'Mine',      'desc': 'Place mine (on hills/mountains)'},
            {'id': 'port',      'name': 'Port',      'desc': 'Place port (on coast)'},
            {'id': 'wall',      'name': 'Wall',      'desc': 'Build wall segment'},
            {'id': 'bridge',    'name': 'Bridge',    'desc': 'Build bridge over water'},
            {'id': 'workshop',  'name': 'Workshop',  'desc': 'Craft center (needs village)'},
            {'id': 'barracks',  'name': 'Barracks',  'desc': 'Train units'},
            {'id': 'graveyard', 'name': 'Graveyard', 'desc': 'Spawns undead in darkness'},
        ],
    },
    {
        'id': 'units', 'name': 'Units', 'icon': 'sword',
        'color': (200, 100, 100),
        'tools': [
            {'id': 'settler',   'name': 'Settler',   'desc': 'Spawn settler — founds villages'},
            {'id': 'warrior',   'name': 'Warrior',   'desc': 'Spawn warrior'},
            {'id': 'archer',    'name': 'Archer',    'desc': 'Spawn archer'},
            {'id': 'mage',      'name': 'Mage',      'desc': 'Spawn mage'},
            {'id': 'knight',    'name': 'Knight',    'desc': 'Spawn knight'},
            {'id': 'dragon',    'name': 'Dragon',    'desc': 'Spawn dragon'},
            {'id': 'undead',    'name': 'Undead',    'desc': 'Raise undead horde'},
            {'id': 'golem',     'name': 'Golem',     'desc': 'Summon stone golem'},
        ],
    },
    {
        'id': 'powers', 'name': 'Powers', 'icon': 'bolt',
        'color': (200, 170, 255),
        'tools': [
            {'id': 'bolt',      'name': 'Lightning', 'desc': 'Strike lightning — fire + glass'},
            {'id': 'meteor',    'name': 'Meteor',    'desc': 'Meteor — crater + fire + lava'},
            {'id': 'tornado',   'name': 'Tornado',   'desc': 'Tornado — destroys area'},
            {'id': 'earthquake','name': 'Earthquake','desc': 'Earthquake — cracks terrain'},
            {'id': 'rain_p',    'name': 'Rain',      'desc': 'Bring rain — adds moisture & water'},
            {'id': 'blizzard',  'name': 'Blizzard',  'desc': 'Blizzard — frost + ice + snow'},
            {'id': 'plague',    'name': 'Plague',     'desc': 'Spawn plague — kills population'},
            {'id': 'flood',     'name': 'Flood',      'desc': 'Massive water surge'},
            {'id': 'eruption',  'name': 'Eruption',   'desc': 'Volcanic eruption — lava rain'},
            {'id': 'purge',     'name': 'Divine Purge','desc': 'Remove all evil from area'},
        ],
    },
    {
        'id': 'divine', 'name': 'Divine', 'icon': 'halo',
        'color': (255, 220, 100),
        'tools': [
            {'id': 'claim',     'name': 'Claim',      'desc': 'Claim tile for god'},
            {'id': 'stronghold','name': 'Stronghold',  'desc': 'Place new stronghold'},
            {'id': 'unclaim',   'name': 'Unclaim',     'desc': 'Remove god ownership'},
            {'id': 'gift',      'name': 'Gift',        'desc': 'Gift resources to settlement'},
            {'id': 'miracle',   'name': 'Miracle',     'desc': 'Heal land + boost growth'},
        ],
    },
    {
        'id': 'weather', 'name': 'Weather', 'icon': 'cloud',
        'color': (120, 160, 200),
        'tools': [
            {'id': 'w_rain',    'name': 'Rain',       'desc': 'Start rain over area'},
            {'id': 'w_storm',   'name': 'Storm',      'desc': 'Thunder storm with lightning'},
            {'id': 'w_snow',    'name': 'Snowfall',   'desc': 'Snow over area'},
            {'id': 'w_heat',    'name': 'Heatwave',   'desc': 'Raise temperature'},
            {'id': 'w_cold',    'name': 'Cold Snap',  'desc': 'Lower temperature'},
            {'id': 'w_clear',   'name': 'Clear Sky',  'desc': 'Clear all weather'},
        ],
    },
    {
        'id': 'erase', 'name': 'Erase', 'icon': 'eraser',
        'color': (180, 60, 60),
        'tools': [
            {'id': 'erase',    'name': 'Erase',     'desc': 'Remove materials / elements'},
            {'id': 'destroy',  'name': 'Destroy',   'desc': 'Destroy everything in area'},
            {'id': 'kill',     'name': 'Kill',      'desc': 'Kill all units in area'},
            {'id': 'reset',    'name': 'Reset',     'desc': 'Reset tile to natural state'},
        ],
    },
]

BRUSH_SIZES = [1, 2, 4, 8, 16, 32, 64]
DEFAULT_BRUSH = 2

# ═══════════════════════════════════════════════════════════════════════════════
# Materials — base + reaction products
# ═══════════════════════════════════════════════════════════════════════════════

MATERIALS = {
    'none':      {'color': None,            'sim': False},
    'fire':      {'color': (255, 80,  20),  'sim': True, 'spread': 0.15, 'life': 60,  'burns': True},
    'water':     {'color': (40,  100, 200), 'sim': True, 'flows': True,  'life': 0},
    'lava':      {'color': (220, 60,  10),  'sim': True, 'flows': True,  'life': 300, 'burns': True, 'cools_to': 'stone'},
    'acid':      {'color': (120, 220, 30),  'sim': True, 'flows': True,  'life': 120, 'dissolves': True},
    'ice':       {'color': (160, 210, 240), 'sim': True, 'life': 0,     'freezes': True},
    'sand_elem': {'color': (210, 190, 120), 'sim': True, 'falls': True,  'life': 0},
    'stone':     {'color': (100, 100, 110), 'sim': False, 'life': 0},
    'flower':    {'color': (220, 80,  160), 'sim': False, 'life': 0},
    'mushroom':  {'color': (160, 80,  60),  'sim': False, 'life': 0},
    'corrupt':   {'color': (60,  10,  50),  'sim': True,  'spread': 0.05, 'life': 0},
    'bless':     {'color': (240, 230, 180), 'sim': True,  'spread': 0.08, 'life': 200},
    'crater':    {'color': (50,  40,  35),  'sim': False},
}
# Merge reaction materials
MATERIALS.update(REACTION_MATERIALS)

# Build index
MAT_NAMES = ['none'] + [k for k in MATERIALS if k != 'none']
MAT_INDEX = {n: i for i, n in enumerate(MAT_NAMES)}

# Build reaction lookup with integer keys for speed
_REACTION_LUT = {}
for (a, b), result in ELEMENT_REACTIONS.items():
    ai, bi = MAT_INDEX.get(a, 0), MAT_INDEX.get(b, 0)
    ri = MAT_INDEX.get(result, 0)
    if ai and bi:
        _REACTION_LUT[(ai, bi)] = ri
        _REACTION_LUT[(bi, ai)] = ri  # symmetric


class ToolState:
    """Tracks current tool, brush, god selection, simulation state."""

    def __init__(self):
        self.category_idx   = 0
        self.tool_idx       = 0
        self.brush_idx      = DEFAULT_BRUSH
        self.selected_god   = 0
        self.painting       = False
        self.sim_paused     = False
        self.sim_speed      = 1        # 1x, 2x, 3x

    @property
    def category(self):
        return TOOL_CATEGORIES[self.category_idx]

    @property
    def tool(self):
        tools = self.category['tools']
        return tools[min(self.tool_idx, len(tools) - 1)]

    @property
    def brush_radius(self):
        return BRUSH_SIZES[self.brush_idx]

    def next_brush(self):
        self.brush_idx = min(self.brush_idx + 1, len(BRUSH_SIZES) - 1)

    def prev_brush(self):
        self.brush_idx = max(self.brush_idx - 1, 0)

    def set_category(self, idx):
        if 0 <= idx < len(TOOL_CATEGORIES):
            self.category_idx = idx
            self.tool_idx = 0

    def set_tool(self, idx):
        tools = self.category['tools']
        if 0 <= idx < len(tools):
            self.tool_idx = idx

    def toggle_pause(self):
        self.sim_paused = not self.sim_paused

    def cycle_speed(self):
        self.sim_speed = self.sim_speed % 3 + 1


# ═══════════════════════════════════════════════════════════════════════════════
# Material Layer — pixel-level simulation with element synergy
# ═══════════════════════════════════════════════════════════════════════════════

class MaterialLayer:
    """Per-tile material grid with physics simulation and element reactions."""

    def __init__(self, w=MAP_W, h=MAP_H):
        self.w, self.h = w, h
        self.mat  = np.zeros((h, w), dtype=np.uint8)
        self.life = np.zeros((h, w), dtype=np.int16)
        self._version = 0
        self._rng = np.random.RandomState(77)

    def paint(self, cx, cy, radius, mat_name):
        mi = MAT_INDEX.get(mat_name, 0)
        info = MATERIALS.get(mat_name, {})
        default_life = info.get('life', 0)

        y0 = max(0, cy - radius)
        y1 = min(self.h, cy + radius + 1)
        x0 = max(0, cx - radius)
        x1 = min(self.w, cx + radius + 1)

        yy, xx = np.ogrid[y0:y1, x0:x1]
        dist2 = (xx - cx) ** 2 + (yy - cy) ** 2
        mask  = dist2 <= radius ** 2

        self.mat[y0:y1, x0:x1][mask] = mi
        if default_life > 0:
            self.life[y0:y1, x0:x1][mask] = default_life + self._rng.randint(-10, 10, size=mask.sum()).astype(np.int16)
        else:
            self.life[y0:y1, x0:x1][mask] = 0
        self._version += 1

    def erase(self, cx, cy, radius):
        y0 = max(0, cy - radius)
        y1 = min(self.h, cy + radius + 1)
        x0 = max(0, cx - radius)
        x1 = min(self.w, cx + radius + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
        self.mat[y0:y1, x0:x1][mask]  = 0
        self.life[y0:y1, x0:x1][mask] = 0
        self._version += 1

    def get_at(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return MAT_NAMES[self.mat[y, x]]
        return 'none'

    # ── simulation tick ────────────────────────────────────────────────────
    def simulate(self, heightmap, biome_map, biome_names):
        changed = False

        # Decrement life
        has_life = (self.life > 0) & (self.mat > 0)
        if np.any(has_life):
            self.life[has_life] -= 1
            expired = has_life & (self.life <= 0)

            # Lava cools to stone
            lava_idx = MAT_INDEX.get('lava', 0)
            stone_idx = MAT_INDEX.get('stone', 0)
            lava_cool = expired & (self.mat == lava_idx)
            if np.any(lava_cool):
                self.mat[lava_cool] = stone_idx
                changed = True

            # Fire leaves ash
            fire_idx = MAT_INDEX.get('fire', 0)
            ash_idx = MAT_INDEX.get('ash', 0)
            fire_die = expired & (self.mat == fire_idx)
            if np.any(fire_die) and ash_idx:
                # 30% chance to leave ash
                rnd = self._rng.random(fire_die.sum())
                ys, xs = np.where(fire_die)
                for k in range(len(ys)):
                    if rnd[k] < 0.3:
                        self.mat[ys[k], xs[k]] = ash_idx
                    else:
                        self.mat[ys[k], xs[k]] = 0
                changed = True

            # Others disappear
            other_expire = expired & ~lava_cool & ~fire_die
            if np.any(other_expire):
                self.mat[other_expire] = 0
                changed = True

        # Element reactions (check adjacency) — run twice for chain cascading
        changed |= self._run_reactions()
        changed |= self._run_reactions()  # second pass catches cascaded products

        # ── Terrain-altering effects (Noita-depth) ─────────────────────
        fire_idx = MAT_INDEX.get('fire', 0)
        lava_idx2 = MAT_INDEX.get('lava', 0)
        frost_idx2 = MAT_INDEX.get('frost', 0)
        hf_idx2 = MAT_INDEX.get('hellfire', 0)

        # Fire / hellfire dries terrain (lower moisture)
        fire_all = (self.mat == fire_idx)
        if hf_idx2:
            fire_all = fire_all | (self.mat == hf_idx2)
        if np.any(fire_all):
            heightmap[fire_all] = np.clip(heightmap[fire_all] - 0.0003, 0, 1)  # slight scorching
            changed = True

        # Frost increases moisture (frozen water seeps in)
        if frost_idx2:
            frost_all = self.mat == frost_idx2
            if np.any(frost_all):
                pass  # moisture handled by weather; frost just spreads

        # Lava raises elevation (cooling magma builds land)
        if lava_idx2:
            lava_all = self.mat == lava_idx2
            if np.any(lava_all):
                heightmap[lava_all] = np.clip(heightmap[lava_all] + 0.0005, 0, 1)
                changed = True

        # Fire spread
        fire_mask = self.mat == fire_idx
        if np.any(fire_mask):
            changed |= self._spread(fire_mask, fire_idx, 0.12, biome_map, biome_names,
                                     flammable={'grassland', 'forest', 'dense_forest',
                                                'savanna', 'swamp', 'tropical', 'taiga'})

        # Hellfire spread (faster)
        hf_idx = MAT_INDEX.get('hellfire', 0)
        if hf_idx:
            hf_mask = self.mat == hf_idx
            if np.any(hf_mask):
                changed |= self._spread(hf_mask, hf_idx, 0.20, biome_map, biome_names,
                                         flammable={'grassland','forest','dense_forest',
                                                    'savanna','swamp','tropical','taiga',
                                                    'desert','beach','hills'})

        # Corruption spread
        corr_idx = MAT_INDEX.get('corrupt', 0)
        corr_mask = self.mat == corr_idx
        if np.any(corr_mask):
            changed |= self._spread(corr_mask, corr_idx, 0.03)

        # Blessing spread + kills corruption
        bless_idx = MAT_INDEX.get('bless', 0)
        bless_mask = self.mat == bless_idx
        if np.any(bless_mask):
            changed |= self._spread(bless_mask, bless_idx, 0.04)

        # Frost spread
        frost_idx = MAT_INDEX.get('frost', 0)
        if frost_idx:
            frost_mask = self.mat == frost_idx
            if np.any(frost_mask):
                changed |= self._spread(frost_mask, frost_idx, 0.04)

        # Vine spread (only on land)
        vine_idx = MAT_INDEX.get('vine', 0)
        if vine_idx:
            vine_mask = self.mat == vine_idx
            if np.any(vine_mask):
                changed |= self._spread(vine_mask, vine_idx, 0.06, biome_map, biome_names,
                                         flammable={'grassland','forest','dense_forest',
                                                    'tropical','savanna','swamp','hills'})

        # Spore spread
        spore_idx = MAT_INDEX.get('spore', 0)
        if spore_idx:
            spore_mask = self.mat == spore_idx
            if np.any(spore_mask):
                changed |= self._spread(spore_mask, spore_idx, 0.03)

        # Water / lava / acid / mud flow
        for mat_name in ('water', 'lava', 'acid', 'mud'):
            mi = MAT_INDEX.get(mat_name, 0)
            if not mi:
                continue
            mask = self.mat == mi
            if np.any(mask):
                changed |= self._flow(mask, mi, heightmap)

        # Steam / swamp_gas rise (drift uphill + disperse on top-down map)
        for mat_name in ('steam', 'swamp_gas'):
            mi = MAT_INDEX.get(mat_name, 0)
            if mi:
                mask = self.mat == mi
                if np.any(mask):
                    changed |= self._rise(mask, mi, heightmap)

        # Sand / ash / stone settle downhill (flow to lower elevation on top-down map)
        for mat_name in ('sand_elem', 'ash', 'stone'):
            mi = MAT_INDEX.get(mat_name, 0)
            if mi:
                mask = self.mat == mi
                if np.any(mask):
                    changed |= self._fall(mask, mi, heightmap)

        # Acid dissolves
        acid_idx = MAT_INDEX.get('acid', 0)
        acid_mask = self.mat == acid_idx
        if np.any(acid_mask):
            heightmap[acid_mask] = np.clip(heightmap[acid_mask] - 0.002, 0, 1)
            changed = True

        if changed:
            self._version += 1
        return changed

    # ── element reactions ──────────────────────────────────────────────────
    def _run_reactions(self):
        """Check adjacent materials for reactions (element synergy)."""
        if not _REACTION_LUT:
            return False
        changed = False
        active = self.mat > 0
        ys, xs = np.where(active)
        if len(ys) == 0:
            return False

        n = min(len(ys), 2000)  # scaled for 1600x1000 map
        idxs = self._rng.choice(len(ys), n, replace=False)

        for i in idxs:
            y, x = int(ys[i]), int(xs[i])
            my_mat = int(self.mat[y, x])
            if my_mat == 0:
                continue
            # Check 4 neighbors
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < self.h and 0 <= nx < self.w:
                    nb = int(self.mat[ny, nx])
                    if nb == 0 or nb == my_mat:
                        continue
                    result = _REACTION_LUT.get((my_mat, nb))
                    if result is not None:
                        if self._rng.random() < 0.18:  # slightly higher chance for more chain activity
                            if result == 0:
                                # Both consumed
                                self.mat[y, x] = 0
                                self.mat[ny, nx] = 0
                                self.life[y, x] = 0
                                self.life[ny, nx] = 0
                            else:
                                # Replace both with result
                                info_r = MATERIALS.get(MAT_NAMES[result], {})
                                rl = info_r.get('life', 0)
                                self.mat[y, x] = result
                                self.mat[ny, nx] = result
                                self.life[y, x] = rl + self._rng.randint(-5, 5) if rl else 0
                                self.life[ny, nx] = rl + self._rng.randint(-5, 5) if rl else 0
                            changed = True
                            break
        return changed

    # ── simulation helpers ─────────────────────────────────────────────────
    def _spread(self, mask, mat_idx, chance, biome_map=None, biome_names=None, flammable=None):
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return False
        n = min(len(ys), 2000)  # scaled for 1600x1000 map
        idxs = self._rng.choice(len(ys), n, replace=False)
        changed = False
        for i in idxs:
            y, x = int(ys[i]), int(xs[i])
            if self._rng.random() > chance:
                continue
            dy, dx = self._rng.randint(-1, 2), self._rng.randint(-1, 2)
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.h and 0 <= nx < self.w and self.mat[ny, nx] == 0:
                if flammable and biome_map is not None and biome_names is not None:
                    b = biome_names[biome_map[ny, nx]]
                    if b not in flammable:
                        continue
                info = MATERIALS.get(MAT_NAMES[mat_idx], {})
                self.mat[ny, nx] = mat_idx
                self.life[ny, nx] = info.get('life', 60) + self._rng.randint(-5, 5)
                changed = True
        return changed

    def _flow(self, mask, mat_idx, heightmap):
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return False
        n = min(len(ys), 1500)  # scaled for 1600x1000 map
        idxs = self._rng.choice(len(ys), n, replace=False)
        changed = False
        for i in idxs:
            y, x = int(ys[i]), int(xs[i])
            h_here = heightmap[y, x]
            best, bx, by = h_here, x, y
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny2, nx2 = y + dy, x + dx
                    if 0 <= ny2 < self.h and 0 <= nx2 < self.w:
                        if heightmap[ny2, nx2] < best and self.mat[ny2, nx2] == 0:
                            best, bx, by = heightmap[ny2, nx2], nx2, ny2
            if (bx, by) != (x, y):
                self.mat[by, bx] = mat_idx
                self.life[by, bx] = self.life[y, x]
                self.mat[y, x] = 0
                self.life[y, x] = 0
                changed = True
        return changed

    def _rise(self, mask, mat_idx, heightmap):
        """Rising materials (steam, gas) — drift uphill or disperse randomly.
        Top-down map: 'rising' means moving toward higher elevation tiles
        or dispersing with wind-like random drift."""
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return False
        n = min(len(ys), 1000)  # scaled for 1600x1000 map
        idxs = self._rng.choice(len(ys), n, replace=False)
        changed = False
        for i in idxs:
            y, x = int(ys[i]), int(xs[i])
            h_here = heightmap[y, x]
            # Try to move to a higher-elevation neighbor or random neighbor
            best_h, bx, by = h_here, x, y
            candidates = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny2, nx2 = y + dy, x + dx
                    if 0 <= ny2 < self.h and 0 <= nx2 < self.w:
                        if self.mat[ny2, nx2] == 0:
                            nh = heightmap[ny2, nx2]
                            if nh > best_h:  # prefer higher ground
                                best_h, bx, by = nh, nx2, ny2
                            candidates.append((nx2, ny2))
            # 60% chance move uphill, 40% random drift (wind)
            if (bx, by) != (x, y) and self._rng.random() < 0.6:
                self.mat[by, bx] = mat_idx
                self.life[by, bx] = self.life[y, x]
                self.mat[y, x] = 0
                self.life[y, x] = 0
                changed = True
            elif candidates and self._rng.random() < 0.3:
                cx, cy = candidates[self._rng.randint(len(candidates))]
                self.mat[cy, cx] = mat_idx
                self.life[cy, cx] = self.life[y, x]
                self.mat[y, x] = 0
                self.life[y, x] = 0
                changed = True
        return changed

    def _fall(self, mask, mat_idx, heightmap):
        """Settling materials (sand, ash) — slide downhill via heightmap.
        Top-down map: 'falling' means flowing to lower elevation, like
        loose material tumbling down slopes."""
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return False
        n = min(len(ys), 1000)  # scaled for 1600x1000 map
        idxs = self._rng.choice(len(ys), n, replace=False)
        changed = False
        for i in idxs:
            y, x = int(ys[i]), int(xs[i])
            h_here = heightmap[y, x]
            # Find lowest neighboring empty tile
            best_h, bx, by = h_here, x, y
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny2, nx2 = y + dy, x + dx
                    if 0 <= ny2 < self.h and 0 <= nx2 < self.w:
                        if heightmap[ny2, nx2] < best_h and self.mat[ny2, nx2] == 0:
                            best_h, bx, by = heightmap[ny2, nx2], nx2, ny2
            # Only move if there's any downhill slope
            if (bx, by) != (x, y) and (h_here - best_h) > 0.0001:
                self.mat[by, bx] = mat_idx
                self.life[by, bx] = self.life[y, x]
                self.mat[y, x] = 0
                self.life[y, x] = 0
                changed = True
        return changed


# ═══════════════════════════════════════════════════════════════════════════════
# Tool execution
# ═══════════════════════════════════════════════════════════════════════════════

def apply_tool(tool_state, tx, ty, heightmap, moisture, biome_map, biome_names,
               material_layer, influence, strongholds, gods, particles,
               reclassify_fn, event_log_fn, **kwargs):
    """Execute current tool at tile position. Returns True if anything changed."""
    tool = tool_state.tool
    tid  = tool['id']
    r    = tool_state.brush_radius
    world = kwargs.get('world')  # WorldMap ref for advanced tools

    if tid in ('select', 'measure'):
        return False

    # ── Terrain ────────────────────────────────────────────────────────
    if tid == 'raise':
        _modify_height(heightmap, tx, ty, r, 0.015)
        reclassify_fn()
        return True
    if tid == 'lower':
        _modify_height(heightmap, tx, ty, r, -0.015)
        reclassify_fn()
        return True
    if tid == 'flatten':
        _flatten(heightmap, tx, ty, r)
        reclassify_fn()
        return True
    if tid == 'smooth':
        _smooth(heightmap, tx, ty, r)
        reclassify_fn()
        return True
    if tid == 'canyon':
        _modify_height(heightmap, tx, ty, max(2, r // 2), -0.08)
        reclassify_fn()
        if event_log_fn: event_log_fn("Canyon carved!")
        return True
    if tid == 'plateau':
        _plateau(heightmap, tx, ty, r)
        reclassify_fn()
        if event_log_fn: event_log_fn("Plateau raised!")
        return True
    if tid == 'river':
        _carve_river(heightmap, tx, ty, r)
        reclassify_fn()
        material_layer.paint(tx, ty, max(1, r // 2), 'water')
        return True
    if tid == 'volcano_t':
        _create_volcano(heightmap, tx, ty)
        reclassify_fn()
        material_layer.paint(tx, ty, 2, 'lava')
        if event_log_fn: event_log_fn("Volcano rises!")
        return True

    # ── Elements ───────────────────────────────────────────────────────
    mat = tool.get('material')
    if mat:
        material_layer.paint(tx, ty, r, mat)
        return True

    # ── Nature ─────────────────────────────────────────────────────────
    if tid == 'forest_p':
        _paint_biome(biome_map, biome_names, heightmap, tx, ty, r, 'forest')
        return True
    if tid == 'tropical_p':
        _paint_biome(biome_map, biome_names, heightmap, tx, ty, r, 'tropical')
        return True
    if tid == 'flower':
        material_layer.paint(tx, ty, r, 'flower')
        return True
    if tid == 'mushroom':
        material_layer.paint(tx, ty, r, 'mushroom')
        return True
    if tid == 'corrupt':
        material_layer.paint(tx, ty, r, 'corrupt')
        return True
    if tid == 'bless':
        material_layer.paint(tx, ty, r, 'bless')
        return True
    if tid == 'crystal_p':
        material_layer.paint(tx, ty, r, 'crystal')
        return True
    if tid == 'swamp_p':
        _paint_biome(biome_map, biome_names, heightmap, tx, ty, r, 'swamp')
        _modify_moisture(moisture, tx, ty, r, 0.15)
        reclassify_fn()
        return True

    # ── Build ──────────────────────────────────────────────────────────
    if tid in ('village','city','farm','mine','port','wall','bridge',
               'workshop','barracks','graveyard'):
        if world and hasattr(world, 'civilizations'):
            god_id = gods[tool_state.selected_god]['god_id'] if gods else None
            world.civilizations.place_building(tid, tx, ty, god_id)
            if event_log_fn: event_log_fn(f"{tid.title()} placed")
        return True

    # ── Units ──────────────────────────────────────────────────────────
    if tid in ('settler','warrior','archer','mage','knight','dragon','undead','golem',
               'scout','healer','berserker','assassin','titan'):
        if world and hasattr(world, 'units'):
            god_id = gods[tool_state.selected_god]['god_id'] if gods else None
            world.units.spawn(tid, tx, ty, god_id)
            if event_log_fn: event_log_fn(f"{tid.title()} spawned")
        return True

    # ── Powers ─────────────────────────────────────────────────────────
    if tid == 'bolt':
        material_layer.paint(tx, ty, 1, 'lightning_mat')
        material_layer.paint(tx, ty, max(2, r // 2), 'fire')
        _modify_height(heightmap, tx, ty, 2, -0.02)
        if particles: _spawn_lightning(particles, tx, ty)
        if event_log_fn: event_log_fn("Lightning strikes!")
        return True
    if tid == 'meteor':
        _modify_height(heightmap, tx, ty, max(6, r), -0.10)
        material_layer.paint(tx, ty, max(4, r), 'fire')
        material_layer.paint(tx, ty, max(2, r // 2), 'lava')
        material_layer.paint(tx, ty, max(1, r // 3), 'crater')
        reclassify_fn()
        if particles: _spawn_meteor(particles, tx, ty, r)
        if event_log_fn: event_log_fn("Meteor impact!")
        return True
    if tid == 'tornado':
        _modify_height(heightmap, tx, ty, r, -0.03)
        material_layer.erase(tx, ty, r)
        reclassify_fn()
        if event_log_fn: event_log_fn("Tornado rages!")
        return True
    if tid == 'earthquake':
        _earthquake(heightmap, tx, ty, r)
        reclassify_fn()
        if event_log_fn: event_log_fn("Earthquake!")
        return True
    if tid == 'rain_p':
        _modify_moisture(moisture, tx, ty, r, 0.08)
        material_layer.paint(tx, ty, r, 'water')
        reclassify_fn()
        return True
    if tid == 'blizzard':
        material_layer.paint(tx, ty, r, 'frost')
        material_layer.paint(tx, ty, max(1, r // 2), 'ice')
        _modify_moisture(moisture, tx, ty, r, 0.05)
        reclassify_fn()
        if event_log_fn: event_log_fn("Blizzard!")
        return True
    if tid == 'plague':
        material_layer.paint(tx, ty, r, 'spore')
        if event_log_fn: event_log_fn("Plague spreads!")
        return True
    if tid == 'flood':
        material_layer.paint(tx, ty, max(r * 2, 16), 'water')
        if event_log_fn: event_log_fn("Flood!")
        return True
    if tid == 'eruption':
        _create_volcano(heightmap, tx, ty)
        material_layer.paint(tx, ty, max(8, r), 'lava')
        material_layer.paint(tx, ty, max(4, r // 2), 'fire')
        reclassify_fn()
        if event_log_fn: event_log_fn("Volcanic eruption!")
        return True
    if tid == 'purge':
        material_layer.erase(tx, ty, r)
        material_layer.paint(tx, ty, r, 'bless')
        if event_log_fn: event_log_fn("Divine purge!")
        return True

    # ── Divine ─────────────────────────────────────────────────────────
    if tid == 'claim':
        god_id = gods[tool_state.selected_god]['god_id'] if gods else None
        if god_id:
            _claim_area(influence, god_id, tx, ty, r, strongholds)
        return True
    if tid == 'stronghold':
        god_id = gods[tool_state.selected_god]['god_id'] if gods else None
        if god_id:
            sh = {
                'id': f'sh_{len(strongholds)+1}',
                'god_id': god_id, 'x': tx, 'y': ty,
                'strength': 0.9, 'radius': 60,
                'name': f'{god_id.replace("god_","").title()} Bastion',
                'type': 'castle',
            }
            strongholds.append(sh)
            influence.add_stronghold(sh)
            if event_log_fn: event_log_fn(f"Stronghold for {god_id.replace('god_','').title()}")
        return True
    if tid == 'unclaim':
        to_remove = [s for s in strongholds
                     if abs(s['x'] - tx) <= r and abs(s['y'] - ty) <= r]
        for s in to_remove:
            strongholds.remove(s)
        if to_remove:
            influence.set_strongholds(strongholds)
        return bool(to_remove)
    if tid == 'gift':
        if world and hasattr(world, 'civilizations'):
            world.civilizations.gift_resources(tx, ty, 50)
            if event_log_fn: event_log_fn("Divine gift!")
        return True
    if tid == 'miracle':
        material_layer.paint(tx, ty, r, 'bless')
        _modify_moisture(moisture, tx, ty, r, 0.05)
        reclassify_fn()
        if event_log_fn: event_log_fn("Miracle!")
        return True

    # ── Weather ────────────────────────────────────────────────────────
    if tid.startswith('w_'):
        if world and hasattr(world, 'weather'):
            wtype = tid[2:]  # rain, storm, snow, heat, cold, clear
            world.weather.cast(wtype, tx, ty, r)
            if event_log_fn: event_log_fn(f"Weather: {wtype}!")
        return True

    # ── Erase ──────────────────────────────────────────────────────────
    if tid == 'erase':
        material_layer.erase(tx, ty, r)
        return True
    if tid == 'destroy':
        material_layer.erase(tx, ty, r)
        _modify_height(heightmap, tx, ty, r, -0.05)
        reclassify_fn()
        if event_log_fn: event_log_fn("Destruction!")
        return True
    if tid == 'kill':
        if world and hasattr(world, 'units'):
            world.units.kill_in_area(tx, ty, r)
            if event_log_fn: event_log_fn("Units slain!")
        return True
    if tid == 'reset':
        material_layer.erase(tx, ty, r)
        _modify_height(heightmap, tx, ty, r, 0)  # no-op but marks dirty
        reclassify_fn()
        return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _tile_range(cx, cy, r):
    y0 = max(0, cy - r)
    y1 = min(MAP_H, cy + r + 1)
    x0 = max(0, cx - r)
    x1 = min(MAP_W, cx + r + 1)
    return x0, y0, x1, y1


def _circ_mask(cx, cy, r):
    x0, y0, x1, y1 = _tile_range(cx, cy, r)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
    return x0, y0, x1, y1, mask


def _modify_height(hm, cx, cy, r, delta):
    x0, y0, x1, y1 = _tile_range(cx, cy, r)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.float32)
    strength = np.clip(1.0 - dist / max(r, 1), 0, 1)
    hm[y0:y1, x0:x1] = np.clip(hm[y0:y1, x0:x1] + delta * strength, 0, 1)


def _modify_moisture(mo, cx, cy, r, delta):
    x0, y0, x1, y1 = _tile_range(cx, cy, r)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.float32)
    strength = np.clip(1.0 - dist / max(r, 1), 0, 1)
    mo[y0:y1, x0:x1] = np.clip(mo[y0:y1, x0:x1] + delta * strength, 0, 1)


def _flatten(hm, cx, cy, r):
    x0, y0, x1, y1, mask = _circ_mask(cx, cy, r)
    region = hm[y0:y1, x0:x1]
    avg = float(np.mean(region[mask])) if np.any(mask) else 0.5
    region[mask] = region[mask] * 0.7 + avg * 0.3


def _smooth(hm, cx, cy, r):
    from scipy.ndimage import uniform_filter
    x0, y0, x1, y1 = _tile_range(cx, cy, max(r + 2, 3))
    region = hm[y0:y1, x0:x1].copy()
    smoothed = uniform_filter(region, size=3)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
    hm[y0:y1, x0:x1][mask] = smoothed[mask]


def _plateau(hm, cx, cy, r):
    x0, y0, x1, y1, mask = _circ_mask(cx, cy, r)
    region = hm[y0:y1, x0:x1]
    target = min(0.75, float(np.max(region[mask])) + 0.05) if np.any(mask) else 0.65
    region[mask] = region[mask] * 0.5 + target * 0.5


def _earthquake(hm, cx, cy, r):
    x0, y0, x1, y1 = _tile_range(cx, cy, r)
    noise = np.random.uniform(-0.06, 0.06, (y1 - y0, x1 - x0)).astype(np.float32)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
    hm[y0:y1, x0:x1][mask] = np.clip(hm[y0:y1, x0:x1][mask] + noise[mask], 0, 1)


def _carve_river(hm, cx, cy, r):
    """Lower a thin strip for river channel."""
    width = max(1, r // 3)
    length = r * 3
    dx = np.random.choice([-1, 0, 1])
    x, y = cx, cy
    for _ in range(length):
        if 0 <= y < MAP_H and 0 <= x < MAP_W:
            x0 = max(0, x - width)
            x1 = min(MAP_W, x + width + 1)
            hm[y, x0:x1] = np.clip(hm[y, x0:x1] - 0.04, 0, 1)
        y += 1
        x += np.random.choice([-1, 0, 0, 1]) + dx
        x = max(0, min(MAP_W - 1, x))


def _create_volcano(hm, cx, cy):
    """Create a volcano cone with crater."""
    r_outer = 12
    r_crater = 3
    x0, y0, x1, y1 = _tile_range(cx, cy, r_outer)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.float32)
    # Cone shape
    cone = np.clip(1.0 - dist / r_outer, 0, 1) * 0.25
    hm[y0:y1, x0:x1] = np.clip(hm[y0:y1, x0:x1] + cone, 0, 1)
    # Crater dip
    crater_mask = dist <= r_crater
    hm[y0:y1, x0:x1][crater_mask] -= 0.05
    np.clip(hm[y0:y1, x0:x1], 0, 1, out=hm[y0:y1, x0:x1])


def _paint_biome(bm, bn, hm, cx, cy, r, biome_name):
    idx = bn.index(biome_name) if biome_name in bn else None
    if idx is None:
        return
    x0, y0, x1, y1, mask = _circ_mask(cx, cy, r)
    water_biomes = {bn.index(b) for b in ('deep_ocean', 'ocean', 'shallow_water') if b in bn}
    region_bm = bm[y0:y1, x0:x1]
    land = np.isin(region_bm, list(water_biomes), invert=True)
    region_bm[mask & land] = idx


def _claim_area(influence, god_id, cx, cy, r, strongholds):
    sh = {
        'id': f'claim_{cx}_{cy}',
        'god_id': god_id, 'x': cx, 'y': cy,
        'strength': 0.6, 'radius': max(r * 2, 20),
        'name': 'Claimed', 'type': 'altar',
    }
    strongholds.append(sh)
    influence.add_stronghold(sh)


def _spawn_lightning(particles, tx, ty):
    import random
    for _ in range(20):
        particles._add(
            tx + random.uniform(-1, 1), ty + random.uniform(-4, 0),
            random.uniform(-0.5, 0.5), random.uniform(-4, -1),
            random.uniform(0.3, 1.0), (255, 255, 200), 2, 'magic')


def _spawn_meteor(particles, tx, ty, r):
    import random
    for _ in range(40):
        particles._add(
            tx + random.uniform(-r, r), ty + random.uniform(-r, r),
            random.uniform(-2, 2), random.uniform(-3, 1),
            random.uniform(0.5, 2.0),
            random.choice([(255, 120, 20), (255, 80, 10), (200, 60, 10)]),
            random.randint(1, 3), 'magic')
