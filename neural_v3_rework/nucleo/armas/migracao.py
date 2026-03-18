"""Migracao e normalizacao do schema de armas v2."""

from __future__ import annotations

import re
import unicodedata
from copy import deepcopy

from .catalogo import FAMILIAS_ARMA_V2, get_family_spec, legacy_type_from_family


def corrigir_texto_legado(valor):
    if not isinstance(valor, str):
        return valor
    texto = valor.strip()
    if any(marker in texto for marker in ("Ã", "â", "ð", "�")):
        try:
            texto = texto.encode("latin1").decode("utf-8")
        except Exception:
            pass
    return texto


def slugify_nome(nome: str) -> str:
    base = unicodedata.normalize("NFKD", corrigir_texto_legado(nome)).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "arma-sem-id"


def normalizar_percentual(valor, default=0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return default
    if numero > 1.0:
        numero /= 100.0
    return max(0.0, min(numero, 0.95))


def normalizar_float(valor, default=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def limitar_variacao(valor, referencia, minimo=0.9, maximo=1.1, default=None) -> float:
    base = normalizar_float(referencia, default if default is not None else 0.0)
    if base <= 0:
        return normalizar_float(valor, base)
    atual = normalizar_float(valor, base)
    fator = max(minimo, min(maximo, atual / base))
    return base * fator


def inferir_familia(tipo_legacy: str, estilo: str = "", categoria: str | None = None) -> str:
    tipo = corrigir_texto_legado(tipo_legacy or "")
    tipo_norm = normalizar_token(tipo)
    estilo_norm = normalizar_token(estilo)

    if categoria == "foco_magico":
        return "foco"

    if "transform" in tipo_norm:
        return "hibrida"
    if "magic" in tipo_norm or "magica" in tipo_norm:
        return "foco"
    if "orbital" in tipo_norm:
        return "orbital"
    if "arco" in tipo_norm:
        return "disparo"
    if "arremesso" in tipo_norm:
        return "arremesso"
    if "corrente" in tipo_norm:
        return "corrente"
    if "dupla" in tipo_norm:
        return "dupla"

    if any(token in estilo_norm for token in ("lanca", "alabarda", "cajado", "estocada")):
        return "haste"
    return "lamina"


def normalizar_token(valor: str) -> str:
    texto = corrigir_texto_legado(valor or "")
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto.lower()


def construir_schema_arma(payload: dict) -> dict:
    bruto = deepcopy(payload)
    schema_version = int(bruto.get("schema_version", 1))

    nome = corrigir_texto_legado(bruto.get("nome", "Arma Sem Nome"))
    estilo = corrigir_texto_legado(bruto.get("estilo", ""))
    tipo_legacy = corrigir_texto_legado(bruto.get("tipo") or bruto.get("tipo_legacy") or "Reta")
    categoria = bruto.get("categoria")
    familia = bruto.get("familia") or inferir_familia(tipo_legacy, estilo, categoria)
    spec = get_family_spec(familia)

    combate_raw = bruto.get("combate") or {}
    visual_raw = bruto.get("visual") or {}
    magia_raw = bruto.get("magia") or {}

    quantidade = int(bruto.get("quantidade", combate_raw.get("projeteis_por_ataque", spec["mecanica"]["projeteis_por_ataque"])))
    qtd_orbitais = int(bruto.get("quantidade_orbitais", combate_raw.get("qtd_orbitais", spec["mecanica"]["qtd_orbitais"])))
    forca_arco = normalizar_float(bruto.get("forca_arco", combate_raw.get("forca_disparo", spec["mecanica"]["forca_disparo"])), spec["mecanica"]["forca_disparo"])

    combate = deepcopy(spec["mecanica"])
    combate.update(combate_raw)
    base_mecanica = spec["mecanica"]
    combate["dano_base"] = limitar_variacao(
        bruto.get("dano", combate.get("dano_base", base_mecanica["dano_base"])),
        base_mecanica["dano_base"],
        0.85, 1.08, base_mecanica["dano_base"],
    )
    combate["peso"] = limitar_variacao(
        bruto.get("peso", combate.get("peso", base_mecanica["peso"])),
        base_mecanica["peso"],
        0.85, 1.15, base_mecanica["peso"],
    )
    if "alcance" in combate_raw:
        combate["alcance"] = max(0.1, normalizar_float(combate_raw.get("alcance"), base_mecanica["alcance"]))
    else:
        combate["alcance"] = limitar_variacao(
            combate.get("alcance", base_mecanica["alcance"]),
            base_mecanica["alcance"],
            0.90,
            1.08,
            base_mecanica["alcance"],
        )
    if "alcance_minimo" in combate_raw:
        combate["alcance_minimo"] = max(
            0.0,
            normalizar_float(combate_raw.get("alcance_minimo"), base_mecanica["alcance_minimo"]),
        )
    else:
        combate["alcance_minimo"] = limitar_variacao(
            combate.get("alcance_minimo", base_mecanica["alcance_minimo"]),
            max(base_mecanica["alcance_minimo"], 0.01),
            0.85,
            1.15,
            base_mecanica["alcance_minimo"],
        )
    combate["cadencia"] = max(
        0.15,
        limitar_variacao(
            bruto.get("velocidade_ataque", combate.get("cadencia", base_mecanica["cadencia"])),
            base_mecanica["cadencia"],
            0.88, 1.08, base_mecanica["cadencia"],
        ),
    )
    if "startup" in combate_raw:
        combate["startup"] = max(0.01, normalizar_float(combate_raw.get("startup"), base_mecanica["startup"]))
    else:
        combate["startup"] = limitar_variacao(
            combate.get("startup", base_mecanica["startup"]),
            base_mecanica["startup"],
            0.90,
            1.18,
            base_mecanica["startup"],
        )
    if "ativo" in combate_raw:
        combate["ativo"] = max(0.01, normalizar_float(combate_raw.get("ativo"), base_mecanica["ativo"]))
    else:
        combate["ativo"] = limitar_variacao(
            combate.get("ativo", base_mecanica["ativo"]),
            base_mecanica["ativo"],
            0.90,
            1.12,
            base_mecanica["ativo"],
        )
    if "recovery" in combate_raw:
        combate["recovery"] = max(0.01, normalizar_float(combate_raw.get("recovery"), base_mecanica["recovery"]))
    else:
        combate["recovery"] = limitar_variacao(
            combate.get("recovery", base_mecanica["recovery"]),
            base_mecanica["recovery"],
            0.92,
            1.22,
            base_mecanica["recovery"],
        )
    if "critico" in bruto or "critico" in combate_raw:
        combate["critico"] = normalizar_percentual(
            bruto.get("critico", combate_raw.get("critico", combate.get("critico", base_mecanica["critico"]))),
            base_mecanica["critico"],
        )
    else:
        combate["critico"] = normalizar_percentual(
            combate.get("critico", base_mecanica["critico"]),
            base_mecanica["critico"],
        )
    combate["escala_forca"] = limitar_variacao(combate.get("escala_forca", base_mecanica["escala_forca"]), base_mecanica["escala_forca"], 0.88, 1.08, base_mecanica["escala_forca"])
    if base_mecanica["escala_mana"] > 0:
        combate["escala_mana"] = limitar_variacao(combate.get("escala_mana", base_mecanica["escala_mana"]), base_mecanica["escala_mana"], 0.88, 1.10, base_mecanica["escala_mana"])
    else:
        combate["escala_mana"] = 0.0
    combate["projeteis_por_ataque"] = max(1, int(combate.get("projeteis_por_ataque", quantidade)))
    combate["qtd_orbitais"] = max(0, int(combate.get("qtd_orbitais", qtd_orbitais)))
    combate["forca_disparo"] = normalizar_float(combate.get("forca_disparo", forca_arco), forca_arco)
    combate["durabilidade_base"] = normalizar_float(bruto.get("durabilidade_max", combate.get("durabilidade_base", spec["mecanica"]["durabilidade_base"])), spec["mecanica"]["durabilidade_base"])

    visual = deepcopy(spec["visual"])
    visual.update(visual_raw)
    visual["cor_base"] = {
        "r": int(bruto.get("r", visual.get("cor_base", {}).get("r", 200))),
        "g": int(bruto.get("g", visual.get("cor_base", {}).get("g", 200))),
        "b": int(bruto.get("b", visual.get("cor_base", {}).get("b", 200))),
    }
    visual["acabamento"] = corrigir_texto_legado(bruto.get("raridade", visual.get("acabamento", "Padrão")))

    magia = {
        "usa_foco": spec["categoria"] == "foco_magico",
        "afinidade": corrigir_texto_legado(bruto.get("afinidade_elemento", magia_raw.get("afinidade"))),
        "habilidades": deepcopy(bruto.get("habilidades", magia_raw.get("habilidades", []))),
        "skill_primaria": corrigir_texto_legado(bruto.get("habilidade", magia_raw.get("skill_primaria", "Nenhuma"))),
        "custo_primario": normalizar_float(bruto.get("custo_mana", magia_raw.get("custo_primario", 0.0)), 0.0),
    }

    geometria = {
        "comp_cabo": normalizar_float(bruto.get("comp_cabo", 15.0), 15.0),
        "comp_lamina": normalizar_float(bruto.get("comp_lamina", 50.0), 50.0),
        "largura": normalizar_float(bruto.get("largura", 30.0), 30.0),
        "distancia": normalizar_float(bruto.get("distancia", combate["alcance"] * 100.0), combate["alcance"] * 100.0),
        "comp_corrente": normalizar_float(bruto.get("comp_corrente", 0.0), 0.0),
        "comp_ponta": normalizar_float(bruto.get("comp_ponta", 0.0), 0.0),
        "largura_ponta": normalizar_float(bruto.get("largura_ponta", 0.0), 0.0),
        "tamanho_projetil": normalizar_float(bruto.get("tamanho_projetil", 0.0), 0.0),
        "tamanho_arco": normalizar_float(bruto.get("tamanho_arco", 0.0), 0.0),
        "tamanho_flecha": normalizar_float(bruto.get("tamanho_flecha", 0.0), 0.0),
        "tamanho": normalizar_float(bruto.get("tamanho", 8.0), 8.0),
        "distancia_max": normalizar_float(bruto.get("distancia_max", combate["alcance"]), combate["alcance"]),
        "separacao": normalizar_float(bruto.get("separacao", 0.0), 0.0),
        "forma1_cabo": normalizar_float(bruto.get("forma1_cabo", 0.0), 0.0),
        "forma1_lamina": normalizar_float(bruto.get("forma1_lamina", 0.0), 0.0),
        "forma2_cabo": normalizar_float(bruto.get("forma2_cabo", 0.0), 0.0),
        "forma2_lamina": normalizar_float(bruto.get("forma2_lamina", 0.0), 0.0),
    }

    return {
        "schema_version": max(2, schema_version),
        "id": bruto.get("id") or slugify_nome(nome),
        "nome": nome,
        "familia": familia,
        "subtipo": bruto.get("subtipo") or spec["subtipos"][0],
        "categoria": bruto.get("categoria") or spec["categoria"],
        "tipo": legacy_type_from_family(familia),
        "tipo_legacy": legacy_type_from_family(familia),
        "estilo": estilo,
        "combate": combate,
        "visual": visual,
        "magia": magia,
        "geometria": geometria,
        "quantidade": quantidade,
        "quantidade_orbitais": qtd_orbitais,
        "forca_arco": forca_arco,
        "durabilidade": normalizar_float(bruto.get("durabilidade", combate["durabilidade_base"]), combate["durabilidade_base"]),
        "durabilidade_max": combate["durabilidade_base"],
        "forma_atual": int(bruto.get("forma_atual", 1)),
        "meta_legado": {
            "raridade": corrigir_texto_legado(bruto.get("raridade", "Padrão")),
            "encantamentos": deepcopy(bruto.get("encantamentos", [])),
            "passiva": deepcopy(bruto.get("passiva")),
        },
    }
