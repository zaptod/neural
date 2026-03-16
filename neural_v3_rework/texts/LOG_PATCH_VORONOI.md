# LOG — Patch: Overlays alinhados ao Voronoi

## Problema
Os `zone.vertices` no JSON são simples retângulos de 4 pontos.
O mapa real usa fronteiras geradas por Voronoi warpado (`territories.py`).
Resultado: as cores de ownership, hover e seleção apareciam como
retângulos que não se encaixavam nas bordas orgânicas do terreno.

## Solução
Todos os overlays agora usam `zone_idx` (bitmap Voronoi, shape `TEX_H × TEX_W`)
em vez de `zone.vertices`. A textura resultante é escalada exatamente
como o terreno, garantindo alinhamento perfeito.

## O que mudou

### _build_ownership_texture (novo)
Constrói uma Surface RGBA (TEX_W × TEX_H) via numpy:
- Pixels de zonas com dono: cor do deus, alpha=52
- Fronteiras entre zonas com donos diferentes: alpha=180 (borda visível)
- Cacheada por hash do ownership — só reconstrói quando os dados mudam

### _draw_ownership (reescrito)
Usa `_build_ownership_texture` e escala+blit como o terreno (mesma lógica de viewport).

### _draw_zone_overlay_indexed (novo)
Overlay de zona individual (hover, seleção) via `zone_idx`:
- Fill: pixels da zona com fill_col
- Borda: erosion/dilation do mask da zona, com border_col
- Escala e blit no viewport atual

### Hover e Seleção
Agora chamam `_draw_zone_overlay_indexed` em vez de `_draw_poly_overlay`.

### _draw_filter_overlay (reescrito)
Mesma abordagem: constrói numpy array com dark overlay apenas nas
zonas fora do filtro, escala e blit no viewport atual.

## Resultado
Ownership, hover, seleção e filtro agora se encaixam perfeitamente
nas fronteiras orgânicas do Voronoi — sem nenhum retângulo aparente.
