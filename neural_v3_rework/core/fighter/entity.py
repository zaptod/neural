"""
NEURAL FIGHTS — core/fighter/entity.py  [D03/D04 Sprint 8]
===========================================================
Lutador: classe principal, herda todos os mixins.

Contém apenas:
  - __init__ (inicialização de todos os atributos)
  - update() (loop central)

Nota: AIBrain é importado dentro de __init__ (import inline intencional)
para quebrar a dependência circular:
  ai/__init__ → ai/brain → core/__init__ → core/entities → core/fighter/entity → ai
"""

import math
import random
import logging

from utils.config import PPM, ALTURA_PADRAO
from utils.balance_config import (
    ESTAMINA_MAX, ALCANCE_IDEAL_DEFAULT,
)
from core.skills import get_skill_data
from models import get_class_data
from core.physics import normalizar_angulo
# AIBrain é importado dentro de __init__ para evitar importação circular

from .stats import StatsMixin
from .physics_mixin import PhysicsMixin
from .combat_mixin import CombatMixin
from .weapons_mixin import WeaponsMixin
from .combat_mixin import StatusSnapshot  # re-exporta para compatibilidade

_log = logging.getLogger("entities")


class Lutador(StatsMixin, PhysicsMixin, CombatMixin, WeaponsMixin):
    """
    Classe principal do lutador com suporte completo a:
    - Sistema de classes expandido
    - Novos tipos de skills (DASH, BUFF, AREA, BEAM, SUMMON)
    - Efeitos de status (DoT, buffs, debuffs)
    - Batalhas multi-lutador com equipes (v13.0)

    [D03 Sprint 8] Dividida em 4 mixins:
        StatsMixin    — stats, skills, channeling        (~120 L)
        PhysicsMixin  — física, movimento, trail         (~220 L)
        CombatMixin   — dano, status, buffs, morte       (~430 L)
        WeaponsMixin  — ataques, skills, projéteis       (~560 L)
    """

    def __init__(self, dados_char, pos_x, pos_y, team_id=0):
        self.dados = dados_char
        self.pos = [pos_x, pos_y]
        self.vel = [0.0, 0.0]
        self.z = 0.0
        self.vel_z = 0.0
        self.raio_fisico = (self.dados.tamanho / 4.0)

        # === v13.0: SISTEMA DE EQUIPES ===
        self.team_id = team_id

        # Dados da classe
        self.classe_nome = getattr(self.dados, 'classe', "Guerreiro (Força Bruta)")
        self.class_data = get_class_data(self.classe_nome)

        # Stats calculados com modificadores de classe
        self.vida_max = self._calcular_vida_max()
        self.vida = self.vida_max
        self.estamina = ESTAMINA_MAX
        self.estamina_max = ESTAMINA_MAX
        self.mana_max = self._calcular_mana_max()
        self.mana = self.mana_max

        self.regen_mana_base = self.class_data.get("regen_mana", 3.0)

        # Modificadores de classe
        self.mod_dano = self.class_data.get("mod_forca", 1.0)
        self.mod_velocidade = self.class_data.get("mod_velocidade", 1.0)
        self.mod_defesa = 1.0 / self.class_data.get("mod_vida", 1.0)
        self.cor_aura = self.class_data.get("cor_aura", (200, 200, 200))

        # === SISTEMA DE SKILLS ===
        self.skills_arma = []
        self.skills_classe = []
        self.skill_atual_idx = 0
        self.cd_skills = {}

        # Carrega skills da arma
        arma = self.dados.arma_obj
        if arma:
            habilidades = getattr(arma, 'habilidades', [])
            if habilidades:
                for hab in habilidades:
                    if isinstance(hab, dict):
                        nome_hab = hab.get("nome", "Nenhuma")
                        custo_hab = hab.get("custo", 0)
                    else:
                        nome_hab = str(hab)
                        custo_hab = getattr(arma, 'custo_mana', 0)
                    skill_data = get_skill_data(nome_hab)
                    if skill_data["tipo"] != "NADA":
                        self.skills_arma.append({"nome": nome_hab, "custo": custo_hab, "data": skill_data})
                        self.cd_skills[nome_hab] = 0.0
            else:
                nome_raw = getattr(arma, 'habilidade', "Nenhuma")
                skill_data = get_skill_data(nome_raw)
                if skill_data["tipo"] != "NADA":
                    custo = getattr(arma, 'custo_mana', skill_data["custo"])
                    self.skills_arma.append({"nome": nome_raw, "custo": custo, "data": skill_data})
                    self.cd_skills[nome_raw] = 0.0

            self.arma_raridade = getattr(arma, 'raridade', 'Comum')
            self.arma_critico = getattr(arma, 'critico', 0.0)
            self.arma_vel_ataque = getattr(arma, 'velocidade_ataque', 1.0)
            self.arma_encantamentos = getattr(arma, 'encantamentos', [])
            self.arma_passiva = getattr(arma, 'passiva', None)
            self.arma_tipo = arma.tipo
        else:
            self.arma_raridade = 'Comum'
            self.arma_critico = 0.0
            self.arma_vel_ataque = 1.0
            self.arma_encantamentos = []
            self.arma_passiva = None
            self.arma_tipo = None

        # Skills de afinidade da classe
        for skill_nome in self.class_data.get("skills_afinidade", []):
            skill_data = get_skill_data(skill_nome)
            if skill_data["tipo"] != "NADA":
                self.skills_classe.append({
                    "nome": skill_nome,
                    "custo": skill_data.get("custo", 15),
                    "data": skill_data
                })
                self.cd_skills[skill_nome] = 0.0

        # Compatibilidade com código antigo
        self.skill_arma_nome = self.skills_arma[0]["nome"] if self.skills_arma else "Nenhuma"
        self.custo_skill_arma = self.skills_arma[0]["custo"] if self.skills_arma else 0
        self.cd_skill_arma = 0.0

        # Buffers de objetos criados
        self.buffer_projeteis = []
        self.buffer_areas = []
        self.buffer_beams = []
        self.buffer_orbes = []

        # Efeitos ativos
        self.buffs_ativos = []
        self.dots_ativos = []
        self.status_effects = []
        self.cc_effects = []

        # Estado de combate
        self.morto = False
        self.invencivel_timer = 0.0
        self.flash_timer = 0.0
        self.flash_cor = (255, 255, 255)
        self.stun_timer = 0.0
        self.slow_timer = 0.0
        self.slow_fator = 1.0
        self.modo_adrenalina = False

        # Channeling v8.0
        self.canalizando = False
        self.skill_canalizando = None
        self.tempo_canalizacao = 0.0
        self.usando_skill = False

        # Animação e visual
        self.angulo_olhar = 0.0
        self.angulo_arma_visual = 0.0
        self.cooldown_ataque = 0.0
        self.timer_animacao = 0.0
        self.atacando = False
        self.modo_ataque_aereo = False

        # Sistema de prevenção de multi-hit v10.1
        self.ataque_id = 0
        self.alvos_atingidos_neste_ataque = set()

        # Animação de arma v2.0
        self.weapon_anim_scale = 1.0
        self.weapon_anim_shake = (0, 0)
        self.weapon_trail_positions = []
        self.arma_droppada_pos = None

        # Sistema de corrente v5.0
        self.chain_momentum = 0.0
        self.chain_spin_speed = 0.0
        self.chain_spinning = False
        self.chain_spin_dmg_timer = 0.0
        self.chain_combo = 0
        self.chain_combo_timer = 0.0
        self.chain_mode = 0
        self.chain_pull_target = None
        self.chain_pull_timer = 0.0
        self.chain_whip_crack = False
        self.chain_whip_stacks = 0
        self.chain_recovery_mult = 1.0

        # Sistema dupla v15.0
        self.dual_combo = 0
        self.dual_combo_timer = 0.0
        self.dual_hand = 0
        self.dual_frenzy = False
        self.dual_cross_slash = False

        # Sistema reta v15.0
        self.reta_combo = 0
        self.reta_combo_timer = 0.0
        self.reta_heavy_charging = False
        self.reta_charge_timer = 0.0
        self.reta_parry_window = 0.0

        # Sistema orbital v15.0
        self.orbital_angle = 0.0
        self.orbital_speed = 180.0
        self.orbital_dmg_timer = 0.0
        self.orbital_shield_active = False
        self.orbital_burst_cd = 0.0

        # Sistema transformável v15.0
        self.transform_forma = 0
        self.transform_cd = 0.0
        self.transform_combo = 0
        self.transform_bonus_timer = 0.0

        # Sistema arco v15.0
        self.bow_charge = 0.0
        self.bow_charging = False
        self.bow_perfect_timer = 0.0

        # Sistema arremesso v15.0
        self.throw_volley_cd = 0.0
        self.throw_consecutive = 0

        self.arma_droppada_ang = 0
        self.fator_escala = self.dados.tamanho / ALTURA_PADRAO
        self.alcance_ideal = ALCANCE_IDEAL_DEFAULT

        # Efeitos visuais temporários
        self.dash_trail = []
        self.aura_pulso = 0.0

        # Dash evasivo v7.0
        self.dash_timer = 0.0
        self.pos_historico = []

        # EFF-2: timers de debuffs declarados no __init__
        self.enraizado_timer = 0.0
        self.silenciado_timer = 0.0
        self.cego_timer = 0.0
        self.medo_timer = 0.0
        self.charme_timer = 0.0
        self.exausto_timer = 0.0
        self.fraco_timer = 0.0
        self.vulnerabilidade_timer = 0.0
        self.dano_reduzido = 1.0
        self.vulnerabilidade = 1.0
        self.cura_bloqueada = 0.0
        self.congelado = False
        self.dormindo = False
        self.sendo_puxado = False
        self.tempo_parado = False
        self.marcado = False

        # IA — import inline intencional para quebrar ciclo:
        # ai/__init__ → brain → core/__init__ → entities → fighter/entity → ai
        from ai import AIBrain  # noqa: PLC0415
        self.brain = AIBrain(self)

    @property
    def ai(self):
        """Alias legado compatível com o brain atual."""
        return self.brain

    @ai.setter
    def ai(self, value):
        self.brain = value

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def update(self, dt, inimigo, todos_lutadores=None):
        """
        Atualiza estado do lutador.

        Args:
            dt: Delta time
            inimigo: Inimigo principal (nearest enemy)
            todos_lutadores: Lista de TODOS os lutadores na arena (None = 1v1 legado)
        """
        if self.invencivel_timer > 0:
            self.invencivel_timer -= dt
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.stun_timer > 0:
            self.stun_timer -= dt

        congelado_t = getattr(self, 'congelado_timer', 0)
        if congelado_t > 0:
            self.congelado_timer = congelado_t - dt
            if self.congelado_timer <= 0:
                self.congelado = False

        if self.cd_skill_arma > 0:
            self.cd_skill_arma -= dt
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_fator = 1.0
        if getattr(self, 'cura_bloqueada', 0) > 0:
            self.cura_bloqueada -= dt

        for attr in ['silenciado_timer', 'cego_timer', 'medo_timer', 'charme_timer', 'exposto_timer']:
            val = getattr(self, attr, 0)
            if val > 0:
                setattr(self, attr, val - dt)

        enraizado_val = getattr(self, 'enraizado_timer', 0)
        if enraizado_val > 0:
            self.enraizado_timer = enraizado_val - dt
            if self.enraizado_timer <= 0 and self.slow_fator == 0.0:
                self.slow_fator = 1.0

        if getattr(self, 'fraco_timer', 0) > 0:
            self.fraco_timer -= dt
            if self.fraco_timer <= 0:
                self.dano_reduzido = 1.0

        if getattr(self, 'vulnerabilidade_timer', 0) > 0:
            self.vulnerabilidade_timer -= dt
            if self.vulnerabilidade_timer <= 0:
                self.vulnerabilidade = 1.0

        if getattr(self, 'exausto_timer', 0) > 0:
            self.exausto_timer -= dt
            if self.exausto_timer <= 0:
                self.regen_mana_base = self.class_data.get("regen_mana", 3.0)

        if getattr(self, 'tempo_parado', False) and self.stun_timer <= 0:
            self.tempo_parado = False
            if self.slow_fator == 0.0:
                self.slow_fator = 1.0

        if getattr(self, 'bomba_relogio_timer', 0) > 0:
            self.bomba_relogio_timer -= dt
            if self.bomba_relogio_timer <= 0:
                dano_bomba = getattr(self, 'bomba_relogio_dano', 80.0)
                self.vida = max(0, self.vida - dano_bomba)
                self.flash_timer = 0.3
                self.flash_cor = (255, 100, 0)
                if self.vida <= 0:
                    self.morrer()

        if self.stun_timer <= 0:
            if getattr(self, 'em_vortex', False):
                self.em_vortex = False
            if getattr(self, 'sendo_puxado', False):
                self.sendo_puxado = False

        for skill_nome in list(self.cd_skills.keys()):
            if self.cd_skills[skill_nome] > 0:
                self.cd_skills[skill_nome] -= dt

        self._atualizar_buffs(dt)
        self._atualizar_dots(dt)
        self._atualizar_dash_trail(dt)
        self._atualizar_orbes(dt)

        if self.dash_timer > 0:
            self.dash_timer -= dt

        self.pos_historico.append((self.pos[0], self.pos[1]))
        if len(self.pos_historico) > 15:
            self.pos_historico.pop(0)

        self.aura_pulso += dt * 3
        if self.aura_pulso > math.pi * 2:
            self.aura_pulso = 0

        if self.morto:
            self.aplicar_fisica(dt)
            return

        mana_regen = self.regen_mana_base
        if getattr(self, 'exausto_timer', 0) > 0:
            mana_regen *= 0.3
        if "Mago" in self.classe_nome:
            mana_regen *= 1.5
        self.mana = min(self.mana_max, self.mana + mana_regen * dt)

        if "Paladino" in self.classe_nome:
            self.vida = min(self.vida_max, self.vida + self.vida_max * 0.005 * dt)

        # v13.0: Multi-fighter targeting
        if todos_lutadores is not None:
            inimigos_vivos = [
                f for f in todos_lutadores
                if f is not self and not f.morto and f.team_id != self.team_id
            ]
            if inimigos_vivos:
                inimigo = min(inimigos_vivos, key=lambda f: math.hypot(
                    f.pos[0] - self.pos[0], f.pos[1] - self.pos[1]))

        if inimigo is None:
            self.aplicar_fisica(dt)
            return

        dx = inimigo.pos[0] - self.pos[0]
        dy = inimigo.pos[1] - self.pos[1]
        distancia = math.hypot(dx, dy)

        pos_intercept = getattr(self.brain, '_pos_interceptacao', None) if self.brain else None
        if (pos_intercept is not None
                and self.brain.acao_atual in ("APROXIMAR", "PRESSIONAR", "CONTRA_ATAQUE")):
            alvo_x, alvo_y = pos_intercept
        else:
            alvo_x, alvo_y = inimigo.pos[0], inimigo.pos[1]

        angulo_alvo = math.degrees(math.atan2(alvo_y - self.pos[1], alvo_x - self.pos[0]))
        diff = normalizar_angulo(angulo_alvo - self.angulo_olhar)
        vel_giro = 20.0 if "Assassino" in self.classe_nome or "Ninja" in self.classe_nome else 10.0
        self.angulo_olhar += diff * vel_giro * dt

        algum_inimigo_vivo = not inimigo.morto
        if todos_lutadores is not None:
            algum_inimigo_vivo = any(
                not f.morto for f in todos_lutadores
                if f is not self and f.team_id != self.team_id
            )

        if self.stun_timer <= 0 and algum_inimigo_vivo:
            if self.brain is not None:
                self.brain.processar(dt, distancia, inimigo, todos_lutadores=todos_lutadores)
                self.executar_movimento(dt, distancia)
                self._atualizar_chain_state(dt, distancia)
                self.executar_ataques(dt, distancia, inimigo)

        self.aplicar_fisica(dt)
