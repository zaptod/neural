"""
Sistema de classificacao de magias.

Cada skill recebe 3 eixos principais:
- elemento
- classe de forca
- classe de utilidade

Tambem gera uma assinatura visual curta para guiar renderer e UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Tuple


class ClasseForcaMagia(str, Enum):
    IMPACTO = "IMPACTO"
    PRESSAO = "PRESSAO"
    PRECISAO = "PRECISAO"
    CATACLISMO = "CATACLISMO"
    SUPORTE = "SUPORTE"


class ClasseUtilidadeMagia(str, Enum):
    DANO = "DANO"
    CONTROLE = "CONTROLE"
    MOBILIDADE = "MOBILIDADE"
    PROTECAO = "PROTECAO"
    CURA = "CURA"
    INVOCACAO = "INVOCACAO"
    ZONA = "ZONA"
    AMPLIFICACAO = "AMPLIFICACAO"
    DISRUPCAO = "DISRUPCAO"


@dataclass(frozen=True)
class ClasseMagia:
    nome_skill: str
    tipo: str
    elemento: str
    classe_forca: ClasseForcaMagia
    classe_utilidade: ClasseUtilidadeMagia
    assinatura_visual: str
    resumo: str
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {
            "nome_skill": self.nome_skill,
            "tipo": self.tipo,
            "elemento": self.elemento,
            "classe_forca": self.classe_forca.value,
            "classe_utilidade": self.classe_utilidade.value,
            "assinatura_visual": self.assinatura_visual,
            "resumo": self.resumo,
            "tags": list(self.tags),
        }


def _tem_algum(data: Dict, chaves: Iterable[str]) -> bool:
    return any(data.get(ch) for ch in chaves)


def _eh_controle(data: Dict) -> bool:
    return _tem_algum(data, (
        "duracao_stun",
        "duracao_fear",
        "duracao_charme",
        "slow_fator",
        "aura_slow",
        "puxa_para_centro",
        "puxa_continuo",
        "bloqueia_movimento",
        "taunt",
        "root",
    ))


def _eh_protecao(data: Dict) -> bool:
    return _tem_algum(data, (
        "escudo",
        "invencivel",
        "reflete_projeteis",
        "remove_todos_debuffs",
        "sem_cooldown",
        "esquiva_garantida",
    ))


def _eh_cura(data: Dict) -> bool:
    return _tem_algum(data, ("cura", "regen", "cura_por_segundo", "lifesteal"))


def _eh_amplificacao(data: Dict) -> bool:
    return _tem_algum(data, (
        "buff_dano",
        "buff_velocidade",
        "bonus_velocidade_ataque",
        "bonus_velocidade_movimento",
        "custo_mana_metade",
    ))


def _eh_zona(data: Dict, tipo: str) -> bool:
    return tipo in {"AREA", "TRAP"} or _tem_algum(data, ("raio_area", "ondas", "meteoros_aleatorios"))


def _classe_utilidade(tipo: str, data: Dict) -> ClasseUtilidadeMagia:
    if tipo == "SUMMON":
        return ClasseUtilidadeMagia.INVOCACAO
    if tipo == "DASH":
        return ClasseUtilidadeMagia.MOBILIDADE
    if _eh_cura(data):
        return ClasseUtilidadeMagia.CURA
    if _eh_protecao(data):
        return ClasseUtilidadeMagia.PROTECAO
    if _eh_amplificacao(data):
        return ClasseUtilidadeMagia.AMPLIFICACAO
    if _eh_controle(data):
        return ClasseUtilidadeMagia.CONTROLE
    if _eh_zona(data, tipo):
        return ClasseUtilidadeMagia.ZONA
    if tipo == "CHANNEL":
        return ClasseUtilidadeMagia.DISRUPCAO if _eh_controle(data) else ClasseUtilidadeMagia.DANO
    return ClasseUtilidadeMagia.DANO


def _classe_forca(tipo: str, data: Dict, utilidade: ClasseUtilidadeMagia) -> ClasseForcaMagia:
    dano = float(data.get("dano", 0) or 0)
    raio = float(data.get("raio_area", data.get("raio_explosao", 0)) or 0)
    dps = float(data.get("dano_por_segundo", data.get("dano_tick", 0)) or 0)
    multi = int(data.get("multi_shot", 1) or 1)

    if utilidade in {
        ClasseUtilidadeMagia.CURA,
        ClasseUtilidadeMagia.PROTECAO,
        ClasseUtilidadeMagia.AMPLIFICACAO,
    } and dano <= 0:
        return ClasseForcaMagia.SUPORTE

    if tipo in {"CHANNEL"} or dps > 0 or data.get("canalizavel"):
        return ClasseForcaMagia.PRESSAO

    if data.get("executa") or data.get("meteoros_aleatorios") or (dano >= 30 and raio >= 1.8):
        return ClasseForcaMagia.CATACLISMO

    if tipo == "BEAM" or data.get("homing") or data.get("perfura") or data.get("retorna"):
        return ClasseForcaMagia.PRECISAO

    if multi >= 4 and dano >= 18:
        return ClasseForcaMagia.CATACLISMO

    if dano > 0 or tipo in {"PROJETIL", "AREA", "TRAP"}:
        return ClasseForcaMagia.IMPACTO

    return ClasseForcaMagia.SUPORTE


def _assinatura_visual(forca: ClasseForcaMagia, utilidade: ClasseUtilidadeMagia, tipo: str) -> str:
    if utilidade == ClasseUtilidadeMagia.INVOCACAO:
        return "sigilo"
    if utilidade == ClasseUtilidadeMagia.CURA:
        return "halo"
    if utilidade == ClasseUtilidadeMagia.PROTECAO:
        return "domo"
    if utilidade == ClasseUtilidadeMagia.AMPLIFICACAO:
        return "aurea"
    if utilidade in {ClasseUtilidadeMagia.CONTROLE, ClasseUtilidadeMagia.ZONA}:
        return "campo"
    if utilidade == ClasseUtilidadeMagia.MOBILIDADE:
        return "seta"
    if tipo == "BEAM":
        return "fluxo"
    if forca == ClasseForcaMagia.PRECISAO:
        return "lanca"
    if forca == ClasseForcaMagia.CATACLISMO:
        return "nucleo"
    if forca == ClasseForcaMagia.PRESSAO:
        return "fluxo"
    if forca == ClasseForcaMagia.SUPORTE:
        return "anel"
    return "cometa"


def _resumo(forca: ClasseForcaMagia, utilidade: ClasseUtilidadeMagia, elemento: str) -> str:
    labels_forca = {
        ClasseForcaMagia.IMPACTO: "Impacto",
        ClasseForcaMagia.PRESSAO: "Pressao",
        ClasseForcaMagia.PRECISAO: "Precisao",
        ClasseForcaMagia.CATACLISMO: "Cataclismo",
        ClasseForcaMagia.SUPORTE: "Suporte",
    }
    labels_util = {
        ClasseUtilidadeMagia.DANO: "dano",
        ClasseUtilidadeMagia.CONTROLE: "controle",
        ClasseUtilidadeMagia.MOBILIDADE: "mobilidade",
        ClasseUtilidadeMagia.PROTECAO: "protecao",
        ClasseUtilidadeMagia.CURA: "cura",
        ClasseUtilidadeMagia.INVOCACAO: "invocacao",
        ClasseUtilidadeMagia.ZONA: "zona",
        ClasseUtilidadeMagia.AMPLIFICACAO: "amplificacao",
        ClasseUtilidadeMagia.DISRUPCAO: "disrupcao",
    }
    return f"{labels_forca[forca]} de {labels_util[utilidade]} ({elemento})"


def classificar_skill_magia(nome_skill: str, data: Dict | None = None) -> ClasseMagia:
    data = data or {}
    tipo = str(data.get("tipo", "NADA") or "NADA").upper()
    elemento = str(data.get("elemento", "NEUTRO") or "NEUTRO").upper()
    utilidade = _classe_utilidade(tipo, data)
    forca = _classe_forca(tipo, data, utilidade)
    assinatura = _assinatura_visual(forca, utilidade, tipo)

    tags = []
    if data.get("homing"):
        tags.append("homing")
    if data.get("perfura"):
        tags.append("perfura")
    if data.get("multi_shot"):
        tags.append("multi")
    if _eh_controle(data):
        tags.append("cc")
    if _eh_protecao(data):
        tags.append("escudo")
    if _eh_cura(data):
        tags.append("cura")

    return ClasseMagia(
        nome_skill=nome_skill,
        tipo=tipo,
        elemento=elemento,
        classe_forca=forca,
        classe_utilidade=utilidade,
        assinatura_visual=assinatura,
        resumo=_resumo(forca, utilidade, elemento),
        tags=tuple(tags),
    )


def enriquecer_skill_data(nome_skill: str, data: Dict) -> Dict:
    classificacao = classificar_skill_magia(nome_skill, data)
    data.setdefault("classe_magia", classificacao.to_dict())
    data.setdefault("classe_forca", classificacao.classe_forca.value)
    data.setdefault("classe_utilidade", classificacao.classe_utilidade.value)
    data.setdefault("assinatura_visual", classificacao.assinatura_visual)
    data.setdefault("resumo_classe", classificacao.resumo)
    return data
