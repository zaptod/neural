"""Auto-generated mixin â€” see scripts/split_brain.py"""
from dataclasses import dataclass
import random
import math
import logging
from typing import TYPE_CHECKING, Any

_log = logging.getLogger("neural_ai")

from utilitarios.config import PPM
from utilitarios.config import (
    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,
    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,
    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,
    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,
    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,
    AI_RAND_POOL_SIZE,
)
from ia.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,
    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES
)

try:
    from nucleo.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
    WEAPON_ANALYSIS_AVAILABLE = True
except ImportError:
    WEAPON_ANALYSIS_AVAILABLE = False

try:
    from ia.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority
    SKILL_STRATEGY_AVAILABLE = True
except ImportError:
    SKILL_STRATEGY_AVAILABLE = False

if TYPE_CHECKING:
    from ia.skill_strategy import CombatSituation as CombatSituation  # noqa: F811

try:
    from nucleo.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

try:
    from nucleo.arena import get_arena as _get_arena
except ImportError:
    _get_arena = None


from nucleo.skills import get_skill_data
from ia._brain_mixin_base import _AIBrainMixinBase
from ia.weapon_ai import resolver_familia_arma


@dataclass(frozen=True)
class SkillDecisionContext:
    """Snapshot do frame usado pelo pipeline estrategico de skills."""

    dt: float
    distancia: float
    parent: Any
    strategy: Any
    hp_pct: float
    inimigo_hp_pct: float
    mana_pct: float
    tempo_combate: float
    role: str
    plano: Any
    skills: dict[str, Any]
    familia_arma: str
    pacote_id: str
    orbes_orbitando: int
    orbital_burst_pronto: bool
    forma_hibrida: int
    bonus_hibrido: bool
    inimigo_stunado: bool
    inimigo_debuffado: bool
    inimigo_queimando: bool
    inimigo_congelado: bool
    inimigo_reposicionando: bool
    inimigo_atk_iminente: bool
    encurralado: bool
    oponente_encurralado: bool
    inimigo_em_zona: bool
    eu_em_zona: bool
    buffs_ativos: int
    tenho_summons: bool
    orders: dict[str, Any]
    has_team: bool
    team_role: str
    is_weakest: bool


class SkillsMixin(_AIBrainMixinBase):
    """Mixin de uso inteligente de skills (estratÃ©gico + legado)."""

    def _obter_pacote_composto_id(self):
        perfil = getattr(self, "arquetipo_composto", None)
        if not isinstance(perfil, dict):
            return ""
        pacote = perfil.get("pacote_referencia") or {}
        if isinstance(pacote, dict):
            return str(pacote.get("id", "") or "").strip().lower()
        return ""

    def _modular_chance_skill_por_arena(self, chance, sk, distancia):
        """Ajusta a chance conforme perigo da arena e oportunidades ambientais."""
        if sk is None:
            return max(0.05, min(0.98, chance))

        esp = getattr(self, "consciencia_espacial", {})
        em_zona = bool(esp.get("zona_perigo_atual"))
        inimigo_em_zona = bool(esp.get("zona_perigo_inimigo"))
        inimigo_na_borda = bool(esp.get("oponente_contra_parede")) or bool(esp.get("oponente_perto_obstaculo"))
        tipo = sk.tipo
        data = sk.data or {}

        skill_move = (
            tipo in ("DASH", "TRANSFORM")
            or data.get("teleporte")
            or data.get("intangivel")
            or data.get("invencivel")
            or data.get("bonus_velocidade")
        )
        skill_controla = (
            tipo in ("TRAP", "CONTROL", "AREA", "BEAM")
            or data.get("bloqueia_movimento", False)
            or data.get("puxa_continuo")
            or data.get("puxa_para_centro")
            or data.get("slow")
            or data.get("stun")
            or data.get("root")
        )

        if em_zona:
            if skill_move:
                chance *= 1.28
            elif tipo == "BUFF" and (data.get("escudo") or data.get("cura") or data.get("bonus_resistencia")):
                chance *= 1.14
            elif skill_controla and distancia < 4.0:
                chance *= 1.08
            else:
                chance *= 0.78

        if inimigo_em_zona:
            if skill_controla:
                chance *= 1.22
            elif tipo in ("PROJETIL", "BEAM", "AREA"):
                chance *= 1.10

        if inimigo_na_borda and (data.get("bloqueia_movimento", False) or data.get("puxa_para_centro")):
            chance *= 1.18

        return max(0.05, min(0.98, chance))

    def _obter_estado_inimigo_para_skills(self, inimigo):
        """Resolve e cacheia o estado do inimigo usado pelo pipeline de skills."""
        stun_now = getattr(inimigo, "stun_timer", 0) > 0
        slow_now = getattr(inimigo, "slow_timer", 0) > 0
        root_now = getattr(inimigo, "root_timer", 0) > 0
        dots_count = len(getattr(inimigo, "dots_ativos", []))
        fx_count = len(getattr(inimigo, "status_effects", []))
        cache_key = (id(inimigo), stun_now, slow_now, root_now, dots_count, fx_count)
        cache = getattr(self, "_estado_inimigo_cache", None)
        stored_key = getattr(self, "_estado_inimigo_frame", None)

        if cache is None or stored_key != cache_key:
            stunado = self._verificar_inimigo_stunado(inimigo)
            debuffado = self._verificar_inimigo_debuffado(inimigo)
            queimando = any(
                getattr(dot, "tipo", getattr(dot, "nome", "")).upper() in ("QUEIMANDO", "QUEIMAR", "BURNING")
                for dot in getattr(inimigo, "dots_ativos", [])
            ) or any(
                getattr(effect, "nome", "").lower() in ("queimando", "burning")
                for effect in getattr(inimigo, "status_effects", [])
            )
            congelado = getattr(inimigo, "congelado", False) or any(
                getattr(effect, "nome", "").lower() in ("congelado", "frozen")
                for effect in getattr(inimigo, "status_effects", [])
            )
            cache = (stunado, debuffado, queimando, congelado)
            self._estado_inimigo_cache = cache
            self._estado_inimigo_frame = cache_key

        return cache

    def _criar_contexto_skills(self, dt, distancia, inimigo):
        """Agrupa o estado do frame em um contexto imutavel para decisões de skill."""
        strategy = self.skill_strategy
        if strategy is None:
            return None

        p = self.parent
        arma = getattr(getattr(p, "dados", None), "arma_obj", None)
        inimigo_stunado, inimigo_debuffado, inimigo_queimando, inimigo_congelado = self._obter_estado_inimigo_para_skills(inimigo)
        orders = getattr(self, "team_orders", {}) or {}

        return SkillDecisionContext(
            dt=dt,
            distancia=distancia,
            parent=p,
            strategy=strategy,
            hp_pct=p.vida / p.vida_max if p.vida_max > 0 else 1.0,
            inimigo_hp_pct=inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0,
            mana_pct=p.mana / p.mana_max if p.mana_max > 0 else 1.0,
            tempo_combate=self.tempo_combate,
            role=strategy.role_principal.value,
            plano=strategy.plano,
            skills=strategy.skills,
            familia_arma=resolver_familia_arma(arma),
            pacote_id=self._obter_pacote_composto_id(),
            orbes_orbitando=len(
                [
                    orb
                    for orb in getattr(p, "buffer_orbes", [])
                    if getattr(orb, "ativo", False) and getattr(orb, "estado", "") == "orbitando"
                ]
            ),
            orbital_burst_pronto=getattr(p, "orbital_burst_cd", 999.0) <= 0.0,
            forma_hibrida=int(getattr(p, "transform_forma", getattr(arma, "forma_atual", 0)) or 0),
            bonus_hibrido=getattr(p, "transform_bonus_timer", 0.0) > 0.0,
            inimigo_stunado=inimigo_stunado,
            inimigo_debuffado=inimigo_debuffado,
            inimigo_queimando=inimigo_queimando,
            inimigo_congelado=inimigo_congelado,
            inimigo_reposicionando=self.leitura_oponente.get("reposicionando", False),
            inimigo_atk_iminente=self.leitura_oponente.get("ataque_iminente", False),
            encurralado=self.consciencia_espacial.get("encurralado", False),
            oponente_encurralado=self.consciencia_espacial.get("oponente_contra_parede", False),
            inimigo_em_zona=bool(self.consciencia_espacial.get("zona_perigo_inimigo")),
            eu_em_zona=bool(self.consciencia_espacial.get("zona_perigo_atual")),
            buffs_ativos=len(getattr(p, "buffs_ativos", [])),
            tenho_summons=self._contar_summons_ativos() > 0,
            orders=orders,
            has_team=orders.get("alive_count", 1) > 1,
            team_role=orders.get("role", "STRIKER"),
            is_weakest=orders.get("is_weakest", False),
        )

    def _pode_usar_skill_estrategica(self, ctx, nome):
        if nome not in ctx.skills:
            return False

        p = ctx.parent
        sk = ctx.skills[nome]
        custo_efetivo = sk.custo
        if "Mago" in getattr(p, "classe_nome", ""):
            custo_efetivo *= 0.8
        for buff in getattr(p, "buffs_ativos", []):
            if getattr(buff, "custo_mana_metade", False):
                custo_efetivo *= 0.5
                break
        if p.mana < custo_efetivo:
            return False
        if nome in getattr(p, "cd_skills", {}) and p.cd_skills[nome] > 0:
            return False
        if sk.tipo in ctx.strategy.cd_por_tipo and ctx.strategy.cd_por_tipo[sk.tipo] > 0:
            return False
        return True

    def _tentar_skill_estrategica(self, ctx, nome, inimigo, motivo=""):
        if not self._pode_usar_skill_estrategica(ctx, nome):
            return False

        sk = ctx.skills.get(nome)
        if sk and not self._skill_aoe_segura_para_time(sk, inimigo, ctx.has_team):
            return False
        if not self._executar_skill_por_nome(nome):
            return False

        ctx.strategy.registrar_uso_skill(nome)
        self._pos_uso_skill_estrategica(ctx.skills[nome])
        return True

    def _alcance_ok_skill_estrategica(self, ctx, nome, margem=1.25):
        sk = ctx.skills.get(nome)
        if not sk or sk.alcance_efetivo <= 0:
            return True
        return ctx.distancia <= sk.alcance_efetivo * margem

    def _chance_skill_contextual(self, ctx, base, skill_nome=None):
        chance = base
        sk = ctx.skills.get(skill_nome) if skill_nome else None
        tipo_skill = sk.tipo if sk else ""

        if "CALCULISTA" in self.tracos:
            if tipo_skill in ("BUFF", "TRAP", "TRANSFORM", "CHANNEL"):
                chance *= 1.12
            elif tipo_skill in ("PROJETIL", "BEAM", "AREA"):
                chance *= 0.88
        if "PACIENTE" in self.tracos:
            if tipo_skill in ("BUFF", "TRAP", "CONTROL", "CHANNEL"):
                chance *= 1.10
            elif ctx.tempo_combate < 8.0 and tipo_skill in ("AREA", "BEAM"):
                chance *= 0.84
        if "BERSERKER" in self.tracos or "FURIOSO" in self.tracos:
            if tipo_skill in ("AREA", "BEAM", "TRANSFORM", "DASH"):
                chance *= 1.16
            elif tipo_skill == "BUFF" and sk and (sk.data.get("cura") or sk.data.get("escudo")):
                chance *= 0.80
        if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
            if tipo_skill in ("DASH", "TRANSFORM", "PROJETIL", "AREA"):
                chance *= 1.12
            elif tipo_skill == "CHANNEL":
                chance *= 0.78

        if ctx.familia_arma == "foco":
            if tipo_skill in ("PROJETIL", "BEAM", "BUFF") and ctx.orbes_orbitando >= 2:
                chance *= 1.12
            if ctx.orbes_orbitando == 0 and ctx.distancia < 2.6 and tipo_skill in ("PROJETIL", "BEAM", "AREA"):
                chance *= 0.82
        elif ctx.familia_arma == "orbital":
            if ctx.orbital_burst_pronto and tipo_skill in ("CONTROL", "AREA", "BUFF", "TRANSFORM"):
                chance *= 1.10
            elif not ctx.orbital_burst_pronto and tipo_skill == "BUFF":
                chance *= 0.92
            if ctx.pacote_id == "bastiao_prismatico":
                if tipo_skill in ("BUFF", "CONTROL", "TRAP"):
                    chance *= 1.16
                if tipo_skill == "PROJETIL":
                    chance *= 1.08 if ctx.distancia <= 3.1 else 0.96
                if tipo_skill in ("PROJETIL", "BEAM", "AREA"):
                    chance *= 0.86 if ctx.distancia < 2.7 else 0.92
                if tipo_skill == "CHANNEL":
                    chance *= 0.58
                if tipo_skill == "DASH":
                    chance *= 0.72
                if ctx.mana_pct < 0.42 and tipo_skill in ("PROJETIL", "BEAM", "AREA"):
                    chance *= 0.74
                if ctx.mana_pct < 0.46 and tipo_skill == "CHANNEL":
                    chance *= 0.54
                if ctx.mana_pct < 0.34 and tipo_skill == "BUFF":
                    chance *= 0.90
            elif ctx.pacote_id == "artilheiro_de_orbita":
                if tipo_skill in ("PROJETIL", "BEAM"):
                    preferida = ctx.strategy.preferencias.get("distancia_preferida", 4.0) * 0.82
                    chance *= 1.18 if ctx.distancia >= max(3.1, preferida) else 0.80
                if tipo_skill in ("BUFF", "CONTROL", "AREA") and ctx.distancia < 2.9:
                    chance *= 0.80
                if tipo_skill == "CHANNEL":
                    chance *= 0.44
                if tipo_skill == "SUMMON":
                    chance *= 0.78
                if tipo_skill == "AREA":
                    chance *= 0.74
                if ctx.mana_pct < 0.38 and tipo_skill not in ("PROJETIL", "BEAM"):
                    chance *= 0.72
                if ctx.mana_pct < 0.48 and tipo_skill == "CHANNEL":
                    chance *= 0.52
        elif ctx.familia_arma == "hibrida":
            if tipo_skill == "TRANSFORM" and not ctx.bonus_hibrido:
                chance *= 1.18
            if ctx.bonus_hibrido and tipo_skill in ("DASH", "PROJETIL", "BEAM", "AREA"):
                chance *= 1.15
            if ctx.forma_hibrida == 1 and tipo_skill == "DASH":
                chance *= 0.84

        return self._modular_chance_skill_por_arena(chance, sk, ctx.distancia)

    def _ordenar_skills_por_dano(self, ctx, nomes):
        return sorted(nomes, key=lambda nome: getattr(ctx.skills.get(nome), "dano_total", 0), reverse=True)

    def _tentar_prioridade_time_skills(self, ctx, inimigo):
        if ctx.has_team and ctx.team_role == "SUPPORT" and not ctx.is_weakest:
            weakest_ally_hp = 1.0
            awareness = getattr(self, "multi_awareness", {}) or {}
            for aliado in awareness.get("aliados", []):
                weakest_ally_hp = min(weakest_ally_hp, aliado["vida_pct"])

            if weakest_ally_hp < 0.4:
                for nome in list(ctx.plano.sustains) + list(ctx.plano.rotacao_critical):
                    sk = ctx.skills.get(nome)
                    if sk and sk.tipo == "BUFF" and (
                        sk.data.get("cura")
                        or sk.data.get("cura_por_segundo")
                        or sk.data.get("escudo")
                        or sk.data.get("buff_defesa")
                    ):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "team_suporte_aliado"):
                            return True

            if weakest_ally_hp > 0.6 and ctx.mana_pct > 0.5 and ctx.buffs_ativos == 0:
                for nome, sk in ctx.skills.items():
                    if sk.tipo == "BUFF" and sk.data.get("buff_dano"):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "team_suporte_buff"):
                            return True

        if ctx.has_team and ctx.team_role == "CONTROLLER" and ctx.mana_pct > 0.3:
            ally_intents = ctx.orders.get("ally_intents", {})
            striker_ready = any(
                getattr(intent, "action", "") in ("MATAR", "ESMAGAR", "PRESSIONAR")
                for intent in ally_intents.values()
            )
            if striker_ready and not ctx.inimigo_stunado:
                for nome in ctx.plano.controls:
                    if self._alcance_ok_skill_estrategica(ctx, nome, 1.15):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "team_cc_para_burst"):
                            return True

        return False

    def _tentar_prioridade_sobrevivencia_skills(self, ctx, inimigo):
        if ctx.hp_pct < 0.28:
            for nome in list(ctx.plano.sustains) + list(ctx.plano.escapes):
                sk = ctx.skills.get(nome)
                if sk and (sk.data.get("invencivel") or sk.data.get("intangivel")):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_invencivel"):
                        return True

            cura_candidatos = [
                (
                    nome,
                    ctx.skills[nome].data.get("cura", 0)
                    + ctx.skills[nome].data.get("cura_por_segundo", 0) * 3
                    + (ctx.skills[nome].data.get("cura_percent", 0) * ctx.parent.vida_max),
                )
                for nome in ctx.plano.rotacao_critical
                if nome in ctx.skills
                and ctx.skills[nome].tipo in ("BUFF", "AREA")
                and (
                    ctx.skills[nome].data.get("cura")
                    or ctx.skills[nome].data.get("cura_por_segundo")
                    or ctx.skills[nome].data.get("cura_percent")
                )
            ]
            for nome, _ in sorted(cura_candidatos, key=lambda item: -item[1]):
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_cura"):
                    return True

            for nome in ctx.plano.sustains:
                sk = ctx.skills.get(nome)
                if sk and sk.data.get("escudo"):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_escudo"):
                        return True

            for nome, sk in ctx.skills.items():
                if sk.tipo == "TRANSFORM" and sk.data.get("bonus_resistencia", 0) > 0.2:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_transform_defensiva"):
                        return True

            if ctx.distancia < 7.0:
                for nome, sk in ctx.skills.items():
                    if sk.data.get("lifesteal", 0) > 0.3 and sk.dano_total > 20:
                        if self._alcance_ok_skill_estrategica(ctx, nome, 1.1):
                            if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_lifesteal"):
                                return True

            if ctx.inimigo_atk_iminente or ctx.hp_pct < 0.18:
                for nome in ctx.plano.escapes:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_escape"):
                        return True

            if ctx.hp_pct < 0.22 and ctx.distancia < 3.0:
                for nome in ctx.plano.controls:
                    if self._alcance_ok_skill_estrategica(ctx, nome, 1.1):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "emergencia_cc_defensivo"):
                            return True

        if ctx.eu_em_zona:
            for nome in list(ctx.plano.escapes) + list(ctx.plano.controls) + list(ctx.plano.sustains):
                sk = ctx.skills.get(nome)
                if not sk:
                    continue
                if self._modular_chance_skill_por_arena(0.92, sk, ctx.distancia) >= 0.88:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "escape_zona_perigosa"):
                        return True

        return False

    def _tentar_prioridade_reacao_skills(self, ctx, inimigo):
        if not ctx.inimigo_atk_iminente or ctx.hp_pct <= 0.28:
            return False

        for nome in ctx.plano.controls:
            if self._alcance_ok_skill_estrategica(ctx, nome, 1.1) and ctx.mana_pct > 0.20:
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "cc_preventivo"):
                    return True

        if ctx.role in ("artillery", "control_mage") or self.medo > 0.5:
            for nome in ctx.plano.escapes:
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "escape_preemptivo"):
                    return True

        return False

    def _tentar_prioridade_janela_cc_skills(self, ctx, inimigo):
        condicao_cc = ctx.inimigo_reposicionando or ctx.distancia > 4.5 or (ctx.oponente_encurralado and ctx.distancia < 7.0)
        if condicao_cc and ctx.mana_pct > 0.22 and not ctx.inimigo_stunado:
            for nome in ctx.plano.controls:
                sk = ctx.skills.get(nome)
                if not sk:
                    continue
                if ctx.inimigo_reposicionando and ctx.distancia < 2.5 and sk.cooldown > 8:
                    continue
                if self._alcance_ok_skill_estrategica(ctx, nome, 1.15):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "janela_cc"):
                        return True

        if ctx.inimigo_em_zona and ctx.mana_pct > 0.18:
            for nome, sk in ctx.skills.items():
                if sk.tipo in ("TRAP", "CONTROL", "AREA", "BEAM") or sk.data.get("bloqueia_movimento", False) or sk.data.get("puxa_para_centro"):
                    if self._alcance_ok_skill_estrategica(ctx, nome, 1.2):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "punir_zona_perigosa"):
                            return True

        return False

    def _tentar_prioridade_combo_skills(self, ctx, inimigo):
        if ctx.mana_pct <= 0.40:
            return False

        if ctx.inimigo_queimando:
            for nome, sk in ctx.skills.items():
                if sk.data.get("condicao") == "ALVO_QUEIMANDO" and self._alcance_ok_skill_estrategica(ctx, nome):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "payload_queimando"):
                        return True

        if ctx.inimigo_congelado:
            for nome, sk in ctx.skills.items():
                if sk.data.get("condicao") == "ALVO_CONGELADO" and self._alcance_ok_skill_estrategica(ctx, nome):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "payload_congelado"):
                        return True

        ultima = ctx.strategy.ultima_skill
        if ultima and ultima in ctx.skills and ctx.skills[ultima].elemento:
            ultimo_elem = ctx.skills[ultima].elemento
            for nome, sk in ctx.skills.items():
                if not sk.elemento or sk.elemento == ultimo_elem:
                    continue
                if not self._pode_usar_skill_estrategica(ctx, nome) or not self._alcance_ok_skill_estrategica(ctx, nome, 1.2):
                    continue
                for combo_entry in ctx.strategy.plano.combos:
                    if len(combo_entry) >= 3 and "elemental_" in combo_entry[2]:
                        if combo_entry[0] == ultima and combo_entry[1] == nome:
                            if self._tentar_skill_estrategica(ctx, nome, inimigo, f"reaction_chain_{combo_entry[2]}"):
                                return True

        inimigo_marcado = any(
            getattr(effect, "nome", "").lower() in ("marcado", "marked")
            for effect in getattr(inimigo, "status_effects", [])
        )
        if inimigo_marcado:
            void_skills = [
                (nome, sk)
                for nome, sk in ctx.skills.items()
                if sk.elemento == "VOID" and sk.dano_total > 15 and self._alcance_ok_skill_estrategica(ctx, nome)
            ]
            void_skills.sort(key=lambda item: item[1].dano_total, reverse=True)
            for nome, _ in void_skills:
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "void_marcado_double"):
                    return True
            for nome in ctx.plano.bursts:
                if self._alcance_ok_skill_estrategica(ctx, nome):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "burst_sobre_marcado"):
                        return True

        combo = ctx.strategy.get_combo_recomendado()
        if not combo:
            return False

        sk1, sk2, razao = combo
        custo_total = (ctx.skills[sk1].custo if sk1 in ctx.skills else 9999) + (ctx.skills[sk2].custo if sk2 in ctx.skills else 9999)
        if ctx.parent.mana < custo_total * 0.88:
            return False

        chance_combo = 0.75 if (ctx.inimigo_stunado or ctx.oponente_encurralado) else 0.50
        if "elemental_" in razao:
            chance_combo = min(0.90, chance_combo + 0.20)
        chance_combo = self._chance_skill_contextual(ctx, chance_combo, sk1)
        if random.random() >= chance_combo:
            return False
        if not self._alcance_ok_skill_estrategica(ctx, sk1, 1.15):
            return False
        if not self._tentar_skill_estrategica(ctx, sk1, inimigo, f"combo_setup_{razao}"):
            return False

        self.combo_state["em_combo"] = True
        self.combo_state["pode_followup"] = True
        self.combo_state["timer_followup"] = 0.5
        self._proximo_skill_combo = sk2
        return True

    def _tentar_prioridade_execucao_skills(self, ctx, inimigo):
        if ctx.inimigo_hp_pct >= 0.32:
            return False

        ally_intents = ctx.orders.get("ally_intents", {})
        allies_on_this = (
            sum(
                1
                for intent in ally_intents.values()
                if getattr(intent, "target_id", 0) == id(inimigo)
                and getattr(intent, "action", "") in ("MATAR", "ESMAGAR", "PRESSIONAR")
            )
            if ctx.has_team
            else 0
        )
        skip_expensive_finisher = allies_on_this >= 2 and ctx.inimigo_hp_pct > 0.10

        if not skip_expensive_finisher:
            for nome in self._ordenar_skills_por_dano(ctx, ctx.plano.finishers):
                if self._alcance_ok_skill_estrategica(ctx, nome, 1.30):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "execucao_finisher"):
                        return True

        for nome in self._ordenar_skills_por_dano(ctx, ctx.plano.bursts):
            if self._alcance_ok_skill_estrategica(ctx, nome, 1.25):
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "execucao_burst"):
                    return True

        if ctx.inimigo_hp_pct < 0.15:
            for nome, sk in ctx.skills.items():
                if sk.dano_total > 0 and self._alcance_ok_skill_estrategica(ctx, nome, 1.2):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "execucao_desesperada"):
                        return True

        return False

    def _tentar_prioridade_burst_skills(self, ctx, inimigo):
        if not (ctx.inimigo_stunado or ctx.inimigo_debuffado) or ctx.mana_pct <= 0.25:
            return False

        chance_burst = 0.95 if ctx.inimigo_stunado else 0.80
        for nome in self._ordenar_skills_por_dano(ctx, ctx.plano.bursts):
            if self._alcance_ok_skill_estrategica(ctx, nome, 1.30) and random.random() < chance_burst:
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "burst_window"):
                    return True

        if ctx.inimigo_stunado:
            for nome, sk in ctx.skills.items():
                if sk.tipo == "AREA" and self._alcance_ok_skill_estrategica(ctx, nome):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "area_sobre_stunado"):
                        return True
            if ctx.distancia < 4.0:
                for nome, sk in ctx.skills.items():
                    if sk.tipo == "CHANNEL" and self._alcance_ok_skill_estrategica(ctx, nome):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "channel_sobre_stunado"):
                            return True

        if ctx.inimigo_debuffado:
            for nome, sk in ctx.skills.items():
                if sk.data.get("penetra_escudo") and self._alcance_ok_skill_estrategica(ctx, nome):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "penetra_sobre_debuffado"):
                        return True

        return False

    def _tentar_prioridade_opener_skills(self, ctx, inimigo):
        if ctx.tempo_combate < 8.0:
            for nome in ctx.plano.rotacao_opening:
                sk = ctx.skills.get(nome)
                if not sk:
                    continue
                if sk.tipo == "BUFF" and sk.data.get("buff_dano") and ctx.buffs_ativos == 0:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_buff_dano"):
                        return True
                elif sk.tipo == "BUFF" and (sk.data.get("lifesteal_global") or sk.data.get("bonus_resistencia")):
                    if ctx.buffs_ativos == 0 and self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_buff_sustain"):
                        return True
                elif sk.tipo == "SUMMON" and not ctx.tenho_summons and ctx.strategy.cd_por_tipo.get("SUMMON", 0) <= 0:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_summon"):
                        return True
                elif sk.tipo == "TRANSFORM":
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_transform"):
                        return True
                elif sk.tipo == "TRAP" and self._contar_traps_ativos() < 2:
                    if not sk.data.get("bloqueia_movimento", False):
                        if self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_trap_trigger"):
                            return True
                elif sk.tipo == "BUFF" and sk.data.get("escudo") and ctx.hp_pct < 0.7:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_escudo"):
                        return True

            for nome, sk in ctx.skills.items():
                if sk.data.get("efeito") == "MARCADO" and self._alcance_ok_skill_estrategica(ctx, nome, 1.15):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "opener_marca"):
                        return True

        return False

    def _tentar_prioridade_poke_skills(self, ctx, inimigo):
        poke_dist_ok = ctx.distancia > 3.0 if ctx.role in ("artillery", "control_mage", "burst_mage") else ctx.distancia > 5.0
        if not poke_dist_ok or ctx.mana_pct <= 0.30:
            return False

        chance_poke = {
            "artillery": 0.88,
            "control_mage": 0.80,
            "burst_mage": 0.70,
            "summoner": 0.60,
            "battle_mage": 0.45,
            "trap_master": 0.75,
            "channeler": 0.72,
        }.get(ctx.role, 0.38)
        if "SPAMMER" in self.tracos:
            chance_poke = min(0.96, chance_poke + 0.14)
        if "CALCULISTA" in self.tracos:
            chance_poke *= 0.80
        if ctx.mana_pct < 0.45:
            chance_poke *= 0.7
        if random.random() >= chance_poke:
            return False

        poke_list = list(ctx.plano.pokes)
        if ctx.mana_pct < 0.50:
            poke_list.sort(key=lambda nome: ctx.skills[nome].dano_por_mana if nome in ctx.skills else 0, reverse=True)
        for nome in poke_list:
            if random.random() < self._chance_skill_contextual(ctx, 0.92, nome):
                if self._alcance_ok_skill_estrategica(ctx, nome, 1.12):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "poke"):
                        return True

        traps_ativos = self._contar_traps_ativos()
        if traps_ativos >= 3:
            return False

        for nome, sk in ctx.skills.items():
            if sk.tipo != "TRAP":
                continue
            if sk.data.get("bloqueia_movimento", False):
                if ctx.inimigo_atk_iminente or ctx.distancia < 4.0:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "wall_zoning_defensivo"):
                        return True
            else:
                if self._tentar_skill_estrategica(ctx, nome, inimigo, "trap_zoning_trigger"):
                    return True

        return False

    def _tentar_prioridade_manutencao_skills(self, ctx, inimigo):
        if not ctx.tenho_summons and ctx.mana_pct > 0.45 and ctx.tempo_combate > 5.0:
            for nome, sk in ctx.skills.items():
                if sk.tipo == "SUMMON" and ctx.strategy.cd_por_tipo.get("SUMMON", 0) <= 0:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "manutencao_summon"):
                        return True

        traps_ativos_agora = self._contar_traps_ativos()
        if traps_ativos_agora < 2 and ctx.mana_pct > 0.40 and ctx.tempo_combate > 6.0:
            for nome, sk in ctx.skills.items():
                if sk.tipo == "TRAP" and ctx.strategy.cd_por_tipo.get("TRAP", 0) <= 0:
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "manutencao_trap"):
                        return True

        if ctx.buffs_ativos == 0 and ctx.mana_pct > 0.35 and ctx.tempo_combate > 6.0:
            for nome, sk in ctx.skills.items():
                if sk.tipo == "BUFF" and sk.data.get("buff_dano"):
                    if self._tentar_skill_estrategica(ctx, nome, inimigo, "manutencao_buff"):
                        return True

        return False

    def _tentar_prioridade_rotacao_skills(self, ctx, inimigo):
        if not SKILL_STRATEGY_AVAILABLE:
            return False

        situacao = CombatSituation(
            distancia=ctx.distancia,
            meu_hp_percent=ctx.hp_pct,
            inimigo_hp_percent=ctx.inimigo_hp_pct,
            meu_mana_percent=ctx.mana_pct,
            estou_encurralado=ctx.encurralado,
            inimigo_encurralado=ctx.oponente_encurralado,
            inimigo_atacando=ctx.inimigo_atk_iminente,
            inimigo_stunado=ctx.inimigo_stunado,
            tenho_summons_ativos=self._contar_summons_ativos(),
            tenho_traps_ativos=self._contar_traps_ativos(),
            tenho_buffs_ativos=ctx.buffs_ativos,
            inimigo_debuffado=ctx.inimigo_debuffado,
            momentum=self.momentum,
            tempo_combate=ctx.tempo_combate,
        )
        resultado = ctx.strategy.obter_melhor_skill(situacao)
        if not resultado:
            return False

        sk_profile, razao = resultado
        chance = {
            "artillery": 0.88,
            "burst_mage": 0.85,
            "control_mage": 0.83,
            "summoner": 0.80,
            "buffer": 0.78,
            "channeler": 0.80,
            "battle_mage": 0.65,
            "dasher": 0.60,
            "transformer": 0.60,
        }.get(ctx.role, 0.52)
        if "SPAMMER" in self.tracos:
            chance = min(0.96, chance + 0.12)
        if "CALCULISTA" in self.tracos:
            chance *= 0.82
        if self.modo_burst:
            chance = 0.96
        if not self._alcance_ok_skill_estrategica(ctx, sk_profile.nome, 1.40):
            chance *= 0.22
        chance = self._chance_skill_contextual(ctx, chance, sk_profile.nome)
        if random.random() >= chance:
            return False
        if not self._executar_skill_por_nome(sk_profile.nome):
            return False

        ctx.strategy.registrar_uso_skill(sk_profile.nome)
        self._pos_uso_skill_estrategica(sk_profile)
        return True


    # =========================================================================
    # SKILLS - SISTEMA INTELIGENTE v1.0
    # =========================================================================
    
    def _processar_skills(self, dt, distancia, inimigo):
        """Processa uso de skills com sistema de estratÃ©gia inteligente"""
        p = self.parent
        
        # Atualiza timers do strategy ANTES do gate (para cd_por_tipo decrementar)
        if self.skill_strategy is not None:
            self.skill_strategy.atualizar(dt)
        
        # Verifica GCD global (curto â€” per-skill CDs controlam spam)
        if hasattr(p, 'cd_skill_arma') and p.cd_skill_arma > 0:
            return False
        
        # TraÃ§o CONSERVADOR reduz uso de skills
        if "CONSERVADOR" in self.tracos and p.mana < p.mana_max * 0.4:
            if random.random() > 0.2:
                return False
        
        # === USA SISTEMA DE ESTRATÃ‰GIA SE DISPONÃVEL ===
        if self.skill_strategy is not None:
            return self._processar_skills_estrategico(dt, distancia, inimigo)

        # === FALLBACK: Sistema legado ===
        # LEGADO-03 (Sprint 4): este caminho Ã© ativado apenas quando o personagem nÃ£o
        # possui skills catalogadas pelo SkillStrategySystem (skill_strategy = None),
        # tipicamente personagens bÃ¡sicos sem skills de arma registradas.
        #
        # Os mÃ©todos legados (_tentar_dash_ofensivo, _tentar_usar_buff, etc.) usam
        # lÃ³gica simplificada superada pelo sistema estratÃ©gico.
        # TODO Sprint 5 (MEL-ARQ-01): avaliar se esses mÃ©todos podem ser removidos ou
        # absorvidos como regras de fallback dentro de _processar_skills_estrategico.
        #
        # Guarda: se nÃ£o hÃ¡ nenhuma skill registrada, nÃ£o tenta executar nada.
        tem_skills = any(len(v) > 0 for v in self.skills_por_tipo.values())
        if not tem_skills:
            return False

        if self._tentar_dash_ofensivo(distancia, inimigo):
            return True
        if self._tentar_usar_buff(distancia, inimigo):
            return True
        if self._tentar_usar_ofensiva(distancia, inimigo):
            return True
        if self._tentar_usar_summon(distancia, inimigo):
            return True
        if self._tentar_usar_trap(distancia, inimigo):
            return True

        return False

    
    def _processar_skills_estrategico(self, dt, distancia, inimigo):
        ctx = self._criar_contexto_skills(dt, distancia, inimigo)
        if ctx is None:
            return False

        for handler in (
            self._tentar_prioridade_time_skills,
            self._tentar_prioridade_sobrevivencia_skills,
            self._tentar_prioridade_reacao_skills,
            self._tentar_prioridade_janela_cc_skills,
            self._tentar_prioridade_combo_skills,
            self._tentar_prioridade_execucao_skills,
            self._tentar_prioridade_burst_skills,
            self._tentar_prioridade_opener_skills,
            self._tentar_prioridade_poke_skills,
            self._tentar_prioridade_manutencao_skills,
        ):
            if handler(ctx, inimigo):
                return True

        return self._tentar_prioridade_rotacao_skills(ctx, inimigo)



    def _distancia_ponto_segmento(self, ponto, inicio, fim):
        """Retorna a distÃƒÂ¢ncia de um ponto a um segmento."""
        px, py = ponto
        x1, y1 = inicio
        x2, y2 = fim
        dx = x2 - x1
        dy = y2 - y1
        seg_len2 = dx * dx + dy * dy
        if seg_len2 <= 1e-9:
            return math.hypot(px - x1, py - y1)

        t = ((px - x1) * dx + (py - y1) * dy) / seg_len2
        t = max(0.0, min(1.0, t))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)


    def _aliados_em_risco_por_skill(self, skill_profile, inimigo=None):
        """Retorna aliados que realmente estÃƒÂ£o na geometria de risco da skill."""
        if not skill_profile or skill_profile.tipo not in ("AREA", "BEAM"):
            return []

        ma = getattr(self, 'multi_awareness', {}) or {}
        aliados = ma.get("aliados", [])
        if not aliados:
            return []

        p = self.parent
        origem = (p.pos[0], p.pos[1])
        em_risco = []

        if skill_profile.tipo == "AREA":
            raio = (
                skill_profile.data.get("raio_area", 0.0)
                or skill_profile.data.get("raio", 0.0)
                or skill_profile.alcance_efetivo
                or 2.0
            )
            for aliado in aliados:
                lutador = aliado.get("lutador")
                if not lutador:
                    continue
                dist = math.hypot(lutador.pos[0] - origem[0], lutador.pos[1] - origem[1])
                margem = getattr(lutador, 'raio_fisico', 0.35)
                if dist <= raio + margem:
                    em_risco.append(aliado)
            return em_risco

        alcance = skill_profile.data.get("alcance", 0.0) or skill_profile.alcance_efetivo or 5.0
        angulo = math.radians(getattr(p, 'angulo_olhar', 0.0))
        destino = (
            origem[0] + math.cos(angulo) * alcance,
            origem[1] + math.sin(angulo) * alcance,
        )
        if inimigo is not None:
            destino = (inimigo.pos[0], inimigo.pos[1])

        largura = skill_profile.data.get("largura", 8.0)
        semi_largura = max(0.35, largura / 50.0)

        for aliado in aliados:
            lutador = aliado.get("lutador")
            if not lutador:
                continue
            dist = self._distancia_ponto_segmento((lutador.pos[0], lutador.pos[1]), origem, destino)
            margem = getattr(lutador, 'raio_fisico', 0.35)
            if dist <= semi_largura + margem:
                em_risco.append(aliado)

        return em_risco


    def _skill_aoe_segura_para_time(self, skill_profile, inimigo=None, has_team=None):
        """Valida friendly fire real antes de permitir AREA/BEAM."""
        if not skill_profile or skill_profile.tipo not in ("AREA", "BEAM"):
            return True

        if has_team is None:
            has_team = getattr(self, 'team_orders', {}).get("alive_count", 1) > 1
        if not has_team:
            return True

        aliados_em_risco = self._aliados_em_risco_por_skill(skill_profile, inimigo)
        if not aliados_em_risco:
            return True

        ma = getattr(self, 'multi_awareness', {}) or {}
        if skill_profile.tipo == "BEAM" and ma.get("aliado_no_caminho", False):
            return random.random() >= 0.90

        return random.random() >= 0.75


    def _executar_skill_por_nome(self, nome_skill):
        """Executa uma skill pelo nome"""
        p = self.parent
        
        # Verifica nas skills da arma (COM ÃNDICE!)
        for idx, skill_info in enumerate(getattr(p, 'skills_arma', [])):
            if skill_info.get("nome") == nome_skill:
                if hasattr(p, 'usar_skill_arma'):
                    resultado = p.usar_skill_arma(skill_idx=idx)
                    if resultado:
                        _log.debug("[SKILL] %s usou skill de arma: %s", p.dados.nome, nome_skill)  # QC-02
                    return resultado
        
        # Verifica nas skills da classe
        for skill_info in getattr(p, 'skills_classe', []):
            if skill_info.get("nome") == nome_skill:
                if hasattr(p, 'usar_skill_classe'):
                    resultado = p.usar_skill_classe(nome_skill)
                    if resultado:
                        _log.debug("[SKILL] %s usou skill de classe: %s", p.dados.nome, nome_skill)  # QC-02
                    return resultado
        
        # LEGADO-04 fix: o fallback por Ã­ndice 0 pode usar a skill errada silenciosamente.
        # Mantemos apenas se o nome coincide explicitamente com skill_arma_nome,
        # e logamos como warning para rastreabilidade.
        if nome_skill == getattr(p, 'skill_arma_nome', None):
            if hasattr(p, 'usar_skill_arma'):
                resultado = p.usar_skill_arma(skill_idx=0)
                if resultado:
                    _log.warning(
                        "[SKILL LEGADA] %s: skill '%s' nÃ£o encontrada por nome â€” "
                        "usando Ã­ndice 0 como fallback de compatibilidade.",
                        p.dados.nome, nome_skill
                    )
                return resultado
        
        return False

    
    def _pos_uso_skill_estrategica(self, skill_profile):
        """Define aÃ§Ã£o apÃ³s usar uma skill baseada na estratÃ©gia v3.1"""
        tipo = skill_profile.tipo
        p = self.parent
        arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        familia_arma = resolver_familia_arma(arma)
        pacote_id = self._obter_pacote_composto_id()
        orbes_orbitando = len([
            o for o in getattr(p, 'buffer_orbes', [])
            if getattr(o, 'ativo', False) and getattr(o, 'estado', '') == "orbitando"
        ])
        forma_hibrida = int(getattr(p, 'transform_forma', getattr(arma, 'forma_atual', 0)) or 0)

        if tipo == "DASH":
            if familia_arma == "hibrida" and forma_hibrida == 1:
                self.acao_atual = "POKE"
            elif skill_profile.data.get("dano_chegada", 0) > 0:
                self.acao_atual = "MATAR"
            else:
                # Dash sem dano = reposicionamento, agir de acordo
                self.acao_atual = "COMBATE"
        elif tipo == "SUMMON":
            # ApÃ³s invocar, recuar para deixar o summon lutar
            if familia_arma == "orbital":
                self.acao_atual = "COMBATE"
            elif self.skill_strategy.preferencias.get("estilo_kite"):
                self.acao_atual = "RECUAR"
            else:
                self.acao_atual = "PRESSIONAR"
        elif tipo == "TRAP":
            if skill_profile.data.get("bloqueia_movimento", False):
                # Wall colocada: recuar para atrÃ¡s da muralha
                self.acao_atual = "RECUAR"
            else:
                # Trigger trap colocada: recuar para atrair inimigo sobre ela
                self.acao_atual = "RECUAR"
        elif tipo == "TRANSFORM":
            # Transformado = agressivo
            if familia_arma == "hibrida" and ("CALCULISTA" in self.tracos or "PACIENTE" in self.tracos):
                self.acao_atual = "COMBATE" if forma_hibrida == 0 else "POKE"
            else:
                self.acao_atual = "MATAR"
        elif tipo == "BUFF":
            if skill_profile.data.get("buff_velocidade"):
                if self.medo > 0.4:
                    self.acao_atual = "FUGIR"
                else:
                    self.acao_atual = "APROXIMAR"
            elif skill_profile.data.get("cura"):
                # Curou: manter distÃ¢ncia segura enquanto cura faz efeito
                self.acao_atual = "RECUAR"
            else:
                if familia_arma == "orbital":
                    if pacote_id == "bastiao_prismatico":
                        self.acao_atual = "COMBATE" if getattr(p, 'orbital_burst_cd', 999.0) <= 1.0 else "CIRCULAR"
                    elif pacote_id == "artilheiro_de_orbita":
                        self.acao_atual = "POKE" if getattr(p, 'orbital_burst_cd', 999.0) > 1.0 else "COMBATE"
                    else:
                        self.acao_atual = "COMBATE" if getattr(p, 'orbital_burst_cd', 999.0) <= 1.0 else "PRESSIONAR"
                elif familia_arma == "foco" and ("CALCULISTA" in self.tracos or "PACIENTE" in self.tracos):
                    self.acao_atual = "POKE"
                else:
                    self.acao_atual = "PRESSIONAR"
        elif tipo in ["PROJETIL", "BEAM"]:
            if familia_arma == "foco":
                self.acao_atual = "COMBATE" if orbes_orbitando >= 1 else ("RECUAR" if "PACIENTE" in self.tracos else "CIRCULAR")
            elif familia_arma == "orbital" and pacote_id == "artilheiro_de_orbita":
                self.acao_atual = "POKE"
            elif familia_arma == "orbital" and pacote_id == "bastiao_prismatico":
                self.acao_atual = "COMBATE"
            elif familia_arma == "hibrida":
                self.acao_atual = "POKE" if forma_hibrida == 1 else "MATAR"
            elif self.estilo_luta in ["KITE", "RANGED"]:
                self.acao_atual = "RECUAR"
            else:
                # Projetil lanÃ§ado: pressionar enquanto projÃ©til voa
                self.acao_atual = "COMBATE"
        elif tipo == "AREA":
            if familia_arma == "orbital":
                self.acao_atual = "CIRCULAR" if pacote_id == "artilheiro_de_orbita" else "COMBATE"
            else:
                self.acao_atual = "MATAR"
        elif tipo == "CHANNEL":
            # BUG-A1 fix: "COMBATE" causava movimento ativo que interrompia o canal.
            # "BLOQUEAR" gera strafe mÃ­nimo (mantÃ©m posiÃ§Ã£o aproximada) e Ã©
            # reconhecido por executar_movimento() como estado de baixa mobilidade.
            self.acao_atual = "BLOQUEAR"


    def _tentar_dash_ofensivo(self, distancia, inimigo):
        """Dash ofensivo"""
        if self.cd_dash > 0:
            return False
        
        dash_skills = self.skills_por_tipo.get("DASH", [])
        if not dash_skills:
            return False
        
        p = self.parent
        
        for skill in dash_skills:
            data = skill["data"]
            dist_dash = data.get("distancia", 3.0)
            
            usar = False
            
            if self.arquetipo in ["ASSASSINO", "NINJA", "ACROBATA", "SOMBRA"]:
                if distancia > 4.0 and distancia < dist_dash + 3.5:
                    if self.confianca > 0.35 or self.raiva > 0.4:
                        usar = True
            
            if self.modo_berserk or "BERSERKER" in self.tracos:
                if distancia > 3.0:
                    usar = True
            
            if "FLANQUEADOR" in self.tracos and random.random() < 0.08:
                if self._usar_skill(skill):
                    self.dir_circular *= -1
                    self.acao_atual = "FLANQUEAR"
                    self.cd_dash = 2.0
                    return True
            
            if "ACROBATA" in self.tracos and random.random() < 0.06:
                usar = True
            
            if usar and self._usar_skill(skill):
                self.acao_atual = "MATAR"
                self.cd_dash = 2.5
                return True
        
        return False


    def _tentar_usar_buff(self, distancia, inimigo):
        """Usa buffs"""
        if self.cd_buff > 0:
            return False
        
        buff_skills = self.skills_por_tipo.get("BUFF", [])
        if not buff_skills:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0  # FP-N01
        
        for skill in buff_skills:
            data = skill["data"]
            usar = False
            
            if data.get("cura"):
                threshold = 0.55 if "CAUTELOSO" in self.tracos else 0.40
                if hp_pct < threshold:
                    usar = True
            elif data.get("escudo"):
                if distancia < 5.0 and hp_pct > 0.6 and random.random() < 0.1:
                    usar = True
                if self.hits_recebidos_recente >= 2:
                    usar = True
            elif data.get("buff_dano"):
                if distancia < 4.0 and self.confianca > 0.5:
                    usar = random.random() < 0.15
                if "EXPLOSIVO" in self.tracos and inimigo.vida < inimigo.vida_max * 0.4:
                    usar = True
                if self.modo_burst:
                    usar = True
            elif data.get("buff_velocidade"):
                if distancia > 6.0 and "PERSEGUIDOR" in self.tracos:
                    usar = True
                if hp_pct < 0.35 and distancia < 4.0:
                    usar = True
            
            if usar and self._usar_skill(skill):
                self.cd_buff = 3.0
                return True
        
        return False


    def _tentar_usar_ofensiva(self, distancia, inimigo):
        """Usa skills ofensivas"""
        p = self.parent
        
        chance = self.agressividade_base
        if "SPAMMER" in self.tracos:
            chance += 0.25
        if self.raiva > 0.6:
            chance += 0.15
        if self.modo_burst:
            chance += 0.3
        if "CALCULISTA" in self.tracos:
            chance -= 0.1
        
        if random.random() > chance:
            return False
        
        # ProjÃ©teis
        for skill in self.skills_por_tipo.get("PROJETIL", []):
            data = skill["data"]
            alcance = data.get("vida", 1.5) * data.get("velocidade", 8.0) * 0.8
            
            usar = False
            if self.arquetipo in ["MAGO", "MAGO_AGRESSIVO", "ARQUEIRO", "INVOCADOR", "PIROMANTE", "CRIOMANTE"]:
                if distancia > 2.5 and distancia < alcance:
                    usar = True
            elif distancia > 1.5 and distancia < alcance * 0.8:
                usar = True
            
            if "SNIPER" in self.tracos and distancia > 5.0:
                usar = True
            if "CLOSE_RANGE" in self.tracos and distancia > 4.0:
                usar = False
            if "SPAMMER" in self.tracos:
                usar = usar or random.random() < 0.3
            
            if usar and self._usar_skill(skill):
                self._pos_uso_skill_ofensiva(data)
                return True
        
        # Beams
        for skill in self.skills_por_tipo.get("BEAM", []):
            data = skill["data"]
            alcance = data.get("alcance", 5.0)
            if distancia < alcance and self._usar_skill(skill):
                self._pos_uso_skill_ofensiva(data)
                return True
        
        # Ãrea
        for skill in self.skills_por_tipo.get("AREA", []):
            data = skill["data"]
            raio = data.get("raio_area", 2.5)
            
            usar = distancia < raio + 0.5
            if "AREA_DENIAL" in self.tracos and distancia < raio + 2.0:
                usar = True
            if self.modo_berserk and distancia < raio + 2.0:
                usar = True
            
            if usar and self._usar_skill(skill):
                self._pos_uso_skill_ofensiva(data)
                return True
        
        # Skill da arma fallback
        if hasattr(p, 'skill_arma_nome') and p.skill_arma_nome and p.skill_arma_nome != "Nenhuma":
            if hasattr(p, 'usar_skill_arma') and p.mana >= p.custo_skill_arma:
                dados = get_skill_data(p.skill_arma_nome)
                if self._avaliar_uso_skill(dados, distancia, inimigo):
                    if p.usar_skill_arma():
                        self._pos_uso_skill_ofensiva(dados)
                        return True
        
        return False


    def _tentar_usar_summon(self, distancia, inimigo):
        """Usa summons com lÃ³gica melhorada (fallback do sistema estratÃ©gico)"""
        summon_skills = self.skills_por_tipo.get("SUMMON", [])
        if not summon_skills:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0
        
        # Conta summons ativos
        summons_ativos = self._contar_summons_ativos()
        
        for skill in summon_skills:
            data = skill["data"]
            custo = skill.get("custo", data.get("custo", 15))
            
            # Verifica mana
            if p.mana < custo:
                continue
            
            # Verifica cooldown
            nome = skill["nome"]
            if nome in p.cd_skills and p.cd_skills[nome] > 0:
                continue
            
            usar = False
            
            # Sem summons = prioridade alta
            if summons_ativos == 0:
                # HP baixo = invocar para distrair
                if hp_pct < 0.4:
                    usar = True
                # DistÃ¢ncia segura = invocar
                elif distancia > 4.0:
                    usar = True
                # InÃ­cio do combate
                elif self.tempo_combate < 5.0:
                    usar = True
                # Chance base
                elif random.random() < 0.25:
                    usar = True
            
            # Tem vantagem = reforÃ§ar
            elif summons_ativos == 1 and inimigo_hp_pct < 0.5:
                if random.random() < 0.3:
                    usar = True
            
            # Medo = invocar ajuda
            if self.medo > 0.4:
                usar = True
            
            # ArquÃ©tipo INVOCADOR sempre tenta invocar
            if self.arquetipo == "INVOCADOR" and random.random() < 0.4:
                usar = True
            
            if usar and self._usar_skill(skill):
                # ApÃ³s invocar, recuar para deixar summon lutar
                self.acao_atual = "RECUAR" if random.random() < 0.6 else "CIRCULAR"
                return True
        
        return False

    
    def _tentar_usar_trap(self, distancia, inimigo):
        """Usa armadilhas estrategicamente v3.0 â€” diferencia wall vs trigger"""
        trap_skills = self.skills_por_tipo.get("TRAP", [])
        if not trap_skills:
            return False
        
        p = self.parent
        traps_ativos = self._contar_traps_ativos()
        
        # Limite de traps
        if traps_ativos >= 3:
            return False
        
        for skill in trap_skills:
            data = skill["data"]
            custo = skill.get("custo", data.get("custo", 15))
            
            if p.mana < custo:
                continue
            
            nome = skill["nome"]
            if nome in p.cd_skills and p.cd_skills[nome] > 0:
                continue
            
            usar = False
            is_wall = data.get("bloqueia_movimento", False)
            
            if is_wall:
                # WALL: usar defensivamente
                # Encurralado = wall para bloquear perseguiÃ§Ã£o
                if self.consciencia_espacial.get("encurralado", False):
                    usar = True
                elif self.consciencia_espacial.get("zona_perigo_atual"):
                    usar = True
                # Inimigo se aproximando agressivamente
                elif self.leitura_oponente.get("ataque_iminente", False) and distancia < 4.0:
                    usar = True
                # HP baixo = barreira defensiva
                elif p.vida / max(p.vida_max, 1) < 0.4 and distancia < 5.0:
                    usar = True
            else:
                # TRIGGER: colocar no caminho provÃ¡vel do inimigo
                # Inimigo se aproximando = colocar na frente
                if self.leitura_oponente.get("ataque_iminente", False) and distancia < 5.0:
                    usar = True
                elif self.consciencia_espacial.get("zona_perigo_inimigo"):
                    usar = True
                # Controle de Ã¡rea geral
                elif traps_ativos < 2 and distancia > 3.0:
                    if random.random() < 0.20:
                        usar = True
                # InÃ­cio do combate = armar o campo
                elif self.tempo_combate < 6.0 and traps_ativos == 0:
                    usar = True
            
            if usar and self._usar_skill(skill):
                self.acao_atual = "RECUAR" if is_wall else "CIRCULAR"
                return True
        
        return False

    
    def _tentar_usar_transform(self, distancia, inimigo):
        """Usa transformaÃ§Ãµes estrategicamente"""
        transform_skills = self.skills_por_tipo.get("TRANSFORM", [])
        if not transform_skills:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0
        
        for skill in transform_skills:
            data = skill["data"]
            custo = skill.get("custo", data.get("custo", 15))
            
            if p.mana < custo:
                continue
            
            nome = skill["nome"]
            if nome in p.cd_skills and p.cd_skills[nome] > 0:
                continue
            
            usar = False
            
            # Transform defensivo se HP baixo
            if data.get("bonus_resistencia", 0) > 0.3 and hp_pct < 0.4:
                usar = True
            
            # Transform ofensivo para finalizar
            elif data.get("bonus_dano") and inimigo_hp_pct < 0.5 and hp_pct > 0.4:
                usar = True
            
            # InÃ­cio do combate
            elif self.tempo_combate < 8.0 and hp_pct > 0.7:
                if random.random() < 0.2:
                    usar = True
            
            if usar and self._usar_skill(skill):
                self.acao_atual = "MATAR"
                return True
        
        return False


    def _usar_skill(self, skill_info):
        """Usa uma skill"""
        p = self.parent
        data = skill_info["data"]
        custo = skill_info.get("custo", data.get("custo", 15))

        if p.mana < custo:
            return False

        if skill_info["fonte"] == "arma":
            if hasattr(p, 'usar_skill_arma'):
                # Encontra o Ã­ndice correto da skill na lista de skills da arma
                nome = skill_info["nome"]
                for idx, sk in enumerate(getattr(p, 'skills_arma', [])):
                    if sk.get("nome") == nome:
                        return p.usar_skill_arma(skill_idx=idx)
                # BUG-A2 fix: fallback silencioso removido.
                # Antes: usava skill_idx=0 quando o nome nÃ£o era encontrado,
                # disparando a skill errada sem nenhum aviso.
                # Agora: falha limpa com log rastreÃ¡vel.
                _log.warning(
                    "[SKILL] _usar_skill: nome '%s' nÃ£o encontrado em skills_arma de %s â€” abortando.",
                    nome, p.dados.nome
                )
                return False
        elif skill_info["fonte"] == "classe":
            if hasattr(p, 'usar_skill_classe'):
                return p.usar_skill_classe(skill_info["nome"])

        return False


    def _avaliar_uso_skill(self, dados, distancia, inimigo):
        """Avalia uso de skill"""
        tipo = dados.get("tipo", "NADA")
        p = self.parent
        
        if tipo == "PROJETIL":
            alcance = dados.get("vida", 1.5) * dados.get("velocidade", 8.0) * 0.8
            return distancia < alcance and distancia > 1.0
        elif tipo == "BEAM":
            return distancia < dados.get("alcance", 5.0)
        elif tipo == "AREA":
            return distancia < dados.get("raio_area", 2.5) + 1.0
        elif tipo == "DASH":
            if self.medo > 0.5:
                return True
            dist = dados.get("distancia", 3.0)
            return distancia > 4.0 and distancia < dist + 2.0
        elif tipo == "BUFF":
            if dados.get("cura"):
                return p.vida < p.vida_max * 0.45
            return distancia < 5.0
        
        return False


    def _pos_uso_skill_ofensiva(self, dados):
        """AÃ§Ã£o pÃ³s-skill ofensiva"""
        tipo = dados.get("tipo", "NADA")
        
        if tipo == "DASH":
            self.acao_atual = "MATAR"
        elif self.estilo_luta in ["KITE", "RANGED", "HIT_RUN"]:
            self.acao_atual = "RECUAR"
        elif self.estilo_luta in ["BERSERK", "AGGRO", "BURST"]:
            self.acao_atual = "MATAR"
        elif "COVARDE" in self.tracos:
            self.acao_atual = "RECUAR"

    
    def _contar_summons_ativos(self):
        """Conta quantos summons estÃ£o ativos"""
        p = self.parent
        # Verifica buffer de summons se existir
        if hasattr(p, 'buffer_summons'):
            return len([s for s in p.buffer_summons if hasattr(s, 'vida') and s.vida > 0])
        return 0

    
    def _contar_traps_ativos(self):
        """Conta quantas traps estÃ£o ativas (CB-08: filtra traps expiradas)"""
        p = self.parent
        if hasattr(p, 'buffer_traps'):
            return sum(1 for t in p.buffer_traps if getattr(t, 'ativo', False))
        return 0

    
    def _verificar_inimigo_stunado(self, inimigo):
        """Verifica se o inimigo estÃ¡ stunado/incapacitado (janela de burst mÃ¡ximo).
        FP-02 fix: root_timer impede movimento mas NÃƒO impede ataques â€” movido para
        _verificar_inimigo_debuffado. Burst total sÃ³ ocorre em stun/paralisia real.
        """
        if hasattr(inimigo, 'stun_timer') and inimigo.stun_timer > 0:
            return True
        # Status effects que impedem TANTO movimento quanto ataque
        for eff in getattr(inimigo, 'status_effects', []):
            nome = getattr(eff, 'nome', '').lower()
            if any(w in nome for w in ['atordoa', 'paralisi', 'sono ', 'medo', 'charme']):
                return True
            # IncapacitaÃ§Ã£o total: nÃ£o pode se mover E nÃ£o pode atacar
            if not getattr(eff, 'pode_mover', True) and not getattr(eff, 'pode_atacar', True):
                return True
        return False


    def _verificar_inimigo_debuffado(self, inimigo):
        """Verifica se o inimigo tem debuffs ativos (janela de oportunidade parcial).
        FP-02 fix: root_timer adicionado aqui â€” inimigo imobilizado ainda ataca,
        entÃ£o burst parcial Ã© vÃ¡lido, mas nÃ£o burst total.
        """
        if hasattr(inimigo, 'dots_ativos') and len(inimigo.dots_ativos) > 0:
            return True
        if hasattr(inimigo, 'slow_timer') and inimigo.slow_timer > 0:
            return True
        if hasattr(inimigo, 'stun_timer') and inimigo.stun_timer > 0:
            return True
        # FP-02 fix: root conta como debuff (nÃ£o como stun)
        if hasattr(inimigo, 'root_timer') and inimigo.root_timer > 0:
            return True
        # Qualquer status effect com mod negativo
        for eff in getattr(inimigo, 'status_effects', []):
            if getattr(eff, 'mod_velocidade', 1.0) < 0.9:
                return True
            if getattr(eff, 'mod_dano_causado', 1.0) < 0.9:
                return True
            if getattr(eff, 'dano_por_tick', 0) > 0:
                return True
            # Congelamento parcial (pode se mover OU pode atacar, mas nÃ£o ambos)
            nome = getattr(eff, 'nome', '').lower()
            if 'congela' in nome:
                return True
        return False

    
    def _usar_tudo(self):
        """Usa todas as skills disponÃ­veis"""
        for tipo in ["BUFF", "DASH", "AREA", "BEAM", "PROJETIL"]:
            for skill in self.skills_por_tipo.get(tipo, []):
                self._usar_skill(skill)

