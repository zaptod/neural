"""Sintese de arquétipos compostos a partir de classe, personalidade, arma e skills."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import unicodedata

from ia.behavior_profiles import FALLBACK_PROFILE, get_behavior_profile
from ia.personalities import LISTA_PERSONALIDADES, PERSONALIDADES_PRESETS
from modelos import LISTA_CLASSES, Arma, get_class_data
from nucleo.armas import inferir_familia, resolver_subtipo_orbital
from nucleo.skills import get_skill_classification, get_skill_data

ROOT = Path(__file__).resolve().parents[1]
FILE_PAPEIS = ROOT / "dados" / "papeis_taticos.json"
FILE_PACOTES = ROOT / "dados" / "pacotes_arquetipos.json"


def _norm(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return base.strip().lower()


def _skill_names(skills) -> list[str]:
    nomes = []
    for skill in skills or []:
        if isinstance(skill, dict):
            nome = str(skill.get("nome", "") or "").strip()
        else:
            nome = str(skill or "").strip()
        if nome and nome != "Nenhuma":
            nomes.append(nome)
    vistos = set()
    unicos = []
    for nome in nomes:
        if nome in vistos:
            continue
        vistos.add(nome)
        unicos.append(nome)
    return unicos


def _load_papeis() -> list[dict]:
    if not FILE_PAPEIS.exists():
        return []
    return list(json.loads(FILE_PAPEIS.read_text(encoding="utf-8")).get("papeis", []))


def _load_pacotes() -> list[dict]:
    if not FILE_PACOTES.exists():
        return []
    return list(json.loads(FILE_PACOTES.read_text(encoding="utf-8")).get("pacotes", []))


def _resolve_family(arma: Arma | None) -> str:
    if arma is None:
        return "lamina"
    return getattr(arma, "familia", "") or inferir_familia(getattr(arma, "tipo", "Reta"), getattr(arma, "estilo", ""))


def _family_signature(familia: str, subtipo_orbital: str) -> dict[str, object]:
    base = {
        "lamina": {"distancia": "curta", "abertura": "aproximar e buscar troca limpa", "postura": "duelo frontal", "eixos": {"burst": 1.1, "pressao": 0.9}},
        "haste": {"distancia": "curta-media", "abertura": "manter ponta de alcance e castigar avanço", "postura": "controle de zona curta", "eixos": {"controle": 0.9, "pressao": 0.6}},
        "dupla": {"distancia": "curta", "abertura": "entrar em explosão curta e sair de lado", "postura": "flanco agressivo", "eixos": {"burst": 1.2, "mobilidade": 0.8}},
        "corrente": {"distancia": "media", "abertura": "pressionar com volume angular e negar corredor", "postura": "zona de ameaça", "eixos": {"controle": 1.0, "pressao": 0.9}},
        "arremesso": {"distancia": "media", "abertura": "poke móvel e rajadas rápidas", "postura": "harass e kite", "eixos": {"pressao": 0.8, "mobilidade": 0.7}},
        "disparo": {"distancia": "longa", "abertura": "carregar, medir espaço e punir lento", "postura": "artilharia", "eixos": {"precisao": 1.0, "pressao": 0.7}},
        "foco": {"distancia": "media-longa", "abertura": "gastar recursos com leitura e setup", "postura": "caster tático", "eixos": {"controle": 0.9, "sustain": 0.6}},
        "hibrida": {"distancia": "variavel", "abertura": "trocar envelope conforme pressão", "postura": "adaptação armada", "eixos": {"mobilidade": 0.7, "burst": 0.8, "controle": 0.5}},
        "orbital": {"distancia": "media", "abertura": "orbitar, preparar janela e modular contato", "postura": "controle perimetral", "eixos": {"controle": 0.9, "pressao": 0.7}},
    }.get(familia, {"distancia": "media", "abertura": "buscar leitura segura", "postura": "equilibrada", "eixos": {}})

    if familia != "orbital":
        return base

    orbital_map = {
        "escudo": {
            "distancia": "curta-media",
            "abertura": "segurar linha, bloquear entrada e responder no contra-tempo",
            "postura": "bastião móvel",
            "eixos": {"resiliencia": 1.2, "controle": 0.9, "burst": -0.2},
        },
        "drone": {
            "distancia": "media-longa",
            "abertura": "varrer ângulos e disparar burst modular",
            "postura": "artilharia orbital",
            "eixos": {"pressao": 1.1, "precisao": 0.8},
        },
        "laminas": {
            "distancia": "curta-media",
            "abertura": "circular, rasgar espaço e converter em rajada",
            "postura": "dança de lâminas",
            "eixos": {"burst": 1.0, "mobilidade": 0.8, "pressao": 0.7},
        },
        "orbes": {
            "distancia": "media",
            "abertura": "marcar ritmo com zonas, sigilos e invocação leve",
            "postura": "regência astral",
            "eixos": {"controle": 1.1, "sustain": 0.5, "pressao": 0.5},
        },
    }
    extra = orbital_map.get(subtipo_orbital or "orbes", orbital_map["orbes"])
    merged = dict(base)
    merged.update(extra)
    return merged


def _traits_for_personality(personalidade: str) -> set[str]:
    preset = PERSONALIDADES_PRESETS.get(personalidade, {})
    return {_norm(v) for v in preset.get("tracos_fixos", [])}


def _score_papeis(classe: str, personalidade: str, arma: Arma | None, skills: list[str]) -> list[dict]:
    family = _resolve_family(arma)
    subtipo_orbital = resolver_subtipo_orbital(arma) if arma else ""
    classe_norm = _norm(classe)
    traits = _traits_for_personality(personalidade)
    skill_classes = []
    skill_forcas = []
    for nome in skills:
        try:
            c = get_skill_classification(nome)
        except Exception:
            continue
        skill_classes.append(_norm(c.classe_utilidade.value))
        skill_forcas.append(_norm(c.classe_forca.value))

    resultados = []
    for papel in _load_papeis():
        score = 0.0
        if family in {_norm(v) for v in papel.get("familias_arma_preferidas", [])}:
            score += 3.0
        for token in papel.get("arquetipos_prioritarios", []):
            nt = _norm(token)
            if nt and nt in classe_norm:
                score += 2.0
        for token in papel.get("tracos_prioritarios", []):
            if _norm(token) in traits:
                score += 1.15
        for token in papel.get("classes_magia_preferidas", []):
            if _norm(token) in skill_classes:
                score += 0.9
        for token in papel.get("forcas_magia_preferidas", []):
            if _norm(token) in skill_forcas:
                score += 0.7

        papel_id = papel.get("id", "")
        if papel_id == "bastiao_orbital" and family == "orbital" and subtipo_orbital == "escudo":
            score += 2.6
        if papel_id == "artilheiro_orbital" and family == "orbital" and subtipo_orbital in {"drone", "laminas"}:
            score += 2.4 if subtipo_orbital == "drone" else 1.6
        if papel_id == "maestro_astral" and family == "orbital" and subtipo_orbital == "orbes":
            score += 2.4

        resultados.append({
            "papel_id": papel_id,
            "nome": papel.get("nome", papel_id),
            "score": round(score, 3),
            "forte_em": list(papel.get("forte_em", [])),
            "fraco_em": list(papel.get("fraco_em", [])),
        })

    resultados.sort(key=lambda item: item["score"], reverse=True)
    return resultados


def _gerar_nome_composto(classe: str, personalidade: str, family: str, skill_names: list[str]) -> str:
    base = classe.split(" (")[0].strip()
    apelido = personalidade.split(" ")[0].strip() if personalidade else "Nucleo"
    elementos = []
    for nome in skill_names:
        try:
            elem = get_skill_classification(nome).elemento
        except Exception:
            elem = ""
        elem_norm = _norm(elem)
        if elem_norm and elem_norm not in {"", "neutro"} and elem_norm not in elementos:
            elementos.append(elem_norm)
    if len(elementos) >= 2:
        sufixo = f"{elementos[0].title()}-{elementos[1].title()}"
    elif elementos:
        sufixo = elementos[0].title()
    else:
        sufixo = family.title()
    return f"{base} {apelido} {sufixo}".strip()


def _match_pacote_referencia(
    classe: str,
    personalidade: str,
    family: str,
    subtipo_orbital: str,
    funcoes: list[str],
    forcas: list[str],
    elementos: list[str],
    postura: str,
    distancia: str,
    papel_primario: dict,
) -> tuple[dict | None, list[str]]:
    classe_norm = _norm(classe)
    traits = _traits_for_personality(personalidade)
    funcoes_norm = {_norm(v) for v in funcoes}
    forcas_norm = {_norm(v) for v in forcas}
    elementos_norm = {_norm(v) for v in elementos}
    postura_norm = _norm(postura)
    distancia_norm = _norm(distancia)
    papel_id = _norm(papel_primario.get("papel_id", ""))

    melhor = None
    melhor_score = -1.0
    for pacote in _load_pacotes():
        score = 0.0
        if family in {_norm(v) for v in pacote.get("familias_arma", [])}:
            score += 3.0
        if subtipo_orbital and subtipo_orbital in {_norm(v) for v in pacote.get("subtipos_orbitais", [])}:
            score += 1.6
        if papel_id in {_norm(v) for v in pacote.get("papeis_prioritarios", [])}:
            score += 2.6
        for token in pacote.get("classes_base", []):
            if _norm(token) and _norm(token) in classe_norm:
                score += 1.3
        for token in pacote.get("tracos_prioritarios", []):
            if _norm(token) in traits:
                score += 0.9
        score += len(funcoes_norm & {_norm(v) for v in pacote.get("funcoes_magia", [])}) * 0.75
        score += len(forcas_norm & {_norm(v) for v in pacote.get("forcas_magia", [])}) * 0.55
        score += len(elementos_norm & {_norm(v) for v in pacote.get("elementos", [])}) * 0.45
        if pacote.get("postura_esperada") and _norm(pacote.get("postura_esperada")) == postura_norm:
            score += 0.7
        if pacote.get("distancia_esperada") and _norm(pacote.get("distancia_esperada")) == distancia_norm:
            score += 0.7

        if score > melhor_score:
            melhor = pacote
            melhor_score = score

    if not melhor or melhor_score < 3.0:
        return None, []

    desvios = []
    familias_ok = {_norm(v) for v in melhor.get("familias_arma", [])}
    if family not in familias_ok:
        desvios.append("Familia da arma fora do pacote de referencia.")
    if melhor.get("subtipos_orbitais") and subtipo_orbital and subtipo_orbital not in {_norm(v) for v in melhor.get("subtipos_orbitais", [])}:
        desvios.append("Subtipo orbital nao bate com o pacote esperado.")
    missing_funcoes = [
        valor for valor in melhor.get("funcoes_magia", [])
        if _norm(valor) not in funcoes_norm
    ]
    if missing_funcoes[:2]:
        desvios.append(f"Funcoes-chave ausentes: {', '.join(missing_funcoes[:2])}.")
    missing_forcas = [
        valor for valor in melhor.get("forcas_magia", [])
        if _norm(valor) not in forcas_norm
    ]
    if missing_forcas[:2]:
        desvios.append(f"Forcas-chave ausentes: {', '.join(missing_forcas[:2])}.")
    if melhor.get("postura_esperada") and _norm(melhor.get("postura_esperada")) != postura_norm:
        desvios.append("Postura inferida diverge da postura esperada do pacote.")
    if melhor.get("distancia_esperada") and _norm(melhor.get("distancia_esperada")) != distancia_norm:
        desvios.append("Faixa de distancia diverge da referencia do pacote.")
    if papel_id and papel_id not in {_norm(v) for v in melhor.get("papeis_prioritarios", [])}:
        desvios.append("Papel primario inferido nao e o centro do pacote oficial.")

    pacote_resumido = dict(melhor)
    pacote_resumido["score_match"] = round(melhor_score, 3)
    return pacote_resumido, desvios


def inferir_arquetipo_composto(classe: str, personalidade: str, arma: Arma | None, skills=None) -> dict:
    skill_names = _skill_names(skills)
    family = _resolve_family(arma)
    subtipo_orbital = resolver_subtipo_orbital(arma) if arma else ""
    behavior = get_behavior_profile(personalidade) if personalidade in LISTA_PERSONALIDADES else FALLBACK_PROFILE
    class_data = get_class_data(classe)
    role_scores = _score_papeis(classe, personalidade, arma, skill_names)
    papel_primario = role_scores[0] if role_scores else {"papel_id": "bruiser", "nome": "Bruiser", "score": 0.0, "forte_em": [], "fraco_em": []}
    papel_secundario = role_scores[1] if len(role_scores) > 1 and role_scores[1]["score"] >= papel_primario["score"] * 0.62 else None

    eixos = defaultdict(float)
    eixos["burst"] += float(class_data.get("mod_forca", 1.0) or 1.0) * 0.45
    eixos["mobilidade"] += float(class_data.get("mod_velocidade", 1.0) or 1.0) * 0.50
    eixos["sustain"] += float(class_data.get("mod_vida", 1.0) or 1.0) * 0.45
    eixos["pressao"] += float(behavior.get("pressao_mult", 1.0) or 1.0) * 0.65
    eixos["controle"] += float(behavior.get("paciencia_mult", 1.0) or 1.0) * 0.22
    eixos["risco"] += float(behavior.get("risco_tolerancia", 0.4) or 0.4) * 1.2
    eixos["cadencia"] += float(behavior.get("combo_tendencia", 1.0) or 1.0) * 0.55

    assinatura_familia = _family_signature(family, subtipo_orbital)
    for eixo, valor in (assinatura_familia.get("eixos", {}) or {}).items():
        eixos[eixo] += float(valor)

    elementos = []
    funcoes = []
    forcas = []
    for nome in skill_names:
        try:
            classificacao = get_skill_classification(nome)
            dados = get_skill_data(nome)
        except Exception:
            continue
        elem = classificacao.elemento
        if elem not in {"", "NEUTRO"} and elem not in elementos:
            elementos.append(elem)
        if classificacao.classe_utilidade.value not in funcoes:
            funcoes.append(classificacao.classe_utilidade.value)
        if classificacao.classe_forca.value not in forcas:
            forcas.append(classificacao.classe_forca.value)

        util = _norm(classificacao.classe_utilidade.value)
        forca = _norm(classificacao.classe_forca.value)
        if util in {"controle", "zona", "disrupcao"}:
            eixos["controle"] += 0.9
        if util in {"cura", "protecao", "amplificacao"}:
            eixos["sustain"] += 0.85
            eixos["resiliencia"] += 0.55
        if util in {"mobilidade", "precisao"}:
            eixos["mobilidade"] += 0.7
        if util in {"invocacao"}:
            eixos["pressao"] += 0.4
            eixos["controle"] += 0.5
        if forca in {"impacto", "cataclismo"}:
            eixos["burst"] += 0.9
        if forca in {"pressao"}:
            eixos["pressao"] += 0.8
        if forca in {"precisao"}:
            eixos["cadencia"] += 0.5

        if dados.get("tipo") in {"AREA", "BEAM"}:
            eixos["controle"] += 0.35

    distancia = assinatura_familia["distancia"]
    abertura = assinatura_familia["abertura"]
    postura = assinatura_familia["postura"]
    approach = float(behavior.get("approach_weight", 1.0) or 1.0)
    retreat = float(behavior.get("retreat_weight", 1.0) or 1.0)
    flank = float(behavior.get("flank_weight", 1.0) or 1.0)
    poke = float(behavior.get("poke_weight", 1.0) or 1.0)

    padrao_decisao = [
        f"Abertura preferida: {abertura}.",
        f"Faixa ideal: {distancia}; postura dominante: {postura}.",
        f"Tom de decisão: aproximação {approach:.2f}, recuo {retreat:.2f}, flanco {flank:.2f}, poke {poke:.2f}.",
    ]

    if eixos["controle"] >= max(eixos["burst"], eixos["pressao"]):
        padrao_decisao.append("Tende a preparar a luta antes de explodir: lê espaço, segura recurso e abre janelas por controle.")
    elif eixos["burst"] > eixos["controle"] and eixos["burst"] >= eixos["pressao"]:
        padrao_decisao.append("Procura converter vantagem em sequência curta e pesada, com prioridade em punição forte.")
    else:
        padrao_decisao.append("Joga em pressão contínua, tentando manter iniciativa e forçar erro por volume de ação.")

    if eixos["sustain"] >= 2.3:
        padrao_decisao.append("Tem sustentação acima da média e aceita trocas mais longas se o mapa permitir.")
    if eixos["mobilidade"] >= 1.9:
        padrao_decisao.append("Consegue reposicionar com frequência e tende a sobreviver melhor a erro de spacing.")

    alertas = []
    if eixos["burst"] >= 2.4 and eixos["controle"] >= 2.1 and eixos["sustain"] >= 2.0:
        alertas.append("Pacote muito completo: burst, controle e sustain altos ao mesmo tempo podem empurrar o kit para dominância.")
    if distancia in {"curta", "curta-media"} and eixos["mobilidade"] < 1.2 and eixos["sustain"] < 1.5:
        alertas.append("Kit de curta distância com pouca mobilidade e sustain: tende a sofrer para kite e poke prolongado.")
    if family == "orbital" and subtipo_orbital == "escudo" and eixos["burst"] > 2.1:
        alertas.append("Escudo orbital com burst muito alto pode apagar a leitura defensiva do subtipo.")
    if family == "orbital" and subtipo_orbital == "drone" and eixos["controle"] > 2.5:
        alertas.append("Drone orbital pode estar acumulando controle demais para um papel que deveria ser mais de pressão/artilharia.")

    role_name = papel_primario["nome"]
    if papel_secundario:
        role_name = f"{papel_primario['nome']} / {papel_secundario['nome']}"

    pacote_referencia, desvios_pacote = _match_pacote_referencia(
        classe,
        personalidade,
        family,
        subtipo_orbital,
        funcoes,
        forcas,
        elementos,
        postura,
        distancia,
        papel_primario,
    )

    resumo = (
        f"{_gerar_nome_composto(classe, personalidade, family, skill_names)} opera como {role_name.lower()}, "
        f"com foco em {postura} e decisões guiadas por {papel_primario['papel_id']}."
    )

    return {
        "nome_composto": _gerar_nome_composto(classe, personalidade, family, skill_names),
        "classe": classe,
        "personalidade": personalidade,
        "arma": getattr(arma, "nome", "Nenhuma"),
        "familia_arma": family,
        "subtipo_orbital": subtipo_orbital,
        "skills": skill_names,
        "elementos": elementos,
        "funcoes_magia": funcoes,
        "forcas_magia": forcas,
        "papel_primario": papel_primario,
        "papel_secundario": papel_secundario,
        "distancia_preferida": distancia,
        "abertura_preferida": abertura,
        "postura": postura,
        "eixos": {k: round(v, 3) for k, v in sorted(eixos.items())},
        "padrao_decisao": padrao_decisao,
        "forte_em": list(papel_primario.get("forte_em", [])),
        "fraco_em": list(papel_primario.get("fraco_em", [])),
        "alertas_balanceamento": alertas,
        "pacote_referencia": pacote_referencia,
        "desvios_pacote": desvios_pacote,
        "resumo": resumo,
        "score_papeis": role_scores[:5],
    }


def construir_arvore_arquetipo(perfil: dict) -> list[dict]:
    """Estrutura simples para Treeview/UI."""
    return [
        {
            "titulo": "Nucleo",
            "filhos": [
                f"Classe: {perfil['classe']}",
                f"Personalidade: {perfil['personalidade']}",
                f"Arma: {perfil['arma']} [{perfil['familia_arma']}]",
                f"Subtipo orbital: {perfil['subtipo_orbital'] or 'n/a'}",
            ],
        },
        {
            "titulo": "Skills",
            "filhos": perfil["skills"] or ["Sem skills equipadas"],
        },
        {
            "titulo": "Leitura Tatica",
            "filhos": [
                f"Papel primario: {perfil['papel_primario']['nome']}",
                f"Papel secundario: {perfil['papel_secundario']['nome']}" if perfil["papel_secundario"] else "Papel secundario: n/a",
                f"Distancia: {perfil['distancia_preferida']}",
                f"Postura: {perfil['postura']}",
            ],
        },
        {
            "titulo": "Padrao De Decisao",
            "filhos": list(perfil["padrao_decisao"]),
        },
        {
            "titulo": "Pacote Oficial",
            "filhos": [
                f"Pacote: {perfil['pacote_referencia']['nome']}" if perfil.get("pacote_referencia") else "Pacote: sem referencia oficial forte",
                f"Resumo: {perfil['pacote_referencia']['resumo']}" if perfil.get("pacote_referencia") else "Resumo: n/a",
                f"Desvios: {' | '.join(perfil['desvios_pacote'])}" if perfil.get("desvios_pacote") else "Desvios: nenhum desvio estrutural forte",
            ],
        },
        {
            "titulo": "Alertas",
            "filhos": perfil["alertas_balanceamento"] or ["Sem alertas imediatos"],
        },
    ]


__all__ = [
    "LISTA_CLASSES",
    "LISTA_PERSONALIDADES",
    "construir_arvore_arquetipo",
    "inferir_arquetipo_composto",
]
