# Neural Fights v3 rework

Simulador de combate 2D com IA, pipeline de torneio e integracao com um world map pygame.

## Instalacao

Jogo base:

```bash
pip install pygame customtkinter
```

Desenvolvimento:

```bash
pip install -e ".[dev]"
```

Video pipeline:

```bash
pip install -e ".[dev,video]"
```

World map:

```bash
pip install -e ".[worldmap]"
```

Tudo:

```bash
pip install -e ".[dev,video,worldmap]"
```

## Execucao

```bash
# Launcher principal
python run.py

# Smoke do bootstrap sem abrir UI
python run.py --smoke

# Simulacao automatica
python run.py --sim

# Modo de teste manual
python run.py --test

# Modo torneio
python run_tournament.py
python run_tournament.py --smoke

# Hub dos postos operacionais
python run_postos.py headless
python run_postos.py simulacao --modo launcher
python run_postos.py pipeline --fights 1
```

## Estrutura principal

- `ia/`: decisao taticamente orientada por mixins e perfis.
- `nucleo/`: entidades, combate, hitbox, arena e runtime das armas.
- `simulacao/`: loop de combate, renderer, efeitos e pacing.
- `dados/`: persistencia, AppState, SQLite e bridge com o world map.
- `interface/`: UI em CustomTkinter.
- `pipeline_video/`: gravacao, overlays e metadados.
- `world_map_pygame/`: subsistema de mapa integrado por arquivos JSON.
- `scripts/`: automacoes de auditoria e ferramentas de suporte.
- `tests/`: suite pytest.

## Auditoria

Os artefatos de auditoria ficam em `documentacao/auditoria/`.

```bash
python scripts/audit_project.py
python scripts/run_audit_checklist.py
```

## Testes

```bash
pytest -q
```
