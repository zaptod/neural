"""
NEURAL FIGHTS — Skills: ❄️ GELO
==================================
Controle, slow, congelamento, shatter

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_GELO = {
    "Avalanche": {
        "tipo": "AREA", "dano": 55.0, "raio_area": 6.0, "cor": (160, 220, 255),
        "custo": 45.0, "cooldown": 22.0, "efeito": "LENTO", "elemento": "GELO",
        "delay": 1.5, "ondas": 3, "forca_empurrao": 2.0,
        "descricao": "3 ondas de gelo que empurram e congelam tudo no caminho"
    },
    "Avatar de Gelo": {
        "tipo": "TRANSFORM", "cor": (150, 200, 255), "custo": 50.0, "cooldown": 45.0,
        "duracao": 12.0, "elemento": "GELO",
        "bonus_resistencia": 0.5, "aura_slow": 0.6, "aura_raio": 3.0,
        "descricao": "Transforma em elemental de gelo - aura de slow"
    },
    "Cone de Gelo": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 20.0, "raio": 0.5,
        "vida": 0.5, "cor": (150, 220, 255), "custo": 15.0, "cooldown": 4.0,
        "efeito": "LENTO", "elemento": "GELO", "cone": True, "angulo_cone": 60,
        "descricao": "Cone de gelo que atinge múltiplos alvos"
    },
    "Espelho de Gelo": {
        "tipo": "TRAP", "dano": 0.0, "cor": (200, 240, 255),
        "custo": 20.0, "cooldown": 12.0, "elemento": "GELO",
        "duracao": 15.0, "vida_estrutura": 80.0,
        "bloqueia_movimento": True, "bloqueia_projeteis": True,
        "dano_wall_contato_base": 5.0,
        "descricao": "Parede de gelo inquebrável que reflete projéteis"
    },
    "Estilhaço Glacial": {
        "tipo": "PROJETIL", "dano": 12.0, "velocidade": 22.0, "raio": 0.2,
        "vida": 1.0, "cor": (180, 230, 255), "custo": 12.0, "cooldown": 2.5,
        "efeito": "LENTO", "elemento": "GELO", "multi_shot": 5,
        "descricao": "Saraivada de 5 fragmentos gélidos"
    },
    "Estilhaço de Gelo": {
        "tipo": "PROJETIL", "dano": 15.0, "velocidade": 18.0, "raio": 0.3,
        "vida": 1.8, "cor": (150, 220, 255), "custo": 10.0, "cooldown": 2.0,
        "efeito": "LENTO", "elemento": "GELO",
        "descricao": "Fragmento gélido que desacelera"
    },
    "Lança de Gelo": {
        "tipo": "PROJETIL", "dano": 28.0, "velocidade": 22.0, "raio": 0.35,
        "vida": 1.5, "cor": (100, 200, 255), "custo": 18.0, "cooldown": 4.0,
        "efeito": "LENTO", "elemento": "GELO", "perfura": True,  # B4 fix: era "PERFURAR" (comportamento, não status) → "LENTO"
        "descricao": "Lança perfurante de gelo puro"
    },
    "Morte Glacial": {
        "tipo": "PROJETIL", "dano": 100.0, "velocidade": 10.0, "raio": 0.5,
        "vida": 2.0, "cor": (200, 230, 255), "custo": 70.0, "cooldown": 40.0,
        "efeito": "CONGELADO", "elemento": "GELO",
        "condicao": "ALVO_BAIXA_VIDA", "executa": True,
        "descricao": "Executa alvos com pouca vida - congela o cadáver"
    },
    "Muralha de Gelo": {
        "tipo": "TRAP", "dano": 0.0, "cor": (180, 220, 255),
        "custo": 20.0, "cooldown": 12.0, "elemento": "GELO",
        "efeito": "CONGELADO",
        "duracao": 6.0, "bloqueia_movimento": True, "vida_estrutura": 100.0,
        "dano_contato": 8.0,
        "descricao": "Cria uma parede de gelo que congela quem tocar"
    },
    "Nevasca": {
        "tipo": "AREA", "dano": 12.0, "raio_area": 4.0, "cor": (200, 230, 255),
        "custo": 28.0, "cooldown": 15.0, "efeito": "LENTO", "elemento": "GELO",
        "duracao": 3.0, "slow_fator": 0.4,
        "descricao": "Área de gelo que causa slow contínuo"
    },
    "Prisão de Gelo": {
        "tipo": "PROJETIL", "dano": 5.0, "velocidade": 15.0, "raio": 0.4,
        "vida": 2.0, "cor": (180, 240, 255), "custo": 22.0, "cooldown": 8.0,
        "efeito": "CONGELADO", "elemento": "GELO",
        "descricao": "Aprisiona o alvo em gelo"
    },
    "Shatter": {
        "tipo": "AREA", "dano": 60.0, "raio_area": 2.5, "cor": (200, 240, 255),
        "custo": 25.0, "cooldown": 10.0, "efeito": "VULNERAVEL", "elemento": "GELO",
        "condicao": "ALVO_CONGELADO", "remove_congelamento": True,
        "descricao": "Estilhaça alvos congelados - dano massivo"
    },
    "Zero Absoluto": {
        "tipo": "AREA", "dano": 30.0, "raio_area": 3.5, "cor": (220, 240, 255),
        "custo": 55.0, "cooldown": 25.0, "efeito": "CONGELADO", "elemento": "GELO",
        "duracao_stun": 3.0,
        "descricao": "Congela todos em grande área"
    },
}
