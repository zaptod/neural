"""
NEURAL FIGHTS — core/fighter/weapons_mixin.py  [D03/D04 Sprint 8]
==================================================================
WeaponsMixin: ataques físicos, sistemas de arma por tipo v15.0.

Imports inline eliminados (D04): ArmaProjetil, FlechaProjetil, OrbeMagico,
Projetil, AreaEffect, Beam, Buff, Summon, Trap, Transform, Channel,
AudioManager, MagicVFXManager, get_element_from_skill,
get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES no topo.
"""

import math
import random
import logging

from utils.balance_config import (
    ESTAMINA_CUSTO_SKILL_MULT, ESTAMINA_CUSTO_SKILL_MULT2,
    CD_ARMA_MAX_RATIO, CD_ARMA_MAX_ABSOLUTO,
)
from core.combat import (
    ArmaProjetil, FlechaProjetil, OrbeMagico,
    Projetil, AreaEffect, Beam, Buff, Summon, Trap, Transform, Channel,
)
from effects.audio import AudioManager
from effects.weapon_animations import (
    get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES,
)
from core.hitbox import HITBOX_PROFILES

_log = logging.getLogger("entities")

# VFX importado com guard para evitar crash em testes headless
try:
    from effects.magic_vfx import MagicVFXManager, get_element_from_skill as _get_elem
    _HAS_VFX = True
except ImportError:
    _HAS_VFX = False
    MagicVFXManager = None
    _get_elem = None


def _vfx_chargeup(nome_skill, data, pos, classe_nome):
    """Helper de chargeup VFX — não lança exceção se VFX indisponível."""
    if not _HAS_VFX:
        return
    try:
        _vfx = MagicVFXManager.get_instance()
        if not _vfx:
            return
        _elem = _get_elem(nome_skill, data)
        _tipo_sk = data.get("tipo", "")
        _dano = max(data.get("dano", 0), data.get("dano_maximo", 0))
        _cd = data.get("cooldown", 3.0)
        _intens = min(3.0, max(0.7, (_dano / 18.0 + _cd / 6.0) * 0.65))
        if _tipo_sk in ("BUFF", "TRANSFORM", "SUMMON"):
            _intens = max(1.4, _intens)
        _dur_map = {"CHANNEL": 0.90, "TRANSFORM": 0.70, "SUMMON": 0.70,
                    "AREA": 0.55, "BUFF": 0.45, "PROJETIL": 0.30, "BEAM": 0.30}
        _dur = _dur_map.get(_tipo_sk, 0.40)
        _cx, _cy = pos[0] * 50, pos[1] * 50
        _vfx.spawn_chargeup(_cx, _cy, _elem, _dur, _intens)
        if _tipo_sk in ("BUFF", "TRANSFORM"):
            _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.80)
        elif _tipo_sk == "SUMMON":
            _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.65)
            _vfx.spawn_aura(_cx, _cy, 40, _elem, _intens * 0.5)
        elif _tipo_sk == "AREA" and _dano > 30:
            _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.55)
    except Exception as e:
        _log.debug("VFX chargeup error: %s", e)


class WeaponsMixin:
    """Mixin com toda a lógica de ataques e disparo de projéteis."""

    # ==================================================================
    # Usar skills
    # ==================================================================

    def usar_skill_arma(self, skill_idx=None):
        """Usa a skill equipada na arma."""
        if getattr(self, 'silenciado_timer', 0) > 0:
            return False

        if skill_idx is not None and skill_idx < len(self.skills_arma):
            skill_info = self.skills_arma[skill_idx]
        elif self.skills_arma:
            skill_info = self.skills_arma[self.skill_atual_idx]
        else:
            return False

        nome_skill = skill_info["nome"]
        if nome_skill == "Nenhuma":
            return False

        if self.cd_skills.get(nome_skill, 0) > 0:
            return False

        data = skill_info["data"]
        tipo = data.get("tipo", "NADA")

        custo_real = skill_info["custo"]
        if "Mago" in self.classe_nome:
            custo_real *= ESTAMINA_CUSTO_SKILL_MULT

        for buff in self.buffs_ativos:
            if getattr(buff, 'custo_mana_metade', False):
                custo_real *= 0.5
                break

        passiva = self.arma_passiva or {}
        if passiva.get("efeito") == "no_mana_cost":
            if random.random() < passiva.get("valor", 0) / 100.0:
                custo_real = 0

        custo_vida = data.get("custo_vida", 0) or data.get("custo_vida_percent", 0) * self.vida_max
        if custo_vida > 0:
            if self.vida <= custo_vida:
                return False
            self.vida -= custo_vida

        if self.mana < custo_real:
            return False

        self.mana -= custo_real

        _vfx_chargeup(nome_skill, data, self.pos, self.classe_nome)

        cd = data["cooldown"]
        if passiva.get("efeito") == "cooldown":
            cd *= (1 - passiva.get("valor", 0) / 100.0)

        for buff in self.buffs_ativos:
            if getattr(buff, 'sem_cooldown', False):
                cd = 0
                break

        self.cd_skills[nome_skill] = cd
        tempo_cast = data.get("tempo_cast", None)
        if tempo_cast is not None:
            self.cd_skill_arma = max(0.05, tempo_cast)
        else:
            self.cd_skill_arma = min(cd * CD_ARMA_MAX_RATIO, CD_ARMA_MAX_ABSOLUTO)

        rad = math.radians(self.angulo_olhar)
        spawn_x = self.pos[0] + math.cos(rad) * 0.6
        spawn_y = self.pos[1] + math.sin(rad) * 0.6

        audio = AudioManager.get_instance()

        if tipo == "PROJETIL":
            if audio:
                audio.play_skill("PROJETIL", nome_skill, self.pos[0], phase="cast")
            multi = data.get("multi_shot", 1)
            if multi > 1:
                spread = 30
                for i in range(multi):
                    ang_offset = -spread / 2 + (spread / (multi - 1)) * i
                    p = Projetil(nome_skill, spawn_x, spawn_y, self.angulo_olhar + ang_offset, self)
                    self.buffer_projeteis.append(p)
            else:
                p = Projetil(nome_skill, spawn_x, spawn_y, self.angulo_olhar, self)
                self.buffer_projeteis.append(p)
            if data["dano"] > 20:
                self.vel[0] -= math.cos(rad) * 5.0
                self.vel[1] -= math.sin(rad) * 5.0

        elif tipo == "AREA":
            if audio:
                audio.play_skill("AREA", nome_skill, self.pos[0], phase="cast")
            self.buffer_areas.append(AreaEffect(nome_skill, self.pos[0], self.pos[1], self))

        elif tipo == "DASH":
            if audio:
                audio.play_skill("DASH", nome_skill, self.pos[0], phase="cast")
            dist = data.get("distancia", 4.0)
            dano = data.get("dano", 0)
            self.pos[0] += math.cos(rad) * dist
            self.pos[1] += math.sin(rad) * dist
            self.dash_timer = 0.25
            for i in range(5):
                self.dash_trail.append((
                    self.pos[0] - math.cos(rad) * dist * (i / 5),
                    self.pos[1] - math.sin(rad) * dist * (i / 5),
                    1.0 - i * 0.2
                ))
            if dano > 0:
                area = AreaEffect(nome_skill, self.pos[0], self.pos[1], self)
                area.dano = dano
                area.raio = 1.5
                self.buffer_areas.append(area)
            dano_chegada = data.get("dano_chegada", 0)
            if dano_chegada > 0:
                area_chegada = AreaEffect(nome_skill, self.pos[0], self.pos[1], self)
                area_chegada.dano = dano_chegada
                area_chegada.raio = 1.0
                area_chegada.duracao = 0.15
                self.buffer_areas.append(area_chegada)
            if data.get("invencivel"):
                self.invencivel_timer = 0.3

        elif tipo == "BUFF":
            if audio:
                audio.play_skill("BUFF", nome_skill, self.pos[0], phase="cast")
            if data.get("cura"):
                self.vida = min(self.vida_max, self.vida + data["cura"])
            self.buffs_ativos.append(Buff(nome_skill, self))

        elif tipo == "BEAM":
            if audio:
                audio.play_skill("BEAM", nome_skill, self.pos[0], phase="cast")
            alcance = data.get("alcance", 8.0)
            end_x = self.pos[0] + math.cos(rad) * alcance
            end_y = self.pos[1] + math.sin(rad) * alcance
            self.buffer_beams.append(Beam(nome_skill, self.pos[0], self.pos[1], end_x, end_y, self))

        elif tipo == "SUMMON":
            if audio:
                audio.play_skill("SUMMON", nome_skill, self.pos[0], phase="cast")
            summon_x = self.pos[0] + math.cos(rad) * 1.5
            summon_y = self.pos[1] + math.sin(rad) * 1.5
            summon = Summon(nome_skill, summon_x, summon_y, self)
            if not hasattr(self, 'buffer_summons'):
                self.buffer_summons = []
            self.buffer_summons.append(summon)

        elif tipo == "TRAP":
            if audio:
                audio.play_skill("TRAP", nome_skill, self.pos[0], phase="cast")
            trap_x = self.pos[0] + math.cos(rad) * 2.0
            trap_y = self.pos[1] + math.sin(rad) * 2.0
            trap = Trap(nome_skill, trap_x, trap_y, self)
            if not hasattr(self, 'buffer_traps'):
                self.buffer_traps = []
            self.buffer_traps.append(trap)

        elif tipo == "TRANSFORM":
            if audio:
                audio.play_skill("TRANSFORM", nome_skill, self.pos[0], phase="cast")
            self.transformacao_ativa = Transform(nome_skill, self)

        elif tipo == "CHANNEL":
            if audio:
                audio.play_skill("CHANNEL", nome_skill, self.pos[0], phase="cast")
            channel = Channel(nome_skill, self)
            if not hasattr(self, 'buffer_channels'):
                self.buffer_channels = []
            self.buffer_channels.append(channel)

        return True

    def usar_skill_classe(self, skill_nome):
        """Usa uma skill de classe específica."""
        if getattr(self, 'silenciado_timer', 0) > 0:
            return False

        skill_info = next((sk for sk in self.skills_classe if sk["nome"] == skill_nome), None)
        if not skill_info:
            return False

        if self.cd_skills.get(skill_nome, 0) > 0:
            return False

        data = skill_info["data"]
        tipo = data.get("tipo", "NADA")
        custo = skill_info["custo"]

        if "Mago" in self.classe_nome:
            custo *= 0.8

        for buff in self.buffs_ativos:
            if getattr(buff, 'custo_mana_metade', False):
                custo *= 0.5
                break

        custo_vida = data.get("custo_vida", 0) or data.get("custo_vida_percent", 0) * self.vida_max
        if custo_vida > 0:
            if self.vida <= custo_vida:
                return False
            self.vida -= custo_vida

        if self.mana < custo:
            return False

        self.mana -= custo

        _vfx_chargeup(skill_nome, data, self.pos, self.classe_nome)

        cd = data.get("cooldown", 5.0)
        for buff in self.buffs_ativos:
            if getattr(buff, 'sem_cooldown', False):
                cd = 0
                break

        self.cd_skills[skill_nome] = cd

        rad = math.radians(self.angulo_olhar)
        spawn_x = self.pos[0] + math.cos(rad) * 0.6
        spawn_y = self.pos[1] + math.sin(rad) * 0.6
        audio = AudioManager.get_instance()

        if tipo == "PROJETIL":
            if audio:
                audio.play_skill("PROJETIL", skill_nome, self.pos[0], phase="cast")
            multi = data.get("multi_shot", 1)
            if multi > 1:
                spread = 30
                for i in range(multi):
                    ang_offset = -spread / 2 + (spread / (multi - 1)) * i
                    p = Projetil(skill_nome, spawn_x, spawn_y, self.angulo_olhar + ang_offset, self)
                    self.buffer_projeteis.append(p)
            else:
                self.buffer_projeteis.append(Projetil(skill_nome, spawn_x, spawn_y, self.angulo_olhar, self))

        elif tipo == "AREA":
            if audio:
                audio.play_skill("AREA", skill_nome, self.pos[0], phase="cast")
            self.buffer_areas.append(AreaEffect(skill_nome, self.pos[0], self.pos[1], self))

        elif tipo == "DASH":
            if audio:
                audio.play_skill("DASH", skill_nome, self.pos[0], phase="cast")
            dist = data.get("distancia", 4.0)
            dano = data.get("dano", 0)
            self.pos[0] += math.cos(rad) * dist
            self.pos[1] += math.sin(rad) * dist
            for i in range(5):
                self.dash_trail.append((
                    self.pos[0] - math.cos(rad) * dist * (i / 5),
                    self.pos[1] - math.sin(rad) * dist * (i / 5),
                    1.0 - i * 0.2
                ))
            if dano > 0:
                area = AreaEffect(skill_nome, self.pos[0], self.pos[1], self)
                area.dano = dano
                area.raio = 1.5
                self.buffer_areas.append(area)
            if data.get("invencivel"):
                self.invencivel_timer = 0.3

        elif tipo == "BUFF":
            if audio:
                audio.play_skill("BUFF", skill_nome, self.pos[0], phase="cast")
            if data.get("cura"):
                self.vida = min(self.vida_max, self.vida + data["cura"])
            self.buffs_ativos.append(Buff(skill_nome, self))

        elif tipo == "BEAM":
            if audio:
                audio.play_skill("BEAM", skill_nome, self.pos[0], phase="cast")
            alcance = data.get("alcance", 8.0)
            end_x = self.pos[0] + math.cos(rad) * alcance
            end_y = self.pos[1] + math.sin(rad) * alcance
            self.buffer_beams.append(Beam(skill_nome, self.pos[0], self.pos[1], end_x, end_y, self))

        elif tipo == "SUMMON":
            if audio:
                audio.play_skill("SUMMON", skill_nome, self.pos[0], phase="cast")
            summon_x = self.pos[0] + math.cos(rad) * 1.5
            summon_y = self.pos[1] + math.sin(rad) * 1.5
            summon = Summon(skill_nome, summon_x, summon_y, self)
            if not hasattr(self, 'buffer_summons'):
                self.buffer_summons = []
            self.buffer_summons.append(summon)

        elif tipo == "TRAP":
            if audio:
                audio.play_skill("TRAP", skill_nome, self.pos[0], phase="cast")
            trap_x = self.pos[0] + math.cos(rad) * 2.0
            trap_y = self.pos[1] + math.sin(rad) * 2.0
            trap = Trap(skill_nome, trap_x, trap_y, self)
            if not hasattr(self, 'buffer_traps'):
                self.buffer_traps = []
            self.buffer_traps.append(trap)

        elif tipo == "TRANSFORM":
            if audio:
                audio.play_skill("TRANSFORM", skill_nome, self.pos[0], phase="cast")
            if not hasattr(self, 'transformacao_ativa'):
                self.transformacao_ativa = None
            self.transformacao_ativa = Transform(skill_nome, self)

        elif tipo == "CHANNEL":
            if audio:
                audio.play_skill("CHANNEL", skill_nome, self.pos[0], phase="cast")
            channel = Channel(skill_nome, self)
            if not hasattr(self, 'channel_ativo'):
                self.channel_ativo = None
            self.channel_ativo = channel

        return True

    # ==================================================================
    # Sistema de ataques físicos v15.0
    # ==================================================================

    def executar_ataques(self, dt, distancia, inimigo):
        """Executa ataques físicos — sistema v15.0."""
        self.cooldown_ataque -= dt

        arma_tipo = self.dados.arma_obj.tipo if self.dados.arma_obj else "Reta"
        arma_estilo = getattr(self.dados.arma_obj, 'estilo', '') if self.dados.arma_obj else ''
        is_orbital = self.dados.arma_obj and "Orbital" in arma_tipo

        if arma_tipo == "Corrente":
            self._executar_ataques_corrente(dt, distancia, inimigo, arma_estilo)
            return
        if arma_tipo == "Dupla":
            self._executar_ataques_dupla(dt, distancia, inimigo, arma_estilo)
            return
        if arma_tipo == "Reta":
            self._executar_ataques_reta(dt, distancia, inimigo, arma_estilo)
            return
        if is_orbital:
            self._executar_ataques_orbital(dt, distancia, inimigo, arma_estilo)
            return
        if arma_tipo in ("Transformável", "Transformavel"):
            self._executar_ataques_transformavel(dt, distancia, inimigo, arma_estilo)
            return

        anim_manager = get_weapon_animation_manager()
        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 2.5
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )
        transform = anim_manager.get_weapon_transform(
            id(self), arma_tipo, self.angulo_olhar, weapon_tip, dt, weapon_style=arma_estilo
        )
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        else:
            self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        if not self.atacando and self.cooldown_ataque <= 0:
            acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR",
                               "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
            deve_atacar = False

            try:
                profile_hitbox = HITBOX_PROFILES.get(arma_tipo, HITBOX_PROFILES.get("Reta", {}))
                alcance_base = self.raio_fisico * profile_hitbox.get("range_mult", 2.0)
                alcance_ataque = alcance_base * 1.1
            except Exception:
                alcance_ataque = self.raio_fisico * 3.0

            if arma_tipo == "Arco":
                alcance_ataque = 14.0
            elif arma_tipo == "Arremesso":
                alcance_ataque = 10.0
            elif arma_tipo == "Mágica":
                alcance_ataque = 7.0

            if self.brain.acao_atual in acoes_ofensivas and distancia < alcance_ataque:
                deve_atacar = True
            if self.brain.acao_atual == "POKE" and abs(distancia - self.alcance_ideal) < 1.5:
                deve_atacar = True
            if self.modo_ataque_aereo and distancia < 2.0:
                deve_atacar = True

            if arma_tipo in ["Arremesso", "Arco"] and distancia < alcance_ataque:
                if self.brain.acao_atual in ["RECUAR", "FUGIR", "APROXIMAR"]:
                    if random.random() < 0.25:
                        deve_atacar = True

            if deve_atacar and abs(self.z - inimigo.z) < 1.5:
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()

                profile = WEAPON_PROFILES.get(arma_tipo, WEAPON_PROFILES["Reta"])
                self.timer_animacao = profile.total_time
                anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=arma_estilo)

                if arma_tipo == "Arremesso":
                    self._disparar_arremesso(inimigo)
                elif arma_tipo == "Arco":
                    self._disparar_flecha(inimigo)
                elif arma_tipo == "Mágica":
                    self._disparar_orbes(inimigo)

                base_cd = 0.5 + random.random() * 0.5
                if arma_tipo == "Arremesso":
                    self.throw_consecutive += 1
                    base_cd = max(0.55, 1.05 - self.throw_consecutive * 0.04) + random.random() * 0.35
                    if self.throw_consecutive >= 5:
                        self.throw_consecutive = 0
                elif arma_tipo == "Arco":
                    charge_bonus = min(0.3, self.bow_charge * 0.2) if self.bow_charge > 0 else 0
                    base_cd = max(0.85, 1.25 - charge_bonus * 0.7) + random.random() * 0.35
                    self.bow_charge = 0.0
                    self.bow_charging = False
                elif arma_tipo == "Mágica":
                    base_cd = 1.35 + random.random() * 0.65

                if "Assassino" in self.classe_nome or "Ninja" in self.classe_nome:
                    base_cd *= 0.7
                elif "Colosso" in self.brain.arquetipo:
                    base_cd *= 1.3

                vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
                self.cooldown_ataque = base_cd / vel_ataque

    # ==================================================================
    # Sistemas dedicados por tipo de arma
    # ==================================================================

    def _atualizar_chain_state(self, dt, distancia):
        """Atualiza estados persistentes de arma v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return
        tipo = arma.tipo
        estilo = getattr(arma, 'estilo', '')

        if tipo == "Corrente":
            if "Mangual" in estilo or "Flail" in estilo:
                self.chain_momentum = max(0, self.chain_momentum - dt * 0.15)
            elif estilo == "Kusarigama":
                if self.chain_combo_timer > 0:
                    self.chain_combo_timer -= dt
                    if self.chain_combo_timer <= 0:
                        self.chain_combo = 0
            elif estilo == "Chicote":
                if self.chain_whip_stacks > 0:
                    self.chain_whip_stacks = max(0, self.chain_whip_stacks - dt * 0.5)
            elif estilo == "Meteor Hammer":
                if self.chain_spinning:
                    self.chain_spin_speed = min(3.0, self.chain_spin_speed + dt * 0.3)
                    self.chain_spin_dmg_timer = max(0, self.chain_spin_dmg_timer - dt)
                else:
                    self.chain_spin_speed = max(0, self.chain_spin_speed - dt * 2.0)
            if self.chain_pull_timer > 0:
                self.chain_pull_timer -= dt
                if self.chain_pull_timer <= 0:
                    self.chain_pull_target = None

        elif tipo == "Dupla":
            if self.dual_combo_timer > 0:
                self.dual_combo_timer -= dt
                if self.dual_combo_timer <= 0:
                    self.dual_combo = 0
                    self.dual_frenzy = False
                    self.dual_cross_slash = False
            if self.dual_combo >= 4:
                self.dual_frenzy = True
            if self.dual_combo >= 6:
                self.dual_cross_slash = True

        elif tipo == "Reta":
            if self.reta_combo_timer > 0:
                self.reta_combo_timer -= dt
                if self.reta_combo_timer <= 0:
                    self.reta_combo = 0
            if self.reta_parry_window > 0:
                self.reta_parry_window -= dt

        elif tipo in ("Transformável", "Transformavel"):
            if self.transform_cd > 0:
                self.transform_cd -= dt
            if self.transform_bonus_timer > 0:
                self.transform_bonus_timer -= dt

        elif tipo == "Arco":
            if self.bow_charging:
                self.bow_charge += dt
            if self.bow_perfect_timer > 0:
                self.bow_perfect_timer -= dt

        if tipo in ("Orbital", "Orbe"):
            arma_obj = self.dados.arma_obj
            if arma_obj:
                self.orbital_angle += self.orbital_speed * dt
                if self.orbital_angle >= 360:
                    self.orbital_angle -= 360
            if self.orbital_dmg_timer > 0:
                self.orbital_dmg_timer -= dt
            if self.orbital_burst_cd > 0:
                self.orbital_burst_cd -= dt

    def _executar_ataques_corrente(self, dt, distancia, inimigo, estilo):
        """Sistema Corrente v5.0."""
        anim_manager = get_weapon_animation_manager()
        arma_tipo = "Corrente"

        if estilo in STYLE_PROFILES:
            profile_key, _profile_dict = estilo, STYLE_PROFILES
        elif estilo in WEAPON_PROFILES:
            profile_key, _profile_dict = estilo, WEAPON_PROFILES
        else:
            profile_key, _profile_dict = arma_tipo, WEAPON_PROFILES

        rad = math.radians(self.angulo_olhar)
        weapon_tip = (
            self.pos[0] + math.cos(rad) * self.raio_fisico * 3.5,
            self.pos[1] + math.sin(rad) * self.raio_fisico * 3.5,
        )
        transform = anim_manager.get_weapon_transform(
            id(self), arma_tipo, self.angulo_olhar, weapon_tip, dt, weapon_style=estilo)
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        # Meteor Hammer spin
        if estilo == "Meteor Hammer" and self.chain_spinning:
            self.angulo_arma_visual += self.chain_spin_speed * 360 * dt
            if self.chain_spin_dmg_timer <= 0:
                self.chain_spin_dmg_timer = max(0.2, 0.6 - self.chain_spin_speed * 0.12)
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.15
                anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
            elif self.timer_animacao > 0:
                self.timer_animacao -= dt
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
                if self.timer_animacao <= 0:
                    self.atacando = False
            acoes_spin = ["MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR", "CIRCULAR"]
            if self.brain.acao_atual not in acoes_spin or distancia > 6.0:
                self.chain_spinning = False
                self.atacando = False
                self.cooldown_ataque = 0.8
            return

        if self.atacando:
            self.timer_animacao -= dt
            profile = _profile_dict.get(profile_key, WEAPON_PROFILES["Corrente"])
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
                if "Mangual" in estilo or "Flail" in estilo:
                    self.chain_recovery_mult = max(0.7, 1.0 - self.chain_momentum * 0.3)
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        else:
            self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        if self.atacando or self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        alcance = self._calcular_alcance_corrente(estilo)
        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        profile = _profile_dict.get(profile_key, WEAPON_PROFILES["Corrente"])

        if "Mangual" in estilo or "Flail" in estilo:
            momentum_bonus = self.chain_momentum * 0.4
            anim_time = profile.total_time * (1.0 - momentum_bonus)
            self.timer_animacao = max(0.3, anim_time)
            peso = getattr(self.dados.arma_obj, 'peso', 8.0)
            base_cd = 1.2 + (peso / 10.0) * 0.5 - self.chain_momentum * 0.4
            self.chain_recovery_mult = 1.0

        elif estilo == "Kusarigama":
            if distancia < self.raio_fisico * 2.5:
                self.chain_mode = 0
                anim_time = profile.total_time * 0.6
                base_cd = 0.35 + random.random() * 0.2
            else:
                self.chain_mode = 1
                anim_time = profile.total_time * 1.2
                base_cd = 0.7 + random.random() * 0.3
            self.timer_animacao = anim_time
            self.chain_combo += 1
            self.chain_combo_timer = 2.5

        elif estilo == "Chicote":
            speed_mult = 1.0 + min(self.chain_whip_stacks, 5) * 0.12
            anim_time = profile.total_time / speed_mult
            self.timer_animacao = max(0.15, anim_time)
            self.chain_whip_crack = distancia >= alcance * 0.65
            base_cd = max(0.2, 0.4 / speed_mult)
            self.chain_whip_stacks = min(6, self.chain_whip_stacks + 1)

        elif estilo == "Meteor Hammer":
            if self.brain.acao_atual in ["MATAR", "PRESSIONAR", "COMBATE"] and distancia < 5.0:
                self.chain_spinning = True
                self.chain_spin_speed = 0.5
                self.chain_spin_dmg_timer = 0.3
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.15
                anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
                return
            else:
                self.timer_animacao = profile.total_time
                base_cd = 0.9 + random.random() * 0.4

        elif "Corrente com Peso" in estilo:
            self.timer_animacao = profile.total_time * 1.1
            base_cd = 1.0 + random.random() * 0.4
            self.chain_pull_target = inimigo
            self.chain_pull_timer = 0.8

        else:
            self.timer_animacao = profile.total_time
            base_cd = 0.6 + random.random() * 0.4

        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd * self.chain_recovery_mult / vel_ataque

    def _calcular_alcance_corrente(self, estilo):
        base = self.raio_fisico
        if "Mangual" in estilo or "Flail" in estilo:
            return base * 4.0
        elif estilo == "Kusarigama":
            return base * 5.5
        elif estilo == "Chicote":
            return base * 6.0
        elif estilo == "Meteor Hammer":
            return base * 5.0
        elif "Corrente com Peso" in estilo:
            return base * 3.5
        return base * 4.0

    def _executar_ataques_dupla(self, dt, distancia, inimigo, estilo):
        """Sistema Dupla v15.0."""
        anim_manager = get_weapon_animation_manager()
        if estilo in STYLE_PROFILES:
            profile = STYLE_PROFILES[estilo]
        elif estilo in WEAPON_PROFILES:
            profile = WEAPON_PROFILES[estilo]
        else:
            profile = WEAPON_PROFILES.get("Dupla", WEAPON_PROFILES["Reta"])

        rad = math.radians(self.angulo_olhar)
        weapon_tip = (
            self.pos[0] + math.cos(rad) * self.raio_fisico * 2.0,
            self.pos[1] + math.sin(rad) * self.raio_fisico * 2.0,
        )
        transform = anim_manager.get_weapon_transform(
            id(self), "Dupla", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo)
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
            return

        self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        if self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        alcance = self.raio_fisico * (2.2 if estilo == "Garras" else 3.0 if estilo in ("Kamas", "Sai") else 2.8)
        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        frenzy_mult = 0.5 if self.dual_frenzy else 1.0
        anim_time = profile.total_time * (0.7 if self.dual_cross_slash else frenzy_mult)
        self.timer_animacao = max(0.06, anim_time)
        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        self.dual_hand = 1 - self.dual_hand
        anim_manager.start_attack(id(self), "Dupla", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

        self.dual_combo = min(8, self.dual_combo + 1)
        self.dual_combo_timer = 2.0

        cd_map = {
            "Adagas Gêmeas": 0.15, "Garras": 0.22, "Kamas": 0.20,
            "Sai": 0.28, "Tonfas": 0.25, "Facas Táticas": 0.18,
        }
        base_cd = max(0.06, cd_map.get(estilo, 0.20) * frenzy_mult)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    def _executar_ataques_reta(self, dt, distancia, inimigo, estilo):
        """Sistema Reta v15.0."""
        anim_manager = get_weapon_animation_manager()
        if estilo in STYLE_PROFILES:
            profile = STYLE_PROFILES[estilo]
        elif estilo in WEAPON_PROFILES:
            profile = WEAPON_PROFILES[estilo]
        else:
            profile = WEAPON_PROFILES.get("Reta", WEAPON_PROFILES["Reta"])

        rad = math.radians(self.angulo_olhar)
        weapon_tip = (
            self.pos[0] + math.cos(rad) * self.raio_fisico * 2.5,
            self.pos[1] + math.sin(rad) * self.raio_fisico * 2.5,
        )
        transform = anim_manager.get_weapon_transform(
            id(self), "Reta", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo)
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
                self.reta_heavy_charging = False
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
            return

        self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        if self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        is_thrust = estilo in ("Estocada (Lança)", "Lança", "Alabarda")
        is_heavy = estilo in ("Contusão (Maça)", "Maça", "Martelo", "Montante", "Claymore")

        alcance = (self.raio_fisico * 3.5 if is_thrust
                   else self.raio_fisico * 2.8 if is_heavy
                   else self.raio_fisico * 2.5)

        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        self.reta_combo = (self.reta_combo + 1) % 3
        self.reta_combo_timer = 2.5

        combo_speed_bonus = {0: 1.0, 1: 0.85, 2: 1.2}.get(self.reta_combo, 1.0)

        if is_heavy:
            anim_time = profile.total_time * combo_speed_bonus * 1.1
            base_cd = 0.6 + random.random() * 0.3
        elif is_thrust:
            anim_time = profile.total_time * combo_speed_bonus * 0.8
            base_cd = 0.25 + random.random() * 0.2
        else:
            anim_time = profile.total_time * combo_speed_bonus
            base_cd = 0.35 + random.random() * 0.25

        self.timer_animacao = max(0.12, anim_time)
        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), "Reta", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    def _executar_ataques_orbital(self, dt, distancia, inimigo, estilo):
        """Sistema Orbital v15.0."""
        anim_manager = get_weapon_animation_manager()
        self.angulo_arma_visual = self.orbital_angle

        rad = math.radians(self.angulo_olhar)
        weapon_tip = (
            self.pos[0] + math.cos(rad) * self.raio_fisico * 1.5,
            self.pos[1] + math.sin(rad) * self.raio_fisico * 1.5,
        )
        transform = anim_manager.get_weapon_transform(
            id(self), "Orbital", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo)
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        arma = self.dados.arma_obj
        if not arma:
            return

        qtd_orbitais = max(1, int(getattr(arma, 'quantidade_orbitais', 1)))
        raio_orbita = self.raio_fisico * 1.5

        if self.orbital_dmg_timer <= 0 and not inimigo.morto:
            alcance_orbital = raio_orbita + self.raio_fisico * 0.5
            if distancia < alcance_orbital and abs(self.z - inimigo.z) < 1.5:
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.15
                anim_manager.start_attack(id(self), "Orbital", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
                self.orbital_dmg_timer = (
                    0.3 if "Lâminas" in estilo or "Laminas" in estilo
                    else 0.8 if "Drone" in estilo or "Ofensivo" in estilo
                    else 1.2 if "Escudo" in estilo or "Defensivo" in estilo
                    else 0.5
                )

        if self.orbital_burst_cd <= 0 and not inimigo.morto:
            acoes = ["MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR"]
            if self.brain.acao_atual in acoes and distancia < raio_orbita * 3:
                self.orbital_burst_cd = 5.0
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.3
                dano_total = arma.dano * (self.dados.forca / 2.0 + 0.5)
                cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (120, 180, 255)
                for i in range(qtd_orbitais):
                    ang_orbital = self.orbital_angle + (360 / qtd_orbitais) * i
                    rad_o = math.radians(ang_orbital)
                    spawn_x = self.pos[0] + math.cos(rad_o) * raio_orbita
                    spawn_y = self.pos[1] + math.sin(rad_o) * raio_orbita
                    ang_para_alvo = math.degrees(math.atan2(
                        inimigo.pos[1] - spawn_y, inimigo.pos[0] - spawn_x))
                    self.buffer_projeteis.append(ArmaProjetil(
                        tipo="orbe", x=spawn_x, y=spawn_y, angulo=ang_para_alvo,
                        dono=self, dano=dano_total / qtd_orbitais,
                        velocidade=14.0, tamanho=0.25, cor=cor))
                anim_manager.start_attack(id(self), "Orbital", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False

    def _executar_ataques_transformavel(self, dt, distancia, inimigo, estilo):
        """Sistema Transformável v15.0."""
        anim_manager = get_weapon_animation_manager()
        profile = WEAPON_PROFILES.get("Transformavel", WEAPON_PROFILES["Reta"])

        rad = math.radians(self.angulo_olhar)
        weapon_tip = (
            self.pos[0] + math.cos(rad) * self.raio_fisico * 2.5,
            self.pos[1] + math.sin(rad) * self.raio_fisico * 2.5,
        )
        transform = anim_manager.get_weapon_transform(
            id(self), "Transformável", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo)
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
            return

        self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        if self.transform_cd <= 0:
            should_switch = (
                (self.transform_forma == 0 and distancia > self.raio_fisico * 4.0) or
                (self.transform_forma == 1 and distancia < self.raio_fisico * 2.0)
            )
            if should_switch:
                self.transform_forma = 1 - self.transform_forma
                self.transform_cd = 3.0
                self.transform_combo = 0
                self.transform_bonus_timer = 1.5

        if self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        if self.transform_forma == 0:
            alcance = self.raio_fisico * 2.5
            anim_time = profile.total_time * 0.8
            base_cd = 0.3 + random.random() * 0.2
        else:
            alcance = self.raio_fisico * 4.0
            anim_time = profile.total_time * 1.2
            base_cd = 0.5 + random.random() * 0.3

        if self.transform_bonus_timer > 0:
            anim_time *= 0.7
            base_cd *= 0.5

        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        self.timer_animacao = max(0.12, anim_time)
        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        self.transform_combo += 1
        anim_manager.start_attack(id(self), "Transformável", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    # ==================================================================
    # Disparo de projéteis
    # ==================================================================

    def _disparar_arremesso(self, alvo):
        """Dispara projéteis de arma de arremesso — v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        qtd = int(getattr(arma, 'quantidade', 3))
        tam = self.raio_fisico * 0.35
        dano_por_proj = arma.dano / max(qtd, 1)
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (200, 200, 200)

        estilo = getattr(arma, 'estilo', '').lower()
        if "shuriken" in estilo:
            tipo_proj, vel = "shuriken", 18.0
        elif "chakram" in estilo:
            tipo_proj, vel = "chakram", 14.0
        elif "bumerangue" in estilo or "boomerang" in estilo:
            tipo_proj, vel = "chakram", 13.0
        elif "bola" in estilo or "boleadeira" in estilo:
            tipo_proj, vel = "faca", 12.0
        elif "rede" in estilo:
            tipo_proj, vel = "faca", 10.0
        else:
            tipo_proj, vel = "faca", 16.0

        consec = getattr(self, 'throw_consecutive', 0)
        volley_bonus = min(consec * 0.08, 0.30)
        vel *= (1.0 + volley_bonus)
        spread_base = 25 if qtd > 1 else 0
        spread = spread_base * max(0.5, 1.0 - consec * 0.1)
        dano_mult = 1.0 + min(consec * 0.05, 0.20)

        dx = alvo.pos[0] - self.pos[0]
        dy = alvo.pos[1] - self.pos[1]
        dist_alvo = math.hypot(dx, dy)
        angulo_base = self.angulo_olhar
        if dist_alvo > 0.1:
            tempo_voo = dist_alvo / vel
            fut_x = alvo.pos[0] + alvo.vel[0] * tempo_voo * 0.5
            fut_y = alvo.pos[1] + alvo.vel[1] * tempo_voo * 0.5
            angulo_base = math.degrees(math.atan2(fut_y - self.pos[1], fut_x - self.pos[0]))

        if dist_alvo < 2.5:
            dano_mult *= 0.82
        elif dist_alvo > 8.5:
            dano_mult *= 1.02

        for i in range(qtd):
            offset = (-spread / 2 + (spread / (qtd - 1)) * i) if qtd > 1 else 0
            ang = angulo_base + offset + random.uniform(-1.5, 1.5)
            spawn_dist = self.raio_fisico + 0.5
            spawn_x = self.pos[0] + math.cos(math.radians(ang)) * spawn_dist
            spawn_y = self.pos[1] + math.sin(math.radians(ang)) * spawn_dist
            self.buffer_projeteis.append(ArmaProjetil(
                tipo=tipo_proj, x=spawn_x, y=spawn_y, angulo=ang, dono=self,
                dano=dano_por_proj * (self.dados.forca / 2.0) * dano_mult,
                velocidade=vel, tamanho=tam, cor=cor))

    def _disparar_flecha(self, alvo):
        """Dispara flecha do arco — v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        dano = arma.dano * (self.dados.forca / 2.0 + 0.5)
        forca = getattr(arma, 'forca_arco', 1.0)
        forca_normalizada = max(0.5, min(2.0, forca / 25.0))
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (139, 90, 43)

        charge = getattr(self, 'bow_charge', 0.0)
        charge_pct = min(charge, 1.5)
        if charge_pct >= 1.0:
            dano *= 1.4
            vel_bonus, tam_mult = 0.25, 1.4
        elif charge_pct >= 0.5:
            dano *= 1.15
            vel_bonus, tam_mult = 0.10, 1.15
        else:
            vel_bonus, tam_mult = 0.0, 1.0

        perfect = getattr(self, 'bow_perfect_timer', 0.0)
        if perfect > 0:
            dano *= 1.25

        self.bow_charge = 0.0
        self.bow_charging = False

        dx = alvo.pos[0] - self.pos[0]
        dy = alvo.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        vel_flecha = (35.0 + forca_normalizada * 20.0) * (1.0 + vel_bonus)

        if dist > 0.1:
            tempo_voo = dist / vel_flecha
            alvo_futuro_x = alvo.pos[0] + alvo.vel[0] * tempo_voo * 0.8
            alvo_futuro_y = alvo.pos[1] + alvo.vel[1] * tempo_voo * 0.8
            angulo_mira = math.degrees(math.atan2(alvo_futuro_y - self.pos[1], alvo_futuro_x - self.pos[0]))
        else:
            angulo_mira = self.angulo_olhar

        imprecisao = max(0.5, 2.0 - charge_pct * 1.0)
        if dist < 3.0:
            imprecisao += 2.8
            dano *= 0.55
        elif dist > 9.5:
            dano *= 1.03
        angulo_mira += random.uniform(-imprecisao, imprecisao)

        rad = math.radians(angulo_mira)
        spawn_dist = self.raio_fisico + 0.3
        spawn_x = self.pos[0] + math.cos(rad) * spawn_dist
        spawn_y = self.pos[1] + math.sin(rad) * spawn_dist

        self.buffer_projeteis.append(FlechaProjetil(
            x=spawn_x, y=spawn_y, angulo=angulo_mira, dono=self,
            dano=dano, forca=forca_normalizada * tam_mult, cor=cor))

    def _disparar_orbes(self, alvo):
        """Dispara orbes mágicos — v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        qtd = int(getattr(arma, 'quantidade', 2))
        dano_por_orbe = arma.dano / max(qtd, 1)
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (100, 100, 255)

        mana_ratio = self.dados.mana / max(self.dados.mana_max, 1) if hasattr(self.dados, 'mana_max') else 0.5
        mana_mult = 0.8 + mana_ratio * 0.6

        estilo = getattr(arma, 'estilo', '').lower()
        if "runas" in estilo or "flutuante" in estilo:
            dano_bonus = 1.15
        elif "cristal" in estilo or "prisma" in estilo:
            dano_bonus = 1.0
            qtd = min(qtd + 1, 5)
        elif "foguete" in estilo or "missil" in estilo:
            dano_bonus = 1.25
        else:
            dano_bonus = 1.0

        orbes_orbitando = [o for o in self.buffer_orbes if o.ativo and o.estado == "orbitando"]

        dist_atual = math.hypot(alvo.pos[0] - self.pos[0], alvo.pos[1] - self.pos[1])
        if dist_atual < 2.2:
            mana_mult *= 0.66
        elif dist_atual > 6.5:
            mana_mult *= 1.02

        if orbes_orbitando:
            for orbe in orbes_orbitando[:qtd]:
                orbe.dano *= mana_mult * dano_bonus
                orbe.iniciar_carga(alvo)
        else:
            for i in range(qtd):
                orbe = OrbeMagico(
                    x=self.pos[0], y=self.pos[1], dono=self,
                    dano=dano_por_orbe * (self.dados.forca / 2.0 + self.dados.mana / 2.0) * mana_mult * dano_bonus,
                    indice=i, total=qtd, cor=cor)
                orbe.iniciar_carga(alvo)
                self.buffer_orbes.append(orbe)
