"""
World Map — World History & Era System  (v6.0 LIVING WORLD)
Tracks everything that happens: wars, alliances, disasters, god actions,
territory changes, civilization rise/fall. History shapes the future.
"""
import time
import random
from config import ERA_LENGTH, ERA_NAMES, HISTORY_MAX_EVENTS


# ═══════════════════════════════════════════════════════════════════════════════
# History Event Types
# ═══════════════════════════════════════════════════════════════════════════════

EVENT_TYPES = {
    # Wars & Combat
    'war_declared':       {'icon': 'sword',   'color': (200, 50, 50),   'importance': 8},
    'war_ended':          {'icon': 'peace',   'color': (100, 200, 100), 'importance': 7},
    'battle':             {'icon': 'battle',  'color': (180, 60, 60),   'importance': 5},
    'siege':              {'icon': 'siege',   'color': (160, 80, 40),   'importance': 6},
    'massacre':           {'icon': 'skull',   'color': (120, 20, 20),   'importance': 9},

    # Civilization
    'settlement_founded': {'icon': 'village', 'color': (100, 180, 80),  'importance': 4},
    'city_upgraded':      {'icon': 'city',    'color': (150, 200, 100), 'importance': 3},
    'settlement_razed':   {'icon': 'ruin',    'color': (140, 60, 40),   'importance': 6},
    'famine':             {'icon': 'hunger',  'color': (180, 140, 40),  'importance': 5},
    'golden_age':         {'icon': 'gold',    'color': (255, 210, 50),  'importance': 6},
    'trade_route':        {'icon': 'trade',   'color': (200, 180, 100), 'importance': 3},
    'population_boom':    {'icon': 'people',  'color': (120, 200, 120), 'importance': 4},

    # Territory & Influence
    'territory_gained':   {'icon': 'flag',    'color': (100, 150, 200), 'importance': 3},
    'territory_lost':     {'icon': 'retreat', 'color': (200, 150, 100), 'importance': 4},
    'stronghold_built':   {'icon': 'castle',  'color': (180, 160, 255), 'importance': 7},
    'stronghold_fell':    {'icon': 'ruin',    'color': (100, 50, 50),   'importance': 9},

    # Natural Disasters
    'great_fire':         {'icon': 'fire',    'color': (255, 102, 34),  'importance': 7},
    'great_flood':        {'icon': 'water',   'color': (48, 78, 128),   'importance': 7},
    'earthquake':         {'icon': 'quake',   'color': (140, 120, 80),  'importance': 8},
    'volcanic_eruption':  {'icon': 'volcano', 'color': (200, 60, 20),   'importance': 9},
    'plague':             {'icon': 'plague',   'color': (130, 90, 140),  'importance': 8},
    'blizzard':           {'icon': 'snow',    'color': (200, 210, 220), 'importance': 6},
    'corruption_spread':  {'icon': 'corrupt', 'color': (50, 15, 40),    'importance': 7},
    'blessing_wave':      {'icon': 'bless',   'color': (170, 200, 255), 'importance': 6},

    # God Actions
    'god_intervention':   {'icon': 'bolt',    'color': (255, 255, 180), 'importance': 8},
    'god_miracle':        {'icon': 'star',    'color': (255, 220, 150), 'importance': 9},
    'god_punishment':     {'icon': 'curse',   'color': (180, 30, 60),   'importance': 9},

    # Eras & Ages
    'era_change':         {'icon': 'epoch',   'color': (220, 200, 255), 'importance': 10},
    'age_of_war':         {'icon': 'sword',   'color': (200, 50, 50),   'importance': 9},
    'age_of_peace':       {'icon': 'peace',   'color': (100, 200, 150), 'importance': 9},

    # Units & Heroes
    'hero_born':          {'icon': 'hero',    'color': (255, 200, 100), 'importance': 5},
    'hero_died':          {'icon': 'grave',   'color': (140, 130, 120), 'importance': 5},
    'army_formed':        {'icon': 'army',    'color': (180, 100, 100), 'importance': 4},
    'army_destroyed':     {'icon': 'defeat',  'color': (120, 60, 60),   'importance': 6},

    # Generic
    'tool_action':        {'icon': 'hand',    'color': (180, 180, 200), 'importance': 1},
    'unknown':            {'icon': '?',       'color': (150, 150, 150), 'importance': 1},
}


class HistoryEvent:
    """A single recorded world event."""
    __slots__ = ('etype', 'text', 'god_id', 'god_id2', 'pos',
                 'tick', 'era', 'importance', 'consequence')

    def __init__(self, etype, text, god_id=None, god_id2=None, pos=None,
                 tick=0, era=0, consequence=None):
        self.etype       = etype
        self.text        = text
        self.god_id      = god_id
        self.god_id2     = god_id2    # second god (for wars, etc.)
        self.pos         = pos        # (x, y) or None
        self.tick        = tick
        self.era         = era
        self.importance  = EVENT_TYPES.get(etype, {}).get('importance', 1)
        self.consequence = consequence  # what this event causes

    def to_dict(self):
        return {
            'type': self.etype, 'text': self.text,
            'god_id': self.god_id, 'god_id2': self.god_id2,
            'pos': self.pos, 'tick': self.tick, 'era': self.era,
            'importance': self.importance, 'consequence': self.consequence,
        }


class WarRecord:
    """Tracks an ongoing or past war between two gods."""
    __slots__ = ('attacker', 'defender', 'start_tick', 'end_tick',
                 'battles', 'casualties_a', 'casualties_d',
                 'buildings_razed', 'winner', 'active')

    def __init__(self, attacker, defender, start_tick):
        self.attacker       = attacker
        self.defender       = defender
        self.start_tick     = start_tick
        self.end_tick       = 0
        self.battles        = 0
        self.casualties_a   = 0
        self.casualties_d   = 0
        self.buildings_razed = 0
        self.winner         = None
        self.active         = True


class DiplomacyState:
    """Tracks relationships between gods."""

    def __init__(self, god_ids):
        self.god_ids = list(god_ids)
        n = len(god_ids)
        # Relation matrix: -100 (mortal enemies) to +100 (allies)
        self.relations = {}
        for i, a in enumerate(god_ids):
            for j, b in enumerate(god_ids):
                if i < j:
                    self.relations[(a, b)] = 0  # neutral start

    def get_relation(self, god_a, god_b):
        if god_a == god_b:
            return 100
        key = tuple(sorted([god_a, god_b]))
        return self.relations.get(key, 0)

    def modify_relation(self, god_a, god_b, delta):
        if god_a == god_b:
            return
        key = tuple(sorted([god_a, god_b]))
        if key in self.relations:
            self.relations[key] = max(-100, min(100, self.relations[key] + delta))

    def are_enemies(self, god_a, god_b):
        return self.get_relation(god_a, god_b) < -30

    def are_allies(self, god_a, god_b):
        return self.get_relation(god_a, god_b) > 50

    def get_enemies_of(self, god_id):
        enemies = []
        for other in self.god_ids:
            if other != god_id and self.are_enemies(god_id, other):
                enemies.append(other)
        return enemies

    def get_allies_of(self, god_id):
        allies = []
        for other in self.god_ids:
            if other != god_id and self.are_allies(god_id, other):
                allies.append(other)
        return allies


# ═══════════════════════════════════════════════════════════════════════════════
# World History — the central chronicle
# ═══════════════════════════════════════════════════════════════════════════════

class WorldHistory:
    """Tracks and shapes the entire world's history."""

    def __init__(self, god_ids):
        self.god_ids = list(god_ids)
        self.events: list[HistoryEvent] = []
        self.wars: list[WarRecord] = []
        self.diplomacy = DiplomacyState(god_ids)

        # Era tracking
        self.current_era = 0
        self.era_timer = 0.0
        self.era_name = ERA_NAMES[0] if ERA_NAMES else 'Unknown'

        # World tick counter
        self.world_tick = 0

        # Stats per god
        self.god_stats = {}
        for gid in god_ids:
            self.god_stats[gid] = {
                'wars_won': 0, 'wars_lost': 0,
                'settlements_founded': 0, 'settlements_lost': 0,
                'units_killed': 0, 'units_lost': 0,
                'peak_territory': 0, 'peak_population': 0,
            }

        # World state tracking for automatic events
        self._prev_territory = {}
        self._prev_population = {}
        self._war_cooldowns = {}   # (godA, godB) → tick when war can happen
        self._disaster_cooldown = 0
        self._initial_events_done = False

    def tick(self, dt, world):
        """Main history tick — detect events, update eras, shape world."""
        self.world_tick += 1
        self.era_timer += dt

        # ── First-tick bootstrap: seed initial events & tension ──
        if not self._initial_events_done:
            self._seed_initial_events(world)
            self._initial_events_done = True

        # Era progression
        if self.era_timer >= ERA_LENGTH:
            self.era_timer -= ERA_LENGTH
            self.current_era += 1
            era_idx = self.current_era % len(ERA_NAMES)
            self.era_name = ERA_NAMES[era_idx]
            self.record('era_change',
                        f"The Age of {self.era_name} begins (Era {self.current_era + 1})")

        # Detect territory changes
        self._detect_territory_shifts(world)

        # Detect population events
        self._detect_population_events(world)

        # Auto-generate wars based on diplomacy + proximity (every 5 ticks)
        if self.world_tick % 5 == 0:
            self._check_war_triggers(world)

        # Random natural disasters (every 20 ticks)
        if self.world_tick % 20 == 0:
            self._check_disasters(world)

        # Update war records
        self._update_wars(world)

        # Trim old events
        if len(self.events) > HISTORY_MAX_EVENTS:
            self.events = self.events[-HISTORY_MAX_EVENTS:]

    def record(self, etype, text, god_id=None, god_id2=None, pos=None,
               consequence=None):
        """Record a new event in history."""
        evt = HistoryEvent(etype, text, god_id, god_id2, pos,
                           self.world_tick, self.current_era, consequence)
        self.events.append(evt)

        # Update diplomacy based on event type
        if etype == 'war_declared' and god_id and god_id2:
            self.diplomacy.modify_relation(god_id, god_id2, -30)
        elif etype == 'trade_route' and god_id and god_id2:
            self.diplomacy.modify_relation(god_id, god_id2, 10)
        elif etype == 'battle' and god_id and god_id2:
            self.diplomacy.modify_relation(god_id, god_id2, -5)

        return evt

    def start_war(self, attacker, defender):
        """Formally declare war between two gods."""
        # Check cooldown
        key = tuple(sorted([attacker, defender]))
        if self._war_cooldowns.get(key, 0) > self.world_tick:
            return None

        war = WarRecord(attacker, defender, self.world_tick)
        self.wars.append(war)
        self._war_cooldowns[key] = self.world_tick + 300  # 300 tick cooldown

        self.record('war_declared',
                    f"War erupts between {attacker} and {defender}!",
                    god_id=attacker, god_id2=defender)
        self.diplomacy.modify_relation(attacker, defender, -40)
        return war

    def end_war(self, war, winner=None):
        """End a war with optional winner."""
        war.active = False
        war.end_tick = self.world_tick
        war.winner = winner

        if winner:
            loser = war.defender if winner == war.attacker else war.attacker
            self.god_stats[winner]['wars_won'] += 1
            self.god_stats[loser]['wars_lost'] += 1
            self.record('war_ended',
                        f"{winner} wins the war against {loser}!",
                        god_id=winner, god_id2=loser)
            self.diplomacy.modify_relation(winner, loser, -20)
        else:
            self.record('war_ended',
                        f"War between {war.attacker} and {war.defender} ends in stalemate.",
                        god_id=war.attacker, god_id2=war.defender)
            self.diplomacy.modify_relation(war.attacker, war.defender, 5)

    def get_active_wars(self):
        return [w for w in self.wars if w.active]

    def get_wars_involving(self, god_id):
        return [w for w in self.wars if w.active and
                (w.attacker == god_id or w.defender == god_id)]

    def are_at_war(self, god_a, god_b):
        for w in self.wars:
            if not w.active:
                continue
            if ((w.attacker == god_a and w.defender == god_b) or
                (w.attacker == god_b and w.defender == god_a)):
                return True
        return False

    def get_recent_events(self, count=20, min_importance=1):
        filtered = [e for e in self.events if e.importance >= min_importance]
        return filtered[-count:]

    def get_era_summary(self):
        """Summarise the current era."""
        era_events = [e for e in self.events if e.era == self.current_era]
        wars = sum(1 for e in era_events if e.etype == 'war_declared')
        settlements = sum(1 for e in era_events if e.etype == 'settlement_founded')
        disasters = sum(1 for e in era_events
                       if e.etype in ('great_fire', 'great_flood', 'earthquake',
                                       'volcanic_eruption', 'plague', 'blizzard'))
        return {
            'era': self.current_era + 1,
            'name': self.era_name,
            'wars': wars,
            'settlements': settlements,
            'disasters': disasters,
            'total_events': len(era_events),
        }

    # ── initial event seeding ──────────────────────────────────────────────
    def _seed_initial_events(self, world):
        """Seed the world with initial events and diplomatic tension."""
        # Record stronghold_built for each god
        for sh in getattr(world, 'strongholds', []):
            gid = sh.get('god_id', '')
            name = sh.get('name', 'Unknown')
            self.record('stronghold_built',
                        f"{gid} establishes the stronghold of {name}",
                        god_id=gid, pos=(sh.get('x', 0), sh.get('y', 0)))

        # Record settlement_founded for existing buildings
        if hasattr(world, 'civilizations'):
            for b in world.civilizations.active_buildings:
                self.record('settlement_founded',
                            f"{b.god_id} founds a {b.btype} at ({b.x},{b.y})",
                            god_id=b.god_id, pos=(b.x, b.y))

        # Seed initial diplomatic tension between all god pairs
        # Gods that are thematically opposed get more tension
        opposed_pairs = {
            ('god_light', 'god_darkness'), ('god_life', 'god_death'),
            ('god_fire', 'god_water'), ('god_order', 'god_chaos'),
        }
        for i, gid_a in enumerate(self.god_ids):
            for gid_b in self.god_ids[i+1:]:
                key = tuple(sorted([gid_a, gid_b]))
                if key in opposed_pairs or (key[1], key[0]) in opposed_pairs:
                    tension = -random.uniform(15, 30)
                else:
                    tension = -random.uniform(3, 12)
                self.diplomacy.modify_relation(gid_a, gid_b, tension)

        # Record the initial era
        self.record('era_change',
                    f"The Age of {self.era_name} dawns upon the world")

    # ── automatic event detection ──────────────────────────────────────────
    def _detect_territory_shifts(self, world):
        """Detect significant territory gains/losses."""
        for god in world.gods:
            gid = god['god_id']
            territory = world.influence.get_god_territory_count(gid)
            prev = self._prev_territory.get(gid, territory)

            # Update peak
            if territory > self.god_stats[gid].get('peak_territory', 0):
                self.god_stats[gid]['peak_territory'] = territory

            # Significant gain (>5% growth or first time exceeding 50)
            if prev > 20 and territory > prev * 1.05:
                self.record('territory_gained',
                            f"{gid} expands territory by {territory - prev} tiles",
                            god_id=gid)

            # Significant loss (>5% loss)
            if prev > 20 and territory < prev * 0.95:
                self.record('territory_lost',
                            f"{gid} loses {prev - territory} tiles of territory",
                            god_id=gid)

            self._prev_territory[gid] = territory

    def _detect_population_events(self, world):
        """Detect population milestones."""
        for god in world.gods:
            gid = god['god_id']
            pop = world.civilizations.get_total_population(gid)
            prev = self._prev_population.get(gid, pop)

            # Update peak
            if pop > self.god_stats[gid].get('peak_population', 0):
                self.god_stats[gid]['peak_population'] = pop

            # Population boom (>20% growth in one check)
            if prev > 5 and pop > prev * 1.2:
                self.record('population_boom',
                            f"{gid}'s population surges to {int(pop)}!",
                            god_id=gid)

            # Famine (>15% population drop)
            if prev > 5 and pop < prev * 0.85:
                self.record('famine',
                            f"Famine strikes {gid} — population drops to {int(pop)}",
                            god_id=gid)

            self._prev_population[gid] = pop

    def _check_war_triggers(self, world):
        """Check if any gods should go to war based on proximity + tension."""
        active_wars = len(self.get_active_wars())
        if active_wars >= 3:
            return  # Too many wars already

        # Natural border friction: neighbouring gods accumulate tension
        for i, gid_a in enumerate(self.god_ids):
            terr_a = world.influence.get_god_territory_count(gid_a)
            for gid_b in self.god_ids[i+1:]:
                if self.are_at_war(gid_a, gid_b):
                    continue
                terr_b = world.influence.get_god_territory_count(gid_b)
                # Both have some territory → generate natural tension
                if terr_a > 30 and terr_b > 30:
                    # Border friction: stronger tension per check
                    friction = -random.uniform(2.0, 5.0)
                    self.diplomacy.modify_relation(gid_a, gid_b, friction)

                relation = self.diplomacy.get_relation(gid_a, gid_b)
                if relation < -40:
                    # High tension — chance of war
                    if terr_a > 30 and terr_b > 30:
                        war_chance = 0.03 + abs(relation) * 0.001
                        if random.random() < war_chance:
                            self.start_war(gid_a, gid_b)

        # Slow natural tension decay (only for very negative relations)
        if self.world_tick % 300 == 0:
            for key in self.diplomacy.relations:
                val = self.diplomacy.relations[key]
                if val < -70:
                    self.diplomacy.relations[key] = min(-70, val + 1)
                elif val > 30:
                    self.diplomacy.relations[key] = max(30, val - 1)

    def _check_disasters(self, world):
        """Random natural disasters that shape the world."""
        if self._disaster_cooldown > self.world_tick:
            return

        if random.random() < 0.08:  # 8% per check — disasters keep the world interesting
            disaster = random.choice([
                'great_fire', 'great_flood', 'earthquake',
                'blizzard', 'plague', 'corruption_spread',
            ])
            x = random.randint(50, world.heightmap.shape[1] - 50)
            y = random.randint(50, world.heightmap.shape[0] - 50)

            gid, _ = world.influence.get_dominant_at(x, y)

            self.record(disaster,
                        f"{disaster.replace('_', ' ').title()} strikes at ({x},{y})!",
                        god_id=gid, pos=(x, y))

            # Apply disaster effects via material layer
            self._apply_disaster(disaster, x, y, world)
            self._disaster_cooldown = self.world_tick + 200

    def _apply_disaster(self, dtype, x, y, world):
        """Actually apply disaster effects to the world."""
        from tools import MAT_INDEX
        ml = world.materials
        r = random.randint(15, 35)

        if dtype == 'great_fire':
            fire_idx = MAT_INDEX.get('fire', 0)
            if fire_idx:
                for _ in range(r * 2):
                    rx = x + random.randint(-r, r)
                    ry = y + random.randint(-r, r)
                    if 0 <= rx < ml.w and 0 <= ry < ml.h and ml.mat[ry, rx] == 0:
                        ml.mat[ry, rx] = fire_idx
                        ml.life[ry, rx] = random.randint(30, 80)
                ml._version += 1

        elif dtype == 'great_flood':
            water_idx = MAT_INDEX.get('water', 0)
            if water_idx:
                for _ in range(r * 3):
                    rx = x + random.randint(-r, r)
                    ry = y + random.randint(-r, r)
                    if 0 <= rx < ml.w and 0 <= ry < ml.h:
                        ml.mat[ry, rx] = water_idx
                        ml.life[ry, rx] = 0
                ml._version += 1

        elif dtype == 'earthquake':
            # Lower terrain in area
            hm = world.heightmap
            y0 = max(0, y - r)
            y1 = min(hm.shape[0], y + r + 1)
            x0 = max(0, x - r)
            x1 = min(hm.shape[1], x + r + 1)
            hm[y0:y1, x0:x1] = np.clip(hm[y0:y1, x0:x1] - 0.05, 0, 1)

        elif dtype == 'blizzard':
            frost_idx = MAT_INDEX.get('frost', 0)
            if frost_idx:
                for _ in range(r * 3):
                    rx = x + random.randint(-r, r)
                    ry = y + random.randint(-r, r)
                    if 0 <= rx < ml.w and 0 <= ry < ml.h and ml.mat[ry, rx] == 0:
                        ml.mat[ry, rx] = frost_idx
                        ml.life[ry, rx] = random.randint(100, 200)
                ml._version += 1

        elif dtype == 'plague':
            spore_idx = MAT_INDEX.get('spore', 0)
            if spore_idx:
                for _ in range(r):
                    rx = x + random.randint(-r, r)
                    ry = y + random.randint(-r, r)
                    if 0 <= rx < ml.w and 0 <= ry < ml.h and ml.mat[ry, rx] == 0:
                        ml.mat[ry, rx] = spore_idx
                        ml.life[ry, rx] = random.randint(150, 250)
                ml._version += 1

        elif dtype == 'corruption_spread':
            corr_idx = MAT_INDEX.get('corrupt', 0)
            if corr_idx:
                for _ in range(r * 2):
                    rx = x + random.randint(-r, r)
                    ry = y + random.randint(-r, r)
                    if 0 <= rx < ml.w and 0 <= ry < ml.h and ml.mat[ry, rx] == 0:
                        ml.mat[ry, rx] = corr_idx
                        ml.life[ry, rx] = 0
                ml._version += 1

    def _update_wars(self, world):
        """Update ongoing wars — check if they should end."""
        for war in self.wars:
            if not war.active:
                continue
            # War duration check
            duration = self.world_tick - war.start_tick
            if duration > 500:  # Long war — chance of stalemate
                if random.random() < 0.02:
                    self.end_war(war, winner=None)
                    continue

            # Check if one side is destroyed
            terr_a = world.influence.get_god_territory_count(war.attacker)
            terr_b = world.influence.get_god_territory_count(war.defender)

            if terr_a < 10:
                self.end_war(war, winner=war.defender)
            elif terr_b < 10:
                self.end_war(war, winner=war.attacker)
            # Decisive advantage
            elif terr_a > terr_b * 3 and duration > 200:
                if random.random() < 0.1:
                    self.end_war(war, winner=war.attacker)
            elif terr_b > terr_a * 3 and duration > 200:
                if random.random() < 0.1:
                    self.end_war(war, winner=war.defender)


# Need numpy for disaster effects
import numpy as np
