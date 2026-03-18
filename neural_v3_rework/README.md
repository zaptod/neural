# Neural Fights v3

Simulador de combate 2D com IA avanÃ§ada â€” 120+ personagens, 15 tipos de arma, 14 elementos mÃ¡gicos e batalhas multi-combatente.

---

## InstalaÃ§Ã£o

```bash
# InstalaÃ§Ã£o rÃ¡pida (apenas o jogo)
pip install pygame customtkinter

# InstalaÃ§Ã£o completa (jogo + vÃ­deo + testes)
pip install -e ".[dev,video]"
```

## Executar

```bash
# Interface grÃ¡fica principal
python run.py

# Modo torneio headless
python run_tournament.py

# Hub dos postos operacionais
python run_postos.py headless --mode rapido
python run_postos.py headless --tatico --modo 1v1 --template duelo_papeis_basicos --runs 3
python run_postos.py simulacao --modo launcher
python run_postos.py pipeline --fights 1
```

## Testes

```bash
pytest tests/
```

## Estrutura do projeto

```
neural_v3_rework/
â”œâ”€â”€ ia/                  Sistema de IA â€” brain, mixins, perfis de comportamento
â”œâ”€â”€ nucleo/
â”‚   â”œâ”€â”€ fighter/         Lutador dividido em 4 mixins (Sprint 8)
â”‚   â”‚   â”œâ”€â”€ entity.py    â€” __init__ + update()
â”‚   â”‚   â”œâ”€â”€ stats.py     â€” vida/mana/skills
â”‚   â”‚   â”œâ”€â”€ physics_mixin.py  â€” fÃ­sica e movimento
â”‚   â”‚   â”œâ”€â”€ combat_mixin.py   â€” dano, status, morte
â”‚   â”‚   â””â”€â”€ weapons_mixin.py  â€” ataques v15.0
â”‚   â”œâ”€â”€ skills/          CatÃ¡logo de skills por elemento (14 arquivos)
â”‚   â”œâ”€â”€ arena.py         Arenas com efeitos especiais e obstÃ¡culos destruÃ­veis
â”‚   â””â”€â”€ combat.py        ProjÃ©teis, Ã¡reas, beams, summons
â”œâ”€â”€ dados/
â”‚   â”œâ”€â”€ app_state.py     Event-bus central (fonte de verdade)
â”‚   â”œâ”€â”€ battle_db.py     SQLite â€” histÃ³rico e ELO
â”‚   â””â”€â”€ world_bridge.py  SincronizaÃ§Ã£o com World Map
â”œâ”€â”€ efeitos/             PartÃ­culas, cÃ¢mera, VFX, Ã¡udio
â”œâ”€â”€ modelos/              Personagens, armas, classes, constantes
â”œâ”€â”€ simulacao/          Loop de simulaÃ§Ã£o, renderer, combate, efeitos
â”œâ”€â”€ ferramentas/               auto_balance.py, balance_report.py
â”œâ”€â”€ tests/               Testes automÃ¡ticos (pytest)
â”œâ”€â”€ interface/                  Interface customtkinter
â”œâ”€â”€ utilitarios/               config.py, balance_config.py
â”œâ”€â”€ pipeline_video/      GeraÃ§Ã£o de vÃ­deos de lutas
â””â”€â”€ _archive/            CÃ³digo arquivado (nÃ£o remover sem consultar)
```

## ConfiguraÃ§Ãµes Ãºteis

### Debug da IA

Em `utilitarios/config.py`:

```python
DEBUG_AI = True            # loga todas as decisÃµes da IA
DEBUG_AI_FIGHTER = "Nome"  # filtra por lutador especÃ­fico
```

SaÃ­da em nÃ­vel `DEBUG` no logger `neural_ai`.

### Balance

```bash
# Torneio automÃ¡tico com relatÃ³rio de win-rate
python ferramentas/auto_balance.py --fights 50 --top 10
```

Ajuste constantes em `utilitarios/balance_config.py` e reexecute para medir o efeito.

---

## Sprints de refactoring (histÃ³rico)

| Sprint | DescriÃ§Ã£o |
|---|---|
| 1 | Infraestrutura base â€” pyproject.toml, logging, arquivamento |
| 2 | Logging + legado â€” database.py marcado |
| 3 | Pipeline de dados â€” BridgeResult, flush stats |
| 4 | Performance â€” surface cache, AI throttle, StatusSnapshot |
| 5 | Balance & organizaÃ§Ã£o â€” balance_config.py, skills por elemento |
| 6 | Features Ã³rfÃ£s â€” cor_ambiente, obstÃ¡culos, reaÃ§Ãµes elementais |
| 7 | Status effects â€” aplicar_cc(), cc_effects, fÃ­sica O(nÂ²) |
| 8 | Entities refactor â€” Lutador dividido em 4 mixins, D04 inline imports |
| 9 | Performance & debug â€” DEBUG_AI, rand_poolÃ—4, clash budget, homing cache |
| 10 | D01/C01/C09 â€” database migrado, magic_system e simulacao_original arquivados |
| 11 | Qualidade final â€” E02 excepts, E03 testes organizados, README |

