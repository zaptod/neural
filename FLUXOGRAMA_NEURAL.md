# Fluxograma do Projeto Neural

Este documento resume como o projeto `neural/` funciona hoje no workspace atual. A pasta raiz atua como um hub com dois aplicativos:

- `neural_v3_rework/`: simulador principal de combate 2D
- `world_map_pygame/`: mapa-mundi separado, integrado aos resultados das lutas

O fluxo principal passa por launcher, interface, estado central, simulacao, IA, persistencia e, opcionalmente, sincronizacao com o world map.

## 1. Entrada Ate a Execucao

O caminho padrao comeca no launcher da raiz e encaminha a execucao para o projeto principal. A partir dali, o sistema pode abrir a UI Tkinter, rodar simulacao direta ou modo de teste manual.

```mermaid
flowchart TD
    A[RUN_GAME.py<br/>Launcher da raiz] --> B[neural_v3_rework/run.py]
    B --> C{Argumentos}
    C -->|sem argumentos| D[interface/main.py<br/>UI Tkinter]
    C -->|--sim| E[simulacao/Simulador]
    C -->|--test| F[utilitarios/test_manual.py]
    D --> G[Tela de selecao e operacao]
    G --> H[TelaLuta / outras telas]
    H --> E
    E --> I[Loop Pygame da luta]
```

## 2. Runtime da Luta

Quando a luta e iniciada, a interface consulta o estado central, monta os combatentes e entrega tudo para o simulador. O loop principal atualiza IA, fisica, combate, efeitos e renderizacao a cada frame ate o resultado final.

```mermaid
flowchart TD
    A[TelaLuta<br/>Configuracao da partida] --> B[AppState<br/>Fonte central de dados]
    B --> C[Personagem + Arma<br/>dados/modelos]
    C --> D[Lutador<br/>nucleo/lutador/entity.py]
    D --> E[AIBrain<br/>ia/brain.py]
    D --> F[Skills / fisica / combate]
    E --> G[Decisao de comportamento]
    G --> H[Simulador.run]
    F --> H
    H --> I[sim_renderer.py<br/>Desenho]
    H --> J[sim_combat.py<br/>Ataques, hitbox, dano]
    H --> K[sim_effects.py<br/>Particulas, camera, VFX, audio]
    I --> L[Frame renderizado]
    J --> M[Estado da luta atualizado]
    K --> M
    M --> N{Fim da luta?}
    N -->|nao| H
    N -->|sim| O[Resultado final]
```

## 3. Dados e Persistencia

O projeto usa JSON como base de configuracao e cadastro, com `AppState` como ponto central de leitura e escrita. Resultados de lutas e estatisticas podem seguir para SQLite, e o vencedor tambem pode propagar efeitos para o `world_map_pygame`.

```mermaid
flowchart TD
    A[dados/personagens.json<br/>dados/armas.json<br/>match_config.json<br/>gods.json] --> B[AppState]
    B --> C[UI Tkinter]
    B --> D[Simulador]
    B --> E[Torneio]
    D --> F[BattleDB<br/>SQLite de historico e ELO]
    E --> F
    D --> G[WorldBridge]
    E --> G
    G --> H[world_map_pygame/data/world_state.json]
    G --> I[world_map_pygame/data/gods.json]
    F --> J[Ranking / historico / estatisticas]
```

## 4. Modos Operacionais

O arquivo `run_postos.py` funciona como orquestrador de operacao. Ele separa execucoes de simulacao, headless e pipeline de video, padronizando logs e saidas em `saidas/`.

```mermaid
flowchart TD
    A[run_postos.py] --> B{Posto}
    B -->|headless| C[Suite headless<br/>ou harness tatico]
    B -->|simulacao| D[Launcher / sim / manual]
    B -->|pipeline| E[pipeline_video/run_pipeline.py]
    C --> F[saidas/headless]
    D --> G[saidas/simulacao]
    E --> H[saidas/pipeline]
    H --> I[Videos, frames, relatorios]
```

## Como Ler a Arquitetura

- `interface`: telas Tkinter para operar o sistema, selecionar personagens, iniciar lutas e consultar visoes auxiliares.
- `simulacao`: loop Pygame da luta, dividido em renderer, combate e efeitos.
- `nucleo`: entidades, hitbox, arena, fisica, combate e catalogo de skills.
- `ia`: cerebro dos bots, com modulos de percepcao, combate, evasao, spatial awareness e coreografia.
- `modelos`: definicao de `Personagem`, `Arma` e constantes de classes e tipos.
- `dados`: JSONs de entrada, `AppState`, banco SQLite e ponte com o world map.
- `efeitos`: camera, particulas, audio e VFX usados durante a luta.
- `torneio`: bracket, progresso e execucao automatizada de confrontos.
- `pipeline_video`: geracao e exportacao de videos a partir das lutas.
- `world_map_pygame`: subsistema externo integrado via `WorldBridge`, consumindo resultados para atualizar territorio e estado global.

## Resumo Mental do Sistema

Pense no projeto em tres camadas:

1. Operacao: launchers, UI e postos de execucao.
2. Runtime: `AppState` entrega dados, a simulacao cria `Lutador`, a IA decide e o loop Pygame resolve a luta.
3. Persistencia e integracao: resultados vao para SQLite e podem refletir no `world_map_pygame`.
