"""diagnostico_hitbox.py â€” DiagnÃ³stico v2.0 (geometria removida)."""
from nucleo.hitbox import HITBOX_PROFILES, get_hitbox_profile


def diagnosticar_arma_hitbox(arma_dict):
    """Valida campos de gameplay de uma arma. Retorna lista de problemas."""
    problemas = []
    tipo = arma_dict.get("tipo", "")
    if not tipo:
        problemas.append({"severidade": "CRITICO", "problema": "Arma sem tipo definido", "sugestao": "Definir 'tipo'"})
        return problemas
    if not get_hitbox_profile(tipo):
        problemas.append({"severidade": "AVISO", "problema": f"Tipo '{tipo}' sem perfil dedicado",
                           "sugestao": f"Tipos vÃ¡lidos: {list(HITBOX_PROFILES.keys())}"})
    if tipo == "Arremesso" and arma_dict.get("quantidade", 0) < 1:
        problemas.append({"severidade": "AVISO", "problema": "Arremesso sem quantidade", "sugestao": "quantidade >= 1"})
    elif tipo == "Arco" and arma_dict.get("forca_arco", 0) <= 0:
        problemas.append({"severidade": "AVISO", "problema": "Arco com forca_arco = 0", "sugestao": "forca_arco > 0"})
    elif tipo == "Orbital" and arma_dict.get("quantidade_orbitais", 0) < 1:
        problemas.append({"severidade": "AVISO", "problema": "Orbital sem quantidade_orbitais", "sugestao": "quantidade_orbitais >= 1"})
    return problemas


def diagnosticar_database(armas):
    return [{"nome": a.get("nome","?"), "problemas": p}
            for a in armas if (p := diagnosticar_arma_hitbox(a))]


def imprimir_relatorio(armas):
    res = diagnosticar_database(armas)
    if not res: print("âœ“ Todas as armas OK"); return
    for r in res:
        print(f"\n[{r['nome']}]")
        for p in r["problemas"]:
            print(f"  {p['severidade']}: {p['problema']} â†’ {p['sugestao']}")


def obter_info_tipo(tipo):
    p = get_hitbox_profile(tipo)
    return {"tipo": tipo, "range_mult": p.get("range_mult", 2.0),
            "nota": "Tamanho depende do personagem (raio_fisico Ã— range_mult)"}

