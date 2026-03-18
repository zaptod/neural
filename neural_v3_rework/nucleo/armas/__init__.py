"""API publica do sistema de armas v2."""

from .catalogo import FAMILIAS_ARMA_V2, get_family_spec, legacy_type_from_family
from .migracao import construir_schema_arma, corrigir_texto_legado, inferir_familia, normalizar_percentual
from .runtime import WeaponRuntimeController, get_weapon_runtime_controller

__all__ = [
    "FAMILIAS_ARMA_V2",
    "get_family_spec",
    "legacy_type_from_family",
    "construir_schema_arma",
    "corrigir_texto_legado",
    "inferir_familia",
    "normalizar_percentual",
    "WeaponRuntimeController",
    "get_weapon_runtime_controller",
]
