# Audit Summary

- Generated at: `2026-03-26T16:32:32-03:00`
- Workspace root: `C:\Users\birul\Desktop\new`
- Total files: `306`
- Total functions: `2520`

## Breakdown

- `ativo`: 251
- `gerado`: 25
- `integracao`: 22
- `legado`: 8

## Severity

- `alta`: 17
- `media`: 150
- `baixa`: 43
- `nenhuma`: 96

## Top File Hotspots

- `neural/neural_v3_rework/simulacao/sim_renderer.py` [alta] -> possivel mojibake/encoding inconsistente (2954 marcadores); captura generica de excecao x43
- `neural/neural_v3_rework/efeitos/magic_vfx.py` [alta] -> possivel mojibake/encoding inconsistente (140 marcadores); sem referencia aproximada na suite de testes; captura generica de excecao x12
- `neural/neural_v3_rework/interface/view_luta.py` [alta] -> captura generica de excecao x12
- `neural/neural_v3_rework/utilitarios/test_headless_battle.py` [alta] -> possivel mojibake/encoding inconsistente (57 marcadores); sem referencia aproximada na suite de testes; captura generica de excecao x12
- `neural/neural_v3_rework/efeitos/weapon_animations.py` [alta] -> possivel mojibake/encoding inconsistente (104 marcadores); sem referencia aproximada na suite de testes; captura generica de excecao x11
- `neural/neural_v3_rework/simulacao/simulacao.py` [alta] -> possivel mojibake/encoding inconsistente (288 marcadores); captura generica de excecao x10; pendencias TODO/FIXME x5
- `neural/neural_v3_rework/dados/app_state.py` [alta] -> possivel mojibake/encoding inconsistente (1683 marcadores); captura generica de excecao x8
- `neural/neural_v3_rework/interface/main.py` [alta] -> captura generica de excecao x6
- `neural/neural_v3_rework/dados/world_bridge.py` [alta] -> possivel mojibake/encoding inconsistente (732 marcadores); sem referencia aproximada na suite de testes; captura generica de excecao x6
- `neural/neural_v3_rework/pipeline_video/fight_recorder.py` [alta] -> possivel mojibake/encoding inconsistente (113 marcadores); captura generica de excecao x4
- `neural/neural_v3_rework/ferramentas/gerador_database.py` [alta] -> possivel mojibake/encoding inconsistente (190 marcadores); sem referencia aproximada na suite de testes; captura generica de excecao x3
- `neural/neural_v3_rework/ia/brain.py` [alta] -> possivel mojibake/encoding inconsistente (514 marcadores); captura generica de excecao x1; pendencias TODO/FIXME x2
- `neural/neural_v3_rework/nucleo/lutador/entity.py` [alta] -> possivel mojibake/encoding inconsistente (37 marcadores); sem referencia aproximada na suite de testes; captura generica de excecao x1
- `neural/neural_v3_rework/pipeline_video/batch_runner.py` [alta] -> sem referencia aproximada na suite de testes; captura generica de excecao x1
- `neural/neural_v3_rework/ia/brain_combat.py` [alta] -> possivel mojibake/encoding inconsistente (1059 marcadores); sem referencia aproximada na suite de testes

## Top Function Hotspots

- `neural/neural_v3_rework/simulacao/sim_renderer.py:2314` `SimuladorRenderer.desenhar_arma` [alta] -> funcao longa (1383 linhas); captura generica de excecao x42
- `neural/neural_v3_rework/simulacao/simulacao.py:629` `Simulador.update` [alta] -> funcao longa (1045 linhas); captura generica de excecao x1; pendencias TODO/FIXME x2
- `neural/neural_v3_rework/ia/brain_skills.py:176` `SkillsMixin._processar_skills_estrategico` [alta] -> funcao longa (703 linhas)
- `neural/neural_v3_rework/ia/brain_combat.py:1316` `CombatMixin._estrategia_generica` [alta] -> funcao longa (475 linhas)
- `neural/neural_v3_rework/efeitos/magic_vfx.py:524` `DramaticExplosion._spawn` [alta] -> funcao longa (425 linhas)
- `neural/neural_v3_rework/interface/main.py:240` `MenuPrincipal._build_ui` [alta] -> funcao longa (387 linhas)
- `neural/neural_v3_rework/simulacao/sim_combat.py:39` `SimuladorCombat.checar_ataque` [alta] -> funcao longa (365 linhas)
- `neural/neural_v3_rework/ia/brain.py:138` `AIBrain.__init__` [alta] -> funcao longa (334 linhas)
- `neural/neural_v3_rework/pipeline_video/batch_runner.py:60` `run_batch` [alta] -> funcao longa (260 linhas); captura generica de excecao x1
- `neural/neural_v3_rework/pipeline_video/fight_recorder.py:206` `FightRecorder.record` [alta] -> funcao longa (260 linhas); captura generica de excecao x1
- `neural/neural_v3_rework/nucleo/lutador/entity.py:52` `Lutador.__init__` [alta] -> funcao longa (254 linhas); captura generica de excecao x1
- `neural/neural_v3_rework/simulacao/sim_renderer.py:1487` `SimuladorRenderer.desenhar` [alta] -> funcao longa (251 linhas)
- `neural/neural_v3_rework/interface/view_luta.py:638` `TelaLuta.iniciar_luta` [alta] -> funcao extensa (134 linhas); captura generica de excecao x8
- `neural/neural_v3_rework/efeitos/magic_vfx.py:254` `MagicParticle.draw` [alta] -> funcao extensa (94 linhas); captura generica de excecao x5
- `neural/neural_v3_rework/simulacao/simulacao.py:551` `Simulador.carregar_luta_dados` [alta] -> captura generica de excecao x3
- `neural/neural_v3_rework/ferramentas/gerador_database.py:620` `salvar_database` [alta] -> captura generica de excecao x3
- `neural/neural_v3_rework/simulacao/simulacao.py:49` `Simulador.run` [alta] -> captura generica de excecao x3
- `neural/neural_v3_rework/pipeline_video/fight_recorder.py:472` `FightRecorder._compute_sim_dt` [alta] -> captura generica de excecao x3
- `neural/world_map_pygame/units.py:437` `UnitSystem.simulate` [media] -> funcao extensa (248 linhas)
- `neural/world_map_pygame/tools.py:630` `apply_tool` [media] -> funcao extensa (234 linhas)

## Outputs

- Raw ledger: `audit_ledger.json`
- Checklist report is generated by `scripts/run_audit_checklist.py`.
