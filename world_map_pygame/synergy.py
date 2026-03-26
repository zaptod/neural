"""
World Map — Universal Synergy Engine  (v5.0)
Everything affects everything: weather↔units↔buildings↔materials↔biomes↔terrain.
Central orchestration for ALL cross-system interactions.
"""
import numpy as np
import math
import random
try:
    from .config import (
        MAP_W, MAP_H, UNIT_TYPES, UNIT_SPEED,
        TEMP_COLD, TEMP_COOL, TEMP_WARM, TEMP_HOT,
        SEASONS,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from config import (
        MAP_W, MAP_H, UNIT_TYPES, UNIT_SPEED,
        TEMP_COLD, TEMP_COOL, TEMP_WARM, TEMP_HOT,
        SEASONS,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTION DATA TABLES
# ═══════════════════════════════════════════════════════════════════════════════

# ── Weather → Unit effects ─────────────────────────────────────────────────────
# weather_type → { stat_modifier dict }
WEATHER_UNIT_EFFECTS = {
    'rain':  {'spd_mult': 0.85, 'hp_tick': 0,    'atk_mult': 0.90, 'desc': 'Rain slows, dampens attacks'},
    'storm': {'spd_mult': 0.70, 'hp_tick': -2,   'atk_mult': 0.80, 'desc': 'Storms damage & disorient'},
    'snow':  {'spd_mult': 0.60, 'hp_tick': -1,   'atk_mult': 0.95, 'desc': 'Snow slows, chills'},
    'heat':  {'spd_mult': 0.90, 'hp_tick': -1.5, 'atk_mult': 0.95, 'desc': 'Heat dehydrates'},
    'cold':  {'spd_mult': 0.55, 'hp_tick': -2,   'atk_mult': 0.85, 'desc': 'Cold freezes & slows'},
}

# Unit immunities to weather
UNIT_WEATHER_IMMUNITY = {
    'dragon':  {'heat', 'rain'},           # Dragons love heat, rain doesn't bother
    'golem':   {'heat', 'cold', 'snow'},   # Stone doesn't care about temperature
    'spirit':  {'rain', 'storm', 'snow', 'heat', 'cold'},  # Ethereal
    'undead':  {'cold', 'snow'},           # Dead don't feel cold
}

# ── Weather → Building effects ─────────────────────────────────────────────────
WEATHER_BUILDING_EFFECTS = {
    'rain':  {'prod_mult': 1.15, 'hp_tick': 0,   'fire_suppress': True,  'desc': 'Rain boosts farms, stops fire'},
    'storm': {'prod_mult': 0.60, 'hp_tick': -3,  'fire_suppress': False, 'desc': 'Storms damage buildings'},
    'snow':  {'prod_mult': 0.40, 'hp_tick': -1,  'fire_suppress': True,  'desc': 'Snow halts production'},
    'heat':  {'prod_mult': 0.75, 'hp_tick': -0.5,'fire_suppress': False, 'desc': 'Heat wilts crops'},
    'cold':  {'prod_mult': 0.30, 'hp_tick': -2,  'fire_suppress': True,  'desc': 'Cold freezes operations'},
}

# Buildings resistant to weather
BUILDING_WEATHER_RESIST = {
    'wall':     {'storm', 'rain', 'snow'},
    'mine':     {'storm', 'rain', 'snow', 'heat'},     # Underground
    'temple':   {'storm', 'cold'},                      # Divine protection
}

# ── Material → Unit effects (per tick on tile) ────────────────────────────────
MATERIAL_UNIT_EFFECTS = {
    'fire':      {'hp_tick': -8,  'spd_mult': 1.0,  'desc': 'Burns'},
    'lava':      {'hp_tick': -15, 'spd_mult': 0.3,  'desc': 'Melts'},
    'hellfire':  {'hp_tick': -12, 'spd_mult': 0.8,  'desc': 'Cursed flames'},
    'acid':      {'hp_tick': -6,  'spd_mult': 0.7,  'desc': 'Dissolves'},
    'frost':     {'hp_tick': -1,  'spd_mult': 0.4,  'desc': 'Freezes movement'},
    'corrupt':   {'hp_tick': -3,  'spd_mult': 0.9,  'desc': 'Corrupts life'},
    'spore':     {'hp_tick': -4,  'spd_mult': 0.8,  'desc': 'Toxic spores'},
    'bless':     {'hp_tick': 5,   'spd_mult': 1.1,  'desc': 'Divine healing'},
    'steam':     {'hp_tick': -1,  'spd_mult': 0.9,  'desc': 'Scalds, obscures'},
    'swamp_gas': {'hp_tick': -3,  'spd_mult': 0.85, 'desc': 'Toxic gas'},
    'vine':      {'hp_tick': 0,   'spd_mult': 0.3,  'desc': 'Entangles'},
    'water':     {'hp_tick': 0,   'spd_mult': 0.6,  'desc': 'Wades through water'},
    'ice':       {'hp_tick': 0,   'spd_mult': 0.5,  'desc': 'Slippery ice'},
    'crystal':   {'hp_tick': 2,   'spd_mult': 1.0,  'desc': 'Crystal energy'},
    'lightning_mat': {'hp_tick': -20, 'spd_mult': 1.0, 'desc': 'Electrocuted'},
}

# Unit immunities to materials
UNIT_MATERIAL_IMMUNITY = {
    'dragon':  {'fire', 'lava', 'hellfire', 'steam'},   # Fire-born
    'golem':   {'fire', 'acid', 'frost', 'vine'},       # Stone body
    'spirit':  {'fire', 'lava', 'acid', 'frost', 'vine', 'water', 'ice'},  # Ethereal
    'undead':  {'corrupt', 'spore', 'swamp_gas'},        # Already dead
}

# Special: bless heals living, hurts undead; corrupt heals undead, hurts living
MATERIAL_UNIT_SPECIAL = {
    ('bless', 'undead'):  {'hp_tick': -10},   # Bless purifies undead
    ('corrupt', 'undead'): {'hp_tick': 3},    # Corruption empowers undead
    ('crystal', 'mage'):   {'hp_tick': 3, 'atk_mult': 1.5},  # Crystal empowers mages
    ('crystal', 'spirit'): {'hp_tick': 3, 'atk_mult': 1.3},  # Crystal empowers spirits
}

# ── Material → Building effects (per tick) ────────────────────────────────────
MATERIAL_BUILDING_EFFECTS = {
    'fire':      {'hp_tick': -10, 'prod_mult': 0.0,  'desc': 'Burning'},
    'lava':      {'hp_tick': -20, 'prod_mult': 0.0,  'desc': 'Engulfed in lava'},
    'hellfire':  {'hp_tick': -15, 'prod_mult': 0.0,  'desc': 'Cursed flames'},
    'acid':      {'hp_tick': -8,  'prod_mult': 0.2,  'desc': 'Dissolving'},
    'frost':     {'hp_tick': -2,  'prod_mult': 0.3,  'desc': 'Frozen'},
    'corrupt':   {'hp_tick': -5,  'prod_mult': 0.4,  'desc': 'Corrupted'},
    'spore':     {'hp_tick': -3,  'prod_mult': 0.5,  'desc': 'Infested'},
    'bless':     {'hp_tick': 5,   'prod_mult': 1.3,  'desc': 'Blessed'},
    'vine':      {'hp_tick': -1,  'prod_mult': 0.6,  'desc': 'Overgrown'},
    'water':     {'hp_tick': -3,  'prod_mult': 0.3,  'desc': 'Flooded'},
    'crystal':   {'hp_tick': 2,   'prod_mult': 1.5,  'desc': 'Crystal-powered'},
    'swamp_gas': {'hp_tick': -2,  'prod_mult': 0.7,  'desc': 'Gas contamination'},
}

# Buildings resistant to certain materials
BUILDING_MATERIAL_RESIST = {
    'wall':   {'vine', 'water', 'frost'},
    'mine':   {'water', 'frost', 'vine'},
    'temple': {'corrupt', 'spore', 'swamp_gas'},  # Divine protection
}

# ── Biome → Unit effects ──────────────────────────────────────────────────────
BIOME_UNIT_EFFECTS = {
    'deep_ocean':    {'spd_mult': 0.0, 'hp_tick': -15, 'def_mult': 0.5},
    'ocean':         {'spd_mult': 0.0, 'hp_tick': -10, 'def_mult': 0.5},
    'shallow_water': {'spd_mult': 0.4, 'hp_tick': -2,  'def_mult': 0.7},
    'reef':          {'spd_mult': 0.3, 'hp_tick': -3,  'def_mult': 0.6},
    'beach':         {'spd_mult': 0.90, 'hp_tick': 0,  'def_mult': 0.9},
    'desert':        {'spd_mult': 0.75, 'hp_tick': -0.5,'def_mult': 0.8},
    'savanna':       {'spd_mult': 0.95, 'hp_tick': 0,  'def_mult': 0.9},
    'grassland':     {'spd_mult': 1.0,  'hp_tick': 0,  'def_mult': 1.0},
    'forest':        {'spd_mult': 0.80, 'hp_tick': 0,  'def_mult': 1.3},
    'dense_forest':  {'spd_mult': 0.60, 'hp_tick': 0,  'def_mult': 1.5},
    'tropical':      {'spd_mult': 0.70, 'hp_tick': -0.3,'def_mult': 1.2},
    'swamp':         {'spd_mult': 0.50, 'hp_tick': -1,  'def_mult': 0.8},
    'tundra':        {'spd_mult': 0.80, 'hp_tick': -0.5,'def_mult': 1.0},
    'taiga':         {'spd_mult': 0.75, 'hp_tick': 0,  'def_mult': 1.2},
    'hills':         {'spd_mult': 0.85, 'hp_tick': 0,  'def_mult': 1.2},
    'mountain':      {'spd_mult': 0.45, 'hp_tick': -0.5,'def_mult': 1.6},
    'high_mountain': {'spd_mult': 0.30, 'hp_tick': -1,  'def_mult': 1.8},
    'volcano':       {'spd_mult': 0.40, 'hp_tick': -3,  'def_mult': 1.0},
    'snow':          {'spd_mult': 0.50, 'hp_tick': -1.5,'def_mult': 1.1},
    'crystal_field': {'spd_mult': 0.85, 'hp_tick': 0.5, 'def_mult': 1.1},
    'corrupted':     {'spd_mult': 0.70, 'hp_tick': -2,  'def_mult': 0.7},
}

# Units with special biome interactions
UNIT_BIOME_BONUS = {
    ('dragon', 'volcano'):       {'atk_mult': 1.5, 'hp_regen': 5},
    ('dragon', 'mountain'):      {'atk_mult': 1.2, 'hp_regen': 2},
    ('undead', 'corrupted'):     {'atk_mult': 1.4, 'hp_regen': 3},
    ('undead', 'swamp'):         {'atk_mult': 1.2, 'hp_regen': 1},
    ('undead', 'graveyard'):     {'atk_mult': 1.3, 'hp_regen': 2},
    ('golem', 'mountain'):       {'atk_mult': 1.3, 'hp_regen': 2},
    ('golem', 'high_mountain'):  {'atk_mult': 1.4, 'hp_regen': 3},
    ('spirit', 'crystal_field'): {'atk_mult': 1.5, 'hp_regen': 4},
    ('mage', 'crystal_field'):   {'atk_mult': 1.4, 'hp_regen': 2},
    ('archer', 'forest'):        {'atk_mult': 1.3, 'def_bonus': 0.3},
    ('archer', 'hills'):         {'atk_mult': 1.4, 'range_bonus': 2},
    ('knight', 'grassland'):     {'atk_mult': 1.2, 'spd_bonus': 1.0},
    ('knight', 'savanna'):       {'atk_mult': 1.2, 'spd_bonus': 0.8},
    ('warrior', 'hills'):        {'atk_mult': 1.1, 'def_bonus': 0.2},
    ('settler', 'grassland'):    {'spd_bonus': 0.5},
    ('settler', 'forest'):       {'spd_bonus': 0.3},
}

# ── Biome → Building production multipliers ───────────────────────────────────
BIOME_BUILDING_PRODUCTION = {
    # biome → { resource: multiplier }
    'grassland':    {'food': 1.3, 'wood': 0.8},
    'forest':       {'food': 0.8, 'wood': 1.8, 'mana': 1.1},
    'dense_forest': {'food': 0.6, 'wood': 2.0, 'mana': 1.2},
    'tropical':     {'food': 1.2, 'wood': 1.5, 'mana': 1.0},
    'savanna':      {'food': 1.0, 'gold': 1.1},
    'desert':       {'food': 0.3, 'gold': 1.5, 'stone': 1.2},
    'swamp':        {'food': 0.5, 'mana': 1.3, 'wood': 0.8},
    'hills':        {'food': 0.7, 'stone': 1.5, 'iron': 1.3},
    'mountain':     {'food': 0.2, 'stone': 2.0, 'iron': 1.8, 'gold': 1.3},
    'high_mountain':{'food': 0.1, 'stone': 2.5, 'iron': 2.0, 'gold': 1.5},
    'tundra':       {'food': 0.3, 'stone': 1.0},
    'taiga':        {'food': 0.5, 'wood': 1.5},
    'snow':         {'food': 0.1, 'stone': 0.8},
    'beach':        {'food': 0.8, 'gold': 1.2},
    'volcano':      {'food': 0.0, 'iron': 2.0, 'mana': 1.5},
    'crystal_field':{'food': 0.3, 'mana': 2.5, 'gold': 1.5},
    'corrupted':    {'food': 0.0, 'mana': 2.0},
}

# ── Season → Global modifiers ─────────────────────────────────────────────────
SEASON_EFFECTS = {
    'spring': {'food_mult': 1.3, 'growth_mult': 1.4, 'unit_heal': 0.5, 'desc': 'Spring renewal'},
    'summer': {'food_mult': 1.5, 'growth_mult': 1.2, 'unit_heal': 0,   'desc': 'Summer abundance'},
    'autumn': {'food_mult': 1.0, 'growth_mult': 0.8, 'unit_heal': 0,   'desc': 'Autumn harvest'},
    'winter': {'food_mult': 0.3, 'growth_mult': 0.3, 'unit_heal': -0.5,'desc': 'Winter hardship'},
}

# ── Unit → Material emissions (what units drop/create) ────────────────────────
UNIT_MATERIAL_EMISSIONS = {
    'dragon': {'material': 'fire', 'chance': 0.03, 'life': 40},
    'undead': {'material': 'corrupt', 'chance': 0.02, 'life': 80},
    'spirit': {'material': 'bless', 'chance': 0.015, 'life': 60},
    'golem':  {'material': 'stone', 'chance': 0.01, 'life': 0},
    'mage':   {'material': 'crystal', 'chance': 0.005, 'life': 0},
}

# ── Building → Environment effects ────────────────────────────────────────────
BUILDING_ENVIRONMENT_EFFECTS = {
    'farm':      {'moisture_boost': 0.002, 'radius': 5},
    'mine':      {'elevation_reduce': 0.0005, 'radius': 3},
    'temple':    {'bless_chance': 0.01, 'radius': 8},
    'graveyard': {'corrupt_chance': 0.008, 'radius': 6},
    'workshop':  {'smoke_chance': 0.005, 'radius': 3},
}

# ── Building → Unit aura buffs ────────────────────────────────────────────────
BUILDING_UNIT_AURA = {
    'barracks':  {'atk_buff': 1.2, 'def_buff': 1.15, 'radius': 10},
    'temple':    {'heal_per_tick': 3,  'def_buff': 1.1,  'radius': 12},
    'wall':      {'def_buff': 1.4, 'radius': 3},
    'workshop':  {'siege_repair': 5,   'golem_repair': 5,  'radius': 8},
    'farm':      {'heal_per_tick': 1,  'radius': 6},
    'graveyard': {'undead_buff': 1.3,  'radius': 8},
    'city':      {'def_buff': 1.1, 'morale': 1.2, 'radius': 15},
    'village':   {'heal_per_tick': 0.5, 'radius': 8},
}

# ── Unit combat type advantages ────────────────────────────────────────────────
# (attacker, defender) → damage multiplier
COMBAT_TYPE_ADVANTAGE = {
    ('warrior', 'archer'):   1.4,
    ('warrior', 'mage'):     1.3,
    ('archer', 'mage'):      1.5,
    ('archer', 'dragon'):    0.6,    # Hard to hit dragons
    ('archer', 'spirit'):    0.3,    # Arrows pass through
    ('knight', 'warrior'):   1.4,
    ('knight', 'archer'):    1.6,    # Cavalry charge
    ('knight', 'settler'):   2.0,
    ('mage', 'warrior'):     1.3,
    ('mage', 'knight'):      1.4,    # Magic vs armor
    ('mage', 'golem'):       1.5,
    ('mage', 'spirit'):      1.4,
    ('siege', 'golem'):      1.3,
    ('siege', 'warrior'):    0.7,    # Siege is for buildings
    ('dragon', 'warrior'):   1.5,
    ('dragon', 'archer'):    1.6,
    ('dragon', 'knight'):    1.3,
    ('dragon', 'undead'):    1.2,
    ('undead', 'settler'):   1.8,
    ('undead', 'warrior'):   0.9,
    ('golem', 'warrior'):    1.4,
    ('golem', 'knight'):     1.3,
    ('golem', 'siege'):      1.5,
    ('spirit', 'warrior'):   1.3,
    ('spirit', 'settler'):   1.5,
    ('spirit', 'undead'):    1.4,    # Spirits disrupt undead
    ('settler', 'warrior'):  0.3,    # Settlers can't fight
    ('settler', 'archer'):   0.3,
    # ── v6.0 new unit types ──
    ('scout', 'settler'):    1.6,    # Scout overwhelms civilians
    ('scout', 'warrior'):    0.7,    # Scout weak in direct combat
    ('scout', 'assassin'):   0.5,    # Scout can't hide from assassin
    ('healer', 'warrior'):   0.4,    # Healer not a fighter
    ('healer', 'undead'):    1.6,    # Holy healing hurts undead
    ('healer', 'spirit'):    1.3,    # Purifying presence
    ('berserker', 'warrior'): 1.5,   # Rage beats discipline
    ('berserker', 'knight'):  1.3,   # Fury vs armor
    ('berserker', 'archer'):  0.8,   # Reckless charge vs ranged
    ('berserker', 'mage'):    0.7,   # Berserkers vulnerable to magic
    ('assassin', 'mage'):     1.8,   # Backstab casters
    ('assassin', 'archer'):   1.6,   # Close-range kill
    ('assassin', 'knight'):   0.6,   # Can't pierce heavy armor
    ('assassin', 'golem'):    0.4,   # No vitals to target
    ('assassin', 'warrior'):  1.3,   # Surprise attack
    ('titan', 'warrior'):     1.8,   # Overwhelming force
    ('titan', 'knight'):      1.6,   # Crushes cavalry
    ('titan', 'archer'):      1.4,   # Arrows bounce off
    ('titan', 'mage'):        0.8,   # Magic can fell titans
    ('titan', 'assassin'):    0.9,   # Titans have weak spots
    ('titan', 'dragon'):      1.2,   # Clash of titans
    ('mage', 'berserker'):    1.5,   # Magic exploits rage
    ('knight', 'assassin'):   1.5,   # Armor protects from backstab
    ('dragon', 'berserker'):  1.4,   # Fire from above
    ('dragon', 'titan'):      0.9,   # Even match  
}

# ═══════════════════════════════════════════════════════════════════════════════
# SYNERGY ENGINE — Orchestrates all cross-system interactions
# ═══════════════════════════════════════════════════════════════════════════════

class SynergyEngine:
    """Central engine that processes all universal synergy interactions each tick."""

    def __init__(self):
        self._rng = np.random.RandomState(500)
        self._tick_count = 0

    def tick(self, dt, world):
        """
        Main synergy tick — called from main.py update loop.
        `world` object must have: weather, units, civilizations, materials,
        heightmap, moisture, biome_map, biome_names, land_mask, influence, temperature.
        """
        self._tick_count += 1
        changed = False

        changed |= self._weather_affects_units(dt, world)
        changed |= self._weather_affects_buildings(dt, world)
        changed |= self._material_affects_units(dt, world)
        changed |= self._material_affects_buildings(dt, world)
        changed |= self._biome_affects_units(dt, world)
        changed |= self._season_affects_world(dt, world)
        changed |= self._units_emit_materials(dt, world)
        changed |= self._buildings_affect_environment(dt, world)
        changed |= self._buildings_buff_units(dt, world)
        changed |= self._units_attack_buildings(dt, world)

        return changed

    # ── Weather → Units ────────────────────────────────────────────────────
    def _weather_affects_units(self, dt, world):
        changed = False
        weather = world.weather
        units = world.units

        for zone in weather.zones:
            effects = WEATHER_UNIT_EFFECTS.get(zone.wtype)
            if not effects:
                continue

            r2 = zone.radius * zone.radius
            for u in units.units:
                if not u.alive:
                    continue
                dx = u.x - zone.x
                dy = u.y - zone.y
                if dx * dx + dy * dy > r2:
                    continue

                # Check immunity
                immunities = UNIT_WEATHER_IMMUNITY.get(u.utype, set())
                if zone.wtype in immunities:
                    continue

                # Apply HP damage
                hp_tick = effects.get('hp_tick', 0)
                if hp_tick != 0:
                    u.hp += hp_tick * dt
                    changed = True

                # Speed modifier applied during movement (stored as weather_spd_mult)
                if not hasattr(u, '_weather_spd'):
                    u._weather_spd = 1.0
                u._weather_spd = min(u._weather_spd, effects.get('spd_mult', 1.0))

                # Attack modifier
                if not hasattr(u, '_weather_atk'):
                    u._weather_atk = 1.0
                u._weather_atk = min(u._weather_atk, effects.get('atk_mult', 1.0))

        return changed

    # ── Weather → Buildings ────────────────────────────────────────────────
    def _weather_affects_buildings(self, dt, world):
        changed = False
        weather = world.weather
        civs = world.civilizations
        materials = world.materials

        for zone in weather.zones:
            effects = WEATHER_BUILDING_EFFECTS.get(zone.wtype)
            if not effects:
                continue

            r2 = zone.radius * zone.radius
            for b in civs.active_buildings:
                dx = b.x - zone.x
                dy = b.y - zone.y
                if dx * dx + dy * dy > r2:
                    continue

                # Check building resistance
                resists = BUILDING_WEATHER_RESIST.get(b.btype, set())
                if zone.wtype in resists:
                    continue

                # HP damage
                hp_tick = effects.get('hp_tick', 0)
                if hp_tick != 0:
                    b.hp += hp_tick * dt
                    changed = True

                # Fire suppression from rain/snow/cold
                if effects.get('fire_suppress', False):
                    try:
                        from .tools import MAT_INDEX
                    except ImportError:  # pragma: no cover - direct script fallback
                        from tools import MAT_INDEX
                    fire_idx = MAT_INDEX.get('fire', 0)
                    hf_idx = MAT_INDEX.get('hellfire', 0)
                    bx, by = b.x, b.y
                    for dy2 in range(-2, 3):
                        for dx2 in range(-2, 3):
                            nx, ny = bx + dx2, by + dy2
                            if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                                m = materials.mat[ny, nx]
                                if m == fire_idx or m == hf_idx:
                                    if self._rng.random() < 0.15:
                                        materials.mat[ny, nx] = 0
                                        materials.life[ny, nx] = 0
                                        changed = True

                # Production modifier stored on building
                if not hasattr(b, '_weather_prod'):
                    b._weather_prod = 1.0
                b._weather_prod = min(b._weather_prod, effects.get('prod_mult', 1.0))

        return changed

    # ── Materials → Units ──────────────────────────────────────────────────
    def _material_affects_units(self, dt, world):
        changed = False
        materials = world.materials
        units = world.units

        for u in units.units:
            if not u.alive:
                continue
            ix, iy = int(u.x), int(u.y)
            if not (0 <= ix < MAP_W and 0 <= iy < MAP_H):
                continue

            mat_name = materials.get_at(ix, iy)
            if mat_name == 'none':
                continue

            # Check special interactions first
            special = MATERIAL_UNIT_SPECIAL.get((mat_name, u.utype))
            if special:
                hp = special.get('hp_tick', 0)
                if hp != 0:
                    u.hp = min(u.max_hp, u.hp + hp * dt)
                    changed = True
                if 'atk_mult' in special:
                    if not hasattr(u, '_mat_atk'):
                        u._mat_atk = 1.0
                    u._mat_atk = max(u._mat_atk, special['atk_mult'])
                continue  # Special overrides generic

            # Check immunity
            immunities = UNIT_MATERIAL_IMMUNITY.get(u.utype, set())
            if mat_name in immunities:
                continue

            effects = MATERIAL_UNIT_EFFECTS.get(mat_name)
            if not effects:
                continue

            hp_tick = effects.get('hp_tick', 0)
            if hp_tick != 0:
                u.hp = min(u.max_hp, u.hp + hp_tick * dt)
                changed = True

            # Speed modifier
            if not hasattr(u, '_mat_spd'):
                u._mat_spd = 1.0
            u._mat_spd = min(u._mat_spd, effects.get('spd_mult', 1.0))

        return changed

    # ── Materials → Buildings ──────────────────────────────────────────────
    def _material_affects_buildings(self, dt, world):
        changed = False
        materials = world.materials
        civs = world.civilizations

        for b in civs.active_buildings:
            ix, iy = b.x, b.y
            if not (0 <= ix < MAP_W and 0 <= iy < MAP_H):
                continue

            # Check materials on and around building
            worst_hp = 0
            worst_prod = 1.0
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = ix + dx, iy + dy
                    if not (0 <= nx < MAP_W and 0 <= ny < MAP_H):
                        continue
                    mat_name = materials.get_at(nx, ny)
                    if mat_name == 'none':
                        continue

                    # Check building resistance
                    resists = BUILDING_MATERIAL_RESIST.get(b.btype, set())
                    if mat_name in resists:
                        continue

                    effects = MATERIAL_BUILDING_EFFECTS.get(mat_name)
                    if not effects:
                        continue

                    hp_tick = effects.get('hp_tick', 0)
                    if hp_tick < worst_hp:
                        worst_hp = hp_tick
                    prod = effects.get('prod_mult', 1.0)
                    if prod < worst_prod:
                        worst_prod = prod

            if worst_hp != 0:
                b.hp += worst_hp * dt
                changed = True

            if not hasattr(b, '_mat_prod'):
                b._mat_prod = 1.0
            b._mat_prod = worst_prod

        return changed

    # ── Biome → Units ──────────────────────────────────────────────────────
    def _biome_affects_units(self, dt, world):
        changed = False
        for u in world.units.units:
            if not u.alive:
                continue
            ix, iy = int(u.x), int(u.y)
            if not (0 <= ix < MAP_W and 0 <= iy < MAP_H):
                continue

            biome = world.biome_names[world.biome_map[iy, ix]]

            # Generic biome effects
            effects = BIOME_UNIT_EFFECTS.get(biome, {})

            # Water check - dragons and spirits can fly
            if biome in ('deep_ocean', 'ocean') and u.utype in ('dragon', 'spirit'):
                continue

            hp_tick = effects.get('hp_tick', 0)
            if hp_tick != 0:
                u.hp = min(u.max_hp, u.hp + hp_tick * dt)
                changed = True

            # Biome speed stored
            if not hasattr(u, '_biome_spd'):
                u._biome_spd = 1.0
            u._biome_spd = effects.get('spd_mult', 1.0)

            # Biome defense stored
            if not hasattr(u, '_biome_def'):
                u._biome_def = 1.0
            u._biome_def = effects.get('def_mult', 1.0)

            # Special unit-biome bonuses
            bonus = UNIT_BIOME_BONUS.get((u.utype, biome))
            if bonus:
                hp_regen = bonus.get('hp_regen', 0)
                if hp_regen > 0:
                    u.hp = min(u.max_hp, u.hp + hp_regen * dt)
                    changed = True
                if not hasattr(u, '_biome_atk'):
                    u._biome_atk = 1.0
                u._biome_atk = bonus.get('atk_mult', 1.0)

        return changed

    # ── Season → Global effects ────────────────────────────────────────────
    def _season_affects_world(self, dt, world):
        changed = False
        season = world.weather.season
        effects = SEASON_EFFECTS.get(season, {})

        # Seasonal healing/damage to all units
        unit_heal = effects.get('unit_heal', 0)
        if unit_heal != 0:
            for u in world.units.units:
                if not u.alive:
                    continue
                u.hp = min(u.max_hp, u.hp + unit_heal * dt)
            changed = True

        return changed

    # ── Units → Material emissions ─────────────────────────────────────────
    def _units_emit_materials(self, dt, world):
        try:
            from .tools import MAT_INDEX
        except ImportError:  # pragma: no cover - direct script fallback
            from tools import MAT_INDEX
        changed = False
        materials = world.materials

        for u in world.units.units:
            if not u.alive:
                continue
            emission = UNIT_MATERIAL_EMISSIONS.get(u.utype)
            if not emission:
                continue

            if self._rng.random() < emission['chance']:
                ix, iy = int(u.x), int(u.y)
                # Place material on a random adjacent tile
                ox = self._rng.randint(-2, 3)
                oy = self._rng.randint(-2, 3)
                tx, ty = ix + ox, iy + oy
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    if materials.mat[ty, tx] == 0:
                        mi = MAT_INDEX.get(emission['material'], 0)
                        if mi:
                            materials.mat[ty, tx] = mi
                            materials.life[ty, tx] = emission.get('life', 0)
                            changed = True

        return changed

    # ── Buildings → Environment ────────────────────────────────────────────
    def _buildings_affect_environment(self, dt, world):
        try:
            from .tools import MAT_INDEX
        except ImportError:  # pragma: no cover - direct script fallback
            from tools import MAT_INDEX
        changed = False
        civs = world.civilizations
        materials = world.materials

        for b in civs.active_buildings:
            effects = BUILDING_ENVIRONMENT_EFFECTS.get(b.btype)
            if not effects:
                continue

            bx, by = b.x, b.y
            radius = effects.get('radius', 5)

            # Farm moisture boost
            if 'moisture_boost' in effects:
                boost = effects['moisture_boost'] * b.level
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        nx, ny = bx + dx, by + dy
                        if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                            if dx * dx + dy * dy <= radius * radius:
                                world.moisture[ny, nx] = min(1.0, world.moisture[ny, nx] + boost * dt)
                changed = True

            # Mine elevation reduce
            if 'elevation_reduce' in effects:
                red = effects['elevation_reduce'] * b.level
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        nx, ny = bx + dx, by + dy
                        if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                            if dx * dx + dy * dy <= radius * radius:
                                world.heightmap[ny, nx] = max(0, world.heightmap[ny, nx] - red * dt)
                changed = True

            # Temple bless spread
            if 'bless_chance' in effects:
                chance = effects['bless_chance'] * b.level
                if self._rng.random() < chance:
                    ox = self._rng.randint(-radius, radius + 1)
                    oy = self._rng.randint(-radius, radius + 1)
                    tx, ty = bx + ox, by + oy
                    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                        if materials.mat[ty, tx] == 0:
                            mi = MAT_INDEX.get('bless', 0)
                            if mi:
                                materials.mat[ty, tx] = mi
                                materials.life[ty, tx] = 60
                                changed = True

            # Graveyard corruption spread
            if 'corrupt_chance' in effects:
                chance = effects['corrupt_chance'] * b.level
                if self._rng.random() < chance:
                    ox = self._rng.randint(-radius, radius + 1)
                    oy = self._rng.randint(-radius, radius + 1)
                    tx, ty = bx + ox, by + oy
                    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                        if materials.mat[ty, tx] == 0:
                            mi = MAT_INDEX.get('corrupt', 0)
                            if mi:
                                materials.mat[ty, tx] = mi
                                materials.life[ty, tx] = 80
                                changed = True

            # Workshop smoke
            if 'smoke_chance' in effects:
                if self._rng.random() < effects['smoke_chance']:
                    ox = self._rng.randint(-radius, radius + 1)
                    oy = self._rng.randint(-radius, radius + 1)
                    tx, ty = bx + ox, by + oy
                    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                        if materials.mat[ty, tx] == 0:
                            mi = MAT_INDEX.get('steam', 0)
                            if mi:
                                materials.mat[ty, tx] = mi
                                materials.life[ty, tx] = 30
                                changed = True

        return changed

    # ── Buildings → Unit aura buffs ────────────────────────────────────────
    def _buildings_buff_units(self, dt, world):
        changed = False
        civs = world.civilizations
        units = world.units

        for b in civs.active_buildings:
            aura = BUILDING_UNIT_AURA.get(b.btype)
            if not aura:
                continue

            radius = aura.get('radius', 8)
            r2 = radius * radius

            for u in units.units:
                if not u.alive:
                    continue
                # Only buff same-team units
                if u.god_id != b.god_id:
                    continue

                dx = u.x - b.x
                dy = u.y - b.y
                if dx * dx + dy * dy > r2:
                    continue

                # Healing
                heal = aura.get('heal_per_tick', 0)
                if heal > 0:
                    u.hp = min(u.max_hp, u.hp + heal * dt)
                    changed = True

                # Siege/golem repair (workshop)
                if u.utype == 'siege' and 'siege_repair' in aura:
                    u.hp = min(u.max_hp, u.hp + aura['siege_repair'] * dt)
                    changed = True
                if u.utype == 'golem' and 'golem_repair' in aura:
                    u.hp = min(u.max_hp, u.hp + aura['golem_repair'] * dt)
                    changed = True

                # Attack buff
                if not hasattr(u, '_building_atk'):
                    u._building_atk = 1.0
                atk_buff = aura.get('atk_buff', 1.0)
                u._building_atk = max(u._building_atk, atk_buff)

                # Defense buff
                if not hasattr(u, '_building_def'):
                    u._building_def = 1.0
                def_buff = aura.get('def_buff', 1.0)
                u._building_def = max(u._building_def, def_buff)

                # Undead bonus from graveyard
                if u.utype == 'undead' and 'undead_buff' in aura:
                    u._building_atk = max(u._building_atk, aura['undead_buff'])

                # Morale
                if not hasattr(u, '_morale'):
                    u._morale = 1.0
                morale = aura.get('morale', 1.0)
                u._morale = max(u._morale, morale)

        return changed

    # ── Units → Buildings (attack enemy buildings) ─────────────────────────
    def _units_attack_buildings(self, dt, world):
        changed = False
        units = world.units
        civs = world.civilizations

        for u in units.units:
            if not u.alive or u.atk <= 0:
                continue
            if u.utype == 'settler':
                continue  # Settlers don't attack

            ix, iy = int(u.x), int(u.y)

            # Check nearby enemy buildings
            nearby = civs.get_nearby(ix, iy, 4)
            for b in nearby:
                if b.god_id == u.god_id:
                    continue  # Same team

                # Unit attacks building
                dmg = u.atk * dt * 0.5  # Half damage to buildings
                # Siege units do double damage to buildings
                if u.utype == 'siege':
                    dmg *= 3.0
                # Dragons do 1.5x to buildings
                elif u.utype == 'dragon':
                    dmg *= 1.5
                # Mages do 1.2x to buildings
                elif u.utype == 'mage':
                    dmg *= 1.2

                b.hp -= dmg
                changed = True

                # Building fights back (garrison defense)
                if hasattr(b, 'population') and b.population > 0:
                    garrison_dmg = b.population * 0.1 * dt
                    u.hp -= garrison_dmg

                break  # Only attack one building per tick

        return changed

    # ── Calculate effective unit stats ─────────────────────────────────────
    @staticmethod
    def get_effective_speed(unit):
        """Get unit's effective speed after all synergy modifiers."""
        base = UNIT_TYPES.get(unit.utype, {}).get('spd', UNIT_SPEED)
        spd = base

        # Weather modifier
        weather_mod = getattr(unit, '_weather_spd', 1.0)
        spd *= weather_mod

        # Material modifier
        mat_mod = getattr(unit, '_mat_spd', 1.0)
        spd *= mat_mod

        # Biome modifier
        biome_mod = getattr(unit, '_biome_spd', 1.0)
        spd *= biome_mod

        # Biome bonus speed
        biome_spd_bonus = getattr(unit, '_biome_spd_bonus', 0)
        spd += biome_spd_bonus

        return max(0.1, spd)

    @staticmethod
    def get_effective_attack(unit):
        """Get unit's effective attack after all synergy modifiers."""
        base = unit.atk

        # Weather modifier
        weather_mod = getattr(unit, '_weather_atk', 1.0)
        base *= weather_mod

        # Material modifier
        mat_mod = getattr(unit, '_mat_atk', 1.0)
        base *= mat_mod

        # Biome modifier
        biome_mod = getattr(unit, '_biome_atk', 1.0)
        base *= biome_mod

        # Building aura buff
        building_mod = getattr(unit, '_building_atk', 1.0)
        base *= building_mod

        # Morale
        morale = getattr(unit, '_morale', 1.0)
        base *= morale

        return max(0, base)

    @staticmethod
    def get_effective_defense(unit):
        """Get unit's effective defense multiplier (damage reduction)."""
        defense = 1.0

        # Biome defense
        biome_def = getattr(unit, '_biome_def', 1.0)
        defense *= biome_def

        # Building aura defense
        building_def = getattr(unit, '_building_def', 1.0)
        defense *= building_def

        return defense

    @staticmethod
    def get_combat_multiplier(attacker_type, defender_type):
        """Get type advantage multiplier for combat."""
        return COMBAT_TYPE_ADVANTAGE.get((attacker_type, defender_type), 1.0)

    @staticmethod
    def get_building_production_mult(building, biome_name, season):
        """Get total production multiplier for a building from all synergy sources."""
        mult = 1.0

        # Biome production
        biome_prods = BIOME_BUILDING_PRODUCTION.get(biome_name, {})
        # Average across all resources this building produces
        if biome_prods:
            avg = sum(biome_prods.values()) / len(biome_prods)
            mult *= avg

        # Season
        season_fx = SEASON_EFFECTS.get(season, {})
        if building.btype == 'farm':
            mult *= season_fx.get('food_mult', 1.0)

        # Weather modifier
        weather_prod = getattr(building, '_weather_prod', 1.0)
        mult *= weather_prod

        # Material modifier
        mat_prod = getattr(building, '_mat_prod', 1.0)
        mult *= mat_prod

        return max(0, mult)

    @staticmethod
    def reset_tick_modifiers(world):
        """Reset per-tick synergy modifiers before next synergy tick.
        Called at the START of each synergy tick so modifiers are recalculated fresh."""
        for u in world.units.units:
            if not u.alive:
                continue
            u._weather_spd = 1.0
            u._weather_atk = 1.0
            u._mat_spd = 1.0
            u._mat_atk = 1.0
            u._biome_spd = 1.0
            u._biome_def = 1.0
            u._biome_atk = 1.0
            u._building_atk = 1.0
            u._building_def = 1.0
            u._morale = 1.0

        for b in world.civilizations.active_buildings:
            b._weather_prod = 1.0
            b._mat_prod = 1.0
