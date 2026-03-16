"""
NEURAL FIGHTS — Skills: 🔥 FOGO
==================================
Dano alto, queimaduras, explosões

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_FOGO = {
    "Armadilha Incendiária": {
        "tipo": "TRAP", "dano": 30.0, "cor": (255, 80, 0),
        "custo": 22.0, "cooldown": 12.0, "elemento": "FOGO",
        "duracao": 8.0, "efeito": "QUEIMANDO", "vida_estrutura": 40.0,
        "bloqueia_movimento": False,
        "descricao": "Mina de fogo que explode ao contato"
    },
    "Bola de Fogo": {
        "tipo": "PROJETIL", "dano": 35.0, "velocidade": 11.0, "raio": 0.5,
        "vida": 2.0, "cor": (255, 100, 0), "custo": 25.0, "cooldown": 5.0,
        "efeito": "EXPLOSAO", "elemento": "FOGO",
        "descricao": "Esfera flamejante que explode no impacto"
    },
    "Chamas do Dragão": {
        "tipo": "BEAM", "dano": 12.0, "alcance": 6.0, "cor": (255, 120, 0),
        "custo": 30.0, "cooldown": 8.0, "efeito": "QUEIMANDO", "elemento": "FOGO",
        "canalizavel": True, "dano_por_segundo": 40.0, "duracao_max": 3.0,
        "descricao": "Sopro de fogo contínuo"
    },
    "Combustão Espontânea": {
        "tipo": "PROJETIL", "dano": 80.0, "velocidade": 0.5, "raio": 0.3,  # B3 fix: era 0 → projétil ficava parado
        "vida": 0.1, "cor": (255, 50, 50), "custo": 50.0, "cooldown": 20.0,
        "efeito": "EXPLOSAO", "elemento": "FOGO",
        "condicao": "ALVO_QUEIMANDO", "dano_bonus_condicao": 2.0,
        "descricao": "Detona queimaduras no alvo - dano massivo se queimando"
    },
    "Cometa": {
        "tipo": "PROJETIL", "dano": 50.0, "velocidade": 8.0, "raio": 0.6,
        "vida": 4.0, "cor": (255, 150, 50), "custo": 40.0, "cooldown": 18.0,
        "efeito": "QUEIMANDO", "elemento": "FOGO",
        "raio_explosao": 3.0, "homing": True,
        "descricao": "Cometa rastreador que explode em chamas ao atingir o alvo"
    },
    "Erupção Vulcânica": {
        "tipo": "CHANNEL", "cor": (255, 80, 0), "custo": 50.0, "cooldown": 30.0,
        "elemento": "FOGO", "canalizavel": True, "duracao_max": 3.0,
        "dano_por_segundo": 45.0, "imobiliza": True,
        "meteoros_aleatorios": 6,
        "descricao": "Canaliza magma que erupciona em meteoros aleatórios"
    },
    "Escudo de Brasas": {
        "tipo": "BUFF", "cor": (255, 100, 50), "custo": 25.0, "cooldown": 15.0,
        "duracao": 8.0, "elemento": "FOGO",
        "dano_contato": 10.0, "escudo": 25.0,
        "descricao": "Escudo que queima quem ataca corpo a corpo"
    },
    "Explosão Nova": {
        "tipo": "AREA", "dano": 45.0, "raio_area": 3.0, "cor": (255, 200, 50),
        "custo": 35.0, "cooldown": 12.0, "efeito": "EMPURRAO", "elemento": "FOGO",
        "descricao": "Explosão ao redor do conjurador"
    },
    "Fênix": {
        "tipo": "SUMMON", "dano": 25.0, "cor": (255, 180, 50), 
        "custo": 60.0, "cooldown": 30.0, "elemento": "FOGO",
        "efeito": "QUEIMANDO",
        "duracao": 15.0, "summon_vida": 80.0, "summon_dano": 15.0,
        "aura_dano": 5.0, "aura_raio": 2.0,
        "descricao": "Invoca uma fênix que ataca com fogo e revive uma vez"
    },
    "Inferno": {
        "tipo": "AREA", "dano": 15.0, "raio_area": 4.0, "cor": (255, 80, 0),
        "custo": 45.0, "cooldown": 15.0, "efeito": "QUEIMANDO", "elemento": "FOGO",
        "duracao": 5.0, "dano_tick": 10.0,
        "descricao": "Campo de fogo persistente"
    },
    "Lança de Fogo": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 25.0, "raio": 0.25,
        "vida": 1.0, "cor": (255, 150, 50), "custo": 12.0, "cooldown": 2.5,
        "efeito": "QUEIMANDO", "elemento": "FOGO",
        "descricao": "Projétil rápido que causa queimadura"
    },
    "Meteoro": {
        "tipo": "PROJETIL", "dano": 60.0, "velocidade": 8.0, "raio": 0.8,
        "vida": 2.5, "cor": (255, 50, 0), "custo": 40.0, "cooldown": 10.0,
        "efeito": "EXPLOSAO", "elemento": "FOGO", "raio_explosao": 2.0,
        "descricao": "Rocha incandescente devastadora"
    },
    "Pilar de Fogo": {
        "tipo": "AREA", "dano": 50.0, "raio_area": 1.5, "cor": (255, 150, 0),
        "custo": 28.0, "cooldown": 7.0, "efeito": "KNOCK_UP", "elemento": "FOGO",
        "delay": 0.8, "duracao": 1.0, "descricao": "Pilar de fogo que lança inimigos"
    },
    "Rastro de Fogo": {
        "tipo": "DASH", "dano": 15.0, "distancia": 5.0, "cor": (255, 120, 0),
        "custo": 18.0, "cooldown": 7.0, "efeito": "QUEIMANDO", "elemento": "FOGO",
        "descricao": "Dash que deixa rastro de fogo no caminho"
    },
}
