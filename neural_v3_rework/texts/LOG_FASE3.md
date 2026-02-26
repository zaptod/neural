# LOG — Fase 3: Nova UI

## Arquivos modificados
- `ui.py` — reescrito completamente
- `main.py` — atualizado para nova arquitetura

---

## Novo Layout

```
┌──────────────────────────────────────────────────────────┐
│  ⚔ AETHERMOOR  [TODOS][fire][arcane]...  Zonas:1/27 FPS  │  ← filter bar (sempre visível)
├──────────────────────────────────────────────────────────┤
│                                                          │
│                    MAPA FULL-WIDTH                       │  ← sem painel lateral
│                                                          │
├──────────────────────────────────────────────────────────┤
│  Nome da Zona (grande serif)  │  Deuses  │  [MINIMAP]   │  ← painel slide-in
│  Região · Natureza            │  Stats   │              │
│  Lore...                      │          │              │
│  Status de posse              │          │              │
└──────────────────────────────────────────────────────────┘
```

---

## ui.py — O que é novo

### draw_filter_bar (substitui draw_top_hud)
Barra fina no topo com:
- Título "⚔ AETHERMOOR" em serif dourado
- Botão [TODOS] + botão por natureza disponível no mundo, coloridos
- Botão ativo tem fundo colorido + borda
- Info direita: zonas, zoom, FPS

### draw_bottom_panel_with_gods (substitui draw_left_panel + draw_seals_panel)
Painel que desliza de baixo ao selecionar uma zona (animação `ease-out ~14x/s`).
Três colunas:
1. **Info da zona**: nome grande serif dourado, região·natureza colorida, lore, status de posse/selo
2. **Deuses + Stats**: contador de zonas/selos/deuses + cards de cada deus com barra de território
3. **Minimap**: visão reduzida do mundo com cores de ownership, cacheado (só rebuilda quando dirty)

### handle_filter_click / handle_minimap_click
Novos métodos que o main.py chama antes de processar o mapa, para capturar cliques nos controles de UI.

### open_panel(zone) / mark_minimap_dirty()
Controle de estado explícito — main.py chama ao selecionar zona ou recarregar dados.

### _draw_ornate_border
Borda dourada com ornamentos nos quatro cantos (linhas em L mais brilhantes).
Usada no painel inferior, tooltip, notificação e loading.

### UI_SCALE em toda tipografia
Todas as fontes agora usam `scaled(n)` — texto legível em qualquer resolução.
Georgia/serif como fonte primária dos labels e informações.

---

## main.py — O que mudou

### Ordem de tratamento de eventos (nova prioridade)
```
1. Clique na filter bar (my < HUD_H)
2. Clique no minimap
3. Scroll no painel inferior
4. Interação com o mapa
```

### Tecla ESC
Agora fecha o painel antes de fechar o jogo.
Primeiro ESC: fecha seleção. Segundo ESC: sai.

### Ordem de render
```python
rend.draw(...)                    # mapa
part.draw(...)                    # partículas
ui.draw_filter_bar(...)           # barra de filtros (topo)
ui.draw_bottom_panel_with_gods(.) # painel inferior
ui.draw_hover_tooltip(...)        # tooltip
ui.draw_notif(...)                # notificação
ui.draw_corners(...)              # cantos dourados
```

### Fundo da tela
`(6, 12, 28)` → `(18, 14, 10)` — preto-sépia consistente com nova paleta

---

## Comportamento do painel

- **Abre**: ao clicar em qualquer zona no mapa (`ui.open_panel(zone)`)
- **Fecha**: clique direito, tecla ESC, ou `H` para home
- **Animação**: interpolação linear com velocidade 14×/dt (suave ~100ms)
- **Minimap cache**: reconstruído apenas quando `mark_minimap_dirty()` é chamado (ao reload de dados)

---

## Nota sobre active_filter
`ui.active_filter` (string: "all" | nome da natureza) está exposto e atualizado pelos cliques na filter bar. O renderer ainda não o usa para escurecer zonas fora do filtro — isso é Fase 4 (polish/integração final).
