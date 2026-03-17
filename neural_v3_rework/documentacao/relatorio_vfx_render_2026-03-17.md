# Relatorio VFX e Render 2026-03-17

## Escopo auditado

- `efeitos/`
- `simulacao/sim_renderer.py`
- integrações com `simulacao/simulacao.py`
- acoplamento visual com `nucleo/lutador/weapons_mixin.py`

## Correcoes aplicadas nesta passada

1. Normalizacao de strings no renderer de armas.
   - O renderer comparava tipos, estilos e raridades com strings corrompidas.
   - Agora o fluxo usa comparacao normalizada, aceitando valores reais como `Épico`, `Mágica`, `Transformável`, `Adagas Gêmeas`, `Tentáculos Sombrios` e `Besta de Repetição`.

2. Fade real de trails e telegraphs.
   - `WeaponTrailEnhanced.draw()` calculava alpha, mas desenhava direto na tela sem surface alpha.
   - `AttackAnticipation.draw()` sofria o mesmo problema.
   - Ambos agora desenham em superfícies `SRCALPHA`, então o fade finalmente funciona como o código sugeria.

3. Regressao automatizada.
   - Novo teste em `tests/test_render_pipeline.py` cobrindo:
     - renderer com strings UTF-8 reais;
     - trail com alpha;
     - anticipation com alpha.

## Bugs confirmados ainda pendentes

### 1. Render mutando estado da simulacao

Arquivo: `simulacao/sim_renderer.py`

- O draw de beams ainda faz `self.particulas.append(...)`.
- Isso torna o VFX dependente de FPS e mistura gameplay/update com render.
- Sintoma esperado:
  - mais FPS = mais particulas;
  - pausas, slow motion ou render duplicado alteram a densidade do efeito.

### 2. Pipeline de animacao de arma parcialmente desligado

Arquivos:
- `nucleo/lutador/weapons_mixin.py`
- `efeitos/weapon_animations.py`
- `simulacao/sim_renderer.py`

- O runtime calcula `weapon_anim_scale` e `weapon_anim_shake`, mas o renderer nao consome `trail_positions`, `spark_list`, `draw_trails()` nem `draw_sparks()`.
- Na pratica, o sistema mais sofisticado de animacao existe, mas o visual final continua muito dependente do renderer manual gigante.

### 3. Mojibake ainda espalhado no codigo visual

Arquivos mais afetados:
- `simulacao/sim_renderer.py`
- `efeitos/weapon_animations.py`
- comentarios e textos em varios modulos de VFX

- Parte do problema ja nao quebra logica por causa da normalizacao aplicada, mas o codigo continua dificil de manter e propenso a regressao.

### 4. Acoplamento alto dos managers de VFX

Arquivos:
- `efeitos/movement.py`
- `efeitos/attack.py`

- Os managers assumem um `lutador` muito completo.
- Isso dificulta testes e reaproveitamento.
- Nao quebra runtime hoje, mas aumenta o custo de manutencao.

## Melhorias de direcao visual

### Armas

1. Definir silhuetas mais fortes por familia.
   - Hoje varias armas compartilham muito brilho e pouca identidade de forma.
   - Prioridade: `Reta`, `Dupla`, `Corrente`, `Orbital`, `Mágica`, `Transformável`.

2. Reduzir glow constante.
   - O visual atual usa glow em muitos estados passivos.
   - Isso lava a leitura e deixa tudo com a mesma “temperatura”.
   - Glow forte deveria ser reservado para:
     - ataque;
     - cast;
     - parry/clash;
     - raridades altas em pontos focais.

3. Criar materiais visuais claros.
   - Metal, madeira, osso, cristal, energia, sombra.
   - Hoje o renderer usa muita variação de linha e pouco material consistente.

### Habilidades

1. Separar linguagem visual por escola.
   - Fogo: massa, calor, turbulencia, laranja profundo.
   - Gelo: corte limpo, shards, bloom curto, azul pálido.
   - Raio: frames mais secos, strobe curto, ramificacoes finas.
   - Trevas: volumes opacos, edge light roxo/azulado, movimento viscoso.
   - Luz: bloom controlado, halos duros, geometria ritual.

2. Melhorar telegraph.
   - Muitas skills vao direto para o impacto.
   - Falta etapa curta e legivel de “arming”:
     - charge ring;
     - runa;
     - linha guia;
     - contra-luz no caster.

3. Adotar timing em 3 fases.
   - antecipacao;
   - impacto;
   - dissipacao.
   - O projeto ja tem varias pecas para isso, mas o uso ainda e irregular.

### Design geral

1. Escolher uma biblia visual unica.
   - Hoje o projeto mistura arena arcade, VFX anime, HUD de prototipo e armas semi-cartunescas.
   - Sugestao de direcao:
     - “arena tática estilizada”;
     - materiais sólidos;
     - VFX fortes só nos picos;
     - menos neon permanente.

2. Rebalancear contraste.
   - Fundos escuros + muitos efeitos claros + outline forte fazem tudo competir.
   - Personagem e arma precisam ser legiveis primeiro.

3. Trocar quantidade por hierarquia.
   - Menos particulas pequenas.
   - Mais 1 ou 2 formas dominantes por ação.

## Proxima etapa recomendada

1. Mover spawn de particulas de beam para `update`.
2. Ligar de fato `weapon_animations.py` ao renderer.
3. Limpar mojibake dos modulos visuais.
4. Fazer uma passada de arte por familia de arma, começando por:
   - `Dupla`
   - `Corrente`
   - `Mágica`
   - `Transformável`
