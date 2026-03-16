"""
NEURAL FIGHTS — Skills: ⚡ RAIO
==================================
Velocidade, chain, stun, paralisia

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_RAIO = {
    "Armadilha Elétrica": {
        "tipo": "TRAP", "dano": 20.0, "cor": (255, 255, 120),
        "custo": 18.0, "cooldown": 10.0, "elemento": "RAIO",
        "duracao": 10.0, "efeito": "PARALISIA", "vida_estrutura": 35.0,
        "bloqueia_movimento": False,
        "descricao": "Armadilha que paralisa quem pisar"
    },
    "Campo Elétrico": {
        "tipo": "AREA", "dano": 8.0, "raio_area": 3.0, "cor": (200, 200, 255),
        "custo": 28.0, "cooldown": 12.0, "efeito": "PARALISIA", "elemento": "RAIO",
        "duracao": 4.0, "chance_stun": 0.3,
        "descricao": "Campo que causa stun aleatório"
    },
    "Corrente Elétrica": {
        "tipo": "PROJETIL", "dano": 12.0, "velocidade": 30.0, "raio": 0.2,
        "vida": 0.8, "cor": (255, 255, 150), "custo": 8.0, "cooldown": 1.0,
        "elemento": "RAIO",  # B5 fix: removido "efeito": "NORMAL" (status inexistente)
        "descricao": "Disparo elétrico ultra-rápido"
    },
    "Corrente em Cadeia": {
        "tipo": "BEAM", "dano": 18.0, "alcance": 10.0, "cor": (255, 255, 120),
        "custo": 25.0, "cooldown": 8.0, "efeito": "PARALISIA", "elemento": "RAIO",
        "chain": 4, "chain_decay": 0.8,
        "descricao": "Raio que salta entre até 4 alvos"
    },
    "Forma Relâmpago": {
        "tipo": "TRANSFORM", "cor": (255, 255, 150), "custo": 45.0, "cooldown": 40.0,
        "duracao": 8.0, "elemento": "RAIO",
        "bonus_velocidade": 2.0, "intangivel": True, "dano_contato": 20.0,
        "descricao": "Transforma em raio puro - atravessa inimigos"
    },
    "Indução Magnética": {
        "tipo": "PROJETIL", "dano": 15.0, "velocidade": 25.0, "raio": 0.3,
        "vida": 1.0, "cor": (200, 200, 255), "custo": 14.0, "cooldown": 3.5,
        "efeito": "PARALISIA", "elemento": "RAIO",
        "chain": 4, "chain_decay": 0.75,
        "descricao": "Pulso eletromagnético que salta entre alvos metálicos"
    },
    "Julgamento de Thor": {
        "tipo": "AREA", "dano": 100.0, "raio_area": 2.0, "cor": (255, 255, 200),
        "custo": 60.0, "cooldown": 30.0, "efeito": "PARALISIA", "elemento": "RAIO",
        "delay": 1.5, "aviso_visual": True,
        "descricao": "Raio massivo do céu após 1.5s"
    },
    "Mjolnir": {
        "tipo": "PROJETIL", "dano": 70.0, "velocidade": 15.0, "raio": 0.6,
        "vida": 2.0, "cor": (255, 255, 150), "custo": 45.0, "cooldown": 15.0,
        "efeito": "KNOCK_UP", "elemento": "RAIO", "retorna": True,
        "descricao": "Martelo de raio que retorna"
    },
    "Relâmpago": {
        "tipo": "BEAM", "dano": 22.0, "alcance": 8.0, "cor": (255, 255, 100),
        "custo": 15.0, "cooldown": 3.0, "efeito": "PARALISIA", "elemento": "RAIO",
        "descricao": "Raio instantâneo que paralisa"
    },
    "Sobrecarga": {
        "tipo": "BUFF", "cor": (255, 255, 100), "custo": 20.0, "cooldown": 15.0,
        "duracao": 6.0, "elemento": "RAIO",
        "bonus_velocidade_ataque": 1.5, "bonus_velocidade_movimento": 1.3,
        "dano_recebido_bonus": 1.2,
        "descricao": "Acelera drasticamente mas recebe mais dano"
    },
    "Teleporte Relâmpago": {
        "tipo": "DASH", "distancia": 5.0, "cor": (255, 255, 200),
        "custo": 20.0, "cooldown": 6.0, "elemento": "RAIO",
        "invencivel": True, "dano_chegada": 15.0,
        "descricao": "Teleporta instantaneamente, causa dano na chegada"
    },
    "Tempestade": {
        "tipo": "AREA", "dano": 40.0, "raio_area": 5.0, "cor": (200, 200, 255),
        "custo": 45.0, "cooldown": 18.0, "efeito": "PARALISIA", "elemento": "RAIO",
        "descricao": "Devastação elétrica em grande área"
    },
    "Tempestade Ascendente": {
        "tipo": "CHANNEL", "cor": (255, 255, 200), "custo": 45.0, "cooldown": 25.0,
        "elemento": "RAIO", "canalizavel": True, "duracao_max": 3.0,
        "dano_por_segundo": 50.0, "imobiliza": True,
        "descricao": "Canaliza uma tempestade elétrica devastadora ao redor"
    },
}
