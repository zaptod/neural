"""
World Map — Civilization System  (v6.0 LIVING WORLD)
Auto-expanding settlements, resource economies, building construction,
trade routes, diplomacy-driven wars. Civilizations LIVE and BREATHE.
"""
import numpy as np
import math
import random
try:
    from .config import (
        MAP_W, MAP_H, RESOURCE_TYPES,
        POP_GROWTH_BASE, POP_MAX_VILLAGE, POP_MAX_CITY,
        GOD_COLORS, BIOME_COLORS,
        SETTLE_MIN_DIST, EXPAND_FOOD_THRESH,
        AUTO_CIV_TICK,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from config import (
        MAP_W, MAP_H, RESOURCE_TYPES,
        POP_GROWTH_BASE, POP_MAX_VILLAGE, POP_MAX_CITY,
        GOD_COLORS, BIOME_COLORS,
        SETTLE_MIN_DIST, EXPAND_FOOD_THRESH,
        AUTO_CIV_TICK,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Building definitions (expanded)
# ═══════════════════════════════════════════════════════════════════════════════

BUILDING_DEFS = {
    'village':   {'pop_cap': POP_MAX_VILLAGE, 'produces': {'food': 3, 'wood': 1.5},  'size': 5},
    'city':      {'pop_cap': POP_MAX_CITY,    'produces': {'food': 2, 'gold': 3, 'wood': 1.0}, 'size': 7},
    'farm':      {'pop_cap': 0, 'produces': {'food': 6},   'size': 4},
    'mine':      {'pop_cap': 0, 'produces': {'stone': 3, 'iron': 2}, 'size': 4,
                  'requires_biome': {'hills', 'mountain', 'high_mountain'}},
    'port':      {'pop_cap': 0, 'produces': {'gold': 2, 'food': 2},  'size': 4,
                  'requires_biome': {'beach', 'shallow_water'}},
    'wall':      {'pop_cap': 0, 'produces': {}, 'size': 2, 'defense': 20},
    'bridge':    {'pop_cap': 0, 'produces': {}, 'size': 2},
    'workshop':  {'pop_cap': 0, 'produces': {'iron': 1, 'gold': 1},  'size': 4},
    'barracks':  {'pop_cap': 0, 'produces': {},  'size': 4, 'trains': True},
    'graveyard': {'pop_cap': 0, 'produces': {'mana': 1},  'size': 4},
    'temple':    {'pop_cap': 0, 'produces': {'mana': 3},  'size': 5},
}

RESOURCE_COLORS = {
    'food': (120, 200, 50), 'wood': (140, 100, 40),
    'stone': (140, 140, 150), 'iron': (180, 180, 190),
    'gold': (255, 210, 50), 'mana': (150, 120, 255),
}

# What each biome provides for resource production
BIOME_RESOURCE_BONUS = {
    'grassland':    {'food': 1.3, 'wood': 0.8},
    'forest':       {'food': 0.8, 'wood': 2.0},
    'dense_forest': {'food': 0.6, 'wood': 2.5, 'mana': 1.2},
    'tropical':     {'food': 1.5, 'wood': 1.5},
    'savanna':      {'food': 1.0},
    'hills':        {'stone': 1.5, 'iron': 1.3},
    'mountain':     {'stone': 2.0, 'iron': 1.8, 'gold': 1.5},
    'high_mountain':{'stone': 2.5, 'iron': 2.0, 'gold': 2.0},
    'swamp':        {'food': 0.5, 'mana': 1.5},
    'desert':       {'gold': 1.2},
    'taiga':        {'wood': 1.8, 'food': 0.5},
    'tundra':       {'stone': 1.2, 'food': 0.3},
    'beach':        {'food': 1.0, 'gold': 1.3},
    'volcano':      {'iron': 2.5, 'mana': 2.0},
    'crystal_field':{'mana': 3.0, 'gold': 1.5},
}

# Auto-build priorities per building type
AUTO_BUILD_PRIORITY = {
    'farm':      {'condition': lambda res: res.get('food', 0) < 30, 'cost': {'wood': 15}},
    'mine':      {'condition': lambda res: res.get('iron', 0) < 10, 'cost': {'wood': 20, 'food': 10}},
    'workshop':  {'condition': lambda res: res.get('iron', 0) > 20, 'cost': {'wood': 25, 'iron': 10}},
    'barracks':  {'condition': lambda res: res.get('food', 0) > 50, 'cost': {'wood': 30, 'iron': 15}},
    'temple':    {'condition': lambda res: res.get('gold', 0) > 20, 'cost': {'stone': 30, 'gold': 20}},
    'wall':      {'condition': lambda res: True, 'cost': {'stone': 10}},
}


class Building:
    """A placed building in the world — with synergy modifier slots."""
    __slots__ = ('btype', 'x', 'y', 'god_id', 'hp', 'max_hp',
                 'level', 'population', 'resources', 'age',
                 '_weather_prod', '_mat_prod')

    def __init__(self, btype, x, y, god_id=None):
        self.btype      = btype
        self.x, self.y  = x, y
        self.god_id     = god_id
        defn            = BUILDING_DEFS.get(btype, {})
        self.max_hp     = 50 + defn.get('defense', 0)
        self.hp         = self.max_hp
        self.level      = 1
        self.population = 10 if defn.get('pop_cap', 0) > 0 else 0
        self.resources  = {r: 0 for r in RESOURCE_TYPES}
        self.age        = 0
        self._weather_prod = 1.0
        self._mat_prod     = 1.0

    @property
    def pop_cap(self):
        defn = BUILDING_DEFS.get(self.btype, {})
        return defn.get('pop_cap', 0) * self.level

    @property
    def display_name(self):
        return f"{self.btype.title()} Lv{self.level}"


class CivilizationSystem:
    """Manages all buildings, population, resources, auto-expansion."""

    def __init__(self):
        self.buildings: list[Building] = []
        self._version = 0
        self.building_grid = np.zeros((MAP_H, MAP_W), dtype=np.int16)
        self.building_grid.fill(-1)
        self._rng = np.random.RandomState(42)
        self._auto_accum = 0.0

    # ── place ──────────────────────────────────────────────────────────────
    def place_building(self, btype, x, y, god_id=None):
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return None
        if self.building_grid[y, x] >= 0:
            return None
        b = Building(btype, x, y, god_id)
        idx = len(self.buildings)
        self.buildings.append(b)
        defn = BUILDING_DEFS.get(btype, {})
        sz = defn.get('size', 3) // 2
        y0, y1 = max(0, y - sz), min(MAP_H, y + sz + 1)
        x0, x1 = max(0, x - sz), min(MAP_W, x + sz + 1)
        self.building_grid[y0:y1, x0:x1] = idx
        self._version += 1
        return b

    def remove_building(self, idx):
        if 0 <= idx < len(self.buildings):
            b = self.buildings[idx]
            defn = BUILDING_DEFS.get(b.btype, {})
            sz = defn.get('size', 3) // 2
            y0, y1 = max(0, b.y - sz), min(MAP_H, b.y + sz + 1)
            x0, x1 = max(0, b.x - sz), min(MAP_W, b.x + sz + 1)
            mask = self.building_grid[y0:y1, x0:x1] == idx
            self.building_grid[y0:y1, x0:x1][mask] = -1
            self.buildings[idx] = None
            self._version += 1

    def get_at(self, x, y):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            idx = int(self.building_grid[y, x])
            if idx >= 0 and idx < len(self.buildings):
                return self.buildings[idx]
        return None

    def get_nearby(self, x, y, radius=10):
        result = []
        for b in self.buildings:
            if b is None:
                continue
            if abs(b.x - x) <= radius and abs(b.y - y) <= radius:
                result.append(b)
        return result

    def gift_resources(self, x, y, amount=50):
        b = self.get_at(x, y)
        if b is None:
            nearby = self.get_nearby(x, y, 15)
            for nb in nearby:
                if nb.btype in ('village', 'city'):
                    b = nb; break
        if b:
            for r in RESOURCE_TYPES:
                b.resources[r] += amount

    # ── simulation tick ────────────────────────────────────────────────────
    def simulate(self, dt, biome_map, biome_names, heightmap, influence, material_layer,
                 weather=None, season=None, world=None):
        """One tick of civilization simulation — with universal synergy + auto-expansion."""
        try:
            from .synergy import (
                BIOME_BUILDING_PRODUCTION,
                SEASON_EFFECTS,
                MATERIAL_BUILDING_EFFECTS,
            )
        except ImportError:  # pragma: no cover - direct script fallback
            from synergy import (
                BIOME_BUILDING_PRODUCTION,
                SEASON_EFFECTS,
                MATERIAL_BUILDING_EFFECTS,
            )
        changed = False

        season_name = season or 'spring'
        season_fx = SEASON_EFFECTS.get(season_name, {})
        growth_mult = season_fx.get('growth_mult', 1.0)
        food_season_mult = season_fx.get('food_mult', 1.0)

        for b in self.buildings:
            if b is None:
                continue
            b.age += 1
            defn = BUILDING_DEFS.get(b.btype, {})

            biome = 'grassland'
            if 0 <= b.x < MAP_W and 0 <= b.y < MAP_H:
                biome = biome_names[biome_map[b.y, b.x]]

            # ── Resource production ────────────────────────────────────
            produces = defn.get('produces', {})
            biome_prods = BIOME_BUILDING_PRODUCTION.get(biome, {})
            biome_bonus = BIOME_RESOURCE_BONUS.get(biome, {})

            for res, base_amt in produces.items():
                biome_mult = biome_prods.get(res, 1.0)
                s_mult = food_season_mult if res == 'food' else 1.0
                w_mult = getattr(b, '_weather_prod', 1.0)
                m_mult = getattr(b, '_mat_prod', 1.0)
                level_mult = 1.0 + (b.level - 1) * 0.3
                total = base_amt * biome_mult * s_mult * w_mult * m_mult * level_mult
                b.resources[res] += max(0, total)

            # Passive biome resource bonus for settlements
            if b.btype in ('village', 'city'):
                for res, mult in biome_bonus.items():
                    if mult > 1.0:
                        b.resources[res] += 0.5 * (mult - 1.0) * b.level

            # ── Population growth ──────────────────────────────────────
            if b.population > 0 and b.pop_cap > 0:
                food = b.resources.get('food', 0)
                if food >= b.population * 0.1:
                    growth = POP_GROWTH_BASE * b.population * growth_mult
                    growth *= (1.0 + food * 0.001)
                    growth *= getattr(b, '_weather_prod', 1.0)
                    growth *= getattr(b, '_mat_prod', 1.0)
                    b.population = min(b.pop_cap, b.population + growth)
                    b.resources['food'] -= b.population * 0.05
                    b.resources['food'] = max(0, b.resources['food'])
                else:
                    starve_rate = 0.5
                    if season_name == 'winter':
                        starve_rate = 1.5
                    b.population = max(1, b.population - starve_rate)

                # Level up
                if b.population >= b.pop_cap * 0.8 and b.level < 5:
                    b.level += 1
                    changed = True
                    if world and hasattr(world, 'history'):
                        world.history.record('city_upgraded',
                            f"{b.btype.title()} at ({b.x},{b.y}) reaches Lv{b.level}",
                            god_id=b.god_id, pos=(b.x, b.y))

                # Village → City upgrade
                if b.btype == 'village' and b.level >= 4 and b.population >= POP_MAX_VILLAGE * 0.9:
                    b.btype = 'city'
                    b.max_hp = 100
                    changed = True

            # ── HP check ───────────────────────────────────────────────
            if b.hp <= 0:
                idx = self.buildings.index(b)
                self.remove_building(idx)
                changed = True
                continue

            if b.hp < b.max_hp:
                b.hp = min(b.max_hp, b.hp + 0.1 * b.level)

            # ── Trade ──────────────────────────────────────────────────
            if b.btype in ('village', 'city', 'port') and b.age % 30 == 0:
                nearby = self.get_nearby(b.x, b.y, 25)
                for nb in nearby:
                    if nb is b or nb is None or nb.god_id != b.god_id:
                        continue
                    for r in RESOURCE_TYPES:
                        excess = b.resources[r] - 50
                        deficit = 50 - nb.resources[r]
                        if excess > 10 and deficit > 10:
                            transfer = min(excess * 0.1, deficit * 0.5)
                            b.resources[r] -= transfer
                            nb.resources[r] += transfer

        # ── Auto-civilization expansion ────────────────────────────────
        self._auto_accum += dt
        if self._auto_accum >= AUTO_CIV_TICK and world:
            self._auto_expand(world, biome_map, biome_names, heightmap, influence)
            self._auto_accum = 0.0
            changed = True

        if changed:
            self._version += 1
        return changed

    # ── auto-expansion: civilizations BUILD and GROW on their own ──────────
    def _auto_expand(self, world, biome_map, biome_names, heightmap, influence):
        """Auto-expand civilizations: found settlements, build structures, train units."""
        # Group buildings by god
        from collections import defaultdict
        god_buildings = defaultdict(list)
        god_resources = defaultdict(lambda: {r: 0 for r in RESOURCE_TYPES})

        for b in self.buildings:
            if b is None:
                continue
            god_buildings[b.god_id].append(b)
            for r in RESOURCE_TYPES:
                god_resources[b.god_id][r] += b.resources.get(r, 0)

        for god in world.gods:
            gid = god['god_id']
            buildings = god_buildings.get(gid, [])
            resources = god_resources[gid]

            # ── Auto-found new settlement ──────────────────────────────
            settlements = [b for b in buildings if b.btype in ('village', 'city')]
            if (resources.get('food', 0) > EXPAND_FOOD_THRESH and
                    resources.get('wood', 0) > 30 and
                    self._rng.random() < 0.15):
                self._auto_found_settlement(gid, settlements, world,
                                             biome_map, biome_names, heightmap, influence)

            # ── Auto-build support structures ──────────────────────────
            for settlement in settlements:
                if settlement.age % 20 != 0:  # Check every 20 civ ticks
                    continue
                self._auto_build_support(gid, settlement, resources, world,
                                          biome_map, biome_names, heightmap, influence)

            # ── Auto-train units from barracks ─────────────────────────
            barracks = [b for b in buildings if b.btype == 'barracks']
            for bk in barracks:
                if bk.age % 25 != 0:
                    continue
                if resources.get('food', 0) > 20:
                    self._auto_train_unit(gid, bk, resources, world)

    def _auto_found_settlement(self, gid, existing_settlements, world,
                                biome_map, biome_names, heightmap, influence):
        """Find a good location and found a new village near existing territory."""
        # Search near existing buildings/strongholds (where territory actually is)
        anchors = []
        for b in self.active_buildings:
            if b.god_id == gid:
                anchors.append((b.x, b.y))
        for sh in getattr(world, 'strongholds', []):
            if sh.get('god_id') == gid:
                anchors.append((sh['x'], sh['y']))
        if not anchors:
            return

        for _ in range(40):
            # Pick a random anchor and offset from it
            ax, ay = anchors[self._rng.randint(0, len(anchors))]
            dist = self._rng.uniform(SETTLE_MIN_DIST, SETTLE_MIN_DIST * 3)
            angle = self._rng.uniform(0, 6.283)
            x = int(ax + dist * math.cos(angle))
            y = int(ay + dist * math.sin(angle))

            if x < 20 or x >= MAP_W - 20 or y < 20 or y >= MAP_H - 20:
                continue

            # Must be in our territory
            dom_gid, strength = influence.get_dominant_at(x, y)
            if dom_gid != gid or strength < 0.1:
                continue

            # Must be land
            biome = biome_names[biome_map[y, x]]
            if biome in ('deep_ocean', 'ocean', 'shallow_water', 'volcano'):
                continue

            # Must be reasonable elevation
            elev = heightmap[y, x]
            if elev < 0.29 or elev > 0.75:
                continue

            # Must be far enough from existing settlements
            too_close = False
            for s in existing_settlements:
                if math.hypot(s.x - x, s.y - y) < SETTLE_MIN_DIST:
                    too_close = True
                    break
            # Also check all buildings
            if not too_close:
                for b in self.active_buildings:
                    if b.btype in ('village', 'city') and math.hypot(b.x - x, b.y - y) < SETTLE_MIN_DIST * 0.7:
                        too_close = True
                        break

            if too_close:
                continue

            # Found a good spot! Place village
            b = self.place_building('village', x, y, gid)
            if b:
                b.resources['food'] = 30
                b.resources['wood'] = 15
                if hasattr(world, 'history'):
                    world.history.record('settlement_founded',
                        f"{gid} founds a village at ({x},{y})",
                        god_id=gid, pos=(x, y))
                    world.history.god_stats[gid]['settlements_founded'] += 1
                break

    def _auto_build_support(self, gid, settlement, resources, world,
                             biome_map, biome_names, heightmap, influence):
        """Auto-build support structures near a settlement."""
        for btype, info in AUTO_BUILD_PRIORITY.items():
            if not info['condition'](resources):
                continue

            # Check cost
            cost = info['cost']
            can_afford = all(resources.get(r, 0) >= amt for r, amt in cost.items())
            if not can_afford:
                continue

            # Check if already have enough nearby
            nearby = self.get_nearby(settlement.x, settlement.y, 15)
            count_type = sum(1 for b in nearby if b.btype == btype)
            if btype == 'farm' and count_type >= 3:
                continue
            if btype in ('mine', 'workshop', 'barracks', 'temple') and count_type >= 1:
                continue
            if btype == 'wall' and count_type >= 6:
                continue

            # Find placement spot
            for _ in range(10):
                dx = self._rng.randint(-12, 13)
                dy = self._rng.randint(-12, 13)
                bx = settlement.x + dx
                by = settlement.y + dy
                if not (0 <= bx < MAP_W and 0 <= by < MAP_H):
                    continue

                # Check biome requirement
                biome = biome_names[biome_map[by, bx]]
                req_biomes = BUILDING_DEFS.get(btype, {}).get('requires_biome')
                if req_biomes and biome not in req_biomes:
                    continue

                if biome in ('deep_ocean', 'ocean', 'shallow_water'):
                    continue

                b = self.place_building(btype, bx, by, gid)
                if b:
                    # Deduct cost from settlement
                    for r, amt in cost.items():
                        settlement.resources[r] = max(0, settlement.resources[r] - amt)
                    break
            break  # Only build one structure per tick

    def _auto_train_unit(self, gid, barracks, resources, world):
        """Auto-train units at barracks."""
        # Pick unit type based on needs
        unit_types = ['warrior', 'archer']
        if resources.get('iron', 0) > 15:
            unit_types.append('knight')
        if resources.get('mana', 0) > 10:
            unit_types.append('mage')
        if resources.get('food', 0) > 40:
            unit_types.append('berserker')

        utype = random.choice(unit_types)
        cost = {'food': 10}

        if all(resources.get(r, 0) >= amt for r, amt in cost.items()):
            world.units.spawn(utype, barracks.x + self._rng.randint(-3, 4),
                             barracks.y + self._rng.randint(-3, 4), gid)
            for r, amt in cost.items():
                barracks.resources[r] = max(0, barracks.resources.get(r, 0) - amt)

    # ── queries ────────────────────────────────────────────────────────────
    def get_god_buildings(self, god_id):
        return [b for b in self.buildings if b and b.god_id == god_id]

    def get_total_population(self, god_id=None):
        total = 0
        for b in self.buildings:
            if b is None:
                continue
            if god_id and b.god_id != god_id:
                continue
            total += b.population
        return int(total)

    def get_total_resources(self, god_id=None):
        totals = {r: 0 for r in RESOURCE_TYPES}
        for b in self.buildings:
            if b is None:
                continue
            if god_id and b.god_id != god_id:
                continue
            for r in RESOURCE_TYPES:
                totals[r] += b.resources.get(r, 0)
        return totals

    @property
    def active_buildings(self):
        return [b for b in self.buildings if b is not None]
