"""
NEURAL FIGHTS â€” Balance Config  [E06]
======================================
Constantes de balanÃ§o do combate centralizadas.

Antes da E06, esses nÃºmeros estavam espalhados em nucleo/entities.py sem nome.
Agora qualquer ajuste de balanÃ§o comeÃ§a aqui.

Para medir o efeito de uma mudanÃ§a:
    1. Altere a constante abaixo.
    2. Rode:  python ferramentas/auto_balance.py --fights 200
    3. Verifique o win-rate no relatÃ³rio gerado.
"""

# =============================================================================
# CRÃTICO
# =============================================================================
CRITICO_CHANCE_BONUS_RAGE  = 0.20   # +chance de crÃ­tico quando em fÃºria/rage
CRITICO_MULT_BASE          = 1.50   # multiplicador base de dano crÃ­tico

# =============================================================================
# DANO â€” modificadores de situaÃ§Ã£o
# =============================================================================
DANO_MULT_FLANQUEAR        = 1.30   # bÃ´nus de dano ao flanquear
DANO_MULT_COSTAS           = 1.15   # bÃ´nus de dano por ataque pelas costas
DANO_MULT_AERIAL           = 1.20   # bÃ´nus de dano de ataques aÃ©reos
DANO_MULT_EXECUCAO         = 1.25   # bÃ´nus de dano quando inimigo estÃ¡ com HP baixo
DANO_ECO_RATIO             = 0.50   # fraÃ§Ã£o do dano aplicada como eco/ricochete

# =============================================================================
# ESTAMINA
# =============================================================================
ESTAMINA_MAX               = 100.0  # estamina mÃ¡xima base
ESTAMINA_CUSTO_SKILL_MULT  = 0.80   # multiplicador de custo de skill (reduÃ§Ã£o por passiva)
ESTAMINA_CUSTO_SKILL_MULT2 = 0.50   # reduÃ§Ã£o maior (passiva tier 2)
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
SLOW_DURACAO_DEFAULT       = 2.00   # duraÃ§Ã£o padrÃ£o do slow em segundos

# =============================================================================
# COOLDOWN DE ARMA
# =============================================================================
CD_ARMA_MAX_RATIO          = 0.20   # fraÃ§Ã£o do cd original usada como cd mÃ­nimo de arma
CD_ARMA_MAX_ABSOLUTO       = 0.35   # teto absoluto do cd mÃ­nimo de arma (segundos)

# =============================================================================
# ALCANCE IDEAL
# =============================================================================
ALCANCE_IDEAL_DEFAULT      = 1.50   # metros â€” distÃ¢ncia preferida de combate corpo-a-corpo

