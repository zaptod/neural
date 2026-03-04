"""
World Map — Weather System  (v5.0 Universal Synergy)
Seasons, weather zones, precipitation, temperature effects.
Weather now affects biomes by modifying moisture/temperature.
"""
import numpy as np
import random
from config import (
    MAP_W, MAP_H,
    WEATHER_TICK_RATE, SEASON_LENGTH, SEASONS,
    TEMP_COLD, TEMP_COOL, TEMP_WARM, TEMP_HOT,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Weather zone — a localized weather effect
# ═══════════════════════════════════════════════════════════════════════════════

class WeatherZone:
    """A localized weather effect (rain, storm, snow, heat, cold)."""
    __slots__ = ('wtype', 'x', 'y', 'radius', 'life', 'intensity')

    def __init__(self, wtype, x, y, radius, life=300, intensity=1.0):
        self.wtype     = wtype
        self.x, self.y = x, y
        self.radius    = radius
        self.life      = life
        self.intensity = intensity


class WeatherSystem:
    """Global weather with seasons and localized weather zones."""

    def __init__(self):
        # Temperature map (0.0 cold → 1.0 hot)
        self.temperature = np.full((MAP_H, MAP_W), 0.5, dtype=np.float32)
        # Active weather zones
        self.zones: list[WeatherZone] = []
        # Season tracking
        self.season_idx   = 0    # 0=spring, 1=summer, 2=autumn, 3=winter
        self.season_timer = 0.0
        self._version = 0
        self._rng = np.random.RandomState(300)

    @property
    def season(self):
        return SEASONS[self.season_idx]

    # ── initialize temperature from latitude + elevation ───────────────────
    def init_temperature(self, heightmap):
        """Generate base temperature from latitude (y) and elevation."""
        h, w = heightmap.shape
        # Latitude: warm at center, cold at poles
        lat = np.abs(np.linspace(-1, 1, h))[:, np.newaxis]  # (H, 1)
        lat_temp = 1.0 - lat * 0.7  # 0.3 at poles, 1.0 at equator

        # Elevation: colder at high altitude
        elev_temp = 1.0 - heightmap * 0.5

        # Combine
        self.temperature = np.clip(lat_temp * 0.6 + elev_temp * 0.4
                                    + self._rng.uniform(-0.05, 0.05, (h, w)),
                                    0, 1).astype(np.float32)

    # ── cast weather tool ──────────────────────────────────────────────────
    def cast(self, wtype, x, y, radius):
        """Place a weather zone (from tool)."""
        radius = max(radius, 5)
        life = 300
        if wtype == 'clear':
            # Remove zones in area
            self.zones = [z for z in self.zones
                          if abs(z.x - x) > radius or abs(z.y - y) > radius]
            self._version += 1
            return
        zone = WeatherZone(wtype, x, y, radius, life)
        self.zones.append(zone)
        self._version += 1

    # ── simulation tick ────────────────────────────────────────────────────
    def simulate(self, dt, heightmap, moisture, material_layer, biome_map, biome_names,
                 reclassify_fn=None):
        """Update weather each tick. Now also shifts biomes via moisture/temp changes."""
        changed = False
        biome_shifted = False

        # Season cycle
        self.season_timer += dt
        if self.season_timer >= SEASON_LENGTH:
            self.season_timer -= SEASON_LENGTH
            self.season_idx = (self.season_idx + 1) % 4
            self._apply_season_shift(heightmap)
            changed = True
            biome_shifted = True  # Season change warrants biome reclass

        # Process active weather zones
        dead = []
        for i, z in enumerate(self.zones):
            z.life -= 1
            if z.life <= 0:
                dead.append(i)
                continue
            zone_changed = self._apply_zone(z, heightmap, moisture, material_layer,
                                             biome_map, biome_names)
            changed |= zone_changed
            if zone_changed and z.wtype in ('rain', 'heat', 'cold', 'snow'):
                biome_shifted = True

        # Remove expired
        for i in reversed(dead):
            self.zones.pop(i)

        # Random ambient weather (small chance per tick)
        if self._rng.random() < 0.005:
            self._spawn_ambient_weather()
            changed = True

        # Reclassify biomes if moisture/temperature shifted significantly
        if biome_shifted and reclassify_fn and self._rng.random() < 0.05:
            reclassify_fn()

        if changed:
            self._version += 1
        return changed

    # ── apply zone effects ─────────────────────────────────────────────────
    def _apply_zone(self, zone, heightmap, moisture, material_layer,
                    biome_map, biome_names):
        from tools import MAT_INDEX
        changed = False
        x, y, r = zone.x, zone.y, zone.radius
        y0 = max(0, y - r)
        y1 = min(MAP_H, y + r + 1)
        x0 = max(0, x - r)
        x1 = min(MAP_W, x + r + 1)

        if zone.wtype == 'rain':
            # Increase moisture across zone — drives biome shifts toward wetter variants
            moisture_slice = moisture[y0:y1, x0:x1]
            moisture_slice[:] = np.clip(moisture_slice + 0.0005, 0, 1)
            # Chance to place water at wet spots
            if self._rng.random() < 0.1:
                rx = x + self._rng.randint(-r, r + 1)
                ry = y + self._rng.randint(-r, r + 1)
                if 0 <= rx < MAP_W and 0 <= ry < MAP_H:
                    moisture[ry, rx] = min(1.0, moisture[ry, rx] + 0.01)
                    if moisture[ry, rx] > 0.8 and material_layer.mat[ry, rx] == 0:
                        water_idx = MAT_INDEX.get('water', 0)
                        if self._rng.random() < 0.05:
                            material_layer.mat[ry, rx] = water_idx
                            changed = True
            # Rain also puts out fire
            fire_idx = MAT_INDEX.get('fire', 0)
            hf_idx = MAT_INDEX.get('hellfire', 0)
            slice_mat = material_layer.mat[y0:y1, x0:x1]
            fire_here = (slice_mat == fire_idx)
            if fire_idx and np.any(fire_here) and self._rng.random() < 0.2:
                ys_f, xs_f = np.where(fire_here)
                if len(ys_f) > 0:
                    k = self._rng.randint(len(ys_f))
                    slice_mat[ys_f[k], xs_f[k]] = 0
                    changed = True

        elif zone.wtype == 'storm':
            # Lightning strikes + rain
            if self._rng.random() < 0.08:
                rx = x + self._rng.randint(-r, r + 1)
                ry = y + self._rng.randint(-r, r + 1)
                if 0 <= rx < MAP_W and 0 <= ry < MAP_H:
                    light_idx = MAT_INDEX.get('lightning_mat', 0)
                    if light_idx and material_layer.mat[ry, rx] == 0:
                        material_layer.mat[ry, rx] = light_idx
                        material_layer.life[ry, rx] = 8
                        changed = True
            # Also some rain
            if self._rng.random() < 0.15:
                rx = x + self._rng.randint(-r, r + 1)
                ry = y + self._rng.randint(-r, r + 1)
                if 0 <= rx < MAP_W and 0 <= ry < MAP_H:
                    moisture[ry, rx] = min(1.0, moisture[ry, rx] + 0.005)

        elif zone.wtype == 'snow':
            # Lower temperature, place frost/ice
            self.temperature[y0:y1, x0:x1] = np.clip(
                self.temperature[y0:y1, x0:x1] - 0.001, 0, 1)
            if self._rng.random() < 0.08:
                rx = x + self._rng.randint(-r, r + 1)
                ry = y + self._rng.randint(-r, r + 1)
                if 0 <= rx < MAP_W and 0 <= ry < MAP_H:
                    frost_idx = MAT_INDEX.get('frost', 0)
                    if frost_idx and material_layer.mat[ry, rx] == 0:
                        material_layer.mat[ry, rx] = frost_idx
                        material_layer.life[ry, rx] = 150
                        changed = True

        elif zone.wtype == 'heat':
            self.temperature[y0:y1, x0:x1] = np.clip(
                self.temperature[y0:y1, x0:x1] + 0.002, 0, 1)
            # Heat dries out moisture → biome shifts toward desert/savanna
            moisture[y0:y1, x0:x1] = np.clip(
                moisture[y0:y1, x0:x1] - 0.0003, 0, 1)
            # Evaporate water
            water_idx = MAT_INDEX.get('water', 0)
            slice_mat = material_layer.mat[y0:y1, x0:x1]
            water_here = slice_mat == water_idx
            if np.any(water_here) and self._rng.random() < 0.1:
                ys, xs = np.where(water_here)
                if len(ys) > 0:
                    k = self._rng.randint(len(ys))
                    gy, gx = ys[k] + y0, xs[k] + x0
                    steam_idx = MAT_INDEX.get('steam', 0)
                    if steam_idx:
                        material_layer.mat[gy, gx] = steam_idx
                        material_layer.life[gy, gx] = 80
                        changed = True
            # Heat can spontaneously ignite flammable biomes
            if self._rng.random() < 0.01:
                rx = x + self._rng.randint(-r, r + 1)
                ry = y + self._rng.randint(-r, r + 1)
                if 0 <= rx < MAP_W and 0 <= ry < MAP_H:
                    biome_here = biome_names[biome_map[ry, rx]]
                    if biome_here in ('forest', 'dense_forest', 'grassland', 'savanna'):
                        if material_layer.mat[ry, rx] == 0:
                            fire_idx = MAT_INDEX.get('fire', 0)
                            if fire_idx:
                                material_layer.mat[ry, rx] = fire_idx
                                material_layer.life[ry, rx] = 50
                                changed = True

        elif zone.wtype == 'cold':
            self.temperature[y0:y1, x0:x1] = np.clip(
                self.temperature[y0:y1, x0:x1] - 0.002, 0, 1)
            # Cold slightly increases moisture (condensation)
            moisture[y0:y1, x0:x1] = np.clip(
                moisture[y0:y1, x0:x1] + 0.0002, 0, 1)
            # Freeze water to ice
            water_idx = MAT_INDEX.get('water', 0)
            ice_idx = MAT_INDEX.get('ice', 0)
            if water_idx and ice_idx:
                slice_mat = material_layer.mat[y0:y1, x0:x1]
                water_here = slice_mat == water_idx
                cold_temp = self.temperature[y0:y1, x0:x1] < TEMP_COLD
                freeze = water_here & cold_temp
                if np.any(freeze):
                    slice_mat[freeze] = ice_idx
                    changed = True
            # Extreme cold places frost on empty tiles
            if self._rng.random() < 0.05:
                rx = x + self._rng.randint(-r, r + 1)
                ry = y + self._rng.randint(-r, r + 1)
                if 0 <= rx < MAP_W and 0 <= ry < MAP_H:
                    if self.temperature[ry, rx] < TEMP_COLD:
                        frost_idx = MAT_INDEX.get('frost', 0)
                        if frost_idx and material_layer.mat[ry, rx] == 0:
                            material_layer.mat[ry, rx] = frost_idx
                            material_layer.life[ry, rx] = 120
                            changed = True

        return changed

    # ── season effects ─────────────────────────────────────────────────────
    def _apply_season_shift(self, heightmap):
        """Shift global temperature based on season."""
        if self.season == 'summer':
            self.temperature += 0.05
        elif self.season == 'winter':
            self.temperature -= 0.05
        elif self.season == 'spring':
            self.temperature += 0.02
        else:  # autumn
            self.temperature -= 0.02
        np.clip(self.temperature, 0, 1, out=self.temperature)

    # ── ambient weather ────────────────────────────────────────────────────
    def _spawn_ambient_weather(self):
        x = int(self._rng.randint(0, MAP_W))
        y = int(self._rng.randint(0, MAP_H))
        r = int(self._rng.randint(20, 60))

        if self.season == 'winter':
            wtype = self._rng.choice(['snow', 'cold', 'storm'])
        elif self.season == 'summer':
            wtype = self._rng.choice(['heat', 'storm', 'rain'])
        else:
            wtype = self._rng.choice(['rain', 'storm', 'rain'])

        zone = WeatherZone(str(wtype), x, y, r, life=200)
        self.zones.append(zone)

    # ── queries ────────────────────────────────────────────────────────────
    def get_weather_at(self, x, y):
        """Return weather type at tile, or None."""
        for z in self.zones:
            if abs(z.x - x) <= z.radius and abs(z.y - y) <= z.radius:
                return z.wtype
        return None

    def get_temp_at(self, x, y):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            return float(self.temperature[y, x])
        return 0.5
