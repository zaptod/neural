# LOG — Feature: Sistema de World Events

## Data
2026-02-26

## Contexto
Campo `world_events` existia no world_state.json mas estava vazio e sem implementação.
Nenhum dado de evento era lido, exibido no mapa ou no painel. Os deuses antigos
(`ancient_gods` no gods.json) também não eram carregados nem acessíveis na UI.

---

## Arquivos criados

### `world_map_pygame/world_events.py` (NOVO)
Módulo central do sistema.

**`EventType` (Enum):**
- ZONE_CONQUERED, ZONE_LOST, ZONE_CONTESTED
- SEAL_CRACKED, SEAL_STIRRING, SEAL_AWAKENED, SEAL_BROKEN
- GOD_ASCENDED, ANCIENT_STIRS

**`WorldEvent` (dataclass):**
Campos: event_id, type, timestamp, description, severity, zone_id, god_id, ancient_id.

**`EVENT_VFX` (dict):**
Config visual por tipo: `color` (RGB) e `shape` ("diamond" | "circle" | "triangle" | "square").
Usado tanto no renderer (marcadores) quanto na UI (ícones no feed).

**`SEVERITY_COLOR` / `SEVERITY_LABEL`:**
Mapeamento de severidade → cor e label.
"low" → cinza, "medium" → dourado, "high" → laranja, "critical" → vermelho.

**`EventLog`:**
- Parseia `raw_events` do JSON.
- Se a lista estiver vazia, chama `_derive()` que gera eventos implícitos
  a partir de `zone_ownership`, `ancient_seals` e `ancient_gods`.
- Mantém índice `_by_zone` para consultas O(1).
- Métodos: `for_zone()`, `worst_for_zone()`, `has_event()`, `recent`, `critical_count`, `high_count`.

---

## Arquivos modificados

### `world_map_pygame/data_loader.py`

**`AncientGod` (novo dataclass):**
Carregado da seção `ancient_gods` do gods.json.
Campos: god_id, god_name, nature, color_primary, color_secondary,
seal_zone, crack_level, status, lore_description.
Método `to_dict()` para compatibilidade com EventLog.

**`load_data()` — assinatura expandida:**
```python
# ANTES
(zones, gods, ownership, ancient_seals, global_stats)

# DEPOIS
(zones, gods, ownership, ancient_seals, global_stats, event_log, ancient_gods)
```

Novo comportamento:
- Carrega `ancient_gods` da seção `ancient_gods` do gods.json.
- Sincroniza `crack_level` e `status` dos ancient_gods com `ancient_seals` do world_state.json.
- Constrói `EventLog` ao final e retorna junto.

---

### `world_map_pygame/renderer.py`

**`draw()` — novo parâmetro `event_log=None`:**
Retrocompatível (default None). Injeta `_draw_event_markers()` logo após o
ownership e antes dos selos.

**`_draw_event_markers(screen, event_log, t, clip)` (novo método):**
- Usa clip-sized surface (mesma otimização dos badges/selos).
- Para cada zona com evento, desenha o pior evento como marcador pequeno
  no canto superior-direito do centróide (offset: +14px, -14px).
- Zonas de selo são ignoradas (já têm ícone próprio).
- Shape e cor vêm de `EVENT_VFX[ev.type]`.
- Pulsação: critical (4.5Hz), high (2.5Hz), medium/low estático.
- Ponto central brilhante para critical e high.

---

### `world_map_pygame/ui.py`

**Imports adicionados:**
`AncientGod`, `EventLog`, `EventType`, `SEVERITY_COLOR`, `SEVERITY_LABEL`, `EVENT_VFX`.

**`draw_bottom_panel()` — novos parâmetros `event_log=None`, `ancient_gods=None`:**
Retrocompatível. Passa para os métodos de coluna.

**Fix: `_panel_content_h` agora é setado corretamente:**
```python
# ANTES — sempre 0, scroll nunca funcionava
self._panel_content_h = 0

# DEPOIS — retorno real dos métodos de coluna
self._panel_content_h = max(content_h, col2_h)
```

**`_draw_zone_info()` — retorna `int` (altura do conteúdo):**
Novas seções quando zone_id tem eventos:
- Lore do deus antigo associado (para zonas de selo).
- Seção "EVENTOS" com até 3 eventos da zona, cada um com ícone geométrico,
  acento colorido por severidade e descrição truncada.

**`_draw_events_panel()` — substitui `_draw_gods_stats()`:**
Layout da coluna 2:
1. Stats compactos em linha única (Zonas, Selos, Deuses).
2. Alerta visível se há eventos critical ou high.
3. Header "WORLD EVENTS" + feed de eventos recentes.
   Cada linha: ícone geométrico (shape de EVENT_VFX) + descrição + timestamp.
4. God cards compactos se sobrar espaço vertical.
Retorna altura total do conteúdo (usado pelo `_panel_content_h`).

**`draw_bottom_panel_with_gods()` — novos parâmetros `event_log=None`, `ancient_gods=None`:**
Passa para `draw_bottom_panel`.

---

### `world_map_pygame/main.py`

- Desempacota novo retorno de `load_data()` (7 valores).
- Reloader (`K_r`) idem.
- Passa `event_log=event_log` para `rend.draw()`.
- Passa `event_log=event_log, ancient_gods=ancient_gods` para `ui.draw_bottom_panel_with_gods()`.

---

### `world_map_pygame/data/world_state.json`

Campo `world_events` populado com 5 eventos reais do estado do mundo:
- evt_001: The God of Balance awakened (critical)
- evt_002: The God of Greed stirring (high)
- evt_003: The God of Balance seal cracks (high, causado por Caleb)
- evt_004: Nightmares from the Seal of Fear (medium)
- evt_005: Caleb claimed the Slum District (medium)

---

## Fluxo completo de dados

```
gods.json [ancient_gods] ──┐
world_state.json           ├──► load_data() ──► EventLog ──► renderer._draw_event_markers()
  [world_events]  ──────────┘                           └──► ui._draw_events_panel()
  [ancient_seals] ──────────────────────────────────────────► ui._draw_zone_info()
```

## Resultado visual

- **No mapa**: marcadores pulsantes no canto superior-direito de zonas com eventos.
  Triângulo vermelho = critical, losango laranja = high, quadrado dourado = medium.
- **No painel (coluna 2)**: feed "WORLD EVENTS" com ícone + descrição + timestamp.
  Alerta em vermelho se houver eventos critical/high.
- **Na zona selecionada (coluna 1)**: seção "EVENTOS" listando eventos locais.
  Para zonas de selo: lore do deus aprisionado exibido abaixo do status.
- **Scroll do painel**: fix de `_panel_content_h` faz o scroll funcionar corretamente.

## Retrocompatibilidade

Todos os parâmetros novos são opcionais com `default=None`.
`load_data()` é a única quebra de API — chamadores precisam desempacotar 7 valores.
