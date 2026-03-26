"""Auto-generated mixin â€” see scripts/split_brain.py"""
import random
import math
import logging

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
from ia.behavior_profiles import get_behavior_profile, FALLBACK_PROFILE
from ia.weapon_ai import obter_metricas_arma, resolver_familia_arma
from nucleo.armas import resolver_subtipo_orbital

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

try:
    from nucleo.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

try:
    from nucleo.arena import get_arena as _get_arena
except ImportError:
    _get_arena = None


import re as _re_arquetipo
from modelos import get_class_data
from nucleo.skills import get_skill_data
from ia.choreographer import CombatChoreographer
from ia._brain_mixin_base import _AIBrainMixinBase


class PersonalityMixin(_AIBrainMixinBase):
    """Mixin de geraÃ§Ã£o e configuraÃ§Ã£o de personalidade procedural."""


    # =========================================================================
    # GERAÃ‡ÃƒO DE PERSONALIDADE
    # =========================================================================
    
    def _gerar_personalidade(self):
        """Gera uma personalidade - usa preset se definido, ou aleatÃ³rio"""
        # Verifica se o personagem tem uma personalidade preset definida
        preset_nome = getattr(self.parent.dados, 'personalidade', 'AleatÃ³rio')
        
        if preset_nome and preset_nome != 'AleatÃ³rio' and preset_nome in PERSONALIDADES_PRESETS:
            # Usa o preset definido
            self._aplicar_preset(preset_nome)
        else:
            # Gera aleatoriamente como antes
            self._gerar_personalidade_aleatoria()

    
    def _gerar_personalidade_aleatoria(self):
        """Gera uma personalidade completamente aleatÃ³ria (comportamento original)"""
        self._definir_arquetipo()
        self._selecionar_estilo()
        self._selecionar_filosofia()
        self._gerar_tracos()
        self._gerar_quirks()
        self._gerar_instintos()
        self._gerar_ritmo()
        self._calcular_agressividade()
        # HIGH-06 fix: antes, personalidades aleatÃ³rias sempre recebiam FALLBACK_PROFILE
        # neutro, ignorando os 186 perfis de traÃ§os disponÃ­veis em BEHAVIOR_PROFILES.
        # Um personagem com traÃ§o BERSERKER gerado aleatoriamente nÃ£o receria o perfil
        # agressivo â€” ficava igual a qualquer personagem neutro.
        # Agora: tenta carregar o perfil do traÃ§o mais "forte" (prioridade: ESPECIAIS â†’ AGRESSIVIDADE).
        self._behavior_profile = self._resolver_behavior_profile_por_tracos()
        self._categorizar_skills()
        self._aplicar_modificadores_iniciais()
        self._inicializar_skill_strategy()


    def _resolver_behavior_profile_por_tracos(self):
        """Retorna o behavior profile mais especÃ­fico disponÃ­vel para os traÃ§os atuais.
        HIGH-06 fix: resolve profile para personalidades aleatÃ³rias usando os traÃ§os gerados.
        Prioridade: traÃ§os especiais > traÃ§os de agressividade > traÃ§os defensivos > fallback.
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
                        "[PERSONALIDADE] %s: behavior profile do traÃ§o '%s'",
                        self.parent.dados.nome if hasattr(self.parent, 'dados') else '?', traco
                    )
                    return profile
        return FALLBACK_PROFILE


    def _gerar_tracos(self):
        """Gera combinaÃ§Ã£o Ãºnica de traÃ§os"""
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
        """Remove traÃ§os que conflitam"""
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
        """Define arquÃ©tipo baseado na classe"""
        p = self.parent
        classe = p.classe_nome.lower() if p.classe_nome else ""
        
        arquetipo_map = {
            "mago": "MAGO", "piromante": "PIROMANTE", "criomante": "CRIOMANTE",
            "eletromante": "ELETROMANTE", "necromante": "INVOCADOR", "feiticeiro": "MAGO",
            "bruxo": "MAGO_CONTROLE", "assassino": "ASSASSINO", "ninja": "NINJA",
            "sombra": "SOMBRA", "berserker": "BERSERKER", "bÃ¡rbaro": "BERSERKER",
            "cavaleiro": "SENTINELA", "paladino": "PALADINO", "ladino": "LADINO",
            "druida": "DRUIDA", "monge": "MONGE", "arqueiro": "ARQUEIRO",
            "caÃ§ador": "ARQUEIRO", "guerreiro": "GUERREIRO", "samurai": "SAMURAI",
            "ronin": "RONIN", "espadachim": "DUELISTA", "gladiador": "GLADIADOR",
            "guardiÃ£o": "GUARDIAO", "templÃ¡rio": "PALADINO",
        }
        
        # MEL-AI-08 fix: usa comparaÃ§Ã£o por palavras completas em vez de substring.
        # Exemplo: "mago-fogo" nÃ£o deve corresponder apenas a "mago".
        # Divide o nome da classe em tokens separados por espaÃ§os e hifens.
        palavras_classe = set(_re_arquetipo.split(r'[\s\-_]+', classe))  # QC-04: usa import de nÃ­vel de mÃ³dulo
        
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
        """Define arquÃ©tipo pela arma se classe nÃ£o mapeada - v12.2 CORRIGIDO"""
        p = self.parent
        arma = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        
        if not arma:
            self.arquetipo = "MONGE"
            p.alcance_ideal = 1.5
            return

        tipo = getattr(arma, 'tipo', '')
        peso = getattr(arma, 'peso', 5.0)
        familia = resolver_familia_arma(arma)
        metricas = obter_metricas_arma(arma, p)
        alcance_max = metricas["alcance_max"]
        alcance_min = metricas["alcance_min"]
        alcance_tatico = metricas["alcance_tatico"]

        # Define arquÃ©tipo e alcance IDEAL (onde a IA quer ficar)
        if familia == "orbital":
            subtipo_orbital = resolver_subtipo_orbital(arma)
            if subtipo_orbital == "escudo":
                self.arquetipo = "BALUARTE_ORBITAL"
                p.alcance_ideal = max(1.15, min(2.0, alcance_tatico))
            elif subtipo_orbital == "drone":
                self.arquetipo = "ARTILHEIRO_ORBITAL"
                p.alcance_ideal = max(1.6, alcance_tatico)
            elif subtipo_orbital == "laminas":
                self.arquetipo = "DANCARINO_ASTRAL"
                p.alcance_ideal = max(1.3, alcance_tatico * 0.92)
            else:
                self.arquetipo = "MAESTRO_ASTRAL"
                p.alcance_ideal = max(1.5, alcance_tatico)

        elif familia == "disparo":
            self.arquetipo = "ARQUEIRO"
            p.alcance_ideal = max(alcance_min + 0.6, alcance_max * 0.62)
            p.alcance_efetivo = alcance_max

        elif familia == "foco" or "Cajado" in tipo:
            self.arquetipo = "MAGO"
            p.alcance_ideal = max(alcance_min + 0.4, alcance_tatico)

        elif familia == "corrente":
            estilo_arma = getattr(arma, 'estilo', '')
            zona_morta = max(alcance_min, alcance_max * 0.30)

            if estilo_arma == "Mangual":
                self.arquetipo = "BERSERKER"
                p.alcance_ideal = max(zona_morta + 0.2, alcance_max * 0.55)
                p.zona_morta_mangual = zona_morta
                p.mangual_momentum = 0.0
            else:
                self.arquetipo = "ACROBATA"
                p.alcance_ideal = alcance_tatico

        elif familia == "arremesso":
            self.arquetipo = "LANCEIRO"
            p.alcance_ideal = max(alcance_min + 0.5, alcance_tatico)

        elif familia == "dupla":
            self.arquetipo = "ASSASSINO"
            estilo_arma = getattr(arma, 'estilo', '')
            if estilo_arma == "Adagas GÃªmeas":
                p.alcance_ideal = alcance_max * 0.70
                p.alcance_agressao = alcance_max * 0.85
            else:
                p.alcance_ideal = alcance_max * 0.70

        elif familia == "hibrida":
            self.arquetipo = "GUERREIRO"
            p.alcance_ideal = alcance_tatico

        elif familia == "haste":
            self.arquetipo = "GUERREIRO"
            p.alcance_ideal = max(alcance_min + 0.2, alcance_max * 0.86)

        elif familia == "lamina":
            # Define arquÃ©tipo pelo peso
            if peso > 10.0:
                self.arquetipo = "COLOSSO"
                p.alcance_ideal = alcance_max * 0.9
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
            p.alcance_ideal = alcance_tatico
        
        # Garante alcance mÃ­nimo razoÃ¡vel
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
        """Gera quirks Ãºnicos"""
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
        """Gera instintos aleatÃ³rios para a IA"""
        num_instintos = random.randint(2, 4)
        self.instintos = random.sample(list(INSTINTOS.keys()), min(num_instintos, len(INSTINTOS)))

    
    def _gerar_ritmo(self):
        """Seleciona um ritmo de batalha aleatÃ³rio"""
        # Alguns ritmos sÃ£o mais raros
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
        
        # Define arquÃ©tipo baseado na classe primeiro
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
        
        # Aplica traÃ§os fixos + alguns aleatÃ³rios
        self.tracos = list(preset["tracos_fixos"])
        # Adiciona 1-2 traÃ§os aleatÃ³rios para variedade
        tracos_extras = random.randint(1, 2)
        tracos_disponiveis = [t for t in TODOS_TRACOS if t not in self.tracos]
        self.tracos.extend(random.sample(tracos_disponiveis, min(tracos_extras, len(tracos_disponiveis))))
        
        # Aplica quirks fixos + chance de um extra aleatÃ³rio
        self.quirks = list(preset["quirks_fixos"])
        if random.random() < 0.3 and len(self.quirks) < 3:
            quirks_disponiveis = [q for q in QUIRKS.keys() if q not in self.quirks]
            if quirks_disponiveis:
                self.quirks.append(random.choice(quirks_disponiveis))
        
        # === NOVOS SISTEMAS v11.0 ===
        # Aplica instintos do preset + alguns aleatÃ³rios
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
        """Categoriza todas as skills disponÃ­veis (expandido para todos os tipos)"""
        p = self.parent
        # HIGH-07 fix: antes, a verificaÃ§Ã£o de duplicata usava nome != p.skill_arma_nome
        # (sÃ³ checava contra a primeira skill legacy). Skills de classe com o mesmo
        # nome de uma skill de arma podiam entrar duplicadas, causando gasto duplo de mana.
        # Agora: conjunto global de nomes jÃ¡ adicionados, checado antes de cada inserÃ§Ã£o.
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
        """Adiciona skill Ã  lista categorizada"""
        tipo = data.get("tipo", "NADA")
        if tipo == "NADA" or tipo not in self.skills_por_tipo:
            return
        
        info = {
            "nome": nome, "data": data, "fonte": fonte,
            "tipo": tipo, "custo": data.get("custo", 15),
        }
        self.skills_por_tipo[tipo].append(info)

    
    def _inicializar_skill_strategy(self):
        """Inicializa o sistema de estratÃ©gia de skills"""
        if SKILL_STRATEGY_AVAILABLE:
            self.skill_strategy = SkillStrategySystem(self.parent, self)
            
            # Ajusta estratÃ©gia baseado na arma
            if hasattr(self.parent.dados, 'arma_obj') and self.parent.dados.arma_obj:
                arma = self.parent.dados.arma_obj
                alcance_arma = obter_metricas_arma(arma, self.parent)["alcance_tatico"]
                if WEAPON_ANALYSIS_AVAILABLE:
                    try:
                        perfil = get_weapon_profile(arma)
                    except Exception:
                        perfil = None
                    if perfil:
                        alcance_arma = max(
                            alcance_arma,
                            getattr(perfil, 'alcance_maximo', 2.0),
                        )
                vel_arma = getattr(arma, 'velocidade_ataque', 1.0)
                self.skill_strategy.ajustar_para_arma(alcance_arma, vel_arma)
                self._ajustar_skill_strategy_por_personalidade_e_arma(
                    resolver_familia_arma(arma),
                    alcance_arma,
                )
                
                # Log do perfil estratÃ©gico
                # QC-02: usa logger estruturado (nÃ­vel DEBUG, silencioso em produÃ§Ã£o)
                _log.debug(
                    "[IA] %s: Role=%s, Skills=%d, Combos=%d",
                    self.parent.dados.nome,
                    self.skill_strategy.role_principal.value,
                    len(self.skill_strategy.todas_skills),
                    len(self.skill_strategy.combos_disponiveis),
                )
        else:
            self.skill_strategy = None

    def _ajustar_skill_strategy_por_personalidade_e_arma(self, familia, alcance_arma):
        """Afina o plano de skills conforme a família da arma e os traços ativos."""
        strategy = self.skill_strategy
        if strategy is None:
            return

        plano = strategy.plano

        if familia == "foco":
            plano.distancia_preferida = max(plano.distancia_preferida, alcance_arma * 0.90)
            if "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos or "PRUDENTE" in self.tracos:
                plano.estilo = "kite"
                plano.foco_mana = "conserve"
            elif "BERSERKER" in self.tracos or "FURIOSO" in self.tracos:
                plano.estilo = "aggressive"
                plano.foco_mana = "spam"
            elif "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
                plano.estilo = "balanced"
                plano.foco_mana = "spam"
            else:
                plano.estilo = "kite" if plano.estilo == "balanced" else plano.estilo

        elif familia == "orbital":
            plano.distancia_preferida = max(2.2, min(alcance_arma, max(plano.distancia_preferida, alcance_arma * 0.96)))
            if "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos:
                plano.estilo = "balanced"
                plano.foco_mana = "conserve"
            elif "BERSERKER" in self.tracos or "AGRESSIVO" in self.tracos:
                plano.estilo = "aggressive"
                plano.foco_mana = "balanced"

        elif familia == "hibrida":
            plano.distancia_preferida = max(2.1, min(alcance_arma, max(plano.distancia_preferida, alcance_arma * 0.84)))
            if "CALCULISTA" in self.tracos or "ADAPTAVEL" in self.tracos:
                plano.estilo = "balanced"
                plano.foco_mana = "balanced"
            elif "BERSERKER" in self.tracos or "IMPRUDENTE" in self.tracos:
                plano.estilo = "aggressive"
                plano.foco_mana = "spam"

        elif familia == "corrente":
            if "ACROBATA" in self.tracos or "FLANQUEADOR" in self.tracos:
                plano.estilo = "aggressive"
            elif "PACIENTE" in self.tracos or "CALCULISTA" in self.tracos:
                plano.estilo = "balanced"

        strategy.preferencias["distancia_preferida"] = plano.distancia_preferida
        strategy.preferencias["estilo_kite"] = plano.estilo == "kite"

