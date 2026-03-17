"""
NEURAL FIGHTS â€” Skills: ðŸŒŒ GRAVITACAO
========================================
Pull, push, manipulaÃ§Ã£o gravitacional

Importado automaticamente por nucleo/skills/__init__.py.
Para editar uma skill, encontre-a neste arquivo e altere os valores.
"""

from utilitarios.config import PPM


SKILLS_GRAVITACAO = {
    "AscensÃ£o": {
        "tipo": "DASH", "distancia": 6.0, "cor": (120, 80, 180),
        "custo": 18.0, "cooldown": 8.0, "elemento": "GRAVITACAO",
        "invencivel": True,
        "descricao": "Anula a gravidade e voa na direÃ§Ã£o escolhida"
    },
    "Buraco Negro": {
        "tipo": "AREA", "dano": 10.0, "raio_area": 4.0, "cor": (20, 0, 40),
        "custo": 50.0, "cooldown": 30.0, "efeito": "VORTEX", "elemento": "GRAVITACAO",
        "duracao": 3.0, "dano_por_segundo": 25.0, "puxa_continuo": True,
        "descricao": "Buraco negro que suga e causa dano"
    },
    "Campo de Gravidade": {
        "tipo": "AREA", "dano": 5.0, "raio_area": 4.0, "cor": (80, 40, 120),
        "custo": 30.0, "cooldown": 15.0, "efeito": "LENTO", "elemento": "GRAVITACAO",
        "duracao": 5.0, "gravidade_aumentada": 3.0,
        "descricao": "Ãrea com gravidade tripla - slow e sem pulo"
    },
    "Colapso": {
        "tipo": "PROJETIL", "dano": 60.0, "velocidade": 8.0, "raio": 0.3,
        "vida": 3.0, "cor": (50, 20, 80), "custo": 40.0, "cooldown": 18.0,
        "efeito": "KNOCK_UP", "elemento": "GRAVITACAO",
        "delay_explosao": 2.0, "raio_explosao": 2.5,
        "descricao": "Esfera que implode apÃ³s 2s"
    },
    "CompressÃ£o": {
        "tipo": "PROJETIL", "dano": 45.0, "velocidade": 6.0, "raio": 0.6,
        "vida": 4.0, "cor": (80, 40, 130), "custo": 32.0, "cooldown": 12.0,
        "efeito": "LENTO", "elemento": "GRAVITACAO", "homing": True,
        "raio_explosao": 2.0,
        "descricao": "Esfera gravitacional lenta que implode ao impacto"
    },
    "Esmagamento": {
        "tipo": "AREA", "dano": 55.0, "raio_area": 2.0, "cor": (80, 40, 130),
        "custo": 35.0, "cooldown": 14.0, "efeito": "LENTO", "elemento": "GRAVITACAO",
        "delay": 1.0, "gravidade_aumentada": 5.0,
        "descricao": "Comprime a gravidade esmagando a Ã¡rea"
    },
    "InversÃ£o Gravitacional": {
        "tipo": "AREA", "dano": 25.0, "raio_area": 3.5, "cor": (130, 90, 200),
        "custo": 30.0, "cooldown": 14.0, "efeito": "KNOCK_UP", "elemento": "GRAVITACAO",
        "forca_empurrao": 3.0,
        "descricao": "Inverte a gravidade lanÃ§ando todos para cima"
    },
    "Lente Gravitacional": {
        "tipo": "BUFF", "cor": (100, 60, 160), "custo": 20.0, "cooldown": 16.0,
        "duracao": 5.0, "elemento": "GRAVITACAO",
        "refletir_projeteis": True, "bonus_velocidade": 1.3,
        "descricao": "Curva projÃ©teis ao redor do caster desviando-os"
    },
    "Levitar": {
        "tipo": "BUFF", "cor": (150, 100, 200), "custo": 15.0, "cooldown": 10.0,
        "duracao": 6.0, "elemento": "GRAVITACAO",
        "voo": True, "imune_ground": True,
        "descricao": "Flutua no ar - imune a efeitos terrestres"
    },
    "MarÃ© Gravitacional": {
        "tipo": "AREA", "dano": 20.0, "raio_area": 5.0, "cor": (70, 30, 120),
        "custo": 40.0, "cooldown": 18.0, "efeito": "EMPURRAO", "elemento": "GRAVITACAO",
        "ondas": 3, "forca_empurrao": 2.5,
        "descricao": "3 ondas de pulso gravitacional devastadoras"
    },
    "MÃ­ssil Gravitacional": {
        "tipo": "PROJETIL", "dano": 30.0, "velocidade": 12.0, "raio": 0.4,
        "vida": 2.5, "cor": (100, 50, 180), "custo": 20.0, "cooldown": 6.0,
        "efeito": "KNOCK_UP", "elemento": "GRAVITACAO", "homing": True,
        "descricao": "ProjÃ©til rastreador que lanÃ§a o alvo ao ar"
    },
    "Pulso Gravitacional": {
        "tipo": "AREA", "dano": 20.0, "raio_area": 3.0, "cor": (100, 50, 150),
        "custo": 20.0, "cooldown": 8.0, "efeito": "PUXADO", "elemento": "GRAVITACAO",
        "puxa_para_centro": True,
        "descricao": "Puxa inimigos para o centro"
    },
    "RepulsÃ£o": {
        "tipo": "AREA", "dano": 15.0, "raio_area": 2.5, "cor": (150, 100, 200),
        "custo": 18.0, "cooldown": 6.0, "efeito": "EMPURRAO", "elemento": "GRAVITACAO",
        "forca_empurrao": 2.0,
        "descricao": "Empurra todos para longe"
    },
    "Singularidade": {
        "tipo": "AREA", "dano": 35.0, "raio_area": 5.0, "cor": (60, 20, 100),
        "custo": 55.0, "cooldown": 30.0, "efeito": "VORTEX", "elemento": "GRAVITACAO",
        "duracao": 4.0, "dano_por_segundo": 20.0, "puxa_continuo": True,
        "descricao": "Cria uma singularidade que devora tudo ao redor"
    },
    "Ã“rbita Mortal": {
        "tipo": "CHANNEL", "cor": (110, 70, 170), "custo": 40.0, "cooldown": 25.0,
        "elemento": "GRAVITACAO", "canalizavel": True, "duracao_max": 4.0,
        "dano_por_segundo": 30.0, "imobiliza": True,
        "descricao": "Faz detritos orbitarem o caster causando dano massivo"
    },
}

