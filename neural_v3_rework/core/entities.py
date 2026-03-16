"""
NEURAL FIGHTS - Entidade Lutador
Classe principal do lutador com sistema de combate.
"""

import math
import random
from utils.config import PPM, GRAVIDADE_Z, ATRITO, ALTURA_PADRAO
from utils.balance_config import (  # E06
    CRITICO_CHANCE_BONUS_RAGE, CRITICO_MULT_BASE,
    DANO_MULT_FLANQUEAR, DANO_MULT_COSTAS, DANO_MULT_AERIAL, DANO_MULT_EXECUCAO,
    DANO_ECO_RATIO, ESTAMINA_MAX, ESTAMINA_CUSTO_SKILL_MULT, ESTAMINA_CUSTO_SKILL_MULT2,
    ESTAMINA_CUSTO_DASH_MULT, ESTAMINA_CUSTO_DASH_MULT2,
    MANA_BASE, MANA_POR_ATRIBUTO, SLOW_FATOR_DEFAULT, SLOW_DURACAO_DEFAULT,
    CD_ARMA_MAX_RATIO, CD_ARMA_MAX_ABSOLUTO, ALCANCE_IDEAL_DEFAULT,
)
import logging
_log = logging.getLogger("entities")


# A05: classe leve que substitui os objetos anônimos criados via type('SE', (), {...})()
# em _atualizar_dots. Usar uma classe nomeada é mais rápido (sem criação de metaclasse
# anônima a cada frame) e permite isinstance() checks no brain/magic_system.
class StatusSnapshot:
    """Snapshot imutável de um status effect para leitura pela IA e magic_system."""
    __slots__ = (
        'nome', 'mod_velocidade', 'mod_dano_causado',
        'mod_dano_recebido', 'pode_mover', 'pode_atacar',
        'pode_usar_skill', 'dano_por_tick',
    )

    def __init__(self, nome, mod_velocidade=1.0, mod_dano_causado=1.0,
                 mod_dano_recebido=1.0, pode_mover=True, pode_atacar=True,
                 pode_usar_skill=True, dano_por_tick=0):
        self.nome              = nome
        self.mod_velocidade    = mod_velocidade
        self.mod_dano_causado  = mod_dano_causado
        self.mod_dano_recebido = mod_dano_recebido
        self.pode_mover        = pode_mover
        self.pode_atacar       = pode_atacar
        self.pode_usar_skill   = pode_usar_skill
        self.dano_por_tick     = dano_por_tick


class Lutador:
    """
    Classe principal do lutador com suporte completo a:
    - Sistema de classes expandido
    - Novos tipos de skills (DASH, BUFF, AREA, BEAM, SUMMON)
    - Efeitos de status (DoT, buffs, debuffs)
    - Batalhas multi-lutador com equipes (v13.0)
    """
    def __init__(self, dados_char, pos_x, pos_y, team_id=0):
        # Importações tardias para evitar circular imports
        from ai import AIBrain
        from core.skills import get_skill_data
        from models import get_class_data
        from core.combat import DotEffect
        from effects.audio import AudioManager
        
        self.dados = dados_char
        self.pos = [pos_x, pos_y]
        self.vel = [0.0, 0.0]
        self.z = 0.0
        self.vel_z = 0.0
        self.raio_fisico = (self.dados.tamanho / 4.0)
        
        # === v13.0: SISTEMA DE EQUIPES ===
        self.team_id = team_id  # 0 = time A, 1 = time B, -1 = FFA
        
        # Carrega dados da classe
        self.classe_nome = getattr(self.dados, 'classe', "Guerreiro (Força Bruta)")
        self.class_data = get_class_data(self.classe_nome)
        
        # Status calculados com modificadores de classe
        self.vida_max = self._calcular_vida_max()
        self.vida = self.vida_max
        self.estamina = ESTAMINA_MAX
        self.estamina_max = ESTAMINA_MAX
        self.mana_max = self._calcular_mana_max()
        self.mana = self.mana_max
        
        # Regeneração baseada na classe
        self.regen_mana_base = self.class_data.get("regen_mana", 3.0)
        
        # Modificadores de classe
        self.mod_dano = self.class_data.get("mod_forca", 1.0)
        self.mod_velocidade = self.class_data.get("mod_velocidade", 1.0)
        self.mod_defesa = 1.0 / self.class_data.get("mod_vida", 1.0)
        
        # Cor de aura da classe
        self.cor_aura = self.class_data.get("cor_aura", (200, 200, 200))
        
        # === SISTEMA DE SKILLS EXPANDIDO ===
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
                        self.skills_arma.append({
                            "nome": nome_hab,
                            "custo": custo_hab,
                            "data": skill_data
                        })
                        self.cd_skills[nome_hab] = 0.0
            else:
                nome_raw = getattr(arma, 'habilidade', "Nenhuma")
                skill_data = get_skill_data(nome_raw)
                if skill_data["tipo"] != "NADA":
                    custo = getattr(arma, 'custo_mana', skill_data["custo"])
                    self.skills_arma.append({
                        "nome": nome_raw,
                        "custo": custo,
                        "data": skill_data
                    })
                    self.cd_skills[nome_raw] = 0.0
            
            # Carrega dados de raridade da arma
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
        
        # Carrega skills de afinidade da classe
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
        
        # Buffers para objetos criados
        self.buffer_projeteis = []
        self.buffer_areas = []
        self.buffer_beams = []
        self.buffer_orbes = []
        
        # Efeitos ativos
        self.buffs_ativos = []
        self.dots_ativos = []
        self.status_effects = []  # Lista unificada para brain.py e magic_system

        # Estado de combate
        self.morto = False
        self.invencivel_timer = 0.0
        self.flash_timer = 0.0
        self.flash_cor = (255, 255, 255)  # Cor do flash de dano
        self.stun_timer = 0.0
        self.slow_timer = 0.0
        self.slow_fator = 1.0
        self.modo_adrenalina = False
        
        # === SISTEMA DE CHANNELING v8.0 (Para Magos) ===
        self.canalizando = False
        self.skill_canalizando = None
        self.tempo_canalizacao = 0.0
        self.usando_skill = False  # Flag para skills em geral
        
        # Animação e visual
        self.angulo_olhar = 0.0
        self.angulo_arma_visual = 0.0
        self.cooldown_ataque = 0.0
        self.timer_animacao = 0.0
        self.atacando = False
        self.modo_ataque_aereo = False
        
        # === SISTEMA DE PREVENÇÃO DE MULTI-HIT v10.1 ===
        # Cada ataque recebe um ID único para evitar múltiplos hits no mesmo swing
        self.ataque_id = 0  # Incrementa a cada novo ataque
        self.alvos_atingidos_neste_ataque = set()  # IDs dos alvos já atingidos neste ataque
        
        # === SISTEMA DE ANIMAÇÃO DE ARMAS v2.0 ===
        self.weapon_anim_scale = 1.0      # Escala da arma (squash/stretch)
        self.weapon_anim_shake = (0, 0)   # Offset de shake no impacto
        self.weapon_trail_positions = []  # Posições do trail da arma
        self.arma_droppada_pos = None

        # === SISTEMA DE CORRENTE v5.0 — Mecânicas únicas por estilo ===
        self.chain_momentum = 0.0        # Mangual: acumula a cada hit (0→1)
        self.chain_spin_speed = 0.0      # Meteor Hammer: velocidade de spin
        self.chain_spinning = False      # Meteor Hammer: girando ativamente?
        self.chain_spin_dmg_timer = 0.0  # Meteor Hammer: timer de dano contínuo
        self.chain_combo = 0             # Kusarigama: combo counter
        self.chain_combo_timer = 0.0     # Kusarigama: tempo até reset do combo
        self.chain_mode = 0              # Kusarigama: 0=foice(perto), 1=peso(longe)
        self.chain_pull_target = None    # Corrente com Peso: alvo sendo puxado
        self.chain_pull_timer = 0.0      # Corrente com Peso: duração do pull
        self.chain_whip_crack = False    # Chicote: próximo hit é crack (sweet spot)
        self.chain_whip_stacks = 0       # Chicote: stacks de velocidade
        self.chain_recovery_mult = 1.0   # Multiplica cooldown pós-ataque

        # === SISTEMA DUPLA v15.0 — Combo counter, frenzy, cross-slash ===
        self.dual_combo = 0              # Hits consecutivos (0→8+)
        self.dual_combo_timer = 0.0      # Tempo até combo resetar
        self.dual_hand = 0              # 0=esquerda, 1=direita (alterna)
        self.dual_frenzy = False         # Ativado em combo >= 4
        self.dual_cross_slash = False    # Ativado em combo >= 6 (ambas adagas)

        # === SISTEMA RETA v15.0 — Stance por estilo ===
        self.reta_combo = 0             # Sequência de golpes (padrões por estilo)
        self.reta_combo_timer = 0.0     # Tempo até reset
        self.reta_heavy_charging = False  # Carregando golpe pesado
        self.reta_charge_timer = 0.0    # Tempo carregando
        self.reta_parry_window = 0.0    # Janela de parry ativa

        # === SISTEMA ORBITAL v15.0 — Defesa + dano automático ===
        self.orbital_angle = 0.0        # Ângulo de rotação atual
        self.orbital_speed = 180.0      # Graus/segundo base
        self.orbital_dmg_timer = 0.0    # Timer de dano por toque
        self.orbital_shield_active = False  # Defesa ativa bloqueando projéteis
        self.orbital_burst_cd = 0.0     # Cooldown do burst ofensivo

        # === SISTEMA TRANSFORMÁVEL v15.0 — Troca de forma ===
        self.transform_forma = 0        # Forma atual (0 ou 1)
        self.transform_cd = 0.0         # Cooldown de troca
        self.transform_combo = 0        # Combo acumulado na forma atual
        self.transform_bonus_timer = 0.0  # Bônus pós-troca

        # === SISTEMA ARCO v15.0 — Carga e tiro especial ===
        self.bow_charge = 0.0           # Tempo carregando (0→1.5)
        self.bow_charging = False       # Carregando ativamente
        self.bow_perfect_timer = 0.0    # Janela do tiro perfeito

        # === SISTEMA ARREMESSO v15.0 — Retorno e ricochete ===
        self.throw_volley_cd = 0.0      # Cooldown de volley especial
        self.throw_consecutive = 0      # Arremessos consecutivos

        self.arma_droppada_ang = 0
        self.fator_escala = self.dados.tamanho / ALTURA_PADRAO
        self.alcance_ideal = ALCANCE_IDEAL_DEFAULT
        
        # Efeitos visuais temporários
        self.dash_trail = []
        self.aura_pulso = 0.0
        
        # Sistema de dash evasivo v7.0
        self.dash_timer = 0.0
        self.pos_historico = []

        # EFF-2: Timers de debuffs declarados no __init__ — elimina hasattr em hot paths
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

        # D02: registro observável de CCs ativos — lido por brain.py e magic_system
        # Os float timers acima continuam sendo a fonte de verdade;
        # cc_effects é atualizado em _aplicar_efeito_status() e em _atualizar_dots().
        self.cc_effects: list = []  # list[StatusSnapshot] — CCs ativos neste frame

        # IA
        self.brain = AIBrain(self)

    def _calcular_vida_max(self):
        """Calcula vida máxima com modificadores"""
        base = 80.0 + (self.dados.resistencia * 5)  # Vida reduzida para lutas mais rápidas
        return base * self.class_data.get("mod_vida", 1.0)
    
    def _calcular_mana_max(self):
        """Calcula mana máxima com modificadores"""
        base = MANA_BASE + (getattr(self.dados, 'mana', 0) * MANA_POR_ATRIBUTO)
        return base * self.class_data.get("mod_mana", 1.0)

    def trocar_skill(self):
        """Troca para a próxima skill disponível"""
        if len(self.skills_arma) <= 1:
            return
        
        self.skill_atual_idx = (self.skill_atual_idx + 1) % len(self.skills_arma)
        skill = self.skills_arma[self.skill_atual_idx]
        self.skill_arma_nome = skill["nome"]
        self.custo_skill_arma = skill["custo"]
    
    def get_skill_atual(self):
        """Retorna dados da skill atualmente selecionada"""
        if not self.skills_arma:
            return None
        return self.skills_arma[self.skill_atual_idx]
    
    def calcular_dano_ataque(self, dano_base):
        """Calcula dano final com crítico, encantamentos e PASSIVA da arma (BUG-03 fix)"""
        from models import ENCANTAMENTOS

        dano = dano_base * self.mod_dano

        # FP-2: aplica penalidade de FRACO se ativa (antes era setado mas nunca lido)
        if getattr(self, 'dano_reduzido', 1.0) != 1.0:
            dano *= self.dano_reduzido

        # === PASSIVA: dano_bonus ===
        passiva = self.arma_passiva or {}
        if passiva.get("efeito") == "dano_bonus":
            dano *= 1.0 + passiva.get("valor", 0) / 100.0

        # === PASSIVA: berserk (dano extra quando HP baixo) ===
        if passiva.get("efeito") == "berserk":
            if self.vida / max(self.vida_max, 1) < 0.30:
                dano *= 1.0 + passiva.get("valor", 0) / 100.0

        # === PASSIVA: all_stats (bonus de dano incluso) ===
        if passiva.get("efeito") == "all_stats":
            dano *= 1.0 + passiva.get("valor", 0) / 100.0

        # Chance crítica base da arma + classe + PASSIVA: crit_chance
        critico_chance = self.arma_critico
        if "Assassino" in self.classe_nome:
            critico_chance += CRITICO_CHANCE_BONUS_RAGE
        if passiva.get("efeito") == "crit_chance":
            critico_chance += passiva.get("valor", 0) / 100.0

        is_critico = random.random() < critico_chance
        if is_critico:
            mult_critico = CRITICO_MULT_BASE
            # === PASSIVA: crit_damage (aumenta multiplicador crítico) ===
            if passiva.get("efeito") == "crit_damage":
                mult_critico += passiva.get("valor", 0) / 100.0
            dano *= mult_critico

        for enc_nome in self.arma_encantamentos:
            if enc_nome in ENCANTAMENTOS:
                enc = ENCANTAMENTOS[enc_nome]
                dano += enc.get("dano_bonus", 0)

        # === v15.0 — Bônus por mecânica de arma ===
        tipo_arma = getattr(self.dados, 'tipo_arma', '')
        
        # Dupla: frenzy +15%, cross-slash +30%
        if tipo_arma == 'Dupla':
            if getattr(self, 'dual_cross_slash', False):
                dano *= DANO_MULT_FLANQUEAR
            elif getattr(self, 'dual_frenzy', False):
                dano *= DANO_MULT_COSTAS
        
        # Reta: 3° golpe do combo = finisher +20%
        if tipo_arma == 'Reta':
            if getattr(self, 'reta_combo', 0) >= 2:
                dano *= DANO_MULT_AERIAL
        
        # Transformável: bonus após troca de forma
        if tipo_arma == 'Transformável':
            if getattr(self, 'transform_bonus_timer', 0) > 0:
                dano *= DANO_MULT_EXECUCAO

        return dano, is_critico

    def aplicar_passiva_em_hit(self, dano_aplicado, alvo, pos_impacto_px=None):
        """
        Processa efeitos de passiva de arma disparados ao acertar um golpe.
        BUG-03 fix: lifesteal, execute, double_hit, aoe_damage, teleport, random_element.
        Retorna dict com flags para simulacao.py processar efeitos visuais.
        """
        passiva = self.arma_passiva or {}
        efeito = passiva.get("efeito")
        valor = passiva.get("valor", 0)
        resultado = {}

        # === PASSIVA: lifesteal ===
        if efeito == "lifesteal":
            cura = dano_aplicado * (valor / 100.0)
            self.vida = min(self.vida_max, self.vida + cura)
            resultado["lifesteal"] = cura

        # === PASSIVA: execute (golpe final em HP baixo) ===
        if efeito == "execute":
            if alvo.vida / max(alvo.vida_max, 1) < (valor / 100.0):
                alvo.vida = 0
                alvo.morrer()
                resultado["execute"] = True

        # === PASSIVA: double_hit (chance de aplicar dano novamente) ===
        if efeito == "double_hit" and random.random() < (valor / 100.0):
            if not alvo.morto:
                dano_eco = dano_aplicado * DANO_ECO_RATIO
                alvo.vida = max(0, alvo.vida - dano_eco)
                resultado["double_hit"] = dano_eco

        # === PASSIVA: aoe_damage (porcentagem do dano em área ao redor do alvo) ===
        if efeito == "aoe_damage":
            resultado["aoe_damage"] = {"dano": dano_aplicado * (valor / 100.0),
                                       "x": alvo.pos[0], "y": alvo.pos[1]}

        # === PASSIVA: teleport (chance de teleportar atrás do inimigo) ===
        if efeito == "teleport" and random.random() < (valor / 100.0):
            ang = math.atan2(alvo.pos[1] - self.pos[1], alvo.pos[0] - self.pos[0])
            self.pos[0] = alvo.pos[0] - math.cos(ang) * 1.2
            self.pos[1] = alvo.pos[1] - math.sin(ang) * 1.2
            resultado["teleport"] = True

        # === PASSIVA: random_element (adiciona efeito elemental aleatório) ===
        if efeito == "random_element":
            from core.combat import DotEffect
            elemento = random.choice(["QUEIMANDO", "ENVENENADO", "CONGELADO", "PARALISIA"])
            cores = {"QUEIMANDO": (255, 100, 0), "ENVENENADO": (100, 255, 100),
                     "CONGELADO": (150, 220, 255), "PARALISIA": (255, 255, 100)}
            dot = DotEffect(elemento, alvo, dano_aplicado * 0.1, 3.0, cores.get(elemento, (255, 255, 255)))
            if not alvo.morto:
                alvo.dots_ativos.append(dot)
            resultado["random_element"] = elemento

        # === v15.0 — Efeitos on-hit por tipo de arma ===
        tipo_arma = getattr(self.dados, 'tipo_arma', '')
        
        # Dupla combo 4+: sangramento (bleed)
        if tipo_arma == 'Dupla' and getattr(self, 'dual_combo', 0) >= 4:
            from core.combat import DotEffect
            if not alvo.morto:
                bleed = DotEffect("Sangrando", alvo, dano_aplicado * 0.06, 2.5, (200, 30, 30))
                alvo.dots_ativos.append(bleed)
                resultado["dual_bleed"] = True
        
        # Reta 3° golpe: stun curto
        if tipo_arma == 'Reta' and getattr(self, 'reta_combo', 0) >= 2:
            if not alvo.morto:
                alvo.stun_timer = max(getattr(alvo, 'stun_timer', 0), 0.3)
                resultado["reta_stun"] = True
        
        # Corrente: arrasto (pull enemy slightly towards self)
        if tipo_arma == 'Corrente':
            if not alvo.morto:
                dx = self.pos[0] - alvo.pos[0]
                dy = self.pos[1] - alvo.pos[1]
                d = math.hypot(dx, dy)
                if d > 0.1:
                    pull = 0.3
                    alvo.vel[0] += (dx / d) * pull
                    alvo.vel[1] += (dy / d) * pull
                    resultado["chain_pull"] = True

        return resultado
    
    def aplicar_efeitos_encantamento(self, alvo, dano_aplicado=0):
        """Aplica efeitos de encantamentos no alvo"""
        from models import ENCANTAMENTOS
        from core.combat import DotEffect
        
        for enc_nome in self.arma_encantamentos:
            if enc_nome not in ENCANTAMENTOS:
                continue
            
            enc = ENCANTAMENTOS[enc_nome]
            efeito = enc.get("efeito")
            
            if random.random() > 0.5:
                continue
            
            if efeito == "burn":
                dot = DotEffect("Queimando", alvo, 5, 3.0, (255, 100, 0))
                alvo.dots_ativos.append(dot)
            elif efeito == "slow":
                alvo.slow_timer = SLOW_DURACAO_DEFAULT
                alvo.slow_fator = SLOW_FATOR_DEFAULT
            elif efeito == "poison":
                dot = DotEffect("Envenenado", alvo, enc.get("dot_dano", 3),
                               enc.get("dot_duracao", 5.0), (100, 255, 100))
                alvo.dots_ativos.append(dot)
            elif efeito == "lifesteal":
                # BUG-F3: lifesteal deve ser baseado no dano aplicado, não no HP do alvo
                percent = enc.get("lifesteal_percent", 10) / 100.0
                cura = dano_aplicado * percent
                self.vida = min(self.vida_max, self.vida + cura)

    def usar_skill_arma(self, skill_idx=None):
        """Usa a skill equipada na arma"""
        from core.combat import Projetil, AreaEffect, Beam, Buff, Summon, Trap, Transform, Channel
        from effects.audio import AudioManager

        # BUG-C4: Silenciado impede uso de skills
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
        
        # CM-15: FP4 — Conjuração Perfeita: custo pela metade durante buff
        for buff in self.buffs_ativos:
            if getattr(buff, 'custo_mana_metade', False):
                custo_real *= 0.5
                break
        
        if self.arma_passiva and self.arma_passiva.get("efeito") == "no_mana_cost":
            chance = self.arma_passiva.get("valor", 0) / 100.0
            if random.random() < chance:
                custo_real = 0
        
        # CM-16: custo_vida para skills de arma (antes só existia em usar_skill_classe)
        custo_vida = data.get("custo_vida", 0) or data.get("custo_vida_percent", 0) * self.vida_max
        if custo_vida > 0:
            if self.vida <= custo_vida:
                return False
            self.vida -= custo_vida
        
        if self.mana < custo_real:
            return False
        
        self.mana -= custo_real
        
        # === VFX v5.0: CHARGEUP DRAMÁTICO no cast ===
        try:
            from effects.magic_vfx import MagicVFXManager, get_element_from_skill
            _vfx = MagicVFXManager.get_instance()
            if _vfx:
                _elem = get_element_from_skill(nome_skill, data)
                _tipo_sk = data.get("tipo", "")
                # Intensidade baseada no dano/cooldown da skill (mais poderosa = mais dramática)
                _dano   = max(data.get("dano", 0), data.get("dano_maximo", 0))
                _cd     = data.get("cooldown", 3.0)
                _intens = min(3.0, max(0.7, (_dano / 18.0 + _cd / 6.0) * 0.65))
                # Skills sem dano direto (buffs, summons) têm chargeup diferente
                if _tipo_sk in ("BUFF", "TRANSFORM", "SUMMON"):
                    _intens = max(1.4, _intens)
                # Duração do chargeup: mais longa para skills pesadas/canalização
                if _tipo_sk == "CHANNEL":
                    _dur = 0.90
                elif _tipo_sk in ("TRANSFORM", "SUMMON"):
                    _dur = 0.70
                elif _tipo_sk == "AREA":
                    _dur = 0.55
                elif _tipo_sk == "BUFF":
                    _dur = 0.45
                elif _tipo_sk in ("PROJETIL", "BEAM"):
                    _dur = 0.30
                else:
                    _dur = 0.40
                _cx = self.pos[0] * 50
                _cy = self.pos[1] * 50
                _vfx.spawn_chargeup(_cx, _cy, _elem, _dur, _intens)
                # Para skills especiais: burst de impacto imediato ao lançar
                if _tipo_sk in ("BUFF", "TRANSFORM"):
                    _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.80)
                elif _tipo_sk == "SUMMON":
                    _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.65)
                    _vfx.spawn_aura(_cx, _cy, 40, _elem, _intens * 0.5)
                elif _tipo_sk == "AREA" and _dano > 30:
                    _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.55)
        except Exception as _e:
            _log.debug("%s", _e)
        
        cd = data["cooldown"]
        if self.arma_passiva and self.arma_passiva.get("efeito") == "cooldown":
            cd *= (1 - self.arma_passiva.get("valor", 0) / 100.0)
        
        # CM-17: FP4 — sem_cooldown buff (Conjuração Perfeita) zera cooldown
        for buff in self.buffs_ativos:
            if getattr(buff, 'sem_cooldown', False):
                cd = 0
                break
        
        self.cd_skills[nome_skill] = cd
        # BUG-A3 fix: o GCD anterior (min(cd, 0.8)) bloqueava skills de CD curto
        # (ex.: dashes de 0.3s ficavam travados por 0.8s).  Novo GCD usa o
        # tempo_cast da skill quando definido, ou 20% do cooldown com teto de 0.35s.
        # Isso preserva a intenção do GCD (evitar cast instantâneo em loop)
        # sem punir kits de skills rápidas.
        tempo_cast = data.get("tempo_cast", None)
        if tempo_cast is not None:
            self.cd_skill_arma = max(0.05, tempo_cast)
        else:
            self.cd_skill_arma = min(cd * CD_ARMA_MAX_RATIO, CD_ARMA_MAX_ABSOLUTO)
        
        rad = math.radians(self.angulo_olhar)
        spawn_x = self.pos[0] + math.cos(rad) * 0.6
        spawn_y = self.pos[1] + math.sin(rad) * 0.6
        
        if tipo == "PROJETIL":
            # === ÁUDIO v10.0 - SOM DE CAST DE PROJÉTIL ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("PROJETIL", nome_skill, self.pos[0], phase="cast")
            
            multi = data.get("multi_shot", 1)
            if multi > 1:
                spread = 30
                for i in range(multi):
                    ang_offset = -spread/2 + (spread / (multi-1)) * i
                    p = Projetil(nome_skill, spawn_x, spawn_y, self.angulo_olhar + ang_offset, self)
                    self.buffer_projeteis.append(p)
            else:
                p = Projetil(nome_skill, spawn_x, spawn_y, self.angulo_olhar, self)
                self.buffer_projeteis.append(p)
            
            if data["dano"] > 20:
                self.vel[0] -= math.cos(rad) * 5.0
                self.vel[1] -= math.sin(rad) * 5.0
        
        elif tipo == "AREA":
            # === ÁUDIO v10.0 - SOM DE ÁREA ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("AREA", nome_skill, self.pos[0], phase="cast")
            
            area = AreaEffect(nome_skill, self.pos[0], self.pos[1], self)
            self.buffer_areas.append(area)
        
        elif tipo == "DASH":
            # === ÁUDIO v10.0 - SOM DE DASH ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("DASH", nome_skill, self.pos[0], phase="cast")
            
            dist = data.get("distancia", 4.0)
            dano = data.get("dano", 0)
            
            self.pos[0] += math.cos(rad) * dist
            self.pos[1] += math.sin(rad) * dist
            
            self.dash_timer = 0.25
            
            for i in range(5):
                self.dash_trail.append((
                    self.pos[0] - math.cos(rad) * dist * (i/5),
                    self.pos[1] - math.sin(rad) * dist * (i/5),
                    1.0 - i*0.2
                ))
            
            if dano > 0:
                area = AreaEffect(nome_skill, self.pos[0], self.pos[1], self)
                area.dano = dano
                area.raio = 1.5
                self.buffer_areas.append(area)

            # BUG-05 fix: aplica dano_chegada no ponto de destino do dash
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
            # === ÁUDIO v10.0 - SOM DE BUFF ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("BUFF", nome_skill, self.pos[0], phase="cast")
            
            if data.get("cura"):
                self.vida = min(self.vida_max, self.vida + data["cura"])
            
            buff = Buff(nome_skill, self)
            self.buffs_ativos.append(buff)
        
        elif tipo == "BEAM":
            # === ÁUDIO v10.0 - SOM DE BEAM ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("BEAM", nome_skill, self.pos[0], phase="cast")
            
            alcance = data.get("alcance", 8.0)
            end_x = self.pos[0] + math.cos(rad) * alcance
            end_y = self.pos[1] + math.sin(rad) * alcance
            
            beam = Beam(nome_skill, self.pos[0], self.pos[1], end_x, end_y, self)
            self.buffer_beams.append(beam)
        
        # === TIPOS ADICIONAIS (v2.0) ===
        elif tipo == "SUMMON":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("SUMMON", nome_skill, self.pos[0], phase="cast")
            
            summon_x = self.pos[0] + math.cos(rad) * 1.5
            summon_y = self.pos[1] + math.sin(rad) * 1.5
            
            summon = Summon(nome_skill, summon_x, summon_y, self)
            if not hasattr(self, 'buffer_summons'):
                self.buffer_summons = []
            self.buffer_summons.append(summon)
        
        elif tipo == "TRAP":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("TRAP", nome_skill, self.pos[0], phase="cast")
            
            trap_x = self.pos[0] + math.cos(rad) * 2.0
            trap_y = self.pos[1] + math.sin(rad) * 2.0
            
            trap = Trap(nome_skill, trap_x, trap_y, self)
            if not hasattr(self, 'buffer_traps'):
                self.buffer_traps = []
            self.buffer_traps.append(trap)
        
        elif tipo == "TRANSFORM":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("TRANSFORM", nome_skill, self.pos[0], phase="cast")
            
            transform = Transform(nome_skill, self)
            self.transformacao_ativa = transform
        
        elif tipo == "CHANNEL":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("CHANNEL", nome_skill, self.pos[0], phase="cast")
            
            channel = Channel(nome_skill, self)
            if not hasattr(self, 'buffer_channels'):
                self.buffer_channels = []
            self.buffer_channels.append(channel)
        
        return True

    def usar_skill_classe(self, skill_nome):
        """Usa uma skill de classe específica"""
        from core.combat import Projetil, AreaEffect, Beam, Buff, Summon, Trap, Transform, Channel
        from effects.audio import AudioManager

        # BUG-C4: Silenciado impede uso de skills
        if getattr(self, 'silenciado_timer', 0) > 0:
            return False

        skill_info = None
        for sk in self.skills_classe:
            if sk["nome"] == skill_nome:
                skill_info = sk
                break
        
        if not skill_info:
            return False
        
        if self.cd_skills.get(skill_nome, 0) > 0:
            return False
        
        data = skill_info["data"]
        tipo = data.get("tipo", "NADA")
        custo = skill_info["custo"]
        
        if "Mago" in self.classe_nome:
            custo *= 0.8
        
        # CM-15b: FP4 — Conjuração Perfeita: custo pela metade durante buff
        for buff in self.buffs_ativos:
            if getattr(buff, 'custo_mana_metade', False):
                custo *= 0.5
                break
        
        # Custo em vida (Pacto de Sangue, Sacrifício)
        custo_vida = data.get("custo_vida", 0) or data.get("custo_vida_percent", 0) * self.vida_max
        if custo_vida > 0:
            if self.vida <= custo_vida:
                return False  # Não pode usar se morreria
            self.vida -= custo_vida
        
        if self.mana < custo:
            return False
        
        self.mana -= custo

        # === VFX v5.0: CHARGEUP para skills de classe ===
        try:
            from effects.magic_vfx import MagicVFXManager, get_element_from_skill
            _vfx = MagicVFXManager.get_instance()
            if _vfx:
                _elem = get_element_from_skill(skill_nome, data)
                _dano = max(data.get("dano", 0), data.get("dano_maximo", 0))
                _cd   = data.get("cooldown", 3.0)
                _intens = min(2.8, max(0.7, (_dano / 18.0 + _cd / 6.0) * 0.60))
                if tipo in ("BUFF", "TRANSFORM", "SUMMON"):
                    _intens = max(1.3, _intens)
                _dur = {"CHANNEL": 0.85, "TRANSFORM": 0.65, "SUMMON": 0.65,
                        "AREA": 0.50, "BUFF": 0.40, "BEAM": 0.28}.get(tipo, 0.35)
                _cx, _cy = self.pos[0] * 50, self.pos[1] * 50
                _vfx.spawn_chargeup(_cx, _cy, _elem, _dur, _intens)
                if tipo in ("BUFF", "TRANSFORM"):
                    _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.75)
                elif tipo == "SUMMON":
                    _vfx.spawn_impact_burst(_cx, _cy, _elem, _intens * 0.60)
        except Exception as _e:
            _log.debug("%s", _e)

        cd = data.get("cooldown", 5.0)
        
        # CM-17b: FP4 — sem_cooldown buff (Conjuração Perfeita) zera cooldown
        for buff in self.buffs_ativos:
            if getattr(buff, 'sem_cooldown', False):
                cd = 0
                break
        
        self.cd_skills[skill_nome] = cd
        
        rad = math.radians(self.angulo_olhar)
        spawn_x = self.pos[0] + math.cos(rad) * 0.6
        spawn_y = self.pos[1] + math.sin(rad) * 0.6
        
        if tipo == "PROJETIL":
            # === ÁUDIO v10.0 - SOM DE SKILL DE CLASSE ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("PROJETIL", skill_nome, self.pos[0], phase="cast")
            
            multi = data.get("multi_shot", 1)
            if multi > 1:
                spread = 30
                for i in range(multi):
                    ang_offset = -spread/2 + (spread / (multi-1)) * i
                    p = Projetil(skill_nome, spawn_x, spawn_y, self.angulo_olhar + ang_offset, self)
                    self.buffer_projeteis.append(p)
            else:
                p = Projetil(skill_nome, spawn_x, spawn_y, self.angulo_olhar, self)
                self.buffer_projeteis.append(p)
        
        elif tipo == "AREA":
            # === ÁUDIO v10.0 - SOM DE SKILL DE CLASSE ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("AREA", skill_nome, self.pos[0], phase="cast")
            
            area = AreaEffect(skill_nome, self.pos[0], self.pos[1], self)
            self.buffer_areas.append(area)
        
        elif tipo == "DASH":
            # === ÁUDIO v10.0 - SOM DE SKILL DE CLASSE ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("DASH", skill_nome, self.pos[0], phase="cast")
            
            dist = data.get("distancia", 4.0)
            dano = data.get("dano", 0)
            
            self.pos[0] += math.cos(rad) * dist
            self.pos[1] += math.sin(rad) * dist
            
            for i in range(5):
                self.dash_trail.append((
                    self.pos[0] - math.cos(rad) * dist * (i/5),
                    self.pos[1] - math.sin(rad) * dist * (i/5),
                    1.0 - i*0.2
                ))
            
            if dano > 0:
                area = AreaEffect(skill_nome, self.pos[0], self.pos[1], self)
                area.dano = dano
                area.raio = 1.5
                self.buffer_areas.append(area)
            
            if data.get("invencivel"):
                self.invencivel_timer = 0.3
        
        elif tipo == "BUFF":
            # === ÁUDIO v10.0 - SOM DE SKILL DE CLASSE ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("BUFF", skill_nome, self.pos[0], phase="cast")
            
            if data.get("cura"):
                self.vida = min(self.vida_max, self.vida + data["cura"])
            
            buff = Buff(skill_nome, self)
            self.buffs_ativos.append(buff)
        
        elif tipo == "BEAM":
            # === ÁUDIO v10.0 - SOM DE SKILL DE CLASSE ===
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("BEAM", skill_nome, self.pos[0], phase="cast")
            
            alcance = data.get("alcance", 8.0)
            end_x = self.pos[0] + math.cos(rad) * alcance
            end_y = self.pos[1] + math.sin(rad) * alcance
            
            beam = Beam(skill_nome, self.pos[0], self.pos[1], end_x, end_y, self)
            self.buffer_beams.append(beam)
        
        # === NOVOS TIPOS v2.0 ===
        elif tipo == "SUMMON":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("SUMMON", skill_nome, self.pos[0], phase="cast")
            
            # Spawn na frente do caster
            summon_x = self.pos[0] + math.cos(rad) * 1.5
            summon_y = self.pos[1] + math.sin(rad) * 1.5
            
            summon = Summon(skill_nome, summon_x, summon_y, self)
            if not hasattr(self, 'buffer_summons'):
                self.buffer_summons = []
            self.buffer_summons.append(summon)
        
        elif tipo == "TRAP":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("TRAP", skill_nome, self.pos[0], phase="cast")
            
            # Spawn na frente do caster
            trap_x = self.pos[0] + math.cos(rad) * 2.0
            trap_y = self.pos[1] + math.sin(rad) * 2.0
            
            trap = Trap(skill_nome, trap_x, trap_y, self)
            if not hasattr(self, 'buffer_traps'):
                self.buffer_traps = []
            self.buffer_traps.append(trap)
        
        elif tipo == "TRANSFORM":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("TRANSFORM", skill_nome, self.pos[0], phase="cast")
            
            transform = Transform(skill_nome, self)
            if not hasattr(self, 'transformacao_ativa'):
                self.transformacao_ativa = None
            self.transformacao_ativa = transform
        
        elif tipo == "CHANNEL":
            audio = AudioManager.get_instance()
            if audio:
                audio.play_skill("CHANNEL", skill_nome, self.pos[0], phase="cast")
            
            channel = Channel(skill_nome, self)
            if not hasattr(self, 'channel_ativo'):
                self.channel_ativo = None
            self.channel_ativo = channel
        
        return True

    def update(self, dt, inimigo, todos_lutadores=None):
        """Atualiza estado do lutador.
        
        Args:
            dt: Delta time
            inimigo: Inimigo principal (nearest enemy) - compatível com 1v1
            todos_lutadores: Lista de TODOS os lutadores na arena (None = modo 1v1 legado)
        """
        from core.physics import normalizar_angulo
        
        if self.invencivel_timer > 0:
            self.invencivel_timer -= dt
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.stun_timer > 0:
            self.stun_timer -= dt
        # Track congelado timer separately from stun timer
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

        # BUG-C3: Decrementar timers de debuffs que antes nunca expiravam
        for attr in ['silenciado_timer', 'cego_timer', 'medo_timer', 'charme_timer', 'exposto_timer']:
            val = getattr(self, attr, 0)
            if val > 0:
                setattr(self, attr, val - dt)

        # FP-4: enraizado_timer decrementado separadamente para restaurar slow_fator ao expirar
        enraizado_val = getattr(self, 'enraizado_timer', 0)
        if enraizado_val > 0:
            self.enraizado_timer = enraizado_val - dt
            if self.enraizado_timer <= 0 and self.slow_fator == 0.0:
                self.slow_fator = 1.0  # Restaura velocidade ao sair do enraizamento

        # FP-2: Decrementar fraco_timer e restaurar dano_reduzido ao expirar
        if getattr(self, 'fraco_timer', 0) > 0:
            self.fraco_timer -= dt
            if self.fraco_timer <= 0:
                self.dano_reduzido = 1.0

        # FP-3: Decrementar vulnerabilidade_timer e restaurar ao expirar
        if getattr(self, 'vulnerabilidade_timer', 0) > 0:
            self.vulnerabilidade_timer -= dt
            if self.vulnerabilidade_timer <= 0:
                self.vulnerabilidade = 1.0

        # BUG-C2: Decrementar exausto_timer e restaurar regen_mana_base ao expirar
        if getattr(self, 'exausto_timer', 0) > 0:
            self.exausto_timer -= dt
            if self.exausto_timer <= 0:
                self.regen_mana_base = self.class_data.get("regen_mana", 3.0)

        # Decrementar tempo_parado e restaurar slow_fator ao expirar
        if getattr(self, 'tempo_parado', False) and self.stun_timer <= 0:
            self.tempo_parado = False
            if self.slow_fator == 0.0:
                self.slow_fator = 1.0

        # Decrementar bomba_relogio_timer e detonar ao expirar
        if getattr(self, 'bomba_relogio_timer', 0) > 0:
            self.bomba_relogio_timer -= dt
            if self.bomba_relogio_timer <= 0:
                dano_bomba = getattr(self, 'bomba_relogio_dano', 80.0)
                self.vida = max(0, self.vida - dano_bomba)
                self.flash_timer = 0.3
                self.flash_cor = (255, 100, 0)
                if self.vida <= 0:
                    self.morrer()

        # Reset em_vortex / sendo_puxado when stun expires
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
            mana_regen *= 0.3  # BUG-C2: penalidade temporária enquanto EXAUSTO estiver ativo
        if "Mago" in self.classe_nome:
            mana_regen *= 1.5
        self.mana = min(self.mana_max, self.mana + mana_regen * dt)
        
        if "Paladino" in self.classe_nome:
            self.vida = min(self.vida_max, self.vida + self.vida_max * 0.005 * dt)  # Reduzido de 2% para 0.5%
        
        # v13.0: Multi-fighter targeting - encontra inimigo mais próximo vivo
        if todos_lutadores is not None:
            inimigos_vivos = [
                f for f in todos_lutadores
                if f is not self and not f.morto and f.team_id != self.team_id
            ]
            if inimigos_vivos:
                inimigo = min(inimigos_vivos, key=lambda f: math.hypot(
                    f.pos[0] - self.pos[0], f.pos[1] - self.pos[1]))
            # Se não tem inimigos vivos, mantém o inimigo original (para physics etc)
        
        # BUG-FIX: se inimigo é None (todos mortos), skip IA e só aplica física
        if inimigo is None:
            self.aplicar_fisica(dt)
            return
        
        dx = inimigo.pos[0] - self.pos[0]
        dy = inimigo.pos[1] - self.pos[1]
        distancia = math.hypot(dx, dy)

        # M-N01: se brain calculou posição futura de intercepção, aponta para ela
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

        # v13.0: Verifica se há QUALQUER inimigo vivo (não só o principal)
        algum_inimigo_vivo = not inimigo.morto
        if todos_lutadores is not None:
            algum_inimigo_vivo = any(
                not f.morto for f in todos_lutadores
                if f is not self and f.team_id != self.team_id
            )

        if self.stun_timer <= 0 and algum_inimigo_vivo:
            # Só processa IA se tiver brain (não em modo manual)
            if self.brain is not None:
                self.brain.processar(dt, distancia, inimigo, todos_lutadores=todos_lutadores)
                self.executar_movimento(dt, distancia)
                self._atualizar_chain_state(dt, distancia)  # v5.0 chain mechanics
                self.executar_ataques(dt, distancia, inimigo)

        self.aplicar_fisica(dt)

    def _atualizar_buffs(self, dt):
        """Atualiza buffs ativos"""
        for buff in self.buffs_ativos[:]:
            buff.atualizar(dt)
            if not buff.ativo:
                self.buffs_ativos.remove(buff)
    
    def _atualizar_dots(self, dt):
        """Atualiza DoTs ativos"""
        for dot in self.dots_ativos[:]:
            dot.atualizar(dt)
            if not dot.ativo:
                self.dots_ativos.remove(dot)
        # Sincroniza status_effects com dots_ativos para brain.py / magic_system
        # Cria objetos leves com atributos esperados pelo brain
        # A05: usa StatusSnapshot em vez de type() anônimo — mais rápido e tipado
        self.status_effects = [
            StatusSnapshot(nome=dot.tipo, dano_por_tick=dot.dano_por_tick)
            for dot in self.dots_ativos
        ]
        # Adiciona CCs ativos (stun, slow, congelado)
        if self.stun_timer > 0:
            self.status_effects.append(StatusSnapshot(
                nome='congelado' if getattr(self, 'congelado', False) else 'atordoado',
                mod_velocidade=0.0, pode_mover=False, pode_atacar=False,
            ))
        elif self.slow_timer > 0:
            self.status_effects.append(StatusSnapshot(
                nome='lento',
                mod_velocidade=self.slow_fator,
            ))

        # D02: sincroniza cc_effects com os CCs de controle de grupo ativos
        # (float timers continuam sendo a fonte de verdade; cc_effects é observável)
        cc = []
        if self.stun_timer > 0:
            cc.append(StatusSnapshot(
                nome='congelado' if getattr(self, 'congelado', False) else 'atordoado',
                mod_velocidade=0.0, pode_mover=False, pode_atacar=False,
            ))
        elif self.slow_timer > 0:
            cc.append(StatusSnapshot(nome='lento', mod_velocidade=self.slow_fator))
        if getattr(self, 'enraizado_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='enraizado', mod_velocidade=0.0, pode_mover=False))
        if getattr(self, 'silenciado_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='silenciado', pode_usar_skill=False))
        if getattr(self, 'cego_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='cego'))
        if getattr(self, 'medo_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='medo'))
        self.cc_effects = cc
    
    def _atualizar_dash_trail(self, dt):
        """Fade do trail de dash"""
        for i, (x, y, alpha) in enumerate(self.dash_trail):
            self.dash_trail[i] = (x, y, alpha - dt * 3)
        self.dash_trail = [(x, y, a) for x, y, a in self.dash_trail if a > 0]

    def _atualizar_orbes(self, dt):
        """Atualiza orbes mágicos e remove os inativos"""
        for orbe in self.buffer_orbes:
            orbe.atualizar(dt)
        self.buffer_orbes = [o for o in self.buffer_orbes if o.ativo]

    def aplicar_fisica(self, dt):
        """Aplica física de movimento"""
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
        """Executa movimento baseado na ação da IA - v8.0 com comportamento humano"""
        acao = self.brain.acao_atual
        acc = 45.0 * self.mod_velocidade
        if self.modo_adrenalina:
            acc = 70.0 * self.mod_velocidade
        
        for buff in self.buffs_ativos:
            acc *= buff.buff_velocidade
        
        # v8.0: Aplica variação humana na aceleração
        if hasattr(self.brain, 'ritmo_combate'):
            acc *= self.brain.ritmo_combate
        
        # v8.0: Momentum afeta velocidade
        if hasattr(self.brain, 'momentum'):
            if self.brain.momentum > 0.3:
                acc *= 1.0 + self.brain.momentum * 0.15
            elif self.brain.momentum < -0.3:
                acc *= 1.0 + self.brain.momentum * 0.1  # Diminui menos quando perdendo
        
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
            
            # v8.0: Micro-ajustes durante ataques para parecer mais humano
            if hasattr(self.brain, 'micro_ajustes'):
                mx += random.uniform(-0.05, 0.05)
                my += random.uniform(-0.05, 0.05)
            
        elif acao == "COMBATE":
            mx = math.cos(rad) * 0.6
            my = math.sin(rad) * 0.6
            # v8.0: Mais variação no combate
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
            # v8.0: Desvio diagonal ao fugir para parecer mais esperto
            if random.random() < 0.3:
                lateral = random.choice([-1, 1]) * self.brain.dir_circular
                rad_lat = math.radians(self.angulo_olhar + (30 * lateral))
                mx += math.cos(rad_lat) * 0.3
                my += math.sin(rad_lat) * 0.3
        
        elif acao == "DESVIO":
            # v8.0: Nova ação de desvio mais dinâmica
            rad_lat = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
            mx = math.cos(rad_lat) * 1.2
            my = math.sin(rad_lat) * 1.2
            # Adiciona um pouco de recuo
            mx -= math.cos(rad) * 0.3
            my -= math.sin(rad) * 0.3
                
        elif acao == "CIRCULAR":
            rad_lat = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
            # v8.1: Variação na velocidade lateral para parecer footwork, não orbita
            circ_mult = random.uniform(0.6, 0.95)
            mx = math.cos(rad_lat) * circ_mult
            my = math.sin(rad_lat) * circ_mult
            # v8.1: Pausas micro — às vezes desacelera no meio do strafe
            if random.random() < 0.12:
                mx *= 0.3
                my *= 0.3
            # Ajuste de distância enquanto circula
            if distancia < 2.5:
                mx -= math.cos(rad) * 0.35  # Afasta mais agressivamente
                my -= math.sin(rad) * 0.35
            elif distancia > 4.0:
                mx += math.cos(rad) * 0.2  # Aproxima um pouco
                my += math.sin(rad) * 0.2
            # v8.1: Na faixa ideal, pequeno approach aleatório em vez de constante
            elif random.random() < 0.4:
                mx += math.cos(rad) * 0.15
                my += math.sin(rad) * 0.15
            
        elif acao == "FLANQUEAR":
            # v8.0: Flanqueio mais dinâmico
            angulo_flank = 50 + random.uniform(-10, 10)  # Variação humana
            rad_f = math.radians(self.angulo_olhar + (angulo_flank * self.brain.dir_circular))
            mx = math.cos(rad_f)
            my = math.sin(rad_f)
            
        elif acao == "APROXIMAR_LENTO":
            mx = math.cos(rad) * 0.55
            my = math.sin(rad) * 0.55
            # v8.0: Pequenos movimentos laterais ao aproximar
            if random.random() < 0.2:
                rad_lat = math.radians(self.angulo_olhar + (90 * random.choice([-1, 1])))
                mx += math.cos(rad_lat) * 0.15
                my += math.sin(rad_lat) * 0.15
            
        elif acao == "POKE":
            # v8.0: Poke mais inteligente
            if random.random() < 0.6:
                mx = math.cos(rad) * 0.8
                my = math.sin(rad) * 0.8
            else:
                # Recua depois do poke
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
        
        # v8.0: Nova ação - pressionar continuamente
        elif acao == "PRESSIONAR_CONTINUO":
            mx = math.cos(rad) * 1.1
            my = math.sin(rad) * 1.1
            # Pequenos ajustes laterais
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
        
        # v8.0: Pulo ofensivo mais inteligente
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

        # MEL-10 fix: estado "NEUTRO" não tinha handler em executar_movimento —
        # mx e my ficavam em 0,0, paralisando o personagem por até 0.5s no início
        # do combate. Agora, se nenhum elif matchou (ação desconhecida ou NEUTRO),
        # aplica uma aproximação leve para que o personagem nunca fique completamente
        # imóvel durante o primeiro timer_decisao.
        if mx == 0 and my == 0 and acao != "BLOQUEAR":
            # Ação não reconhecida — aproxima levemente para evitar paralisia
            mx = math.cos(rad) * 0.3
            my = math.sin(rad) * 0.3

        self.vel[0] += mx * acc * dt
        self.vel[1] += my * acc * dt

    def executar_ataques(self, dt, distancia, inimigo):
        """Executa ataques físicos com sistema de animação aprimorado v15.0"""
        from core.combat import ArmaProjetil, FlechaProjetil, OrbeMagico
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES
        
        self.cooldown_ataque -= dt
        
        arma_tipo = self.dados.arma_obj.tipo if self.dados.arma_obj else "Reta"
        arma_estilo = getattr(self.dados.arma_obj, 'estilo', '') if self.dados.arma_obj else ''
        is_orbital = self.dados.arma_obj and "Orbital" in arma_tipo
        
        # === v5.0: CORRENTE usa sistema dedicado ===
        if arma_tipo == "Corrente":
            self._executar_ataques_corrente(dt, distancia, inimigo, arma_estilo)
            return
        
        # === v15.0: DUPLA usa sistema dedicado ===
        if arma_tipo == "Dupla":
            self._executar_ataques_dupla(dt, distancia, inimigo, arma_estilo)
            return
        
        # === v15.0: RETA usa sistema dedicado ===
        if arma_tipo == "Reta":
            self._executar_ataques_reta(dt, distancia, inimigo, arma_estilo)
            return
        
        # === v15.0: ORBITAL usa sistema dedicado ===
        if is_orbital:
            self._executar_ataques_orbital(dt, distancia, inimigo, arma_estilo)
            return
        
        # === v15.0: TRANSFORMÁVEL usa sistema dedicado ===
        if arma_tipo in ("Transformável", "Transformavel"):
            self._executar_ataques_transformavel(dt, distancia, inimigo, arma_estilo)
            return
        
        # Obtém gerenciador de animações
        anim_manager = get_weapon_animation_manager()
        
        # Calcula posição da ponta da arma para trail
        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 2.5
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )
        
        # Atualiza animação
        transform = anim_manager.get_weapon_transform(
            id(self), arma_tipo, self.angulo_olhar, weapon_tip, dt, weapon_style=arma_estilo
        )
        
        # Aplica transformações
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]
        
        # Animação de ataque (Arco, Arremesso, Mágica)
        if self.atacando:
            self.timer_animacao -= dt
            
            profile = WEAPON_PROFILES.get(arma_tipo, WEAPON_PROFILES["Reta"])
            
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        else:
            self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        if not self.atacando and self.cooldown_ataque <= 0:
            acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
            deve_atacar = False
            
            # Calcula alcance de ataque usando mesmo método que brain.py
            try:
                from core.hitbox import HITBOX_PROFILES
                from utils.config import PPM
                profile_hitbox = HITBOX_PROFILES.get(arma_tipo, HITBOX_PROFILES.get("Reta", {}))
                range_mult = profile_hitbox.get("range_mult", 2.0)
                alcance_base = self.raio_fisico * range_mult
                
                # Adiciona componente da arma como brain.py faz
                arma = self.dados.arma_obj if self.dados else None
                # Alcance = raio × range_mult (geometria removida)
                alcance_ataque = alcance_base
                
                # CRIT-04 fix: margem unificada com brain_combat._calcular_alcance_efetivo()
                # Antes: 1.3× (30%) aqui vs 1.1× (10%) no brain → IA decidia fora de alcance
                # mas entities atacava, ou IA decidia atacar e entities não executava.
                # Agora ambos usam a mesma margem de 1.1×.
                alcance_ataque *= 1.1
            except Exception:
                alcance_ataque = self.raio_fisico * 3.0  # Fallback generoso
            
            # Ajustes APENAS para armas ranged (não sobrescreve corpo-a-corpo!)
            if arma_tipo == "Arco":
                alcance_ataque = 14.0
            elif arma_tipo == "Arremesso":
                alcance_ataque = 10.0
            elif arma_tipo == "Mágica":
                alcance_ataque = 7.0
            # Para armas corpo-a-corpo (incluindo Dupla), usa o cálculo baseado no profile
            
            # Verifica se deve atacar
            if self.brain.acao_atual in acoes_ofensivas and distancia < alcance_ataque:
                deve_atacar = True
            if self.brain.acao_atual == "POKE" and abs(distancia - self.alcance_ideal) < 1.5:
                deve_atacar = True
            if self.modo_ataque_aereo and distancia < 2.0:
                deve_atacar = True
            
            # === ARMAS RANGED: atacam mesmo recuando/fugindo! ===
            if arma_tipo in ["Arremesso", "Arco"] and distancia < alcance_ataque:
                # Arqueiros atiram mesmo fugindo (desde que não esteja em cooldown)
                if self.brain.acao_atual in ["RECUAR", "FUGIR", "APROXIMAR"]:
                    if random.random() < 0.25:
                        deve_atacar = True

            if deve_atacar and abs(self.z - inimigo.z) < 1.5:
                self.atacando = True
                
                # === v10.1: Novo ataque = novo ID, limpa alvos atingidos ===
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                
                # Usa duração do perfil da arma
                profile = WEAPON_PROFILES.get(arma_tipo, WEAPON_PROFILES["Reta"])
                self.timer_animacao = profile.total_time
                
                # Inicia animação no gerenciador
                anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=arma_estilo)
                
                if arma_tipo == "Arremesso":
                    self._disparar_arremesso(inimigo)
                elif arma_tipo == "Arco":
                    self._disparar_flecha(inimigo)
                elif arma_tipo == "Mágica":
                    self._disparar_orbes(inimigo)
                
                base_cd = 0.5 + random.random() * 0.5
                if arma_tipo == "Arremesso":
                    # v15.0: volleys consecutivas ficam mais rápidas
                    self.throw_consecutive += 1
                    base_cd = max(0.55, 1.05 - self.throw_consecutive * 0.04) + random.random() * 0.35
                    if self.throw_consecutive >= 5:
                        self.throw_consecutive = 0  # Reset após volley longa
                elif arma_tipo == "Arco":
                    # v15.0: tiros consecutivos mantêm ritmo, charge bonus
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
                # BUG-06 fix: velocidade_ataque da arma reduz o cooldown
                vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
                self.cooldown_ataque = base_cd / vel_ataque

    # =====================================================================
    # === SISTEMA DE CORRENTE v5.0 — Mecânicas únicas por estilo ========
    # =====================================================================

    def _atualizar_chain_state(self, dt, distancia):
        """Atualiza estados persistentes de TODAS as mecânicas de arma v15.0."""
        arma = self.dados.arma_obj
        if not arma:
            return

        tipo = arma.tipo
        estilo = getattr(arma, 'estilo', '')

        # ═══ CORRENTE ═══
        if tipo == "Corrente":
            if "Mangual" in estilo or "Flail" in estilo:
                self.chain_momentum = max(0, self.chain_momentum - dt * 0.15)
            elif estilo == "Kusarigama":
                if self.chain_combo_timer > 0:
                    self.chain_combo_timer -= dt
                    if self.chain_combo_timer <= 0:
                        self.chain_combo = 0
                        self.chain_mode = 0
            elif estilo == "Chicote":
                if self.chain_whip_stacks > 0 and not self.atacando:
                    self.chain_whip_stacks = max(0, self.chain_whip_stacks - dt * 2.0)
            elif estilo == "Meteor Hammer":
                if self.chain_spinning:
                    self.chain_spin_speed = min(3.0, self.chain_spin_speed + dt * 0.8)
                    self.chain_spin_dmg_timer -= dt
                else:
                    self.chain_spin_speed = max(0, self.chain_spin_speed - dt * 1.5)
            elif "Corrente com Peso" in estilo:
                if self.chain_pull_timer > 0:
                    self.chain_pull_timer -= dt
                    if self.chain_pull_timer <= 0:
                        self.chain_pull_target = None

        # ═══ DUPLA: combo decai sem hits ═══
        elif tipo == "Dupla":
            if self.dual_combo_timer > 0:
                self.dual_combo_timer -= dt
                if self.dual_combo_timer <= 0:
                    self.dual_combo = max(0, self.dual_combo - 1)
                    if self.dual_combo > 0:
                        self.dual_combo_timer = 2.0
                    else:
                        self.dual_frenzy = False
                        self.dual_cross_slash = False
            self.dual_frenzy = self.dual_combo >= 4
            self.dual_cross_slash = self.dual_combo >= 6

        # ═══ RETA: combo decai, charge timer, parry window ═══
        elif tipo == "Reta":
            if self.reta_combo_timer > 0:
                self.reta_combo_timer -= dt
                if self.reta_combo_timer <= 0:
                    self.reta_combo = 0
            if self.reta_parry_window > 0:
                self.reta_parry_window -= dt
            if self.reta_heavy_charging:
                self.reta_charge_timer += dt
                if self.reta_charge_timer > 1.5:
                    self.reta_charge_timer = 1.5  # Max charge

        # ═══ ORBITAL: rota atualiza sempre, cooldowns decaem ═══
        elif "Orbital" in tipo:
            combat_speed = 1.0
            if self.brain.acao_atual in ["MATAR", "BLOQUEAR", "COMBATE"] or distancia < 2.5:
                combat_speed = 3.0
            self.orbital_angle += self.orbital_speed * combat_speed * dt
            self.orbital_dmg_timer -= dt
            if self.orbital_burst_cd > 0:
                self.orbital_burst_cd -= dt
            # Ativa escudo quando em modo defensivo
            self.orbital_shield_active = self.brain.acao_atual in ["BLOQUEAR", "RECUAR", "FUGIR"]

        # ═══ TRANSFORMÁVEL: cooldowns, bônus pós-troca ═══
        elif "Transformável" in tipo or "Transformavel" in tipo:
            if self.transform_cd > 0:
                self.transform_cd -= dt
            if self.transform_bonus_timer > 0:
                self.transform_bonus_timer -= dt

        # ═══ ARCO: carga ═══
        elif tipo == "Arco":
            if self.bow_perfect_timer > 0:
                self.bow_perfect_timer -= dt

        # ═══ ARREMESSO: cooldowns ═══
        elif tipo == "Arremesso":
            if self.throw_volley_cd > 0:
                self.throw_volley_cd -= dt

    def _executar_ataques_corrente(self, dt, distancia, inimigo, estilo):
        """
        Sistema de ataque dedicado para armas CORRENTE v5.0.
        Cada estilo tem mecânica, timings e efeitos completamente diferentes.
        
        Mangual:       Golpes gravitacionais com momentum crescente
        Kusarigama:    Alterna foice rápida (perto) e peso lento (longe)
        Chicote:       Ataques rápidos, crack no sweet spot, interrupção
        Meteor Hammer: Spin contínuo 360° com dano em área crescente
        Corrente+Peso: Golpes lentos que slow + pull o inimigo
        """
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES

        anim_manager = get_weapon_animation_manager()

        # Resolução de profile: STYLE_PROFILES tem per-style timings (Mangual, Chicote, etc.)
        arma_tipo = "Corrente"
        # v5.0 fix: busca primeiro em STYLE_PROFILES (per-style), depois WEAPON_PROFILES (per-type)
        if estilo in STYLE_PROFILES:
            profile_key = estilo
            _profile_dict = STYLE_PROFILES
        elif estilo in WEAPON_PROFILES:
            profile_key = estilo
            _profile_dict = WEAPON_PROFILES
        else:
            profile_key = arma_tipo
            _profile_dict = WEAPON_PROFILES

        # Calcula posição ponta da arma para trail
        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 3.5  # Correntes são mais longas
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )

        # Atualiza animação — v5.0: passa estilo para per-style animations
        transform = anim_manager.get_weapon_transform(
            id(self), arma_tipo, self.angulo_olhar, weapon_tip, dt, weapon_style=estilo
        )
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        # ── METEOR HAMMER: modo spin contínuo ──
        if estilo == "Meteor Hammer" and self.chain_spinning:
            # Enquanto girando, arma visual gira continuamente
            self.angulo_arma_visual += self.chain_spin_speed * 360 * dt
            # Timer de dano contínuo (não usa cooldown normal)
            if self.chain_spin_dmg_timer <= 0:
                self.chain_spin_dmg_timer = max(0.2, 0.6 - self.chain_spin_speed * 0.12)
                # Marca como atacando por um breve momento para hitbox detectar
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                profile = _profile_dict.get(profile_key, WEAPON_PROFILES["Corrente"])
                self.timer_animacao = 0.15  # Mini-ataque contínuo
                anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
            elif self.timer_animacao > 0:
                self.timer_animacao -= dt
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
                if self.timer_animacao <= 0:
                    self.atacando = False

            # Sai do spin se recuar/fugir ou perder a ação
            acoes_spin = ["MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR", "CIRCULAR"]
            if self.brain.acao_atual not in acoes_spin or distancia > 6.0:
                self.chain_spinning = False
                self.atacando = False
                self.cooldown_ataque = 0.8  # Penalidade ao parar de girar
            return

        # ── Processo normal de ataque (não-spin) ──
        if self.atacando:
            self.timer_animacao -= dt
            profile = _profile_dict.get(profile_key, WEAPON_PROFILES["Corrente"])
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
                # Mangual: recovery penalty se não acertou (momentum perde)
                if ("Mangual" in estilo or "Flail" in estilo):
                    self.chain_recovery_mult = max(0.7, 1.0 - self.chain_momentum * 0.3)
            else:
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        else:
            self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        # ── Decisão de atacar ──
        if self.atacando or self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        # ── Alcance por estilo ──
        alcance = self._calcular_alcance_corrente(estilo)

        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        # ══════════════════════════════════════════════════════════════
        # PER-STYLE ATTACK LOGIC
        # ══════════════════════════════════════════════════════════════

        profile = _profile_dict.get(profile_key, WEAPON_PROFILES["Corrente"])

        if "Mangual" in estilo or "Flail" in estilo:
            # ── MANGUAL: Golpes gravitacionais com momentum ──
            # Mais momentum = menos wind-up, mais dano
            momentum_bonus = self.chain_momentum * 0.4  # Até 40% mais rápido
            anim_time = profile.total_time * (1.0 - momentum_bonus)
            self.timer_animacao = max(0.3, anim_time)
            # Cooldown AUMENTA com base no peso (arma pesada = lenta)
            peso = getattr(self.dados.arma_obj, 'peso', 8.0)
            base_cd = 1.2 + (peso / 10.0) * 0.5 - self.chain_momentum * 0.4
            self.chain_recovery_mult = 1.0

        elif estilo == "Kusarigama":
            # ── KUSARIGAMA: Dual-mode (foice perto / peso longe) ──
            # Auto-seleciona modo baseado na distância
            alcance_foice = self.raio_fisico * 2.5
            if distancia < alcance_foice:
                self.chain_mode = 0  # Foice: rápido, curto
                anim_time = profile.total_time * 0.6  # 40% mais rápido
                base_cd = 0.35 + random.random() * 0.2
            else:
                self.chain_mode = 1  # Peso: lento, longo
                anim_time = profile.total_time * 1.2
                base_cd = 0.7 + random.random() * 0.3
            self.timer_animacao = anim_time
            # Combo: ataques rápidos incrementam
            self.chain_combo += 1
            self.chain_combo_timer = 2.5  # Reset em 2.5s sem atacar

        elif estilo == "Chicote":
            # ── CHICOTE: Ataques rápidos com crack no sweet spot ──
            # Velocidade aumenta com stacks (cada hit acumula)
            speed_mult = 1.0 + min(self.chain_whip_stacks, 5) * 0.12
            anim_time = profile.total_time / speed_mult
            self.timer_animacao = max(0.15, anim_time)
            # Crack: se inimigo está na faixa de sweet spot (70-100% do alcance)
            faixa_min = alcance * 0.65
            self.chain_whip_crack = distancia >= faixa_min
            base_cd = max(0.2, 0.4 / speed_mult)
            self.chain_whip_stacks = min(6, self.chain_whip_stacks + 1)

        elif estilo == "Meteor Hammer":
            # ── METEOR HAMMER: Inicia spin ou golpe único ──
            if self.brain.acao_atual in ["MATAR", "PRESSIONAR", "COMBATE"] and distancia < 5.0:
                # Inicia modo spin contínuo!
                self.chain_spinning = True
                self.chain_spin_speed = 0.5
                self.chain_spin_dmg_timer = 0.3
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.15
                anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)
                return  # Spin mode takes over
            else:
                # Golpe único (lançamento)
                anim_time = profile.total_time
                self.timer_animacao = anim_time
                base_cd = 0.9 + random.random() * 0.4

        elif "Corrente com Peso" in estilo:
            # ── CORRENTE COM PESO: Golpes lentos que slow + pull ──
            anim_time = profile.total_time * 1.1  # Ligeiramente mais lento
            self.timer_animacao = anim_time
            base_cd = 1.0 + random.random() * 0.4
            # Pull setup: marca alvo para ser puxado no hit
            self.chain_pull_target = inimigo
            self.chain_pull_timer = 0.8  # 0.8s de pull window

        else:
            # Fallback genérico para estilos desconhecidos
            self.timer_animacao = profile.total_time
            base_cd = 0.6 + random.random() * 0.4

        # ── Inicia ataque ──
        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()
        anim_manager.start_attack(id(self), arma_tipo, tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

        # ── Cooldown final ──
        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd * self.chain_recovery_mult / vel_ataque

    def _calcular_alcance_corrente(self, estilo):
        """Retorna o alcance de ataque para cada estilo de corrente."""
        base = self.raio_fisico
        if "Mangual" in estilo or "Flail" in estilo:
            return base * 4.0    # Mangual: alcance médio-longo
        elif estilo == "Kusarigama":
            # Kusarigama: usa alcance máximo (peso) para decisão de iniciar ataque
            # O modo (foice vs peso) é decidido DENTRO do ataque, não aqui
            return base * 5.5    # Sempre usa alcance do modo peso para check
        elif estilo == "Chicote":
            return base * 6.0    # Chicote: maior alcance melee do jogo
        elif estilo == "Meteor Hammer":
            return base * 5.0    # Meteor: longo
        elif "Corrente com Peso" in estilo:
            return base * 3.5    # Peso: médio (compensa com pull)
        return base * 4.0        # Fallback

    # =====================================================================
    # === SISTEMA DUPLA v15.0 — Combo, Frenzy, Cross-Slash ===============
    # =====================================================================

    def _executar_ataques_dupla(self, dt, distancia, inimigo, estilo):
        """
        Sistema de ataque dedicado para armas DUPLA v15.0.
        Alterna mão esquerda/direita, combo counter com frenzy e cross-slash.
        
        Kamas:          Cortes alternados rápidos, frenzy reduz recovery
        Adagas Gêmeas:  Ultra-rápidas, cross-slash simultâneo em combo 6+
        Sai:            Parry integrado, contra-atacar após bloquear
        Garras:         Aumenta dano por stack, sangramento em combo 4+
        Tonfas:         Hits combinam contusão + velocidade, stun em combo alto
        Facas Táticas:  Ataques precisos, crit bonus em combo 3+
        """
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES

        anim_manager = get_weapon_animation_manager()

        # Resolução de profile
        if estilo in STYLE_PROFILES:
            profile = STYLE_PROFILES[estilo]
        elif estilo in WEAPON_PROFILES:
            profile = WEAPON_PROFILES[estilo]
        else:
            profile = WEAPON_PROFILES.get("Dupla", WEAPON_PROFILES["Reta"])

        # Calcula posição ponta
        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 2.0
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )

        transform = anim_manager.get_weapon_transform(
            id(self), "Dupla", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo
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
            return

        self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        if self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        # Alcance
        alcance = self.raio_fisico * 2.8
        if estilo == "Garras":
            alcance = self.raio_fisico * 2.2  # Garras: mais curto
        elif estilo in ("Kamas", "Sai"):
            alcance = self.raio_fisico * 3.0

        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        # ── Inicia ataque ──
        # Frenzy mode: recovery ultra-rápida
        frenzy_mult = 0.5 if self.dual_frenzy else 1.0
        # Cross-slash: ambas adagas = animação dupla
        if self.dual_cross_slash:
            anim_time = profile.total_time * 0.7  # Mais rápido
        else:
            anim_time = profile.total_time * frenzy_mult

        self.timer_animacao = max(0.06, anim_time)
        self.atacando = True
        self.ataque_id += 1
        self.alvos_atingidos_neste_ataque.clear()

        # Alterna mão (visual)
        self.dual_hand = 1 - self.dual_hand

        anim_manager.start_attack(id(self), "Dupla", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

        # ── Combo tracking ──
        self.dual_combo = min(8, self.dual_combo + 1)
        self.dual_combo_timer = 2.0  # 2s sem atacar = combo cai

        # ── Cooldown por estilo ──
        if estilo == "Adagas Gêmeas":
            base_cd = max(0.08, 0.15 * frenzy_mult)
        elif estilo == "Garras":
            base_cd = max(0.10, 0.22 * frenzy_mult)
        elif estilo == "Kamas":
            base_cd = max(0.10, 0.20 * frenzy_mult)
        elif estilo == "Sai":
            base_cd = max(0.12, 0.28 * frenzy_mult)
        elif estilo == "Tonfas":
            base_cd = max(0.12, 0.25 * frenzy_mult)
        elif estilo == "Facas Táticas":
            base_cd = max(0.09, 0.18 * frenzy_mult)
        else:
            base_cd = max(0.10, 0.20 * frenzy_mult)

        vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
        self.cooldown_ataque = base_cd / vel_ataque

    # =====================================================================
    # === SISTEMA RETA v15.0 — Stance, Combo, Heavy Charge ===============
    # =====================================================================

    def _executar_ataques_reta(self, dt, distancia, inimigo, estilo):
        """
        Sistema de ataque dedicado para armas RETA v15.0.
        Combos variados por estilo, golpe pesado carregável, parry.
        
        Corte (Espada):  Combo 3-hit (horizontal, diagonal, vertical)
        Estocada (Lança): Thrusts rápidos, alcance longo, combo poke
        Contusão (Maça):  Golpes lentos com stun chance, carga devastadora
        Katana:           Iaido (saque rápido), combo alternado
        Montante:         Golpes largos com cleave, lentos e poderosos
        Martelo:          Smash com AoE no ground pound
        """
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES

        anim_manager = get_weapon_animation_manager()

        # Resolução de profile
        if estilo in STYLE_PROFILES:
            profile = STYLE_PROFILES[estilo]
        elif estilo in WEAPON_PROFILES:
            profile = WEAPON_PROFILES[estilo]
        else:
            profile = WEAPON_PROFILES.get("Reta", WEAPON_PROFILES["Reta"])

        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 2.5
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )

        transform = anim_manager.get_weapon_transform(
            id(self), "Reta", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo
        )
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

        # ── Alcance por estilo ──
        is_thrust = estilo in ("Estocada (Lança)", "Lança", "Alabarda")
        is_heavy = estilo in ("Contusão (Maça)", "Maça", "Martelo", "Montante", "Claymore")

        if is_thrust:
            alcance = self.raio_fisico * 3.5  # Lanças: alcance longo
        elif is_heavy:
            alcance = self.raio_fisico * 2.8  # Pesadas: médio
        else:
            alcance = self.raio_fisico * 2.5  # Espadas: padrão

        if distancia > alcance or abs(self.z - inimigo.z) > 1.5:
            return

        # ── Combo counter ──
        self.reta_combo = (self.reta_combo + 1) % 3  # Ciclo de 3 golpes
        self.reta_combo_timer = 2.5

        # ── Timing por estilo e combo ──
        combo_speed_bonus = 1.0
        if self.reta_combo == 1:
            combo_speed_bonus = 0.85  # 2º golpe mais rápido
        elif self.reta_combo == 2:
            combo_speed_bonus = 1.2  # 3º golpe mais lento (finisher)

        if is_heavy:
            # Pesadas: mais lentas mas shake/dano maiores
            anim_time = profile.total_time * combo_speed_bonus * 1.1
            base_cd = 0.6 + random.random() * 0.3
        elif is_thrust:
            # Estocadas: rápidas, quase sem recovery
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

    # =====================================================================
    # === SISTEMA ORBITAL v15.0 — Dano automático + burst + escudo ======
    # =====================================================================

    def _executar_ataques_orbital(self, dt, distancia, inimigo, estilo):
        """
        Sistema de ataque dedicado para armas ORBITAL v15.0.
        Orbitais giram ao redor do dono e causam dano por contato automático.
        
        Defensivo (Escudo):    Bloqueia projéteis, reflete 30% dano
        Ofensivo (Drone):      Dispara projéteis automáticos
        Mágico (Orbe):         Gera campo de dano em área
        Lâminas Orbitais:      Dano contínuo corpo-a-corpo em quem se aproxima
        """
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES

        anim_manager = get_weapon_animation_manager()

        # Orbital sempre gira (visual)
        self.angulo_arma_visual = self.orbital_angle

        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 1.5
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )

        transform = anim_manager.get_weapon_transform(
            id(self), "Orbital", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo
        )
        self.weapon_anim_scale = transform["scale"]
        self.weapon_anim_shake = transform["shake"]
        self.weapon_trail_positions = transform["trail_positions"]

        arma = self.dados.arma_obj
        if not arma:
            return

        # Alcance orbital = raio de órbita
        qtd_orbitais = max(1, int(getattr(arma, 'quantidade_orbitais', 1)))
        raio_orbita = self.raio_fisico * 1.5

        # ── DANO AUTOMÁTICO POR PROXIMIDADE ──
        # Orbitais danificam inimigos que entram no raio de órbita
        if self.orbital_dmg_timer <= 0 and not inimigo.morto:
            # Verifica se inimigo está dentro do alcance orbital
            alcance_orbital = raio_orbita + self.raio_fisico * 0.5
            if distancia < alcance_orbital and abs(self.z - inimigo.z) < 1.5:
                # Dano automático!
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.15

                anim_manager.start_attack(id(self), "Orbital", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

                # Timer entre hits automáticos (varia por estilo)
                if "Lâminas" in estilo or "Laminas" in estilo:
                    self.orbital_dmg_timer = 0.3  # Rápido, dano por tick
                elif "Drone" in estilo or "Ofensivo" in estilo:
                    self.orbital_dmg_timer = 0.8  # Dispara projéteis
                elif "Escudo" in estilo or "Defensivo" in estilo:
                    self.orbital_dmg_timer = 1.2  # Lento mas reflete
                else:
                    self.orbital_dmg_timer = 0.5  # Padrão

        # ── BURST OFENSIVO: ataque especial em cooldown ──
        if self.orbital_burst_cd <= 0 and not inimigo.morto:
            acoes = ["MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR"]
            if self.brain.acao_atual in acoes and distancia < raio_orbita * 3:
                # Burst: todos os orbitais disparam no inimigo
                self.orbital_burst_cd = 5.0  # 5s cooldown
                self.atacando = True
                self.ataque_id += 1
                self.alvos_atingidos_neste_ataque.clear()
                self.timer_animacao = 0.3

                # Cria projéteis de burst (um por orbital)
                from core.combat import ArmaProjetil
                dano_total = arma.dano * (self.dados.forca / 2.0 + 0.5)
                cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (120, 180, 255)

                for i in range(qtd_orbitais):
                    ang_orbital = self.orbital_angle + (360 / qtd_orbitais) * i
                    rad_o = math.radians(ang_orbital)
                    spawn_x = self.pos[0] + math.cos(rad_o) * raio_orbita
                    spawn_y = self.pos[1] + math.sin(rad_o) * raio_orbita

                    ang_para_alvo = math.degrees(math.atan2(
                        inimigo.pos[1] - spawn_y, inimigo.pos[0] - spawn_x
                    ))

                    proj = ArmaProjetil(
                        tipo="orbe",
                        x=spawn_x, y=spawn_y,
                        angulo=ang_para_alvo,
                        dono=self,
                        dano=dano_total / qtd_orbitais,
                        velocidade=14.0,
                        tamanho=0.25,
                        cor=cor
                    )
                    self.buffer_projeteis.append(proj)

                anim_manager.start_attack(id(self), "Orbital", tuple(self.pos), self.angulo_olhar, weapon_style=estilo)

        # Atualiza animação de ataque em progresso
        if self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False

    # =====================================================================
    # === SISTEMA TRANSFORMÁVEL v15.0 — Troca de forma dinâmica =========
    # =====================================================================

    def _executar_ataques_transformavel(self, dt, distancia, inimigo, estilo):
        """
        Sistema de ataque dedicado para armas TRANSFORMÁVEL v15.0.
        Troca entre duas formas com mecânicas distintas.
        
        Espada↔Lança:       Forma 0 = espada rápida (curto), Forma 1 = lança (longo)
        Compacta↔Estendida:  Forma 0 = rápido (curto), Forma 1 = lento (longo)
        Chicote↔Espada:      Forma 0 = chicote (longo, area), Forma 1 = espada (curto)
        Arco↔Lâminas:       Forma 0 = ranged (arco), Forma 1 = melee (lâminas)
        """
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES, STYLE_PROFILES

        anim_manager = get_weapon_animation_manager()
        profile = WEAPON_PROFILES.get("Transformavel", WEAPON_PROFILES["Reta"])

        rad = math.radians(self.angulo_olhar)
        tip_dist = self.raio_fisico * 2.5
        weapon_tip = (
            self.pos[0] + math.cos(rad) * tip_dist,
            self.pos[1] + math.sin(rad) * tip_dist
        )

        transform = anim_manager.get_weapon_transform(
            id(self), "Transformável", self.angulo_olhar, weapon_tip, dt, weapon_style=estilo
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
            return

        self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        # ── Auto-troca de forma baseada em distância ──
        if self.transform_cd <= 0:
            # Forma 0 = curto alcance/rápido, Forma 1 = longo alcance/lento
            should_switch = False
            if self.transform_forma == 0 and distancia > self.raio_fisico * 4.0:
                should_switch = True   # Longe demais, troca pra forma longa
            elif self.transform_forma == 1 and distancia < self.raio_fisico * 2.0:
                should_switch = True   # Perto demais, troca pra forma curta

            if should_switch:
                self.transform_forma = 1 - self.transform_forma
                self.transform_cd = 3.0  # 3s entre trocas
                self.transform_combo = 0
                self.transform_bonus_timer = 1.5  # 1.5s de bônus pós-troca

        if self.cooldown_ataque > 0:
            return

        acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO",
                           "FLANQUEAR", "POKE", "PRESSIONAR", "CONTRA_ATAQUE"]
        if self.brain.acao_atual not in acoes_ofensivas:
            return

        # Alcance baseado na forma atual
        if self.transform_forma == 0:
            alcance = self.raio_fisico * 2.5
            anim_time = profile.total_time * 0.8
            base_cd = 0.3 + random.random() * 0.2
        else:
            alcance = self.raio_fisico * 4.0
            anim_time = profile.total_time * 1.2
            base_cd = 0.5 + random.random() * 0.3

        # Bônus pós-troca: primeiro ataque após trocar é mais forte/rápido
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

    def _disparar_arremesso(self, alvo):
        """Dispara projéteis de arma de arremesso — v15.0 volley system"""
        from core.combat import ArmaProjetil
        
        arma = self.dados.arma_obj
        if not arma:
            return
        
        qtd = int(getattr(arma, 'quantidade', 3))
        tam = self.raio_fisico * 0.35
        dano_por_proj = arma.dano / max(qtd, 1)
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (200, 200, 200)
        
        # --- Tipo & velocidade base por estilo ---
        estilo = getattr(arma, 'estilo', '').lower()
        if "shuriken" in estilo:
            tipo_proj = "shuriken"
            vel = 18.0
        elif "chakram" in estilo:
            tipo_proj = "chakram"
            vel = 14.0
        elif "bumerangue" in estilo or "boomerang" in estilo:
            tipo_proj = "chakram"        # mesma visual, retorna
            vel = 13.0
        elif "bola" in estilo or "boleadeira" in estilo:
            tipo_proj = "faca"
            vel = 12.0
        elif "rede" in estilo:
            tipo_proj = "faca"
            vel = 10.0
        else:
            tipo_proj = "faca"
            vel = 16.0
        
        # --- Volley bonus: arremessos consecutivos ficam mais rápidos e com spread menor ---
        consec = getattr(self, 'throw_consecutive', 0)
        volley_bonus = min(consec * 0.08, 0.30)   # até +30% vel
        vel *= (1.0 + volley_bonus)
        spread_base = 25 if qtd > 1 else 0
        spread = spread_base * max(0.5, 1.0 - consec * 0.1)  # spread encolhe a cada volley
        
        # --- Dano bonus por consecutivos ---
        dano_mult = 1.0 + min(consec * 0.05, 0.20)  # até +20% dano
        
        # --- Mira preditiva no alvo ---
        dx = alvo.pos[0] - self.pos[0]
        dy = alvo.pos[1] - self.pos[1]
        dist_alvo = math.hypot(dx, dy)
        angulo_base = self.angulo_olhar
        if dist_alvo > 0.1:
            tempo_voo = dist_alvo / vel
            fut_x = alvo.pos[0] + alvo.vel[0] * tempo_voo * 0.5
            fut_y = alvo.pos[1] + alvo.vel[1] * tempo_voo * 0.5
            angulo_base = math.degrees(math.atan2(fut_y - self.pos[1], fut_x - self.pos[0]))
        
        dist_atual = math.hypot(alvo.pos[0] - self.pos[0], alvo.pos[1] - self.pos[1])
        if dist_atual < 2.5:
            dano_mult *= 0.82
        elif dist_atual > 8.5:
            dano_mult *= 1.02

        for i in range(qtd):
            if qtd > 1:
                offset = -spread / 2 + (spread / (qtd - 1)) * i
            else:
                offset = 0
            
            ang = angulo_base + offset + random.uniform(-1.5, 1.5)
            spawn_dist = self.raio_fisico + 0.5
            spawn_x = self.pos[0] + math.cos(math.radians(ang)) * spawn_dist
            spawn_y = self.pos[1] + math.sin(math.radians(ang)) * spawn_dist
            
            proj = ArmaProjetil(
                tipo=tipo_proj,
                x=spawn_x, y=spawn_y,
                angulo=ang,
                dono=self,
                dano=dano_por_proj * (self.dados.forca / 2.0) * dano_mult,
                velocidade=vel,
                tamanho=tam,
                cor=cor
            )
            self.buffer_projeteis.append(proj)
    
    def _disparar_flecha(self, alvo):
        """Dispara flecha do arco — v15.0 charged shot system"""
        from core.combat import FlechaProjetil
        
        arma = self.dados.arma_obj
        if not arma:
            return
        
        dano = arma.dano * (self.dados.forca / 2.0 + 0.5)
        forca = getattr(arma, 'forca_arco', 1.0)
        forca_normalizada = max(0.5, min(2.0, forca / 25.0))
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (139, 90, 43)
        
        # --- Charged shot bonus ---
        charge = getattr(self, 'bow_charge', 0.0)
        charge_pct = min(charge, 1.5)          # cap 1.5s de carga
        if charge_pct >= 1.0:
            # Full charge: +40% dano, +25% vel, flecha maior
            dano *= 1.4
            vel_bonus = 0.25
            tam_mult = 1.4
        elif charge_pct >= 0.5:
            # Half charge: +15% dano, +10% vel
            dano *= 1.15
            vel_bonus = 0.10
            tam_mult = 1.15
        else:
            vel_bonus = 0.0
            tam_mult = 1.0
        
        # --- Perfect shot window (marcado pela IA) ---
        perfect = getattr(self, 'bow_perfect_timer', 0.0)
        if perfect > 0:
            dano *= 1.25  # +25% extra em tiro perfeito
        
        # Reset charge after firing
        self.bow_charge = 0.0
        self.bow_charging = False
        
        # === MIRA DIRETA NO ALVO (sem gravidade) ===
        dx = alvo.pos[0] - self.pos[0]
        dy = alvo.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        
        vel_flecha = (35.0 + forca_normalizada * 20.0) * (1.0 + vel_bonus)
        
        if dist > 0.1:
            tempo_voo = dist / vel_flecha
            
            # Predição melhor: 80% da velocidade do alvo (melhoria v15)
            alvo_futuro_x = alvo.pos[0] + alvo.vel[0] * tempo_voo * 0.8
            alvo_futuro_y = alvo.pos[1] + alvo.vel[1] * tempo_voo * 0.8
            
            dx_mira = alvo_futuro_x - self.pos[0]
            dy_mira = alvo_futuro_y - self.pos[1]
            angulo_mira = math.degrees(math.atan2(dy_mira, dx_mira))
        else:
            angulo_mira = self.angulo_olhar
        
        # Imprecisão menor com charge (mais focado)
        imprecisao = max(0.5, 2.0 - charge_pct * 1.0)
        # Em curta distância, arqueiro sob pressão perde precisão e dano.
        if dist < 3.0:
            imprecisao += 2.8
            dano *= 0.55
        elif dist > 9.5:
            dano *= 1.03
        angulo_mira += random.uniform(-imprecisao, imprecisao)
        
        # === SPAWN DA FLECHA ===
        rad = math.radians(angulo_mira)
        spawn_dist = self.raio_fisico + 0.3
        spawn_x = self.pos[0] + math.cos(rad) * spawn_dist
        spawn_y = self.pos[1] + math.sin(rad) * spawn_dist
        
        flecha = FlechaProjetil(
            x=spawn_x, y=spawn_y,
            angulo=angulo_mira,
            dono=self,
            dano=dano,
            forca=forca_normalizada * tam_mult,
            cor=cor
        )
        self.buffer_projeteis.append(flecha)

    def _disparar_orbes(self, alvo):
        """Dispara orbes mágicos — v15.0 salva/mana scaling"""
        from core.combat import OrbeMagico
        
        arma = self.dados.arma_obj
        if not arma:
            return
        
        qtd = int(getattr(arma, 'quantidade', 2))
        dano_por_orbe = arma.dano / max(qtd, 1)
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (100, 100, 255)
        
        # --- Mana scaling: mana alta = orbes mais fortes ---
        mana_ratio = self.dados.mana / max(self.dados.mana_max, 1) if hasattr(self.dados, 'mana_max') else 0.5
        mana_mult = 0.8 + mana_ratio * 0.6   # 0.8x (sem mana) → 1.4x (mana cheia)
        
        # --- Estilo bonus ---
        estilo = getattr(arma, 'estilo', '').lower()
        if "runas" in estilo or "flutuante" in estilo:
            dano_bonus = 1.15      # Runas: mais dano por orbe
        elif "cristal" in estilo or "prisma" in estilo:
            dano_bonus = 1.0
            qtd = min(qtd + 1, 5)  # Cristal: +1 orbe extra (max 5)
        elif "foguete" in estilo or "missil" in estilo:
            dano_bonus = 1.25      # Míssil: mais dano puro
        else:
            dano_bonus = 1.0
        
        orbes_orbitando = [o for o in self.buffer_orbes if o.ativo and o.estado == "orbitando"]
        
        dist_atual = math.hypot(alvo.pos[0] - self.pos[0], alvo.pos[1] - self.pos[1])
        if dist_atual < 2.2:
            mana_mult *= 0.66
        elif dist_atual > 6.5:
            mana_mult *= 1.02

        if orbes_orbitando:
            # --- Salva: dispara todos de uma vez ao invés de um por um ---
            for orbe in orbes_orbitando[:qtd]:
                orbe.dano *= mana_mult * dano_bonus  # aplica bonus ao disparar
                orbe.iniciar_carga(alvo)
        else:
            for i in range(qtd):
                orbe = OrbeMagico(
                    x=self.pos[0], y=self.pos[1],
                    dono=self,
                    dano=dano_por_orbe * (self.dados.forca / 2.0 + self.dados.mana / 2.0) * mana_mult * dano_bonus,
                    indice=i,
                    total=qtd,
                    cor=cor
                )
                orbe.iniciar_carga(alvo)
                self.buffer_orbes.append(orbe)

    def tomar_dano(self, dano, empurrao_x, empurrao_y, tipo_efeito="NORMAL", atacante=None):
        """Recebe dano com suporte a efeitos e reflexão"""
        from core.combat import DotEffect
        
        if self.morto or self.invencivel_timer > 0:
            return False
        
        # SONO: acordar ao tomar dano
        if getattr(self, 'dormindo', False):
            self.dormindo = False
            self.stun_timer = 0
        
        dano_final = dano

        if "Cavaleiro" in self.classe_nome:
            dano_final *= 0.75

        if "Ladino" in self.classe_nome and random.random() < 0.2:
            return False

        # CM-12: CEGO reduz chance de acerto do ATACANTE (aplicado no defensor via atacante)
        if atacante is not None and getattr(atacante, 'cego_timer', 0) > 0:
            if random.random() < 0.5:  # 50% de miss quando cego
                return False

        # CM-13: ESQUIVA_GARANTIDA (Previsão buff) — consome 1 carga de esquiva
        esquivas = getattr(self, 'esquivas_garantidas', 0)
        if esquivas > 0:
            self.esquivas_garantidas -= 1
            return False

        # CM-08 fix: aplica dano_recebido_bonus de buffs (ex: Sobrecarga recebe mais dano)
        for buff in self.buffs_ativos:
            dano_recebido = getattr(buff, 'dano_recebido_bonus', 1.0)
            if dano_recebido != 1.0:
                dano_final *= dano_recebido

        # FP-3: aplica vulnerabilidade se ativa (antes era setada mas nunca lida)
        if getattr(self, 'vulnerabilidade', 1.0) != 1.0:
            dano_final *= self.vulnerabilidade

        # CM-10: EXPOSTO aumenta dano recebido em 2x (antes timer setado mas nunca lido)
        if getattr(self, 'exposto_timer', 0) > 0:
            dano_final *= 2.0

        # MARCADO: próximo ataque causa dano extra e consume a marca
        if getattr(self, 'marcado', False):
            dano_final *= 1.3
            self.marcado = False

        # CM-11: CONGELADO aumenta dano recebido em 1.5x (magic_system define mod_dano_recebido: 1.5)
        if getattr(self, 'congelado', False):
            dano_final *= 1.5

        for buff in self.buffs_ativos:
            if buff.escudo_atual > 0:
                dano_final = buff.absorver_dano(dano_final)
        
        # Reflexo de dano (Reflexo Espelhado)
        dano_refletido = 0
        for buff in self.buffs_ativos:
            if hasattr(buff, 'refletir') and buff.refletir > 0:
                dano_refletido += dano_final * buff.refletir
        
        # Aplica dano refletido ao atacante (se existir)
        if dano_refletido > 0 and atacante is not None and not atacante.morto:
            # Aplica dano direto sem recursão (sem passar atacante)
            atacante.vida -= dano_refletido
            atacante.flash_timer = 0.15
            atacante.flash_cor = (200, 200, 255)  # Flash azulado para reflexo
            if atacante.vida <= 0:
                atacante.morrer()
        
        self.vida -= dano_final
        self.invencivel_timer = 0.3

        # === PASSIVA: sobreviver — uma vez por luta sobrevive com 1 HP (BUG-03 fix) ===
        passiva = getattr(self, 'arma_passiva', None) or {}
        if passiva.get("efeito") == "sobreviver" and self.vida <= 0:
            if not getattr(self, '_sobreviver_usado', False):
                self.vida = 1
                self._sobreviver_usado = True
        
        # Flash de dano mais longo e visível (proporcional ao dano)
        self.flash_timer = min(0.25, 0.1 + dano_final * 0.005)
        
        # Cor do flash baseada no tipo de efeito
        self.flash_cor = {
            "NORMAL": (255, 255, 255),
            # Fogo
            "FOGO": (255, 150, 50),
            "QUEIMAR": (255, 100, 0),
            "QUEIMANDO": (255, 120, 20),
            # Gelo
            "GELO": (150, 220, 255),
            "CONGELAR": (100, 200, 255),
            "CONGELADO": (180, 230, 255),
            "LENTO": (150, 200, 255),
            # Natureza/Veneno
            "VENENO": (100, 255, 100),
            "ENVENENADO": (80, 220, 80),
            "NATUREZA": (100, 200, 50),
            # Sangue
            "SANGRAMENTO": (255, 50, 50),
            "SANGRANDO": (200, 30, 30),
            "SANGUE": (180, 0, 50),
            # Raio
            "RAIO": (255, 255, 100),
            "PARALISIA": (255, 255, 150),
            # Trevas
            "TREVAS": (150, 50, 200),
            "MALDITO": (100, 0, 150),
            "NECROSE": (50, 50, 50),
            "DRENAR": (120, 0, 150),
            # Luz
            "LUZ": (255, 255, 220),
            "CEGO": (255, 255, 200),
            # Arcano
            "ARCANO": (150, 100, 255),
            "SILENCIADO": (180, 150, 255),
            # Tempo
            "TEMPO": (200, 180, 255),
            "TEMPO_PARADO": (220, 200, 255),
            # Gravitação
            "GRAVITACAO": (100, 50, 150),
            "PUXADO": (120, 70, 180),
            "VORTEX": (80, 30, 130),
            # Caos
            "CAOS": (255, 100, 200),
            # CC
            "ATORDOAR": (255, 255, 100),
            "ATORDOADO": (255, 255, 100),
            "ENRAIZADO": (139, 90, 43),
            "MEDO": (150, 0, 150),
            "CHARME": (255, 150, 200),
            "SONO": (100, 100, 200),
            "KNOCK_UP": (200, 200, 255),
            # Debuffs
            "FRACO": (150, 150, 150),
            "VULNERAVEL": (255, 150, 150),
            "EXAUSTO": (100, 100, 100),
            "MARCADO": (255, 200, 50),
            "EXPOSTO": (255, 180, 100),
            "CORROENDO": (150, 100, 50),
            # Especiais
            "EXPLOSAO": (255, 200, 100),
            "EMPURRAO": (200, 200, 200),
            "BOMBA_RELOGIO": (255, 150, 0),
            "POSSESSO": (100, 0, 100),
        }.get(tipo_efeito, (255, 255, 255))
        
        if self.brain is not None:
            self.brain.raiva += 0.2
        
        # Knockback proporcional ao dano e vida restante
        kb = 15.0 + (1.0 - (self.vida/self.vida_max)) * 10.0
        kb += dano_final * 0.2  # Dano alto = mais knockback
        self.vel[0] += empurrao_x * kb
        self.vel[1] += empurrao_y * kb
        
        self._aplicar_efeito_status(tipo_efeito)
        
        if self.vida < self.vida_max * 0.3:
            self.modo_adrenalina = True
        
        if self.vida <= 0:
            self.morrer()
            return True
        return False

    def aplicar_cc(self, efeito: str, duracao: float = None, intensidade: float = 1.0) -> None:
        """
        D02: Ponto de entrada PÚBLICO para aplicar qualquer CC ou status.
        Alias de _aplicar_efeito_status() — garante que todo código novo
        use este método, facilitando a migração futura para StatusEffect.

        Exemplos:
            lutador.aplicar_cc("LENTO", duracao=2.0)
            lutador.aplicar_cc("CONGELADO", duracao=1.5, intensidade=1.2)
        """
        self._aplicar_efeito_status(efeito, duracao=duracao, intensidade=intensidade)

    def _aplicar_efeito_status(self, efeito, duracao=None, intensidade=1.0):
        """
        Aplica efeitos de status do dano - Sistema v2.0 COLOSSAL
        
        Args:
            efeito: Nome do efeito a aplicar
            duracao: Duração customizada (opcional)
            intensidade: Multiplicador de intensidade (default 1.0)
        """
        from core.combat import DotEffect
        
        # =================================================================
        # DANOS AO LONGO DO TEMPO (DoT)
        # =================================================================
        if efeito == "VENENO" or efeito == "ENVENENADO":
            dot = DotEffect("ENVENENADO", self, 1.5 * intensidade, duracao or 4.0, (100, 255, 100))
            self.dots_ativos.append(dot)
            
        elif efeito == "SANGRAMENTO" or efeito == "SANGRANDO":
            dot = DotEffect("SANGRANDO", self, 2.0 * intensidade, duracao or 3.0, (180, 0, 30))
            self.dots_ativos.append(dot)
            
        elif efeito == "QUEIMAR" or efeito == "QUEIMANDO":
            dot = DotEffect("QUEIMANDO", self, 2.5 * intensidade, duracao or 2.5, (255, 100, 0))
            self.dots_ativos.append(dot)
            
        elif efeito == "CORROENDO":
            # Corrosão: Dano + reduz defesa
            dot = DotEffect("CORROENDO", self, 1.5 * intensidade, duracao or 4.0, (150, 100, 50))
            self.dots_ativos.append(dot)
            self.mod_defesa *= 0.8  # -20% defesa
            
        elif efeito == "NECROSE":
            # Necrose: DoT que impede cura
            dot = DotEffect("NECROSE", self, 3.0 * intensidade, duracao or 5.0, (50, 50, 50))
            self.dots_ativos.append(dot)
            self.cura_bloqueada = duracao or 5.0
            
        elif efeito == "MALDITO":
            # Maldição: DoT + dano recebido aumentado
            dot = DotEffect("MALDITO", self, 1.0 * intensidade, duracao or 6.0, (100, 0, 100))
            self.dots_ativos.append(dot)
            self.vulnerabilidade = 1.3
            # FP-3: timer para expirar o bônus de vulnerabilidade junto com o DoT
            self.vulnerabilidade_timer = duracao or 6.0
        
        # =================================================================
        # CONTROLE DE GRUPO (CC)
        # =================================================================
        elif efeito == "CONGELAR" or efeito == "CONGELADO":
            self.stun_timer = max(self.stun_timer, duracao or 2.0)
            self.slow_timer = max(self.slow_timer, (duracao or 2.0) + 1.0)
            self.slow_fator = 0.3
            self.congelado = True
            self.congelado_timer = max(getattr(self, 'congelado_timer', 0), duracao or 2.0)
            
        elif efeito == "LENTO":
            self.slow_timer = max(self.slow_timer, duracao or 2.0)
            self.slow_fator = min(self.slow_fator, 0.5 / intensidade)
            
        elif efeito == "ATORDOAR" or efeito == "ATORDOADO":
            self.stun_timer = max(self.stun_timer, (duracao or 0.8) * intensidade)
            
        elif efeito == "PARALISIA":
            # Paralisia: Stun mais curto mas frequente
            self.stun_timer = max(self.stun_timer, (duracao or 0.5) * intensidade)
            self.flash_cor = (255, 255, 100)
            self.flash_timer = 0.3
            
        elif efeito == "ENRAIZADO":
            # Enraizado: Não pode mover mas pode atacar
            self.enraizado_timer = max(self.enraizado_timer, duracao or 2.5)
            self.slow_fator = 0.0  # Velocidade zero
            
        elif efeito == "SILENCIADO":
            # Silenciado: Não pode usar skills
            self.silenciado_timer = duracao or 3.0
            
        elif efeito == "CEGO":
            # Cego: Ângulo de visão prejudicado (IA afetada)
            self.cego_timer = duracao or 2.0
            self.flash_cor = (255, 255, 200)
            self.flash_timer = 0.5
            
        elif efeito == "MEDO":
            # Medo: Força a fugir
            self.medo_timer = duracao or 2.5
            if self.brain is not None:
                self.brain.medo = 1.0  # Maximiza medo na IA
            
        elif efeito == "CHARME":
            # Charme: Inimigo te segue
            self.charme_timer = duracao or 2.0
            
        elif efeito == "SONO":
            # Sono: Stun longo que quebra com dano
            self.dormindo = True
            self.stun_timer = max(self.stun_timer, duracao or 4.0)
            
        elif efeito == "KNOCK_UP":
            # Knock Up: Joga no ar
            self.vel_z = 12.0 * intensidade
            self.stun_timer = max(self.stun_timer, 0.5)
            
        elif efeito == "PUXADO":
            # Puxado: Atração gravitacional (implementado no efeito de área)
            self.sendo_puxado = True
            
        elif efeito == "TEMPO_PARADO":
            # Tempo parado: Completamente imobilizado
            self.stun_timer = max(self.stun_timer, duracao or 2.0)
            self.slow_fator = 0.0
            self.tempo_parado = True
            
        elif efeito == "VORTEX":
            # Vortex: Sendo puxado continuamente
            self.em_vortex = True
        
        # =================================================================
        # DEBUFFS
        # =================================================================
        elif efeito == "FRACO":
            # Fraco: Dano reduzido
            self.dano_reduzido = 0.7
            # FP-2: adiciona timer para que o efeito expire
            self.fraco_timer = duracao or 3.0
            
        elif efeito == "VULNERAVEL":
            # Vulnerável: Dano recebido aumentado
            self.vulnerabilidade = 1.5
            # FP-3: adiciona timer para que o efeito expire
            self.vulnerabilidade_timer = duracao or 3.0
            
        elif efeito == "EXAUSTO":
            # Exausto: Regen de stamina/mana reduzida
            # BUG-C2: Não modificar regen_mana_base diretamente (era permanente).
            # O timer é decrementado no update() e a penalidade é aplicada condicionalmente no cálculo de mana.
            self.exausto_timer = duracao or 5.0
            
        elif efeito == "MARCADO":
            # Marcado: Próximo ataque causa dano extra
            self.marcado = True
            
        elif efeito == "EXPOSTO":
            # Exposto: Ignora parte da defesa
            if not hasattr(self, 'exposto_timer'):
                self.exposto_timer = 0
            self.exposto_timer = duracao or 4.0
        
        # =================================================================
        # EFEITOS DE EMPURRÃO/MOVIMENTO
        # =================================================================
        elif efeito == "EMPURRAO":
            # Já tratado pelo knockback normal
            pass
            
        elif efeito == "EXPLOSAO":
            # Explosão já causa o knockback
            pass
        
        # =================================================================
        # EFEITOS ESPECIAIS
        # =================================================================
        elif efeito == "DRENAR":
            # Drenar: Já é tratado pelo lifesteal da skill
            pass
            
        elif efeito == "BOMBA_RELOGIO":
            # Bomba relógio: Explode depois de X segundos
            if not hasattr(self, 'bomba_relogio_timer'):
                self.bomba_relogio_timer = 0
            self.bomba_relogio_timer = duracao or 3.0
            self.bomba_relogio_dano = 80.0 * intensidade
            
        elif efeito == "LINK_ALMA":
            # Link de alma: Dano compartilhado
            if not hasattr(self, 'link_alma_alvo'):
                self.link_alma_alvo = None
                
        elif efeito == "POSSESSO":
            # Possessão: Controle invertido temporário
            if not hasattr(self, 'possesso_timer'):
                self.possesso_timer = 0
            self.possesso_timer = duracao or 3.0

    def tomar_clash(self, ex, ey):
        """Recebe impacto de clash de armas"""
        self.stun_timer = 0.5
        self.atacando = False
        self.vel[0] += ex * 25
        self.vel[1] += ey * 25

    def morrer(self):
        """Processa morte do lutador"""
        # CM-14: FP1 fix — verifica buffs/skills com ativa_ao_morrer (Último Suspiro)
        for buff in list(self.buffs_ativos):
            if getattr(buff, 'ativa_ao_morrer', False):
                cura_pct = getattr(buff, 'cura_percent', 0.5)
                self.vida = self.vida_max * cura_pct
                self.buffs_ativos.remove(buff)
                self.morto = False
                return  # Reviveu!

        # CM-14b: FP1 — verifica skills de arma com ativa_ao_morrer
        for sk in getattr(self, 'skills_arma', []):
            data = sk.get("data", {})
            if data.get("ativa_ao_morrer") and not getattr(self, '_ultimo_suspiro_usado', False):
                cura_pct = data.get("cura_percent", 0.5)
                self.vida = self.vida_max * cura_pct
                self._ultimo_suspiro_usado = True
                self.morto = False
                self.invencivel_timer = 1.0  # Breve invencibilidade após reviver
                return

        # CM-14c: FP1 — verifica skills de classe com ativa_ao_morrer
        for sk in getattr(self, 'skills_classe', []):
            data = sk.get("data", {})
            if data.get("ativa_ao_morrer") and not getattr(self, '_ultimo_suspiro_usado', False):
                cura_pct = data.get("cura_percent", 0.5)
                self.vida = self.vida_max * cura_pct
                self._ultimo_suspiro_usado = True
                self.morto = False
                self.invencivel_timer = 1.0
                return

        self.morto = True
        self.vida = 0
        self.arma_droppada_pos = list(self.pos)
        self.arma_droppada_ang = self.angulo_arma_visual

    def get_pos_ponteira_arma(self):
        """Retorna posição da ponta da arma"""
        arma = self.dados.arma_obj
        if not arma:
            return None
        
        if any(t in arma.tipo for t in ["Orbital", "Arremesso", "Mágica"]):
            return None
        
        rad = math.radians(self.angulo_arma_visual)
        ax, ay = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        
        # Posição da arma baseada em raio_fisico × range_mult (geometria removida)
        from core.hitbox import HITBOX_PROFILES
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

    def get_escudo_info(self):
        """Retorna info do escudo orbital"""
        arma = self.dados.arma_obj
        if not arma or "Orbital" not in arma.tipo:
            return None
        cx, cy = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        dist_base_px = int(((arma.distancia/100)*PPM)*self.fator_escala)
        raio_char_px = int((self.dados.tamanho/2)*PPM)
        return (cx, cy), dist_base_px + raio_char_px, self.angulo_arma_visual, arma.largura
    
    def get_dano_modificado(self, dano_base):
        """Retorna dano com todos os modificadores (buffs, classe, passivas)"""
        dano = dano_base * self.mod_dano

        for buff in self.buffs_ativos:
            dano *= buff.buff_dano
            # CM-08 fix: bonus_velocidade_ataque não afeta dano — mas buff_dano sim

        if "Berserker" in self.classe_nome:
            hp_pct = self.vida / self.vida_max
            dano *= 1.0 + (1.0 - hp_pct) * 0.5

        if "Assassino" in self.classe_nome and random.random() < 0.25:
            dano *= 2.0

        return dano

    # =========================================================================
    # SISTEMA DE CHANNELING v8.0 (Para Classes Mágicas)
    # =========================================================================
    
    def pode_canalizar_magia(self) -> bool:
        """
        Verifica se o personagem pode canalizar magias.
        Apenas classes mágicas têm acesso ao channeling.
        """
        classes_magicas = ["Mago", "Piromante", "Criomante", "Necromante", "Feiticeiro"]
        return any(c in self.classe_nome for c in classes_magicas)
    
    def iniciar_canalizacao(self, skill_nome: str, skill_data: dict) -> bool:
        """
        Inicia a canalização de uma magia poderosa.
        
        Args:
            skill_nome: Nome da skill a ser canalizada
            skill_data: Dados da skill
            
        Returns:
            True se a canalização iniciou com sucesso
            
        Nota:
            O GameFeelManager gerencia o estado real da canalização.
            Este método apenas marca o lutador como "canalizando".
        """
        if not self.pode_canalizar_magia():
            return False
        
        # Marca estado de canalização no lutador
        self.canalizando = True
        self.skill_canalizando = skill_nome
        self.tempo_canalizacao = 0.0
        
        # O resto é gerenciado pelo GameFeelManager
        return True
    
    def interromper_canalizacao(self):
        """Interrompe a canalização atual"""
        self.canalizando = False
        self.skill_canalizando = None
        self.tempo_canalizacao = 0.0
    
    def atualizar_canalizacao(self, dt: float) -> dict:
        """
        Atualiza o estado de canalização.
        
        Returns:
            Dict com resultado se a magia foi liberada, None caso contrário
        """
        if not getattr(self, 'canalizando', False):
            return None
        
        self.tempo_canalizacao += dt
        
        # O GameFeelManager processa a lógica real
        # Este método apenas rastreia o tempo no lutador
        return None
    
    def get_progresso_canalizacao(self) -> float:
        """Retorna o progresso da canalização (0.0 a 1.0)"""
        if not getattr(self, 'canalizando', False):
            return 0.0
        
        # Tempo padrão de canalização varia por classe
        tempo_base = {
            "Mago (Arcano)": 1.5,
            "Piromante (Fogo)": 2.0,
            "Criomante (Gelo)": 1.2,
            "Necromante (Trevas)": 2.5,
            "Feiticeiro (Caos)": 1.0,
        }.get(self.classe_nome, 1.5)
        
        return min(1.0, getattr(self, 'tempo_canalizacao', 0.0) / tempo_base)
