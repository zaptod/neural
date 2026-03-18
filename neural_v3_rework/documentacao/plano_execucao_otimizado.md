# Plano de Execução Otimizado

Este plano organiza o trabalho principal do projeto em uma sequência que reduz retrabalho e acelera iteração.

## Objetivo central

Construir um ecossistema em que:
- a luta é divertida de assistir
- a IA parece viva
- o balanceamento é mensurável
- o projeto serve para vídeo, simulação visual e coleta headless
- o mesmo núcleo suporta `1v1`, `grupo vs grupo` e `grupo vs horda`

## Regra de operação

Toda feature relevante deve passar por 3 postos:

1. `Posto Headless`
Valida estabilidade, pacing e métricas.

2. `Posto de Simulação Completa`
Valida legibilidade, diversão, VFX, bugs de timing e comportamento emergente.

3. `Posto de Pipeline`
Valida se o resultado final gera conteúdo bom e legível para postagem.

## Ordem ótima de trabalho

### Fase 1. Infra operacional

Objetivo:
- garantir que os 3 postos existam, tenham saídas previsíveis e gerem sessão rastreável

Checklist:
- hub `run_postos.py`
- saídas padronizadas em `saidas/`
- manifesto por sessão
- relatório consolidado do posto headless

Teste obrigatório:
- `python run_postos.py --help`
- `python run_postos.py headless --mode rapido`
- `python run_postos.py simulacao --modo launcher`
- `python run_postos.py pipeline --fights 1`

### Fase 2. Pacotes táticos

Objetivo:
- sair de balanceamento por personagem solto e passar para blocos reutilizáveis

Blocos oficiais:
- papel tático
- personalidade
- família de arma
- classe de magia

Teste obrigatório:
- verificar cada papel em `1v1`
- verificar composição básica em `grupo vs grupo`
- verificar sustain/limpeza em `grupo vs horda`

### Fase 3. Harness de validação

Objetivo:
- medir o sistema sem depender de feeling

Métricas base:
- win rate
- tempo médio de luta
- dano por fonte
- cura e escudo
- sobrevivência por papel
- uso de skill
- pressão de mapa
- eficiência contra horda

Teste obrigatório:
- seeds múltiplas
- relatório único por sessão
- comparação entre runs

### Fase 4. Balanceamento estrutural

Objetivo:
- ajustar primeiro o papel, depois o pacote e só então o número fino

Ordem:
1. armas
2. skills
3. personalidades
4. pacotes táticos
5. composições

Teste obrigatório:
- headless antes/depois
- simulação visual de amostra
- checagem de conteúdo no pipeline

### Fase 5. Missões e hordas

Objetivo:
- preparar o jogo para além de duelo

Modos:
- `1v1`
- `grupo vs grupo`
- `grupo vs horda`

Expansão futura:
- dungeon room
- defesa de objetivo
- escolta
- chefe + adds

Teste obrigatório:
- sobrevivência por função
- valor de defensor e curandeiro
- legibilidade do caos em tela

## Loop de execução

Para cada feature:

1. implementar
2. rodar `headless`
3. assistir no posto de `simulação`
4. validar no `pipeline`
5. registrar observações
6. corrigir
7. repetir

## Prioridades reais agora

### Prioridade A
- consolidar o posto headless
- montar relatório por sessão
- transformar métricas em base de decisão

### Prioridade B
- criar templates de composição por papel
- rodar baterias `1v1`, `grupo vs grupo`, `grupo vs horda`

### Prioridade C
- rebalancear com base em pacote
- revisar pacing e sustain
- manter luta emocionante

### Prioridade D
- transformar resultados bons em vídeos rápidos no pipeline

## Regra para economizar tempo

Não balancear 500 personagens individualmente.

Balancear:
- famílias de arma
- famílias de skill
- personalidades-base
- papéis táticos
- templates de composição

Os personagens finais devem ser derivados desses blocos.

## Critério de pronto

Uma feature só é considerada pronta quando:
- passa no headless
- faz sentido na simulação visual
- não fica ruim no pipeline
- deixa log ou relatório útil para comparação futura
