"""
World Map — Procedural Terrain Generator  (v4.0 MEGA UPDATE)
Generates heightmap + moisture + temperature via layered noise (fBm).
Classifies 22 biomes including tropical, tundra, taiga, volcano, crystal, corrupted.
"""
import numpy as np
from scipy.ndimage import zoom as _zoom

try:
    from .config import (
        MAP_W, MAP_H,
        TERRAIN_SEED, MOISTURE_SEED, TEMPERATURE_SEED,
        TERRAIN_OCTAVES, TERRAIN_PERSISTENCE, TERRAIN_LACUNARITY,
        BIOME_COLORS,
        ELEV_DEEP_OCEAN, ELEV_OCEAN, ELEV_SHALLOW, ELEV_BEACH,
        ELEV_LOWLAND, ELEV_HIGHLAND, ELEV_MOUNTAIN, ELEV_PEAK,
        MOIST_DRY, MOIST_MED, MOIST_WET,
        TEMP_COLD, TEMP_COOL, TEMP_WARM, TEMP_HOT,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from config import (
        MAP_W, MAP_H,
        TERRAIN_SEED, MOISTURE_SEED, TEMPERATURE_SEED,
        TERRAIN_OCTAVES, TERRAIN_PERSISTENCE, TERRAIN_LACUNARITY,
        BIOME_COLORS,
        ELEV_DEEP_OCEAN, ELEV_OCEAN, ELEV_SHALLOW, ELEV_BEACH,
        ELEV_LOWLAND, ELEV_HIGHLAND, ELEV_MOUNTAIN, ELEV_PEAK,
        MOIST_DRY, MOIST_MED, MOIST_WET,
        TEMP_COLD, TEMP_COOL, TEMP_WARM, TEMP_HOT,
    )

# ───────────────────────────────────────────────────────────────────────────────
# Noise helpers
# ───────────────────────────────────────────────────────────────────────────────

def _generate_noise(w, h, seed, octaves, persistence, lacunarity, base_scale=6):
    """Generate 2-D fBm noise using layered interpolated random grids."""
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    amplitude = 1.0
    total_amp = 0.0

    for octave in range(octaves):
        grid_w = max(4, int(base_scale * (lacunarity ** octave)) + 2)
        grid_h = max(4, int(grid_w * h / w) + 2)

        noise = rng.randn(grid_h, grid_w).astype(np.float32)

        scale_y = h / grid_h
        scale_x = w / grid_w
        up = _zoom(noise, (scale_y, scale_x), order=3)

        # Ensure exact dimensions
        up = up[:h, :w]
        if up.shape != (h, w):
            padded = np.zeros((h, w), dtype=np.float32)
            ph, pw = min(h, up.shape[0]), min(w, up.shape[1])
            padded[:ph, :pw] = up[:ph, :pw]
            up = padded

        result += up * amplitude
        total_amp += amplitude
        amplitude *= persistence

    result /= total_amp
    result = (result - result.min()) / (result.max() - result.min() + 1e-10)
    return result


def _apply_island_mask(heightmap, seed=42):
    """Apply radial falloff with noise for irregular coastline."""
    h, w = heightmap.shape
    y = np.linspace(0, 1, h)
    x = np.linspace(0, 1, w)
    xx, yy = np.meshgrid(x, y)

    dx = (xx - 0.5) * 2.0
    dy = (yy - 0.5) * 2.0
    dist = np.sqrt(dx ** 2 + dy ** 2)

    # Add noise for irregular coast
    coast_noise = _generate_noise(w, h, seed + 50, 3, 0.5, 2.0, base_scale=4)
    dist = dist + (coast_noise - 0.5) * 0.3

    mask = 1.0 - np.clip(dist * 1.05, 0, 1) ** 1.6
    result = heightmap * 0.55 + heightmap * mask * 0.45
    result = result * mask ** 0.5

    result = (result - result.min()) / (result.max() - result.min() + 1e-10)
    return result


# ───────────────────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────────────────

def generate_terrain(seed=None):
    """
    Generate the full terrain.

    Returns
    -------
    heightmap    : ndarray (MAP_H, MAP_W) float32, 0..1
    moisture     : ndarray (MAP_H, MAP_W) float32, 0..1
    temperature  : ndarray (MAP_H, MAP_W) float32, 0..1
    biome_map    : ndarray (MAP_H, MAP_W) uint8  — biome indices
    biome_names  : list[str]                      — index → name
    """
    hs = seed if seed is not None else TERRAIN_SEED
    ms = (seed + 95) if seed is not None else MOISTURE_SEED
    ts = (seed + 201) if seed is not None else TEMPERATURE_SEED

    print("  heightmap...", end=" ", flush=True)
    heightmap = _generate_noise(MAP_W, MAP_H, hs,
                                TERRAIN_OCTAVES, TERRAIN_PERSISTENCE, TERRAIN_LACUNARITY)
    heightmap = _apply_island_mask(heightmap, hs)
    print("done.")

    print("  moisture...", end=" ", flush=True)
    moisture = _generate_noise(MAP_W, MAP_H, ms, 4, 0.5, 2.0, base_scale=5)
    print("done.")

    print("  temperature...", end=" ", flush=True)
    temperature = _generate_temperature(MAP_W, MAP_H, ts, heightmap)
    print("done.")

    # ── Biome classification (vectorized, 22 biomes) ───────────────────
    biome_names = list(BIOME_COLORS.keys())
    idx = {name: i for i, name in enumerate(biome_names)}

    bm = np.full((MAP_H, MAP_W), idx['grassland'], dtype=np.uint8)
    e = heightmap
    m = moisture
    t = temperature

    # Water
    bm[e < ELEV_DEEP_OCEAN] = idx['deep_ocean']
    bm[(e >= ELEV_DEEP_OCEAN) & (e < ELEV_OCEAN)]  = idx['ocean']
    bm[(e >= ELEV_OCEAN)     & (e < ELEV_SHALLOW)]  = idx['shallow_water']
    bm[(e >= ELEV_SHALLOW)   & (e < ELEV_BEACH)]    = idx['beach']

    # Reef: shallow water + warm + high moisture
    reef_mask = (e >= ELEV_OCEAN) & (e < ELEV_SHALLOW) & (t > TEMP_WARM) & (m > MOIST_WET)
    bm[reef_mask] = idx['reef']

    # Lowlands (beach to lowland threshold)
    low = (e >= ELEV_BEACH) & (e < ELEV_LOWLAND)

    # Cold lowlands → tundra / taiga
    bm[low & (t < TEMP_COLD)]                                  = idx['tundra']
    bm[low & (t >= TEMP_COLD) & (t < TEMP_COOL) & (m >= MOIST_MED)] = idx['taiga']
    bm[low & (t >= TEMP_COLD) & (t < TEMP_COOL) & (m < MOIST_MED)]  = idx['tundra']

    # Temperate lowlands
    bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m < MOIST_DRY)]   = idx['desert']
    bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m >= MOIST_DRY) & (m < MOIST_MED)] = idx['savanna']
    bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m >= MOIST_MED) & (m < MOIST_WET)] = idx['grassland']
    bm[low & (t >= TEMP_COOL) & (t < TEMP_HOT) & (m >= MOIST_WET)]  = idx['forest']

    # Hot lowlands → tropical / desert
    bm[low & (t >= TEMP_HOT) & (m < MOIST_DRY)]               = idx['desert']
    bm[low & (t >= TEMP_HOT) & (m >= MOIST_DRY) & (m < MOIST_MED)] = idx['savanna']
    bm[low & (t >= TEMP_HOT) & (m >= MOIST_MED)]              = idx['tropical']

    # Swamp: warm + very wet lowland
    swamp_mask = low & (m > 0.70) & (t >= TEMP_COOL)
    bm[swamp_mask] = idx['swamp']

    # River: carved channels (very low elevation in lowland areas)
    river_mask = (e >= ELEV_BEACH) & (e < ELEV_BEACH + 0.02) & (m > MOIST_WET)
    bm[river_mask] = idx['river']

    # Highlands
    hi = (e >= ELEV_LOWLAND) & (e < ELEV_HIGHLAND)
    bm[hi & (t < TEMP_COOL) & (m >= MOIST_MED)]   = idx['taiga']
    bm[hi & (t < TEMP_COOL) & (m < MOIST_MED)]    = idx['tundra']
    bm[hi & (t >= TEMP_COOL) & (m < MOIST_DRY)]   = idx['hills']
    bm[hi & (t >= TEMP_COOL) & (m >= MOIST_DRY) & (m < 0.70)] = idx['dense_forest']
    bm[hi & (t >= TEMP_COOL) & (m >= 0.70)]       = idx['swamp']

    # Mountains
    mt = (e >= ELEV_HIGHLAND) & (e < ELEV_MOUNTAIN)
    bm[mt & (m < 0.40)]  = idx['mountain']
    bm[mt & (m >= 0.40)] = idx['high_mountain']

    # Peaks → snow
    bm[(e >= ELEV_MOUNTAIN) & (e < ELEV_PEAK)] = idx['snow']

    # Extreme peaks → volcano (rare, hot + dry + very high)
    volcano_mask = (e >= ELEV_PEAK) & (t > TEMP_WARM) & (m < MOIST_DRY)
    bm[volcano_mask] = idx['volcano']
    bm[(e >= ELEV_PEAK) & ~volcano_mask] = idx['snow']

    # Crystal field: rare — high moisture + cool + highland
    crystal_mask = (e >= ELEV_HIGHLAND) & (e < ELEV_MOUNTAIN) & (m > 0.75) & (t < TEMP_COOL)
    bm[crystal_mask] = idx['crystal_field']

    print(f"  biomes classified — {len(biome_names)} types.")
    return heightmap, moisture, temperature, bm, biome_names


def _generate_temperature(w, h, seed, heightmap):
    """Temperature from latitude + noise + elevation cooling."""
    rng = np.random.RandomState(seed)

    # Latitude gradient: warm at center, cold at poles
    lat = np.abs(np.linspace(-1, 1, h))[:, np.newaxis]  # (H, 1)
    lat_temp = 1.0 - lat * 0.65  # ~0.35 at poles, 1.0 at equator

    # Add noise for variety
    temp_noise = _generate_noise(w, h, seed, 3, 0.5, 2.0, base_scale=4)

    # Elevation cooling
    elev_cool = heightmap * 0.4

    temperature = np.clip(
        lat_temp * 0.55 + temp_noise * 0.25 + 0.2 - elev_cool,
        0, 1
    ).astype(np.float32)
    return temperature


def is_land(biome_idx, biome_names):
    """True if the biome index represents land (not water)."""
    return biome_names[biome_idx] not in ('deep_ocean', 'ocean', 'shallow_water')
