# Neural Fights v3

Simulador de combate 2D com IA avançada — 120+ personagens, 15 tipos de arma, 14 elementos mágicos e batalhas multi-combatente.

---

## Instalação

```bash
# Instalação rápida (apenas o jogo)
pip install pygame customtkinter

# Instalação completa (jogo + vídeo + testes)
pip install -e ".[dev,video]"
```

## Executar

```bash
# Interface gráfica principal
python run.py

# Modo torneio headless
python run_tournament.py
```

## Testes

```bash
pytest tests/
```

## Estrutura do projeto

```
neural_v3_rework/
├── ai/                  Sistema de IA — brain, mixins, perfis de comportamento
├── core/
│   ├── fighter/         Lutador dividido em 4 mixins (Sprint 8)
│   │   ├── entity.py    — __init__ + update()
│   │   ├── stats.py     — vida/mana/skills
│   │   ├── physics_mixin.py  — física e movimento
│   │   ├── combat_mixin.py   — dano, status, morte
│   │   └── weapons_mixin.py  — ataques v15.0
│   ├── skills/          Catálogo de skills por elemento (14 arquivos)
│   ├── arena.py         Arenas com efeitos especiais e obstáculos destruíveis
│   └── combat.py        Projéteis, áreas, beams, summons
├── data/
│   ├── app_state.py     Event-bus central (fonte de verdade)
│   ├── battle_db.py     SQLite — histórico e ELO
│   └── world_bridge.py  Sincronização com World Map
├── effects/             Partículas, câmera, VFX, áudio
├── models/              Personagens, armas, classes, constantes
├── simulation/          Loop de simulação, renderer, combate, efeitos
├── tools/               auto_balance.py, balance_report.py
├── tests/               Testes automáticos (pytest)
├── ui/                  Interface customtkinter
├── utils/               config.py, balance_config.py
├── video_pipeline/      Geração de vídeos de lutas
└── _archive/            Código arquivado (não remover sem consultar)
```

## Configurações úteis

### Debug da IA

Em `utils/config.py`:

```python
DEBUG_AI = True            # loga todas as decisões da IA
DEBUG_AI_FIGHTER = "Nome"  # filtra por lutador específico
```

Saída em nível `DEBUG` no logger `neural_ai`.

### Balance

```bash
# Torneio automático com relatório de win-rate
python tools/auto_balance.py --fights 50 --top 10
```

Ajuste constantes em `utils/balance_config.py` e reexecute para medir o efeito.

---

## Sprints de refactoring (histórico)

| Sprint | Descrição |
|---|---|
| 1 | Infraestrutura base — pyproject.toml, logging, arquivamento |
| 2 | Logging + legado — database.py marcado |
| 3 | Pipeline de dados — BridgeResult, flush stats |
| 4 | Performance — surface cache, AI throttle, StatusSnapshot |
| 5 | Balance & organização — balance_config.py, skills por elemento |
| 6 | Features órfãs — cor_ambiente, obstáculos, reações elementais |
| 7 | Status effects — aplicar_cc(), cc_effects, física O(n²) |
| 8 | Entities refactor — Lutador dividido em 4 mixins, D04 inline imports |
| 9 | Performance & debug — DEBUG_AI, rand_pool×4, clash budget, homing cache |
| 10 | D01/C01/C09 — database migrado, magic_system e simulacao_original arquivados |
| 11 | Qualidade final — E02 excepts, E03 testes organizados, README |
