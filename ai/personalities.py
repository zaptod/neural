"""
=============================================================================
NEURAL FIGHTS - Personalidades da IA
=============================================================================
Sistema de personalidade procedural com CENTENAS de combinações:
- 50+ Traços de personalidade
- 25+ Arquétipos de combate  
- 15+ Estilos de luta
- 20+ Quirks (comportamentos únicos)
- 10+ Filosofias de combate
- Sistema de humor dinâmico
=============================================================================
"""

# =============================================================================
# TRAÇOS DE PERSONALIDADE (50+)
# =============================================================================

TRACOS_AGRESSIVIDADE = [
    "IMPRUDENTE",      # Ignora defesa completamente
    "AGRESSIVO",       # Prefere sempre atacar
    "BERSERKER",       # Mais forte com menos HP
    "OPORTUNISTA",     # Ataca quando inimigo erra
    "SANGUINARIO",     # Não para até matar
    "PREDADOR",        # Persegue alvos feridos
    "SELVAGEM",        # Ataques frenéticos
    "IMPLACAVEL",      # Nunca recua voluntariamente
    "FURIOSO",         # Raiva constante
    "BRUTAL",          # Prefere golpes pesados
]

TRACOS_DEFENSIVO = [
    "COVARDE",         # Foge com HP baixo
    "CAUTELOSO",       # Mantém distância segura
    "PACIENTE",        # Espera oportunidades
    "REATIVO",         # Contra-ataca
    "TANQUE",          # Absorve dano
    "PROTETOR",        # Defende área
    "EVASIVO",         # Esquiva muito
    "PARANOICO",       # Sempre esperando ataque
    "MEDROSO",         # Medo constante
    "PRUDENTE",        # Calcula riscos
]

TRACOS_MOBILIDADE = [
    "SALTADOR",        # Pula frequentemente
    "ACROBATA",        # Usa dash muito
    "ERRATICO",        # Movimentos imprevisíveis
    "FLANQUEADOR",     # Ataca pelos lados
    "PERSEGUIDOR",     # Não deixa fugir
    "VELOZ",           # Sempre se movendo
    "ESTATICO",        # Prefere ficar parado
    "DESLIZANTE",      # Move suavemente
    "TELEGRAFICO",     # Movimentos previsíveis
    "CAOTICO",         # Direções aleatórias
]

TRACOS_SKILLS = [
    "SPAMMER",         # Usa skills frequentemente
    "CALCULISTA",      # Usa skills estrategicamente
    "CONSERVADOR",     # Economiza mana
    "EXPLOSIVO",       # Salva skills para burst
    "COMBO_MASTER",    # Encadeia skills
    "SNIPER",          # Skills de longa distância
    "CLOSE_RANGE",     # Skills corpo a corpo
    "AREA_DENIAL",     # Controla espaço
    "DEBUFFER",        # Foca em status
    "SUPPORT",         # Buffs próprios
]

TRACOS_MENTAL = [
    "VINGATIVO",       # Raiva aumenta com dano
    "DETERMINADO",     # Não desiste nunca
    "ADAPTAVEL",       # Muda estratégia
    "FRIO",            # Emoções não afetam
    "EMOTIVO",         # Emoções extremas
    "FOCADO",          # Ignora distrações
    "DISPERSO",        # Muda alvo facilmente
    "TEIMOSO",         # Mantém estratégia
    "CRIATIVO",        # Tenta coisas novas
    "METODICO",        # Padrões repetitivos
]

TRACOS_ESPECIAIS = [
    "SHOWMAN",         # Faz poses dramáticas
    "ASSASSINO_NATO",  # Executa com precisão
    "BERSERKER_RAGE",  # Modo fúria quando crítico
    "PHOENIX",         # Mais forte perto da morte
    "VAMPIRO",         # Foca em drenar vida
    "KAMIKAZE",        # Ignora própria vida
    "TRICKSTER",       # Engana o oponente
    "HONORAVEL",       # Luta "justo"
    "COVARDE_TATICO",  # Foge estrategicamente
    "ULTIMO_SUSPIRO",  # Burst final quando morrendo
]

# Todos os traços combinados
TODOS_TRACOS = (TRACOS_AGRESSIVIDADE + TRACOS_DEFENSIVO + TRACOS_MOBILIDADE + 
                TRACOS_SKILLS + TRACOS_MENTAL + TRACOS_ESPECIAIS)


# =============================================================================
# ARQUÉTIPOS DE COMBATE (25+)
# =============================================================================

ARQUETIPO_DATA = {
    # === MAGOS ===
    "MAGO": {"alcance": 7.0, "estilo": "RANGED", "agressividade": 0.3},
    "MAGO_AGRESSIVO": {"alcance": 5.0, "estilo": "RANGED", "agressividade": 0.7},
    "MAGO_CONTROLE": {"alcance": 6.0, "estilo": "RANGED", "agressividade": 0.4},
    "INVOCADOR": {"alcance": 6.0, "estilo": "SUMMON", "agressividade": 0.3},
    "PIROMANTE": {"alcance": 5.0, "estilo": "BURST", "agressividade": 0.8},
    "CRIOMANTE": {"alcance": 6.0, "estilo": "CONTROL", "agressividade": 0.4},
    "ELETROMANTE": {"alcance": 5.5, "estilo": "COMBO", "agressividade": 0.6},
    
    # === ASSASSINOS ===
    "ASSASSINO": {"alcance": 2.0, "estilo": "BURST", "agressividade": 0.8},
    "NINJA": {"alcance": 2.5, "estilo": "HIT_RUN", "agressividade": 0.7},
    "LADINO": {"alcance": 3.0, "estilo": "OPPORTUNIST", "agressividade": 0.6},
    "SOMBRA": {"alcance": 2.0, "estilo": "AMBUSH", "agressividade": 0.9},
    
    # === GUERREIROS ===
    "GUERREIRO": {"alcance": 2.5, "estilo": "BALANCED", "agressividade": 0.5},
    "GUERREIRO_PESADO": {"alcance": 2.0, "estilo": "TANK", "agressividade": 0.4},
    "BERSERKER": {"alcance": 1.5, "estilo": "BERSERK", "agressividade": 0.9},
    "DUELISTA": {"alcance": 2.0, "estilo": "COUNTER", "agressividade": 0.5},
    "GLADIADOR": {"alcance": 2.0, "estilo": "SHOWMAN", "agressividade": 0.6},
    
    # === DEFENSIVOS ===
    "SENTINELA": {"alcance": 2.5, "estilo": "TANK", "agressividade": 0.3},
    "PALADINO": {"alcance": 2.5, "estilo": "BALANCED", "agressividade": 0.4},
    "COLOSSO": {"alcance": 2.0, "estilo": "TANK", "agressividade": 0.5},
    "GUARDIAO": {"alcance": 2.0, "estilo": "DEFENSIVE", "agressividade": 0.2},
    
    # === HÍBRIDOS ===
    "LANCEIRO": {"alcance": 4.0, "estilo": "POKE", "agressividade": 0.5},
    "ARQUEIRO": {"alcance": 7.0, "estilo": "KITE", "agressividade": 0.4},
    "ACROBATA": {"alcance": 3.5, "estilo": "MOBILE", "agressividade": 0.6},  # Corrente tem alcance maior
    "MONGE": {"alcance": 1.5, "estilo": "COMBO", "agressividade": 0.6},
    "DRUIDA": {"alcance": 5.0, "estilo": "ADAPTIVE", "agressividade": 0.4},
    "SAMURAI": {"alcance": 2.5, "estilo": "COUNTER", "agressividade": 0.5},
    "RONIN": {"alcance": 2.0, "estilo": "AGGRO", "agressividade": 0.7},
}


# =============================================================================
# ESTILOS DE LUTA (15+)
# =============================================================================

ESTILOS_LUTA = {
    # === ESTILOS AGRESSIVOS ===
    "RANGED": {
        "descricao": "Mantém distância, dispara projéteis",
        "acao_perto": "RECUAR",
        "acao_longe": "PRESSIONAR",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.5,
    },
    "BURST": {
        "descricao": "Salva recursos para dano explosivo",
        "acao_perto": "MATAR",
        "acao_longe": "APROXIMAR",
        "acao_medio": "PRESSIONAR",
        "agressividade_base": 0.7,
    },
    "TANK": {
        "descricao": "Absorve dano, avança constantemente",
        "acao_perto": "COMBATE",
        "acao_longe": "APROXIMAR",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.6,
    },
    "HIT_RUN": {
        "descricao": "Ataca e recua rapidamente",
        "acao_perto": "ATAQUE_RAPIDO",
        "acao_longe": "APROXIMAR",
        "acao_medio": "FLANQUEAR",
        "agressividade_base": 0.7,
    },
    "BERSERK": {
        "descricao": "Ataque constante sem defesa",
        "acao_perto": "MATAR",
        "acao_longe": "MATAR",
        "acao_medio": "MATAR",
        "agressividade_base": 1.0,
    },
    "COUNTER": {
        "descricao": "Espera e contra-ataca agressivamente",
        "acao_perto": "CONTRA_ATAQUE",
        "acao_longe": "APROXIMAR",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.55,
    },
    "POKE": {
        "descricao": "Ataques rápidos de média distância",
        "acao_perto": "ATAQUE_RAPIDO",
        "acao_longe": "APROXIMAR",
        "acao_medio": "POKE",
        "agressividade_base": 0.65,
    },
    "KITE": {
        "descricao": "Mantém distância enquanto ataca",
        "acao_perto": "ATAQUE_RAPIDO",
        "acao_longe": "PRESSIONAR",
        "acao_medio": "POKE",
        "agressividade_base": 0.5,
    },
    "MOBILE": {
        "descricao": "Movimento constante e agressivo",
        "acao_perto": "FLANQUEAR",
        "acao_longe": "APROXIMAR",
        "acao_medio": "FLANQUEAR",
        "agressividade_base": 0.75,
    },
    "COMBO": {
        "descricao": "Encadeia ataques",
        "acao_perto": "MATAR",
        "acao_longe": "APROXIMAR",
        "acao_medio": "MATAR",
        "agressividade_base": 0.85,
    },
    "OPPORTUNIST": {
        "descricao": "Ataca em toda abertura",
        "acao_perto": "ATAQUE_RAPIDO",
        "acao_longe": "APROXIMAR",
        "acao_medio": "FLANQUEAR",
        "agressividade_base": 0.65,
    },
    "AMBUSH": {
        "descricao": "Espera pouco e ataca de surpresa",
        "acao_perto": "ESMAGAR",
        "acao_longe": "APROXIMAR",
        "acao_medio": "FLANQUEAR",
        "agressividade_base": 0.7,
    },
    "CONTROL": {
        "descricao": "Controla o espaço agressivamente",
        "acao_perto": "ATAQUE_RAPIDO",
        "acao_longe": "PRESSIONAR",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.6,
    },
    "DEFENSIVE": {
        "descricao": "Defensivo mas contra-ataca",
        "acao_perto": "CONTRA_ATAQUE",
        "acao_longe": "COMBATE",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.4,
    },
    "ADAPTIVE": {
        "descricao": "Muda baseado na situação",
        "acao_perto": "COMBATE",
        "acao_longe": "APROXIMAR",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.6,
    },
    "SHOWMAN": {
        "descricao": "Luta para impressionar",
        "acao_perto": "ATAQUE_RAPIDO",
        "acao_longe": "APROXIMAR",
        "acao_medio": "FLANQUEAR",
        "agressividade_base": 0.8,
    },
    "AGGRO": {
        "descricao": "Agressão constante",
        "acao_perto": "ESMAGAR",
        "acao_longe": "MATAR",
        "acao_medio": "MATAR",
        "agressividade_base": 0.95,
    },
    "SUMMON": {
        "descricao": "Posiciona enquanto invocações lutam",
        "acao_perto": "COMBATE",
        "acao_longe": "PRESSIONAR",
        "acao_medio": "COMBATE",
        "agressividade_base": 0.45,
    },
    "BALANCED": {
        "descricao": "Equilíbrio com tendência agressiva",
        "acao_perto": "COMBATE",
        "acao_longe": "APROXIMAR",
        "acao_medio": "PRESSIONAR",
        "agressividade_base": 0.65,
    },
}


# =============================================================================
# QUIRKS (20+)
# =============================================================================

QUIRKS = {
    "GRITO_GUERRA": {
        "descricao": "Grita antes de atacar",
        "trigger": "pre_ataque",
        "efeito": "buff_dano_temporario",
    },
    "DANCA_MORTE": {
        "descricao": "Gira ao redor do inimigo",
        "trigger": "combate_longo",
        "efeito": "circular_rapido",
    },
    "OLHO_VERMELHO": {
        "descricao": "Fica mais forte com raiva",
        "trigger": "raiva_alta",
        "efeito": "buff_velocidade",
    },
    "SEGUNDO_FOLEGO": {
        "descricao": "Recupera energia com HP crítico",
        "trigger": "hp_critico",
        "efeito": "regen_stamina",
    },
    "SEDE_SANGUE": {
        "descricao": "Fica mais rápido após matar",
        "trigger": "kill",
        "efeito": "buff_velocidade",
    },
    "PROVOCADOR": {
        "descricao": "Para para provocar o inimigo",
        "trigger": "random",
        "efeito": "pausa_dramatica",
    },
    "FINALIZADOR": {
        "descricao": "Ataque especial quando inimigo está fraco",
        "trigger": "inimigo_fraco",
        "efeito": "burst_damage",
    },
    "ESQUIVA_REFLEXA": {
        "descricao": "Pula automaticamente quando atacado",
        "trigger": "tomando_dano",
        "efeito": "auto_jump",
    },
    "FURIA_CEGA": {
        "descricao": "Ignora tudo quando com raiva",
        "trigger": "raiva_maxima",
        "efeito": "ignore_defense",
    },
    "PERSISTENTE": {
        "descricao": "Continua atacando mesmo atordoado",
        "trigger": "stunned",
        "efeito": "resist_stun",
    },
    "CALCULISTA_FRIO": {
        "descricao": "Fica mais preciso com o tempo",
        "trigger": "combate_longo",
        "efeito": "buff_precisao",
    },
    "EXPLOSAO_FINAL": {
        "descricao": "Usa todas skills antes de morrer",
        "trigger": "pre_morte",
        "efeito": "spam_skills",
    },
    "CONTRA_ATAQUE_PERFEITO": {
        "descricao": "Contra-ataque devastador",
        "trigger": "esquiva_sucesso",
        "efeito": "counter_damage",
    },
    "AURA_INTIMIDANTE": {
        "descricao": "Inimigo fica mais cauteloso",
        "trigger": "sempre",
        "efeito": "debuff_inimigo",
    },
    "REGENERADOR": {
        "descricao": "Regenera HP lentamente",
        "trigger": "sempre",
        "efeito": "regen_hp",
    },
    "VAMPIRICO": {
        "descricao": "Rouba vida com ataques",
        "trigger": "hit_sucesso",
        "efeito": "lifesteal",
    },
    "ESPELHO": {
        "descricao": "Copia movimentos do inimigo",
        "trigger": "sempre",
        "efeito": "mirror_behavior",
    },
    "MESTRE_COMBO": {
        "descricao": "Combos mais longos e rápidos",
        "trigger": "combo_ativo",
        "efeito": "extended_combo",
    },
    "INSTINTO_ANIMAL": {
        "descricao": "Reage instantaneamente a perigo",
        "trigger": "perigo",
        "efeito": "instant_react",
    },
    "PACIENCIA_INFINITA": {
        "descricao": "Espera o momento perfeito",
        "trigger": "sempre",
        "efeito": "perfect_timing",
    },
}


# =============================================================================
# FILOSOFIAS DE COMBATE (10+)
# =============================================================================

FILOSOFIAS = {
    "DOMINACAO": {
        "objetivo": "Controlar a luta completamente",
        "preferencia_acao": ["ESMAGAR", "MATAR", "PRESSIONAR"],
        "mod_agressividade": 0.4,
    },
    "SOBREVIVENCIA": {
        "objetivo": "Sobreviver mas contra-atacar",
        "preferencia_acao": ["CONTRA_ATAQUE", "COMBATE", "RECUAR"],
        "mod_agressividade": -0.1,
    },
    "EQUILIBRIO": {
        "objetivo": "Balancear com foco em ataque",
        "preferencia_acao": ["COMBATE", "MATAR", "FLANQUEAR"],
        "mod_agressividade": 0.1,
    },
    "OPORTUNISMO": {
        "objetivo": "Explorar fraquezas do inimigo",
        "preferencia_acao": ["MATAR", "FLANQUEAR", "ATAQUE_RAPIDO"],
        "mod_agressividade": 0.2,
    },
    "PRESSAO": {
        "objetivo": "Pressionar constantemente",
        "preferencia_acao": ["PRESSIONAR", "MATAR", "ESMAGAR"],
        "mod_agressividade": 0.35,
    },
    "PACIENCIA": {
        "objetivo": "Esperar e então atacar",
        "preferencia_acao": ["COMBATE", "CONTRA_ATAQUE", "FLANQUEAR"],
        "mod_agressividade": 0.0,
    },
    "CAOS": {
        "objetivo": "Ser imprevisível e agressivo",
        "preferencia_acao": ["MATAR", "FLANQUEAR", "ATAQUE_RAPIDO"],
        "mod_agressividade": 0.25,
    },
    "HONRA": {
        "objetivo": "Lutar com honra - combate direto",
        "preferencia_acao": ["COMBATE", "MATAR", "APROXIMAR"],
        "mod_agressividade": 0.15,
    },
    "EXECUCAO": {
        "objetivo": "Terminar rápido",
        "preferencia_acao": ["MATAR", "ESMAGAR", "PRESSIONAR"],
        "mod_agressividade": 0.4,
    },
    "RESISTENCIA": {
        "objetivo": "Vencer por attrition - atacando",
        "preferencia_acao": ["COMBATE", "CONTRA_ATAQUE", "POKE"],
        "mod_agressividade": 0.0,
    },
    "ESPETACULO": {
        "objetivo": "Dar um show agressivo",
        "preferencia_acao": ["FLANQUEAR", "MATAR", "ATAQUE_RAPIDO"],
        "mod_agressividade": 0.2,
    },
    "ADAPTACAO": {
        "objetivo": "Mudar conforme necessário",
        "preferencia_acao": ["COMBATE", "MATAR", "FLANQUEAR"],
        "mod_agressividade": 0.1,
    },
}


# =============================================================================
# HUMORES DINÂMICOS (10)
# =============================================================================

HUMORES = {
    "CONFIANTE": {"mod_agressividade": 0.2, "mod_defesa": -0.1},
    "NERVOSO": {"mod_agressividade": -0.1, "mod_defesa": 0.1},
    "FURIOSO": {"mod_agressividade": 0.4, "mod_defesa": -0.2},
    "CALMO": {"mod_agressividade": 0.0, "mod_defesa": 0.0},
    "DESESPERADO": {"mod_agressividade": 0.3, "mod_defesa": -0.3},
    "FOCADO": {"mod_agressividade": 0.1, "mod_defesa": 0.1},
    "ENTEDIADO": {"mod_agressividade": -0.2, "mod_defesa": -0.1},
    "ANIMADO": {"mod_agressividade": 0.15, "mod_defesa": 0.0},
    "ASSUSTADO": {"mod_agressividade": -0.3, "mod_defesa": 0.2},
    "DETERMINADO": {"mod_agressividade": 0.1, "mod_defesa": 0.15},
}
