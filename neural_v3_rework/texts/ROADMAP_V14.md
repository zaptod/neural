# NEURAL FIGHTS — Roadmap v14.0 "Polimento & Fundações"

> **Início**: 2026-03-05  
> **Objetivo**: Construir infraestrutura sólida de dados, balanceamento e lore antes de expandir gameplay.

---

## Legenda de Status

| Símbolo | Significado |
|---------|-------------|
| `[ ]`   | Pendente |
| `[~]`   | Em progresso |
| `[x]`   | Concluído e testado |
| `[!]`   | Bloqueado / requer revisão |

---

## Feature 1 — Battle Log Persistente (SQLite)
> **Prioridade**: P0 — Fundação para ELO, Replay e Balance  
> **Impacto**: Todas as features dependem de histórico de lutas persistente

- [x] 1.1 Criar `data/battle_db.py` com schema SQLite (tabelas: matches, events, stats)
- [x] 1.2 Criar tabela `matches`: id, p1, p2, winner, loser, duration, ko_type, arena, timestamp
- [x] 1.3 Criar tabela `match_events`: id, match_id, frame, event_type, data_json
- [x] 1.4 Criar tabela `character_stats`: name, wins, losses, elo, matches_played, last_updated
- [x] 1.5 Integrar com `AppState.record_fight_result()` — gravar match no SQLite
- [x] 1.6 Testes unitários: insert, query, integridade referencial (15/15 passed)
- [x] 1.7 Migração segura: não quebrar dados existentes em JSON (aditivo, JSON intocado)

---

## Feature 2 — Sistema ELO/Rating
> **Prioridade**: P0 — Ranking competitivo  
> **Dependência**: Feature 1 (character_stats no SQLite)

- [x] 2.1 Criar `core/elo_system.py` com cálculo ELO (K-factor adaptativo)
- [x] 2.2 Definir tiers: BRONZE → SILVER → GOLD → PLATINUM → DIAMOND → MASTER
- [x] 2.3 Integrar com `record_fight_result()` — atualizar ELO após cada luta
- [x] 2.4 ELO persistido no SQLite (character_stats) — não em Personagem.to_dict()
- [x] 2.5 Persistir rating no SQLite (`character_stats`) com peak_elo tracking
- [x] 2.6 Testes: 12/12 ELO + integration test passed
- [x] 2.7 Validação: ELO floor=0, K-factor 40→32→24 por experiência

---

## Feature 3 — Coleta de Dados de Balance
> **Prioridade**: P1 — Balanceamento por dados  
> **Dependência**: Feature 1 (match_events para dados granulares)

- [x] 3.1 Capturar stats por luta em `sim_combat.py`: dano dealt/taken, skills used, hit accuracy
- [x] 3.2 Gravar `match_events` no SQLite (hits, skills, mortes, combos)
- [x] 3.3 Criar `tools/balance_report.py` — queries de winrate por classe/arma/elemento
- [x] 3.4 Exportar relatório: weapon matchup matrix, skill usage, class tier list
- [x] 3.5 Testes: dados capturados corretamente, queries retornam valores esperados (21+6 tests)
- [x] 3.6 Fix: double-recording em tournament mode (refactor flush pipeline)

---

## ⚠ AUDITORIA DE EXPERIÊNCIA (Resultado da conferência v14.0)

**Data**: 2026-03-05

Todos os sistemas backend (Features 1-3) foram testados e funcionam:
- **29/29 testes unitários + integração passando**
- **BattleDB**: 1 luta real gravada com ELO, classes, armas
- **ELO**: Cálculo correto (1600±23 primeira luta, K-factor adaptativo)
- **MatchStats**: Collector registra hits/blocks/dodges/deaths no sim_combat
- **BalanceReport**: CLI funcional com leaderboard, winrates, matchups

### Problema Crítico Identificado:
**NENHUMA feature v14.0 é visível ao usuário final.**

| Feature | Backend | UI/UX |
|---------|---------|-------|
| ELO/Tier | ✅ Funciona | ❌ Invisível — não aparece em nenhuma tela |
| Win/Loss | ✅ Salvo no DB | ❌ Invisível — nem na seleção de personagem |
| Leaderboard | ✅ DB query pronta | ❌ Sem tela — só CLI (`balance_report.py`) |
| Pós-luta | ✅ Resultado gravado | ❌ Sem tela de resultado — volta ao menu |
| Match History | ✅ SQLite completo | ❌ Sem visualizador |
| Stat Events | ✅ Collector integrado | ❌ Sem replay/histograma |

### Próxima fase DEVE priorizar:
1. **Tela pós-luta** (resultado + ELO delta + stats da luta)
2. **ELO visível na seleção** de personagem
3. **Tela de Leaderboard** acessível pelo menu principal
4. Só depois: Features 4-6 (Elemental, Replay, WorldMap Events)

---

## Feature 4 — Reações Elementais Completas
> **Prioridade**: P1 — Gameplay depth  
> **Dependência**: Nenhuma (sistema independente, já 95% pronto)

- [ ] 4.1 Implementar `trigger_elemental_reaction()` no sim_combat.py
- [ ] 4.2 Conectar com sistema de dano existente (calcular_dano_magico)
- [ ] 4.3 Tracking de "aura elemental" por lutador (último elemento aplicado)
- [ ] 4.4 VFX/feedback visual para cada reação no renderer
- [ ] 4.5 Testes: todas as 35+ reações disparam corretamente

---

## Feature 5 — Sistema de Replay
> **Prioridade**: P1 — Análise e entretenimento  
> **Dependência**: Feature 1 (frame data no SQLite)

- [ ] 5.1 Criar `ReplayFrame` dataclass — state snapshot por frame
- [ ] 5.2 Capturar frames em `simulacao.py` (posição, HP, mana, efeitos por lutador)
- [ ] 5.3 Serializar replay completo em `data/replays/{match_id}.json`
- [ ] 5.4 Criar `SimuladorReplay` — playback mode (sem input, lê frames salvos)
- [ ] 5.5 Controles: play/pause, seek, velocidade variável (0.25x a 4x)
- [ ] 5.6 Testes: save → load → playback gera mesma sequência visual

---

## Feature 6 — Eventos Procedurais no World Map
> **Prioridade**: P2 — Lore e imersão  
> **Dependência**: Feature 1 (histórico de lutas), Feature 2 (ratings)

- [ ] 6.1 Estender `WorldBridge.on_fight_result()` com milestones de campeão
- [ ] 6.2 Gerar eventos dinâmicos baseados em resultados: conquistas, guerras, eras
- [ ] 6.3 Conectar ELO com expansão territorial (top-rated gods ganham território)
- [ ] 6.4 UI: exibir eventos recentes no world map renderer
- [ ] 6.5 Testes: eventos gerados corretamente, sem crash no world map

---

## Resumo de Progresso

| Feature | Status | Itens | Concluídos | % |
|---------|--------|-------|------------|---|
| 1. Battle Log (SQLite) | **Concluído** | 7 | 7 | 100% |
| 2. ELO/Rating | **Concluído** | 7 | 7 | 100% |
| 3. Balance Data | **Concluído** | 6 | 6 | 100% |
| 4. Elemental Reactions | Pendente | 5 | 0 | 0% |
| 5. Replay System | Pendente | 6 | 0 | 0% |
| 6. World Map Events | Pendente | 5 | 0 | 0% |
| **FASE 2** | **Concluído** | **15** | **13** | **87%** |
| **TOTAL** | **Em progresso** | **51** | **33** | **65%** |

---

# ═══════════════════════════════════════════════════════════
# FASE 2 — "VISIBILIDADE" (Próxima)
# ═══════════════════════════════════════════════════════════

> **Objetivo**: Tornar TODAS as features v14.0 visíveis e úteis para o usuário.
> Nenhum sistema backend novo — foco 100% em interface e UX.

---

## Feature 7 — Tela Pós-Luta (Post-Fight Results)
> **Prioridade**: P0 — O usuário PRECISA ver o resultado
> **Problema atual**: Luta acaba → volta ao menu sem feedback nenhum

- [x] 7.1 Criar janela/popup `PostFightScreen` (Tkinter)
  - Nome do vencedor (destaque), nome do perdedor
  - Duração da luta, tipo de vitória (KO / Timeout)
  - ELO antes → ELO depois (delta com seta ↑↓ colorida)
  - Tier badge do vencedor (BRONZE/SILVER/GOLD/etc)
- [x] 7.2 Exibir stats da luta (do `MatchStatsCollector`):
  - Dano dealt, hits landed, accuracy%, crits, max combo
  - Lado a lado (winner vs loser)
- [x] 7.3 Integrar em `view_luta.py` e `view_torneio.py`
  - Mostrar automaticamente quando a luta acaba
  - Botão "Continuar" para voltar ao menu/bracket

---

## Feature 8 — ELO Visível na Seleção de Personagem
> **Prioridade**: P0 — O usuário escolhe sem contexto competitivo
> **Problema atual**: Preview mostra só VEL/RES — nada de ELO/W-L

- [x] 8.1 Na `view_luta.py`, ao selecionar personagem, mostrar:
  - ELO atual + Tier badge (cor/ícone)
  - Record: "12W — 5L (70.6%)"
  - Peak ELO (se diferente do atual)
- [x] 8.2 Na `view_chars.py` (criação), mostrar stats competitivos
- [x] 8.3 No `view_torneio.py`, mostrar ELO no bracket card

---

## Feature 9 — Tela de Leaderboard / Rankings
> **Prioridade**: P1 — Dá sentido a todo o sistema de dados
> **Problema atual**: Leaderboard só existe como CLI (`balance_report.py`)

- [x] 9.1 Criar `TelaLeaderboard` no menu principal (Tkinter)
  - Tabela com: Rank, Nome, ELO, Tier, W, L, WR%
  - Top 20 personagens ordenados por ELO
  - Cores por tier (Bronze=marrom, Silver=cinza, Gold=dourado, etc)
- [x] 9.2 Adicionar aba "Winrates por Classe" (class tier list)
- [x] 9.3 Adicionar aba "Matchups de Arma" (weapon matrix)
- [x] 9.4 Botão no menu principal: "🏆 Rankings"
- [ ] 9.5 Filtros opcionais: por classe, por arma, mínimo de lutas

---

## Feature 10 — Histórico de Lutas
> **Prioridade**: P2 — Nice to have, completa a experiência
> **Problema atual**: Match history no DB mas sem visualizador

- [x] 10.1 Criar `TelaHistorico` com lista das últimas N lutas
  - Data, P1 vs P2, vencedor, duração, KO/Timeout
  - Clicável para ver detalhes (stats, ELO delta)
- [x] 10.2 Integrar como aba dentro do Leaderboard ou menu próprio

---

## Ordem de Implementação (Fase 2)

```
7. Post-Fight Screen  ←── PRIMEIRO (impacto imediato)
8. ELO na Seleção     ←── contextualiza escolha
9. Leaderboard UI     ←── dá sentido longo prazo
10. Histórico         ←── se sobrar tempo
```

Depois da Fase 2: retornar às Features 4-6 (Elemental, Replay, WorldMap).

---

## Notas de Segurança

- SQLite: Sempre usar parâmetros `?` — **nunca** f-strings em queries
- JSON: Validar antes de deserializar — schema checking
- Replays: Sanitizar nomes de arquivo (path traversal prevention)
- Backups: JSON existentes não são deletados, migração aditiva
- Testes: Cada feature tem testes antes de merge
