"""
NEURAL FIGHTS â€” Skills: ðŸ’š NATUREZA
======================================
Veneno, cura, controle, raÃ­zes

Importado automaticamente por nucleo/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utilitarios.config import PPM


SKILLS_NATUREZA = {
    "Dardo Venenoso": {
        "tipo": "PROJETIL", "dano": 5.0, "velocidade": 22.0, "raio": 0.15,
        "vida": 1.5, "cor": (100, 255, 100), "custo": 10.0, "cooldown": 2.0,
        "efeito": "ENVENENADO", "elemento": "NATUREZA",
        "descricao": "Dardo rÃ¡pido com veneno potente"
    },
    "Espinhos": {
        "tipo": "PROJETIL", "dano": 12.0, "velocidade": 20.0, "raio": 0.2,
        "vida": 1.2, "cor": (80, 150, 50), "custo": 8.0, "cooldown": 1.5,
        "efeito": "SANGRANDO", "elemento": "NATUREZA", "multi_shot": 3,
        "descricao": "Dispara 3 espinhos em leque"
    },
    "Esporo Explosivo": {
        "tipo": "PROJETIL", "dano": 15.0, "velocidade": 12.0, "raio": 0.4,
        "vida": 2.0, "cor": (120, 180, 50), "custo": 16.0, "cooldown": 5.0,
        "efeito": "ENVENENADO", "elemento": "NATUREZA",
        "raio_explosao": 1.5,
        "descricao": "Esporo que explode em nuvem tÃ³xica"
    },
    "Esporos AlucinÃ³genos": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 3.0, "cor": (200, 150, 255),
        "custo": 28.0, "cooldown": 15.0, "efeito": "CHARME", "elemento": "NATUREZA",
        "duracao_charme": 2.0,
        "descricao": "Confunde inimigos - eles te seguem"
    },
    "FotossÃ­ntese": {
        "tipo": "CHANNEL", "cor": (150, 255, 100), "custo": 0, "cooldown": 20.0,
        "elemento": "NATUREZA", "canalizavel": True, "duracao_max": 4.0,
        "cura_por_segundo": 15.0, "imobiliza": True,
        "descricao": "Canaliza para curar (nÃ£o pode mover)"
    },
    "Ira da Floresta": {
        "tipo": "SUMMON", "dano": 15.0, "cor": (80, 150, 50),
        "custo": 40.0, "cooldown": 25.0, "elemento": "NATUREZA",
        "efeito": "ENVENENADO",
        "duracao": 12.0, "summon_vida": 100.0, "summon_dano": 12.0,
        "summon_tipo": "TREANT",
        "descricao": "Invoca um treant que envenena inimigos"
    },
    "Nuvem TÃ³xica": {
        "tipo": "AREA", "dano": 5.0, "raio_area": 3.5, "cor": (150, 200, 50),
        "custo": 25.0, "cooldown": 12.0, "efeito": "ENVENENADO", "elemento": "NATUREZA",
        "duracao": 4.0, "stacks_por_segundo": 1,
        "descricao": "Nuvem persistente de veneno"
    },
    "Praga": {
        "tipo": "PROJETIL", "dano": 10.0, "velocidade": 8.0, "raio": 0.6,
        "vida": 4.0, "cor": (80, 100, 30), "custo": 35.0, "cooldown": 18.0,
        "efeito": "ENVENENADO", "elemento": "NATUREZA",
        "contagioso": True, "raio_contagio": 2.0,
        "descricao": "Veneno que se espalha entre inimigos"
    },
    "RaÃ­zes": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 2.0, "cor": (100, 80, 50),
        "custo": 18.0, "cooldown": 8.0, "efeito": "ENRAIZADO", "elemento": "NATUREZA",
        "duracao": 2.5,
        "descricao": "Prende inimigos no lugar"
    },
    "RegeneraÃ§Ã£o": {
        "tipo": "BUFF", "cor": (100, 255, 100), "custo": 20.0, "cooldown": 15.0,
        "duracao": 8.0, "elemento": "NATUREZA",
        "efeito_buff": "REGENERANDO", "cura_tick": 8.0,
        "descricao": "Regenera vida ao longo do tempo"
    },
    "Selva Viva": {
        "tipo": "SUMMON", "cor": (60, 180, 40), "custo": 40.0, "cooldown": 25.0,
        "duracao": 12.0, "summon_vida": 70.0, "summon_dano": 10.0,
        "elemento": "NATUREZA", "efeito": "ENRAIZADO",
        "descricao": "Invoca um treant que enraÃ­za inimigos ao atacar"
    },
    "Simbiose": {
        "tipo": "BUFF", "cor": (100, 200, 80), "custo": 30.0, "cooldown": 20.0,
        "duracao": 10.0, "elemento": "NATUREZA",
        "cura_por_segundo": 10.0, "escudo": 30.0,
        "descricao": "Simbiose com a natureza que regenera HP e cria escudo vivo"
    },
    "Videira Constritora": {
        "tipo": "BEAM", "dano": 8.0, "alcance": 5.0, "cor": (80, 140, 40),
        "custo": 15.0, "cooldown": 6.0, "efeito": "ENRAIZADO", "elemento": "NATUREZA",
        "canalizavel": True, "dano_por_segundo": 15.0, "duracao_max": 3.0,
        "descricao": "Videira que prende e espreme o alvo"
    },
    "Wrath of Nature": {
        "tipo": "AREA", "dano": 60.0, "raio_area": 6.0, "cor": (100, 200, 50),
        "custo": 65.0, "cooldown": 40.0, "elemento": "NATUREZA",
        "efeito": "ENRAIZADO", "efeito2": "ENVENENADO",
        "delay": 1.0, "ondas": 3,
        "descricao": "3 ondas de natureza devastadora"
    },
}

