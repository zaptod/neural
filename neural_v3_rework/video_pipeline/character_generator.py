"""
Character Generator — Cria lutadores completamente aleatórios para vídeos.
"""
import random, math
from typing import Tuple

from video_pipeline.config import (
    NOMES_MASCULINOS, NOMES_FEMININOS,
)


TITULOS_MASCULINOS = [
    "o Implacável", "o Imortal", "o Lendário", "o Carmesim", "o Predador",
    "o Titã", "o Dragão", "o Relâmpago", "o Colosso", "o Inferno",
    "o Trovão", "o Solar", "o Abissal",
]

TITULOS_FEMININOS = [
    "a Destruidora", "a Sombria", "a Invicta", "a Tempestade", "a Fantasma",
    "a Valquíria", "a Fênix", "a Serpente", "a Lâmina", "a Gélida",
    "a Noturna", "a Lunar",
]

TITULOS_NEUTROS = [
    "das Cinzas", "do Vazio", "da Aurora", "das Sombras", "do Trovão", "",
]


_ROTATION_POOLS: dict[str, list] = {}
_USE_COVERAGE_ROTATION = True


def reset_coverage_rotation() -> None:
    _ROTATION_POOLS.clear()


def set_coverage_rotation(enabled: bool) -> None:
    global _USE_COVERAGE_ROTATION
    _USE_COVERAGE_ROTATION = bool(enabled)
    if not _USE_COVERAGE_ROTATION:
        reset_coverage_rotation()


def _normalizar_espacos(texto: str) -> str:
    return " ".join(str(texto).split())


def _tokens_base(texto: str) -> set[str]:
    tokens = []
    for t in _normalizar_espacos(texto).lower().split():
        t = t.strip(".,;:!?()[]{}\"'`´^~")
        if len(t) >= 3:
            tokens.append(t)
    return set(tokens)


def _dedupe_nome_composto(*partes: str) -> str:
    nome = _normalizar_espacos(" ".join(p for p in partes if p))
    palavras = nome.split()
    saida = []
    prev = None
    for palavra in palavras:
        p = palavra.lower()
        if p != prev:
            saida.append(palavra)
        prev = p
    return " ".join(saida)


def _escolher_titulo_personagem(genero: str) -> str:
    genero = (genero or "").upper()
    if genero == "F":
        pool = TITULOS_FEMININOS + TITULOS_NEUTROS
    else:
        pool = TITULOS_MASCULINOS + TITULOS_NEUTROS
    return random.choice(pool)


def _pick_rotativo(pool_key: str, opcoes: list):
    if not opcoes:
        return None
    if not _USE_COVERAGE_ROTATION:
        return random.choice(opcoes)

    pool = _ROTATION_POOLS.get(pool_key)
    if not pool:
        pool = list(opcoes)
        random.shuffle(pool)
        _ROTATION_POOLS[pool_key] = pool

    return pool.pop() if pool else random.choice(opcoes)


def gerar_cor_harmonica() -> Tuple[int, int, int]:
    """Gera uma cor RGB vibrante usando HSL → RGB.
    Evita cores apagadas / marrons / cinzas."""
    hue = random.random()                     # 0-1
    sat = random.uniform(0.55, 0.95)          # saturação alta
    lum = random.uniform(0.40, 0.65)          # luminosidade média

    # HSL → RGB (simplificado)
    def hue2rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    q = lum * (1 + sat) if lum < 0.5 else lum + sat - lum * sat
    p = 2 * lum - q
    r = int(hue2rgb(p, q, hue + 1/3) * 255)
    g = int(hue2rgb(p, q, hue) * 255)
    b = int(hue2rgb(p, q, hue - 1/3) * 255)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def gerar_cor_arma_tematica(cor_char: Tuple[int, int, int], raridade: str) -> Tuple[int, int, int]:
    """Gera cor de arma complementar ao personagem.
    Raridades altas → cores mais brilhantes/saturadas."""
    brilho_extra = {
        "Comum": 0, "Incomum": 15, "Raro": 30,
        "Épico": 50, "Lendário": 70, "Mítico": 90
    }.get(raridade, 0)

    # Cor complementar levemente deslocada
    r = min(255, max(50, 255 - cor_char[0] + random.randint(-30, 30) + brilho_extra))
    g = min(255, max(50, 255 - cor_char[1] + random.randint(-30, 30) + brilho_extra))
    b = min(255, max(50, 255 - cor_char[2] + random.randint(-30, 30) + brilho_extra))
    return (r, g, b)


def gerar_arma(nome_arma: str = None, raridade: str = None, 
               cor_char: Tuple[int, int, int] = (200, 200, 200)) -> dict:
    """Gera arma completamente aleatória com balanceamento por raridade."""
    from models.constants import TIPOS_ARMA, LISTA_RARIDADES, LISTA_ENCANTAMENTOS, PASSIVAS_ARMA, get_raridade_data
    from core.skills import SKILL_DB

    # Raridade com peso (mais chances de raridades altas para ser visual)
    if raridade is None:
        raridades_ponderadas = []
        for raridade_nome, peso in zip(LISTA_RARIDADES, [20, 25, 25, 15, 10, 5]):
            raridades_ponderadas.extend([raridade_nome] * peso)
        raridade = _pick_rotativo("raridade_arma", raridades_ponderadas)
    rar_data = get_raridade_data(raridade)

    # Tipo + estilo
    tipo = _pick_rotativo("tipo_arma", list(TIPOS_ARMA.keys()))
    tipo_data = TIPOS_ARMA[tipo]
    estilos = tipo_data.get("estilos", ["Misto"])
    estilo = random.choice(estilos)

    # Nome automático
    if nome_arma is None:
        prefixos_tipo = {
            "Reta": ["Espada", "Lança", "Claymore", "Montante", "Sabre"],
            "Dupla": ["Adagas", "Kamas", "Garras", "Tonfas", "Sais"],
            "Corrente": ["Mangual", "Kusarigama", "Chicote", "Flagelo", "Meteora"],
            "Arremesso": ["Machado", "Chakram", "Shuriken", "Bumerangue", "Disco"],
            "Arco": ["Arco", "Besta", "Ballista", "Longbow", "Arbalesta"],
            "Orbital": ["Escudo", "Drone", "Orbe", "Sentinela", "Satélite"],
            "Mágica": ["Grimório", "Cajado", "Cristal", "Runa", "Tomo"],
            "Transformável": ["Morphblade", "Shifter", "Camaleão", "Proteus", "Flux"],
        }
        sufixos = [
            "do Caos", "das Cinzas", "do Vórtex", "do Trovão", "de Sangue",
            "da Aurora", "das Sombras", "do Eclipse", "do Abismo", "do Vento",
            "de Ferro", "de Jade", "de Obsidiana", "de Cristal", "de Prata",
        ]
        prefixo = random.choice(prefixos_tipo.get(tipo, ["Arma"]))
        nome_arma = _dedupe_nome_composto(prefixo, random.choice(sufixos))

    # Cor da arma
    cor = gerar_cor_arma_tematica(cor_char, raridade)

    # Habilidades
    num_skills = rar_data.get("slots_habilidade", 1)
    skills_pool = [s for s in SKILL_DB.keys() if SKILL_DB[s].get("tipo", "NADA") != "NADA"]
    habilidades = []
    used = set()
    for _ in range(min(num_skills, len(skills_pool))):
        available = [s for s in skills_pool if s not in used]
        if not available:
            break
        skill = random.choice(available)
        used.add(skill)
        custo = SKILL_DB[skill].get("custo", 20.0)
        habilidades.append({"nome": skill, "custo": custo})

    # Encantamentos
    max_ench = rar_data.get("max_encantamentos", 0)
    num_ench = random.randint(0, max_ench)
    encantamentos = random.sample(LISTA_ENCANTAMENTOS, min(num_ench, len(LISTA_ENCANTAMENTOS)))

    # Passiva
    passiva = None
    passiva_tipo = rar_data.get("passiva")
    if passiva_tipo and passiva_tipo in PASSIVAS_ARMA:
        passiva = random.choice(PASSIVAS_ARMA[passiva_tipo])

    # Stats escalados por raridade
    dano_base = random.uniform(3.0, 8.0)
    peso_base = random.uniform(2.0, 7.0)

    arma = {
        "nome": nome_arma,
        "tipo": tipo,
        "dano": round(dano_base, 1),
        "peso": round(peso_base, 1),
        "raridade": raridade,
        "r": cor[0], "g": cor[1], "b": cor[2],
        "estilo": estilo,
        "habilidades": habilidades,
        "encantamentos": encantamentos,
        "passiva": passiva,
        "critico": round(random.uniform(0.0, 8.0 + (LISTA_RARIDADES.index(raridade) if raridade in LISTA_RARIDADES else 0) * 2), 1),
        "velocidade_ataque": round(random.uniform(0.7, 1.4), 2),
        "afinidade_elemento": random.choice([None, None, "FOGO", "GELO", "RAIO", "VENTO", "TERRA", "TREVAS", "LUZ"]),
        "habilidade": habilidades[0]["nome"] if habilidades else "Nenhuma",
        "custo_mana": habilidades[0]["custo"] if habilidades else 0.0,
        "durabilidade": 100.0,
        "durabilidade_max": 100.0,
        # Geometria
        "comp_cabo": random.uniform(10.0, 35.0),
        "comp_lamina": random.uniform(30.0, 90.0),
        "largura": random.uniform(4.0, 12.0),
        "distancia": 20.0,
        "comp_corrente": random.uniform(20.0, 50.0) if tipo == "Corrente" else 0.0,
        "comp_ponta": random.uniform(8.0, 18.0) if tipo == "Corrente" else 0.0,
        "largura_ponta": random.uniform(4.0, 10.0) if tipo == "Corrente" else 0.0,
        "tamanho_projetil": random.uniform(6.0, 16.0) if tipo == "Arremesso" else 0.0,
        "quantidade": random.randint(2, 5) if tipo == "Arremesso" else 1,
        "tamanho_arco": random.uniform(35.0, 55.0) if tipo == "Arco" else 0.0,
        "forca_arco": random.uniform(6.0, 14.0) if tipo == "Arco" else 0.0,
        "tamanho_flecha": random.uniform(30.0, 50.0) if tipo == "Arco" else 0.0,
        "quantidade_orbitais": random.randint(2, 4) if tipo == "Orbital" else 1,
        "tamanho": random.uniform(6.0, 16.0),
        "distancia_max": random.uniform(6.0, 12.0) if tipo == "Mágica" else 0.0,
        "separacao": random.uniform(12.0, 25.0) if tipo == "Dupla" else 0.0,
        "forma1_cabo": random.uniform(12.0, 22.0),
        "forma1_lamina": random.uniform(35.0, 55.0),
        "forma2_cabo": random.uniform(12.0, 22.0),
        "forma2_lamina": random.uniform(35.0, 55.0),
        "cabo_dano": random.random() < 0.2,
    }
    return arma


def gerar_personagem(nome: str = None, classe: str = None,
                     personalidade: str = None) -> Tuple[dict, dict]:
    """Gera um personagem + arma completamente aleatórios.
    Retorna (char_data, arma_data)."""
    from models.constants import LISTA_CLASSES
    from ai.personalities import LISTA_PERSONALIDADES

    # Nome com título épico
    if nome is None:
        genero = random.choice(["M", "F"])
        pool = NOMES_MASCULINOS if genero == "M" else NOMES_FEMININOS
        nome_base = random.choice(pool)
        titulo = _escolher_titulo_personagem(genero)

        # Evita sobreposição feia entre base e título (ex.: "Tempest ... Tempestade")
        if titulo and _tokens_base(nome_base).intersection(_tokens_base(titulo)):
            titulo = random.choice(TITULOS_NEUTROS)

        nome = _dedupe_nome_composto(nome_base, titulo)

    if classe is None:
        classe = _pick_rotativo("classe_personagem", LISTA_CLASSES)
    if personalidade is None:
        personalidade = _pick_rotativo("personalidade", LISTA_PERSONALIDADES)

    # Cor do personagem
    cor = gerar_cor_harmonica()

    # Stats influenciados pela classe
    is_mage = any(x in classe for x in ["Mago", "Feiticeiro", "Piromante", "Criomante", "Necromante"])
    is_tank = any(x in classe for x in ["Cavaleiro", "Paladino", "Gladiador"])
    is_fast = any(x in classe for x in ["Assassino", "Ninja", "Ladino"])

    forca = round(random.uniform(3.0, 10.0), 1)
    mana = round(random.uniform(3.0, 10.0), 1)
    tamanho = round(random.uniform(1.5, 2.2), 2)

    if is_mage:
        mana = round(random.uniform(7.0, 10.0), 1)
        forca = round(random.uniform(2.0, 6.0), 1)
    elif is_tank:
        tamanho = round(random.uniform(1.8, 2.5), 2)
        forca = round(random.uniform(6.0, 10.0), 1)
    elif is_fast:
        tamanho = round(random.uniform(1.3, 1.8), 2)
        forca = round(random.uniform(5.0, 9.0), 1)

    # Gera arma
    arma_data = gerar_arma(cor_char=cor)

    char_data = {
        "nome": nome,
        "tamanho": tamanho,
        "forca": forca,
        "mana": mana,
        "nome_arma": arma_data["nome"],
        "cor_r": cor[0],
        "cor_g": cor[1],
        "cor_b": cor[2],
        "classe": classe,
        "personalidade": personalidade,
    }

    return char_data, arma_data


def _pontuacao_poder(char_data: dict, arma_data: dict) -> float:
    """Score aproximado de poder para pareamento justo no pipeline.

    Objetivo: reduzir stomps e vídeos curtos demais sem alterar o formato dos dados.
    """
    raridade_bonus = {
        "Comum": 0.0,
        "Incomum": 0.8,
        "Raro": 1.6,
        "Épico": 2.4,
        "Lendário": 3.3,
        "Mítico": 4.4,
    }

    forca = float(char_data.get("forca", 0.0))
    mana = float(char_data.get("mana", 0.0))
    tamanho = float(char_data.get("tamanho", 0.0))

    dano = float(arma_data.get("dano", 0.0))
    critico = float(arma_data.get("critico", 0.0))
    vel_ataque = float(arma_data.get("velocidade_ataque", 1.0))
    raridade = str(arma_data.get("raridade", "Comum"))

    # Peso maior em dano/força (kill speed), com contribuição moderada de mana e velocidade.
    return (
        forca * 1.85 +
        mana * 1.20 +
        tamanho * 1.10 +
        dano * 2.10 +
        critico * 0.18 +
        vel_ataque * 3.25 +
        raridade_bonus.get(raridade, 0.0)
    )


def _gap_poder(c1: dict, a1: dict, c2: dict, a2: dict) -> Tuple[float, float]:
    """Retorna (gap_absoluto, gap_relativo) entre os dois lutadores."""
    p1 = _pontuacao_poder(c1, a1)
    p2 = _pontuacao_poder(c2, a2)
    gap_abs = abs(p1 - p2)
    base = max(1.0, min(p1, p2))
    gap_rel = gap_abs / base
    return gap_abs, gap_rel


def _gerar_par_bruto() -> Tuple[dict, dict, dict, dict]:
    c1, a1 = gerar_personagem()
    c2, a2 = gerar_personagem()
    tentativas_nome = 0
    while c2["nome"] == c1["nome"] and tentativas_nome < 10:
        c2, a2 = gerar_personagem()
        tentativas_nome += 1
    return c1, a1, c2, a2


def gerar_par_de_lutadores(generation_mode: str = "hybrid",
                           hybrid_balanced_ratio: float = 0.7) -> Tuple[dict, dict, dict, dict]:
    """Gera dois lutadores opostos para uma batalha.
    Retorna (char1, arma1, char2, arma2)."""
    mode = (generation_mode or "hybrid").strip().lower()

    if mode == "pure_random":
        return _gerar_par_bruto()

    if mode == "hybrid":
        ratio = max(0.0, min(1.0, float(hybrid_balanced_ratio)))
        if random.random() > ratio:
            return _gerar_par_bruto()

    # Matchmaking justo: tenta vários pares e aceita cedo quando o gap é pequeno.
    max_tentativas = 40
    gap_abs_aceitavel = 2.4
    gap_rel_aceitavel = 0.16  # 16%

    melhor = None
    melhor_score = float("inf")

    for _ in range(max_tentativas):
        c1, a1 = gerar_personagem()
        c2, a2 = gerar_personagem()
        if c2["nome"] == c1["nome"]:
            continue

        gap_abs, gap_rel = _gap_poder(c1, a1, c2, a2)

        # Função de custo: prioriza gap relativo, depois absoluto.
        custo = gap_rel * 100.0 + gap_abs
        if custo < melhor_score:
            melhor_score = custo
            melhor = (c1, a1, c2, a2)

        # Aceita imediatamente quando o par já está equilibrado.
        if gap_abs <= gap_abs_aceitavel and gap_rel <= gap_rel_aceitavel:
            return c1, a1, c2, a2

    # Fallback determinístico: retorna o melhor par encontrado.
    if melhor is not None:
        return melhor

    # Fallback extremo (praticamente impossível): mantém comportamento anterior.
    return _gerar_par_bruto()
