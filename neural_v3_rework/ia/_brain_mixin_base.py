"""
=============================================================================
Stub base class for AIBrain mixin type resolution.
=============================================================================
At type-checking time (Pylance/Pyright), _AIBrainMixinBase declares all
attributes initialised in AIBrain.__init__ plus cross-mixin method stubs.
At runtime it is just ``object`` — zero overhead.

AIBrain's MRO:
    AIBrain → PersonalityMixin → ... → ChoreographyMixin → _AIBrainMixinBase → object
=============================================================================
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:

    class _AIBrainMixinBase:
        """Provides attribute declarations so Pylance can resolve self.xxx
        inside mixin classes that don't define their own __init__."""

        # ── referência ao lutador ────────────────────────────────────
        parent: Any

        # ── controle de frame ────────────────────────────────────────
        timer_decisao: float
        acao_atual: str
        dir_circular: int
        tempo_combate: float

        # ── pool de random por frame (QC-03) ────────────────────────
        _rand_pool: list[float]
        _rand_idx: int

        # ── emoções (0.0-1.0) ───────────────────────────────────────
        medo: float
        raiva: float
        confianca: float
        frustracao: float
        adrenalina: float
        excitacao: float
        tedio: float

        # ── humor ───────────────────────────────────────────────────
        humor: str
        humor_timer: float

        # ── memória de combate ──────────────────────────────────────
        hits_recebidos_total: int
        hits_dados_total: int
        hits_recebidos_recente: int
        hits_dados_recente: int
        tempo_desde_dano: float
        tempo_desde_hit: float
        ultimo_dano_recebido: float
        vezes_que_fugiu: int
        ultimo_hp: float
        combo_atual: int
        max_combo: int

        # ── personalidade ───────────────────────────────────────────
        arquetipo: str
        estilo_luta: str
        filosofia: str
        tracos: list[str]
        quirks: list[str]
        agressividade_base: float
        _agressividade_temp_mod: float

        # ── sistemas v11.0 ──────────────────────────────────────────
        instintos: list[Any]
        ritmo: str | None
        ritmo_fase_atual: int
        ritmo_timer: float
        ritmo_modificadores: dict[str, Any]

        # ── debug ───────────────────────────────────────────────────
        DEBUG_AI_DECISIONS: bool

        # ── cooldowns internos ──────────────────────────────────────
        cd_dash: float
        cd_pulo: float
        cd_mudanca_direcao: float
        cd_reagir: float
        cd_buff: float
        cd_quirk: float
        cd_mudanca_humor: float

        # ── cache de skills ─────────────────────────────────────────
        skills_por_tipo: dict[str, list[Any]]
        skill_strategy: Any  # SkillStrategySystem | None

        # ── estados especiais ───────────────────────────────────────
        modo_berserk: bool
        modo_defensivo: bool
        modo_burst: bool
        executando_quirk: bool

        # ── coreografia v5.0 ────────────────────────────────────────
        momento_cinematografico: Any
        acao_sincronizada: Any
        respondendo_a_oponente: bool
        memoria_oponente: dict[str, Any]
        reacao_pendente: Any
        tempo_reacao: float

        # ── leitura do oponente v8.0 ────────────────────────────────
        leitura_oponente: dict[str, Any]

        # ── janelas de oportunidade ─────────────────────────────────
        janela_ataque: dict[str, Any]

        # ── baiting ─────────────────────────────────────────────────
        bait_state: dict[str, Any]

        # ── momentum / pressão ──────────────────────────────────────
        momentum: float
        pressao_aplicada: float
        pressao_recebida: float

        # ── hesitação / impulso humano ──────────────────────────────
        hesitacao: float
        impulso: float
        congelamento: float

        # ── timing humano ───────────────────────────────────────────
        tempo_reacao_base: float
        variacao_timing: float
        micro_ajustes: int
        ultimo_bloqueio: float
        _inimigo_estava_atacando: bool
        _hits_recebidos_antes_ataque_ini: int

        # ── combos / follow-ups ─────────────────────────────────────
        combo_state: dict[str, Any]

        # ── ritmo de combate ────────────────────────────────────────
        ritmo_combate: float
        burst_counter: int
        descanso_timer: float

        # ── histórico ──────────────────────────────────────────────
        historico_acoes: list[Any]
        repeticao_contador: dict[str, int]

        # ── consciência espacial v9.0 ──────────────────────────────
        consciencia_espacial: dict[str, Any]
        tatica_espacial: dict[str, Any]

        # ── percepção de armas v10.0 ───────────────────────────────
        percepcao_arma: dict[str, Any]

        # ── atributo de classe ─────────────────────────────────────
        _historico_combates: dict[str, Any]

        # ============================================================
        # Cross-mixin method stubs
        # (real implementations live in their respective mixin files)
        # ============================================================

        # SkillsMixin
        def _usar_tudo(self, *args: Any, **kwargs: Any) -> Any: ...
        def _usar_skill(self, *args: Any, **kwargs: Any) -> Any: ...

        # CombatMixin
        def _executar_ataque(self, *args: Any, **kwargs: Any) -> Any: ...
        def _calcular_alcance_efetivo(self, *args: Any, **kwargs: Any) -> Any: ...

        # SpatialMixin
        def _aplicar_modificadores_espaciais(self, *args: Any, **kwargs: Any) -> Any: ...

        # PerceptionMixin
        def _aplicar_modificadores_armas(self, *args: Any, **kwargs: Any) -> Any: ...

        # EmotionsMixin
        def _rand(self, *args: Any, **kwargs: Any) -> Any: ...

        # EvasionMixin
        def _tentar_pulo_evasivo(self, *args: Any, **kwargs: Any) -> Any: ...
        def _tentar_dash_emergencia(self, *args: Any, **kwargs: Any) -> Any: ...

else:
    _AIBrainMixinBase = object
