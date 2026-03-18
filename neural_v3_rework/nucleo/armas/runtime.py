"""Controladores de runtime por familia de arma."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponRuntimeController:
    familia: str
    handler: str
    animation_key: str
    allows_reposition_attack: bool = False
    cooldown_mult: float = 1.0
    range_bias: float = 1.08

    def attack_range(self, fighter, arma) -> float:
        alcance = float(getattr(arma, "alcance_efetivo", 0.0) or 0.0)
        if alcance > 0:
            return alcance * self.range_bias

        fallback = {
            "corrente": fighter.raio_fisico * 4.0,
            "dupla": fighter.raio_fisico * 3.2,
            "lamina": fighter.raio_fisico * 2.6,
            "haste": fighter.raio_fisico * 3.0,
            "arremesso": 10.0,
            "disparo": 14.0,
            "orbital": fighter.raio_fisico * 3.0,
            "foco": 7.0,
            "hibrida": fighter.raio_fisico * 3.2,
        }
        return fallback.get(self.familia, fighter.raio_fisico * 3.0)

    def base_cooldown(self, fighter, arma) -> float:
        perfil = getattr(arma, "perfil_mecanico", {}) or {}
        base = max(0.12, perfil.get("startup", 0.12) + perfil.get("ativo", 0.08) + perfil.get("recovery", 0.18))
        return base * self.cooldown_mult


_FAMILY_RUNTIME_MAP = {
    "lamina": WeaponRuntimeController("lamina", "reta", "Reta", cooldown_mult=1.08),
    "haste": WeaponRuntimeController("haste", "reta", "Reta", cooldown_mult=1.16, range_bias=1.10),
    "dupla": WeaponRuntimeController("dupla", "dupla", "Dupla", cooldown_mult=0.98),
    "corrente": WeaponRuntimeController("corrente", "corrente", "Corrente", cooldown_mult=1.24, range_bias=0.98),
    "arremesso": WeaponRuntimeController("arremesso", "arremesso", "Arremesso", allows_reposition_attack=True, cooldown_mult=1.08, range_bias=0.98),
    "disparo": WeaponRuntimeController("disparo", "disparo", "Arco", allows_reposition_attack=True, cooldown_mult=1.22, range_bias=0.98),
    "orbital": WeaponRuntimeController("orbital", "orbital", "Orbital", cooldown_mult=1.08, range_bias=1.0),
    "foco": WeaponRuntimeController("foco", "foco", "Mágica", cooldown_mult=1.16, range_bias=1.0),
    "hibrida": WeaponRuntimeController("hibrida", "transformavel", "Transformável", cooldown_mult=1.10, range_bias=1.0),
}


def get_weapon_runtime_controller(arma) -> WeaponRuntimeController:
    familia = getattr(arma, "familia", None) or "lamina"
    return _FAMILY_RUNTIME_MAP.get(familia, _FAMILY_RUNTIME_MAP["lamina"])
