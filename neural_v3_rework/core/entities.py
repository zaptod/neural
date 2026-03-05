"""
NEURAL FIGHTS - Entidade Lutador
Classe principal do lutador com sistema de combate.
"""
import math
import random
from typing import TYPE_CHECKING
from utils.config import PPM, GRAVIDADE_Z, ATRITO, ALTURA_PADRAO

if TYPE_CHECKING:
    from models.characters import Personagem


class Lutador:
    """
    Classe principal do lutador com suporte completo a:
    - Sistema de classes expandido
    - Novos tipos de skills (DASH, BUFF, AREA, BEAM, SUMMON)
    - Efeitos de status (DoT, buffs, debuffs)
    - Batalhas multi-lutador com equipes (v13.0)
    """
    def __init__(self, dados_char: 'Personagem', pos_x, pos_y, team_id=0):  # type: ignore[name-defined]
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
        self.estamina = 100.0
        self.estamina_max = 100.0
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
            # v16.0: Sistema de durabilidade de arma
            self.arma_durabilidade = getattr(arma, 'durabilidade', 100.0)
            self.arma_durabilidade_max = getattr(arma, 'durabilidade_max', 100.0)
        else:
            self.arma_raridade = 'Comum'
            self.arma_critico = 0.0
            self.arma_vel_ataque = 1.0
            self.arma_encantamentos = []
            self.arma_passiva = None
            self.arma_tipo = None
            self.arma_durabilidade = 100.0
            self.arma_durabilidade_max = 100.0
        
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
        self._kill_registered: bool = False  # Flag para detectar mortes indiretas (DoT, hazard)
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
        self.ultimo_atacante = None  # Rastreia quem causou o último dano
        
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
        self.arma_droppada_ang = 0
        self.fator_escala = self.dados.tamanho / ALTURA_PADRAO
        self.alcance_ideal = 1.5
        
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

        # IA
        self.brain = AIBrain(self)

    def _calcular_vida_max(self):
        """Calcula vida máxima com modificadores"""
        base = 80.0 + (self.dados.resistencia * 5)  # Vida reduzida para lutas mais rápidas
        return base * self.class_data.get("mod_vida", 1.0)
    
    def _calcular_mana_max(self):
        """Calcula mana máxima com modificadores"""
        base = 50.0 + (getattr(self.dados, 'mana', 0) * 10.0)
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
    
    def calcular_dano_ataque(self, dano_base, alvo=None):
        """Calcula dano final com crítico, encantamentos e PASSIVA da arma (BUG-03 fix)"""
        from models import ENCANTAMENTOS

        dano = dano_base * self.mod_dano

        # === v16.0: penalidade de durabilidade de arma ===
        dano *= self._get_durabilidade_mult()

        # FP-2: aplica penalidade de FRACO se ativa (antes era setado mas nunca lido)
        if getattr(self, 'dano_reduzido', 1.0) != 1.0:
            dano *= self.dano_reduzido

        # === v16.0: PASSIVAS DE CLASSE — dano ofensivo ===
        if "Guerreiro" in self.classe_nome:
            dano *= 1.10  # "Golpes físicos causam 10% mais dano"
        if "Berserker" in self.classe_nome:
            hp_ratio = self.vida / max(self.vida_max, 1)
            if hp_ratio < 1.0:
                # Escala linear: 0% HP → +30%, 100% HP → +0%
                bonus_berserk = (1.0 - hp_ratio) * 0.30
                dano *= 1.0 + bonus_berserk
        if "Piromante" in self.classe_nome:
            # "+15% dano em magias de fogo" — verifica elemento da arma/encantamento
            for enc_nome in self.arma_encantamentos:
                if enc_nome in ("Chamas",):
                    dano *= 1.15
                    break
        if "Duelista" in self.classe_nome:
            # "+10% dano em 1v1" — sempre ativo em duelos
            dano *= 1.10
        if "Monge" in self.classe_nome:
            # "Ataques desarmados causam dano mágico" — bonus escala com mana
            mana_ratio = self.mana / max(self.mana_max, 1)
            dano *= 1.0 + mana_ratio * 0.15  # até +15% com mana cheia

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
            critico_chance += 0.20
        if passiva.get("efeito") == "crit_chance":
            critico_chance += passiva.get("valor", 0) / 100.0

        is_critico = random.random() < critico_chance
        if is_critico:
            mult_critico = 1.5
            # === PASSIVA: crit_damage (aumenta multiplicador crítico) ===
            if passiva.get("efeito") == "crit_damage":
                mult_critico += passiva.get("valor", 0) / 100.0
            dano *= mult_critico

        for enc_nome in self.arma_encantamentos:
            if enc_nome in ENCANTAMENTOS:
                enc = ENCANTAMENTOS[enc_nome]
                dano += enc.get("dano_bonus", 0)

        # === v16.0: BÊNÇÃO DIVINA — modificador de dano ofensivo ===
        try:
            from core.divine import DivineBlessingManager
            divine = DivineBlessingManager.get_instance()
            dano = divine.aplicar_passiva_dano(self, dano, alvo=alvo)
        except Exception:
            pass

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
                if not alvo.morto and getattr(alvo, 'invencivel_timer', 0) <= 0:
                    # Usa tomar_dano para respeitar shields, sobreviver, class reduction
                    alvo.tomar_dano(alvo.vida + 10, 0, 0, "NORMAL", atacante=self)
                    resultado["execute"] = True

        # === PASSIVA: double_hit (chance de aplicar dano novamente) ===
        if efeito == "double_hit" and random.random() < (valor / 100.0):
            if not alvo.morto:
                dano_eco = dano_aplicado * 0.5
                alvo.vida = max(0, alvo.vida - dano_eco)
                resultado["double_hit"] = dano_eco
                if alvo.vida <= 0 and not alvo.morto:
                    alvo.morrer()

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

        # === v16.0: PASSIVAS DE CLASSE — on_hit ===
        # Necromante: Drena 10% do dano causado como vida
        if "Necromante" in self.classe_nome:
            cura_necro = dano_aplicado * 0.10
            self.vida = min(self.vida_max, self.vida + cura_necro)
            resultado["necro_lifesteal"] = cura_necro

        # Feiticeiro: 15% chance de "lançar duas vezes" — aplica 50% do dano novamente
        if "Feiticeiro" in self.classe_nome and random.random() < 0.15:
            if not alvo.morto:
                dano_eco = dano_aplicado * 0.50
                alvo.vida = max(0, alvo.vida - dano_eco)
                resultado["feiticeiro_duplo"] = dano_eco
                if alvo.vida <= 0 and not alvo.morto:
                    alvo.morrer()

        # Criomante: Ataques sempre aplicam slow (simplificado como dot de gelo curto)
        if "Criomante" in self.classe_nome and not alvo.morto:
            from core.combat import DotEffect
            jah_congelado = any(d.tipo == "CONGELADO" for d in getattr(alvo, 'dots_ativos', []))
            if not jah_congelado:
                dot_gelo = DotEffect("CONGELADO", alvo, 0, 1.5, (150, 220, 255))
                alvo.dots_ativos.append(dot_gelo)
                resultado["criomante_slow"] = True

        # Druida: Venenos duram 50% mais — aplicado em aplicar_efeitos_encantamento
        # (hookado separadamente pois precisa modificar duração do DOT)

        # === v16.0: BÊNÇÃO DIVINA — on_hit ===
        try:
            from core.divine import DivineBlessingManager
            divine = DivineBlessingManager.get_instance()
            divine.aplicar_passiva_on_hit(self, alvo, dano_aplicado)
        except Exception:
            pass

        # === v16.0: COMBO SYSTEM — registra hit ===
        try:
            from core.combo import ComboSystem
            combo = ComboSystem.get_instance()
            combo_evento = combo.on_hit(self, alvo, dano_aplicado)
            if combo_evento:
                resultado["combo"] = combo_evento
        except Exception:
            pass

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
                alvo.slow_timer = 2.0
                alvo.slow_fator = 0.5
            elif efeito == "poison":
                duracao_veneno = enc.get("dot_duracao", 5.0)
                # v16.0: Druida — venenos duram 50% mais
                if "Druida" in self.classe_nome:
                    duracao_veneno *= 1.50
                dot = DotEffect("Envenenado", alvo, enc.get("dot_dano", 3),
                               duracao_veneno, (100, 255, 100))
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
            custo_real *= 0.8
        
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
        
        # === v16.0: BÊNÇÃO DIVINA — redução de custo de mana ===
        try:
            from core.divine import DivineBlessingManager
            divine = DivineBlessingManager.get_instance()
            custo_real *= divine.get_mod_custo_mana(self)
        except Exception:
            pass
        
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
        except Exception:
            pass
        
        cd = data["cooldown"]
        if self.arma_passiva and self.arma_passiva.get("efeito") == "cooldown":
            cd *= (1 - self.arma_passiva.get("valor", 0) / 100.0)
        
        # CM-17: FP4 — sem_cooldown buff (Conjuração Perfeita) zera cooldown
        for buff in self.buffs_ativos:
            if getattr(buff, 'sem_cooldown', False):
                cd = 0
                break
        
        # === v16.0: BÊNÇÃO DIVINA — modificador de cooldown ===
        try:
            from core.divine import DivineBlessingManager
            divine = DivineBlessingManager.get_instance()
            cd *= divine.get_mod_cooldown(self)
        except Exception:
            pass
        
        self.cd_skills[nome_skill] = cd
        self.cd_skill_arma = cd
        
        # === v16.0: DURABILIDADE — perda por uso de skill ===
        self._perder_durabilidade(1.0)
        
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
        except Exception:
            pass

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
        if self.cooldown_ataque > 0:
            self.cooldown_ataque -= dt
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

        # Decrementar possesso_timer
        if getattr(self, 'possesso_timer', 0) > 0:
            self.possesso_timer -= dt

        # Limpar flag dormindo quando stun expira naturalmente
        if getattr(self, 'dormindo', False) and self.stun_timer <= 0:
            self.dormindo = False

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
                self.flash_timer = 0.3
                self.flash_cor = (255, 100, 0)
                # Usa tomar_dano para respeitar invencibilidade, shields, sobreviver
                self.tomar_dano(dano_bomba, 0, 0, "EXPLOSAO")

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
        # v16.0: Gladiador — regen mana 30% mais rápido (análogo a "stamina regen")
        if "Gladiador" in self.classe_nome:
            mana_regen *= 1.30
        self.mana = min(self.mana_max, self.mana + mana_regen * dt)
        
        if "Paladino" in self.classe_nome and getattr(self, 'cura_bloqueada', 0) <= 0:
            self.vida = min(self.vida_max, self.vida + self.vida_max * 0.005 * dt)  # 0.5% HP/s
        
        # v16.0: Necromante — drena 10% do dano causado como vida (processado em aplicar_passiva_em_hit)
        # (já hookado via on_hit)
        
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
        
        # Bug fix: não rotacionar durante stun (hitbox ativa não deve rastrear inimigo)
        if self.stun_timer <= 0:
            self.angulo_olhar += diff * vel_giro * dt

        # v13.0: Verifica se há QUALQUER inimigo vivo (não só o principal)
        algum_inimigo_vivo = not inimigo.morto
        if todos_lutadores is not None:
            algum_inimigo_vivo = any(
                not f.morto for f in todos_lutadores
                if f is not self and f.team_id != self.team_id
            )

        # Bug fix: cancelar ataque ao ser stunado (previne dano melee durante stun)
        if self.stun_timer > 0 and self.atacando:
            self.atacando = False
            self.timer_animacao = 0
            self.alvos_atingidos_neste_ataque.clear()

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
        self.status_effects = [
            type('SE', (), {
                'nome': dot.tipo,
                'mod_velocidade': 1.0,
                'mod_dano_causado': 1.0,
                'mod_dano_recebido': 1.0,
                'pode_mover': True,
                'pode_atacar': True,
                'dano_por_tick': dot.dano_por_tick,
            })()
            for dot in self.dots_ativos
        ]
        # Adiciona CCs ativos (stun, slow, congelado)
        if self.stun_timer > 0:
            self.status_effects.append(type('SE', (), {
                'nome': 'congelado' if getattr(self, 'congelado', False) else 'atordoado',
                'mod_velocidade': 0.0, 'mod_dano_causado': 1.0, 'mod_dano_recebido': 1.0,
                'pode_mover': False, 'pode_atacar': False, 'dano_por_tick': 0,
            })())
        elif self.slow_timer > 0:
            self.status_effects.append(type('SE', (), {
                'nome': 'lento',
                'mod_velocidade': self.slow_fator, 'mod_dano_causado': 1.0, 'mod_dano_recebido': 1.0,
                'pode_mover': True, 'pode_atacar': True, 'dano_por_tick': 0,
            })())
    
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
        
        # === v16.0: PASSIVA DE CLASSE — Ninja: +30% velocidade de movimento ===
        if "Ninja" in self.classe_nome:
            acc *= 1.30
        
        # === v16.0: CLIMA — modificador de velocidade ===
        try:
            from core.weather import WeatherSystem
            weather = WeatherSystem.get_instance()
            acc *= weather.get_mod_velocidade()
        except Exception:
            pass
        
        # === v16.0: BÊNÇÃO DIVINA — modificador de velocidade ===
        try:
            from core.divine import DivineBlessingManager
            divine = DivineBlessingManager.get_instance()
            acc *= divine.get_mod_velocidade(self)
        except Exception:
            pass
        
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
        
        # Anti-overlap: quando praticamente dentro do oponente, reduz aproximação
        muito_perto = distancia < self.raio_fisico * 1.5
        fator_aprox = 0.4 if muito_perto else 1.0
        
        if acao in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "APROXIMAR", "CONTRA_ATAQUE", "PRESSIONAR"]:
            mx = math.cos(rad)
            my = math.sin(rad)
            mult = {
                "MATAR": 1.0, "ESMAGAR": 0.85, "ATAQUE_RAPIDO": 1.25,
                "APROXIMAR": 1.0, "CONTRA_ATAQUE": 1.4, "PRESSIONAR": 1.1
            }.get(acao, 1.0)
            mx *= mult * fator_aprox
            my *= mult * fator_aprox
            
            # v8.0: Micro-ajustes durante ataques para parecer mais humano
            if hasattr(self.brain, 'micro_ajustes'):
                mx += random.uniform(-0.05, 0.05)
                my += random.uniform(-0.05, 0.05)
            
        elif acao == "COMBATE":
            mx = math.cos(rad) * 0.6 * fator_aprox
            my = math.sin(rad) * 0.6 * fator_aprox
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
            # Ajuste de distância enquanto circula — usa alcance_ideal relativo
            alcance_ref = self.alcance_ideal
            if distancia < alcance_ref * 0.8:
                mx -= math.cos(rad) * 0.35  # Afasta mais agressivamente
                my -= math.sin(rad) * 0.35
            elif distancia > alcance_ref * 1.8:
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
            mx = math.cos(rad) * 0.55 * fator_aprox
            my = math.sin(rad) * 0.55 * fator_aprox
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
            mx = math.cos(rad) * 1.1 * fator_aprox
            my = math.sin(rad) * 1.1 * fator_aprox
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

        self.vel[0] += mx * acc * dt
        self.vel[1] += my * acc * dt

    def executar_ataques(self, dt, distancia, inimigo):
        """Executa ataques físicos com sistema de animação aprimorado v2.0"""
        from core.combat import ArmaProjetil, FlechaProjetil, OrbeMagico
        from effects.weapon_animations import get_weapon_animation_manager, WEAPON_PROFILES
        
        arma_tipo = self.dados.arma_obj.tipo if self.dados.arma_obj else "Reta"
        arma_estilo = getattr(self.dados.arma_obj, 'estilo', '') if self.dados.arma_obj else ''
        is_orbital = self.dados.arma_obj and "Orbital" in arma_tipo
        
        # === v5.0: CORRENTE usa sistema dedicado ===
        if arma_tipo == "Corrente":
            self._executar_ataques_corrente(dt, distancia, inimigo, arma_estilo)
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
        
        # Orbital: sempre gira
        if is_orbital:
            spd = 200
            if self.brain.acao_atual in ["MATAR", "BLOQUEAR", "COMBATE"] or distancia < 2.5:
                spd = 1000
            self.angulo_arma_visual += spd * dt
        elif self.atacando:
            # Usa novo sistema de animação
            self.timer_animacao -= dt
            
            # Obtém perfil da arma
            profile = WEAPON_PROFILES.get(arma_tipo, WEAPON_PROFILES["Reta"])
            
            if self.timer_animacao <= 0:
                self.atacando = False
                self.angulo_arma_visual = self.angulo_olhar
            else:
                # Aplica offset do animador
                self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]
        else:
            # Animação idle
            self.angulo_arma_visual = self.angulo_olhar + transform["angle_offset"]

        if not self.atacando and not is_orbital and self.cooldown_ataque <= 0:
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
                
                # Margem de 30% para garantir ataque quando IA decide
                alcance_ataque *= 1.3
            except Exception:
                alcance_ataque = self.raio_fisico * 3.0  # Fallback generoso
            
            # Ajustes APENAS para armas ranged (não sobrescreve corpo-a-corpo!)
            if arma_tipo == "Arco":
                alcance_ataque = 20.0  # Arco: MUITO alcance (20 metros!)
            elif arma_tipo == "Arremesso":
                alcance_ataque = 12.0  # Arremesso: alcance médio
            elif arma_tipo == "Mágica":
                alcance_ataque = 8.0
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
                    if random.random() < 0.7:  # 70% chance de atirar mesmo recuando
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
                if arma_tipo in ["Arremesso", "Arco"]:
                    base_cd = 0.8 + random.random() * 0.4
                elif arma_tipo == "Mágica":
                    base_cd = 1.0 + random.random() * 0.5
                if "Assassino" in self.classe_nome:
                    base_cd *= 0.75  # Assassino: precisão mortal
                if "Ninja" in self.classe_nome:
                    base_cd *= 0.70  # Ninja: +30% velocidade de ataque (v16.0)
                elif "Colosso" in self.brain.arquetipo:
                    base_cd *= 1.3
                # BUG-06 fix: velocidade_ataque da arma reduz o cooldown
                vel_ataque = max(0.1, getattr(self, 'arma_vel_ataque', 1.0))
                self.cooldown_ataque = base_cd / vel_ataque
                
                # === v16.0: DURABILIDADE — perda por ataque ===
                self._perder_durabilidade(0.5)

    # =====================================================================
    # === v16.0: SISTEMA DE DURABILIDADE DE ARMA =========================
    # =====================================================================

    def _perder_durabilidade(self, perda_base: float):
        """
        Reduz durabilidade da arma. Raridades altas perdem menos.
        perda_base: valor bruto de perda (0.5 por ataque, 1.0 por skill, 2.0 por clash)
        """
        from models.constants import RARIDADES
        rar_data = RARIDADES.get(self.arma_raridade, {})
        # Raridade reduz perda: Mítico perde 70% menos
        mod = rar_data.get("mod_durabilidade", 1.0)
        perda_real = perda_base / max(mod, 0.5)  # mod_durabilidade alto = menos perda
        self.arma_durabilidade = max(0.0, self.arma_durabilidade - perda_real)

    def _get_durabilidade_mult(self) -> float:
        """Retorna multiplicador de dano/velocidade baseado na durabilidade restante."""
        if self.arma_durabilidade_max <= 0:
            return 1.0
        ratio = self.arma_durabilidade / self.arma_durabilidade_max
        if ratio <= 0:
            return 0.4  # Arma quebrada: -60% dano
        elif ratio < 0.25:
            return 0.7  # Quase quebrada: -30% dano
        elif ratio < 0.5:
            return 0.85  # Desgastada: -15% dano
        return 1.0

    # =====================================================================
    # === SISTEMA DE CORRENTE v5.0 — Mecânicas únicas por estilo ========
    # =====================================================================

    def _atualizar_chain_state(self, dt, distancia):
        """Atualiza estados persistentes das mecânicas de corrente."""
        arma = self.dados.arma_obj
        if not arma or arma.tipo != "Corrente":
            return

        estilo = getattr(arma, 'estilo', '')

        # Mangual: momentum decai lentamente (precisa de hits para manter)
        if "Mangual" in estilo or "Flail" in estilo:
            self.chain_momentum = max(0, self.chain_momentum - dt * 0.15)

        # Kusarigama: combo timer decai, resets combo
        elif estilo == "Kusarigama":
            if self.chain_combo_timer > 0:
                self.chain_combo_timer -= dt
                if self.chain_combo_timer <= 0:
                    self.chain_combo = 0
                    self.chain_mode = 0  # Reset para foice

        # Chicote: stacks de velocidade decaem
        elif estilo == "Chicote":
            if self.chain_whip_stacks > 0 and not self.atacando:
                self.chain_whip_stacks = max(0, self.chain_whip_stacks - dt * 2.0)

        # Meteor Hammer: spin contínuo consome "energia de spin"
        elif estilo == "Meteor Hammer":
            if self.chain_spinning:
                self.chain_spin_speed = min(3.0, self.chain_spin_speed + dt * 0.8)
                # Dano contínuo em área enquanto gira
                self.chain_spin_dmg_timer -= dt
            else:
                self.chain_spin_speed = max(0, self.chain_spin_speed - dt * 1.5)

        # Corrente com Peso: pull timer e slow
        elif "Corrente com Peso" in estilo:
            if self.chain_pull_timer > 0:
                self.chain_pull_timer -= dt
                if self.chain_pull_timer <= 0:
                    self.chain_pull_target = None

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

    def _disparar_arremesso(self, alvo):
        """Dispara projéteis de arma de arremesso"""
        from core.combat import ArmaProjetil
        
        arma = self.dados.arma_obj
        if not arma:
            return
        
        qtd = int(getattr(arma, 'quantidade', 3))
        tam = self.raio_fisico * 0.35  # tamanho projétil = 35% do raio
        dano_por_proj = arma.dano / max(qtd, 1)
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (200, 200, 200)
        
        nome_lower = arma.nome.lower()
        if "shuriken" in nome_lower:
            tipo_proj = "shuriken"
            vel = 18.0
        elif "chakram" in nome_lower:
            tipo_proj = "chakram"
            vel = 14.0
        else:
            tipo_proj = "faca"
            vel = 16.0
        
        rad_base = math.radians(self.angulo_olhar)
        spread = 25 if qtd > 1 else 0
        
        for i in range(qtd):
            if qtd > 1:
                offset = -spread/2 + (spread / (qtd-1)) * i
            else:
                offset = 0
            
            ang = self.angulo_olhar + offset
            # Spawn BEM FORA do corpo do lutador
            spawn_dist = self.raio_fisico + 0.5
            spawn_x = self.pos[0] + math.cos(math.radians(ang)) * spawn_dist
            spawn_y = self.pos[1] + math.sin(math.radians(ang)) * spawn_dist
            
            proj = ArmaProjetil(
                tipo=tipo_proj,
                x=spawn_x, y=spawn_y,
                angulo=ang,
                dono=self,
                dano=dano_por_proj * (self.dados.forca / 2.0),
                velocidade=vel,
                tamanho=tam,
                cor=cor
            )
            self.buffer_projeteis.append(proj)
    
    def _disparar_flecha(self, alvo):
        """Dispara flecha do arco - DIRETA E PRECISA"""
        from core.combat import FlechaProjetil
        
        arma = self.dados.arma_obj
        if not arma:
            return
        
        dano = arma.dano * (self.dados.forca / 2.0 + 0.5)  # Dano base melhor
        forca = getattr(arma, 'forca_arco', 1.0)
        # Normaliza força do arco (valores no JSON são 5-50, queremos 0.5-2.0)
        forca_normalizada = max(0.5, min(2.0, forca / 25.0))
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (139, 90, 43)
        
        # === MIRA DIRETA NO ALVO (sem gravidade, sem complicação) ===
        dx = alvo.pos[0] - self.pos[0]
        dy = alvo.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        
        if dist > 0.1:
            # Velocidade da flecha
            vel_flecha = 35.0 + forca_normalizada * 20.0
            tempo_voo = dist / vel_flecha
            
            # Predição simples: 70% da velocidade do alvo
            alvo_futuro_x = alvo.pos[0] + alvo.vel[0] * tempo_voo * 0.7
            alvo_futuro_y = alvo.pos[1] + alvo.vel[1] * tempo_voo * 0.7
            
            # Mira direto no alvo (sem compensação de gravidade - flecha voa reta!)
            dx_mira = alvo_futuro_x - self.pos[0]
            dy_mira = alvo_futuro_y - self.pos[1]
            angulo_mira = math.degrees(math.atan2(dy_mira, dx_mira))
        else:
            angulo_mira = self.angulo_olhar
        
        # Imprecisão pequena (arqueiro é preciso!)
        angulo_mira += random.uniform(-2, 2)
        
        # === SPAWN DA FLECHA: Sai do CORPO do arqueiro (não do range!) ===
        # A flecha nasce na beirada do corpo do arqueiro, na direção da mira
        rad = math.radians(angulo_mira)
        spawn_dist = self.raio_fisico + 0.3  # Logo na borda do corpo + pequena folga
        spawn_x = self.pos[0] + math.cos(rad) * spawn_dist
        spawn_y = self.pos[1] + math.sin(rad) * spawn_dist
        
        flecha = FlechaProjetil(
            x=spawn_x, y=spawn_y,
            angulo=angulo_mira,
            dono=self,
            dano=dano,
            forca=forca_normalizada,
            cor=cor
        )
        self.buffer_projeteis.append(flecha)

    def _disparar_orbes(self, alvo):
        """Dispara orbes mágicos"""
        from core.combat import OrbeMagico
        
        arma = self.dados.arma_obj
        if not arma:
            return
        
        qtd = int(getattr(arma, 'quantidade', 2))
        dano_por_orbe = arma.dano / max(qtd, 1)
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (100, 100, 255)
        
        orbes_orbitando = [o for o in self.buffer_orbes if o.ativo and o.estado == "orbitando"]
        
        if orbes_orbitando:
            for orbe in orbes_orbitando[:qtd]:
                orbe.iniciar_carga(alvo)
        else:
            for i in range(qtd):
                orbe = OrbeMagico(
                    x=self.pos[0], y=self.pos[1],
                    dono=self,
                    dano=dano_por_orbe * (self.dados.forca / 2.0 + self.dados.mana / 2.0),
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
        
        # Rastreia último atacante para atribuição de kills indiretas
        if atacante is not None:
            self.ultimo_atacante = atacante
        
        # SONO: acordar ao tomar dano
        if getattr(self, 'dormindo', False):
            self.dormindo = False
            self.stun_timer = 0
        
        dano_final = dano

        if "Cavaleiro" in self.classe_nome:
            dano_final *= 0.70  # v16.0: corrigido para 30% menos dano (era 25%)

        if "Ladino" in self.classe_nome and random.random() < 0.2:
            return False

        # v16.0: Duelista — ataques nunca erram (inverte miss do atacante se for duelista)
        # (implementado como anti-miss no atacante em executar_ataques)

        if "Ninja" in self.classe_nome and random.random() < 0.10:
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

        # === v16.0: BÊNÇÃO DIVINA — modificador de defesa ===
        try:
            from core.divine import DivineBlessingManager
            divine = DivineBlessingManager.get_instance()
            dano_final = divine.aplicar_passiva_defesa(self, dano_final, atacante)
        except Exception:
            pass

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
        # BUG-18 fix v2: melee attacks passam empurrao já escalado (magnitude
        # 5-25) via calcular_knockback_com_forca — usar diretamente.
        # Vetores de direção pura (DOTs, efeitos) têm magnitude ≤ 1.5 e
        # precisam da fórmula interna de kb.
        emp_mag = math.hypot(empurrao_x, empurrao_y)
        if emp_mag > 0.01:
            if emp_mag > 1.5:
                # Melee: empurrao já escalado por calcular_knockback_com_forca
                # Bônus leve por vida baixa (até +40%)
                vida_ratio = 1.0 - (self.vida / max(self.vida_max, 1))
                bonus = 1.0 + vida_ratio * 0.4
                self.vel[0] += empurrao_x * bonus
                self.vel[1] += empurrao_y * bonus
            else:
                # Direção pura (DOT, habilidade) — aplica fórmula interna
                nx = empurrao_x / emp_mag
                ny = empurrao_y / emp_mag
                kb = 15.0 + (1.0 - (self.vida / max(self.vida_max, 1))) * 10.0
                kb += dano_final * 0.2
                self.vel[0] += nx * kb
                self.vel[1] += ny * kb
        
        self._aplicar_efeito_status(tipo_efeito)
        
        if self.vida < self.vida_max * 0.3:
            self.modo_adrenalina = True
        
        if self.vida <= 0:
            self.morrer()
            return self.morto  # False if revived by buff/skill
        return False

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
            # Corrosão: Dano + reduz defesa temporariamente
            dot = DotEffect("CORROENDO", self, 1.5 * intensidade, duracao or 4.0, (150, 100, 50))
            self.dots_ativos.append(dot)
            self.vulnerabilidade = getattr(self, 'vulnerabilidade', 1.0) * 1.25  # +25% dano recebido
            self.vulnerabilidade_timer = max(getattr(self, 'vulnerabilidade_timer', 0), duracao or 4.0)
            
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
            self.silenciado_timer = max(self.silenciado_timer, duracao or 3.0)
            
        elif efeito == "CEGO":
            # Cego: Ângulo de visão prejudicado (IA afetada)
            self.cego_timer = max(getattr(self, 'cego_timer', 0), duracao or 2.0)
            self.flash_cor = (255, 255, 200)
            self.flash_timer = 0.5
            
        elif efeito == "MEDO":
            # Medo: Força a fugir
            self.medo_timer = max(getattr(self, 'medo_timer', 0), duracao or 2.5)
            if self.brain is not None:
                self.brain.medo = 1.0  # Maximiza medo na IA
            
        elif efeito == "CHARME":
            # Charme: Inimigo te segue
            self.charme_timer = max(getattr(self, 'charme_timer', 0), duracao or 2.0)
            
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
            self.fraco_timer = max(getattr(self, 'fraco_timer', 0), duracao or 3.0)
            
        elif efeito == "VULNERAVEL":
            # Vulnerável: Dano recebido aumentado
            self.vulnerabilidade = 1.5
            # FP-3: adiciona timer para que o efeito expire
            self.vulnerabilidade_timer = max(getattr(self, 'vulnerabilidade_timer', 0), duracao or 3.0)
            
        elif efeito == "EXAUSTO":
            # Exausto: Regen de stamina/mana reduzida
            # BUG-C2: Não modificar regen_mana_base diretamente (era permanente).
            # O timer é decrementado no update() e a penalidade é aplicada condicionalmente no cálculo de mana.
            self.exausto_timer = max(getattr(self, 'exausto_timer', 0), duracao or 5.0)
            
        elif efeito == "MARCADO":
            # Marcado: Próximo ataque causa dano extra
            self.marcado = True
            
        elif efeito == "EXPOSTO":
            # Exposto: Ignora parte da defesa
            self.exposto_timer = max(getattr(self, 'exposto_timer', 0), duracao or 4.0)
        
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
        from core.hitbox import HITBOX_PROFILES
        _perfil = HITBOX_PROFILES.get(arma.tipo, HITBOX_PROFILES.get("Orbital", {}))
        _range_mult = _perfil.get("range_mult", 1.5)
        _arc = _perfil.get("base_arc", 360)
        cx, cy = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        raio_char_px = int((self.dados.tamanho / 2) * PPM)
        dist_base_px = int(raio_char_px * _range_mult * self.fator_escala)
        return (cx, cy), dist_base_px + raio_char_px, self.angulo_arma_visual, _arc
    
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
