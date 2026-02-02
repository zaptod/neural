# NEURAL FIGHTS - Estrutura do Projeto v10.0

## Visão Geral da Arquitetura

O projeto foi reorganizado em módulos bem definidos para melhor manutenibilidade e escalabilidade.
**A raiz do projeto está limpa, sem arquivos Python de lógica - apenas o `run.py` como ponto de entrada.**

## Estrutura de Diretórios

```
neural/
├── run.py              # ÚNICO ponto de entrada (launcher)
│
├── core/               # Módulos essenciais do jogo
│   ├── entities.py     # Classe Lutador e entidades do jogo
│   ├── physics.py      # Sistema de física e colisões
│   ├── skills.py       # Catálogo de habilidades (SKILL_DB)
│   ├── combat.py       # Classes de projéteis e efeitos de combate
│   ├── hitbox.py       # Sistema de hitbox e detecção de colisão
│   ├── arena.py        # Sistema de arenas com obstáculos
│   └── game_feel.py    # Sistema de Game Feel (hit stop, camera shake)
│
├── ai/                 # Sistema de Inteligência Artificial
│   ├── brain.py        # Cérebro principal da IA
│   ├── emotions.py     # Sistema de emoções e humor
│   ├── spatial.py      # Consciência espacial (paredes, obstáculos)
│   ├── combat_tactics.py # Táticas de combate (leitura, momentum, baiting)
│   ├── choreographer.py # Coreografia de combate cinematográfico
│   └── personalities.py # Arquétipos, traços e quirks de personalidade
│
├── effects/            # Efeitos visuais e áudio
│   ├── particles.py    # Sistema de partículas
│   ├── camera.py       # Sistema de câmera
│   ├── movement.py     # Animações de movimento
│   ├── attack.py       # Efeitos de ataque
│   ├── impact.py       # Efeitos de impacto
│   ├── visual.py       # Textos flutuantes, decals
│   ├── audio.py        # Sistema de áudio
│   └── weapon_animations.py # Animações de armas
│
├── ui/                 # Interface do usuário (Tkinter)
│   ├── main.py         # Launcher principal
│   ├── view_armas.py   # Tela de criação/edição de armas
│   ├── view_chars.py   # Tela de criação/edição de personagens
│   ├── view_luta.py    # Tela de configuração de luta
│   └── theme.py        # Configurações de tema visual
│
├── models/             # Modelos de dados
│   ├── constants.py    # Constantes (raridades, tipos de arma, etc)
│   ├── weapons.py      # Classe Arma e funções relacionadas
│   └── characters.py   # Classe Personagem
│
├── data/               # Persistência de dados
│   ├── database.py     # Funções de carregar/salvar JSON
│   ├── armas.json      # Banco de armas
│   ├── personagens.json # Banco de personagens
│   └── match_config.json # Configuração de partida
│
├── utils/              # Utilitários
│   ├── config.py       # Constantes globais (cores, dimensões, física)
│   └── helpers.py      # Funções auxiliares
│
├── simulation/         # Simulação de combate
│   └── simulacao.py    # Simulador principal (Pygame)
│
├── tools/              # Ferramentas de desenvolvimento
│   ├── diagnostico_hitbox.py # Diagnóstico visual de hitboxes
│   └── analise_armas.py      # Análise de armas
│
├── examples/           # Exemplos de uso
│   └── exemplo_sons_customizados.py # Exemplo de sons
│
└── sounds/             # Arquivos de áudio
```

## Como Executar

```bash
# Inicia o launcher (interface gráfica)
python run.py

# Inicia a simulação diretamente
python run.py --sim
```

## Módulos Principais

### core/
Contém a lógica essencial do jogo:
- **entities.py**: Classe `Lutador` com todas as propriedades e métodos
- **physics.py**: Cálculos de colisão, distância, normalização de ângulos
- **skills.py**: Banco de dados de habilidades (SKILL_DB)
- **combat.py**: Projéteis, áreas de efeito, buffs, DOTs
- **hitbox.py**: Sistema de hitbox para detecção de colisão
- **arena.py**: Arenas com obstáculos e zonas especiais
- **game_feel.py**: Hit stop, camera shake, super armor, channeling

### ai/
Sistema de inteligência artificial modular:
- **brain.py** (121KB): Cérebro principal - decisões, personalidade, comportamentos
- **emotions.py**: Estados emocionais (medo, raiva, confiança)
- **spatial.py**: Consciência de paredes, obstáculos, caminhos
- **combat_tactics.py**: Leitura de oponente, momentum, baiting
- **choreographer.py**: Coreografia cinematográfica de combate
- **personalities.py**: Arquétipos, traços e quirks

### effects/
Sistema visual e sonoro:
- **particles.py**: Partículas, faíscas, ondas de choque
- **camera.py**: Controle de câmera e zoom
- **movement.py**: Afterimages, dust clouds, speed lines
- **attack.py**: Trails de arma, anticipation, impacts
- **audio.py**: Gerenciador de áudio com suporte a Pygame mixer
- **weapon_animations.py**: Animações procedurais de armas

### simulation/
- **simulacao.py** (106KB): Motor principal do jogo - loop de jogo, renderização, lógica de combate

### data/
- **database.py**: Funções para carregar/salvar armas e personagens em JSON
- Arquivos JSON com dados persistidos

### ui/
Interface gráfica Tkinter:
- **main.py**: Launcher com botões para cada tela
- **view_armas.py**: Editor de armas
- **view_chars.py**: Editor de personagens
- **view_luta.py**: Configuração de luta

## Imports Recomendados

```python
# Core
from core import Lutador, SKILL_DB, distancia_pontos
from core.hitbox import sistema_hitbox, verificar_hit
from core.arena import ArenaObstaculos
from core.combat import Projetil, AreaEffect

# AI
from ai import AIBrain, PersonalidadeIA
from ai.emotions import SistemaEmocoes
from ai.spatial import SistemaEspacial

# Effects
from effects import Particula, Câmera
from effects.audio import GerenciadorAudio

# Models
from models import Arma, Personagem, TipoArma

# Data
from data.database import carregar_personagens, salvar_personagem

# Config
from utils.config import LARGURA, ALTURA, CORES
```

## Histórico de Versões

### v10.0 - Estrutura Limpa
- Raiz do projeto limpa (apenas run.py)
- simulacao.py movido para simulation/
- arena.py movido para core/
- audio.py movido para effects/
- main.py movido para ui/
- Arquivos JSON movidos para data/
- Ferramentas movidas para tools/
- Exemplos movidos para examples/
- Todos os wrappers removidos
- Imports atualizados em todos os módulos
