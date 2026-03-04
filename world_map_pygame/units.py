"""
World Map — Unit System  (v6.0 LIVING WORLD)
Deep unit AI: armies, patrols, raids, escorts, formations, morale.
Units form groups, seek targets, coordinate attacks, retreat when losing.
"""
import numpy as np
import math
import random
from config import (
    MAP_W, MAP_H, UNIT_TYPES, UNIT_SPEED, GOD_COLORS,
    ARMY_MIN_SIZE, ARMY_MERGE_RADIUS, PATROL_RADIUS, RAID_RANGE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit class (with synergy slots + deep AI state)
# ═══════════════════════════════════════════════════════════════════════════════

class Unit:
    """A single unit on the map — with synergy modifiers + AI state."""
    __slots__ = ('utype', 'x', 'y', 'god_id', 'hp', 'max_hp',
                 'atk', 'spd', 'target_x', 'target_y',
                 'state', 'age', 'alive', 'kills',
                 '_weather_spd', '_weather_atk',
                 '_mat_spd', '_mat_atk',
                 '_biome_spd', '_biome_def', '_biome_atk',
                 '_building_atk', '_building_def',
                 '_morale',
                 'army_id', 'role', 'home_x', 'home_y',
                 'xp', 'level', 'is_veteran')

    def __init__(self, utype, x, y, god_id=None):
        self.utype = utype
        self.x  = float(x)
        self.y  = float(y)
        self.god_id = god_id
        info = UNIT_TYPES.get(utype, {})
        self.max_hp = info.get('hp', 50)
        self.hp     = self.max_hp
        self.atk    = info.get('atk', 5)
        self.spd    = info.get('spd', UNIT_SPEED)
        self.target_x = float(x)
        self.target_y = float(y)
        self.state  = 'idle'    # idle, moving, fighting, patrolling, raiding, retreating, dead
        self.age    = 0
        self.alive  = True
        self.kills  = 0

        # Synergy modifiers (recalculated each tick by SynergyEngine)
        self._weather_spd = 1.0
        self._weather_atk = 1.0
        self._mat_spd     = 1.0
        self._mat_atk     = 1.0
        self._biome_spd   = 1.0
        self._biome_def   = 1.0
        self._biome_atk   = 1.0
        self._building_atk = 1.0
        self._building_def = 1.0
        self._morale      = 1.0

        # Deep AI state
        self.army_id  = -1         # which army this unit belongs to
        self.role     = 'free'     # free, patrol, raid, escort, defend, army
        self.home_x   = float(x)   # assigned home position (for patrols)
        self.home_y   = float(y)
        self.xp       = 0
        self.level    = 1
        self.is_veteran = False

    @property
    def tile_pos(self):
        return (int(self.x), int(self.y))

    @property
    def icon(self):
        return UNIT_TYPES.get(self.utype, {}).get('icon', 'sword')

    @property
    def effective_speed(self):
        base = UNIT_TYPES.get(self.utype, {}).get('spd', UNIT_SPEED)
        return max(0.1, base * self._weather_spd * self._mat_spd * self._biome_spd)

    @property
    def effective_attack(self):
        level_mult = 1.0 + (self.level - 1) * 0.15
        vet_mult = 1.2 if self.is_veteran else 1.0
        return max(0, self.atk * self._weather_atk * self._mat_atk
                   * self._biome_atk * self._building_atk * self._morale
                   * level_mult * vet_mult)

    def gain_xp(self, amount):
        """Gain experience, potentially leveling up."""
        self.xp += amount
        threshold = self.level * 20
        if self.xp >= threshold:
            self.xp -= threshold
            self.level = min(10, self.level + 1)
            self.max_hp = int(UNIT_TYPES.get(self.utype, {}).get('hp', 50) * (1 + self.level * 0.1))
            self.hp = min(self.hp + 10, self.max_hp)
            if self.level >= 5:
                self.is_veteran = True


# ═══════════════════════════════════════════════════════════════════════════════
# Army — a coordinated group of units
# ═══════════════════════════════════════════════════════════════════════════════

class Army:
    """A group of units acting together with a shared objective."""
    __slots__ = ('army_id', 'god_id', 'objective', 'target_x', 'target_y',
                 'state', 'formation', 'strength', 'morale')

    def __init__(self, army_id, god_id, x=0, y=0):
        self.army_id   = army_id
        self.god_id    = god_id
        self.objective = 'idle'     # idle, patrol, raid, attack, defend, retreat
        self.target_x  = float(x)
        self.target_y  = float(y)
        self.state     = 'forming'  # forming, marching, fighting, retreating
        self.formation = 'loose'    # loose, tight, wedge, circle
        self.strength  = 0
        self.morale    = 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Unit System (v6.0 with Army AI)
# ═══════════════════════════════════════════════════════════════════════════════

class UnitSystem:
    """Manages all units: spawning, movement, combat, armies, AI."""

    def __init__(self):
        self.units: list[Unit] = []
        self.armies: list[Army] = []
        self._version = 0
        self._rng = np.random.RandomState(200)
        self._next_army_id = 0
        self._army_check_accum = 0.0

    # ── spawn ──────────────────────────────────────────────────────────────
    def spawn(self, utype, x, y, god_id=None, count=1):
        for _ in range(count):
            u = Unit(utype,
                     x + self._rng.uniform(-1, 1),
                     y + self._rng.uniform(-1, 1),
                     god_id)
            self.units.append(u)
        self._version += 1

    def kill_in_area(self, cx, cy, radius):
        for u in self.units:
            if not u.alive:
                continue
            if abs(u.x - cx) <= radius and abs(u.y - cy) <= radius:
                dx = u.x - cx
                dy = u.y - cy
                if dx * dx + dy * dy <= radius * radius:
                    u.alive = False
                    u.state = 'dead'
        self._cleanup()
        self._version += 1

    # ── army management ────────────────────────────────────────────────────
    def create_army(self, god_id, x, y, objective='patrol'):
        """Create a new army and assign nearby free units to it."""
        army = Army(self._next_army_id, god_id, x, y)
        army.objective = objective
        army.target_x = float(x)
        army.target_y = float(y)
        self.armies.append(army)
        self._next_army_id += 1

        # Recruit nearby free units
        recruited = 0
        for u in self.units:
            if (u.alive and u.god_id == god_id and u.army_id == -1
                    and u.role == 'free' and u.atk > 0):
                dist = math.hypot(u.x - x, u.y - y)
                if dist < ARMY_MERGE_RADIUS * 2:
                    u.army_id = army.army_id
                    u.role = 'army'
                    recruited += 1
                    if recruited >= 15:
                        break

        army.strength = recruited
        return army

    def _auto_form_armies(self, world):
        """Auto-detect clusters of same-god units and form armies."""
        from collections import defaultdict

        god_free = defaultdict(list)
        for u in self.units:
            if u.alive and u.army_id == -1 and u.role == 'free' and u.atk > 0:
                god_free[u.god_id].append(u)

        for god_id, free_units in god_free.items():
            if len(free_units) < ARMY_MIN_SIZE:
                continue

            # Simple clustering: find dense groups
            checked = set()
            for i, u in enumerate(free_units):
                if i in checked:
                    continue
                cluster = [u]
                checked.add(i)
                for j, other in enumerate(free_units):
                    if j in checked:
                        continue
                    if math.hypot(other.x - u.x, other.y - u.y) < ARMY_MERGE_RADIUS:
                        cluster.append(other)
                        checked.add(j)

                if len(cluster) >= ARMY_MIN_SIZE:
                    cx = sum(c.x for c in cluster) / len(cluster)
                    cy = sum(c.y for c in cluster) / len(cluster)

                    # Decide objective based on context
                    objective = 'patrol'
                    if hasattr(world, 'history'):
                        enemies = world.history.diplomacy.get_enemies_of(god_id)
                        if enemies and self._rng.random() < 0.4:
                            objective = 'raid'

                    army = Army(self._next_army_id, god_id, cx, cy)
                    army.objective = objective
                    self.armies.append(army)
                    self._next_army_id += 1

                    for c in cluster:
                        c.army_id = army.army_id
                        c.role = 'army'
                    army.strength = len(cluster)

    def _update_armies(self, dt, world):
        """Update army objectives and movement."""
        dead_armies = []

        for army in self.armies:
            members = [u for u in self.units
                       if u.alive and u.army_id == army.army_id]
            army.strength = len(members)

            if army.strength == 0:
                dead_armies.append(army)
                continue

            # Calculate army center
            cx = sum(u.x for u in members) / len(members)
            cy = sum(u.y for u in members) / len(members)

            # Update morale based on strength and HP
            avg_hp_ratio = sum(u.hp / u.max_hp for u in members) / len(members)
            army.morale = max(0.2, min(1.5, avg_hp_ratio * (1 + len(members) * 0.02)))
            for u in members:
                u._morale = army.morale

            if army.objective == 'patrol':
                self._army_patrol(army, members, cx, cy, world, dt)
            elif army.objective == 'raid':
                self._army_raid(army, members, cx, cy, world, dt)
            elif army.objective == 'attack':
                self._army_attack(army, members, cx, cy, world, dt)
            elif army.objective == 'defend':
                self._army_defend(army, members, cx, cy, world, dt)
            elif army.objective == 'retreat':
                self._army_retreat(army, members, cx, cy, world, dt)

            # Morale break — retreat if morale drops too low
            if army.morale < 0.3 and army.objective != 'retreat':
                army.objective = 'retreat'
                army.state = 'retreating'
                if hasattr(world, 'history'):
                    world.history.record('army_destroyed',
                        f"{army.god_id}'s army routs!",
                        god_id=army.god_id)

        # Remove dead/empty armies
        for army in dead_armies:
            # Free surviving members
            for u in self.units:
                if u.army_id == army.army_id:
                    u.army_id = -1
                    u.role = 'free'
            self.armies.remove(army)

    def _army_patrol(self, army, members, cx, cy, world, dt):
        """Army patrols territory borders."""
        dist_to_target = math.hypot(army.target_x - cx, army.target_y - cy)
        if dist_to_target < 5 or army.state == 'forming':
            # Pick new patrol point within territory
            for _ in range(10):
                nx = cx + self._rng.uniform(-PATROL_RADIUS, PATROL_RADIUS)
                ny = cy + self._rng.uniform(-PATROL_RADIUS, PATROL_RADIUS)
                nx = max(5, min(MAP_W - 5, nx))
                ny = max(5, min(MAP_H - 5, ny))
                gid, st = world.influence.get_dominant_at(int(nx), int(ny))
                if gid == army.god_id:
                    army.target_x = nx
                    army.target_y = ny
                    army.state = 'marching'
                    break

        self._move_army_toward(members, army.target_x, army.target_y, dt)

        # Check for enemies while patrolling
        self._army_check_enemies(army, members, cx, cy, world)

    def _army_raid(self, army, members, cx, cy, world, dt):
        """Army raids enemy territory."""
        if army.state == 'forming' or army.state == 'marching':
            # Find nearest enemy building or territory
            if hasattr(world, 'history'):
                enemies = world.history.diplomacy.get_enemies_of(army.god_id)
                if not enemies:
                    enemies = [g['god_id'] for g in world.gods if g['god_id'] != army.god_id]

                best_target = None
                best_dist = RAID_RANGE * 2
                for b in world.civilizations.active_buildings:
                    if b.god_id in enemies:
                        d = math.hypot(b.x - cx, b.y - cy)
                        if d < best_dist:
                            best_dist = d
                            best_target = b

                if best_target:
                    army.target_x = float(best_target.x)
                    army.target_y = float(best_target.y)
                    army.state = 'marching'
                else:
                    army.objective = 'patrol'
                    return

        self._move_army_toward(members, army.target_x, army.target_y, dt)
        self._army_check_enemies(army, members, cx, cy, world)

        # Check if we reached target
        dist = math.hypot(army.target_x - cx, army.target_y - cy)
        if dist < 5:
            army.state = 'fighting'
            # Damage buildings in area
            for b in world.civilizations.get_nearby(int(cx), int(cy), 10):
                if b.god_id != army.god_id:
                    dmg = sum(u.effective_attack for u in members) * dt * 0.1
                    b.hp -= dmg
                    if b.hp <= 0 and hasattr(world, 'history'):
                        world.history.record('settlement_razed',
                            f"{army.god_id}'s army razes {b.btype} at ({b.x},{b.y})",
                            god_id=army.god_id, pos=(b.x, b.y))

    def _army_attack(self, army, members, cx, cy, world, dt):
        """Direct attack on a position."""
        self._move_army_toward(members, army.target_x, army.target_y, dt)
        self._army_check_enemies(army, members, cx, cy, world)

    def _army_defend(self, army, members, cx, cy, world, dt):
        """Hold position and fight any nearby enemies."""
        # Stay near target
        dist = math.hypot(army.target_x - cx, army.target_y - cy)
        if dist > 10:
            self._move_army_toward(members, army.target_x, army.target_y, dt)
        # Tight formation for defense
        army.formation = 'circle'
        self._army_check_enemies(army, members, cx, cy, world)

    def _army_retreat(self, army, members, cx, cy, world, dt):
        """Retreat to nearest friendly stronghold."""
        # Find nearest friendly stronghold
        best_sh = None
        best_dist = float('inf')
        for sh in world.strongholds:
            if sh.get('god_id') == army.god_id:
                d = math.hypot(sh['x'] - cx, sh['y'] - cy)
                if d < best_dist:
                    best_dist = d
                    best_sh = sh

        if best_sh:
            army.target_x = float(best_sh['x'])
            army.target_y = float(best_sh['y'])

        self._move_army_toward(members, army.target_x, army.target_y, dt, speed_mult=1.3)

        # If reached home, disband
        if best_dist < 10:
            for u in members:
                u.army_id = -1
                u.role = 'free'
                u.hp = min(u.max_hp, u.hp + u.max_hp * 0.2)  # Rest heals
            army.strength = 0

    def _move_army_toward(self, members, tx, ty, dt, speed_mult=1.0):
        """Move army members toward target position."""
        for u in members:
            u.target_x = tx + self._rng.uniform(-3, 3)
            u.target_y = ty + self._rng.uniform(-3, 3)
            dx = u.target_x - u.x
            dy = u.target_y - u.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 1.0:
                speed = u.effective_speed * dt * speed_mult
                u.x += dx / dist * min(speed, dist)
                u.y += dy / dist * min(speed, dist)
                u.x = max(0, min(MAP_W - 1, u.x))
                u.y = max(0, min(MAP_H - 1, u.y))
                u.state = 'moving'

    def _army_check_enemies(self, army, members, cx, cy, world):
        """Check for enemies near army and engage."""
        for u in self.units:
            if not u.alive or u.god_id == army.god_id:
                continue
            if abs(u.x - cx) > 20 or abs(u.y - cy) > 20:
                continue
            # Mark army as fighting
            army.state = 'fighting'
            if army.objective == 'patrol':
                army.objective = 'attack'
                army.target_x = u.x
                army.target_y = u.y
            break

    # ── simulation tick ────────────────────────────────────────────────────
    def simulate(self, dt, heightmap, biome_map, biome_names, land_mask,
                 influence=None, material_layer=None, world=None):
        """Update all units: move, fight, army AI, die."""
        from synergy import COMBAT_TYPE_ADVANTAGE
        changed = False

        # Army auto-formation check (every 2 seconds)
        self._army_check_accum += dt
        if self._army_check_accum >= 2.0 and world:
            self._auto_form_armies(world)
            self._update_armies(dt, world)
            self._army_check_accum = 0.0

        for u in self.units:
            if not u.alive:
                continue
            u.age += 1
            ix, iy = int(u.x), int(u.y)

            # Death check
            if u.hp <= 0:
                u.alive = False
                u.state = 'dead'
                changed = True
                continue

            # HP regeneration (slow, for non-combat units or when idle)
            if u.state == 'idle' and u.hp < u.max_hp:
                u.hp = min(u.max_hp, u.hp + 0.2 * dt)

            # Skip movement for army units (handled by army AI)
            if u.army_id >= 0:
                continue

            # ── Free unit AI ───────────────────────────────────────────
            if u.state == 'idle':
                # More purposeful wandering
                if self._rng.random() < 0.03:
                    # Try to stay in friendly territory
                    for _ in range(5):
                        nx = u.x + self._rng.uniform(-25, 25)
                        ny = u.y + self._rng.uniform(-25, 25)
                        nx = max(0, min(MAP_W - 1, nx))
                        ny = max(0, min(MAP_H - 1, ny))
                        gid, _ = influence.get_dominant_at(int(nx), int(ny))
                        if gid == u.god_id or gid is None:
                            u.target_x = nx
                            u.target_y = ny
                            u.state = 'moving'
                            break
                    else:
                        u.target_x = max(0, min(MAP_W - 1, u.x + self._rng.uniform(-20, 20)))
                        u.target_y = max(0, min(MAP_H - 1, u.y + self._rng.uniform(-20, 20)))
                        u.state = 'moving'

                # Healers seek injured friendlies
                if u.utype == 'healer' and self._rng.random() < 0.1:
                    for other in self.units:
                        if (other.alive and other.god_id == u.god_id
                                and other is not u and other.hp < other.max_hp * 0.7):
                            d = math.hypot(other.x - u.x, other.y - u.y)
                            if d < 20:
                                other.hp = min(other.max_hp, other.hp + 5)
                                u.gain_xp(1)
                                break

                # Scouts explore unexplored territory
                if u.utype == 'scout' and self._rng.random() < 0.08:
                    u.target_x = self._rng.uniform(10, MAP_W - 10)
                    u.target_y = self._rng.uniform(10, MAP_H - 10)
                    u.state = 'moving'

            elif u.state == 'moving':
                dx = u.target_x - u.x
                dy = u.target_y - u.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 0.5:
                    u.state = 'idle'
                else:
                    speed = u.effective_speed * dt
                    if 0 <= ix < MAP_W and 0 <= iy < MAP_H:
                        elev = heightmap[iy, ix]
                        if elev > 0.8:
                            speed *= 0.4
                        elif elev > 0.7:
                            speed *= 0.6

                    mx = dx / dist * speed
                    my = dy / dist * speed
                    nx = u.x + mx
                    ny = u.y + my
                    nx = max(0, min(MAP_W - 1, nx))
                    ny = max(0, min(MAP_H - 1, ny))
                    tix, tiy = int(nx), int(ny)
                    if (0 <= tix < MAP_W and 0 <= tiy < MAP_H
                            and not land_mask[tiy, tix]
                            and u.utype not in ('dragon', 'spirit')):
                        u.state = 'idle'
                    else:
                        u.x, u.y = nx, ny
                        changed = True

            elif u.state == 'retreating':
                # Move back to home
                dx = u.home_x - u.x
                dy = u.home_y - u.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 3:
                    u.state = 'idle'
                    u._morale = min(1.0, u._morale + 0.3)
                else:
                    speed = u.effective_speed * dt * 1.2  # Faster when retreating
                    u.x += dx / dist * speed
                    u.y += dy / dist * speed
                    u.x = max(0, min(MAP_W - 1, u.x))
                    u.y = max(0, min(MAP_H - 1, u.y))

            # ── Combat (all units, including army members) ─────────────
            if u.state in ('idle', 'moving', 'fighting') and u.atk > 0:
                combat_range = 3
                if u.utype == 'archer':
                    combat_range = 6
                elif u.utype == 'mage':
                    combat_range = 5
                elif u.utype == 'siege':
                    combat_range = 8
                elif u.utype == 'dragon':
                    combat_range = 5
                elif u.utype == 'assassin':
                    combat_range = 2

                best_target = None
                best_dist2 = combat_range * combat_range + 1

                for other in self.units:
                    if not other.alive or other is u:
                        continue
                    if other.god_id == u.god_id:
                        continue
                    ddx = other.x - u.x
                    ddy = other.y - u.y
                    d2 = ddx * ddx + ddy * ddy
                    if d2 < best_dist2:
                        best_dist2 = d2
                        best_target = other

                if best_target is not None:
                    eff_atk = u.effective_attack

                    # Type advantage
                    type_mult = COMBAT_TYPE_ADVANTAGE.get(
                        (u.utype, best_target.utype), 1.0)
                    eff_atk *= type_mult

                    # Assassin bonus: first strike does 3× if target is full HP
                    if u.utype == 'assassin' and best_target.hp >= best_target.max_hp * 0.9:
                        eff_atk *= 3.0

                    # Berserker rage: more damage at low HP
                    if u.utype == 'berserker':
                        hp_ratio = u.hp / u.max_hp
                        if hp_ratio < 0.5:
                            eff_atk *= 1.5 + (0.5 - hp_ratio)

                    # Target defense
                    target_def = best_target._biome_def * best_target._building_def
                    if target_def > 0:
                        eff_atk /= target_def

                    # Apply damage
                    best_target.hp -= eff_atk * dt
                    u.state = 'fighting'
                    changed = True

                    # Check kill
                    if best_target.hp <= 0:
                        best_target.alive = False
                        best_target.state = 'dead'
                        u.kills += 1
                        u.gain_xp(5)

                        # Record kills in history
                        if world and hasattr(world, 'history'):
                            if u.kills >= 10 and u.kills % 5 == 0:
                                world.history.record('hero_born',
                                    f"A legendary {u.utype} of {u.god_id} has {u.kills} kills!",
                                    god_id=u.god_id, pos=(int(u.x), int(u.y)))

                    # Move towards target if melee
                    if u.utype not in ('archer', 'mage', 'siege') and best_dist2 > 4:
                        ddx = best_target.x - u.x
                        ddy = best_target.y - u.y
                        dd = math.sqrt(best_dist2)
                        sp = u.effective_speed * dt * 0.5
                        u.x += ddx / dd * sp
                        u.y += ddy / dd * sp

                    # Morale check — retreat if losing badly
                    if u.hp < u.max_hp * 0.2 and u._morale < 0.5 and u.army_id < 0:
                        u.state = 'retreating'

            # Reset fighting state
            if u.state == 'fighting':
                u.state = 'idle'

        # Cleanup dead
        self._cleanup()

        if changed:
            self._version += 1
        return changed

    def _cleanup(self):
        self.units = [u for u in self.units if u.alive]

    # ── queries ────────────────────────────────────────────────────────────
    def get_at(self, x, y, radius=2):
        result = []
        for u in self.units:
            if not u.alive:
                continue
            if abs(u.x - x) <= radius and abs(u.y - y) <= radius:
                result.append(u)
        return result

    def get_god_units(self, god_id):
        return [u for u in self.units if u.alive and u.god_id == god_id]

    @property
    def count(self):
        return len([u for u in self.units if u.alive])

    def get_type_count(self, utype=None, god_id=None):
        total = 0
        for u in self.units:
            if not u.alive:
                continue
            if utype and u.utype != utype:
                continue
            if god_id and u.god_id != god_id:
                continue
            total += 1
        return total

    def get_army_count(self, god_id=None):
        if god_id:
            return len([a for a in self.armies if a.god_id == god_id])
        return len(self.armies)
