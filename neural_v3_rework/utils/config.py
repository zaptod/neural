# config.py

# FÍSICA
PPM = 50 
GRAVIDADE_Z = 35.0 
ATRITO = 8.0 
ALTURA_PADRAO = 1.70

# VISUAL
LARGURA, ALTURA = 1200, 800
LARGURA_PORTRAIT, ALTURA_PORTRAIT = 540, 960  # 9:16 para filmagem vertical
FPS = 60

# CORES
PRETO = (0, 0, 0)
BRANCO = (255, 255, 255)
CHAO_COR = (30, 30, 30)
COR_FUNDO = (25, 25, 30)
COR_GRID = (35, 35, 45)
VERMELHO_SANGUE = (180, 0, 0)
SANGUE_ESCURO = (100, 0, 0)
AMARELO_FAISCA = (255, 230, 100) 
VERDE_VIDA = (46, 204, 113)
VERMELHO_VIDA = (231, 76, 60)
AZUL_MANA = (52, 152, 219)
COR_CORPO = (20, 20, 20)
COR_P1 = (52, 152, 219) 
COR_P2 = (231, 76, 60)
COR_UI_BG = (0, 0, 0, 150)
COR_TEXTO_TITULO = (255, 215, 0)
COR_TEXTO_INFO = (200, 200, 200)
# =============================================================================
# CONFIGURAÇÃO DA IA (LEGADO-05 fix: constantes antes espalhadas em brain.py)
# Centralizar aqui permite ajuste de balanceamento sem alterar a lógica da IA.
# =============================================================================

# --- Limites de HP ---
AI_HP_CRITICO      = 0.28   # Abaixo disto a IA entra em modo de emergência
AI_HP_BAIXO        = 0.40   # Abaixo disto a IA fica mais defensiva
AI_HP_EXECUTE      = 0.20   # Inimigo abaixo disto ativa Execute Mode

# --- Distâncias e Alcances ---
AI_DIST_ATAQUE_IMINENTE = 3.5   # (metros) Distância máxima para considerar ataque iminente
AI_DIST_PAREDE_CRITICA  = 2.0   # (metros) Distância de parede para considerar "encurralado"
AI_DIST_PAREDE_AVISO    = 3.0   # (metros) Inicia detecção de parede

# --- Intervalos de Atualização ---
AI_INTERVALO_ESPACIAL       = 0.20  # (segundos) Frequência de atualização da consciência espacial
AI_INTERVALO_ARMAS          = 0.50  # (segundos) Frequência de análise de armas
AI_INTERVALO_RITMO          = 5.0   # (segundos) Duração típica de um ciclo de ritmo

# --- Probabilidades e Thresholds ---
AI_PREVISIBILIDADE_ALTA     = 0.70  # Acima disto o oponente é considerado previsível
AI_AGRESSIVIDADE_ALTA       = 0.80  # Acima disto o oponente é considerado muito agressivo
AI_MOMENTUM_POSITIVO        = 0.30  # Momentum acima disto → mais agressivo
AI_MOMENTUM_NEGATIVO        = -0.30 # Momentum abaixo disto → mais cauteloso
AI_PRESSAO_ALTA             = 0.70  # Pressão acima disto → decisões extremas

# --- Tamanho do Pool de Aleatoriedade (QC-03) ---
AI_RAND_POOL_SIZE           = 8     # Valores aleatórios pré-gerados por frame
