#!/usr/bin/env python3
"""
Harness tatico do posto headless.

Objetivo:
- Selecionar composicoes reais do roster por papel tatico
- Rodar cenarios 1v1, grupo vs grupo e grupo vs horda em modo dummy/headless
- Gerar relatorio comparavel por template e por papel
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dados.app_state import AppState
from ia.composite_archetypes import inferir_arquetipo_composto
from modelos import Arma, Personagem
from nucleo.armas import resolver_subtipo_orbital
from nucleo.skills import get_skill_classification
from simulacao import Simulador
from utilitarios.postos_operacao import ensure_posto_dirs
from utilitarios.encounter_config import build_horde_match_config, build_team_match_config, get_horde_preset

FILE_PAPEIS = ROOT / "dados" / "papeis_taticos.json"
FILE_PLANO = ROOT / "dados" / "plano_testes_taticos.json"
FILE_TEMPLATES = ROOT / "dados" / "templates_composicao_tatica.json"


@dataclass
class CandidatoTatico:
    personagem: Personagem
    arma: Arma
    papel_id: str
    score: float
    motivos: list[str]
    pacote_arquetipo: str = ""
    pacote_nome: str = ""
    desvios_pacote: list[str] | None = None


def normalizar_texto(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(ch for ch in base if not unicodedata.combining(ch))
    return sem_acento.upper().strip()


def carregar_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def carregar_catalogos() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        carregar_json(FILE_PAPEIS),
        carregar_json(FILE_PLANO),
        carregar_json(FILE_TEMPLATES),
    )


def carregar_criterios_modo(modo: str) -> dict[str, Any]:
    _, plano_data, _ = carregar_catalogos()
    for item in plano_data.get("modos", []):
        if item.get("id") == modo:
            return dict(item.get("criterios_alerta", {}) or {})
    return {}


def _team_slots(template: dict[str, Any], team_key: str) -> list[dict[str, Any]]:
    return list(template.get(team_key, []) or [])


def _team_tem_papel(template: dict[str, Any], team_key: str, papel_id: str) -> bool:
    return any(slot.get("papel") == papel_id for slot in _team_slots(template, team_key))


def gerar_alertas_balanceamento(template: dict[str, Any], resumo: dict[str, Any]) -> list[dict[str, Any]]:
    alertas: list[dict[str, Any]] = []
    modo = str(resumo.get("modo", template.get("template_meta", {}).get("modo", "")) or "")
    criterios = carregar_criterios_modo(modo)
    avg_tempo = float(resumo.get("avg_tempo_simulado", 0.0) or 0.0)
    team_win_rate = dict(resumo.get("team_win_rate", {}) or {})

    tempo_min = criterios.get("tempo_medio_min_seg")
    if tempo_min is not None and avg_tempo < float(tempo_min):
        alertas.append(
            {
                "nivel": "aviso",
                "codigo": "TEMPO_MUITO_CURTO",
                "mensagem": f"Tempo medio baixo demais para {modo}: {avg_tempo:.1f}s (< {float(tempo_min):.1f}s).",
            }
        )

    tempo_max = criterios.get("tempo_medio_max_seg")
    if tempo_max is not None and avg_tempo > float(tempo_max):
        alertas.append(
            {
                "nivel": "aviso",
                "codigo": "TEMPO_MUITO_LONGO",
                "mensagem": f"Tempo medio alto demais para {modo}: {avg_tempo:.1f}s (> {float(tempo_max):.1f}s).",
            }
        )

    win_threshold = criterios.get("win_rate_comp_max", criterios.get("win_rate_isolado_max"))
    if win_threshold is not None:
        for team_key, taxa in team_win_rate.items():
            if float(taxa or 0.0) > float(win_threshold):
                alertas.append(
                    {
                        "nivel": "aviso",
                        "codigo": "DOMINANCIA_EXCESSIVA",
                        "mensagem": f"{team_key} venceu {float(taxa) * 100:.1f}% das rodadas, acima do teto de {float(win_threshold) * 100:.1f}%.",
                        "time": team_key,
                    }
                )

    if modo == "grupo_vs_grupo":
        if (
            _team_tem_papel(template, "team_a", "curandeiro")
            and not _team_tem_papel(template, "team_b", "curandeiro")
            and float(team_win_rate.get("team_a", 0.0) or 0.0) > float(criterios.get("win_rate_comp_max", 0.66))
        ):
            alertas.append(
                {
                    "nivel": "info",
                    "codigo": "CURA_SOBRESSAIU",
                    "mensagem": "Time A dominou sem espelho de cura; vale revisar sustain e janela de punish contra curandeiro.",
                    "time": "team_a",
                }
            )
        if (
            _team_tem_papel(template, "team_b", "curandeiro")
            and not _team_tem_papel(template, "team_a", "curandeiro")
            and float(team_win_rate.get("team_b", 0.0) or 0.0) > float(criterios.get("win_rate_comp_max", 0.66))
        ):
            alertas.append(
                {
                    "nivel": "info",
                    "codigo": "CURA_SOBRESSAIU",
                    "mensagem": "Time B dominou sem espelho de cura; vale revisar sustain e janela de punish contra curandeiro.",
                    "time": "team_b",
                }
            )

        survival = resumo.get("team_survival_avg", {}) or {}
        if tempo_max is not None and avg_tempo > float(tempo_max) * 0.75:
            if float(survival.get("team_a", 0.0) or 0.0) > 0.35 and float(survival.get("team_b", 0.0) or 0.0) > 0.35:
                alertas.append(
                    {
                        "nivel": "info",
                        "codigo": "SUSTAIN_ALTO",
                        "mensagem": "As duas composições estão sobrevivendo demais por muito tempo; pode haver sustain excessivo ou falta de conversão.",
                    }
                )

    if modo == "grupo_vs_horda":
        if bool(criterios.get("defensor_recomendado", False)) and not _team_tem_papel(template, "team_a", "defensor"):
            alertas.append(
                {
                    "nivel": "aviso",
                    "codigo": "SEM_DEFENSOR_NA_HORDA",
                    "mensagem": "O template de horda não tem defensor, embora o plano oficial recomende frontline para segurar corredor.",
                }
            )

        if bool(criterios.get("limpador_de_horda_obrigatorio", False)) and not _team_tem_papel(template, "team_a", "limpador_de_horda"):
            alertas.append(
                {
                    "nivel": "aviso",
                    "codigo": "SEM_LIMPADOR_DE_HORDA",
                    "mensagem": "O cenário exige limpador de horda, mas o template atual não trouxe esse papel.",
                }
            )

        horda = resumo.get("horda", {}) or {}
        completion_rate = float(horda.get("completion_rate", 0.0) or 0.0)
        if completion_rate < 0.5:
            alertas.append(
                {
                    "nivel": "aviso",
                    "codigo": "BAIXA_CONCLUSAO_DE_ONDAS",
                    "mensagem": f"A equipe concluiu a horda em apenas {completion_rate * 100:.1f}% das rodadas; sustain e controle de corredor ainda estão fracos.",
                }
            )
        wipe_min = criterios.get("tempo_ate_wipe_min_seg")
        if wipe_min is not None and avg_tempo < float(wipe_min):
            alertas.append(
                {
                    "nivel": "aviso",
                    "codigo": "SUSTAIN_BAIXO_HORDA",
                    "mensagem": f"O grupo está caindo cedo demais na horda: {avg_tempo:.1f}s (< {float(wipe_min):.1f}s).",
                }
            )

    return alertas


def calcular_score_saude_template(report: dict[str, Any]) -> float:
    score = 100.0
    resumo_alertas = report.get("resumo_alertas", {}) or {}
    score -= float(resumo_alertas.get("aviso", 0) or 0) * 15.0
    score -= float(resumo_alertas.get("info", 0) or 0) * 5.0

    modo = str(report.get("modo", "") or "")
    if modo in {"1v1", "grupo_vs_grupo"}:
        win_rate = report.get("team_win_rate", {}) or {}
        gap = abs(float(win_rate.get("team_a", 0.0) or 0.0) - float(win_rate.get("team_b", 0.0) or 0.0))
        score -= gap * 18.0
        survival = report.get("team_survival_avg", {}) or {}
        survival_gap = abs(float(survival.get("team_a", 0.0) or 0.0) - float(survival.get("team_b", 0.0) or 0.0))
        score -= survival_gap * 10.0
    elif modo == "grupo_vs_horda":
        horda = report.get("horda", {}) or {}
        score += float(horda.get("completion_rate", 0.0) or 0.0) * 18.0
        score += min(10.0, float(horda.get("avg_wave_alcancada", 0.0) or 0.0) * 2.0)
        score -= float(horda.get("failure_rate", 0.0) or 0.0) * 12.0

    tempo_real = float(report.get("avg_tempo_simulado", 0.0) or 0.0)
    if tempo_real > 0:
        score += min(6.0, tempo_real / 40.0)

    return round(max(0.0, min(100.0, score)), 3)


def _iter_team_slots(report: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    slots: list[tuple[str, dict[str, Any]]] = []
    for team_key in ("team_a", "team_b"):
        for slot in report.get(team_key, []) or []:
            slots.append((team_key, slot))
    return slots


def _detectar_times_favorecidos(report: dict[str, Any]) -> set[str]:
    win_rate = report.get("team_win_rate", {}) or {}
    taxa_a = float(win_rate.get("team_a", 0.0) or 0.0)
    taxa_b = float(win_rate.get("team_b", 0.0) or 0.0)
    if taxa_a > taxa_b:
        return {"team_a"}
    if taxa_b > taxa_a:
        return {"team_b"}
    return {"team_a", "team_b"}


def _slot_counter(report: dict[str, Any], team_keys: set[str], campo: str) -> Counter:
    counter = Counter()
    for team_key, slot in _iter_team_slots(report):
        if team_key not in team_keys:
            continue
        valor = str(slot.get(campo, "") or "").strip()
        if valor:
            counter[valor] += 1
    return counter


def _top_key(counter: Counter) -> str:
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def _skills_ativas_personagem(personagem: Personagem, arma: Arma | None = None) -> list[Any]:
    skills = list(getattr(personagem, "skills_personagem", []) or [])
    if skills:
        return skills
    if arma is not None:
        return list(getattr(arma, "habilidades", []) or [])
    return []


def gerar_recomendacoes_balanceamento(reports: list[dict[str, Any]], comparativo: dict[str, Any]) -> list[dict[str, Any]]:
    recomendacoes: list[dict[str, Any]] = []
    alertas_comuns = comparativo.get("alertas_mais_comuns", {}) or {}
    total_templates = max(1, int(comparativo.get("total_templates", len(reports)) or len(reports) or 1))

    familia_all = Counter()
    familia_win = Counter()
    papel_all = Counter()
    papel_win = Counter()
    pacote_all = Counter()
    pacote_win = Counter()

    for report in reports:
        times_favorecidos = _detectar_times_favorecidos(report)
        for team_key, slot in _iter_team_slots(report):
            papel = str(slot.get("papel", "") or "")
            familia = str(slot.get("familia_arma", "") or "")
            pacote = str(slot.get("pacote_arquetipo", "") or "")
            if papel:
                papel_all[papel] += 1
                if team_key in times_favorecidos:
                    papel_win[papel] += 1
            if familia:
                familia_all[familia] += 1
                if team_key in times_favorecidos:
                    familia_win[familia] += 1
            if pacote:
                pacote_all[pacote] += 1
                if team_key in times_favorecidos:
                    pacote_win[pacote] += 1

    if alertas_comuns.get("TEMPO_MUITO_CURTO", 0) >= max(1, total_templates // 2):
        recomendacoes.append(
            {
                "codigo": "AJUSTAR_BURST_GLOBAL",
                "eixo": "ritmo",
                "prioridade": "alta",
                "mensagem": "Muitas lutas estão terminando cedo demais. Vale revisar burst inicial, startup muito eficiente e conversão de dano por janela curta.",
                "evidencia": {"TEMPO_MUITO_CURTO": alertas_comuns.get("TEMPO_MUITO_CURTO", 0)},
            }
        )

    if (
        alertas_comuns.get("TEMPO_MUITO_LONGO", 0) >= max(1, total_templates // 2)
        or alertas_comuns.get("SUSTAIN_ALTO", 0) >= 1
    ):
        recomendacoes.append(
            {
                "codigo": "AJUSTAR_SUSTAIN_E_PUNISH",
                "eixo": "sustain",
                "prioridade": "alta",
                "mensagem": "As composições estão prolongando demais a luta. Revise cura, escudo, cooldown defensivo e ferramentas de conversão/punish.",
                "evidencia": {
                    "TEMPO_MUITO_LONGO": alertas_comuns.get("TEMPO_MUITO_LONGO", 0),
                    "SUSTAIN_ALTO": alertas_comuns.get("SUSTAIN_ALTO", 0),
                },
            }
        )

    if alertas_comuns.get("CURA_SOBRESSAIU", 0) >= 1:
        recomendacoes.append(
            {
                "codigo": "REVISAR_CURANDEIRO",
                "eixo": "papel",
                "prioridade": "media",
                "mensagem": "Curandeiro está aparecendo como eixo de dominância. Vale revisar sustain bruto e como o resto do elenco pune backline de cura.",
                "evidencia": {"CURA_SOBRESSAIU": alertas_comuns.get("CURA_SOBRESSAIU", 0)},
            }
        )

    if (
        alertas_comuns.get("BAIXA_CONCLUSAO_DE_ONDAS", 0) >= 1
        or alertas_comuns.get("SUSTAIN_BAIXO_HORDA", 0) >= 1
    ):
        recomendacoes.append(
            {
                "codigo": "FORTALECER_PACOTES_DE_HORDA",
                "eixo": "horda",
                "prioridade": "alta",
                "mensagem": "Os grupos estão sofrendo para fechar ondas. Revise sustain, controle de corredor, limpeza em área e prioridade contra elites.",
                "evidencia": {
                    "BAIXA_CONCLUSAO_DE_ONDAS": alertas_comuns.get("BAIXA_CONCLUSAO_DE_ONDAS", 0),
                    "SUSTAIN_BAIXO_HORDA": alertas_comuns.get("SUSTAIN_BAIXO_HORDA", 0),
                },
            }
        )

    if alertas_comuns.get("SEM_DEFENSOR_NA_HORDA", 0) >= 1:
        recomendacoes.append(
            {
                "codigo": "FRONTLINE_RECOMENDADA_NA_HORDA",
                "eixo": "composicao",
                "prioridade": "media",
                "mensagem": "Os cenários de horda continuam premiando frontline. Garanta pelo menos um defensor ou reforce peel/zone para compensar.",
                "evidencia": {"SEM_DEFENSOR_NA_HORDA": alertas_comuns.get("SEM_DEFENSOR_NA_HORDA", 0)},
            }
        )

    familia_bias = []
    for familia, total in familia_all.items():
        if total <= 0:
            continue
        taxa = float(familia_win.get(familia, 0) or 0) / float(total)
        if taxa >= 0.75 and total >= 2:
            familia_bias.append((familia, total, round(taxa, 3)))
    familia_bias.sort(key=lambda item: (item[2], item[1]), reverse=True)
    if familia_bias:
        familia, total, taxa = familia_bias[0]
        recomendacoes.append(
            {
                "codigo": "REVISAR_FAMILIA_DOMINANTE",
                "eixo": "arma",
                "prioridade": "media",
                "mensagem": f"A família '{familia}' apareceu forte demais entre os lados favorecidos. Vale revisar alcance, janela ativa e eficiência de conversão.",
                "evidencia": {"familia": familia, "presencas": total, "taxa_lado_favorecido": taxa},
            }
        )

    papel_bias = []
    for papel, total in papel_all.items():
        if total <= 0:
            continue
        taxa = float(papel_win.get(papel, 0) or 0) / float(total)
        if taxa >= 0.75 and total >= 2 and papel != "horda":
            papel_bias.append((papel, total, round(taxa, 3)))
    papel_bias.sort(key=lambda item: (item[2], item[1]), reverse=True)
    if papel_bias:
        papel, total, taxa = papel_bias[0]
        recomendacoes.append(
            {
                "codigo": "REVISAR_PAPEL_DOMINANTE",
                "eixo": "papel",
                "prioridade": "media",
                "mensagem": f"O papel '{papel}' está aparecendo demais nos lados favorecidos. Revise o pacote completo: classe, arma, skill e ritmo de decisão.",
                "evidencia": {"papel": papel, "presencas": total, "taxa_lado_favorecido": taxa},
            }
        )

    pacote_bias = []
    for pacote, total in pacote_all.items():
        if total <= 0:
            continue
        taxa = float(pacote_win.get(pacote, 0) or 0) / float(total)
        if taxa >= 0.75 and total >= 2:
            pacote_bias.append((pacote, total, round(taxa, 3)))
    pacote_bias.sort(key=lambda item: (item[2], item[1]), reverse=True)
    if pacote_bias:
        pacote, total, taxa = pacote_bias[0]
        recomendacoes.append(
            {
                "codigo": "REVISAR_PACOTE_DOMINANTE",
                "eixo": "pacote",
                "prioridade": "media",
                "mensagem": f"O pacote oficial '{pacote}' esta aparecendo demais nos lados favorecidos. Revise o conjunto inteiro: papel, arma, skills e IA.",
                "evidencia": {"pacote": pacote, "presencas": total, "taxa_lado_favorecido": taxa},
            }
        )

    if not recomendacoes:
        recomendacoes.append(
            {
                "codigo": "BALANCEAMENTO_ESTAVEL",
                "eixo": "geral",
                "prioridade": "baixa",
                "mensagem": "Os templates testados estão relativamente estáveis. O próximo ganho vem de aumentar cobertura de cenários e volume de runs.",
                "evidencia": {"templates_analisados": total_templates},
            }
        )

    return recomendacoes


def gerar_plano_ajuste_template(report: dict[str, Any]) -> dict[str, Any]:
    alertas = report.get("alertas", []) or []
    codigos = {str(alerta.get("codigo", "") or "") for alerta in alertas}
    times_favorecidos = _detectar_times_favorecidos(report)
    familias_fav = _slot_counter(report, times_favorecidos, "familia_arma")
    papeis_fav = _slot_counter(report, times_favorecidos, "papel")
    pacotes_fav = _slot_counter(report, times_favorecidos, "pacote_arquetipo")
    familia_dominante = _top_key(familias_fav)
    papel_dominante = _top_key(papeis_fav)
    pacote_dominante = _top_key(pacotes_fav)

    sugestoes: list[dict[str, Any]] = []

    def add(area: str, prioridade: str, alvo: str, acao: str, motivo: str):
        sugestoes.append(
            {
                "area": area,
                "prioridade": prioridade,
                "alvo": alvo,
                "acao": acao,
                "motivo": motivo,
            }
        )

    if "TEMPO_MUITO_CURTO" in codigos:
        add(
            "arma",
            "alta",
            familia_dominante or "familia_ofensiva",
            "reduzir conversão de burst inicial revisando startup, recovery, alcance efetivo e follow-up da família dominante",
            "o template está encerrando lutas cedo demais",
        )
        add(
            "skill",
            "alta",
            "kit_ofensivo",
            "apertar dano por janela curta e eficiência de skills de impacto para evitar snowball instantâneo",
            "o tempo médio está abaixo da faixa recomendada",
        )

    if "TEMPO_MUITO_LONGO" in codigos or "SUSTAIN_ALTO" in codigos:
        add(
            "skill",
            "alta",
            "cura_escudo_sustain",
            "reduzir sustain bruto ou aumentar janelas de punish após defesa/cura",
            "a luta está longa demais ou com conversão baixa",
        )

    if "DOMINANCIA_EXCESSIVA" in codigos:
        add(
            "composicao",
            "alta",
            papel_dominante or "time_favorecido",
            "revisar sinergia do lado favorecido e comparar se a composição adversária perdeu função demais",
            "a taxa de vitória do template saiu do teto aceitável",
        )
        add(
            "ia",
            "media",
            "foco_de_alvo",
            "verificar se a IA está punindo corretamente o pacote dominante, especialmente backline e janelas de resposta",
            "dominância excessiva também pode vir de decisão ruim do time adversário",
        )

        if pacote_dominante:
            add(
                "pacote",
                "alta",
                pacote_dominante,
                "revisar o conjunto oficial dominante como pacote fechado, separando o que vem de arma, skill, papel e coordenacao",
                "a dominancia atual parece vir da sinergia do conjunto inteiro, nao so de uma peca isolada",
            )

    if "CURA_SOBRESSAIU" in codigos:
        add(
            "papel",
            "alta",
            "curandeiro",
            "revisar orçamento do pacote de cura e como os outros papéis conseguem pressionar esse backline",
            "o curandeiro apareceu como eixo de domínio",
        )
        add(
            "ia",
            "media",
            "prioridade_backline",
            "aumentar pressão e foco tático contra cura quando a frontline inimiga abre janela",
            "parte do problema pode ser baixa punição ao suporte",
        )

    if "SEM_DEFENSOR_NA_HORDA" in codigos:
        add(
            "composicao",
            "alta",
            "frontline_horda",
            "incluir defensor ou reforçar ferramentas equivalentes de peel e segurar corredor",
            "a composição entrou na horda sem frontline recomendada",
        )

    if "BAIXA_CONCLUSAO_DE_ONDAS" in codigos or "SUSTAIN_BAIXO_HORDA" in codigos:
        add(
            "papel",
            "alta",
            papel_dominante or "pacote_horda",
            "reforçar sustain, controle de corredor e cobertura da backline no pacote de horda",
            "a equipe não está fechando ondas com consistência",
        )
        add(
            "ia",
            "media",
            "prioridade_elite_corredor",
            "melhorar leitura de elite, foco em ameaça alta e posicionamento defensivo em corredor",
            "o problema de horda também pode ser coordenação ruim",
        )

    if not sugestoes:
        add(
            "geral",
            "baixa",
            report.get("template_id", "template"),
            "manter o template estável e aumentar o número de seeds/cenários antes de mexer em números",
            "não houve sinal forte de desequilíbrio neste pacote",
        )

    prioridade_geral = "baixa"
    if any(item["prioridade"] == "alta" for item in sugestoes):
        prioridade_geral = "alta"
    elif any(item["prioridade"] == "media" for item in sugestoes):
        prioridade_geral = "media"

    return {
        "template_id": str(report.get("template_id", "") or ""),
        "modo": str(report.get("modo", "") or ""),
        "score_saude": calcular_score_saude_template(report),
        "prioridade_geral": prioridade_geral,
        "familia_dominante": familia_dominante,
        "papel_dominante": papel_dominante,
        "pacote_dominante": pacote_dominante,
        "sugestoes": sugestoes,
    }


def comparar_templates(reports: list[dict[str, Any]]) -> dict[str, Any]:
    alerta_counter = Counter()
    modo_counter = Counter()
    ranking: list[dict[str, Any]] = []
    papel_impacto: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "templates": 0.0,
            "damage_dealt": 0.0,
            "kills": 0.0,
            "score_medio": 0.0,
        }
    )
    pacote_impacto: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "templates": 0.0,
            "damage_dealt": 0.0,
            "kills": 0.0,
            "score_medio": 0.0,
        }
    )

    for report in reports:
        template_id = str(report.get("template_id", "") or "")
        modo = str(report.get("modo", "") or "")
        modo_counter[modo] += 1
        alertas = report.get("alertas", []) or []
        for alerta in alertas:
            alerta_counter[str(alerta.get("codigo", "DESCONHECIDO"))] += 1

        score_saude = calcular_score_saude_template(report)
        resumo_alertas = report.get("resumo_alertas", {}) or {}
        ranking.append(
            {
                "template_id": template_id,
                "modo": modo,
                "score_saude": score_saude,
                "avisos": int(resumo_alertas.get("aviso", 0) or 0),
                "infos": int(resumo_alertas.get("info", 0) or 0),
                "avg_tempo_simulado": float(report.get("avg_tempo_simulado", 0.0) or 0.0),
                "team_win_rate": dict(report.get("team_win_rate", {}) or {}),
            }
        )

        for papel, dados in (report.get("papeis", {}) or {}).items():
            impacto = papel_impacto[papel]
            impacto["templates"] += 1.0
            impacto["damage_dealt"] += float(dados.get("damage_dealt", 0.0) or 0.0)
            impacto["kills"] += float(dados.get("kills", 0.0) or 0.0)
            impacto["score_medio"] += score_saude

        for pacote, dados in (report.get("pacotes", {}) or {}).items():
            impacto = pacote_impacto[pacote]
            impacto["templates"] += 1.0
            impacto["damage_dealt"] += float(dados.get("damage_dealt", 0.0) or 0.0)
            impacto["kills"] += float(dados.get("kills", 0.0) or 0.0)
            impacto["score_medio"] += score_saude

    ranking.sort(key=lambda item: (item["score_saude"], -item["avisos"], -item["infos"]), reverse=True)
    papel_ranking = []
    for papel, dados in papel_impacto.items():
        templates_count = max(1.0, float(dados["templates"] or 1.0))
        papel_ranking.append(
            {
                "papel": papel,
                "templates": int(templates_count),
                "damage_dealt_medio": round(float(dados["damage_dealt"]) / templates_count, 3),
                "kills_medios": round(float(dados["kills"]) / templates_count, 3),
                "score_saude_medio": round(float(dados["score_medio"]) / templates_count, 3),
            }
        )
    papel_ranking.sort(key=lambda item: (item["score_saude_medio"], item["damage_dealt_medio"], item["kills_medios"]), reverse=True)

    pacote_ranking = []
    for pacote, dados in pacote_impacto.items():
        templates_count = max(1.0, float(dados["templates"] or 1.0))
        pacote_ranking.append(
            {
                "pacote": pacote,
                "templates": int(templates_count),
                "damage_dealt_medio": round(float(dados["damage_dealt"]) / templates_count, 3),
                "kills_medios": round(float(dados["kills"]) / templates_count, 3),
                "score_saude_medio": round(float(dados["score_medio"]) / templates_count, 3),
            }
        )
    pacote_ranking.sort(key=lambda item: (item["score_saude_medio"], item["damage_dealt_medio"], item["kills_medios"]), reverse=True)

    templates_criticos = [
        item for item in ranking
        if item["avisos"] > 0 or item["score_saude"] < 70.0
    ]

    planos_ajuste = [gerar_plano_ajuste_template(report) for report in reports]
    area_counter = Counter()
    prioridade_counter = Counter()
    for plano in planos_ajuste:
        prioridade_counter[str(plano.get("prioridade_geral", "baixa"))] += 1
        for sugestao in plano.get("sugestoes", []):
            area_counter[str(sugestao.get("area", "geral"))] += 1

    comparativo = {
        "total_templates": len(reports),
        "modos": dict(modo_counter),
        "ranking_templates": ranking,
        "melhor_template": ranking[0] if ranking else None,
        "pior_template": ranking[-1] if ranking else None,
        "alertas_mais_comuns": dict(alerta_counter.most_common(8)),
        "papeis_impacto": papel_ranking,
        "pacotes_impacto": pacote_ranking,
        "templates_criticos": templates_criticos,
        "planos_ajuste_templates": planos_ajuste,
        "resumo_plano_ajuste": {
            "areas_mais_citadas": dict(area_counter.most_common(8)),
            "prioridade_templates": dict(prioridade_counter),
        },
    }
    comparativo["recomendacoes_balanceamento"] = gerar_recomendacoes_balanceamento(reports, comparativo)
    return comparativo


def score_personagem_para_papel(personagem: Personagem, arma: Arma, papel: dict[str, Any]) -> CandidatoTatico:
    score = 0.0
    motivos: list[str] = []
    classe = normalizar_texto(getattr(personagem, "classe", ""))
    personalidade = normalizar_texto(getattr(personagem, "personalidade", ""))
    familia = str(getattr(arma, "familia", "") or "").strip().lower()
    subtipo_orbital = resolver_subtipo_orbital(arma) if familia == "orbital" else ""
    skills_ativas = _skills_ativas_personagem(personagem, arma)
    perfil_composto = inferir_arquetipo_composto(
        getattr(personagem, "classe", ""),
        getattr(personagem, "personalidade", ""),
        arma,
        skills_ativas,
    )
    pacote_referencia = perfil_composto.get("pacote_referencia") or {}
    papel_composto = str((perfil_composto.get("papel_primario") or {}).get("papel_id", "") or "")
    papel_secundario = str((perfil_composto.get("papel_secundario") or {}).get("papel_id", "") or "")

    for token in papel.get("arquetipos_prioritarios", []):
        token_norm = normalizar_texto(token)
        if token_norm and token_norm in classe:
            score += 4.0
            motivos.append(f"classe:{token}")

    for token in papel.get("tracos_prioritarios", []):
        token_norm = normalizar_texto(token)
        if token_norm and token_norm in personalidade:
            score += 3.0
            motivos.append(f"traco:{token}")

    if familia in set(papel.get("familias_arma_preferidas", []) or []):
        score += 4.0
        motivos.append(f"familia:{familia}")

    if papel_composto == papel["id"]:
        score += 2.5
        motivos.append(f"perfil:{papel_composto}")
    elif papel_secundario == papel["id"]:
        score += 1.2
        motivos.append(f"perfil_sec:{papel_secundario}")

    if papel["id"] in set(pacote_referencia.get("papeis_prioritarios", []) or []):
        score += 1.5
        motivos.append(f"pacote:{pacote_referencia.get('id', '')}")

    if papel["id"] == "bastiao_orbital":
        if familia == "orbital" and subtipo_orbital == "escudo":
            score += 5.5
            motivos.append("orbital:escudo")
        elif familia == "hibrida":
            score += 1.0
            motivos.append("orbital:backup_hibrida")
    elif papel["id"] == "artilheiro_orbital":
        if familia == "orbital" and subtipo_orbital == "drone":
            score += 5.0
            motivos.append("orbital:drone")
        elif familia == "orbital" and subtipo_orbital == "laminas":
            score += 3.2
            motivos.append("orbital:laminas")
        elif familia == "disparo":
            score += 1.0
            motivos.append("orbital:backup_disparo")
    elif papel["id"] == "maestro_astral":
        if familia == "orbital" and subtipo_orbital == "orbes":
            score += 5.0
            motivos.append("orbital:orbes")
        elif familia == "orbital":
            score += 2.5
            motivos.append(f"orbital:{subtipo_orbital or 'geral'}")
        elif familia == "foco":
            score += 2.0
            motivos.append("orbital:backup_foco")

    classes_magia = {normalizar_texto(v) for v in papel.get("classes_magia_preferidas", [])}
    forcas_magia = {normalizar_texto(v) for v in papel.get("forcas_magia_preferidas", [])}
    for skill in skills_ativas:
        if isinstance(skill, dict):
            nome_skill = skill.get("nome", "")
        else:
            nome_skill = str(skill)
        if not nome_skill:
            continue
        try:
            classificacao = get_skill_classification(nome_skill)
        except Exception:
            continue
        utilidade = normalizar_texto(getattr(classificacao, "classe_utilidade", ""))
        forca = normalizar_texto(getattr(classificacao, "classe_forca", ""))
        if utilidade in classes_magia:
            score += 1.5
            motivos.append(f"skill_util:{nome_skill}")
        if forca in forcas_magia:
            score += 1.0
            motivos.append(f"skill_forca:{nome_skill}")

    stats = getattr(personagem, "stats", None) or {}
    vida = float(stats.get("vida_max", 100.0) or 100.0)
    mana = float(stats.get("mana_max", getattr(personagem, "mana", 0.0)) or 0.0)
    forca_attr = float(getattr(personagem, "forca", 0.0) or 0.0)

    papel_id = papel["id"]
    if papel_id == "defensor":
        score += min(vida / 60.0, 3.0)
    elif papel_id == "curandeiro":
        score += min(mana / 25.0, 3.0)
    elif papel_id == "bastiao_orbital":
        score += min(vida / 70.0, 2.4)
        score += min(mana / 35.0, 1.8)
    elif papel_id == "artilheiro_orbital":
        score += min(mana / 28.0, 2.6)
        score += min(forca_attr / 4.0, 1.2)
    elif papel_id == "maestro_astral":
        score += min(mana / 24.0, 3.2)
    elif papel_id in {"bruiser", "assassino", "duelista"}:
        score += min(forca_attr / 3.0, 2.0)
    elif papel_id in {"atirador", "suporte_controle", "invocador", "controlador_de_area"}:
        score += min(mana / 30.0, 2.5)

    return CandidatoTatico(
        personagem=personagem,
        arma=arma,
        papel_id=papel_id,
        score=round(score, 3),
        motivos=motivos[:8],
        pacote_arquetipo=str(pacote_referencia.get("id", "") or ""),
        pacote_nome=str(pacote_referencia.get("nome", "") or ""),
        desvios_pacote=list(perfil_composto.get("desvios_pacote", []) or []),
    )


def construir_pool_tatico() -> tuple[AppState, dict[str, dict[str, Any]], list[CandidatoTatico]]:
    state = AppState.get()
    papeis_data, _, _ = carregar_catalogos()
    papeis = {item["id"]: item for item in papeis_data.get("papeis", [])}
    weapons = {arma.nome: arma for arma in state.weapons}
    candidatos: list[CandidatoTatico] = []
    for personagem in state.characters:
        arma = weapons.get(getattr(personagem, "nome_arma", ""))
        if arma is None:
            continue
        for papel in papeis.values():
            candidatos.append(score_personagem_para_papel(personagem, arma, papel))
    return state, papeis, candidatos


def selecionar_para_papel(
    papel_id: str,
    candidatos: list[CandidatoTatico],
    usados: set[str] | None = None,
    limite: int = 1,
) -> list[CandidatoTatico]:
    usados = usados or set()
    filtrados = [
        c for c in candidatos
        if c.papel_id == papel_id and c.personagem.nome not in usados
    ]
    filtrados.sort(key=lambda c: (c.score, c.personagem.nome), reverse=True)
    return filtrados[:limite]


def selecionar_para_slot(
    slot: dict[str, Any],
    candidatos: list[CandidatoTatico],
    usados: set[str] | None = None,
    limite: int = 1,
) -> list[CandidatoTatico]:
    usados = usados or set()
    papel_id = str(slot.get("papel", "") or "")
    nome_forcado = str(slot.get("personagem", "") or slot.get("nome_personagem", "") or "").strip()
    pacote_forcado = str(slot.get("pacote_arquetipo", "") or "").strip().lower()
    classe_forcada = normalizar_texto(slot.get("classe", "")) if slot.get("classe") else ""
    personalidade_forcada = normalizar_texto(slot.get("personalidade", "")) if slot.get("personalidade") else ""
    familia_forcada = str(slot.get("familia_arma", "") or "").strip().lower()

    filtrados = [
        c for c in candidatos
        if c.papel_id == papel_id and c.personagem.nome not in usados
    ]
    if nome_forcado:
        filtrados = [c for c in filtrados if c.personagem.nome == nome_forcado]
    if pacote_forcado:
        filtrados = [c for c in filtrados if str(c.pacote_arquetipo or "").strip().lower() == pacote_forcado]
    if classe_forcada:
        filtrados = [c for c in filtrados if normalizar_texto(getattr(c.personagem, "classe", "")) == classe_forcada]
    if personalidade_forcada:
        filtrados = [c for c in filtrados if normalizar_texto(getattr(c.personagem, "personalidade", "")) == personalidade_forcada]
    if familia_forcada:
        filtrados = [c for c in filtrados if str(getattr(c.arma, "familia", "") or "").strip().lower() == familia_forcada]

    filtrados.sort(key=lambda c: (c.score, c.personagem.nome), reverse=True)
    return filtrados[:limite]


def montar_template_selecionado(template_id: str) -> dict[str, Any]:
    state, papeis, candidatos = construir_pool_tatico()
    _, _, templates_data = carregar_catalogos()
    template = next((t for t in templates_data.get("templates", []) if t["id"] == template_id), None)
    if template is None:
        raise ValueError(f"Template tatico nao encontrado: {template_id}")

    usados_globais: set[str] = set()
    selecao = {
        "template": deepcopy(template),
        "team_a": [],
        "team_b": [],
        "horda": [],
        "horda_config": None,
    }

    for team_key in ("team_a", "team_b"):
        for slot in template.get(team_key, {}).get("slots", []):
            papel_id = slot["papel"]
            escolhidos = selecionar_para_slot(slot, candidatos, usados_globais, limite=1)
            if not escolhidos:
                raise ValueError(f"Nao encontrei personagem para o papel '{papel_id}' no template '{template_id}'")
            escolhido = escolhidos[0]
            usados_globais.add(escolhido.personagem.nome)
            selecao[team_key].append(
                {
                    "papel": papel_id,
                    "personagem": escolhido.personagem,
                    "arma": escolhido.arma,
                    "score": escolhido.score,
                    "motivos": escolhido.motivos,
                    "pacote_arquetipo": escolhido.pacote_arquetipo,
                    "pacote_nome": escolhido.pacote_nome,
                    "desvios_pacote": list(escolhido.desvios_pacote or []),
                }
            )

    if template["modo"] == "grupo_vs_horda":
        preset_id = (template.get("horda") or {}).get("preset_id")
        preset = get_horde_preset(preset_id)
        if preset is None and template.get("horda"):
            preset = deepcopy(template["horda"])
        selecao["horda_config"] = preset or {}
        selecao["horda"] = gerar_horda(template.get("horda") or {})

    return selecao


def gerar_horda(config_horda: dict[str, Any]) -> list[dict[str, Any]]:
    quantidade = int(config_horda.get("quantidade", 5))
    familia = str(config_horda.get("familia_arma", "lamina"))
    classe = str(config_horda.get("classe", "Guerreiro (Força Bruta)"))
    personalidade = str(config_horda.get("personalidade", "Agressivo"))
    horda: list[dict[str, Any]] = []
    for idx in range(quantidade):
        arma = Arma(
            nome=f"Horda Lixo {idx + 1}",
            familia=familia,
            categoria="arma_fisica",
            subtipo="garra" if familia == "lamina" else "improviso",
            tipo="Reta",
            dano=3.2,
            peso=2.1,
            velocidade_ataque=0.88,
            critico=0.02,
            habilidades=[],
            afinidade_elemento=None,
            estilo="Rustico",
            raridade="Padrão",
        )
        personagem = Personagem(
            nome=f"Zumbi_{idx + 1:02d}",
            tamanho=1.68,
            forca=3.4,
            mana=1.2,
            nome_arma=arma.nome,
            peso_arma_cache=arma.peso,
            r=110,
            g=145,
            b=110,
            classe=classe,
            personalidade=personalidade,
            lore="Minion temporario gerado pelo harness tatico.",
        )
        horda.append(
            {
                "papel": "horda",
                "personagem": personagem,
                "arma": arma,
                "score": 0.0,
                "motivos": ["horda_temporaria"],
                "pacote_arquetipo": "",
                "pacote_nome": "",
                "desvios_pacote": [],
            }
        )
    return horda


class OverlayState:
    def __init__(self, state: AppState, extra_chars: list[Personagem], extra_weapons: list[Arma], match_config: dict[str, Any]):
        self.state = state
        self.extra_chars = extra_chars
        self.extra_weapons = extra_weapons
        self.match_config = match_config
        self.old_match = deepcopy(state.match_config)
        self.old_chars = list(state._characters)
        self.old_weapons = list(state._weapons)

    def __enter__(self):
        self.state._characters = self.old_chars + list(self.extra_chars)
        self.state._weapons = self.old_weapons + list(self.extra_weapons)
        self.state._match = {**self.old_match, **self.match_config}
        return self

    def __exit__(self, exc_type, exc, tb):
        self.state._characters = self.old_chars
        self.state._weapons = self.old_weapons
        self.state._match = self.old_match
        return False


def _resumir_times(sim: Simulador, nomes_a: set[str], nomes_b: set[str]) -> dict[str, Any]:
    stats = sim.stats_collector.get_summary() if hasattr(sim, "stats_collector") else {}
    fighters = getattr(sim, "fighters", []) or []
    team_status = {
        "team_a": {"vivos": 0, "mortos": 0, "names": []},
        "team_b": {"vivos": 0, "mortos": 0, "names": []},
    }
    for fighter in fighters:
        nome = getattr(getattr(fighter, "dados", None), "nome", "")
        if nome in nomes_a:
            bucket = "team_a"
        elif nome in nomes_b:
            bucket = "team_b"
        else:
            continue
        team_status[bucket]["names"].append(nome)
        if getattr(fighter, "morto", False):
            team_status[bucket]["mortos"] += 1
        else:
            team_status[bucket]["vivos"] += 1

    team_stats = {
        "team_a": {"damage_dealt": 0.0, "damage_taken": 0.0, "kills": 0, "deaths": 0, "skills_cast": 0, "mana_spent": 0.0},
        "team_b": {"damage_dealt": 0.0, "damage_taken": 0.0, "kills": 0, "deaths": 0, "skills_cast": 0, "mana_spent": 0.0},
    }
    for nome, fighter_stats in stats.items():
        if nome in nomes_a:
            bucket = "team_a"
        elif nome in nomes_b:
            bucket = "team_b"
        else:
            continue
        team_stats[bucket]["damage_dealt"] += float(fighter_stats.get("damage_dealt", 0.0) or 0.0)
        team_stats[bucket]["damage_taken"] += float(fighter_stats.get("damage_taken", 0.0) or 0.0)
        team_stats[bucket]["kills"] += int(fighter_stats.get("kills", 0) or 0)
        team_stats[bucket]["deaths"] += int(fighter_stats.get("deaths", 0) or 0)
        team_stats[bucket]["skills_cast"] += int(fighter_stats.get("skills_cast", 0) or 0)
        team_stats[bucket]["mana_spent"] += float(fighter_stats.get("mana_spent", 0.0) or 0.0)

    team_stats["team_a"] = {k: round(v, 3) if isinstance(v, float) else v for k, v in team_stats["team_a"].items()}
    team_stats["team_b"] = {k: round(v, 3) if isinstance(v, float) else v for k, v in team_stats["team_b"].items()}
    return {"fighters": stats, "team_stats": team_stats, "team_status": team_status}


def executar_match_headless_real(
    state: AppState,
    team_a: list[dict[str, Any]],
    team_b: list[dict[str, Any]],
    *,
    cenario: str,
    duracao_max_seg: float,
    modo: str = "grupo_vs_grupo",
    horda_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra_slots = team_a if modo == "grupo_vs_horda" else (team_a + team_b)
    extra_chars = [slot["personagem"] for slot in extra_slots if slot["personagem"].nome not in state.character_names()]
    extra_weapons = [slot["arma"] for slot in extra_slots if slot["arma"].nome not in state.weapon_names()]
    if modo == "grupo_vs_horda":
        match_config = build_horde_match_config(
            [
                {
                    "team_id": 0,
                    "label": "Expedicao",
                    "members": [slot["personagem"].nome for slot in team_a],
                }
            ],
            horda_config or {},
            cenario=cenario,
        )
    else:
        match_config = build_team_match_config(
            [
                {
                    "team_id": 0,
                    "label": "Time 1",
                    "members": [slot["personagem"].nome for slot in team_a],
                },
                {
                    "team_id": 1,
                    "label": "Time 2",
                    "members": [slot["personagem"].nome for slot in team_b],
                },
            ],
            cenario=cenario,
        )

    with OverlayState(state, extra_chars, extra_weapons, match_config):
        sim = Simulador()
        sim.TEMPO_MAX_LUTA = float(duracao_max_seg)
        dt = 1.0 / 60.0
        start = time.perf_counter()
        max_frames = int(duracao_max_seg * 60) + 30
        for _ in range(max_frames):
            if sim.vencedor:
                break
            sim.update(dt)
        elapsed_real = round(time.perf_counter() - start, 3)
        resumo = _resumir_times(
            sim,
            {slot["personagem"].nome for slot in team_a},
            {slot["personagem"].nome for slot in team_b},
        )
        vencedor = str(sim.vencedor or "Sem vencedor")
        frames = int(getattr(getattr(sim, "stats_collector", None), "_frame", 0) or 0)
        try:
            import pygame
            pygame.display.quit()
            pygame.mixer.quit()
            pygame.quit()
        except Exception:
            pass
        payload = {
            "vencedor": vencedor,
            "frames": frames,
            "tempo_simulado": round(frames / 60.0, 3),
            "tempo_real": elapsed_real,
            **resumo,
        }
        if modo == "grupo_vs_horda" and getattr(sim, "horde_manager", None):
            payload["horda"] = sim.horde_manager.export_summary()
        return payload


def agregar_relatorio(template: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    team_wins = Counter()
    fighter_wins = Counter()
    frames = 0
    tempo_simulado = 0.0
    tempo_real = 0.0
    damage_totals = {"team_a": 0.0, "team_b": 0.0}
    team_metric_totals = {
        "team_a": {"damage_dealt": 0.0, "damage_taken": 0.0, "kills": 0.0, "deaths": 0.0, "skills_cast": 0.0, "mana_spent": 0.0},
        "team_b": {"damage_dealt": 0.0, "damage_taken": 0.0, "kills": 0.0, "deaths": 0.0, "skills_cast": 0.0, "mana_spent": 0.0},
    }
    team_survival_totals = {"team_a": 0.0, "team_b": 0.0}
    papel_resumo: dict[str, dict[str, Any]] = defaultdict(lambda: {"presencas": 0, "damage_dealt": 0.0, "kills": 0})
    pacote_resumo: dict[str, dict[str, Any]] = defaultdict(lambda: {"presencas": 0, "damage_dealt": 0.0, "kills": 0, "nome": ""})
    horda_wave_total = 0.0
    horda_kills_total = 0.0
    horda_completion_total = 0.0
    horda_fail_total = 0.0
    horda_spawned_total = 0.0

    for run in runs:
        frames += int(run.get("frames", 0) or 0)
        tempo_simulado += float(run.get("tempo_simulado", 0.0) or 0.0)
        tempo_real += float(run.get("tempo_real", 0.0) or 0.0)
        vencedor = str(run.get("vencedor", ""))
        if vencedor.startswith("Time 1") or vencedor in run.get("team_status", {}).get("team_a", {}).get("names", []):
            team_wins["team_a"] += 1
        elif vencedor.startswith("Time 2") or vencedor in run.get("team_status", {}).get("team_b", {}).get("names", []):
            team_wins["team_b"] += 1
        fighter_wins[vencedor] += 1

        for team_key in ("team_a", "team_b"):
            team_stats = run.get("team_stats", {}).get(team_key, {}) or {}
            damage_totals[team_key] += float(team_stats.get("damage_dealt", 0.0) or 0.0)
            for metric in team_metric_totals[team_key]:
                team_metric_totals[team_key][metric] += float(team_stats.get(metric, 0.0) or 0.0)
            team_status = run.get("team_status", {}).get(team_key, {}) or {}
            vivos = float(team_status.get("vivos", 0) or 0)
            mortos = float(team_status.get("mortos", 0) or 0)
            total = vivos + mortos
            if total > 0:
                team_survival_totals[team_key] += vivos / total
        if run.get("horda"):
            horda_wave_total += float(run["horda"].get("wave_atual", 0) or 0)
            horda_kills_total += float(run["horda"].get("total_killed", 0) or 0)
            horda_spawned_total += float(run["horda"].get("total_spawned", 0) or 0)
            horda_completion_total += 1.0 if run["horda"].get("completed") else 0.0
            horda_fail_total += 1.0 if run["horda"].get("failed") else 0.0

        fighter_stats = run.get("fighters", {}) or {}
        papel_lookup = {}
        pacote_lookup = {}
        for team_key in ("team_a", "team_b"):
            for slot in template[team_key]:
                nome = slot.get("nome")
                if not nome and "personagem" in slot:
                    nome = getattr(slot["personagem"], "nome", "")
                if nome:
                    papel_lookup[nome] = slot["papel"]
                    pacote_lookup[nome] = {
                        "id": str(slot.get("pacote_arquetipo", "") or ""),
                        "nome": str(slot.get("pacote_nome", "") or ""),
                    }
        for nome, stats in fighter_stats.items():
            papel_id = papel_lookup.get(nome, "horda")
            papel_resumo[papel_id]["presencas"] += 1
            papel_resumo[papel_id]["damage_dealt"] += float(stats.get("damage_dealt", 0.0) or 0.0)
            papel_resumo[papel_id]["kills"] += int(stats.get("kills", 0) or 0)
            pacote_info = pacote_lookup.get(nome, {})
            pacote_id = str(pacote_info.get("id", "") or "")
            if pacote_id:
                pacote_resumo[pacote_id]["presencas"] += 1
                pacote_resumo[pacote_id]["damage_dealt"] += float(stats.get("damage_dealt", 0.0) or 0.0)
                pacote_resumo[pacote_id]["kills"] += int(stats.get("kills", 0) or 0)
                pacote_resumo[pacote_id]["nome"] = str(pacote_info.get("nome", "") or pacote_id)

    total_runs = max(len(runs), 1)
    resumo = {
        "template_id": template["template_meta"]["id"],
        "modo": template["template_meta"]["modo"],
        "runs": len(runs),
        "team_wins": dict(team_wins),
        "team_win_rate": {
            "team_a": round(float(team_wins.get("team_a", 0) or 0) / total_runs, 3),
            "team_b": round(float(team_wins.get("team_b", 0) or 0) / total_runs, 3),
        },
        "winner_counts": dict(fighter_wins),
        "avg_frames": round(frames / total_runs, 2),
        "avg_tempo_simulado": round(tempo_simulado / total_runs, 3),
        "avg_tempo_real": round(tempo_real / total_runs, 3),
        "team_damage_avg": {
            "team_a": round(damage_totals["team_a"] / total_runs, 3),
            "team_b": round(damage_totals["team_b"] / total_runs, 3),
        },
        "team_metric_avg": {
            team_key: {
                metric: round(value / total_runs, 3)
                for metric, value in team_metric_totals[team_key].items()
            }
            for team_key in ("team_a", "team_b")
        },
        "team_survival_avg": {
            team_key: round(team_survival_totals[team_key] / total_runs, 3)
            for team_key in ("team_a", "team_b")
        },
        "papeis": {
            papel: {
                "presencas": dados["presencas"],
                "damage_dealt": round(dados["damage_dealt"], 3),
                "kills": dados["kills"],
            }
            for papel, dados in sorted(papel_resumo.items())
        },
        "pacotes": {
            pacote: {
                "nome": dados["nome"] or pacote,
                "presencas": dados["presencas"],
                "damage_dealt": round(dados["damage_dealt"], 3),
                "kills": dados["kills"],
            }
            for pacote, dados in sorted(pacote_resumo.items())
        },
    }
    if horda_wave_total > 0:
        resumo["horda"] = {
            "avg_wave_alcancada": round(horda_wave_total / total_runs, 3),
            "avg_abates_horda": round(horda_kills_total / total_runs, 3),
            "avg_spawned": round(horda_spawned_total / total_runs, 3),
            "completion_rate": round(horda_completion_total / total_runs, 3),
            "failure_rate": round(horda_fail_total / total_runs, 3),
        }
    resumo["alertas"] = gerar_alertas_balanceamento(template, resumo)
    resumo["resumo_alertas"] = dict(Counter(alerta["nivel"] for alerta in resumo["alertas"]))
    return resumo


def executar_template(template_id: str, runs: int, seed: int = 0) -> dict[str, Any]:
    random.seed(seed)
    selecao = montar_template_selecionado(template_id)
    state = AppState.get()
    template_meta = selecao["template"]
    if selecao["horda"]:
        team_b = selecao["horda"]
    else:
        team_b = selecao["team_b"]

    lutas = []
    for idx in range(runs):
        random.seed(seed + idx)
        resultado = executar_match_headless_real(
            state,
            selecao["team_a"],
            team_b,
            cenario=template_meta.get("cenario", "Arena"),
            duracao_max_seg=float(template_meta.get("duracao_max_seg", 90.0) or 90.0),
            modo=template_meta.get("modo", "grupo_vs_grupo"),
            horda_config=selecao.get("horda_config"),
        )
        resultado["run_index"] = idx
        lutas.append(resultado)

    report_template = {
        "template_meta": {
            "id": template_meta["id"],
            "modo": template_meta["modo"],
            "nome": template_meta["nome"],
            "cenario": template_meta.get("cenario", "Arena"),
        },
        "team_labels": {
            "team_a": template_meta.get("team_a", {}).get("label", "Time 1"),
            "team_b": template_meta.get("team_b", {}).get("label", "Time 2"),
        },
        "team_a": [
            {
                "papel": slot["papel"],
                "nome": slot["personagem"].nome,
                "arma": slot["arma"].nome,
                "familia_arma": slot["arma"].familia,
                "score": slot["score"],
                "pacote_arquetipo": str(slot.get("pacote_arquetipo", "") or ""),
                "pacote_nome": str(slot.get("pacote_nome", "") or ""),
                "desvios_pacote": list(slot.get("desvios_pacote", []) or []),
            }
            for slot in selecao["team_a"]
        ],
        "team_b": [
            {
                "papel": slot["papel"],
                "nome": slot["personagem"].nome,
                "arma": slot["arma"].nome,
                "familia_arma": slot["arma"].familia,
                "score": slot["score"],
                "pacote_arquetipo": str(slot.get("pacote_arquetipo", "") or ""),
                "pacote_nome": str(slot.get("pacote_nome", "") or ""),
                "desvios_pacote": list(slot.get("desvios_pacote", []) or []),
            }
            for slot in team_b
        ],
    }
    report = agregar_relatorio(report_template, lutas)
    report.update(report_template)
    report["lutas"] = lutas
    return report


def listar_templates() -> list[dict[str, Any]]:
    _, _, templates_data = carregar_catalogos()
    return templates_data.get("templates", [])


def salvar_relatorio(report: dict[str, Any], json_out: str | None) -> Path:
    dirs = ensure_posto_dirs()
    if json_out:
        path = Path(json_out)
    else:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        report_slug = str(report.get("template_id") or report.get("modo") or "comparativo")
        path = dirs["headless_reports"] / f"harness_tatico_{report_slug}_{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness tatico do posto headless")
    parser.add_argument("--modo", choices=["1v1", "grupo_vs_grupo", "grupo_vs_horda", "todos"], default="todos")
    parser.add_argument("--template", default=None, help="ID de um template especifico")
    parser.add_argument("--runs", type=int, default=None, help="Quantidade de execucoes por template")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--listar-templates", action="store_true")
    args = parser.parse_args()

    templates = listar_templates()
    if args.listar_templates:
        print(json.dumps(templates, ensure_ascii=False, indent=2))
        return 0

    filtrados = templates
    if args.template:
        filtrados = [tpl for tpl in templates if tpl["id"] == args.template]
        if not filtrados:
            raise SystemExit(f"Template nao encontrado: {args.template}")
    elif args.modo != "todos":
        filtrados = [tpl for tpl in templates if tpl["modo"] == args.modo]

    reports = []
    for idx, template in enumerate(filtrados):
        runs = int(args.runs or template.get("runs_recomendados", 1))
        report = executar_template(template["id"], runs=runs, seed=args.seed + idx * 17)
        reports.append(report)

    payload: dict[str, Any]
    if len(reports) == 1:
        payload = reports[0]
    else:
        payload = {
            "modo": args.modo,
            "templates": reports,
            "total_templates": len(reports),
            "comparativo": comparar_templates(reports),
        }

    path = salvar_relatorio(payload, args.json_out)
    print(f"[harness tatico] relatorio salvo em: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
