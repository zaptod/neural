"""
NEURAL FIGHTS - Sistema de Skills
Catálogo de todas as habilidades do jogo.
"""

from config import PPM

# ============================================================================
# CATÁLOGO MASTER DE HABILIDADES
# ============================================================================
# Tipos: PROJETIL, BUFF, AREA, DASH, SUMMON, BEAM
# Efeitos: NORMAL, EMPURRAO, SANGRAMENTO, VENENO, EXPLOSAO, CONGELAR, 
#          ATORDOAR, QUEIMAR, DRENAR, PERFURAR
# ============================================================================

SKILL_DB = {
    "Nenhuma": {
        "custo": 0, "cooldown": 0, "tipo": "NADA"
    },
    
    # =========================================================================
    # 🔥 FOGO
    # =========================================================================
    "Bola de Fogo": {
        "tipo": "PROJETIL", "dano": 35.0, "velocidade": 11.0, "raio": 0.5,
        "vida": 2.0, "cor": (255, 100, 0), "custo": 25.0, "cooldown": 5.0,
        "efeito": "EXPLOSAO", "descricao": "Esfera flamejante que explode no impacto"
    },
    "Meteoro": {
        "tipo": "PROJETIL", "dano": 60.0, "velocidade": 8.0, "raio": 0.8,
        "vida": 2.5, "cor": (255, 50, 0), "custo": 40.0, "cooldown": 10.0,
        "efeito": "EXPLOSAO", "descricao": "Rocha incandescente devastadora"
    },
    "Lança de Fogo": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 25.0, "raio": 0.25,
        "vida": 1.0, "cor": (255, 150, 50), "custo": 12.0, "cooldown": 2.5,
        "efeito": "QUEIMAR", "descricao": "Projétil rápido que causa queimadura"
    },
    "Explosão Nova": {
        "tipo": "AREA", "dano": 45.0, "raio_area": 3.0, "cor": (255, 200, 50),
        "custo": 35.0, "cooldown": 12.0, "efeito": "EMPURRAO",
        "descricao": "Explosão ao redor do conjurador"
    },
    
    # =========================================================================
    # ❄️ GELO
    # =========================================================================
    "Estilhaço de Gelo": {
        "tipo": "PROJETIL", "dano": 15.0, "velocidade": 18.0, "raio": 0.3,
        "vida": 1.8, "cor": (150, 220, 255), "custo": 10.0, "cooldown": 2.0,
        "efeito": "CONGELAR", "descricao": "Fragmento gélido que desacelera"
    },
    "Lança de Gelo": {
        "tipo": "PROJETIL", "dano": 28.0, "velocidade": 22.0, "raio": 0.35,
        "vida": 1.5, "cor": (100, 200, 255), "custo": 18.0, "cooldown": 4.0,
        "efeito": "PERFURAR", "descricao": "Lança perfurante de gelo puro"
    },
    "Nevasca": {
        "tipo": "AREA", "dano": 8.0, "raio_area": 4.0, "cor": (200, 230, 255),
        "custo": 30.0, "cooldown": 15.0, "efeito": "CONGELAR", "duracao": 3.0,
        "descricao": "Área de gelo que causa slow contínuo"
    },
    "Prisão de Gelo": {
        "tipo": "PROJETIL", "dano": 5.0, "velocidade": 15.0, "raio": 0.4,
        "vida": 2.0, "cor": (180, 240, 255), "custo": 22.0, "cooldown": 8.0,
        "efeito": "ATORDOAR", "descricao": "Aprisiona o alvo brevemente"
    },
    
    # =========================================================================
    # ⚡ RAIO
    # =========================================================================
    "Relâmpago": {
        "tipo": "BEAM", "dano": 22.0, "alcance": 8.0, "cor": (255, 255, 100),
        "custo": 15.0, "cooldown": 3.0, "efeito": "ATORDOAR",
        "descricao": "Raio instantâneo que atordoa"
    },
    "Corrente Elétrica": {
        "tipo": "PROJETIL", "dano": 12.0, "velocidade": 30.0, "raio": 0.2,
        "vida": 0.8, "cor": (255, 255, 150), "custo": 8.0, "cooldown": 1.0,
        "efeito": "NORMAL", "descricao": "Disparo elétrico ultra-rápido"
    },
    "Tempestade": {
        "tipo": "AREA", "dano": 40.0, "raio_area": 5.0, "cor": (200, 200, 255),
        "custo": 45.0, "cooldown": 18.0, "efeito": "ATORDOAR",
        "descricao": "Devastação elétrica em grande área"
    },
    "Teleporte Relâmpago": {
        "tipo": "DASH", "distancia": 5.0, "cor": (255, 255, 200),
        "custo": 20.0, "cooldown": 6.0, "efeito": "NORMAL", "invencivel": True,
        "descricao": "Teleporta instantaneamente"
    },
    
    # =========================================================================
    # 🌑 TREVAS
    # =========================================================================
    "Esfera Sombria": {
        "tipo": "PROJETIL", "dano": 18.0, "velocidade": 12.0, "raio": 0.45,
        "vida": 2.5, "cor": (80, 0, 120), "custo": 14.0, "cooldown": 3.0,
        "efeito": "DRENAR", "descricao": "Drena vida do alvo"
    },
    "Lâmina de Sangue": {
        "tipo": "PROJETIL", "dano": 25.0, "velocidade": 16.0, "raio": 0.4,
        "vida": 0.6, "cor": (180, 0, 30), "custo": 15.0, "cooldown": 4.5,
        "efeito": "SANGRAMENTO", "descricao": "Corte que causa sangramento"
    },
    "Maldição": {
        "tipo": "PROJETIL", "dano": 8.0, "velocidade": 10.0, "raio": 0.5,
        "vida": 3.0, "cor": (100, 0, 100), "custo": 20.0, "cooldown": 10.0,
        "efeito": "VENENO", "dot_dano": 5.0, "dot_duracao": 5.0,
        "descricao": "Maldição que causa dano ao longo do tempo"
    },
    "Explosão Necrótica": {
        "tipo": "AREA", "dano": 30.0, "raio_area": 2.5, "cor": (60, 0, 80),
        "custo": 28.0, "cooldown": 9.0, "efeito": "DRENAR",
        "descricao": "Explosão que drena vida de todos ao redor"
    },
    
    # =========================================================================
    # 💚 NATUREZA/VENENO
    # =========================================================================
    "Dardo Venenoso": {
        "tipo": "PROJETIL", "dano": 5.0, "velocidade": 22.0, "raio": 0.15,
        "vida": 1.5, "cor": (100, 255, 100), "custo": 10.0, "cooldown": 2.0,
        "efeito": "VENENO", "descricao": "Dardo rápido com veneno potente"
    },
    "Nuvem Tóxica": {
        "tipo": "AREA", "dano": 5.0, "raio_area": 3.5, "cor": (150, 200, 50),
        "custo": 25.0, "cooldown": 12.0, "efeito": "VENENO", "duracao": 4.0,
        "descricao": "Nuvem persistente de veneno"
    },
    "Espinhos": {
        "tipo": "PROJETIL", "dano": 12.0, "velocidade": 20.0, "raio": 0.2,
        "vida": 1.2, "cor": (80, 150, 50), "custo": 8.0, "cooldown": 1.5,
        "efeito": "SANGRAMENTO", "multi_shot": 3,
        "descricao": "Dispara 3 espinhos em leque"
    },
    "Raízes": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 2.0, "cor": (100, 80, 50),
        "custo": 18.0, "cooldown": 8.0, "efeito": "ATORDOAR", "duracao": 2.0,
        "descricao": "Prende inimigos no lugar"
    },
    
    # =========================================================================
    # ⚔️ FÍSICO/MARCIAL
    # =========================================================================
    "Impacto Sônico": {
        "tipo": "PROJETIL", "dano": 18.0, "velocidade": 20.0, "raio": 0.6,
        "vida": 0.35, "cor": (200, 200, 255), "custo": 12.0, "cooldown": 3.0,
        "efeito": "EMPURRAO", "descricao": "Onda de choque curta mas poderosa"
    },
    "Avanço Brutal": {
        "tipo": "DASH", "dano": 25.0, "distancia": 4.0, "cor": (255, 100, 100),
        "custo": 15.0, "cooldown": 5.0, "efeito": "EMPURRAO",
        "descricao": "Avança causando dano no caminho"
    },
    "Fúria Giratória": {
        "tipo": "AREA", "dano": 20.0, "raio_area": 2.0, "cor": (200, 150, 150),
        "custo": 18.0, "cooldown": 6.0, "efeito": "NORMAL",
        "descricao": "Gira a arma atingindo todos ao redor"
    },
    "Golpe do Executor": {
        "tipo": "BUFF", "cor": (150, 0, 0), "custo": 20.0, "cooldown": 15.0,
        "duracao": 3.0, "buff_dano": 2.0,
        "descricao": "Próximo ataque causa dano dobrado"
    },
    
    # =========================================================================
    # 🛡️ DEFESA/SUPORTE
    # =========================================================================
    "Escudo Arcano": {
        "tipo": "BUFF", "cor": (100, 150, 255), "custo": 20.0, "cooldown": 12.0,
        "duracao": 5.0, "escudo": 30.0,
        "descricao": "Cria um escudo absorvente"
    },
    "Cura Menor": {
        "tipo": "BUFF", "cor": (100, 255, 150), "custo": 25.0, "cooldown": 15.0,
        "cura": 25.0, "descricao": "Recupera vida instantaneamente"
    },
    "Reflexo Espelhado": {
        "tipo": "BUFF", "cor": (200, 200, 255), "custo": 30.0, "cooldown": 20.0,
        "duracao": 3.0, "refletir": 0.5,
        "descricao": "Reflete 50% do dano recebido"
    },
    "Velocidade Arcana": {
        "tipo": "BUFF", "cor": (255, 255, 150), "custo": 15.0, "cooldown": 10.0,
        "duracao": 4.0, "buff_velocidade": 1.5,
        "descricao": "Aumenta velocidade de movimento"
    },
    
    # =========================================================================
    # 💀 ESPECIAIS
    # =========================================================================
    "Disparo de Mana": {
        "tipo": "PROJETIL", "dano": 10.0, "velocidade": 14.0, "raio": 0.3,
        "vida": 2.5, "cor": (50, 150, 255), "custo": 8.0, "cooldown": 1.5,
        "efeito": "NORMAL", "descricao": "Projétil básico de mana pura"
    },
    "Invocação: Espírito": {
        "tipo": "SUMMON", "cor": (180, 180, 255), "custo": 35.0, "cooldown": 25.0,
        "duracao": 10.0, "summon_vida": 50.0, "summon_dano": 8.0,
        "descricao": "Invoca um espírito aliado"
    },
    "Troca de Almas": {
        "tipo": "DASH", "distancia": 0.0, "cor": (150, 0, 150),
        "custo": 40.0, "cooldown": 30.0, "efeito": "TROCAR_POS",
        "descricao": "Troca de posição com o alvo"
    },
    "Execução": {
        "tipo": "PROJETIL", "dano": 100.0, "velocidade": 8.0, "raio": 0.3,
        "vida": 1.5, "cor": (255, 0, 0), "custo": 50.0, "cooldown": 30.0,
        "efeito": "NORMAL", "condicao": "alvo_baixa_vida",
        "descricao": "Dano massivo contra alvos com pouca vida"
    },
}


def get_skill_data(nome):
    """Retorna os dados de uma skill pelo nome"""
    return SKILL_DB.get(nome, SKILL_DB["Nenhuma"])


def get_skills_by_tipo(tipo):
    """Retorna todas as skills de um determinado tipo"""
    return {k: v for k, v in SKILL_DB.items() if v.get("tipo") == tipo}


def get_skills_by_elemento(elemento):
    """Retorna skills por elemento baseado na cor"""
    elementos = {
        "FOGO": [(255, 100, 0), (255, 50, 0), (255, 150, 50), (255, 200, 50)],
        "GELO": [(150, 220, 255), (100, 200, 255), (200, 230, 255), (180, 240, 255)],
        "RAIO": [(255, 255, 100), (255, 255, 150), (200, 200, 255), (255, 255, 200)],
        "TREVAS": [(80, 0, 120), (180, 0, 30), (100, 0, 100), (60, 0, 80)],
        "NATUREZA": [(100, 255, 100), (150, 200, 50), (80, 150, 50), (100, 80, 50)],
    }
    cores = elementos.get(elemento, [])
    return {k: v for k, v in SKILL_DB.items() if v.get("cor") in cores}


def listar_skills_para_ui():
    """Retorna lista formatada para ComboBox"""
    return list(SKILL_DB.keys())
