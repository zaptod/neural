#!/usr/bin/env python3
"""
NEURAL FIGHTS - Ponto de Entrada Principal
Execute este arquivo para iniciar o jogo.

Uso:
    python run.py         # Inicia o launcher (UI)
    python run.py --sim   # Inicia a simulação diretamente
"""
import sys
import os

# Adiciona o diretório do projeto ao path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

def main():
    """Ponto de entrada principal."""
    if len(sys.argv) > 1 and sys.argv[1] == '--sim':
        # Executa simulação diretamente
        from simulation import Simulador
        sim = Simulador()
        sim.executar()
    else:
        # Executa o launcher (UI)
        from ui.main import main as run_launcher
        run_launcher()

if __name__ == '__main__':
    main()
