# skills.py
from config import *

# Catálogo de Habilidades
# Tipo: 'PROJETIL', 'BUFF', 'AREA', 'DASH'
SKILL_DB = {
    "Nenhuma": {
        "custo": 0, "cooldown": 0, "tipo": "NADA"
    },
    
    # --- MAGIAS DE ARMA (PROJÉTEIS) ---
    "Impacto Sônico (Reta)": {
        "tipo": "PROJETIL",
        "dano": 18.0,
        "velocidade": 20.0,
        "raio": 0.6,
        "vida": 0.35,  # Alcance curto
        "cor": (200, 200, 255),
        "custo": 12.0,
        "cooldown": 3.0,
        "efeito": "EMPURRAO"
    },
    "Lâmina de Sangue (Reta)": {
        "tipo": "PROJETIL",
        "dano": 25.0,
        "velocidade": 16.0,
        "raio": 0.4,
        "vida": 0.6,
        "cor": (200, 0, 0),
        "custo": 15.0,
        "cooldown": 4.5,
        "efeito": "SANGRAMENTO"
    },
    "Disparo de Mana (Qualquer)": {
        "tipo": "PROJETIL",
        "dano": 10.0,
        "velocidade": 14.0,
        "raio": 0.3,
        "vida": 2.5,   # Alcance longo
        "cor": (50, 150, 255),
        "custo": 8.0,
        "cooldown": 1.5, # Spamável
        "efeito": "NORMAL"
    },
    "Bola de Fogo": {
        "tipo": "PROJETIL",
        "dano": 35.0,
        "velocidade": 11.0,
        "raio": 0.5,
        "vida": 2.0,
        "cor": (255, 100, 0),
        "custo": 25.0,
        "cooldown": 6.0,
        "efeito": "EXPLOSAO"
    },
    "Dardo Venenoso": {
        "tipo": "PROJETIL",
        "dano": 5.0,
        "velocidade": 22.0,
        "raio": 0.15,
        "vida": 1.5,
        "cor": (100, 255, 100),
        "custo": 10.0,
        "cooldown": 2.0,
        "efeito": "VENENO"
    }
}

def get_skill_data(nome):
    return SKILL_DB.get(nome, SKILL_DB["Nenhuma"])