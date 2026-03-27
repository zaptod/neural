"""Auto-generated mixin Ã¢â‚¬â€ gerado por scripts/split_simulacao.py (arquivado em _archive/scripts/)"""
from dataclasses import dataclass
import pygame
import logging
_log = logging.getLogger("simulacao")  # QC-02
import json
import math
import random
import sys
import os
import unicodedata

# Adiciona o diretÃ³rio pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilitarios.config import (
    PPM, LARGURA, ALTURA, LARGURA_PORTRAIT, ALTURA_PORTRAIT, FPS,
    BRANCO, VERMELHO_SANGUE, SANGUE_ESCURO, AMARELO_FAISCA,
    AZUL_MANA, COR_CORPO, COR_P1, COR_P2, COR_FUNDO, COR_GRID,
    COR_UI_BG, COR_TEXTO_TITULO, COR_TEXTO_INFO,
)
from utilitarios.estado_espectador import resolver_badges_estado, resolver_destaque_cinematico
from efeitos import (Particula, FloatingText, Decal, Shockwave, Camera, EncantamentoEffect,
                     ImpactFlash, MagicClash, BlockEffect, DashTrail, HitSpark,
                     MovementAnimationManager, MovementType,  # v8.0 Movement Animations
                     AttackAnimationManager, calcular_knockback_com_forca, get_impact_tier,  # v8.0 Attack Animations
                     MagicVFXManager, ELEMENT_PALETTES, get_element_from_skill)  # v11.0 Magic VFX
from efeitos.audio import AudioManager  # v10.0 Sistema de Ãudio
from nucleo.entities import Lutador
from nucleo.skills import get_skill_classification
from nucleo.armas import inferir_familia, resolver_subtipo_orbital
from nucleo.physics import colisao_linha_circulo, intersect_line_circle, colisao_linha_linha, normalizar_angulo
from nucleo.hitbox import sistema_hitbox, verificar_hit, get_debug_visual, atualizar_debug, DEBUG_VISUAL
from nucleo.arena import Arena, ARENAS, get_arena, set_arena  # v9.0 Sistema de Arena

# v13.0: Paleta de cores por time para rendering multi-fighter
CORES_TIME_RENDER = [
    (231, 76, 60),    # Time 0 - Vermelho
    (52, 152, 219),   # Time 1 - Azul
    (46, 204, 113),   # Time 2 - Verde
    (243, 156, 18),   # Time 3 - Amarelo
]
from ia import CombatChoreographer  # Sistema de Coreografia v5.0
from nucleo.game_feel import GameFeelManager, HitStopManager  # Sistema de Game Feel v8.0


def _texto_normalizado(valor) -> str:
    """Normaliza texto para comparacoes robustas no renderer."""
    texto = str(valor or "").replace("?", " ")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.lower().split())


@dataclass(frozen=True)
class RenderFrameContext:
    """Snapshot leve do frame para manter o pipeline de desenho deterministico."""

    fundo: tuple
    pulse_time: float
    lutadores_ordenados: list


@dataclass(frozen=True)
class FighterRenderContext:
    """Snapshot do render do lutador para reduzir acoplamento na montagem do frame."""

    lutador: object
    arma: object
    sx: int
    sy: int
    off_y: int
    raio: int
    centro: tuple
    cor_corpo: tuple
    cor_contorno: tuple
    largura_contorno: int
    sombra_d: int
    tam_sombra: int
    pulse_time: float
    anim_scale: float
    centro_arma: tuple
    tipo_arma_norm: str
    desenha_slash_arc: bool


@dataclass(frozen=True)
class WeaponRenderContext:
    """Snapshot visual da arma para reduzir acoplamento no renderer."""

    arma: object
    centro: tuple
    cx: float
    cy: float
    angulo: float
    rad: float
    tam_char: float
    raio_char: float
    anim_scale: float
    zoom: float
    cor: tuple
    cor_clara: tuple
    cor_escura: tuple
    raridade_norm: str
    cor_raridade: tuple
    tipo: str
    tipo_norm: str
    estilo_arma: str
    estilo_norm: str
    base_scale: float
    larg_base: int
    atacando: bool
    tempo: int

    def zw(self, px):
        return max(1, int(px * self.zoom))


@dataclass(frozen=True)
class WeaponPresenceRenderContext:
    """Snapshot da presenca visual da arma ao redor do lutador."""

    lutador: object
    arma: object
    centro: tuple
    raio: float
    anim_scale: float
    perfil_visual: dict
    cor: tuple
    tipo: str
    familia: str
    rad: float
    alcance: float
    tip_x: float
    tip_y: float
    intensidade: float
    brilho: float
    aura_alpha: int
    glow_r: int
    ornamento: str
    perp_x: float
    perp_y: float
    tempo_ticks: int
    paleta: object


@dataclass(frozen=True)
class SlashArcRenderContext:
    """Snapshot do arco de corte para manter o efeito em pipeline explicito."""

    lutador: object
    arma: object
    centro: tuple
    zoom: float
    cor: tuple
    cor_brilho: tuple
    cor_glow: tuple
    arc_start: float
    current_arc: float
    arc_radius: float
    fade: float
    alpha_base: int
    arc_width_factor: float
    surf_size: int
    arc_center: tuple
    num_points: int


@dataclass(frozen=True)
class WeaponTrailRenderContext:
    """Snapshot do trail da arma para separar coleta, integraçao e desenho local."""

    lutador: object
    arma: object
    cor: tuple
    cor_brilho: tuple
    tipo: str
    tipo_norm: str
    estilo: str
    zoom: float
    screen_pts: list
    profile: object


@dataclass(frozen=True)
class ProjectileFrameRenderContext:
    """Snapshot do projetil no frame para separar trail, glow e corpo visual."""

    proj: object
    pulse_time: float
    px: int
    py: int
    pr: int
    cor: tuple
    tipo_proj: str
    ang_visual: float
    rad: float


@dataclass(frozen=True)
class HitboxDebugRenderContext:
    """Snapshot da hitbox em debug para separar coleta e desenho por tipo."""

    lutador: object
    hitbox: object
    cor_debug: tuple
    cx_screen: int
    cy_screen: int
    off_y: int
    alcance_screen: int


@dataclass(frozen=True)
class MagicProjectileRenderContext:
    """Snapshot visual do projetil magico para manter o pipeline explicito."""

    proj: object
    classe: dict
    perfil: dict
    assinatura_especifica: dict
    elemento: str
    paleta: dict
    assinatura: str
    utilidade: str
    forca: str
    variante: str
    px: float
    py: float
    pr: float
    pulse_time: float
    ang_visual: float
    cor: tuple
    rad: float
    drift: float
    tail_len: float
    tail_x: float
    tail_y: float


@dataclass(frozen=True)
class MagicOrbRenderContext:
    """Snapshot visual do orbe magico para manter o fluxo previsivel."""

    orbe: object
    ox: float
    oy: float
    or_visual: float
    classe: dict
    perfil: dict
    elemento: str
    paleta: dict
    assinatura: str
    utilidade: str
    pulso: float


@dataclass(frozen=True)
class MagicBeamRenderContext:
    """Snapshot visual do beam magico para manter o fluxo deterministico."""

    beam: object
    pulse_time: float
    pts_screen: list
    classe: dict
    perfil: dict
    assinatura: dict
    elemento: str
    paleta: dict
    pulse: float
    forca: str
    utilidade: str
    largura_efetiva: int
    min_x: int
    min_y: int
    width: int
    height: int
    local_pts: list


@dataclass(frozen=True)
class MagicAreaRenderContext:
    """Snapshot visual da area magica para manter o telegraph organizado."""

    area: object
    pulse_time: float
    ax: int
    ay: int
    ar: int
    classe: dict
    perfil: dict
    assinatura: dict
    elemento: str
    paleta: dict
    utilidade: str
    forca: str
    ativo: bool
    pulse: float
    alpha_base: int
    raio_visual: int
    zonal: bool
    suporte: bool
    invocacao: bool
    cataclismo: bool


@dataclass(frozen=True)
class MagicCircularPatternContext:
    """Snapshot leve do motivo circular para separar setup de roteamento visual."""

    x: float
    y: float
    raio: int
    paleta: dict
    perfil: dict
    tempo: float
    intensidade: float
    motivo: str
    ornamento: str
    alpha: int


@dataclass(frozen=True)
class BuffRenderContext:
    """Snapshot visual de um buff orbitando o lutador."""

    buff: object
    idx: int
    centro: tuple
    raio: float
    pulse_time: float
    classe: dict
    perfil: dict
    assinatura: dict
    elemento: str
    paleta: dict
    progresso: float
    aura_r: int
    variante: str


@dataclass(frozen=True)
class SummonRenderContext:
    """Snapshot visual da invocacao para separar setup e pipeline de desenho."""

    summon: object
    pulse_time: float
    sx: int
    sy: int
    raio: int
    classe: dict
    perfil: dict
    assinatura: dict
    elemento: str
    paleta: dict
    centro: tuple
    base_r: int
    variante: str


@dataclass(frozen=True)
class TrapRenderContext:
    """Snapshot visual da armadilha magica para separar estado e apresentação."""

    trap: object
    pulse_time: float
    tx: int
    ty: int
    traio: int
    classe: dict
    perfil: dict
    assinatura: dict
    elemento: str
    paleta: dict
    variante: str


@dataclass(frozen=True)
class HudMultiLayout:
    """Layout compartilhado do HUD multi antes do desenho por time."""

    times: dict
    num_times: int
    bar_w: int
    bar_h: int
    mana_h: int
    nome_h: int
    slot_h: int


@dataclass(frozen=True)
class HudMultiTeamLayout:
    """Snapshot de um bloco de time no HUD multi."""

    team_id: int
    members: list
    team_index: int
    base_x: int
    cor_time: tuple
    layout: HudMultiLayout


class SimuladorRenderer:
    """Mixin de renderizaÃ§Ã£o: desenho de lutadores, armas, UI e debug."""

    # Ã¢â€â‚¬Ã¢â€â‚¬ FONT CACHE Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ evita criar fontes a cada frame (perf-fix)
    _font_cache = {}

    @classmethod
    def _get_font(cls, name, size, bold=False):
        if not pygame.font.get_init():
            pygame.font.init()
        key = (name, size, bold)
        if key not in cls._font_cache:
            cls._font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
        return cls._font_cache[key]

    # â”€â”€ SURFACE CACHE (A01) â”€â”€â”€ evita alocar pygame.Surface(SRCALPHA) todo frame
    # Chave: (width, height, flags). fill() limpa sem realocar memÃ³ria.
    _surface_cache: dict = {}

    @classmethod
    def _get_surface(cls, width: int, height: int, flags: int = 0) -> "pygame.Surface":
        """Retorna Surface cacheada e limpa (fill transparente). Usar apenas na thread pygame."""
        key = (width, height, flags)
        surf = cls._surface_cache.get(key)
        if surf is None:
            surf = pygame.Surface((width, height), flags)
            cls._surface_cache[key] = surf
        else:
            surf.fill((0, 0, 0, 0))
        return surf

    def _cor_com_alpha(self, cor, alpha):
        rgb = tuple(int(max(0, min(255, c))) for c in cor[:3])
        return (*rgb, int(max(0, min(255, alpha))))

    def _misturar_cor(self, cor_a, cor_b, ratio):
        ratio = max(0.0, min(1.0, ratio))
        return tuple(int(cor_a[i] + (cor_b[i] - cor_a[i]) * ratio) for i in range(3))

    def _desenhar_badges_estado(self, lutador, x, y, *, align_right=False, compact=False, max_badges=2):
        badges = resolver_badges_estado(lutador, max_badges=max_badges)
        if not badges:
            return

        font_size = 10 if compact else (11 if self.portrait_mode else 12)
        font = self._get_font("Arial", font_size, bold=True)
        padding_x = 6 if compact else 8
        badge_h = 14 if compact else (16 if self.portrait_mode else 18)
        spacing = 4

        total_w = 0
        renders = []
        for badge in badges:
            surf = font.render(str(badge.get("texto", "")), True, badge.get("fg", BRANCO))
            rect_w = surf.get_width() + padding_x * 2
            total_w += rect_w
            renders.append((badge, surf, rect_w))
        total_w += spacing * max(0, len(renders) - 1)

        cursor_x = x - total_w if align_right else x
        for badge, surf, rect_w in renders:
            rect = pygame.Rect(cursor_x, y, rect_w, badge_h)
            pygame.draw.rect(self.tela, badge.get("bg", (40, 40, 40)), rect, border_radius=badge_h // 2)
            pygame.draw.rect(self.tela, badge.get("borda", BRANCO), rect, 1, border_radius=badge_h // 2)
            text_y = rect.y + (badge_h - surf.get_height()) // 2 - 1
            self.tela.blit(surf, (rect.x + padding_x, text_y))
            cursor_x += rect_w + spacing

    def _desenhar_overlay_cinematico(self):
        destaque = getattr(self, "direcao_cinematica", None) or resolver_destaque_cinematico(getattr(self, "fighters", []))
        if not isinstance(destaque, dict):
            return

        intensidade = max(0.0, min(1.0, float(destaque.get("intensidade", 0.0) or 0.0)))
        overlay_timer = max(0.0, float(destaque.get("overlay_timer", destaque.get("duracao_overlay", 0.0)) or 0.0))
        if intensidade <= 0.08 and overlay_timer <= 0.0:
            return

        pulse_time = pygame.time.get_ticks() / 1000.0
        pulso = 0.75 + 0.25 * math.sin(pulse_time * 7.0)
        overlay_mix = max(intensidade * 0.75, min(1.0, overlay_timer / max(float(destaque.get("duracao_overlay", 0.25) or 0.25), 0.01)))
        alpha_base = int(18 + 68 * destaque.get("overlay", 0.4) * overlay_mix * pulso)
        cor = tuple(int(c) for c in destaque.get("cor", (255, 200, 120)))
        cor_sec = tuple(int(c) for c in destaque.get("cor_secundaria", (255, 240, 180)))

        overlay = self._get_surface(self.screen_width, self.screen_height, pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*cor, min(110, alpha_base)), overlay.get_rect(), width=max(4, int(self.screen_width * 0.008)), border_radius=22)
        band_h = max(36, int(self.screen_height * 0.055))
        self._draw_gradient_band(overlay, pygame.Rect(0, 0, self.screen_width, band_h), cor, cor_sec, min(76, alpha_base))
        self._draw_gradient_band(overlay, pygame.Rect(0, self.screen_height - band_h, self.screen_width, band_h), cor_sec, cor, min(58, alpha_base))
        self.tela.blit(overlay, (0, 0))

        label = str(destaque.get("rotulo", "")).upper()
        if label:
            font = self._get_font("Impact", 18 if self.portrait_mode else 22, bold=False)
            surf = font.render(label, True, cor_sec)
            badge_w = surf.get_width() + 28
            badge_h = surf.get_height() + 10
            badge_x = self.screen_width // 2 - badge_w // 2
            badge_y = 10 if self.portrait_mode else 12
            badge = pygame.Rect(badge_x, badge_y, badge_w, badge_h)
            pygame.draw.rect(self.tela, (10, 14, 22), badge, border_radius=badge_h // 2)
            pygame.draw.rect(self.tela, cor, badge, 2, border_radius=badge_h // 2)
            self.tela.blit(surf, (badge.x + 14, badge.y + 3))

    def _draw_gradient_band(self, surface, rect, cor_a, cor_b, alpha):
        band = self._get_surface(rect.width, rect.height, pygame.SRCALPHA)
        span = max(1, rect.width)
        for idx in range(span):
            t = idx / max(1, span - 1)
            color = (
                int(cor_a[0] + (cor_b[0] - cor_a[0]) * t),
                int(cor_a[1] + (cor_b[1] - cor_a[1]) * t),
                int(cor_a[2] + (cor_b[2] - cor_a[2]) * t),
                int(alpha),
            )
            pygame.draw.line(band, color, (idx, 0), (idx, rect.height))
        surface.blit(band, rect.topleft)

    def _paleta_magica(self, elemento=None, cor_base=None):
        paleta = ELEMENT_PALETTES.get(elemento or "DEFAULT", ELEMENT_PALETTES["DEFAULT"])
        if not cor_base:
            return paleta
        base = tuple(int(max(0, min(255, c))) for c in cor_base[:3])
        return {
            "core": self._misturar_cor(paleta["core"], (255, 255, 255), 0.25),
            "mid": [self._misturar_cor(c, base, 0.35) for c in paleta["mid"]],
            "outer": [self._misturar_cor(c, base, 0.55) for c in paleta["outer"]],
            "spark": self._misturar_cor(paleta["spark"], base, 0.25),
            "glow": (*self._misturar_cor(paleta["glow"][:3], base, 0.45), paleta["glow"][3]),
        }

    def _detectar_elemento_visual(self, nome="", tipo="", elemento=None):
        if elemento:
            return str(elemento).upper()
        return get_element_from_skill(str(nome or tipo), {"elemento": elemento} if elemento else {})

    def _resolver_classe_magia(self, entidade=None, nome="", tipo="", elemento=None):
        classe = getattr(entidade, "classe_magia", None) if entidade is not None else None
        if isinstance(classe, dict) and classe:
            return classe
        skill_nome = getattr(entidade, "nome", "") if entidade is not None else nome
        skill_tipo = getattr(entidade, "tipo", "") if entidade is not None else tipo
        skill_elemento = getattr(entidade, "elemento", None) if entidade is not None else elemento
        if skill_nome:
            classificacao = get_skill_classification(str(skill_nome))
        else:
            classificacao = get_skill_classification(str(skill_tipo))
        resultado = classificacao.to_dict()
        if skill_tipo and resultado.get("tipo") == "NADA":
            resultado["tipo"] = str(skill_tipo).upper()
        if skill_elemento and resultado.get("elemento") == "NEUTRO":
            resultado["elemento"] = str(skill_elemento).upper()
        if skill_tipo == "ORBE" and resultado.get("assinatura_visual") == "cometa":
            resultado["assinatura_visual"] = "anel"
            resultado["classe_forca"] = "PRESSAO"
            resultado["classe_utilidade"] = "DANO"
        return resultado

    def _perfil_visual_magia(self, classe):
        utilidade = str(classe.get("classe_utilidade", "DANO") or "DANO").upper()
        forca = str(classe.get("classe_forca", "IMPACTO") or "IMPACTO").upper()
        perfil = {
            "motivo": "impacto",
            "ornamento": "cometa",
            "marcas": 6,
            "perigo": 1.0,
            "suavidade": 0.55,
        }

        if utilidade == "PROTECAO":
            perfil.update({"motivo": "protecao", "ornamento": "hexagono", "marcas": 6, "suavidade": 0.85})
        elif utilidade == "CURA":
            perfil.update({"motivo": "cura", "ornamento": "petalas", "marcas": 5, "suavidade": 0.95})
        elif utilidade == "INVOCACAO":
            perfil.update({"motivo": "invocacao", "ornamento": "triangulos", "marcas": 3, "suavidade": 0.7})
        elif utilidade in {"CONTROLE", "ZONA"}:
            perfil.update({"motivo": "controle", "ornamento": "grade", "marcas": 8, "perigo": 1.15, "suavidade": 0.45})
        elif utilidade == "DISRUPCAO":
            perfil.update({"motivo": "disrupcao", "ornamento": "fratura", "marcas": 7, "perigo": 1.18, "suavidade": 0.42})
        elif utilidade == "AMPLIFICACAO":
            perfil.update({"motivo": "amplificacao", "ornamento": "chevrons", "marcas": 4, "suavidade": 0.8})
        elif utilidade == "MOBILIDADE":
            perfil.update({"motivo": "mobilidade", "ornamento": "setas", "marcas": 3, "perigo": 0.95, "suavidade": 0.6})

        if forca == "CATACLISMO":
            perfil.update({"ornamento": "espinhos", "perigo": max(perfil["perigo"], 1.45), "marcas": max(perfil["marcas"], 10)})
        elif forca == "PRECISAO":
            perfil.update({"ornamento": "mira" if perfil["ornamento"] == "cometa" else perfil["ornamento"], "marcas": max(perfil["marcas"], 4)})
        elif forca == "PRESSAO":
            perfil.update({"ornamento": "orbitas" if perfil["ornamento"] == "cometa" else perfil["ornamento"], "marcas": max(perfil["marcas"], 5)})
        elif forca == "SUPORTE":
            perfil["suavidade"] = max(perfil["suavidade"], 0.9)

        perfil["utilidade"] = utilidade
        perfil["forca"] = forca
        return perfil

    def _assinatura_magia_especifica(self, entidade=None, nome="", tipo=""):
        skill_nome = _texto_normalizado(getattr(entidade, "nome", "") if entidade is not None else nome)
        skill_tipo = str(getattr(entidade, "tipo", "") if entidade is not None else tipo).upper()
        especiais = {
            "bola de fogo": {"variante": "bola_fogo", "familia": "projetil"},
            "cometa": {"variante": "cometa_rastreador", "familia": "projetil"},
            "meteoro": {"variante": "meteoro_brutal", "familia": "projetil"},
            "lanca de luz": {"variante": "lanca_luz", "familia": "projetil"},
            "lanca de gelo": {"variante": "lanca_gelo", "familia": "projetil"},
            "misseis arcanos": {"variante": "misseis_arcanos", "familia": "projetil"},
            "orbe de mana": {"variante": "orbe_mana", "familia": "projetil"},
            "mjolnir": {"variante": "martelo_trovao", "familia": "projetil"},
            "sentenca do vazio": {"variante": "sentenca_void", "familia": "projetil"},
            "pilar de fogo": {"variante": "pilar_fogo", "familia": "area"},
            "julgamento celestial": {"variante": "julgamento_celestial", "familia": "area"},
            "redencao": {"variante": "redencao", "familia": "area"},
            "nevasca": {"variante": "nevasca", "familia": "area"},
            "zero absoluto": {"variante": "zero_absoluto", "familia": "area"},
            "tempestade": {"variante": "tempestade", "familia": "area"},
            "julgamento de thor": {"variante": "julgamento_thor", "familia": "area"},
            "aniquilacao": {"variante": "aniquilacao_void", "familia": "area"},
            "colapso do vazio": {"variante": "colapso_void", "familia": "area"},
            "implosao": {"variante": "implosao_void", "familia": "area"},
            "chamas do dragao": {"variante": "sopro_dragao", "familia": "beam"},
            "desintegrar": {"variante": "desintegrar", "familia": "beam"},
            "raio sagrado": {"variante": "raio_sagrado", "familia": "beam"},
            "corrente em cadeia": {"variante": "corrente_cadeia", "familia": "beam"},
            "devorar": {"variante": "devorar", "familia": "beam"},
            "rasgo dimensional": {"variante": "rasgo_dimensional", "familia": "beam"},
            "escudo arcano": {"variante": "escudo_arcano", "familia": "buff"},
            "falange prismatica": {"variante": "escudo_arcano", "familia": "buff"},
            "barreira divina": {"variante": "barreira_divina", "familia": "buff"},
            "escudo de brasas": {"variante": "escudo_brasas", "familia": "buff"},
            "absorcao do vazio": {"variante": "absorcao_vazio", "familia": "buff"},
            "cura maior": {"variante": "cura_maior", "familia": "buff"},
            "purificar": {"variante": "purificar", "familia": "buff"},
            "sobrecarga": {"variante": "sobrecarga", "familia": "buff"},
            "amplificar magia": {"variante": "amplificar_magia", "familia": "buff"},
            "conjuracao perfeita": {"variante": "conjuracao_perfeita", "familia": "buff"},
            "fenix": {"variante": "fenix", "familia": "summon"},
            "enxame astral": {"variante": "espirito_arcano", "familia": "summon"},
            "invocacao: espirito": {"variante": "espirito_arcano", "familia": "summon"},
            "portal do vazio": {"variante": "portal_vazio", "familia": "summon"},
            "anomalia espacial": {"variante": "anomalia_espacial", "familia": "summon"},
            "mare prismatica": {"variante": "tempestade", "familia": "area"},
            "muralha de gelo": {"variante": "muralha_gelo", "familia": "trap"},
            "espelho de gelo": {"variante": "espelho_gelo", "familia": "trap"},
            "prisao de luz": {"variante": "prisao_luz", "familia": "trap"},
            "armadilha incendiaria": {"variante": "armadilha_incendiaria", "familia": "trap"},
            "armadilha eletrica": {"variante": "armadilha_eletrica", "familia": "trap"},
            "laminas de saturno": {"variante": "misseis_arcanos", "familia": "projetil"},
            "avatar de gelo": {"variante": "avatar_gelo", "familia": "transform"},
            "forma relampago": {"variante": "forma_relampago", "familia": "transform"},
            "forma do vazio": {"variante": "forma_vazio", "familia": "transform"},
        }
        assinatura = dict(especiais.get(skill_nome, {}))
        if not assinatura:
            if "orbe" in skill_nome and skill_tipo == "PROJETIL":
                assinatura = {"variante": "orbe_mana", "familia": "projetil"}
            elif "portal" in skill_nome:
                assinatura = {"variante": "portal", "familia": "invocacao"}
            else:
                assinatura = {"variante": "", "familia": ""}
        assinatura["nome"] = skill_nome
        return assinatura

    def _desenhar_glow_circular(self, x, y, raio, cor, alpha, layers=4):
        raio = int(max(2, raio))
        for idx in range(layers, 0, -1):
            layer_r = int(raio * (0.45 + idx / layers))
            layer_alpha = alpha * (idx / layers) * 0.32
            surf = self._get_surface(layer_r * 2 + 6, layer_r * 2 + 6, pygame.SRCALPHA)
            pygame.draw.circle(
                surf,
                self._cor_com_alpha(cor, layer_alpha),
                (layer_r + 3, layer_r + 3),
                layer_r,
            )
            self.tela.blit(surf, (int(x) - layer_r - 3, int(y) - layer_r - 3))

    def _desenhar_sigilo_magico(self, x, y, raio, paleta, tempo, intensidade=1.0):
        raio = int(max(6, raio))
        anel = self._get_surface(raio * 2 + 12, raio * 2 + 12, pygame.SRCALPHA)
        centro = raio + 6
        pygame.draw.circle(anel, self._cor_com_alpha(paleta["mid"][0], 70 * intensidade), (centro, centro), raio, 2)
        for i in range(6):
            ang = tempo * (1.2 + i * 0.06) + i * (math.pi * 2 / 6)
            x1 = centro + math.cos(ang) * raio * 0.55
            y1 = centro + math.sin(ang) * raio * 0.55
            x2 = centro + math.cos(ang) * raio
            y2 = centro + math.sin(ang) * raio
            pygame.draw.line(
                anel,
                self._cor_com_alpha(paleta["spark"], 150 * intensidade),
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                2,
            )
        self.tela.blit(anel, (int(x) - centro, int(y) - centro))

    def _pontos_poligono_regular(self, x, y, raio, lados, rotacao=0.0, fator_intercalado=1.0):
        pontos = []
        lados = max(3, int(lados))
        for i in range(lados):
            ang = rotacao + i * (math.pi * 2 / lados)
            dist = raio * (fator_intercalado if i % 2 == 0 else 1.0)
            pontos.append((x + math.cos(ang) * dist, y + math.sin(ang) * dist))
        return pontos

    def _desenhar_arco_magico(self, x, y, raio, cor, alpha, ang_inicio, ang_fim, largura=2):
        raio = int(max(4, raio))
        surf = self._get_surface(raio * 2 + 12, raio * 2 + 12, pygame.SRCALPHA)
        pygame.draw.arc(
            surf,
            self._cor_com_alpha(cor, alpha),
            pygame.Rect(6, 6, raio * 2, raio * 2),
            ang_inicio,
            ang_fim,
            max(1, int(largura)),
        )
        self.tela.blit(surf, (int(x) - raio - 6, int(y) - raio - 6))

    def _gerar_linha_zigzag(self, x1, y1, x2, y2, amplitude, segmentos=6, fase=0.0):
        pontos = [(x1, y1)]
        segmentos = max(2, int(segmentos))
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist <= 0.001:
            return [(x1, y1), (x2, y2)]
        perp_x = -dy / dist
        perp_y = dx / dist
        for i in range(1, segmentos):
            t = i / segmentos
            sway = amplitude * math.sin(fase + i * math.pi) * (1 if i % 2 == 0 else -1)
            pontos.append((x1 + dx * t + perp_x * sway, y1 + dy * t + perp_y * sway))
        pontos.append((x2, y2))
        return pontos

    def _coletar_buffs_visuais_ativos(self, lutador):
        return [buff for buff in getattr(lutador, "buffs_ativos", []) if getattr(buff, "ativo", True)]

    def _criar_contexto_buff_lutador(self, buff, idx, centro, raio, pulse_time):
        classe = self._resolver_classe_magia(buff)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(buff, tipo="BUFF")
        elemento = self._detectar_elemento_visual(getattr(buff, "nome", ""), "BUFF", getattr(buff, "elemento", None))
        paleta = self._paleta_magica(elemento, getattr(buff, "cor", None))
        progresso = max(0.0, min(1.0, getattr(buff, "vida", 0.0) / max(getattr(buff, "duracao", 1.0), 0.001)))
        return BuffRenderContext(
            buff=buff,
            idx=idx,
            centro=centro,
            raio=raio,
            pulse_time=pulse_time,
            classe=classe,
            perfil=perfil,
            assinatura=assinatura,
            elemento=elemento,
            paleta=paleta,
            progresso=progresso,
            aura_r=int(raio * (1.25 + idx * 0.2)),
            variante=assinatura.get("variante", ""),
        )

    def _desenhar_base_buff_lutador(self, contexto):
        self._desenhar_glow_circular(
            contexto.centro[0],
            contexto.centro[1],
            int(contexto.aura_r * (0.95 + contexto.perfil["suavidade"] * 0.2)),
            contexto.paleta["outer"][0],
            28 + 22 * contexto.progresso,
            3,
        )
        self._desenhar_motivo_circular_magia(
            contexto.centro[0],
            contexto.centro[1],
            contexto.aura_r,
            contexto.paleta,
            contexto.perfil,
            contexto.pulse_time + contexto.idx * 0.35,
            0.48 + contexto.progresso * 0.25,
        )

    def _desenhar_escudo_buff_lutador(self, contexto):
        if getattr(contexto.buff, "escudo", 0) <= 0:
            return
        escudo_pct = max(0.0, min(1.0, getattr(contexto.buff, "escudo_atual", contexto.buff.escudo) / max(contexto.buff.escudo, 0.001)))
        shell = self._pontos_poligono_regular(contexto.centro[0], contexto.centro[1], contexto.aura_r * 1.08, 6, contexto.pulse_time * 0.22 + contexto.idx * 0.3)
        pygame.draw.polygon(
            self.tela,
            self._cor_com_alpha(contexto.paleta["mid"][0], 90 + 65 * escudo_pct),
            [(int(px), int(py)) for px, py in shell],
            max(1, int(2 + escudo_pct * 2)),
        )

    def _desenhar_variante_buff_escudo_arcano(self, contexto):
        self._desenhar_sigilo_magico(contexto.centro[0], contexto.centro[1], int(contexto.aura_r * 0.88), contexto.paleta, contexto.pulse_time * 0.8, 0.72)
        self._desenhar_sigilo_magico(contexto.centro[0], contexto.centro[1], int(contexto.aura_r * 0.58), contexto.paleta, -contexto.pulse_time * 0.95, 0.45)

    def _desenhar_variante_buff_barreira_divina(self, contexto):
        self._desenhar_arco_magico(contexto.centro[0], contexto.centro[1], int(contexto.aura_r * 1.05), contexto.paleta["spark"], 145, math.pi * 1.05, math.pi * 1.95, 3)
        pygame.draw.line(self.tela, contexto.paleta["core"], (int(contexto.centro[0]), int(contexto.centro[1] - contexto.aura_r * 0.7)), (int(contexto.centro[0]), int(contexto.centro[1] + contexto.aura_r * 0.7)), 1)

    def _desenhar_variante_buff_escudo_brasas(self, contexto):
        for off in (0.0, 2.09, 4.18):
            ex = contexto.centro[0] + math.cos(contexto.pulse_time * 2.6 + off) * contexto.aura_r * 0.92
            ey = contexto.centro[1] + math.sin(contexto.pulse_time * 2.6 + off) * contexto.aura_r * 0.92
            pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], 150), (int(ex), int(ey)), max(2, int(contexto.raio * 0.16)))

    def _desenhar_variante_buff_absorcao_vazio(self, contexto):
        pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 170), (int(contexto.centro[0]), int(contexto.centro[1])), max(2, int(contexto.aura_r * 0.54)))
        for side in (-1, 1):
            self._desenhar_arco_magico(contexto.centro[0], contexto.centro[1], int(contexto.aura_r * 0.96), contexto.paleta["mid"][0], 105, contexto.pulse_time * side, contexto.pulse_time * side + math.pi * 0.8, 2)

    def _desenhar_variante_buff_cura_maior(self, contexto):
        pygame.draw.line(self.tela, contexto.paleta["core"], (int(contexto.centro[0] - contexto.aura_r * 0.28), int(contexto.centro[1])), (int(contexto.centro[0] + contexto.aura_r * 0.28), int(contexto.centro[1])), 2)
        pygame.draw.line(self.tela, contexto.paleta["core"], (int(contexto.centro[0]), int(contexto.centro[1] - contexto.aura_r * 0.28)), (int(contexto.centro[0]), int(contexto.centro[1] + contexto.aura_r * 0.28)), 2)

    def _desenhar_variante_buff_purificar(self, contexto):
        for fator in (0.45, 0.72, 1.0):
            pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["spark"], 85), (int(contexto.centro[0]), int(contexto.centro[1])), max(2, int(contexto.aura_r * fator)), 1)

    def _desenhar_variante_buff_sobrecarga(self, contexto):
        for ang in (contexto.pulse_time * 8.0, contexto.pulse_time * 8.0 + math.pi):
            ex = contexto.centro[0] + math.cos(ang) * contexto.aura_r * 1.02
            ey = contexto.centro[1] + math.sin(ang) * contexto.aura_r * 1.02
            zig = self._gerar_linha_zigzag(contexto.centro[0], contexto.centro[1], ex, ey, contexto.aura_r * 0.12, 4, contexto.pulse_time * 14.0)
            pygame.draw.lines(self.tela, contexto.paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)

    def _desenhar_variante_buff_amplificacao(self, contexto):
        for i in range(4):
            ang = contexto.pulse_time * 0.5 + i * (math.pi / 2)
            ponta = (contexto.centro[0] + math.cos(ang) * contexto.aura_r * 1.08, contexto.centro[1] + math.sin(ang) * contexto.aura_r * 1.08)
            base = (contexto.centro[0] + math.cos(ang) * contexto.aura_r * 0.66, contexto.centro[1] + math.sin(ang) * contexto.aura_r * 0.66)
            lat_a = (base[0] + math.cos(ang + math.pi / 2) * contexto.aura_r * 0.12, base[1] + math.sin(ang + math.pi / 2) * contexto.aura_r * 0.12)
            lat_b = (base[0] + math.cos(ang - math.pi / 2) * contexto.aura_r * 0.12, base[1] + math.sin(ang - math.pi / 2) * contexto.aura_r * 0.12)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][0], 125), [(int(ponta[0]), int(ponta[1])), (int(lat_a[0]), int(lat_a[1])), (int(lat_b[0]), int(lat_b[1]))])

    def _desenhar_variante_buff_lutador(self, contexto):
        dispatch = {
            "escudo_arcano": self._desenhar_variante_buff_escudo_arcano,
            "barreira_divina": self._desenhar_variante_buff_barreira_divina,
            "escudo_brasas": self._desenhar_variante_buff_escudo_brasas,
            "absorcao_vazio": self._desenhar_variante_buff_absorcao_vazio,
            "cura_maior": self._desenhar_variante_buff_cura_maior,
            "purificar": self._desenhar_variante_buff_purificar,
            "sobrecarga": self._desenhar_variante_buff_sobrecarga,
            "amplificar_magia": self._desenhar_variante_buff_amplificacao,
            "conjuracao_perfeita": self._desenhar_variante_buff_amplificacao,
        }
        drawer = dispatch.get(contexto.variante)
        if drawer is not None:
            drawer(contexto)

    def _desenhar_buffs_lutador(self, lutador, centro, raio, pulse_time):
        buffs = self._coletar_buffs_visuais_ativos(lutador)
        if not buffs:
            return
        for idx, buff in enumerate(buffs[:3]):
            contexto = self._criar_contexto_buff_lutador(buff, idx, centro, raio, pulse_time)
            self._desenhar_base_buff_lutador(contexto)
            self._desenhar_escudo_buff_lutador(contexto)
            self._desenhar_variante_buff_lutador(contexto)

    def _desenhar_transformacao_lutador(self, lutador, centro, raio, pulse_time):
        transform = getattr(lutador, "transformacao_ativa", None)
        if not transform or not getattr(transform, "ativo", False):
            return

        classe = self._resolver_classe_magia(transform)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(transform, tipo="TRANSFORM")
        elemento = self._detectar_elemento_visual(getattr(transform, "nome", ""), "TRANSFORM", getattr(transform, "elemento", None))
        paleta = self._paleta_magica(elemento, getattr(transform, "cor", None))
        aura_r = int(raio * 1.55)

        self._desenhar_glow_circular(centro[0], centro[1], int(aura_r * 1.15), paleta["outer"][0], 42, 4)
        self._desenhar_motivo_circular_magia(centro[0], centro[1], aura_r, paleta, perfil, pulse_time, 0.72)

        variante = assinatura.get("variante", "")
        if variante == "avatar_gelo":
            estrela = self._pontos_poligono_regular(centro[0], centro[1], aura_r * 1.02, 8, pulse_time * 0.15, 1.32)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], 145), [(int(px), int(py)) for px, py in estrela], 2)
            for i in range(6):
                ang = pulse_time * 0.28 + i * (math.pi / 3)
                ex = centro[0] + math.cos(ang) * aura_r * 0.92
                ey = centro[1] + math.sin(ang) * aura_r * 0.92
                pygame.draw.line(self.tela, paleta["core"], (int(centro[0]), int(centro[1])), (int(ex), int(ey)), 1)
        elif variante == "forma_relampago":
            for ang in (pulse_time * 7.0, pulse_time * 7.0 + 2.2, pulse_time * 7.0 + 4.1):
                ex = centro[0] + math.cos(ang) * aura_r
                ey = centro[1] + math.sin(ang) * aura_r
                zig = self._gerar_linha_zigzag(centro[0], centro[1], ex, ey, aura_r * 0.14, 4, pulse_time * 12.0 + ang)
                pygame.draw.lines(self.tela, paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)
        elif variante == "forma_vazio":
            pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 185), (int(centro[0]), int(centro[1])), max(3, int(aura_r * 0.62)))
            for i in range(5):
                ang = pulse_time * 0.33 + i * (math.pi * 2 / 5)
                x1 = centro[0] + math.cos(ang) * aura_r * 0.92
                y1 = centro[1] + math.sin(ang) * aura_r * 0.92
                x2 = centro[0] + math.cos(ang) * aura_r * 0.32
                y2 = centro[1] + math.sin(ang) * aura_r * 0.32
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["mid"][1], 110), (int(x1), int(y1)), (int(x2), int(y2)), 2)

        aura_real = getattr(transform, "aura_raio", 0)
        if aura_real and aura_real > 0:
            aura_px = self.cam.converter_tam(aura_real * PPM)
            if aura_px > 0:
                pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["outer"][0], 70), (int(centro[0]), int(centro[1])), int(aura_px), 1)

    def _criar_contexto_summon_magico(self, summon, pulse_time):
        sx, sy = self.cam.converter(summon.x * PPM, summon.y * PPM)
        raio = self.cam.converter_tam(0.8 * PPM)
        classe = self._resolver_classe_magia(summon)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(summon, tipo="SUMMON")
        elemento = self._detectar_elemento_visual(getattr(summon, "nome", ""), "SUMMON", getattr(summon, "elemento", None))
        paleta = self._paleta_magica(elemento, getattr(summon, "cor", None))
        return SummonRenderContext(
            summon=summon,
            pulse_time=pulse_time,
            sx=sx,
            sy=sy,
            raio=raio,
            classe=classe,
            perfil=perfil,
            assinatura=assinatura,
            elemento=elemento,
            paleta=paleta,
            centro=(sx, sy),
            base_r=max(8, int(raio * 1.55)),
            variante=assinatura.get("variante", ""),
        )

    def _desenhar_base_summon_magico(self, contexto):
        self._desenhar_motivo_circular_magia(contexto.centro[0], contexto.centro[1] + contexto.raio * 0.18, int(contexto.base_r * 0.9), contexto.paleta, contexto.perfil, contexto.pulse_time, 0.75)
        pygame.draw.ellipse(self.tela, (30, 30, 30), (contexto.sx - contexto.raio, contexto.sy + contexto.raio // 2, contexto.raio * 2, contexto.raio // 2))
        self._desenhar_glow_circular(contexto.centro[0], contexto.centro[1], int(contexto.raio * 1.9), contexto.paleta["outer"][0], 58, 3)

    def _desenhar_flash_summon_magico(self, contexto):
        if getattr(contexto.summon, "flash_timer", 0) <= 0:
            return
        flash_cor = getattr(contexto.summon, "flash_cor", (255, 255, 255))
        flash_alpha = int(180 * min(1.0, contexto.summon.flash_timer / 0.3))
        sf = self._get_surface(int(contexto.raio * 3), int(contexto.raio * 3), pygame.SRCALPHA)
        pygame.draw.circle(sf, (*flash_cor, flash_alpha), (sf.get_width() // 2, sf.get_height() // 2), int(contexto.raio * 1.15))
        self.tela.blit(sf, (contexto.sx - sf.get_width() // 2, contexto.sy - sf.get_height() // 2))

    def _desenhar_variante_fenix_summon(self, contexto):
        corpo = [(contexto.sx, contexto.sy - contexto.raio * 1.1), (contexto.sx + contexto.raio * 0.45, contexto.sy), (contexto.sx, contexto.sy + contexto.raio * 0.75), (contexto.sx - contexto.raio * 0.45, contexto.sy)]
        asa_esq = [(contexto.sx - contexto.raio * 0.15, contexto.sy - contexto.raio * 0.2), (contexto.sx - contexto.raio * 1.25, contexto.sy - contexto.raio * 0.62), (contexto.sx - contexto.raio * 0.6, contexto.sy + contexto.raio * 0.15)]
        asa_dir = [(contexto.sx + contexto.raio * 0.15, contexto.sy - contexto.raio * 0.2), (contexto.sx + contexto.raio * 1.25, contexto.sy - contexto.raio * 0.62), (contexto.sx + contexto.raio * 0.6, contexto.sy + contexto.raio * 0.15)]
        cauda = [(contexto.sx, contexto.sy + contexto.raio * 0.5), (contexto.sx - contexto.raio * 0.28, contexto.sy + contexto.raio * 1.35), (contexto.sx + contexto.raio * 0.28, contexto.sy + contexto.raio * 1.35)]
        pygame.draw.polygon(self.tela, contexto.paleta["mid"][1], [(int(x), int(y)) for x, y in asa_esq])
        pygame.draw.polygon(self.tela, contexto.paleta["mid"][1], [(int(x), int(y)) for x, y in asa_dir])
        pygame.draw.polygon(self.tela, contexto.paleta["mid"][0], [(int(x), int(y)) for x, y in corpo])
        pygame.draw.polygon(self.tela, contexto.paleta["spark"], [(int(x), int(y)) for x, y in cauda])
        if getattr(contexto.summon, "revive_count", 0) > 0:
            self._desenhar_arco_magico(contexto.sx, contexto.sy - contexto.raio * 0.2, int(contexto.raio * 1.05), contexto.paleta["spark"], 120, math.pi * 1.12, math.pi * 1.88, 2)

    def _desenhar_variante_espirito_arcano_summon(self, contexto):
        fantasma = [(contexto.sx, contexto.sy - contexto.raio * 1.1), (contexto.sx + contexto.raio * 0.62, contexto.sy - contexto.raio * 0.18), (contexto.sx + contexto.raio * 0.42, contexto.sy + contexto.raio * 0.9), (contexto.sx, contexto.sy + contexto.raio * 0.52), (contexto.sx - contexto.raio * 0.42, contexto.sy + contexto.raio * 0.9), (contexto.sx - contexto.raio * 0.62, contexto.sy - contexto.raio * 0.18)]
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][0], 180), [(int(x), int(y)) for x, y in fantasma])
        self._desenhar_sigilo_magico(contexto.sx, contexto.sy, int(contexto.raio * 0.82), contexto.paleta, contexto.pulse_time, 0.55)

    def _desenhar_variante_portal_void_summon(self, contexto):
        pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 210), (int(contexto.sx), int(contexto.sy)), max(2, int(contexto.raio * 0.95)))
        count = 3 if contexto.variante == "portal_vazio" else 5
        largura = 1 if contexto.variante == "portal_vazio" else 2
        for i in range(count):
            ang = contexto.pulse_time * 0.36 + i * (math.pi * 2 / count)
            ex = contexto.sx + math.cos(ang) * contexto.raio * 1.18
            ey = contexto.sy + math.sin(ang) * contexto.raio * 1.18
            pygame.draw.line(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], 110), (int(ex), int(ey)), (int(contexto.sx), int(contexto.sy)), largura)
        self._desenhar_motivo_circular_magia(contexto.sx, contexto.sy, int(contexto.raio * 1.2), contexto.paleta, contexto.perfil, contexto.pulse_time, 0.82)

    def _desenhar_fallback_summon_magico(self, contexto):
        pygame.draw.circle(self.tela, contexto.summon.cor, (int(contexto.sx), int(contexto.sy)), int(contexto.raio))
        pygame.draw.circle(self.tela, tuple(min(255, c + 50) for c in contexto.summon.cor), (int(contexto.sx), int(contexto.sy)), int(contexto.raio * 0.7))

    def _desenhar_variante_summon_magico(self, contexto):
        dispatch = {
            "fenix": self._desenhar_variante_fenix_summon,
            "espirito_arcano": self._desenhar_variante_espirito_arcano_summon,
            "portal_vazio": self._desenhar_variante_portal_void_summon,
            "anomalia_espacial": self._desenhar_variante_portal_void_summon,
        }
        dispatch.get(contexto.variante, self._desenhar_fallback_summon_magico)(contexto)

    def _desenhar_overlay_summon_magico(self, contexto):
        pygame.draw.circle(self.tela, BRANCO, (int(contexto.sx), int(contexto.sy)), max(1, int(contexto.raio * 0.28)))
        if contexto.summon.alvo:
            ang_rad = math.radians(contexto.summon.angulo)
            eye_dist = contexto.raio * 0.45
            eye_x = int(contexto.sx + math.cos(ang_rad) * eye_dist)
            eye_y = int(contexto.sy + math.sin(ang_rad) * eye_dist)
            pygame.draw.circle(self.tela, (255, 255, 200), (eye_x, eye_y), max(1, int(contexto.raio * 0.18)))
        vida_pct = contexto.summon.vida / max(contexto.summon.vida_max, 1)
        barra_w = contexto.raio * 2
        pygame.draw.rect(self.tela, (50, 50, 50), (contexto.sx - contexto.raio, contexto.sy - contexto.raio - 10, barra_w, 5))
        cor_vida = (int(255 * (1 - vida_pct)), int(255 * vida_pct), 50) if vida_pct < 0.5 else contexto.summon.cor
        pygame.draw.rect(self.tela, cor_vida, (contexto.sx - contexto.raio, contexto.sy - contexto.raio - 10, barra_w * vida_pct, 5))
        font = self._get_font(None, 16)
        nome_txt = font.render(contexto.summon.nome, True, contexto.summon.cor)
        self.tela.blit(nome_txt, (contexto.sx - nome_txt.get_width() // 2, contexto.sy - contexto.raio - 22))

    def _desenhar_summon_magico(self, summon, pulse_time):
        contexto = self._criar_contexto_summon_magico(summon, pulse_time)
        self._desenhar_base_summon_magico(contexto)
        self._desenhar_flash_summon_magico(contexto)
        self._desenhar_variante_summon_magico(contexto)
        self._desenhar_overlay_summon_magico(contexto)

    def _criar_contexto_trap_magica(self, trap, pulse_time):
        tx, ty = self.cam.converter(trap.x * PPM, trap.y * PPM)
        traio = self.cam.converter_tam(trap.raio * PPM)
        classe = self._resolver_classe_magia(trap)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(trap, tipo="TRAP")
        elemento = self._detectar_elemento_visual(getattr(trap, "nome", ""), "TRAP", getattr(trap, "elemento", None))
        paleta = self._paleta_magica(elemento, getattr(trap, "cor", None))
        return TrapRenderContext(
            trap=trap,
            pulse_time=pulse_time,
            tx=tx,
            ty=ty,
            traio=traio,
            classe=classe,
            perfil=perfil,
            assinatura=assinatura,
            elemento=elemento,
            paleta=paleta,
            variante=assinatura.get("variante", ""),
        )

    def _desenhar_flash_trap_magica(self, contexto):
        if getattr(contexto.trap, "flash_timer", 0) <= 0:
            return
        flash_cor = getattr(contexto.trap, "flash_cor", (255, 255, 255))
        flash_alpha = int(200 * min(1.0, contexto.trap.flash_timer / 0.15))
        tf4 = max(1, int(contexto.traio * 4))
        s_flash = self._get_surface(tf4, tf4, pygame.SRCALPHA)
        pygame.draw.circle(s_flash, (*flash_cor, min(255, flash_alpha)), (tf4 // 2, tf4 // 2), int(contexto.traio * 1.5))
        self.tela.blit(s_flash, (contexto.tx - tf4 // 2, contexto.ty - tf4 // 2))

    def _desenhar_variante_barreira_trap(self, contexto):
        if contexto.variante == "muralha_gelo":
            for i in range(3):
                ang = contexto.pulse_time * 0.12 + i * (math.pi / 3)
                x1 = contexto.tx + math.cos(ang) * contexto.traio * 0.8
                y1 = contexto.ty + math.sin(ang) * contexto.traio * 0.8
                x2 = contexto.tx + math.cos(ang + math.pi) * contexto.traio * 0.45
                y2 = contexto.ty + math.sin(ang + math.pi) * contexto.traio * 0.45
                pygame.draw.line(self.tela, contexto.paleta["core"], (int(x1), int(y1)), (int(x2), int(y2)), 1)
        elif contexto.variante == "espelho_gelo":
            inner = self._pontos_poligono_regular(contexto.tx, contexto.ty, contexto.traio * 0.62, 6, -contexto.pulse_time * 0.1)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["spark"], 110), [(int(px), int(py)) for px, py in inner], 1)

    def _desenhar_trap_bloqueio_movimento(self, contexto):
        vida_pct = contexto.trap.vida / contexto.trap.vida_max if contexto.trap.vida_max > 0 else 1
        shell = self._pontos_poligono_regular(contexto.tx, contexto.ty, contexto.traio, 6, getattr(contexto.trap, "angulo", 0) + contexto.pulse_time * 0.08)
        s_wall = self._get_surface(max(1, int(contexto.traio * 2 + 12)), max(1, int(contexto.traio * 2 + 12)), pygame.SRCALPHA)
        pts_local = [(p[0] - contexto.tx + s_wall.get_width() // 2, p[1] - contexto.ty + s_wall.get_height() // 2) for p in shell]
        pygame.draw.polygon(s_wall, (*contexto.trap.cor, int(170 * vida_pct + 50)), pts_local)
        self.tela.blit(s_wall, (contexto.tx - s_wall.get_width() // 2, contexto.ty - s_wall.get_height() // 2))
        pygame.draw.polygon(self.tela, BRANCO, [(int(px), int(py)) for px, py in shell], 2)
        self._desenhar_motivo_circular_magia(contexto.tx, contexto.ty, int(contexto.traio * 0.72), contexto.paleta, contexto.perfil, contexto.pulse_time, 0.62)
        self._desenhar_variante_barreira_trap(contexto)

    def _desenhar_trap_ativada(self, contexto):
        exp_alpha = int(200 * (contexto.trap.vida_timer / 0.5)) if contexto.trap.vida_timer > 0 else 0
        te4 = max(1, int(contexto.traio * 4))
        s_exp = self._get_surface(te4, te4, pygame.SRCALPHA)
        pygame.draw.circle(s_exp, (*contexto.trap.cor, min(255, exp_alpha)), (te4 // 2, te4 // 2), int(contexto.traio * 2))
        self.tela.blit(s_exp, (contexto.tx - te4 // 2, contexto.ty - te4 // 2))

    def _desenhar_variante_armadilha_magica(self, contexto):
        if contexto.variante == "prisao_luz":
            for ang in (0, math.pi / 2):
                pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.tx + math.cos(ang) * contexto.traio), int(contexto.ty + math.sin(ang) * contexto.traio)), (int(contexto.tx - math.cos(ang) * contexto.traio), int(contexto.ty - math.sin(ang) * contexto.traio)), 1)
        elif contexto.variante == "armadilha_incendiaria":
            tri = [(contexto.tx, contexto.ty - contexto.traio * 0.95), (contexto.tx + contexto.traio * 0.82, contexto.ty + contexto.traio * 0.6), (contexto.tx - contexto.traio * 0.82, contexto.ty + contexto.traio * 0.6)]
            pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], 120), [(int(x), int(y)) for x, y in tri], 1)
        elif contexto.variante == "armadilha_eletrica":
            zig = self._gerar_linha_zigzag(contexto.tx - contexto.traio * 0.8, contexto.ty, contexto.tx + contexto.traio * 0.8, contexto.ty, contexto.traio * 0.18, 5, contexto.pulse_time * 10.0)
            pygame.draw.lines(self.tela, contexto.paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)

    def _desenhar_trap_inativa(self, contexto):
        trap_pulse = 0.6 + 0.4 * math.sin(contexto.pulse_time * 3 + hash(id(contexto.trap)) % 10)
        trap_r = max(1, int(contexto.traio * trap_pulse))
        s = self._get_surface(trap_r * 2 + 4, trap_r * 2 + 4, pygame.SRCALPHA)
        pygame.draw.circle(s, (*contexto.trap.cor, 80), (trap_r + 2, trap_r + 2), trap_r)
        self.tela.blit(s, (contexto.tx - trap_r - 2, contexto.ty - trap_r - 2))
        pygame.draw.circle(self.tela, contexto.trap.cor, (int(contexto.tx), int(contexto.ty)), int(contexto.traio), 2)
        self._desenhar_motivo_circular_magia(contexto.tx, contexto.ty, int(contexto.traio * 0.82), contexto.paleta, contexto.perfil, contexto.pulse_time, 0.68)
        self._desenhar_variante_armadilha_magica(contexto)

    def _desenhar_trap_magica(self, trap, pulse_time):
        contexto = self._criar_contexto_trap_magica(trap, pulse_time)
        self._desenhar_flash_trap_magica(contexto)
        if contexto.trap.bloqueia_movimento:
            self._desenhar_trap_bloqueio_movimento(contexto)
            return
        if getattr(contexto.trap, "ativada", False):
            self._desenhar_trap_ativada(contexto)
            return
        self._desenhar_trap_inativa(contexto)

    def _criar_contexto_motivo_circular_magia(self, x, y, raio, paleta, perfil, tempo, intensidade=1.0):
        raio = int(max(8, raio))
        return MagicCircularPatternContext(
            x=x,
            y=y,
            raio=raio,
            paleta=paleta,
            perfil=perfil,
            tempo=tempo,
            intensidade=intensidade,
            motivo=perfil["motivo"],
            ornamento=perfil["ornamento"],
            alpha=max(45, int(160 * intensidade)),
        )

    def _desenhar_motivo_protecao_circular_magia(self, contexto):
        hexa = self._pontos_poligono_regular(contexto.x, contexto.y, contexto.raio, 6, contexto.tempo * 0.14 + math.pi / 6)
        hexa_inner = self._pontos_poligono_regular(contexto.x, contexto.y, contexto.raio * 0.68, 6, -contexto.tempo * 0.18)
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][0], contexto.alpha), [(int(px), int(py)) for px, py in hexa], 2)
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["core"], contexto.alpha - 25), [(int(px), int(py)) for px, py in hexa_inner], 1)
        for px, py in hexa:
            pygame.draw.circle(self.tela, contexto.paleta["spark"], (int(px), int(py)), max(2, int(contexto.raio * 0.08)))

    def _desenhar_motivo_cura_circular_magia(self, contexto):
        for i in range(5):
            ang = contexto.tempo * 0.45 + i * (math.pi * 2 / 5)
            ponta = (contexto.x + math.cos(ang) * contexto.raio * 1.1, contexto.y + math.sin(ang) * contexto.raio * 1.1)
            base_esq = (contexto.x + math.cos(ang + 0.55) * contexto.raio * 0.38, contexto.y + math.sin(ang + 0.55) * contexto.raio * 0.38)
            base_dir = (contexto.x + math.cos(ang - 0.55) * contexto.raio * 0.38, contexto.y + math.sin(ang - 0.55) * contexto.raio * 0.38)
            pygame.draw.polygon(
                self.tela,
                self._cor_com_alpha(contexto.paleta["mid"][1], contexto.alpha - 20),
                [(int(base_esq[0]), int(base_esq[1])), (int(ponta[0]), int(ponta[1])), (int(base_dir[0]), int(base_dir[1]))],
            )
        pygame.draw.line(
            self.tela,
            contexto.paleta["core"],
            (int(contexto.x - contexto.raio * 0.35), int(contexto.y)),
            (int(contexto.x + contexto.raio * 0.35), int(contexto.y)),
            2,
        )
        pygame.draw.line(
            self.tela,
            contexto.paleta["core"],
            (int(contexto.x), int(contexto.y - contexto.raio * 0.35)),
            (int(contexto.x), int(contexto.y + contexto.raio * 0.35)),
            2,
        )

    def _desenhar_motivo_invocacao_circular_magia(self, contexto):
        tri_a = self._pontos_poligono_regular(contexto.x, contexto.y, contexto.raio, 3, contexto.tempo * 0.25 - math.pi / 2)
        tri_b = self._pontos_poligono_regular(contexto.x, contexto.y, contexto.raio * 0.72, 3, -contexto.tempo * 0.3 + math.pi / 2)
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][0], contexto.alpha), [(int(px), int(py)) for px, py in tri_a], 2)
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["spark"], contexto.alpha - 25), [(int(px), int(py)) for px, py in tri_b], 2)
        for i in range(3):
            ang = contexto.tempo * 0.7 + i * (math.pi * 2 / 3)
            rx = contexto.x + math.cos(ang) * contexto.raio * 0.55
            ry = contexto.y + math.sin(ang) * contexto.raio * 0.55
            pygame.draw.circle(self.tela, contexto.paleta["core"], (int(rx), int(ry)), max(2, int(contexto.raio * 0.08)))

    def _desenhar_motivo_controle_circular_magia(self, contexto):
        for i in range(4):
            ang = contexto.tempo * 0.18 + i * (math.pi / 2)
            x1 = contexto.x + math.cos(ang) * contexto.raio
            y1 = contexto.y + math.sin(ang) * contexto.raio
            x2 = contexto.x + math.cos(ang + math.pi) * contexto.raio
            y2 = contexto.y + math.sin(ang + math.pi) * contexto.raio
            pygame.draw.line(
                self.tela,
                self._cor_com_alpha(contexto.paleta["mid"][0], contexto.alpha - 35),
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                1,
            )
        for i in range(4):
            inicio = contexto.tempo * 0.22 + i * (math.pi / 2)
            self._desenhar_arco_magico(contexto.x, contexto.y, contexto.raio, contexto.paleta["spark"], contexto.alpha - 10, inicio, inicio + math.pi / 4, 2)

    def _desenhar_motivo_disrupcao_circular_magia(self, contexto):
        for i in range(5):
            ang = contexto.tempo * 0.34 + i * (math.pi * 2 / 5)
            inicio = ang - 0.25
            fim = ang + 0.18
            self._desenhar_arco_magico(contexto.x, contexto.y, contexto.raio, contexto.paleta["mid"][0], contexto.alpha - 20, inicio, fim, 2)
            sx = contexto.x + math.cos(ang) * contexto.raio * 0.55
            sy = contexto.y + math.sin(ang) * contexto.raio * 0.55
            ex = contexto.x + math.cos(ang + 0.4) * contexto.raio * 1.05
            ey = contexto.y + math.sin(ang + 0.4) * contexto.raio * 1.05
            pygame.draw.line(self.tela, self._cor_com_alpha(contexto.paleta["spark"], contexto.alpha - 15), (int(sx), int(sy)), (int(ex), int(ey)), 2)

    def _desenhar_motivo_amplificacao_circular_magia(self, contexto):
        for i in range(4):
            ang = contexto.tempo * 0.28 + i * (math.pi / 2)
            ponta = (contexto.x + math.cos(ang) * contexto.raio * 1.05, contexto.y + math.sin(ang) * contexto.raio * 1.05)
            base = (contexto.x + math.cos(ang) * contexto.raio * 0.42, contexto.y + math.sin(ang) * contexto.raio * 0.42)
            lat_a = (base[0] + math.cos(ang + math.pi / 2) * contexto.raio * 0.18, base[1] + math.sin(ang + math.pi / 2) * contexto.raio * 0.18)
            lat_b = (base[0] + math.cos(ang - math.pi / 2) * contexto.raio * 0.18, base[1] + math.sin(ang - math.pi / 2) * contexto.raio * 0.18)
            pygame.draw.polygon(
                self.tela,
                self._cor_com_alpha(contexto.paleta["mid"][0], contexto.alpha - 10),
                [(int(ponta[0]), int(ponta[1])), (int(lat_a[0]), int(lat_a[1])), (int(base[0]), int(base[1])), (int(lat_b[0]), int(lat_b[1]))],
                0,
            )

    def _desenhar_motivo_mobilidade_circular_magia(self, contexto):
        for i in range(3):
            ang = contexto.tempo * 0.55 + i * (math.pi * 2 / 3)
            ponta = (contexto.x + math.cos(ang) * contexto.raio, contexto.y + math.sin(ang) * contexto.raio)
            cauda = (contexto.x - math.cos(ang) * contexto.raio * 0.15, contexto.y - math.sin(ang) * contexto.raio * 0.15)
            lat_a = (cauda[0] + math.cos(ang + 2.5) * contexto.raio * 0.22, cauda[1] + math.sin(ang + 2.5) * contexto.raio * 0.22)
            lat_b = (cauda[0] + math.cos(ang - 2.5) * contexto.raio * 0.22, cauda[1] + math.sin(ang - 2.5) * contexto.raio * 0.22)
            pygame.draw.polygon(
                self.tela,
                self._cor_com_alpha(contexto.paleta["spark"], contexto.alpha - 10),
                [(int(ponta[0]), int(ponta[1])), (int(lat_a[0]), int(lat_a[1])), (int(lat_b[0]), int(lat_b[1]))],
            )

    def _desenhar_ornamento_espinhos_circular_magia(self, contexto):
        estrela = self._pontos_poligono_regular(contexto.x, contexto.y, contexto.raio, 10, contexto.tempo * 0.2, 1.42)
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], contexto.alpha), [(int(px), int(py)) for px, py in estrela], 2)

    def _desenhar_ornamento_mira_circular_magia(self, contexto):
        pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["mid"][0], contexto.alpha), (int(contexto.x), int(contexto.y)), contexto.raio, 1)
        pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.x - contexto.raio), int(contexto.y)), (int(contexto.x + contexto.raio), int(contexto.y)), 1)
        pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.x), int(contexto.y - contexto.raio)), (int(contexto.x), int(contexto.y + contexto.raio)), 1)

    def _desenhar_ornamento_orbitas_circular_magia(self, contexto):
        for fator in (0.72, 1.0):
            self._desenhar_arco_magico(
                contexto.x,
                contexto.y,
                int(contexto.raio * fator),
                contexto.paleta["mid"][0],
                contexto.alpha - 15,
                contexto.tempo * 0.35,
                contexto.tempo * 0.35 + math.pi * 1.2,
                2,
            )

    def _desenhar_fallback_circular_magia(self, contexto):
        pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["mid"][0], contexto.alpha - 15), (int(contexto.x), int(contexto.y)), contexto.raio, 2)

    def _desenhar_motivo_circular_magia(self, x, y, raio, paleta, perfil, tempo, intensidade=1.0):
        contexto = self._criar_contexto_motivo_circular_magia(x, y, raio, paleta, perfil, tempo, intensidade)
        motivo_dispatch = {
            "protecao": self._desenhar_motivo_protecao_circular_magia,
            "cura": self._desenhar_motivo_cura_circular_magia,
            "invocacao": self._desenhar_motivo_invocacao_circular_magia,
            "controle": self._desenhar_motivo_controle_circular_magia,
            "disrupcao": self._desenhar_motivo_disrupcao_circular_magia,
            "amplificacao": self._desenhar_motivo_amplificacao_circular_magia,
            "mobilidade": self._desenhar_motivo_mobilidade_circular_magia,
        }
        ornamento_dispatch = {
            "espinhos": self._desenhar_ornamento_espinhos_circular_magia,
            "mira": self._desenhar_ornamento_mira_circular_magia,
            "orbitas": self._desenhar_ornamento_orbitas_circular_magia,
        }
        drawer = motivo_dispatch.get(contexto.motivo) or ornamento_dispatch.get(contexto.ornamento) or self._desenhar_fallback_circular_magia
        drawer(contexto)

    def _iterar_segmentos_ornamento_feixe(self, pontos):
        for i in range(len(pontos) - 1):
            x1, y1 = pontos[i]
            x2, y2 = pontos[i + 1]
            seg_dx = x2 - x1
            seg_dy = y2 - y1
            seg_len = math.hypot(seg_dx, seg_dy)
            if seg_len < 6:
                continue
            perp_x = -seg_dy / seg_len
            perp_y = seg_dx / seg_len
            mid_x = x1 + seg_dx * 0.5
            mid_y = y1 + seg_dy * 0.5
            yield i, x1, y1, x2, y2, seg_dx, seg_dy, seg_len, perp_x, perp_y, mid_x, mid_y

    def _desenhar_ornamento_controle_feixe(self, surf, segmento, paleta, pulse_time, largura):
        i, x1, y1, _x2, _y2, seg_dx, seg_dy, _seg_len, perp_x, perp_y, mid_x, mid_y = segmento
        for side in (-1, 1):
            fork_len = largura * (0.95 + 0.25 * math.sin(pulse_time * 18 + i))
            fx = mid_x + perp_x * fork_len * side
            fy = mid_y + perp_y * fork_len * side
            pygame.draw.line(
                surf,
                self._cor_com_alpha(paleta["spark"], 110),
                (int(x1 + seg_dx * 0.45), int(y1 + seg_dy * 0.45)),
                (int(fx), int(fy)),
                max(1, largura // 4),
            )
        pygame.draw.line(
            surf,
            self._cor_com_alpha(paleta["mid"][0], 95),
            (int(mid_x + perp_x * largura * 0.9), int(mid_y + perp_y * largura * 0.9)),
            (int(mid_x - perp_x * largura * 0.9), int(mid_y - perp_y * largura * 0.9)),
            max(1, largura // 5),
        )

    def _desenhar_ornamento_protecao_feixe(self, surf, segmento, paleta, _pulse_time, largura):
        *_prefix, perp_x, perp_y, mid_x, mid_y = segmento[-5:]
        for side in (-1, 1):
            ox = mid_x + perp_x * largura * 0.72 * side
            oy = mid_y + perp_y * largura * 0.72 * side
            pygame.draw.circle(surf, self._cor_com_alpha(paleta["core"], 110), (int(ox), int(oy)), max(1, largura // 3))

    def _desenhar_ornamento_cura_feixe(self, surf, segmento, paleta, pulse_time, largura):
        i = segmento[0]
        perp_x, perp_y, mid_x, mid_y = segmento[-4:]
        sway = math.sin(pulse_time * 10 + i) * largura * 0.55
        pygame.draw.circle(
            surf,
            self._cor_com_alpha(paleta["spark"], 105),
            (int(mid_x + perp_x * sway), int(mid_y + perp_y * sway)),
            max(1, largura // 3),
        )

    def _desenhar_ornamento_invocacao_feixe(self, surf, segmento, paleta, pulse_time, largura):
        i = segmento[0]
        mid_x = segmento[-2]
        mid_y = segmento[-1]
        tri = [
            (mid_x + math.cos(pulse_time + i) * largura * 0.8, mid_y + math.sin(pulse_time + i) * largura * 0.8),
            (mid_x + math.cos(pulse_time + i + 2.1) * largura * 0.8, mid_y + math.sin(pulse_time + i + 2.1) * largura * 0.8),
            (mid_x + math.cos(pulse_time + i + 4.2) * largura * 0.8, mid_y + math.sin(pulse_time + i + 4.2) * largura * 0.8),
        ]
        pygame.draw.polygon(surf, self._cor_com_alpha(paleta["mid"][0], 80), [(int(px), int(py)) for px, py in tri], 1)

    def _desenhar_ornamento_disrupcao_feixe(self, surf, segmento, paleta, _pulse_time, largura):
        _i, _x1, _y1, _x2, _y2, seg_dx, seg_dy, seg_len, perp_x, perp_y, mid_x, mid_y = segmento
        for side in (-1, 1):
            ox = mid_x + perp_x * largura * 0.8 * side
            oy = mid_y + perp_y * largura * 0.8 * side
            ex = ox + seg_dx / max(seg_len, 1) * largura * 0.6
            ey = oy + seg_dy / max(seg_len, 1) * largura * 0.6
            pygame.draw.line(surf, self._cor_com_alpha(paleta["spark"], 105), (int(ox), int(oy)), (int(ex), int(ey)), 1)

    def _desenhar_ornamento_mira_feixe(self, surf, segmento, paleta, _pulse_time, largura):
        mid_x = segmento[-2]
        mid_y = segmento[-1]
        pygame.draw.circle(surf, self._cor_com_alpha(paleta["spark"], 90), (int(mid_x), int(mid_y)), max(1, largura // 2))

    def _desenhar_ornamento_espinhos_feixe(self, surf, segmento, paleta, _pulse_time, largura):
        perp_x, perp_y, mid_x, mid_y = segmento[-4:]
        for side in (-1, 1):
            ox = mid_x + perp_x * largura * 1.15 * side
            oy = mid_y + perp_y * largura * 1.15 * side
            pygame.draw.line(
                surf,
                self._cor_com_alpha(paleta["mid"][1], 120),
                (int(mid_x), int(mid_y)),
                (int(ox), int(oy)),
                max(1, largura // 5),
            )

    def _desenhar_ornamento_orbitas_feixe(self, surf, segmento, paleta, pulse_time, largura):
        i = segmento[0]
        perp_x, perp_y, mid_x, mid_y = segmento[-4:]
        for side in (-1, 1):
            ox = mid_x + perp_x * math.sin(pulse_time * 7 + i) * largura * 0.65 * side
            oy = mid_y + perp_y * math.sin(pulse_time * 7 + i) * largura * 0.65 * side
            pygame.draw.circle(surf, self._cor_com_alpha(paleta["mid"][0], 80), (int(ox), int(oy)), max(1, largura // 4))

    def _desenhar_ornamentos_feixe(self, surf, pontos, paleta, perfil, pulse_time, largura):
        if len(pontos) < 2:
            return
        motivo_dispatch = {
            "controle": self._desenhar_ornamento_controle_feixe,
            "protecao": self._desenhar_ornamento_protecao_feixe,
            "cura": self._desenhar_ornamento_cura_feixe,
            "invocacao": self._desenhar_ornamento_invocacao_feixe,
            "disrupcao": self._desenhar_ornamento_disrupcao_feixe,
        }
        ornamento_dispatch = {
            "mira": self._desenhar_ornamento_mira_feixe,
            "espinhos": self._desenhar_ornamento_espinhos_feixe,
            "orbitas": self._desenhar_ornamento_orbitas_feixe,
        }
        drawer = motivo_dispatch.get(perfil["motivo"]) or ornamento_dispatch.get(perfil["ornamento"])
        if drawer is None:
            return
        for segmento in self._iterar_segmentos_ornamento_feixe(pontos):
            drawer(surf, segmento, paleta, pulse_time, largura)

    def _criar_contexto_area_magica(self, area, pulse_time):
        ax, ay = self.cam.converter(area.x * PPM, area.y * PPM)
        ar = self.cam.converter_tam(area.raio_atual * PPM)
        if ar <= 0:
            return None

        classe = self._resolver_classe_magia(area)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(area, tipo=getattr(area, "tipo_efeito", "AREA"))
        elemento = self._detectar_elemento_visual(area.nome, area.tipo_efeito, getattr(area, "elemento", None))
        paleta = self._paleta_magica(elemento, area.cor)
        utilidade = classe.get("classe_utilidade", "ZONA")
        forca = classe.get("classe_forca", "IMPACTO")
        ativo = getattr(area, "ativado", True)
        pulse = 0.82 + 0.18 * math.sin(pulse_time * (4.5 if ativo else 8.0))
        alpha_base = min(255, getattr(area, "alpha", 255))
        raio_visual = int(ar * (pulse if ativo else 1.0))
        zonal = utilidade in {"CONTROLE", "ZONA"}
        suporte = utilidade in {"PROTECAO", "CURA", "AMPLIFICACAO"}
        invocacao = utilidade == "INVOCACAO"
        cataclismo = forca == "CATACLISMO"
        return MagicAreaRenderContext(
            area=area,
            pulse_time=pulse_time,
            ax=ax,
            ay=ay,
            ar=ar,
            classe=classe,
            perfil=perfil,
            assinatura=assinatura,
            elemento=elemento,
            paleta=paleta,
            utilidade=utilidade,
            forca=forca,
            ativo=ativo,
            pulse=pulse,
            alpha_base=alpha_base,
            raio_visual=raio_visual,
            zonal=zonal,
            suporte=suporte,
            invocacao=invocacao,
            cataclismo=cataclismo,
        )

    def _desenhar_base_area_magica(self, contexto):
        self._desenhar_glow_circular(
            contexto.ax,
            contexto.ay,
            contexto.ar * ((1.75 if contexto.suporte else 2.0) * contexto.perfil["perigo"]),
            contexto.paleta["outer"][0],
            (24 if contexto.suporte else 42 if contexto.ativo else 58) + contexto.alpha_base * 0.08,
        )

        fill = self._get_surface(contexto.ar * 2 + 8, contexto.ar * 2 + 8, pygame.SRCALPHA)
        pygame.draw.circle(
            fill,
            self._cor_com_alpha(contexto.paleta["outer"][1], 34 if contexto.suporte else 46 if contexto.ativo else 26),
            (contexto.ar + 4, contexto.ar + 4),
            max(2, contexto.raio_visual),
        )
        pygame.draw.circle(
            fill,
            self._cor_com_alpha(contexto.paleta["mid"][0], 24 if contexto.suporte else 18 if contexto.ativo else 9),
            (contexto.ar + 4, contexto.ar + 4),
            max(2, int(contexto.raio_visual * (0.58 if contexto.suporte else 0.72))),
        )
        self.tela.blit(fill, (contexto.ax - contexto.ar - 4, contexto.ay - contexto.ar - 4))

    def _desenhar_aneis_area_magica(self, contexto):
        for i in range(2 if contexto.suporte else 3 if contexto.perfil["motivo"] != "controle" else 4):
            phase = (contexto.pulse_time * (1.5 + i * 0.45) + i * 0.21) % 1.0
            ring_r = int(contexto.ar * (0.25 + phase * 0.75))
            if 4 < ring_r < contexto.ar:
                ring = self._get_surface(ring_r * 2 + 8, ring_r * 2 + 8, pygame.SRCALPHA)
                pygame.draw.circle(
                    ring,
                    self._cor_com_alpha(contexto.paleta["spark"], (130 if contexto.ativo else 95) * (1.0 - phase)),
                    (ring_r + 4, ring_r + 4),
                    ring_r,
                    2,
                )
                self.tela.blit(ring, (contexto.ax - ring_r - 4, contexto.ay - ring_r - 4))

    def _desenhar_marcadores_area_magica(self, contexto):
        marker_count = max(6, contexto.perfil["marcas"] + (2 if contexto.ativo and contexto.cataclismo else 0))
        for i in range(marker_count):
            ang = contexto.pulse_time * (0.4 if contexto.suporte else 0.8 if contexto.ativo else 2.1) + i * (math.pi * 2 / marker_count)
            outer_r = contexto.ar + (2 if contexto.suporte else 6)
            inner_r = max(6, int(contexto.ar * (0.78 if contexto.zonal else 0.86 if contexto.suporte else 0.72)))
            x1 = contexto.ax + math.cos(ang) * inner_r
            y1 = contexto.ay + math.sin(ang) * inner_r
            x2 = contexto.ax + math.cos(ang) * outer_r
            y2 = contexto.ay + math.sin(ang) * outer_r
            pygame.draw.line(self.tela, contexto.paleta["mid"][0], (int(x1), int(y1)), (int(x2), int(y2)), 2 if contexto.zonal or contexto.cataclismo else 1)

    def _desenhar_centro_area_magica(self, contexto):
        if contexto.zonal:
            step = max(8, int(contexto.ar * 0.35))
            for gx in range(contexto.ax - contexto.ar + step, contexto.ax + contexto.ar, step):
                pygame.draw.line(self.tela, self._cor_com_alpha(contexto.paleta["outer"][0], 55), (gx, contexto.ay - contexto.ar + 6), (gx, contexto.ay + contexto.ar - 6), 1)
        motivo_raio = int(contexto.ar * (0.66 if contexto.zonal else 0.58 if contexto.suporte else 0.52 if contexto.ativo else 0.45))
        self._desenhar_motivo_circular_magia(contexto.ax, contexto.ay, motivo_raio, contexto.paleta, contexto.perfil, contexto.pulse_time, 1.0 if contexto.ativo else 0.78)
        if contexto.invocacao:
            self._desenhar_sigilo_magico(contexto.ax, contexto.ay, int(contexto.ar * 0.42), contexto.paleta, contexto.pulse_time, 1.1 if contexto.ativo else 0.8)
        elif contexto.suporte:
            pygame.draw.circle(self.tela, contexto.paleta["core"], (contexto.ax, contexto.ay), max(2, int(contexto.ar * 0.32)), 2)
            pygame.draw.circle(self.tela, contexto.paleta["mid"][0], (contexto.ax, contexto.ay), max(2, int(contexto.ar * 0.16)))
        elif contexto.perfil["motivo"] == "impacto":
            self._desenhar_sigilo_magico(contexto.ax, contexto.ay, int(contexto.ar * (0.22 if contexto.zonal else 0.28 if contexto.ativo else 0.4)), contexto.paleta, contexto.pulse_time, 1.0 if contexto.ativo else 0.8)

    def _desenhar_area_pilar_fogo(self, contexto):
        for i in range(4):
            ang = contexto.pulse_time * 0.55 + i * (math.pi / 2)
            base_x = contexto.ax + math.cos(ang) * contexto.ar * 0.42
            base_y = contexto.ay + math.sin(ang) * contexto.ar * 0.42
            topo = (base_x, base_y - contexto.ar * 0.42)
            lat_a = (base_x - contexto.ar * 0.08, base_y)
            lat_b = (base_x + contexto.ar * 0.08, base_y)
            pygame.draw.polygon(
                self.tela,
                self._cor_com_alpha(contexto.paleta["mid"][1], 170 if contexto.ativo else 110),
                [(int(lat_a[0]), int(lat_a[1])), (int(topo[0]), int(topo[1])), (int(lat_b[0]), int(lat_b[1]))],
            )

    def _desenhar_area_julgamento_celestial(self, contexto):
        for i in range(5):
            ang = contexto.pulse_time * 0.18 + i * (math.pi * 2 / 5)
            x = contexto.ax + math.cos(ang) * contexto.ar * 0.52
            y = contexto.ay + math.sin(ang) * contexto.ar * 0.52
            pygame.draw.line(self.tela, contexto.paleta["spark"], (int(x), int(y - contexto.ar * 0.22)), (int(x), int(y + contexto.ar * 0.14)), 2)
            pygame.draw.circle(self.tela, contexto.paleta["core"], (int(x), int(y + contexto.ar * 0.14)), max(2, int(contexto.ar * 0.05)))
        pygame.draw.line(self.tela, contexto.paleta["core"], (int(contexto.ax - contexto.ar * 0.25), int(contexto.ay)), (int(contexto.ax + contexto.ar * 0.25), int(contexto.ay)), 2)
        pygame.draw.line(self.tela, contexto.paleta["core"], (int(contexto.ax), int(contexto.ay - contexto.ar * 0.25)), (int(contexto.ax), int(contexto.ay + contexto.ar * 0.25)), 2)

    def _desenhar_area_redencao(self, contexto):
        for fator in (0.32, 0.54, 0.78):
            pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["spark"], 95), (contexto.ax, contexto.ay), max(2, int(contexto.ar * fator)), 1)
        for i in range(4):
            ang = contexto.pulse_time * 0.25 + i * (math.pi / 2)
            ex = contexto.ax + math.cos(ang) * contexto.ar * 0.7
            ey = contexto.ay + math.sin(ang) * contexto.ar * 0.7
            pygame.draw.line(self.tela, contexto.paleta["core"], (contexto.ax, contexto.ay), (int(ex), int(ey)), 1)

    def _desenhar_area_nevasca(self, contexto):
        for i in range(6):
            ang = contexto.pulse_time * 0.22 + i * (math.pi / 3)
            ex = contexto.ax + math.cos(ang) * contexto.ar * 0.62
            ey = contexto.ay + math.sin(ang) * contexto.ar * 0.62
            pygame.draw.line(self.tela, contexto.paleta["core"], (contexto.ax, contexto.ay), (int(ex), int(ey)), 1)
        for i in range(3):
            self._desenhar_arco_magico(
                contexto.ax,
                contexto.ay,
                int(contexto.ar * (0.42 + i * 0.12)),
                contexto.paleta["spark"],
                90,
                contexto.pulse_time * 0.35 + i,
                contexto.pulse_time * 0.35 + i + math.pi / 3,
                1,
            )

    def _desenhar_area_zero_absoluto(self, contexto):
        estrela = self._pontos_poligono_regular(contexto.ax, contexto.ay, contexto.ar * 0.62, 8, contexto.pulse_time * 0.12, 1.38)
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["core"], 150), [(int(px), int(py)) for px, py in estrela], 2)
        pygame.draw.circle(self.tela, contexto.paleta["spark"], (contexto.ax, contexto.ay), max(2, int(contexto.ar * 0.18)))

    def _desenhar_area_tempestade(self, contexto):
        for i in range(3):
            x1 = contexto.ax - contexto.ar * 0.75 + i * contexto.ar * 0.5
            y1 = contexto.ay - contexto.ar * 0.35
            x2 = x1 + contexto.ar * 0.35
            y2 = contexto.ay + contexto.ar * 0.45
            zig = self._gerar_linha_zigzag(x1, y1, x2, y2, contexto.ar * 0.11, 5, contexto.pulse_time * 8 + i)
            pygame.draw.lines(self.tela, contexto.paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)

    def _desenhar_area_julgamento_thor(self, contexto):
        bolt = self._gerar_linha_zigzag(contexto.ax, contexto.ay - contexto.ar * 0.9, contexto.ax, contexto.ay + contexto.ar * 0.05, contexto.ar * 0.12, 6, contexto.pulse_time * 10)
        pygame.draw.lines(self.tela, contexto.paleta["spark"], False, [(int(px), int(py)) for px, py in bolt], 3)
        pygame.draw.circle(self.tela, contexto.paleta["core"], (contexto.ax, contexto.ay), max(2, int(contexto.ar * 0.16)))

    def _desenhar_area_aniquilacao_void(self, contexto):
        pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 12), 210), (contexto.ax, contexto.ay), max(3, int(contexto.ar * 0.44)))
        for i in range(8):
            ang = contexto.pulse_time * 0.18 + i * (math.pi * 2 / 8)
            x1 = contexto.ax + math.cos(ang) * contexto.ar * 0.68
            y1 = contexto.ay + math.sin(ang) * contexto.ar * 0.68
            x2 = contexto.ax + math.cos(ang) * contexto.ar * 0.3
            y2 = contexto.ay + math.sin(ang) * contexto.ar * 0.3
            pygame.draw.line(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], 120), (int(x1), int(y1)), (int(x2), int(y2)), 2)

    def _desenhar_area_colapso_void(self, contexto):
        variante = contexto.assinatura.get("variante", "")
        for i in range(6):
            ang = contexto.pulse_time * 0.3 + i * (math.pi * 2 / 6)
            x1 = contexto.ax + math.cos(ang) * contexto.ar * 0.76
            y1 = contexto.ay + math.sin(ang) * contexto.ar * 0.76
            x2 = contexto.ax + math.cos(ang) * contexto.ar * 0.22
            y2 = contexto.ay + math.sin(ang) * contexto.ar * 0.22
            pygame.draw.line(
                self.tela,
                self._cor_com_alpha(contexto.paleta["spark"], 110),
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                1 if variante == "implosao_void" else 2,
            )
        pygame.draw.circle(self.tela, self._cor_com_alpha((4, 0, 10), 190), (contexto.ax, contexto.ay), max(3, int(contexto.ar * 0.28)))

    def _desenhar_variante_area_magica(self, contexto):
        variante = contexto.assinatura.get("variante", "")
        dispatch = {
            "pilar_fogo": self._desenhar_area_pilar_fogo,
            "julgamento_celestial": self._desenhar_area_julgamento_celestial,
            "redencao": self._desenhar_area_redencao,
            "nevasca": self._desenhar_area_nevasca,
            "zero_absoluto": self._desenhar_area_zero_absoluto,
            "tempestade": self._desenhar_area_tempestade,
            "julgamento_thor": self._desenhar_area_julgamento_thor,
            "aniquilacao_void": self._desenhar_area_aniquilacao_void,
            "colapso_void": self._desenhar_area_colapso_void,
            "implosao_void": self._desenhar_area_colapso_void,
        }
        drawer = dispatch.get(variante)
        if drawer is not None:
            drawer(contexto)

    def _desenhar_nucleo_area_magica(self, contexto):
        pygame.draw.circle(self.tela, contexto.paleta["mid"][0], (contexto.ax, contexto.ay), max(2, contexto.raio_visual), 2 if contexto.suporte else 3)
        pygame.draw.circle(
            self.tela,
            contexto.paleta["core"],
            (contexto.ax, contexto.ay),
            max(2, int(contexto.ar * (0.12 if contexto.suporte else 0.18 if not contexto.cataclismo else 0.22))),
        )

    def _desenhar_aviso_area_magica(self, contexto):
        aviso = self._get_surface(contexto.ar * 2 + 20, contexto.ar * 2 + 20, pygame.SRCALPHA)
        rect = pygame.Rect(10, 10, contexto.ar * 2, contexto.ar * 2)
        countdown = max(0.05, min(1.0, getattr(contexto.area, "delay", 0.0)))
        arc_end = math.radians(360 * countdown)
        pygame.draw.arc(aviso, self._cor_com_alpha((255, 240, 180), 220), rect, -math.pi / 2, -math.pi / 2 + arc_end, 4)
        self.tela.blit(aviso, (contexto.ax - contexto.ar - 10, contexto.ay - contexto.ar - 10))

    def _desenhar_area_magica(self, area, pulse_time):
        contexto = self._criar_contexto_area_magica(area, pulse_time)
        if contexto is None:
            return
        self._desenhar_base_area_magica(contexto)
        self._desenhar_aneis_area_magica(contexto)
        self._desenhar_marcadores_area_magica(contexto)
        self._desenhar_centro_area_magica(contexto)
        self._desenhar_variante_area_magica(contexto)
        self._desenhar_nucleo_area_magica(contexto)
        if not contexto.ativo:
            self._desenhar_aviso_area_magica(contexto)

    def _criar_contexto_beam_magico(self, beam, pulse_time):
        pts_screen = [self.cam.converter(bx * PPM, by * PPM) for bx, by in beam.segments]
        if len(pts_screen) < 2:
            return None

        classe = self._resolver_classe_magia(beam)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(beam, tipo=getattr(beam, "tipo_efeito", "BEAM"))
        elemento = self._detectar_elemento_visual(getattr(beam, "nome", ""), getattr(beam, "tipo_efeito", ""), None)
        paleta = self._paleta_magica(elemento, beam.cor)
        pulse = 0.84 + 0.26 * abs(math.sin(pulse_time * 12))
        forca = classe.get("classe_forca", "PRECISAO")
        utilidade = classe.get("classe_utilidade", "DANO")
        largura_base = 0.78 if forca == "PRECISAO" else 1.34 if forca == "PRESSAO" else 1.18 if forca == "CATACLISMO" else 1.0
        largura_efetiva = max(2, int(beam.largura * pulse * largura_base))

        min_x = int(min(p[0] for p in pts_screen) - largura_efetiva - 16)
        min_y = int(min(p[1] for p in pts_screen) - largura_efetiva - 16)
        max_x = int(max(p[0] for p in pts_screen) + largura_efetiva + 16)
        max_y = int(max(p[1] for p in pts_screen) + largura_efetiva + 16)
        width = int(max_x - min_x + 1)
        height = int(max_y - min_y + 1)
        if width <= 0 or height <= 0:
            return None

        local_pts = [(int(px - min_x), int(py - min_y)) for px, py in pts_screen]
        return MagicBeamRenderContext(
            beam=beam,
            pulse_time=pulse_time,
            pts_screen=pts_screen,
            classe=classe,
            perfil=perfil,
            assinatura=assinatura,
            elemento=elemento,
            paleta=paleta,
            pulse=pulse,
            forca=forca,
            utilidade=utilidade,
            largura_efetiva=largura_efetiva,
            min_x=min_x,
            min_y=min_y,
            width=width,
            height=height,
            local_pts=local_pts,
        )

    def _desenhar_corpo_beam_magico(self, contexto, surf):
        pygame.draw.lines(surf, self._cor_com_alpha(contexto.paleta["outer"][0], 60), False, contexto.local_pts, contexto.largura_efetiva + (10 if contexto.forca == "PRECISAO" else 14))
        pygame.draw.lines(surf, self._cor_com_alpha(contexto.paleta["mid"][0], 145), False, contexto.local_pts, contexto.largura_efetiva + (4 if contexto.forca == "PRECISAO" else 7))
        pygame.draw.lines(surf, self._cor_com_alpha(contexto.beam.cor, 255), False, contexto.local_pts, contexto.largura_efetiva)
        pygame.draw.lines(surf, self._cor_com_alpha(contexto.paleta["core"], 255), False, contexto.local_pts, max(1, contexto.largura_efetiva // 2))
        self._desenhar_ornamentos_feixe(surf, contexto.local_pts, contexto.paleta, contexto.perfil, contexto.pulse_time, contexto.largura_efetiva)

    def _desenhar_beam_sopro_dragao(self, contexto, surf):
        for i in range(len(contexto.local_pts) - 1):
            x1, y1 = contexto.local_pts[i]
            x2, y2 = contexto.local_pts[i + 1]
            seg_dx = x2 - x1
            seg_dy = y2 - y1
            seg_len = math.hypot(seg_dx, seg_dy)
            if seg_len < 4:
                continue
            perp_x = -seg_dy / seg_len
            perp_y = seg_dx / seg_len
            mx = x1 + seg_dx * 0.55
            my = y1 + seg_dy * 0.55
            for side in (-1, 1):
                ponta = (mx + perp_x * contexto.largura_efetiva * 1.35 * side, my + perp_y * contexto.largura_efetiva * 1.35 * side)
                base_a = (mx + perp_x * contexto.largura_efetiva * 0.35 * side, my + perp_y * contexto.largura_efetiva * 0.35 * side)
                base_b = (mx + seg_dx * 0.08, my + seg_dy * 0.08)
                pygame.draw.polygon(surf, self._cor_com_alpha(contexto.paleta["mid"][1], 90), [(int(base_a[0]), int(base_a[1])), (int(ponta[0]), int(ponta[1])), (int(base_b[0]), int(base_b[1]))])

    def _desenhar_beam_desintegrar(self, contexto, surf):
        for i in range(len(contexto.local_pts) - 1):
            x1, y1 = contexto.local_pts[i]
            x2, y2 = contexto.local_pts[i + 1]
            mx = int(x1 + (x2 - x1) * 0.5)
            my = int(y1 + (y2 - y1) * 0.5)
            pygame.draw.rect(
                surf,
                self._cor_com_alpha(contexto.paleta["spark"], 95),
                pygame.Rect(mx - contexto.largura_efetiva // 2, my - contexto.largura_efetiva // 2, max(2, contexto.largura_efetiva), max(2, contexto.largura_efetiva)),
                1,
            )

    def _desenhar_beam_raio_sagrado(self, contexto, surf):
        for i in range(0, len(contexto.local_pts), 2):
            px, py = contexto.local_pts[i]
            pygame.draw.line(surf, self._cor_com_alpha(contexto.paleta["spark"], 100), (int(px - contexto.largura_efetiva), int(py)), (int(px + contexto.largura_efetiva), int(py)), 1)
            pygame.draw.line(surf, self._cor_com_alpha(contexto.paleta["spark"], 100), (int(px), int(py - contexto.largura_efetiva)), (int(px), int(py + contexto.largura_efetiva)), 1)

    def _desenhar_beam_corrente_cadeia(self, contexto, surf):
        for i in range(len(contexto.local_pts) - 1):
            x1, y1 = contexto.local_pts[i]
            x2, y2 = contexto.local_pts[i + 1]
            zig = self._gerar_linha_zigzag(x1, y1, x2, y2, contexto.largura_efetiva * 0.55, 5, contexto.pulse_time * 11 + i)
            pygame.draw.lines(surf, self._cor_com_alpha(contexto.paleta["spark"], 120), False, [(int(px), int(py)) for px, py in zig], max(1, contexto.largura_efetiva // 4))

    def _desenhar_beam_devorar(self, contexto, surf):
        for i in range(len(contexto.local_pts) - 1):
            x1, y1 = contexto.local_pts[i]
            x2, y2 = contexto.local_pts[i + 1]
            seg_dx = x2 - x1
            seg_dy = y2 - y1
            seg_len = math.hypot(seg_dx, seg_dy)
            if seg_len < 5:
                continue
            perp_x = -seg_dy / seg_len
            perp_y = seg_dx / seg_len
            mx = x1 + seg_dx * 0.5
            my = y1 + seg_dy * 0.5
            for side in (-1, 1):
                ox = mx + perp_x * contexto.largura_efetiva * 0.95 * side
                oy = my + perp_y * contexto.largura_efetiva * 0.95 * side
                pygame.draw.circle(surf, self._cor_com_alpha((10, 0, 20), 150), (int(ox), int(oy)), max(1, contexto.largura_efetiva // 3))

    def _desenhar_beam_rasgo_dimensional(self, contexto, surf):
        for i in range(len(contexto.local_pts) - 1):
            x1, y1 = contexto.local_pts[i]
            x2, y2 = contexto.local_pts[i + 1]
            seg_dx = x2 - x1
            seg_dy = y2 - y1
            seg_len = math.hypot(seg_dx, seg_dy)
            if seg_len < 6:
                continue
            perp_x = -seg_dy / seg_len
            perp_y = seg_dx / seg_len
            mx = x1 + seg_dx * 0.5
            my = y1 + seg_dy * 0.5
            pygame.draw.line(
                surf,
                self._cor_com_alpha(contexto.paleta["mid"][1], 115),
                (int(mx - perp_x * contexto.largura_efetiva * 1.25), int(my - perp_y * contexto.largura_efetiva * 1.25)),
                (int(mx + perp_x * contexto.largura_efetiva * 1.25), int(my + perp_y * contexto.largura_efetiva * 1.25)),
                2,
            )

    def _desenhar_variante_beam_magico(self, contexto, surf):
        variante = contexto.assinatura.get("variante", "")
        dispatch = {
            "sopro_dragao": self._desenhar_beam_sopro_dragao,
            "desintegrar": self._desenhar_beam_desintegrar,
            "raio_sagrado": self._desenhar_beam_raio_sagrado,
            "corrente_cadeia": self._desenhar_beam_corrente_cadeia,
            "devorar": self._desenhar_beam_devorar,
            "rasgo_dimensional": self._desenhar_beam_rasgo_dimensional,
        }
        drawer = dispatch.get(variante)
        if drawer is not None:
            drawer(contexto, surf)

    def _desenhar_terminais_beam_magico(self, contexto):
        sx, sy = contexto.pts_screen[0]
        ex, ey = contexto.pts_screen[-1]
        self._desenhar_glow_circular(sx, sy, contexto.largura_efetiva * (1.9 if contexto.perfil["suavidade"] < 0.8 else 1.6), contexto.paleta["mid"][0], 80)
        self._desenhar_glow_circular(ex, ey, contexto.largura_efetiva * (3.0 if contexto.perfil["ornamento"] == "espinhos" else 2.3 if contexto.utilidade in {"PROTECAO", "CURA"} else 2.6), contexto.paleta["core"], 120)
        if contexto.perfil["motivo"] in {"protecao", "cura", "invocacao"}:
            self._desenhar_motivo_circular_magia(ex, ey, int(contexto.largura_efetiva * 1.25), contexto.paleta, contexto.perfil, contexto.pulse_time, 0.72)

    def _desenhar_beam_magico(self, beam, pulse_time):
        contexto = self._criar_contexto_beam_magico(beam, pulse_time)
        if contexto is None:
            return

        surf = self._get_surface(contexto.width, contexto.height, pygame.SRCALPHA)
        self._desenhar_corpo_beam_magico(contexto, surf)
        self._desenhar_variante_beam_magico(contexto, surf)
        self.tela.blit(surf, (contexto.min_x, contexto.min_y))
        self._desenhar_terminais_beam_magico(contexto)

    def _desenhar_trilha_magica(self, trail_pts, cor, largura_base):
        for i in range(1, len(trail_pts)):
            t = i / len(trail_pts)
            alpha = int(255 * t * 0.65)
            largura = max(1, int(largura_base * (0.45 + t)))
            p1 = self.cam.converter(trail_pts[i - 1][0] * PPM, trail_pts[i - 1][1] * PPM)
            p2 = self.cam.converter(trail_pts[i][0] * PPM, trail_pts[i][1] * PPM)
            surf_w = abs(int(p2[0] - p1[0])) + largura * 5
            surf_h = abs(int(p2[1] - p1[1])) + largura * 5
            if surf_w <= 2 or surf_h <= 2:
                continue
            surf = self._get_surface(surf_w, surf_h, pygame.SRCALPHA)
            offset_x = min(p1[0], p2[0]) - largura * 2
            offset_y = min(p1[1], p2[1]) - largura * 2
            local_p1 = (int(p1[0] - offset_x), int(p1[1] - offset_y))
            local_p2 = (int(p2[0] - offset_x), int(p2[1] - offset_y))
            pygame.draw.line(surf, self._cor_com_alpha(cor, alpha // 3), local_p1, local_p2, largura * 2)
            pygame.draw.line(surf, self._cor_com_alpha(cor, alpha), local_p1, local_p2, largura)
            self.tela.blit(surf, (offset_x, offset_y))

    def _criar_contexto_projetil_magico(self, proj, px, py, pr, pulse_time, ang_visual, cor):
        classe = self._resolver_classe_magia(proj)
        perfil = self._perfil_visual_magia(classe)
        assinatura_especifica = self._assinatura_magia_especifica(proj, tipo=getattr(proj, "tipo", "PROJETIL"))
        elemento = self._detectar_elemento_visual(
            getattr(proj, "nome", ""),
            getattr(proj, "tipo", ""),
            getattr(proj, "elemento", None),
        )
        paleta = self._paleta_magica(elemento, cor)
        assinatura = classe.get("assinatura_visual", "cometa")
        utilidade = classe.get("classe_utilidade", "DANO")
        forca = classe.get("classe_forca", "IMPACTO")
        rad = math.radians(ang_visual)
        drift = pulse_time + (id(proj) % 97) * 0.11
        tail_len = max(pr * 2.4, 10)
        return MagicProjectileRenderContext(
            proj=proj,
            classe=classe,
            perfil=perfil,
            assinatura_especifica=assinatura_especifica,
            elemento=elemento,
            paleta=paleta,
            assinatura=assinatura,
            utilidade=utilidade,
            forca=forca,
            variante=assinatura_especifica.get("variante", ""),
            px=px,
            py=py,
            pr=pr,
            pulse_time=pulse_time,
            ang_visual=ang_visual,
            cor=cor,
            rad=rad,
            drift=drift,
            tail_len=tail_len,
            tail_x=px - math.cos(rad) * tail_len,
            tail_y=py - math.sin(rad) * tail_len,
        )

    def _desenhar_preludio_projetil_magico(self, contexto):
        self._desenhar_glow_circular(contexto.px, contexto.py, contexto.pr * 2.5, contexto.paleta["outer"][0], 65)
        wake = self._get_surface(int(contexto.pr * 6 + 20), int(contexto.pr * 6 + 20), pygame.SRCALPHA)
        wc = wake.get_width() // 2
        hc = wake.get_height() // 2
        wake_pts = [
            (wc + math.cos(contexto.rad) * contexto.pr * 1.7, hc + math.sin(contexto.rad) * contexto.pr * 1.7),
            (wc + math.cos(contexto.rad + 2.45) * contexto.pr * 0.9, hc + math.sin(contexto.rad + 2.45) * contexto.pr * 0.9),
            (wc - math.cos(contexto.rad) * contexto.pr * 2.6, hc - math.sin(contexto.rad) * contexto.pr * 2.6),
            (wc + math.cos(contexto.rad - 2.45) * contexto.pr * 0.9, hc + math.sin(contexto.rad - 2.45) * contexto.pr * 0.9),
        ]
        pygame.draw.polygon(wake, self._cor_com_alpha(contexto.paleta["outer"][0], 55), wake_pts)
        self.tela.blit(wake, (int(contexto.px) - wc, int(contexto.py) - hc))

        if hasattr(contexto.proj, "trail") and len(contexto.proj.trail) > 1:
            self._desenhar_trilha_magica(contexto.proj.trail, contexto.paleta["mid"][0], max(2, contexto.pr))

    def _desenhar_projetil_bola_fogo(self, contexto):
        for off in (0.0, 2.1, 4.2):
            ponto_x = contexto.px + math.cos(contexto.drift * 2.5 + off) * contexto.pr * 0.34
            ponto_y = contexto.py + math.sin(contexto.drift * 2.5 + off) * contexto.pr * 0.34
            pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], 185), (int(ponto_x), int(ponto_y)), max(2, int(contexto.pr * 0.52)))
        pygame.draw.circle(self.tela, contexto.paleta["core"], (int(contexto.px), int(contexto.py)), max(2, int(contexto.pr * 0.5)))
        return True

    def _desenhar_projetil_cometa_rastreador(self, contexto):
        cauda = [
            (contexto.px + math.cos(contexto.rad) * contexto.pr * 1.9, contexto.py + math.sin(contexto.rad) * contexto.pr * 1.9),
            (contexto.px + math.cos(contexto.rad + 2.55) * contexto.pr * 0.82, contexto.py + math.sin(contexto.rad + 2.55) * contexto.pr * 0.82),
            (contexto.px - math.cos(contexto.rad) * contexto.pr * 3.6, contexto.py - math.sin(contexto.rad) * contexto.pr * 3.6),
            (contexto.px + math.cos(contexto.rad - 2.55) * contexto.pr * 0.82, contexto.py + math.sin(contexto.rad - 2.55) * contexto.pr * 0.82),
        ]
        pygame.draw.polygon(self.tela, self._cor_com_alpha(contexto.paleta["mid"][1], 180), [(int(x), int(y)) for x, y in cauda])
        for scale in (0.7, 1.05):
            ex = contexto.px - math.cos(contexto.rad) * contexto.pr * (2.8 + scale)
            ey = contexto.py - math.sin(contexto.rad) * contexto.pr * (2.8 + scale)
            pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["spark"], 85), (int(ex), int(ey)), max(1, int(contexto.pr * 0.18 * scale)))
        return True

    def _desenhar_projetil_meteoro_brutal(self, contexto):
        rocha = self._pontos_poligono_regular(contexto.px, contexto.py, contexto.pr * 1.18, 7, contexto.drift * 0.2, 1.18)
        pygame.draw.polygon(self.tela, (88, 40, 18), [(int(x), int(y)) for x, y in rocha])
        for ang in (contexto.rad, contexto.rad + 1.9, contexto.rad - 1.6):
            ex = contexto.px + math.cos(ang) * contexto.pr * 0.92
            ey = contexto.py + math.sin(ang) * contexto.pr * 0.92
            pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.px), int(contexto.py)), (int(ex), int(ey)), 2)
        return True

    def _desenhar_projetil_lanca_luz(self, contexto):
        haste = [
            (contexto.px + math.cos(contexto.rad) * contexto.pr * 2.1, contexto.py + math.sin(contexto.rad) * contexto.pr * 2.1),
            (contexto.px + math.cos(contexto.rad + 2.55) * contexto.pr * 0.55, contexto.py + math.sin(contexto.rad + 2.55) * contexto.pr * 0.55),
            (contexto.tail_x, contexto.tail_y),
            (contexto.px + math.cos(contexto.rad - 2.55) * contexto.pr * 0.55, contexto.py + math.sin(contexto.rad - 2.55) * contexto.pr * 0.55),
        ]
        pygame.draw.polygon(self.tela, contexto.paleta["core"], [(int(x), int(y)) for x, y in haste])
        pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.px - contexto.pr * 1.1), int(contexto.py)), (int(contexto.px + contexto.pr * 1.1), int(contexto.py)), 1)
        pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.px), int(contexto.py - contexto.pr * 1.1)), (int(contexto.px), int(contexto.py + contexto.pr * 1.1)), 1)
        return True

    def _desenhar_projetil_lanca_gelo(self, contexto):
        cristal = [
            (contexto.px + math.cos(contexto.rad) * contexto.pr * 2.0, contexto.py + math.sin(contexto.rad) * contexto.pr * 2.0),
            (contexto.px + math.cos(contexto.rad + 2.45) * contexto.pr * 0.78, contexto.py + math.sin(contexto.rad + 2.45) * contexto.pr * 0.78),
            (contexto.px - math.cos(contexto.rad) * contexto.pr * 1.35, contexto.py - math.sin(contexto.rad) * contexto.pr * 1.35),
            (contexto.px + math.cos(contexto.rad - 2.45) * contexto.pr * 0.78, contexto.py + math.sin(contexto.rad - 2.45) * contexto.pr * 0.78),
        ]
        pygame.draw.polygon(self.tela, contexto.paleta["mid"][0], [(int(x), int(y)) for x, y in cristal], 2)
        pygame.draw.line(self.tela, contexto.paleta["core"], (int(contexto.px - contexto.pr * 0.8), int(contexto.py)), (int(contexto.px + contexto.pr * 1.2), int(contexto.py)), 1)
        return True

    def _desenhar_projetil_misseis_arcanos(self, contexto):
        for orbit in (0.0, 2.09, 4.18):
            sx = contexto.px + math.cos(contexto.drift * 3.0 + orbit) * contexto.pr * 0.58
            sy = contexto.py + math.sin(contexto.drift * 3.0 + orbit) * contexto.pr * 0.58
            pygame.draw.circle(self.tela, self._cor_com_alpha(contexto.paleta["spark"], 110), (int(sx), int(sy)), max(1, int(contexto.pr * 0.22)))
        pygame.draw.circle(self.tela, contexto.paleta["core"], (int(contexto.px), int(contexto.py)), max(2, int(contexto.pr * 0.4)))
        return True

    def _desenhar_projetil_orbe_mana(self, contexto):
        pygame.draw.circle(self.tela, contexto.paleta["mid"][0], (int(contexto.px), int(contexto.py)), int(contexto.pr * 1.15), 2)
        for orbit in (0.0, math.pi):
            sx = contexto.px + math.cos(contexto.drift * 1.8 + orbit) * contexto.pr * 0.88
            sy = contexto.py + math.sin(contexto.drift * 1.8 + orbit) * contexto.pr * 0.88
            pygame.draw.circle(self.tela, contexto.paleta["spark"], (int(sx), int(sy)), max(1, int(contexto.pr * 0.18)))
        return True

    def _desenhar_projetil_martelo_trovao(self, contexto):
        cabeca = [
            (contexto.px + math.cos(contexto.rad) * contexto.pr * 1.05, contexto.py + math.sin(contexto.rad) * contexto.pr * 1.05),
            (contexto.px + math.cos(contexto.rad + 1.1) * contexto.pr * 0.92, contexto.py + math.sin(contexto.rad + 1.1) * contexto.pr * 0.92),
            (contexto.px + math.cos(contexto.rad + math.pi) * contexto.pr * 0.32, contexto.py + math.sin(contexto.rad + math.pi) * contexto.pr * 0.32),
            (contexto.px + math.cos(contexto.rad - 1.1) * contexto.pr * 0.92, contexto.py + math.sin(contexto.rad - 1.1) * contexto.pr * 0.92),
        ]
        pygame.draw.polygon(self.tela, contexto.paleta["mid"][0], [(int(x), int(y)) for x, y in cabeca])
        pygame.draw.line(self.tela, contexto.paleta["spark"], (int(contexto.px), int(contexto.py)), (int(contexto.tail_x), int(contexto.tail_y)), max(1, int(contexto.pr * 0.28)))
        return True

    def _desenhar_projetil_sentenca_void(self, contexto):
        pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 210), (int(contexto.px), int(contexto.py)), max(2, int(contexto.pr * 0.95)))
        self._desenhar_arco_magico(contexto.px, contexto.py, int(contexto.pr * 1.15), contexto.paleta["mid"][0], 110, contexto.drift * 0.6, contexto.drift * 0.6 + math.pi * 1.1, 2)
        self._desenhar_arco_magico(contexto.px, contexto.py, int(contexto.pr * 0.78), contexto.paleta["spark"], 90, contexto.drift * -0.7, contexto.drift * -0.7 + math.pi * 0.9, 1)
        return True

    def _desenhar_variante_explicita_projetil_magico(self, contexto):
        dispatch = {
            "bola_fogo": self._desenhar_projetil_bola_fogo,
            "cometa_rastreador": self._desenhar_projetil_cometa_rastreador,
            "meteoro_brutal": self._desenhar_projetil_meteoro_brutal,
            "lanca_luz": self._desenhar_projetil_lanca_luz,
            "lanca_gelo": self._desenhar_projetil_lanca_gelo,
            "misseis_arcanos": self._desenhar_projetil_misseis_arcanos,
            "orbe_mana": self._desenhar_projetil_orbe_mana,
            "martelo_trovao": self._desenhar_projetil_martelo_trovao,
            "sentenca_void": self._desenhar_projetil_sentenca_void,
        }
        drawer = dispatch.get(contexto.variante)
        return drawer(contexto) if drawer is not None else False

    def _desenhar_motivo_projetil_magico(self, contexto):
        px = contexto.px
        py = contexto.py
        pr = contexto.pr
        rad = contexto.rad
        drift = contexto.drift
        paleta = contexto.paleta
        motivo = contexto.perfil["motivo"]

        if motivo == "protecao":
            escudo = self._pontos_poligono_regular(px, py, pr * 1.28, 6, rad + math.pi / 6)
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in escudo], 2)
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.52)))
            return True
        if motivo == "cura":
            for i in range(4):
                ang = drift * 0.9 + i * (math.pi / 2)
                ponta = (px + math.cos(ang) * pr * 1.25, py + math.sin(ang) * pr * 1.25)
                base_esq = (px + math.cos(ang + 0.8) * pr * 0.45, py + math.sin(ang + 0.8) * pr * 0.45)
                base_dir = (px + math.cos(ang - 0.8) * pr * 0.45, py + math.sin(ang - 0.8) * pr * 0.45)
                pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][1], 170), [(int(base_esq[0]), int(base_esq[1])), (int(ponta[0]), int(ponta[1])), (int(base_dir[0]), int(base_dir[1]))])
            return True
        if motivo == "invocacao":
            tri = self._pontos_poligono_regular(px, py, pr * 1.26, 3, rad - math.pi / 2)
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in tri], 2)
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.38)))
            return True
        if motivo == "controle":
            grade = self._pontos_poligono_regular(px, py, pr * 1.1, 6, drift * 0.22)
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in grade], 2)
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr), int(py)), (int(px + pr), int(py)), 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py - pr)), (int(px), int(py + pr)), 1)
            return True
        if motivo == "disrupcao":
            losango = [
                (px + math.cos(rad) * pr * 1.25, py + math.sin(rad) * pr * 1.25),
                (px + math.cos(rad + math.pi / 2) * pr * 0.65, py + math.sin(rad + math.pi / 2) * pr * 0.65),
                (px - math.cos(rad) * pr * 0.95, py - math.sin(rad) * pr * 0.95),
                (px + math.cos(rad - math.pi / 2) * pr * 0.65, py + math.sin(rad - math.pi / 2) * pr * 0.65),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in losango], 2)
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr * 0.8), int(py - pr * 0.2)), (int(px + pr * 0.8), int(py + pr * 0.2)), 2)
            return True
        if motivo == "amplificacao":
            for scale in (1.2, 0.78):
                seta = [
                    (px + math.cos(rad) * pr * scale * 1.45, py + math.sin(rad) * pr * scale * 1.45),
                    (px + math.cos(rad + 2.45) * pr * scale * 0.55, py + math.sin(rad + 2.45) * pr * scale * 0.55),
                    (px - math.cos(rad) * pr * scale * 0.55, py - math.sin(rad) * pr * scale * 0.55),
                    (px + math.cos(rad - 2.45) * pr * scale * 0.55, py + math.sin(rad - 2.45) * pr * scale * 0.55),
                ]
                pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], 120 if scale > 1.0 else 200), [(int(x), int(y)) for x, y in seta], 2 if scale > 1.0 else 0)
            return True
        return False

    def _desenhar_assinatura_projetil_magico(self, contexto):
        px = contexto.px
        py = contexto.py
        pr = contexto.pr
        rad = contexto.rad
        drift = contexto.drift
        paleta = contexto.paleta
        assinatura = contexto.assinatura

        if assinatura == "lanca":
            pts = [
                (px + math.cos(rad) * pr * 2.0, py + math.sin(rad) * pr * 2.0),
                (px + math.cos(rad + 2.55) * pr * 0.7, py + math.sin(rad + 2.55) * pr * 0.7),
                (contexto.tail_x, contexto.tail_y),
                (px + math.cos(rad - 2.55) * pr * 0.7, py + math.sin(rad - 2.55) * pr * 0.7),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in pts])
            return True
        if assinatura == "fluxo":
            wave = []
            for i in range(5):
                step = i / 4
                wx = px - math.cos(rad) * pr * (1.8 - step * 2.4)
                wy = py - math.sin(rad) * pr * (1.8 - step * 2.4)
                sway = math.sin(drift * 8 + i) * pr * 0.28
                wave.append((wx + math.cos(rad + math.pi / 2) * sway, wy + math.sin(rad + math.pi / 2) * sway))
            pygame.draw.lines(self.tela, paleta["mid"][0], False, [(int(x), int(y)) for x, y in wave], max(2, int(pr * 0.8)))
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.45)))
            return True
        if assinatura in {"campo", "domo"}:
            poly = []
            lados = 6 if assinatura == "campo" else 8
            for i in range(lados):
                ang = rad + i * (math.pi * 2 / lados)
                dist = pr * (1.35 if i % 2 == 0 else 1.0)
                poly.append((px + math.cos(ang) * dist, py + math.sin(ang) * dist))
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in poly], 2)
            pygame.draw.circle(self.tela, paleta["mid"][1], (int(px), int(py)), max(1, int(pr * 0.7)))
            return True
        if assinatura in {"sigilo", "anel", "aurea"}:
            pygame.draw.circle(self.tela, paleta["mid"][0], (int(px), int(py)), int(pr), 2)
            self._desenhar_sigilo_magico(px, py, int(pr * 1.1), paleta, drift, 0.65)
            return True
        return False

    def _desenhar_fallback_projetil_magico(self, contexto):
        flame = [
            (contexto.px + math.cos(contexto.rad) * contexto.pr * 1.8, contexto.py + math.sin(contexto.rad) * contexto.pr * 1.8),
            (contexto.px + math.cos(contexto.rad + 2.2) * contexto.pr * 0.9, contexto.py + math.sin(contexto.rad + 2.2) * contexto.pr * 0.9),
            (contexto.tail_x, contexto.tail_y),
            (contexto.px + math.cos(contexto.rad - 2.2) * contexto.pr * 0.9, contexto.py + math.sin(contexto.rad - 2.2) * contexto.pr * 0.9),
        ]
        pygame.draw.polygon(self.tela, contexto.paleta["mid"][1], [(int(x), int(y)) for x, y in flame])
        pygame.draw.circle(self.tela, contexto.paleta["mid"][0], (int(contexto.px), int(contexto.py)), int(contexto.pr))

    def _desenhar_overlay_elemental_projetil_magico(self, contexto):
        px = contexto.px
        py = contexto.py
        pr = contexto.pr
        paleta = contexto.paleta
        elemento = contexto.elemento

        if elemento == "GELO":
            pygame.draw.line(self.tela, paleta["core"], (int(px - pr * 0.9), int(py)), (int(px + pr * 0.9), int(py)), 2)
        elif elemento == "RAIO":
            for i in range(2 if contexto.forca == "PRECISAO" else 3):
                ang = contexto.drift * 12 + i * (math.pi * 2 / max(1, 2 if contexto.forca == "PRECISAO" else 3))
                ex = px + math.cos(ang) * pr * 1.6
                ey = py + math.sin(ang) * pr * 1.6
                pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py)), (int(ex), int(ey)), 1)
        elif elemento in {"TREVAS", "VOID"}:
            pygame.draw.circle(self.tela, (10, 0, 18), (int(px), int(py)), int(pr * 1.1), 1)
        elif elemento == "LUZ":
            pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py - pr * 1.4)), (int(px), int(py + pr * 1.4)), 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr * 1.4), int(py)), (int(px + pr * 1.4), int(py)), 1)
        elif elemento == "ARCANO":
            self._desenhar_sigilo_magico(px, py, int(pr * 0.9), contexto.paleta, contexto.drift, 0.4)
        elif elemento == "NATUREZA":
            for off in (-0.55, 0.55):
                ex = px + math.cos(contexto.rad + off) * pr * 1.4
                ey = py + math.sin(contexto.rad + off) * pr * 1.4
                pygame.draw.line(self.tela, contexto.paleta["outer"][0], (int(px), int(py)), (int(ex), int(ey)), 2)
        elif elemento == "SANGUE":
            drip = [(int(px - pr * 0.28), int(py)), (int(px + pr * 0.28), int(py)), (int(px), int(py + pr * 1.6))]
            pygame.draw.polygon(self.tela, contexto.paleta["outer"][0], drip)

    def _desenhar_nucleo_projetil_magico(self, contexto):
        pygame.draw.circle(self.tela, contexto.paleta["core"], (int(contexto.px), int(contexto.py)), max(1, int(contexto.pr * 0.42)))
        pygame.draw.circle(self.tela, contexto.paleta["spark"], (int(contexto.px), int(contexto.py)), max(1, int(contexto.pr * 0.18)))
        if contexto.perfil["motivo"] in {"protecao", "cura", "invocacao"}:
            self._desenhar_motivo_circular_magia(contexto.px, contexto.py, int(contexto.pr * 1.35), contexto.paleta, contexto.perfil, contexto.drift, 0.62)

    def _criar_contexto_orbe_magico(self, orbe, ox, oy, or_visual):
        classe = self._resolver_classe_magia(orbe, tipo="ORBE", elemento=getattr(orbe, "elemento", None))
        perfil = self._perfil_visual_magia(classe)
        elemento = self._detectar_elemento_visual(getattr(orbe, "nome", ""), getattr(orbe, "estado", ""), getattr(orbe, "elemento", None))
        paleta = self._paleta_magica(elemento, orbe.cor)
        assinatura = classe.get("assinatura_visual", "anel")
        utilidade = classe.get("classe_utilidade", "DANO")
        pulso = 0.7 + 0.3 * math.sin(orbe.pulso)
        return MagicOrbRenderContext(
            orbe=orbe,
            ox=ox,
            oy=oy,
            or_visual=or_visual,
            classe=classe,
            perfil=perfil,
            elemento=elemento,
            paleta=paleta,
            assinatura=assinatura,
            utilidade=utilidade,
            pulso=pulso,
        )

    def _desenhar_trilha_orbe_magico(self, contexto):
        if contexto.orbe.estado == "disparando" and len(contexto.orbe.trail) > 1:
            self._desenhar_trilha_magica(contexto.orbe.trail, contexto.paleta["mid"][0], max(2, int(contexto.or_visual * 0.8)))

    def _desenhar_particulas_orbe_magico(self, contexto):
        for part in contexto.orbe.particulas:
            ppx, ppy = self.cam.converter(part['x'] * PPM, part['y'] * PPM)
            palpha = int(255 * (part['vida'] / 0.3))
            glow_r = 4
            surf = self._get_surface(glow_r * 2 + 4, glow_r * 2 + 4, pygame.SRCALPHA)
            pygame.draw.circle(surf, self._cor_com_alpha(part['cor'], palpha), (glow_r + 2, glow_r + 2), glow_r)
            self.tela.blit(surf, (ppx - glow_r - 2, ppy - glow_r - 2))

    def _desenhar_corpo_orbe_magico(self, contexto):
        self._desenhar_glow_circular(
            contexto.ox,
            contexto.oy,
            contexto.or_visual * (1.9 if contexto.utilidade in {"CURA", "PROTECAO"} else 2.2 + contexto.pulso * 0.3),
            contexto.paleta["outer"][0],
            85 * contexto.pulso,
        )
        self._desenhar_motivo_circular_magia(
            contexto.ox,
            contexto.oy,
            int(contexto.or_visual * (1.45 if contexto.perfil["motivo"] in {"controle", "disrupcao"} else 1.2)),
            contexto.paleta,
            contexto.perfil,
            contexto.orbe.pulso,
            0.86,
        )
        if contexto.assinatura in {"sigilo", "aurea"}:
            self._desenhar_sigilo_magico(
                contexto.ox,
                contexto.oy,
                int(contexto.or_visual * (1.4 + 0.2 * contexto.pulso)),
                contexto.paleta,
                contexto.orbe.pulso,
                0.9,
            )
        else:
            pygame.draw.circle(self.tela, contexto.paleta["mid"][0], (int(contexto.ox), int(contexto.oy)), int(contexto.or_visual * 1.4), 2)
        pygame.draw.circle(self.tela, contexto.paleta["mid"][0], (int(contexto.ox), int(contexto.oy)), int(contexto.or_visual))
        pygame.draw.circle(self.tela, contexto.paleta["core"], (int(contexto.ox), int(contexto.oy)), max(1, int(contexto.or_visual * 0.48)))

    def _desenhar_carga_orbe_magico(self, contexto):
        carga_pct = min(1.0, contexto.orbe.tempo_carga / max(contexto.orbe.carga_max, 0.001))
        ring_r = int(contexto.or_visual * (1.8 + carga_pct * 1.3))
        pygame.draw.circle(self.tela, contexto.paleta["spark"], (int(contexto.ox), int(contexto.oy)), ring_r, 2)
        for i in range(4):
            ang = contexto.orbe.pulso * 0.9 + i * (math.pi / 2)
            ex = contexto.ox + math.cos(ang) * ring_r
            ey = contexto.oy + math.sin(ang) * ring_r
            pygame.draw.line(self.tela, contexto.paleta["mid"][1], (int(contexto.ox), int(contexto.oy)), (int(ex), int(ey)), 1)
        if contexto.perfil["motivo"] in {"invocacao", "protecao", "cura"}:
            self._desenhar_motivo_circular_magia(
                contexto.ox,
                contexto.oy,
                int(ring_r * 0.58),
                contexto.paleta,
                contexto.perfil,
                contexto.orbe.pulso + carga_pct,
                0.74,
            )

    def _desenhar_projetil_magico(self, proj, px, py, pr, pulse_time, ang_visual, cor):
        contexto = self._criar_contexto_projetil_magico(proj, px, py, pr, pulse_time, ang_visual, cor)
        self._desenhar_preludio_projetil_magico(contexto)
        if not self._desenhar_variante_explicita_projetil_magico(contexto):
            if not self._desenhar_motivo_projetil_magico(contexto):
                if not self._desenhar_assinatura_projetil_magico(contexto):
                    self._desenhar_fallback_projetil_magico(contexto)
        self._desenhar_overlay_elemental_projetil_magico(contexto)
        self._desenhar_nucleo_projetil_magico(contexto)

    def _desenhar_orbe_magico(self, orbe):
        ox, oy = self.cam.converter(orbe.x * PPM, orbe.y * PPM)
        or_visual = self.cam.converter_tam(orbe.raio_visual * PPM)
        if or_visual <= 0:
            return
        contexto = self._criar_contexto_orbe_magico(orbe, ox, oy, or_visual)
        self._desenhar_trilha_orbe_magico(contexto)
        self._desenhar_particulas_orbe_magico(contexto)
        self._desenhar_corpo_orbe_magico(contexto)
        if orbe.estado == "carregando":
            self._desenhar_carga_orbe_magico(contexto)

    def _resolver_alcance_presenca_arma(self, raio, familia, tipo):
        return raio * {
            "lamina": 1.75,
            "haste": 2.05,
            "dupla": 1.28,
            "corrente": 2.2,
            "arremesso": 1.18,
            "disparo": 1.55,
            "orbital": 1.78,
            "foco": 1.62,
            "hibrida": 1.92,
        }.get(familia, {
            "reta": 1.8,
            "dupla": 1.35,
            "corrente": 2.1,
            "arco": 1.5,
            "arremesso": 1.2,
            "orbital": 1.7,
            "magica": 1.6,
            "transformavel": 1.9,
        }.get(tipo, 1.5))

    def _criar_contexto_presenca_arma(self, lutador, centro, raio, anim_scale):
        arma = lutador.dados.arma_obj
        if not arma:
            return None

        perfil_visual = getattr(arma, "perfil_visual", {}) or {}
        cor = (getattr(arma, "r", 180), getattr(arma, "g", 180), getattr(arma, "b", 180))
        tipo = _texto_normalizado(getattr(arma, "tipo", ""))
        familia = getattr(arma, "familia", None) or inferir_familia(getattr(arma, "tipo", ""), getattr(arma, "estilo", ""))
        rad = math.radians(getattr(lutador, "angulo_arma_visual", getattr(lutador, "angulo_olhar", 0.0)))
        alcance = self._resolver_alcance_presenca_arma(raio, familia, tipo)
        tip_x = centro[0] + math.cos(rad) * alcance
        tip_y = centro[1] + math.sin(rad) * alcance
        intensidade = max(0.0, anim_scale - 0.92)
        if intensidade <= 0.05 and familia not in {"foco", "orbital"} and tipo not in {"magica", "orbital"}:
            return None

        brilho = float(perfil_visual.get("brilho", 0.18) or 0.18)
        ornamento = perfil_visual.get("ornamento", "")
        perp_x = math.cos(rad + math.pi / 2.0)
        perp_y = math.sin(rad + math.pi / 2.0)
        usa_paleta_magica = familia in {"foco", "orbital"} or tipo in {"magica", "orbital"} or ornamento in {"anel_runico", "sigilo_orbital"}
        paleta = self._paleta_magica(getattr(arma, "afinidade_elemento", None), cor) if usa_paleta_magica else None
        return WeaponPresenceRenderContext(
            lutador=lutador,
            arma=arma,
            centro=centro,
            raio=raio,
            anim_scale=anim_scale,
            perfil_visual=perfil_visual,
            cor=cor,
            tipo=tipo,
            familia=familia,
            rad=rad,
            alcance=alcance,
            tip_x=tip_x,
            tip_y=tip_y,
            intensidade=intensidade,
            brilho=brilho,
            aura_alpha=int(30 + 90 * min(1.0, intensidade * (1.4 + brilho * 1.5))),
            glow_r=max(6, int(raio * (0.22 + brilho * 0.24 + intensidade * 0.22))),
            ornamento=ornamento,
            perp_x=perp_x,
            perp_y=perp_y,
            tempo_ticks=pygame.time.get_ticks(),
            paleta=paleta,
        )

    def _desenhar_aura_presenca_arma(self, contexto):
        self._desenhar_glow_circular(contexto.tip_x, contexto.tip_y, contexto.glow_r, contexto.cor, contexto.aura_alpha)

    def _desenhar_presenca_lamina_haste(self, contexto):
        back_x = contexto.tip_x - math.cos(contexto.rad) * contexto.raio * 0.55
        back_y = contexto.tip_y - math.sin(contexto.rad) * contexto.raio * 0.55
        cor_linha = self._misturar_cor(contexto.cor, (255, 255, 255), 0.4)
        pygame.draw.line(
            self.tela,
            cor_linha,
            (int(back_x), int(back_y)),
            (int(contexto.tip_x), int(contexto.tip_y)),
            max(1, int(2 * self.cam.zoom)),
        )
        if contexto.familia != "haste":
            return

        head_x = contexto.tip_x + math.cos(contexto.rad) * contexto.raio * 0.10
        head_y = contexto.tip_y + math.sin(contexto.rad) * contexto.raio * 0.10
        wing = contexto.raio * 0.12
        cor_asa = self._misturar_cor(contexto.cor, (255, 255, 255), 0.22)
        pygame.draw.line(
            self.tela,
            cor_asa,
            (int(contexto.tip_x - contexto.perp_x * wing), int(contexto.tip_y - contexto.perp_y * wing)),
            (int(head_x), int(head_y)),
            max(1, int(2 * self.cam.zoom)),
        )
        pygame.draw.line(
            self.tela,
            cor_asa,
            (int(contexto.tip_x + contexto.perp_x * wing), int(contexto.tip_y + contexto.perp_y * wing)),
            (int(head_x), int(head_y)),
            max(1, int(2 * self.cam.zoom)),
        )

    def _desenhar_presenca_dupla(self, contexto):
        branch = contexto.raio * 0.13
        branch_len = contexto.raio * 0.42
        cor_linha = self._misturar_cor(contexto.cor, (255, 255, 255), 0.35)
        for side in (-1, 1):
            sx = contexto.tip_x - math.cos(contexto.rad) * branch_len + contexto.perp_x * branch * side
            sy = contexto.tip_y - math.sin(contexto.rad) * branch_len + contexto.perp_y * branch * side
            ex = contexto.tip_x + contexto.perp_x * branch * side
            ey = contexto.tip_y + contexto.perp_y * branch * side
            pygame.draw.line(self.tela, cor_linha, (int(sx), int(sy)), (int(ex), int(ey)), max(1, int(2 * self.cam.zoom)))

    def _desenhar_presenca_corrente(self, contexto):
        for i in range(3):
            orbit = contexto.tempo_ticks / 220.0 + i * 2.0
            ex = contexto.tip_x + math.cos(orbit) * contexto.raio * 0.18
            ey = contexto.tip_y + math.sin(orbit) * contexto.raio * 0.18
            pygame.draw.circle(self.tela, contexto.cor, (int(ex), int(ey)), max(1, int(contexto.raio * 0.08)))

    def _desenhar_presenca_arremesso(self, contexto):
        tail_x = contexto.tip_x - math.cos(contexto.rad) * contexto.raio * 0.48
        tail_y = contexto.tip_y - math.sin(contexto.rad) * contexto.raio * 0.48
        cor_linha = self._misturar_cor(contexto.cor, (255, 255, 255), 0.30)
        pygame.draw.line(
            self.tela,
            cor_linha,
            (int(tail_x), int(tail_y)),
            (int(contexto.tip_x), int(contexto.tip_y)),
            max(1, int(2 * self.cam.zoom)),
        )
        if contexto.familia != "disparo":
            return

        ring_r = max(3, int(contexto.raio * 0.10))
        cor_anel = self._misturar_cor(contexto.cor, (255, 255, 255), 0.25)
        cor_eixo = self._misturar_cor(contexto.cor, (255, 255, 255), 0.18)
        pygame.draw.circle(self.tela, cor_anel, (int(contexto.tip_x), int(contexto.tip_y)), ring_r, 1)
        pygame.draw.line(
            self.tela,
            cor_eixo,
            (int(contexto.tip_x - contexto.perp_x * ring_r * 1.5), int(contexto.tip_y - contexto.perp_y * ring_r * 1.5)),
            (int(contexto.tip_x + contexto.perp_x * ring_r * 1.5), int(contexto.tip_y + contexto.perp_y * ring_r * 1.5)),
            1,
        )

    def _desenhar_presenca_magica(self, contexto):
        paleta = contexto.paleta or self._paleta_magica(getattr(contexto.arma, "afinidade_elemento", None), contexto.cor)
        self._desenhar_sigilo_magico(contexto.tip_x, contexto.tip_y, int(contexto.raio * 0.28), paleta, contexto.tempo_ticks / 1000.0, 0.65)
        if contexto.familia == "orbital":
            for i in range(3):
                orbit = contexto.tempo_ticks / 280.0 + i * (math.pi * 2.0 / 3.0)
                ex = contexto.tip_x + math.cos(orbit) * contexto.raio * 0.16
                ey = contexto.tip_y + math.sin(orbit) * contexto.raio * 0.16
                pygame.draw.circle(self.tela, paleta["mid"][0], (int(ex), int(ey)), max(1, int(contexto.raio * 0.05)))
            return
        if contexto.familia == "foco":
            rune_r = contexto.raio * 0.14
            for i in range(4):
                orbit = contexto.tempo_ticks / 420.0 + i * (math.pi / 2.0)
                ex = contexto.tip_x + math.cos(orbit) * rune_r
                ey = contexto.tip_y + math.sin(orbit) * rune_r
                pygame.draw.line(
                    self.tela,
                    paleta["spark"],
                    (int(ex - contexto.perp_x * 3), int(ey - contexto.perp_y * 3)),
                    (int(ex + contexto.perp_x * 3), int(ey + contexto.perp_y * 3)),
                    1,
                )

    def _desenhar_presenca_hibrida(self, contexto):
        split = contexto.raio * 0.12
        cor_linha = self._misturar_cor(contexto.cor, (255, 255, 255), 0.28)
        for side in (-1, 1):
            sx = contexto.tip_x - math.cos(contexto.rad) * contexto.raio * 0.38
            sy = contexto.tip_y - math.sin(contexto.rad) * contexto.raio * 0.38
            ex = contexto.tip_x + contexto.perp_x * split * side
            ey = contexto.tip_y + contexto.perp_y * split * side
            pygame.draw.line(self.tela, cor_linha, (int(sx), int(sy)), (int(ex), int(ey)), max(1, int(2 * self.cam.zoom)))

    def _desenhar_forma_presenca_arma(self, contexto):
        if contexto.familia in {"lamina", "haste"} or contexto.tipo == "reta":
            self._desenhar_presenca_lamina_haste(contexto)
            return
        if contexto.familia == "dupla" or contexto.tipo == "dupla":
            self._desenhar_presenca_dupla(contexto)
            return
        if contexto.familia == "corrente" or contexto.tipo == "corrente":
            self._desenhar_presenca_corrente(contexto)
            return
        if contexto.familia in {"arremesso", "disparo"} or contexto.tipo in {"arremesso", "arco"}:
            self._desenhar_presenca_arremesso(contexto)
            return
        if contexto.familia in {"foco", "orbital"} or contexto.tipo in {"magica", "orbital"}:
            self._desenhar_presenca_magica(contexto)
            return
        if contexto.familia == "hibrida" or contexto.tipo == "transformavel":
            self._desenhar_presenca_hibrida(contexto)

    def _desenhar_ornamento_presenca_arma(self, contexto):
        if contexto.ornamento == "elo":
            for idx in range(3):
                ex = contexto.tip_x - math.cos(contexto.rad) * contexto.raio * (0.10 + idx * 0.10)
                ey = contexto.tip_y - math.sin(contexto.rad) * contexto.raio * (0.10 + idx * 0.10)
                pygame.draw.circle(
                    self.tela,
                    self._misturar_cor(contexto.cor, (255, 255, 255), 0.25),
                    (int(ex), int(ey)),
                    max(1, int(contexto.raio * 0.06)),
                    1,
                )
            return
        if contexto.ornamento in {"anel_runico", "sigilo_orbital"}:
            paleta = contexto.paleta or self._paleta_magica(getattr(contexto.arma, "afinidade_elemento", None), contexto.cor)
            self._desenhar_sigilo_magico(contexto.tip_x, contexto.tip_y, int(contexto.raio * 0.20), paleta, contexto.tempo_ticks / 1200.0, 0.45 + contexto.brilho * 0.3)

    def _desenhar_presenca_arma(self, lutador, centro, raio, anim_scale):
        contexto = self._criar_contexto_presenca_arma(lutador, centro, raio, anim_scale)
        if contexto is None:
            return
        self._desenhar_aura_presenca_arma(contexto)
        self._desenhar_forma_presenca_arma(contexto)
        self._desenhar_ornamento_presenca_arma(contexto)

    def _desenhar_sparks_arma(self, lutador, centro, raio):
        arma = lutador.dados.arma_obj
        if not arma:
            return
        from efeitos.weapon_animations import get_weapon_animation_manager
        tipo = getattr(arma, "tipo", "Reta")
        dist = raio * {
            "Reta": 1.8,
            "Dupla": 1.3,
            "Corrente": 2.0,
            "Magica": 1.6,
            "Mágica": 1.6,
            "Orbital": 1.7,
            "Transformavel": 1.9,
            "Transformável": 1.9,
        }.get(tipo, 1.5)
        rad = math.radians(lutador.angulo_arma_visual)
        tip_pos = (centro[0] + math.cos(rad) * dist, centro[1] + math.sin(rad) * dist)
        get_weapon_animation_manager().draw_sparks(self.tela, id(lutador), tip_pos)

    def _criar_contexto_render_frame(self):
        # C03: mistura COR_FUNDO com cor_ambiente da arena para luz ambiente perceptÃ­vel
        fundo = COR_FUNDO
        if self.arena and hasattr(self.arena, 'config'):
            ca = self.arena.config.cor_ambiente  # e.g. (10, 30, 10)
            if ca and any(c > 0 for c in ca):
                fundo = (
                    min(255, COR_FUNDO[0] + ca[0]),
                    min(255, COR_FUNDO[1] + ca[1]),
                    min(255, COR_FUNDO[2] + ca[2]),
                )
        lutadores = list(getattr(self, 'fighters', ()))
        lutadores.sort(key=lambda p: 0 if getattr(p, 'morto', False) else 1)
        return RenderFrameContext(
            fundo=fundo,
            pulse_time=pygame.time.get_ticks() / 1000.0,
            lutadores_ordenados=lutadores,
        )

    def _desenhar_fundo_frame(self, contexto):
        self.tela.fill(contexto.fundo)

        # === DESENHA ARENA v9.0 (ANTES DE TUDO) ===
        if self.arena:
            self.arena.desenhar(self.tela, self.cam)
        else:
            # Fallback: grid antigo se nÃ£o houver arena
            self.desenhar_grid()

        for d in getattr(self, 'decals', ()):
            d.draw(self.tela, self.cam)

    def _desenhar_camadas_magicas_frame(self, contexto):
        # === DESENHA ÃREAS COM EFEITOS DRAMÃTICOS v11.0 ===
        for area in getattr(self, 'areas', ()):
            if area.ativo:
                self._desenhar_area_magica(area, contexto.pulse_time)

        # === DESENHA BEAMS COM EFEITOS DRAMÃTICOS v11.0 ===
        for beam in getattr(self, 'beams', ()):
            if beam.ativo:
                self._desenhar_beam_magico(beam, contexto.pulse_time)

    def _desenhar_particulas_frame(self, contexto):
        for p in getattr(self, 'particulas', ()):
            sx, sy = self.cam.converter(p.x, p.y); tam = self.cam.converter_tam(p.tamanho)
            # v15.0: PartÃ­culas com glow melhorado
            life_alpha = max(0, min(255, int(255 * max(0, p.vida))))
            if tam > 3:
                surf_size = int(tam * 3) + 6
                s = self._get_surface(surf_size, surf_size, pygame.SRCALPHA)
                c = surf_size // 2
                # Glow externo suave
                glow_a = max(0, min(255, life_alpha // 4))
                pygame.draw.circle(s, (*p.cor[:3], glow_a), (c, c), min(c - 1, int(tam * 1.5)))
                # Core colorido
                core_a = max(0, min(255, life_alpha))
                pygame.draw.circle(s, (*p.cor[:3], core_a), (c, c), max(1, int(tam * 0.7)))
                # Hotspot branco
                hot_a = max(0, min(255, int(life_alpha * 0.6)))
                pygame.draw.circle(s, (255, 255, 255, hot_a), (c, c), max(1, int(tam * 0.3)))
                self.tela.blit(s, (sx - c, sy - c))
            elif tam > 1:
                s = self._get_surface(6, 6, pygame.SRCALPHA)
                pygame.draw.circle(s, (*p.cor[:3], life_alpha), (3, 3), max(1, int(tam)))
                self.tela.blit(s, (sx - 3, sy - 3))
            else:
                pygame.draw.rect(self.tela, p.cor, (sx, sy, max(1, int(tam)), max(1, int(tam))))

    def _desenhar_invocacoes_traps_frame(self, contexto):
        # === DESENHA SUMMONS (Invocacoes) ===
        for summon in getattr(self, 'summons', ()):
            if summon.ativo:
                self._desenhar_summon_magico(summon, contexto.pulse_time)

        # === DESENHA TRAPS (Armadilhas) ===
        for trap in getattr(self, 'traps', ()):
            if trap.ativo:
                self._desenhar_trap_magica(trap, contexto.pulse_time)

        # === DESENHA MARCAS NO CHÃƒÆ’O (CRATERAS, RACHADURAS) - v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_ground(self.tela, self.cam)

    def _desenhar_lutadores_frame(self, contexto):
        for lutador in contexto.lutadores_ordenados:
            self.desenhar_lutador(lutador)

    def _desenhar_trail_legado_projetil(self, proj):
        trail = getattr(proj, "trail", None)
        if not trail or len(trail) <= 1:
            return
        if any(w in str(getattr(proj, "nome", "")).lower() for w in ["fogo", "gelo", "raio", "trevas", "luz", "arcano", "sangue", "veneno", "void"]):
            return

        cor_trail = proj.cor if hasattr(proj, "cor") else BRANCO
        for i in range(1, len(trail)):
            t = i / len(trail)
            alpha = int(255 * t * 0.7)
            largura = max(1, int(proj.raio * PPM * self.cam.zoom * t))
            p1 = self.cam.converter(trail[i - 1][0] * PPM, trail[i - 1][1] * PPM)
            p2 = self.cam.converter(trail[i][0] * PPM, trail[i][1] * PPM)
            if largura <= 2:
                pygame.draw.line(self.tela, cor_trail, p1, p2, largura)
                continue
            s = self._get_surface(abs(int(p2[0] - p1[0])) + largura * 4, abs(int(p2[1] - p1[1])) + largura * 4, pygame.SRCALPHA)
            offset_x = min(p1[0], p2[0]) - largura * 2
            offset_y = min(p1[1], p2[1]) - largura * 2
            local_p1 = (p1[0] - offset_x, p1[1] - offset_y)
            local_p2 = (p2[0] - offset_x, p2[1] - offset_y)
            pygame.draw.line(s, (*cor_trail[:3], alpha // 2), local_p1, local_p2, largura * 2)
            pygame.draw.line(s, (*cor_trail[:3], alpha), local_p1, local_p2, largura)
            self.tela.blit(s, (offset_x, offset_y))

    def _criar_contexto_projetil_frame(self, proj, pulse_time):
        px, py = self.cam.converter(proj.x * PPM, proj.y * PPM)
        pr = self.cam.converter_tam(proj.raio * PPM)
        cor = proj.cor if hasattr(proj, "cor") else BRANCO
        ang_visual = getattr(proj, "angulo_visual", proj.angulo) if hasattr(proj, "angulo") else 0
        return ProjectileFrameRenderContext(
            proj=proj,
            pulse_time=pulse_time,
            px=px,
            py=py,
            pr=pr,
            cor=cor,
            tipo_proj=getattr(proj, "tipo", "skill"),
            ang_visual=ang_visual,
            rad=math.radians(ang_visual),
        )

    def _desenhar_glow_projetil_frame(self, contexto):
        glow_pulse = 0.8 + 0.4 * math.sin(contexto.pulse_time * 10 + id(contexto.proj) % 100)
        glow_r = int(contexto.pr * 2 * glow_pulse)
        if glow_r <= 3:
            return
        s = self._get_surface(glow_r * 2 + 4, glow_r * 2 + 4, pygame.SRCALPHA)
        pygame.draw.circle(s, (*contexto.cor[:3], 60), (glow_r + 2, glow_r + 2), glow_r)
        self.tela.blit(s, (contexto.px - glow_r - 2, contexto.py - glow_r - 2))

    def _desenhar_projetil_faca_frame(self, contexto):
        tam = max(contexto.pr * 2, 8)
        pts = [
            (contexto.px + math.cos(contexto.rad) * tam, contexto.py + math.sin(contexto.rad) * tam),
            (contexto.px + math.cos(contexto.rad + 2.5) * tam * 0.4, contexto.py + math.sin(contexto.rad + 2.5) * tam * 0.4),
            (contexto.px - math.cos(contexto.rad) * tam * 0.3, contexto.py - math.sin(contexto.rad) * tam * 0.3),
            (contexto.px + math.cos(contexto.rad - 2.5) * tam * 0.4, contexto.py + math.sin(contexto.rad - 2.5) * tam * 0.4),
        ]
        pygame.draw.polygon(self.tela, contexto.cor, pts)
        pygame.draw.polygon(self.tela, BRANCO, pts, 1)

    def _desenhar_projetil_shuriken_frame(self, contexto):
        tam = max(contexto.pr * 2, 10)
        pts = []
        for i in range(8):
            ang_pt = contexto.rad + i * (math.pi / 4)
            dist = tam if i % 2 == 0 else tam * 0.3
            pts.append((contexto.px + math.cos(ang_pt) * dist, contexto.py + math.sin(ang_pt) * dist))
        pygame.draw.polygon(self.tela, contexto.cor, pts)
        pygame.draw.polygon(self.tela, (50, 50, 50), pts, 1)

    def _desenhar_projetil_chakram_frame(self, contexto):
        tam = max(contexto.pr * 2, 12)
        pygame.draw.circle(self.tela, contexto.cor, (int(contexto.px), int(contexto.py)), int(tam), 3)
        pygame.draw.circle(self.tela, BRANCO, (int(contexto.px), int(contexto.py)), int(tam * 0.5), 2)
        for i in range(6):
            ang_blade = contexto.rad + i * (math.pi / 3)
            bx = contexto.px + math.cos(ang_blade) * tam
            by = contexto.py + math.sin(ang_blade) * tam
            pygame.draw.line(self.tela, contexto.cor, (contexto.px, contexto.py), (int(bx), int(by)), 2)

    def _desenhar_projetil_flecha_frame(self, contexto):
        tam = max(contexto.pr * 3, 15)
        x1 = contexto.px - math.cos(contexto.rad) * tam * 0.7
        y1 = contexto.py - math.sin(contexto.rad) * tam * 0.7
        x2 = contexto.px + math.cos(contexto.rad) * tam * 0.3
        y2 = contexto.py + math.sin(contexto.rad) * tam * 0.3
        pygame.draw.line(self.tela, (139, 90, 43), (int(x1), int(y1)), (int(x2), int(y2)), 2)
        pts = [
            (contexto.px + math.cos(contexto.rad) * tam * 0.6, contexto.py + math.sin(contexto.rad) * tam * 0.6),
            (contexto.px + math.cos(contexto.rad + 2.7) * tam * 0.2, contexto.py + math.sin(contexto.rad + 2.7) * tam * 0.2),
            (contexto.px + math.cos(contexto.rad - 2.7) * tam * 0.2, contexto.py + math.sin(contexto.rad - 2.7) * tam * 0.2),
        ]
        pygame.draw.polygon(self.tela, contexto.cor, pts)
        for offset in [-0.3, 0.3]:
            fx = x1 + math.cos(contexto.rad + offset) * tam * 0.15
            fy = y1 + math.sin(contexto.rad + offset) * tam * 0.15
            pygame.draw.line(self.tela, (200, 200, 200), (int(x1), int(y1)), (int(fx), int(fy)), 1)

    def _desenhar_corpo_projetil_frame(self, contexto):
        if contexto.tipo_proj == "faca":
            self._desenhar_projetil_faca_frame(contexto)
            return
        if contexto.tipo_proj == "shuriken":
            self._desenhar_projetil_shuriken_frame(contexto)
            return
        if contexto.tipo_proj == "chakram":
            self._desenhar_projetil_chakram_frame(contexto)
            return
        if contexto.tipo_proj == "flecha":
            self._desenhar_projetil_flecha_frame(contexto)
            return
        self._desenhar_projetil_magico(contexto.proj, contexto.px, contexto.py, contexto.pr, contexto.pulse_time, contexto.ang_visual, contexto.cor)

    def _desenhar_projeteis_frame(self, contexto):
        for proj in getattr(self, 'projeteis', ()):
            self._desenhar_trail_legado_projetil(proj)
            proj_contexto = self._criar_contexto_projetil_frame(proj, contexto.pulse_time)
            self._desenhar_glow_projetil_frame(proj_contexto)
            self._desenhar_corpo_projetil_frame(proj_contexto)

    def _desenhar_orbes_frame(self, contexto):
        # === DESENHA ORBES MÃGICOS ===
        for p in getattr(self, 'fighters', ()):
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if not orbe.ativo:
                        continue
                    self._desenhar_orbe_magico(orbe)

    def _desenhar_efeitos_frame(self, contexto):
        # === EFEITOS v7.0 IMPACT EDITION ===
        for ef in getattr(self, 'dash_trails', ()): ef.draw(self.tela, self.cam)
        for ef in getattr(self, 'hit_sparks', ()): ef.draw(self.tela, self.cam)
        for ef in getattr(self, 'magic_clashes', ()): ef.draw(self.tela, self.cam)
        for ef in getattr(self, 'impact_flashes', ()): ef.draw(self.tela, self.cam)
        for ef in getattr(self, 'block_effects', ()): ef.draw(self.tela, self.cam)

        # === MAGIC VFX v11.0 DRAMATIC EDITION ===
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            self.magic_vfx.draw(self.tela, self.cam)

        # === ANIMAÃƒâ€¡Ãƒâ€¢ES DE MOVIMENTO v8.0 CINEMATIC EDITION ===
        if self.movement_anims:
            self.movement_anims.draw(self.tela, self.cam)

        # === ANIMAÃƒâ€¡Ãƒâ€¢ES DE ATAQUE v8.0 IMPACT EDITION ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_effects(self.tela, self.cam)

        for s in getattr(self, 'shockwaves', ()): s.draw(self.tela, self.cam)
        for t in getattr(self, 'textos', ()): t.draw(self.tela, self.cam)

        # === SCREEN EFFECTS (FLASH) v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_screen_effects(self.tela, self.screen_width, self.screen_height)

        self._desenhar_overlay_cinematico()

        # === DEBUG VISUAL DE HITBOX ===
        if self.show_hitbox_debug:
            self.desenhar_hitbox_debug()

    def _desenhar_interface_frame(self, contexto):
        if self.show_hud:
            if not self.vencedor:
                # v13.0: HUD multi-fighter com barras por time
                if getattr(self, 'modo_multi', False) and len(self.fighters) > 2:
                    self._desenhar_hud_multi()
                else:
                    self.desenhar_barras(self.p1, 20, 20, COR_P1, self.vida_visual_p1)
                    p2_offset = 220 if self.portrait_mode else 320
                    self.desenhar_barras(self.p2, self.screen_width - p2_offset, 20, COR_P2, self.vida_visual_p2)
                # DES-4: Timer de luta no centro do HUD
                tempo_restante = max(0, self.TEMPO_MAX_LUTA - self.tempo_luta)
                cor_timer = (255, 80, 80) if tempo_restante < 15 else (255, 255, 255)
                font_timer = self._get_font("Impact", 28)
                txt_timer = font_timer.render(f"{int(tempo_restante)}", True, cor_timer)
                self.tela.blit(txt_timer, (self.screen_width // 2 - txt_timer.get_width() // 2, 24))
                if getattr(self, "modo_partida", "duelo") == "horda":
                    self._desenhar_overlay_horda()
                if not self.portrait_mode:  # Esconde controles em portrait para mais espaÃ§o
                    self.desenhar_controles()
            else: self.desenhar_vitoria()
            if self.paused: self.desenhar_pause()
        if self.show_analysis: self.desenhar_analise()

    def desenhar(self):
        contexto = self._criar_contexto_render_frame()
        self._desenhar_fundo_frame(contexto)
        self._desenhar_camadas_magicas_frame(contexto)
        self._desenhar_particulas_frame(contexto)
        self._desenhar_invocacoes_traps_frame(contexto)
        self._desenhar_lutadores_frame(contexto)
        self._desenhar_projeteis_frame(contexto)
        self._desenhar_orbes_frame(contexto)
        self._desenhar_efeitos_frame(contexto)
        self._desenhar_interface_frame(contexto)


    def desenhar_grid(self):
        start_x = int((-self.cam.x * self.cam.zoom) % (50 * self.cam.zoom))
        start_y = int((-self.cam.y * self.cam.zoom) % (50 * self.cam.zoom))
        step = int(50 * self.cam.zoom)
        for x in range(start_x, self.screen_width, step): pygame.draw.line(self.tela, COR_GRID, (x, 0), (x, self.screen_height))
        for y in range(start_y, self.screen_height, step): pygame.draw.line(self.tela, COR_GRID, (0, y), (self.screen_width, y))

    def _desenhar_overlay_horda(self):
        manager = getattr(self, "horde_manager", None)
        if manager is None:
            return
        painel = pygame.Surface((250, 78), pygame.SRCALPHA)
        pygame.draw.rect(painel, (7, 16, 24, 210), (0, 0, 250, 78), border_radius=14)
        pygame.draw.rect(painel, (120, 224, 166, 180), (0, 0, 250, 78), 2, border_radius=14)
        wave = max(1, int(manager.current_wave_index + 1))
        total = max(1, len(getattr(manager, "waves", []) or []))
        ativos = len(manager._alive_monsters()) if hasattr(manager, "_alive_monsters") else 0
        titulo = self._get_font("Impact", 24).render(f"HORDA {wave}/{total}", True, (240, 248, 252))
        sub = self._get_font("Arial", 15).render(
            f"Ativos {ativos}  |  Eliminados {int(getattr(manager, 'total_killed', 0) or 0)}",
            True,
            (198, 222, 235),
        )
        painel.blit(titulo, (14, 8))
        painel.blit(sub, (14, 42))
        self.tela.blit(painel, (self.screen_width - 270, 64))


    def _resolver_cor_corpo_lutador(self, lutador):
        cor_original = (
            int(getattr(lutador.dados, "cor_r", 200) or 200),
            int(getattr(lutador.dados, "cor_g", 50) or 50),
            int(getattr(lutador.dados, "cor_b", 50) or 50),
        )
        if getattr(lutador, "flash_timer", 0) <= 0:
            return cor_original

        flash_cor = getattr(lutador, "flash_cor", (255, 255, 255))
        flash_intensity = getattr(lutador, "flash_timer", 0) / 0.25
        return tuple(
            int(max(0, min(255, flash_cor[i] * flash_intensity + cor_original[i] * (1 - flash_intensity))))
            for i in range(3)
        )

    def _resolver_contorno_lutador(self, lutador):
        if getattr(lutador, "stun_timer", 0) > 0:
            return AMARELO_FAISCA, max(2, self.cam.converter_tam(5))
        if getattr(lutador, "atacando", False):
            return (255, 255, 255), max(2, self.cam.converter_tam(4))
        if getattr(lutador, "flash_timer", 0) > 0:
            return (255, 100, 100), max(2, self.cam.converter_tam(4))
        return (50, 50, 50), max(1, self.cam.converter_tam(2))

    def _criar_contexto_lutador(self, lutador):
        px = lutador.pos[0] * PPM
        py = lutador.pos[1] * PPM
        sx, sy = self.cam.converter(px, py)
        off_y = self.cam.converter_tam(lutador.z * PPM)
        raio = self.cam.converter_tam((lutador.dados.tamanho / 2) * PPM)
        centro = (sx, sy - off_y)
        cor_contorno, largura_contorno = self._resolver_contorno_lutador(lutador)
        shake = getattr(lutador, "weapon_anim_shake", (0, 0))
        anim_scale = getattr(lutador, "weapon_anim_scale", 1.0)
        arma = getattr(lutador.dados, "arma_obj", None)
        tipo_arma_norm = _texto_normalizado(getattr(arma, "tipo", "")) if arma else ""
        return FighterRenderContext(
            lutador=lutador,
            arma=arma,
            sx=sx,
            sy=sy,
            off_y=off_y,
            raio=raio,
            centro=centro,
            cor_corpo=self._resolver_cor_corpo_lutador(lutador),
            cor_contorno=cor_contorno,
            largura_contorno=largura_contorno,
            sombra_d=max(1, raio * 2),
            tam_sombra=max(1, int(max(1, raio * 2) * max(0.4, 1.0 - (lutador.z / 4.0)))),
            pulse_time=pygame.time.get_ticks() / 1000.0,
            anim_scale=anim_scale,
            centro_arma=(centro[0] + shake[0], centro[1] + shake[1]),
            tipo_arma_norm=tipo_arma_norm,
            desenha_slash_arc=getattr(lutador, "atacando", False) and tipo_arma_norm in {"reta", "dupla", "corrente", "transformavel"},
        )

    def _desenhar_rastro_lutador(self, contexto):
        rastros = getattr(self, "rastros", {})
        try:
            rastro_lutador = rastros.get(contexto.lutador)
        except TypeError:
            rastro_lutador = rastros.get(id(contexto.lutador))
        if not rastro_lutador or len(rastro_lutador) <= 2 or not contexto.arma:
            return

        pts_rastro = []
        for ponta, cabo in rastro_lutador:
            p_conv = self.cam.converter(ponta[0], ponta[1])
            c_conv = self.cam.converter(cabo[0], cabo[1])
            pts_rastro.append((p_conv[0], p_conv[1] - contexto.off_y))
            pts_rastro.insert(0, (c_conv[0], c_conv[1] - contexto.off_y))
        if len(pts_rastro) <= 2:
            return

        xs = [p[0] for p in pts_rastro]
        ys = [p[1] for p in pts_rastro]
        min_x, max_x = int(min(xs)) - 2, int(max(xs)) + 2
        min_y, max_y = int(min(ys)) - 2, int(max(ys)) + 2
        sw = max(1, max_x - min_x)
        sh = max(1, max_y - min_y)
        if sw >= 2000 or sh >= 2000:
            return

        s = self._get_surface(sw, sh, pygame.SRCALPHA)
        local_pts = [(p[0] - min_x, p[1] - min_y) for p in pts_rastro]
        cor_rastro = (contexto.arma.r, contexto.arma.g, contexto.arma.b, 80)
        pygame.draw.polygon(s, cor_rastro, local_pts)
        self.tela.blit(s, (min_x, min_y))

    def _desenhar_lutador_morto(self, contexto):
        pygame.draw.ellipse(
            self.tela,
            COR_CORPO,
            (contexto.sx - contexto.raio, contexto.sy - contexto.raio, contexto.raio * 2, contexto.raio * 2),
        )
        if not contexto.arma:
            return
        ax = contexto.lutador.arma_droppada_pos[0] * PPM
        ay = contexto.lutador.arma_droppada_pos[1] * PPM
        asx, asy = self.cam.converter(ax, ay)
        self.desenhar_arma(
            contexto.arma,
            (asx, asy),
            contexto.lutador.arma_droppada_ang,
            contexto.lutador.dados.tamanho,
            contexto.raio,
        )

    def _obter_sombra_lutador(self, sombra_d):
        if not hasattr(self, "_shadow_cache"):
            self._shadow_cache = {}
        if sombra_d not in self._shadow_cache:
            ss = self._get_surface(sombra_d, sombra_d, pygame.SRCALPHA)
            pygame.draw.ellipse(ss, (0, 0, 0, 80), (0, 0, sombra_d, sombra_d))
            self._shadow_cache[sombra_d] = ss
        return self._shadow_cache[sombra_d]

    def _desenhar_sombra_lutador(self, contexto):
        if contexto.tam_sombra <= 0:
            return
        sombra = self._obter_sombra_lutador(contexto.sombra_d)
        if contexto.tam_sombra != contexto.sombra_d:
            sombra = pygame.transform.scale(sombra, (contexto.tam_sombra, contexto.tam_sombra))
        self.tela.blit(sombra, (contexto.sx - contexto.tam_sombra // 2, contexto.sy - contexto.tam_sombra // 2))

    def _desenhar_corpo_lutador(self, contexto):
        pygame.draw.circle(self.tela, contexto.cor_corpo, contexto.centro, contexto.raio)
        pygame.draw.circle(self.tela, contexto.cor_contorno, contexto.centro, contexto.raio, contexto.largura_contorno)

    def _desenhar_emocoes_lutador(self, contexto):
        brain = getattr(contexto.lutador, "brain", None)
        if brain is None or getattr(contexto.lutador, "morto", False):
            return

        pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 120)
        raiva_val = getattr(brain, "raiva", 0.0)
        medo_val = getattr(brain, "medo", 0.0)
        excit_val = getattr(brain, "excitacao", 0.0)

        if raiva_val > 0.55:
            ring_alpha = int(min(200, raiva_val * 160 * pulso))
            ring_r = max(1, contexto.raio + self.cam.converter_tam(4))
            ring_w = max(1, self.cam.converter_tam(3))
            s_ring = self._get_surface(ring_r * 2 + ring_w * 2, ring_r * 2 + ring_w * 2, pygame.SRCALPHA)
            pygame.draw.circle(s_ring, (220, 40, 40, ring_alpha), (ring_r + ring_w, ring_r + ring_w), ring_r + ring_w // 2, ring_w)
            self.tela.blit(s_ring, (contexto.centro[0] - ring_r - ring_w, contexto.centro[1] - ring_r - ring_w))
            return

        if medo_val > 0.50:
            tremor = int(2 * medo_val * pulso)
            ring_alpha = int(min(180, medo_val * 140))
            ring_r = max(1, contexto.raio + self.cam.converter_tam(3))
            ring_w = max(1, self.cam.converter_tam(2))
            s_ring = self._get_surface(ring_r * 2 + ring_w * 2 + tremor * 2, ring_r * 2 + ring_w * 2 + tremor * 2, pygame.SRCALPHA)
            pygame.draw.circle(
                s_ring,
                (80, 140, 255, ring_alpha),
                (ring_r + ring_w + tremor, ring_r + ring_w + tremor),
                ring_r + ring_w // 2,
                ring_w,
            )
            self.tela.blit(s_ring, (contexto.centro[0] - ring_r - ring_w - tremor, contexto.centro[1] - ring_r - ring_w - tremor))
            return

        if excit_val > 0.70:
            ring_alpha = int(min(150, excit_val * 120 * pulso))
            ring_r = max(1, contexto.raio + self.cam.converter_tam(2))
            ring_w = max(1, self.cam.converter_tam(2))
            s_ring = self._get_surface(ring_r * 2 + ring_w * 2, ring_r * 2 + ring_w * 2, pygame.SRCALPHA)
            pygame.draw.circle(s_ring, (255, 220, 80, ring_alpha), (ring_r + ring_w, ring_r + ring_w), ring_r + ring_w // 2, ring_w)
            self.tela.blit(s_ring, (contexto.centro[0] - ring_r - ring_w, contexto.centro[1] - ring_r - ring_w))

    def _desenhar_adrenalina_lutador(self, contexto):
        if not getattr(contexto.lutador, "modo_adrenalina", False) or getattr(contexto.lutador, "morto", False):
            return
        pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150)
        glow_size = int(contexto.raio * 1.3)
        s = self._get_surface(glow_size * 2, glow_size * 2, pygame.SRCALPHA)
        glow_alpha = int(60 * pulso)
        pygame.draw.circle(s, (255, 50, 50, glow_alpha), (glow_size, glow_size), glow_size)
        self.tela.blit(s, (contexto.centro[0] - glow_size, contexto.centro[1] - glow_size))

    def _desenhar_efeitos_lutador(self, contexto):
        self._desenhar_buffs_lutador(contexto.lutador, contexto.centro, contexto.raio, contexto.pulse_time)
        self._desenhar_transformacao_lutador(contexto.lutador, contexto.centro, contexto.raio, contexto.pulse_time)

    def _desenhar_arma_lutador(self, contexto):
        if not contexto.arma:
            return
        if contexto.desenha_slash_arc:
            self._desenhar_slash_arc(contexto.lutador, contexto.centro, contexto.raio, contexto.anim_scale)
        self._desenhar_presenca_arma(contexto.lutador, contexto.centro_arma, contexto.raio, contexto.anim_scale)
        self._desenhar_weapon_trail(contexto.lutador)
        self.desenhar_arma(
            contexto.arma,
            contexto.centro_arma,
            contexto.lutador.angulo_arma_visual,
            contexto.lutador.dados.tamanho,
            contexto.raio,
            contexto.anim_scale,
        )
        self._desenhar_sparks_arma(contexto.lutador, contexto.centro_arma, contexto.raio)

    def _desenhar_nome_lutador(self, contexto):
        self._desenhar_nome_tag(contexto.lutador, contexto.centro, contexto.raio)

    def desenhar_lutador(self, l):
        contexto = self._criar_contexto_lutador(l)
        self._desenhar_rastro_lutador(contexto)
        if l.morto:
            self._desenhar_lutador_morto(contexto)
            return
        self._desenhar_sombra_lutador(contexto)
        self._desenhar_corpo_lutador(contexto)
        self._desenhar_emocoes_lutador(contexto)
        self._desenhar_adrenalina_lutador(contexto)
        self._desenhar_efeitos_lutador(contexto)
        self._desenhar_arma_lutador(contexto)
        self._desenhar_nome_lutador(contexto)


    def _desenhar_nome_tag(self, l, centro, raio):
        """Desenha o nome do personagem flutuando acima da cabeÃ§a, estilo Minecraft."""
        nome = l.dados.nome
        hp_pct = l.vida / l.vida_max if l.vida_max > 0 else 0.0

        # PosiÃ§Ã£o: acima do topo do cÃ­rculo (centro jÃ¡ desconta o Z via off_y em desenhar_lutador)
        OFFSET_Y = 14   # pixels acima do topo do cÃ­rculo

        # === FONTE ===
        font = self._get_font("Arial", 13, bold=True)
        texto = font.render(nome, True, (255, 255, 255))
        tw = texto.get_width()
        th = texto.get_height()

        tag_x = centro[0]
        tag_y = centro[1] - raio - OFFSET_Y - th

        # === FUNDO SEMI-TRANSPARENTE (placa preta) ===
        padding_x, padding_y = 6, 3
        bg_w = tw + padding_x * 2
        bg_h = th + padding_y * 2
        bg_x = tag_x - bg_w // 2
        bg_y = tag_y - padding_y

        bg = self._get_surface(bg_w, bg_h, pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.tela.blit(bg, (bg_x, bg_y))

        # === TEXTO DO NOME ===
        self.tela.blit(texto, (tag_x - tw // 2, tag_y))

        # === BARRA DE VIDA MINÃƒÅ¡SCULA ABAIXO DO NOME ===
        bar_w = bg_w
        bar_h = 4
        bar_x = bg_x
        bar_y = bg_y + bg_h + 2

        # Fundo da barra
        pygame.draw.rect(self.tela, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))

        # Cor da barra: verde Ã¢â€ â€™ amarelo Ã¢â€ â€™ vermelho
        if hp_pct > 0.5:
            t = (hp_pct - 0.5) / 0.5
            cor_hp = (int(255 * (1 - t)), 200, 0)
        else:
            t = hp_pct / 0.5
            cor_hp = (220, int(200 * t), 0)

        vida_w = int(bar_w * max(0, hp_pct))
        if vida_w > 0:
            pygame.draw.rect(self.tela, cor_hp, (bar_x, bar_y, vida_w, bar_h))

        # Borda da barra
        pygame.draw.rect(self.tela, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h), 1)


    def _criar_contexto_slash_arc(self, lutador, centro, raio, anim_scale):
        arma = lutador.dados.arma_obj
        if not arma:
            return None

        from efeitos.weapon_animations import WEAPON_PROFILES

        profile = WEAPON_PROFILES.get(arma.tipo, WEAPON_PROFILES["Reta"])
        total_time = profile.total_time
        if total_time <= 0:
            return None

        prog = 1.0 - (lutador.timer_animacao / total_time)
        antecipation_end = profile.anticipation_time / total_time
        attack_end = (profile.anticipation_time + profile.attack_time + profile.impact_time) / total_time
        if prog < antecipation_end or prog > attack_end + 0.15:
            return None

        attack_prog = max(0.0, min(1.0, (prog - antecipation_end) / max(attack_end - antecipation_end, 0.01)))
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, "r") else (255, 255, 255)
        arc_radius = raio * 3.0 * anim_scale
        surf_size = int(arc_radius * 3.5)
        if surf_size < 10:
            return None

        angulo_base = lutador.angulo_olhar
        arc_start = angulo_base + profile.anticipation_angle
        arc_end = angulo_base + profile.attack_angle
        return SlashArcRenderContext(
            lutador=lutador,
            arma=arma,
            centro=centro,
            zoom=getattr(self.cam, "zoom", 1.0),
            cor=cor,
            cor_brilho=tuple(min(255, c + 100) for c in cor),
            cor_glow=tuple(min(255, c + 40) for c in cor),
            arc_start=arc_start,
            current_arc=arc_start + (arc_end - arc_start) * attack_prog,
            arc_radius=arc_radius,
            fade=1.0 - attack_prog,
            alpha_base=int(220 * (1.0 - attack_prog) * (1.0 - attack_prog)),
            arc_width_factor=1.0 - attack_prog * 0.6,
            surf_size=surf_size,
            arc_center=(surf_size // 2, surf_size // 2),
            num_points=20,
        )

    def _coletar_pontos_arco_slash(self, contexto, raio_relativo, *, as_int=False):
        pontos = []
        for i in range(contexto.num_points + 1):
            t = i / contexto.num_points
            angle = math.radians(contexto.arc_start + (contexto.current_arc - contexto.arc_start) * t)
            px = contexto.arc_center[0] + math.cos(angle) * contexto.arc_radius * raio_relativo
            py = contexto.arc_center[1] + math.sin(angle) * contexto.arc_radius * raio_relativo
            pontos.append((int(px), int(py)) if as_int else (px, py))
        return pontos

    def _desenhar_glow_slash_arc(self, contexto, surf):
        outer = self._coletar_pontos_arco_slash(contexto, 1.15)
        inner = self._coletar_pontos_arco_slash(contexto, 0.5)
        if len(outer) > 2:
            glow_polygon = outer + inner[::-1]
            glow_alpha = max(0, min(255, int(contexto.alpha_base * 0.25)))
            pygame.draw.polygon(surf, (*contexto.cor_glow, glow_alpha), glow_polygon)

    def _desenhar_corpo_slash_arc(self, contexto, surf):
        for layer in range(3):
            layer_t = layer / 3.0
            outer = self._coletar_pontos_arco_slash(contexto, 0.95 - layer_t * 0.15)
            inner = self._coletar_pontos_arco_slash(contexto, 0.65 + layer_t * 0.08)
            if len(outer) <= 2:
                continue
            layer_alpha = max(0, min(255, int(contexto.alpha_base * (0.8 - layer_t * 0.3))))
            if layer == 0:
                arc_color = (*contexto.cor_brilho, layer_alpha)
            elif layer == 1:
                arc_color = (*contexto.cor, layer_alpha)
            else:
                arc_color = (*contexto.cor_glow, layer_alpha)
            pygame.draw.polygon(surf, arc_color, outer + inner[::-1])

    def _desenhar_borda_slash_arc(self, contexto, surf):
        edge_points = self._coletar_pontos_arco_slash(contexto, 0.82, as_int=True)
        if len(edge_points) <= 1:
            return
        edge_alpha = max(0, min(255, int(contexto.alpha_base * 0.9)))
        edge_width = max(1, int(5 * contexto.zoom * contexto.arc_width_factor))
        pygame.draw.lines(surf, (*contexto.cor_brilho, edge_alpha), False, edge_points, edge_width)
        core_alpha = max(0, min(255, int(contexto.alpha_base * 0.7)))
        pygame.draw.lines(surf, (255, 255, 255, core_alpha), False, edge_points, max(1, edge_width // 2))

    def _desenhar_ponta_slash_arc(self, contexto, surf):
        last_angle = math.radians(contexto.current_arc)
        tip_x = contexto.arc_center[0] + math.cos(last_angle) * contexto.arc_radius * 0.82
        tip_y = contexto.arc_center[1] + math.sin(last_angle) * contexto.arc_radius * 0.82
        tip_size = max(4, int(10 * contexto.fade))
        tip_alpha = max(0, min(255, int(255 * contexto.fade)))
        pygame.draw.circle(surf, (255, 255, 255, tip_alpha), (int(tip_x), int(tip_y)), tip_size)
        pygame.draw.circle(surf, (*contexto.cor_brilho, max(0, tip_alpha - 50)), (int(tip_x), int(tip_y)), tip_size * 2)

    def _desenhar_slash_arc(self, lutador, centro, raio, anim_scale):
        """Desenha arco de corte visivel durante ataques melee em pipeline explicito."""
        contexto = self._criar_contexto_slash_arc(lutador, centro, raio, anim_scale)
        if contexto is None:
            return
        s = self._get_surface(contexto.surf_size, contexto.surf_size, pygame.SRCALPHA)
        self._desenhar_glow_slash_arc(contexto, s)
        self._desenhar_corpo_slash_arc(contexto, s)
        self._desenhar_borda_slash_arc(contexto, s)
        self._desenhar_ponta_slash_arc(contexto, s)
        self.tela.blit(s, (contexto.centro[0] - contexto.arc_center[0], contexto.centro[1] - contexto.arc_center[1]))

    def _criar_contexto_weapon_trail(self, lutador):
        trail = getattr(lutador, "weapon_trail_positions", [])
        if len(trail) < 2:
            return None

        arma = lutador.dados.arma_obj
        if not arma:
            return None

        from efeitos.weapon_animations import get_animation_profile

        cor = (arma.r, arma.g, arma.b) if hasattr(arma, "r") else (200, 200, 200)
        tipo = arma.tipo
        estilo = getattr(arma, "estilo", "")
        screen_pts = []
        for x, y, alpha in trail:
            p = self.cam.converter(x * PPM, y * PPM)
            screen_pts.append((p[0], p[1], alpha))

        return WeaponTrailRenderContext(
            lutador=lutador,
            arma=arma,
            cor=cor,
            cor_brilho=tuple(min(255, c + 80) for c in cor),
            tipo=tipo,
            tipo_norm=_texto_normalizado(tipo),
            estilo=estilo,
            zoom=getattr(self.cam, "zoom", 1.0),
            screen_pts=screen_pts,
            profile=get_animation_profile(tipo, estilo),
        )

    def _desenhar_trail_avancado_arma(self, contexto):
        from efeitos.weapon_animations import get_weapon_animation_manager

        try:
            get_weapon_animation_manager().trail_renderer.draw_trail(
                self.tela,
                contexto.screen_pts,
                contexto.cor,
                contexto.tipo,
                contexto.profile,
                contexto.estilo,
            )
        except Exception as exc:
            _log.debug("Weapon trail advanced render: %s", exc)

    def _desenhar_segmento_magico_weapon_trail(self, contexto, p1, p2, alpha, t, base_width):
        x1, y1 = p1
        x2, y2 = p2
        glow_width = base_width + max(1, int(4 * contexto.zoom))
        glow_alpha = max(0, min(255, int(100 * alpha * t)))
        surf_w = abs(x2 - x1) + glow_width * 4 + 20
        surf_h = abs(y2 - y1) + glow_width * 4 + 20
        if surf_w <= 2 or surf_h <= 2:
            return
        s = self._get_surface(int(surf_w), int(surf_h), pygame.SRCALPHA)
        ox = min(x1, x2) - glow_width * 2 - 10
        oy = min(y1, y2) - glow_width * 2 - 10
        lp1 = (int(x1 - ox), int(y1 - oy))
        lp2 = (int(x2 - ox), int(y2 - oy))
        pygame.draw.line(s, (*contexto.cor, glow_alpha), lp1, lp2, glow_width)
        pygame.draw.line(s, (*contexto.cor_brilho, min(255, int(glow_alpha * 1.5))), lp1, lp2, base_width)
        pygame.draw.line(s, (255, 255, 255, min(255, int(glow_alpha * 0.8))), lp1, lp2, max(1, base_width // 2))
        self.tela.blit(s, (int(ox), int(oy)))

    def _desenhar_segmento_corte_weapon_trail(self, contexto, p1, p2, alpha, t, base_width):
        x1, y1 = p1
        x2, y2 = p2
        line_alpha = max(0, min(255, int(200 * alpha * t)))
        glow_width = base_width + max(1, int(3 * contexto.zoom))
        surf_w = abs(x2 - x1) + glow_width * 3 + 16
        surf_h = abs(y2 - y1) + glow_width * 3 + 16
        if surf_w <= 2 or surf_h <= 2:
            return
        s = self._get_surface(int(surf_w), int(surf_h), pygame.SRCALPHA)
        ox = min(x1, x2) - glow_width - 8
        oy = min(y1, y2) - glow_width - 8
        lp1 = (int(x1 - ox), int(y1 - oy))
        lp2 = (int(x2 - ox), int(y2 - oy))
        pygame.draw.line(s, (*contexto.cor, max(0, line_alpha // 3)), lp1, lp2, glow_width)
        trail_color = tuple(min(255, int(c * 0.6 + 100 * alpha)) for c in contexto.cor)
        pygame.draw.line(s, (*trail_color, line_alpha), lp1, lp2, base_width)
        if base_width > 3:
            pygame.draw.line(s, (255, 255, 255, max(0, line_alpha // 2)), lp1, lp2, max(1, base_width // 3))
        self.tela.blit(s, (int(ox), int(oy)))

    def _desenhar_segmentos_weapon_trail(self, contexto):
        for i in range(1, len(contexto.screen_pts)):
            x1, y1, a1 = contexto.screen_pts[i - 1]
            x2, y2, a2 = contexto.screen_pts[i]
            alpha = min(a1, a2)
            if alpha < 0.05:
                continue
            t = i / len(contexto.screen_pts)
            base_width = max(1, int(8 * contexto.zoom * t * alpha))
            if contexto.tipo_norm == "magica":
                self._desenhar_segmento_magico_weapon_trail(contexto, (x1, y1), (x2, y2), alpha, t, base_width)
            else:
                self._desenhar_segmento_corte_weapon_trail(contexto, (x1, y1), (x2, y2), alpha, t, base_width)

    def _desenhar_weapon_trail(self, lutador):
        """Desenha trail da arma durante ataques em pipeline explicito."""
        contexto = self._criar_contexto_weapon_trail(lutador)
        if contexto is None:
            return
        self._desenhar_trail_avancado_arma(contexto)
        self._desenhar_segmentos_weapon_trail(contexto)


    def _desenhar_modulo_orbital(self, subtipo_orbital, ox, oy, ang, tam_orbe, cor, cor_clara, cor_escura, cor_raridade, pulso, larg_base):
        if subtipo_orbital == "escudo":
            self._desenhar_glow_circular(ox, oy, tam_orbe * 1.9, cor_raridade, 72 * pulso, layers=3)
            frente = ang
            lateral = ang + math.pi / 2
            ponta = (ox + math.cos(frente) * tam_orbe * 1.35, oy + math.sin(frente) * tam_orbe * 1.35)
            ombro_a = (ox + math.cos(frente) * tam_orbe * 0.18 + math.cos(lateral) * tam_orbe * 0.92,
                       oy + math.sin(frente) * tam_orbe * 0.18 + math.sin(lateral) * tam_orbe * 0.92)
            ombro_b = (ox + math.cos(frente) * tam_orbe * 0.18 - math.cos(lateral) * tam_orbe * 0.92,
                       oy + math.sin(frente) * tam_orbe * 0.18 - math.sin(lateral) * tam_orbe * 0.92)
            base_a = (ox - math.cos(frente) * tam_orbe * 1.05 + math.cos(lateral) * tam_orbe * 0.55,
                      oy - math.sin(frente) * tam_orbe * 1.05 + math.sin(lateral) * tam_orbe * 0.55)
            base_b = (ox - math.cos(frente) * tam_orbe * 1.05 - math.cos(lateral) * tam_orbe * 0.55,
                      oy - math.sin(frente) * tam_orbe * 1.05 - math.sin(lateral) * tam_orbe * 0.55)
            pts = [(int(ponta[0]), int(ponta[1])), (int(ombro_a[0]), int(ombro_a[1])), (int(base_a[0]), int(base_a[1])),
                   (int(base_b[0]), int(base_b[1])), (int(ombro_b[0]), int(ombro_b[1]))]
            pygame.draw.polygon(self.tela, cor_escura, pts)
            pygame.draw.polygon(self.tela, cor, pts, max(2, larg_base // 2))
            pygame.draw.line(self.tela, cor_clara, (int(ponta[0]), int(ponta[1])), (int((base_a[0] + base_b[0]) / 2), int((base_a[1] + base_b[1]) / 2)), 2)
            pygame.draw.circle(self.tela, cor_raridade, (int(ox), int(oy)), max(3, tam_orbe // 4))
            return

        if subtipo_orbital == "drone":
            self._desenhar_glow_circular(ox, oy, tam_orbe * 1.7, cor, 54 * pulso, layers=2)
            pts = self._pontos_poligono_regular(ox, oy, tam_orbe, 6, rotacao=ang * 2.2)
            pygame.draw.polygon(self.tela, cor_escura, [(int(px), int(py)) for px, py in pts])
            pygame.draw.polygon(self.tela, cor, [(int(px), int(py)) for px, py in pts], max(2, larg_base // 2))
            for wing_sign in (-1, 1):
                wing_ang = ang + wing_sign * 1.65
                wx = ox + math.cos(wing_ang) * tam_orbe * 1.55
                wy = oy + math.sin(wing_ang) * tam_orbe * 1.55
                pygame.draw.line(self.tela, cor_clara, (int(ox), int(oy)), (int(wx), int(wy)), max(2, larg_base // 2))
            exhaust_x = ox - math.cos(ang) * tam_orbe * 1.55
            exhaust_y = oy - math.sin(ang) * tam_orbe * 1.55
            self._desenhar_glow_circular(exhaust_x, exhaust_y, tam_orbe * 0.65, (120, 210, 255), 110 * pulso, layers=2)
            pygame.draw.circle(self.tela, cor_raridade, (int(ox), int(oy)), max(3, tam_orbe // 3))
            return

        if subtipo_orbital == "laminas":
            blade_len = tam_orbe * 1.9
            perp_bx = math.cos(ang + math.pi / 2)
            perp_by = math.sin(ang + math.pi / 2)
            tip1x = ox + math.cos(ang) * blade_len
            tip1y = oy + math.sin(ang) * blade_len
            tip2x = ox - math.cos(ang) * blade_len
            tip2y = oy - math.sin(ang) * blade_len
            w = max(2, larg_base - 2)
            blade_pts = [
                (int(tip1x), int(tip1y)),
                (int(ox + perp_bx * w), int(oy + perp_by * w)),
                (int(tip2x), int(tip2y)),
                (int(ox - perp_bx * w), int(oy - perp_by * w)),
            ]
            pygame.draw.polygon(self.tela, cor_escura, blade_pts)
            pygame.draw.polygon(self.tela, cor, blade_pts, 2)
            pygame.draw.line(self.tela, cor_clara, (int(tip1x), int(tip1y)), (int(tip2x), int(tip2y)), 1)
            self._desenhar_glow_circular(ox, oy, tam_orbe * 1.2, cor_raridade, 62 * pulso, layers=2)
            return

        self._desenhar_glow_circular(ox, oy, tam_orbe * 1.8, cor, 70 * pulso, layers=3)
        pygame.draw.circle(self.tela, cor, (int(ox), int(oy)), tam_orbe)
        pygame.draw.circle(self.tela, cor_clara, (int(ox), int(oy)), max(3, tam_orbe // 2))
        pygame.draw.circle(self.tela, cor_raridade, (int(ox), int(oy)), tam_orbe, 2)
        self._desenhar_sigilo_magico(ox, oy, tam_orbe + 5, self._paleta_magica(cor_base=cor), pygame.time.get_ticks() / 1000.0, intensidade=0.45)

    def _criar_contexto_render_arma(self, arma, centro, angulo, tam_char, raio_char, anim_scale=1.0):
        cx, cy = centro
        rad = math.radians(angulo)
        zoom = getattr(self.cam, 'zoom', 1.0)

        cor_r = getattr(arma, 'r', 180) or 180
        cor_g = getattr(arma, 'g', 180) or 180
        cor_b = getattr(arma, 'b', 180) or 180
        cor = (int(cor_r), int(cor_g), int(cor_b))
        cor_clara = tuple(min(255, c + 60) for c in cor)
        cor_escura = tuple(max(0, c - 40) for c in cor)

        raridade_norm = _texto_normalizado(getattr(arma, 'raridade', 'Comum'))
        cor_raridade = {
            'comum': (180, 180, 180),
            'incomum': (30, 255, 30),
            'raro': (30, 144, 255),
            'epico': (148, 0, 211),
            'lendario': (255, 165, 0),
            'mitico': (255, 20, 147),
        }.get(raridade_norm, (180, 180, 180))

        tipo = getattr(arma, 'tipo', 'Reta')
        estilo_arma = getattr(arma, 'estilo', '')
        tipo_norm = _texto_normalizado(tipo)
        estilo_norm = _texto_normalizado(estilo_arma)

        return WeaponRenderContext(
            arma=arma,
            centro=centro,
            cx=cx,
            cy=cy,
            angulo=angulo,
            rad=rad,
            tam_char=tam_char,
            raio_char=raio_char,
            anim_scale=anim_scale,
            zoom=zoom,
            cor=cor,
            cor_clara=cor_clara,
            cor_escura=cor_escura,
            raridade_norm=raridade_norm,
            cor_raridade=cor_raridade,
            tipo=tipo,
            tipo_norm=tipo_norm,
            estilo_arma=estilo_arma,
            estilo_norm=estilo_norm,
            base_scale=raio_char * 0.025,
            larg_base=max(2, int(raio_char * 0.12 * anim_scale)),
            atacando=anim_scale > 1.05,
            tempo=pygame.time.get_ticks(),
        )

    def _desenhar_arma_reta_lanca(self, contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg):
        for i in range(2):
            shade = (90 - i * 20, 55 - i * 15, 22 - i * 8)
            pygame.draw.line(
                self.tela,
                shade,
                (int(contexto.cx), int(contexto.cy)),
                (int(cabo_end_x), int(cabo_end_y)),
                max(2, larg - i * 2),
            )
        tip_w = max(2, larg - 2)
        lance_pts = [
            (int(cabo_end_x - perp_x * tip_w), int(cabo_end_y - perp_y * tip_w)),
            (int(cabo_end_x + perp_x * tip_w), int(cabo_end_y + perp_y * tip_w)),
            (int(lamina_end_x + perp_x), int(lamina_end_y + perp_y)),
            (int(lamina_end_x), int(lamina_end_y)),
            (int(lamina_end_x - perp_x), int(lamina_end_y - perp_y)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, lance_pts)
            pygame.draw.polygon(self.tela, contexto.cor, lance_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.circle(self.tela, (160, 165, 175), (int(cabo_end_x), int(cabo_end_y)), larg // 2 + 1, contexto.zw(2))
        pygame.draw.line(self.tela, contexto.cor_clara, (int(cabo_end_x), int(cabo_end_y)), (int(lamina_end_x), int(lamina_end_y)), 1)

    def _desenhar_arma_reta_maca(self, contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg):
        pygame.draw.line(self.tela, (30, 18, 8), (int(contexto.cx) + 1, int(contexto.cy) + 1), (int(cabo_end_x) + 1, int(cabo_end_y) + 1), larg + 2)
        pygame.draw.line(self.tela, (90, 55, 25), (int(contexto.cx), int(contexto.cy)), (int(cabo_end_x), int(cabo_end_y)), larg)
        head_half = larg * 1.8
        head_pts = [
            (int(cabo_end_x - perp_x * head_half), int(cabo_end_y - perp_y * head_half)),
            (int(cabo_end_x + perp_x * head_half), int(cabo_end_y + perp_y * head_half)),
            (int(lamina_end_x + perp_x * head_half), int(lamina_end_y + perp_y * head_half)),
            (int(lamina_end_x - perp_x * head_half), int(lamina_end_y - perp_y * head_half)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, head_pts)
            pygame.draw.polygon(self.tela, contexto.cor, head_pts, contexto.zw(2))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        mid_x = (cabo_end_x + lamina_end_x) / 2
        mid_y = (cabo_end_y + lamina_end_y) / 2
        for s_sign in [-1, 1]:
            sx1 = int(mid_x + perp_x * head_half * s_sign)
            sy1 = int(mid_y + perp_y * head_half * s_sign)
            sx2 = int(mid_x + perp_x * (head_half + 6) * s_sign)
            sy2 = int(mid_y + perp_y * (head_half + 6) * s_sign)
            pygame.draw.line(self.tela, contexto.cor_clara, (sx1, sy1), (sx2, sy2), max(2, larg // 2))
        pygame.draw.circle(self.tela, contexto.cor_clara, (int(cabo_end_x), int(cabo_end_y)), max(2, larg // 3))
        if contexto.raridade_norm not in ['comum', 'incomum']:
            pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 200)
            pygame.draw.circle(self.tela, contexto.cor_raridade, (int(lamina_end_x), int(lamina_end_y)), max(3, int(larg * 0.8 * (1 + pulso * 0.3))))

    def _desenhar_arma_reta_padrao(self, contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg, lamina_len):
        guarda_x = cabo_end_x + math.cos(contexto.rad) * 2
        guarda_y = cabo_end_y + math.sin(contexto.rad) * 2
        pygame.draw.ellipse(self.tela, (80, 60, 40), (int(guarda_x - larg * 1.5), int(guarda_y - larg * 0.8), larg * 3, larg * 1.6))
        for i in range(3):
            shade = (90 - i * 15, 50 - i * 10, 20 - i * 5)
            pygame.draw.line(self.tela, shade, (int(contexto.cx) + i - 1, int(contexto.cy) + i - 1), (int(cabo_end_x) + i - 1, int(cabo_end_y) + i - 1), max(2, larg - i))
        lamina_pts = [
            (int(cabo_end_x - perp_x * larg * 0.6), int(cabo_end_y - perp_y * larg * 0.6)),
            (int(cabo_end_x + perp_x * larg * 0.6), int(cabo_end_y + perp_y * larg * 0.6)),
            (int(lamina_end_x - perp_x * larg * 0.3), int(lamina_end_y - perp_y * larg * 0.3)),
            (int(lamina_end_x), int(lamina_end_y)),
            (int(lamina_end_x + perp_x * larg * 0.3), int(lamina_end_y + perp_y * larg * 0.3)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor, lamina_pts)
            pygame.draw.polygon(self.tela, contexto.cor_escura, lamina_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        mid_x = (cabo_end_x + lamina_end_x) / 2
        mid_y = (cabo_end_y + lamina_end_y) / 2
        pygame.draw.line(self.tela, contexto.cor_clara, (int(cabo_end_x), int(cabo_end_y)), (int(mid_x), int(mid_y)), max(1, larg // 3))
        if contexto.raridade_norm not in ['comum', 'incomum']:
            pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 200)
            pygame.draw.circle(self.tela, contexto.cor_raridade, (int(lamina_end_x), int(lamina_end_y)), max(3, int(larg * 0.8 * (1 + pulso * 0.3))))
        if contexto.atacando:
            try:
                gl = self._get_surface(int(lamina_len * 2), int(lamina_len * 2), pygame.SRCALPHA)
                for r2 in range(3, 0, -1):
                    pygame.draw.line(
                        gl,
                        (*contexto.cor_clara, 50 // r2),
                        (int(lamina_len), int(lamina_len)),
                        (int(lamina_len + math.cos(contexto.rad) * lamina_len * 0.8), int(lamina_len + math.sin(contexto.rad) * lamina_len * 0.8)),
                        larg + r2 * 2,
                    )
                self.tela.blit(gl, (int(cabo_end_x - lamina_len), int(cabo_end_y - lamina_len)))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_arma_reta(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        estilo_norm = contexto.estilo_norm

        if 'lanca' in estilo_norm or 'estocada' in estilo_norm:
            cabo_len = raio_char * 1.00
            lamina_len = raio_char * 1.80 * anim_scale
        elif 'maca' in estilo_norm or 'contusao' in estilo_norm:
            cabo_len = raio_char * 0.90
            lamina_len = raio_char * 0.70 * anim_scale
        else:
            cabo_len = raio_char * 0.55
            lamina_len = raio_char * 1.30 * anim_scale
        larg = max(contexto.zw(3), int(contexto.larg_base * 1.2))

        cabo_end_x = cx + math.cos(rad) * cabo_len
        cabo_end_y = cy + math.sin(rad) * cabo_len
        lamina_end_x = cx + math.cos(rad) * (cabo_len + lamina_len)
        lamina_end_y = cy + math.sin(rad) * (cabo_len + lamina_len)

        perp_x = math.cos(rad + math.pi / 2)
        perp_y = math.sin(rad + math.pi / 2)

        if "lanca" in estilo_norm or "estocada" in estilo_norm:
            self._desenhar_arma_reta_lanca(contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg)
            return

        if "maca" in estilo_norm or "contusao" in estilo_norm:
            self._desenhar_arma_reta_maca(contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg)
            return

        self._desenhar_arma_reta_padrao(contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg, lamina_len)

    def _desenhar_arma_arremesso_machado(self, contexto, px, py, tam_proj, rot):
        cabo_ax = px + math.cos(rot) * tam_proj * 0.5
        cabo_ay = py + math.sin(rot) * tam_proj * 0.5
        pygame.draw.line(self.tela, (60, 35, 12), (int(px), int(py)), (int(cabo_ax), int(cabo_ay)), max(2, contexto.larg_base - 1))
        perp_ax = math.cos(rot + math.pi / 2)
        perp_ay = math.sin(rot + math.pi / 2)
        ax_pts = [
            (int(cabo_ax - perp_ax * tam_proj * 0.9), int(cabo_ay - perp_ay * tam_proj * 0.9)),
            (int(cabo_ax + perp_ax * tam_proj * 0.3), int(cabo_ay + perp_ay * tam_proj * 0.3)),
            (int(cabo_ax + math.cos(rot) * tam_proj * 0.8 + perp_ax * tam_proj * 0.25), int(cabo_ay + math.sin(rot) * tam_proj * 0.8 + perp_ay * tam_proj * 0.25)),
            (int(cabo_ax + math.cos(rot) * tam_proj * 0.9), int(cabo_ay + math.sin(rot) * tam_proj * 0.9)),
            (int(cabo_ax + math.cos(rot) * tam_proj * 0.8 - perp_ax * tam_proj * 0.9), int(cabo_ay + math.sin(rot) * tam_proj * 0.8 - perp_ay * tam_proj * 0.9)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, ax_pts)
            pygame.draw.polygon(self.tela, contexto.cor, ax_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(cabo_ax + math.cos(rot) * tam_proj * 0.9), int(cabo_ay + math.sin(rot) * tam_proj * 0.9)), max(2, contexto.larg_base - 2))

    def _desenhar_arma_arremesso_chakram(self, contexto, px, py, tam_proj, rot, pulso):
        r2 = max(7, tam_proj - 1)
        pygame.draw.circle(self.tela, contexto.cor_escura, (int(px), int(py)), r2 + 1)
        pygame.draw.circle(self.tela, contexto.cor, (int(px), int(py)), r2, max(3, contexto.larg_base - 1))
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(px), int(py)), r2, contexto.zw(1))
        for rj in range(3):
            ra = rot + rj * math.pi / 3 * 2
            pygame.draw.line(self.tela, contexto.cor_clara, (int(px + math.cos(ra) * r2 * 0.5), int(py + math.sin(ra) * r2 * 0.5)), (int(px - math.cos(ra) * r2 * 0.5), int(py - math.sin(ra) * r2 * 0.5)), 1)
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(px), int(py)), max(2, r2 // 3))
        if contexto.atacando:
            try:
                gs = self._get_surface(r2 * 4, r2 * 4, pygame.SRCALPHA)
                pygame.draw.circle(gs, (*contexto.cor, int(80 * pulso)), (r2 * 2, r2 * 2), r2 * 2)
                self.tela.blit(gs, (int(px) - r2 * 2, int(py) - r2 * 2))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_arma_arremesso_bumerangue(self, contexto, px, py, tam_proj, rot):
        t2 = tam_proj
        bum_pts = [
            (int(px + math.cos(rot) * t2 * 1.1), int(py + math.sin(rot) * t2 * 1.1)),
            (int(px + math.cos(rot + 2.3) * t2 * 0.5), int(py + math.sin(rot + 2.3) * t2 * 0.5)),
            (int(px), int(py)),
            (int(px + math.cos(rot - 2.3) * t2 * 0.5), int(py + math.sin(rot - 2.3) * t2 * 0.5)),
            (int(px + math.cos(rot + math.pi) * t2 * 0.9), int(py + math.sin(rot + math.pi) * t2 * 0.9)),
            (int(px + math.cos(rot + math.pi + 0.5) * t2 * 0.4), int(py + math.sin(rot + math.pi + 0.5) * t2 * 0.4)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, bum_pts)
            pygame.draw.polygon(self.tela, contexto.cor, bum_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(px), int(py)), max(2, contexto.larg_base - 2))

    def _desenhar_arma_arremesso_padrao(self, contexto, px, py, tam_proj, rot):
        blade = tam_proj * 1.2
        perp_f = math.cos(rot + math.pi / 2) * max(2, contexto.larg_base // 2)
        perp_fy = math.sin(rot + math.pi / 2) * max(2, contexto.larg_base // 2)
        tip_fx = px + math.cos(rot) * blade
        tip_fy = py + math.sin(rot) * blade
        faca_pts = [
            (int(px - perp_f), int(py - perp_fy)),
            (int(px + perp_f), int(py + perp_fy)),
            (int(tip_fx + perp_f * 0.3), int(tip_fy + perp_fy * 0.3)),
            (int(tip_fx), int(tip_fy)),
            (int(tip_fx - perp_f * 0.3), int(tip_fy - perp_fy * 0.3)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, faca_pts)
            pygame.draw.polygon(self.tela, contexto.cor, faca_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.line(self.tela, contexto.cor_clara, (int(px), int(py)), (int(tip_fx), int(tip_fy)), contexto.zw(1))
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(tip_fx), int(tip_fy)), max(2, contexto.larg_base - 2))

    def _desenhar_arma_arremesso(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        raio_char = contexto.raio_char
        estilo_norm = contexto.estilo_norm
        tempo = contexto.tempo

        tam_proj = max(8, int(raio_char * 0.35))
        qtd = min(5, int(getattr(contexto.arma, 'quantidade', 3)))
        pulso = 0.5 + 0.5 * math.sin(tempo / 180)

        for i in range(qtd):
            offset_ang = (i - (qtd - 1) / 2) * 20
            r_proj = rad + math.radians(offset_ang)
            dist = raio_char * 1.15 + tam_proj * 0.6
            px = cx + math.cos(r_proj) * dist
            py = cy + math.sin(r_proj) * dist
            rot = tempo / 90 + i * (math.pi * 2 / max(1, qtd))

            if "machado" in estilo_norm:
                self._desenhar_arma_arremesso_machado(contexto, px, py, tam_proj, rot)
                continue

            if "chakram" in estilo_norm:
                self._desenhar_arma_arremesso_chakram(contexto, px, py, tam_proj, rot, pulso)
                continue

            if "bumerangue" in estilo_norm:
                self._desenhar_arma_arremesso_bumerangue(contexto, px, py, tam_proj, rot)
                continue

            self._desenhar_arma_arremesso_padrao(contexto, px, py, tam_proj, rot)

    def _desenhar_arma_arco_besta(self, contexto, tam_arco, tam_flecha):
        stock_len = tam_arco * 0.6
        stock_ex = contexto.cx + math.cos(contexto.rad) * stock_len
        stock_ey = contexto.cy + math.sin(contexto.rad) * stock_len
        perp_x = math.cos(contexto.rad + math.pi / 2)
        perp_y = math.sin(contexto.rad + math.pi / 2)
        pygame.draw.line(self.tela, (30, 18, 8), (int(contexto.cx) + 1, int(contexto.cy) + 1), (int(stock_ex) + 1, int(stock_ey) + 1), contexto.larg_base + 3)
        pygame.draw.line(self.tela, (90, 55, 25), (int(contexto.cx), int(contexto.cy)), (int(stock_ex), int(stock_ey)), contexto.larg_base + 1)
        pygame.draw.line(self.tela, (130, 85, 40), (int(contexto.cx), int(contexto.cy)), (int(stock_ex), int(stock_ey)), max(1, contexto.larg_base - 1))
        limbo_len = tam_arco * 0.45
        mid_x = contexto.cx + math.cos(contexto.rad) * stock_len * 0.75
        mid_y = contexto.cy + math.sin(contexto.rad) * stock_len * 0.75
        limbo_p1 = (int(mid_x + perp_x * limbo_len), int(mid_y + perp_y * limbo_len))
        limbo_p2 = (int(mid_x - perp_x * limbo_len), int(mid_y - perp_y * limbo_len))
        pygame.draw.line(self.tela, (20, 18, 20), (int(limbo_p1[0]) + 1, int(limbo_p1[1]) + 1), (int(limbo_p2[0]) + 1, int(limbo_p2[1]) + 1), max(3, contexto.larg_base) + 1)
        pygame.draw.line(self.tela, contexto.cor, limbo_p1, limbo_p2, max(3, contexto.larg_base))
        pygame.draw.line(self.tela, contexto.cor_clara, limbo_p1, limbo_p2, contexto.zw(1))
        trilho_x = contexto.cx + math.cos(contexto.rad) * stock_len * 0.95
        trilho_y = contexto.cy + math.sin(contexto.rad) * stock_len * 0.95
        pygame.draw.line(self.tela, (200, 185, 140), limbo_p1, (int(trilho_x), int(trilho_y)), contexto.zw(2))
        pygame.draw.line(self.tela, (200, 185, 140), limbo_p2, (int(trilho_x), int(trilho_y)), contexto.zw(2))
        pygame.draw.line(self.tela, (139, 90, 43), (int(trilho_x), int(trilho_y)), (int(trilho_x + math.cos(contexto.rad) * tam_flecha * 0.6), int(trilho_y + math.sin(contexto.rad) * tam_flecha * 0.6)), max(2, contexto.larg_base // 2))
        tip_bx = int(trilho_x + math.cos(contexto.rad) * tam_flecha * 0.6)
        tip_by = int(trilho_y + math.sin(contexto.rad) * tam_flecha * 0.6)
        pts_tip = [
            (tip_bx, tip_by),
            (int(tip_bx - math.cos(contexto.rad) * 8 + perp_x * 4), int(tip_by - math.sin(contexto.rad) * 8 + perp_y * 4)),
            (int(tip_bx - math.cos(contexto.rad) * 8 - perp_x * 4), int(tip_by - math.sin(contexto.rad) * 8 - perp_y * 4)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_raridade, pts_tip)
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        if "repeticao" in contexto.estilo_norm:
            px2 = int(mid_x + math.cos(contexto.rad) * stock_len * 0.05)
            py2 = int(mid_y + math.sin(contexto.rad) * stock_len * 0.05)
            pygame.draw.rect(self.tela, (55, 30, 10), (px2 - 6, py2 - 18, 12, 16))
            pygame.draw.rect(self.tela, contexto.cor_raridade, (px2 - 6, py2 - 18, 12, 16), contexto.zw(1))
        if contexto.raridade_norm not in ['comum', 'incomum']:
            pygame.draw.circle(self.tela, contexto.cor_raridade, (tip_bx, tip_by), max(3, contexto.larg_base))

    def _desenhar_arma_arco_longo(self, contexto, tam_arco, tam_flecha):
        arco_pts = []
        span = tam_arco * 0.9
        for i in range(15):
            ang = contexto.rad + math.radians(-60 + i * (120 / 14))
            curva = math.sin((i / 14) * math.pi) * span * 0.12
            r2 = span * 0.55 + curva
            arco_pts.append((int(contexto.cx + math.cos(ang) * r2), int(contexto.cy + math.sin(ang) * r2)))
        if len(arco_pts) > 1:
            pygame.draw.lines(self.tela, contexto.cor_escura, False, [(p[0] + 1, p[1] + 1) for p in arco_pts], contexto.larg_base + 2)
            pygame.draw.lines(self.tela, contexto.cor, False, arco_pts, contexto.larg_base + 1)
            pygame.draw.lines(self.tela, contexto.cor_clara, False, arco_pts, contexto.zw(1))
            pygame.draw.line(self.tela, (200, 185, 140), arco_pts[0], arco_pts[-1], contexto.zw(2))
        flecha_end_x = contexto.cx + math.cos(contexto.rad) * tam_flecha
        flecha_end_y = contexto.cy + math.sin(contexto.rad) * tam_flecha
        pygame.draw.line(self.tela, (100, 65, 25), (int(contexto.cx), int(contexto.cy)), (int(flecha_end_x), int(flecha_end_y)), max(2, contexto.larg_base // 2))
        plen = tam_flecha * 0.14
        perp_f = math.pi / 2
        tip_pts = [
            (int(flecha_end_x), int(flecha_end_y)),
            (int(flecha_end_x - math.cos(contexto.rad) * plen + math.cos(contexto.rad + perp_f) * plen * 0.4), int(flecha_end_y - math.sin(contexto.rad) * plen + math.sin(contexto.rad + perp_f) * plen * 0.4)),
            (int(flecha_end_x - math.cos(contexto.rad) * plen - math.cos(contexto.rad + perp_f) * plen * 0.4), int(flecha_end_y - math.sin(contexto.rad) * plen - math.sin(contexto.rad + perp_f) * plen * 0.4)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_raridade, tip_pts)
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        for poff in [-1, 1]:
            pex = contexto.cx + math.cos(contexto.rad) * tam_flecha * 0.12
            pey = contexto.cy + math.sin(contexto.rad) * tam_flecha * 0.12
            pygame.draw.line(self.tela, (200, 50, 50), (int(pex), int(pey)), (int(pex + math.cos(contexto.rad + poff * 0.6) * tam_flecha * 0.12), int(pey + math.sin(contexto.rad + poff * 0.6) * tam_flecha * 0.12)), 2)

    def _desenhar_arma_arco_padrao(self, contexto, tam_arco, tam_flecha):
        arco_pts = []
        for i in range(13):
            ang = contexto.rad + math.radians(-50 + i * (100 / 12))
            curva = math.sin((i / 12) * math.pi) * tam_arco * 0.15
            r2 = tam_arco * 0.5 + curva
            arco_pts.append((int(contexto.cx + math.cos(ang) * r2), int(contexto.cy + math.sin(ang) * r2)))
        if len(arco_pts) > 1:
            pygame.draw.lines(self.tela, contexto.cor, False, arco_pts, max(contexto.zw(3), contexto.larg_base))
            pygame.draw.lines(self.tela, contexto.cor_escura, False, arco_pts, contexto.zw(1))
            pygame.draw.line(self.tela, (200, 180, 140), arco_pts[0], arco_pts[-1], contexto.zw(2))
        flecha_end_x = contexto.cx + math.cos(contexto.rad) * tam_flecha
        flecha_end_y = contexto.cy + math.sin(contexto.rad) * tam_flecha
        pygame.draw.line(self.tela, (139, 90, 43), (int(contexto.cx), int(contexto.cy)), (int(flecha_end_x), int(flecha_end_y)), max(2, contexto.larg_base // 2))
        plen = tam_flecha * 0.15
        perp_f = math.pi / 2
        tip_pts = [
            (int(flecha_end_x), int(flecha_end_y)),
            (int(flecha_end_x - math.cos(contexto.rad) * plen + math.cos(contexto.rad + perp_f) * plen * 0.4), int(flecha_end_y - math.sin(contexto.rad) * plen + math.sin(contexto.rad + perp_f) * plen * 0.4)),
            (int(flecha_end_x - math.cos(contexto.rad) * plen - math.cos(contexto.rad + perp_f) * plen * 0.4), int(flecha_end_y - math.sin(contexto.rad) * plen - math.sin(contexto.rad + perp_f) * plen * 0.4)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_raridade, tip_pts)
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        for poff in [-1, 1]:
            pex = contexto.cx + math.cos(contexto.rad) * tam_flecha * 0.15
            pey = contexto.cy + math.sin(contexto.rad) * tam_flecha * 0.15
            pygame.draw.line(self.tela, (200, 50, 50), (int(pex), int(pey)), (int(pex + math.cos(contexto.rad + poff * 0.5) * tam_flecha * 0.1), int(pey + math.sin(contexto.rad + poff * 0.5) * tam_flecha * 0.1)), 2)

    def _desenhar_arma_arco(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        estilo_norm = contexto.estilo_norm

        tam_arco = raio_char * 1.30
        tam_flecha = raio_char * 1.20 * anim_scale

        if "besta" in estilo_norm:
            self._desenhar_arma_arco_besta(contexto, tam_arco, tam_flecha)
            return

        if "longo" in estilo_norm:
            self._desenhar_arma_arco_longo(contexto, tam_arco, tam_flecha)
            return

        self._desenhar_arma_arco_padrao(contexto, tam_arco, tam_flecha)

    def _desenhar_arma_orbital(self, contexto):
        subtipo_orbital = resolver_subtipo_orbital(contexto.arma)
        dist_por_subtipo = {"escudo": 1.28, "drone": 1.88, "laminas": 1.46, "orbes": 1.64}
        dist_orbit = contexto.raio_char * dist_por_subtipo.get(subtipo_orbital, 1.6)
        qtd = max(1, min(5, int(getattr(contexto.arma, 'quantidade_orbitais', 2))))
        tam_orbe = max(9, int(contexto.raio_char * (0.36 if subtipo_orbital == "escudo" else 0.28 if subtipo_orbital == "drone" else 0.30)))
        rot_speed = contexto.tempo / (1150 if subtipo_orbital == "escudo" else 760 if subtipo_orbital == "drone" else 540 if subtipo_orbital == "laminas" else 820)
        pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 200)
        for i in range(qtd):
            ang = rot_speed + (2 * math.pi / qtd) * i
            ox = contexto.cx + math.cos(ang) * dist_orbit
            oy = contexto.cy + math.sin(ang) * dist_orbit
            pygame.draw.line(self.tela, (62, 70, 92), (int(contexto.cx), int(contexto.cy)), (int(ox), int(oy)), contexto.zw(1))
            self._desenhar_modulo_orbital(
                subtipo_orbital,
                ox,
                oy,
                ang,
                tam_orbe,
                contexto.cor,
                contexto.cor_clara,
                contexto.cor_escura,
                contexto.cor_raridade,
                pulso,
                contexto.larg_base,
            )

    def _desenhar_arma_magica_espada(self, contexto, px, py, tam_base, r_m):
        sword_ex = px + math.cos(r_m) * tam_base
        sword_ey = py + math.sin(r_m) * tam_base
        perp_mx = math.cos(r_m + math.pi / 2) * max(2, contexto.larg_base // 2)
        perp_my = math.sin(r_m + math.pi / 2) * max(2, contexto.larg_base // 2)
        blade_pts = [
            (int(px - perp_mx), int(py - perp_my)),
            (int(px + perp_mx), int(py + perp_my)),
            (int(sword_ex + perp_mx * 0.3), int(sword_ey + perp_my * 0.3)),
            (int(sword_ex), int(sword_ey)),
            (int(sword_ex - perp_mx * 0.3), int(sword_ey - perp_my * 0.3)),
        ]
        try:
            gs = self._get_surface(int(tam_base * 4), int(tam_base * 4), pygame.SRCALPHA)
            local_pts = [(p[0] - int(px) + int(tam_base * 2), p[1] - int(py) + int(tam_base * 2)) for p in blade_pts]
            pygame.draw.polygon(gs, (*contexto.cor, 160), local_pts)
            self.tela.blit(gs, (int(px) - int(tam_base * 2), int(py) - int(tam_base * 2)))
            pygame.draw.polygon(self.tela, contexto.cor, blade_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.line(self.tela, contexto.cor_clara, (int(px), int(py)), (int(sword_ex), int(sword_ey)), contexto.zw(1))
        pygame.draw.line(
            self.tela,
            contexto.cor_raridade,
            (int(px - perp_mx * 2.5), int(py - perp_my * 2.5)),
            (int(px + perp_mx * 2.5), int(py + perp_my * 2.5)),
            max(2, contexto.larg_base - 1),
        )
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(sword_ex), int(sword_ey)), 3)

    def _desenhar_arma_magica_runa(self, contexto, px, py, tam_base, rot_off, pulso, i, qtd):
        r2 = max(8, int(tam_base * 0.65))
        pygame.draw.circle(self.tela, contexto.cor_escura, (int(px), int(py)), r2 + 2)
        pygame.draw.circle(self.tela, contexto.cor, (int(px), int(py)), r2, max(2, contexto.larg_base - 1))
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(px), int(py)), r2, contexto.zw(1))
        ang_r = rot_off + i * math.pi / qtd
        for ra in [ang_r, ang_r + math.pi / 4, ang_r + math.pi / 2, ang_r + 3 * math.pi / 4]:
            pygame.draw.line(
                self.tela,
                contexto.cor_clara,
                (int(px + math.cos(ra) * (r2 - 3)), int(py + math.sin(ra) * (r2 - 3))),
                (int(px - math.cos(ra) * (r2 - 3)), int(py - math.sin(ra) * (r2 - 3))),
                1,
            )
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(px), int(py)), max(2, r2 // 3))
        if contexto.raridade_norm != 'comum':
            try:
                gs = self._get_surface(r2 * 4, r2 * 4, pygame.SRCALPHA)
                pygame.draw.circle(gs, (*contexto.cor_raridade, int(80 * pulso)), (r2 * 2, r2 * 2), r2 * 2)
                self.tela.blit(gs, (int(px) - r2 * 2, int(py) - r2 * 2))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_arma_magica_tentaculo(self, contexto, px, py, tam_base, r_m, i):
        tent_len = tam_base * 2.0
        t_pts = []
        for s in range(9):
            t = s / 8
            wave = math.sin(t * math.pi * 2.5 + contexto.tempo / 100 + i) * tam_base * 0.4 * (1 - t * 0.3)
            tx2 = px + math.cos(r_m) * tent_len * t + math.cos(r_m + math.pi / 2) * wave
            ty2 = py + math.sin(r_m) * tent_len * t + math.sin(r_m + math.pi / 2) * wave
            t_pts.append((int(tx2), int(ty2)))
        if len(t_pts) > 1:
            try: pygame.draw.lines(self.tela, contexto.cor, False, t_pts, max(2, contexto.larg_base - 1))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
            try: pygame.draw.lines(self.tela, contexto.cor_clara, False, t_pts, contexto.zw(1))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        for si in range(1, 4):
            sv = t_pts[si * 2] if si * 2 < len(t_pts) else t_pts[-1]
            pygame.draw.circle(self.tela, contexto.cor_raridade, sv, max(2, contexto.larg_base - 2))

    def _desenhar_arma_magica_padrao(self, contexto, px, py, tam_base, rot_off, i):
        r2 = max(7, int(tam_base * 0.6))
        crystal_pts = [
            (int(px + math.cos(rot_off + i) * r2 * 1.4), int(py + math.sin(rot_off + i) * r2 * 1.4)),
            (int(px + math.cos(rot_off + i + 2.1) * r2), int(py + math.sin(rot_off + i + 2.1) * r2)),
            (int(px + math.cos(rot_off + i + 2.5) * r2 * 0.6), int(py + math.sin(rot_off + i + 2.5) * r2 * 0.6)),
            (int(px + math.cos(rot_off + i + 3.8) * r2), int(py + math.sin(rot_off + i + 3.8) * r2)),
            (int(px + math.cos(rot_off + i - 2.1) * r2), int(py + math.sin(rot_off + i - 2.1) * r2)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, crystal_pts)
            pygame.draw.polygon(self.tela, contexto.cor, crystal_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.circle(self.tela, contexto.cor_clara, (int(px), int(py)), max(2, r2 // 3))
        if contexto.raridade_norm != 'comum':
            pygame.draw.circle(self.tela, contexto.cor_raridade, crystal_pts[0], 3)

    def _desenhar_arma_magica(self, contexto):
        qtd = min(5, int(getattr(contexto.arma, 'quantidade', 3)))
        tam_base = max(12, int(contexto.raio_char * 0.65))
        dist_base = contexto.raio_char * 1.4
        float_off = math.sin(contexto.tempo / 250) * contexto.raio_char * 0.1
        rot_off = contexto.tempo / 1500
        pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 200)

        for i in range(qtd):
            offset_ang = (i - (qtd - 1) / 2) * 22 + math.degrees(rot_off)
            r_m = contexto.rad + math.radians(offset_ang)
            dist = dist_base + float_off * (1 + i * 0.2)
            px = contexto.cx + math.cos(r_m) * dist
            py = contexto.cy + math.sin(r_m) * dist

            if "espada" in contexto.estilo_norm or "espectral" in contexto.estilo_norm:
                self._desenhar_arma_magica_espada(contexto, px, py, tam_base, r_m)
            elif "runa" in contexto.estilo_norm:
                self._desenhar_arma_magica_runa(contexto, px, py, tam_base, rot_off, pulso, i, qtd)
            elif "tentaculo" in contexto.estilo_norm:
                self._desenhar_arma_magica_tentaculo(contexto, px, py, tam_base, r_m, i)
            else:
                self._desenhar_arma_magica_padrao(contexto, px, py, tam_base, rot_off, i)

    def _resolver_dimensoes_transformavel(self, contexto):
        forma = getattr(contexto.arma, 'forma_atual', 1)
        if forma == 1:
            cabo_len = contexto.raio_char * 0.50
            lamina_len = contexto.raio_char * 1.20 * contexto.anim_scale
        else:
            cabo_len = contexto.raio_char * 0.85
            lamina_len = contexto.raio_char * 1.55 * contexto.anim_scale
        return forma, cabo_len, lamina_len

    def _desenhar_base_transformavel(self, contexto, cabo_end_x, cabo_end_y, larg, pulso):
        mec_col = (int(120 + 80 * pulso), int(100 + 60 * pulso), int(90 + 50 * pulso))
        pygame.draw.circle(self.tela, (40, 40, 50), (int(cabo_end_x), int(cabo_end_y)), larg + 2)
        pygame.draw.circle(self.tela, mec_col, (int(cabo_end_x), int(cabo_end_y)), larg, contexto.zw(2))
        pygame.draw.line(self.tela, (30, 18, 8), (int(contexto.cx) + 1, int(contexto.cy) + 1), (int(cabo_end_x) + 1, int(cabo_end_y) + 1), larg + 2)
        pygame.draw.line(self.tela, (90, 55, 25), (int(contexto.cx), int(contexto.cy)), (int(cabo_end_x), int(cabo_end_y)), larg)

    def _desenhar_transformavel_lanca_espada(self, contexto, forma, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg):
        if forma == 1:
            blade_pts = [
                (int(cabo_end_x - perp_x * larg * 0.7), int(cabo_end_y - perp_y * larg * 0.7)),
                (int(cabo_end_x + perp_x * larg * 0.7), int(cabo_end_y + perp_y * larg * 0.7)),
                (int(lamina_end_x - perp_x * larg * 0.3), int(lamina_end_y - perp_y * larg * 0.3)),
                (int(lamina_end_x), int(lamina_end_y)),
                (int(lamina_end_x + perp_x * larg * 0.3), int(lamina_end_y + perp_y * larg * 0.3)),
            ]
            pygame.draw.line(
                self.tela,
                (160, 165, 175),
                (int(cabo_end_x - perp_x * (larg + 4)), int(cabo_end_y - perp_y * (larg + 4))),
                (int(cabo_end_x + perp_x * (larg + 4)), int(cabo_end_y + perp_y * (larg + 4))),
                max(2, larg - 1),
            )
        else:
            blade_pts = [
                (int(cabo_end_x - perp_x * larg * 0.5), int(cabo_end_y - perp_y * larg * 0.5)),
                (int(cabo_end_x + perp_x * larg * 0.5), int(cabo_end_y + perp_y * larg * 0.5)),
                (int(lamina_end_x + perp_x), int(lamina_end_y + perp_y)),
                (int(lamina_end_x), int(lamina_end_y)),
                (int(lamina_end_x - perp_x), int(lamina_end_y - perp_y)),
            ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor, blade_pts)
            pygame.draw.polygon(self.tela, contexto.cor_escura, blade_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.line(self.tela, contexto.cor_clara, (int(cabo_end_x), int(cabo_end_y)), (int(lamina_end_x), int(lamina_end_y)), contexto.zw(1))

    def _desenhar_transformavel_chicote(self, contexto, forma, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg, lamina_len):
        if forma == 1:
            blade_pts = [
                (int(cabo_end_x - perp_x * larg * 0.7), int(cabo_end_y - perp_y * larg * 0.7)),
                (int(cabo_end_x + perp_x * larg * 0.7), int(cabo_end_y + perp_y * larg * 0.7)),
                (int(lamina_end_x - perp_x * larg * 0.3), int(lamina_end_y - perp_y * larg * 0.3)),
                (int(lamina_end_x), int(lamina_end_y)),
                (int(lamina_end_x + perp_x * larg * 0.3), int(lamina_end_y + perp_y * larg * 0.3)),
            ]
            try:
                pygame.draw.polygon(self.tela, contexto.cor, blade_pts)
                pygame.draw.polygon(self.tela, contexto.cor_escura, blade_pts, contexto.zw(1))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
            return

        num_seg = 14
        wpts = []
        for s in range(num_seg + 1):
            t = s / num_seg
            amp = contexto.raio_char * 0.2 * (1 - t * 0.7)
            wave = math.sin(t * math.pi * 3 + contexto.tempo / 100) * amp
            wx2 = cabo_end_x + math.cos(contexto.rad) * lamina_len * t
            wy2 = cabo_end_y + math.sin(contexto.rad) * lamina_len * t + math.cos(contexto.rad + math.pi / 2) * wave
            wpts.append((int(wx2), int(wy2)))
        for j in range(len(wpts) - 1):
            thick = max(1, int(larg * (1 - j / num_seg) + 0.5))
            try: pygame.draw.line(self.tela, contexto.cor, wpts[j], wpts[j + 1], thick)
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        if wpts:
            pygame.draw.circle(self.tela, contexto.cor_raridade, wpts[-1], max(2, larg - 2))

    def _desenhar_transformavel_padrao(self, contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg):
        blade_pts = [
            (int(cabo_end_x - perp_x * larg * 0.6), int(cabo_end_y - perp_y * larg * 0.6)),
            (int(cabo_end_x + perp_x * larg * 0.6), int(cabo_end_y + perp_y * larg * 0.6)),
            (int(lamina_end_x - perp_x * larg * 0.3), int(lamina_end_y - perp_y * larg * 0.3)),
            (int(lamina_end_x), int(lamina_end_y)),
            (int(lamina_end_x + perp_x * larg * 0.3), int(lamina_end_y + perp_y * larg * 0.3)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor, blade_pts)
            pygame.draw.polygon(self.tela, contexto.cor_escura, blade_pts, contexto.zw(1))
        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.line(self.tela, contexto.cor_clara, (int(cabo_end_x), int(cabo_end_y)), (int(lamina_end_x), int(lamina_end_y)), 1)

    def _desenhar_arma_transformavel(self, contexto):
        forma, cabo_len, lamina_len = self._resolver_dimensoes_transformavel(contexto)
        larg = max(contexto.zw(3), int(contexto.larg_base * 1.1))
        pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 200)

        cabo_end_x = contexto.cx + math.cos(contexto.rad) * cabo_len
        cabo_end_y = contexto.cy + math.sin(contexto.rad) * cabo_len
        lamina_end_x = contexto.cx + math.cos(contexto.rad) * (cabo_len + lamina_len)
        lamina_end_y = contexto.cy + math.sin(contexto.rad) * (cabo_len + lamina_len)
        perp_x = math.cos(contexto.rad + math.pi / 2)
        perp_y = math.sin(contexto.rad + math.pi / 2)
        self._desenhar_base_transformavel(contexto, cabo_end_x, cabo_end_y, larg, pulso)

        if "lanca" in contexto.estilo_norm and "espada" in contexto.estilo_norm:
            self._desenhar_transformavel_lanca_espada(contexto, forma, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg)
        elif "chicote" in contexto.estilo_norm:
            self._desenhar_transformavel_chicote(contexto, forma, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg, lamina_len)
        else:
            self._desenhar_transformavel_padrao(contexto, cabo_end_x, cabo_end_y, lamina_end_x, lamina_end_y, perp_x, perp_y, larg)

        if contexto.raridade_norm not in ['comum', 'incomum']:
            pygame.draw.circle(self.tela, contexto.cor_raridade, (int(lamina_end_x), int(lamina_end_y)), max(4, larg // 2))

    def _desenhar_empunhadura_adagas_gemeas(self, contexto, hand_x, hand_y, cabo_ex, cabo_ey, larg, daga_ang):
        pygame.draw.line(self.tela, (30, 18, 8), (int(hand_x) + 1, int(hand_y) + 1), (int(cabo_ex) + 1, int(cabo_ey) + 1), larg + 3)
        pygame.draw.line(self.tela, (60, 38, 18), (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), larg + 2)
        pygame.draw.line(self.tela, (100, 65, 30), (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), max(1, larg))
        for gi in range(1, 4):
            gt = gi / 4
            gx = int(hand_x + (cabo_ex - hand_x) * gt)
            gy = int(hand_y + (cabo_ey - hand_y) * gt)
            gp_x = math.cos(daga_ang + math.pi / 2) * (larg + 1)
            gp_y = math.sin(daga_ang + math.pi / 2) * (larg + 1)
            pygame.draw.line(self.tela, (45, 28, 10), (int(gx - gp_x), int(gy - gp_y)), (int(gx + gp_x), int(gy + gp_y)), 1)
        grd_x = math.cos(daga_ang + math.pi / 2) * (larg + 3)
        grd_y = math.sin(daga_ang + math.pi / 2) * (larg + 3)
        pygame.draw.line(self.tela, (150, 155, 165), (int(cabo_ex - grd_x), int(cabo_ey - grd_y)), (int(cabo_ex + grd_x), int(cabo_ey + grd_y)), max(2, larg))

    def _desenhar_lamina_adagas_gemeas(self, contexto, cabo_ex, cabo_ey, corpo_end_x, corpo_end_y, tip_x, tip_y, lam_w_base, lam_w_tip, perp_bx, perp_by):
        pygame.draw.line(self.tela, (20, 20, 25), (int(cabo_ex) + 1, int(cabo_ey) + 1), (int(tip_x) + 1, int(tip_y) + 1), lam_w_base + 2)
        lam_poly = [
            (int(cabo_ex - perp_bx * lam_w_base), int(cabo_ey - perp_by * lam_w_base)),
            (int(cabo_ex + perp_bx * lam_w_base), int(cabo_ey + perp_by * lam_w_base)),
            (int(corpo_end_x + perp_bx * lam_w_tip), int(corpo_end_y + perp_by * lam_w_tip)),
            (int(tip_x), int(tip_y)),
            (int(corpo_end_x - perp_bx * lam_w_tip), int(corpo_end_y - perp_by * lam_w_tip)),
        ]
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, lam_poly)
            pygame.draw.polygon(self.tela, contexto.cor, lam_poly, contexto.zw(1))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.line(self.tela, contexto.cor_clara, (int(cabo_ex), int(cabo_ey)), (int(corpo_end_x), int(corpo_end_y)), 1)

    def _desenhar_fx_adagas_gemeas(self, contexto, cabo_ex, cabo_ey, corpo_end_x, corpo_end_y, tip_x, tip_y, lamina_len, lam_w_base, glow_alpha_base, i):
        if contexto.atacando or glow_alpha_base > 50:
            try:
                sz = max(8, int(lamina_len * 2))
                gs = self._get_surface(sz * 2, sz * 2, pygame.SRCALPHA)
                mid_x = int((cabo_ex + tip_x) / 2) - sz
                mid_y = int((cabo_ey + tip_y) / 2) - sz
                local_s = (sz - int(cabo_ex - mid_x - sz), sz - int(cabo_ey - mid_y - sz))
                local_e = (
                    sz - int(cabo_ex - mid_x - sz) + int(tip_x - cabo_ex),
                    sz - int(cabo_ey - mid_y - sz) + int(tip_y - cabo_ey),
                )
                pygame.draw.line(
                    gs,
                    (*contexto.cor, glow_alpha_base),
                    (max(0, min(sz * 2 - 1, local_s[0])), max(0, min(sz * 2 - 1, local_s[1]))),
                    (max(0, min(sz * 2 - 1, local_e[0])), max(0, min(sz * 2 - 1, local_e[1]))),
                    max(4, lam_w_base + 3),
                )
                self.tela.blit(gs, (mid_x, mid_y))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01

        if contexto.raridade_norm not in ['comum', 'incomum']:
            rune_x = int((cabo_ex + corpo_end_x) / 2)
            rune_y = int((cabo_ey + corpo_end_y) / 2)
            rune_a = int(160 + 80 * math.sin(contexto.tempo / 120 + i * math.pi))
            try:
                rs = self._get_surface(contexto.zw(8), contexto.zw(8), pygame.SRCALPHA)
                pygame.draw.circle(rs, (*contexto.cor_raridade, rune_a), (4, 4), 3)
                self.tela.blit(rs, (rune_x - 4, rune_y - 4))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01

        tip_r = max(2, max(contexto.zw(3), int(contexto.larg_base * 1.1)) - 1)
        tip_a = int(160 + 80 * math.sin(contexto.tempo / 90 + i))
        try:
            ts = self._get_surface(tip_r * 5, tip_r * 5, pygame.SRCALPHA)
            pygame.draw.circle(ts, (*contexto.cor_clara, tip_a), (tip_r * 2, tip_r * 2), tip_r * 2)
            self.tela.blit(ts, (int(tip_x) - tip_r * 2, int(tip_y) - tip_r * 2))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01
        tip_cor = contexto.cor_raridade if contexto.raridade_norm != 'comum' else contexto.cor_clara
        pygame.draw.circle(self.tela, tip_cor, (int(tip_x), int(tip_y)), tip_r)

    def _desenhar_arma_dupla_adagas_gemeas(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        larg_base = contexto.larg_base
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale

        sep = raio_char * 0.55
        larg = max(contexto.zw(3), int(larg_base * 1.1))
        cabo_len = raio_char * 0.35
        lamina_len = raio_char * 1.05 * anim_scale
        pulso = 0.5 + 0.5 * math.sin(tempo / 180)
        glow_alpha_base = int(100 + 70 * pulso) if contexto.atacando else int(35 + 20 * pulso)

        for i, lado_sinal in enumerate([-1, 1]):
            hand_x = cx + math.cos(rad + math.pi / 2) * sep * lado_sinal * 0.85
            hand_y = cy + math.sin(rad + math.pi / 2) * sep * lado_sinal * 0.85

            spread_deg = 18 * lado_sinal
            daga_ang = rad + math.radians(spread_deg)

            cabo_ex = hand_x + math.cos(daga_ang) * cabo_len
            cabo_ey = hand_y + math.sin(daga_ang) * cabo_len
            self._desenhar_empunhadura_adagas_gemeas(contexto, hand_x, hand_y, cabo_ex, cabo_ey, larg, daga_ang)

            corpo_pct = 0.72
            curva_pct = 0.28
            corpo_end_x = cabo_ex + math.cos(daga_ang) * lamina_len * corpo_pct
            corpo_end_y = cabo_ey + math.sin(daga_ang) * lamina_len * corpo_pct
            curva_deg = -12 * lado_sinal
            curva_ang = daga_ang + math.radians(curva_deg)
            tip_x = corpo_end_x + math.cos(curva_ang) * lamina_len * curva_pct
            tip_y = corpo_end_y + math.sin(curva_ang) * lamina_len * curva_pct

            lam_w_base = max(3, larg - 1)
            lam_w_tip = max(1, larg // 3)
            perp_bx = math.cos(daga_ang + math.pi / 2)
            perp_by = math.sin(daga_ang + math.pi / 2)
            self._desenhar_lamina_adagas_gemeas(contexto, cabo_ex, cabo_ey, corpo_end_x, corpo_end_y, tip_x, tip_y, lam_w_base, lam_w_tip, perp_bx, perp_by)
            self._desenhar_fx_adagas_gemeas(contexto, cabo_ex, cabo_ey, corpo_end_x, corpo_end_y, tip_x, tip_y, lamina_len, lam_w_base, glow_alpha_base, i)

    def _desenhar_arma_dupla_kamas(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_clara = contexto.cor_clara
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        _zw = contexto.zw

        sep = raio_char * 0.55
        larg = max(_zw(3), int(larg_base * 1.1))
        cabo_len = raio_char * 0.40
        lamina_len = raio_char * 0.90 * anim_scale
        lw = max(3, larg)
        pulso = 0.5 + 0.5 * math.sin(tempo / 180)

        for lado_sinal in [-1, 1]:
            hand_x = cx + math.cos(rad + math.pi / 2) * sep * lado_sinal * 0.8
            hand_y = cy + math.sin(rad + math.pi / 2) * sep * lado_sinal * 0.8
            spread = math.radians(20 * lado_sinal)
            ang = rad + spread

            cabo_ex = hand_x + math.cos(ang) * cabo_len
            cabo_ey = hand_y + math.sin(ang) * cabo_len
            pygame.draw.line(self.tela, (30, 18, 8), (int(hand_x) + 1, int(hand_y) + 1), (int(cabo_ex) + 1, int(cabo_ey) + 1), lw + 2)
            pygame.draw.line(self.tela, (90, 55, 25), (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw)
            g_perp_x = math.cos(ang + math.pi / 2) * (lw + 4)
            g_perp_y = math.sin(ang + math.pi / 2) * (lw + 4)
            pygame.draw.line(self.tela, (160, 165, 175), (int(cabo_ex - g_perp_x), int(cabo_ey - g_perp_y)), (int(cabo_ex + g_perp_x), int(cabo_ey + g_perp_y)), max(2, lw - 1))
            curve_ang = ang + math.pi / 2 * lado_sinal
            ctrl_x = cabo_ex + math.cos(curve_ang) * lamina_len * 0.5
            ctrl_y = cabo_ey + math.sin(curve_ang) * lamina_len * 0.5
            hook_x = cabo_ex + math.cos(curve_ang) * lamina_len
            hook_y = cabo_ey + math.sin(curve_ang) * lamina_len
            prev = (int(cabo_ex), int(cabo_ey))
            for seg in range(1, 9):
                t = seg / 8
                bx = (1 - t) ** 2 * cabo_ex + 2 * (1 - t) * t * ctrl_x + t ** 2 * hook_x
                by = (1 - t) ** 2 * cabo_ey + 2 * (1 - t) * t * ctrl_y + t ** 2 * hook_y
                pygame.draw.line(self.tela, cor, prev, (int(bx), int(by)), lw)
                prev = (int(bx), int(by))
            glow_r = max(3, lw)
            try:
                gs = self._get_surface(glow_r * 4, glow_r * 4, pygame.SRCALPHA)
                pygame.draw.circle(gs, (*cor_clara, int(150 + 80 * pulso)), (glow_r * 2, glow_r * 2), glow_r * 2)
                self.tela.blit(gs, (int(hook_x) - glow_r * 2, int(hook_y) - glow_r * 2))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01
            pygame.draw.circle(self.tela, cor_raridade, (int(hook_x), int(hook_y)), glow_r)

    def _desenhar_arma_dupla_sai(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_clara = contexto.cor_clara
        cor_escura = contexto.cor_escura
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        _zw = contexto.zw

        sep = raio_char * 0.55
        larg = max(_zw(3), int(larg_base * 1.1))
        cabo_len = raio_char * 0.40
        lamina_len = raio_char * 0.90 * anim_scale
        lw = max(3, larg)

        def _dupla_blade_poly(bx, by, tx, ty, ang, w_base, w_tip):
            px = math.cos(ang + math.pi / 2)
            py = math.sin(ang + math.pi / 2)
            return [
                (int(bx - px * w_base), int(by - py * w_base)),
                (int(bx + px * w_base), int(by + py * w_base)),
                (int(tx + px * w_tip), int(ty + py * w_tip)),
                (int(tx), int(ty)),
                (int(tx - px * w_tip), int(ty - py * w_tip)),
            ]

        for lado_sinal in [-1, 1]:
            hand_x = cx + math.cos(rad + math.pi / 2) * sep * lado_sinal * 0.8
            hand_y = cy + math.sin(rad + math.pi / 2) * sep * lado_sinal * 0.8
            spread = math.radians(20 * lado_sinal)
            ang = rad + spread

            cabo_ex = hand_x + math.cos(ang) * cabo_len
            cabo_ey = hand_y + math.sin(ang) * cabo_len
            tip_x = cabo_ex + math.cos(ang) * lamina_len
            tip_y = cabo_ey + math.sin(ang) * lamina_len

            pygame.draw.line(self.tela, (30, 18, 8), (int(hand_x) + 1, int(hand_y) + 1), (int(cabo_ex) + 1, int(cabo_ey) + 1), lw + 2)
            pygame.draw.line(self.tela, (90, 55, 25), (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw)
            lam_poly_c = _dupla_blade_poly(hand_x, hand_y, tip_x, tip_y, ang, lw, lw // 2)
            try:
                pygame.draw.polygon(self.tela, cor_escura, lam_poly_c)
                pygame.draw.polygon(self.tela, cor, lam_poly_c, _zw(1))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01
            pygame.draw.line(self.tela, cor_clara, (int(cabo_ex), int(cabo_ey)), (int(tip_x), int(tip_y)), _zw(1))
            asa_len = lamina_len * 0.4
            for asa_sinal in [-1, 1]:
                asa_ang = ang + math.pi / 2 * asa_sinal * 0.7
                ax = cabo_ex + math.cos(asa_ang) * asa_len
                ay = cabo_ey + math.sin(asa_ang) * asa_len
                pygame.draw.line(self.tela, (180, 185, 195), (int(cabo_ex), int(cabo_ey)), (int(ax), int(ay)), max(1, lw - 1))
                pygame.draw.circle(self.tela, (200, 205, 215), (int(ax), int(ay)), max(2, lw - 2))
            pygame.draw.circle(self.tela, cor_raridade, (int(tip_x), int(tip_y)), max(2, lw - 1))

    def _desenhar_arma_dupla_garras(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_clara = contexto.cor_clara
        cor_escura = contexto.cor_escura
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        atacando = contexto.atacando
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        _zw = contexto.zw

        sep = raio_char * 0.55
        larg = max(_zw(3), int(larg_base * 1.1))
        cabo_len = raio_char * 0.40
        lamina_len = raio_char * 0.90 * anim_scale
        lw = max(3, larg)
        pulso = 0.5 + 0.5 * math.sin(tempo / 180)

        for lado_sinal in [-1, 1]:
            hand_x = cx + math.cos(rad + math.pi / 2) * sep * lado_sinal * 0.8
            hand_y = cy + math.sin(rad + math.pi / 2) * sep * lado_sinal * 0.8
            spread = math.radians(20 * lado_sinal)
            ang = rad + spread

            cabo_ex = hand_x + math.cos(ang) * cabo_len
            cabo_ey = hand_y + math.sin(ang) * cabo_len
            perp_x = math.cos(ang + math.pi / 2) * (lw + 3)
            perp_y = math.sin(ang + math.pi / 2) * (lw + 3)
            base_pts = [
                (int(hand_x - perp_x), int(hand_y - perp_y)),
                (int(hand_x + perp_x), int(hand_y + perp_y)),
                (int(cabo_ex + perp_x), int(cabo_ey + perp_y)),
                (int(cabo_ex - perp_x), int(cabo_ey - perp_y)),
            ]
            try:
                pygame.draw.polygon(self.tela, (55, 30, 12), base_pts)
                pygame.draw.polygon(self.tela, (100, 65, 30), base_pts, _zw(1))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01
            garra_len = lamina_len * 0.7
            for ga_deg in [-25 * lado_sinal, 0, 25 * lado_sinal]:
                ga = ang + math.radians(ga_deg)
                gx = cabo_ex + math.cos(ga) * garra_len
                gy = cabo_ey + math.sin(ga) * garra_len
                pygame.draw.line(self.tela, cor_escura, (int(cabo_ex) + 1, int(cabo_ey) + 1), (int(gx) + 1, int(gy) + 1), max(1, lw - 1) + 1)
                pygame.draw.line(self.tela, cor, (int(cabo_ex), int(cabo_ey)), (int(gx), int(gy)), max(1, lw - 1))
                pygame.draw.line(self.tela, cor_clara, (int(cabo_ex), int(cabo_ey)), (int(gx), int(gy)), 1)
                pygame.draw.circle(self.tela, cor_raridade, (int(gx), int(gy)), max(2, lw - 2))
            if atacando:
                try:
                    sz = int(garra_len * 2.5)
                    gs = self._get_surface(sz, sz, pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*cor, int(80 * pulso)), (sz // 2, sz // 2), sz // 2)
                    self.tela.blit(gs, (int(cabo_ex) - sz // 2, int(cabo_ey) - sz // 2))
                except Exception as _e:
                    _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_arma_dupla_tonfas(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_clara = contexto.cor_clara
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        _zw = contexto.zw

        sep = raio_char * 0.55
        larg = max(_zw(3), int(larg_base * 1.1))
        cabo_len = raio_char * 0.40
        lamina_len = raio_char * 0.90 * anim_scale
        lw = max(3, larg)

        for lado_sinal in [-1, 1]:
            hand_x = cx + math.cos(rad + math.pi / 2) * sep * lado_sinal * 0.8
            hand_y = cy + math.sin(rad + math.pi / 2) * sep * lado_sinal * 0.8
            spread = math.radians(20 * lado_sinal)
            ang = rad + spread

            tip_x = hand_x + math.cos(ang) * lamina_len
            tip_y = hand_y + math.sin(ang) * lamina_len
            pygame.draw.line(self.tela, (20, 18, 20), (int(hand_x) + 1, int(hand_y) + 1), (int(tip_x) + 1, int(tip_y) + 1), lw + 3)
            pygame.draw.line(self.tela, cor, (int(hand_x), int(hand_y)), (int(tip_x), int(tip_y)), lw + 1)
            pygame.draw.line(self.tela, cor_clara, (int(hand_x), int(hand_y)), (int(tip_x), int(tip_y)), _zw(1))
            pivot_x = hand_x + math.cos(ang) * lamina_len * 0.28
            pivot_y = hand_y + math.sin(ang) * lamina_len * 0.28
            handle_ang = ang + math.pi / 2 * lado_sinal
            grip_x = pivot_x + math.cos(handle_ang) * cabo_len
            grip_y = pivot_y + math.sin(handle_ang) * cabo_len
            pygame.draw.line(self.tela, (30, 18, 8), (int(pivot_x) + 1, int(pivot_y) + 1), (int(grip_x) + 1, int(grip_y) + 1), lw + 2)
            pygame.draw.line(self.tela, (90, 55, 25), (int(pivot_x), int(pivot_y)), (int(grip_x), int(grip_y)), lw)
            pygame.draw.circle(self.tela, cor_raridade, (int(tip_x), int(tip_y)), max(2, lw - 1))
            pygame.draw.circle(self.tela, (180, 185, 195), (int(grip_x), int(grip_y)), max(2, lw - 2))
            for fi in [0.35, 0.65]:
                fx = int(pivot_x + (grip_x - pivot_x) * fi)
                fy = int(pivot_y + (grip_y - pivot_y) * fi)
                pygame.draw.circle(self.tela, (50, 28, 10), (fx, fy), max(2, lw - 1))

    def _criar_poligono_lamina_dupla(self, bx, by, tx, ty, ang, w_base, w_tip):
        perp_x = math.cos(ang + math.pi / 2)
        perp_y = math.sin(ang + math.pi / 2)
        return [
            (int(bx - perp_x * w_base), int(by - perp_y * w_base)),
            (int(bx + perp_x * w_base), int(by + perp_y * w_base)),
            (int(tx + perp_x * w_tip), int(ty + perp_y * w_tip)),
            (int(tx), int(ty)),
            (int(tx - perp_x * w_tip), int(ty - perp_y * w_tip)),
        ]

    def _iterar_laminas_duplas_padrao(self, contexto, sep, cabo_len, lamina_len):
        for lado_sinal in (-1, 1):
            hand_x = contexto.cx + math.cos(contexto.rad + math.pi / 2) * sep * lado_sinal * 0.8
            hand_y = contexto.cy + math.sin(contexto.rad + math.pi / 2) * sep * lado_sinal * 0.8
            ang = contexto.rad + math.radians(20 * lado_sinal)
            cabo_ex = hand_x + math.cos(ang) * cabo_len
            cabo_ey = hand_y + math.sin(ang) * cabo_len
            tip_x = cabo_ex + math.cos(ang) * lamina_len
            tip_y = cabo_ey + math.sin(ang) * lamina_len
            yield hand_x, hand_y, cabo_ex, cabo_ey, tip_x, tip_y, ang

    def _desenhar_empunhadura_dupla_padrao(self, contexto, hand_x, hand_y, cabo_ex, cabo_ey, ang, lw):
        pygame.draw.line(self.tela, (30, 18, 8), (int(hand_x) + 1, int(hand_y) + 1), (int(cabo_ex) + 1, int(cabo_ey) + 1), lw + 2)
        pygame.draw.line(self.tela, (80, 48, 20), (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw + 1)
        for gi in range(1, 4):
            gt = gi / 4
            gx = int(hand_x + (cabo_ex - hand_x) * gt)
            gy = int(hand_y + (cabo_ey - hand_y) * gt)
            gp_x = math.cos(ang + math.pi / 2) * (lw + 1)
            gp_y = math.sin(ang + math.pi / 2) * (lw + 1)
            pygame.draw.line(self.tela, (45, 26, 8), (int(gx - gp_x), int(gy - gp_y)), (int(gx + gp_x), int(gy + gp_y)), 1)

    def _desenhar_guarda_dupla_padrao(self, cabo_ex, cabo_ey, ang, lw):
        g_perp_x = math.cos(ang + math.pi / 2) * (lw + 4)
        g_perp_y = math.sin(ang + math.pi / 2) * (lw + 4)
        pygame.draw.line(self.tela, (160, 165, 175), (int(cabo_ex - g_perp_x), int(cabo_ey - g_perp_y)), (int(cabo_ex + g_perp_x), int(cabo_ey + g_perp_y)), max(2, lw - 1))

    def _desenhar_lamina_dupla_padrao(self, contexto, hand_x, hand_y, cabo_ex, cabo_ey, tip_x, tip_y, ang, lw):
        lam_poly = self._criar_poligono_lamina_dupla(hand_x, hand_y, tip_x, tip_y, ang, lw, max(1, lw // 2))
        try:
            pygame.draw.polygon(self.tela, contexto.cor_escura, lam_poly)
            pygame.draw.polygon(self.tela, contexto.cor, lam_poly, contexto.zw(1))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.line(self.tela, contexto.cor_clara, (int(cabo_ex), int(cabo_ey)), (int(tip_x), int(tip_y)), contexto.zw(1))
        perp_x = math.cos(ang + math.pi / 2) * (lw + 1)
        perp_y = math.sin(ang + math.pi / 2) * (lw + 1)
        for si in range(1, 5):
            st = si / 5
            sx = cabo_ex + (tip_x - cabo_ex) * st
            sy = cabo_ey + (tip_y - cabo_ey) * st
            tsx = cabo_ex + (tip_x - cabo_ex) * (st - 0.04)
            tsy = cabo_ey + (tip_y - cabo_ey) * (st - 0.04)
            pygame.draw.line(self.tela, contexto.cor_clara, (int(sx + perp_x), int(sy + perp_y)), (int(tsx + perp_x * 2.5), int(tsy + perp_y * 2.5)), 1)

    def _desenhar_glow_dupla_padrao(self, contexto, cabo_ex, cabo_ey, tip_x, tip_y, lamina_len, lw, pulso):
        glow_a = int(100 + 70 * pulso) if contexto.atacando else int(30 + 15 * pulso)
        try:
            sz = max(8, int(lamina_len * 2))
            gs = self._get_surface(sz * 2, sz * 2, pygame.SRCALPHA)
            mid_x = int((cabo_ex + tip_x) / 2) - sz
            mid_y = int((cabo_ey + tip_y) / 2) - sz
            ls = (sz - int(cabo_ex - mid_x - sz), sz - int(cabo_ey - mid_y - sz))
            le = (sz - int(cabo_ex - mid_x - sz) + int(tip_x - cabo_ex), sz - int(cabo_ey - mid_y - sz) + int(tip_y - cabo_ey))
            pygame.draw.line(gs, (*contexto.cor, glow_a), (max(0, min(sz * 2 - 1, ls[0])), max(0, min(sz * 2 - 1, ls[1]))), (max(0, min(sz * 2 - 1, le[0])), max(0, min(sz * 2 - 1, le[1]))), max(4, lw + 2))
            self.tela.blit(gs, (mid_x, mid_y))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_ponta_dupla_padrao(self, contexto, tip_x, tip_y, lw):
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(tip_x), int(tip_y)), max(2, lw - 1))

    def _desenhar_arma_dupla_padrao(self, contexto):
        sep = contexto.raio_char * 0.55
        larg = max(contexto.zw(3), int(contexto.larg_base * 1.1))
        cabo_len = contexto.raio_char * 0.40
        lamina_len = contexto.raio_char * 0.90 * contexto.anim_scale
        lw = max(3, larg)
        pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 180)
        for hand_x, hand_y, cabo_ex, cabo_ey, tip_x, tip_y, ang in self._iterar_laminas_duplas_padrao(contexto, sep, cabo_len, lamina_len):
            self._desenhar_empunhadura_dupla_padrao(contexto, hand_x, hand_y, cabo_ex, cabo_ey, ang, lw)
            self._desenhar_guarda_dupla_padrao(cabo_ex, cabo_ey, ang, lw)
            self._desenhar_lamina_dupla_padrao(contexto, hand_x, hand_y, cabo_ex, cabo_ey, tip_x, tip_y, ang, lw)
            self._desenhar_glow_dupla_padrao(contexto, cabo_ex, cabo_ey, tip_x, tip_y, lamina_len, lw, pulso)
            self._desenhar_ponta_dupla_padrao(contexto, tip_x, tip_y, lw)

    def _desenhar_arma_dupla(self, contexto):
        estilo_norm = contexto.estilo_norm
        if estilo_norm == "adagas gemeas":
            return self._desenhar_arma_dupla_adagas_gemeas(contexto)
        if estilo_norm == "kamas":
            return self._desenhar_arma_dupla_kamas(contexto)
        if estilo_norm == "sai":
            return self._desenhar_arma_dupla_sai(contexto)
        if estilo_norm == "garras":
            return self._desenhar_arma_dupla_garras(contexto)
        if estilo_norm == "tonfas":
            return self._desenhar_arma_dupla_tonfas(contexto)
        return self._desenhar_arma_dupla_padrao(contexto)

    def _desenhar_cabo_mangual(self, contexto, cabo_ex, cabo_ey, perp_cx, perp_cy):
        pygame.draw.line(self.tela, (20, 18, 25), (int(contexto.cx) + 2, int(contexto.cy) + 2), (int(cabo_ex) + 2, int(cabo_ey) + 2), max(7, contexto.larg_base + 5))
        pygame.draw.line(self.tela, (55, 50, 65), (int(contexto.cx), int(contexto.cy)), (int(cabo_ex), int(cabo_ey)), max(6, contexto.larg_base + 4))
        pygame.draw.line(self.tela, (110, 105, 125), (int(contexto.cx), int(contexto.cy)), (int(cabo_ex), int(cabo_ey)), max(2, contexto.larg_base))
        for fi in range(1, 4):
            ft = 0.15 + fi * 0.22
            fx = contexto.cx + (cabo_ex - contexto.cx) * ft
            fy = contexto.cy + (cabo_ey - contexto.cy) * ft
            g_perp = contexto.larg_base + 3
            pygame.draw.line(
                self.tela,
                (40, 25, 15),
                (int(fx - perp_cx * g_perp), int(fy - perp_cy * g_perp)),
                (int(fx + perp_cx * g_perp), int(fy + perp_cy * g_perp)),
                2,
            )
        pygame.draw.circle(self.tela, (70, 65, 80), (int(contexto.cx), int(contexto.cy)), max(3, contexto.larg_base // 2 + 1))
        pygame.draw.circle(self.tela, contexto.cor_raridade, (int(contexto.cx), int(contexto.cy)), max(2, contexto.larg_base // 2), contexto.zw(1))

    def _desenhar_pivo_mangual(self, contexto, cabo_ex, cabo_ey):
        piv_r = max(5, contexto.larg_base + 2)
        pygame.draw.circle(self.tela, (45, 42, 55), (int(cabo_ex), int(cabo_ey)), piv_r + 2)
        pygame.draw.circle(self.tela, (130, 125, 145), (int(cabo_ex), int(cabo_ey)), piv_r, contexto.zw(2))
        for ri in range(3):
            r_ang = contexto.tempo / 300 + ri * math.pi * 2 / 3
            rx = cabo_ex + math.cos(r_ang) * (piv_r - 1)
            ry = cabo_ey + math.sin(r_ang) * (piv_r - 1)
            rune_a = int(120 + 80 * math.sin(contexto.tempo / 180 + ri))
            try:
                rs = self._get_surface(contexto.zw(6), contexto.zw(6), pygame.SRCALPHA)
                pygame.draw.circle(rs, (*contexto.cor_raridade, min(255, rune_a)), (3, 3), 3)
                self.tela.blit(rs, (int(rx) - 3, int(ry) - 3))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

    def _coletar_pontos_corrente_mangual(self, contexto, cabo_ex, cabo_ey, corrente_comp, num_elos, perp_cx, perp_cy):
        chain_pts = []
        sag = corrente_comp * 0.06 * (1 + 0.05 * math.sin(contexto.tempo / 250))
        for ei in range(num_elos + 1):
            t = ei / num_elos
            base_px = cabo_ex + math.cos(contexto.rad) * corrente_comp * t
            base_py = cabo_ey + math.sin(contexto.rad) * corrente_comp * t
            grav = sag * math.sin(t * math.pi)
            wave = math.sin(t * math.pi * 2.5 + contexto.tempo / 180) * contexto.raio_char * 0.025 * (1 - t * 0.3)
            off_x = perp_cx * (wave + grav * 0.3)
            off_y = perp_cy * (wave + grav * 0.3) + grav * 0.7
            chain_pts.append((base_px + off_x, base_py + off_y))
        return chain_pts

    def _desenhar_elos_mangual(self, contexto, chain_pts):
        for ei, (ex, ey) in enumerate(chain_pts):
            elo_ang = contexto.rad + (math.pi / 2 if ei % 2 == 0 else 0) + math.sin(contexto.tempo / 200 + ei) * 0.15
            ew = max(4, contexto.larg_base + 1)
            eh = max(3, contexto.larg_base - 1)
            e_perp_x = math.cos(elo_ang) * ew
            e_perp_y = math.sin(elo_ang) * ew
            e_fwd_x = math.cos(elo_ang + math.pi / 2) * eh
            e_fwd_y = math.sin(elo_ang + math.pi / 2) * eh
            elo_pts = [
                (int(ex - e_perp_x - e_fwd_x), int(ey - e_perp_y - e_fwd_y)),
                (int(ex + e_perp_x - e_fwd_x), int(ey + e_perp_y - e_fwd_y)),
                (int(ex + e_perp_x + e_fwd_x), int(ey + e_perp_y + e_fwd_y)),
                (int(ex - e_perp_x + e_fwd_x), int(ey - e_perp_y + e_fwd_y)),
            ]
            try:
                shade = min(255, 75 + int(ei * 12))
                pygame.draw.polygon(self.tela, (shade, shade - 5, shade + 8), elo_pts)
                pygame.draw.polygon(self.tela, (min(255, shade + 40), min(255, shade + 35), min(255, shade + 50)), elo_pts, contexto.zw(1))
            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_glow_cabeca_mangual(self, contexto, hx, hy, head_r, breath):
        glow_r = int(head_r * (1.8 + 0.4 * breath))
        try:
            gs = self._get_surface(glow_r * 2, glow_r * 2, pygame.SRCALPHA)
            glow_a = int(50 + 40 * breath) if not contexto.atacando else int(140 * contexto.anim_scale)
            pygame.draw.circle(gs, (*contexto.cor, min(255, glow_a)), (glow_r, glow_r), glow_r)
            self.tela.blit(gs, (int(hx) - glow_r, int(hy) - glow_r))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_corpo_cabeca_mangual(self, contexto, hx, hy, head_r):
        pygame.draw.circle(self.tela, (12, 10, 18), (int(hx) + 3, int(hy) + 3), head_r + 2)
        pygame.draw.circle(self.tela, contexto.cor_escura, (int(hx), int(hy)), head_r)
        pygame.draw.circle(self.tela, contexto.cor, (int(hx), int(hy)), head_r - 1)
        pygame.draw.circle(self.tela, contexto.cor_clara, (int(hx - head_r * 0.25), int(hy - head_r * 0.25)), max(2, head_r // 3))

    def _desenhar_spikes_cabeca_mangual(self, contexto, hx, hy, head_r):
        num_spikes = 8
        spike_rot = contexto.tempo / 120
        for si in range(num_spikes):
            s_ang = spike_rot + si * math.pi * 2 / num_spikes
            spike_len = head_r * 0.85
            spike_w = max(2, head_r // 3)
            tip_x = hx + math.cos(s_ang) * (head_r + spike_len)
            tip_y = hy + math.sin(s_ang) * (head_r + spike_len)
            mid_x = hx + math.cos(s_ang) * (head_r + spike_len * 0.25)
            mid_y = hy + math.sin(s_ang) * (head_r + spike_len * 0.25)
            s_perp_x = math.cos(s_ang + math.pi / 2) * spike_w
            s_perp_y = math.sin(s_ang + math.pi / 2) * spike_w
            base_x = hx + math.cos(s_ang) * (head_r - 1)
            base_y = hy + math.sin(s_ang) * (head_r - 1)
            diamond = [(int(base_x), int(base_y)), (int(mid_x - s_perp_x), int(mid_y - s_perp_y)), (int(tip_x), int(tip_y)), (int(mid_x + s_perp_x), int(mid_y + s_perp_y))]
            try:
                pygame.draw.polygon(self.tela, contexto.cor, diamond)
                pygame.draw.polygon(self.tela, contexto.cor_clara, diamond, contexto.zw(1))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_runas_cabeca_mangual(self, contexto, hx, hy, head_r):
        ring_r = int(head_r * 0.75)
        pygame.draw.circle(self.tela, contexto.cor_escura, (int(hx), int(hy)), ring_r, contexto.zw(2))
        for ri in range(4):
            rune_ang = contexto.tempo / 200 + ri * math.pi / 2
            rune_x = hx + math.cos(rune_ang) * ring_r
            rune_y = hy + math.sin(rune_ang) * ring_r
            rune_brightness = int(160 + 80 * math.sin(contexto.tempo / 150 + ri * 1.5))
            try:
                rs = self._get_surface(contexto.zw(6), contexto.zw(6), pygame.SRCALPHA)
                pygame.draw.circle(rs, (*contexto.cor_raridade, min(255, rune_brightness)), (3, 3), 3)
                self.tela.blit(rs, (int(rune_x) - 3, int(rune_y) - 3))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_impacto_cabeca_mangual(self, contexto, hx, hy, head_r):
        if not contexto.atacando:
            return
        ring_prog = min(1.0, (contexto.anim_scale - 1.05) * 5)
        impact_r = int(head_r * 2.5 * ring_prog)
        if impact_r <= 3:
            return
        try:
            irs = self._get_surface(impact_r * 2 + 4, impact_r * 2 + 4, pygame.SRCALPHA)
            ring_a = int(180 * (1 - ring_prog * 0.7))
            pygame.draw.circle(irs, (*contexto.cor_raridade, ring_a), (impact_r + 2, impact_r + 2), impact_r, max(2, contexto.larg_base // 2))
            self.tela.blit(irs, (int(hx) - impact_r - 2, int(hy) - impact_r - 2))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_aura_raridade_cabeca_mangual(self, contexto, hx, hy, head_r, breath, pulso):
        if contexto.raridade_norm == "comum":
            return
        rar_a = int(80 + 60 * pulso)
        rar_r = head_r + int(head_r * 0.6 * breath)
        try:
            rs = self._get_surface(rar_r * 4, rar_r * 4, pygame.SRCALPHA)
            pygame.draw.circle(rs, (*contexto.cor_raridade, rar_a), (rar_r * 2, rar_r * 2), rar_r)
            self.tela.blit(rs, (int(hx) - rar_r * 2, int(hy) - rar_r * 2))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_cabeca_mangual(self, contexto, hx, hy, head_r, breath, pulso):
        self._desenhar_glow_cabeca_mangual(contexto, hx, hy, head_r, breath)
        self._desenhar_corpo_cabeca_mangual(contexto, hx, hy, head_r)
        self._desenhar_spikes_cabeca_mangual(contexto, hx, hy, head_r)
        self._desenhar_runas_cabeca_mangual(contexto, hx, hy, head_r)
        self._desenhar_impacto_cabeca_mangual(contexto, hx, hy, head_r)
        self._desenhar_aura_raridade_cabeca_mangual(contexto, hx, hy, head_r, breath, pulso)

    def _desenhar_arma_corrente_mangual(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        larg_base = contexto.larg_base
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale

        cabo_tam = raio_char * 0.65
        corrente_comp = raio_char * 1.50 * anim_scale
        head_r = max(7, int(raio_char * 0.24 * anim_scale))
        num_elos = 7
        pulso = 0.5 + 0.5 * math.sin(tempo / 200)
        breath = 0.5 + 0.5 * math.sin(tempo / 350)

        cabo_ex = cx + math.cos(rad) * cabo_tam
        cabo_ey = cy + math.sin(rad) * cabo_tam
        perp_cx = math.cos(rad + math.pi / 2)
        perp_cy = math.sin(rad + math.pi / 2)
        self._desenhar_cabo_mangual(contexto, cabo_ex, cabo_ey, perp_cx, perp_cy)
        self._desenhar_pivo_mangual(contexto, cabo_ex, cabo_ey)
        chain_pts = self._coletar_pontos_corrente_mangual(contexto, cabo_ex, cabo_ey, corrente_comp, num_elos, perp_cx, perp_cy)
        self._desenhar_elos_mangual(contexto, chain_pts)

        if not chain_pts:
            return

        hx, hy = chain_pts[-1]
        if contexto.atacando and len(chain_pts) >= 3:
            trail_pts = chain_pts[-4:]
            for ti in range(len(trail_pts) - 1):
                t_alpha = int(60 + 80 * (ti / len(trail_pts)))
                t_r = max(2, int(head_r * (0.3 + 0.4 * ti / len(trail_pts))))
                try:
                    ts = self._get_surface(t_r * 2, t_r * 2, pygame.SRCALPHA)
                    pygame.draw.circle(ts, (*contexto.cor, min(255, t_alpha)), (t_r, t_r), t_r)
                    self.tela.blit(ts, (int(trail_pts[ti][0]) - t_r, int(trail_pts[ti][1]) - t_r))
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

        self._desenhar_cabeca_mangual(contexto, hx, hy, head_r, breath, pulso)

    def _coletar_pontos_corrente_meteor(self, contexto, corrente_comp, num_elos, rot_speed):
        chain_pts = []
        for ei in range(num_elos + 1):
            t = ei / num_elos
            base_px = contexto.cx + math.cos(contexto.rad) * corrente_comp * t
            base_py = contexto.cy + math.sin(contexto.rad) * corrente_comp * t
            if contexto.atacando:
                wave = math.sin(t * math.pi * 4 + rot_speed) * contexto.raio_char * 0.08 * (1 - t * 0.3)
            else:
                wave = math.sin(t * math.pi * 2 + contexto.tempo / 200) * contexto.raio_char * 0.05
            perp_x2 = math.cos(contexto.rad + math.pi / 2) * wave
            perp_y2 = math.sin(contexto.rad + math.pi / 2) * wave
            chain_pts.append((base_px + perp_x2, base_py + perp_y2))
        return chain_pts

    def _desenhar_elos_corrente_meteor(self, contexto, chain_pts):
        if len(chain_pts) <= 1:
            return
        for j in range(len(chain_pts) - 1):
            pygame.draw.line(self.tela, (80, 75, 70), (int(chain_pts[j][0]), int(chain_pts[j][1])), (int(chain_pts[j + 1][0]), int(chain_pts[j + 1][1])), max(2, contexto.larg_base - 1))
        for j in range(0, len(chain_pts), 2):
            pygame.draw.circle(self.tela, (100, 95, 85), (int(chain_pts[j][0]), int(chain_pts[j][1])), max(2, contexto.larg_base // 2))

    def _desenhar_cabeca_corrente_meteor(self, contexto, mx, my, head_r, pulso):
        fire_r = int(head_r * (2.2 + 0.5 * pulso))
        try:
            fs = self._get_surface(fire_r * 2, fire_r * 2, pygame.SRCALPHA)
            pygame.draw.circle(fs, (255, 80, 20, int(60 + 40 * pulso)), (fire_r, fire_r), fire_r)
            pygame.draw.circle(fs, (255, 160, 40, int(40 + 30 * pulso)), (fire_r, fire_r), int(fire_r * 0.7))
            self.tela.blit(fs, (int(mx) - fire_r, int(my) - fire_r))
        except Exception as _e:
            _log.debug("Render: %s", _e)  # QC-01
        pygame.draw.circle(self.tela, (40, 35, 30), (int(mx) + 2, int(my) + 2), head_r + 1)
        pygame.draw.circle(self.tela, contexto.cor_escura, (int(mx), int(my)), head_r)
        pygame.draw.circle(self.tela, contexto.cor, (int(mx), int(my)), head_r - 1)
        pygame.draw.circle(self.tela, contexto.cor_clara, (int(mx) - head_r // 3, int(my) - head_r // 3), max(2, head_r // 3))

    def _desenhar_orbitas_corrente_meteor(self, contexto, mx, my, head_r, pulso, rot_speed):
        for fi in range(4):
            f_ang = rot_speed * 2 + fi * math.pi / 2
            f_dist = head_r + head_r * 0.4 * math.sin(contexto.tempo / 80 + fi)
            f_x = mx + math.cos(f_ang) * f_dist
            f_y = my + math.sin(f_ang) * f_dist
            f_size = max(2, int(head_r * 0.35))
            try:
                fs = self._get_surface(f_size * 2, f_size * 2, pygame.SRCALPHA)
                pygame.draw.circle(fs, (255, 120 + int(80 * pulso), 20, int(150 + 50 * pulso)), (f_size, f_size), f_size)
                self.tela.blit(fs, (int(f_x) - f_size, int(f_y) - f_size))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01

    def _desenhar_arma_corrente_meteor(self, contexto):
        corrente_comp = contexto.raio_char * 2.40 * contexto.anim_scale
        head_r = max(6, int(contexto.raio_char * 0.22 * contexto.anim_scale))
        num_elos = 10
        pulso = 0.5 + 0.5 * math.sin(contexto.tempo / 150)
        rot_speed = contexto.tempo / 100
        chain_pts = self._coletar_pontos_corrente_meteor(contexto, corrente_comp, num_elos, rot_speed)
        self._desenhar_elos_corrente_meteor(contexto, chain_pts)
        if not chain_pts:
            return
        mx, my = chain_pts[-1]
        self._desenhar_cabeca_corrente_meteor(contexto, mx, my, head_r, pulso)
        self._desenhar_orbitas_corrente_meteor(contexto, mx, my, head_r, pulso, rot_speed)

    def _desenhar_arma_corrente_kusarigama(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_clara = contexto.cor_clara
        cor_escura = contexto.cor_escura
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale

        comp_total = raio_char * 2.10 * anim_scale
        cabo_len = raio_char * 0.60
        ponta_tam = max(6, int(raio_char * 0.25))

        kama_cabo_x = cx + math.cos(rad) * cabo_len
        kama_cabo_y = cy + math.sin(rad) * cabo_len
        pygame.draw.line(self.tela, (30, 18, 8), (int(cx) + 1, int(cy) + 1), (int(kama_cabo_x) + 1, int(kama_cabo_y) + 1), max(3, larg_base) + 1)
        pygame.draw.line(self.tela, (90, 55, 25), (int(cx), int(cy)), (int(kama_cabo_x), int(kama_cabo_y)), max(3, larg_base))
        kama_len = ponta_tam * 2.5
        curve_ang = rad - math.pi / 2
        ctrl_x = kama_cabo_x + math.cos(curve_ang) * kama_len * 0.5
        ctrl_y = kama_cabo_y + math.sin(curve_ang) * kama_len * 0.5
        hook_x = kama_cabo_x + math.cos(curve_ang) * kama_len
        hook_y = kama_cabo_y + math.sin(curve_ang) * kama_len
        prev = (int(kama_cabo_x), int(kama_cabo_y))
        for seg in range(1, 9):
            t = seg / 8
            bx2 = (1 - t) ** 2 * kama_cabo_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * hook_x
            by2 = (1 - t) ** 2 * kama_cabo_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * hook_y
            pygame.draw.line(self.tela, cor, prev, (int(bx2), int(by2)), max(2, larg_base))
            prev = (int(bx2), int(by2))
        pygame.draw.circle(self.tela, cor_raridade, (int(hook_x), int(hook_y)), max(2, larg_base - 1))
        chain_pts = []
        for i in range(14):
            t = i / 13
            wave = math.sin(t * math.pi * 3 + tempo / 120) * raio_char * 0.12
            px2 = kama_cabo_x + math.cos(rad) * comp_total * t
            py2 = kama_cabo_y + math.sin(rad) * comp_total * t + wave
            chain_pts.append((int(px2), int(py2)))
        if len(chain_pts) > 1:
            try:
                pygame.draw.lines(self.tela, (80, 82, 90), False, chain_pts, max(2, larg_base - 1))
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01
            for j in range(0, len(chain_pts) - 1, 2):
                pygame.draw.circle(self.tela, (60, 62, 72), chain_pts[j], max(2, larg_base // 2))
        if chain_pts:
            ex, ey = chain_pts[-1]
            pygame.draw.circle(self.tela, cor_escura, (ex, ey), ponta_tam + 1)
            pygame.draw.circle(self.tela, cor, (ex, ey), ponta_tam - 1)
            pygame.draw.circle(self.tela, cor_clara, (ex - ponta_tam // 3, ey - ponta_tam // 3), max(1, ponta_tam // 3))

    def _desenhar_arma_corrente_chicote(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        _zw = contexto.zw

        comp_total = raio_char * 2.10 * anim_scale
        cabo_len = raio_char * 0.60
        cabo_ex = cx + math.cos(rad) * cabo_len
        cabo_ey = cy + math.sin(rad) * cabo_len
        pygame.draw.line(self.tela, (20, 10, 4), (int(cx) + 1, int(cy) + 1), (int(cabo_ex) + 1, int(cabo_ey) + 1), max(_zw(3), larg_base) + 2)
        pygame.draw.line(self.tela, (60, 30, 10), (int(cx), int(cy)), (int(cabo_ex), int(cabo_ey)), max(_zw(3), larg_base))
        for fi in range(1, 4):
            ft = fi / 4
            fx = int(cx + (cabo_ex - cx) * ft)
            fy = int(cy + (cabo_ey - cy) * ft)
            perp_x2 = math.cos(rad + math.pi / 2) * (larg_base + 2)
            perp_y2 = math.sin(rad + math.pi / 2) * (larg_base + 2)
            pygame.draw.line(self.tela, (35, 16, 4), (int(fx - perp_x2), int(fy - perp_y2)), (int(fx + perp_x2), int(fy + perp_y2)), 1)
        num_seg = 20
        pts = []
        for i in range(num_seg + 1):
            t = i / num_seg
            amp = raio_char * 0.25 * (1 - t * 0.75)
            wave = math.sin(t * math.pi * 3.5 + tempo / 100) * amp
            px2 = cabo_ex + math.cos(rad) * comp_total * t
            py2 = cabo_ey + math.sin(rad) * comp_total * t
            perp_x2 = math.cos(rad + math.pi / 2) * wave
            perp_y2 = math.sin(rad + math.pi / 2) * wave
            pts.append((int(px2 + perp_x2), int(py2 + perp_y2)))
        for j in range(len(pts) - 1):
            thick = max(1, int(larg_base * (1 - j / num_seg) + 0.5))
            try:
                pygame.draw.line(self.tela, cor, pts[j], pts[j + 1], thick)
            except Exception as _e:
                _log.debug("Render: %s", _e)  # QC-01
        if pts:
            pygame.draw.circle(self.tela, cor_raridade, pts[-1], max(2, larg_base - 1))

    def _desenhar_arma_corrente_padrao(self, contexto):
        cx = contexto.cx
        cy = contexto.cy
        rad = contexto.rad
        cor = contexto.cor
        cor_clara = contexto.cor_clara
        cor_raridade = contexto.cor_raridade
        larg_base = contexto.larg_base
        tempo = contexto.tempo
        raio_char = contexto.raio_char
        anim_scale = contexto.anim_scale
        raridade_norm = contexto.raridade_norm
        _zw = contexto.zw

        comp_total = raio_char * 2.10 * anim_scale
        ponta_tam = max(6, int(raio_char * 0.25))

        pygame.draw.circle(self.tela, (80, 82, 90), (int(cx), int(cy)), larg_base + 2, _zw(2))
        num_elos = 8
        pts = []
        for i in range(num_elos + 1):
            t = i / num_elos
            wave = math.sin(t * math.pi * 2 + tempo / 200) * raio_char * 0.1
            px2 = cx + math.cos(rad) * comp_total * t
            py2 = cy + math.sin(rad) * comp_total * t + wave
            pts.append((int(px2), int(py2)))
        for j in range(len(pts) - 1):
            pygame.draw.line(self.tela, (30, 30, 38), pts[j], pts[j + 1], larg_base + 3)
            pygame.draw.line(self.tela, (90, 92, 105), pts[j], pts[j + 1], larg_base)
            if j % 2 == 0:
                perp_x2 = math.cos(rad + math.pi / 2) * (larg_base + 3)
                perp_y2 = math.sin(rad + math.pi / 2) * (larg_base + 3)
                mx = (pts[j][0] + pts[j + 1][0]) // 2
                my = (pts[j][1] + pts[j + 1][1]) // 2
                pygame.draw.line(self.tela, (55, 56, 65), (int(mx - perp_x2), int(my - perp_y2)), (int(mx + perp_x2), int(my + perp_y2)), 2)
        if pts:
            ex, ey = pts[-1]
            hw = ponta_tam + 2
            hh = int(ponta_tam * 1.4)
            pygame.draw.rect(self.tela, (20, 22, 28), (ex - hw, ey - hh, hw * 2, hh * 2))
            pygame.draw.rect(self.tela, cor, (ex - hw + 1, ey - hh + 1, hw * 2 - 2, hh * 2 - 2), _zw(2))
            pygame.draw.line(self.tela, cor_clara, (ex - hw + 2, ey - hh + 2), (ex - hw // 2, ey - hh // 2), _zw(2))
            if raridade_norm != 'comum':
                pygame.draw.rect(self.tela, cor_raridade, (ex - hw, ey - hh, hw * 2, hh * 2), 2)

    def _desenhar_arma_corrente(self, contexto):
        estilo_norm = contexto.estilo_norm
        if "mangual" in estilo_norm or "flail" in estilo_norm:
            return self._desenhar_arma_corrente_mangual(contexto)
        if "meteor" in estilo_norm:
            return self._desenhar_arma_corrente_meteor(contexto)
        if estilo_norm == "kusarigama":
            return self._desenhar_arma_corrente_kusarigama(contexto)
        if estilo_norm == "chicote":
            return self._desenhar_arma_corrente_chicote(contexto)
        return self._desenhar_arma_corrente_padrao(contexto)

    def _desenhar_arma_fallback(self, contexto):
        cabo_len = contexto.raio_char * 0.55
        lamina_len = contexto.raio_char * 1.20 * contexto.anim_scale

        cabo_end_x = contexto.cx + math.cos(contexto.rad) * cabo_len
        cabo_end_y = contexto.cy + math.sin(contexto.rad) * cabo_len
        lamina_end_x = contexto.cx + math.cos(contexto.rad) * (cabo_len + lamina_len)
        lamina_end_y = contexto.cy + math.sin(contexto.rad) * (cabo_len + lamina_len)

        pygame.draw.line(self.tela, (80, 50, 30), (int(contexto.cx), int(contexto.cy)), (int(cabo_end_x), int(cabo_end_y)), contexto.larg_base)
        pygame.draw.line(self.tela, contexto.cor, (int(cabo_end_x), int(cabo_end_y)), (int(lamina_end_x), int(lamina_end_y)), contexto.larg_base)

    def _desenhar_arma_inline_legacy(self, arma, centro, angulo, tam_char, raio_char, anim_scale=1.0):
        """Compat wrapper para chamadas antigas; a fonte canonica agora e `desenhar_arma`."""
        return self.desenhar_arma(arma, centro, angulo, tam_char, raio_char, anim_scale)

    def desenhar_arma(self, arma, centro, angulo, tam_char, raio_char, anim_scale=1.0):
        """Dispatcher enxuto e fonte canonica do renderer de armas."""
        contexto = self._criar_contexto_render_arma(arma, centro, angulo, tam_char, raio_char, anim_scale)

        if contexto.tipo_norm == "reta":
            return self._desenhar_arma_reta(contexto)
        if contexto.tipo_norm == "dupla":
            return self._desenhar_arma_dupla(contexto)
        if contexto.tipo_norm == "corrente":
            return self._desenhar_arma_corrente(contexto)
        if contexto.tipo_norm == "arremesso":
            return self._desenhar_arma_arremesso(contexto)
        if contexto.tipo_norm == "arco":
            return self._desenhar_arma_arco(contexto)
        if contexto.tipo_norm == "orbital":
            return self._desenhar_arma_orbital(contexto)
        if contexto.tipo_norm == "magica":
            return self._desenhar_arma_magica(contexto)
        if contexto.tipo_norm == "transformavel":
            return self._desenhar_arma_transformavel(contexto)
        return self._desenhar_arma_fallback(contexto)

    def _criar_contexto_hitbox_debug(self, lutador):
        if getattr(lutador, "morto", False):
            return None

        hitbox = sistema_hitbox.calcular_hitbox_arma(lutador)
        if not hitbox:
            return None

        cx_screen, cy_screen = self.cam.converter(hitbox.centro[0], hitbox.centro[1])
        off_y = self.cam.converter_tam(getattr(lutador, "z", 0.0) * PPM)
        cy_screen -= off_y
        team_id = getattr(lutador, "team_id", 0)
        return HitboxDebugRenderContext(
            lutador=lutador,
            hitbox=hitbox,
            cor_debug=(*CORES_TIME_RENDER[team_id % len(CORES_TIME_RENDER)], 128),
            cx_screen=cx_screen,
            cy_screen=cy_screen,
            off_y=off_y,
            alcance_screen=self.cam.converter_tam(hitbox.alcance),
        )

    def _desenhar_label_hitbox_debug(self, surface, fonte, contexto, texto, cor):
        txt = fonte.render(texto, True, cor)
        surface.blit(txt, (contexto.cx_screen - 50, contexto.cy_screen - contexto.alcance_screen - 20))

    def _desenhar_hitbox_corrente_debug(self, surface, fonte, contexto):
        cor_arco = (255, 128, 0, 200) if contexto.hitbox.ativo else (100, 100, 100, 100)
        pontos_screen = []
        for ponto in contexto.hitbox.pontos:
            ps = self.cam.converter(ponto[0], ponto[1])
            pontos_screen.append((ps[0], ps[1] - contexto.off_y))
        if len(pontos_screen) > 1:
            for i in range(len(pontos_screen) - 1):
                pygame.draw.line(surface, cor_arco, pontos_screen[i], pontos_screen[i + 1], 3)

        rad_bola = math.radians(contexto.hitbox.angulo)
        bola_x = contexto.hitbox.centro[0] + math.cos(rad_bola) * contexto.hitbox.alcance
        bola_y = contexto.hitbox.centro[1] + math.sin(rad_bola) * contexto.hitbox.alcance
        bola_screen = self.cam.converter(bola_x, bola_y)
        bola_screen = (bola_screen[0], bola_screen[1] - contexto.off_y)
        pygame.draw.circle(surface, (255, 50, 50, 255), bola_screen, 10, 3)
        pygame.draw.line(surface, (255, 128, 0, 100), (contexto.cx_screen, contexto.cy_screen), bola_screen, 1)
        alcance_min_screen = self.cam.converter_tam(contexto.hitbox.alcance * 0.4)
        pygame.draw.circle(surface, (100, 100, 100, 50), (contexto.cx_screen, contexto.cy_screen), alcance_min_screen, 1)

        label = f"{contexto.lutador.dados.nome}: Corrente"
        if contexto.hitbox.ativo:
            label += f" [GIRANDO t={contexto.lutador.timer_animacao:.2f}]"
        self._desenhar_label_hitbox_debug(surface, fonte, contexto, label, BRANCO)

    def _desenhar_hitbox_ranged_debug(self, surface, fonte, contexto):
        cor_traj = (0, 200, 255, 150) if contexto.hitbox.ativo else (100, 100, 100, 80)
        if len(contexto.hitbox.pontos) > 2:
            for ponto in contexto.hitbox.pontos:
                ps = self.cam.converter(ponto[0], ponto[1])
                ps = (ps[0], ps[1] - contexto.off_y)
                pygame.draw.line(surface, cor_traj, (contexto.cx_screen, contexto.cy_screen), ps, 1)
                pygame.draw.circle(surface, cor_traj, ps, 5)
        elif len(contexto.hitbox.pontos) == 2:
            p1_screen = self.cam.converter(contexto.hitbox.pontos[0][0], contexto.hitbox.pontos[0][1])
            p2_screen = self.cam.converter(contexto.hitbox.pontos[1][0], contexto.hitbox.pontos[1][1])
            p1_screen = (p1_screen[0], p1_screen[1] - contexto.off_y)
            p2_screen = (p2_screen[0], p2_screen[1] - contexto.off_y)
            pygame.draw.line(surface, cor_traj, p1_screen, p2_screen, 2)
            pygame.draw.circle(surface, (255, 100, 100), p2_screen, 6)

        label = f"{contexto.lutador.dados.nome}: {contexto.hitbox.tipo} [RANGED]"
        if contexto.hitbox.ativo:
            label += " DISPARANDO!"
        self._desenhar_label_hitbox_debug(surface, fonte, contexto, label, (0, 200, 255))

    def _desenhar_hitbox_lamina_debug(self, surface, fonte, contexto):
        p1_screen = self.cam.converter(contexto.hitbox.pontos[0][0], contexto.hitbox.pontos[0][1])
        p2_screen = self.cam.converter(contexto.hitbox.pontos[1][0], contexto.hitbox.pontos[1][1])
        p1_screen = (p1_screen[0], p1_screen[1] - contexto.off_y)
        p2_screen = (p2_screen[0], p2_screen[1] - contexto.off_y)
        cor_linha = (255, 0, 0, 200) if contexto.hitbox.ativo else (100, 100, 100, 100)
        pygame.draw.line(surface, cor_linha, p1_screen, p2_screen, 4)
        pygame.draw.circle(surface, (255, 255, 0), p1_screen, 5)
        pygame.draw.circle(surface, (255, 0, 0), p2_screen, 5)

        label = f"{contexto.lutador.dados.nome}: {contexto.hitbox.tipo}"
        if contexto.hitbox.ativo:
            label += f" [ATACANDO t={contexto.lutador.timer_animacao:.2f}]"
        self._desenhar_label_hitbox_debug(surface, fonte, contexto, label, BRANCO)

    def _desenhar_hitbox_area_debug(self, surface, contexto):
        rad = math.radians(contexto.hitbox.angulo)
        rad_min = rad - math.radians(contexto.hitbox.largura_angular / 2)
        rad_max = rad + math.radians(contexto.hitbox.largura_angular / 2)
        fx = contexto.cx_screen + math.cos(rad) * contexto.alcance_screen
        fy = contexto.cy_screen + math.sin(rad) * contexto.alcance_screen
        pygame.draw.line(surface, (*contexto.cor_debug[:3], 150), (contexto.cx_screen, contexto.cy_screen), (int(fx), int(fy)), 2)
        fx_min = contexto.cx_screen + math.cos(rad_min) * contexto.alcance_screen
        fy_min = contexto.cy_screen + math.sin(rad_min) * contexto.alcance_screen
        fx_max = contexto.cx_screen + math.cos(rad_max) * contexto.alcance_screen
        fy_max = contexto.cy_screen + math.sin(rad_max) * contexto.alcance_screen
        pygame.draw.line(surface, (*contexto.cor_debug[:3], 100), (contexto.cx_screen, contexto.cy_screen), (int(fx_min), int(fy_min)), 1)
        pygame.draw.line(surface, (*contexto.cor_debug[:3], 100), (contexto.cx_screen, contexto.cy_screen), (int(fx_max), int(fy_max)), 1)

    def _desenhar_hitbox_lutador_debug(self, contexto, fonte):
        s = self._get_surface(self.screen_width, self.screen_height, pygame.SRCALPHA)
        pygame.draw.circle(s, (*contexto.cor_debug[:3], 30), (contexto.cx_screen, contexto.cy_screen), contexto.alcance_screen, 2)

        if contexto.hitbox.pontos:
            if contexto.hitbox.tipo == "Corrente":
                self._desenhar_hitbox_corrente_debug(s, fonte, contexto)
            elif contexto.hitbox.tipo in ["Arremesso", "Arco"]:
                self._desenhar_hitbox_ranged_debug(s, fonte, contexto)
            else:
                self._desenhar_hitbox_lamina_debug(s, fonte, contexto)
        else:
            self._desenhar_hitbox_area_debug(s, contexto)

        self.tela.blit(s, (0, 0))

    def desenhar_hitbox_debug(self):
        """Desenha visualizaÃ§Ã£o de debug das hitboxes"""
        _ = get_debug_visual()
        fonte = self._get_font("Arial", 10)

        for lutador in self.fighters:
            contexto = self._criar_contexto_hitbox_debug(lutador)
            if contexto is not None:
                self._desenhar_hitbox_lutador_debug(contexto, fonte)

        self.desenhar_painel_debug()

    
    def desenhar_painel_debug(self):
        """Desenha painel com info de debug"""
        x, y = self.screen_width - 300, 80
        w, h = 280, 250
        
        s = self._get_surface(w, h, pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (255, 100, 100), (x, y, w, h), 2)
        
        fonte = self._get_font("Arial", 10)
        fonte_bold = self._get_font("Arial", 11, bold=True)
        
        self.tela.blit(fonte_bold.render("DEBUG HITBOX [H para toggle]", True, (255, 100, 100)), (x + 10, y + 5))
        
        # DistÃ¢ncia entre lutadores (mostra entre os 2 primeiros ou min/max em multi)
        if len(self.fighters) == 2:
            dist = math.hypot(self.fighters[1].pos[0] - self.fighters[0].pos[0], self.fighters[1].pos[1] - self.fighters[0].pos[1])
            self.tela.blit(fonte_bold.render(f"DistÃ¢ncia: {dist:.2f}m", True, (200, 200, 255)), (x + 10, y + 22))
        else:
            self.tela.blit(fonte_bold.render(f"Lutadores: {len(self.fighters)}", True, (200, 200, 255)), (x + 10, y + 22))
        
        off = 40
        for idx, p in enumerate(self.fighters):
            cor = CORES_TIME_RENDER[p.team_id % len(CORES_TIME_RENDER)]
            self.tela.blit(fonte_bold.render(f"=== {p.dados.nome} ===", True, cor), (x + 10, y + off))
            off += 14
            
            arma = p.dados.arma_obj
            if arma:
                self.tela.blit(fonte.render(f"Arma: {arma.nome} ({arma.tipo})", True, BRANCO), (x + 10, y + off))
                off += 11
            
            # Status de ataque
            atk_cor = (0, 255, 0) if p.atacando else (150, 150, 150)
            self.tela.blit(fonte.render(f"Atacando: {p.atacando} Timer: {p.timer_animacao:.3f}", True, atk_cor), (x + 10, y + off))
            off += 11
            self.tela.blit(fonte.render(f"Alcance IA: {p.alcance_ideal:.2f}m CD: {p.cooldown_ataque:.2f}", True, BRANCO), (x + 10, y + off))
            off += 11
            acao_atual = p.brain.acao_atual if p.brain is not None else "MANUAL"
            self.tela.blit(fonte.render(f"AÃ§Ã£o: {acao_atual}", True, BRANCO), (x + 10, y + off))
            off += 16


    def _agrupar_times_hud_multi(self):
        times = {}
        for fighter in self.fighters:
            times.setdefault(fighter.team_id, []).append(fighter)
        return times

    def _criar_layout_hud_multi(self):
        times = self._agrupar_times_hud_multi()
        num_times = len(times)
        return HudMultiLayout(
            times=times,
            num_times=num_times,
            bar_w=min(200, (self.screen_width - 40) // max(num_times, 1) - 10),
            bar_h=16,
            mana_h=6,
            nome_h=14,
            slot_h=16 + 6 + 14 + 8,
        )

    def _calcular_base_x_time_hud_multi(self, layout, team_index):
        if team_index < (layout.num_times + 1) // 2:
            return 15 + team_index * (layout.bar_w + 15)
        right_idx = team_index - (layout.num_times + 1) // 2
        return self.screen_width - (layout.bar_w + 15) * (right_idx + 1)

    def _criar_contexto_time_hud_multi(self, layout, team_index, team_id, members):
        return HudMultiTeamLayout(
            team_id=team_id,
            members=members,
            team_index=team_index,
            base_x=self._calcular_base_x_time_hud_multi(layout, team_index),
            cor_time=CORES_TIME_RENDER[team_id % len(CORES_TIME_RENDER)],
            layout=layout,
        )

    def _desenhar_header_time_hud_multi(self, contexto_time):
        ft_team = self._get_font("Arial", 12, bold=True)
        team_label = ft_team.render(f"TIME {contexto_time.team_id + 1}", True, contexto_time.cor_time)
        self.tela.blit(team_label, (contexto_time.base_x, 5))

    def _desenhar_barras_slot_hud_multi(self, contexto_time, fighter, y, vida_vis):
        y_bar = y + contexto_time.layout.nome_h
        pygame.draw.rect(self.tela, (20, 20, 20), (contexto_time.base_x, y_bar, contexto_time.layout.bar_w, contexto_time.layout.bar_h))
        pct_vis = max(0, vida_vis / fighter.vida_max) if fighter.vida_max > 0 else 0
        pct_real = max(0, fighter.vida / fighter.vida_max) if fighter.vida_max > 0 else 0
        if pct_vis > pct_real:
            pygame.draw.rect(self.tela, BRANCO, (contexto_time.base_x, y_bar, int(contexto_time.layout.bar_w * pct_vis), contexto_time.layout.bar_h))
        cor_hp = (100, 100, 100) if fighter.morto else contexto_time.cor_time
        pygame.draw.rect(self.tela, cor_hp, (contexto_time.base_x, y_bar, int(contexto_time.layout.bar_w * pct_real), contexto_time.layout.bar_h))
        pygame.draw.rect(self.tela, BRANCO, (contexto_time.base_x, y_bar, contexto_time.layout.bar_w, contexto_time.layout.bar_h), 1)
        y_mana = y_bar + contexto_time.layout.bar_h + 2
        pct_mana = max(0, fighter.mana / fighter.mana_max) if fighter.mana_max > 0 else 0
        pygame.draw.rect(self.tela, (20, 20, 20), (contexto_time.base_x, y_mana, contexto_time.layout.bar_w, contexto_time.layout.mana_h))
        pygame.draw.rect(self.tela, AZUL_MANA, (contexto_time.base_x, y_mana, int(contexto_time.layout.bar_w * pct_mana), contexto_time.layout.mana_h))

    def _obter_vida_visual_hud_multi(self, fighter):
        vida_visual = getattr(self, "vida_visual", {})
        try:
            return vida_visual.get(fighter, fighter.vida)
        except TypeError:
            return fighter.vida

    def _desenhar_slot_lutador_hud_multi(self, contexto_time, fighter, member_index):
        y = 20 + member_index * contexto_time.layout.slot_h
        vida_vis = self._obter_vida_visual_hud_multi(fighter)
        ft_nome = self._get_font("Arial", 11, bold=True)
        cor_nome = (150, 150, 150) if fighter.morto else BRANCO
        self.tela.blit(ft_nome.render(fighter.dados.nome, True, cor_nome), (contexto_time.base_x + 2, y))
        self._desenhar_badges_estado(fighter, contexto_time.base_x + contexto_time.layout.bar_w - 2, y, align_right=True, compact=True, max_badges=1)
        self._desenhar_barras_slot_hud_multi(contexto_time, fighter, y, vida_vis)

    def _desenhar_hud_multi(self):
        """v13.0: HUD compacto para multi-fighter - barras empilhadas por time."""
        layout = self._criar_layout_hud_multi()
        for team_index, (team_id, members) in enumerate(sorted(layout.times.items())):
            contexto_time = self._criar_contexto_time_hud_multi(layout, team_index, team_id, members)
            self._desenhar_header_time_hud_multi(contexto_time)
            for member_index, fighter in enumerate(members):
                self._desenhar_slot_lutador_hud_multi(contexto_time, fighter, member_index)

    def desenhar_barras(self, l, x, y, cor, vida_vis):
        # Ajusta largura das barras baseado no modo (menor em portrait)
        w = 200 if self.portrait_mode else 300
        h = 25 if self.portrait_mode else 30
        pygame.draw.rect(self.tela, (20,20,20), (x, y, w, h))
        pct_vis = max(0, vida_vis / max(l.vida_max, 1)); pygame.draw.rect(self.tela, BRANCO, (x, y, int(w * pct_vis), h))
        pct_real = max(0, l.vida / max(l.vida_max, 1)); pygame.draw.rect(self.tela, cor, (x, y, int(w * pct_real), h))
        pygame.draw.rect(self.tela, BRANCO, (x, y, w, h), 2)
        pct_mana = max(0, l.mana / max(l.mana_max, 1))
        pygame.draw.rect(self.tela, (20, 20, 20), (x, y + h + 5, w, 10))
        pygame.draw.rect(self.tela, AZUL_MANA, (x, y + h + 5, int(w * pct_mana), 10))
        ft_size = 14 if self.portrait_mode else 16
        ft = self._get_font("Arial", ft_size, bold=True)
        self.tela.blit(ft.render(f"{l.dados.nome}", True, BRANCO), (x+10, y+5))
        self._desenhar_badges_estado(l, x + w - 8, y + 4, align_right=True, compact=self.portrait_mode, max_badges=2)


    def desenhar_controles(self):
        x, y = 20, 90 
        w, h = 220, 210
        s = self._get_surface(w, h, pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (100, 100, 100), (x, y, w, h), 1)
        fonte_tit = self._get_font("Arial", 14, bold=True); fonte_txt = self._get_font("Arial", 12)
        self.tela.blit(fonte_tit.render("COMANDOS", True, COR_TEXTO_TITULO), (x + 10, y + 10))
        comandos = [("WASD / Setas", "Mover Camera"), ("Scroll", "Zoom"), ("1/2/3", "Modos Cam"), ("SPACE", "Pause"), ("T/F", "Speed"), ("TAB", "Dados"), ("G", "HUD"), ("H", "Debug Hitbox"), ("R", "Reset"), ("ESC", "Sair")]
        off_y = 35
        for t, a in comandos:
            self.tela.blit(fonte_txt.render(t, True, BRANCO), (x + 10, y + off_y))
            self.tela.blit(fonte_txt.render(a, True, COR_TEXTO_INFO), (x + 110, y + off_y))
            off_y += 16


    def desenhar_analise(self):
        s = pygame.Surface((300, self.screen_height)); s.fill(COR_UI_BG); self.tela.blit(s, (0,0))
        ft = self._get_font("Consolas", 14)
        lines = [
            "--- ANÃLISE ---", f"FPS: {int(self.clock.get_fps())}", f"Cam: {self.cam.modo}", "",
        ]
        # v13.0: Dinamicamente mostra stats de todos os lutadores
        for f in self.fighters:
            team_label = f"T{f.team_id}" if getattr(self, 'modo_multi', False) else ""
            lines.append(f"--- {f.dados.nome} {team_label} ---")
            lines.append(f"HP: {int(f.vida)}  Mana: {int(f.mana)}  Est: {int(f.estamina)}")
            acao = f.brain.acao_atual if f.brain else "MANUAL"
            lines.append(f"Action: {acao}  Skill: {f.skill_arma_nome}")
            if f.morto:
                lines.append("[MORTO]")
            lines.append("")
        for i, l in enumerate(lines):
            c = COR_TEXTO_TITULO if "---" in l else COR_TEXTO_INFO
            self.tela.blit(ft.render(l, True, c), (20, 20 + i*20))


    def desenhar_pause(self):
        ft = self._get_font("Impact", 60); txt = ft.render("PAUSE", True, BRANCO)
        self.tela.blit(txt, (self.screen_width//2 - txt.get_width()//2, self.screen_height//2 - 50))


    def desenhar_vitoria(self):
        s = self._get_surface(self.screen_width, self.screen_height, pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (0,0))
        ft = self._get_font("Impact", 80); txt = ft.render(f"{self.vencedor} VENCEU!", True, COR_TEXTO_TITULO)
        self.tela.blit(txt, (self.screen_width//2 - txt.get_width()//2, self.screen_height//2 - 100))
        ft2 = self._get_font("Arial", 24); msg = ft2.render("Pressione 'R' para Reiniciar ou 'ESC' para Sair", True, COR_TEXTO_INFO)
        self.tela.blit(msg, (self.screen_width//2 - msg.get_width()//2, self.screen_height//2 + 20))





