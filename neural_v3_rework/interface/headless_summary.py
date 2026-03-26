import json
import os
import re


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDAS_DIR = os.path.join(ROOT_DIR, "saidas")
SAIDAS_HEADLESS_DIR = os.path.join(SAIDAS_DIR, "headless")
SAIDAS_HEADLESS_REPORTS_DIR = os.path.join(SAIDAS_HEADLESS_DIR, "relatorios")
FILE_TEMPLATES_TATICOS = os.path.join(ROOT_DIR, "dados", "templates_composicao_tatica.json")
REPORT_STAMP_RE = re.compile(r"_(\d{8}_\d{6})\.json$", re.IGNORECASE)


def formatar_token_relatorio(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""
    return texto.replace("_", " ").strip().title()


def stamp_relatorio(nome_arquivo):
    match = REPORT_STAMP_RE.search(str(nome_arquivo or ""))
    return match.group(1) if match else ""


def _carregar_relatorio_recente(report_dir):
    if not os.path.isdir(report_dir):
        return "", None
    arquivos = [
        os.path.join(report_dir, nome)
        for nome in os.listdir(report_dir)
        if nome.lower().endswith(".json")
    ]
    if not arquivos:
        return "", None
    arquivos.sort(key=lambda path: (stamp_relatorio(os.path.basename(path)), os.path.basename(path)))
    latest = arquivos[-1]
    with open(latest, "r", encoding="utf-8") as handle:
        return latest, json.load(handle)


def _carregar_templates_taticos(path=FILE_TEMPLATES_TATICOS):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {}
    lookup = {}
    for item in data.get("templates", []):
        if isinstance(item, dict) and item.get("id"):
            lookup[str(item["id"])] = item
    return lookup


def _score_prioridade(prioridade):
    prioridade = str(prioridade or "").strip().lower()
    if prioridade == "alta":
        return 3
    if prioridade == "media":
        return 2
    return 1


def _selecionar_plano_inspecao(comparativo):
    planos = list(comparativo.get("planos_ajuste_templates", []) or [])
    if not planos:
        return None
    planos.sort(
        key=lambda item: (
            _score_prioridade(item.get("prioridade_geral")),
            float(item.get("score_saude", 0.0) or 0.0) * -1,
        ),
        reverse=True,
    )
    return planos[0]


def _resolver_alvo_inspecao_comparativo(comparativo):
    plano = _selecionar_plano_inspecao(comparativo)
    if plano:
        sugestoes = list(plano.get("sugestoes", []) or [])
        if sugestoes:
            ordem_area = {"arma": 5, "skill": 4, "papel": 3, "ia": 2, "composicao": 1, "geral": 0}
            sugestoes.sort(key=lambda item: (ordem_area.get(str(item.get("area", "")), 0), _score_prioridade(item.get("prioridade"))), reverse=True)
            sugestao = sugestoes[0]
            area = formatar_token_relatorio(sugestao.get("area", "geral")) or "Geral"
            template_id = formatar_token_relatorio(plano.get("template_id", "")) or "Template"
            alvo = formatar_token_relatorio(sugestao.get("alvo", "")) or area
            acao = str(sugestao.get("acao", "") or "").strip()
            motivo = str(sugestao.get("motivo", "") or "").strip()
            pacote = formatar_token_relatorio(plano.get("pacote_dominante", "")) or ""
            if pacote:
                alvo = f"{alvo} | Pacote: {pacote}"
            return {
                "inspection_title": f"Inspecionar {area} em {template_id}",
                "inspection_text": f"Alvo: {alvo}. {acao}. Motivo: {motivo}",
            }

    recomendacoes = list(comparativo.get("recomendacoes_balanceamento", []) or [])
    if recomendacoes:
        rec = recomendacoes[0]
        eixo = formatar_token_relatorio(rec.get("eixo", "geral")) or "Geral"
        return {
            "inspection_title": f"Inspecionar {eixo}",
            "inspection_text": str(rec.get("mensagem", "") or "Sem alvo de inspecao detalhado."),
        }

    return {
        "inspection_title": "Sem alvo de inspecao definido",
        "inspection_text": "Rode mais templates ou mais seeds para o comparativo apontar um foco claro.",
    }


def _resolver_foco_balanceamento_comparativo(comparativo):
    plano = _selecionar_plano_inspecao(comparativo)
    if plano:
        sugestoes = list(plano.get("sugestoes", []) or [])
        if sugestoes:
            ordem_area = {"arma": 5, "skill": 4, "papel": 3, "ia": 2, "composicao": 1, "geral": 0}
            sugestoes.sort(
                key=lambda item: (ordem_area.get(str(item.get("area", "")), 0), _score_prioridade(item.get("prioridade"))),
                reverse=True,
            )
            sugestao = sugestoes[0]
            area = str(sugestao.get("area", "") or "geral")
            alvo = str(sugestao.get("alvo", "") or "").strip()
            pacote = str(plano.get("pacote_dominante", "") or "").strip()
            return {
                "found": True,
                "template_id": str(plano.get("template_id", "") or ""),
                "pacote_foco": pacote,
                "area": area,
                "area_text": formatar_token_relatorio(area) or "Geral",
                "alvo": alvo,
                "alvo_text": formatar_token_relatorio(alvo) or (formatar_token_relatorio(area) or "Geral"),
                "acao": str(sugestao.get("acao", "") or "").strip(),
                "motivo": str(sugestao.get("motivo", "") or "").strip(),
                "prioridade": str(sugestao.get("prioridade", "") or "").strip(),
            }

    recomendacoes = list(comparativo.get("recomendacoes_balanceamento", []) or [])
    if recomendacoes:
        rec = recomendacoes[0]
        eixo = str(rec.get("eixo", "") or "geral")
        return {
            "found": True,
            "template_id": "",
            "pacote_foco": "",
            "area": eixo,
            "area_text": formatar_token_relatorio(eixo) or "Geral",
            "alvo": "",
            "alvo_text": formatar_token_relatorio(eixo) or "Geral",
            "acao": str(rec.get("codigo", "") or "").strip(),
            "motivo": str(rec.get("mensagem", "") or "").strip(),
            "prioridade": "",
        }

    return {
        "found": False,
        "template_id": "",
        "pacote_foco": "",
        "area": "",
        "area_text": "",
        "alvo": "",
        "alvo_text": "",
        "acao": "",
        "motivo": "",
        "prioridade": "",
    }


def _construir_target_relatorio(report, *, path="", templates_lookup=None):
    report = dict(report or {})
    template_id = str(report.get("template_id", "") or "")
    template_meta = dict(report.get("template_meta", {}) or {})
    template_cfg = dict((templates_lookup or {}).get(template_id, {}) or {})
    horda_cfg = dict(template_cfg.get("horda", {}) or {})
    pacotes = dict(report.get("pacotes", {}) or {})
    pacote_foco = ""
    if pacotes:
        pacote_foco = max(
            pacotes.items(),
            key=lambda item: float((item[1] or {}).get("damage_dealt", 0.0) or 0.0),
        )[0]
    return {
        "found": True,
        "path": path,
        "modo": str(report.get("modo", "") or ""),
        "template_id": template_id,
        "template_nome": str(template_meta.get("nome") or template_cfg.get("nome") or template_id),
        "cenario": str(report.get("cenario") or template_meta.get("cenario") or template_cfg.get("cenario") or "Arena"),
        "team_a_members": [str(item.get("nome", "") or "").strip() for item in report.get("team_a", []) or [] if str(item.get("nome", "") or "").strip()],
        "team_b_members": [str(item.get("nome", "") or "").strip() for item in report.get("team_b", []) or [] if str(item.get("nome", "") or "").strip()],
        "team_labels": dict(report.get("team_labels", {}) or {}),
        "horde_preset_id": str(report.get("horda_preset_id") or horda_cfg.get("preset_id") or ""),
        "pacote_foco": pacote_foco,
    }


def _iter_slots_relatorio(report):
    for team_key in ("team_a", "team_b"):
        for slot in list((report or {}).get(team_key, []) or []):
            if isinstance(slot, dict):
                yield team_key, slot


def _top_pacote_relatorio(report):
    pacotes = dict((report or {}).get("pacotes", {}) or {})
    if pacotes:
        return max(
            pacotes.items(),
            key=lambda item: float((item[1] or {}).get("damage_dealt", 0.0) or 0.0),
        )[0]
    for _team_key, slot in _iter_slots_relatorio(report):
        pacote = str(slot.get("pacote_arquetipo", "") or "").strip()
        if pacote:
            return pacote
    return ""


def _resolver_report_foco(data):
    comparativo = data.get("comparativo") if isinstance(data, dict) else None
    if comparativo:
        plano = _selecionar_plano_inspecao(comparativo)
        template_id = str((plano or {}).get("template_id", "") or "")
        pacote_dominante = str((plano or {}).get("pacote_dominante", "") or "")
        for report in data.get("templates", []) or []:
            if str((report or {}).get("template_id", "") or "") == template_id:
                return report, (pacote_dominante or _top_pacote_relatorio(report))
    if isinstance(data, dict) and data.get("template_id"):
        return data, _top_pacote_relatorio(data)
    return None, ""


def load_latest_headless_archetype_focus(report_dir=SAIDAS_HEADLESS_REPORTS_DIR):
    vazio = {
        "found": False,
        "path": "",
        "template_id": "",
        "template_nome": "",
        "modo": "",
        "pacote_foco": "",
        "pacote_nome": "",
        "personagem_nome": "",
        "arma_nome": "",
        "team_key": "",
    }
    try:
        latest, data = _carregar_relatorio_recente(report_dir)
        if not latest or not isinstance(data, dict):
            return vazio
        report, pacote_foco = _resolver_report_foco(data)
        if not report:
            return vazio
        pacote_nome = ""
        if pacote_foco:
            pacote_nome = str((((report.get("pacotes", {}) or {}).get(pacote_foco, {}) or {}).get("nome", "") or ""))
        slot_foco = None
        for team_key, slot in _iter_slots_relatorio(report):
            if pacote_foco and str(slot.get("pacote_arquetipo", "") or "") == pacote_foco:
                slot_foco = (team_key, slot)
                break
        if slot_foco is None:
            for team_key, slot in _iter_slots_relatorio(report):
                if str(slot.get("nome", "") or "").strip():
                    slot_foco = (team_key, slot)
                    break
        if slot_foco is None:
            return vazio
        team_key, slot = slot_foco
        return {
            "found": True,
            "path": latest,
            "template_id": str(report.get("template_id", "") or ""),
            "template_nome": str(((report.get("template_meta", {}) or {}).get("nome", "") or report.get("template_id", "") or "")),
            "modo": str(report.get("modo", "") or ""),
            "pacote_foco": pacote_foco,
            "pacote_nome": pacote_nome or str(slot.get("pacote_nome", "") or ""),
            "personagem_nome": str(slot.get("nome", "") or ""),
            "arma_nome": str(slot.get("arma", "") or ""),
            "team_key": team_key,
        }
    except Exception:
        return vazio


def load_latest_headless_inspection_target(report_dir=SAIDAS_HEADLESS_REPORTS_DIR, templates_path=FILE_TEMPLATES_TATICOS):
    vazio = {
        "found": False,
        "path": "",
        "modo": "",
        "template_id": "",
        "template_nome": "",
        "cenario": "",
        "team_a_members": [],
        "team_b_members": [],
        "team_labels": {},
        "horde_preset_id": "",
        "pacote_foco": "",
    }
    try:
        latest, data = _carregar_relatorio_recente(report_dir)
        if not latest or not isinstance(data, dict):
            return vazio
        templates_lookup = _carregar_templates_taticos(templates_path)
        comparativo = data.get("comparativo") if isinstance(data, dict) else None
        if comparativo:
            plano = _selecionar_plano_inspecao(comparativo)
            template_id = str((plano or {}).get("template_id", "") or "")
            for report in data.get("templates", []) or []:
                if str((report or {}).get("template_id", "") or "") == template_id:
                    return _construir_target_relatorio(report, path=latest, templates_lookup=templates_lookup)
        if data.get("template_id"):
            return _construir_target_relatorio(data, path=latest, templates_lookup=templates_lookup)
    except Exception:
        return vazio
    return vazio


def load_latest_headless_balance_focus(report_dir=SAIDAS_HEADLESS_REPORTS_DIR):
    vazio = {
        "found": False,
        "path": "",
        "template_id": "",
        "pacote_foco": "",
        "area": "",
        "area_text": "",
        "alvo": "",
        "alvo_text": "",
        "acao": "",
        "motivo": "",
        "prioridade": "",
    }
    try:
        latest, data = _carregar_relatorio_recente(report_dir)
        if not latest or not isinstance(data, dict):
            return vazio
        comparativo = data.get("comparativo") if isinstance(data, dict) else None
        if comparativo:
            foco = _resolver_foco_balanceamento_comparativo(comparativo)
            foco["path"] = latest
            return foco
    except Exception:
        return vazio
    return vazio


def load_latest_headless_report_summary(report_dir=SAIDAS_HEADLESS_REPORTS_DIR):
    vazio = {
        "found": False,
        "path": "",
        "headline": "Nenhum relatorio headless ainda",
        "subheadline": "Rode o posto headless ou o harness tatico para preencher este painel.",
        "status_text": "SEM RELATORIO",
        "status_tone": "idle",
        "alert_count": 0,
        "alert_text": "Sem alertas disponiveis.",
        "recommendation_text": "Sem recomendacoes ainda.",
        "areas_text": "Aguardando primeiro comparativo.",
        "package_text": "Nenhum pacote em evidencia ainda.",
        "review_axis_text": "Sem eixo prioritario ainda.",
        "review_plan_text": "Assim que existir um comparativo, este painel destaca o primeiro ponto para revisar.",
        "inspection_title": "Sem alvo de inspecao",
        "inspection_text": "Assim que existir um relatorio recente, este painel aponta o que vale assistir primeiro.",
    }
    try:
        latest, data = _carregar_relatorio_recente(report_dir)
        if not latest or not isinstance(data, dict):
            return vazio
    except Exception:
        return vazio

    comparativo = data.get("comparativo") if isinstance(data, dict) else None
    if comparativo:
        alertas = dict(comparativo.get("alertas_mais_comuns", {}) or {})
        resumo_ajuste = dict((comparativo.get("resumo_plano_ajuste") or {}).get("areas_mais_citadas", {}) or {})
        recomendacoes = comparativo.get("recomendacoes_balanceamento", []) or []
        pacotes_impacto = list(comparativo.get("pacotes_impacto", []) or [])
        melhor = (comparativo.get("melhor_template") or {}).get("template_id", "")
        pior = (comparativo.get("pior_template") or {}).get("template_id", "")
        alert_total = sum(int(v or 0) for v in alertas.values())
        status_tone = "healthy" if alert_total == 0 else ("warning" if alert_total <= 3 else "critical")
        top_alerts = ", ".join(formatar_token_relatorio(k) for k in list(alertas.keys())[:3]) or "Sem alertas principais."
        top_recs = " | ".join(formatar_token_relatorio(item.get("codigo", "")) for item in recomendacoes[:2]) or "Sem recomendacoes."
        top_areas = ", ".join(formatar_token_relatorio(k) for k in list(resumo_ajuste.keys())[:3]) or "Sem areas sinalizadas."
        top_pacotes = ", ".join(formatar_token_relatorio(item.get("pacote", "")) for item in pacotes_impacto[:3] if item.get("pacote")) or "Sem pacote dominante claro."
        payload = {
            "found": True,
            "path": latest,
            "headline": f"{int(comparativo.get('total_templates', 0) or 0)} templates comparados",
            "subheadline": f"Melhor: {formatar_token_relatorio(melhor) or '-'} | Pior: {formatar_token_relatorio(pior) or '-'}",
            "status_text": "ESTAVEL" if status_tone == "healthy" else ("ATENCAO" if status_tone == "warning" else "CRITICO"),
            "status_tone": status_tone,
            "alert_count": alert_total,
            "alert_text": top_alerts,
            "recommendation_text": top_recs,
            "areas_text": top_areas,
            "package_text": top_pacotes,
            "review_axis_text": "Sem eixo prioritario claro.",
            "review_plan_text": "Rode mais seeds ou templates para consolidar um plano de ajuste.",
        }
        payload.update(_resolver_alvo_inspecao_comparativo(comparativo))
        foco_balance = _resolver_foco_balanceamento_comparativo(comparativo)
        if foco_balance.get("found"):
            alvo = foco_balance.get("alvo_text", "") or foco_balance.get("area_text", "") or "Geral"
            pacote = formatar_token_relatorio(foco_balance.get("pacote_foco", "")) or ""
            payload["review_axis_text"] = f"{foco_balance.get('area_text', 'Geral')} -> {alvo}"
            review_plan = []
            if pacote:
                review_plan.append(f"Pacote: {pacote}")
            acao = str(foco_balance.get("acao", "") or "").strip()
            motivo = str(foco_balance.get("motivo", "") or "").strip()
            if acao:
                review_plan.append(acao)
            if motivo:
                review_plan.append(f"Motivo: {motivo}")
            payload["review_plan_text"] = " | ".join(review_plan) if review_plan else "Abra o template visual e revise esse eixo primeiro."
        return payload

    alertas = data.get("alertas", []) or []
    resumo_alertas = data.get("resumo_alertas", {}) or {}
    pacotes = dict(data.get("pacotes", {}) or {})
    alert_total = sum(int(v or 0) for v in resumo_alertas.values())
    status_tone = "healthy" if alert_total == 0 else ("warning" if alert_total <= 3 else "critical")
    top_alerts = ", ".join(formatar_token_relatorio(item.get("codigo", "")) for item in alertas[:3]) or "Sem alertas principais."
    pacote_text = "Nenhum pacote em evidencia."
    if pacotes:
        pacote_top = max(
            pacotes.items(),
            key=lambda item: float((item[1] or {}).get("damage_dealt", 0.0) or 0.0),
        )
        pacote_text = formatar_token_relatorio((pacote_top[1] or {}).get("nome") or pacote_top[0])
    return {
        "found": True,
        "path": latest,
        "headline": formatar_token_relatorio(data.get("template_id") or data.get("modo") or os.path.basename(latest)),
        "subheadline": f"Modo: {formatar_token_relatorio(data.get('modo', 'headless'))} | Alertas: {alert_total}",
        "status_text": "ESTAVEL" if status_tone == "healthy" else ("ATENCAO" if status_tone == "warning" else "CRITICO"),
        "status_tone": status_tone,
        "alert_count": alert_total,
        "alert_text": top_alerts,
        "recommendation_text": "Abra o JSON para ver o diagnostico detalhado deste template.",
        "areas_text": "Comparativo e plano de ajuste aparecem quando voce roda varios templates no mesmo modo.",
        "package_text": pacote_text,
        "review_axis_text": "Template unico: validar pacote inteiro.",
        "review_plan_text": "Comece por leitura de alvo, conversao de dano e identidade do pacote antes de mexer em numeros finos.",
        "inspection_title": "Inspecionar o template atual",
        "inspection_text": "Use a luta visual para validar o timing, a leitura de alvo e a conversao de dano do pacote que acabou de ser analisado.",
    }
