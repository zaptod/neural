"""Helpers de IA para interpretar o sistema de armas v2."""

from __future__ import annotations

from nucleo.armas import get_family_spec, inferir_familia, resolver_subtipo_orbital

try:
    from nucleo.armas import get_weapon_runtime_controller
except ImportError:  # pragma: no cover - fallback defensivo
    get_weapon_runtime_controller = None


FAMILIAS_RANGED = {"arremesso", "disparo", "foco"}
FAMILIAS_LINHA = {"arremesso", "disparo", "foco"}
FAMILIAS_PRESSAO_MELEE = {"lamina", "haste", "dupla", "corrente", "hibrida"}
FAMILIAS_CURTA_DISTANCIA = {"lamina", "dupla", "hibrida", "orbital"}


def resolver_familia_arma(arma) -> str:
    """Resolve a familia canônica da arma mesmo em payload legado."""
    if arma is None:
        return "lamina"
    return (
        getattr(arma, "familia", None)
        or inferir_familia(
            getattr(arma, "tipo", ""),
            getattr(arma, "estilo", ""),
            getattr(arma, "categoria", None),
        )
    )


def arma_eh_ranged(arma) -> bool:
    return resolver_familia_arma(arma) in FAMILIAS_RANGED


def arma_dispara_em_linha(arma) -> bool:
    return resolver_familia_arma(arma) in FAMILIAS_LINHA


def obter_metricas_arma(arma, fighter=None) -> dict[str, float | str]:
    """Retorna alcance maximo/minimo/tatico padronizado para a IA."""
    familia = resolver_familia_arma(arma)
    spec = get_family_spec(familia)
    mecanica = spec.get("mecanica", {})

    alcance_max = float(
        getattr(arma, "alcance_efetivo", 0.0)
        or getattr(arma, "alcance_base", 0.0)
        or mecanica.get("alcance", 2.0)
        or 2.0
    )

    if alcance_max <= 0.0 and arma is not None and fighter is not None and get_weapon_runtime_controller:
        try:
            controller = get_weapon_runtime_controller(arma)
            alcance_max = float(controller.attack_range(fighter, arma))
        except Exception:  # pragma: no cover - fallback defensivo
            alcance_max = 2.0

    alcance_min = float(
        getattr(arma, "alcance_minimo", 0.0)
        or mecanica.get("alcance_minimo", 0.0)
        or 0.0
    )
    cadencia = float(
        getattr(arma, "velocidade_ataque", 0.0)
        or mecanica.get("cadencia", 1.0)
        or 1.0
    )

    if familia == "corrente":
        alcance_tatico = (alcance_max + max(alcance_min, alcance_max * 0.40)) / 2.0
    elif familia == "arremesso":
        alcance_tatico = max(alcance_min * 1.10, alcance_max * 0.72)
    elif familia == "disparo":
        alcance_tatico = max(alcance_min * 1.15, alcance_max * 0.88)
    elif familia == "foco":
        alcance_tatico = max(alcance_min + 0.25, alcance_max * 0.80)
    elif familia == "orbital":
        subtipo_orbital = resolver_subtipo_orbital(arma)
        if subtipo_orbital == "escudo":
            alcance_tatico = max(1.15, min(2.1, alcance_max * 0.72))
        elif subtipo_orbital == "drone":
            alcance_tatico = max(1.65, alcance_max * 1.02)
        elif subtipo_orbital == "laminas":
            alcance_tatico = max(1.35, alcance_max * 0.84)
        else:
            alcance_tatico = max(1.55, alcance_max * 0.94)
    elif familia == "dupla":
        alcance_tatico = max(0.75, alcance_min + 0.10, alcance_max * 0.72)
    elif familia == "haste":
        alcance_tatico = max(alcance_min + 0.15, alcance_max * 0.86)
    elif familia == "hibrida":
        forma_atual = int(getattr(arma, "forma_atual", 1) or 1)
        bias = 0.78 if forma_atual == 1 else 0.98
        alcance_tatico = max(alcance_min + 0.12, alcance_max * bias)
    else:
        alcance_tatico = max(alcance_min + 0.12, alcance_max * 0.82)

    return {
        "familia": familia,
        "alcance_max": max(0.8, alcance_max),
        "alcance_min": max(0.0, alcance_min),
        "alcance_tatico": max(0.8, alcance_tatico),
        "cadencia": max(0.1, cadencia),
    }
