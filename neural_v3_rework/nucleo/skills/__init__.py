"""
NEURAL FIGHTS â€” nucleo/skills/  [E07]
=====================================
CatÃ¡logo de skills organizado por elemento.

Estrutura:
    skills_fogo.py        ðŸ”¥ 14 skills
    skills_gelo.py        â„ï¸ 13 skills
    skills_raio.py        âš¡ 13 skills
    skills_trevas.py      ðŸŒ‘ 13 skills
    skills_luz.py         âœ¨ 14 skills
    skills_natureza.py    ðŸ’š 14 skills
    skills_arcano.py      ðŸ’œ 13 skills
    skills_tempo.py       ðŸŒ€ 15 skills
    skills_gravitacao.py  ðŸŒŒ 15 skills
    skills_caos.py        ðŸ’€ 14 skills
    skills_void.py        ðŸ•³ï¸ 15 skills
    skills_sangue.py      ðŸ©¸ 15 skills
    skills_especiais.py   âš”ï¸ 16 skills (sem elemento â€” fÃ­sicas/tÃ¡ticas/utilidade)

Este __init__.py monta o SKILL_DB completo para retrocompatibilidade total.
Todo cÃ³digo que fazia `from core.skills import SKILL_DB` continua funcionando.

Para encontrar e editar uma skill:
    1. Saiba o elemento da skill (campo "elemento" no dict).
    2. Abra o arquivo correspondente (ex: skills_fogo.py).
    3. Busque pelo nome da skill.
"""

from .skills_fogo       import SKILLS_FOGO
from .skills_gelo       import SKILLS_GELO
from .skills_raio       import SKILLS_RAIO
from .skills_trevas     import SKILLS_TREVAS
from .skills_luz        import SKILLS_LUZ
from .skills_natureza   import SKILLS_NATUREZA
from .skills_arcano     import SKILLS_ARCANO
from .skills_tempo      import SKILLS_TEMPO
from .skills_gravitacao import SKILLS_GRAVITACAO
from .skills_caos       import SKILLS_CAOS
from .skills_void       import SKILLS_VOID
from .skills_sangue     import SKILLS_SANGUE
from .skills_especiais  import SKILLS_ESPECIAIS
from .skills_nenhuma    import SKILLS_NENHUMA
from .classificacao import (
    ClasseForcaMagia,
    ClasseUtilidadeMagia,
    ClasseMagia,
    classificar_skill_magia,
    enriquecer_skill_data,
)

# SKILL_DB completo â€” retrocompatÃ­vel com todo cÃ³digo existente
SKILL_DB: dict = {
    **SKILLS_NENHUMA,
    **SKILLS_FOGO,
    **SKILLS_GELO,
    **SKILLS_RAIO,
    **SKILLS_TREVAS,
    **SKILLS_LUZ,
    **SKILLS_NATUREZA,
    **SKILLS_ARCANO,
    **SKILLS_TEMPO,
    **SKILLS_GRAVITACAO,
    **SKILLS_CAOS,
    **SKILLS_VOID,
    **SKILLS_SANGUE,
    **SKILLS_ESPECIAIS,
}

# Acesso por elemento â€” Ãºtil para auditoria e balance
SKILLS_BY_ELEMENT: dict[str, dict] = {
    "FOGO":       SKILLS_FOGO,
    "GELO":       SKILLS_GELO,
    "RAIO":       SKILLS_RAIO,
    "TREVAS":     SKILLS_TREVAS,
    "LUZ":        SKILLS_LUZ,
    "NATUREZA":   SKILLS_NATUREZA,
    "ARCANO":     SKILLS_ARCANO,
    "TEMPO":      SKILLS_TEMPO,
    "GRAVITACAO": SKILLS_GRAVITACAO,
    "CAOS":       SKILLS_CAOS,
    "VOID":       SKILLS_VOID,
    "SANGUE":     SKILLS_SANGUE,
    "ESPECIAIS":  SKILLS_ESPECIAIS,
}

__all__ = ["SKILL_DB", "SKILLS_BY_ELEMENT",
           "get_skill_data", "get_skills_by_tipo", "get_skills_by_elemento",
           "get_skills_by_efeito", "listar_skills_para_ui", "listar_elementos", "contar_skills",
           "ClasseForcaMagia", "ClasseUtilidadeMagia", "ClasseMagia",
           "get_skill_classification", "get_skills_by_class", "listar_skills_filtradas"]


SKILL_BALANCE_PROFILE = {
    "PROJETIL": {"damage_cap": 40.0, "pressure_cap": 6.4, "cooldown_floor": 3.6, "cost_floor": 11.0},
    "AREA": {"damage_cap": 50.0, "pressure_cap": 4.5, "cooldown_floor": 8.5, "cost_floor": 20.0},
    "BEAM": {"damage_cap": 26.0, "pressure_cap": 4.8, "cooldown_floor": 7.5, "cost_floor": 18.0, "dps_cap": 20.0},
    "SUMMON": {"damage_cap": 17.0, "pressure_cap": 3.2, "cooldown_floor": 14.0, "cost_floor": 24.0},
    "TRAP": {"damage_cap": 28.0, "pressure_cap": 3.4, "cooldown_floor": 9.0, "cost_floor": 16.0},
    "DASH": {"damage_cap": 20.0, "pressure_cap": 3.2, "cooldown_floor": 6.5, "cost_floor": 12.0},
    "CHANNEL": {"damage_cap": 0.0, "pressure_cap": 3.6, "cooldown_floor": 10.0, "cost_floor": 18.0, "dps_cap": 13.0},
    "TRANSFORM": {"damage_cap": 0.0, "pressure_cap": 2.8, "cooldown_floor": 16.0, "cost_floor": 20.0},
    "BUFF": {"damage_cap": 0.0, "pressure_cap": 0.0, "cooldown_floor": 8.0, "cost_floor": 10.0},
}


def _clamp_high(valor, cap, overflow_scale=0.45):
    numero = float(valor or 0.0)
    if cap <= 0 or numero <= cap:
        return numero
    return cap + (numero - cap) * overflow_scale


def _estimate_skill_pressure(data: dict) -> float:
    dano = float(data.get("dano", 0.0) or 0.0)
    cooldown = max(0.1, float(data.get("cooldown", 1.0) or 1.0))
    duracao = float(data.get("duracao", data.get("duracao_max", 0.0)) or 0.0)
    dano_tick = float(data.get("dano_tick", 0.0) or 0.0)
    dano_ps = float(data.get("dano_por_segundo", 0.0) or 0.0)
    multi = int(data.get("multi_shot", 1) or 1)
    summon_dano = float(data.get("summon_dano", 0.0) or 0.0)
    aura_dano = float(data.get("aura_dano", 0.0) or 0.0)
    dano_contato = float(data.get("dano_contato", 0.0) or 0.0)
    dano_chegada = float(data.get("dano_chegada", 0.0) or 0.0)
    total = dano + dano_chegada
    if multi > 1:
        total *= 1.0 + (multi - 1) * 0.45
    if dano_tick > 0 and duracao > 0:
        total += dano_tick * min(duracao, 3.0)
    if dano_ps > 0 and duracao > 0:
        total += dano_ps * min(duracao, 2.5) * 0.85
    if summon_dano > 0:
        total += summon_dano * min(max(duracao, 6.0), 10.0) * 0.20
    if aura_dano > 0:
        total += aura_dano * min(max(duracao, 5.0), 10.0) * 0.35
    if dano_contato > 0:
        total += dano_contato * 2.5
    return total / cooldown


def _rebalance_skill_data(nome: str, data: dict) -> None:
    tipo = str(data.get("tipo", "NADA") or "NADA").upper()
    profile = SKILL_BALANCE_PROFILE.get(tipo)
    if not profile:
        return

    data["cooldown"] = max(profile["cooldown_floor"], float(data.get("cooldown", profile["cooldown_floor"]) or profile["cooldown_floor"]))
    data["custo"] = max(profile["cost_floor"], float(data.get("custo", profile["cost_floor"]) or profile["cost_floor"]))

    if tipo == "PROJETIL":
        data["dano"] = _clamp_high(data.get("dano", 0.0), profile["damage_cap"], 0.24)
    elif tipo == "AREA":
        data["dano"] = _clamp_high(data.get("dano", 0.0), profile["damage_cap"], 0.32)
    elif tipo in {"BEAM", "TRAP"}:
        data["dano"] = _clamp_high(data.get("dano", 0.0), profile["damage_cap"], 0.34)
    elif tipo == "DASH":
        data["dano"] = _clamp_high(data.get("dano", 0.0), profile["damage_cap"], 0.35)
        data["dano_chegada"] = _clamp_high(data.get("dano_chegada", 0.0), profile["damage_cap"], 0.30)
    elif tipo == "SUMMON":
        data["summon_dano"] = _clamp_high(data.get("summon_dano", 0.0), profile["damage_cap"], 0.45)
        data["aura_dano"] = _clamp_high(data.get("aura_dano", 0.0), 5.0, 0.35)
        if data.get("duracao", 0) > 0:
            data["duracao"] = min(float(data["duracao"]), 11.0)
    elif tipo == "CHANNEL":
        if data.get("dano_por_segundo", 0) > 0:
            data["dano_por_segundo"] = _clamp_high(data.get("dano_por_segundo", 0.0), profile["dps_cap"], 0.08)
        if data.get("duracao_max", 0) > 0:
            data["duracao_max"] = min(float(data["duracao_max"]), 3.5)
    elif tipo == "TRANSFORM":
        data["dano_contato"] = _clamp_high(data.get("dano_contato", 0.0), 12.0, 0.35)
        if data.get("duracao", 0) > 0:
            data["duracao"] = min(float(data["duracao"]), 12.0)

    if tipo == "AREA" and data.get("raio_area", 0) > 0:
        data["raio_area"] = min(float(data["raio_area"]), 3.8)
    if tipo == "PROJETIL":
        if data.get("multi_shot", 1) > 2:
            data["multi_shot"] = 2
        if data.get("velocidade", 0) > 0:
            data["velocidade"] = min(float(data["velocidade"]), 14.5)
        multi = int(data.get("multi_shot", 1) or 1)
        dano = float(data.get("dano", 0.0) or 0.0)
        if multi > 1:
            data["cooldown"] = max(float(data["cooldown"]), 4.3)
            data["custo"] = max(float(data["custo"]), 14.0 + (multi - 1) * 2.0)
        if dano >= 24.0:
            data["cooldown"] = max(float(data["cooldown"]), 4.8)
            data["custo"] = max(float(data["custo"]), 16.0)
        if dano >= 32.0:
            data["cooldown"] = max(float(data["cooldown"]), 5.6)
            data["custo"] = max(float(data["custo"]), 22.0)
    if tipo == "AREA":
        dano = float(data.get("dano", 0.0) or 0.0)
        raio = float(data.get("raio_area", 0.0) or 0.0)
        if raio >= 2.2:
            data["cooldown"] = max(float(data["cooldown"]), 9.5)
            data["custo"] = max(float(data["custo"]), 24.0)
        if dano >= 38.0:
            data["cooldown"] = max(float(data["cooldown"]), 10.5)
            data["custo"] = max(float(data["custo"]), 26.0)
        if dano >= 48.0 or raio >= 3.2:
            data["cooldown"] = max(float(data["cooldown"]), 11.5)
            data["custo"] = max(float(data["custo"]), 30.0)
    if tipo == "BEAM":
        if data.get("alcance", 0) > 0:
            data["alcance"] = min(float(data["alcance"]), 8.0)
        if data.get("dano_por_segundo", 0) > 0:
            data["dano_por_segundo"] = _clamp_high(data.get("dano_por_segundo", 0.0), profile["dps_cap"], 0.12)
    if tipo == "TRAP" and data.get("dano_contato", 0) > 0:
        data["dano_contato"] = _clamp_high(data.get("dano_contato", 0.0), 12.0, 0.35)

    pressure = _estimate_skill_pressure(data)
    if profile["pressure_cap"] > 0 and pressure > profile["pressure_cap"]:
        fator = min(1.55, pressure / profile["pressure_cap"])
        data["cooldown"] = round(float(data["cooldown"]) * fator, 2)
        data["custo"] = round(float(data["custo"]) * min(1.30, 1.0 + (fator - 1.0) * 0.45), 2)

    data["balance_profile"] = {"tipo": tipo, "versao": "v3_runtime"}


SKILL_CLASS_DB: dict[str, ClasseMagia] = {}
for _skill_nome, _skill_data in SKILL_DB.items():
    _rebalance_skill_data(_skill_nome, _skill_data)
for _skill_nome, _skill_data in SKILL_DB.items():
    enriquecer_skill_data(_skill_nome, _skill_data)
    SKILL_CLASS_DB[_skill_nome] = classificar_skill_magia(_skill_nome, _skill_data)


# â”€â”€ FunÃ§Ãµes helpers â€” retrocompatÃ­veis com core.skills originais â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_skill_data(nome: str) -> dict:
    """Retorna os dados de uma skill pelo nome."""
    return SKILL_DB.get(nome, SKILL_DB["Nenhuma"])


def get_skill_classification(nome: str) -> ClasseMagia:
    """Retorna a classificacao formal da skill."""
    if nome in SKILL_CLASS_DB:
        return SKILL_CLASS_DB[nome]
    return classificar_skill_magia(nome, get_skill_data(nome))


def get_skills_by_tipo(tipo: str) -> dict:
    """Retorna todas as skills de um determinado tipo."""
    return {k: v for k, v in SKILL_DB.items() if v.get("tipo") == tipo}


def get_skills_by_elemento(elemento: str) -> dict:
    """Retorna skills por elemento. Usa SKILLS_BY_ELEMENT quando possÃ­vel."""
    return SKILLS_BY_ELEMENT.get(elemento.upper(), {})


def get_skills_by_efeito(efeito: str) -> dict:
    """Retorna skills que causam um determinado efeito."""
    return {k: v for k, v in SKILL_DB.items() if v.get("efeito") == efeito}


def get_skills_by_class(forca: str | None = None, utilidade: str | None = None, elemento: str | None = None) -> dict:
    """Filtra skills por classe de força, utilidade e elemento."""
    resultado = {}
    for nome, dados in SKILL_DB.items():
        classe = get_skill_classification(nome)
        if forca and classe.classe_forca.value != str(forca).upper():
            continue
        if utilidade and classe.classe_utilidade.value != str(utilidade).upper():
            continue
        if elemento and classe.elemento != str(elemento).upper():
            continue
        resultado[nome] = dados
    return resultado


def listar_skills_filtradas(
    elemento: str | None = None,
    tipo: str | None = None,
    forca: str | None = None,
    utilidade: str | None = None,
    incluir_nenhuma: bool = False,
) -> list[str]:
    """Lista nomes de skills filtrados e ordenados por classe para UI."""
    resultado = []
    for nome, dados in SKILL_DB.items():
        if nome == "Nenhuma":
            continue
        classe = get_skill_classification(nome)
        if elemento and elemento != "Todos" and dados.get("elemento") != elemento:
            continue
        if tipo and tipo != "Todos" and dados.get("tipo") != tipo:
            continue
        if forca and forca != "Todos" and classe.classe_forca.value != str(forca).upper():
            continue
        if utilidade and utilidade != "Todos" and classe.classe_utilidade.value != str(utilidade).upper():
            continue
        resultado.append(nome)

    resultado.sort(
        key=lambda nome: (
            get_skill_classification(nome).classe_utilidade.value,
            get_skill_classification(nome).classe_forca.value,
            get_skill_classification(nome).elemento,
            nome,
        )
    )
    if incluir_nenhuma:
        return ["Nenhuma", *resultado]
    return resultado


def listar_skills_para_ui() -> list:
    """Retorna lista formatada para ComboBox."""
    return list(SKILL_DB.keys())


def listar_elementos() -> list:
    """Retorna lista de elementos disponÃ­veis."""
    return sorted(SKILLS_BY_ELEMENT.keys())


def contar_skills() -> dict:
    """Retorna contagem de skills por tipo."""
    contagem: dict = {}
    for skill in SKILL_DB.values():
        tipo = skill.get("tipo", "DESCONHECIDO")
        contagem[tipo] = contagem.get(tipo, 0) + 1
    return contagem

