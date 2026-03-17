"""
NEURAL FIGHTS â€” nucleo/lutador/physics_mixin.py  [D03/D04 Sprint 8]
==================================================================
PhysicsMixin: fÃ­sica de movimento, dash trail, orbes, consulta de posiÃ§Ã£o.

Imports inline eliminados (D04): normalizar_angulo, HITBOX_PROFILES no topo.
"""

import math
import random
import logging

from utilitarios.config import PPM, GRAVIDADE_Z, ATRITO
from nucleo.physics import normalizar_angulo
from nucleo.hitbox import HITBOX_PROFILES

_log = logging.getLogger("entities")


class PhysicsMixin:
    """Mixin com fÃ­sica de movimento e helpers posicionais."""

    # ------------------------------------------------------------------
    # FÃ­sica
    # ------------------------------------------------------------------

    def aplicar_fisica(self, dt):
        """Aplica fÃ­sica de movimento."""
        vel_mult = self.slow_fator * self.mod_velocidade

        if self.z > 0 or self.vel_z > 0:
            self.vel_z -= GRAVIDADE_Z * dt
            self.z += self.vel_z * dt
            if self.z < 0:
                self.z = 0
                self.vel_z = 0

        fr = ATRITO if self.z == 0 else ATRITO * 0.2
        self.vel[0] -= self.vel[0] * fr * dt
        self.vel[1] -= self.vel[1] * fr * dt
        self.pos[0] += self.vel[0] * vel_mult * dt
        self.pos[1] += self.vel[1] * vel_mult * dt

    def executar_movimento(self, dt, distancia):
        """Executa movimento baseado na aÃ§Ã£o da IA â€” v8.0 com comportamento humano."""
        acao = self.brain.acao_atual
        acc = 45.0 * self.mod_velocidade
        if self.modo_adrenalina:
            acc = 70.0 * self.mod_velocidade

        for buff in self.buffs_ativos:
            acc *= buff.buff_velocidade

        if hasattr(self.brain, 'ritmo_combate'):
            acc *= self.brain.ritmo_combate

        if hasattr(self.brain, 'momentum'):
            if self.brain.momentum > 0.3:
                acc *= 1.0 + self.brain.momentum * 0.15
            elif self.brain.momentum < -0.3:
                acc *= 1.0 + self.brain.momentum * 0.1

        mx, my = 0, 0
        rad = math.radians(self.angulo_olhar)

        if acao in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "APROXIMAR", "CONTRA_ATAQUE", "PRESSIONAR"]:
            mx = math.cos(rad)
            my = math.sin(rad)
            mult = {
                "MATAR": 1.0, "ESMAGAR": 0.85, "ATAQUE_RAPIDO": 1.25,
                "APROXIMAR": 1.0, "CONTRA_ATAQUE": 1.4, "PRESSIONAR": 1.1
            }.get(acao, 1.0)
            mx *= mult
            my *= mult
            if hasattr(self.brain, 'micro_ajustes'):
                mx += random.uniform(-0.05, 0.05)
                my += random.uniform(-0.05, 0.05)

        elif acao == "COMBATE":
            mx = math.cos(rad) * 0.6
            my = math.sin(rad) * 0.6
            chance_strafe = 0.35 if "ESPACAMENTO_MESTRE" in self.brain.tracos else 0.3
            if random.random() < chance_strafe:
                strafe_rad = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
                strafe_mult = random.uniform(0.25, 0.4)
                mx += math.cos(strafe_rad) * strafe_mult
                my += math.sin(strafe_rad) * strafe_mult

        elif acao in ["RECUAR", "FUGIR"]:
            mx = -math.cos(rad)
            my = -math.sin(rad)
            if acao == "FUGIR":
                mx *= 1.3
                my *= 1.3
            if random.random() < 0.3:
                lateral = random.choice([-1, 1]) * self.brain.dir_circular
                rad_lat = math.radians(self.angulo_olhar + (30 * lateral))
                mx += math.cos(rad_lat) * 0.3
                my += math.sin(rad_lat) * 0.3

        elif acao == "DESVIO":
            rad_lat = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
            mx = math.cos(rad_lat) * 1.2
            my = math.sin(rad_lat) * 1.2
            mx -= math.cos(rad) * 0.3
            my -= math.sin(rad) * 0.3

        elif acao == "CIRCULAR":
            rad_lat = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
            circ_mult = random.uniform(0.6, 0.95)
            mx = math.cos(rad_lat) * circ_mult
            my = math.sin(rad_lat) * circ_mult
            if random.random() < 0.12:
                mx *= 0.3
                my *= 0.3
            if distancia < 2.5:
                mx -= math.cos(rad) * 0.35
                my -= math.sin(rad) * 0.35
            elif distancia > 4.0:
                mx += math.cos(rad) * 0.2
                my += math.sin(rad) * 0.2
            elif random.random() < 0.4:
                mx += math.cos(rad) * 0.15
                my += math.sin(rad) * 0.15

        elif acao == "FLANQUEAR":
            angulo_flank = 50 + random.uniform(-10, 10)
            rad_f = math.radians(self.angulo_olhar + (angulo_flank * self.brain.dir_circular))
            mx = math.cos(rad_f)
            my = math.sin(rad_f)

        elif acao == "APROXIMAR_LENTO":
            mx = math.cos(rad) * 0.55
            my = math.sin(rad) * 0.55
            if random.random() < 0.2:
                rad_lat = math.radians(self.angulo_olhar + (90 * random.choice([-1, 1])))
                mx += math.cos(rad_lat) * 0.15
                my += math.sin(rad_lat) * 0.15

        elif acao == "POKE":
            if random.random() < 0.6:
                mx = math.cos(rad) * 0.8
                my = math.sin(rad) * 0.8
            else:
                mx = -math.cos(rad) * 0.4
                my = -math.sin(rad) * 0.4

        elif acao == "BLOQUEAR":
            if random.random() < 0.4 and distancia > 2.5:
                strafe_rad = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
                mx = math.cos(strafe_rad) * 0.2
                my = math.sin(strafe_rad) * 0.2

        elif acao == "ATAQUE_AEREO":
            mx = math.cos(rad) * 0.8
            my = math.sin(rad) * 0.8

        elif acao == "PRESSIONAR_CONTINUO":
            mx = math.cos(rad) * 1.1
            my = math.sin(rad) * 1.1
            if random.random() < 0.25:
                rad_lat = math.radians(self.angulo_olhar + (30 * self.brain.dir_circular))
                mx += math.cos(rad_lat) * 0.2
                my += math.sin(rad_lat) * 0.2

        # Sistema de pulos
        if "SALTADOR" in self.brain.tracos and self.z == 0:
            chance_pulo = 0.08
            if distancia < 3.0:
                chance_pulo = 0.12
            if acao in ["RECUAR", "FUGIR"]:
                chance_pulo = 0.15
            if random.random() < chance_pulo:
                self.vel_z = random.uniform(10.0, 14.0)

        elif acao in ["RECUAR", "FUGIR"] and self.z == 0:
            chance = 0.03
            if self.brain is not None and self.brain.medo > 0.5:
                chance = 0.06
            if random.random() < chance:
                self.vel_z = random.uniform(9.0, 12.0)

        ofensivos = ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "CONTRA_ATAQUE"]
        if acao in ofensivos and 3.5 < distancia < 7.0 and self.z == 0:
            chance = 0.025
            if "ACROBATA" in self.brain.tracos:
                chance = 0.05
            if random.random() < chance:
                self.vel_z = random.uniform(12.0, 15.0)
                self.modo_ataque_aereo = True

        if self.z == 0 and distancia < 5.0 and random.random() < 0.005:
            self.vel_z = random.uniform(8.0, 11.0)

        # MEL-10 fix: aÃ§Ã£o desconhecida / NEUTRO â†’ aproxima levemente
        if mx == 0 and my == 0 and acao != "BLOQUEAR":
            mx = math.cos(rad) * 0.3
            my = math.sin(rad) * 0.3

        self.vel[0] += mx * acc * dt
        self.vel[1] += my * acc * dt

    # ------------------------------------------------------------------
    # Trail / orbes
    # ------------------------------------------------------------------

    def _atualizar_dash_trail(self, dt):
        """Fade do trail de dash."""
        for i, (x, y, alpha) in enumerate(self.dash_trail):
            self.dash_trail[i] = (x, y, alpha - dt * 3)
        self.dash_trail = [(x, y, a) for x, y, a in self.dash_trail if a > 0]

    def _atualizar_orbes(self, dt):
        """Atualiza orbes mÃ¡gicos e remove os inativos."""
        for orbe in self.buffer_orbes:
            orbe.atualizar(dt)
        self.buffer_orbes = [o for o in self.buffer_orbes if o.ativo]

    # ------------------------------------------------------------------
    # Consultas de posiÃ§Ã£o
    # ------------------------------------------------------------------

    def get_pos_ponteira_arma(self):
        """Retorna posiÃ§Ã£o da ponta da arma."""
        arma = self.dados.arma_obj
        if not arma:
            return None

        if any(t in arma.tipo for t in ["Orbital", "Arremesso", "MÃ¡gica"]):
            return None

        rad = math.radians(self.angulo_arma_visual)
        ax, ay = int(self.pos[0] * PPM), int(self.pos[1] * PPM)

        _perfil = HITBOX_PROFILES.get(arma.tipo, HITBOX_PROFILES.get("Reta", {}))
        _raio_px = self.raio_fisico * PPM * self.fator_escala
        _alcance = _raio_px * _perfil.get("range_mult", 2.0)
        cabo_px   = int(_alcance * 0.30)
        lamina_px = int(_alcance * 0.70)

        xi = ax + math.cos(rad) * cabo_px
        yi = ay + math.sin(rad) * cabo_px
        xf = ax + math.cos(rad) * (cabo_px + lamina_px)
        yf = ay + math.sin(rad) * (cabo_px + lamina_px)
        return (xi, yi), (xf, yf)

