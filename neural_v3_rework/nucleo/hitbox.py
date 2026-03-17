# hitbox.py - Sistema de Hitbox Modular com Debug v2.0
"""
Sistema centralizado de detecÃ§Ã£o de colisÃ£o para combate.
Inclui logging extensivo para debug.
v2.0 - IntegraÃ§Ã£o com WeaponAnalysis para hitboxes mais precisas
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from utilitarios.config import PPM

# === CONFIGURAÃ‡ÃƒO DE DEBUG ===
DEBUG_HITBOX = False  # Ativar/desativar prints de debug (MUITO VERBOSO)
DEBUG_VISUAL = True  # Mostrar hitboxes visuais no jogo


# === PERFIS DE HITBOX POR TIPO DE ARMA v2.0 ===
# Define caracterÃ­sticas especÃ­ficas de hitbox para cada tipo
HITBOX_PROFILES = {
    "Reta": {
        "shape": "arc",           # Durante ataque usa arco
        "idle_shape": "line",     # Fora de ataque usa linha
        "base_arc": 90,           # Arco base de ataque em graus
        "attack_arc_mult": 1.2,   # Multiplicador de arco durante ataque
        "range_mult": 2.35,       # Multiplicador de alcance (x raio_char)
        "min_range_ratio": 0.3,   # Ratio mÃ­nimo do alcance (para zona morta)
        "hit_window_start": 0.2,  # Quando comeÃ§a a janela de hit (% da animaÃ§Ã£o)
        "hit_window_end": 0.85,   # Quando termina
        "sweet_spot_start": 0.6,  # Zona de dano mÃ¡ximo inÃ­cio
        "sweet_spot_end": 1.0,    # Zona de dano mÃ¡ximo fim (% do alcance)
    },
    "Dupla": {
        "shape": "dual_arc",
        "idle_shape": "dual_line",
        "base_arc": 100,           # Arco amplo para adagas
        "attack_arc_mult": 2.0,    # Swing bem amplo
        "range_mult": 3.2,         # Alcance maior (adagas velozes)
        "min_range_ratio": 0.05,   # Quase sem zona morta
        "hit_window_start": 0.10,  # Janela mais cedo (ataques rÃ¡pidos)
        "hit_window_end": 0.85,
        "sweet_spot_start": 0.2,
        "sweet_spot_end": 1.0,
        "offset_angles": [-40, 40],  # Ã‚ngulos bem abertos das lÃ¢minas
    },
    "Corrente": {
        "shape": "sweep_arc",
        "idle_shape": "arc",
        "base_arc": 180,
        "attack_arc_mult": 1.1,
        "range_mult": 4.0,
        "min_range_ratio": 0.25,    # Zona morta maior
        "hit_window_start": 0.1,
        "hit_window_end": 0.9,
        "sweet_spot_start": 0.7,
        "sweet_spot_end": 1.0,
        "has_dead_zone": True,      # NÃ£o acerta muito perto
    },
    # === PER-STYLE CHAIN PROFILES v5.0 ===
    "Mangual": {
        "shape": "sweep_arc",
        "idle_shape": "arc",
        "base_arc": 120,            # Arco estreito (golpe vertical pesado)
        "attack_arc_mult": 1.0,
        "range_mult": 4.0,
        "min_range_ratio": 0.35,    # Zona morta GRANDE (bola pesada)
        "hit_window_start": 0.25,   # Acerta sÃ³ na descida
        "hit_window_end": 0.70,
        "sweet_spot_start": 0.75,   # Sweet spot na ponta
        "sweet_spot_end": 1.0,
        "has_dead_zone": True,
    },
    "Kusarigama_foice": {
        "shape": "arc",
        "idle_shape": "line",
        "base_arc": 100,            # Cortes rÃ¡pidos de foice
        "attack_arc_mult": 1.3,
        "range_mult": 2.5,          # Curto (foice Ã© perto)
        "min_range_ratio": 0.05,    # Quase sem zona morta
        "hit_window_start": 0.08,   # Acerta cedo (rÃ¡pido)
        "hit_window_end": 0.75,
        "sweet_spot_start": 0.3,
        "sweet_spot_end": 0.8,
        "has_dead_zone": False,
    },
    "Kusarigama_peso": {
        "shape": "sweep_arc",
        "idle_shape": "arc",
        "base_arc": 60,             # Arco estreito (arremessa peso)
        "attack_arc_mult": 1.0,
        "range_mult": 5.5,          # Muito longo
        "min_range_ratio": 0.40,    # Zona morta enorme
        "hit_window_start": 0.30,   # Demora p/ chegar
        "hit_window_end": 0.85,
        "sweet_spot_start": 0.80,
        "sweet_spot_end": 1.0,
        "has_dead_zone": True,
    },
    "Chicote": {
        "shape": "sweep_arc",
        "idle_shape": "line",
        "base_arc": 45,             # Arco fino (laÃ§o reto)
        "attack_arc_mult": 1.5,
        "range_mult": 6.0,          # MAIOR alcance melee
        "min_range_ratio": 0.15,    # Zona morta pequena
        "hit_window_start": 0.05,   # Acerta muito cedo
        "hit_window_end": 0.60,     # Mas acaba rÃ¡pido
        "sweet_spot_start": 0.70,   # Crack = ponta (70-100%)
        "sweet_spot_end": 1.0,
        "has_dead_zone": False,
        "crack_bonus": 2.0,         # 2x dano no crack
    },
    "Meteor Hammer": {
        "shape": "circle",          # 360Â° quando girando!
        "idle_shape": "arc",
        "base_arc": 360,            # Ãrea completa
        "attack_arc_mult": 1.0,
        "range_mult": 5.0,
        "min_range_ratio": 0.20,
        "hit_window_start": 0.0,    # Sempre acerta (spin)
        "hit_window_end": 1.0,
        "sweet_spot_start": 0.60,
        "sweet_spot_end": 1.0,
        "has_dead_zone": True,
        "spin_area": True,          # Flag de dano em Ã¡rea
    },
    "Corrente com Peso": {
        "shape": "sweep_arc",
        "idle_shape": "arc",
        "base_arc": 140,            # Arco mÃ©dio
        "attack_arc_mult": 1.0,
        "range_mult": 3.5,          # Alcance mÃ©dio-curto
        "min_range_ratio": 0.15,    # Zona morta menor
        "hit_window_start": 0.15,
        "hit_window_end": 0.80,
        "sweet_spot_start": 0.50,
        "sweet_spot_end": 0.90,
        "has_dead_zone": True,
        "applies_slow": True,       # Aplica slow no hit
        "applies_pull": True,       # Puxa o alvo
    },
    "Arremesso": {
        "shape": "projectile_cone",
        "idle_shape": "point",
        "base_arc": 30,
        "attack_arc_mult": 2.0,     # Spread quando joga mÃºltiplos
        "range_mult": 5.0,
        "min_range_ratio": 0.5,
        "hit_window_start": 0.0,
        "hit_window_end": 1.0,
        "is_projectile": True,
    },
    "Arco": {
        "shape": "line",
        "idle_shape": "point",
        "base_arc": 15,
        "attack_arc_mult": 1.0,
        "range_mult": 13.0,
        "min_range_ratio": 0.35,    # Mais vulnerÃ¡vel no corpo-a-corpo
        "hit_window_start": 0.2,
        "hit_window_end": 0.8,
        "is_projectile": True,
    },
    "MÃ¡gica": {
        "shape": "area",
        "idle_shape": "aura",
        "base_arc": 120,
        "attack_arc_mult": 1.0,
        "range_mult": 2.2,
        "min_range_ratio": 0.0,     # Sem zona morta
        "hit_window_start": 0.2,
        "hit_window_end": 0.8,
        "is_area": True,
    },
    "Orbital": {
        "shape": "circle",
        "idle_shape": "circle",
        "base_arc": 360,
        "attack_arc_mult": 1.0,
        "range_mult": 1.9,
        "min_range_ratio": 0.0,
        "hit_window_start": 0.0,
        "hit_window_end": 1.0,
        "always_active": True,
    },
    "TransformÃ¡vel": {
        "shape": "arc",
        "idle_shape": "line",
        "base_arc": 100,
        "attack_arc_mult": 1.15,
        "range_mult": 3.0,
        "min_range_ratio": 0.15,
        "hit_window_start": 0.2,
        "hit_window_end": 0.8,
        "sweet_spot_start": 0.5,
        "sweet_spot_end": 1.0,
    },
}

def debug_log(msg: str, categoria: str = "INFO"):
    """Log de debug condicional"""
    if DEBUG_HITBOX:
        print(f"[HITBOX:{categoria}] {msg}")


def get_hitbox_profile(tipo: str, estilo: str = "") -> Dict:
    """Retorna o perfil de hitbox para um tipo de arma.
    v5.0: Para Corrente, busca perfil por estilo primeiro."""
    # v5.0: Chain weapons â€” perfil por estilo primeiro
    if tipo == "Corrente" and estilo:
        # Kusarigama dual-mode: checa chain_mode via suffix
        if estilo in HITBOX_PROFILES:
            return HITBOX_PROFILES[estilo]
        # Tenta match parcial (estilo in key OR key in estilo)
        for key in HITBOX_PROFILES:
            if key in estilo or estilo in key:
                return HITBOX_PROFILES[key]
        # Fallback para Corrente genÃ©rico
        return HITBOX_PROFILES["Corrente"]

    # Tenta match exato primeiro
    if tipo in HITBOX_PROFILES:
        return HITBOX_PROFILES[tipo]
    
    # Tenta match parcial
    for key in HITBOX_PROFILES:
        if key in tipo:
            return HITBOX_PROFILES[key]
    
    # Fallback para Reta
    return HITBOX_PROFILES["Reta"]


@dataclass
class HitboxInfo:
    """InformaÃ§Ãµes de uma hitbox para debug e colisÃ£o v2.0"""
    tipo: str
    centro: Tuple[float, float]  # Em pixels
    alcance: float  # Em pixels
    angulo: float  # Em graus
    largura_angular: float  # Em graus (para armas de Ã¡rea)
    pontos: List[Tuple[float, float]] = None  # Pontos da linha (para armas de lÃ¢mina)
    ativo: bool = False
    
    # Novos campos v2.0
    alcance_minimo: float = 0.0      # Zona morta
    sweet_spot_min: float = 0.0      # InÃ­cio do sweet spot
    sweet_spot_max: float = 0.0      # Fim do sweet spot
    forma: str = "arc"               # Forma da hitbox
    dano_mult: float = 1.0           # Multiplicador de dano na posiÃ§Ã£o
    profile: Dict = field(default_factory=dict)  # Perfil completo
    
    def __str__(self):
        if self.pontos:
            return f"Hitbox[{self.tipo}] linha=({self.pontos[0]}) -> ({self.pontos[1]}) alcance={self.alcance:.1f}px"
        return f"Hitbox[{self.tipo}] centro={self.centro} alcance={self.alcance:.1f}px ang={self.angulo:.1f}Â° larg={self.largura_angular:.1f}Â°"
    
    def get_damage_at_distance(self, dist: float) -> float:
        """Calcula multiplicador de dano baseado na distÃ¢ncia (sweet spot)"""
        if dist < self.alcance_minimo:
            return 0.3  # Na zona morta
        
        # Calcula posiÃ§Ã£o relativa no alcance
        alcance_efetivo = self.alcance - self.alcance_minimo
        if alcance_efetivo <= 0:
            return 1.0
        
        pos_relativa = (dist - self.alcance_minimo) / alcance_efetivo
        
        # Verifica se estÃ¡ no sweet spot
        if self.sweet_spot_min <= pos_relativa <= self.sweet_spot_max:
            return 1.2  # Dano aumentado no sweet spot
        
        return 1.0  # Dano normal
    
    def is_in_hitbox(self, pos: Tuple[float, float], raio_alvo: float = 0) -> Tuple[bool, float]:
        """
        Verifica se uma posiÃ§Ã£o estÃ¡ dentro da hitbox.
        Retorna (estÃ¡_dentro, multiplicador_dano)
        """
        cx, cy = self.centro
        px, py = pos
        
        dist = math.hypot(px - cx, py - cy)
        
        # Verifica alcance
        alcance_efetivo = self.alcance + raio_alvo
        if dist > alcance_efetivo:
            return False, 0.0
        
        if dist < self.alcance_minimo - raio_alvo:
            return False, 0.0
        
        # Verifica Ã¢ngulo
        ang_para_pos = math.degrees(math.atan2(py - cy, px - cx))
        diff_ang = ang_para_pos - self.angulo
        while diff_ang > 180:
            diff_ang -= 360
        while diff_ang < -180:
            diff_ang += 360
        
        if abs(diff_ang) > self.largura_angular / 2:
            return False, 0.0
        
        # Calcula multiplicador de dano
        dano_mult = self.get_damage_at_distance(dist)
        
        return True, dano_mult


class SistemaHitbox:
    """Sistema centralizado de hitbox com debug"""
    
    def __init__(self):
        self.ultimo_ataque_info = {}  # Cache de info para debug visual
        self.hits_registrados = []  # HistÃ³rico de hits (capped at 100)
        
    def calcular_hitbox_arma(self, lutador) -> Optional[HitboxInfo]:
        """
        Calcula a hitbox da arma de um lutador.
        Retorna None se nÃ£o houver hitbox ativa.
        """
        arma = lutador.dados.arma_obj
        if not arma:
            debug_log(f"{lutador.dados.nome}: Sem arma equipada", "WARN")
            return None
        
        # PosiÃ§Ã£o central do lutador em pixels
        cx = lutador.pos[0] * PPM
        cy = lutador.pos[1] * PPM
        raio_char = (lutador.dados.tamanho / 2) * PPM
        fator = lutador.fator_escala
        
        tipo = arma.tipo
        angulo = lutador.angulo_arma_visual
        rad = math.radians(angulo)
        
        debug_log(f"{lutador.dados.nome}: Calculando hitbox tipo={tipo} pos=({cx:.1f}, {cy:.1f}) ang={angulo:.1f}Â°", "CALC")
        
        # === ARMAS DE CORRENTE (colisÃ£o por arco/varredura) ===
        if self._eh_arma_corrente(tipo):
            return self._calcular_hitbox_corrente(lutador, arma, cx, cy, rad, fator, raio_char)

        # === ARMAS DE LÃ‚MINA (colisÃ£o por linha/arco de varredura) ===
        elif self._eh_arma_lamina(tipo):
            return self._calcular_hitbox_lamina(lutador, arma, cx, cy, rad, fator, raio_char)

        # === ARMAS DE ÃREA (MÃ¡gica) â€” DEVE vir antes de ranged ===
        # M-05 fix: MÃ¡gica Ã© capturada aqui PRIMEIRO (Ã¡rea), por isso foi removida de
        # _eh_arma_ranged. O dano real Ã© aplicado via orbes/projÃ©teis em entities.py;
        # esta hitbox Ã© visual/debug e apenas Ã© marcada ativa durante o ataque.
        elif self._eh_arma_area(tipo):
            return self._calcular_hitbox_area(lutador, arma, cx, cy, rad, fator, raio_char)

        # === ARMAS RANGED FÃSICAS (Arremesso/Arco) â€” Usam projÃ©teis, nÃ£o hitbox direta ===
        elif self._eh_arma_ranged(tipo):
            return self._calcular_hitbox_ranged(lutador, arma, cx, cy, rad, fator, raio_char)

        # === ARMAS ORBITAIS (colisÃ£o especial) ===
        elif "Orbital" in tipo:
            return self._calcular_hitbox_orbital(lutador, arma, cx, cy, fator, raio_char)

        # === FALLBACK ===
        else:
            debug_log(f"{lutador.dados.nome}: Tipo de arma desconhecido: {tipo}", "WARN")
            return self._calcular_hitbox_lamina(lutador, arma, cx, cy, rad, fator, raio_char)
    
    def _eh_arma_corrente(self, tipo: str) -> bool:
        """Verifica se Ã© arma de corrente/mangual (usa colisÃ£o de arco)"""
        return "Corrente" in tipo
    
    def _eh_arma_lamina(self, tipo: str) -> bool:
        """Verifica se Ã© arma de lÃ¢mina (usa colisÃ£o de linha)"""
        return any(t in tipo for t in ["Reta", "Dupla", "TransformÃ¡vel"])
    
    def _eh_arma_ranged(self, tipo: str) -> bool:
        """Verifica se Ã© arma ranged fÃ­sica (usa projÃ©teis de arma).
        FP-01 fix: MÃ¡gica foi removida daqui â€” ela Ã© capturada ANTES por _eh_arma_area,
        portanto listÃ¡-la aqui era cÃ³digo unreachable e causava confusÃ£o."""
        return any(t in tipo for t in ["Arremesso", "Arco"])
    
    def _eh_arma_area(self, tipo: str) -> bool:
        """Verifica se Ã© arma de Ã¡rea (usa colisÃ£o de distÃ¢ncia) - Apenas MÃ¡gica"""
        return "MÃ¡gica" in tipo
    
    def _calcular_hitbox_lamina(self, lutador, arma, cx, cy, rad, fator, raio_char) -> HitboxInfo:
        """
        Calcula hitbox para armas de lÃ¢mina v2.0.
        Usa perfis de hitbox para caracterÃ­sticas precisas por tipo.
        """
        tipo = arma.tipo
        profile = get_hitbox_profile(tipo)
        
        # Alcance = raio do personagem Ã— multiplicador do perfil (geometria removida)
        fator_arma = profile["range_mult"]
        alcance_total = raio_char * fator_arma
        cabo_px   = alcance_total * 0.30  # 30% = cabo
        lamina_px = alcance_total * 0.70  # 70% = lÃ¢mina
        
        # Calcula zona morta e sweet spot baseado no perfil
        alcance_minimo = alcance_total * profile["min_range_ratio"]
        sweet_spot_start = profile.get("sweet_spot_start", 0.6)
        sweet_spot_end = profile.get("sweet_spot_end", 1.0)
        
        # === DURANTE ATAQUE: USA ARCO DE VARREDURA ===
        if lutador.atacando:
            # Pega o perfil de animaÃ§Ã£o para saber o arco total
            try:
                from efeitos.weapon_animations import WEAPON_PROFILES
                anim_profile = WEAPON_PROFILES.get(tipo, WEAPON_PROFILES.get("Reta"))
                arco_total = abs(anim_profile.anticipation_angle) + abs(anim_profile.attack_angle)
                angulo_centro = lutador.angulo_olhar
            except ImportError:
                arco_total = profile["base_arc"]
                angulo_centro = math.degrees(rad)
            
            # Largura angular: arco de ataque * multiplicador do perfil
            largura_angular = max(profile["base_arc"], arco_total * profile["attack_arc_mult"])
            
            debug_log(f"  LÃ¢mina ATAQUE v2: arco={arco_total:.1f}Â° largura={largura_angular:.1f}Â° centro={angulo_centro:.1f}Â°", "CALC")
            
            return HitboxInfo(
                tipo=tipo,
                centro=(cx, cy),
                alcance=alcance_total,
                angulo=angulo_centro,
                largura_angular=largura_angular,
                pontos=None,
                ativo=True,
                alcance_minimo=alcance_minimo,
                sweet_spot_min=sweet_spot_start,
                sweet_spot_max=sweet_spot_end,
                forma=profile["shape"],
                profile=profile
            )
        
        # === FORA DE ATAQUE: USA LINHA (para debug visual) ===
        x1 = cx + math.cos(rad) * cabo_px
        y1 = cy + math.sin(rad) * cabo_px
        x2 = cx + math.cos(rad) * (cabo_px + lamina_px)
        y2 = cy + math.sin(rad) * (cabo_px + lamina_px)
        
        debug_log(f"  LÃ¢mina IDLE: cabo_px={cabo_px:.1f} lamina_px={lamina_px:.1f}", "CALC")
        
        return HitboxInfo(
            tipo=tipo,
            centro=(cx, cy),
            alcance=alcance_total,
            angulo=math.degrees(rad),
            largura_angular=30.0,
            pontos=[(x1, y1), (x2, y2)],
            ativo=False,
            alcance_minimo=alcance_minimo,
            sweet_spot_min=sweet_spot_start,
            sweet_spot_max=sweet_spot_end,
            forma=profile["idle_shape"],
            profile=profile
        )
    
    def _calcular_hitbox_corrente(self, lutador, arma, cx, cy, rad, fator, raio_char) -> HitboxInfo:
        """
        Calcula hitbox para armas de corrente v5.0.
        Usa perfil por ESTILO, nÃ£o genÃ©rico. Kusarigama tem dual-mode.
        """
        tipo = arma.tipo
        estilo = getattr(arma, 'estilo', '')
        
        # v5.0: Kusarigama dual-mode â€” resolve o perfil baseado em chain_mode
        if estilo == "Kusarigama":
            chain_mode = getattr(lutador, 'chain_mode', 0)
            profile_key = "Kusarigama_foice" if chain_mode == 0 else "Kusarigama_peso"
            profile = get_hitbox_profile("Corrente", profile_key)
        else:
            profile = get_hitbox_profile("Corrente", estilo)
        
        # Alcance = raio Ã— perfil
        fator_arma = profile["range_mult"]
        alcance_px = raio_char * fator_arma
        alcance_minimo = alcance_px * profile["min_range_ratio"]
        angulo_bola = math.degrees(rad)
        tamanho_bola = raio_char * 0.20
        largura_base = math.degrees(2 * math.atan2(tamanho_bola, alcance_px))
        
        # Meteor Hammer spinning: 360Â° hitbox
        is_spinning = getattr(lutador, 'chain_spinning', False)
        
        # Durante ataque, a corrente varre um arco baseado no perfil
        if lutador.atacando or is_spinning:
            angulo_bola = lutador.angulo_olhar
            if is_spinning or profile.get("spin_area"):
                largura_angular = 360.0  # Full circle
            else:
                largura_angular = profile["base_arc"] * profile["attack_arc_mult"]
        else:
            largura_angular = max(largura_base + 30, 45)
        
        debug_log(f"  Corrente v5: estilo={estilo} alcance={alcance_px:.1f} zona_morta={alcance_minimo:.1f}", "CALC")
        debug_log(f"  Corrente v5: ang={angulo_bola:.1f}Â° largura={largura_angular:.1f}Â° atacando={lutador.atacando}", "CALC")
        
        # Gera pontos do arco para visualizaÃ§Ã£o
        pontos_arco = []
        num_segmentos = 6
        ang_inicio = angulo_bola - largura_angular / 2
        ang_fim = angulo_bola + largura_angular / 2
        
        for i in range(num_segmentos + 1):
            ang = math.radians(ang_inicio + (ang_fim - ang_inicio) * i / num_segmentos)
            px = cx + math.cos(ang) * alcance_px
            py = cy + math.sin(ang) * alcance_px
            pontos_arco.append((px, py))
        
        return HitboxInfo(
            tipo="Corrente",
            centro=(cx, cy),
            alcance=alcance_px,
            angulo=angulo_bola,
            largura_angular=largura_angular,
            pontos=pontos_arco,
            ativo=lutador.atacando,
            alcance_minimo=alcance_minimo,
            sweet_spot_min=profile.get("sweet_spot_start", 0.7),
            sweet_spot_max=profile.get("sweet_spot_end", 1.0),
            forma=profile["shape"] if lutador.atacando else profile["idle_shape"],
            profile=profile
        )
    
    def _calcular_hitbox_ranged(self, lutador, arma, cx, cy, rad, fator, raio_char) -> HitboxInfo:
        """
        Calcula hitbox para armas ranged (Arremesso, Arco).
        Estas armas usam PROJÃ‰TEIS, entÃ£o a hitbox aqui Ã© apenas visual/informativa.
        O dano real Ã© feito pelos projÃ©teis.
        """
        tipo = arma.tipo
        
        # Armas ranged tÃªm alcance maior (onde os projÃ©teis vÃ£o)
        if "Arremesso" in tipo:
            fator_arma = 5.0  # Facas voam longe
            qtd = int(getattr(arma, 'quantidade', 3))
        elif "Arco" in tipo:
            fator_arma = 8.0  # Flechas vÃ£o mais longe ainda
            qtd = 1
        else:
            fator_arma = 4.0
            qtd = 1
        
        alcance_px = raio_char * fator_arma
        
        # Spread visual (para arremesso com mÃºltiplos projÃ©teis)
        largura_angular = 30.0 if qtd > 1 else 10.0
        
        debug_log(f"  Ranged: tipo={tipo} alcance_px={alcance_px:.1f} qtd={qtd}", "CALC")
        
        # Gera linhas de trajetÃ³ria para visualizaÃ§Ã£o
        pontos_traj = []
        if qtd > 1:
            spread = 25  # graus
            for i in range(qtd):
                offset = -spread/2 + (spread / (qtd-1)) * i
                ang = math.radians(math.degrees(rad) + offset)
                px = cx + math.cos(ang) * alcance_px
                py = cy + math.sin(ang) * alcance_px
                pontos_traj.append((px, py))
        else:
            # Linha Ãºnica
            px = cx + math.cos(rad) * alcance_px
            py = cy + math.sin(rad) * alcance_px
            pontos_traj = [(cx, cy), (px, py)]
        
        return HitboxInfo(
            tipo=tipo,
            centro=(cx, cy),
            alcance=alcance_px,
            angulo=math.degrees(rad),
            largura_angular=largura_angular,
            pontos=pontos_traj,  # Linhas de trajetÃ³ria
            ativo=lutador.atacando  # SÃ³ mostra quando ataca
        )
    
    def _calcular_hitbox_area(self, lutador, arma, cx, cy, rad, fator, raio_char) -> HitboxInfo:
        """Calcula hitbox de debug visual para armas de Ã¡rea (MÃ¡gica).
        FP-02 fix: ativo agora reflete se o lutador estÃ¡ atacando, nÃ£o sempre True.
        O dano real de MÃ¡gica acontece via orbes/projÃ©teis â€” esta hitbox Ã© APENAS visual."""
        tipo = arma.tipo

        if "MÃ¡gica" in tipo:
            fator_arma = 2.5
        else:
            fator_arma = 2.0

        alcance_px = raio_char * fator_arma
        largura_ang = max(60.0, getattr(arma, 'largura', 30) * 2)

        debug_log(f"  Ãrea: raio_char={raio_char:.1f} fator={fator_arma} alcance_px={alcance_px:.1f} largura={largura_ang}Â°", "CALC")

        return HitboxInfo(
            tipo=tipo,
            centro=(cx, cy),
            alcance=alcance_px,
            angulo=math.degrees(rad),
            largura_angular=largura_ang,
            # FP-02 fix: sÃ³ marca ativo durante ataque (Ã© puramente visual/debug)
            ativo=lutador.atacando
        )
    
    def _calcular_hitbox_orbital(self, lutador, arma, cx, cy, fator, raio_char) -> HitboxInfo:
        """Calcula hitbox para armas orbitais"""
        # Orbital: 1.5x o raio (escudo/drone orbita perto)
        fator_arma = 1.5
        dist_orbital = raio_char * fator_arma
        
        debug_log(f"  Orbital: raio_char={raio_char:.1f} fator={fator_arma} dist_px={dist_orbital:.1f}", "CALC")
        
        return HitboxInfo(
            tipo="Orbital",
            centro=(cx, cy),
            alcance=dist_orbital,
            angulo=lutador.angulo_arma_visual,
            largura_angular=getattr(arma, 'largura', 90.0),
            ativo=True
        )
    
    def _verificar_janela_hit(self, atacante, tipo_arma: str) -> bool:
        """
        Verifica se o atacante estÃ¡ na janela de hit correta.
        MUITO MAIS GENEROSA: praticamente toda a animaÃ§Ã£o de ataque conta.
        
        A janela de hit Ã© durante as fases: ATTACK, IMPACT e quase todo FOLLOW_THROUGH
        """
        if not hasattr(atacante, 'timer_animacao'):
            return True  # Se nÃ£o tem timer, assume que pode acertar
        
        timer = atacante.timer_animacao
        
        # Se nÃ£o estÃ¡ atacando, sem hit
        if not atacante.atacando:
            return False
        
        # Tenta obter o perfil de animaÃ§Ã£o
        try:
            from efeitos.weapon_animations import WEAPON_PROFILES
            profile = WEAPON_PROFILES.get(tipo_arma, WEAPON_PROFILES.get("Reta"))
            
            if profile:
                total_time = profile.total_time
                
                # O timer comeÃ§a em total_time e vai atÃ© 0
                if total_time > 0:
                    # Calcula quanto tempo passou desde o inÃ­cio
                    tempo_passado = total_time - timer
                    
                    # Fases da animaÃ§Ã£o (tempos acumulados)
                    t_anticipation_end = profile.anticipation_time
                    t_attack_end = t_anticipation_end + profile.attack_time
                    t_impact_end = t_attack_end + profile.impact_time
                    # CM-06: t_follow_end removido â€” nunca era referenciado aqui

                    # JANELA GENEROSA:
                    # ComeÃ§a bem no inÃ­cio da fase de ataque (50% da anticipation)
                    # Vai atÃ© 90% do follow_through
                    janela_inicio = t_anticipation_end * 0.5
                    janela_fim = t_impact_end + (profile.follow_through_time * 0.9)
                    
                    # Verifica se estÃ¡ na janela
                    na_janela = janela_inicio <= tempo_passado <= janela_fim
                    
                    debug_log(f"  Janela hit: tipo={tipo_arma} t_passado={tempo_passado:.3f} " +
                             f"janela=[{janela_inicio:.3f}, {janela_fim:.3f}] ok={na_janela}", "CHECK")
                    
                    return na_janela
        except ImportError:
            pass
        
        # Fallback: muito generoso - quase toda a animaÃ§Ã£o
        # Para correntes, janela mais ampla
        if "Corrente" in tipo_arma:
            return timer < 0.7  # 70% da animaÃ§Ã£o
        # Para armas duplas, janela curta mas frequente
        elif "Dupla" in tipo_arma:
            return timer < 0.25
        # PadrÃ£o - muito generoso
        else:
            return timer < 0.5  # 50% da animaÃ§Ã£o
    
    def verificar_colisao(self, atacante, defensor) -> Tuple[bool, str]:
        """
        Verifica se o atacante acerta o defensor.
        Retorna (acertou: bool, motivo: str)
        """
        if defensor.morto:
            return False, "defensor morto"
        
        arma = atacante.dados.arma_obj
        if not arma:
            return False, "sem arma"
        
        # Armas de arremesso, arco e mÃ¡gicas causam dano APENAS atravÃ©s de projÃ©teis
        # NÃ£o verificam colisÃ£o por hitbox convencional
        if arma.tipo in ["Arremesso", "Arco", "MÃ¡gica"]:
            return False, "arma ranged/mÃ¡gica - dano via projÃ©til"
        
        # Verifica altura (Z)
        diff_z = abs(atacante.z - defensor.z)
        if diff_z > 1.5:
            debug_log(f"{atacante.dados.nome} vs {defensor.dados.nome}: Falhou - diff_z={diff_z:.2f}", "MISS")
            return False, f"altura diferente (z={diff_z:.2f})"
        
        # Calcula hitbox do atacante
        hitbox = self.calcular_hitbox_arma(atacante)
        if not hitbox:
            return False, "hitbox invÃ¡lida"
        
        # PosiÃ§Ã£o e raio do defensor
        dx = defensor.pos[0] * PPM
        dy = defensor.pos[1] * PPM
        raio_def = (defensor.dados.tamanho / 2) * PPM
        
        debug_log(f"  Defensor {defensor.dados.nome}: pos=({dx:.1f}, {dy:.1f}) raio={raio_def:.1f}px", "CHECK")
        
        # Armazena info para debug visual
        self.ultimo_ataque_info[atacante.dados.nome] = {
            'hitbox': hitbox,
            'alvo': (dx, dy, raio_def),
            'tempo': 0.5  # segundos para mostrar
        }
        
        # === COLISÃƒO POR TIPO ===
        
        # Armas ORBITAIS (escudo): sempre causam dano quando o alvo encosta
        if hitbox.tipo == "Orbital":
            # Orbitais nÃ£o precisam de janela de hit - sempre ativos
            # Verifica apenas distÃ¢ncia e Ã¢ngulo
            acertou, motivo = self._colisao_orbital(hitbox, (dx, dy), raio_def)
            
            if acertou:
                debug_log(f"  HIT! {atacante.dados.nome} -> {defensor.dados.nome} (Orbital)", "HIT")
                self.hits_registrados.append({
                    'atacante': atacante.dados.nome,
                    'defensor': defensor.dados.nome,
                    'tipo': hitbox.tipo
                })
            else:
                debug_log(f"  MISS (Orbital): {motivo}", "MISS")
            
            return acertou, motivo
        
        # Armas de corrente: verifica colisÃ£o por arco/varredura
        elif hitbox.tipo == "Corrente":
            # Verifica se estÃ¡ atacando
            if not hitbox.ativo:
                debug_log(f"  {atacante.dados.nome}: Corrente mas nÃ£o estÃ¡ atacando", "MISS")
                return False, "nÃ£o estÃ¡ atacando"
            
            # Verifica janela de animaÃ§Ã£o usando o novo sistema de fases
            hit_window_ok = self._verificar_janela_hit(atacante, "Corrente")
            if not hit_window_ok:
                debug_log(f"  {atacante.dados.nome}: Fora da janela de hit", "MISS")
                return False, "fora da janela de hit"
            
            # ColisÃ£o por arco: verifica distÃ¢ncia E se estÃ¡ dentro do arco angular
            acertou, motivo = self._colisao_arco(hitbox, (dx, dy), raio_def)
            
            if acertou:
                debug_log(f"  HIT! {atacante.dados.nome} -> {defensor.dados.nome} (Corrente)", "HIT")
                self.hits_registrados.append({
                    'atacante': atacante.dados.nome,
                    'defensor': defensor.dados.nome,
                    'tipo': hitbox.tipo
                })
            else:
                debug_log(f"  MISS: {motivo}", "MISS")
            
            return acertou, motivo
        
        # Armas de lÃ¢mina ATACANDO: usa colisÃ£o de ARCO (varredura)
        # PATH A â€” activo durante ataque e hitbox sem pontos explÃ­citos (fase ATTACK/IMPACT)
        elif hitbox.ativo and hitbox.pontos is None:
            tipo_arma = hitbox.tipo if hitbox.tipo else "Reta"
            hit_window_ok = self._verificar_janela_hit(atacante, tipo_arma)
            if not hit_window_ok:
                debug_log(f"  {atacante.dados.nome}: Fora da janela de hit (arco)", "MISS")
                return False, "fora da janela de hit"

            acertou, motivo = self._colisao_lamina_arco(hitbox, (dx, dy), raio_def)

            # FP-03 fix: segunda chance Dupla centralizada no helper
            if not acertou and "Dupla" in hitbox.tipo:
                acertou, motivo = self._colisao_dupla_offsets_arco(hitbox, (dx, dy), raio_def)

            if acertou:
                debug_log(f"  HIT! {atacante.dados.nome} -> {defensor.dados.nome} (LÃ¢mina Arco)", "HIT")
                self.hits_registrados.append({'atacante': atacante.dados.nome,
                                              'defensor': defensor.dados.nome, 'tipo': hitbox.tipo})
            else:
                debug_log(f"  MISS (arco): {motivo}", "MISS")
            return acertou, motivo

        # Armas de lÃ¢mina NÃƒO atacando ou com pontos definidos: usa linha
        # PATH B â€” fallback com pontos explÃ­citos (fase FOLLOW_THROUGH ou idle com hitbox precisa)
        elif hitbox.pontos and len(hitbox.pontos) == 2:
            if not hitbox.ativo:
                debug_log(f"  {atacante.dados.nome}: Arma de lÃ¢mina mas nÃ£o estÃ¡ atacando", "MISS")
                return False, "nÃ£o estÃ¡ atacando"

            tipo_arma = hitbox.tipo if hitbox.tipo else "Reta"
            hit_window_ok = self._verificar_janela_hit(atacante, tipo_arma)
            if not hit_window_ok:
                debug_log(f"  {atacante.dados.nome}: Fora da janela de hit", "MISS")
                return False, "fora da janela de hit"

            acertou, motivo = self._colisao_linha_circulo(
                hitbox.pontos[0], hitbox.pontos[1], (dx, dy), raio_def
            )

            # FP-03 fix: segunda chance Dupla centralizada no mesmo helper
            if not acertou and "Dupla" in hitbox.tipo:
                acertou, motivo = self._verificar_segunda_lamina(atacante, arma, (dx, dy), raio_def)

            if acertou:
                debug_log(f"  HIT! {atacante.dados.nome} -> {defensor.dados.nome}", "HIT")
                self.hits_registrados.append({'atacante': atacante.dados.nome,
                                              'defensor': defensor.dados.nome, 'tipo': hitbox.tipo})
            else:
                debug_log(f"  MISS: {motivo}", "MISS")
            return acertou, motivo
        
        # Armas de Ã¡rea: verifica distÃ¢ncia e Ã¢ngulo
        else:
            acertou_area, motivo_area = self._colisao_area(hitbox, (dx, dy), raio_def, atacante.dados.nome)
            # Cap hits_registrados to prevent unbounded growth
            if len(self.hits_registrados) > 100:
                self.hits_registrados = self.hits_registrados[-50:]
            return acertou_area, motivo_area
    
    def _colisao_linha_circulo(self, p1: Tuple[float, float], p2: Tuple[float, float],
                               centro: Tuple[float, float], raio: float) -> Tuple[bool, str]:
        """
        Verifica colisÃ£o entre linha (p1->p2) e cÃ­rculo (centro, raio).
        Retorna (colidiu, motivo)
        """
        x1, y1 = p1
        x2, y2 = p2
        cx, cy = centro
        
        # Vetor da linha
        dx_linha = x2 - x1
        dy_linha = y2 - y1
        
        # Vetor do inÃ­cio da linha atÃ© o centro do cÃ­rculo
        dx_circ = cx - x1
        dy_circ = cy - y1
        
        # Comprimento da linha ao quadrado
        len_sq = dx_linha * dx_linha + dy_linha * dy_linha
        
        if len_sq == 0:
            # Linha degenerada (ponto)
            dist = math.hypot(dx_circ, dy_circ)
            if dist <= raio:
                return True, "ponto dentro do cÃ­rculo"
            return False, f"ponto fora (dist={dist:.1f}, raio={raio:.1f})"
        
        # ProjeÃ§Ã£o do ponto no segmento (0 = p1, 1 = p2)
        t = max(0, min(1, (dx_circ * dx_linha + dy_circ * dy_linha) / len_sq))
        
        # Ponto mais prÃ³ximo na linha
        px = x1 + t * dx_linha
        py = y1 + t * dy_linha
        
        # DistÃ¢ncia do ponto mais prÃ³ximo ao centro
        dist = math.hypot(cx - px, cy - py)
        
        debug_log(f"    Linha-cÃ­rculo: t={t:.2f} ponto_proximo=({px:.1f}, {py:.1f}) dist={dist:.1f} raio={raio:.1f}", "GEOM")
        
        if dist <= raio:
            return True, f"colisÃ£o em t={t:.2f}"
        return False, f"sem colisÃ£o (dist={dist:.1f} > raio={raio:.1f})"
    
    def _colisao_dupla_offsets_arco(self, hitbox: HitboxInfo, alvo: Tuple[float, float],
                                     raio_alvo: float) -> Tuple[bool, str]:
        """
        FP-03 fix: helper centralizado para a segunda chance de colisÃ£o de armas Duplas
        no path de arco (PATH A). Evita duplicaÃ§Ã£o com _verificar_segunda_lamina (PATH B).
        Testa offsets angulares -25Â° e +25Â° para cobrir ambas as lÃ¢minas.
        """
        for offset in [-25, 25]:
            hitbox_offset = HitboxInfo(
                tipo=hitbox.tipo,
                centro=hitbox.centro,
                alcance=hitbox.alcance,
                angulo=hitbox.angulo + offset,
                largura_angular=hitbox.largura_angular,
                ativo=True
            )
            acertou, motivo = self._colisao_lamina_arco(hitbox_offset, alvo, raio_alvo)
            if acertou:
                debug_log(f"    Dupla offset arco ({offset:+}Â°) acertou!", "HIT")
                return True, f"Dupla segunda lÃ¢mina arco offset={offset}Â°"
        return False, "Dupla ambas lÃ¢minas falharam (arco)"

    def _verificar_segunda_lamina(self, atacante, arma, alvo: Tuple[float, float], 
                                   raio: float) -> Tuple[bool, str]:
        """Verifica segunda lÃ¢mina de armas duplas"""
        cx = atacante.pos[0] * PPM
        cy = atacante.pos[1] * PPM
        rad = math.radians(atacante.angulo_arma_visual)
        raio_char = (atacante.dados.tamanho / 2) * PPM
        
        # Adagas: 1.5Ã— raio (geometria removida)
        alcance_alvo = raio_char * 1.5
        cabo_px   = alcance_alvo * 0.30
        lamina_px = alcance_alvo * 0.70
        
        # Testa ambos os offsets de Ã¢ngulo
        for offset in [-25, 25]:
            r2 = rad + math.radians(offset)
            x1 = cx + math.cos(r2) * cabo_px
            y1 = cy + math.sin(r2) * cabo_px
            x2 = cx + math.cos(r2) * (cabo_px + lamina_px)
            y2 = cy + math.sin(r2) * (cabo_px + lamina_px)
            
            acertou, motivo = self._colisao_linha_circulo((x1, y1), (x2, y2), alvo, raio)
            if acertou:
                debug_log(f"    Segunda lÃ¢mina (offset={offset}Â°) acertou!", "HIT")
                return True, f"segunda lÃ¢mina offset={offset}Â°"
        
        return False, "segunda lÃ¢mina tambÃ©m falhou"
    
    def _colisao_lamina_arco(self, hitbox: HitboxInfo, alvo: Tuple[float, float],
                             raio_alvo: float) -> Tuple[bool, str]:
        """
        Verifica colisÃ£o de arco para armas de lÃ¢mina.
        Similar ao arco de correntes, mas SEM margem interna (pode acertar de perto).
        """
        cx, cy = hitbox.centro
        ax, ay = alvo
        
        # DistÃ¢ncia do centro do atacante ao centro do alvo
        dist = math.hypot(ax - cx, ay - cy)
        
        # Alcance mÃ¡ximo: alcance da arma + raio do alvo + margem
        alcance_max = hitbox.alcance + raio_alvo * 1.2
        
        debug_log(f"    LÃ¢mina arco: dist={dist:.1f} alcance_max={alcance_max:.1f}", "GEOM")
        
        if dist > alcance_max:
            return False, f"fora de alcance (dist={dist:.1f} > max={alcance_max:.1f})"
        
        # Ã‚ngulo para o alvo
        ang_para_alvo = math.degrees(math.atan2(ay - cy, ax - cx))
        
        # DiferenÃ§a angular
        diff_ang = self._normalizar_angulo(ang_para_alvo - hitbox.angulo)
        
        # Para lÃ¢minas, a margem angular Ã© metade da largura_angular
        margem = hitbox.largura_angular / 2
        
        debug_log(f"    LÃ¢mina ang: para_alvo={ang_para_alvo:.1f}Â° hitbox={hitbox.angulo:.1f}Â° diff={diff_ang:.1f}Â° margem={margem:.1f}Â°", "GEOM")
        
        if abs(diff_ang) > margem:
            return False, f"fora do arco (diff={diff_ang:.1f}Â° > margem={margem:.1f}Â°)"
        
        return True, "colisÃ£o de lÃ¢mina (arco)"
    
    def _colisao_area(self, hitbox: HitboxInfo, alvo: Tuple[float, float], 
                      raio_alvo: float, nome_atacante: str) -> Tuple[bool, str]:
        """Verifica colisÃ£o de Ã¡rea (distÃ¢ncia + Ã¢ngulo)"""
        cx, cy = hitbox.centro
        dx, dy = alvo
        
        # DistÃ¢ncia entre centros
        dist = math.hypot(dx - cx, dy - cy)
        
        # Alcance efetivo (hitbox alcanÃ§a + raio do alvo)
        alcance_efetivo = hitbox.alcance + raio_alvo
        
        debug_log(f"    Ãrea: dist={dist:.1f} alcance_efetivo={alcance_efetivo:.1f}", "GEOM")
        
        if dist > alcance_efetivo:
            return False, f"fora de alcance (dist={dist:.1f} > alcance={alcance_efetivo:.1f})"
        
        # Ã‚ngulo para o alvo
        ang_para_alvo = math.degrees(math.atan2(dy - cy, dx - cx))
        
        # DiferenÃ§a angular
        diff_ang = self._normalizar_angulo(ang_para_alvo - hitbox.angulo)
        
        debug_log(f"    Ã‚ngulo: para_alvo={ang_para_alvo:.1f}Â° hitbox={hitbox.angulo:.1f}Â° diff={diff_ang:.1f}Â° margem={hitbox.largura_angular/2:.1f}Â°", "GEOM")
        
        if abs(diff_ang) > hitbox.largura_angular / 2:
            return False, f"fora do arco (diff={diff_ang:.1f}Â° > margem={hitbox.largura_angular/2:.1f}Â°)"
        
        return True, "colisÃ£o de Ã¡rea confirmada"
    
    def _colisao_orbital(self, hitbox: HitboxInfo, alvo: Tuple[float, float],
                         raio_alvo: float) -> Tuple[bool, str]:
        """
        Verifica colisÃ£o para armas orbitais (escudo, drone).
        O orbital gira ao redor do personagem e causa dano quando colide.
        
        Verifica se o alvo estÃ¡ prÃ³ximo da posiÃ§Ã£o atual do orbital.
        """
        cx, cy = hitbox.centro
        ax, ay = alvo
        
        # PosiÃ§Ã£o atual do orbital (no Ã¢ngulo visual)
        rad = math.radians(hitbox.angulo)
        orbital_x = cx + math.cos(rad) * hitbox.alcance
        orbital_y = cy + math.sin(rad) * hitbox.alcance
        
        # DistÃ¢ncia do orbital ao centro do alvo
        dist = math.hypot(ax - orbital_x, ay - orbital_y)
        
        # Raio do orbital (largura estÃ¡ em CENTÃMETROS -> converter para pixels)
        # largura_angular aqui guarda a largura do escudo em cm
        # cm -> m -> px: (cm / 100) * PPM
        raio_orbital = (hitbox.largura_angular / 100.0) * PPM * 0.5
        
        # Garantir raio mÃ­nimo visÃ­vel
        raio_orbital = max(raio_orbital, 15.0)  # mÃ­nimo 15px
        
        # Raio de colisÃ£o generoso: orbital + alvo + margem
        raio_colisao = raio_orbital + raio_alvo + 5  # +5px de margem
        
        debug_log(f"    Orbital: pos=({orbital_x:.1f}, {orbital_y:.1f}) dist={dist:.1f} raio_col={raio_colisao:.1f} (raio_orb={raio_orbital:.1f})", "GEOM")
        
        if dist <= raio_colisao:
            return True, "colisÃ£o orbital (escudo)"
        
        return False, f"orbital fora de alcance (dist={dist:.1f} > raio={raio_colisao:.1f})"
    
    def _colisao_arco(self, hitbox: HitboxInfo, alvo: Tuple[float, float],
                      raio_alvo: float) -> Tuple[bool, str]:
        """
        Verifica colisÃ£o de arco (para correntes/mangual).
        BUG-07 fix: usa hitbox.alcance_minimo definido pelo perfil, sem recalcular.
        """
        cx, cy = hitbox.centro
        ax, ay = alvo

        dist = math.hypot(ax - cx, ay - cy)

        # BUG-07 fix: usa zona morta calculada centralmente no perfil
        alcance_min = hitbox.alcance_minimo
        alcance_max = hitbox.alcance + raio_alvo * 1.5

        debug_log(f"    Arco: dist={dist:.1f} alcance_min={alcance_min:.1f} alcance_max={alcance_max:.1f}", "GEOM")

        if dist < alcance_min:
            return False, f"muito perto para corrente (dist={dist:.1f} < min={alcance_min:.1f})"

        if dist > alcance_max:
            return False, f"fora de alcance (dist={dist:.1f} > max={alcance_max:.1f})"

        ang_para_alvo = math.degrees(math.atan2(ay - cy, ax - cx))
        diff_ang = self._normalizar_angulo(ang_para_alvo - hitbox.angulo)

        debug_log(f"    Arco ang: para_alvo={ang_para_alvo:.1f}Â° hitbox={hitbox.angulo:.1f}Â° diff={diff_ang:.1f}Â° margem={hitbox.largura_angular/2:.1f}Â°", "GEOM")

        if abs(diff_ang) > hitbox.largura_angular / 2:
            return False, f"fora do arco (diff={diff_ang:.1f}Â° > margem={hitbox.largura_angular/2:.1f}Â°)"

        return True, "colisÃ£o de arco (corrente)"
    
    def _normalizar_angulo(self, ang: float) -> float:
        """Normaliza Ã¢ngulo para -180 a 180"""
        while ang > 180:
            ang -= 360
        while ang < -180:
            ang += 360
        return ang
    
    def atualizar_debug_visual(self, dt: float):
        """Atualiza timers de debug visual"""
        for nome in list(self.ultimo_ataque_info.keys()):
            self.ultimo_ataque_info[nome]['tempo'] -= dt
            if self.ultimo_ataque_info[nome]['tempo'] <= 0:
                del self.ultimo_ataque_info[nome]
    
    def get_debug_info(self) -> dict:
        """Retorna info de debug para renderizaÃ§Ã£o"""
        return {
            'ataques': self.ultimo_ataque_info.copy(),
            'hits': self.hits_registrados[-10:] if self.hits_registrados else []
        }
    
    def limpar_historico(self):
        """Limpa histÃ³rico de hits"""
        self.hits_registrados.clear()


# InstÃ¢ncia global do sistema
sistema_hitbox = SistemaHitbox()


def verificar_hit(atacante, defensor) -> Tuple[bool, str]:
    """FunÃ§Ã£o de conveniÃªncia para verificar hit"""
    return sistema_hitbox.verificar_colisao(atacante, defensor)


def get_debug_visual():
    """Retorna dados para debug visual"""
    return sistema_hitbox.get_debug_info()


def atualizar_debug(dt: float):
    """Atualiza sistema de debug"""
    sistema_hitbox.atualizar_debug_visual(dt)

