# NEURAL FIGHTS â€” Roadmap v14.0 "Polimento & FundaÃ§Ãµes"

> **InÃ­cio**: 2026-03-05  
> **Objetivo**: Construir infraestrutura sÃ³lida de dados, balanceamento e lore antes de expandir gameplay.

---

## Legenda de Status

| SÃ­mbolo | Significado |
|---------|-------------|
| `[ ]`   | Pendente |
| `[~]`   | Em progresso |
| `[x]`   | ConcluÃ­do e testado |
| `[!]`   | Bloqueado / requer revisÃ£o |

---

## Feature 1 â€” Battle Log Persistente (SQLite)
> **Prioridade**: P0 â€” FundaÃ§Ã£o para ELO, Replay e Balance  
> **Impacto**: Todas as features dependem de histÃ³rico de lutas persistente

- [x] 1.1 Criar `dados/battle_db.py` com schema SQLite (tabelas: matches, events, stats)
- [x] 1.2 Criar tabela `matches`: id, p1, p2, winner, loser, duration, ko_type, arena, timestamp
- [x] 1.3 Criar tabela `match_events`: id, match_id, frame, event_type, data_json
- [x] 1.4 Criar tabela `character_stats`: name, wins, losses, elo, matches_played, last_updated
- [x] 1.5 Integrar com `AppState.record_fight_result()` â€” gravar match no SQLite
- [x] 1.6 Testes unitÃ¡rios: insert, query, integridade referencial (15/15 passed)
- [x] 1.7 MigraÃ§Ã£o segura: nÃ£o quebrar dados existentes em JSON (aditivo, JSON intocado)

---

## Feature 2 â€” Sistema ELO/Rating
> **Prioridade**: P0 â€” Ranking competitivo  
> **DependÃªncia**: Feature 1 (character_stats no SQLite)

- [x] 2.1 Criar `nucleo/elo_system.py` com cÃ¡lculo ELO (K-factor adaptativo)
- [x] 2.2 Definir tiers: BRONZE â†’ SILVER â†’ GOLD â†’ PLATINUM â†’ DIAMOND â†’ MASTER
- [x] 2.3 Integrar com `record_fight_result()` â€” atualizar ELO apÃ³s cada luta
- [x] 2.4 ELO persistido no SQLite (character_stats) â€” nÃ£o em Personagem.to_dict()
- [x] 2.5 Persistir rating no SQLite (`character_stats`) com peak_elo tracking
- [x] 2.6 Testes: 12/12 ELO + integration test passed
- [x] 2.7 ValidaÃ§Ã£o: ELO floor=0, K-factor 40â†’32â†’24 por experiÃªncia

---

## Feature 3 â€” Coleta de Dados de Balance
> **Prioridade**: P1 â€” Balanceamento por dados  
> **DependÃªncia**: Feature 1 (match_events para dados granulares)

- [x] 3.1 Capturar stats por luta em `sim_combat.py`: dano dealt/taken, skills used, hit accuracy
- [x] 3.2 Gravar `match_events` no SQLite (hits, skills, mortes, combos)
- [x] 3.3 Criar `ferramentas/balance_report.py` â€” queries de winrate por classe/arma/elemento
- [x] 3.4 Exportar relatÃ³rio: weapon matchup matrix, skill usage, class tier list
- [x] 3.5 Testes: dados capturados corretamente, queries retornam valores esperados (21+6 tests)
- [x] 3.6 Fix: double-recording em tournament mode (refactor flush pipeline)

---

## âš  AUDITORIA DE EXPERIÃŠNCIA (Resultado da conferÃªncia v14.0)

**Data**: 2026-03-05

Todos os sistemas backend (Features 1-3) foram testados e funcionam:
- **29/29 testes unitÃ¡rios + integraÃ§Ã£o passando**
- **BattleDB**: 1 luta real gravada com ELO, classes, armas
- **ELO**: CÃ¡lculo correto (1600Â±23 primeira luta, K-factor adaptativo)
- **MatchStats**: Collector registra hits/blocks/dodges/deaths no sim_combat
- **BalanceReport**: CLI funcional com leaderboard, winrates, matchups

### Problema CrÃ­tico Identificado:
**NENHUMA feature v14.0 Ã© visÃ­vel ao usuÃ¡rio final.**

| Feature | Backend | UI/UX |
|---------|---------|-------|
| ELO/Tier | âœ… Funciona | âŒ InvisÃ­vel â€” nÃ£o aparece em nenhuma tela |
| Win/Loss | âœ… Salvo no DB | âŒ InvisÃ­vel â€” nem na seleÃ§Ã£o de personagem |
| Leaderboard | âœ… DB query pronta | âŒ Sem tela â€” sÃ³ CLI (`balance_report.py`) |
| PÃ³s-luta | âœ… Resultado gravado | âŒ Sem tela de resultado â€” volta ao menu |
| Match History | âœ… SQLite completo | âŒ Sem visualizador |
| Stat Events | âœ… Collector integrado | âŒ Sem replay/histograma |

### PrÃ³xima fase DEVE priorizar:
1. **Tela pÃ³s-luta** (resultado + ELO delta + stats da luta)
2. **ELO visÃ­vel na seleÃ§Ã£o** de personagem
3. **Tela de Leaderboard** acessÃ­vel pelo menu principal
4. SÃ³ depois: Features 4-6 (Elemental, Replay, WorldMap Events)

---

## Feature 4 â€” ReaÃ§Ãµes Elementais Completas
> **Prioridade**: P1 â€” Gameplay depth  
> **DependÃªncia**: Nenhuma (sistema independente, jÃ¡ 95% pronto)

- [ ] 4.1 Implementar `trigger_elemental_reaction()` no sim_combat.py
- [ ] 4.2 Conectar com sistema de dano existente (calcular_dano_magico)
- [ ] 4.3 Tracking de "aura elemental" por lutador (Ãºltimo elemento aplicado)
- [ ] 4.4 VFX/feedback visual para cada reaÃ§Ã£o no renderer
- [ ] 4.5 Testes: todas as 35+ reaÃ§Ãµes disparam corretamente

---

## Feature 5 â€” Sistema de Replay
> **Prioridade**: P1 â€” AnÃ¡lise e entretenimento  
> **DependÃªncia**: Feature 1 (frame data no SQLite)

- [ ] 5.1 Criar `ReplayFrame` dataclass â€” state snapshot por frame
- [ ] 5.2 Capturar frames em `simulacao.py` (posiÃ§Ã£o, HP, mana, efeitos por lutador)
- [ ] 5.3 Serializar replay completo em `dados/replays/{match_id}.json`
- [ ] 5.4 Criar `SimuladorReplay` â€” playback mode (sem input, lÃª frames salvos)
- [ ] 5.5 Controles: play/pause, seek, velocidade variÃ¡vel (0.25x a 4x)
- [ ] 5.6 Testes: save â†’ load â†’ playback gera mesma sequÃªncia visual

---

## Feature 6 â€” Eventos Procedurais no World Map
> **Prioridade**: P2 â€” Lore e imersÃ£o  
> **DependÃªncia**: Feature 1 (histÃ³rico de lutas), Feature 2 (ratings)

- [ ] 6.1 Estender `WorldBridge.on_fight_result()` com milestones de campeÃ£o
- [ ] 6.2 Gerar eventos dinÃ¢micos baseados em resultados: conquistas, guerras, eras
- [ ] 6.3 Conectar ELO com expansÃ£o territorial (top-rated gods ganham territÃ³rio)
- [ ] 6.4 UI: exibir eventos recentes no world map renderer
- [ ] 6.5 Testes: eventos gerados corretamente, sem crash no world map

---

## Resumo de Progresso

| Feature | Status | Itens | ConcluÃ­dos | % |
|---------|--------|-------|------------|---|
| 1. Battle Log (SQLite) | **ConcluÃ­do** | 7 | 7 | 100% |
| 2. ELO/Rating | **ConcluÃ­do** | 7 | 7 | 100% |
| 3. Balance Data | **ConcluÃ­do** | 6 | 6 | 100% |
| 4. Elemental Reactions | Pendente | 5 | 0 | 0% |
| 5. Replay System | Pendente | 6 | 0 | 0% |
| 6. World Map Events | Pendente | 5 | 0 | 0% |
| **FASE 2** | **ConcluÃ­do** | **15** | **13** | **87%** |
| **TOTAL** | **Em progresso** | **51** | **33** | **65%** |

---

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FASE 2 â€” "VISIBILIDADE" (PrÃ³xima)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

> **Objetivo**: Tornar TODAS as features v14.0 visÃ­veis e Ãºteis para o usuÃ¡rio.
> Nenhum sistema backend novo â€” foco 100% em interface e UX.

---

## Feature 7 â€” Tela PÃ³s-Luta (Post-Fight Results)
> **Prioridade**: P0 â€” O usuÃ¡rio PRECISA ver o resultado
> **Problema atual**: Luta acaba â†’ volta ao menu sem feedback nenhum

- [x] 7.1 Criar janela/popup `PostFightScreen` (Tkinter)
  - Nome do vencedor (destaque), nome do perdedor
  - DuraÃ§Ã£o da luta, tipo de vitÃ³ria (KO / Timeout)
  - ELO antes â†’ ELO depois (delta com seta â†‘â†“ colorida)
  - Tier badge do vencedor (BRONZE/SILVER/GOLD/etc)
- [x] 7.2 Exibir stats da luta (do `MatchStatsCollector`):
  - Dano dealt, hits landed, accuracy%, crits, max combo
  - Lado a lado (winner vs loser)
- [x] 7.3 Integrar em `view_luta.py` e `view_torneio.py`
  - Mostrar automaticamente quando a luta acaba
  - BotÃ£o "Continuar" para voltar ao menu/bracket

---

## Feature 8 â€” ELO VisÃ­vel na SeleÃ§Ã£o de Personagem
> **Prioridade**: P0 â€” O usuÃ¡rio escolhe sem contexto competitivo
> **Problema atual**: Preview mostra sÃ³ VEL/RES â€” nada de ELO/W-L

- [x] 8.1 Na `view_luta.py`, ao selecionar personagem, mostrar:
  - ELO atual + Tier badge (cor/Ã­cone)
  - Record: "12W â€” 5L (70.6%)"
  - Peak ELO (se diferente do atual)
- [x] 8.2 Na `view_chars.py` (criaÃ§Ã£o), mostrar stats competitivos
- [x] 8.3 No `view_torneio.py`, mostrar ELO no bracket card

---

## Feature 9 â€” Tela de Leaderboard / Rankings
> **Prioridade**: P1 â€” DÃ¡ sentido a todo o sistema de dados
> **Problema atual**: Leaderboard sÃ³ existe como CLI (`balance_report.py`)

- [x] 9.1 Criar `TelaLeaderboard` no menu principal (Tkinter)
  - Tabela com: Rank, Nome, ELO, Tier, W, L, WR%
  - Top 20 personagens ordenados por ELO
  - Cores por tier (Bronze=marrom, Silver=cinza, Gold=dourado, etc)
- [x] 9.2 Adicionar aba "Winrates por Classe" (class tier list)
- [x] 9.3 Adicionar aba "Matchups de Arma" (weapon matrix)
- [x] 9.4 BotÃ£o no menu principal: "ðŸ† Rankings"
- [ ] 9.5 Filtros opcionais: por classe, por arma, mÃ­nimo de lutas

---

## Feature 10 â€” HistÃ³rico de Lutas
> **Prioridade**: P2 â€” Nice to have, completa a experiÃªncia
> **Problema atual**: Match history no DB mas sem visualizador

- [x] 10.1 Criar `TelaHistorico` com lista das Ãºltimas N lutas
  - Data, P1 vs P2, vencedor, duraÃ§Ã£o, KO/Timeout
  - ClicÃ¡vel para ver detalhes (stats, ELO delta)
- [x] 10.2 Integrar como aba dentro do Leaderboard ou menu prÃ³prio

---

## Ordem de ImplementaÃ§Ã£o (Fase 2)

```
7. Post-Fight Screen  â†â”€â”€ PRIMEIRO (impacto imediato)
8. ELO na SeleÃ§Ã£o     â†â”€â”€ contextualiza escolha
9. Leaderboard UI     â†â”€â”€ dÃ¡ sentido longo prazo
10. HistÃ³rico         â†â”€â”€ se sobrar tempo
```

Depois da Fase 2: retornar Ã s Features 4-6 (Elemental, Replay, WorldMap).

---

## Notas de SeguranÃ§a

- SQLite: Sempre usar parÃ¢metros `?` â€” **nunca** f-strings em queries
- JSON: Validar antes de deserializar â€” schema checking
- Replays: Sanitizar nomes de arquivo (path traversal prevention)
- Backups: JSON existentes nÃ£o sÃ£o deletados, migraÃ§Ã£o aditiva
- Testes: Cada feature tem testes antes de merge

