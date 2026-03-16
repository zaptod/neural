"""
NEURAL FIGHTS — Skills: 🩸 SANGUE
====================================
Lifesteal, sangramento, sacrifício, hemomancia

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_SANGUE = {
    "Armadura de Sangue": {
        "tipo": "TRANSFORM", "cor": (150, 0, 40), "custo": 0, "cooldown": 40.0,
        "custo_vida_percent": 0.1, "duracao": 12.0, "elemento": "SANGUE",
        "bonus_resistencia": 0.4, "lifesteal_global": 0.15,
        "dano_contato": 10.0, "bonus_velocidade": 1.2,
        "descricao": "Solidifica o sangue em armadura — regenera ao causar dano"
    },
    "Avatar de Sangue": {
        "tipo": "TRANSFORM", "cor": (180, 0, 40), "custo": 0, "cooldown": 45.0,
        "custo_vida_percent": 0.15, "duracao": 10.0, "elemento": "SANGUE",
        "bonus_resistencia": 0.3, "dano_contato": 15.0, "lifesteal_global": 0.2,
        "descricao": "Transforma em elemental de sangue - lifesteal em tudo"
    },
    "Chicote de Sangue": {
        "tipo": "BEAM", "dano": 18.0, "alcance": 6.0, "cor": (180, 0, 40),
        "custo": 14.0, "cooldown": 3.5, "efeito": "SANGRANDO", "elemento": "SANGUE",
        "lifesteal": 0.2,
        "descricao": "Chicote hemático que drena e causa sangramento"
    },
    "Coágulo": {
        "tipo": "TRAP", "dano": 10.0, "cor": (120, 0, 30),
        "custo": 18.0, "cooldown": 10.0, "elemento": "SANGUE",
        "duracao": 8.0, "efeito": "LENTO", "vida_estrutura": 50.0,
        "bloqueia_movimento": False,
        "descricao": "Armadilha de sangue coagulado que causa slow"
    },
    "Escudo Hemático": {
        "tipo": "BUFF", "cor": (180, 30, 50), "custo": 0, "cooldown": 15.0,
        "custo_vida": 15.0, "duracao": 6.0, "elemento": "SANGUE",
        "escudo": 40.0, "dano_contato": 8.0,
        "descricao": "Converte HP em escudo que fere quem toca"
    },
    "Estilhaço Sanguíneo": {
        "tipo": "PROJETIL", "dano": 18.0, "velocidade": 20.0, "raio": 0.25,
        "vida": 1.5, "cor": (200, 20, 40), "custo": 12.0, "cooldown": 3.0,
        "efeito": "SANGRANDO", "elemento": "SANGUE", "multi_shot": 4,
        "perfura": True,
        "descricao": "Dispara 4 lâminas de sangue cristalizado que perfuram"
    },
    "Explosão Sanguínea": {
        "tipo": "AREA", "dano": 40.0, "raio_area": 3.0, "cor": (180, 0, 30),
        "custo": 15.0, "cooldown": 15.0, "custo_vida": 25.0, "elemento": "SANGUE",
        "efeito": "SANGRANDO", "lifesteal": 0.3,
        "descricao": "Detona o próprio sangue - área com lifesteal"
    },
    "Frenesi Vampírico": {
        "tipo": "BUFF", "cor": (150, 0, 50), "custo": 20.0, "cooldown": 20.0,
        "duracao": 8.0, "elemento": "SANGUE",
        "bonus_velocidade_ataque": 1.8, "buff_dano": 1.3,
        "descricao": "Frenesi que aumenta velocidade e dano de ataque"
    },
    "Hemorrragia": {
        "tipo": "PROJETIL", "dano": 12.0, "velocidade": 16.0, "raio": 0.3,
        "vida": 1.5, "cor": (200, 20, 20), "custo": 10.0, "cooldown": 2.5,
        "efeito": "SANGRANDO", "elemento": "SANGUE", "multi_shot": 3,
        "descricao": "Dispara 3 lâminas de sangue"
    },
    "Lâmina de Sangue": {
        "tipo": "PROJETIL", "dano": 25.0, "velocidade": 16.0, "raio": 0.4,
        "vida": 0.6, "cor": (180, 0, 30), "custo": 15.0, "cooldown": 4.5,
        "efeito": "SANGRANDO", "elemento": "SANGUE",
        "descricao": "Corte que causa sangramento"
    },
    "Pacto de Sangue": {
        "tipo": "BUFF", "cor": (150, 0, 50), "custo": 0, "cooldown": 30.0,
        "custo_vida": 30.0, "elemento": "SANGUE",
        "duracao": 10.0, "bonus_dano": 1.8, "lifesteal": 0.2,
        "descricao": "Sacrifica HP por poder - lifesteal e dano"
    },
    "Ritual de Sangue": {
        "tipo": "CHANNEL", "cor": (200, 0, 50), "custo": 0, "cooldown": 25.0,
        "custo_vida_percent": 0.2, "elemento": "SANGUE",
        "canalizavel": True, "duracao_max": 3.0, "dano_por_segundo": 60.0,
        "imobiliza": True,
        "descricao": "Canaliza HP em dano massivo ao redor"
    },
    "Sanguessuga": {
        "tipo": "PROJETIL", "dano": 25.0, "velocidade": 10.0, "raio": 0.5,
        "vida": 3.0, "cor": (150, 0, 40), "custo": 22.0, "cooldown": 8.0,
        "efeito": "DRENAR", "elemento": "SANGUE", "lifesteal": 0.5,
        "homing": True,
        "descricao": "Projétil rastreador que drena vida massivamente"
    },
    "Transfusão": {
        "tipo": "BUFF", "cor": (200, 50, 50), "custo": 0, "cooldown": 18.0,
        "custo_vida": 20.0, "duracao": 8.0, "elemento": "SANGUE",
        "cura_por_segundo": 8.0, "bonus_velocidade_movimento": 1.3,
        "descricao": "Sacrifica HP por regeneração contínua e velocidade"
    },
    "Transfusão Forçada": {
        "tipo": "BEAM", "dano": 15.0, "alcance": 7.0, "cor": (180, 0, 50),
        "custo": 0, "cooldown": 15.0, "custo_vida": 30.0, "elemento": "SANGUE",
        "lifesteal": 0.6, "canalizavel": True, "dano_por_segundo": 35.0,
        "duracao_max": 3.0,
        "descricao": "Sacrifica HP para drenar massivamente a vida do inimigo"
    },
}
