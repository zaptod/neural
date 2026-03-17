# LOG â€” Feature: Sistema de World Events

## Data
2026-02-26

## Contexto
Campo `world_events` existia no world_state.json mas estava vazio e sem implementaÃ§Ã£o.
Nenhum dado de evento era lido, exibido no mapa ou no painel. Os deuses antigos
(`ancient_gods` no gods.json) tambÃ©m nÃ£o eram carregados nem acessÃ­veis na UI.

---

## Arquivos criados

### `world_map_pygame/world_events.py` (NOVO)
MÃ³dulo central do sistema.

**`EventType` (Enum):**
- ZONE_CONQUERED, ZONE_LOST, ZONE_CONTESTED
- SEAL_CRACKED, SEAL_STIRRING, SEAL_AWAKENED, SEAL_BROKEN
- GOD_ASCENDED, ANCIENT_STIRS

**`WorldEvent` (dataclass):**
Campos: event_id, type, timestamp, description, severity, zone_id, god_id, ancient_id.

**`EVENT_VFX` (dict):**
Config visual por tipo: `color` (RGB) e `shape` ("diamond" | "circle" | "triangle" | "square").
Usado tanto no renderer (marcadores) quanto na UI (Ã­cones no feed).

**`SEVERITY_COLOR` / `SEVERITY_LABEL`:**
Mapeamento de severidade â†’ cor e label.
"low" â†’ cinza, "medium" â†’ dourado, "high" â†’ laranja, "critical" â†’ vermelho.

**`EventLog`:**
- Parseia `raw_events` do JSON.
- Se a lista estiver vazia, chama `_derive()` que gera eventos implÃ­citos
  a partir de `zone_ownership`, `ancient_seals` e `ancient_gods`.
- MantÃ©m Ã­ndice `_by_zone` para consultas O(1).
- MÃ©todos: `for_zone()`, `worst_for_zone()`, `has_event()`, `recent`, `critical_count`, `high_count`.

---

## Arquivos modificados

### `world_map_pygame/data_loader.py`

**`AncientGod` (novo dataclass):**
Carregado da seÃ§Ã£o `ancient_gods` do gods.json.
Campos: god_id, god_name, nature, color_primary, color_secondary,
seal_zone, crack_level, status, lore_description.
MÃ©todo `to_dict()` para compatibilidade com EventLog.

**`load_data()` â€” assinatura expandida:**
```python
# ANTES
(zones, gods, ownership, ancient_seals, global_stats)

# DEPOIS
(zones, gods, ownership, ancient_seals, global_stats, event_log, ancient_gods)
```

Novo comportamento:
- Carrega `ancient_gods` da seÃ§Ã£o `ancient_gods` do gods.json.
- Sincroniza `crack_level` e `status` dos ancient_gods com `ancient_seals` do world_state.json.
- ConstrÃ³i `EventLog` ao final e retorna junto.

---

### `world_map_pygame/renderer.py`

**`draw()` â€” novo parÃ¢metro `event_log=None`:**
RetrocompatÃ­vel (default None). Injeta `_draw_event_markers()` logo apÃ³s o
ownership e antes dos selos.

**`_draw_event_markers(screen, event_log, t, clip)` (novo mÃ©todo):**
- Usa clip-sized surface (mesma otimizaÃ§Ã£o dos badges/selos).
- Para cada zona com evento, desenha o pior evento como marcador pequeno
  no canto superior-direito do centrÃ³ide (offset: +14px, -14px).
- Zonas de selo sÃ£o ignoradas (jÃ¡ tÃªm Ã­cone prÃ³prio).
- Shape e cor vÃªm de `EVENT_VFX[ev.type]`.
- PulsaÃ§Ã£o: critical (4.5Hz), high (2.5Hz), medium/low estÃ¡tico.
- Ponto central brilhante para critical e high.

---

### `world_map_pygame/ui.py`

**Imports adicionados:**
`AncientGod`, `EventLog`, `EventType`, `SEVERITY_COLOR`, `SEVERITY_LABEL`, `EVENT_VFX`.

**`draw_bottom_panel()` â€” novos parÃ¢metros `event_log=None`, `ancient_gods=None`:**
RetrocompatÃ­vel. Passa para os mÃ©todos de coluna.

**Fix: `_panel_content_h` agora Ã© setado corretamente:**
```python
# ANTES â€” sempre 0, scroll nunca funcionava
self._panel_content_h = 0

# DEPOIS â€” retorno real dos mÃ©todos de coluna
self._panel_content_h = max(content_h, col2_h)
```

**`_draw_zone_info()` â€” retorna `int` (altura do conteÃºdo):**
Novas seÃ§Ãµes quando zone_id tem eventos:
- Lore do deus antigo associado (para zonas de selo).
- SeÃ§Ã£o "EVENTOS" com atÃ© 3 eventos da zona, cada um com Ã­cone geomÃ©trico,
  acento colorido por severidade e descriÃ§Ã£o truncada.

**`_draw_events_panel()` â€” substitui `_draw_gods_stats()`:**
Layout da coluna 2:
1. Stats compactos em linha Ãºnica (Zonas, Selos, Deuses).
2. Alerta visÃ­vel se hÃ¡ eventos critical ou high.
3. Header "WORLD EVENTS" + feed de eventos recentes.
   Cada linha: Ã­cone geomÃ©trico (shape de EVENT_VFX) + descriÃ§Ã£o + timestamp.
4. God cards compactos se sobrar espaÃ§o vertical.
Retorna altura total do conteÃºdo (usado pelo `_panel_content_h`).

**`draw_bottom_panel_with_gods()` â€” novos parÃ¢metros `event_log=None`, `ancient_gods=None`:**
Passa para `draw_bottom_panel`.

---

### `world_map_pygame/main.py`

- Desempacota novo retorno de `load_data()` (7 valores).
- Reloader (`K_r`) idem.
- Passa `event_log=event_log` para `rend.draw()`.
- Passa `event_log=event_log, ancient_gods=ancient_gods` para `ui.draw_bottom_panel_with_gods()`.

---

### `world_map_pygame/dados/world_state.json`

Campo `world_events` populado com 5 eventos reais do estado do mundo:
- evt_001: The God of Balance awakened (critical)
- evt_002: The God of Greed stirring (high)
- evt_003: The God of Balance seal cracks (high, causado por Caleb)
- evt_004: Nightmares from the Seal of Fear (medium)
- evt_005: Caleb claimed the Slum District (medium)

---

## Fluxo completo de dados

```
gods.json [ancient_gods] â”€â”€â”
world_state.json           â”œâ”€â”€â–º load_data() â”€â”€â–º EventLog â”€â”€â–º renderer._draw_event_markers()
  [world_events]  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                           â””â”€â”€â–º ui._draw_events_panel()
  [ancient_seals] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º ui._draw_zone_info()
```

## Resultado visual

- **No mapa**: marcadores pulsantes no canto superior-direito de zonas com eventos.
  TriÃ¢ngulo vermelho = critical, losango laranja = high, quadrado dourado = medium.
- **No painel (coluna 2)**: feed "WORLD EVENTS" com Ã­cone + descriÃ§Ã£o + timestamp.
  Alerta em vermelho se houver eventos critical/high.
- **Na zona selecionada (coluna 1)**: seÃ§Ã£o "EVENTOS" listando eventos locais.
  Para zonas de selo: lore do deus aprisionado exibido abaixo do status.
- **Scroll do painel**: fix de `_panel_content_h` faz o scroll funcionar corretamente.

## Retrocompatibilidade

Todos os parÃ¢metros novos sÃ£o opcionais com `default=None`.
`load_data()` Ã© a Ãºnica quebra de API â€” chamadores precisam desempacotar 7 valores.

