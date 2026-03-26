# Postos Operacionais

O projeto agora fica organizado em 3 postos principais:

Todos eles agora usam a arvore padrao:

```text
saidas/
├── headless/
│   ├── logs/
│   └── relatorios/
├── simulacao/
│   └── sessoes/
└── pipeline/
    ├── output/
    ├── frames/
    └── portraits/
```

## 1. Posto Headless

Serve para coleta rapida de informacao, stress, auditoria e balanceamento sem abrir janela.

Comandos:

```bash
python run_posto_headless.py --mode rapido
python run_posto_headless.py --mode stress --stress-count 25
python run_postos.py headless --mode classes
python run_postos.py headless --tatico --modo 1v1 --template duelo_papeis_basicos --runs 3
python run_postos.py headless --tatico --modo grupo_vs_grupo --template esquadrao_balanceado_3v3 --runs 2
python run_postos.py headless --tatico --modo grupo_vs_horda --template corredor_contra_horda --runs 2
```

Uso recomendado:
- medir estabilidade
- comparar pacing
- coletar dados em lote
- validar balanceamento depois de mudancas
- testar pacotes taticos por papel

Saidas principais:
- `saidas/headless/logs/<timestamp>/sessao.json`
- `saidas/headless/logs/<timestamp>/exec.log`
- `saidas/headless/logs/<timestamp>/relatorio_execucao.json`
- `saidas/headless/logs/<timestamp>/headless_resumo.json`
- `saidas/headless/logs/<timestamp>/harness_tatico_resumo.json`
- `saidas/headless/relatorios/harness_tatico_*.json`

Harness tatico:
- usa [templates_composicao_tatica.json](/abs/path/c:/Users/birul/Desktop/new/neural/neural_v3_rework/dados/templates_composicao_tatica.json)
- escolhe personagens reais do roster por papel tatico
- roda combate real em modo dummy para `1v1`, `grupo_vs_grupo` e `grupo_vs_horda`
- gera metricas comparaveis por time, papel e template
- quando roda varios templates no mesmo modo, gera `comparativo` com ranking de saude, alertas mais comuns, templates criticos e impacto medio por papel
- o `comparativo` agora tambem gera `recomendacoes_balanceamento`, apontando eixos provaveis de ajuste como burst, sustain, frontline de horda, papel dominante e familia de arma dominante
- cada template no comparativo agora tambem recebe um `plano_ajuste` separado por area (`arma`, `skill`, `papel`, `ia`, `composicao`) para guiar a iteracao do balanceamento

## 2. Posto de Simulacao Completa

Serve para olhar a luta, sentir pacing, perceber bugs visuais, rir, inspecionar IA e VFX.

Comandos:

```bash
python run_posto_simulacao.py --modo launcher
python run_posto_simulacao.py --modo sim
python run_posto_simulacao.py --modo manual
python run_postos.py simulacao --modo launcher
```

Modos:
- `launcher`: abre a UI principal
- `sim`: entra na simulacao automatizada
- `manual`: abre o modo de teste manual

## 3. Posto de Pipeline de Videos

Serve para gerar material pronto para postagem usando o pipeline ja ativo.

Comandos:

```bash
python run_posto_pipeline.py --fights 1
python run_posto_pipeline.py --video-format comment_roulette --comment "Eu serei Deus de outro mundo"
python run_postos.py pipeline --fights 2 --generation-mode hybrid
```

Uso recomendado:
- gerar batch curto para postagem
- testar copy e roleta por comentario
- validar overlays e metadata

## Hub unico

Se quiser usar um so ponto de entrada:

```bash
python run_postos.py headless --mode rapido
python run_postos.py headless --tatico --modo 1v1 --template duelo_papeis_basicos --runs 3
python run_postos.py simulacao --modo launcher
python run_postos.py pipeline --fights 1
```

## Estrategia de uso

Fluxo recomendado no dia a dia:

1. `headless` para medir rapidamente
2. `simulacao` para assistir e confirmar comportamento real
3. `pipeline` para transformar o que ja esta bom em conteudo
