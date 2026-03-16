"""Auto-generated mixin — see scripts/split_brain.py"""
import random
import math
import logging

_log = logging.getLogger("neural_ai")

from utils.config import PPM
from utils.config import (
    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,
    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,
    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,
    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,
    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,
    AI_RAND_POOL_SIZE,
)
from ai.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,
    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES
)
from ai.behavior_profiles import get_behavior_profile, FALLBACK_PROFILE

try:
    from core.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
    WEAPON_ANALYSIS_AVAILABLE = True
except ImportError:
    WEAPON_ANALYSIS_AVAILABLE = False

try:
    from ai.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority
    SKILL_STRATEGY_AVAILABLE = True
except ImportError:
    SKILL_STRATEGY_AVAILABLE = False

try:
    from core.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

try:
    from core.arena import get_arena as _get_arena
except ImportError:
    _get_arena = None


import re as _re_arquetipo
from models import get_class_data
from core.skills import get_skill_data
from ai.choreographer import CombatChoreographer
from ai._brain_mixin_base import _AIBrainMixinBase


class PersonalityMixin(_AIBrainMixinBase):
    """Mixin de geração e configuração de personalidade procedural."""


    # =========================================================================
    # GERAÇÃO DE PERSONALIDADE
    # =========================================================================
    
    def _gerar_personalidade(self):
        """Gera uma personalidade - usa preset se definido, ou aleatório"""
        # Verifica se o personagem tem uma personalidade preset definida
        preset_nome = getattr(self.parent.dados, 'personalidade', 'Aleatório')
        
        if preset_nome and preset_nome != 'Aleatório' and preset_nome in PERSONALIDADES_PRESETS:
            # Usa o preset definido
            self._aplicar_preset(preset_nome)
        else:
            # Gera aleatoriamente como antes
            self._gerar_personalidade_aleatoria()

    
    def _gerar_personalidade_aleatoria(self):
        """Gera uma personalidade completamente aleatória (comportamento original)"""
        self._definir_arquetipo()
        self._selecionar_estilo()
        self._selecionar_filosofia()
        self._gerar_tracos()
        self._gerar_quirks()
        self._gerar_instintos()
        self._gerar_ritmo()
        self._calcular_agressividade()
        # HIGH-06 fix: antes, personalidades aleatórias sempre recebiam FALLBACK_PROFILE
        # neutro, ignorando os 186 perfis de traços disponíveis em BEHAVIOR_PROFILES.
        # Um personagem com traço BERSERKER gerado aleatoriamente não receria o perfil
        # agressivo — ficava igual a qualquer personagem neutro.
        # Agora: tenta carregar o perfil do traço mais "forte" (prioridade: ESPECIAIS → AGRESSIVIDADE).
        self._behavior_profile = self._resolver_behavior_profile_por_tracos()
        self._categorizar_skills()
        self._aplicar_modificadores_iniciais()
        self._inicializar_skill_strategy()


    def _resolver_behavior_profile_por_tracos(self):
        """Retorna o behavior profile mais específico disponível para os traços atuais.
        HIGH-06 fix: resolve profile para personalidades aleatórias usando os traços gerados.
        Prioridade: traços especiais > traços de agressividade > traços defensivos > fallback.
        """
        if not self.tracos:
            return FALLBACK_PROFILE
        # Ordem de prioridade: especiais primeiro, depois agressivos, depois o resto
        prioridade = (
            list(TRACOS_ESPECIAIS) +
            list(TRACOS_AGRESSIVIDADE) +
            list(TRACOS_DEFENSIVO) +
            list(TRACOS_MENTAL) +
            list(TRACOS_MOBILIDADE) +
            list(TRACOS_SKILLS)
        )
        for traco in prioridade:
            if traco in self.tracos:
                profile = get_behavior_profile(traco)
                if profile is not FALLBACK_PROFILE:
                    _log.debug(
                        "[PERSONALIDADE] %s: behavior profile do traço '%s'",
                        self.parent.dados.nome if hasattr(self.parent, 'dados') else '?', traco
                    )
                    return profile
        return FALLBACK_PROFILE


    def _gerar_tracos(self):
        """Gera combinação única de traços"""
        num_tracos = random.randint(5, 7)
        
        categorias = [
            TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
            TRACOS_SKILLS, TRACOS_MENTAL,
        ]
        
        self.tracos = []
        
        for cat in categorias:
            self.tracos.append(random.choice(cat))
        
        extras_needed = num_tracos - len(self.tracos)
        todos_restantes = [t for t in TODOS_TRACOS if t not in self.tracos]
        
        if random.random() < 0.4:
            especial = random.choice(TRACOS_ESPECIAIS)
            if especial not in self.tracos:
                self.tracos.append(especial)
                extras_needed -= 1
        
        if extras_needed > 0:
            extras = random.sample(todos_restantes, min(extras_needed, len(todos_restantes)))
            self.tracos.extend(extras)
        
        self._resolver_conflitos_tracos()


    def _resolver_conflitos_tracos(self):
        """Remove traços que conflitam"""
        conflitos = [
            ("COVARDE", "BERSERKER"), ("MEDROSO", "IMPLACAVEL"),
            ("ESTATICO", "VELOZ"), ("CALCULISTA", "IMPRUDENTE"),
            ("PACIENTE", "FURIOSO"), ("FRIO", "EMOTIVO"),
            ("TEIMOSO", "ADAPTAVEL"),
        ]
        
        for t1, t2 in conflitos:
            if t1 in self.tracos and t2 in self.tracos:
                self.tracos.remove(random.choice([t1, t2]))


    def _definir_arquetipo(self):
        """Define arquétipo baseado na classe"""
        p = self.parent
        classe = p.classe_nome.lower() if p.classe_nome else ""
        
        arquetipo_map = {
            "mago": "MAGO", "piromante": "PIROMANTE", "criomante": "CRIOMANTE",
            "eletromante": "ELETROMANTE", "necromante": "INVOCADOR", "feiticeiro": "MAGO",
            "bruxo": "MAGO_CONTROLE", "assassino": "ASSASSINO", "ninja": "NINJA",
            "sombra": "SOMBRA", "berserker": "BERSERKER", "bárbaro": "BERSERKER",
            "cavaleiro": "SENTINELA", "paladino": "PALADINO", "ladino": "LADINO",
            "druida": "DRUIDA", "monge": "MONGE", "arqueiro": "ARQUEIRO",
            "caçador": "ARQUEIRO", "guerreiro": "GUERREIRO", "samurai": "SAMURAI",
            "ronin": "RONIN", "espadachim": "DUELISTA", "gladiador": "GLADIADOR",
            "guardião": "GUARDIAO", "templário": "PALADINO",
        }
        
        # MEL-AI-08 fix: usa comparação por palavras completas em vez de substring.
        # Exemplo: "mago-fogo" não deve corresponder apenas a "mago".
        # Divide o nome da classe em tokens separados por espaços e hifens.
        palavras_classe = set(_re_arquetipo.split(r'[\s\-_]+', classe))  # QC-04: usa import de nível de módulo
        
        for key, arq in arquetipo_map.items():
            if key in palavras_classe:
                self.arquetipo = arq
                break
        else:
            self._definir_arquetipo_por_arma()
        
        if self.arquetipo in ARQUETIPO_DATA:
            data = ARQUETIPO_DATA[self.arquetipo]
            p.alcance_ideal = data["alcance"]
            self.estilo_luta = data["estilo"]
            self.agressividade_base = data["agressividade"]


    def _definir_arquetipo_por_arma(self):
        """Define arquétipo pela arma se classe não mapeada - v12.2 CORRIGIDO"""
        p = self.parent
        arma = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        
        if not arma:
            self.arquetipo = "MONGE"
            p.alcance_ideal = 1.5
            return

        tipo = getattr(arma, 'tipo', '')
        peso = getattr(arma, 'peso', 5.0)
        
        # Importa perfis de hitbox para alcance preciso (QC-04: HITBOX_PROFILES já importado no módulo)
        try:
            perfil = HITBOX_PROFILES.get(tipo, HITBOX_PROFILES.get("Reta", {}))
            range_mult = perfil.get("range_mult", 2.0)
        except (KeyError, AttributeError):
            perfil = {}
            range_mult = 2.0
        
        # Calcula alcance REAL em metros: raio do personagem * multiplicador da arma
        raio = p.raio_fisico if hasattr(p, 'raio_fisico') else 0.4
        alcance_max = raio * range_mult
        
        # Define arquétipo e alcance IDEAL (onde a IA quer ficar)
        if "Orbital" in tipo:
            self.arquetipo = "SENTINELA"
            # Orbitais: fica bem perto para os orbes acertarem
            p.alcance_ideal = alcance_max * 0.8
            
        elif "Arco" in tipo:
            self.arquetipo = "ARQUEIRO"
            # Arco tem range_mult = 20.0, então alcance_max = raio * 20 = ~8.5m
            # Arqueiro quer ficar BEM LONGE - usa 60% do alcance máximo
            # Isso coloca ele a ~5m do inimigo, seguro mas efetivo
            p.alcance_ideal = alcance_max * 0.6
            p.alcance_efetivo = alcance_max  # Pode acertar em todo o alcance
            
        elif "Mágica" in tipo or "Cajado" in tipo:
            self.arquetipo = "MAGO"
            # Mago: distância média para skills
            p.alcance_ideal = alcance_max * 0.7
            
        elif "Corrente" in tipo:
            estilo_arma = getattr(arma, 'estilo', '')
            min_range_ratio = perfil.get("min_range_ratio", 0.25)
            zona_morta = alcance_max * min_range_ratio
            
            if estilo_arma == "Mangual":
                # v3.0 Mangual: zona morta 40%, spin zone 40-72% do alcance
                # Zona morta grande, mas tem bônus quando acumula momentum
                self.arquetipo = "BERSERKER"  # Mangual é um Berserker de corrente
                # Alcance ideal = ponto de spin máximo (55% do alcance máximo)
                p.alcance_ideal = alcance_max * 0.55
                p.zona_morta_mangual = zona_morta  # Salva para uso na IA
                p.mangual_momentum = 0.0            # Estado de momentum acumulado
            else:
                self.arquetipo = "ACROBATA"
                # Outras correntes: meio termo entre zona morta e máximo
                p.alcance_ideal = (alcance_max + zona_morta) / 2
            
        elif "Arremesso" in tipo:
            self.arquetipo = "LANCEIRO"
            # Arremesso: mantém distância segura mas não muito longe
            p.alcance_ideal = alcance_max * 0.5
            
        elif "Dupla" in tipo:
            self.arquetipo = "ASSASSINO"
            estilo_arma = getattr(arma, 'estilo', '')
            if estilo_arma == "Adagas Gêmeas":
                # v3.1: Adagas têm lâminas longas — combate próximo mas não colado
                # Range ideal é 70% do alcance max: perto suficiente para o combo,
                # longe suficiente para ter tempo de reagir/esquivar
                p.alcance_ideal = alcance_max * 0.70
                p.alcance_agressao = alcance_max * 0.85  # começa a pressionar aqui
            else:
                # Outras armas duplas: perto mas não tão colado
                p.alcance_ideal = alcance_max * 0.70
            
        elif "Transformável" in tipo:
            self.arquetipo = "GUERREIRO"
            # Transformável: distância média (adapta-se)
            p.alcance_ideal = alcance_max * 0.8
            
        elif "Reta" in tipo:
            # Define arquétipo pelo peso
            if peso > 10.0:
                self.arquetipo = "COLOSSO"
                p.alcance_ideal = alcance_max * 0.9  # Pesadas = mais perto
            elif peso < 2.5:
                self.arquetipo = "DUELISTA"
                p.alcance_ideal = alcance_max * 0.75
            elif peso > 6.0:
                self.arquetipo = "GUERREIRO_PESADO"
                p.alcance_ideal = alcance_max * 0.85
            else:
                self.arquetipo = "GUERREIRO"
                p.alcance_ideal = alcance_max * 0.8
        else:
            # Fallback
            if peso > 10.0:
                self.arquetipo = "COLOSSO"
            elif peso < 2.5:
                self.arquetipo = "DUELISTA"
            elif peso > 6.0:
                self.arquetipo = "GUERREIRO_PESADO"
            else:
                self.arquetipo = "GUERREIRO"
            p.alcance_ideal = alcance_max * 0.8
        
        # Garante alcance mínimo razoável
        p.alcance_ideal = max(0.8, p.alcance_ideal)


    def _selecionar_estilo(self):
        """Seleciona estilo de luta"""
        if random.random() < 0.7:
            return
        
        estilos_alternativos = {
            "MAGO": ["BURST", "CONTROL", "KITE"],
            "ASSASSINO": ["AMBUSH", "COMBO", "OPPORTUNIST"],
            "GUERREIRO": ["AGGRO", "COUNTER", "TANK"],
            "ARQUEIRO": ["RANGED", "MOBILE", "POKE"],
            "BERSERKER": ["AGGRO", "BURST", "BERSERK"],
        }
        
        if self.arquetipo in estilos_alternativos:
            self.estilo_luta = random.choice(estilos_alternativos[self.arquetipo])
        else:
            self.estilo_luta = random.choice(list(ESTILOS_LUTA.keys()))


    def _selecionar_filosofia(self):
        """Seleciona filosofia de combate"""
        filosofias_por_estilo = {
            "BERSERK": ["DOMINACAO", "PRESSAO", "EXECUCAO"],
            "TANK": ["RESISTENCIA", "SOBREVIVENCIA", "EQUILIBRIO"],
            "KITE": ["SOBREVIVENCIA", "PACIENCIA", "OPORTUNISMO"],
            "BURST": ["EXECUCAO", "OPORTUNISMO", "DOMINACAO"],
            "COUNTER": ["PACIENCIA", "OPORTUNISMO", "EQUILIBRIO"],
        }
        
        if self.estilo_luta in filosofias_por_estilo:
            self.filosofia = random.choice(filosofias_por_estilo[self.estilo_luta])
        else:
            self.filosofia = random.choice(list(FILOSOFIAS.keys()))


    def _gerar_quirks(self):
        """Gera quirks únicos"""
        num_quirks = random.randint(1, 3)
        
        quirks_por_traco = {
            "BERSERKER": ["FURIA_CEGA", "GRITO_GUERRA"],
            "VINGATIVO": ["OLHO_VERMELHO", "PERSISTENTE"],
            "ASSASSINO_NATO": ["FINALIZADOR", "CONTRA_ATAQUE_PERFEITO"],
            "PHOENIX": ["SEGUNDO_FOLEGO", "EXPLOSAO_FINAL"],
            "VAMPIRO": ["VAMPIRICO", "SEDE_SANGUE"],
            "SHOWMAN": ["PROVOCADOR", "DANCA_MORTE"],
            "EVASIVO": ["ESQUIVA_REFLEXA", "INSTINTO_ANIMAL"],
            "PACIENTE": ["PACIENCIA_INFINITA", "CALCULISTA_FRIO"],
        }
        
        self.quirks = []
        
        for traco in self.tracos:
            if traco in quirks_por_traco and random.random() < 0.5:
                quirk = random.choice(quirks_por_traco[traco])
                if quirk not in self.quirks:
                    self.quirks.append(quirk)
        
        while len(self.quirks) < num_quirks:
            quirk = random.choice(list(QUIRKS.keys()))
            if quirk not in self.quirks:
                self.quirks.append(quirk)

    
    def _gerar_instintos(self):
        """Gera instintos aleatórios para a IA"""
        num_instintos = random.randint(2, 4)
        self.instintos = random.sample(list(INSTINTOS.keys()), min(num_instintos, len(INSTINTOS)))

    
    def _gerar_ritmo(self):
        """Seleciona um ritmo de batalha aleatório"""
        # Alguns ritmos são mais raros
        ritmos_comuns = ["ONDAS", "RESPIRACAO", "CONSTANTE", "PREDADOR"]
        ritmos_raros = ["TEMPESTADE", "BERSERKER", "CAOTICO", "ESCALADA"]
        
        if random.random() < 0.3:
            self.ritmo = random.choice(ritmos_raros)
        else:
            self.ritmo = random.choice(ritmos_comuns)
        
        self.ritmo_fase_atual = 0
        self.ritmo_timer = 0.0


    def _calcular_agressividade(self):
        """Calcula agressividade final"""
        agg = self.agressividade_base
        
        if self.filosofia in FILOSOFIAS:
            agg += FILOSOFIAS[self.filosofia]["mod_agressividade"]
        
        tracos_agressivos = ["IMPRUDENTE", "AGRESSIVO", "BERSERKER", "SANGUINARIO", 
                           "PREDADOR", "SELVAGEM", "IMPLACAVEL", "FURIOSO", "BRUTAL"]
        tracos_defensivos = ["COVARDE", "CAUTELOSO", "PACIENTE", "PARANOICO", 
                           "MEDROSO", "PRUDENTE", "EVASIVO"]
        
        for traco in self.tracos:
            if traco in tracos_agressivos:
                agg += 0.08
            elif traco in tracos_defensivos:
                agg -= 0.06
        
        self.agressividade_base = max(0.1, min(0.95, agg))


    def _aplicar_modificadores_iniciais(self):
        """Aplica modificadores baseados na personalidade"""
        p = self.parent
        
        if "IMPRUDENTE" in self.tracos:
            p.alcance_ideal *= 0.7
            self.confianca = 0.8
        if "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
            p.alcance_ideal *= 1.3
            self.medo = 0.2
        if "AGRESSIVO" in self.tracos:
            p.alcance_ideal *= 0.85
        if "CAUTELOSO" in self.tracos or "PRUDENTE" in self.tracos:
            p.alcance_ideal *= 1.2
        if "BERSERKER" in self.tracos:
            self.raiva = 0.3
        if "FURIOSO" in self.tracos:
            self.raiva = 0.4
        if "FRIO" in self.tracos:
            self.medo = 0.0
            self.raiva = 0.0

    
    def _aplicar_preset(self, preset_nome):
        """Aplica um preset de personalidade"""
        preset = PERSONALIDADES_PRESETS[preset_nome]
        
        # Define arquétipo baseado na classe primeiro
        self._definir_arquetipo()
        
        # Aplica estilo fixo se definido
        if preset["estilo_fixo"]:
            self.estilo_luta = preset["estilo_fixo"]
        else:
            self._selecionar_estilo()
        
        # Aplica filosofia fixa se definida
        if preset["filosofia_fixa"]:
            self.filosofia = preset["filosofia_fixa"]
        else:
            self._selecionar_filosofia()
        
        # Aplica traços fixos + alguns aleatórios
        self.tracos = list(preset["tracos_fixos"])
        # Adiciona 1-2 traços aleatórios para variedade
        tracos_extras = random.randint(1, 2)
        tracos_disponiveis = [t for t in TODOS_TRACOS if t not in self.tracos]
        self.tracos.extend(random.sample(tracos_disponiveis, min(tracos_extras, len(tracos_disponiveis))))
        
        # Aplica quirks fixos + chance de um extra aleatório
        self.quirks = list(preset["quirks_fixos"])
        if random.random() < 0.3 and len(self.quirks) < 3:
            quirks_disponiveis = [q for q in QUIRKS.keys() if q not in self.quirks]
            if quirks_disponiveis:
                self.quirks.append(random.choice(quirks_disponiveis))
        
        # === NOVOS SISTEMAS v11.0 ===
        # Aplica instintos do preset + alguns aleatórios
        self.instintos = list(preset.get("instintos_fixos", []))
        if random.random() < 0.4:
            instintos_disponiveis = [i for i in INSTINTOS.keys() if i not in self.instintos]
            if instintos_disponiveis:
                self.instintos.append(random.choice(instintos_disponiveis))
        
        # Aplica ritmo do preset ou seleciona aleatoriamente
        ritmo_fixo = preset.get("ritmo_fixo")
        if ritmo_fixo and ritmo_fixo in RITMOS:
            self.ritmo = ritmo_fixo
        else:
            self.ritmo = random.choice(list(RITMOS.keys()))
        self.ritmo_fase_atual = 0
        self.ritmo_timer = 0.0
        
        # Calcula agressividade com modificador do preset
        self._calcular_agressividade()
        self.agressividade_base = max(0.0, min(1.0, self.agressividade_base + preset["agressividade_mod"]))
        
        # Load behavior profile for this preset
        self._behavior_profile = get_behavior_profile(preset_nome)

        # Categoriza skills e aplica modificadores
        self._categorizar_skills()
        self._aplicar_modificadores_iniciais()
        self._inicializar_skill_strategy()


    def _categorizar_skills(self):
        """Categoriza todas as skills disponíveis (expandido para todos os tipos)"""
        p = self.parent
        # HIGH-07 fix: antes, a verificação de duplicata usava nome != p.skill_arma_nome
        # (só checava contra a primeira skill legacy). Skills de classe com o mesmo
        # nome de uma skill de arma podiam entrar duplicadas, causando gasto duplo de mana.
        # Agora: conjunto global de nomes já adicionados, checado antes de cada inserção.
        _nomes_adicionados = set()

        # Skills da arma (legado)
        if hasattr(p, 'skill_arma_nome') and p.skill_arma_nome and p.skill_arma_nome != "Nenhuma":
            data = get_skill_data(p.skill_arma_nome)
            self._adicionar_skill(p.skill_arma_nome, data, "arma")
            _nomes_adicionados.add(p.skill_arma_nome)

        # Skills da arma (novo sistema com lista)
        for skill_info in getattr(p, 'skills_arma', []):
            nome = skill_info.get("nome", "Nenhuma")
            if nome != "Nenhuma" and nome not in _nomes_adicionados:
                data = skill_info.get("data", get_skill_data(nome))
                self._adicionar_skill(nome, data, "arma")
                _nomes_adicionados.add(nome)

        # Skills da classe
        if hasattr(p, 'classe_nome') and p.classe_nome:
            class_data = get_class_data(p.classe_nome)
            for skill_nome in class_data.get("skills_afinidade", []):
                if skill_nome not in _nomes_adicionados:
                    data = get_skill_data(skill_nome)
                    self._adicionar_skill(skill_nome, data, "classe")
                    _nomes_adicionados.add(skill_nome)

        # Skills da classe (novo sistema com lista)
        for skill_info in getattr(p, 'skills_classe', []):
            nome = skill_info.get("nome", "Nenhuma")
            if nome != "Nenhuma" and nome not in _nomes_adicionados:
                data = skill_info.get("data", get_skill_data(nome))
                self._adicionar_skill(nome, data, "classe")
                _nomes_adicionados.add(nome)


    def _adicionar_skill(self, nome, data, fonte):
        """Adiciona skill à lista categorizada"""
        tipo = data.get("tipo", "NADA")
        if tipo == "NADA" or tipo not in self.skills_por_tipo:
            return
        
        info = {
            "nome": nome, "data": data, "fonte": fonte,
            "tipo": tipo, "custo": data.get("custo", 15),
        }
        self.skills_por_tipo[tipo].append(info)

    
    def _inicializar_skill_strategy(self):
        """Inicializa o sistema de estratégia de skills"""
        if SKILL_STRATEGY_AVAILABLE:
            self.skill_strategy = SkillStrategySystem(self.parent, self)
            
            # Ajusta estratégia baseado na arma
            if hasattr(self.parent.dados, 'arma_obj') and self.parent.dados.arma_obj:
                arma = self.parent.dados.arma_obj
                alcance_arma = getattr(arma, 'alcance', 2.0)
                vel_arma = getattr(arma, 'velocidade_ataque', 1.0)
                self.skill_strategy.ajustar_para_arma(alcance_arma, vel_arma)
                
                # Log do perfil estratégico
                # QC-02: usa logger estruturado (nível DEBUG, silencioso em produção)
                _log.debug(
                    "[IA] %s: Role=%s, Skills=%d, Combos=%d",
                    self.parent.dados.nome,
                    self.skill_strategy.role_principal.value,
                    len(self.skill_strategy.todas_skills),
                    len(self.skill_strategy.combos_disponiveis),
                )
        else:
            self.skill_strategy = None
