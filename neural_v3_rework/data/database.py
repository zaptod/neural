"""
NEURAL FIGHTS - Módulo Database
Funções de persistência de dados (JSON).
[PHASE 3] Adicionado hook para sincronização com World Map (WorldStateSync).
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Personagem, Arma

# Caminhos dos arquivos de dados - agora dentro de data/
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CHARS = os.path.join(DATA_DIR, "personagens.json")
ARQUIVO_ARMAS = os.path.join(DATA_DIR, "armas.json")
ARQUIVO_MATCH = os.path.join(DATA_DIR, "match_config.json")

# ── WorldBridge (sincronização com World Map) ──────────────────────────────────
# A sincronização com o World Map é gerenciada por WorldBridge (data/world_bridge.py).
# Ela é acionada automaticamente pelo AppState via eventos após cada luta/torneio.
# Não é necessário nenhum hook aqui.


def carregar_json(arquivo):
    if not os.path.exists(arquivo): return []
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_armas():
    raw = carregar_json(ARQUIVO_ARMAS)
    return [Arma(**item) for item in raw]

def carregar_personagens():
    raw_chars = carregar_json(ARQUIVO_CHARS)
    raw_armas = carregar_json(ARQUIVO_ARMAS)
    
    lista = []
    for item in raw_chars:
        peso_arma = 0
        nome_arma = item.get("nome_arma", "")
        
        # Busca o peso atualizado da arma
        for a in raw_armas:
            if a["nome"] == nome_arma:
                peso_arma = a["peso"]
                break
        
        p = Personagem(
            item["nome"], item["tamanho"], item["forca"], item["mana"],
            nome_arma, peso_arma,
            item.get("cor_r", 200), item.get("cor_g", 50), item.get("cor_b", 50),
            item.get("classe", "Guerreiro (Força Bruta)"),
            item.get("personalidade", "Aleatório"),
            item.get("god_id", None),       # [PHASE 3] Carrega vínculo divino
            item.get("lore", ""),           # INC-1: lore não estava sendo carregado
        )
        lista.append(p)
    return lista

def salvar_lista_armas(lista):
    salvar_json(ARQUIVO_ARMAS, [a.to_dict() for a in lista])

def salvar_lista_chars(lista):
    """Salva lista de personagens via AppState (que dispara WorldBridge automaticamente)."""
    dicts = [p.to_dict() for p in lista]
    salvar_json(ARQUIVO_CHARS, dicts)


def carregar_arma_por_nome(nome_arma):
    """Carrega uma arma específica pelo nome"""
    armas = carregar_armas()
    for arma in armas:
        if arma.nome == nome_arma:
            return arma
    return None


# Funções de compatibilidade WorldMap — redirecionam para WorldBridge
def get_worldmap_sync():
    """Legacy: retorna WorldBridge ou None."""
    try:
        from data.world_bridge import WorldBridge
        return WorldBridge.get()
    except Exception:
        return None

def is_worldmap_active():
    """Legacy: retorna True se WorldBridge encontrou o world_map_pygame/."""
    try:
        from data.world_bridge import WORLDMAP_AVAILABLE
        return WORLDMAP_AVAILABLE
    except Exception:
        return False
