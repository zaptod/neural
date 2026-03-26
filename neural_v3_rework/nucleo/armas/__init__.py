"""API publica do sistema de armas v2."""

from __future__ import annotations

import unicodedata

from .catalogo import FAMILIAS_ARMA_V2, get_family_spec, legacy_type_from_family
from .migracao import construir_schema_arma, corrigir_texto_legado, inferir_familia, normalizar_percentual
from .runtime import WeaponRuntimeController, get_weapon_runtime_controller


def _texto_norm_arma(valor) -> str:
    texto = str(valor or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.lower().split())


def resolver_subtipo_orbital(arma) -> str:
    """Resolve o subtipo canonico de armas orbitais.

    A familia orbital hoje suporta quatro papeis taticos:
    - ``escudo``: bloqueio, peel e controle de proximidade
    - ``drone``: pressao e artilharia orbital
    - ``laminas``: agressao giratoria corpo a corpo
    - ``orbes``: controle misto e magia de pressao
    """
    if arma is None:
        return "orbes"

    subtipo = _texto_norm_arma(getattr(arma, "subtipo", ""))
    if subtipo in {"escudo", "drone", "laminas", "orbes"}:
        return subtipo

    estilo = _texto_norm_arma(getattr(arma, "estilo", ""))
    nome = _texto_norm_arma(getattr(arma, "nome", ""))
    texto = f"{subtipo} {estilo} {nome}"

    if any(token in texto for token in ("escudo", "bastiao", "barreira", "guardiao", "defensivo", "santuario")):
        return "escudo"
    if any(token in texto for token in ("drone", "sentinela", "artilharia", "colmeia", "ofensivo")):
        return "drone"
    if any(token in texto for token in ("lamina", "laminas", "coroa", "cortante", "shard", "gume")):
        return "laminas"
    return "orbes"

__all__ = [
    "FAMILIAS_ARMA_V2",
    "get_family_spec",
    "legacy_type_from_family",
    "construir_schema_arma",
    "corrigir_texto_legado",
    "inferir_familia",
    "normalizar_percentual",
    "resolver_subtipo_orbital",
    "WeaponRuntimeController",
    "get_weapon_runtime_controller",
]
