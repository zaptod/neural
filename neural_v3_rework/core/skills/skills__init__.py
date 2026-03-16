"""
NEURAL FIGHTS — core/skills/  [E07]
=====================================
Catálogo de skills organizado por elemento.

Estrutura:
    skills_fogo.py        🔥 14 skills
    skills_gelo.py        ❄️ 13 skills
    skills_raio.py        ⚡ 13 skills
    skills_trevas.py      🌑 13 skills
    skills_luz.py         ✨ 14 skills
    skills_natureza.py    💚 14 skills
    skills_arcano.py      💜 13 skills
    skills_tempo.py       🌀 15 skills
    skills_gravitacao.py  🌌 15 skills
    skills_caos.py        💀 14 skills
    skills_void.py        🕳️ 15 skills
    skills_sangue.py      🩸 15 skills
    skills_especiais.py   ⚔️ 16 skills (sem elemento — físicas/táticas/utilidade)

Este __init__.py monta o SKILL_DB completo para retrocompatibilidade total.
Todo código que fazia `from core.skills import SKILL_DB` continua funcionando.

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

# SKILL_DB completo — retrocompatível com todo código existente
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

# Acesso por elemento — útil para auditoria e balance
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
           "get_skills_by_efeito", "listar_skills_para_ui", "listar_elementos", "contar_skills"]


# ── Funções helpers — retrocompatíveis com core.skills originais ──────────────

def get_skill_data(nome: str) -> dict:
    """Retorna os dados de uma skill pelo nome."""
    return SKILL_DB.get(nome, SKILL_DB["Nenhuma"])


def get_skills_by_tipo(tipo: str) -> dict:
    """Retorna todas as skills de um determinado tipo."""
    return {k: v for k, v in SKILL_DB.items() if v.get("tipo") == tipo}


def get_skills_by_elemento(elemento: str) -> dict:
    """Retorna skills por elemento. Usa SKILLS_BY_ELEMENT quando possível."""
    return SKILLS_BY_ELEMENT.get(elemento.upper(), {})


def get_skills_by_efeito(efeito: str) -> dict:
    """Retorna skills que causam um determinado efeito."""
    return {k: v for k, v in SKILL_DB.items() if v.get("efeito") == efeito}


def listar_skills_para_ui() -> list:
    """Retorna lista formatada para ComboBox."""
    return list(SKILL_DB.keys())


def listar_elementos() -> list:
    """Retorna lista de elementos disponíveis."""
    return sorted(SKILLS_BY_ELEMENT.keys())


def contar_skills() -> dict:
    """Retorna contagem de skills por tipo."""
    contagem: dict = {}
    for skill in SKILL_DB.values():
        tipo = skill.get("tipo", "DESCONHECIDO")
        contagem[tipo] = contagem.get(tipo, 0) + 1
    return contagem
