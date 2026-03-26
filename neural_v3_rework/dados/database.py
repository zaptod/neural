"""
NEURAL FIGHTS - MÃ³dulo Database  [LEGADO â€” C08]
================================================
PersistÃªncia JSON original do projeto.

âš ï¸  ATENÃ‡ÃƒO â€” LEGADO: Este mÃ³dulo Ã© a camada de dados original (JSON flat-file).
    A stack atual usa app_state.py (event-bus in-memory) e battle_db.py (SQLite).
    Novos arquivos NÃƒO devem importar este mÃ³dulo.
    Manter apenas para compatibilidade com cÃ³digo existente atÃ© migraÃ§Ã£o completa (Sprint D01).
"""
import json
import logging
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_log = logging.getLogger("database")

from modelos import Personagem, Arma

# Caminhos dos arquivos de dados - agora dentro de dados/
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CHARS = os.path.join(DATA_DIR, "personagens.json")
ARQUIVO_ARMAS = os.path.join(DATA_DIR, "armas.json")
ARQUIVO_MATCH = os.path.join(DATA_DIR, "match_config.json")

# â”€â”€ WorldBridge (sincronizaÃ§Ã£o com World Map) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# A sincronizaÃ§Ã£o com o World Map Ã© gerenciada por WorldBridge (dados/world_bridge.py).
# Ela Ã© acionada automaticamente pelo AppState via eventos apÃ³s cada luta/torneio.
# NÃ£o Ã© necessÃ¡rio nenhum hook aqui.


def carregar_json(arquivo):
    if not os.path.exists(arquivo): return []
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _log.error("JSON invÃ¡lido em %s: %s", arquivo, e)
        return []
    except Exception as e:
        _log.error("Erro ao ler %s: %s", arquivo, e)
        return []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_armas():
    raw = carregar_json(ARQUIVO_ARMAS)
    return [Arma.from_dict(item) for item in raw]

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
            item.get("classe", "Guerreiro (ForÃ§a Bruta)"),
            item.get("personalidade", "AleatÃ³rio"),
            item.get("god_id", None),       # [PHASE 3] Carrega vÃ­nculo divino
            item.get("lore", ""),           # INC-1: lore nÃ£o estava sendo carregado
            item.get("skills_personagem", item.get("habilidades_personagem", [])),
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
    """Carrega uma arma especÃ­fica pelo nome"""
    armas = carregar_armas()
    for arma in armas:
        if arma.nome == nome_arma:
            return arma
    return None


# FunÃ§Ãµes de compatibilidade WorldMap â€” redirecionam para WorldBridge
def get_worldmap_sync():
    """Legacy: retorna WorldBridge ou None."""
    try:
        from dados.world_bridge import WorldBridge
        return WorldBridge.get()
    except Exception:
        return None

def is_worldmap_active():
    """Legacy: retorna True se WorldBridge encontrou o world_map_pygame/."""
    try:
        from dados.world_bridge import WORLDMAP_AVAILABLE
        return WORLDMAP_AVAILABLE
    except Exception:
        return False

