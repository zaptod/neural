"""Auto-generated mixin â€” see scripts/split_brain.py"""
import random
import math
import logging
from typing import TYPE_CHECKING

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


class SkillsMixin(_AIBrainMixinBase):
    """Mixin de uso inteligente de skills (estratÃ©gico + legado)."""


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
        """
        IA de Skills v4.0 â€” ESTRATÃ‰GIA TÃTICA CONSCIENTE
        ===================================================
        A IA lÃª o estado real do combate e toma decisÃµes contextuais:

        CONTEXTO ANALISADO:
          â€¢ HP/Mana prÃ³prios e do inimigo
          â€¢ Estado do inimigo: stunado, debuffado, queimando, congelado
          â€¢ DistÃ¢ncia e mobilidade
          â€¢ Fase do combate (inÃ­cio, neutro, vantagem, crÃ­tico, finalizaÃ§Ã£o)
          â€¢ Sinergias de combo entre skills
          â€¢ PadrÃ£o recente do inimigo (ataque iminente, reposicionando)

        HIERARQUIA (verificadas em ordem, retorna True ao usar):
          1. SOBREVIVÃŠNCIA  â€” HP < 28%: cura, escudo, invencibilidade, escape
          2. JANELA DE CC   â€” inimigo exposto/longe: CC para abrir combo
          3. REAÃ‡ÃƒO CC      â€” inimigo vai atacar: CC preventivo / dash de escape
          4. COMBO SINÃ‰RGICOâ€” setup + payload em sequÃªncia
          5. EXECUÃ‡ÃƒO       â€” inimigo < 30% HP: skill de dano mÃ¡ximo
          6. BURST WINDOW   â€” inimigo stunado/debuffado: mÃ¡ximo dano
          7. OPENER         â€” primeiros 8s: buffs, summons, preparaÃ§Ã£o
          8. POKE/ZONING    â€” fase neutra: pressÃ£o segura de distÃ¢ncia
          9. ROTAÃ‡ÃƒO NORMAL â€” melhor skill disponÃ­vel da fase atual
        """
        p = self.parent
        strategy = self.skill_strategy
        if strategy is None:
            return False

        # (atualizar jÃ¡ foi chamado em _processar_skills antes do GCD gate)

        # â”€â”€ Estado de combate â”€â”€
        hp_pct          = p.vida / p.vida_max if p.vida_max > 0 else 1.0
        inimigo_hp_pct  = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0
        mana_pct        = p.mana / p.mana_max if p.mana_max > 0 else 1.0
        tempo_combate   = self.tempo_combate
        role            = strategy.role_principal.value
        plano           = strategy.plano
        skills          = strategy.skills

        # â”€â”€ Estado do inimigo (BUG-A4 fix: chave de cache baseada em estado real,
        # nÃ£o em tempo â€” a chave anterior usava int(tempo_combate * 10) que
        # invalidava o cache a cada 0.1s independente de mudanÃ§as, tornando
        # a otimizaÃ§Ã£o inoperante.  A nova chave reflete os atributos que
        # realmente mudam quando o estado do inimigo muda.) â”€â”€
        _stun_now   = getattr(inimigo, 'stun_timer', 0) > 0
        _slow_now   = getattr(inimigo, 'slow_timer', 0) > 0
        _root_now   = getattr(inimigo, 'root_timer', 0) > 0
        _dots_count = len(getattr(inimigo, 'dots_ativos', []))
        _fx_count   = len(getattr(inimigo, 'status_effects', []))
        _cache_key  = (id(inimigo), _stun_now, _slow_now, _root_now, _dots_count, _fx_count)
        _cache      = getattr(self, '_estado_inimigo_cache', None)
        _cache_stored_key = getattr(self, '_estado_inimigo_frame', None)
        if _cache is None or _cache_stored_key != _cache_key:
            _stunado     = self._verificar_inimigo_stunado(inimigo)
            _debuffado   = self._verificar_inimigo_debuffado(inimigo)
            _queimando   = any(
                getattr(d, 'tipo', getattr(d, 'nome', '')).upper() in ('QUEIMANDO', 'QUEIMAR', 'BURNING')
                for d in getattr(inimigo, 'dots_ativos', [])
            ) or any(
                getattr(e, 'nome', '').lower() in ('queimando', 'burning')
                for e in getattr(inimigo, 'status_effects', [])
            )
            _congelado   = getattr(inimigo, 'congelado', False) or any(
                getattr(e, 'nome', '').lower() in ('congelado', 'frozen')
                for e in getattr(inimigo, 'status_effects', [])
            )
            self._estado_inimigo_cache = (_stunado, _debuffado, _queimando, _congelado)
            self._estado_inimigo_frame = _cache_key  # BUG-A4 fix: armazena a chave real

        inimigo_stunado, inimigo_debuffado, inimigo_queimando, inimigo_congelado = self._estado_inimigo_cache

        inimigo_reposicionando = self.leitura_oponente.get("reposicionando", False)
        inimigo_atk_iminente  = self.leitura_oponente.get("ataque_iminente", False)
        encurralado           = self.consciencia_espacial.get("encurralado", False)
        oponente_encurralado  = self.consciencia_espacial.get("oponente_contra_parede", False)
        inimigo_mana_baixa    = getattr(inimigo, 'mana', 999) < getattr(inimigo, 'mana_max', 999) * 0.2
        buffs_ativos          = len(getattr(p, 'buffs_ativos', []))
        tenho_summons         = self._contar_summons_ativos() > 0

        # â”€â”€ v13.0: Team context â”€â”€
        orders = getattr(self, 'team_orders', {})
        team_role = orders.get("role", "STRIKER")
        team_tactic = orders.get("tactic", "FOCUS_FIRE")
        has_team = orders.get("alive_count", 1) > 1
        is_carry = orders.get("is_carry", False)
        is_weakest = orders.get("is_weakest", False)
        ally_no_caminho = getattr(self, 'multi_awareness', {}).get("aliado_no_caminho", False)

        # v13.0: AoE friendly fire suppression helper
        def _aoe_safe(nome):
            """Verifica se skill AoE Ã© segura (sem aliados na blast zone)."""
            if not has_team:
                return True
            sk = skills.get(nome)
            if not sk:
                return True
            if sk.tipo not in ("AREA", "BEAM"):
                return True  # NÃ£o AoE, sempre seguro
            # Se aliado estÃ¡ no caminho do alvo, suprime AoE 80% das vezes
            if ally_no_caminho and random.random() < 0.80:
                return False
            # Checa raio de AoE vs posiÃ§Ã£o de aliados
            raio_aoe = sk.data.get("raio", 0) or sk.data.get("largura", 0) or 2.0
            aliados = getattr(self, 'multi_awareness', {}).get("aliados", [])
            for aliado in aliados:
                if aliado["distancia"] < raio_aoe * 1.3 and aliado["distancia"] < distancia:
                    if random.random() < 0.75:
                        return False
            return True

        # â”€â”€ Helpers â”€â”€
        def pode_usar(nome):
            if nome not in skills:
                return False
            sk = skills[nome]
            # Custo efetivo com descontos de classe/buff
            custo_efetivo = sk.custo
            if "Mago" in p.classe_nome:
                custo_efetivo *= 0.8
            for buff in p.buffs_ativos:
                if getattr(buff, 'custo_mana_metade', False):
                    custo_efetivo *= 0.5
                    break
            if p.mana < custo_efetivo:
                return False
            if nome in p.cd_skills and p.cd_skills[nome] > 0:
                return False
            if sk.tipo in strategy.cd_por_tipo and strategy.cd_por_tipo[sk.tipo] > 0:
                return False
            return True

        def tentar(nome, motivo=""):
            if pode_usar(nome):
                # v13.0: AoE friendly fire check
                sk = skills.get(nome)
                if sk and not self._skill_aoe_segura_para_time(sk, inimigo, has_team):
                    return False
                if self._executar_skill_por_nome(nome):
                    strategy.registrar_uso_skill(nome)
                    self._pos_uso_skill_estrategica(skills[nome])
                    return True
            return False

        def alcance_ok(nome, margem=1.25):
            sk = skills.get(nome)
            if not sk or sk.alcance_efetivo <= 0:
                return True
            return distancia <= sk.alcance_efetivo * margem

        # ================================================================
        # v13.0 PRIORIDADE 0: TEAM SUPPORT SKILLS â€” cura/buff aliados
        # Antes de tudo: se sou SUPPORT e aliado precisa de cura
        # ================================================================
        if has_team and team_role == "SUPPORT" and not is_weakest:
            weakest_ally_hp = 1.0
            ma = getattr(self, 'multi_awareness', {})
            for aliado in ma.get("aliados", []):
                if aliado["vida_pct"] < weakest_ally_hp:
                    weakest_ally_hp = aliado["vida_pct"]

            if weakest_ally_hp < 0.4:
                # Aliado em perigo â€” prioriza cura/buff
                for nome in list(plano.sustains) + list(plano.rotacao_critical):
                    sk = skills.get(nome)
                    if sk and sk.tipo == "BUFF" and (
                        sk.data.get("cura") or sk.data.get("cura_por_segundo") or
                        sk.data.get("escudo") or sk.data.get("buff_defesa")
                    ):
                        if tentar(nome, "team_suporte_aliado"):
                            return True

            # SUPPORT tambÃ©m buff aliados se todos saudÃ¡veis
            if weakest_ally_hp > 0.6 and mana_pct > 0.5 and buffs_ativos == 0:
                for nome in [n for n, sk in skills.items()
                             if sk.tipo == "BUFF" and sk.data.get("buff_dano")]:
                    if tentar(nome, "team_suporte_buff"):
                        return True

        # v13.0: CONTROLLER CC para time â€” se aliado Striker estÃ¡ pronto para burst
        if has_team and team_role == "CONTROLLER" and mana_pct > 0.3:
            ally_intents = orders.get("ally_intents", {})
            striker_ready = any(
                getattr(intent, 'action', '') in ("MATAR", "ESMAGAR", "PRESSIONAR")
                for intent in ally_intents.values()
            )
            if striker_ready and not inimigo_stunado:
                for nome in plano.controls:
                    if alcance_ok(nome, 1.15):
                        if tentar(nome, "team_cc_para_burst"):
                            return True

        # ================================================================
        # PRIORIDADE 1: SOBREVIVÃŠNCIA â€” HP crÃ­tico
        # ================================================================
        if hp_pct < 0.28:
            # 1a. Invencibilidade ou transformaÃ§Ã£o defensiva
            for nome in list(plano.sustains) + list(plano.escapes):
                sk = skills.get(nome)
                if sk and (sk.data.get("invencivel") or sk.data.get("intangivel")):
                    if tentar(nome, "emergencia_invencivel"):
                        return True
            # 1b. Curas diretas (prioriza a de maior valor)
            cura_candidatos = [
                (nome, skills[nome].data.get("cura", 0) + skills[nome].data.get("cura_por_segundo", 0) * 3
                 + (skills[nome].data.get("cura_percent", 0) * p.vida_max))
                for nome in plano.rotacao_critical
                if nome in skills and skills[nome].tipo in ("BUFF", "AREA")
                and (skills[nome].data.get("cura") or skills[nome].data.get("cura_por_segundo")
                     or skills[nome].data.get("cura_percent"))
            ]
            for nome, _ in sorted(cura_candidatos, key=lambda x: -x[1]):
                if tentar(nome, "emergencia_cura"):
                    return True
            # 1c. Escudo mÃ¡gico
            for nome in plano.sustains:
                sk = skills.get(nome)
                if sk and sk.data.get("escudo"):
                    if tentar(nome, "emergencia_escudo"):
                        return True
            # 1c2. v14.0: TransformaÃ§Ãµes defensivas (Armadura de Sangue, etc.)
            for nome, sk in skills.items():
                if sk.tipo == "TRANSFORM" and sk.data.get("bonus_resistencia", 0) > 0.2:
                    if tentar(nome, "emergencia_transform_defensiva"):
                        return True
            # 1c3. v14.0: Lifesteal beams as sustain (drain to survive)
            if distancia < 7.0:
                for nome, sk in skills.items():
                    if sk.data.get("lifesteal", 0) > 0.3 and sk.dano_total > 20:
                        if alcance_ok(nome, 1.1):
                            if tentar(nome, "emergencia_lifesteal"):
                                return True
            # 1d. Escape / dash (prioritÃ¡rio se inimigo atacando)
            if inimigo_atk_iminente or hp_pct < 0.18:
                for nome in plano.escapes:
                    if tentar(nome, "emergencia_escape"):
                        return True
            # 1e. Skill de controle defensivo (stun para criar espaÃ§o)
            if hp_pct < 0.22 and distancia < 3.0:
                for nome in plano.controls:
                    if alcance_ok(nome, 1.1) and tentar(nome, "emergencia_cc_defensivo"):
                        return True

        # ================================================================
        # PRIORIDADE 2: REAÃ‡ÃƒO A ATAQUE IMINENTE
        # ================================================================
        if inimigo_atk_iminente and hp_pct > 0.28:
            # 2a. CC preventivo para interromper o ataque
            for nome in plano.controls:
                if alcance_ok(nome, 1.1) and mana_pct > 0.20:
                    if tentar(nome, "cc_preventivo"):
                        return True
            # 2b. Dash de escape se role Ã© kite
            if role in ("artillery", "control_mage") or self.medo > 0.5:
                for nome in plano.escapes:
                    if tentar(nome, "escape_preemptivo"):
                        return True

        # ================================================================
        # PRIORIDADE 3: JANELA DE CC â€” inimigo exposto
        # Momentos ideais: longe (projÃ©til alcanÃ§a), reposicionando, encurralado
        # ================================================================
        condicao_cc = (
            inimigo_reposicionando            or
            distancia > 4.5                   or
            (oponente_encurralado and distancia < 7.0)
        )
        if condicao_cc and mana_pct > 0.22 and not inimigo_stunado:
            for nome in plano.controls:
                sk = skills.get(nome)
                if not sk:
                    continue
                # NÃ£o usar CC lento se inimigo estÃ¡ muito perto e se movendo
                if inimigo_reposicionando and distancia < 2.5 and sk.cooldown > 8:
                    continue
                if alcance_ok(nome, 1.15):
                    if tentar(nome, "janela_cc"):
                        return True

        # ================================================================
        # PRIORIDADE 4: COMBO SINÃ‰RGICO â€” setup â†’ payload
        # Ex: Congelar â†’ Shatter / Queimar â†’ Detonar / Buff â†’ Burst
        # ================================================================
        if mana_pct > 0.40:
            # 4a. Se inimigo jÃ¡ estÃ¡ queimando, prioriza detonate (payload)
            if inimigo_queimando:
                det_skills = [n for n, sk in skills.items()
                              if sk.data.get("condicao") == "ALVO_QUEIMANDO" and alcance_ok(n)]
                for nome in det_skills:
                    if tentar(nome, "payload_queimando"):
                        return True

            # 4b. Se inimigo congelado, prioriza shatter
            if inimigo_congelado:
                sht_skills = [n for n, sk in skills.items()
                              if sk.data.get("condicao") == "ALVO_CONGELADO" and alcance_ok(n)]
                for nome in sht_skills:
                    if tentar(nome, "payload_congelado"):
                        return True

            # 4c. v14.0: ELEMENTAL REACTION CHAINING
            # Se a Ãºltima skill usada tem um elemento, procura skill com elemento
            # diferente que gera uma reaÃ§Ã£o forte (multiplicador â‰¥ 1.5)
            ultima = strategy.ultima_skill
            if ultima and ultima in skills and skills[ultima].elemento:
                ultimo_elem = skills[ultima].elemento
                # Procura skills de elemento diferente que combinam
                for nome, sk in skills.items():
                    if not sk.elemento or sk.elemento == ultimo_elem:
                        continue
                    if not pode_usar(nome) or not alcance_ok(nome, 1.2):
                        continue
                    # Verifica se gera reaÃ§Ã£o
                    for combo_entry in strategy.plano.combos:
                        if len(combo_entry) >= 3 and "elemental_" in combo_entry[2]:
                            if combo_entry[0] == ultima and combo_entry[1] == nome:
                                if tentar(nome, f"reaction_chain_{combo_entry[2]}"):
                                    return True

            # 4d. v14.0: MARCADO â†’ follow-up burst
            # Se inimigo tem status MARCADO, prioriza skill VOID de alto dano
            inimigo_marcado = any(
                getattr(e, 'nome', '').lower() in ('marcado', 'marked')
                for e in getattr(inimigo, 'status_effects', [])
            )
            if inimigo_marcado:
                # Skills void primeiro (dano dobrado em marcado)
                void_skills = [(n, sk) for n, sk in skills.items()
                               if sk.elemento == "VOID" and sk.dano_total > 15
                               and alcance_ok(n)]
                void_skills.sort(key=lambda x: x[1].dano_total, reverse=True)
                for nome, _ in void_skills:
                    if tentar(nome, "void_marcado_double"):
                        return True
                # Qualquer burst se nÃ£o tem void
                for nome in plano.bursts:
                    if alcance_ok(nome) and tentar(nome, "burst_sobre_marcado"):
                        return True

            # 4e. Inicia um combo sinÃ©rgico se tiver mana suficiente
            combo = strategy.get_combo_recomendado()
            if combo:
                sk1, sk2, razao = combo
                custo_total = (skills[sk1].custo if sk1 in skills else 9999) + \
                              (skills[sk2].custo if sk2 in skills else 9999)
                if p.mana >= custo_total * 0.88:
                    # Chance aumenta se inimigo estÃ¡ parado (stunado/encurralado)
                    chance_combo = 0.75 if (inimigo_stunado or oponente_encurralado) else 0.50
                    # v14.0: Elemental combos get bonus chance
                    if "elemental_" in razao:
                        chance_combo = min(0.90, chance_combo + 0.20)
                    if random.random() < chance_combo:
                        if alcance_ok(sk1, 1.15) and tentar(sk1, f"combo_setup_{razao}"):
                            self.combo_state["em_combo"] = True
                            self.combo_state["pode_followup"] = True
                            self.combo_state["timer_followup"] = 0.5
                            self._proximo_skill_combo = sk2
                            return True

        # ================================================================
        # PRIORIDADE 5: EXECUÃ‡ÃƒO â€” inimigo HP baixo
        # Gasta mais recursos quando pode confirmar kill
        # v13.0: Evita overkill se aliados jÃ¡ estÃ£o focando
        # ================================================================
        if inimigo_hp_pct < 0.32:
            # v13.0: Check overkill â€” se 2+ aliados jÃ¡ focam este alvo,
            # nÃ£o gasta finisher caro (a nÃ£o ser que HP < 10%)
            ally_intents = orders.get("ally_intents", {})
            allies_on_this = sum(
                1 for i in ally_intents.values()
                if getattr(i, 'target_id', 0) == id(inimigo)
                and getattr(i, 'action', '') in ("MATAR", "ESMAGAR", "PRESSIONAR")
            ) if has_team else 0
            skip_expensive_finisher = allies_on_this >= 2 and inimigo_hp_pct > 0.10

            # 5a. Finisher dedicado
            if not skip_expensive_finisher:
                for nome in sorted(plano.finishers,
                                   key=lambda n: skills.get(n, type("", (), {"dano_total": 0})).dano_total,
                                   reverse=True):
                    sk = skills.get(nome)
                    if not sk:
                        continue
                    if alcance_ok(nome, 1.30):
                        if tentar(nome, "execucao_finisher"):
                            return True
            # 5b. Burst de maior dano
            for nome in sorted(plano.bursts,
                               key=lambda n: skills.get(n, type("", (), {"dano_total": 0})).dano_total,
                               reverse=True):
                sk = skills.get(nome)
                if sk and alcance_ok(nome, 1.25):
                    if tentar(nome, "execucao_burst"):
                        return True
            # 5c. Se inimigo HP < 15%, usa QUALQUER skill disponÃ­vel
            if inimigo_hp_pct < 0.15:
                for nome in skills:
                    sk = skills[nome]
                    if sk.dano_total > 0 and alcance_ok(nome, 1.2):
                        if tentar(nome, "execucao_desesperada"):
                            return True

        # ================================================================
        # PRIORIDADE 6: BURST WINDOW â€” inimigo stunado/debuffado
        # Janela de oportunidade para dano mÃ¡ximo
        # ================================================================
        if (inimigo_stunado or inimigo_debuffado) and mana_pct > 0.25:
            chance_burst = 0.95 if inimigo_stunado else 0.80
            # Usa burst com mais dano primeiro
            for nome in sorted(plano.bursts,
                               key=lambda n: skills.get(n, type("", (), {"dano_total": 0})).dano_total,
                               reverse=True):
                sk = skills.get(nome)
                if sk and alcance_ok(nome, 1.30):
                    if random.random() < chance_burst:
                        if tentar(nome, "burst_window"):
                            return True
            # Se stunado: usa area tambÃ©m
            if inimigo_stunado:
                for nome in [n for n, sk in skills.items() if sk.tipo == "AREA" and alcance_ok(n)]:
                    if tentar(nome, "area_sobre_stunado"):
                        return True
            # v14.0: Se stunado e temos channel â€” perfect window (can't interrupt)
            if inimigo_stunado and distancia < 4.0:
                for nome in [n for n, sk in skills.items()
                             if sk.tipo == "CHANNEL" and alcance_ok(n)]:
                    if tentar(nome, "channel_sobre_stunado"):
                        return True
            # v14.0: Se debuffado (vulnerÃ¡vel/marcado) â€” use penetrating attacks
            if inimigo_debuffado:
                penetra = [n for n, sk in skills.items()
                           if sk.data.get("penetra_escudo") and alcance_ok(n)]
                for nome in penetra:
                    if tentar(nome, "penetra_sobre_debuffado"):
                        return True

        # ================================================================
        # PRIORIDADE 7: OPENER â€” primeiros 8 segundos
        # Estabelecer vantagem: buffs de dano, summons, traps, transformaÃ§Ãµes
        # v14.0: Also considers lifesteal buffs and mark skills as openers
        # ================================================================
        if tempo_combate < 8.0:
            for nome in plano.rotacao_opening:
                sk = skills.get(nome)
                if not sk:
                    continue
                if sk.tipo == "BUFF" and sk.data.get("buff_dano") and buffs_ativos == 0:
                    if tentar(nome, "opener_buff_dano"):
                        return True
                # v14.0: Lifesteal/resistance buffs as opener
                elif sk.tipo == "BUFF" and (sk.data.get("lifesteal_global") or sk.data.get("bonus_resistencia")):
                    if buffs_ativos == 0 and tentar(nome, "opener_buff_sustain"):
                        return True
                elif sk.tipo == "SUMMON" and not tenho_summons and strategy.cd_por_tipo.get("SUMMON", 0) <= 0:
                    if tentar(nome, "opener_summon"):
                        return True
                elif sk.tipo == "TRANSFORM":
                    if tentar(nome, "opener_transform"):
                        return True
                elif sk.tipo == "TRAP" and self._contar_traps_ativos() < 2:
                    # Trigger traps como zona de controle inicial
                    if not sk.data.get("bloqueia_movimento", False):
                        if tentar(nome, "opener_trap_trigger"):
                            return True
                elif sk.tipo == "BUFF" and sk.data.get("escudo") and hp_pct < 0.7:
                    if tentar(nome, "opener_escudo"):
                        return True
            # v14.0: Mark skills as openers (setup combos for later)
            for nome, sk in skills.items():
                if sk.data.get("efeito") == "MARCADO" and alcance_ok(nome, 1.15):
                    if tentar(nome, "opener_marca"):
                        return True

        # ================================================================
        # PRIORIDADE 8: POKE / ZONING â€” fase neutra
        # Manter pressÃ£o sem se expor. Mais importante para ranged/arty.
        # v14.0: Enhanced mana management â€” prefer efficient skills when low
        # ================================================================
        poke_dist_ok = distancia > 3.0 if role in ("artillery", "control_mage", "burst_mage") else distancia > 5.0
        if poke_dist_ok and mana_pct > 0.30:
            chance_poke = {
                "artillery": 0.88, "control_mage": 0.80, "burst_mage": 0.70,
                "summoner": 0.60, "battle_mage": 0.45, "trap_master": 0.75,
                "channeler": 0.72,
            }.get(role, 0.38)
            if "SPAMMER" in self.tracos:
                chance_poke = min(0.96, chance_poke + 0.14)
            if "CALCULISTA" in self.tracos:
                chance_poke *= 0.80
            # v14.0: When mana is medium-low, reduce poke frequency
            if mana_pct < 0.45:
                chance_poke *= 0.7
            if random.random() < chance_poke:
                # v14.0: Sort pokes by mana efficiency when mana < 50%
                poke_list = list(plano.pokes)
                if mana_pct < 0.50:
                    poke_list.sort(
                        key=lambda n: skills[n].dano_por_mana if n in skills else 0,
                        reverse=True
                    )
                for nome in poke_list:
                    if alcance_ok(nome, 1.12) and tentar(nome, "poke"):
                        return True
                # Traps como zoning â€” diferencia wall vs trigger
                traps_ativos = self._contar_traps_ativos()
                if traps_ativos < 3:
                    for nome in [n for n, sk in skills.items() if sk.tipo == "TRAP"]:
                        sk = skills[nome]
                        if sk.data.get("bloqueia_movimento", False):
                            # Walls: colocar entre eu e o inimigo quando inimigo avanÃ§a
                            if inimigo_atk_iminente or distancia < 4.0:
                                if tentar(nome, "wall_zoning_defensivo"):
                                    return True
                        else:
                            # Trigger traps: colocar no caminho do inimigo
                            if tentar(nome, "trap_zoning_trigger"):
                                return True

        # ================================================================
        # PRIORIDADE 9: SUMMON MANUTENÃ‡ÃƒO
        # Re-invocar summons quando nÃ£o hÃ¡ nenhum ativo
        # ================================================================
        if not tenho_summons and mana_pct > 0.45 and tempo_combate > 5.0:
            for nome in [n for n, sk in skills.items()
                         if sk.tipo == "SUMMON" and strategy.cd_por_tipo.get("SUMMON", 0) <= 0]:
                if tentar(nome, "manutencao_summon"):
                    return True

        # ================================================================
        # PRIORIDADE 9.5: TRAP MANUTENÃ‡ÃƒO
        # Re-colocar traps quando poucas ativas
        # ================================================================
        traps_ativos_agora = self._contar_traps_ativos()
        if traps_ativos_agora < 2 and mana_pct > 0.40 and tempo_combate > 6.0:
            for nome in [n for n, sk in skills.items()
                         if sk.tipo == "TRAP" and strategy.cd_por_tipo.get("TRAP", 0) <= 0]:
                if tentar(nome, "manutencao_trap"):
                    return True

        # ================================================================
        # PRIORIDADE 10: BUFF MANUTENÃ‡ÃƒO
        # Renovar buffs que expiraram durante o combate
        # ================================================================
        if buffs_ativos == 0 and mana_pct > 0.35 and tempo_combate > 6.0:
            for nome in [n for n, sk in skills.items()
                         if sk.tipo == "BUFF" and sk.data.get("buff_dano")]:
                if tentar(nome, "manutencao_buff"):
                    return True

        # ================================================================
        # PRIORIDADE 11: ROTAÃ‡ÃƒO GERAL â€” usa o sistema de battle plan
        # ================================================================
        if not SKILL_STRATEGY_AVAILABLE:
            return False
        situacao = CombatSituation(
            distancia=distancia,
            meu_hp_percent=hp_pct,
            inimigo_hp_percent=inimigo_hp_pct,
            meu_mana_percent=mana_pct,
            estou_encurralado=encurralado,
            inimigo_encurralado=oponente_encurralado,
            inimigo_atacando=inimigo_atk_iminente,
            inimigo_stunado=inimigo_stunado,
            tenho_summons_ativos=self._contar_summons_ativos(),
            tenho_traps_ativos=self._contar_traps_ativos(),
            tenho_buffs_ativos=buffs_ativos,
            inimigo_debuffado=inimigo_debuffado,
            momentum=self.momentum,
            tempo_combate=tempo_combate
        )
        resultado = strategy.obter_melhor_skill(situacao)
        if resultado:
            sk_profile, razao = resultado
            chance = {
                "artillery": 0.88, "burst_mage": 0.85, "control_mage": 0.83,
                "summoner": 0.80, "buffer": 0.78, "channeler": 0.80,
                "battle_mage": 0.65, "dasher": 0.60, "transformer": 0.60,
            }.get(role, 0.52)
            if "SPAMMER" in self.tracos:
                chance = min(0.96, chance + 0.12)
            if "CALCULISTA" in self.tracos:
                chance *= 0.82
            if self.modo_burst:
                chance = 0.96
            if not alcance_ok(sk_profile.nome, 1.40):
                chance *= 0.22
            if random.random() < chance:
                if self._executar_skill_por_nome(sk_profile.nome):
                    strategy.registrar_uso_skill(sk_profile.nome)
                    self._pos_uso_skill_estrategica(sk_profile)
                    return True

        return False


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
        
        if tipo == "DASH":
            if skill_profile.data.get("dano_chegada", 0) > 0:
                self.acao_atual = "MATAR"
            else:
                # Dash sem dano = reposicionamento, agir de acordo
                self.acao_atual = "COMBATE"
        elif tipo == "SUMMON":
            # ApÃ³s invocar, recuar para deixar o summon lutar
            if self.skill_strategy.preferencias.get("estilo_kite"):
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
                self.acao_atual = "PRESSIONAR"
        elif tipo in ["PROJETIL", "BEAM"]:
            if self.estilo_luta in ["KITE", "RANGED"]:
                self.acao_atual = "RECUAR"
            else:
                # Projetil lanÃ§ado: pressionar enquanto projÃ©til voa
                self.acao_atual = "COMBATE"
        elif tipo == "AREA":
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

