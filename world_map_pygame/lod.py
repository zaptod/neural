"""
world_map_pygame/lod.py
Level-of-Detail manager — decides what to show/hide at each zoom level.

LOD 0 (zoom < 0.35): STRATEGIC
  - Region blobs (no zone borders)
  - Large region names only
  - Simplified terrain
  - Seal glow indicators

LOD 1 (0.35 ≤ zoom < 0.90): REGIONAL
  - Zone boundaries visible
  - Zone names
  - Ownership colors
  - Seal icons
  - Event markers

LOD 2 (0.90 ≤ zoom < 2.0): TACTICAL
  - Structure icons at centroids
  - Nature tinting / corruption overlay
  - God badges
  - Roads between cities
  - More detailed labels

LOD 3 (2.0 ≤ zoom < 3.5): DETAIL
  - Individual pixel-art buildings
  - Landmarks
  - Vegetation / terrain features
  - Pathways

LOD 4 (zoom ≥ 3.5): CLOSE-UP
  - Sub-district markers & labels
  - Detailed building interiors markers
  - Points of interest (NPCs, quests)
  - Full nature VFX particles
"""
from dataclasses import dataclass
from .config import get_lod


@dataclass(frozen=True)
class LODFeatures:
    """Feature flags for current LOD level."""
    level: int

    # LOD 0+
    show_terrain: bool = True
    show_regions: bool = True
    show_ocean: bool = True

    # LOD 1+
    show_zone_borders: bool = False
    show_zone_names: bool = False
    show_ownership: bool = False
    show_seals: bool = False
    show_events: bool = False

    # LOD 2+
    show_structure_icons: bool = False
    show_nature_tint: bool = False
    show_god_badges: bool = False
    show_roads: bool = False
    show_nature_names: bool = False

    # LOD 3+
    show_buildings: bool = False
    show_landmarks: bool = False
    show_vegetation: bool = False
    show_pathways: bool = False
    show_nature_vfx: bool = False

    # LOD 4+
    show_subdistricts: bool = False
    show_poi: bool = False
    show_full_vfx: bool = False
    show_building_details: bool = False


# Pre-built feature sets for each LOD level
_LOD_FEATURES = {
    0: LODFeatures(
        level=0,
        show_terrain=True,
        show_regions=True,
        show_ocean=True,
    ),
    1: LODFeatures(
        level=1,
        show_terrain=True,
        show_regions=True,
        show_ocean=True,
        show_zone_borders=True,
        show_zone_names=True,
        show_ownership=True,
        show_seals=True,
        show_events=True,
    ),
    2: LODFeatures(
        level=2,
        show_terrain=True,
        show_regions=True,
        show_ocean=True,
        show_zone_borders=True,
        show_zone_names=True,
        show_ownership=True,
        show_seals=True,
        show_events=True,
        show_structure_icons=True,
        show_nature_tint=True,
        show_god_badges=True,
        show_roads=True,
        show_nature_names=True,
    ),
    3: LODFeatures(
        level=3,
        show_terrain=True,
        show_regions=True,
        show_ocean=True,
        show_zone_borders=True,
        show_zone_names=True,
        show_ownership=True,
        show_seals=True,
        show_events=True,
        show_structure_icons=True,
        show_nature_tint=True,
        show_god_badges=True,
        show_roads=True,
        show_nature_names=True,
        show_buildings=True,
        show_landmarks=True,
        show_vegetation=True,
        show_pathways=True,
        show_nature_vfx=True,
    ),
    4: LODFeatures(
        level=4,
        show_terrain=True,
        show_regions=True,
        show_ocean=True,
        show_zone_borders=True,
        show_zone_names=True,
        show_ownership=True,
        show_seals=True,
        show_events=True,
        show_structure_icons=True,
        show_nature_tint=True,
        show_god_badges=True,
        show_roads=True,
        show_nature_names=True,
        show_buildings=True,
        show_landmarks=True,
        show_vegetation=True,
        show_pathways=True,
        show_nature_vfx=True,
        show_subdistricts=True,
        show_poi=True,
        show_full_vfx=True,
        show_building_details=True,
    ),
}


class LODManager:
    """
    Tracks current LOD level and provides feature flags.
    Smoothly transitions between LOD levels with hysteresis to prevent flickering.
    """

    HYSTERESIS = 0.05   # zoom buffer to prevent LOD flickering at boundaries

    def __init__(self):
        self._current_lod = 0
        self._features = _LOD_FEATURES[0]
        self._prev_lod = 0
        self._transition_t = 0.0   # 0→1 when transitioning between LOD

    @property
    def level(self) -> int:
        return self._current_lod

    @property
    def features(self) -> LODFeatures:
        return self._features

    @property
    def transitioning(self) -> bool:
        return self._transition_t < 1.0

    @property
    def transition_alpha(self) -> float:
        """0.0 = fully prev LOD, 1.0 = fully current LOD."""
        return min(1.0, self._transition_t)

    def update(self, zoom: float, dt: float):
        """Update LOD based on current zoom. Call every frame."""
        new_lod = get_lod(zoom)

        # Hysteresis: require a slightly larger change to switch back
        if new_lod < self._current_lod:
            from .config import LOD_THRESHOLDS
            if self._current_lod > 0:
                threshold = LOD_THRESHOLDS[self._current_lod - 1]
                if zoom > threshold - self.HYSTERESIS:
                    new_lod = self._current_lod

        if new_lod != self._current_lod:
            self._prev_lod = self._current_lod
            self._current_lod = new_lod
            self._features = _LOD_FEATURES[min(4, new_lod)]
            self._transition_t = 0.0

        # Advance transition
        if self._transition_t < 1.0:
            self._transition_t = min(1.0, self._transition_t + dt * 4.0)

    def should_show(self, feature: str) -> bool:
        """Check if a feature should be visible at current LOD."""
        return getattr(self._features, feature, False)
