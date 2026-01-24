# database.py
import json
import os
from models import Personagem, Arma

ARQUIVO_CHARS = "personagens.json"
ARQUIVO_ARMAS = "armas.json"

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
            item.get("cor_r", 200), item.get("cor_g", 50), item.get("cor_b", 50)
        )
        lista.append(p)
    return lista

def salvar_lista_armas(lista):
    salvar_json(ARQUIVO_ARMAS, [a.to_dict() for a in lista])

def salvar_lista_chars(lista):
    salvar_json(ARQUIVO_CHARS, [p.to_dict() for p in lista])