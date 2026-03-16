# _archive — Código Morto / Obsoleto

Esta pasta contém arquivos **removidos do pacote ativo** na Sprint 1 (C05/C06/C07).
Nenhum destes arquivos é importado pelo projeto. Estão aqui como referência histórica.

## Conteúdo

| Arquivo | Motivo do arquivamento |
|---|---|
| `simulation/simulacao_original.py` | Backup de 4560 L gerado pelo `split_simulacao.py`. O produto do split (`sim_combat.py`, `sim_renderer.py`, `sim_effects.py`) está ativo em `simulation/`. |
| `scripts/split_brain.py` | Script gerador já executado. O produto (`ai/brain_*.py`) está ativo. |
| `scripts/split_simulacao.py` | Script gerador já executado. O produto (`simulation/sim_*.py`) está ativo. |
| `ai/brain_original.py` | Backup gerado pelo `split_brain.py` (se presente). |

## Remoção definitiva

Após confirmação de que os mixins gerados funcionam corretamente, estes arquivos
podem ser removidos permanentemente com:

```bash
rm -rf _archive/
```
