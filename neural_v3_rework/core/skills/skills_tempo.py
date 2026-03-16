"""
NEURAL FIGHTS — Skills: 🌀 TEMPO
===================================
Slow, haste, reset de cooldown, reversão

Importado automaticamente por core/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utils.config import PPM


SKILLS_TEMPO = {
    "Acelerar": {
        "tipo": "BUFF", "cor": (255, 200, 150), "custo": 20.0, "cooldown": 12.0,
        "duracao": 5.0, "elemento": "TEMPO",
        "efeito_buff": "ACELERADO", "bonus_velocidade": 1.8,
        "descricao": "Acelera muito o movimento"
    },
    "Aceleração Fatal": {
        "tipo": "BUFF", "cor": (220, 200, 255), "custo": 25.0, "cooldown": 22.0,
        "duracao": 6.0, "elemento": "TEMPO",
        "bonus_velocidade_ataque": 2.5, "bonus_velocidade_movimento": 2.0,
        "dano_recebido_bonus": 1.3,
        "descricao": "Velocidade extrema ao custo de fragilidade"
    },
    "Armadilha Temporal": {
        "tipo": "TRAP", "dano": 0.0, "cor": (200, 180, 255),
        "custo": 20.0, "cooldown": 12.0, "elemento": "TEMPO",
        "duracao": 10.0, "efeito": "TEMPO_PARADO", "vida_estrutura": 30.0,
        "bloqueia_movimento": False,
        "descricao": "Armadilha que para o tempo de quem pisar"
    },
    "Dilatação Temporal": {
        "tipo": "BUFF", "cor": (190, 170, 255), "custo": 30.0, "cooldown": 20.0,
        "duracao": 6.0, "elemento": "TEMPO",
        "bonus_velocidade_ataque": 2.0, "bonus_velocidade_movimento": 1.6,
        "descricao": "Distorce o tempo pessoal - tudo mais rápido"
    },
    "Eco Temporal": {
        "tipo": "PROJETIL", "dano": 25.0, "velocidade": 15.0, "raio": 0.4,
        "vida": 2.0, "cor": (200, 180, 255), "custo": 30.0, "cooldown": 10.0,
        "elemento": "TEMPO", "duplica_apos": 1.0,
        "descricao": "Projétil que duplica após 1s"
    },
    "Envelhecimento": {
        "tipo": "BEAM", "dano": 20.0, "alcance": 7.0, "cor": (150, 130, 200),
        "custo": 28.0, "cooldown": 12.0, "efeito": "EXAUSTO", "elemento": "TEMPO",
        "dano_por_segundo": 25.0, "canalizavel": True, "duracao_max": 2.5,
        "descricao": "Raio que envelhece o alvo reduzindo seus atributos"
    },
    "Estase": {
        "tipo": "AREA", "dano": 15.0, "raio_area": 3.5, "cor": (190, 170, 255),
        "custo": 35.0, "cooldown": 18.0, "efeito": "TEMPO_PARADO", "elemento": "TEMPO",
        "duracao": 2.0, "delay": 0.5,
        "descricao": "Bolha que congela o tempo em uma area"
    },
    "Idade Acelerada": {
        "tipo": "PROJETIL", "dano": 30.0, "velocidade": 10.0, "raio": 0.5,
        "vida": 2.5, "cor": (150, 130, 200), "custo": 35.0, "cooldown": 15.0,
        "efeito": "EXAUSTO", "elemento": "TEMPO",
        "descricao": "Envelhece o alvo temporariamente"
    },
    "Paradoxo": {
        "tipo": "PROJETIL", "dano": 35.0, "velocidade": 5.0, "raio": 0.5,
        "vida": 4.0, "cor": (210, 190, 255), "custo": 28.0, "cooldown": 10.0,
        "elemento": "TEMPO", "efeito": "LENTO",
        "duplica_apos": 1.5,
        "descricao": "Projétil temporal lento que se duplica"
    },
    "Parar o Tempo": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 5.0, "cor": (220, 200, 255),
        "custo": 50.0, "cooldown": 45.0, "efeito": "TEMPO_PARADO", "elemento": "TEMPO",
        "duracao_stop": 2.0, "afeta_caster": False,
        "descricao": "Para o tempo para inimigos"
    },
    "Previsão": {
        "tipo": "BUFF", "cor": (180, 180, 255), "custo": 15.0, "cooldown": 20.0,
        "duracao": 6.0, "elemento": "TEMPO",
        "esquiva_garantida": 3, "ve_ataques": True,
        "descricao": "Vê o futuro - esquiva os próximos 3 ataques"
    },
    "Rebobinar": {
        "tipo": "BUFF", "cor": (200, 180, 255), "custo": 45.0, "cooldown": 40.0,
        "duracao": 0.1, "elemento": "TEMPO",
        "cura_percent": 0.3, "remove_debuffs": True,
        "descricao": "Rebobina o tempo pessoal recuperando HP e removendo debuffs"
    },
    "Reverter": {
        "tipo": "BUFF", "cor": (200, 150, 255), "custo": 40.0, "cooldown": 30.0,
        "duracao": 6.0, "elemento": "TEMPO",
        "cura": 40.0, "bonus_velocidade": 1.5,
        "descricao": "Regenera HP e acelera temporariamente"
    },
    "Ricochete Temporal": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 16.0, "raio": 0.35,
        "vida": 3.0, "cor": (210, 195, 255), "custo": 22.0, "cooldown": 7.0,
        "elemento": "TEMPO", "chain": 3, "chain_decay": 0.8,
        "descricao": "Projétil que salta entre alvos corrigindo o passado"
    },
    "Slow Motion": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 4.0, "cor": (200, 180, 255),
        "custo": 25.0, "cooldown": 15.0, "efeito": "LENTO", "elemento": "TEMPO",
        "slow_fator": 0.3, "duracao": 3.0,
        "descricao": "Desacelera o tempo na área"
    },
}
