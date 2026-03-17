"""
NEURAL FIGHTS - Script de GeraÃ§Ã£o Completa do Roster
====================================================
Gera personagens e armas cobrindo TODAS as combinaÃ§Ãµes possÃ­veis:
- 16 Classes
- 6 Raridades
- 8 Tipos de Arma
- 12 Encantamentos
- 20+ Personalidades
- 100+ Skills

Execute este script para popular o banco de dados antes de um torneio.
"""

import os
import sys

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ferramentas.gerador_database import (
    gerar_database_completa, 
    salvar_database,
    gerar_arma,
    gerar_personagem,
    LISTA_PERSONALIDADES,
    TODAS_SKILLS
)
from modelos.constants import (
    LISTA_CLASSES, 
    LISTA_RARIDADES, 
    LISTA_TIPOS_ARMA,
    LISTA_ENCANTAMENTOS
)


def gerar_roster_completo():
    """
    Gera um roster completo cobrindo todas as combinaÃ§Ãµes principais.
    
    CombinaÃ§Ãµes:
    - 8 tipos de arma x 6 raridades = 48 armas base
    - 48 armas x alguns encantamentos = ~100 armas variadas
    - 16 classes x 4 personalidades principais = 64 personagens mÃ­nimo
    """
    print("=" * 70)
    print("  NEURAL FIGHTS - GERADOR DE ROSTER COMPLETO")
    print("=" * 70)
    
    armas = []
    personagens = []
    
    # === GERA ARMAS ===
    print("\nðŸ“¦ Gerando armas...")
    
    arma_count = 0
    
    # Uma arma de cada tipo para cada raridade (48 armas base)
    for tipo in LISTA_TIPOS_ARMA:
        for raridade in LISTA_RARIDADES:
            # VersÃ£o sem encantamento
            arma = gerar_arma(tipo, raridade)
            armas.append(arma)
            arma_count += 1
            
            # Para raridades altas, adiciona versÃµes com encantamentos
            if raridade in ["Ã‰pico", "LendÃ¡rio", "MÃ­tico"]:
                for enc in LISTA_ENCANTAMENTOS[:3]:  # 3 encantamentos principais
                    arma_enc = gerar_arma(tipo, raridade, encantamentos=[enc])
                    armas.append(arma_enc)
                    arma_count += 1
    
    print(f"   âœ… {arma_count} armas geradas")
    
    # === GERA PERSONAGENS ===
    print("\nðŸ‘¥ Gerando personagens...")
    
    char_count = 0
    
    # Personalidades principais para variar
    personalidades_principais = [
        "Agressivo", "Defensivo", "TÃ¡tico", "Equilibrado",
        "Berserker", "Assassino", "Showman", "Sombrio"
    ]
    
    # Um personagem de cada classe com cada personalidade principal
    for classe in LISTA_CLASSES:
        for i, personalidade in enumerate(personalidades_principais):
            # Pega uma arma diferente para cada personagem
            arma_idx = (char_count) % len(armas)
            arma_nome = armas[arma_idx]["nome"]
            
            personagem = gerar_personagem(classe, personalidade, arma_nome)
            personagens.append(personagem)
            char_count += 1
    
    # Adiciona mais personagens com personalidades exÃ³ticas
    personalidades_exoticas = [
        "Viking", "Samurai", "Perseguidor", "Protetor",
        "AcrobÃ¡tico", "AleatÃ³rio"
    ]
    
    for i, personalidade in enumerate(personalidades_exoticas):
        classe = LISTA_CLASSES[i % len(LISTA_CLASSES)]
        arma_idx = (char_count) % len(armas)
        arma_nome = armas[arma_idx]["nome"]
        
        personagem = gerar_personagem(classe, personalidade, arma_nome)
        personagens.append(personagem)
        char_count += 1
    
    print(f"   âœ… {char_count} personagens gerados")
    
    # === SALVA ===
    print("\nðŸ’¾ Salvando database...")
    salvar_database(armas, personagens)
    
    # === SUMÃRIO ===
    print("\n" + "=" * 70)
    print("  SUMÃRIO DA GERAÃ‡ÃƒO")
    print("=" * 70)
    print(f"\n  ðŸ—¡ï¸  Armas: {len(armas)}")
    print(f"      - Tipos: {len(LISTA_TIPOS_ARMA)} ({', '.join(LISTA_TIPOS_ARMA)})")
    print(f"      - Raridades: {len(LISTA_RARIDADES)}")
    print(f"      - Encantamentos disponÃ­veis: {len(LISTA_ENCANTAMENTOS)}")
    
    print(f"\n  ðŸ‘¤ Personagens: {len(personagens)}")
    print(f"      - Classes: {len(LISTA_CLASSES)}")
    
    classes_usadas = set(p["classe"] for p in personagens)
    print(f"      - Classes utilizadas: {len(classes_usadas)}")
    
    personalidades_usadas = set(p["personalidade"] for p in personagens)
    print(f"      - Personalidades: {len(personalidades_usadas)}")
    
    print("\n" + "=" * 70)
    print("  âœ… ROSTER COMPLETO GERADO COM SUCESSO!")
    print("  Execute o Modo Torneio para iniciar os combates.")
    print("=" * 70)
    
    return armas, personagens


def gerar_roster_torneio_64():
    """Gera um roster otimizado para torneio de 64 lutadores"""
    print("=" * 70)
    print("  NEURAL FIGHTS - ROSTER PARA TORNEIO DE 64")
    print("=" * 70)
    
    armas, personagens = gerar_database_completa(64, "balanceada")
    salvar_database(armas, personagens)
    
    print(f"\nâœ… Gerados {len(personagens)} lutadores para o torneio!")
    return armas, personagens


def gerar_roster_torneio_16():
    """Gera um roster compacto para torneio de 16 lutadores"""
    print("=" * 70)
    print("  NEURAL FIGHTS - ROSTER PARA TORNEIO DE 16")
    print("=" * 70)
    
    armas, personagens = gerar_database_completa(16, "representativa")
    salvar_database(armas, personagens)
    
    print(f"\nâœ… Gerados {len(personagens)} lutadores para o torneio!")
    return armas, personagens


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerador de Roster Neural Fights")
    parser.add_argument("--modo", choices=["completo", "64", "16"], default="completo",
                       help="Modo de geraÃ§Ã£o: completo, 64 ou 16 lutadores")
    
    args = parser.parse_args()
    
    if args.modo == "64":
        gerar_roster_torneio_64()
    elif args.modo == "16":
        gerar_roster_torneio_16()
    else:
        gerar_roster_completo()

