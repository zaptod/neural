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


SKILL_CLASS_DB: dict[str, ClasseMagia] = {}
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

