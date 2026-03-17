"""
NEURAL FIGHTS â€” Skills: ðŸ•³ï¸ VOID
==================================
AniquilaÃ§Ã£o, silÃªncio, marcaÃ§Ã£o, absorÃ§Ã£o

Importado automaticamente por nucleo/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utilitarios.config import PPM


SKILLS_VOID = {
    "AbsorÃ§Ã£o do Vazio": {
        "tipo": "BUFF", "cor": (30, 0, 50), "custo": 22.0, "cooldown": 15.0,
        "duracao": 5.0, "elemento": "VOID",
        "escudo": 60.0, "reflete_projeteis": True,
        "descricao": "Escudo de vazio que absorve e reflete projÃ©teis"
    },
    "AniquilaÃ§Ã£o": {
        "tipo": "AREA", "dano": 90.0, "raio_area": 2.5, "cor": (10, 0, 20),
        "custo": 60.0, "cooldown": 35.0, "efeito": "VULNERAVEL", "elemento": "VOID",
        "delay": 2.0, "aviso_visual": True,
        "descricao": "DestruiÃ§Ã£o total do vazio apÃ³s 2s de carga"
    },
    "Anomalia Espacial": {
        "tipo": "SUMMON", "cor": (40, 0, 65), "custo": 50.0, "cooldown": 35.0,
        "duracao": 15.0, "summon_vida": 100.0, "summon_dano": 15.0,
        "elemento": "VOID", "efeito": "SILENCIADO",
        "aura_dano": 5.0, "aura_raio": 3.0,
        "descricao": "Invoca uma anomalia que silencia e drena numa grande Ã¡rea"
    },
    "Colapso do Vazio": {
        "tipo": "AREA", "dano": 70.0, "raio_area": 3.5, "cor": (15, 0, 30),
        "custo": 55.0, "cooldown": 28.0, "efeito": "VULNERAVEL", "elemento": "VOID",
        "delay": 2.5, "aviso_visual": True, "puxa_para_centro": True,
        "descricao": "Concentra energia void que implode apÃ³s longo carregamento"
    },
    "Deslocamento Void": {
        "tipo": "DASH", "distancia": 7.0, "cor": (50, 0, 80),
        "custo": 20.0, "cooldown": 8.0, "elemento": "VOID",
        "invencivel": True, "dano_chegada": 20.0,
        "descricao": "Teleporta pelo vazio, dano na chegada"
    },
    "Devorar": {
        "tipo": "BEAM", "dano": 35.0, "alcance": 6.0, "cor": (30, 0, 50),
        "custo": 30.0, "cooldown": 12.0, "efeito": "DRENAR", "elemento": "VOID",
        "penetra_escudo": True, "lifesteal": 0.3,
        "canalizavel": True, "dano_por_segundo": 40.0, "duracao_max": 2.0,
        "descricao": "Raio que devora a essÃªncia do alvo ignorando defesas"
    },
    "Forma do Vazio": {
        "tipo": "TRANSFORM", "cor": (30, 0, 50), "custo": 50.0, "cooldown": 45.0,
        "duracao": 10.0, "elemento": "VOID",
        "intangivel": True, "bonus_velocidade": 1.5, "dano_contato": 18.0,
        "descricao": "Transforma em ser do vazio - intangÃ­vel e mortal"
    },
    "Fragmento do Vazio": {
        "tipo": "PROJETIL", "dano": 20.0, "velocidade": 14.0, "raio": 0.35,
        "vida": 2.0, "cor": (40, 0, 60), "custo": 12.0, "cooldown": 3.0,
        "efeito": "SILENCIADO", "elemento": "VOID",
        "descricao": "EstilhaÃ§o do vazio que silencia"
    },
    "ImplosÃ£o": {
        "tipo": "AREA", "dano": 45.0, "raio_area": 3.0, "cor": (20, 0, 40),
        "custo": 32.0, "cooldown": 12.0, "efeito": "PUXADO", "elemento": "VOID",
        "puxa_para_centro": True,
        "descricao": "Puxa todos para o centro e causa dano"
    },
    "Marca do Vazio": {
        "tipo": "PROJETIL", "dano": 15.0, "velocidade": 18.0, "raio": 0.3,
        "vida": 2.0, "cor": (50, 10, 70), "custo": 18.0, "cooldown": 6.0,
        "efeito": "MARCADO", "elemento": "VOID",
        "descricao": "Marca o alvo â€” prÃ³ximo ataque void causa dano dobrado"
    },
    "Nulificar": {
        "tipo": "AREA", "dano": 0.0, "raio_area": 4.0, "cor": (40, 0, 60),
        "custo": 28.0, "cooldown": 18.0, "efeito": "SILENCIADO", "elemento": "VOID",
        "duracao": 3.0,
        "descricao": "Ãrea que anula toda magia"
    },
    "Portal do Vazio": {
        "tipo": "SUMMON", "cor": (40, 0, 60), "custo": 45.0, "cooldown": 30.0,
        "duracao": 12.0, "summon_vida": 80.0, "summon_dano": 12.0,
        "elemento": "VOID", "efeito": "LENTO",
        "aura_dano": 3.0, "aura_raio": 2.5,
        "descricao": "Invoca uma entidade do vazio que drena e retarda"
    },
    "Rasgo Dimensional": {
        "tipo": "BEAM", "dano": 30.0, "alcance": 9.0, "cor": (60, 0, 90),
        "custo": 25.0, "cooldown": 8.0, "efeito": "VULNERAVEL", "elemento": "VOID",
        "penetra_escudo": True,
        "descricao": "Raio que ignora defesas e expÃµe o alvo"
    },
    "SentenÃ§a do Vazio": {
        "tipo": "PROJETIL", "dano": 55.0, "velocidade": 8.0, "raio": 0.6,
        "vida": 3.0, "cor": (30, 0, 50), "custo": 38.0, "cooldown": 15.0,
        "efeito": "MALDITO", "elemento": "VOID",
        "condicao": "ALVO_BAIXA_VIDA", "dano_bonus_condicao": 1.5,
        "descricao": "Esfera lenta e mortal - bÃ´nus contra alvos fracos"
    },
    "TentÃ¡culos do Vazio": {
        "tipo": "AREA", "dano": 15.0, "raio_area": 3.0, "cor": (30, 0, 50),
        "custo": 30.0, "cooldown": 10.0, "efeito": "ENRAIZADO", "elemento": "VOID",
        "duracao": 3.0, "dano_tick": 8.0,
        "descricao": "TentÃ¡culos que prendem e causam dano"
    },
}

