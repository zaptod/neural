"""
NEURAL FIGHTS â€” Skills: ðŸ’€ CAOS
==================================
AleatÃ³rio, instÃ¡vel, poderoso, imprevisÃ­vel

Importado automaticamente por nucleo/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utilitarios.config import PPM


SKILLS_CAOS = {
    "Apocalipse": {
        "tipo": "AREA", "dano": 80.0, "raio_area": 6.0, "cor": (255, 0, 150),
        "custo": 70.0, "cooldown": 60.0, "elemento": "CAOS",
        "delay": 3.0, "meteoros_aleatorios": 10,
        "descricao": "Chuva de meteoros caÃ³ticos"
    },
    "Chama CaÃ³tica": {
        "tipo": "PROJETIL", "dano": 30.0, "velocidade": 12.0, "raio": 0.4,
        "vida": 2.0, "cor": (255, 50, 150), "custo": 22.0, "cooldown": 5.0,
        "elemento": "CAOS", "elemento_aleatorio": True, "dano_variavel": (0.5, 2.0),
        "descricao": "Dano e elemento aleatÃ³rios"
    },
    "DistorÃ§Ã£o da Realidade": {
        "tipo": "AREA", "dano": 50.0, "raio_area": 4.0, "cor": (255, 80, 200),
        "custo": 45.0, "cooldown": 20.0, "elemento": "CAOS",
        "efeito_aleatorio": True, "efeitos_possiveis": [
            "QUEIMANDO", "CONGELADO", "PARALISIA", "ENVENENADO",
            "LENTO", "SILENCIADO", "CEGO", "MEDO"
        ],
        "delay": 1.5, "aviso_visual": True,
        "descricao": "Rasga a realidade aplicando efeitos caÃ³ticos em Ã¡rea"
    },
    "DuplicaÃ§Ã£o CaÃ³tica": {
        "tipo": "PROJETIL", "dano": 25.0, "velocidade": 14.0, "raio": 0.4,
        "vida": 2.5, "cor": (255, 100, 180), "custo": 28.0, "cooldown": 8.0,
        "elemento": "CAOS", "duplica_apos": 0.8, "split_aleatorio": True, "max_splits": 3,
        "descricao": "ProjÃ©til instÃ¡vel que se divide e duplica"
    },
    "Espelho do Caos": {
        "tipo": "TRAP", "dano": 0.0, "cor": (255, 140, 220),
        "custo": 25.0, "cooldown": 15.0, "elemento": "CAOS",
        "duracao": 12.0, "vida_estrutura": 60.0,
        "efeito": "CHARME", "bloqueia_movimento": False,
        "descricao": "Armadilha que confunde inimigos fazendo-os atacar aliados"
    },
    "ExplosÃ£o do Caos": {
        "tipo": "AREA", "dano": 40.0, "raio_area": 3.0, "cor": (255, 100, 200),
        "custo": 35.0, "cooldown": 12.0, "elemento": "CAOS",
        "efeito_aleatorio": True, "efeitos_possiveis": [
            "QUEIMANDO", "CONGELADO", "PARALISIA", "ENVENENADO", "LENTO"
        ],
        "descricao": "ExplosÃ£o com efeito aleatÃ³rio"
    },
    "Fissura CaÃ³tica": {
        "tipo": "BEAM", "dano": 25.0, "alcance": 8.0, "cor": (255, 80, 180),
        "custo": 22.0, "cooldown": 6.0, "elemento": "CAOS",
        "efeito_aleatorio": True, "efeitos_possiveis": [
            "QUEIMANDO", "PARALISIA", "ENVENENADO", "SANGRANDO"
        ],
        "descricao": "Raio caÃ³tico com efeito aleatÃ³rio"
    },
    "Instabilidade": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 10.0, "raio": 0.5,
        "vida": 3.0, "cor": (255, 150, 200), "custo": 28.0, "cooldown": 8.0,
        "elemento": "CAOS", "split_aleatorio": True, "max_splits": 4,
        "descricao": "Divide aleatoriamente em mais projÃ©teis"
    },
    "Loteria da Morte": {
        "tipo": "PROJETIL", "dano": 50.0, "velocidade": 18.0, "raio": 0.3,
        "vida": 1.5, "cor": (255, 50, 200), "custo": 25.0, "cooldown": 10.0,
        "elemento": "CAOS", "dano_variavel": (0.3, 3.0),
        "homing": True,
        "descricao": "MÃ­ssil caÃ³tico com dano ultra-aleatÃ³rio"
    },
    "MutaÃ§Ã£o": {
        "tipo": "BUFF", "cor": (200, 50, 150), "custo": 25.0, "cooldown": 20.0,
        "duracao": 8.0, "elemento": "CAOS",
        "stats_aleatorios": True,
        "descricao": "Stats aleatÃ³rios (pode ser bom ou ruim)"
    },
    "Portal do Caos": {
        "tipo": "DASH", "distancia": 8.0, "cor": (255, 50, 150),
        "custo": 15.0, "cooldown": 5.0, "elemento": "CAOS",
        "dano_chegada": 25.0,
        "descricao": "Teleporte caÃ³tico com explosÃ£o na chegada"
    },
    "Roleta Russa": {
        "tipo": "PROJETIL", "dano": 75.0, "velocidade": 20.0, "raio": 0.3,
        "vida": 1.5, "cor": (255, 0, 100), "custo": 30.0, "cooldown": 15.0,
        "elemento": "CAOS", "chance_backfire": 0.2,
        "descricao": "Dano massivo mas 20% chance de acertar vocÃª"
    },
    "Sobrecarga EntrÃ³pica": {
        "tipo": "BUFF", "cor": (255, 120, 200), "custo": 30.0, "cooldown": 25.0,
        "duracao": 8.0, "elemento": "CAOS",
        "buff_dano": 1.8, "dano_variavel": (0.5, 2.0),
        "chance_backfire": 0.1,
        "descricao": "Amplifica dano caoticamente â€” cada hit Ã© imprevisÃ­vel"
    },
    "TransmutaÃ§Ã£o": {
        "tipo": "TRANSFORM", "cor": (255, 100, 180), "custo": 35.0, "cooldown": 40.0,
        "duracao": 10.0, "elemento": "CAOS",
        "stats_aleatorios": True,
        "descricao": "Transforma com stats aleatÃ³rios - sorte ou azar"
    },
}

