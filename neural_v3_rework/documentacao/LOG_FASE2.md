# LOG — Fase 2: Renderer Melhorado

## Arquivo modificado
- `renderer.py` — reescrito completamente

---

## Mudanças

### 1. smoothscale — qualidade no zoom
```python
# Antes
scaled = pygame.transform.scale(chunk, (dw, dh))       # nearest-neighbor, pixelado

# Depois
scaled_surf = pygame.transform.smoothscale(chunk, (dw, dh))  # bilinear, suave
```
Combinado com a textura 2048×1434 da Fase 1, o zoom alto agora é nítido.

### 2. Labels — serif, maiores, visíveis desde zoom 0.30
```python
# Antes: Consolas, zoom >= 0.42, tamanho fixo 8–14px
# Depois: Georgia/serif, zoom >= 0.30, tamanho escalado por UI_SCALE
fsz  = max(scaled(9), min(scaled(20), int(scaled(14) * cam.zoom)))
font = self._lf(fsz, serif=True)
```
Sombra dupla (preta offset 2px + sépia offset 1px) garante legibilidade sobre qualquer cor de terreno.
Sub-label de natureza em itálico aparece a partir de zoom 0.55.

### 3. Hover espesso dourado
```python
# Antes: borda 1.5px branca, fill alpha=18 — quase invisível
# Depois: glow 9px alpha=55 + borda 5px alpha=200 + fill alpha=22
```
Três camadas: fill suave → glow externo largo → borda principal fina e definida.

### 4. Ícone de Selo Antigo (procedural)
Símbolo rúnico desenhado em `_draw_seal_icons`:
- Círculo externo (aura pulsante)
- Círculo interno com borda
- 2 linhas diagonais cruzadas em X
- Ponto central brilhante

Velocidade de pulso por status: sleeping=lento, stirring=médio, awakened=rápido, broken=parado.
Visível a partir de `zoom >= 0.40`.

### 5. Indicador de Dono (badge com iniciais)
`_draw_owner_badges` desenha um círculo colorido logo abaixo do label:
- Fill na cor primária do deus (alpha=160)
- Borda dourada fina
- Iniciais do nome (até 2 letras)

Visível entre `zoom 0.35` e `zoom 2.0`.

### 6. Rosa dos ventos — paleta dourada
Cores do compasso atualizadas para o tema dourado (era misto de dourado e cinza).

### 7. Borda pulsante — dourada (era cyan)
```python
# Antes: (0, p//2, p) — azul/cyan pulsante
# Depois: gold_pulse = (p, int(p*0.83), int(p*0.38)) — dourado pulsante
```

---

## Cache de fontes atualizado
`_lf(size, serif=True/False)` agora aceita dois tipos:
- `serif=True` → `georgia, times new roman, serif` (labels do mapa)
- `serif=False` → `consolas` (dados numéricos do HUD)

---

## Próximo passo: Fase 3 — ui.py
- Remover painel lateral e HUD de topo antigos
- Barra de filtros (topo, sempre visível)
- Painel inferior com slide-in/out ao selecionar zona
- Info da zona + deuses + stats + minimap
- Tipografia serif + bordas ornamentais douradas
