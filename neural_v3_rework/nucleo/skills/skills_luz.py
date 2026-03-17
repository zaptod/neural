"""
NEURAL FIGHTS â€” Skills: âœ¨ LUZ
=================================
Cura, purify, dano a mortos-vivos, escudos

Importado automaticamente por nucleo/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utilitarios.config import PPM


SKILLS_LUZ = {
    "Anjo GuardiÃ£o": {
        "tipo": "BUFF", "cor": (255, 255, 220), "custo": 60.0, "cooldown": 60.0,
        "duracao": 15.0, "elemento": "LUZ",
        "efeito_buff": "IMORTAL", "duracao_imortal": 3.0,
        "descricao": "Previne morte uma vez (HP mÃ­nimo 1)"
    },
    "Aura Sagrada": {
        "tipo": "CHANNEL", "cor": (255, 255, 180), "custo": 30.0, "cooldown": 20.0,
        "elemento": "LUZ", "canalizavel": True, "duracao_max": 4.0,
        "cura_por_segundo": 20.0, "imobiliza": True,
        "descricao": "Canaliza aura curativa intensa"
    },
    "Barreira Divina": {
        "tipo": "BUFF", "cor": (255, 255, 180), "custo": 35.0, "cooldown": 18.0,
        "duracao": 5.0, "elemento": "LUZ",
        "escudo": 50.0, "reflete_dano": 0.3,
        "descricao": "Escudo que reflete 30% do dano"
    },
    "BenÃ§Ã£o": {
        "tipo": "BUFF", "cor": (255, 255, 200), "custo": 20.0, "cooldown": 20.0,
        "duracao": 10.0, "elemento": "LUZ",
        "efeito_buff": "ABENÃ‡OADO",
        "descricao": "BÃªnÃ§Ã£o que aumenta cura e regenera"
    },
    "Cura Maior": {
        "tipo": "BUFF", "cor": (150, 255, 200), "custo": 45.0, "cooldown": 25.0,
        "cura": 60.0, "remove_debuffs": 2, "elemento": "LUZ",
        "descricao": "Cura massiva + remove 2 debuffs"
    },
    "Cura Menor": {
        "tipo": "BUFF", "cor": (100, 255, 150), "custo": 25.0, "cooldown": 15.0,
        "cura": 25.0, "elemento": "LUZ",
        "descricao": "Recupera vida instantaneamente"
    },
    "Julgamento Celestial": {
        "tipo": "AREA", "dano": 80.0, "raio_area": 3.0, "cor": (255, 255, 200),
        "custo": 55.0, "cooldown": 30.0, "efeito": "CEGO", "elemento": "LUZ",
        "delay": 2.0, "pilares": 5,
        "descricao": "5 pilares de luz caem do cÃ©u"
    },
    "LanÃ§a de Luz": {
        "tipo": "PROJETIL", "dano": 22.0, "velocidade": 28.0, "raio": 0.25,
        "vida": 1.0, "cor": (255, 255, 200), "custo": 14.0, "cooldown": 3.0,
        "efeito": "CEGO", "elemento": "LUZ", "perfura": True,
        "descricao": "LanÃ§a de luz rÃ¡pida que perfura e cega"
    },
    "PrisÃ£o de Luz": {
        "tipo": "TRAP", "dano": 20.0, "cor": (255, 255, 180),
        "custo": 25.0, "cooldown": 15.0, "elemento": "LUZ",
        "duracao": 8.0, "efeito": "CEGO", "vida_estrutura": 50.0,
        "bloqueia_movimento": False,
        "descricao": "Armadilha de luz que cega e danifica quem ativar"
    },
    "Purificar": {
        "tipo": "BUFF", "cor": (255, 255, 255), "custo": 30.0, "cooldown": 12.0,
        "elemento": "LUZ", "remove_todos_debuffs": True, "imune_debuffs": 3.0,
        "descricao": "Remove TODOS debuffs + imunidade"
    },
    "Raio Sagrado": {
        "tipo": "BEAM", "dano": 25.0, "alcance": 10.0, "cor": (255, 255, 220),
        "custo": 18.0, "cooldown": 5.0, "efeito": "CEGO", "elemento": "LUZ",
        "bonus_vs_trevas": 2.0,
        "descricao": "Raio de luz que cega"
    },
    "RedenÃ§Ã£o": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 4.0, "cor": (255, 255, 200),
        "custo": 40.0, "cooldown": 25.0, "elemento": "LUZ",
        "cura": 50.0, "remove_debuffs": True,
        "descricao": "Pulso de luz que cura aliados e remove todos os debuffs"
    },
    "RessurreiÃ§Ã£o": {
        "tipo": "BUFF", "cor": (255, 255, 255), "custo": 80.0, "cooldown": 120.0,
        "duracao": 30.0, "elemento": "LUZ",
        "ativa_ao_morrer": True, "cura_percent": 0.3,
        "descricao": "Revive com 30% HP ao morrer (buff passivo)"
    },
    "Smite": {
        "tipo": "PROJETIL", "dano": 40.0, "velocidade": 25.0, "raio": 0.3,
        "vida": 1.0, "cor": (255, 255, 150), "custo": 22.0, "cooldown": 6.0,
        "efeito": "EXPOSTO", "elemento": "LUZ",
        "bonus_vs_trevas": 1.5,
        "descricao": "Castigo divino - extra contra trevas"
    },
}

