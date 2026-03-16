# LOG — Patch: Performance fix renderer.py (world_map_pygame)

## Data
2026-02-26

## Contexto
Após o patch "Overlays alinhados ao Voronoi" (LOG_PATCH_VORONOI.md), a visualização
de mundo ficou com lag severo. As causas estavam todas em `renderer.py`.

---

## Causas identificadas

### 🔴 CRÍTICO — `_draw_zone_overlay_indexed` (hover / seleção)
`binary_erosion` + `binary_dilation` (scipy) rodavam **a cada frame** sobre a textura
inteira (2048×1434 px) para cada zona em hover ou selecionada.
Custo estimado: 20–80 ms por zona por frame.

### 🟠 ALTO — `_draw_filter_overlay` (filtro de natureza)
Reconstruía o surfarray completo todo frame, mesmo sem mudança de filtro.
Continha também um **bug de NameError** (`dark` referenciado antes de ser criado —
o código tinha um loop morto antes do loop correto, resquício de iteração anterior).

### 🟡 MÉDIO — `_draw_seal_icons` e `_draw_owner_badges`
Alocavam `Surface(SCREEN_W, SCREEN_H, SRCALPHA)` a cada frame (~3.7 MB cada),
mesmo com apenas 3–5 elementos visíveis dentro do clip.

### 🟢 MENOR — Imports dentro de métodos
`import numpy as np` e `from scipy.ndimage import binary_erosion, binary_dilation`
executavam dentro dos métodos a cada chamada. Impacto pequeno mas desnecessário.

---

## Correções aplicadas

### `_draw_zone_overlay_indexed`
- Adicionado cache `self._mask_cache: Dict[(zone_i, border_w), (mask_t, border_t)]`
- `binary_erosion` / `binary_dilation` agora rodam **uma única vez** por zona,
  na primeira vez que ela é hovereada ou selecionada.
- Frames seguintes apenas reutilizam as máscaras já calculadas (operação O(1)).

### `_draw_filter_overlay`
- Adicionado cache `self._filter_surf` com chave `(active_filter, sel_id)`.
- Overlay só é reconstruído quando filtro ativo ou zona selecionada mudam.
- Removido loop morto com variável `dark` não definida (bug corrigido).
- `surf` local substituído por `self._filter_surf` no blit final.

### `_draw_seal_icons` e `_draw_owner_badges`
- Surface reduzida de `(SCREEN_W, SCREEN_H)` para `(clip.width, clip.height)`.
- Coordenadas de draw convertidas para espaço local da surf com offset `(ox, oy)`.
- Blit atualizado: `screen.blit(surf, clip.topleft)` em vez de `(0, 0)`.

### Imports
- `import numpy as np` movido para o topo do arquivo.
- `from scipy.ndimage import binary_erosion, binary_dilation` movido para o topo.
- Tipo `Tuple` adicionado ao import de `typing`.

---

## Arquivos modificados
- `world_map_pygame/renderer.py`

## Arquivos não modificados
Nenhuma outra parte do projeto foi tocada. A interface pública de `MapRenderer`
permanece idêntica — nenhum caller precisa ser atualizado.

---

## Resultado esperado
- Hover e seleção de zona: sem spike de CPU após o primeiro hover de cada zona.
- Filtro de natureza: sem rebuild de surfarray por frame.
- Selos e badges: alocação de memória ~4× menor por frame.
