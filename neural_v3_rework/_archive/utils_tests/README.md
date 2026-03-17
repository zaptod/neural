# _archive/utils_tests/

## Testes manuais arquivados (Sprint 11 — E03)

Estes arquivos foram movidos de `utils/` para cá porque são testes
**manuais interativos** que requerem display, som ou hardware — não
podem ser executados pelo pytest automaticamente.

| Arquivo | Tipo |
|---|---|
| `test_arena.py` | Visual: renderiza arena manualmente |
| `test_chain.py` | Manual: testa armas de corrente |
| `test_chain_battle.py` | Headless com setup manual |
| `test_headless_battle.py` | Smoke test headless (precisa de pygame) |
| `test_jump_sound.py` | Som: testa pulos e SFX |
| `test_manual.py` | Manual: ciclo de luta completo |
| `test_sound.py` | Som: teste do sistema de áudio |
| `test_vfx.py` | Visual: partículas e efeitos |
| `test_visual_debug.py` | Visual: hitboxes e debug overlay |

Para rodar qualquer um, execute diretamente do diretório raiz:
```bash
python _archive/utils_tests/test_headless_battle.py
```

## Testes automáticos (pytest)

Os testes automáticos ficam em `tests/` e rodam com:
```bash
pytest tests/
```
