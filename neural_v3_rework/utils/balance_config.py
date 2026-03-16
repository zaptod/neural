"""
NEURAL FIGHTS — Balance Config  [E06]
======================================
Constantes de balanço do combate centralizadas.

Antes da E06, esses números estavam espalhados em core/entities.py sem nome.
Agora qualquer ajuste de balanço começa aqui.

Para medir o efeito de uma mudança:
    1. Altere a constante abaixo.
    2. Rode:  python tools/auto_balance.py --fights 200
    3. Verifique o win-rate no relatório gerado.
"""

# =============================================================================
# CRÍTICO
# =============================================================================
CRITICO_CHANCE_BONUS_RAGE  = 0.20   # +chance de crítico quando em fúria/rage
CRITICO_MULT_BASE          = 1.50   # multiplicador base de dano crítico

# =============================================================================
# DANO — modificadores de situação
# =============================================================================
DANO_MULT_FLANQUEAR        = 1.30   # bônus de dano ao flanquear
DANO_MULT_COSTAS           = 1.15   # bônus de dano por ataque pelas costas
DANO_MULT_AERIAL           = 1.20   # bônus de dano de ataques aéreos
DANO_MULT_EXECUCAO         = 1.25   # bônus de dano quando inimigo está com HP baixo
DANO_ECO_RATIO             = 0.50   # fração do dano aplicada como eco/ricochete

# =============================================================================
# ESTAMINA
# =============================================================================
ESTAMINA_MAX               = 100.0  # estamina máxima base
ESTAMINA_CUSTO_SKILL_MULT  = 0.80   # multiplicador de custo de skill (redução por passiva)
ESTAMINA_CUSTO_SKILL_MULT2 = 0.50   # redução maior (passiva tier 2)
ESTAMINA_CUSTO_DASH_MULT   = 0.80   # custo de dash com passiva de economia
ESTAMINA_CUSTO_DASH_MULT2  = 0.50   # custo de dash com passiva tier 2

# =============================================================================
# MANA
# =============================================================================
MANA_BASE                  = 50.0   # mana base antes de atributo
MANA_POR_ATRIBUTO          = 10.0   # mana adicional por ponto de atributo "mana"

# =============================================================================
# SLOW / CONGELAMENTO
# =============================================================================
SLOW_FATOR_DEFAULT         = 0.50   # velocidade ao ser "lento" (50% da normal)
SLOW_DURACAO_DEFAULT       = 2.00   # duração padrão do slow em segundos

# =============================================================================
# COOLDOWN DE ARMA
# =============================================================================
CD_ARMA_MAX_RATIO          = 0.20   # fração do cd original usada como cd mínimo de arma
CD_ARMA_MAX_ABSOLUTO       = 0.35   # teto absoluto do cd mínimo de arma (segundos)

# =============================================================================
# ALCANCE IDEAL
# =============================================================================
ALCANCE_IDEAL_DEFAULT      = 1.50   # metros — distância preferida de combate corpo-a-corpo
