# _archive/core/

## magic_system.py (arquivado na Sprint 10 — C01)

974 linhas com sistema completo de status effects, reações elementais e combos
mágicos **nunca conectados ao combate real**.

### O que continua funcionando

Dois arquivos ainda importam deste módulo:
- `simulation/simulacao.py` — `verificar_reacao_elemental` (inline, dentro de `try/except`)
- `ai/skill_strategy.py` — `REACOES_ELEMENTAIS`, `Elemento` (guarded com `try/except ImportError`)

Como ambos têm guards, o jogo funciona normalmente mesmo com o arquivo arquivado.

### Plano futuro (D06)

Na unificação de status effects (D06), `magic_system.StatusEffect` e
`STATUS_EFFECTS_DB` serão portados para `core/fighter/combat_mixin.py`,
substituindo definitivamente os float timers paralelos. Somente então este
arquivo pode ser removido do projeto.
