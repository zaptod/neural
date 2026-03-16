"""
TEAM AI COORDINATOR v13.0 — NEURAL FIGHTS
═══════════════════════════════════════════════════════════════
Sistema de coordenação de IA para batalhas em equipe.
Gerencia comunicação entre aliados, atribuição de papéis,
foco de alvo, sinergias e táticas de grupo.

Integra-se com: brain.py, skill_strategy.py,
spatial, emotions, choreographer, personalities, classes.
═══════════════════════════════════════════════════════════════
"""
import math
import random
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

_log = logging.getLogger("team_ai")


# ═══════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════

class TeamRole(Enum):
    """Papel tático do lutador no time."""
    VANGUARD = auto()     # Frontliner - tanques/guerreiros, absorve dano
    STRIKER = auto()      # DPS principal - assassinos/berserkers
    FLANKER = auto()      # Flanqueador - ninjas/ladinos, ataca pelo lado
    ARTILLERY = auto()    # Longa distância - magos/arqueiros
    SUPPORT = auto()      # Suporte - paladinos/druidas, cura e buffs
    CONTROLLER = auto()   # Controlador - criomantes/feiticeiros, CC


class TeamTactic(Enum):
    """Tática geral do time."""
    FULL_AGGRO = auto()       # Todos atacam o mesmo alvo
    SPLIT_PUSH = auto()       # Cada um pega um alvo diferente  
    PROTECT_CARRY = auto()    # Proteger o DPS/mago principal
    FOCUS_FIRE = auto()       # Focar fogo no alvo mais fraco
    KITE_AND_POKE = auto()    # Manter distância e desgastar
    PINCER_ATTACK = auto()    # Ataque em pinça (flanquear)
    RETREAT_REGROUP = auto()  # Recuar e reagrupar
    BAIT_AND_PUNISH = auto()  # Iscar e punir


class TargetPriority(Enum):
    """Prioridade de alvo."""
    LOWEST_HP = auto()
    HIGHEST_THREAT = auto()
    NEAREST = auto()
    ISOLATED = auto()
    HEALER_FIRST = auto()
    CARRY_FIRST = auto()


# ─── CLASSE→ROLE MAPPING ───────────────────────────────────────
CLASS_ROLE_MAP = {
    "Guerreiro (Força Bruta)": TeamRole.VANGUARD,
    "Berserker (Fúria)":       TeamRole.STRIKER,
    "Gladiador (Combate)":     TeamRole.VANGUARD,
    "Cavaleiro (Defesa)":      TeamRole.VANGUARD,
    "Assassino (Crítico)":     TeamRole.FLANKER,
    "Ladino (Evasão)":        TeamRole.FLANKER,
    "Ninja (Velocidade)":      TeamRole.FLANKER,
    "Duelista (Precisão)":     TeamRole.STRIKER,
    "Mago (Arcano)":           TeamRole.ARTILLERY,
    "Piromante (Fogo)":        TeamRole.ARTILLERY,
    "Criomante (Gelo)":        TeamRole.CONTROLLER,
    "Necromante (Trevas)":     TeamRole.CONTROLLER,
    "Paladino (Sagrado)":      TeamRole.SUPPORT,
    "Druida (Natureza)":       TeamRole.SUPPORT,
    "Feiticeiro (Caos)":       TeamRole.CONTROLLER,
    "Monge (Chi)":             TeamRole.STRIKER,
}

# ─── PERSONALIDADE→TÁTICA MODIFICADORES ──────────────────────
PERSONALITY_TACTIC_BIAS = {
    # Traços que favorecem certas táticas
    "AGRESSIVO":     {"FULL_AGGRO": 0.3, "FOCUS_FIRE": 0.2},
    "BERSERKER":     {"FULL_AGGRO": 0.5},
    "CAUTELOSO":     {"PROTECT_CARRY": 0.2, "KITE_AND_POKE": 0.3},
    "OPORTUNISTA":   {"FOCUS_FIRE": 0.3, "BAIT_AND_PUNISH": 0.2},
    "CALCULISTA":    {"PINCER_ATTACK": 0.3, "BAIT_AND_PUNISH": 0.2},
    "PACIENTE":      {"KITE_AND_POKE": 0.3, "BAIT_AND_PUNISH": 0.2},
    "VINGATIVO":     {"FOCUS_FIRE": 0.4},
    "PROTETOR":      {"PROTECT_CARRY": 0.5},
    "DOMINADOR":     {"FULL_AGGRO": 0.3, "SPLIT_PUSH": 0.2},
    "COLADO":        {"PROTECT_CARRY": 0.3},
    "KITER":         {"KITE_AND_POKE": 0.4},
    "PRESSAO_CONSTANTE": {"FULL_AGGRO": 0.3, "SPLIT_PUSH": 0.2},
    "ARMADILHEIRO":  {"BAIT_AND_PUNISH": 0.4},
    "ZONER":         {"KITE_AND_POKE": 0.3},
    "FRIO":          {"PINCER_ATTACK": 0.2, "BAIT_AND_PUNISH": 0.2},
    "COVARDE":       {"RETREAT_REGROUP": 0.4, "KITE_AND_POKE": 0.3},
}


@dataclass
class TeamIntent:
    """Intenção comunicada de um lutador para o time."""
    fighter_id: int  # id() do lutador
    action: str      # acao_atual planejada
    target_id: int   # id() do alvo pretendido, ou 0
    skill_name: str = ""   # skill que pretende usar
    position: Tuple[float, float] = (0.0, 0.0)  # posição pretendida
    urgency: float = 0.0  # 0-1, quão urgente é a ação
    timestamp: float = 0.0


@dataclass
class FocusTarget:
    """Alvo de foco do time."""
    fighter: Any       # Lutador alvo
    priority: float    # 0-1 prioridade
    reason: str        # Por que esse alvo
    assigned: List[int] = field(default_factory=list)  # IDs dos atacantes designados


@dataclass
class TeamSynergy:
    """Sinergia detectada entre dois aliados."""
    fighter_a_id: int
    fighter_b_id: int
    tipo: str          # "cc_burst", "heal_tank", "flank_distract", "element_combo"
    score: float       # 0-1 quão forte é a sinergia
    details: str = ""


# ═══════════════════════════════════════════════════════════════
# TEAM COORDINATOR (um por time)
# ═══════════════════════════════════════════════════════════════

class TeamCoordinator:
    """
    Coordenador de IA do time. Um por equipe.
    Responsabilidades:
    - Atribuir roles (VANGUARD, STRIKER, etc.) baseado em classe/arma/personalidade
    - Determinar foco de alvo do time
    - Detectar sinergias (CC→burst, heal+tank, flanquear, combos elementais)
    - Comunicar intenções entre aliados
    - Ajustar tática geral do time
    - Gerenciar friendly-fire awareness
    - Coordenar recuos e reagrupamentos
    """

    def __init__(self, team_id: int, members: list):
        self.team_id = team_id
        self.members = members  # List[Lutador]
        self.member_ids = {id(m) for m in members}

        # === ROLES ===
        self.roles: Dict[int, TeamRole] = {}  # id(lutador) → TeamRole
        self.role_confidence: Dict[int, float] = {}  # quão certo estamos do role

        # === TÁTICAS ===
        self.tactic = TeamTactic.FOCUS_FIRE
        self.tactic_timer = 0.0
        self.tactic_reeval_cd = 3.0  # Reavalia a cada 3s
        self.target_priority = TargetPriority.LOWEST_HP

        # === FOCO ===
        self.focus_targets: List[FocusTarget] = []
        self.primary_target: Optional[Any] = None  # O alvo #1

        # === SINERGIAS ===
        self.synergies: List[TeamSynergy] = []

        # === COMUNICAÇÃO ===
        self.intents: Dict[int, TeamIntent] = {}  # Último intent de cada membro
        self.callouts: List[dict] = []  # Chamadas urgentes
        self.callout_cooldown: float = 0.0

        # === ESTADO DO TIME ===
        self.team_hp_pct: float = 1.0
        self.alive_count: int = len(members)
        self.enemy_alive_count: int = 0
        self.em_desvantagem: bool = False
        self.carry_id: int = 0  # melhor DPS do time
        self.weakest_id: int = 0  # membro mais fraco

        # === AWARENESS ===
        self.enemy_positions: Dict[int, Tuple[float, float]] = {}
        self.ally_positions: Dict[int, Tuple[float, float]] = {}
        self.center_of_mass: Tuple[float, float] = (0.0, 0.0)
        self.spread: float = 0.0  # quão espalhado está o time (metros)

        # Inicializa
        self._assign_roles()
        self._detect_synergies()

    # ─── ATRIBUIÇÃO DE ROLES ──────────────────────────────────
    def _assign_roles(self):
        """Atribui roles baseado em classe, arma e personalidade."""
        role_counts = {r: 0 for r in TeamRole}

        for m in self.members:
            mid = id(m)
            classe = getattr(m.dados, 'classe', '') if hasattr(m, 'dados') else ''
            arma = m.dados.arma_obj if hasattr(m, 'dados') and hasattr(m.dados, 'arma_obj') else None
            arma_tipo = arma.tipo if arma else ""

            # 1) Classe→Role mapping
            role = CLASS_ROLE_MAP.get(classe, None)

            # 2) Override por tipo de arma se necessário
            if role is None:
                if arma_tipo in ("Arco", "Arremesso"):
                    role = TeamRole.ARTILLERY
                elif arma_tipo == "Corrente":
                    role = TeamRole.CONTROLLER
                elif arma_tipo == "Mágica":
                    role = TeamRole.ARTILLERY
                elif arma_tipo in ("Reta", "Dupla"):
                    role = TeamRole.STRIKER
                else:
                    role = TeamRole.STRIKER

            # 3) Ajuste por personalidade
            if hasattr(m, 'brain') and m.brain:
                tracos = getattr(m.brain, 'tracos', [])
                if "PROTETOR" in tracos or "TANQUE" in tracos or "MURALHA" in tracos:
                    role = TeamRole.VANGUARD
                elif "FANTASMA" in tracos or "ERRATICO" in tracos:
                    role = TeamRole.FLANKER
                elif "SPAMMER" in tracos or "ZONER" in tracos:
                    role = TeamRole.CONTROLLER

            # 4) Checa se time precisa de variedade (evita 4 do mesmo role)
            if role_counts.get(role, 0) >= 2 and len(self.members) > 2:
                # Tenta role alternativo
                needed = min(role_counts, key=role_counts.get)
                if role_counts[needed] == 0:
                    role = needed

            self.roles[mid] = role
            self.role_confidence[mid] = 0.7  # confiança base
            role_counts[role] = role_counts.get(role, 0) + 1

        # Identifica carry (maior dano potencial)
        best_dmg = 0
        for m in self.members:
            dmg = self._estimar_dano_potencial(m)
            if dmg > best_dmg:
                best_dmg = dmg
                self.carry_id = id(m)

    def _estimar_dano_potencial(self, fighter) -> float:
        """Estima o potencial de dano de um lutador."""
        dano = 0.0
        if hasattr(fighter, 'dados') and hasattr(fighter.dados, 'arma_obj') and fighter.dados.arma_obj:
            dano += fighter.dados.arma_obj.dano
        forca = getattr(fighter.dados, 'forca', 5) if hasattr(fighter, 'dados') else 5
        dano += forca * 3
        # Skills ofensivas
        if hasattr(fighter, 'brain') and fighter.brain and hasattr(fighter.brain, 'skill_strategy'):
            ss = fighter.brain.skill_strategy
            if ss and hasattr(ss, 'profiles'):
                for p in ss.profiles.values():
                    dano += getattr(p, 'dano_total', 0) * 0.3
        return dano

    # ─── DETECÇÃO DE SINERGIAS ────────────────────────────────
    def _detect_synergies(self):
        """Descobre sinergias entre membros do time."""
        self.synergies.clear()

        for i, m1 in enumerate(self.members):
            for m2 in self.members[i+1:]:
                self._check_synergy_pair(m1, m2)

    def _check_synergy_pair(self, m1, m2):
        """Verifica sinergias entre dois membros."""
        id1, id2 = id(m1), id(m2)
        r1 = self.roles.get(id1, TeamRole.STRIKER)
        r2 = self.roles.get(id2, TeamRole.STRIKER)

        # ── TANK + DPS (Vanguard protege Striker/Artillery) ──
        if (r1 == TeamRole.VANGUARD and r2 in (TeamRole.STRIKER, TeamRole.ARTILLERY)) or \
           (r2 == TeamRole.VANGUARD and r1 in (TeamRole.STRIKER, TeamRole.ARTILLERY)):
            self.synergies.append(TeamSynergy(
                id1, id2, "tank_dps", 0.8,
                "Vanguard absorve dano enquanto DPS ataca livremente"
            ))

        # ── SUPPORT + qualquer (Cura/Buff) ──
        if r1 == TeamRole.SUPPORT or r2 == TeamRole.SUPPORT:
            self.synergies.append(TeamSynergy(
                id1, id2, "heal_support", 0.7,
                "Suporte mantém aliado vivo com cura/buffs"
            ))

        # ── CONTROLLER + STRIKER (CC→Burst) ──
        if (r1 == TeamRole.CONTROLLER and r2 == TeamRole.STRIKER) or \
           (r2 == TeamRole.CONTROLLER and r1 == TeamRole.STRIKER):
            self.synergies.append(TeamSynergy(
                id1, id2, "cc_burst", 0.9,
                "Controller aplica CC, Striker aproveita janela de burst"
            ))

        # ── FLANKER + qualquer (Distração + Pinça) ──
        if r1 == TeamRole.FLANKER or r2 == TeamRole.FLANKER:
            other = r2 if r1 == TeamRole.FLANKER else r1
            if other in (TeamRole.VANGUARD, TeamRole.STRIKER):
                self.synergies.append(TeamSynergy(
                    id1, id2, "flank_distract", 0.75,
                    "Flanker distrai, aliado pressiona frontalmente"
                ))

        # ── Sinergia Elemental ──
        self._check_elemental_synergy(m1, m2, id1, id2)

    def _check_elemental_synergy(self, m1, m2, id1, id2):
        """Verifica sinergias elementais entre skills dos dois lutadores."""
        SYNERGY_ELEMENTS = {
            ("GELO", "FOGO"): ("melt_combo", 0.8, "Gelo→Fogo: derrete para dano extra"),
            ("FOGO", "GELO"): ("melt_combo", 0.8, "Fogo→Gelo: derrete para dano extra"),
            ("GELO", "RAIO"): ("shatter_chain", 0.85, "Gelo congela→Raio estilhaça"),
            ("RAIO", "GELO"): ("shatter_chain", 0.85, "Raio paralisa→Gelo congela"),
            ("TREVAS", "LUZ"): ("void_holy", 0.7, "Trevas debuff→Luz purifica com dano"),
            ("LUZ", "TREVAS"): ("void_holy", 0.7, "Luz escudo→Trevas drena"),
            ("NATUREZA", "FOGO"): ("burn_poison", 0.75, "Veneno+Fogo: DoT amplificado"),
            ("FOGO", "NATUREZA"): ("burn_poison", 0.75, "Queimadura+Veneno: dano contínuo brutal"),
            ("GRAVITACAO", "FOGO"): ("gravity_bomb", 0.9, "Puxa inimigos→explode com AoE"),
            ("GRAVITACAO", "RAIO"): ("gravity_chain", 0.85, "Agrupa→Chain lightning máximo"),
        }

        elems1 = self._get_fighter_elements(m1)
        elems2 = self._get_fighter_elements(m2)

        for e1 in elems1:
            for e2 in elems2:
                key = (e1, e2)
                if key in SYNERGY_ELEMENTS:
                    tipo, score, desc = SYNERGY_ELEMENTS[key]
                    # Evita duplicata
                    if not any(s.tipo == tipo and {s.fighter_a_id, s.fighter_b_id} == {id1, id2}
                               for s in self.synergies):
                        self.synergies.append(TeamSynergy(id1, id2, tipo, score, desc))

    def _get_fighter_elements(self, fighter) -> List[str]:
        """Retorna elementos das skills do lutador."""
        elements = set()
        for skill_list_attr in ('skills_arma', 'skills_classe'):
            skill_list = getattr(fighter, skill_list_attr, [])
            for skill_info in skill_list:
                data = skill_info.get("data", {}) if isinstance(skill_info, dict) else {}
                elem = data.get("elemento", "")
                if elem:
                    elements.add(elem)
        return list(elements)

    # ═══════════════════════════════════════════════════════════
    # UPDATE PRINCIPAL (chamado a cada frame pela simulação)
    # ═══════════════════════════════════════════════════════════

    def update(self, dt: float, all_fighters: list):
        """Atualiza coordenação do time a cada frame."""
        # 1) Atualiza estado do time
        self._update_team_state(all_fighters)

        # 2) Atualiza posições
        self._update_positions(all_fighters)

        # 3) Reavalia tática se necessário
        self.tactic_timer += dt
        if self.tactic_timer >= self.tactic_reeval_cd:
            self.tactic_timer = 0
            self._evaluate_tactic(all_fighters)

        # 4) Atualiza foco de alvo
        self._update_focus_targets(all_fighters)

        # 5) Processa callouts
        self._process_callouts(dt)

        # 6) Distribui ordens
        self._distribute_orders()

    def _update_team_state(self, all_fighters):
        """Recalcula estado geral do time."""
        total_hp = 0
        total_hp_max = 0
        alive = 0
        weakest_hp_pct = 999
        enemy_alive = 0

        for m in self.members:
            if not m.morto:
                alive += 1
                hp_pct = m.vida / m.vida_max if m.vida_max > 0 else 0
                if hp_pct < weakest_hp_pct:
                    weakest_hp_pct = hp_pct
                    self.weakest_id = id(m)
            total_hp += max(0, m.vida)
            total_hp_max += m.vida_max

        self.alive_count = alive
        self.team_hp_pct = total_hp / total_hp_max if total_hp_max > 0 else 0

        # Conta inimigos vivos
        enemy_alive = sum(1 for f in all_fighters
                          if f.team_id != self.team_id and not f.morto)
        self.enemy_alive_count = enemy_alive
        self.em_desvantagem = alive < enemy_alive

    def _update_positions(self, all_fighters):
        """Atualiza posições e métricas espaciais do time."""
        self.ally_positions.clear()
        self.enemy_positions.clear()

        ax, ay, count = 0.0, 0.0, 0
        for m in self.members:
            if not m.morto:
                self.ally_positions[id(m)] = tuple(m.pos)
                ax += m.pos[0]
                ay += m.pos[1]
                count += 1

        if count > 0:
            self.center_of_mass = (ax / count, ay / count)
        
        # Spread (desvio médio do centro)
        if count > 1:
            total_dist = sum(
                math.hypot(m.pos[0] - self.center_of_mass[0],
                           m.pos[1] - self.center_of_mass[1])
                for m in self.members if not m.morto
            )
            self.spread = total_dist / count
        else:
            self.spread = 0

        for f in all_fighters:
            if f.team_id != self.team_id and not f.morto:
                self.enemy_positions[id(f)] = tuple(f.pos)

    # ─── AVALIAÇÃO DE TÁTICA ─────────────────────────────────
    def _evaluate_tactic(self, all_fighters):
        """Escolhe a melhor tática do time baseada na situação."""
        scores = {t: 0.0 for t in TeamTactic}
        enemies = [f for f in all_fighters if f.team_id != self.team_id and not f.morto]
        allies = [m for m in self.members if not m.morto]

        if not enemies or not allies:
            return

        # ── Fatores situacionais ──
        numerical_advantage = self.alive_count - self.enemy_alive_count
        team_hp = self.team_hp_pct
        enemy_hp = sum(e.vida for e in enemies) / sum(e.vida_max for e in enemies) if enemies else 1

        # Alguém no time está morrendo?
        someone_critical = any(m.vida / m.vida_max < 0.25 for m in allies if m.vida_max > 0)
        # Inimigo fraco?
        enemy_weak = any(e.vida / e.vida_max < 0.25 for e in enemies if e.vida_max > 0)
        # Time tem suporte?
        has_support = any(self.roles.get(id(m)) == TeamRole.SUPPORT for m in allies)
        has_flanker = any(self.roles.get(id(m)) == TeamRole.FLANKER for m in allies)
        has_controller = any(self.roles.get(id(m)) == TeamRole.CONTROLLER for m in allies)
        has_vanguard = any(self.roles.get(id(m)) == TeamRole.VANGUARD for m in allies)

        # ── SCORING DE TÁTICAS ──

        # FULL_AGGRO: bom com vantagem numérica, HP alto do time
        scores[TeamTactic.FULL_AGGRO] += numerical_advantage * 0.3
        scores[TeamTactic.FULL_AGGRO] += (team_hp - 0.5) * 0.4
        if enemy_weak:
            scores[TeamTactic.FULL_AGGRO] += 0.3

        # FOCUS_FIRE: sempre bom, ainda melhor com controlador
        scores[TeamTactic.FOCUS_FIRE] += 0.4  # Base alta
        if has_controller:
            scores[TeamTactic.FOCUS_FIRE] += 0.2
        if enemy_weak:
            scores[TeamTactic.FOCUS_FIRE] += 0.3

        # SPLIT_PUSH: bom com vantagem e lutadores independentes
        if numerical_advantage >= 2:
            scores[TeamTactic.SPLIT_PUSH] += 0.4
        if not has_support:
            scores[TeamTactic.SPLIT_PUSH] += 0.1

        # PROTECT_CARRY: bom com suporte e carry forte
        if has_support and has_vanguard:
            scores[TeamTactic.PROTECT_CARRY] += 0.5
        elif has_vanguard:
            scores[TeamTactic.PROTECT_CARRY] += 0.3

        # KITE_AND_POKE: bom com artillery dominante
        artillery_count = sum(1 for m in allies if self.roles.get(id(m)) == TeamRole.ARTILLERY)
        scores[TeamTactic.KITE_AND_POKE] += artillery_count * 0.25

        # PINCER_ATTACK: requer flanker
        if has_flanker:
            scores[TeamTactic.PINCER_ATTACK] += 0.4
        if len(enemies) <= 2:
            scores[TeamTactic.PINCER_ATTACK] += 0.2

        # RETREAT_REGROUP: time ferido ou em desvantagem
        if self.em_desvantagem:
            scores[TeamTactic.RETREAT_REGROUP] += 0.5
        if someone_critical:
            scores[TeamTactic.RETREAT_REGROUP] += 0.3
        if team_hp < 0.3:
            scores[TeamTactic.RETREAT_REGROUP] += 0.4

        # BAIT_AND_PUNISH: bom com combinação de controller + striker
        if has_controller and (has_flanker or has_vanguard):
            scores[TeamTactic.BAIT_AND_PUNISH] += 0.35

        # ── Modificadores de personalidade do time ──
        for m in allies:
            if hasattr(m, 'brain') and m.brain:
                for traco in getattr(m.brain, 'tracos', []):
                    biases = PERSONALITY_TACTIC_BIAS.get(traco, {})
                    for tactic_name, bonus in biases.items():
                        try:
                            t = TeamTactic[tactic_name]
                            scores[t] += bonus / len(allies)  # Normaliza pelo num de aliados
                        except (KeyError, ValueError):
                            pass

        # Seleciona tática com maior score
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            self.tactic = best

        # Atualiza prioridade de alvo baseada na tática
        if self.tactic == TeamTactic.FOCUS_FIRE:
            self.target_priority = TargetPriority.LOWEST_HP
        elif self.tactic == TeamTactic.FULL_AGGRO:
            self.target_priority = TargetPriority.NEAREST
        elif self.tactic == TeamTactic.PROTECT_CARRY:
            self.target_priority = TargetPriority.HIGHEST_THREAT
        elif self.tactic == TeamTactic.KITE_AND_POKE:
            self.target_priority = TargetPriority.NEAREST
        elif self.tactic == TeamTactic.PINCER_ATTACK:
            self.target_priority = TargetPriority.ISOLATED
        elif self.tactic == TeamTactic.BAIT_AND_PUNISH:
            self.target_priority = TargetPriority.HIGHEST_THREAT
        else:
            self.target_priority = TargetPriority.LOWEST_HP

    # ─── FOCO DE ALVO ────────────────────────────────────────
    def _update_focus_targets(self, all_fighters):
        """Determina alvos de foco para o time."""
        self.focus_targets.clear()
        enemies = [f for f in all_fighters if f.team_id != self.team_id and not f.morto]

        if not enemies:
            self.primary_target = None
            return

        for enemy in enemies:
            score = self._score_target(enemy, all_fighters)
            reason = self._get_target_reason(enemy)
            self.focus_targets.append(FocusTarget(
                fighter=enemy, priority=score, reason=reason
            ))

        # Ordena por prioridade
        self.focus_targets.sort(key=lambda ft: ft.priority, reverse=True)
        self.primary_target = self.focus_targets[0].fighter if self.focus_targets else None

        # Atribui atacantes ao alvo primário
        self._assign_attackers()

    def _score_target(self, enemy, all_fighters) -> float:
        """Pontua um alvo inimigo."""
        score = 0.0
        hp_pct = enemy.vida / enemy.vida_max if enemy.vida_max > 0 else 1.0

        # HP baixo
        if self.target_priority == TargetPriority.LOWEST_HP:
            score += (1.0 - hp_pct) * 3.0
        else:
            score += (1.0 - hp_pct) * 1.5

        # Proximidade (média dos aliados vivos)
        allies_alive = [m for m in self.members if not m.morto]
        if allies_alive:
            avg_dist = sum(
                math.hypot(m.pos[0] - enemy.pos[0], m.pos[1] - enemy.pos[1])
                for m in allies_alive
            ) / len(allies_alive)
            if self.target_priority == TargetPriority.NEAREST:
                score += max(0, 3.0 - avg_dist * 0.3)
            else:
                score += max(0, 2.0 - avg_dist * 0.2)

        # Isolamento (longe dos aliados desse inimigo)
        enemy_allies = [f for f in all_fighters
                        if f.team_id == enemy.team_id and not f.morto and f is not enemy]
        if enemy_allies:
            min_ally_dist = min(
                math.hypot(ea.pos[0] - enemy.pos[0], ea.pos[1] - enemy.pos[1])
                for ea in enemy_allies
            )
            if self.target_priority == TargetPriority.ISOLATED:
                score += min_ally_dist * 0.3
            elif min_ally_dist > 5.0:  # Está sozinho
                score += 0.5
        else:
            score += 1.0  # Último sobrevivente

        # Ameaça (potencial de dano)
        threat = self._estimate_enemy_threat(enemy)
        if self.target_priority == TargetPriority.HIGHEST_THREAT:
            score += threat * 2.0
        else:
            score += threat * 0.5

        # HP crítico = priority de execução
        if hp_pct < 0.2:
            score += 2.0

        # É um healer/suporte? (prioridade alta)
        enemy_classe = getattr(enemy.dados, 'classe', '') if hasattr(enemy, 'dados') else ''
        if enemy_classe in ("Paladino (Sagrado)", "Druida (Natureza)"):
            if self.target_priority in (TargetPriority.HEALER_FIRST, TargetPriority.HIGHEST_THREAT):
                score += 2.5
            else:
                score += 1.0

        # Está atacando o nosso carry?
        if hasattr(enemy, 'alvo') and id(getattr(enemy, 'alvo', None)) == self.carry_id:
            score += 1.5

        return score

    def _estimate_enemy_threat(self, enemy) -> float:
        """Estima a ameaça de um inimigo (0-3)."""
        threat = 1.0
        hp_pct = enemy.vida / enemy.vida_max if enemy.vida_max > 0 else 0

        # Atacando = mais ameaçador
        if getattr(enemy, 'atacando', False):
            threat += 0.5
        
        # Classe
        classe = getattr(enemy.dados, 'classe', '') if hasattr(enemy, 'dados') else ''
        if classe in ("Berserker (Fúria)", "Assassino (Crítico)", "Piromante (Fogo)"):
            threat += 0.5
        if classe in ("Cavaleiro (Defesa)", "Gladiador (Combate)"):
            threat -= 0.3

        # Berserker com HP baixo é MUITO perigoso
        if "Berserker" in classe and hp_pct < 0.4:
            threat += 1.0

        # Mana alta = pode usar skills perigosas
        if hasattr(enemy, 'mana') and hasattr(enemy, 'mana_max') and enemy.mana_max > 0:
            if enemy.mana / enemy.mana_max > 0.7:
                threat += 0.3

        return min(3.0, max(0.0, threat))

    def _get_target_reason(self, enemy) -> str:
        """Retorna razão legível do por que estamos focando esse alvo."""
        hp_pct = enemy.vida / enemy.vida_max if enemy.vida_max > 0 else 1
        if hp_pct < 0.2:
            return "EXECUTAR"
        classe = getattr(enemy.dados, 'classe', '') if hasattr(enemy, 'dados') else ''
        if classe in ("Paladino (Sagrado)", "Druida (Natureza)"):
            return "ELIMINAR_SUPORTE"
        if self.target_priority == TargetPriority.ISOLATED:
            return "ALVO_ISOLADO"
        if self.target_priority == TargetPriority.LOWEST_HP:
            return "HP_BAIXO"
        return "FOCO_TIME"

    def _assign_attackers(self):
        """Distribui atacantes entre os alvos."""
        allies = [m for m in self.members if not m.morto]
        if not allies or not self.focus_targets:
            return

        # Limpa atribuições anteriores
        for ft in self.focus_targets:
            ft.assigned.clear()

        if self.tactic in (TeamTactic.FOCUS_FIRE, TeamTactic.FULL_AGGRO):
            # Todos focam o primário
            for m in allies:
                self.focus_targets[0].assigned.append(id(m))

        elif self.tactic == TeamTactic.SPLIT_PUSH:
            # Distribui 1-para-1
            for i, m in enumerate(allies):
                target_idx = i % len(self.focus_targets)
                self.focus_targets[target_idx].assigned.append(id(m))

        elif self.tactic == TeamTactic.PINCER_ATTACK:
            # Flankers vão para o secundário, resto no primário
            for m in allies:
                role = self.roles.get(id(m), TeamRole.STRIKER)
                if role == TeamRole.FLANKER and len(self.focus_targets) > 1:
                    self.focus_targets[1].assigned.append(id(m))
                else:
                    self.focus_targets[0].assigned.append(id(m))

        elif self.tactic == TeamTactic.PROTECT_CARRY:
            # Vanguards protegem, carry e artillery atacam primário
            for m in allies:
                role = self.roles.get(id(m), TeamRole.STRIKER)
                if role in (TeamRole.VANGUARD, TeamRole.SUPPORT):
                    # Protegem o carry — focam quem está atacando o carry
                    carry_threat = None
                    for ft in self.focus_targets:
                        if hasattr(ft.fighter, 'alvo') and id(getattr(ft.fighter, 'alvo', None)) == self.carry_id:
                            carry_threat = ft
                            break
                    if carry_threat:
                        carry_threat.assigned.append(id(m))
                    else:
                        self.focus_targets[0].assigned.append(id(m))
                else:
                    self.focus_targets[0].assigned.append(id(m))
        else:
            # Default: todos no primário
            for m in allies:
                self.focus_targets[0].assigned.append(id(m))

    # ─── COMUNICAÇÃO ──────────────────────────────────────────
    def broadcast_intent(self, fighter, action: str, target=None, skill: str = "",
                          urgency: float = 0.0):
        """Um membro comunica sua intenção ao time."""
        self.intents[id(fighter)] = TeamIntent(
            fighter_id=id(fighter),
            action=action,
            target_id=id(target) if target else 0,
            skill_name=skill,
            position=tuple(fighter.pos) if hasattr(fighter, 'pos') else (0, 0),
            urgency=urgency,
        )

    def request_help(self, fighter, urgency: float = 0.8):
        """Membro pede ajuda ao time."""
        if self.callout_cooldown > 0:
            # Cooldown ativo — enfileira se urgência suficiente
            if urgency >= 0.9:
                self.callouts.append({
                    "type": "HELP",
                    "from": id(fighter),
                    "pos": tuple(fighter.pos) if hasattr(fighter, 'pos') else (0, 0),
                    "urgency": urgency,
                })
            return
        self.callouts.append({
            "type": "HELP",
            "from": id(fighter),
            "pos": tuple(fighter.pos) if hasattr(fighter, 'pos') else (0, 0),
            "urgency": urgency,
        })
        self.callout_cooldown = 2.0  # Cooldown de callout

    def callout_target(self, fighter, target, reason: str = "FOCUS"):
        """Membro indica um alvo para o time."""
        if self.callout_cooldown > 0:
            # Cooldown ativo — aceita FOCUS mesmo assim
            if reason == "FOCUS":
                self.callouts.append({
                    "type": "TARGET",
                    "from": id(fighter),
                    "target": id(target),
                    "reason": reason,
                })
            return
        self.callouts.append({
            "type": "TARGET",
            "from": id(fighter),
            "target": id(target),
            "reason": reason,
        })
        self.callout_cooldown = 1.5

    def _process_callouts(self, dt):
        """Processa e decai callouts."""
        self.callout_cooldown = max(0, self.callout_cooldown - dt)
        # Remove callouts antigos
        self.callouts = self.callouts[-5:]  # mantém últimos 5

    def _distribute_orders(self):
        """Distribui ordens passivas aos membros via team_orders no brain."""
        for m in self.members:
            if m.morto or not hasattr(m, 'brain') or not m.brain:
                continue
            mid = id(m)

            # Constrói orders dict para este membro
            orders = {
                "role": self.roles.get(mid, TeamRole.STRIKER).name,
                "tactic": self.tactic.name,
                "primary_target_id": id(self.primary_target) if self.primary_target else 0,
                "em_desvantagem": self.em_desvantagem,
                "team_hp_pct": self.team_hp_pct,
                "alive_count": self.alive_count,
                "enemy_alive_count": self.enemy_alive_count,
                "is_carry": mid == self.carry_id,
                "is_weakest": mid == self.weakest_id,
                "team_center": self.center_of_mass,
                "team_spread": self.spread,
                "synergies": [s for s in self.synergies if mid in (s.fighter_a_id, s.fighter_b_id)],
                "callouts": [c for c in self.callouts if c.get("from") != mid],
                "ally_intents": {k: v for k, v in self.intents.items() if k != mid},
            }

            # Injeta no brain
            m.brain.team_orders = orders

    # ─── QUERIES PARA O BRAIN ─────────────────────────────────
    def get_assigned_target(self, fighter) -> Optional[Any]:
        """Retorna o alvo atribuído para este lutador, ou None."""
        mid = id(fighter)
        for ft in self.focus_targets:
            if mid in ft.assigned:
                return ft.fighter
        return self.primary_target

    def is_ally_attacking_target(self, fighter, target) -> bool:
        """Verifica se outro aliado já está atacando esse alvo."""
        tid = id(target)
        for k, intent in self.intents.items():
            if k != id(fighter) and intent.target_id == tid:
                if intent.action in ("MATAR", "ESMAGAR", "PRESSIONAR", "ATAQUE_RAPIDO"):
                    return True
        return False

    def count_allies_on_target(self, target) -> int:
        """Conta quantos aliados estão focando esse alvo."""
        tid = id(target)
        count = 0
        for intent in self.intents.values():
            if intent.target_id == tid:
                count += 1
        return count

    def get_nearest_ally(self, fighter) -> Optional[Any]:
        """Retorna o aliado mais próximo vivo."""
        best = None
        best_dist = float('inf')
        for m in self.members:
            if m is fighter or m.morto:
                continue
            d = math.hypot(m.pos[0] - fighter.pos[0], m.pos[1] - fighter.pos[1])
            if d < best_dist:
                best_dist = d
                best = m
        return best

    def should_retreat_to_ally(self, fighter) -> Optional[Tuple[float, float]]:
        """Se o lutador deve recuar para um aliado (quando HP baixo)."""
        if fighter.vida / max(fighter.vida_max, 1) > 0.35:
            return None
        
        role = self.roles.get(id(fighter), TeamRole.STRIKER)
        if role == TeamRole.VANGUARD:
            return None  # Vanguards não recuam

        # Procura aliado suporte ou vanguard mais próximo
        best = None
        best_dist = float('inf')
        for m in self.members:
            if m is fighter or m.morto:
                continue
            ally_role = self.roles.get(id(m), TeamRole.STRIKER)
            if ally_role in (TeamRole.SUPPORT, TeamRole.VANGUARD):
                d = math.hypot(m.pos[0] - fighter.pos[0], m.pos[1] - fighter.pos[1])
                if d < best_dist:
                    best_dist = d
                    best = m

        if best and best_dist > 3.0:
            return tuple(best.pos)
        return None

    def get_friendly_fire_zones(self, fighter) -> List[dict]:
        """Retorna zonas de friendly-fire ativas (onde aliados estão atacando/usando skills)."""
        zones = []
        for k, intent in self.intents.items():
            if k == id(fighter):
                continue
            if intent.skill_name:
                zones.append({
                    "pos": intent.position,
                    "skill": intent.skill_name,
                    "danger": intent.urgency,
                })
        return zones


# ═══════════════════════════════════════════════════════════════
# TEAM COORDINATOR MANAGER (singleton global)
# ═══════════════════════════════════════════════════════════════

class TeamCoordinatorManager:
    """Gerencia todos os TeamCoordinators. Singleton."""
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self):
        self.coordinators: Dict[int, TeamCoordinator] = {}  # team_id → coordinator

    def initialize(self, fighters: list, teams: dict):
        """Cria coordenadores para cada time.
        
        Args:
            fighters: Lista de todos os Lutador
            teams: Dict {team_id: [lutadores]}
        """
        self.coordinators.clear()
        for team_id, members in teams.items():
            self.coordinators[team_id] = TeamCoordinator(team_id, members)

    def update(self, dt: float, all_fighters: list):
        """Atualiza todos os coordenadores."""
        for coord in self.coordinators.values():
            coord.update(dt, all_fighters)

    def get_coordinator(self, team_id: int) -> Optional[TeamCoordinator]:
        """Retorna o coordenador de um time."""
        return self.coordinators.get(team_id)

    def get_fighter_coordinator(self, fighter) -> Optional[TeamCoordinator]:
        """Retorna o coordenador do time de um lutador."""
        return self.coordinators.get(getattr(fighter, 'team_id', -1))
