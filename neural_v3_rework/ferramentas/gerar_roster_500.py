"""Gera um roster novo de 500 personagens para personagens.json."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ia.personalities import LISTA_PERSONALIDADES
from modelos import Arma, LISTA_CLASSES, get_class_data
from modelos.characters import Personagem

ARMAS_PATH = ROOT / "dados" / "armas.json"
PERSONAGENS_PATH = ROOT / "dados" / "personagens.json"

TOTAL_PERSONAGENS = 500


PREFIXOS = [
    "Aeron", "Kaelis", "Mira", "Darian", "Lyra", "Thorne", "Selka", "Valen", "Nyra", "Cael",
    "Riven", "Sorin", "Talia", "Draven", "Iris", "Korin", "Vesper", "Noa", "Seren", "Orin",
    "Zarya", "Lukan", "Elda", "Cassian", "Rhea", "Tarek", "Alina", "Bren", "Nerys", "Lucan",
]

SUFIXOS = [
    "Ferro", "Vale", "Cendra", "Noite", "Solar", "Rune", "Marfim", "Tempra", "Gume", "Aurora",
    "Bruma", "Orion", "Cinza", "Rubra", "Vesper", "Doura", "Luar", "Fulgor", "Eco", "Nexus",
]

EPITETOS = [
    "da Brasa", "do Eclipse", "das Runas", "da Vigilia", "do Vazio", "da Tempestade",
    "da Coroa", "da Areia", "do Trovão", "do Musgo", "da Lanca Sombria", "da Ultima Luz",
    "do Portal", "da Queda", "do Labirinto", "da Aurora", "do Selo", "das Correntes",
]


def _clamp_color(value: int) -> int:
    return max(35, min(255, value))


def _class_family(classe: str) -> str:
    if any(tag in classe for tag in ("Mago", "Piromante", "Criomante", "Necromante")):
        return "magico"
    if any(tag in classe for tag in ("Assassino", "Ladino", "Ninja", "Duelista")):
        return "agil"
    if any(tag in classe for tag in ("Paladino", "Druida", "Feiticeiro", "Monge")):
        return "hibrido"
    return "fisico"


def _roll_stats(classe: str, weapon_family: str, rng: random.Random) -> tuple[float, float, float]:
    perfil = _class_family(classe)
    if perfil == "fisico":
        tamanho = rng.uniform(1.55, 2.45)
        forca = rng.uniform(6.2, 8.9)
        mana = rng.uniform(3.2, 6.8)
    elif perfil == "agil":
        tamanho = rng.uniform(1.35, 1.95)
        forca = rng.uniform(5.1, 7.6)
        mana = rng.uniform(4.0, 7.2)
    elif perfil == "magico":
        tamanho = rng.uniform(1.35, 2.05)
        forca = rng.uniform(3.4, 5.9)
        mana = rng.uniform(7.6, 9.8)
    else:
        tamanho = rng.uniform(1.45, 2.20)
        forca = rng.uniform(4.8, 7.9)
        mana = rng.uniform(5.4, 8.8)

    if weapon_family in {"disparo", "arremesso"}:
        forca -= 0.25
        mana += 0.20
    elif weapon_family in {"corrente", "haste"}:
        tamanho += 0.08
        forca += 0.30
    elif weapon_family in {"foco", "orbital"}:
        forca -= 0.35
        mana += 0.45
    elif weapon_family == "dupla":
        tamanho -= 0.06
        mana += 0.10

    return (
        round(max(0.6, min(2.9, tamanho)), 2),
        round(max(1.1, min(9.8, forca)), 2),
        round(max(1.1, min(9.9, mana)), 2),
    )


def _build_name(index: int) -> str:
    prefixo = PREFIXOS[index % len(PREFIXOS)]
    sufixo = SUFIXOS[(index // len(PREFIXOS)) % len(SUFIXOS)]
    epiteto = EPITETOS[(index // (len(PREFIXOS) * len(SUFIXOS))) % len(EPITETOS)]
    return f"{prefixo} {sufixo} {epiteto}"


def _build_lore(nome: str, classe: str, personalidade: str, arma_nome: str) -> str:
    classe_curta = classe.split(" (")[0]
    return (
        f"{nome} e um {classe_curta.lower()} de perfil {personalidade.lower()} "
        f"que transforma {arma_nome} em sua assinatura de combate."
    )


def main() -> None:
    rng = random.Random(50017)
    armas_payload = json.loads(ARMAS_PATH.read_text(encoding="utf-8"))
    armas = [Arma.from_dict(payload) for payload in armas_payload]
    if not armas:
        raise RuntimeError("Nenhuma arma encontrada para gerar o roster.")

    personagens = []
    for i in range(TOTAL_PERSONAGENS):
        arma = armas[i % len(armas)]
        classe = LISTA_CLASSES[i % len(LISTA_CLASSES)]
        personalidade = LISTA_PERSONALIDADES[(i * 7) % len(LISTA_PERSONALIDADES)]
        tamanho, forca, mana = _roll_stats(classe, arma.familia, rng)
        aura = get_class_data(classe).get("cor_aura", (180, 180, 180))
        cor_r = _clamp_color(aura[0] + rng.randint(-25, 25))
        cor_g = _clamp_color(aura[1] + rng.randint(-25, 25))
        cor_b = _clamp_color(aura[2] + rng.randint(-25, 25))
        nome = _build_name(i)
        personagem = Personagem(
            nome=nome,
            tamanho=tamanho,
            forca=forca,
            mana=mana,
            nome_arma=arma.nome,
            r=cor_r,
            g=cor_g,
            b=cor_b,
            classe=classe,
            personalidade=personalidade,
            god_id=None,
            lore=_build_lore(nome, classe, personalidade, arma.nome),
        )
        personagens.append(personagem.to_dict())

    PERSONAGENS_PATH.write_text(
        json.dumps(personagens, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    print(f"personagens_gerados={len(personagens)}")


if __name__ == "__main__":
    main()
