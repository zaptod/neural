"""
NEURAL FIGHTS â€” nucleo/lutador/weapons_mixin.py  [D03/D04 Sprint 8]
==================================================================
WeaponsMixin: ataques fÃ­sicos, sistemas de arma por tipo v15.0.

Imports inline eliminados (D04): ArmaProjetil, FlechaProjetil, OrbeMagico,
Projetil, AreaEffect, Beam, Buff, Summon, Trap, Transform, Channel,
AudioManager, MagicVFXManager, get_element_from_skill,
get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES no topo.
"""

import math
import random
import logging

from utilitarios.balance_config import (
    ESTAMINA_CUSTO_SKILL_MULT, ESTAMINA_CUSTO_SKILL_MULT2,
    CD_ARMA_MAX_RATIO, CD_ARMA_MAX_ABSOLUTO,
)
from nucleo.combat import (
    ArmaProjetil, FlechaProjetil, OrbeMagico,
    Projetil, AreaEffect, Beam, Buff, Summon, Trap, Transform, Channel,
)
from efeitos.audio import AudioManager
from efeitos.weapon_animations import (
    get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES,
)
from nucleo.hitbox import HITBOX_PROFILES
from nucleo.armas import get_weapon_runtime_controller, resolver_subtipo_orbital

_log = logging.getLogger("entities")

# VFX importado com guard para evitar crash em testes headless
try:
    from efeitos.magic_vfx import MagicVFXManager, get_element_from_skill as _get_elem
    _HAS_VFX = True
except ImportError:
    _HAS_VFX = False
    MagicVFXManager = None
    _get_elem = None


def _vfx_chargeup(nome_skill, data, pos, classe_nome):
    """Helper de chargeup VFX â€” nÃ£o lanÃ§a exceÃ§Ã£o se VFX indisponÃ­vel."""
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


def _registrar_skill_cast(lutador, nome_skill, custo_mana, tipo_skill):
    """Envia uso de skill para o coletor de stats quando houver simulador ativo."""
    collector = getattr(lutador, "stats_collector", None)
    dados = getattr(lutador, "dados", None)
    if collector and dados and getattr(dados, "nome", ""):
        collector.record_skill(dados.nome, nome_skill, mana_cost=custo_mana, skill_type=tipo_skill)


class WeaponsMixin:
    """Mixin com toda a lÃ³gica de ataques e disparo de projÃ©teis."""

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
        _registrar_skill_cast(self, nome_skill, custo_real, tipo)

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
        """Usa uma skill de classe especÃ­fica."""
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
        _registrar_skill_cast(self, skill_nome, custo, tipo)

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
    # Sistema de ataques fÃ­sicos v15.0
    # ==================================================================

    def executar_ataques(self, dt, distancia, inimigo):
        """Executa ataques fÃ­sicos â€” sistema v15.0."""
        self.cooldown_ataque -= dt

        arma = self.dados.arma_obj
        arma_tipo = arma.tipo if arma else "Reta"
        arma_estilo = getattr(arma, 'estilo', '') if arma else ''
        controller = get_weapon_runtime_controller(arma) if arma else get_weapon_runtime_controller(None)

        if controller.handler == "corrente":
            self._executar_ataques_corrente(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "dupla":
            self._executar_ataques_dupla(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "reta":
            self._executar_ataques_reta(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "orbital":
            self._executar_ataques_orbital(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "transformavel":
            self._executar_ataques_transformavel(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "arremesso":
            self._executar_ataques_arremesso(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "disparo":
            self._executar_ataques_disparo(dt, distancia, inimigo, arma_estilo)
            return
        if controller.handler == "foco":
            self._executar_ataques_foco(dt, distancia, inimigo, arma_estilo)
            return

        anim_manager = get_weapon_animation_manager()
        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 2.5
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )
        transform = anim_manager.get_weapon_transform(
            id(self), controller.animation_key, self.angulo_olhar, weapon_tip, dt, weapon_style=arma_estilo
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
                alcance_ataque = controller.attack_range(self, arma)
            except Exception:
                alcance_ataque = self.raio_fisico * 3.0

            if self.brain.acao_atual in acoes_ofensivas and distancia < alcance_ataque:
                deve_atacar = True
            if self.brain.acao_atual == "POKE" and abs(distancia - self.alcance_ideal) < 1.5:
                deve_atacar = True
            if self.modo_ataque_aereo and distancia < 2.0:
                deve_atacar = True

            if controller.allows_reposition_attack and distancia < alcance_ataque:
                if self.brain.acao_atual in ["RECUAR", "FUGIR", "APROXIMAR"]:
                    if random.random() < 0.25:
                        deve_atacar = True

            if deve_atacar and abs(self.z - inimigo.z) < 1.5:
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()

                profile = WEAPON_PROFILES.get(controller.animation_key, WEAPON_PROFILES["Reta"])
                self.timer_animacao = profile.total_time
                anim_manager.start_attack(id(self), controller.animation_key, tuple(self.pos), self.angulo_olhar, weapon_style=arma_estilo)

                if controller.familia == "arremesso":
                    self._disparar_arremesso(inimigo)
                elif controller.familia == "disparo":
                    self._disparar_flecha(inimigo)
                elif controller.familia == "foco":
                    self._disparar_orbes(inimigo)

                base_cd = controller.base_cooldown(self, arma)
                if controller.familia == "arremesso":
                    self.throw_consecutive += 1
                    base_cd = max(0.28, base_cd * 0.9 - self.throw_consecutive * 0.03)
                    if self.throw_consecutive >= 5:
                        self.throw_consecutive = 0
                elif controller.familia == "disparo":
                    charge_bonus = min(0.3, self.bow_charge * 0.2) if self.bow_charge > 0 else 0
                    base_cd = max(0.4, base_cd * 1.15 - charge_bonus * 0.5)
                    self.bow_charge = 0.0
                    self.bow_charging = False
                elif controller.familia == "foco":
                    base_cd = max(0.5, base_cd * 1.2)

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
        familia = getattr(arma, "familia", None)
        estilo = getattr(arma, 'estilo', '')

        if familia == "arremesso":
            self.throw_consecutive = max(0.0, self.throw_consecutive - dt * 1.25)

        if familia == "Corrente" or familia == "corrente" or tipo == "Corrente":
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

        elif familia == "dupla" or tipo == "Dupla":
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

        elif familia in ("lamina", "haste") or tipo == "Reta":
            if self.reta_combo_timer > 0:
                self.reta_combo_timer -= dt
                if self.reta_combo_timer <= 0:
                    self.reta_combo = 0
            if self.reta_parry_window > 0:
                self.reta_parry_window -= dt

        elif familia == "hibrida" or tipo in ("TransformÃ¡vel", "Transformavel"):
            if self.transform_cd > 0:
                self.transform_cd -= dt
            if self.transform_bonus_timer > 0:
                self.transform_bonus_timer -= dt

        elif familia == "disparo" or tipo == "Arco":
            if self.bow_charging:
                self.bow_charge = min(1.6, self.bow_charge + dt)
            if self.bow_perfect_timer > 0:
                self.bow_perfect_timer -= dt

        if familia in ("orbital", "foco") or tipo in ("Orbital", "Orbe", "Mágica", "Magica"):
            arma_obj = self.dados.arma_obj
            if arma_obj:
                if familia == "orbital" or tipo == "Orbital":
                    perfil_orbital = self._perfil_orbital_runtime(arma_obj)
                    self.orbital_speed = perfil_orbital["velocidade"]
                    subtipo_orbital = perfil_orbital["subtipo"]
                    if subtipo_orbital == "escudo":
                        alvo = self.angulo_olhar % 360
                        diff = ((alvo - self.orbital_angle + 540) % 360) - 180
                        passo = min(abs(diff), self.orbital_speed * dt)
                        if diff >= 0:
                            self.orbital_angle += passo
                        else:
                            self.orbital_angle -= passo
                        self.orbital_shield_active = True
                    else:
                        self.orbital_angle += self.orbital_speed * dt
                        self.orbital_shield_active = False
                    self.orbital_angle %= 360
                else:
                    self.orbital_angle += self.orbital_speed * dt
                    if self.orbital_angle >= 360:
                        self.orbital_angle -= 360
            if self.orbital_dmg_timer > 0:
                self.orbital_dmg_timer -= dt
            if self.orbital_burst_cd > 0:
                self.orbital_burst_cd -= dt

    def _perfil_orbital_runtime(self, arma):
        """Resolve comportamento mecânico das orbitais por subtipo."""
        subtipo = resolver_subtipo_orbital(arma)
        qtd = max(1, int(getattr(arma, "quantidade_orbitais", 1) or 1))
        perfis = {
            "escudo": {
                "subtipo": "escudo",
                "qtd": qtd,
                "raio_mult": 1.28,
                "velocidade": 104.0,
                "contato_cd": 0.58,
                "burst_cd": 4.6,
                "burst_speed": 11.0,
                "burst_projeteis": max(1, qtd),
                "burst_spread": 28.0,
                "burst_tipo": "chakram",
                "burst_tamanho": 0.30,
                "dano_mult": 0.86,
                "alcance_extra": 0.75,
                "escudo_angular": 132.0,
            },
            "drone": {
                "subtipo": "drone",
                "qtd": qtd,
                "raio_mult": 1.88,
                "velocidade": 156.0,
                "contato_cd": 0.74,
                "burst_cd": 3.8,
                "burst_speed": 16.5,
                "burst_projeteis": max(2, qtd + 1),
                "burst_spread": 20.0,
                "burst_tipo": "faca",
                "burst_tamanho": 0.20,
                "dano_mult": 0.82,
                "alcance_extra": 1.45,
                "escudo_angular": 0.0,
            },
            "laminas": {
                "subtipo": "laminas",
                "qtd": qtd,
                "raio_mult": 1.46,
                "velocidade": 268.0,
                "contato_cd": 0.24,
                "burst_cd": 4.1,
                "burst_speed": 15.2,
                "burst_projeteis": max(2, qtd * 2),
                "burst_spread": 16.0,
                "burst_tipo": "shuriken",
                "burst_tamanho": 0.18,
                "dano_mult": 0.74,
                "alcance_extra": 1.05,
                "escudo_angular": 0.0,
            },
            "orbes": {
                "subtipo": "orbes",
                "qtd": qtd,
                "raio_mult": 1.64,
                "velocidade": 188.0,
                "contato_cd": 0.36,
                "burst_cd": 4.8,
                "burst_speed": 13.4,
                "burst_projeteis": max(1, qtd),
                "burst_spread": 12.0,
                "burst_tipo": "orbe",
                "burst_tamanho": 0.26,
                "dano_mult": 0.78,
                "alcance_extra": 1.20,
                "escudo_angular": 0.0,
            },
        }
        return perfis.get(subtipo, perfis["orbes"])

    def _disparar_burst_orbital(self, inimigo, arma, perfil_orbital, raio_orbita):
        """Dispara burst orbital respeitando o papel tático do subtipo."""
        if not inimigo or inimigo.morto:
            return

        mana_total = float(getattr(self, "mana", getattr(self.dados, "mana", 0.0)) or 0.0)
        dano_total = arma.dano * (0.72 + self.dados.forca / 3.8 + mana_total / 18.0)
        dano_total *= perfil_orbital["dano_mult"]
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, "r") else (120, 180, 255)
        qtd = perfil_orbital["qtd"]
        projeteis = perfil_orbital["burst_projeteis"]
        spread = perfil_orbital["burst_spread"]
        tipo_proj = perfil_orbital["burst_tipo"]

        for i in range(projeteis):
            ang_orbital = self.orbital_angle + (360 / qtd) * (i % qtd)
            rad_o = math.radians(ang_orbital)
            spawn_x = self.pos[0] + math.cos(rad_o) * raio_orbita
            spawn_y = self.pos[1] + math.sin(rad_o) * raio_orbita
            ang_para_alvo = math.degrees(math.atan2(inimigo.pos[1] - spawn_y, inimigo.pos[0] - spawn_x))
            if projeteis > 1:
                offset = -spread / 2 + (spread / max(1, projeteis - 1)) * i
            else:
                offset = 0.0
            self.buffer_projeteis.append(ArmaProjetil(
                tipo=tipo_proj,
                x=spawn_x,
                y=spawn_y,
                angulo=ang_para_alvo + offset,
                dono=self,
                dano=dano_total / max(1, projeteis),
                velocidade=perfil_orbital["burst_speed"],
                tamanho=perfil_orbital["burst_tamanho"],
                cor=cor,
            ))

    def _alcances_orbitais_runtime(self, arma, raio_orbita, perfil_orbital):
        """Converte o perfil orbital para alcances reais de contato e burst."""
        subtipo = perfil_orbital["subtipo"]
        controller = get_weapon_runtime_controller(arma)
        alcance_base = float(controller.attack_range(self, arma) if arma else 0.0)

        alcance_contato = raio_orbita + self.raio_fisico * perfil_orbital["alcance_extra"]
        alcance_burst = raio_orbita + self.raio_fisico * (
            3.1 if subtipo == "drone" else 2.4 if subtipo == "escudo" else 2.8
        )

        contato_bias = {
            "escudo": 1.02,
            "drone": 0.78,
            "laminas": 0.90,
            "orbes": 0.84,
        }
        burst_bias = {
            "escudo": 1.18,
            "drone": 1.42,
            "laminas": 1.55,
            "orbes": 1.30,
        }

        if alcance_base > 0:
            alcance_contato = max(alcance_contato, alcance_base * contato_bias.get(subtipo, 0.84))
            alcance_burst = max(alcance_burst, alcance_base * burst_bias.get(subtipo, 1.24))

        return alcance_contato, alcance_burst

    def _orbital_em_janela_de_contato(self, inimigo, distancia, arma, raio_orbita, perfil_orbital):
        """Decide quando a órbita pode registrar um hit corpo a corpo."""
        if inimigo is None or inimigo.morto or abs(self.z - inimigo.z) >= 1.5:
            return False

        alcance_contato, _ = self._alcances_orbitais_runtime(arma, raio_orbita, perfil_orbital)
        if distancia > alcance_contato:
            return False

        if perfil_orbital["subtipo"] != "escudo":
            return True

        ang_inimigo = math.degrees(math.atan2(inimigo.pos[1] - self.pos[1], inimigo.pos[0] - self.pos[0]))
        diff = ((ang_inimigo - self.orbital_angle + 540) % 360) - 180
        return abs(diff) <= perfil_orbital["escudo_angular"] / 2

    def _executar_ataques_corrente(self, dt, distancia, inimigo, estilo):
        """Sistema Corrente v6.0 com modos mais consistentes."""
        arma = self.dados.arma_obj
        controller = get_weapon_runtime_controller(arma)
        estilo_n = (estilo or "").lower()
        anim_manager, transform = self._aplicar_animacao_runtime(dt, "Corrente", estilo, self.raio_fisico * 3.5)

        if "meteor" in estilo_n and self.chain_spinning:
            self.angulo_arma_visual += self.chain_spin_speed * 360 * dt
            if self.chain_spin_dmg_timer <= 0:
                self.chain_spin_dmg_timer = max(0.18, 0.52 - self.chain_spin_speed * 0.10)
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.12
                anim_manager.start_attack(id(self), "Corrente", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
            elif self.timer_animacao > 0:
                self.timer_animacao -= dt
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
                if self.timer_animacao <= 0:
                    self.atacando = False
            acoes_spin = {"MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR", "CIRCULAR"}
            if self.brain.acao_atual not in acoes_spin or distancia > controller.attack_range(self, arma) * 0.95:
                self.chain_spinning = False
                self.atacando = False
                self.cooldown_ataque = 0.8
            return

        if self._consumir_animacao_ativa(dt, transform):
            if "mangual" in estilo_n or "flail" in estilo_n:
                self.chain_recovery_mult = max(0.72, 1.0 - self.chain_momentum * 0.28)
            return

        if self.cooldown_ataque > 0 or abs(self.z - inimigo.z) > 1.5:
            return

        acoes_ofensivas = {"MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE", "CIRCULAR"}
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        alcance = self._calcular_alcance_corrente(estilo)
        alcance_min = max(0.8, float(getattr(arma, "alcance_minimo", 0.7) or 0.7) * 0.95)
        if distancia > alcance or distancia < alcance_min * 0.45:
            return

        if estilo in STYLE_PROFILES:
            profile = STYLE_PROFILES[estilo]
        elif estilo in WEAPON_PROFILES:
            profile = WEAPON_PROFILES[estilo]
        else:
            profile = WEAPON_PROFILES["Corrente"]

        base_cd = controller.base_cooldown(self, arma)

        if "mangual" in estilo_n or "flail" in estilo_n:
            self.chain_momentum = min(1.35, self.chain_momentum + 0.18)
            momentum_bonus = self.chain_momentum * 0.22
            self.timer_animacao = max(0.24, profile.total_time * (1.0 - momentum_bonus))
            self.chain_recovery_mult = 1.0
            base_cd = max(0.45, base_cd * (1.08 - momentum_bonus))

        elif "kusarigama" in estilo_n:
            media_dist = max(alcance_min + 0.9, alcance * 0.58)
            if distancia < media_dist:
                self.chain_mode = 0
                self.timer_animacao = max(0.14, profile.total_time * 0.64)
                base_cd = max(0.22, base_cd * 0.72)
                self.chain_pull_target = None
                self.chain_pull_timer = 0.0
            else:
                self.chain_mode = 1
                self.timer_animacao = max(0.26, profile.total_time * 1.08)
                base_cd = max(0.46, base_cd * 1.08)
                self.chain_pull_target = inimigo
                self.chain_pull_timer = 0.7
            self.chain_combo += 1
            self.chain_combo_timer = 2.5

        elif "chicote" in estilo_n:
            speed_mult = 1.0 + min(self.chain_whip_stacks, 5) * 0.10
            self.timer_animacao = max(0.12, profile.total_time / speed_mult)
            self.chain_whip_crack = distancia >= alcance * 0.62
            base_cd = max(0.18, base_cd * (0.70 / speed_mult))
            self.chain_whip_stacks = min(6, self.chain_whip_stacks + 1)

        elif "meteor" in estilo_n:
            if self.brain.acao_atual in {"MATAR", "PRESSIONAR", "COMBATE", "CIRCULAR"} and distancia < alcance * 0.82:
                self.chain_spinning = True
                self.chain_spin_speed = 0.55
                self.chain_spin_dmg_timer = 0.25
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.12
                anim_manager.start_attack(id(self), "Corrente", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
                return
            self.timer_animacao = max(0.22, profile.total_time)
            base_cd = max(0.58, base_cd * 1.18)

        elif "peso" in estilo_n:
            self.timer_animacao = max(0.26, profile.total_time * 1.05)
            base_cd = max(0.52, base_cd * 1.10)
            self.chain_pull_target = inimigo
            self.chain_pull_timer = 0.8

        else:
            self.timer_animacao = max(0.20, profile.total_time)
            base_cd = max(0.34, base_cd)

        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), "Corrente", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = max(0.14, base_cd * self.chain_recovery_mult) / vel_ataque

    def _calcular_alcance_corrente(self, estilo):
        arma = self.dados.arma_obj
        controller = get_weapon_runtime_controller(arma)
        alcance_base = controller.attack_range(self, arma)
        estilo_n = (estilo or "").lower()
        if "mangual" in estilo_n or "flail" in estilo_n:
            return max(self.raio_fisico * 4.0, alcance_base * 0.92)
        if "kusarigama" in estilo_n:
            return max(self.raio_fisico * 5.2, alcance_base * 1.05)
        if "chicote" in estilo_n:
            return max(self.raio_fisico * 5.6, alcance_base * 1.12)
        if "meteor" in estilo_n:
            return max(self.raio_fisico * 4.8, alcance_base)
        if "peso" in estilo_n:
            return max(self.raio_fisico * 3.6, alcance_base * 0.9)
        return max(self.raio_fisico * 4.0, alcance_base)

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
            "Adagas GÃªmeas": 0.15, "Garras": 0.22, "Kamas": 0.20,
            "Sai": 0.28, "Tonfas": 0.25, "Facas TÃ¡ticas": 0.18,
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

        is_thrust = estilo in ("Estocada (LanÃ§a)", "LanÃ§a", "Alabarda")
        is_heavy = estilo in ("ContusÃ£o (MaÃ§a)", "MaÃ§a", "Martelo", "Montante", "Claymore")

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
        """Sistema Orbital v16.0 com papeis distintos por subtipo."""
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

        perfil_orbital = self._perfil_orbital_runtime(arma)
        subtipo_orbital = perfil_orbital["subtipo"]
        raio_orbita = self.raio_fisico * perfil_orbital["raio_mult"]
        self.orbital_speed = perfil_orbital["velocidade"]
        self.orbital_shield_active = subtipo_orbital == "escudo"

        if subtipo_orbital == "escudo" and inimigo and not inimigo.morto:
            ang_para_inimigo = math.degrees(math.atan2(inimigo.pos[1] - self.pos[1], inimigo.pos[0] - self.pos[0]))
            diff = ((ang_para_inimigo - self.orbital_angle + 540) % 360) - 180
            self.orbital_angle = (self.orbital_angle + max(-42.0 * dt, min(42.0 * dt, diff))) % 360
            self.angulo_arma_visual = self.orbital_angle

        alcance_contato, alcance_burst = self._alcances_orbitais_runtime(arma, raio_orbita, perfil_orbital)

        if self.orbital_dmg_timer <= 0 and self._orbital_em_janela_de_contato(inimigo, distancia, arma, raio_orbita, perfil_orbital):
            self.atacando = True
            self.ataque_id += 1
            self.alvos_atingidos_neste_ataque.clear()
            self.timer_animacao = 0.14 if subtipo_orbital == "laminas" else 0.18 if subtipo_orbital == "escudo" else 0.16
            anim_manager.start_attack(id(self), "Orbital", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
            self.orbital_dmg_timer = perfil_orbital["contato_cd"]
            if subtipo_orbital == "escudo":
                dx = inimigo.pos[0] - self.pos[0]
                dy = inimigo.pos[1] - self.pos[1]
                mag = math.hypot(dx, dy) or 1.0
                inimigo.vel[0] += (dx / mag) * 0.45
                inimigo.vel[1] += (dy / mag) * 0.45

        if self.orbital_burst_cd <= 0 and not inimigo.morto:
            acoes = {"MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR", "CONTRA_ATAQUE", "POKE"}
            if self.brain.acao_atual in acoes and distancia < alcance_burst:
                self.orbital_burst_cd = perfil_orbital["burst_cd"]
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.26 if subtipo_orbital == "escudo" else 0.22
                self._disparar_burst_orbital(inimigo, arma, perfil_orbital, raio_orbita)
                anim_manager.start_attack(id(self), "Orbital", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False

    def _executar_ataques_transformavel(self, dt, distancia, inimigo, estilo):
        """Sistema TransformÃ¡vel v16.0 com troca por envelope de alcance."""
        arma = self.dados.arma_obj
        controller = get_weapon_runtime_controller(arma)
        estilo_n = (estilo or "").lower()
        anim_manager, transform = self._aplicar_animacao_runtime(dt, "TransformÃ¡vel", estilo, self.raio_fisico * 2.8)
        if self._consumir_animacao_ativa(dt, transform):
            return

        alcance_total = max(self.raio_fisico * 3.2, controller.attack_range(self, arma))
        alcance_min = max(self.raio_fisico * 1.4, float(getattr(arma, "alcance_minimo", 0.6) or 0.6) * 1.6)
        cutoff_longo = max(self.raio_fisico * 3.6, alcance_total * 0.72)
        cutoff_curto = max(self.raio_fisico * 1.9, alcance_min * 1.25)

        if "arco" in estilo_n or "lança" in estilo_n or "lanca" in estilo_n:
            cutoff_longo *= 0.92
        if "chicote" in estilo_n:
            cutoff_longo *= 1.04

        if self.transform_cd <= 0:
            should_switch = (
                (self.transform_forma == 0 and distancia > cutoff_longo) or
                (self.transform_forma == 1 and distancia < cutoff_curto)
            )
            if should_switch:
                self.transform_forma = 1 - self.transform_forma
                self.transform_cd = 2.4
                self.transform_combo = 0
                self.transform_bonus_timer = 1.2

        if self.cooldown_ataque > 0 or abs(self.z - inimigo.z) > 1.5:
            return

        acoes_ofensivas = {"MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"}
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        profile = WEAPON_PROFILES.get("Transformavel", WEAPON_PROFILES["Reta"])
        if self.transform_forma == 0:
            alcance = max(self.raio_fisico * 2.4, alcance_total * 0.68)
            anim_time = profile.total_time * 0.78
            base_cd = max(0.22, controller.base_cooldown(self, arma) * 0.82)
        else:
            alcance = max(self.raio_fisico * 3.8, alcance_total * 1.04)
            anim_time = profile.total_time * 1.08
            base_cd = max(0.36, controller.base_cooldown(self, arma) * 1.12)

        if self.transform_bonus_timer > 0:
            anim_time *= 0.72
            base_cd *= 0.62

        if distancia > alcance:
            return

        self.timer_animacao = max(0.12, anim_time)
        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        self.transform_combo += 1
        anim_manager.start_attack(id(self), "TransformÃ¡vel", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    def _aplicar_animacao_runtime(self, dt, animation_key, estilo, alcance_visual):
        anim_manager = get_weapon_animation_manager()
        rad = math.radians(self.angulo_olhar)
        weapon_tip = (
            self.pos[0] + math.cos(rad) * alcance_visual,
            self.pos[1] + math.sin(rad) * alcance_visual,
        )
        transform = anim_manager.get_weapon_transform(
            id(self), animation_key, self.angulo_olhar, weapon_tip, dt, weapon_style=estilo
        )
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]
        return anim_manager, transform

    def _consumir_animacao_ativa(self, dt, transform):
        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
            return True

        self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        return False

    def _executar_ataques_arremesso(self, dt, distancia, inimigo, estilo):
        """Ataques de arremesso com ritmo de rajada e kite."""
        arma = self.dados.arma_obj
        controller = get_weapon_runtime_controller(arma)
        anim_manager, transform = self._aplicar_animacao_runtime(dt, controller.animation_key, estilo, self.raio_fisico * 2.3)
        if self._consumir_animacao_ativa(dt, transform):
            return
        if self.cooldown_ataque > 0 or abs(self.z - inimigo.z) > 1.5:
            return

        acoes_ofensivas = {"MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"}
        acoes_move = {"RECUAR", "FUGIR", "APROXIMAR"}
        alcance = controller.attack_range(self, arma)
        alcance_min = max(1.4, float(getattr(arma, "alcance_minimo", 1.2) or 1.2) * 0.8)
        pode_kitar = self.brain.acao_atual in acoes_move and distancia > alcance_min
        if self.brain.acao_atual not in acoes_ofensivas and not pode_kitar:
            return
        if distancia > alcance or distancia < alcance_min * 0.55:
            return

        consec = float(getattr(self, "throw_consecutive", 0.0))
        cadencia = max(0.16, 0.34 - min(consec * 0.035, 0.12))
        anim_time = max(0.08, WEAPON_PROFILES.get(controller.animation_key, WEAPON_PROFILES["Reta"]).total_time * (0.58 if pode_kitar else 0.66))

        self.atacando = True
        self.timer_animacao = anim_time
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), controller.animation_key, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        self._disparar_arremesso(inimigo)
        self.throw_consecutive = min(5.0, consec + 1.0)

        base_cd = max(0.22, controller.base_cooldown(self, arma) * 0.72)
        if pode_kitar:
            base_cd *= 0.92
        base_cd = max(cadencia, base_cd - min(consec * 0.02, 0.08))
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    def _executar_ataques_disparo(self, dt, distancia, inimigo, estilo):
        """Ataques de disparo com carga e janela de tiro."""
        arma = self.dados.arma_obj
        controller = get_weapon_runtime_controller(arma)
        anim_manager, transform = self._aplicar_animacao_runtime(dt, controller.animation_key, estilo, self.raio_fisico * 2.6)
        if self._consumir_animacao_ativa(dt, transform):
            return

        acoes_ofensivas = {"MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"}
        alcance = controller.attack_range(self, arma)
        alcance_min = max(1.8, float(getattr(arma, "alcance_minimo", 1.8) or 1.8))

        if abs(self.z - inimigo.z) > 1.5:
            self.bow_charging = False
            self.bow_charge = 0.0
            return

        if self.cooldown_ataque > 0:
            self.bow_charging = False
            self.bow_charge = 0.0
            return

        if self.brain.acao_atual not in acoes_ofensivas:
            self.bow_charging = False
            self.bow_charge = 0.0
            return

        if distancia > alcance or distancia < alcance_min * 0.75:
            self.bow_charging = False
            self.bow_charge = 0.0
            return

        if not self.bow_charging:
            self.bow_charging = True
            self.bow_charge = 0.0
            self.bow_perfect_timer = 0.18
            return

        self.bow_charge = min(1.6, self.bow_charge + dt)
        release_threshold = 0.28 if distancia < alcance * 0.55 else 0.52
        pressured = distancia < max(alcance_min + 0.7, 3.4)
        if pressured:
            release_threshold = min(release_threshold, 0.24)

        if self.bow_charge < release_threshold:
            self.weapon_anim_scale = max(self.weapon_anim_scale, 1.05 + self.bow_charge * 0.2)
            return

        self.atacando = True
        self.timer_animacao = max(0.12, WEAPON_PROFILES.get(controller.animation_key, WEAPON_PROFILES["Reta"]).total_time * (0.82 + min(self.bow_charge, 1.0) * 0.18))
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), controller.animation_key, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        self._disparar_flecha(inimigo)

        base_cd = max(0.38, controller.base_cooldown(self, arma) * (0.92 + min(self.bow_charge, 1.2) * 0.22))
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    def _executar_ataques_foco(self, dt, distancia, inimigo, estilo):
        """Ataques de foco magico com weave de orbes."""
        arma = self.dados.arma_obj
        controller = get_weapon_runtime_controller(arma)
        anim_manager, transform = self._aplicar_animacao_runtime(dt, controller.animation_key, estilo, self.raio_fisico * 2.2)
        if self._consumir_animacao_ativa(dt, transform):
            return
        if self.cooldown_ataque > 0 or abs(self.z - inimigo.z) > 1.5:
            return

        acoes_ofensivas = {"MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"}
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        alcance = controller.attack_range(self, arma)
        if distancia > alcance:
            return

        orbes_orbitando = [o for o in self.buffer_orbes if o.ativo and o.estado == "orbitando"]
        mana_ratio = self.dados.mana / max(self.dados.mana_max, 1) if hasattr(self.dados, "mana_max") else 0.5
        weave_mult = 0.82 if orbes_orbitando else 1.0
        if distancia < 2.2 and not orbes_orbitando:
            weave_mult *= 1.15

        self.atacando = True
        self.timer_animacao = max(0.10, WEAPON_PROFILES.get(controller.animation_key, WEAPON_PROFILES["Reta"]).total_time * (0.76 if orbes_orbitando else 0.92))
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), controller.animation_key, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
        self._disparar_orbes(inimigo)

        base_cd = max(0.42, controller.base_cooldown(self, arma) * (1.08 - min(mana_ratio * 0.18, 0.12)) * weave_mult)
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    # ==================================================================
    # Disparo de projÃ©teis
    # ==================================================================

    def _disparar_arremesso(self, alvo):
        """Dispara projÃ©teis de arma de arremesso â€” v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        qtd = int(getattr(arma, 'quantidade', getattr(arma, 'projeteis_por_ataque', 3)))
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
        vel = float(getattr(arma, "velocidade_projetil", vel) or vel) * (1.0 + volley_bonus)
        spread_base = float(getattr(arma, "spread_base", 25 if qtd > 1 else 0) or 0.0)
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
        """Dispara flecha do arco â€” v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        dano = arma.dano * (self.dados.forca / 2.0 + 0.5)
        forca = getattr(arma, 'forca_arco', getattr(arma, 'perfil_mecanico', {}).get('forca_disparo', 1.0))
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
        vel_flecha = float(getattr(arma, "velocidade_projetil", 35.0 + forca_normalizada * 20.0) or 35.0) * (1.0 + vel_bonus)

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
        """Dispara orbes mÃ¡gicos â€” v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        qtd = int(getattr(arma, 'quantidade', getattr(arma, 'projeteis_por_ataque', 2)))
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

