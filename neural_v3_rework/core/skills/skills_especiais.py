"""
NEURAL FIGHTS — Skills: ⚔️ ESPECIAIS
=======================================
Skills universais sem elemento — físicas, táticas, de utilidade

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_ESPECIAIS = {
    "Avanço Brutal": {
        "tipo": "DASH", "dano": 25.0, "distancia": 4.0, "cor": (255, 100, 100),
        "custo": 15.0, "cooldown": 5.0, "efeito": "EMPURRAO",
        "descricao": "Avança causando dano no caminho"
    },
    "Bomba Relógio": {
        "tipo": "PROJETIL", "dano": 80.0, "velocidade": 15.0, "raio": 0.4,
        "vida": 3.0, "cor": (255, 100, 0), "custo": 40.0, "cooldown": 20.0,
        "efeito": "BOMBA_RELOGIO", "delay_explosao": 3.0, "raio_explosao": 2.5,
        "descricao": "Marca o alvo - explode após 3s"
    },
    "Determinação": {
        "tipo": "BUFF", "cor": (255, 200, 100), "custo": 25.0, "cooldown": 25.0,
        "duracao": 6.0, "efeito_buff": "DETERMINADO",
        "descricao": "Cooldowns reduzidos pela metade"
    },
    "Execução": {
        "tipo": "PROJETIL", "dano": 100.0, "velocidade": 8.0, "raio": 0.3,
        "vida": 1.5, "cor": (255, 0, 0), "custo": 50.0, "cooldown": 30.0,
        "condicao": "ALVO_BAIXA_VIDA",
        "descricao": "Dano massivo contra alvos com pouca vida"
    },
    "Fúria Giratória": {
        "tipo": "AREA", "dano": 20.0, "raio_area": 2.0, "cor": (200, 150, 150),
        "custo": 18.0, "cooldown": 6.0, "efeito": "EMPURRAO",
        "descricao": "Gira a arma atingindo todos ao redor"
    },
    "Golpe do Executor": {
        "tipo": "BUFF", "cor": (150, 0, 0), "custo": 20.0, "cooldown": 15.0,
        "duracao": 3.0, "buff_dano": 2.0,
        "descricao": "Próximo ataque causa dano dobrado"
    },
    "Grito de Guerra": {
        "tipo": "BUFF", "cor": (255, 150, 100), "custo": 20.0, "cooldown": 20.0,
        "duracao": 8.0, "efeito_buff": "FURIA",
        "descricao": "Entra em fúria - mais dano, mais vulnerável"
    },
    "Impacto Sônico": {
        "tipo": "PROJETIL", "dano": 18.0, "velocidade": 20.0, "raio": 0.6,
        "vida": 0.35, "cor": (200, 200, 255), "custo": 12.0, "cooldown": 3.0,
        "efeito": "EMPURRAO", "descricao": "Onda de choque curta mas poderosa"
    },
    "Link de Vida": {
        "tipo": "PROJETIL", "dano": 0.0, "velocidade": 20.0, "raio": 0.3,
        "vida": 2.0, "cor": (255, 100, 255), "custo": 30.0, "cooldown": 25.0,
        "efeito": "LINK_ALMA", "link_percent": 0.5,
        "descricao": "Conecta almas - dano dividido 50/50"
    },
    "Provocar": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 5.0, "cor": (255, 50, 50),
        "custo": 10.0, "cooldown": 10.0,
        "taunt": True, "duracao_taunt": 3.0,
        "descricao": "Força inimigos a te atacarem"
    },
    "Reflexo Espelhado": {
        "tipo": "BUFF", "cor": (200, 200, 255), "custo": 30.0, "cooldown": 20.0,
        "duracao": 3.0, "refletir": 0.5,
        "descricao": "Reflete 50% do dano recebido"
    },
    "Sacrifício": {
        "tipo": "AREA", "dano": 120.0, "raio_area": 3.0, "cor": (255, 0, 0),
        "custo": 0, "cooldown": 120.0, "custo_vida_percent": 0.5,
        "descricao": "Sacrifica 50% HP para dano massivo"
    },
    "Terremoto": {
        "tipo": "AREA", "dano": 45.0, "raio_area": 4.0, "cor": (150, 100, 50),
        "custo": 35.0, "cooldown": 15.0, "efeito": "KNOCK_UP",
        "descricao": "Abala o chão derrubando inimigos"
    },
    "Troca de Almas": {
        "tipo": "DASH", "distancia": 0.0, "cor": (150, 0, 150),
        "custo": 40.0, "cooldown": 30.0, "efeito": "TROCAR_POS",
        "descricao": "Troca de posição com o alvo"
    },
    "Velocidade Arcana": {
        "tipo": "BUFF", "cor": (255, 255, 150), "custo": 15.0, "cooldown": 10.0,
        "duracao": 4.0, "buff_velocidade": 1.5,
        "descricao": "Aumenta velocidade de movimento"
    },
    "Último Suspiro": {
        "tipo": "BUFF", "cor": (255, 100, 100), "custo": 0, "cooldown": 90.0,
        "duracao": 60.0, "ativa_ao_morrer": True, "cura_percent": 0.5,
        "descricao": "Ao morrer, revive com 50% HP (passivo)"
    },
}
