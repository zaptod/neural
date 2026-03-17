# LOG — Fase 4: Integração e Polish

## Arquivos modificados
- `renderer.py` — filtro de natureza + map_h dinâmico
- `main.py` — passagem de active_filter e map_h para o renderer

---

## renderer.py

### Overlay de filtro (_draw_filter_overlay)
Quando `active_filter != "all"`, todas as zonas fora da natureza filtrada
recebem um overlay escuro `(12, 8, 4, alpha=165)` — suficientemente opaco
para destacar as zonas filtradas sem apagar completamente o terreno.

A zona atualmente **selecionada nunca é escurecida**, para não confundir
o jogador que está vendo os detalhes dela no painel inferior.

```python
# Em draw():
if active_filter != "all":
    self._draw_filter_overlay(screen, active_filter, selected_zone, clip)
```

### Assinatura de draw() atualizada
```python
def draw(self, screen, ownership, selected_zone, hover_zone,
         ancient_seals, t, map_x, map_w,
         active_filter="all",   # novo
         map_h=0):              # novo
```

`map_h=0` usa fallback de `SCREEN_H - map_y` quando não passado — mantém
compatibilidade retroativa com qualquer código que chame sem esses params.

### map_h dinâmico
O renderer agora respeita `ui.map_h`, que desconta a altura do painel
inferior quando ele está aberto. Efeito prático: a **rosa dos ventos
nunca fica atrás do painel inferior**.

---

## main.py

### active_filter propagado
```python
rend.draw(screen, ownership, selected_zone, hover_zone,
          ancient_seals, t_anim, ui.map_x, ui.map_w,
          active_filter=ui.active_filter,   # novo
          map_h=ui.map_h)                   # novo
```

### cam.map_w sempre full-width
```python
cam.map_w = config.SCREEN_W   # era ui.map_w (mesmo valor, mas mais explícito)
```

---

## Resumo de todas as fases

| Fase | Arquivos | O que resolveu |
|------|----------|----------------|
| 1 | config, camera, terrain | Paleta sépia, TEX 2×, UI_SCALE, MAP_Y_OFFSET eliminado da câmera |
| 1 (patch) | ui, main, renderer | Bug de clique: MAP_Y_OFFSET hardcoded eliminado de todos os pontos |
| 2 | renderer | smoothscale, labels serif, hover dourado, ícones de selo, badges de dono |
| 3 | ui, main | Layout completo: filter bar, painel inferior, minimap, tipografia |
| 4 | renderer, main | Filtro funcional, rosa dos ventos respeita painel, polish final |
