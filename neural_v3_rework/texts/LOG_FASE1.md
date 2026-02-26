# LOG — Fase 1: Infraestrutura e Correção de Bugs

## Arquivos modificados
- `config.py` — paleta + resolução + UI_SCALE + constantes de layout
- `camera.py` — bug de clique corrigido
- `terrain.py` — paleta do terreno atualizada

---

## config.py

### Bug corrigido: MAP_Y_OFFSET removido
`MAP_Y_OFFSET = 40` estava hardcoded neste arquivo e em `renderer.py` sem comunicação.
Removido. A câmera agora recebe `map_y` dinamicamente.

### TEX_W/H: 1024×717 → 2048×1434
Dobrar a resolução da textura base elimina o pixelado ao usar zoom alto.
O `renderer.py` (Fase 2) vai usar `smoothscale` para aproveitar essa resolução.

### UI_SCALE
```python
UI_SCALE = max(0.7, min(2.0, SCREEN_H / 900.0))
```
Calculado em runtime. Na tela de teste (720px de altura): `UI_SCALE = 0.80`.
Todos os tamanhos de fonte e medidas de UI devem usar `scaled(n)` em vez de `n`.

### Novo layout
```python
FILTER_BAR_H   = scaled(36)   # barra de filtros (topo)
BOTTOM_PANEL_H = scaled(180)  # painel inferior (slide-in ao selecionar zona)
```

### Paleta — antes vs depois
| Elemento       | Antes                 | Depois               |
|----------------|-----------------------|----------------------|
| Terra baixa    | `(232, 244, 253)` azul | `(210, 195, 162)` pergaminho |
| Terra alta     | `(217, 236, 251)` azul | `(185, 168, 135)` pergaminho escuro |
| Oceano fundo   | `(85, 115, 170)`       | `(48, 62, 92)` azul-noite sépia |
| Destaque UI    | CYAN `(0, 217, 255)`   | GOLD `(210, 175, 80)` dourado |
| Fundo UI       | `(6, 12, 28)` azul-preto | `(18, 14, 10)` preto-sépia |
| Fronteiras     | `(170, 200, 226)` azul | `(155, 138, 108)` sépia |

---

## camera.py

### Bug de clique — causa raiz e correção

**Antes:**
```python
MAP_Y_OFFSET = 40  # hardcoded, sem comunicação com a UI

def s2w(self, sx, sy):
    return (
        (sx - self.map_x) / self.zoom + self.offset_x,
        (sy - self.map_y) / self.zoom + self.offset_y,  # ← usava MAP_Y_OFFSET
    )
```

**Depois:**
```python
def __init__(self, map_x, map_w, map_y=0):  # map_y recebido como parâmetro
    self.map_y = map_y  # atualizado dinamicamente pelo main loop

def s2w(self, sx, sy):
    return (
        (sx - self.map_x) / self.zoom + self.offset_x,
        (sy - self.map_y) / self.zoom + self.offset_y,  # usa valor real
    )
```

**Impacto:** `zoom_at` também corrigido — usava `self.map_y` implicitamente no mesmo ponto.

**Como manter dinâmico no main loop:**
```python
# Em main.py — adicionar na atualização do loop:
cam.map_x = 0           # mapa começa na borda esquerda agora
cam.map_y = ui.map_y    # barra de filtros é o único offset vertical
cam.map_w = SCREEN_W
```

---

## terrain.py

### Paleta atualizada
- `C_LAND`: `(232, 244, 253)` → `(210, 195, 162)` — pergaminho quente
- `C_LAND_HI`: `(217, 236, 251)` → `(185, 168, 135)` — pergaminho escuro
- `C_RIVER`: `(148, 190, 225)` → `(110, 130, 155)` — azul-sépia suave
- `C_BORDER`: `(170, 200, 226)` → `(155, 138, 108)` — sépia médio

### Ruído de textura
Adicionado pontilhado duplo (claro + escuro) para imitar fibra de papel envelhecido:
```python
dots_dark  = land_mask & (noise < 0.018)   # era 0.014, só escuro
dots_light = land_mask & (noise > 0.984)   # novo: pontos claros
```

---

## Validação
```
SCREEN_W/H:     1280 x 720
UI_SCALE:       0.800
TEX_W/H:        2048 x 1434  ✓
FILTER_BAR_H:   28px          ✓
BOTTOM_PANEL_H: 144px         ✓
GOLD:           (210, 175, 80) ✓
Round-trip s2w→w2s: OK        ✓ (bug de clique corrigido)
```

---

## Próximo passo: Fase 2 — renderer.py
- Substituir `scale` por `smoothscale` (qualidade no zoom)
- Remover `MAP_Y_OFFSET` hardcoded do renderer
- Labels maiores com fonte serif
- Hover de fronteira espesso e dourado
- Ícones de selo antigo nos centroides
- Indicadores visuais de dono (círculo com inicial)
