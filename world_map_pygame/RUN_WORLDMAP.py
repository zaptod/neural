"""
RUN_WORLDMAP.py — Neural Fights · Aethermoor World Map (pygame)

Coloque este arquivo na raiz do projeto (projeto1.0/) e execute:
    python RUN_WORLDMAP.py
"""
import sys, os

# Adiciona o diretório PAI (projeto1.0/) ao path para que
# "world_map_pygame" seja encontrado como pacote
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world_map_pygame.main import run

if __name__ == "__main__":
    run()
