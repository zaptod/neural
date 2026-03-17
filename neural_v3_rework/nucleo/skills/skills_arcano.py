"""
NEURAL FIGHTS â€” Skills: ðŸ’œ ARCANO
====================================
Puro, amplificaÃ§Ã£o, manipulaÃ§Ã£o mÃ¡gica

Importado automaticamente por nucleo/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utilitarios.config import PPM


SKILLS_ARCANO = {
    "Amplificar Magia": {
        "tipo": "BUFF", "cor": (180, 100, 255), "custo": 15.0, "cooldown": 20.0,
        "duracao": 8.0, "elemento": "ARCANO",
        "bonus_dano_magico": 1.5, "bonus_area": 1.3,
        "descricao": "PrÃ³ximas magias +50% dano e Ã¡rea"
    },
    "ConjuraÃ§Ã£o Perfeita": {
        "tipo": "BUFF", "cor": (255, 200, 255), "custo": 50.0, "cooldown": 60.0,
        "duracao": 10.0, "elemento": "ARCANO",
        "sem_cooldown": True, "custo_mana_metade": True,
        "descricao": "Skills sem cooldown e custo reduzido por 10s"
    },
    "ContrafeitiÃ§o": {
        "tipo": "BUFF", "cor": (150, 150, 255), "custo": 25.0, "cooldown": 15.0,
        "duracao": 2.0, "elemento": "ARCANO",
        "reflete_skills": True,
        "descricao": "Reflete a prÃ³xima skill inimiga"
    },
    "Desintegrar": {
        "tipo": "BEAM", "dano": 15.0, "alcance": 12.0, "cor": (200, 100, 255),
        "custo": 40.0, "cooldown": 12.0, "elemento": "ARCANO",
        "canalizavel": True, "dano_por_segundo": 50.0, "duracao_max": 3.0,
        "penetra_escudo": True,
        "descricao": "Raio que ignora escudos"
    },
    "Disparo de Mana": {
        "tipo": "PROJETIL", "dano": 10.0, "velocidade": 14.0, "raio": 0.3,
        "vida": 2.5, "cor": (50, 150, 255), "custo": 8.0, "cooldown": 1.5,
        "elemento": "ARCANO",
        "descricao": "ProjÃ©til bÃ¡sico de mana pura"
    },
    "Escudo Arcano": {
        "tipo": "BUFF", "cor": (100, 150, 255), "custo": 20.0, "cooldown": 12.0,
        "duracao": 5.0, "elemento": "ARCANO",
        "escudo": 40.0, "reflete_projeteis": True,
        "descricao": "Escudo que reflete projÃ©teis"
    },
    "ExplosÃ£o Arcana": {
        "tipo": "AREA", "dano": 35.0, "raio_area": 2.5, "cor": (150, 100, 255),
        "custo": 25.0, "cooldown": 8.0, "efeito": "SILENCIADO", "elemento": "ARCANO",
        "descricao": "ExplosÃ£o que silencia"
    },
    "InvocaÃ§Ã£o: EspÃ­rito": {
        "tipo": "SUMMON", "cor": (180, 180, 255), "custo": 35.0, "cooldown": 25.0,
        "elemento": "ARCANO", "efeito": "LENTO",
        "duracao": 10.0, "summon_vida": 50.0, "summon_dano": 8.0,
        "descricao": "Invoca um espÃ­rito arcano que retarda inimigos"
    },
    "MÃ­sseis Arcanos": {
        "tipo": "PROJETIL", "dano": 8.0, "velocidade": 18.0, "raio": 0.2,
        "vida": 1.5, "cor": (100, 100, 255), "custo": 15.0, "cooldown": 3.0,
        "elemento": "ARCANO", "multi_shot": 5, "homing": True,
        "descricao": "5 mÃ­sseis teleguiados"
    },
    "Orbe de Mana": {
        "tipo": "PROJETIL", "dano": 30.0, "velocidade": 8.0, "raio": 0.5,
        "vida": 4.0, "cor": (120, 80, 255), "custo": 20.0, "cooldown": 6.0,
        "elemento": "ARCANO", "homing": True,
        "descricao": "Orbe de mana rastreadora e persistente"
    },
    "Portal Arcano": {
        "tipo": "DASH", "distancia": 10.0, "cor": (100, 100, 255),
        "custo": 30.0, "cooldown": 15.0, "elemento": "ARCANO",
        "cria_portal": True, "duracao_portal": 5.0,
        "descricao": "Cria portal de ida e volta"
    },
    "Roubar Magia": {
        "tipo": "PROJETIL", "dano": 15.0, "velocidade": 20.0, "raio": 0.3,
        "vida": 1.5, "cor": (200, 150, 255), "custo": 20.0, "cooldown": 10.0,
        "elemento": "ARCANO", "rouba_buff": True,
        "descricao": "Rouba um buff aleatÃ³rio do alvo"
    },
    "Ruptura Arcana": {
        "tipo": "AREA", "dano": 50.0, "raio_area": 2.0, "cor": (180, 120, 255),
        "custo": 30.0, "cooldown": 10.0, "efeito": "SILENCIADO", "elemento": "ARCANO",
        "delay": 0.5, "duracao": 2.0,
        "descricao": "Ruptura que silencia e causa dano contÃ­nuo"
    },
}

