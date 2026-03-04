"""
Aethermoor — World Map  (v6.0 Living World)
Pixel-art retro world map with freeform influence, god tools,
material sim, civilizations, units, weather, element synergy.
EVERYTHING interacts with EVERYTHING: weather↔units↔buildings↔materials↔biomes.
v6.0: 1600×1000 map, chunk renderer, world history & eras, army AI,
      auto-civ expansion, Noita-depth 44 reactions, diplomacy.
"""
import pygame
import sys
import os
import random
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *
from terrain import generate_terrain, is_land
from influence import InfluenceMap
from camera import Camera
from renderer import Renderer
from structures import StructureRenderer
from particles import ParticleSystem
from ui import WorldBoxUI
from tools import ToolState, MaterialLayer, apply_tool, MATERIALS, MAT_NAMES
from events import EventLog
from data_loader import load_world_state, save_world_state, load_gods, save_gods
from live_sync import LiveSync
from civilizations import CivilizationSystem
from units import UnitSystem
from weather import WeatherSystem
from synergy import SynergyEngine
from history import WorldHistory

# ─── Default gods ──────────────────────────────────────────────────────────────
DEFAULT_GODS = [
    {"god_id": "god_balance",  "god_name": "Goddess of Balance",
     "nature": "Balance",  "color_primary": "#b4a0ff"},
    {"god_id": "god_fear",     "god_name": "God of Fear",
     "nature": "Fear",     "color_primary": "#c81e1e"},
    {"god_id": "god_greed",    "god_name": "God of Greed",
     "nature": "Greed",    "color_primary": "#ffc800"},
    {"god_id": "god_nature",   "god_name": "God of Nature",
     "nature": "Nature",   "color_primary": "#22aa44"},
    {"god_id": "god_fire",     "god_name": "God of Fire",
     "nature": "Fire",     "color_primary": "#ff6622"},
    {"god_id": "god_ice",      "god_name": "God of Ice",
     "nature": "Ice",      "color_primary": "#44bbdd"},
    {"god_id": "god_darkness", "god_name": "God of Darkness",
     "nature": "Darkness", "color_primary": "#5522aa"},
    {"god_id": "god_chaos",    "god_name": "God of Chaos",
     "nature": "Chaos",    "color_primary": "#dd22aa"},
    {"god_id": "god_void",     "god_name": "God of the Void",
     "nature": "Void",     "color_primary": "#225566"},
]

STRONGHOLD_NAMES = [
    "Astral Citadel", "Dread Fortress", "Golden Vault",
    "Verdant Spire",  "Ember Keep",     "Frost Bastion",
    "Shadow Sanctum", "Maelstrom Tower","Abyssal Throne",
]
STRONGHOLD_TYPES = [
    "citadel", "castle", "temple", "temple",
    "castle",  "citadel","temple", "tower", "altar",
]


def _find_land_positions(heightmap, biome_map, biome_names, count=9):
    land_set = {i for i, n in enumerate(biome_names)
                if n not in ('deep_ocean', 'ocean', 'shallow_water')}
    valid = []
    for y in range(MAP_H):
        for x in range(MAP_W):
            if biome_map[y, x] in land_set:
                e = heightmap[y, x]
                if 0.32 <= e <= 0.65:
                    valid.append((x, y))
    if not valid:
        for y in range(MAP_H):
            for x in range(MAP_W):
                if biome_map[y, x] in land_set:
                    valid.append((x, y))
    if len(valid) < count:
        return valid
    rng = np.random.RandomState(42)
    selected = [valid[rng.randint(len(valid))]]
    sample_n = min(2000, len(valid))
    for _ in range(count - 1):
        idxs = rng.choice(len(valid), sample_n, replace=False)
        best_d, best_p = -1, None
        for i in idxs:
            p = valid[i]
            md = min(math.hypot(p[0] - s[0], p[1] - s[1]) for s in selected)
            if md > best_d:
                best_d, best_p = md, p
        if best_p:
            selected.append(best_p)
    return selected


def _generate_strongholds(heightmap, biome_map, biome_names):
    positions = _find_land_positions(heightmap, biome_map, biome_names, 9)
    out = []
    for i, (god, pos) in enumerate(zip(DEFAULT_GODS, positions)):
        out.append({
            "id":       f"sh_{i+1}",
            "god_id":   god["god_id"],
            "x":        pos[0],
            "y":        pos[1],
            "strength": round(random.uniform(0.8, 1.0), 2),
            "radius":   random.randint(35, 55),
            "name":     STRONGHOLD_NAMES[i] if i < len(STRONGHOLD_NAMES) else f"Stronghold {i+1}",
            "type":     STRONGHOLD_TYPES[i]  if i < len(STRONGHOLD_TYPES) else "castle",
        })
    return out


# ═══════════════════════════════════════════════════════════════════════════════
class WorldMap:
    """Main application — WorldBox-style god game with civilizations, units, weather."""

    def __init__(self):
        pygame.init()

        # ── auto-detect screen size ────────────────────────────────────────
        info = pygame.display.Info()
        init_w = max(800, min(int(info.current_w * 0.90), 1920))
        init_h = max(600, min(int(info.current_h * 0.88), 1080))
        SCR.resize(init_w, init_h)

        self.screen = pygame.display.set_mode((SCR.w, SCR.h), pygame.RESIZABLE)
        pygame.display.set_caption("Aethermoor — World Map")
        self.clock   = pygame.time.Clock()
        self.running = True

        # ── terrain (now returns 5 values with temperature) ────────────────
        print("[WorldMap] generating terrain…")
        self.terrain_data = generate_terrain()
        self.heightmap, self.moisture, self.temperature, self.biome_map, self.biome_names = self.terrain_data

        self.land_mask = np.zeros((MAP_H, MAP_W), dtype=bool)
        for i, name in enumerate(self.biome_names):
            if name not in ('deep_ocean', 'ocean', 'shallow_water'):
                self.land_mask |= (self.biome_map == i)

        # ── material layer ─────────────────────────────────────────────────
        self.materials = MaterialLayer()

        # ── gods ───────────────────────────────────────────────────────────
        self._init_gods()
        god_ids = [g["god_id"] for g in self.gods]

        # ── influence ──────────────────────────────────────────────────────
        self.influence = InfluenceMap(god_ids, self.land_mask)
        self._init_strongholds()

        # ── tool state ─────────────────────────────────────────────────────
        self.tool_state = ToolState()

        # ── NEW: civilizations, units, weather, SYNERGY, HISTORY ───────────
        self.civilizations = CivilizationSystem()
        self.units         = UnitSystem()
        self.weather       = WeatherSystem()
        self.weather.init_temperature(self.heightmap)
        self.synergy       = SynergyEngine()
        self.history       = WorldHistory(god_ids)

        # ── subsystems ─────────────────────────────────────────────────────
        self.camera     = Camera()
        self.renderer   = Renderer(self.screen,
                                   (self.heightmap, self.moisture, self.biome_map, self.biome_names),
                                   self.influence, self.materials)
        self.structures = StructureRenderer()
        self.particles  = ParticleSystem()
        self.ui         = WorldBoxUI(self.tool_state, self.gods)
        self.event_log  = EventLog()

        # load saved events
        state = load_world_state()
        if state.get("world_events"):
            self.event_log.load_from_state(state["world_events"])
            for d in self.event_log.get_display(20):
                self.ui.add_event(d)

        self._refresh_standings()

        # ── live sync ──────────────────────────────────────────────────────
        self.live_sync = LiveSync(on_state_changed=self._on_sync)
        self.live_sync.start()

        # ── simulation timers ──────────────────────────────────────────────
        self._sim_accum     = 0.0
        self._civ_accum     = 0.0
        self._weather_accum = 0.0
        self._unit_accum    = 0.0
        self._synergy_accum = 0.0
        self._history_accum = 0.0

        self.ui.add_event("World map initialised — v6.0 Living World")
        print("[WorldMap] ready — 1600x1000, 22 biomes, 44 reactions, armies, history, auto-civ, LIVING WORLD.")

    # ── helpers ────────────────────────────────────────────────────────────
    def _init_gods(self):
        gd = load_gods()
        if gd.get("gods"):
            self.gods = gd["gods"]
        else:
            self.gods = DEFAULT_GODS
            save_gods({"gods": self.gods})

    def _init_strongholds(self):
        state = load_world_state()
        sh = state.get("strongholds")
        # Validate positions for new map size
        valid = True
        if sh:
            for s in sh:
                if s['x'] >= MAP_W or s['y'] >= MAP_H:
                    valid = False
                    break
        if sh and valid:
            self.strongholds = sh
        else:
            self.strongholds = _generate_strongholds(
                self.heightmap, self.biome_map, self.biome_names)
            state["strongholds"] = self.strongholds
            save_world_state(state)
        self.influence.set_strongholds(self.strongholds)

    def _refresh_standings(self):
        st = []
        for g in self.gods:
            gid = g["god_id"]
            pop = self.civilizations.get_total_population(gid)
            units = self.units.get_type_count(god_id=gid)
            armies = sum(1 for a in self.units.armies if a.god_id == gid) if hasattr(self.units, 'armies') else 0
            st.append({
                "god_id":      gid,
                "god_name":    g.get("god_name", gid),
                "territories": self.influence.get_god_territory_count(gid),
                "population":  pop,
                "units":       units,
                "armies":      armies,
            })
        st.sort(key=lambda x: x["territories"], reverse=True)
        self.ui.set_standings(st)

    def _on_sync(self, new_state):
        if new_state.get("strongholds"):
            self.strongholds = new_state["strongholds"]
            self.influence.set_strongholds(self.strongholds)
            self.renderer.mark_influence_dirty()
            self._refresh_standings()
        evts = new_state.get("world_events", [])
        if evts:
            desc = EventLog.format(evts[-1])
            self.event_log.add(evts[-1].get("type", "unknown"), desc,
                               evts[-1].get("god_id"))
            self.ui.add_event(desc)

    def _reclassify_biomes(self):
        """Re-run biome classification after terrain edits."""
        from config import (ELEV_DEEP_OCEAN, ELEV_OCEAN, ELEV_SHALLOW, ELEV_BEACH,
                            ELEV_LOWLAND, ELEV_HIGHLAND, ELEV_MOUNTAIN, ELEV_PEAK,
                            MOIST_DRY, MOIST_MED, MOIST_WET,
                            TEMP_COLD, TEMP_COOL, TEMP_WARM, TEMP_HOT)
        bn = self.biome_names
        idx = {name: i for i, name in enumerate(bn)}
        bm = self.biome_map
        e  = self.heightmap
        m  = self.moisture
        t  = self.temperature

        bm[:] = idx['grassland']
        bm[e < ELEV_DEEP_OCEAN] = idx['deep_ocean']
        bm[(e >= ELEV_DEEP_OCEAN) & (e < ELEV_OCEAN)] = idx['ocean']
        bm[(e >= ELEV_OCEAN) & (e < ELEV_SHALLOW)] = idx['shallow_water']
        bm[(e >= ELEV_SHALLOW) & (e < ELEV_BEACH)] = idx['beach']

        # Reef
        reef_mask = (e >= ELEV_OCEAN) & (e < ELEV_SHALLOW) & (t > TEMP_WARM) & (m > MOIST_WET)
        bm[reef_mask] = idx['reef']

        low = (e >= ELEV_BEACH) & (e < ELEV_LOWLAND)
        bm[low & (t < TEMP_COLD)] = idx['tundra']
        bm[low & (t >= TEMP_COLD) & (t < TEMP_COOL) & (m >= MOIST_MED)] = idx['taiga']
        bm[low & (t >= TEMP_COLD) & (t < TEMP_COOL) & (m < MOIST_MED)] = idx['tundra']
        bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m < MOIST_DRY)] = idx['desert']
        bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m >= MOIST_DRY) & (m < MOIST_MED)] = idx['savanna']
        bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m >= MOIST_MED) & (m < MOIST_WET)] = idx['grassland']
        bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m >= MOIST_WET)] = idx['forest']
        bm[low & (t >= TEMP_HOT) & (m < MOIST_DRY)] = idx['desert']
        bm[low & (t >= TEMP_HOT) & (m >= MOIST_DRY) & (m < MOIST_MED)] = idx['savanna']
        bm[low & (t >= TEMP_HOT) & (m >= MOIST_MED)] = idx['tropical']
        bm[low & (m > 0.70) & (t >= TEMP_COOL)] = idx['swamp']

        hi = (e >= ELEV_LOWLAND) & (e < ELEV_HIGHLAND)
        bm[hi & (t < TEMP_COOL) & (m >= MOIST_MED)] = idx['taiga']
        bm[hi & (t < TEMP_COOL) & (m < MOIST_MED)] = idx['tundra']
        bm[hi & (t >= TEMP_COOL) & (m < MOIST_DRY)] = idx['hills']
        bm[hi & (t >= TEMP_COOL) & (m >= MOIST_DRY) & (m < 0.70)] = idx['dense_forest']
        bm[hi & (t >= TEMP_COOL) & (m >= 0.70)] = idx['swamp']

        mt = (e >= ELEV_HIGHLAND) & (e < ELEV_MOUNTAIN)
        bm[mt & (m < 0.40)] = idx['mountain']
        bm[mt & (m >= 0.40)] = idx['high_mountain']
        bm[(e >= ELEV_MOUNTAIN) & (e < ELEV_PEAK)] = idx['snow']

        volcano_mask = (e >= ELEV_PEAK) & (t > TEMP_WARM) & (m < MOIST_DRY)
        bm[volcano_mask] = idx['volcano']
        bm[(e >= ELEV_PEAK) & ~volcano_mask] = idx['snow']

        crystal_mask = (e >= ELEV_HIGHLAND) & (e < ELEV_MOUNTAIN) & (m > 0.75) & (t < TEMP_COOL)
        bm[crystal_mask] = idx['crystal_field']

        self.renderer.terrain_colors = self.renderer._build_base_colors()
        self.renderer.mark_influence_dirty()

        self.land_mask[:] = False
        for i, name in enumerate(bn):
            if name not in ('deep_ocean', 'ocean', 'shallow_water'):
                self.land_mask |= (bm == i)

    def _event_log_fn(self, text):
        self.event_log.add("tool_action", text)
        self.ui.add_event(text)

    def _screen_to_tile(self, sx, sy):
        return self.camera.screen_to_tile(sx, sy - TOPBAR_H)

    # ═══════════════════════════════════════════════════════════════════════
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self._events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        self.live_sync.stop()
        pygame.quit()

    # ── events ─────────────────────────────────────────────────────────────
    def _events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False

            elif ev.type == pygame.VIDEORESIZE:
                SCR.resize(ev.w, ev.h)
                self.screen = pygame.display.set_mode((SCR.w, SCR.h), pygame.RESIZABLE)
                self.renderer.mark_influence_dirty()
                self.structures.clear_cache()
                self.camera._clamp()

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.ui.show_info_panel:
                        self.ui.close_info()
                    else:
                        self.running = False
                elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    self.camera.zoom_in(); self.structures.clear_cache()
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.camera.zoom_out(); self.structures.clear_cache()
                elif ev.key == pygame.K_SPACE:
                    self.tool_state.toggle_pause()
                elif ev.key == pygame.K_LEFTBRACKET:
                    self.tool_state.prev_brush()
                elif ev.key == pygame.K_RIGHTBRACKET:
                    self.tool_state.next_brush()
                elif ev.key == pygame.K_TAB:
                    self.ui.show_info_panel = not self.ui.show_info_panel

            elif ev.type == pygame.MOUSEWHEEL:
                if ev.y > 0:
                    self.camera.zoom_in(); self.structures.clear_cache()
                elif ev.y < 0:
                    self.camera.zoom_out(); self.structures.clear_cache()

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if ev.button == 1:
                    if self.ui.handle_click(mx, my):
                        continue
                    if not self.ui.is_over_ui(mx, my):
                        self.tool_state.painting = True
                        self._apply_at_mouse(mx, my)
                elif ev.button in (2, 3):
                    if not self.ui.is_over_ui(mx, my):
                        self.camera.start_drag((mx, my - TOPBAR_H))

            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    self.tool_state.painting = False
                elif ev.button in (2, 3):
                    self.camera.stop_drag()

            elif ev.type == pygame.MOUSEMOTION:
                mx, my = ev.pos
                if self.camera.dragging:
                    self.camera.update_drag((mx, my - TOPBAR_H))

                if self.tool_state.painting and not self.ui.is_over_ui(mx, my):
                    self._apply_at_mouse(mx, my)

                if not self.ui.is_over_ui(mx, my) and my > TOPBAR_H:
                    tx, ty = self._screen_to_tile(mx, my)
                    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                        biome = self.biome_names[self.biome_map[ty, tx]]
                        gid, st = self.influence.get_dominant_at(tx, ty)
                        mat = self.materials.get_at(tx, ty)
                        elev = float(self.heightmap[ty, tx])
                        moist = float(self.moisture[ty, tx])
                        temp = float(self.temperature[ty, tx])
                        weather = self.weather.get_weather_at(tx, ty)
                        building = self.civilizations.get_at(tx, ty)
                        units_here = self.units.get_at(tx, ty)
                        self.ui.set_hover(tx, ty, biome, gid, round(st, 2),
                                          mat, round(elev, 3), round(moist, 3),
                                          round(temp, 3), weather,
                                          building, len(units_here))

    def _apply_at_mouse(self, mx, my):
        tx, ty = self._screen_to_tile(mx, my)
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
            return
        tool = self.tool_state.tool
        tid  = tool['id']

        if tid == 'select':
            biome = self.biome_names[self.biome_map[ty, tx]]
            gid, st = self.influence.get_dominant_at(tx, ty)
            sh = None
            for s in self.strongholds:
                if abs(s['x'] - tx) <= 3 and abs(s['y'] - ty) <= 3:
                    sh = s; break
            building = self.civilizations.get_at(tx, ty)
            units_here = self.units.get_at(tx, ty)
            self.ui.set_info({
                "biome": biome, "god_id": gid,
                "influence": st, "stronghold": sh,
                "pos": (tx, ty),
                "elevation": float(self.heightmap[ty, tx]),
                "moisture": float(self.moisture[ty, tx]),
                "temperature": float(self.temperature[ty, tx]),
                "material": self.materials.get_at(tx, ty),
                "building": building,
                "units": units_here,
                "weather": self.weather.get_weather_at(tx, ty),
                "season": self.weather.season,
            })
            return

        if tid == 'measure':
            return

        changed = apply_tool(
            self.tool_state, tx, ty,
            self.heightmap, self.moisture, self.biome_map, self.biome_names,
            self.materials, self.influence, self.strongholds, self.gods,
            self.particles, self._reclassify_biomes, self._event_log_fn,
            world=self,
        )
        if changed:
            self.renderer.mark_influence_dirty()
            self._refresh_standings()

    # ── update ─────────────────────────────────────────────────────────────
    def _update(self, dt):
        self.camera.handle_keys(dt)
        self.particles.update(dt, self.camera, self.biome_map,
                              self.biome_names, self.influence)

        if not self.tool_state.sim_paused:
            speed = self.tool_state.sim_speed

            # Material simulation
            sim_dt = 1.0 / SIM_TICKS_PER_SEC
            self._sim_accum += dt * speed
            ticks = 0
            while self._sim_accum >= sim_dt and ticks < 5:
                self.materials.simulate(self.heightmap, self.biome_map,
                                        self.biome_names)
                self._sim_accum -= sim_dt
                ticks += 1

            # Weather simulation (now with biome reclassify callback)
            weather_dt = 1.0 / max(WEATHER_TICK_RATE, 0.1)
            self._weather_accum += dt * speed
            if self._weather_accum >= weather_dt:
                self.weather.simulate(
                    self._weather_accum, self.heightmap, self.moisture,
                    self.materials, self.biome_map, self.biome_names,
                    reclassify_fn=self._reclassify_biomes)
                self._weather_accum = 0.0

            # ── UNIVERSAL SYNERGY ENGINE ───────────────────────────────
            self._synergy_accum += dt * speed
            if self._synergy_accum >= 0.2:  # 5 synergy ticks per second
                from synergy import SynergyEngine as SE
                SE.reset_tick_modifiers(self)
                self.synergy.tick(self._synergy_accum, self)
                self._synergy_accum = 0.0

            # Civilization simulation (now with season + world ref)
            civ_dt = 1.0 / max(CIV_TICK_RATE, 0.1)
            self._civ_accum += dt * speed
            if self._civ_accum >= civ_dt:
                self.civilizations.simulate(
                    self._civ_accum, self.biome_map, self.biome_names,
                    self.heightmap, self.influence, self.materials,
                    weather=self.weather, season=self.weather.season,
                    world=self)
                self._civ_accum = 0.0

            # Unit simulation (synergy modifiers already applied + world ref)
            self._unit_accum += dt * speed
            if self._unit_accum >= 0.1:
                self.units.simulate(
                    self._unit_accum, self.heightmap, self.biome_map,
                    self.biome_names, self.land_mask,
                    self.influence, self.materials,
                    world=self)
                self._unit_accum = 0.0

            # World History tick
            self._history_accum += dt * speed
            if self._history_accum >= 1.0:
                self.history.tick(self._history_accum, self)
                self._history_accum = 0.0
                # Push recent history events to UI event log
                for ev in self.history.events[-3:]:
                    if ev.tick == self.history.world_tick:
                        self.ui.add_event(f"[{ev.era}] {ev.text}")

    # ── draw ───────────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill((6, 6, 10))
        self._draw_map_area()
        army_count = len(self.units.armies) if hasattr(self.units, 'armies') else 0
        war_count = len([w for w in self.history.wars if w.winner is None]) if hasattr(self, 'history') else 0
        self.ui.render(self.screen, fps=self.clock.get_fps(),
                       season=self.weather.season,
                       pop=self.civilizations.get_total_population(),
                       unit_count=self.units.count,
                       building_count=len(self.civilizations.active_buildings),
                       weather_zones=len(self.weather.zones),
                       era=getattr(self.history, 'era_name', ''),
                       army_count=army_count,
                       war_count=war_count)

    def _draw_map_area(self):
        cell = self.camera.cell_size
        x0, y0, x1, y1 = self.camera.get_visible_rect()
        vis_w = x1 - x0
        vis_h = y1 - y0
        if vis_w <= 0 or vis_h <= 0:
            return

        # Terrain + influence + materials
        self.renderer.render_map_to_area(self.camera, TOPBAR_H)

        # ── Buildings ──────────────────────────────────────────────────
        for b in self.civilizations.active_buildings:
            tx, ty = b.x, b.y
            if tx < x0 - 6 or tx > x1 + 6 or ty < y0 - 6 or ty > y1 + 6:
                continue
            sx, sy = self.camera.tile_to_screen(tx, ty)
            sy += TOPBAR_H
            god_col = GOD_COLORS.get(b.god_id, (180, 180, 180))
            icon_sc = max(2, cell // 2)
            stype = b.btype if b.btype in ('village','city','farm','mine','port',
                        'wall','bridge','workshop','barracks','graveyard','temple') else 'castle'
            key = (stype, b.god_id or '', icon_sc)
            if key not in self.structures._cache:
                self.structures._cache[key] = self.structures._make(
                    stype, god_col, icon_sc)
            icon = self.structures._cache[key]
            ix = sx + cell // 2 - icon.get_width() // 2
            iy = sy + cell // 2 - icon.get_height() // 2
            self.screen.blit(icon, (ix, iy))

        # ── Strongholds ───────────────────────────────────────────────
        for sh in self.strongholds:
            tx, ty = sh['x'], sh['y']
            if tx < x0 - 6 or tx > x1 + 6 or ty < y0 - 6 or ty > y1 + 6:
                continue
            sx, sy = self.camera.tile_to_screen(tx, ty)
            sy += TOPBAR_H
            stype  = sh.get('type', 'castle')
            god_id = sh.get('god_id', '')
            god_col = GOD_COLORS.get(god_id, (180, 180, 180))
            icon_sc = max(2, cell // 2)
            key = (stype, god_id, icon_sc)
            if key not in self.structures._cache:
                self.structures._cache[key] = self.structures._make(
                    stype, god_col, icon_sc)
            icon = self.structures._cache[key]
            ix = sx + cell // 2 - icon.get_width() // 2
            iy = sy + cell // 2 - icon.get_height() // 2
            self.screen.blit(icon, (ix, iy))

        # ── Units ──────────────────────────────────────────────────────
        _UNIT_SHAPES = {
            'scout': 'diamond', 'healer': 'cross', 'berserker': 'square',
            'assassin': 'triangle', 'titan': 'big_circle',
            'dragon': 'big_circle', 'mage': 'diamond', 'knight': 'square',
        }
        for u in self.units.units:
            if not u.alive:
                continue
            utx, uty = int(u.x), int(u.y)
            if utx < x0 - 2 or utx > x1 + 2 or uty < y0 - 2 or uty > y1 + 2:
                continue
            sx, sy = self.camera.tile_to_screen(utx, uty)
            sy += TOPBAR_H
            god_col = GOD_COLORS.get(u.god_id, (200, 200, 200))
            sz = max(2, cell // 3)
            cx_u = sx + cell // 2
            cy_u = sy + cell // 2
            shape = _UNIT_SHAPES.get(u.utype, 'circle')

            # Veteran glow
            if getattr(u, 'is_veteran', False):
                pygame.draw.circle(self.screen, (255, 255, 100),
                                   (cx_u, cy_u), sz + 2, 1)

            if shape == 'diamond':
                pts = [(cx_u, cy_u - sz), (cx_u + sz, cy_u),
                       (cx_u, cy_u + sz), (cx_u - sz, cy_u)]
                pygame.draw.polygon(self.screen, god_col, pts)
                pygame.draw.polygon(self.screen, (20, 20, 30), pts, 1)
            elif shape == 'square':
                pygame.draw.rect(self.screen, god_col,
                                 (cx_u - sz, cy_u - sz, sz * 2, sz * 2))
                pygame.draw.rect(self.screen, (20, 20, 30),
                                 (cx_u - sz, cy_u - sz, sz * 2, sz * 2), 1)
            elif shape == 'triangle':
                pts = [(cx_u, cy_u - sz), (cx_u + sz, cy_u + sz),
                       (cx_u - sz, cy_u + sz)]
                pygame.draw.polygon(self.screen, god_col, pts)
                pygame.draw.polygon(self.screen, (20, 20, 30), pts, 1)
            elif shape == 'cross':
                pygame.draw.line(self.screen, god_col,
                                 (cx_u - sz, cy_u), (cx_u + sz, cy_u), 2)
                pygame.draw.line(self.screen, god_col,
                                 (cx_u, cy_u - sz), (cx_u, cy_u + sz), 2)
            elif shape == 'big_circle':
                pygame.draw.circle(self.screen, god_col,
                                   (cx_u, cy_u), sz + 1)
                pygame.draw.circle(self.screen, (20, 20, 30),
                                   (cx_u, cy_u), sz + 1, 1)
            else:
                pygame.draw.circle(self.screen, god_col,
                                   (cx_u, cy_u), sz)
                pygame.draw.circle(self.screen, (20, 20, 30),
                                   (cx_u, cy_u), sz, 1)

            # HP bar for damaged units
            if u.hp < u.max_hp:
                bw = max(4, cell)
                bh = max(1, cell // 6)
                bx = sx + cell // 2 - bw // 2
                by = sy - 2
                hp_ratio = u.hp / u.max_hp
                pygame.draw.rect(self.screen, (40, 0, 0), (bx, by, bw, bh))
                pygame.draw.rect(self.screen, (0, 200, 0), (bx, by, int(bw * hp_ratio), bh))

        # ── Weather zone overlays ──────────────────────────────────────
        for z in self.weather.zones:
            zx, zy = z.x, z.y
            zr = z.radius
            if zx + zr < x0 or zx - zr > x1 or zy + zr < y0 or zy - zr > y1:
                continue
            sx, sy = self.camera.tile_to_screen(zx, zy)
            sy += TOPBAR_H
            rpx = zr * cell
            ws = pygame.Surface((rpx * 2, rpx * 2), pygame.SRCALPHA)
            if z.wtype == 'rain':
                pygame.draw.circle(ws, (60, 100, 200, 20), (rpx, rpx), rpx)
            elif z.wtype == 'storm':
                pygame.draw.circle(ws, (80, 60, 120, 25), (rpx, rpx), rpx)
            elif z.wtype == 'snow':
                pygame.draw.circle(ws, (200, 210, 220, 18), (rpx, rpx), rpx)
            elif z.wtype == 'heat':
                pygame.draw.circle(ws, (200, 100, 40, 15), (rpx, rpx), rpx)
            elif z.wtype == 'cold':
                pygame.draw.circle(ws, (100, 160, 220, 18), (rpx, rpx), rpx)
            self.screen.blit(ws, (sx - rpx, sy - rpx))

        # ── Particles ─────────────────────────────────────────────────
        for p in self.particles.particles:
            sx, sy = self.camera.tile_to_screen(p.x, p.y)
            sy += TOPBAR_H
            if (sx < -20 or sx > SCR.w + 20
                    or sy < TOPBAR_H - 20
                    or sy > TOPBAR_H + SCR.viewport_h + 20):
                continue
            sz = max(1, int(p.size * cell / 4))
            a  = p.alpha
            if p.kind == 'cloud':
                sz2 = max(4, int(p.size * cell / 2))
                cs = pygame.Surface((sz2 * 3, sz2 * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(cs, (*p.color, min(a, 50)),
                                    (0, 0, sz2 * 3, sz2 * 2))
                self.screen.blit(cs, (sx - sz2, sy - sz2 // 2))
            elif p.kind == 'magic':
                gs = sz * 3
                ms = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
                pygame.draw.circle(ms, (*p.color, a // 3), (gs, gs), gs)
                pygame.draw.circle(ms, (*p.color, a), (gs, gs), sz)
                self.screen.blit(ms, (sx - gs, sy - gs))
            else:
                if a > 200:
                    pygame.draw.rect(self.screen, p.color, (sx, sy, sz, sz))
                else:
                    ps = pygame.Surface((sz, sz), pygame.SRCALPHA)
                    ps.fill((*p.color, a))
                    self.screen.blit(ps, (sx, sy))

        # Minimap
        self.renderer.render_minimap(self.camera, y_offset=TOPBAR_H)


# ═══════════════════════════════════════════════════════════════════════════════
def main():
    app = WorldMap()
    app.run()


if __name__ == "__main__":
    main()
