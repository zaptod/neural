"""
NEURAL FIGHTS — Skills: 🌑 TREVAS
====================================
Drain, fear, debuffs, silêncio

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_TREVAS = {
    "Ceifar": {
        "tipo": "AREA", "dano": 60.0, "raio_area": 2.0, "cor": (50, 0, 70),
        "custo": 35.0, "cooldown": 14.0, "efeito": "DRENAR", "elemento": "TREVAS",
        "lifesteal": 0.4, "condicao": "ALVO_BAIXA_VIDA",
        "descricao": "Ceifa vida de alvos fracos com lifesteal massivo"
    },
    "Colheita de Almas": {
        "tipo": "AREA", "dano": 50.0, "raio_area": 5.0, "cor": (80, 0, 100),
        "custo": 60.0, "cooldown": 45.0, "efeito": "DRENAR", "elemento": "TREVAS",
        "cura_por_morte": 50.0,
        "descricao": "Dano em área - cura massiva se matar"
    },
    "Cópia Sombria": {
        "tipo": "SUMMON", "cor": (100, 100, 100), "custo": 45.0, "cooldown": 30.0,
        "elemento": "TREVAS", "efeito": "CEGO",
        "duracao": 10.0, "summon_vida": 60.0, "summon_dano": 18.0,
        "descricao": "Invoca uma sombra que cega inimigos ao atacar"
    },
    "Eclipse": {
        "tipo": "AREA", "dano": 40.0, "raio_area": 5.0, "cor": (30, 0, 50),
        "custo": 50.0, "cooldown": 30.0, "efeito": "CEGO", "elemento": "TREVAS",
        "duracao": 4.0, "dano_por_segundo": 15.0,
        "descricao": "Escurece uma área massiva cegando e drenando inimigos"
    },
    "Esfera Sombria": {
        "tipo": "PROJETIL", "dano": 18.0, "velocidade": 12.0, "raio": 0.45,
        "vida": 2.5, "cor": (80, 0, 120), "custo": 14.0, "cooldown": 3.0,
        "efeito": "DRENAR", "elemento": "TREVAS", "lifesteal": 0.3,
        "descricao": "Drena vida do alvo"
    },
    "Explosão Necrótica": {
        "tipo": "AREA", "dano": 30.0, "raio_area": 2.5, "cor": (60, 0, 80),
        "custo": 28.0, "cooldown": 9.0, "efeito": "DRENAR", "elemento": "TREVAS",
        "lifesteal": 0.25,
        "descricao": "Explosão que drena vida de todos ao redor"
    },
    "Maldição": {
        "tipo": "PROJETIL", "dano": 8.0, "velocidade": 10.0, "raio": 0.5,
        "vida": 3.0, "cor": (100, 0, 100), "custo": 20.0, "cooldown": 10.0,
        "efeito": "MALDITO", "elemento": "TREVAS",
        "descricao": "Maldição que enfraquece e causa DoT"
    },
    "Marca da Morte": {
        "tipo": "PROJETIL", "dano": 10.0, "velocidade": 15.0, "raio": 0.4,
        "vida": 2.0, "cor": (60, 0, 90), "custo": 20.0, "cooldown": 10.0,
        "efeito": "MALDITO", "elemento": "TREVAS",
        "delay_explosao": 3.0, "raio_explosao": 2.0,
        "descricao": "Marca o alvo que explode em trevas após 3 segundos"
    },
    "Medo Profundo": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 4.0, "cor": (50, 0, 80),
        "custo": 22.0, "cooldown": 12.0, "efeito": "MEDO", "elemento": "TREVAS",
        "duracao_fear": 2.5,
        "descricao": "Causa medo em todos próximos"
    },
    "Necrose": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 8.0, "raio": 0.5,
        "vida": 3.0, "cor": (30, 30, 30), "custo": 35.0, "cooldown": 15.0,
        "efeito": "NECROSE", "elemento": "TREVAS",
        "descricao": "Causa necrose - sem cura possível"
    },
    "Portal Sombrio": {
        "tipo": "DASH", "distancia": 8.0, "cor": (60, 0, 100),
        "custo": 25.0, "cooldown": 10.0, "elemento": "TREVAS",
        "invisivel_durante": True, "delay_saida": 0.5,
        "descricao": "Teleporta através das sombras, invisível durante"
    },
    "Possessão": {
        "tipo": "PROJETIL", "dano": 0.0, "velocidade": 12.0, "raio": 0.4,
        "vida": 2.0, "cor": (100, 0, 100), "custo": 50.0, "cooldown": 35.0,
        "efeito": "POSSESSO", "elemento": "TREVAS",
        "duracao_controle": 3.0,
        "descricao": "Controla a mente do inimigo brevemente"
    },
    "Sombra Envolvente": {
        "tipo": "BUFF", "cor": (40, 0, 60), "custo": 18.0, "cooldown": 15.0,
        "duracao": 5.0, "elemento": "TREVAS",
        "escudo": 30.0, "buff_velocidade": 1.4,
        "descricao": "Envolve em sombras - escudo e velocidade"
    },
}
