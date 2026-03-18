"""Helpers para expor estados internos da IA ao espectador via badges curtos."""

from __future__ import annotations


_BADGES_CENA = {
    "clash": {"texto": "CLASH", "bg": (255, 114, 74), "fg": (255, 248, 242), "borda": (255, 212, 168), "prioridade": 140},
    "final_showdown": {"texto": "FINAL", "bg": (255, 214, 92), "fg": (36, 24, 8), "borda": (255, 240, 168), "prioridade": 138},
    "sequencia_perfeita": {"texto": "SEQUENCIA", "bg": (255, 208, 74), "fg": (42, 28, 8), "borda": (255, 238, 164), "prioridade": 132},
    "virada": {"texto": "VIRADA", "bg": (82, 205, 255), "fg": (10, 26, 34), "borda": (182, 238, 255), "prioridade": 130},
    "leitura_perfeita": {"texto": "LEITURA", "bg": (96, 255, 214), "fg": (8, 30, 24), "borda": (192, 255, 236), "prioridade": 126},
    "dominando": {"texto": "DOMINIO", "bg": (255, 122, 122), "fg": (42, 10, 10), "borda": (255, 205, 205), "prioridade": 122},
    "humilhado": {"texto": "ABALO", "bg": (154, 132, 255), "fg": (18, 16, 38), "borda": (214, 207, 255), "prioridade": 118},
    "quase_morte": {"texto": "LIMITE", "bg": (255, 88, 102), "fg": (255, 246, 246), "borda": (255, 196, 204), "prioridade": 136},
}

_BADGES_FOLLOWUP = {
    "PRESSIONAR": {"texto": "PRESSAO", "bg": (255, 118, 92), "fg": (255, 248, 244), "borda": (255, 214, 198), "prioridade": 112},
    "MATAR": {"texto": "RUPTURA", "bg": (255, 86, 118), "fg": (255, 248, 250), "borda": (255, 194, 208), "prioridade": 114},
    "ESMAGAR": {"texto": "IMPACTO", "bg": (255, 154, 70), "fg": (40, 24, 8), "borda": (255, 220, 176), "prioridade": 113},
    "ATAQUE_RAPIDO": {"texto": "RITMO", "bg": (116, 214, 255), "fg": (8, 22, 32), "borda": (198, 238, 255), "prioridade": 108},
    "FLANQUEAR": {"texto": "FLANCO", "bg": (164, 116, 255), "fg": (18, 12, 34), "borda": (221, 203, 255), "prioridade": 109},
    "COMBATE": {"texto": "TROCA", "bg": (116, 238, 200), "fg": (10, 28, 24), "borda": (198, 255, 233), "prioridade": 104},
    "POKE": {"texto": "POKE", "bg": (126, 188, 255), "fg": (10, 22, 40), "borda": (205, 227, 255), "prioridade": 102},
    "APROXIMAR": {"texto": "CERCO", "bg": (255, 162, 86), "fg": (42, 22, 8), "borda": (255, 222, 184), "prioridade": 101},
}

_BADGE_BURST = {"texto": "BURST", "bg": (255, 92, 166), "fg": (255, 246, 252), "borda": (255, 198, 224), "prioridade": 110}
_BADGE_ORBES = {"texto": "ORBES", "bg": (128, 214, 255), "fg": (8, 24, 36), "borda": (202, 238, 255), "prioridade": 106}
_BADGES_RELACAO = {
    "respeito": {"texto": "RESPEITO", "bg": (106, 220, 255), "fg": (8, 22, 34), "borda": (200, 238, 255), "prioridade": 88},
    "vinganca": {"texto": "REVANCHE", "bg": (255, 98, 132), "fg": (255, 246, 250), "borda": (255, 200, 214), "prioridade": 94},
    "obsessao": {"texto": "RIVAL", "bg": (166, 118, 255), "fg": (246, 242, 255), "borda": (224, 206, 255), "prioridade": 90},
    "caca": {"texto": "CACADA", "bg": (255, 156, 82), "fg": (42, 22, 8), "borda": (255, 222, 182), "prioridade": 92},
}

_PERFIS_CINEMATICOS = {
    "clash": {
        "rotulo": "CLASH",
        "cor": (255, 126, 84),
        "cor_secundaria": (255, 222, 164),
        "prioridade": 140,
        "shake": 8.0,
        "zoom": 0.05,
        "slow_scale": 0.86,
        "slow_duracao": 0.10,
        "overlay": 0.58,
        "duracao_overlay": 0.38,
    },
    "final_showdown": {
        "rotulo": "FINAL SHOWDOWN",
        "cor": (255, 220, 104),
        "cor_secundaria": (255, 244, 182),
        "prioridade": 138,
        "shake": 7.5,
        "zoom": 0.06,
        "slow_scale": 0.72,
        "slow_duracao": 0.18,
        "overlay": 0.62,
        "duracao_overlay": 0.52,
    },
    "quase_morte": {
        "rotulo": "NO LIMITE",
        "cor": (255, 92, 112),
        "cor_secundaria": (255, 204, 214),
        "prioridade": 136,
        "shake": 4.0,
        "zoom": 0.03,
        "slow_scale": 0.90,
        "slow_duracao": 0.06,
        "overlay": 0.54,
        "duracao_overlay": 0.46,
    },
    "sequencia_perfeita": {
        "rotulo": "SEQUENCIA",
        "cor": (255, 206, 72),
        "cor_secundaria": (255, 238, 164),
        "prioridade": 132,
        "shake": 5.0,
        "zoom": 0.035,
        "slow_scale": 0.92,
        "slow_duracao": 0.07,
        "overlay": 0.50,
        "duracao_overlay": 0.34,
    },
    "virada": {
        "rotulo": "VIRADA",
        "cor": (94, 210, 255),
        "cor_secundaria": (188, 238, 255),
        "prioridade": 130,
        "shake": 5.6,
        "zoom": 0.04,
        "slow_scale": 0.88,
        "slow_duracao": 0.09,
        "overlay": 0.50,
        "duracao_overlay": 0.40,
    },
    "leitura_perfeita": {
        "rotulo": "LEITURA",
        "cor": (94, 255, 220),
        "cor_secundaria": (194, 255, 238),
        "prioridade": 126,
        "shake": 3.4,
        "zoom": 0.025,
        "slow_scale": 0.93,
        "slow_duracao": 0.05,
        "overlay": 0.42,
        "duracao_overlay": 0.28,
    },
    "dominando": {
        "rotulo": "DOMINIO",
        "cor": (255, 132, 132),
        "cor_secundaria": (255, 210, 210),
        "prioridade": 122,
        "shake": 3.2,
        "zoom": 0.02,
        "slow_scale": 0.94,
        "slow_duracao": 0.04,
        "overlay": 0.38,
        "duracao_overlay": 0.26,
    },
    "humilhado": {
        "rotulo": "ABALO",
        "cor": (164, 136, 255),
        "cor_secundaria": (220, 210, 255),
        "prioridade": 118,
        "shake": 3.8,
        "zoom": 0.024,
        "slow_scale": 0.92,
        "slow_duracao": 0.05,
        "overlay": 0.40,
        "duracao_overlay": 0.30,
    },
    "rivalidade_respeito": {
        "rotulo": "RESPEITO",
        "cor": (106, 220, 255),
        "cor_secundaria": (200, 238, 255),
        "prioridade": 84,
        "shake": 2.2,
        "zoom": 0.015,
        "slow_scale": 0.96,
        "slow_duracao": 0.03,
        "overlay": 0.28,
        "duracao_overlay": 0.22,
    },
    "rivalidade_vinganca": {
        "rotulo": "REVANCHE",
        "cor": (255, 98, 132),
        "cor_secundaria": (255, 202, 214),
        "prioridade": 90,
        "shake": 3.4,
        "zoom": 0.022,
        "slow_scale": 0.95,
        "slow_duracao": 0.04,
        "overlay": 0.34,
        "duracao_overlay": 0.24,
    },
    "rivalidade_obsessao": {
        "rotulo": "RIVAL",
        "cor": (166, 118, 255),
        "cor_secundaria": (224, 206, 255),
        "prioridade": 88,
        "shake": 2.8,
        "zoom": 0.018,
        "slow_scale": 0.96,
        "slow_duracao": 0.03,
        "overlay": 0.30,
        "duracao_overlay": 0.22,
    },
    "rivalidade_caca": {
        "rotulo": "CACADA",
        "cor": (255, 156, 82),
        "cor_secundaria": (255, 222, 182),
        "prioridade": 89,
        "shake": 3.0,
        "zoom": 0.02,
        "slow_scale": 0.95,
        "slow_duracao": 0.03,
        "overlay": 0.32,
        "duracao_overlay": 0.22,
    },
}


def _clamp_unit(value, default=0.0):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _contar_orbes_orbitando(lutador) -> int:
    ativos = 0
    for orbe in getattr(lutador, "buffer_orbes", []) or []:
        if getattr(orbe, "ativo", False) and getattr(orbe, "estado", "") == "orbitando":
            ativos += 1
    return ativos


def _badge_personalizado(texto, bg, fg, borda, prioridade):
    return {
        "texto": str(texto).upper(),
        "bg": tuple(bg),
        "fg": tuple(fg),
        "borda": tuple(borda),
        "prioridade": float(prioridade),
    }


def _resolver_badge_postura(lutador, brain):
    hp_pct = 0.0
    try:
        hp_pct = max(0.0, min(1.0, float(getattr(lutador, "vida", 0.0)) / max(float(getattr(lutador, "vida_max", 1.0)), 1.0)))
    except (TypeError, ValueError, ZeroDivisionError):
        hp_pct = 0.0

    acao = str(getattr(brain, "acao_atual", "") or "").upper()
    momentum = _clamp_unit((getattr(brain, "momentum", 0.0) + 1.0) * 0.5, default=0.5)
    confianca = _clamp_unit(getattr(brain, "confianca", 0.5), default=0.5)
    medo = _clamp_unit(getattr(brain, "medo", 0.0))
    excitacao = _clamp_unit(getattr(brain, "excitacao", 0.0))

    if hp_pct <= 0.22:
        return _badge_personalizado("LIMITE", (255, 96, 110), (255, 248, 248), (255, 204, 210), 96)
    if acao in {"RECUAR", "FUGIR"}:
        return _badge_personalizado("RESPIRO", (98, 118, 150), (240, 244, 248), (178, 192, 214), 93)
    if acao in {"FLANQUEAR", "CIRCULAR"}:
        return _badge_personalizado("FLANCO", (148, 116, 255), (246, 242, 255), (216, 202, 255), 95)
    if acao in {"BLOQUEAR", "CONTRA_ATAQUE"}:
        return _badge_personalizado("LEITURA", (94, 238, 214), (8, 26, 24), (188, 255, 238), 98)
    if acao == "POKE":
        return _badge_personalizado("POKE", (120, 190, 255), (8, 24, 40), (206, 230, 255), 92)
    if acao in {"MATAR", "ESMAGAR", "PRESSIONAR", "APROXIMAR"}:
        return _badge_personalizado("PRESSAO" if momentum > 0.62 else "CERCO", (255, 132, 92), (255, 248, 244), (255, 214, 196), 97)
    if excitacao > 0.72 and momentum > 0.58:
        return _badge_personalizado("RITMO", (255, 182, 74), (42, 24, 8), (255, 226, 170), 91)
    if confianca > 0.66 and medo < 0.30:
        return _badge_personalizado("FOCO", (104, 218, 255), (8, 22, 34), (196, 236, 255), 90)
    if medo > 0.58 and confianca < 0.42:
        return _badge_personalizado("RESPIRO", (102, 122, 150), (244, 248, 252), (182, 196, 214), 89)
    return None


def _resolver_badge_relacao(brain):
    memoria = getattr(brain, "memoria_oponente", None)
    if not isinstance(memoria, dict):
        return None
    chave = memoria.get("id_atual")
    buckets = memoria.get("adaptacao_por_oponente", {})
    if not chave or not isinstance(buckets, dict):
        return None
    bucket = buckets.get(chave)
    if not isinstance(bucket, dict):
        return None
    dominante = bucket.get("relacao_dominante")
    if dominante in _BADGES_RELACAO:
        intensidade = max(
            0.0,
            min(
                1.0,
                float(bucket.get(f"relacao_{dominante}", 0.0) or 0.0),
            ),
        )
        if intensidade >= 0.24:
            badge = dict(_BADGES_RELACAO[dominante])
            badge["prioridade"] += intensidade * 12.0
            return badge
    return None


def resolver_badges_estado(lutador, *, max_badges=2):
    """Retorna badges curtos e legiveis para o espectador."""
    brain = getattr(lutador, "brain", None) or getattr(lutador, "ai", None)
    if brain is None:
        return []

    badges = []
    memoria = getattr(brain, "memoria_cena", None)
    if isinstance(memoria, dict):
        tipo = str(memoria.get("tipo") or "").strip().lower()
        intensidade = _clamp_unit(memoria.get("intensidade", 0.0))
        duracao = max(0.0, float(memoria.get("duracao", 0.0) or 0.0))
        if tipo in _BADGES_CENA and intensidade >= 0.12 and duracao > 0.0:
            badge_cena = dict(_BADGES_CENA[tipo])
            badge_cena["prioridade"] += intensidade * 10.0
            badges.append(badge_cena)

    combo = getattr(brain, "combo_state", None)
    if isinstance(combo, dict):
        followup = str(combo.get("followup_forcado") or "").upper()
        timer = max(0.0, float(combo.get("timer", 0.0) or 0.0))
        if followup in _BADGES_FOLLOWUP and timer > 0.05:
            badges.append(dict(_BADGES_FOLLOWUP[followup]))

    if getattr(lutador, "orbital_burst_cd", 999.0) <= 0.0:
        badges.append(dict(_BADGE_BURST))

    if _contar_orbes_orbitando(lutador) >= 2:
        badges.append(dict(_BADGE_ORBES))

    badge_relacao = _resolver_badge_relacao(brain)
    if badge_relacao:
        badges.append(badge_relacao)

    badge_postura = _resolver_badge_postura(lutador, brain)
    if badge_postura:
        badges.append(badge_postura)

    vistos = set()
    unicos = []
    for badge in sorted(badges, key=lambda item: item.get("prioridade", 0.0), reverse=True):
        texto = badge.get("texto")
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        unicos.append(badge)
        if len(unicos) >= max_badges:
            break
    return unicos


def resolver_destaque_cinematico(lutadores):
    """Resolve o estado dramático dominante entre os lutadores ativos."""
    melhor = None
    for lutador in lutadores or []:
        brain = getattr(lutador, "brain", None) or getattr(lutador, "ai", None)
        memoria = getattr(brain, "memoria_cena", None)
        if isinstance(memoria, dict):
            tipo = str(memoria.get("tipo") or "").strip().lower()
            intensidade = _clamp_unit(memoria.get("intensidade", 0.0))
            duracao = max(0.0, float(memoria.get("duracao", 0.0) or 0.0))
            if tipo in _PERFIS_CINEMATICOS and intensidade > 0.10 and duracao > 0.0:
                perfil = dict(_PERFIS_CINEMATICOS[tipo])
                perfil["tipo"] = tipo
                perfil["intensidade"] = intensidade
                perfil["duracao_restante"] = duracao
                perfil["lutador"] = lutador
                perfil["score"] = perfil["prioridade"] + intensidade * 18.0 + min(1.0, duracao) * 4.0
                if melhor is None or perfil["score"] > melhor["score"]:
                    melhor = perfil

        memoria_oponente = getattr(brain, "memoria_oponente", None)
        if not isinstance(memoria_oponente, dict):
            continue
        chave = memoria_oponente.get("id_atual")
        buckets = memoria_oponente.get("adaptacao_por_oponente", {})
        if not chave or not isinstance(buckets, dict):
            continue
        bucket = buckets.get(chave)
        if not isinstance(bucket, dict):
            continue
        dominante = bucket.get("relacao_dominante")
        if dominante not in {"respeito", "vinganca", "obsessao", "caca"}:
            continue
        intensidade_rel = max(0.0, min(1.0, float(bucket.get(f"relacao_{dominante}", 0.0) or 0.0)))
        if intensidade_rel < 0.34:
            continue
        perfil = dict(_PERFIS_CINEMATICOS[f"rivalidade_{dominante}"])
        perfil["tipo"] = f"rivalidade_{dominante}"
        perfil["intensidade"] = intensidade_rel
        perfil["duracao_restante"] = intensidade_rel
        perfil["lutador"] = lutador
        perfil["score"] = perfil["prioridade"] + intensidade_rel * 10.0
        if melhor is None or perfil["score"] > melhor["score"]:
            melhor = perfil
    return melhor
