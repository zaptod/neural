"""Auto-generated mixin Ã¢â‚¬â€ gerado por scripts/split_simulacao.py (arquivado em _archive/scripts/)"""
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
from efeitos import (Particula, FloatingText, Decal, Shockwave, Camera, EncantamentoEffect,
                     ImpactFlash, MagicClash, BlockEffect, DashTrail, HitSpark,
                     MovementAnimationManager, MovementType,  # v8.0 Movement Animations
                     AttackAnimationManager, calcular_knockback_com_forca, get_impact_tier,  # v8.0 Attack Animations
                     MagicVFXManager, ELEMENT_PALETTES, get_element_from_skill)  # v11.0 Magic VFX
from efeitos.audio import AudioManager  # v10.0 Sistema de Ãudio
from nucleo.entities import Lutador
from nucleo.skills import get_skill_classification
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
    texto = str(valor or "").replace("→", " ")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.lower().split())


class SimuladorRenderer:
    """Mixin de renderizaÃ§Ã£o: desenho de lutadores, armas, UI e debug."""

    # Ã¢â€â‚¬Ã¢â€â‚¬ FONT CACHE Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ evita criar fontes a cada frame (perf-fix)
    _font_cache = {}

    @classmethod
    def _get_font(cls, name, size, bold=False):
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
            "barreira divina": {"variante": "barreira_divina", "familia": "buff"},
            "escudo de brasas": {"variante": "escudo_brasas", "familia": "buff"},
            "absorcao do vazio": {"variante": "absorcao_vazio", "familia": "buff"},
            "cura maior": {"variante": "cura_maior", "familia": "buff"},
            "purificar": {"variante": "purificar", "familia": "buff"},
            "sobrecarga": {"variante": "sobrecarga", "familia": "buff"},
            "amplificar magia": {"variante": "amplificar_magia", "familia": "buff"},
            "conjuracao perfeita": {"variante": "conjuracao_perfeita", "familia": "buff"},
            "fenix": {"variante": "fenix", "familia": "summon"},
            "invocacao: espirito": {"variante": "espirito_arcano", "familia": "summon"},
            "portal do vazio": {"variante": "portal_vazio", "familia": "summon"},
            "anomalia espacial": {"variante": "anomalia_espacial", "familia": "summon"},
            "muralha de gelo": {"variante": "muralha_gelo", "familia": "trap"},
            "espelho de gelo": {"variante": "espelho_gelo", "familia": "trap"},
            "prisao de luz": {"variante": "prisao_luz", "familia": "trap"},
            "armadilha incendiaria": {"variante": "armadilha_incendiaria", "familia": "trap"},
            "armadilha eletrica": {"variante": "armadilha_eletrica", "familia": "trap"},
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

    def _desenhar_buffs_lutador(self, lutador, centro, raio, pulse_time):
        buffs = [buff for buff in getattr(lutador, "buffs_ativos", []) if getattr(buff, "ativo", True)]
        if not buffs:
            return

        for idx, buff in enumerate(buffs[:3]):
            classe = self._resolver_classe_magia(buff)
            perfil = self._perfil_visual_magia(classe)
            assinatura = self._assinatura_magia_especifica(buff, tipo="BUFF")
            elemento = self._detectar_elemento_visual(getattr(buff, "nome", ""), "BUFF", getattr(buff, "elemento", None))
            paleta = self._paleta_magica(elemento, getattr(buff, "cor", None))
            progresso = max(0.0, min(1.0, getattr(buff, "vida", 0.0) / max(getattr(buff, "duracao", 1.0), 0.001)))
            aura_r = int(raio * (1.25 + idx * 0.2))

            self._desenhar_glow_circular(centro[0], centro[1], int(aura_r * (0.95 + perfil["suavidade"] * 0.2)), paleta["outer"][0], 28 + 22 * progresso, 3)
            self._desenhar_motivo_circular_magia(centro[0], centro[1], aura_r, paleta, perfil, pulse_time + idx * 0.35, 0.48 + progresso * 0.25)

            variante = assinatura.get("variante", "")
            if getattr(buff, "escudo", 0) > 0:
                escudo_pct = max(0.0, min(1.0, getattr(buff, "escudo_atual", buff.escudo) / max(buff.escudo, 0.001)))
                shell = self._pontos_poligono_regular(centro[0], centro[1], aura_r * 1.08, 6, pulse_time * 0.22 + idx * 0.3)
                pygame.draw.polygon(
                    self.tela,
                    self._cor_com_alpha(paleta["mid"][0], 90 + 65 * escudo_pct),
                    [(int(px), int(py)) for px, py in shell],
                    max(1, int(2 + escudo_pct * 2)),
                )

            if variante == "escudo_arcano":
                self._desenhar_sigilo_magico(centro[0], centro[1], int(aura_r * 0.88), paleta, pulse_time * 0.8, 0.72)
                self._desenhar_sigilo_magico(centro[0], centro[1], int(aura_r * 0.58), paleta, -pulse_time * 0.95, 0.45)
            elif variante == "barreira_divina":
                self._desenhar_arco_magico(centro[0], centro[1], int(aura_r * 1.05), paleta["spark"], 145, math.pi * 1.05, math.pi * 1.95, 3)
                pygame.draw.line(self.tela, paleta["core"], (int(centro[0]), int(centro[1] - aura_r * 0.7)), (int(centro[0]), int(centro[1] + aura_r * 0.7)), 1)
            elif variante == "escudo_brasas":
                for off in (0.0, 2.09, 4.18):
                    ex = centro[0] + math.cos(pulse_time * 2.6 + off) * aura_r * 0.92
                    ey = centro[1] + math.sin(pulse_time * 2.6 + off) * aura_r * 0.92
                    pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["mid"][1], 150), (int(ex), int(ey)), max(2, int(raio * 0.16)))
            elif variante == "absorcao_vazio":
                pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 170), (int(centro[0]), int(centro[1])), max(2, int(aura_r * 0.54)))
                for side in (-1, 1):
                    self._desenhar_arco_magico(centro[0], centro[1], int(aura_r * 0.96), paleta["mid"][0], 105, pulse_time * side, pulse_time * side + math.pi * 0.8, 2)
            elif variante == "cura_maior":
                pygame.draw.line(self.tela, paleta["core"], (int(centro[0] - aura_r * 0.28), int(centro[1])), (int(centro[0] + aura_r * 0.28), int(centro[1])), 2)
                pygame.draw.line(self.tela, paleta["core"], (int(centro[0]), int(centro[1] - aura_r * 0.28)), (int(centro[0]), int(centro[1] + aura_r * 0.28)), 2)
            elif variante == "purificar":
                for fator in (0.45, 0.72, 1.0):
                    pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["spark"], 85), (int(centro[0]), int(centro[1])), max(2, int(aura_r * fator)), 1)
            elif variante == "sobrecarga":
                for ang in (pulse_time * 8.0, pulse_time * 8.0 + math.pi):
                    ex = centro[0] + math.cos(ang) * aura_r * 1.02
                    ey = centro[1] + math.sin(ang) * aura_r * 1.02
                    zig = self._gerar_linha_zigzag(centro[0], centro[1], ex, ey, aura_r * 0.12, 4, pulse_time * 14.0)
                    pygame.draw.lines(self.tela, paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)
            elif variante in {"amplificar_magia", "conjuracao_perfeita"}:
                for i in range(4):
                    ang = pulse_time * 0.5 + i * (math.pi / 2)
                    ponta = (centro[0] + math.cos(ang) * aura_r * 1.08, centro[1] + math.sin(ang) * aura_r * 1.08)
                    base = (centro[0] + math.cos(ang) * aura_r * 0.66, centro[1] + math.sin(ang) * aura_r * 0.66)
                    lat_a = (base[0] + math.cos(ang + math.pi / 2) * aura_r * 0.12, base[1] + math.sin(ang + math.pi / 2) * aura_r * 0.12)
                    lat_b = (base[0] + math.cos(ang - math.pi / 2) * aura_r * 0.12, base[1] + math.sin(ang - math.pi / 2) * aura_r * 0.12)
                    pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], 125), [(int(ponta[0]), int(ponta[1])), (int(lat_a[0]), int(lat_a[1])), (int(lat_b[0]), int(lat_b[1]))])

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

    def _desenhar_summon_magico(self, summon, pulse_time):
        sx, sy = self.cam.converter(summon.x * PPM, summon.y * PPM)
        raio = self.cam.converter_tam(0.8 * PPM)
        classe = self._resolver_classe_magia(summon)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(summon, tipo="SUMMON")
        elemento = self._detectar_elemento_visual(getattr(summon, "nome", ""), "SUMMON", getattr(summon, "elemento", None))
        paleta = self._paleta_magica(elemento, getattr(summon, "cor", None))
        centro = (sx, sy)
        base_r = max(8, int(raio * 1.55))

        self._desenhar_motivo_circular_magia(centro[0], centro[1] + raio * 0.18, int(base_r * 0.9), paleta, perfil, pulse_time, 0.75)
        pygame.draw.ellipse(self.tela, (30, 30, 30), (sx - raio, sy + raio // 2, raio * 2, raio // 2))
        self._desenhar_glow_circular(centro[0], centro[1], int(raio * 1.9), paleta["outer"][0], 58, 3)

        if getattr(summon, "flash_timer", 0) > 0:
            flash_cor = getattr(summon, "flash_cor", (255, 255, 255))
            flash_alpha = int(180 * min(1.0, summon.flash_timer / 0.3))
            sf = self._get_surface(int(raio * 3), int(raio * 3), pygame.SRCALPHA)
            pygame.draw.circle(sf, (*flash_cor, flash_alpha), (sf.get_width() // 2, sf.get_height() // 2), int(raio * 1.15))
            self.tela.blit(sf, (sx - sf.get_width() // 2, sy - sf.get_height() // 2))

        variante = assinatura.get("variante", "")
        if variante == "fenix":
            corpo = [(sx, sy - raio * 1.1), (sx + raio * 0.45, sy), (sx, sy + raio * 0.75), (sx - raio * 0.45, sy)]
            asa_esq = [(sx - raio * 0.15, sy - raio * 0.2), (sx - raio * 1.25, sy - raio * 0.62), (sx - raio * 0.6, sy + raio * 0.15)]
            asa_dir = [(sx + raio * 0.15, sy - raio * 0.2), (sx + raio * 1.25, sy - raio * 0.62), (sx + raio * 0.6, sy + raio * 0.15)]
            cauda = [(sx, sy + raio * 0.5), (sx - raio * 0.28, sy + raio * 1.35), (sx + raio * 0.28, sy + raio * 1.35)]
            pygame.draw.polygon(self.tela, paleta["mid"][1], [(int(x), int(y)) for x, y in asa_esq])
            pygame.draw.polygon(self.tela, paleta["mid"][1], [(int(x), int(y)) for x, y in asa_dir])
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in corpo])
            pygame.draw.polygon(self.tela, paleta["spark"], [(int(x), int(y)) for x, y in cauda])
            if getattr(summon, "revive_count", 0) > 0:
                self._desenhar_arco_magico(sx, sy - raio * 0.2, int(raio * 1.05), paleta["spark"], 120, math.pi * 1.12, math.pi * 1.88, 2)
        elif variante == "espirito_arcano":
            fantasma = [(sx, sy - raio * 1.1), (sx + raio * 0.62, sy - raio * 0.18), (sx + raio * 0.42, sy + raio * 0.9), (sx, sy + raio * 0.52), (sx - raio * 0.42, sy + raio * 0.9), (sx - raio * 0.62, sy - raio * 0.18)]
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], 180), [(int(x), int(y)) for x, y in fantasma])
            self._desenhar_sigilo_magico(sx, sy, int(raio * 0.82), paleta, pulse_time, 0.55)
        elif variante in {"portal_vazio", "anomalia_espacial"}:
            pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 210), (int(sx), int(sy)), max(2, int(raio * 0.95)))
            for i in range(3 if variante == "portal_vazio" else 5):
                ang = pulse_time * 0.36 + i * (math.pi * 2 / (3 if variante == "portal_vazio" else 5))
                ex = sx + math.cos(ang) * raio * 1.18
                ey = sy + math.sin(ang) * raio * 1.18
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["mid"][1], 110), (int(ex), int(ey)), (int(sx), int(sy)), 1 if variante == "portal_vazio" else 2)
            self._desenhar_motivo_circular_magia(sx, sy, int(raio * 1.2), paleta, perfil, pulse_time, 0.82)
        else:
            pygame.draw.circle(self.tela, summon.cor, (int(sx), int(sy)), int(raio))
            pygame.draw.circle(self.tela, tuple(min(255, c + 50) for c in summon.cor), (int(sx), int(sy)), int(raio * 0.7))

        pygame.draw.circle(self.tela, BRANCO, (int(sx), int(sy)), max(1, int(raio * 0.28)))
        if summon.alvo:
            ang_rad = math.radians(summon.angulo)
            eye_dist = raio * 0.45
            eye_x = int(sx + math.cos(ang_rad) * eye_dist)
            eye_y = int(sy + math.sin(ang_rad) * eye_dist)
            pygame.draw.circle(self.tela, (255, 255, 200), (eye_x, eye_y), max(1, int(raio * 0.18)))

        vida_pct = summon.vida / max(summon.vida_max, 1)
        barra_w = raio * 2
        pygame.draw.rect(self.tela, (50, 50, 50), (sx - raio, sy - raio - 10, barra_w, 5))
        cor_vida = (int(255 * (1 - vida_pct)), int(255 * vida_pct), 50) if vida_pct < 0.5 else summon.cor
        pygame.draw.rect(self.tela, cor_vida, (sx - raio, sy - raio - 10, barra_w * vida_pct, 5))
        font = self._get_font(None, 16)
        nome_txt = font.render(summon.nome, True, summon.cor)
        self.tela.blit(nome_txt, (sx - nome_txt.get_width() // 2, sy - raio - 22))

    def _desenhar_trap_magica(self, trap, pulse_time):
        tx, ty = self.cam.converter(trap.x * PPM, trap.y * PPM)
        traio = self.cam.converter_tam(trap.raio * PPM)
        classe = self._resolver_classe_magia(trap)
        perfil = self._perfil_visual_magia(classe)
        assinatura = self._assinatura_magia_especifica(trap, tipo="TRAP")
        elemento = self._detectar_elemento_visual(getattr(trap, "nome", ""), "TRAP", getattr(trap, "elemento", None))
        paleta = self._paleta_magica(elemento, getattr(trap, "cor", None))

        if getattr(trap, "flash_timer", 0) > 0:
            flash_cor = getattr(trap, 'flash_cor', (255, 255, 255))
            flash_alpha = int(200 * min(1.0, trap.flash_timer / 0.15))
            tf4 = max(1, int(traio * 4))
            s_flash = self._get_surface(tf4, tf4, pygame.SRCALPHA)
            pygame.draw.circle(s_flash, (*flash_cor, min(255, flash_alpha)), (tf4 // 2, tf4 // 2), int(traio * 1.5))
            self.tela.blit(s_flash, (tx - tf4 // 2, ty - tf4 // 2))

        variante = assinatura.get("variante", "")
        if trap.bloqueia_movimento:
            vida_pct = trap.vida / trap.vida_max if trap.vida_max > 0 else 1
            shell = self._pontos_poligono_regular(tx, ty, traio, 6, getattr(trap, "angulo", 0) + pulse_time * 0.08)
            s_wall = self._get_surface(max(1, int(traio * 2 + 12)), max(1, int(traio * 2 + 12)), pygame.SRCALPHA)
            pts_local = [(p[0] - tx + s_wall.get_width() // 2, p[1] - ty + s_wall.get_height() // 2) for p in shell]
            pygame.draw.polygon(s_wall, (*trap.cor, int(170 * vida_pct + 50)), pts_local)
            self.tela.blit(s_wall, (tx - s_wall.get_width() // 2, ty - s_wall.get_height() // 2))
            pygame.draw.polygon(self.tela, BRANCO, [(int(px), int(py)) for px, py in shell], 2)
            self._desenhar_motivo_circular_magia(tx, ty, int(traio * 0.72), paleta, perfil, pulse_time, 0.62)
            if variante == "muralha_gelo":
                for i in range(3):
                    ang = pulse_time * 0.12 + i * (math.pi / 3)
                    x1 = tx + math.cos(ang) * traio * 0.8
                    y1 = ty + math.sin(ang) * traio * 0.8
                    x2 = tx + math.cos(ang + math.pi) * traio * 0.45
                    y2 = ty + math.sin(ang + math.pi) * traio * 0.45
                    pygame.draw.line(self.tela, paleta["core"], (int(x1), int(y1)), (int(x2), int(y2)), 1)
            elif variante == "espelho_gelo":
                inner = self._pontos_poligono_regular(tx, ty, traio * 0.62, 6, -pulse_time * 0.1)
                pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["spark"], 110), [(int(px), int(py)) for px, py in inner], 1)
        else:
            if getattr(trap, 'ativada', False):
                exp_alpha = int(200 * (trap.vida_timer / 0.5)) if trap.vida_timer > 0 else 0
                te4 = max(1, int(traio * 4))
                s_exp = self._get_surface(te4, te4, pygame.SRCALPHA)
                pygame.draw.circle(s_exp, (*trap.cor, min(255, exp_alpha)), (te4 // 2, te4 // 2), int(traio * 2))
                self.tela.blit(s_exp, (tx - te4 // 2, ty - te4 // 2))
            else:
                trap_pulse = 0.6 + 0.4 * math.sin(pulse_time * 3 + hash(id(trap)) % 10)
                trap_r = max(1, int(traio * trap_pulse))
                s = self._get_surface(trap_r * 2 + 4, trap_r * 2 + 4, pygame.SRCALPHA)
                pygame.draw.circle(s, (*trap.cor, 80), (trap_r + 2, trap_r + 2), trap_r)
                self.tela.blit(s, (tx - trap_r - 2, ty - trap_r - 2))
                pygame.draw.circle(self.tela, trap.cor, (int(tx), int(ty)), int(traio), 2)
                self._desenhar_motivo_circular_magia(tx, ty, int(traio * 0.82), paleta, perfil, pulse_time, 0.68)
                if variante == "prisao_luz":
                    for ang in (0, math.pi / 2):
                        pygame.draw.line(self.tela, paleta["spark"], (int(tx + math.cos(ang) * traio), int(ty + math.sin(ang) * traio)), (int(tx - math.cos(ang) * traio), int(ty - math.sin(ang) * traio)), 1)
                elif variante == "armadilha_incendiaria":
                    tri = [(tx, ty - traio * 0.95), (tx + traio * 0.82, ty + traio * 0.6), (tx - traio * 0.82, ty + traio * 0.6)]
                    pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][1], 120), [(int(x), int(y)) for x, y in tri], 1)
                elif variante == "armadilha_eletrica":
                    zig = self._gerar_linha_zigzag(tx - traio * 0.8, ty, tx + traio * 0.8, ty, traio * 0.18, 5, pulse_time * 10.0)
                    pygame.draw.lines(self.tela, paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)

    def _desenhar_motivo_circular_magia(self, x, y, raio, paleta, perfil, tempo, intensidade=1.0):
        raio = int(max(8, raio))
        motivo = perfil["motivo"]
        ornamento = perfil["ornamento"]
        alpha = max(45, int(160 * intensidade))

        if motivo == "protecao":
            hexa = self._pontos_poligono_regular(x, y, raio, 6, tempo * 0.14 + math.pi / 6)
            hexa_inner = self._pontos_poligono_regular(x, y, raio * 0.68, 6, -tempo * 0.18)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], alpha), [(int(px), int(py)) for px, py in hexa], 2)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["core"], alpha - 25), [(int(px), int(py)) for px, py in hexa_inner], 1)
            for px, py in hexa:
                pygame.draw.circle(self.tela, paleta["spark"], (int(px), int(py)), max(2, int(raio * 0.08)))
        elif motivo == "cura":
            for i in range(5):
                ang = tempo * 0.45 + i * (math.pi * 2 / 5)
                ponta = (x + math.cos(ang) * raio * 1.1, y + math.sin(ang) * raio * 1.1)
                base_esq = (x + math.cos(ang + 0.55) * raio * 0.38, y + math.sin(ang + 0.55) * raio * 0.38)
                base_dir = (x + math.cos(ang - 0.55) * raio * 0.38, y + math.sin(ang - 0.55) * raio * 0.38)
                pygame.draw.polygon(
                    self.tela,
                    self._cor_com_alpha(paleta["mid"][1], alpha - 20),
                    [(int(base_esq[0]), int(base_esq[1])), (int(ponta[0]), int(ponta[1])), (int(base_dir[0]), int(base_dir[1]))],
                )
            pygame.draw.line(self.tela, paleta["core"], (int(x - raio * 0.35), int(y)), (int(x + raio * 0.35), int(y)), 2)
            pygame.draw.line(self.tela, paleta["core"], (int(x), int(y - raio * 0.35)), (int(x), int(y + raio * 0.35)), 2)
        elif motivo == "invocacao":
            tri_a = self._pontos_poligono_regular(x, y, raio, 3, tempo * 0.25 - math.pi / 2)
            tri_b = self._pontos_poligono_regular(x, y, raio * 0.72, 3, -tempo * 0.3 + math.pi / 2)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], alpha), [(int(px), int(py)) for px, py in tri_a], 2)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["spark"], alpha - 25), [(int(px), int(py)) for px, py in tri_b], 2)
            for i in range(3):
                ang = tempo * 0.7 + i * (math.pi * 2 / 3)
                rx = x + math.cos(ang) * raio * 0.55
                ry = y + math.sin(ang) * raio * 0.55
                pygame.draw.circle(self.tela, paleta["core"], (int(rx), int(ry)), max(2, int(raio * 0.08)))
        elif motivo == "controle":
            for i in range(4):
                ang = tempo * 0.18 + i * (math.pi / 2)
                x1 = x + math.cos(ang) * raio
                y1 = y + math.sin(ang) * raio
                x2 = x + math.cos(ang + math.pi) * raio
                y2 = y + math.sin(ang + math.pi) * raio
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["mid"][0], alpha - 35), (int(x1), int(y1)), (int(x2), int(y2)), 1)
            for i in range(4):
                inicio = tempo * 0.22 + i * (math.pi / 2)
                self._desenhar_arco_magico(x, y, raio, paleta["spark"], alpha - 10, inicio, inicio + math.pi / 4, 2)
        elif motivo == "disrupcao":
            for i in range(5):
                ang = tempo * 0.34 + i * (math.pi * 2 / 5)
                inicio = ang - 0.25
                fim = ang + 0.18
                self._desenhar_arco_magico(x, y, raio, paleta["mid"][0], alpha - 20, inicio, fim, 2)
                sx = x + math.cos(ang) * raio * 0.55
                sy = y + math.sin(ang) * raio * 0.55
                ex = x + math.cos(ang + 0.4) * raio * 1.05
                ey = y + math.sin(ang + 0.4) * raio * 1.05
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["spark"], alpha - 15), (int(sx), int(sy)), (int(ex), int(ey)), 2)
        elif motivo == "amplificacao":
            for i in range(4):
                ang = tempo * 0.28 + i * (math.pi / 2)
                ponta = (x + math.cos(ang) * raio * 1.05, y + math.sin(ang) * raio * 1.05)
                base = (x + math.cos(ang) * raio * 0.42, y + math.sin(ang) * raio * 0.42)
                lat_a = (base[0] + math.cos(ang + math.pi / 2) * raio * 0.18, base[1] + math.sin(ang + math.pi / 2) * raio * 0.18)
                lat_b = (base[0] + math.cos(ang - math.pi / 2) * raio * 0.18, base[1] + math.sin(ang - math.pi / 2) * raio * 0.18)
                pygame.draw.polygon(
                    self.tela,
                    self._cor_com_alpha(paleta["mid"][0], alpha - 10),
                    [(int(ponta[0]), int(ponta[1])), (int(lat_a[0]), int(lat_a[1])), (int(base[0]), int(base[1])), (int(lat_b[0]), int(lat_b[1]))],
                    0,
                )
        elif motivo == "mobilidade":
            for i in range(3):
                ang = tempo * 0.55 + i * (math.pi * 2 / 3)
                ponta = (x + math.cos(ang) * raio, y + math.sin(ang) * raio)
                cauda = (x - math.cos(ang) * raio * 0.15, y - math.sin(ang) * raio * 0.15)
                lat_a = (cauda[0] + math.cos(ang + 2.5) * raio * 0.22, cauda[1] + math.sin(ang + 2.5) * raio * 0.22)
                lat_b = (cauda[0] + math.cos(ang - 2.5) * raio * 0.22, cauda[1] + math.sin(ang - 2.5) * raio * 0.22)
                pygame.draw.polygon(
                    self.tela,
                    self._cor_com_alpha(paleta["spark"], alpha - 10),
                    [(int(ponta[0]), int(ponta[1])), (int(lat_a[0]), int(lat_a[1])), (int(lat_b[0]), int(lat_b[1]))],
                )
        elif ornamento == "espinhos":
            estrela = self._pontos_poligono_regular(x, y, raio, 10, tempo * 0.2, 1.42)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][1], alpha), [(int(px), int(py)) for px, py in estrela], 2)
        elif ornamento == "mira":
            pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["mid"][0], alpha), (int(x), int(y)), raio, 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(x - raio), int(y)), (int(x + raio), int(y)), 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(x), int(y - raio)), (int(x), int(y + raio)), 1)
        elif ornamento == "orbitas":
            for fator in (0.72, 1.0):
                self._desenhar_arco_magico(x, y, int(raio * fator), paleta["mid"][0], alpha - 15, tempo * 0.35, tempo * 0.35 + math.pi * 1.2, 2)
        else:
            pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["mid"][0], alpha - 15), (int(x), int(y)), raio, 2)

    def _desenhar_ornamentos_feixe(self, surf, pontos, paleta, perfil, pulse_time, largura):
        if len(pontos) < 2:
            return

        motivo = perfil["motivo"]
        ornamento = perfil["ornamento"]
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

            if motivo == "controle":
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
            elif motivo == "protecao":
                for side in (-1, 1):
                    ox = mid_x + perp_x * largura * 0.72 * side
                    oy = mid_y + perp_y * largura * 0.72 * side
                    pygame.draw.circle(surf, self._cor_com_alpha(paleta["core"], 110), (int(ox), int(oy)), max(1, largura // 3))
            elif motivo == "cura":
                sway = math.sin(pulse_time * 10 + i) * largura * 0.55
                pygame.draw.circle(
                    surf,
                    self._cor_com_alpha(paleta["spark"], 105),
                    (int(mid_x + perp_x * sway), int(mid_y + perp_y * sway)),
                    max(1, largura // 3),
                )
            elif motivo == "invocacao":
                tri = [
                    (mid_x + math.cos(pulse_time + i) * largura * 0.8, mid_y + math.sin(pulse_time + i) * largura * 0.8),
                    (mid_x + math.cos(pulse_time + i + 2.1) * largura * 0.8, mid_y + math.sin(pulse_time + i + 2.1) * largura * 0.8),
                    (mid_x + math.cos(pulse_time + i + 4.2) * largura * 0.8, mid_y + math.sin(pulse_time + i + 4.2) * largura * 0.8),
                ]
                pygame.draw.polygon(surf, self._cor_com_alpha(paleta["mid"][0], 80), [(int(px), int(py)) for px, py in tri], 1)
            elif motivo == "disrupcao":
                for side in (-1, 1):
                    ox = mid_x + perp_x * largura * 0.8 * side
                    oy = mid_y + perp_y * largura * 0.8 * side
                    ex = ox + seg_dx / max(seg_len, 1) * largura * 0.6
                    ey = oy + seg_dy / max(seg_len, 1) * largura * 0.6
                    pygame.draw.line(surf, self._cor_com_alpha(paleta["spark"], 105), (int(ox), int(oy)), (int(ex), int(ey)), 1)
            elif ornamento == "mira":
                pygame.draw.circle(surf, self._cor_com_alpha(paleta["spark"], 90), (int(mid_x), int(mid_y)), max(1, largura // 2))
            elif ornamento == "espinhos":
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
            elif ornamento == "orbitas":
                for side in (-1, 1):
                    ox = mid_x + perp_x * math.sin(pulse_time * 7 + i) * largura * 0.65 * side
                    oy = mid_y + perp_y * math.sin(pulse_time * 7 + i) * largura * 0.65 * side
                    pygame.draw.circle(surf, self._cor_com_alpha(paleta["mid"][0], 80), (int(ox), int(oy)), max(1, largura // 4))

    def _desenhar_area_magica(self, area, pulse_time):
        ax, ay = self.cam.converter(area.x * PPM, area.y * PPM)
        ar = self.cam.converter_tam(area.raio_atual * PPM)
        if ar <= 0:
            return

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

        self._desenhar_glow_circular(
            ax,
            ay,
            ar * ((1.75 if suporte else 2.0) * perfil["perigo"]),
            paleta["outer"][0],
            (24 if suporte else 42 if ativo else 58) + alpha_base * 0.08,
        )

        fill = self._get_surface(ar * 2 + 8, ar * 2 + 8, pygame.SRCALPHA)
        pygame.draw.circle(fill, self._cor_com_alpha(paleta["outer"][1], 34 if suporte else 46 if ativo else 26), (ar + 4, ar + 4), max(2, raio_visual))
        pygame.draw.circle(fill, self._cor_com_alpha(paleta["mid"][0], 24 if suporte else 18 if ativo else 9), (ar + 4, ar + 4), max(2, int(raio_visual * (0.58 if suporte else 0.72))))
        self.tela.blit(fill, (ax - ar - 4, ay - ar - 4))

        for i in range(2 if suporte else 3 if perfil["motivo"] != "controle" else 4):
            phase = (pulse_time * (1.5 + i * 0.45) + i * 0.21) % 1.0
            ring_r = int(ar * (0.25 + phase * 0.75))
            if 4 < ring_r < ar:
                ring = self._get_surface(ring_r * 2 + 8, ring_r * 2 + 8, pygame.SRCALPHA)
                pygame.draw.circle(
                    ring,
                    self._cor_com_alpha(paleta["spark"], (130 if ativo else 95) * (1.0 - phase)),
                    (ring_r + 4, ring_r + 4),
                    ring_r,
                    2,
                )
                self.tela.blit(ring, (ax - ring_r - 4, ay - ring_r - 4))

        marker_count = max(6, perfil["marcas"] + (2 if ativo and cataclismo else 0))
        for i in range(marker_count):
            ang = pulse_time * (0.4 if suporte else 0.8 if ativo else 2.1) + i * (math.pi * 2 / marker_count)
            outer_r = ar + (2 if suporte else 6)
            inner_r = max(6, int(ar * (0.78 if zonal else 0.86 if suporte else 0.72)))
            x1 = ax + math.cos(ang) * inner_r
            y1 = ay + math.sin(ang) * inner_r
            x2 = ax + math.cos(ang) * outer_r
            y2 = ay + math.sin(ang) * outer_r
            pygame.draw.line(self.tela, paleta["mid"][0], (int(x1), int(y1)), (int(x2), int(y2)), 2 if zonal or cataclismo else 1)

        if zonal:
            step = max(8, int(ar * 0.35))
            for gx in range(ax - ar + step, ax + ar, step):
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["outer"][0], 55), (gx, ay - ar + 6), (gx, ay + ar - 6), 1)
        motivo_raio = int(ar * (0.66 if zonal else 0.58 if suporte else 0.52 if ativo else 0.45))
        self._desenhar_motivo_circular_magia(ax, ay, motivo_raio, paleta, perfil, pulse_time, 1.0 if ativo else 0.78)
        if invocacao:
            self._desenhar_sigilo_magico(ax, ay, int(ar * 0.42), paleta, pulse_time, 1.1 if ativo else 0.8)
        elif suporte:
            pygame.draw.circle(self.tela, paleta["core"], (ax, ay), max(2, int(ar * 0.32)), 2)
            pygame.draw.circle(self.tela, paleta["mid"][0], (ax, ay), max(2, int(ar * 0.16)))
        elif perfil["motivo"] == "impacto":
            self._desenhar_sigilo_magico(ax, ay, int(ar * (0.22 if zonal else 0.28 if ativo else 0.4)), paleta, pulse_time, 1.0 if ativo else 0.8)

        variante = assinatura.get("variante", "")
        if variante == "pilar_fogo":
            for i in range(4):
                ang = pulse_time * 0.55 + i * (math.pi / 2)
                base_x = ax + math.cos(ang) * ar * 0.42
                base_y = ay + math.sin(ang) * ar * 0.42
                topo = (base_x, base_y - ar * 0.42)
                lat_a = (base_x - ar * 0.08, base_y)
                lat_b = (base_x + ar * 0.08, base_y)
                pygame.draw.polygon(
                    self.tela,
                    self._cor_com_alpha(paleta["mid"][1], 170 if ativo else 110),
                    [(int(lat_a[0]), int(lat_a[1])), (int(topo[0]), int(topo[1])), (int(lat_b[0]), int(lat_b[1]))],
                )
        elif variante == "julgamento_celestial":
            for i in range(5):
                ang = pulse_time * 0.18 + i * (math.pi * 2 / 5)
                x = ax + math.cos(ang) * ar * 0.52
                y = ay + math.sin(ang) * ar * 0.52
                pygame.draw.line(self.tela, paleta["spark"], (int(x), int(y - ar * 0.22)), (int(x), int(y + ar * 0.14)), 2)
                pygame.draw.circle(self.tela, paleta["core"], (int(x), int(y + ar * 0.14)), max(2, int(ar * 0.05)))
            pygame.draw.line(self.tela, paleta["core"], (int(ax - ar * 0.25), int(ay)), (int(ax + ar * 0.25), int(ay)), 2)
            pygame.draw.line(self.tela, paleta["core"], (int(ax), int(ay - ar * 0.25)), (int(ax), int(ay + ar * 0.25)), 2)
        elif variante == "redencao":
            for fator in (0.32, 0.54, 0.78):
                pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["spark"], 95), (ax, ay), max(2, int(ar * fator)), 1)
            for i in range(4):
                ang = pulse_time * 0.25 + i * (math.pi / 2)
                ex = ax + math.cos(ang) * ar * 0.7
                ey = ay + math.sin(ang) * ar * 0.7
                pygame.draw.line(self.tela, paleta["core"], (ax, ay), (int(ex), int(ey)), 1)
        elif variante == "nevasca":
            for i in range(6):
                ang = pulse_time * 0.22 + i * (math.pi / 3)
                ex = ax + math.cos(ang) * ar * 0.62
                ey = ay + math.sin(ang) * ar * 0.62
                pygame.draw.line(self.tela, paleta["core"], (ax, ay), (int(ex), int(ey)), 1)
            for i in range(3):
                self._desenhar_arco_magico(ax, ay, int(ar * (0.42 + i * 0.12)), paleta["spark"], 90, pulse_time * 0.35 + i, pulse_time * 0.35 + i + math.pi / 3, 1)
        elif variante == "zero_absoluto":
            estrela = self._pontos_poligono_regular(ax, ay, ar * 0.62, 8, pulse_time * 0.12, 1.38)
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["core"], 150), [(int(px), int(py)) for px, py in estrela], 2)
            pygame.draw.circle(self.tela, paleta["spark"], (ax, ay), max(2, int(ar * 0.18)))
        elif variante == "tempestade":
            for i in range(3):
                x1 = ax - ar * 0.75 + i * ar * 0.5
                y1 = ay - ar * 0.35
                x2 = x1 + ar * 0.35
                y2 = ay + ar * 0.45
                zig = self._gerar_linha_zigzag(x1, y1, x2, y2, ar * 0.11, 5, pulse_time * 8 + i)
                pygame.draw.lines(self.tela, paleta["spark"], False, [(int(px), int(py)) for px, py in zig], 2)
        elif variante == "julgamento_thor":
            bolt = self._gerar_linha_zigzag(ax, ay - ar * 0.9, ax, ay + ar * 0.05, ar * 0.12, 6, pulse_time * 10)
            pygame.draw.lines(self.tela, paleta["spark"], False, [(int(px), int(py)) for px, py in bolt], 3)
            pygame.draw.circle(self.tela, paleta["core"], (ax, ay), max(2, int(ar * 0.16)))
        elif variante == "aniquilacao_void":
            pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 12), 210), (ax, ay), max(3, int(ar * 0.44)))
            for i in range(8):
                ang = pulse_time * 0.18 + i * (math.pi * 2 / 8)
                x1 = ax + math.cos(ang) * ar * 0.68
                y1 = ay + math.sin(ang) * ar * 0.68
                x2 = ax + math.cos(ang) * ar * 0.3
                y2 = ay + math.sin(ang) * ar * 0.3
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["mid"][1], 120), (int(x1), int(y1)), (int(x2), int(y2)), 2)
        elif variante in {"colapso_void", "implosao_void"}:
            for i in range(6):
                ang = pulse_time * 0.3 + i * (math.pi * 2 / 6)
                x1 = ax + math.cos(ang) * ar * 0.76
                y1 = ay + math.sin(ang) * ar * 0.76
                x2 = ax + math.cos(ang) * ar * 0.22
                y2 = ay + math.sin(ang) * ar * 0.22
                pygame.draw.line(self.tela, self._cor_com_alpha(paleta["spark"], 110), (int(x1), int(y1)), (int(x2), int(y2)), 1 if variante == "implosao_void" else 2)
            pygame.draw.circle(self.tela, self._cor_com_alpha((4, 0, 10), 190), (ax, ay), max(3, int(ar * 0.28)))

        pygame.draw.circle(self.tela, paleta["mid"][0], (ax, ay), max(2, raio_visual), 2 if suporte else 3)
        pygame.draw.circle(self.tela, paleta["core"], (ax, ay), max(2, int(ar * (0.12 if suporte else 0.18 if not cataclismo else 0.22))))

        if not ativo:
            aviso = self._get_surface(ar * 2 + 20, ar * 2 + 20, pygame.SRCALPHA)
            rect = pygame.Rect(10, 10, ar * 2, ar * 2)
            countdown = max(0.05, min(1.0, getattr(area, "delay", 0.0)))
            arc_end = math.radians(360 * countdown)
            pygame.draw.arc(aviso, self._cor_com_alpha((255, 240, 180), 220), rect, -math.pi / 2, -math.pi / 2 + arc_end, 4)
            self.tela.blit(aviso, (ax - ar - 10, ay - ar - 10))

    def _desenhar_beam_magico(self, beam, pulse_time):
        pts_screen = [self.cam.converter(bx * PPM, by * PPM) for bx, by in beam.segments]
        if len(pts_screen) < 2:
            return

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

        min_x = min(p[0] for p in pts_screen) - largura_efetiva - 16
        min_y = min(p[1] for p in pts_screen) - largura_efetiva - 16
        max_x = max(p[0] for p in pts_screen) + largura_efetiva + 16
        max_y = max(p[1] for p in pts_screen) + largura_efetiva + 16
        w = int(max_x - min_x + 1)
        h = int(max_y - min_y + 1)
        if w <= 0 or h <= 0:
            return

        surf = self._get_surface(w, h, pygame.SRCALPHA)
        local_pts = [(int(px - min_x), int(py - min_y)) for px, py in pts_screen]
        pygame.draw.lines(surf, self._cor_com_alpha(paleta["outer"][0], 60), False, local_pts, largura_efetiva + (10 if forca == "PRECISAO" else 14))
        pygame.draw.lines(surf, self._cor_com_alpha(paleta["mid"][0], 145), False, local_pts, largura_efetiva + (4 if forca == "PRECISAO" else 7))
        pygame.draw.lines(surf, self._cor_com_alpha(beam.cor, 255), False, local_pts, largura_efetiva)
        pygame.draw.lines(surf, self._cor_com_alpha(paleta["core"], 255), False, local_pts, max(1, largura_efetiva // 2))
        self._desenhar_ornamentos_feixe(surf, local_pts, paleta, perfil, pulse_time, largura_efetiva)

        variante = assinatura.get("variante", "")
        if variante == "sopro_dragao":
            for i in range(len(local_pts) - 1):
                x1, y1 = local_pts[i]
                x2, y2 = local_pts[i + 1]
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
                    ponta = (mx + perp_x * largura_efetiva * 1.35 * side, my + perp_y * largura_efetiva * 1.35 * side)
                    base_a = (mx + perp_x * largura_efetiva * 0.35 * side, my + perp_y * largura_efetiva * 0.35 * side)
                    base_b = (mx + seg_dx * 0.08, my + seg_dy * 0.08)
                    pygame.draw.polygon(surf, self._cor_com_alpha(paleta["mid"][1], 90), [(int(base_a[0]), int(base_a[1])), (int(ponta[0]), int(ponta[1])), (int(base_b[0]), int(base_b[1]))])
        elif variante == "desintegrar":
            for i in range(len(local_pts) - 1):
                x1, y1 = local_pts[i]
                x2, y2 = local_pts[i + 1]
                mx = int(x1 + (x2 - x1) * 0.5)
                my = int(y1 + (y2 - y1) * 0.5)
                pygame.draw.rect(surf, self._cor_com_alpha(paleta["spark"], 95), pygame.Rect(mx - largura_efetiva // 2, my - largura_efetiva // 2, max(2, largura_efetiva), max(2, largura_efetiva)), 1)
        elif variante == "raio_sagrado":
            for i in range(0, len(local_pts), 2):
                px, py = local_pts[i]
                pygame.draw.line(surf, self._cor_com_alpha(paleta["spark"], 100), (int(px - largura_efetiva), int(py)), (int(px + largura_efetiva), int(py)), 1)
                pygame.draw.line(surf, self._cor_com_alpha(paleta["spark"], 100), (int(px), int(py - largura_efetiva)), (int(px), int(py + largura_efetiva)), 1)
        elif variante == "corrente_cadeia":
            for i in range(len(local_pts) - 1):
                x1, y1 = local_pts[i]
                x2, y2 = local_pts[i + 1]
                zig = self._gerar_linha_zigzag(x1, y1, x2, y2, largura_efetiva * 0.55, 5, pulse_time * 11 + i)
                pygame.draw.lines(surf, self._cor_com_alpha(paleta["spark"], 120), False, [(int(px), int(py)) for px, py in zig], max(1, largura_efetiva // 4))
        elif variante == "devorar":
            for i in range(len(local_pts) - 1):
                x1, y1 = local_pts[i]
                x2, y2 = local_pts[i + 1]
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
                    ox = mx + perp_x * largura_efetiva * 0.95 * side
                    oy = my + perp_y * largura_efetiva * 0.95 * side
                    pygame.draw.circle(surf, self._cor_com_alpha((10, 0, 20), 150), (int(ox), int(oy)), max(1, largura_efetiva // 3))
        elif variante == "rasgo_dimensional":
            for i in range(len(local_pts) - 1):
                x1, y1 = local_pts[i]
                x2, y2 = local_pts[i + 1]
                seg_dx = x2 - x1
                seg_dy = y2 - y1
                seg_len = math.hypot(seg_dx, seg_dy)
                if seg_len < 6:
                    continue
                perp_x = -seg_dy / seg_len
                perp_y = seg_dx / seg_len
                mx = x1 + seg_dx * 0.5
                my = y1 + seg_dy * 0.5
                pygame.draw.line(surf, self._cor_com_alpha(paleta["mid"][1], 115), (int(mx - perp_x * largura_efetiva * 1.25), int(my - perp_y * largura_efetiva * 1.25)), (int(mx + perp_x * largura_efetiva * 1.25), int(my + perp_y * largura_efetiva * 1.25)), 2)

        self.tela.blit(surf, (min_x, min_y))

        sx, sy = pts_screen[0]
        ex, ey = pts_screen[-1]
        self._desenhar_glow_circular(sx, sy, largura_efetiva * (1.9 if perfil["suavidade"] < 0.8 else 1.6), paleta["mid"][0], 80)
        self._desenhar_glow_circular(ex, ey, largura_efetiva * (3.0 if perfil["ornamento"] == "espinhos" else 2.3 if utilidade in {"PROTECAO", "CURA"} else 2.6), paleta["core"], 120)
        if perfil["motivo"] in {"protecao", "cura", "invocacao"}:
            self._desenhar_motivo_circular_magia(ex, ey, int(largura_efetiva * 1.25), paleta, perfil, pulse_time, 0.72)

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

    def _desenhar_projetil_magico(self, proj, px, py, pr, pulse_time, ang_visual, cor):
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
        tail_x = px - math.cos(rad) * tail_len
        tail_y = py - math.sin(rad) * tail_len

        self._desenhar_glow_circular(px, py, pr * 2.5, paleta["outer"][0], 65)
        wake = self._get_surface(int(pr * 6 + 20), int(pr * 6 + 20), pygame.SRCALPHA)
        wc = wake.get_width() // 2
        hc = wake.get_height() // 2
        wake_pts = [
            (wc + math.cos(rad) * pr * 1.7, hc + math.sin(rad) * pr * 1.7),
            (wc + math.cos(rad + 2.45) * pr * 0.9, hc + math.sin(rad + 2.45) * pr * 0.9),
            (wc - math.cos(rad) * pr * 2.6, hc - math.sin(rad) * pr * 2.6),
            (wc + math.cos(rad - 2.45) * pr * 0.9, hc + math.sin(rad - 2.45) * pr * 0.9),
        ]
        pygame.draw.polygon(wake, self._cor_com_alpha(paleta["outer"][0], 55), wake_pts)
        self.tela.blit(wake, (int(px) - wc, int(py) - hc))

        if hasattr(proj, "trail") and len(proj.trail) > 1:
            self._desenhar_trilha_magica(proj.trail, paleta["mid"][0], max(2, pr))

        variante = assinatura_especifica.get("variante", "")
        if variante == "bola_fogo":
            for off in (0.0, 2.1, 4.2):
                ponto_x = px + math.cos(drift * 2.5 + off) * pr * 0.34
                ponto_y = py + math.sin(drift * 2.5 + off) * pr * 0.34
                pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["mid"][1], 185), (int(ponto_x), int(ponto_y)), max(2, int(pr * 0.52)))
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(2, int(pr * 0.5)))
        elif variante == "cometa_rastreador":
            cauda = [
                (px + math.cos(rad) * pr * 1.9, py + math.sin(rad) * pr * 1.9),
                (px + math.cos(rad + 2.55) * pr * 0.82, py + math.sin(rad + 2.55) * pr * 0.82),
                (px - math.cos(rad) * pr * 3.6, py - math.sin(rad) * pr * 3.6),
                (px + math.cos(rad - 2.55) * pr * 0.82, py + math.sin(rad - 2.55) * pr * 0.82),
            ]
            pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][1], 180), [(int(x), int(y)) for x, y in cauda])
            for scale in (0.7, 1.05):
                ex = px - math.cos(rad) * pr * (2.8 + scale)
                ey = py - math.sin(rad) * pr * (2.8 + scale)
                pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["spark"], 85), (int(ex), int(ey)), max(1, int(pr * 0.18 * scale)))
        elif variante == "meteoro_brutal":
            rocha = self._pontos_poligono_regular(px, py, pr * 1.18, 7, drift * 0.2, 1.18)
            pygame.draw.polygon(self.tela, (88, 40, 18), [(int(x), int(y)) for x, y in rocha])
            for ang in (rad, rad + 1.9, rad - 1.6):
                ex = px + math.cos(ang) * pr * 0.92
                ey = py + math.sin(ang) * pr * 0.92
                pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py)), (int(ex), int(ey)), 2)
        elif variante == "lanca_luz":
            haste = [
                (px + math.cos(rad) * pr * 2.1, py + math.sin(rad) * pr * 2.1),
                (px + math.cos(rad + 2.55) * pr * 0.55, py + math.sin(rad + 2.55) * pr * 0.55),
                (tail_x, tail_y),
                (px + math.cos(rad - 2.55) * pr * 0.55, py + math.sin(rad - 2.55) * pr * 0.55),
            ]
            pygame.draw.polygon(self.tela, paleta["core"], [(int(x), int(y)) for x, y in haste])
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr * 1.1), int(py)), (int(px + pr * 1.1), int(py)), 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py - pr * 1.1)), (int(px), int(py + pr * 1.1)), 1)
        elif variante == "lanca_gelo":
            cristal = [
                (px + math.cos(rad) * pr * 2.0, py + math.sin(rad) * pr * 2.0),
                (px + math.cos(rad + 2.45) * pr * 0.78, py + math.sin(rad + 2.45) * pr * 0.78),
                (px - math.cos(rad) * pr * 1.35, py - math.sin(rad) * pr * 1.35),
                (px + math.cos(rad - 2.45) * pr * 0.78, py + math.sin(rad - 2.45) * pr * 0.78),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in cristal], 2)
            pygame.draw.line(self.tela, paleta["core"], (int(px - pr * 0.8), int(py)), (int(px + pr * 1.2), int(py)), 1)
        elif variante == "misseis_arcanos":
            for orbit in (0.0, 2.09, 4.18):
                sx = px + math.cos(drift * 3.0 + orbit) * pr * 0.58
                sy = py + math.sin(drift * 3.0 + orbit) * pr * 0.58
                pygame.draw.circle(self.tela, self._cor_com_alpha(paleta["spark"], 110), (int(sx), int(sy)), max(1, int(pr * 0.22)))
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(2, int(pr * 0.4)))
        elif variante == "orbe_mana":
            pygame.draw.circle(self.tela, paleta["mid"][0], (int(px), int(py)), int(pr * 1.15), 2)
            for orbit in (0.0, math.pi):
                sx = px + math.cos(drift * 1.8 + orbit) * pr * 0.88
                sy = py + math.sin(drift * 1.8 + orbit) * pr * 0.88
                pygame.draw.circle(self.tela, paleta["spark"], (int(sx), int(sy)), max(1, int(pr * 0.18)))
        elif variante == "martelo_trovao":
            cabeca = [
                (px + math.cos(rad) * pr * 1.05, py + math.sin(rad) * pr * 1.05),
                (px + math.cos(rad + 1.1) * pr * 0.92, py + math.sin(rad + 1.1) * pr * 0.92),
                (px + math.cos(rad + math.pi) * pr * 0.32, py + math.sin(rad + math.pi) * pr * 0.32),
                (px + math.cos(rad - 1.1) * pr * 0.92, py + math.sin(rad - 1.1) * pr * 0.92),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in cabeca])
            pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py)), (int(tail_x), int(tail_y)), max(1, int(pr * 0.28)))
        elif variante == "sentenca_void":
            pygame.draw.circle(self.tela, self._cor_com_alpha((8, 0, 14), 210), (int(px), int(py)), max(2, int(pr * 0.95)))
            self._desenhar_arco_magico(px, py, int(pr * 1.15), paleta["mid"][0], 110, drift * 0.6, drift * 0.6 + math.pi * 1.1, 2)
            self._desenhar_arco_magico(px, py, int(pr * 0.78), paleta["spark"], 90, drift * -0.7, drift * -0.7 + math.pi * 0.9, 1)
        elif perfil["motivo"] == "protecao":
            escudo = self._pontos_poligono_regular(px, py, pr * 1.28, 6, rad + math.pi / 6)
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in escudo], 2)
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.52)))
        elif perfil["motivo"] == "cura":
            for i in range(4):
                ang = drift * 0.9 + i * (math.pi / 2)
                ponta = (px + math.cos(ang) * pr * 1.25, py + math.sin(ang) * pr * 1.25)
                base_esq = (px + math.cos(ang + 0.8) * pr * 0.45, py + math.sin(ang + 0.8) * pr * 0.45)
                base_dir = (px + math.cos(ang - 0.8) * pr * 0.45, py + math.sin(ang - 0.8) * pr * 0.45)
                pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][1], 170), [(int(base_esq[0]), int(base_esq[1])), (int(ponta[0]), int(ponta[1])), (int(base_dir[0]), int(base_dir[1]))])
        elif perfil["motivo"] == "invocacao":
            tri = self._pontos_poligono_regular(px, py, pr * 1.26, 3, rad - math.pi / 2)
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in tri], 2)
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.38)))
        elif perfil["motivo"] == "controle":
            grade = self._pontos_poligono_regular(px, py, pr * 1.1, 6, drift * 0.22)
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in grade], 2)
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr), int(py)), (int(px + pr), int(py)), 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py - pr)), (int(px), int(py + pr)), 1)
        elif perfil["motivo"] == "disrupcao":
            losango = [
                (px + math.cos(rad) * pr * 1.25, py + math.sin(rad) * pr * 1.25),
                (px + math.cos(rad + math.pi / 2) * pr * 0.65, py + math.sin(rad + math.pi / 2) * pr * 0.65),
                (px - math.cos(rad) * pr * 0.95, py - math.sin(rad) * pr * 0.95),
                (px + math.cos(rad - math.pi / 2) * pr * 0.65, py + math.sin(rad - math.pi / 2) * pr * 0.65),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in losango], 2)
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr * 0.8), int(py - pr * 0.2)), (int(px + pr * 0.8), int(py + pr * 0.2)), 2)
        elif perfil["motivo"] == "amplificacao":
            for scale in (1.2, 0.78):
                seta = [
                    (px + math.cos(rad) * pr * scale * 1.45, py + math.sin(rad) * pr * scale * 1.45),
                    (px + math.cos(rad + 2.45) * pr * scale * 0.55, py + math.sin(rad + 2.45) * pr * scale * 0.55),
                    (px - math.cos(rad) * pr * scale * 0.55, py - math.sin(rad) * pr * scale * 0.55),
                    (px + math.cos(rad - 2.45) * pr * scale * 0.55, py + math.sin(rad - 2.45) * pr * scale * 0.55),
                ]
                pygame.draw.polygon(self.tela, self._cor_com_alpha(paleta["mid"][0], 120 if scale > 1.0 else 200), [(int(x), int(y)) for x, y in seta], 2 if scale > 1.0 else 0)
        elif assinatura == "lanca":
            pts = [
                (px + math.cos(rad) * pr * 2.0, py + math.sin(rad) * pr * 2.0),
                (px + math.cos(rad + 2.55) * pr * 0.7, py + math.sin(rad + 2.55) * pr * 0.7),
                (tail_x, tail_y),
                (px + math.cos(rad - 2.55) * pr * 0.7, py + math.sin(rad - 2.55) * pr * 0.7),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in pts])
        elif assinatura == "fluxo":
            wave = []
            for i in range(5):
                step = i / 4
                wx = px - math.cos(rad) * pr * (1.8 - step * 2.4)
                wy = py - math.sin(rad) * pr * (1.8 - step * 2.4)
                sway = math.sin(drift * 8 + i) * pr * 0.28
                wave.append((wx + math.cos(rad + math.pi / 2) * sway, wy + math.sin(rad + math.pi / 2) * sway))
            pygame.draw.lines(self.tela, paleta["mid"][0], False, [(int(x), int(y)) for x, y in wave], max(2, int(pr * 0.8)))
            pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.45)))
        elif assinatura in {"campo", "domo"}:
            poly = []
            lados = 6 if assinatura == "campo" else 8
            for i in range(lados):
                ang = rad + i * (math.pi * 2 / lados)
                dist = pr * (1.35 if i % 2 == 0 else 1.0)
                poly.append((px + math.cos(ang) * dist, py + math.sin(ang) * dist))
            pygame.draw.polygon(self.tela, paleta["mid"][0], [(int(x), int(y)) for x, y in poly], 2)
            pygame.draw.circle(self.tela, paleta["mid"][1], (int(px), int(py)), max(1, int(pr * 0.7)))
        elif assinatura in {"sigilo", "anel", "aurea"}:
            pygame.draw.circle(self.tela, paleta["mid"][0], (int(px), int(py)), int(pr), 2)
            self._desenhar_sigilo_magico(px, py, int(pr * 1.1), paleta, drift, 0.65)
        else:
            flame = [
                (px + math.cos(rad) * pr * 1.8, py + math.sin(rad) * pr * 1.8),
                (px + math.cos(rad + 2.2) * pr * 0.9, py + math.sin(rad + 2.2) * pr * 0.9),
                (tail_x, tail_y),
                (px + math.cos(rad - 2.2) * pr * 0.9, py + math.sin(rad - 2.2) * pr * 0.9),
            ]
            pygame.draw.polygon(self.tela, paleta["mid"][1], [(int(x), int(y)) for x, y in flame])
            pygame.draw.circle(self.tela, paleta["mid"][0], (int(px), int(py)), int(pr))

        if elemento == "GELO":
            pygame.draw.line(self.tela, paleta["core"], (int(px - pr * 0.9), int(py)), (int(px + pr * 0.9), int(py)), 2)
        elif elemento == "RAIO":
            for i in range(2 if forca == "PRECISAO" else 3):
                ang = drift * 12 + i * (math.pi * 2 / max(1, 2 if forca == "PRECISAO" else 3))
                ex = px + math.cos(ang) * pr * 1.6
                ey = py + math.sin(ang) * pr * 1.6
                pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py)), (int(ex), int(ey)), 1)
        elif elemento in {"TREVAS", "VOID"}:
            pygame.draw.circle(self.tela, (10, 0, 18), (int(px), int(py)), int(pr * 1.1), 1)
        elif elemento == "LUZ":
            pygame.draw.line(self.tela, paleta["spark"], (int(px), int(py - pr * 1.4)), (int(px), int(py + pr * 1.4)), 1)
            pygame.draw.line(self.tela, paleta["spark"], (int(px - pr * 1.4), int(py)), (int(px + pr * 1.4), int(py)), 1)
        elif elemento == "ARCANO":
            self._desenhar_sigilo_magico(px, py, int(pr * 0.9), paleta, drift, 0.4)
        elif elemento == "NATUREZA":
            for off in (-0.55, 0.55):
                ex = px + math.cos(rad + off) * pr * 1.4
                ey = py + math.sin(rad + off) * pr * 1.4
                pygame.draw.line(self.tela, paleta["outer"][0], (int(px), int(py)), (int(ex), int(ey)), 2)
        elif elemento == "SANGUE":
            drip = [(int(px - pr * 0.28), int(py)), (int(px + pr * 0.28), int(py)), (int(px), int(py + pr * 1.6))]
            pygame.draw.polygon(self.tela, paleta["outer"][0], drip)

        pygame.draw.circle(self.tela, paleta["core"], (int(px), int(py)), max(1, int(pr * 0.42)))
        pygame.draw.circle(self.tela, paleta["spark"], (int(px), int(py)), max(1, int(pr * 0.18)))
        if perfil["motivo"] in {"protecao", "cura", "invocacao"}:
            self._desenhar_motivo_circular_magia(px, py, int(pr * 1.35), paleta, perfil, drift, 0.62)

    def _desenhar_orbe_magico(self, orbe):
        ox, oy = self.cam.converter(orbe.x * PPM, orbe.y * PPM)
        or_visual = self.cam.converter_tam(orbe.raio_visual * PPM)
        if or_visual <= 0:
            return

        classe = self._resolver_classe_magia(orbe, tipo="ORBE", elemento=getattr(orbe, "elemento", None))
        perfil = self._perfil_visual_magia(classe)
        elemento = self._detectar_elemento_visual(getattr(orbe, "nome", ""), getattr(orbe, "estado", ""), getattr(orbe, "elemento", None))
        paleta = self._paleta_magica(elemento, orbe.cor)
        assinatura = classe.get("assinatura_visual", "anel")
        utilidade = classe.get("classe_utilidade", "DANO")

        if orbe.estado == "disparando" and len(orbe.trail) > 1:
            self._desenhar_trilha_magica(orbe.trail, paleta["mid"][0], max(2, int(or_visual * 0.8)))

        for part in orbe.particulas:
            ppx, ppy = self.cam.converter(part['x'] * PPM, part['y'] * PPM)
            palpha = int(255 * (part['vida'] / 0.3))
            glow_r = 4
            surf = self._get_surface(glow_r * 2 + 4, glow_r * 2 + 4, pygame.SRCALPHA)
            pygame.draw.circle(surf, self._cor_com_alpha(part['cor'], palpha), (glow_r + 2, glow_r + 2), glow_r)
            self.tela.blit(surf, (ppx - glow_r - 2, ppy - glow_r - 2))

        pulso = 0.7 + 0.3 * math.sin(orbe.pulso)
        self._desenhar_glow_circular(ox, oy, or_visual * (1.9 if utilidade in {"CURA", "PROTECAO"} else 2.2 + pulso * 0.3), paleta["outer"][0], 85 * pulso)
        self._desenhar_motivo_circular_magia(ox, oy, int(or_visual * (1.45 if perfil["motivo"] in {"controle", "disrupcao"} else 1.2)), paleta, perfil, orbe.pulso, 0.86)
        if assinatura in {"sigilo", "aurea"}:
            self._desenhar_sigilo_magico(ox, oy, int(or_visual * (1.4 + 0.2 * pulso)), paleta, orbe.pulso, 0.9)
        else:
            pygame.draw.circle(self.tela, paleta["mid"][0], (int(ox), int(oy)), int(or_visual * 1.4), 2)
        pygame.draw.circle(self.tela, paleta["mid"][0], (int(ox), int(oy)), int(or_visual))
        pygame.draw.circle(self.tela, paleta["core"], (int(ox), int(oy)), max(1, int(or_visual * 0.48)))

        if orbe.estado == "carregando":
            carga_pct = min(1.0, orbe.tempo_carga / max(orbe.carga_max, 0.001))
            ring_r = int(or_visual * (1.8 + carga_pct * 1.3))
            pygame.draw.circle(self.tela, paleta["spark"], (int(ox), int(oy)), ring_r, 2)
            for i in range(4):
                ang = orbe.pulso * 0.9 + i * (math.pi / 2)
                ex = ox + math.cos(ang) * ring_r
                ey = oy + math.sin(ang) * ring_r
                pygame.draw.line(self.tela, paleta["mid"][1], (int(ox), int(oy)), (int(ex), int(ey)), 1)
            if perfil["motivo"] in {"invocacao", "protecao", "cura"}:
                self._desenhar_motivo_circular_magia(ox, oy, int(ring_r * 0.58), paleta, perfil, orbe.pulso + carga_pct, 0.74)

    def _desenhar_presenca_arma(self, lutador, centro, raio, anim_scale):
        arma = lutador.dados.arma_obj
        if not arma:
            return
        cor = (getattr(arma, 'r', 180), getattr(arma, 'g', 180), getattr(arma, 'b', 180))
        tipo = _texto_normalizado(getattr(arma, 'tipo', ''))
        rad = math.radians(lutador.angulo_arma_visual)
        alcance = raio * {
            "reta": 1.8,
            "dupla": 1.35,
            "corrente": 2.1,
            "arco": 1.5,
            "arremesso": 1.2,
            "orbital": 1.7,
            "magica": 1.6,
            "transformavel": 1.9,
        }.get(tipo, 1.5)
        tip_x = centro[0] + math.cos(rad) * alcance
        tip_y = centro[1] + math.sin(rad) * alcance
        intensidade = max(0.0, anim_scale - 0.92)
        if intensidade <= 0.05 and tipo not in {"magica", "orbital"}:
            return
        aura_alpha = 30 + 90 * min(1.0, intensidade * 1.8)
        self._desenhar_glow_circular(tip_x, tip_y, max(6, int(raio * (0.24 + intensidade * 0.22))), cor, aura_alpha)
        if tipo in {"reta", "dupla", "transformavel"}:
            back_x = tip_x - math.cos(rad) * raio * 0.55
            back_y = tip_y - math.sin(rad) * raio * 0.55
            pygame.draw.line(self.tela, self._misturar_cor(cor, (255, 255, 255), 0.4), (int(back_x), int(back_y)), (int(tip_x), int(tip_y)), max(1, int(2 * self.cam.zoom)))
        elif tipo == "corrente":
            for i in range(3):
                orbit = pygame.time.get_ticks() / 220.0 + i * 2.0
                ex = tip_x + math.cos(orbit) * raio * 0.18
                ey = tip_y + math.sin(orbit) * raio * 0.18
                pygame.draw.circle(self.tela, cor, (int(ex), int(ey)), max(1, int(raio * 0.08)))
        elif tipo in {"magica", "orbital"}:
            paleta = self._paleta_magica(getattr(arma, "afinidade_elemento", None), cor)
            self._desenhar_sigilo_magico(tip_x, tip_y, int(raio * 0.28), paleta, pygame.time.get_ticks() / 1000.0, 0.65)

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

    def desenhar(self):
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
        self.tela.fill(fundo)
        
        # === DESENHA ARENA v9.0 (ANTES DE TUDO) ===
        if self.arena:
            self.arena.desenhar(self.tela, self.cam)
        else:
            # Fallback: grid antigo se nÃ£o houver arena
            self.desenhar_grid()
        
        for d in self.decals: d.draw(self.tela, self.cam)
        
        # === DESENHA ÃREAS COM EFEITOS DRAMÃTICOS v11.0 ===
        if hasattr(self, 'areas'):
            for area in self.areas:
                if area.ativo:
                    pulse_time = pygame.time.get_ticks() / 1000.0
                    self._desenhar_area_magica(area, pulse_time)
        
        # === DESENHA BEAMS COM EFEITOS DRAMÃTICOS v11.0 ===
        if hasattr(self, 'beams'):
            pulse_time = pygame.time.get_ticks() / 1000.0
            for beam in self.beams:
                if beam.ativo:
                    self._desenhar_beam_magico(beam, pulse_time)
        
        for p in self.particulas:
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
        
        # === DESENHA SUMMONS (Invocacoes) ===
        if hasattr(self, 'summons') and self.summons:
            pulse_time = pygame.time.get_ticks() / 1000.0
            for summon in self.summons:
                if summon.ativo:
                    self._desenhar_summon_magico(summon, pulse_time)
        
        # === DESENHA TRAPS (Armadilhas) ===
        if hasattr(self, 'traps'):
            pulse_time = pygame.time.get_ticks() / 1000.0
            for trap in self.traps:
                if trap.ativo:
                    self._desenhar_trap_magica(trap, pulse_time)
        
        # === DESENHA MARCAS NO CHÃƒÆ’O (CRATERAS, RACHADURAS) - v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_ground(self.tela, self.cam)
        
        lutadores = list(self.fighters)
        lutadores.sort(key=lambda p: 0 if p.morto else 1)
        for l in lutadores: self.desenhar_lutador(l)
        
        # === DESENHA PROJÃƒâ€°TEIS COM TRAIL ELEMENTAL v4.0 ===
        pulse_time = pygame.time.get_ticks() / 1000.0
        
        # (trail update movido para update())
        
        for proj in self.projeteis:
            # Trail legado como fallback (projÃ©teis fÃ­sicos nÃ£o mÃ¡gicos)
            if hasattr(proj, 'trail') and len(proj.trail) > 1 and not any(
                    w in str(getattr(proj, 'nome', '')).lower()
                    for w in ["fogo","gelo","raio","trevas","luz","arcano","sangue","veneno","void"]):
                cor_trail = proj.cor if hasattr(proj, 'cor') else BRANCO
                for i in range(1, len(proj.trail)):
                    t = i / len(proj.trail)
                    alpha = int(255 * t * 0.7)
                    largura = max(1, int(proj.raio * PPM * self.cam.zoom * t))
                    p1 = self.cam.converter(proj.trail[i-1][0] * PPM, proj.trail[i-1][1] * PPM)
                    p2 = self.cam.converter(proj.trail[i][0] * PPM, proj.trail[i][1] * PPM)
                    if largura > 2:
                        s = pygame.Surface((abs(int(p2[0]-p1[0]))+largura*4, abs(int(p2[1]-p1[1]))+largura*4), pygame.SRCALPHA)
                        offset_x = min(p1[0], p2[0]) - largura*2
                        offset_y = min(p1[1], p2[1]) - largura*2
                        local_p1 = (p1[0] - offset_x, p1[1] - offset_y)
                        local_p2 = (p2[0] - offset_x, p2[1] - offset_y)
                        pygame.draw.line(s, (*cor_trail[:3], alpha // 2), local_p1, local_p2, largura * 2)
                        pygame.draw.line(s, (*cor_trail[:3], alpha), local_p1, local_p2, largura)
                        self.tela.blit(s, (offset_x, offset_y))
                    else:
                        pygame.draw.line(self.tela, cor_trail, p1, p2, largura)
            
            # ProjÃ©til principal - desenho baseado no tipo
            px, py = self.cam.converter(proj.x * PPM, proj.y * PPM)
            pr = self.cam.converter_tam(proj.raio * PPM)
            cor = proj.cor if hasattr(proj, 'cor') else BRANCO
            
            # Glow do projÃ©til
            glow_pulse = 0.8 + 0.4 * math.sin(pulse_time * 10 + id(proj) % 100)
            glow_r = int(pr * 2 * glow_pulse)
            if glow_r > 3:
                s = self._get_surface(glow_r*2+4, glow_r*2+4, pygame.SRCALPHA)
                pygame.draw.circle(s, (*cor[:3], 60), (glow_r+2, glow_r+2), glow_r)
                self.tela.blit(s, (px - glow_r - 2, py - glow_r - 2))
            
            tipo_proj = getattr(proj, 'tipo', 'skill')
            ang_visual = getattr(proj, 'angulo_visual', proj.angulo) if hasattr(proj, 'angulo') else 0
            rad = math.radians(ang_visual)
            
            if tipo_proj == "faca":
                # Desenha faca (triÃ¢ngulo alongado)
                tam = max(pr * 2, 8)
                pts = [
                    (px + math.cos(rad) * tam, py + math.sin(rad) * tam),  # Ponta
                    (px + math.cos(rad + 2.5) * tam * 0.4, py + math.sin(rad + 2.5) * tam * 0.4),
                    (px - math.cos(rad) * tam * 0.3, py - math.sin(rad) * tam * 0.3),  # Base
                    (px + math.cos(rad - 2.5) * tam * 0.4, py + math.sin(rad - 2.5) * tam * 0.4),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, BRANCO, pts, 1)
                
            elif tipo_proj == "shuriken":
                # Desenha shuriken (estrela de 4 pontas girando)
                tam = max(pr * 2, 10)
                pts = []
                for i in range(8):
                    ang_pt = rad + i * (math.pi / 4)
                    dist = tam if i % 2 == 0 else tam * 0.3
                    pts.append((px + math.cos(ang_pt) * dist, py + math.sin(ang_pt) * dist))
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, (50, 50, 50), pts, 1)
                
            elif tipo_proj == "chakram":
                # Desenha chakram (anel girando)
                tam = max(pr * 2, 12)
                pygame.draw.circle(self.tela, cor, (int(px), int(py)), int(tam), 3)
                pygame.draw.circle(self.tela, BRANCO, (int(px), int(py)), int(tam * 0.5), 2)
                # LÃ¢minas
                for i in range(6):
                    ang_blade = rad + i * (math.pi / 3)
                    bx = px + math.cos(ang_blade) * tam
                    by = py + math.sin(ang_blade) * tam
                    pygame.draw.line(self.tela, cor, (px, py), (int(bx), int(by)), 2)
                
            elif tipo_proj == "flecha":
                # Desenha flecha
                tam = max(pr * 3, 15)
                # Corpo da flecha
                x1 = px - math.cos(rad) * tam * 0.7
                y1 = py - math.sin(rad) * tam * 0.7
                x2 = px + math.cos(rad) * tam * 0.3
                y2 = py + math.sin(rad) * tam * 0.3
                pygame.draw.line(self.tela, (139, 90, 43), (int(x1), int(y1)), (int(x2), int(y2)), 2)
                # Ponta da flecha (triÃ¢ngulo)
                pts = [
                    (px + math.cos(rad) * tam * 0.6, py + math.sin(rad) * tam * 0.6),
                    (px + math.cos(rad + 2.7) * tam * 0.2, py + math.sin(rad + 2.7) * tam * 0.2),
                    (px + math.cos(rad - 2.7) * tam * 0.2, py + math.sin(rad - 2.7) * tam * 0.2),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                # Penas (traseira)
                for offset in [-0.3, 0.3]:
                    fx = x1 + math.cos(rad + offset) * tam * 0.15
                    fy = y1 + math.sin(rad + offset) * tam * 0.15
                    pygame.draw.line(self.tela, (200, 200, 200), (int(x1), int(y1)), (int(fx), int(fy)), 1)
                
            else:
                self._desenhar_projetil_magico(proj, px, py, pr, pulse_time, ang_visual, cor)

        # === DESENHA ORBES MÃGICOS ===
        for p in self.fighters:
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if not orbe.ativo:
                        continue
                    self._desenhar_orbe_magico(orbe)

        # === EFEITOS v7.0 IMPACT EDITION ===
        for ef in self.dash_trails: ef.draw(self.tela, self.cam)
        for ef in self.hit_sparks: ef.draw(self.tela, self.cam)
        for ef in self.magic_clashes: ef.draw(self.tela, self.cam)
        for ef in self.impact_flashes: ef.draw(self.tela, self.cam)
        for ef in self.block_effects: ef.draw(self.tela, self.cam)
        
        # === MAGIC VFX v11.0 DRAMATIC EDITION ===
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            self.magic_vfx.draw(self.tela, self.cam)

        # === ANIMAÃƒâ€¡Ãƒâ€¢ES DE MOVIMENTO v8.0 CINEMATIC EDITION ===
        if self.movement_anims:
            self.movement_anims.draw(self.tela, self.cam)

        # === ANIMAÃƒâ€¡Ãƒâ€¢ES DE ATAQUE v8.0 IMPACT EDITION ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_effects(self.tela, self.cam)

        for s in self.shockwaves: s.draw(self.tela, self.cam)
        for t in self.textos: t.draw(self.tela, self.cam)

        # === SCREEN EFFECTS (FLASH) v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_screen_effects(self.tela, self.screen_width, self.screen_height)

        # === DEBUG VISUAL DE HITBOX ===
        if self.show_hitbox_debug:
            self.desenhar_hitbox_debug()

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
                if not self.portrait_mode:  # Esconde controles em portrait para mais espaÃ§o
                    self.desenhar_controles() 
            else: self.desenhar_vitoria()
            if self.paused: self.desenhar_pause()
        if self.show_analysis: self.desenhar_analise()


    def desenhar_grid(self):
        start_x = int((-self.cam.x * self.cam.zoom) % (50 * self.cam.zoom))
        start_y = int((-self.cam.y * self.cam.zoom) % (50 * self.cam.zoom))
        step = int(50 * self.cam.zoom)
        for x in range(start_x, self.screen_width, step): pygame.draw.line(self.tela, COR_GRID, (x, 0), (x, self.screen_height))
        for y in range(start_y, self.screen_height, step): pygame.draw.line(self.tela, COR_GRID, (0, y), (self.screen_width, y))


    def desenhar_lutador(self, l):
        px = l.pos[0] * PPM; py = l.pos[1] * PPM
        sx, sy = self.cam.converter(px, py); off_y = self.cam.converter_tam(l.z * PPM); raio = self.cam.converter_tam((l.dados.tamanho / 2) * PPM)
        if l in self.rastros and len(self.rastros[l]) > 2 and l.dados.arma_obj:
            pts_rastro = []
            for ponta, cabo in self.rastros[l]:
                p_conv = self.cam.converter(ponta[0], ponta[1]); c_conv = self.cam.converter(cabo[0], cabo[1])
                p_conv = (p_conv[0], p_conv[1] - off_y); c_conv = (c_conv[0], c_conv[1] - off_y)
                pts_rastro.append(p_conv); pts_rastro.insert(0, c_conv)
            cor_rastro = (l.dados.arma_obj.r, l.dados.arma_obj.g, l.dados.arma_obj.b, 80)
            if len(pts_rastro) > 2:
                # Usa bounding-box surface em vez de full-screen para performance
                xs = [p[0] for p in pts_rastro]; ys = [p[1] for p in pts_rastro]
                min_x, max_x = int(min(xs)) - 2, int(max(xs)) + 2
                min_y, max_y = int(min(ys)) - 2, int(max(ys)) + 2
                sw = max(1, max_x - min_x); sh = max(1, max_y - min_y)
                if sw < 2000 and sh < 2000:  # sanity cap
                    s = self._get_surface(sw, sh, pygame.SRCALPHA)
                    local_pts = [(p[0] - min_x, p[1] - min_y) for p in pts_rastro]
                    pygame.draw.polygon(s, cor_rastro, local_pts)
                    self.tela.blit(s, (min_x, min_y))
        if l.morto:
            pygame.draw.ellipse(self.tela, COR_CORPO, (sx-raio, sy-raio, raio*2, raio*2))
            if l.dados.arma_obj:
                ax = l.arma_droppada_pos[0]*PPM; ay = l.arma_droppada_pos[1]*PPM
                asx, asy = self.cam.converter(ax, ay)
                self.desenhar_arma(l.dados.arma_obj, (asx, asy), l.arma_droppada_ang, l.dados.tamanho, raio)
            return
        sombra_d = max(1, raio * 2)
        tam_s = max(1, int(sombra_d * max(0.4, 1.0 - (l.z/4.0))))
        # Use cached shadow surface keyed by diameter
        if not hasattr(self, '_shadow_cache'):
            self._shadow_cache = {}
        if sombra_d not in self._shadow_cache:
            ss = self._get_surface(sombra_d, sombra_d, pygame.SRCALPHA)
            pygame.draw.ellipse(ss, (0,0,0,80), (0, 0, sombra_d, sombra_d))
            self._shadow_cache[sombra_d] = ss
        sombra = self._shadow_cache[sombra_d]
        if tam_s > 0:
            if tam_s != sombra_d:
                sombra_scaled = pygame.transform.scale(sombra, (tam_s, tam_s))
                self.tela.blit(sombra_scaled, (sx-tam_s//2, sy-tam_s//2))
            else:
                self.tela.blit(sombra, (sx-tam_s//2, sy-tam_s//2))
        centro = (sx, sy - off_y)
        
        # === COR DO CORPO COM FLASH DE DANO MELHORADO ===
        if l.flash_timer > 0:
            # Usa cor de flash personalizada se disponÃ­vel
            flash_cor = getattr(l, 'flash_cor', (255, 255, 255))
            # Intensidade do flash diminui com o tempo
            flash_intensity = l.flash_timer / 0.25
            # Mistura cor original com cor de flash
            cor_r = getattr(l.dados, 'cor_r', 200) or 200
            cor_g = getattr(l.dados, 'cor_g', 50) or 50
            cor_b = getattr(l.dados, 'cor_b', 50) or 50
            cor_original = (cor_r, cor_g, cor_b)
            cor = tuple(int(max(0, min(255, flash_cor[i] * flash_intensity + cor_original[i] * (1 - flash_intensity)))) for i in range(3))
        else:
            cor_r = getattr(l.dados, 'cor_r', 200) or 200
            cor_g = getattr(l.dados, 'cor_g', 50) or 50
            cor_b = getattr(l.dados, 'cor_b', 50) or 50
            cor = (int(cor_r), int(cor_g), int(cor_b))
        
        pygame.draw.circle(self.tela, cor, centro, raio)
        
        # === CONTORNO APRIMORADO ===
        if l.stun_timer > 0:
            contorno = AMARELO_FAISCA
            largura = max(2, self.cam.converter_tam(5))
        elif l.atacando:
            contorno = (255, 255, 255)
            largura = max(2, self.cam.converter_tam(4))
        elif l.flash_timer > 0:
            # Contorno vermelho durante dano
            contorno = (255, 100, 100)
            largura = max(2, self.cam.converter_tam(4))
        else:
            contorno = (50, 50, 50)
            largura = max(1, self.cam.converter_tam(2))
        
        pygame.draw.circle(self.tela, contorno, centro, raio, largura)

        # === Sprint3: EMOÃ‡Ã•ES â†’ CONTORNOS SECUNDÃRIOS ===
        # raiva alta â†’ anel vermelho pulsante (fora do contorno principal)
        # medo alto  â†’ anel azul frio
        # As emoÃ§Ãµes eram calculadas a cada frame mas nÃ£o tinham nenhum output visual.
        brain = getattr(l, 'brain', None)
        if brain is not None and not l.morto:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 120)
            raiva_val  = getattr(brain, 'raiva', 0.0)
            medo_val   = getattr(brain, 'medo', 0.0)
            excit_val  = getattr(brain, 'excitacao', 0.0)

            if raiva_val > 0.55:
                # Anel vermelho â€” intensidade proporcional Ã  raiva
                ring_alpha = int(min(200, raiva_val * 160 * pulso))
                ring_r = max(1, raio + self.cam.converter_tam(4))
                ring_w = max(1, self.cam.converter_tam(3))
                s_ring = self._get_surface(ring_r * 2 + ring_w * 2, ring_r * 2 + ring_w * 2, pygame.SRCALPHA)
                pygame.draw.circle(
                    s_ring, (220, 40, 40, ring_alpha),
                    (ring_r + ring_w, ring_r + ring_w), ring_r + ring_w // 2, ring_w
                )
                self.tela.blit(s_ring, (centro[0] - ring_r - ring_w, centro[1] - ring_r - ring_w))

            elif medo_val > 0.50:
                # Anel azul frio â€” trÃªmulo
                tremor = int(2 * medo_val * pulso)
                ring_alpha = int(min(180, medo_val * 140))
                ring_r = max(1, raio + self.cam.converter_tam(3))
                ring_w = max(1, self.cam.converter_tam(2))
                s_ring = self._get_surface(ring_r * 2 + ring_w * 2 + tremor * 2, ring_r * 2 + ring_w * 2 + tremor * 2, pygame.SRCALPHA)
                pygame.draw.circle(
                    s_ring, (80, 140, 255, ring_alpha),
                    (ring_r + ring_w + tremor, ring_r + ring_w + tremor), ring_r + ring_w // 2, ring_w
                )
                self.tela.blit(s_ring, (centro[0] - ring_r - ring_w - tremor, centro[1] - ring_r - ring_w - tremor))

            elif excit_val > 0.70:
                # Anel dourado-branco quando excitado (apÃ³s combos ou vitÃ³rias parciais)
                ring_alpha = int(min(150, excit_val * 120 * pulso))
                ring_r = max(1, raio + self.cam.converter_tam(2))
                ring_w = max(1, self.cam.converter_tam(2))
                s_ring = self._get_surface(ring_r * 2 + ring_w * 2, ring_r * 2 + ring_w * 2, pygame.SRCALPHA)
                pygame.draw.circle(
                    s_ring, (255, 220, 80, ring_alpha),
                    (ring_r + ring_w, ring_r + ring_w), ring_r + ring_w // 2, ring_w
                )
                self.tela.blit(s_ring, (centro[0] - ring_r - ring_w, centro[1] - ring_r - ring_w))
        
        # === EFEITO DE GLOW EM VIDA BAIXA (ADRENALINA) ===
        if l.modo_adrenalina and not l.morto:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150)
            glow_size = int(raio * 1.3)
            s = self._get_surface(glow_size * 2, glow_size * 2, pygame.SRCALPHA)
            glow_alpha = int(60 * pulso)
            pygame.draw.circle(s, (255, 50, 50, glow_alpha), (glow_size, glow_size), glow_size)
            self.tela.blit(s, (centro[0] - glow_size, centro[1] - glow_size))

        pulse_time = pygame.time.get_ticks() / 1000.0
        self._desenhar_buffs_lutador(l, centro, raio, pulse_time)
        self._desenhar_transformacao_lutador(l, centro, raio, pulse_time)

        # === RENDERIZA ARMA COM ANIMAÃƒâ€¡Ãƒâ€¢ES APRIMORADAS ===
        if l.dados.arma_obj:
            # Aplica shake da animaÃ§Ã£o
            shake = getattr(l, 'weapon_anim_shake', (0, 0))
            centro_ajustado = (centro[0] + shake[0], centro[1] + shake[1])
            
            # Escala da animaÃ§Ã£o
            anim_scale = getattr(l, 'weapon_anim_scale', 1.0)
            
            # Desenha slash arc se estiver atacando (para armas melee)
            if l.atacando and _texto_normalizado(l.dados.arma_obj.tipo) in {"reta", "dupla", "corrente", "transformavel"}:
                self._desenhar_slash_arc(l, centro, raio, anim_scale)
            
            self._desenhar_presenca_arma(l, centro_ajustado, raio, anim_scale)

            # Desenha trail antes da arma
            self._desenhar_weapon_trail(l)
            
            # Desenha arma com escala
            self.desenhar_arma(l.dados.arma_obj, centro_ajustado, l.angulo_arma_visual, 
                             l.dados.tamanho, raio, anim_scale)
            self._desenhar_sparks_arma(l, centro_ajustado, raio)

        # === TAG DE NOME (estilo Minecraft) Ã¢â‚¬â€ sempre acima da cabeÃ§a ===
        self._desenhar_nome_tag(l, centro, raio)


    def _desenhar_nome_tag(self, l, centro, raio):
        """Desenha o nome do personagem flutuando acima da cabeÃ§a, estilo Minecraft."""
        nome = l.dados.nome
        hp_pct = l.vida / l.vida_max if l.vida_max > 0 else 0.0

        # PosiÃ§Ã£o: acima do topo do cÃ­rculo (centro jÃ¡ desconta o Z via off_y em desenhar_lutador)
        OFFSET_Y = 14   # pixels acima do topo do cÃ­rculo

        # === FONTE ===
        if not hasattr(self, '_fonte_nametag'):
            self._fonte_nametag = pygame.font.SysFont("Arial", 13, bold=True)
        font = self._fonte_nametag
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


    def _desenhar_slash_arc(self, lutador, centro, raio, anim_scale):
        """Desenha arco de corte visÃ­vel durante ataques melee Ã¢â‚¬â€ v15.0 POLISHED"""
        arma = lutador.dados.arma_obj
        if not arma:
            return
        
        # === ZOOM FACTOR v15.1 ===
        zoom = getattr(self.cam, 'zoom', 1.0)
        
        # Cor do arco baseada na arma
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (255, 255, 255)
        cor_brilho = tuple(min(255, c + 100) for c in cor)
        cor_glow = tuple(min(255, c + 40) for c in cor)
        
        # Progresso da animaÃ§Ã£o
        timer = lutador.timer_animacao
        
        # Perfil da arma para saber a duraÃ§Ã£o total
        from efeitos.weapon_animations import WEAPON_PROFILES
        profile = WEAPON_PROFILES.get(arma.tipo, WEAPON_PROFILES["Reta"])
        total_time = profile.total_time
        
        # Progresso normalizado (0-1)
        prog = 1.0 - (timer / total_time) if total_time > 0 else 0
        
        # SÃ³ desenha durante a fase de ataque principal
        antecipation_end = profile.anticipation_time / total_time
        attack_end = (profile.anticipation_time + profile.attack_time + profile.impact_time) / total_time
        
        if prog < antecipation_end or prog > attack_end + 0.15:
            return
        
        # Calcula fase dentro do ataque
        attack_prog = (prog - antecipation_end) / max(attack_end - antecipation_end, 0.01)
        attack_prog = max(0, min(1, attack_prog))
        
        # ParÃ¢metros do arco
        angulo_base = lutador.angulo_olhar
        arc_start = angulo_base + profile.anticipation_angle
        arc_end = angulo_base + profile.attack_angle
        
        # Ãƒâ€šngulo atual do arco
        current_arc = arc_start + (arc_end - arc_start) * attack_prog
        
        # Raio do arco Ã¢â‚¬â€ maior e mais dramÃ¡tico
        arc_radius = raio * 3.0 * anim_scale
        
        # Alpha com fade suave (ease out)
        fade = 1.0 - attack_prog
        alpha_base = int(220 * fade * fade)  # Quadratic fade
        
        # Largura do arco decrescente
        arc_width_factor = 1.0 - attack_prog * 0.6
        
        # Surface para o arco
        surf_size = int(arc_radius * 3.5)
        if surf_size < 10:
            return
        s = self._get_surface(surf_size, surf_size, pygame.SRCALPHA)
        arc_center = (surf_size // 2, surf_size // 2)
        
        # === CAMADA 1: GLOW EXTERNO (amplo e suave) ===
        num_points = 20
        points_outer_glow = []
        for i in range(num_points + 1):
            t = i / num_points
            angle = math.radians(arc_start + (current_arc - arc_start) * t)
            glow_radius = arc_radius * 1.15
            ox = arc_center[0] + math.cos(angle) * glow_radius
            oy = arc_center[1] + math.sin(angle) * glow_radius
            points_outer_glow.append((ox, oy))
        
        points_inner_glow = []
        for i in range(num_points + 1):
            t = i / num_points
            angle = math.radians(arc_start + (current_arc - arc_start) * t)
            inner_r = arc_radius * 0.5
            ix = arc_center[0] + math.cos(angle) * inner_r
            iy = arc_center[1] + math.sin(angle) * inner_r
            points_inner_glow.append((ix, iy))
        
        if len(points_outer_glow) > 2:
            glow_polygon = points_outer_glow + points_inner_glow[::-1]
            glow_alpha = max(0, min(255, int(alpha_base * 0.25)))
            pygame.draw.polygon(s, (*cor_glow, glow_alpha), glow_polygon)
        
        # === CAMADA 2: ARCO PRINCIPAL (gradiente de dentro para fora) ===
        for layer in range(3):
            layer_t = layer / 3.0
            outer_r = arc_radius * (0.95 - layer_t * 0.15)
            inner_r = arc_radius * (0.65 + layer_t * 0.08)
            
            points_outer = []
            points_inner = []
            for i in range(num_points + 1):
                t = i / num_points
                angle = math.radians(arc_start + (current_arc - arc_start) * t)
                
                # Gradiente de alpha ao longo do arco (mais brilhante na ponta)
                seg_alpha = 0.4 + 0.6 * t
                
                ox = arc_center[0] + math.cos(angle) * outer_r
                oy = arc_center[1] + math.sin(angle) * outer_r
                points_outer.append((ox, oy))
                
                ix = arc_center[0] + math.cos(angle) * inner_r
                iy = arc_center[1] + math.sin(angle) * inner_r
                points_inner.append((ix, iy))
            
            if len(points_outer) > 2:
                arc_polygon = points_outer + points_inner[::-1]
                layer_alpha = max(0, min(255, int(alpha_base * (0.8 - layer_t * 0.3))))
                if layer == 0:
                    arc_color = (*cor_brilho, layer_alpha)
                elif layer == 1:
                    arc_color = (*cor, layer_alpha)
                else:
                    arc_color = (*cor_glow, layer_alpha)
                pygame.draw.polygon(s, arc_color, arc_polygon)
        
        # === CAMADA 3: LINHA DE CORTE BRILHANTE (edge) ===
        edge_points = []
        for i in range(num_points + 1):
            t = i / num_points
            angle = math.radians(arc_start + (current_arc - arc_start) * t)
            edge_r = arc_radius * 0.82
            ex = arc_center[0] + math.cos(angle) * edge_r
            ey = arc_center[1] + math.sin(angle) * edge_r
            edge_points.append((int(ex), int(ey)))
        
        if len(edge_points) > 1:
            edge_alpha = max(0, min(255, int(alpha_base * 0.9)))
            edge_width = max(1, int(5 * zoom * arc_width_factor))
            pygame.draw.lines(s, (*cor_brilho, edge_alpha), False, edge_points, edge_width)
            # Core branco ainda mais fino
            core_alpha = max(0, min(255, int(alpha_base * 0.7)))
            pygame.draw.lines(s, (255, 255, 255, core_alpha), False, edge_points, max(1, edge_width // 2))
        
        # === CAMADA 4: PONTA DO CORTE (leading edge brilhante) ===
        last_angle = math.radians(current_arc)
        tip_x = arc_center[0] + math.cos(last_angle) * arc_radius * 0.82
        tip_y = arc_center[1] + math.sin(last_angle) * arc_radius * 0.82
        tip_size = max(4, int(10 * fade))
        tip_alpha = max(0, min(255, int(255 * fade)))
        pygame.draw.circle(s, (255, 255, 255, tip_alpha), (int(tip_x), int(tip_y)), tip_size)
        pygame.draw.circle(s, (*cor_brilho, max(0, tip_alpha - 50)), (int(tip_x), int(tip_y)), tip_size * 2)
        
        # Blit na posiÃ§Ã£o do lutador
        blit_pos = (centro[0] - arc_center[0], centro[1] - arc_center[1])
        self.tela.blit(s, blit_pos)

    
    def _desenhar_weapon_trail(self, lutador):
        """Desenha trail da arma durante ataques Ã¢â‚¬â€ v15.0 POLISHED com glow"""
        trail = getattr(lutador, 'weapon_trail_positions', [])
        if len(trail) < 2:
            return
        
        arma = lutador.dados.arma_obj
        if not arma:
            return
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (200, 200, 200)
        cor_brilho = tuple(min(255, c + 80) for c in cor)
        tipo = arma.tipo
        estilo = getattr(arma, "estilo", "")

        from utilitarios.config import PPM
        from efeitos.weapon_animations import get_animation_profile, get_weapon_animation_manager
        
        # === ZOOM FACTOR v15.1 ===
        zoom = getattr(self.cam, 'zoom', 1.0)
        
        # Collect screen points
        screen_pts = []
        for i in range(len(trail)):
            x, y, a = trail[i]
            p = self.cam.converter(x * PPM, y * PPM)
            screen_pts.append((p[0], p[1], a))

        try:
            profile = get_animation_profile(tipo, estilo)
            get_weapon_animation_manager().trail_renderer.draw_trail(
                self.tela,
                screen_pts,
                cor,
                tipo,
                profile,
                estilo,
            )
        except Exception as exc:
            _log.debug("Weapon trail advanced render: %s", exc)

        # Desenha segmentos com glow
        for i in range(1, len(screen_pts)):
            x1, y1, a1 = screen_pts[i - 1]
            x2, y2, a2 = screen_pts[i]
            
            alpha = min(a1, a2)
            if alpha < 0.05:
                continue
            
            # Progresso ao longo do trail (0=antigo, 1=recente)
            t = i / len(screen_pts)
            
            # Largura crescente (fino no inÃ­cio, grosso no fim) â€” zoom-scaled v15.1
            base_width = max(1, int(8 * zoom * t * alpha))
            
            if _texto_normalizado(tipo) == "magica":
                # Trail mÃ¡gico: glow intenso com cor vibrante
                glow_width = base_width + max(1, int(4 * zoom))
                glow_alpha = max(0, min(255, int(100 * alpha * t)))
                
                # Glow externo
                surf_w = abs(x2 - x1) + glow_width * 4 + 20
                surf_h = abs(y2 - y1) + glow_width * 4 + 20
                if surf_w > 2 and surf_h > 2:
                    s = pygame.Surface((int(surf_w), int(surf_h)), pygame.SRCALPHA)
                    ox = min(x1, x2) - glow_width * 2 - 10
                    oy = min(y1, y2) - glow_width * 2 - 10
                    lp1 = (int(x1 - ox), int(y1 - oy))
                    lp2 = (int(x2 - ox), int(y2 - oy))
                    pygame.draw.line(s, (*cor, glow_alpha), lp1, lp2, glow_width)
                    pygame.draw.line(s, (*cor_brilho, min(255, int(glow_alpha * 1.5))), lp1, lp2, base_width)
                    pygame.draw.line(s, (255, 255, 255, min(255, int(glow_alpha * 0.8))), lp1, lp2, max(1, base_width // 2))
                    self.tela.blit(s, (int(ox), int(oy)))
            else:
                # Trail de corte: gradiente com core brilhante
                line_alpha = max(0, min(255, int(200 * alpha * t)))
                
                # Camada de glow
                glow_width = base_width + max(1, int(3 * zoom))
                surf_w = abs(x2 - x1) + glow_width * 3 + 16
                surf_h = abs(y2 - y1) + glow_width * 3 + 16
                if surf_w > 2 and surf_h > 2:
                    s = pygame.Surface((int(surf_w), int(surf_h)), pygame.SRCALPHA)
                    ox = min(x1, x2) - glow_width - 8
                    oy = min(y1, y2) - glow_width - 8
                    lp1 = (int(x1 - ox), int(y1 - oy))
                    lp2 = (int(x2 - ox), int(y2 - oy))
                    
                    # Glow externo suave
                    pygame.draw.line(s, (*cor, max(0, line_alpha // 3)), lp1, lp2, glow_width)
                    # Corpo do trail
                    trail_color = tuple(min(255, int(c * 0.6 + 100 * alpha)) for c in cor)
                    pygame.draw.line(s, (*trail_color, line_alpha), lp1, lp2, base_width)
                    # Core branco brilhante
                    if base_width > 3:
                        pygame.draw.line(s, (255, 255, 255, max(0, line_alpha // 2)), lp1, lp2, max(1, base_width // 3))
                    self.tela.blit(s, (int(ox), int(oy)))


    def desenhar_arma(self, arma, centro, angulo, tam_char, raio_char, anim_scale=1.0):
        """
        Renderiza a arma do lutador - VERSÃƒÆ’O APRIMORADA v3.0 + zoom-fix v15.1
        Visual muito mais bonito com gradientes, brilhos e detalhes.
        """
        cx, cy = centro
        rad = math.radians(angulo)
        
        # === ZOOM FACTOR v15.1 â€” escala larguras de linha pela cÃ¢mera ===
        zoom = getattr(self.cam, 'zoom', 1.0)
        def _zw(px):
            """Converte largura em pixels fixos â†’ pixels escalados pelo zoom."""
            return max(1, int(px * zoom))
        
        # Cores da arma com validaÃ§Ã£o
        cor_r = getattr(arma, 'r', 180) or 180
        cor_g = getattr(arma, 'g', 180) or 180
        cor_b = getattr(arma, 'b', 180) or 180
        cor = (int(cor_r), int(cor_g), int(cor_b))
        
        # Cor mais clara para highlights
        cor_clara = tuple(min(255, c + 60) for c in cor)
        # Cor mais escura para sombras
        cor_escura = tuple(max(0, c - 40) for c in cor)
        
        # Cor de raridade para efeitos especiais
        raridade = getattr(arma, 'raridade', 'Comum')
        raridade_norm = _texto_normalizado(raridade)
        cores_raridade = {
            'comum': (180, 180, 180),
            'incomum': (30, 255, 30),
            'raro': (30, 144, 255),
            'epico': (148, 0, 211),
            'lendario': (255, 165, 0),
            'mitico': (255, 20, 147)
        }
        cor_raridade = cores_raridade.get(raridade_norm, (180, 180, 180))
        
        tipo = getattr(arma, 'tipo', 'Reta')
        tipo_norm = _texto_normalizado(tipo)
        estilo_arma = getattr(arma, 'estilo', '')
        estilo_norm = _texto_normalizado(estilo_arma)
        
        # Escala base da arma
        base_scale = raio_char * 0.025  # Escala relativa ao personagem
        
        # Largura da arma proporcional â€” jÃ¡ escala com raio_char (que Ã© zoom-scaled)
        larg_base = max(2, int(raio_char * 0.12 * anim_scale))
        
        # Flag de ataque ativo (para efeitos especiais)
        atacando = anim_scale > 1.05
        tempo = pygame.time.get_ticks()
        
        # Helper para estilos Dupla: polÃ­gono cÃ´nico (base larga Ã¢â€ â€™ ponta)
        def _dupla_blade_poly(bx, by, tx, ty, ang, w_base, w_tip):
            px = math.cos(ang + math.pi/2)
            py = math.sin(ang + math.pi/2)
            return [
                (int(bx - px*w_base), int(by - py*w_base)),
                (int(bx + px*w_base), int(by + py*w_base)),
                (int(tx + px*w_tip),  int(ty + py*w_tip)),
                (int(tx),             int(ty)),
                (int(tx - px*w_tip),  int(ty - py*w_tip)),
            ]

        # === RETA (Espadas, LanÃ§as, Machados) ===
        if tipo_norm == "reta":
            # Geometria fixa por estilo (baseada em raio_char)
            if 'lanca' in estilo_norm or 'estocada' in estilo_norm:
                cabo_len   = raio_char * 1.00
                lamina_len = raio_char * 1.80 * anim_scale
            elif 'maca' in estilo_norm or 'contusao' in estilo_norm:
                cabo_len   = raio_char * 0.90
                lamina_len = raio_char * 0.70 * anim_scale
            else:  # Espada / Misto
                cabo_len   = raio_char * 0.55
                lamina_len = raio_char * 1.30 * anim_scale
            larg = max(_zw(3), int(larg_base * 1.2))

            cabo_end_x = cx + math.cos(rad) * cabo_len
            cabo_end_y = cy + math.sin(rad) * cabo_len
            lamina_end_x = cx + math.cos(rad) * (cabo_len + lamina_len)
            lamina_end_y = cy + math.sin(rad) * (cabo_len + lamina_len)

            perp_x = math.cos(rad + math.pi/2)
            perp_y = math.sin(rad + math.pi/2)

            # Ã¢â€â‚¬Ã¢â€â‚¬ ESTOCADA (LanÃ§a) Ã¢â‚¬â€ haste longa, ponta de metal estreita Ã¢â€â‚¬Ã¢â€â‚¬
            if "lanca" in estilo_norm or "estocada" in estilo_norm:
                # Haste de madeira (mais fina)
                for i in range(2):
                    shade = (90 - i*20, 55 - i*15, 22 - i*8)
                    pygame.draw.line(self.tela, shade,
                                     (int(cx), int(cy)), (int(cabo_end_x), int(cabo_end_y)),
                                     max(2, larg - i*2))
                # Ponteira metÃ¡lica Ã¢â‚¬â€ triÃ¢ngulo estreito e longo
                tip_w = max(2, larg - 2)
                lance_pts = [
                    (int(cabo_end_x - perp_x * tip_w), int(cabo_end_y - perp_y * tip_w)),
                    (int(cabo_end_x + perp_x * tip_w), int(cabo_end_y + perp_y * tip_w)),
                    (int(lamina_end_x + perp_x), int(lamina_end_y + perp_y)),
                    (int(lamina_end_x), int(lamina_end_y)),
                    (int(lamina_end_x - perp_x), int(lamina_end_y - perp_y)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor_escura, lance_pts)
                    pygame.draw.polygon(self.tela, cor, lance_pts, _zw(1))
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                # Anel metÃ¡lico na virola
                pygame.draw.circle(self.tela, (160,165,175), (int(cabo_end_x), int(cabo_end_y)), larg//2 + 1, _zw(2))
                # Fio central da ponta
                pygame.draw.line(self.tela, cor_clara,
                                 (int(cabo_end_x), int(cabo_end_y)),
                                 (int(lamina_end_x), int(lamina_end_y)), 1)

            # Ã¢â€â‚¬Ã¢â€â‚¬ CONTUSÃƒÆ’O (MaÃ§a) Ã¢â‚¬â€ cabo + cabeÃ§a larga com espigÃµes Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            elif "maca" in estilo_norm or "contusao" in estilo_norm:
                # Cabo
                pygame.draw.line(self.tela, (30, 18, 8),
                                 (int(cx)+1, int(cy)+1), (int(cabo_end_x)+1, int(cabo_end_y)+1), larg+2)
                pygame.draw.line(self.tela, (90, 55, 25),
                                 (int(cx), int(cy)), (int(cabo_end_x), int(cabo_end_y)), larg)
                # CabeÃ§a Ã¢â‚¬â€ cilindro largo
                head_half = larg * 1.8
                head_pts = [
                    (int(cabo_end_x - perp_x*head_half), int(cabo_end_y - perp_y*head_half)),
                    (int(cabo_end_x + perp_x*head_half), int(cabo_end_y + perp_y*head_half)),
                    (int(lamina_end_x + perp_x*head_half), int(lamina_end_y + perp_y*head_half)),
                    (int(lamina_end_x - perp_x*head_half), int(lamina_end_y - perp_y*head_half)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor_escura, head_pts)
                    pygame.draw.polygon(self.tela, cor, head_pts, _zw(2))
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                # EspigÃµes nas 4 faces
                mid_x = (cabo_end_x + lamina_end_x) / 2
                mid_y = (cabo_end_y + lamina_end_y) / 2
                for s_sign in [-1, 1]:
                    sx1 = int(mid_x + perp_x * head_half * s_sign)
                    sy1 = int(mid_y + perp_y * head_half * s_sign)
                    sx2 = int(mid_x + perp_x * (head_half + 6) * s_sign)
                    sy2 = int(mid_y + perp_y * (head_half + 6) * s_sign)
                    pygame.draw.line(self.tela, cor_clara, (sx1, sy1), (sx2, sy2), max(2, larg//2))
                # Highlight
                pygame.draw.circle(self.tela, cor_clara, (int(cabo_end_x), int(cabo_end_y)), max(2, larg//3))
                if raridade_norm not in ['comum', 'incomum']:
                    pulso = 0.5 + 0.5 * math.sin(tempo/200)
                    pygame.draw.circle(self.tela, cor_raridade,
                                       (int(lamina_end_x), int(lamina_end_y)), max(3, int(larg*0.8*(1+pulso*0.3))))

            # Ã¢â€â‚¬Ã¢â€â‚¬ CORTE (Espada) Ã¢â‚¬â€ lÃ¢mina larga, guarda, fio Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            else:  # "Espada" in estilo ou "Misto" ou fallback
                # Guarda (oval perpendicular)
                guarda_x = cabo_end_x + math.cos(rad) * 2
                guarda_y = cabo_end_y + math.sin(rad) * 2
                pygame.draw.ellipse(self.tela, (80, 60, 40),
                                    (int(guarda_x - larg*1.5), int(guarda_y - larg*0.8), larg*3, larg*1.6))
                # Cabo com faixas de couro
                for i in range(3):
                    shade = (90 - i*15, 50 - i*10, 20 - i*5)
                    pygame.draw.line(self.tela, shade,
                                     (int(cx)+i-1, int(cy)+i-1),
                                     (int(cabo_end_x)+i-1, int(cabo_end_y)+i-1), max(2, larg - i))
                # LÃ¢mina (polÃ­gono)
                lamina_pts = [
                    (int(cabo_end_x - perp_x*larg*0.6), int(cabo_end_y - perp_y*larg*0.6)),
                    (int(cabo_end_x + perp_x*larg*0.6), int(cabo_end_y + perp_y*larg*0.6)),
                    (int(lamina_end_x - perp_x*larg*0.3), int(lamina_end_y - perp_y*larg*0.3)),
                    (int(lamina_end_x), int(lamina_end_y)),
                    (int(lamina_end_x + perp_x*larg*0.3), int(lamina_end_y + perp_y*larg*0.3)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor, lamina_pts)
                    pygame.draw.polygon(self.tela, cor_escura, lamina_pts, _zw(1))
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                # Fio (highlight)
                mid_x = (cabo_end_x + lamina_end_x) / 2
                mid_y = (cabo_end_y + lamina_end_y) / 2
                pygame.draw.line(self.tela, cor_clara,
                                 (int(cabo_end_x), int(cabo_end_y)), (int(mid_x), int(mid_y)),
                                 max(1, larg//3))
                # Glow de raridade
                if raridade_norm not in ['comum', 'incomum']:
                    pulso = 0.5 + 0.5 * math.sin(tempo/200)
                    pygame.draw.circle(self.tela, cor_raridade,
                                       (int(lamina_end_x), int(lamina_end_y)),
                                       max(3, int(larg*0.8*(1+pulso*0.3))))
                # Glow de ataque
                if atacando:
                    try:
                        gl = pygame.Surface((int(lamina_len*2), int(lamina_len*2)), pygame.SRCALPHA)
                        for r2 in range(3, 0, -1):
                            pygame.draw.line(gl, (*cor_clara, 50//r2),
                                             (int(lamina_len), int(lamina_len)),
                                             (int(lamina_len + math.cos(rad)*lamina_len*0.8),
                                              int(lamina_len + math.sin(rad)*lamina_len*0.8)), larg+r2*2)
                        self.tela.blit(gl, (int(cabo_end_x-lamina_len), int(cabo_end_y-lamina_len)))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
        
        # === DUPLA - ADAGAS GÃƒÅ MEAS v3.0 (Karambit Reverse-Grip) ===
        elif tipo_norm == "dupla":
            sep = raio_char * 0.55  # separaÃ§Ã£o fixa
            larg = max(_zw(3), int(larg_base * 1.1))

            if estilo_norm == "adagas gemeas":
                # Ã¢â€â‚¬Ã¢â€â‚¬ ADAGAS GÃƒÅ MEAS v3.1: Laterais do corpo, empunhadura normal apontando Ã  frente Ã¢â€â‚¬Ã¢â€â‚¬
                # Cada daga fica na mÃ£o do personagem (lateral), lÃ¢mina apontando na direÃ§Ã£o do ataque
                cabo_len   = raio_char * 0.35
                lamina_len = raio_char * 1.05 * anim_scale
                pulso = 0.5 + 0.5 * math.sin(tempo / 180)
                glow_alpha_base = int(100 + 70 * pulso) if atacando else int(35 + 20 * pulso)

                for i, lado_sinal in enumerate([-1, 1]):
                    # Ã¢â€â‚¬Ã¢â€â‚¬ PosiÃ§Ã£o da mÃ£o: lateral ao corpo, fora do centro Ã¢â€â‚¬Ã¢â€â‚¬
                    # sep jÃ¡ dÃ¡ a separaÃ§Ã£o lateral adequada
                    hand_x = cx + math.cos(rad + math.pi/2) * sep * lado_sinal * 0.85
                    hand_y = cy + math.sin(rad + math.pi/2) * sep * lado_sinal * 0.85

                    # Ãƒâ€šngulo da daga: aponta para frente com leve abertura lateral
                    spread_deg = 18 * lado_sinal  # abertura: esquerda vai -18Ã‚Â°, direita vai +18Ã‚Â°
                    daga_ang = rad + math.radians(spread_deg)

                    # Ã¢â€â‚¬Ã¢â€â‚¬ Cabo (handle) Ã¢â€â‚¬Ã¢â€â‚¬
                    cabo_ex = hand_x + math.cos(daga_ang) * cabo_len
                    cabo_ey = hand_y + math.sin(daga_ang) * cabo_len
                    # Sombra
                    pygame.draw.line(self.tela, (30, 18, 8),
                                     (int(hand_x)+1, int(hand_y)+1),
                                     (int(cabo_ex)+1, int(cabo_ey)+1), larg + 3)
                    # Madeira/grip
                    pygame.draw.line(self.tela, (60, 38, 18),
                                     (int(hand_x), int(hand_y)),
                                     (int(cabo_ex), int(cabo_ey)), larg + 2)
                    pygame.draw.line(self.tela, (100, 65, 30),
                                     (int(hand_x), int(hand_y)),
                                     (int(cabo_ex), int(cabo_ey)), max(1, larg))
                    # Faixas de grip
                    for gi in range(1, 4):
                        gt = gi / 4
                        gx = int(hand_x + (cabo_ex - hand_x) * gt)
                        gy = int(hand_y + (cabo_ey - hand_y) * gt)
                        gp_x = math.cos(daga_ang + math.pi/2) * (larg + 1)
                        gp_y = math.sin(daga_ang + math.pi/2) * (larg + 1)
                        pygame.draw.line(self.tela, (45, 28, 10),
                                         (int(gx-gp_x), int(gy-gp_y)),
                                         (int(gx+gp_x), int(gy+gp_y)), 1)

                    # Ã¢â€â‚¬Ã¢â€â‚¬ Guarda cruzada (finger guard) Ã¢â€â‚¬Ã¢â€â‚¬
                    grd_x = math.cos(daga_ang + math.pi/2) * (larg + 3)
                    grd_y = math.sin(daga_ang + math.pi/2) * (larg + 3)
                    pygame.draw.line(self.tela, (150, 155, 165),
                                     (int(cabo_ex - grd_x), int(cabo_ey - grd_y)),
                                     (int(cabo_ex + grd_x), int(cabo_ey + grd_y)), max(2, larg))

                    # Ã¢â€â‚¬Ã¢â€â‚¬ LÃ¢mina: reta com ponta levemente curvada para dentro Ã¢â€â‚¬Ã¢â€â‚¬
                    # Divide em dois segmentos: corpo reto + curva terminal
                    corpo_pct = 0.72  # 72% da lÃ¢mina Ã© reta
                    curva_pct = 0.28  # 28% final curva levemente

                    corpo_end_x = cabo_ex + math.cos(daga_ang) * lamina_len * corpo_pct
                    corpo_end_y = cabo_ey + math.sin(daga_ang) * lamina_len * corpo_pct

                    # Curva da ponta (gira ligeiramente para o centro)
                    curva_deg = -12 * lado_sinal  # curva para dentro
                    curva_ang = daga_ang + math.radians(curva_deg)
                    tip_x = corpo_end_x + math.cos(curva_ang) * lamina_len * curva_pct
                    tip_y = corpo_end_y + math.sin(curva_ang) * lamina_len * curva_pct

                    # Largura da lÃ¢mina (afunila atÃ© a ponta)
                    lam_w_base = max(3, larg - 1)
                    lam_w_tip  = max(1, larg // 3)

                    # Sombra da lÃ¢mina
                    pygame.draw.line(self.tela, (20, 20, 25),
                                     (int(cabo_ex)+1, int(cabo_ey)+1),
                                     (int(tip_x)+1,   int(tip_y)+1), lam_w_base + 2)

                    # Corpo da lÃ¢mina (parte reta)
                    perp_bx = math.cos(daga_ang + math.pi/2)
                    perp_by = math.sin(daga_ang + math.pi/2)
                    lam_poly = [
                        (int(cabo_ex - perp_bx * lam_w_base), int(cabo_ey - perp_by * lam_w_base)),
                        (int(cabo_ex + perp_bx * lam_w_base), int(cabo_ey + perp_by * lam_w_base)),
                        (int(corpo_end_x + perp_bx * lam_w_tip), int(corpo_end_y + perp_by * lam_w_tip)),
                        (int(tip_x), int(tip_y)),
                        (int(corpo_end_x - perp_bx * lam_w_tip), int(corpo_end_y - perp_by * lam_w_tip)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, lam_poly)
                        pygame.draw.polygon(self.tela, cor, lam_poly, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    # Fio da lÃ¢mina (highlight central)
                    pygame.draw.line(self.tela, cor_clara,
                                     (int(cabo_ex), int(cabo_ey)),
                                     (int(corpo_end_x), int(corpo_end_y)), 1)

                    # Ã¢â€â‚¬Ã¢â€â‚¬ Glow de energia durante ataque Ã¢â€â‚¬Ã¢â€â‚¬
                    if atacando or glow_alpha_base > 50:
                        try:
                            sz = max(8, int(lamina_len * 2))
                            gs = self._get_surface(sz * 2, sz * 2, pygame.SRCALPHA)
                            mid_x = int((cabo_ex + tip_x) / 2) - sz
                            mid_y = int((cabo_ey + tip_y) / 2) - sz
                            local_s = (sz - int(cabo_ex - mid_x - sz), sz - int(cabo_ey - mid_y - sz))
                            local_e = (sz - int(cabo_ex - mid_x - sz) + int(tip_x - cabo_ex),
                                       sz - int(cabo_ey - mid_y - sz) + int(tip_y - cabo_ey))
                            pygame.draw.line(gs, (*cor, glow_alpha_base),
                                             (max(0,min(sz*2-1,local_s[0])), max(0,min(sz*2-1,local_s[1]))),
                                             (max(0,min(sz*2-1,local_e[0])), max(0,min(sz*2-1,local_e[1]))),
                                             max(4, lam_w_base + 3))
                            self.tela.blit(gs, (mid_x, mid_y))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Ã¢â€â‚¬Ã¢â€â‚¬ Runa na lÃ¢mina (raridade) Ã¢â€â‚¬Ã¢â€â‚¬
                    if raridade_norm not in ['comum', 'incomum']:
                        rune_x = int((cabo_ex + corpo_end_x) / 2)
                        rune_y = int((cabo_ey + corpo_end_y) / 2)
                        rune_a = int(160 + 80 * math.sin(tempo / 120 + i * math.pi))
                        try:
                            rs = pygame.Surface((_zw(8), _zw(8)), pygame.SRCALPHA)
                            pygame.draw.circle(rs, (*cor_raridade, rune_a), (4, 4), 3)
                            self.tela.blit(rs, (rune_x - 4, rune_y - 4))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Ã¢â€â‚¬Ã¢â€â‚¬ Ponta brilhante Ã¢â€â‚¬Ã¢â€â‚¬
                    tip_r = max(2, larg - 1)
                    tip_a = int(160 + 80 * math.sin(tempo / 90 + i))
                    try:
                        ts = self._get_surface(tip_r * 5, tip_r * 5, pygame.SRCALPHA)
                        pygame.draw.circle(ts, (*cor_clara, tip_a), (tip_r*2, tip_r*2), tip_r * 2)
                        self.tela.blit(ts, (int(tip_x) - tip_r*2, int(tip_y) - tip_r*2))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    tip_cor = cor_raridade if raridade_norm != 'comum' else cor_clara
                    pygame.draw.circle(self.tela, tip_cor, (int(tip_x), int(tip_y)), tip_r)

            else:
                # Ã¢â€â‚¬Ã¢â€â‚¬ PER-STYLE RENDERERS para os demais estilos Dupla Ã¢â€â‚¬Ã¢â€â‚¬
                # Kamas, Sai, Garras, Tonfas, Facas TÃ¡ticas Ã¢â‚¬â€ cada um com visual Ãºnico
                cabo_len   = raio_char * 0.40
                lamina_len = raio_char * 0.90 * anim_scale
                lw         = max(3, larg)
                pulso      = 0.5 + 0.5 * math.sin(tempo / 180)

                for i, lado_sinal in enumerate([-1, 1]):
                    # PosiÃ§Ã£o da mÃ£o
                    hand_x = cx + math.cos(rad + math.pi/2) * sep * lado_sinal * 0.8
                    hand_y = cy + math.sin(rad + math.pi/2) * sep * lado_sinal * 0.8
                    # Ãƒâ€šngulo com leve abertura lateral
                    spread = math.radians(20 * lado_sinal)
                    ang    = rad + spread

                    # Ponta do cabo
                    cabo_ex = hand_x + math.cos(ang) * cabo_len
                    cabo_ey = hand_y + math.sin(ang) * cabo_len

                    # Ponto final da lÃ¢mina
                    tip_x = cabo_ex + math.cos(ang) * lamina_len
                    tip_y = cabo_ey + math.sin(ang) * lamina_len

                    # Ã¢â€â‚¬Ã¢â€â‚¬ KAMAS: foice Ã¢â‚¬â€ cabo + lÃ¢mina curva perpendicular Ã¢â€â‚¬Ã¢â€â‚¬
                    if estilo_norm == "kamas":
                        # Cabo
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(hand_x)+1, int(hand_y)+1), (int(cabo_ex)+1, int(cabo_ey)+1), lw+2)
                        pygame.draw.line(self.tela, (90, 55, 25),
                                         (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw)
                        # Guarda (crossguard)
                        g_perp_x = math.cos(ang + math.pi/2) * (lw + 4)
                        g_perp_y = math.sin(ang + math.pi/2) * (lw + 4)
                        pygame.draw.line(self.tela, (160, 165, 175),
                                         (int(cabo_ex - g_perp_x), int(cabo_ey - g_perp_y)),
                                         (int(cabo_ex + g_perp_x), int(cabo_ey + g_perp_y)), max(2, lw-1))
                        # LÃ¢mina curva (arco): gira 90Ã‚Â° para o interior
                        curve_ang  = ang + math.pi/2 * lado_sinal
                        ctrl_x = cabo_ex + math.cos(curve_ang) * lamina_len * 0.5
                        ctrl_y = cabo_ey + math.sin(curve_ang) * lamina_len * 0.5
                        hook_x = cabo_ex + math.cos(curve_ang) * lamina_len
                        hook_y = cabo_ey + math.sin(curve_ang) * lamina_len
                        # BÃ©zier aproximado: dividir em 8 segmentos
                        prev = (int(cabo_ex), int(cabo_ey))
                        for seg in range(1, 9):
                            t = seg / 8
                            bx = (1-t)**2*cabo_ex + 2*(1-t)*t*ctrl_x + t**2*hook_x
                            by = (1-t)**2*cabo_ey + 2*(1-t)*t*ctrl_y + t**2*hook_y
                            pygame.draw.line(self.tela, cor, prev, (int(bx), int(by)), lw)
                            prev = (int(bx), int(by))
                        # Glow na ponta
                        glow_r = max(3, lw)
                        try:
                            gs = self._get_surface(glow_r*4, glow_r*4, pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor_clara, int(150+80*pulso)), (glow_r*2, glow_r*2), glow_r*2)
                            self.tela.blit(gs, (int(hook_x)-glow_r*2, int(hook_y)-glow_r*2))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        pygame.draw.circle(self.tela, cor_raridade, (int(hook_x), int(hook_y)), glow_r)

                    # Ã¢â€â‚¬Ã¢â€â‚¬ SAI: tridente Ã¢â‚¬â€ lÃ¢mina central + duas guardas diagonais Ã¢â€â‚¬Ã¢â€â‚¬
                    elif estilo_norm == "sai":
                        # Cabo
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(hand_x)+1, int(hand_y)+1), (int(cabo_ex)+1, int(cabo_ey)+1), lw+2)
                        pygame.draw.line(self.tela, (90, 55, 25),
                                         (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw)
                        # LÃ¢mina central
                        lam_poly_c = _dupla_blade_poly(hand_x, hand_y, tip_x, tip_y, ang, lw, lw//2)
                        try:
                            pygame.draw.polygon(self.tela, cor_escura, lam_poly_c)
                            pygame.draw.polygon(self.tela, cor, lam_poly_c, _zw(1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        pygame.draw.line(self.tela, cor_clara, (int(cabo_ex), int(cabo_ey)), (int(tip_x), int(tip_y)), _zw(1))
                        # Guardas (asas do Sai) Ã¢â‚¬â€ partem do final do cabo em diagonal
                        asa_len = lamina_len * 0.4
                        for asa_sinal in [-1, 1]:
                            asa_ang = ang + math.pi/2 * asa_sinal * 0.7
                            ax = cabo_ex + math.cos(asa_ang) * asa_len
                            ay = cabo_ey + math.sin(asa_ang) * asa_len
                            pygame.draw.line(self.tela, (180, 185, 195),
                                             (int(cabo_ex), int(cabo_ey)), (int(ax), int(ay)), max(1, lw-1))
                            pygame.draw.circle(self.tela, (200, 205, 215), (int(ax), int(ay)), max(2, lw-2))
                        # Ponta central
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip_x), int(tip_y)), max(2, lw-1))

                    # Ã¢â€â‚¬Ã¢â€â‚¬ GARRAS: 3 lÃ¢minas curtas em leque de uma base knuckle Ã¢â€â‚¬Ã¢â€â‚¬
                    elif estilo_norm == "garras":
                        # Base (knuckle duster)
                        perp_x = math.cos(ang + math.pi/2) * (lw + 3)
                        perp_y = math.sin(ang + math.pi/2) * (lw + 3)
                        base_pts = [
                            (int(hand_x - perp_x), int(hand_y - perp_y)),
                            (int(hand_x + perp_x), int(hand_y + perp_y)),
                            (int(cabo_ex + perp_x), int(cabo_ey + perp_y)),
                            (int(cabo_ex - perp_x), int(cabo_ey - perp_y)),
                        ]
                        try:
                            pygame.draw.polygon(self.tela, (55, 30, 12), base_pts)
                            pygame.draw.polygon(self.tela, (100, 65, 30), base_pts, _zw(1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        # 3 garras em leque: -25Ã‚Â°, 0Ã‚Â°, +25Ã‚Â°
                        garra_len = lamina_len * 0.7
                        for ga_deg in [-25 * lado_sinal, 0, 25 * lado_sinal]:
                            ga = ang + math.radians(ga_deg)
                            gx = cabo_ex + math.cos(ga) * garra_len
                            gy = cabo_ey + math.sin(ga) * garra_len
                            pygame.draw.line(self.tela, cor_escura, (int(cabo_ex)+1, int(cabo_ey)+1), (int(gx)+1, int(gy)+1), max(1, lw-1)+1)
                            pygame.draw.line(self.tela, cor,         (int(cabo_ex),   int(cabo_ey)),   (int(gx),   int(gy)),   max(1, lw-1))
                            pygame.draw.line(self.tela, cor_clara,   (int(cabo_ex),   int(cabo_ey)),   (int(gx),   int(gy)),   1)
                            pygame.draw.circle(self.tela, cor_raridade, (int(gx), int(gy)), max(2, lw-2))
                        # Glow de ataque nas garras
                        if atacando:
                            try:
                                sz = int(garra_len * 2.5)
                                gs = self._get_surface(sz, sz, pygame.SRCALPHA)
                                pygame.draw.circle(gs, (*cor, int(80*pulso)), (sz//2, sz//2), sz//2)
                                self.tela.blit(gs, (int(cabo_ex)-sz//2, int(cabo_ey)-sz//2))
                            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Ã¢â€â‚¬Ã¢â€â‚¬ TONFAS: bastÃ£o-L Ã¢â‚¬â€ braÃ§o longo + cabo perpendicular curto Ã¢â€â‚¬Ã¢â€â‚¬
                    elif estilo_norm == "tonfas":
                        # BraÃ§o principal (lÃ¢mina = comprimento do bastÃ£o)
                        pygame.draw.line(self.tela, (20, 18, 20),
                                         (int(hand_x)+1, int(hand_y)+1), (int(tip_x)+1, int(tip_y)+1), lw+3)
                        pygame.draw.line(self.tela, cor, (int(hand_x), int(hand_y)), (int(tip_x), int(tip_y)), lw+1)
                        pygame.draw.line(self.tela, cor_clara, (int(hand_x), int(hand_y)), (int(tip_x), int(tip_y)), _zw(1))
                        # Cabo perpendicular (pega) Ã¢â‚¬â€ 1/4 do braÃ§o a partir da mÃ£o
                        pivot_x = hand_x + math.cos(ang) * lamina_len * 0.28
                        pivot_y = hand_y + math.sin(ang) * lamina_len * 0.28
                        handle_ang = ang + math.pi/2 * lado_sinal
                        grip_x = pivot_x + math.cos(handle_ang) * cabo_len
                        grip_y = pivot_y + math.sin(handle_ang) * cabo_len
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(pivot_x)+1, int(pivot_y)+1), (int(grip_x)+1, int(grip_y)+1), lw+2)
                        pygame.draw.line(self.tela, (90, 55, 25),
                                         (int(pivot_x), int(pivot_y)), (int(grip_x), int(grip_y)), lw)
                        # Pontas brilhantes
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip_x),  int(tip_y)),  max(2, lw-1))
                        pygame.draw.circle(self.tela, (180, 185, 195), (int(grip_x), int(grip_y)), max(2, lw-2))
                        # Faixas de grip no cabo perpendicular
                        for fi in [0.35, 0.65]:
                            fx = int(pivot_x + (grip_x - pivot_x) * fi)
                            fy = int(pivot_y + (grip_y - pivot_y) * fi)
                            pygame.draw.circle(self.tela, (50, 28, 10), (fx, fy), max(2, lw-1))

                    # Ã¢â€â‚¬Ã¢â€â‚¬ FACAS TÃTICAS (e fallback genÃ©rico): lÃ¢mina militar reta com fio Ã¢â€â‚¬Ã¢â€â‚¬
                    else:
                        # Cabo com serrilha
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(hand_x)+1, int(hand_y)+1), (int(cabo_ex)+1, int(cabo_ey)+1), lw+2)
                        pygame.draw.line(self.tela, (80, 48, 20),
                                         (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw+1)
                        # Faixas de grip no cabo
                        for gi in range(1, 4):
                            gt = gi / 4
                            gx = int(hand_x + (cabo_ex - hand_x) * gt)
                            gy = int(hand_y + (cabo_ey - hand_y) * gt)
                            gp_x = math.cos(ang + math.pi/2) * (lw + 1)
                            gp_y = math.sin(ang + math.pi/2) * (lw + 1)
                            pygame.draw.line(self.tela, (45, 26, 8),
                                             (int(gx-gp_x), int(gy-gp_y)), (int(gx+gp_x), int(gy+gp_y)), 1)
                        # Guarda (crossguard)
                        g_perp_x = math.cos(ang + math.pi/2) * (lw + 4)
                        g_perp_y = math.sin(ang + math.pi/2) * (lw + 4)
                        pygame.draw.line(self.tela, (160, 165, 175),
                                         (int(cabo_ex - g_perp_x), int(cabo_ey - g_perp_y)),
                                         (int(cabo_ex + g_perp_x), int(cabo_ey + g_perp_y)), max(2, lw-1))
                        # LÃ¢mina: polÃ­gono cÃ´nico
                        lam_poly = _dupla_blade_poly(hand_x, hand_y, tip_x, tip_y, ang, lw, max(1, lw//2))
                        try:
                            pygame.draw.polygon(self.tela, cor_escura, lam_poly)
                            pygame.draw.polygon(self.tela, cor,        lam_poly, _zw(1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        # Fio central
                        pygame.draw.line(self.tela, cor_clara, (int(cabo_ex), int(cabo_ey)), (int(tip_x), int(tip_y)), _zw(1))
                        # Serrilha no dorso (4 dentes)
                        perp_x = math.cos(ang + math.pi/2) * (lw + 1)
                        perp_y = math.sin(ang + math.pi/2) * (lw + 1)
                        for si in range(1, 5):
                            st  = si / 5
                            sx  = cabo_ex + (tip_x - cabo_ex) * st
                            sy  = cabo_ey + (tip_y - cabo_ey) * st
                            ts  = 0.04
                            tsx = cabo_ex + (tip_x - cabo_ex) * (st - ts)
                            tsy = cabo_ey + (tip_y - cabo_ey) * (st - ts)
                            pygame.draw.line(self.tela, cor_clara,
                                             (int(sx + perp_x), int(sy + perp_y)),
                                             (int(tsx + perp_x*2.5), int(tsy + perp_y*2.5)), 1)
                        # Glow de ataque
                        glow_a = int(100 + 70 * pulso) if atacando else int(30 + 15 * pulso)
                        try:
                            sz = max(8, int(lamina_len * 2))
                            gs = self._get_surface(sz*2, sz*2, pygame.SRCALPHA)
                            mid_x = int((cabo_ex + tip_x) / 2) - sz
                            mid_y = int((cabo_ey + tip_y) / 2) - sz
                            ls = (sz - int(cabo_ex - mid_x - sz), sz - int(cabo_ey - mid_y - sz))
                            le = (sz - int(cabo_ex - mid_x - sz) + int(tip_x - cabo_ex),
                                  sz - int(cabo_ey - mid_y - sz) + int(tip_y - cabo_ey))
                            pygame.draw.line(gs, (*cor, glow_a),
                                             (max(0,min(sz*2-1,ls[0])), max(0,min(sz*2-1,ls[1]))),
                                             (max(0,min(sz*2-1,le[0])), max(0,min(sz*2-1,le[1]))),
                                             max(4, lw+2))
                            self.tela.blit(gs, (mid_x, mid_y))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        # Ponta brilhante
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip_x), int(tip_y)), max(2, lw-1))

        
        # === CORRENTE v4.0 (Mangual / Meteor Hammer / Kusarigama / Chicote / Peso) ===
        elif tipo_norm == "corrente":

            if "mangual" in estilo_norm or "flail" in estilo_norm:
                # Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
                # Ã¢â€â‚¬Ã¢â€â‚¬ MANGUAL v4.0: ESTRELA DA MANHÃƒÆ’ (Morning Star) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                # Visual: Cabo reforÃ§ado de aÃ§o Ã¢â€ â€™ elos ovais articulados Ã¢â€ â€™
                #         cabeÃ§a cristalina em forma de estrela com glow interno
                # Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
                cabo_tam      = raio_char * 0.65
                corrente_comp = raio_char * 1.50 * anim_scale
                head_r = max(7, int(raio_char * 0.24 * anim_scale))
                num_elos = 7
                pulso = 0.5 + 0.5 * math.sin(tempo / 200)
                breath = 0.5 + 0.5 * math.sin(tempo / 350)  # RespiraÃ§Ã£o lenta

                # Ã¢â€â‚¬Ã¢â€â‚¬ 1. Cabo de aÃ§o reforÃ§ado Ã¢â€â‚¬Ã¢â€â‚¬
                cabo_ex = cx + math.cos(rad) * cabo_tam
                cabo_ey = cy + math.sin(rad) * cabo_tam
                perp_cx = math.cos(rad + math.pi/2)
                perp_cy = math.sin(rad + math.pi/2)
                # Sombra
                pygame.draw.line(self.tela, (20, 18, 25),
                    (int(cx)+2, int(cy)+2), (int(cabo_ex)+2, int(cabo_ey)+2), max(7, larg_base+5))
                # Corpo metÃ¡lico escuro
                pygame.draw.line(self.tela, (55, 50, 65),
                    (int(cx), int(cy)), (int(cabo_ex), int(cabo_ey)), max(6, larg_base+4))
                # Highlight central (brilho do metal)
                pygame.draw.line(self.tela, (110, 105, 125),
                    (int(cx), int(cy)), (int(cabo_ex), int(cabo_ey)), max(2, larg_base))
                # Grip de couro tranÃ§ado (3 faixas diagonais)
                for fi in range(1, 4):
                    ft = 0.15 + fi * 0.22
                    fx = cx + (cabo_ex - cx) * ft
                    fy = cy + (cabo_ey - cy) * ft
                    g_perp = larg_base + 3
                    pygame.draw.line(self.tela, (40, 25, 15),
                        (int(fx - perp_cx*g_perp), int(fy - perp_cy*g_perp)),
                        (int(fx + perp_cx*g_perp), int(fy + perp_cy*g_perp)), 2)
                # Pommel (base do cabo Ã¢â‚¬â€ pequeno orbe)
                pygame.draw.circle(self.tela, (70, 65, 80), (int(cx), int(cy)), max(3, larg_base//2+1))
                pygame.draw.circle(self.tela, cor_raridade, (int(cx), int(cy)), max(2, larg_base//2), _zw(1))

                # Ã¢â€â‚¬Ã¢â€â‚¬ 2. PivÃ´ articulado com runas Ã¢â€â‚¬Ã¢â€â‚¬
                piv_r = max(5, larg_base + 2)
                pygame.draw.circle(self.tela, (45, 42, 55), (int(cabo_ex), int(cabo_ey)), piv_r + 2)
                pygame.draw.circle(self.tela, (130, 125, 145), (int(cabo_ex), int(cabo_ey)), piv_r, _zw(2))
                # Mini runas pulsantes no pivÃ´
                for ri in range(3):
                    r_ang = tempo / 300 + ri * math.pi * 2 / 3
                    rx = cabo_ex + math.cos(r_ang) * (piv_r - 1)
                    ry = cabo_ey + math.sin(r_ang) * (piv_r - 1)
                    rune_a = int(120 + 80 * math.sin(tempo / 180 + ri))
                    try:
                        rs = pygame.Surface((_zw(6), _zw(6)), pygame.SRCALPHA)
                        pygame.draw.circle(rs, (*cor_raridade, min(255, rune_a)), (3, 3), 3)
                        self.tela.blit(rs, (int(rx)-3, int(ry)-3))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                # Ã¢â€â‚¬Ã¢â€â‚¬ 3. Corrente com elos ovais articulados Ã¢â€â‚¬Ã¢â€â‚¬
                chain_pts = []
                sag = corrente_comp * 0.06 * (1 + 0.05 * math.sin(tempo / 250))
                for ei in range(num_elos + 1):
                    t = ei / num_elos
                    base_px = cabo_ex + math.cos(rad) * corrente_comp * t
                    base_py = cabo_ey + math.sin(rad) * corrente_comp * t
                    # OndulaÃ§Ã£o gravitacional + micro-oscilaÃ§Ã£o
                    grav = sag * math.sin(t * math.pi)
                    wave = math.sin(t * math.pi * 2.5 + tempo / 180) * raio_char * 0.025 * (1 - t * 0.3)
                    off_x = perp_cx * (wave + grav * 0.3)
                    off_y = perp_cy * (wave + grav * 0.3) + grav * 0.7
                    chain_pts.append((base_px + off_x, base_py + off_y))

                # Elos articulados: ovais alternando orientaÃ§Ã£o
                for ei in range(len(chain_pts)):
                    ex, ey = chain_pts[ei]
                    elo_ang = rad + (math.pi/2 if ei % 2 == 0 else 0) + math.sin(tempo/200 + ei) * 0.15
                    ew = max(4, larg_base + 1)
                    eh = max(3, larg_base - 1)
                    # Cada elo como elipse orientada
                    e_perp_x = math.cos(elo_ang) * ew
                    e_perp_y = math.sin(elo_ang) * ew
                    e_fwd_x = math.cos(elo_ang + math.pi/2) * eh
                    e_fwd_y = math.sin(elo_ang + math.pi/2) * eh
                    elo_pts = [
                        (int(ex - e_perp_x - e_fwd_x), int(ey - e_perp_y - e_fwd_y)),
                        (int(ex + e_perp_x - e_fwd_x), int(ey + e_perp_y - e_fwd_y)),
                        (int(ex + e_perp_x + e_fwd_x), int(ey + e_perp_y + e_fwd_y)),
                        (int(ex - e_perp_x + e_fwd_x), int(ey - e_perp_y + e_fwd_y)),
                    ]
                    try:
                        # Gradiente: elos ficam mais claros conforme se aproximam da cabeÃ§a
                        shade = min(255, 75 + int(ei * 12))
                        pygame.draw.polygon(self.tela, (shade, shade-5, shade+8), elo_pts)
                        pygame.draw.polygon(self.tela, (min(255, shade+40), min(255, shade+35), min(255, shade+50)), elo_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                # Ã¢â€â‚¬Ã¢â€â‚¬ 4. CabeÃ§a Ã¢â‚¬â€ Estrela da ManhÃ£ (Morning Star) Ã¢â€â‚¬Ã¢â€â‚¬
                if chain_pts:
                    hx, hy = chain_pts[-1]
                    # Trail de cometa quando atacando
                    if atacando and len(chain_pts) >= 3:
                        trail_pts = chain_pts[-4:]
                        for ti in range(len(trail_pts)-1):
                            t_alpha = int(60 + 80 * (ti / len(trail_pts)))
                            t_r = max(2, int(head_r * (0.3 + 0.4 * ti / len(trail_pts))))
                            try:
                                ts = self._get_surface(t_r*2, t_r*2, pygame.SRCALPHA)
                                pygame.draw.circle(ts, (*cor, min(255, t_alpha)), (t_r, t_r), t_r)
                                self.tela.blit(ts, (int(trail_pts[ti][0])-t_r, int(trail_pts[ti][1])-t_r))
                            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Glow interno (energia pulsante)
                    glow_r = int(head_r * (1.8 + 0.4 * breath))
                    try:
                        gs = self._get_surface(glow_r*2, glow_r*2, pygame.SRCALPHA)
                        glow_a = int(50 + 40 * breath) if not atacando else int(140 * anim_scale)
                        pygame.draw.circle(gs, (*cor, min(255, glow_a)), (glow_r, glow_r), glow_r)
                        self.tela.blit(gs, (int(hx)-glow_r, int(hy)-glow_r))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Sombra da cabeÃ§a
                    pygame.draw.circle(self.tela, (12, 10, 18), (int(hx)+3, int(hy)+3), head_r+2)

                    # Esfera central com gradiente (escuro Ã¢â€ â€™ claro)
                    pygame.draw.circle(self.tela, cor_escura, (int(hx), int(hy)), head_r)
                    pygame.draw.circle(self.tela, cor, (int(hx), int(hy)), head_r - 1)
                    # Highlight esfÃ©rico (reflexo de luz)
                    hl_x = int(hx - head_r * 0.25)
                    hl_y = int(hy - head_r * 0.25)
                    pygame.draw.circle(self.tela, cor_clara, (hl_x, hl_y), max(2, head_r // 3))

                    # 8 Espinhos facetados em estrela (Morning Star)
                    num_spikes = 8
                    spike_rot = tempo / 120  # RotaÃ§Ã£o lenta das pontas
                    for si in range(num_spikes):
                        s_ang = spike_rot + si * math.pi * 2 / num_spikes
                        # Spike principal Ã¢â‚¬â€ losango facetado (4 pontos)
                        spike_len = head_r * 0.85
                        spike_w = max(2, head_r // 3)
                        # Ponta exterior
                        tip_x = hx + math.cos(s_ang) * (head_r + spike_len)
                        tip_y = hy + math.sin(s_ang) * (head_r + spike_len)
                        # Lados perpendiculares (losango)
                        mid_x = hx + math.cos(s_ang) * (head_r + spike_len * 0.25)
                        mid_y = hy + math.sin(s_ang) * (head_r + spike_len * 0.25)
                        s_perp_x = math.cos(s_ang + math.pi/2) * spike_w
                        s_perp_y = math.sin(s_ang + math.pi/2) * spike_w
                        # Base na superfÃ­cie
                        base_x = hx + math.cos(s_ang) * (head_r - 1)
                        base_y = hy + math.sin(s_ang) * (head_r - 1)
                        diamond = [
                            (int(base_x), int(base_y)),
                            (int(mid_x - s_perp_x), int(mid_y - s_perp_y)),
                            (int(tip_x), int(tip_y)),
                            (int(mid_x + s_perp_x), int(mid_y + s_perp_y)),
                        ]
                        try:
                            pygame.draw.polygon(self.tela, cor, diamond)
                            # Borda luminosa nos spikes
                            pygame.draw.polygon(self.tela, cor_clara, diamond, _zw(1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Anel equatorial com runas girando
                    ring_r = int(head_r * 0.75)
                    pygame.draw.circle(self.tela, cor_escura, (int(hx), int(hy)), ring_r, _zw(2))
                    # 4 runas orbitando o anel
                    for ri in range(4):
                        rune_ang = tempo / 200 + ri * math.pi / 2
                        rune_x = hx + math.cos(rune_ang) * ring_r
                        rune_y = hy + math.sin(rune_ang) * ring_r
                        rune_brightness = int(160 + 80 * math.sin(tempo/150 + ri * 1.5))
                        try:
                            rs = pygame.Surface((_zw(6), _zw(6)), pygame.SRCALPHA)
                            pygame.draw.circle(rs, (*cor_raridade, min(255, rune_brightness)), (3, 3), 3)
                            self.tela.blit(rs, (int(rune_x)-3, int(rune_y)-3))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Onda de impacto no chÃ£o (ground ring) quando atacando
                    if atacando:
                        ring_prog = min(1.0, (anim_scale - 1.05) * 5)
                        impact_r = int(head_r * 2.5 * ring_prog)
                        if impact_r > 3:
                            try:
                                irs = self._get_surface(impact_r*2+4, impact_r*2+4, pygame.SRCALPHA)
                                ring_a = int(180 * (1 - ring_prog * 0.7))
                                pygame.draw.circle(irs, (*cor_raridade, ring_a),
                                    (impact_r+2, impact_r+2), impact_r, max(2, larg_base//2))
                                self.tela.blit(irs, (int(hx)-impact_r-2, int(hy)-impact_r-2))
                            except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                    # Glow de raridade (anel externo pulsante)
                    if raridade_norm != 'comum':
                        rar_a = int(80 + 60 * pulso)
                        rar_r = head_r + int(head_r * 0.6 * breath)
                        try:
                            rs = self._get_surface(rar_r*4, rar_r*4, pygame.SRCALPHA)
                            pygame.draw.circle(rs, (*cor_raridade, rar_a), (rar_r*2, rar_r*2), rar_r)
                            self.tela.blit(rs, (int(hx)-rar_r*2, int(hy)-rar_r*2))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

            elif "meteor" in estilo_norm:
                # Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
                # Ã¢â€â‚¬Ã¢â€â‚¬ METEOR HAMMER v1.0: Bola flamejante em corrente longa Ã¢â€â‚¬Ã¢â€â‚¬
                # Visual: Sem cabo Ã¢â€ â€™ corrente longa Ã¢â€ â€™ esfera em chamas
                # Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
                corrente_comp = raio_char * 2.40 * anim_scale
                head_r = max(6, int(raio_char * 0.22 * anim_scale))
                num_elos = 10
                pulso = 0.5 + 0.5 * math.sin(tempo / 150)
                rot_speed = tempo / 100

                # Corrente longa desde a mÃ£o
                chain_pts = []
                for ei in range(num_elos + 1):
                    t = ei / num_elos
                    base_px = cx + math.cos(rad) * corrente_comp * t
                    base_py = cy + math.sin(rad) * corrente_comp * t
                    # Espiral quando atacando, ondulaÃ§Ã£o quando idle
                    if atacando:
                        wave = math.sin(t * math.pi * 4 + rot_speed) * raio_char * 0.08 * (1 - t * 0.3)
                    else:
                        wave = math.sin(t * math.pi * 2 + tempo / 200) * raio_char * 0.05
                    perp_x2 = math.cos(rad + math.pi/2) * wave
                    perp_y2 = math.sin(rad + math.pi/2) * wave
                    chain_pts.append((base_px + perp_x2, base_py + perp_y2))

                # Elos simples (cÃ­rculos conectados)
                if len(chain_pts) > 1:
                    for j in range(len(chain_pts)-1):
                        pygame.draw.line(self.tela, (80, 75, 70),
                            (int(chain_pts[j][0]), int(chain_pts[j][1])),
                            (int(chain_pts[j+1][0]), int(chain_pts[j+1][1])), max(2, larg_base-1))
                    for j in range(0, len(chain_pts), 2):
                        pygame.draw.circle(self.tela, (100, 95, 85),
                            (int(chain_pts[j][0]), int(chain_pts[j][1])), max(2, larg_base//2))

                # CabeÃ§a flamejante
                if chain_pts:
                    mx, my = chain_pts[-1]
                    # Aura de fogo
                    fire_r = int(head_r * (2.2 + 0.5 * pulso))
                    try:
                        fs = self._get_surface(fire_r*2, fire_r*2, pygame.SRCALPHA)
                        pygame.draw.circle(fs, (255, 80, 20, int(60 + 40*pulso)), (fire_r, fire_r), fire_r)
                        pygame.draw.circle(fs, (255, 160, 40, int(40 + 30*pulso)), (fire_r, fire_r), int(fire_r*0.7))
                        self.tela.blit(fs, (int(mx)-fire_r, int(my)-fire_r))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    # Esfera metÃ¡lica
                    pygame.draw.circle(self.tela, (40, 35, 30), (int(mx)+2, int(my)+2), head_r+1)
                    pygame.draw.circle(self.tela, cor_escura, (int(mx), int(my)), head_r)
                    pygame.draw.circle(self.tela, cor, (int(mx), int(my)), head_r-1)
                    pygame.draw.circle(self.tela, cor_clara, (int(mx)-head_r//3, int(my)-head_r//3), max(2, head_r//3))
                    # PartÃ­culas de fogo (4 chamas giratÃ³rias)
                    for fi in range(4):
                        f_ang = rot_speed * 2 + fi * math.pi / 2
                        f_dist = head_r + head_r * 0.4 * math.sin(tempo/80 + fi)
                        f_x = mx + math.cos(f_ang) * f_dist
                        f_y = my + math.sin(f_ang) * f_dist
                        f_size = max(2, int(head_r * 0.35))
                        try:
                            fs = self._get_surface(f_size*2, f_size*2, pygame.SRCALPHA)
                            pygame.draw.circle(fs, (255, 120+int(80*pulso), 20, int(150+50*pulso)), (f_size, f_size), f_size)
                            self.tela.blit(fs, (int(f_x)-f_size, int(f_y)-f_size))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

            else:
                # Ã¢â€â‚¬Ã¢â€â‚¬ PER-STYLE RENDERERS: Kusarigama, Chicote, Corrente com Peso Ã¢â€â‚¬Ã¢â€â‚¬
                comp_total = raio_char * 2.10 * anim_scale
                cabo_len   = raio_char * 0.60
                ponta_tam  = max(6, int(raio_char * 0.25))
                pulso      = 0.5 + 0.5 * math.sin(tempo / 180)

                # Ã¢â€â‚¬Ã¢â€â‚¬ KUSARIGAMA Ã¢â‚¬â€ foice small + corrente + peso Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                if estilo_norm == "kusarigama":
                    # Cabo pequeno da foice
                    kama_cabo_x = cx + math.cos(rad) * cabo_len
                    kama_cabo_y = cy + math.sin(rad) * cabo_len
                    pygame.draw.line(self.tela, (30,18,8), (int(cx)+1,int(cy)+1), (int(kama_cabo_x)+1,int(kama_cabo_y)+1), max(3,larg_base)+1)
                    pygame.draw.line(self.tela, (90,55,25), (int(cx),int(cy)), (int(kama_cabo_x),int(kama_cabo_y)), max(3,larg_base))
                    # LÃ¢mina da foice (arco rÃ¡pido usando BÃ©zier)
                    kama_len = ponta_tam * 2.5
                    curve_ang = rad - math.pi/2
                    ctrl_x = kama_cabo_x + math.cos(curve_ang) * kama_len * 0.5
                    ctrl_y = kama_cabo_y + math.sin(curve_ang) * kama_len * 0.5
                    hook_x = kama_cabo_x + math.cos(curve_ang) * kama_len
                    hook_y = kama_cabo_y + math.sin(curve_ang) * kama_len
                    prev = (int(kama_cabo_x), int(kama_cabo_y))
                    for seg in range(1, 9):
                        t = seg / 8
                        bx2 = (1-t)**2*kama_cabo_x + 2*(1-t)*t*ctrl_x + t**2*hook_x
                        by2 = (1-t)**2*kama_cabo_y + 2*(1-t)*t*ctrl_y + t**2*hook_y
                        pygame.draw.line(self.tela, cor, prev, (int(bx2),int(by2)), max(2,larg_base))
                        prev = (int(bx2),int(by2))
                    pygame.draw.circle(self.tela, cor_raridade, (int(hook_x),int(hook_y)), max(2,larg_base-1))
                    # Corrente ondulada saindo do cabo
                    chain_pts = []
                    for i in range(14):
                        t = i / 13
                        wave = math.sin(t * math.pi * 3 + tempo/120) * raio_char * 0.12
                        px2 = kama_cabo_x + math.cos(rad) * comp_total * t
                        py2 = kama_cabo_y + math.sin(rad) * comp_total * t + wave
                        chain_pts.append((int(px2),int(py2)))
                    if len(chain_pts) > 1:
                        try: pygame.draw.lines(self.tela, (80,82,90), False, chain_pts, max(2,larg_base-1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        for j in range(0,len(chain_pts)-1,2):
                            pygame.draw.circle(self.tela,(60,62,72),chain_pts[j],max(2,larg_base//2))
                    # Peso (bola pequena no final)
                    if chain_pts:
                        ex,ey = chain_pts[-1]
                        pygame.draw.circle(self.tela, cor_escura, (ex,ey), ponta_tam+1)
                        pygame.draw.circle(self.tela, cor, (ex,ey), ponta_tam-1)
                        pygame.draw.circle(self.tela, cor_clara, (ex-ponta_tam//3,ey-ponta_tam//3), max(1,ponta_tam//3))

                # Ã¢â€â‚¬Ã¢â€â‚¬ CHICOTE Ã¢â‚¬â€ longo, sinuoso, afunilando Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif estilo_norm == "chicote":
                    # Cabo de couro
                    cabo_ex = cx + math.cos(rad) * cabo_len
                    cabo_ey = cy + math.sin(rad) * cabo_len
                    pygame.draw.line(self.tela, (20,10,4),  (int(cx)+1,int(cy)+1), (int(cabo_ex)+1,int(cabo_ey)+1), max(_zw(3), larg_base)+2)
                    pygame.draw.line(self.tela, (60,30,10), (int(cx),int(cy)), (int(cabo_ex),int(cabo_ey)), max(_zw(3), larg_base))
                    # Tira de couro com faixas
                    for fi in range(1,4):
                        ft = fi/4
                        fx = int(cx + (cabo_ex-cx)*ft)
                        fy = int(cy + (cabo_ey-cy)*ft)
                        perp_x2 = math.cos(rad+math.pi/2)*(larg_base+2)
                        perp_y2 = math.sin(rad+math.pi/2)*(larg_base+2)
                        pygame.draw.line(self.tela,(35,16,4),(int(fx-perp_x2),int(fy-perp_y2)),(int(fx+perp_x2),int(fy+perp_y2)),1)
                    # Chicote ondulado (20 segmentos, afunilando)
                    num_seg = 20
                    pts = []
                    for i in range(num_seg+1):
                        t = i / num_seg
                        amp = raio_char * 0.25 * (1 - t*0.75)
                        wave = math.sin(t*math.pi*3.5 + tempo/100) * amp
                        px2 = cabo_ex + math.cos(rad) * comp_total * t
                        py2 = cabo_ey + math.sin(rad) * comp_total * t
                        perp_x2 = math.cos(rad+math.pi/2)*wave
                        perp_y2 = math.sin(rad+math.pi/2)*wave
                        pts.append((int(px2+perp_x2), int(py2+perp_y2)))
                    for j in range(len(pts)-1):
                        thick = max(1, int(larg_base * (1 - j/num_seg) + 0.5))
                        alpha_t = 80 + int(80 * (1 - j/num_seg))
                        try: pygame.draw.line(self.tela, cor, pts[j], pts[j+1], thick)
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    # NÃ³ da ponta
                    if pts:
                        pygame.draw.circle(self.tela, cor_raridade, pts[-1], max(2,larg_base-1))

                # Ã¢â€â‚¬Ã¢â€â‚¬ CORRENTE COM PESO Ã¢â‚¬â€ elos quadrados + bloco metÃ¡lico Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                else:
                    # Argola de pulso
                    pygame.draw.circle(self.tela, (80,82,90), (int(cx),int(cy)), larg_base+2, _zw(2))
                    # Elos robustos (retÃ¢ngulos grandes)
                    num_elos = 8
                    pts = []
                    for i in range(num_elos+1):
                        t = i / num_elos
                        wave = math.sin(t*math.pi*2+tempo/200)*raio_char*0.1
                        px2 = cx + math.cos(rad)*comp_total*t
                        py2 = cy + math.sin(rad)*comp_total*t + wave
                        pts.append((int(px2),int(py2)))
                    for j in range(len(pts)-1):
                        pygame.draw.line(self.tela,(30,30,38),pts[j],pts[j+1],larg_base+3)
                        pygame.draw.line(self.tela,(90,92,105),pts[j],pts[j+1],larg_base)
                        if j%2==0:
                            perp_x2 = math.cos(rad+math.pi/2)*(larg_base+3)
                            perp_y2 = math.sin(rad+math.pi/2)*(larg_base+3)
                            mx=(pts[j][0]+pts[j+1][0])//2; my=(pts[j][1]+pts[j+1][1])//2
                            pygame.draw.line(self.tela,(55,56,65),(int(mx-perp_x2),int(my-perp_y2)),(int(mx+perp_x2),int(my+perp_y2)),2)
                    # Peso Ã¢â‚¬â€ bloco metÃ¡lico pesado
                    if pts:
                        ex,ey = pts[-1]
                        hw = ponta_tam+2; hh = int(ponta_tam*1.4)
                        pygame.draw.rect(self.tela,(20,22,28),(ex-hw,ey-hh,hw*2,hh*2))
                        pygame.draw.rect(self.tela, cor, (ex-hw+1,ey-hh+1,hw*2-2,hh*2-2), _zw(2))
                        pygame.draw.line(self.tela, cor_clara, (ex-hw+2,ey-hh+2),(ex-hw//2,ey-hh//2), _zw(2))
                        if raridade_norm != 'comum':
                            pygame.draw.rect(self.tela,cor_raridade,(ex-hw,ey-hh,hw*2,hh*2),2)

        
        # === ARREMESSO (Machado, Faca RÃ¡pida, Chakram, Bumerangue) ===
        elif tipo_norm == "arremesso":
            estilo_arma = getattr(arma, 'estilo', '')
            tam_proj = max(8, int(raio_char * 0.35))
            qtd = min(5, int(getattr(arma, 'quantidade', 3)))
            pulso = 0.5 + 0.5 * math.sin(tempo / 180)

            for i in range(qtd):
                offset_ang = (i - (qtd-1)/2) * 20
                r_proj = rad + math.radians(offset_ang)
                dist = raio_char * 1.15 + tam_proj * 0.6
                px = cx + math.cos(r_proj) * dist
                py = cy + math.sin(r_proj) * dist
                rot = tempo / 90 + i * (math.pi * 2 / max(1, qtd))

                # Ã¢â€â‚¬Ã¢â€â‚¬ MACHADO (NÃ£o Retorna) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                if "machado" in estilo_norm:
                    # Cabo giratÃ³rio
                    cabo_ax = px + math.cos(rot) * tam_proj * 0.5
                    cabo_ay = py + math.sin(rot) * tam_proj * 0.5
                    pygame.draw.line(self.tela, (60,35,12), (int(px), int(py)), (int(cabo_ax), int(cabo_ay)), max(2,larg_base-1))
                    # CabeÃ§a assimÃ©trica
                    perp_ax = math.cos(rot + math.pi/2)
                    perp_ay = math.sin(rot + math.pi/2)
                    ax_pts = [
                        (int(cabo_ax - perp_ax*tam_proj*0.9), int(cabo_ay - perp_ay*tam_proj*0.9)),
                        (int(cabo_ax + perp_ax*tam_proj*0.3), int(cabo_ay + perp_ay*tam_proj*0.3)),
                        (int(cabo_ax + math.cos(rot)*tam_proj*0.8 + perp_ax*tam_proj*0.25),
                         int(cabo_ay + math.sin(rot)*tam_proj*0.8 + perp_ay*tam_proj*0.25)),
                        (int(cabo_ax + math.cos(rot)*tam_proj*0.9), int(cabo_ay + math.sin(rot)*tam_proj*0.9)),
                        (int(cabo_ax + math.cos(rot)*tam_proj*0.8 - perp_ax*tam_proj*0.9),
                         int(cabo_ay + math.sin(rot)*tam_proj*0.8 - perp_ay*tam_proj*0.9)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, ax_pts)
                        pygame.draw.polygon(self.tela, cor, ax_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.circle(self.tela, cor_raridade, (int(cabo_ax+math.cos(rot)*tam_proj*0.9),int(cabo_ay+math.sin(rot)*tam_proj*0.9)), max(2,larg_base-2))

                # Ã¢â€â‚¬Ã¢â€â‚¬ CHAKRAM (Retorna) Ã¢â‚¬â€ anel com fio Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif "chakram" in estilo_norm:
                    r2 = max(7, tam_proj - 1)
                    # Anel com espessura
                    pygame.draw.circle(self.tela, cor_escura, (int(px), int(py)), r2+1)
                    pygame.draw.circle(self.tela, cor, (int(px), int(py)), r2, max(3,larg_base-1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(px), int(py)), r2, _zw(1))
                    # Raios internos girando
                    for rj in range(3):
                        ra = rot + rj * math.pi / 3 * 2
                        pygame.draw.line(self.tela, cor_clara,
                                         (int(px + math.cos(ra)*r2*0.5), int(py + math.sin(ra)*r2*0.5)),
                                         (int(px - math.cos(ra)*r2*0.5), int(py - math.sin(ra)*r2*0.5)), 1)
                    pygame.draw.circle(self.tela, cor_raridade, (int(px),int(py)), max(2,r2//3))
                    # Glow de ataque
                    if atacando:
                        try:
                            gs = self._get_surface(r2*4, r2*4, pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor, int(80*pulso)), (r2*2,r2*2), r2*2)
                            self.tela.blit(gs, (int(px)-r2*2, int(py)-r2*2))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                # Ã¢â€â‚¬Ã¢â€â‚¬ BUMERANGUE Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif "bumerangue" in estilo_norm:
                    t2 = tam_proj
                    bum_pts = [
                        (int(px + math.cos(rot)*t2*1.1),         int(py + math.sin(rot)*t2*1.1)),
                        (int(px + math.cos(rot+2.3)*t2*0.5),     int(py + math.sin(rot+2.3)*t2*0.5)),
                        (int(px),                                  int(py)),
                        (int(px + math.cos(rot-2.3)*t2*0.5),     int(py + math.sin(rot-2.3)*t2*0.5)),
                        (int(px + math.cos(rot+math.pi)*t2*0.9), int(py + math.sin(rot+math.pi)*t2*0.9)),
                        (int(px + math.cos(rot+math.pi+0.5)*t2*0.4), int(py + math.sin(rot+math.pi+0.5)*t2*0.4)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, bum_pts)
                        pygame.draw.polygon(self.tela, cor, bum_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.circle(self.tela, cor_raridade, (int(px), int(py)), max(2,larg_base-2))

                # Ã¢â€â‚¬Ã¢â€â‚¬ FACA (RÃ¡pida) e fallback Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                else:
                    # Throwing knife Ã¢â‚¬â€ estreita e rÃ¡pida
                    blade = tam_proj * 1.2
                    perp_f = math.cos(rot + math.pi/2) * max(2, larg_base//2)
                    perp_fy = math.sin(rot + math.pi/2) * max(2, larg_base//2)
                    tip_fx = px + math.cos(rot) * blade
                    tip_fy = py + math.sin(rot) * blade
                    faca_pts = [
                        (int(px - perp_f), int(py - perp_fy)),
                        (int(px + perp_f), int(py + perp_fy)),
                        (int(tip_fx + perp_f*0.3), int(tip_fy + perp_fy*0.3)),
                        (int(tip_fx), int(tip_fy)),
                        (int(tip_fx - perp_f*0.3), int(tip_fy - perp_fy*0.3)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, faca_pts)
                        pygame.draw.polygon(self.tela, cor, faca_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.line(self.tela, cor_clara, (int(px),int(py)), (int(tip_fx),int(tip_fy)), _zw(1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(tip_fx),int(tip_fy)), max(2,larg_base-2))

        # === ARCO (Arco Curto, Arco Longo, Besta, Besta de RepetiÃ§Ã£o) ===
        elif tipo_norm == "arco":
            estilo_arma = getattr(arma, 'estilo', '')
            tam_arco   = raio_char * 1.30
            tam_flecha = raio_char * 1.20 * anim_scale
            pulso = 0.5 + 0.5 * math.sin(tempo / 200)

            # Ã¢â€â‚¬Ã¢â€â‚¬ BESTA / BESTA DE REPETIÃƒâ€¡ÃƒÆ’O Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            if "besta" in estilo_norm:
                # Coronha (stock) Ã¢â‚¬â€ paralela ao rad
                stock_len = tam_arco * 0.6
                stock_ex = cx + math.cos(rad) * stock_len
                stock_ey = cy + math.sin(rad) * stock_len
                perp_x = math.cos(rad + math.pi/2)
                perp_y = math.sin(rad + math.pi/2)
                # Madeira da coronha
                pygame.draw.line(self.tela, (30,18,8), (int(cx)+1,int(cy)+1),(int(stock_ex)+1,int(stock_ey)+1), larg_base+3)
                pygame.draw.line(self.tela, (90,55,25),(int(cx),int(cy)),(int(stock_ex),int(stock_ey)),larg_base+1)
                pygame.draw.line(self.tela, (130,85,40),(int(cx),int(cy)),(int(stock_ex),int(stock_ey)),max(1,larg_base-1))
                # Limbo horizontal (os "braÃ§os")
                limbo_len = tam_arco * 0.45
                mid_x = cx + math.cos(rad) * stock_len * 0.75
                mid_y = cy + math.sin(rad) * stock_len * 0.75
                limbo_p1 = (int(mid_x + perp_x*limbo_len), int(mid_y + perp_y*limbo_len))
                limbo_p2 = (int(mid_x - perp_x*limbo_len), int(mid_y - perp_y*limbo_len))
                pygame.draw.line(self.tela, (20,18,20), (int(limbo_p1[0])+1,int(limbo_p1[1])+1),(int(limbo_p2[0])+1,int(limbo_p2[1])+1), max(3,larg_base)+1)
                pygame.draw.line(self.tela, cor, limbo_p1, limbo_p2, max(3,larg_base))
                pygame.draw.line(self.tela, cor_clara, limbo_p1, limbo_p2, _zw(1))
                # Corda (de ponta a ponta do limbo, passando pelo trilho)
                trilho_x = cx + math.cos(rad) * stock_len * 0.95
                trilho_y = cy + math.sin(rad) * stock_len * 0.95
                pygame.draw.line(self.tela, (200,185,140), limbo_p1, (int(trilho_x),int(trilho_y)), _zw(2))
                pygame.draw.line(self.tela, (200,185,140), limbo_p2, (int(trilho_x),int(trilho_y)), _zw(2))
                # Virote (bolto) no trilho
                pygame.draw.line(self.tela, (139,90,43), (int(trilho_x),int(trilho_y)),(int(trilho_x+math.cos(rad)*tam_flecha*0.6),int(trilho_y+math.sin(rad)*tam_flecha*0.6)), max(2,larg_base//2))
                tip_bx = int(trilho_x + math.cos(rad)*tam_flecha*0.6)
                tip_by = int(trilho_y + math.sin(rad)*tam_flecha*0.6)
                pts_tip = [(tip_bx,tip_by),
                           (int(tip_bx-math.cos(rad)*8+perp_x*4),int(tip_by-math.sin(rad)*8+perp_y*4)),
                           (int(tip_bx-math.cos(rad)*8-perp_x*4),int(tip_by-math.sin(rad)*8-perp_y*4))]
                try: pygame.draw.polygon(self.tela, cor_raridade, pts_tip)
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                # Pente de repetiÃ§Ã£o (caixinha em cima do trilho)
                if "repeticao" in estilo_norm:
                    px2 = int(mid_x + math.cos(rad)*stock_len*0.05)
                    py2 = int(mid_y + math.sin(rad)*stock_len*0.05)
                    pygame.draw.rect(self.tela, (55,30,10), (px2-6, py2-18, 12, 16))
                    pygame.draw.rect(self.tela, cor_raridade, (px2-6, py2-18, 12, 16), _zw(1))
                # Glow de raridade
                if raridade_norm not in ['comum', 'incomum']:
                    pygame.draw.circle(self.tela, cor_raridade, (tip_bx,tip_by), max(3,larg_base))

            # Ã¢â€â‚¬Ã¢â€â‚¬ ARCO LONGO Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            elif "longo" in estilo_norm:
                arco_pts = []
                span = tam_arco * 0.9
                for i in range(15):
                    ang = rad + math.radians(-60 + i * (120/14))
                    curva = math.sin((i/14)*math.pi) * span * 0.12
                    r2 = span*0.55 + curva
                    arco_pts.append((int(cx+math.cos(ang)*r2), int(cy+math.sin(ang)*r2)))
                if len(arco_pts) > 1:
                    pygame.draw.lines(self.tela, cor_escura, False, [(p[0]+1,p[1]+1) for p in arco_pts], larg_base+2)
                    pygame.draw.lines(self.tela, cor, False, arco_pts, larg_base+1)
                    pygame.draw.lines(self.tela, cor_clara, False, arco_pts, _zw(1))
                    pygame.draw.line(self.tela, (200,185,140), arco_pts[0], arco_pts[-1], _zw(2))
                # Flecha longa
                flecha_end_x = cx + math.cos(rad)*tam_flecha
                flecha_end_y = cy + math.sin(rad)*tam_flecha
                pygame.draw.line(self.tela, (100,65,25),(int(cx),int(cy)),(int(flecha_end_x),int(flecha_end_y)),max(2,larg_base//2))
                plen = tam_flecha*0.14; perp_f = math.pi/2
                tip_pts = [(int(flecha_end_x),int(flecha_end_y)),
                           (int(flecha_end_x-math.cos(rad)*plen+math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen+math.sin(rad+perp_f)*plen*0.4)),
                           (int(flecha_end_x-math.cos(rad)*plen-math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen-math.sin(rad+perp_f)*plen*0.4))]
                try: pygame.draw.polygon(self.tela, cor_raridade, tip_pts)
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                # Penas
                for poff in [-1,1]:
                    pex = cx+math.cos(rad)*tam_flecha*0.12
                    pey = cy+math.sin(rad)*tam_flecha*0.12
                    pygame.draw.line(self.tela,(200,50,50),(int(pex),int(pey)),(int(pex+math.cos(rad+poff*0.6)*tam_flecha*0.12),int(pey+math.sin(rad+poff*0.6)*tam_flecha*0.12)),2)

            # Ã¢â€â‚¬Ã¢â€â‚¬ ARCO CURTO (default) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            else:
                arco_pts = []
                for i in range(13):
                    ang = rad + math.radians(-50 + i*(100/12))
                    curva = math.sin((i/12)*math.pi) * tam_arco * 0.15
                    r2 = tam_arco*0.5 + curva
                    arco_pts.append((int(cx+math.cos(ang)*r2), int(cy+math.sin(ang)*r2)))
                if len(arco_pts) > 1:
                    pygame.draw.lines(self.tela, cor, False, arco_pts, max(_zw(3), larg_base))
                    pygame.draw.lines(self.tela, cor_escura, False, arco_pts, _zw(1))
                    pygame.draw.line(self.tela, (200,180,140), arco_pts[0], arco_pts[-1], _zw(2))
                flecha_end_x = cx+math.cos(rad)*tam_flecha
                flecha_end_y = cy+math.sin(rad)*tam_flecha
                pygame.draw.line(self.tela,(139,90,43),(int(cx),int(cy)),(int(flecha_end_x),int(flecha_end_y)),max(2,larg_base//2))
                plen = tam_flecha*0.15; perp_f = math.pi/2
                tip_pts = [(int(flecha_end_x),int(flecha_end_y)),
                           (int(flecha_end_x-math.cos(rad)*plen+math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen+math.sin(rad+perp_f)*plen*0.4)),
                           (int(flecha_end_x-math.cos(rad)*plen-math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen-math.sin(rad+perp_f)*plen*0.4))]
                try: pygame.draw.polygon(self.tela, cor_raridade, tip_pts)
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                for poff in [-1,1]:
                    pex = cx+math.cos(rad)*tam_flecha*0.15
                    pey = cy+math.sin(rad)*tam_flecha*0.15
                    pygame.draw.line(self.tela,(200,50,50),(int(pex),int(pey)),(int(pex+math.cos(rad+poff*0.5)*tam_flecha*0.1),int(pey+math.sin(rad+poff*0.5)*tam_flecha*0.1)),2)

        # === ORBITAL (Escudo, Drone, Orbes, LÃ¢minas Orbitais) ===
        elif tipo_norm == "orbital":
            estilo_arma = getattr(arma, 'estilo', '')
            dist_orbit = raio_char * 1.6
            qtd  = max(1, min(5, int(getattr(arma, 'quantidade_orbitais', 2))))
            tam_orbe = max(8, int(raio_char * 0.32))
            rot_speed = tempo / 800
            pulso = 0.5 + 0.5 * math.sin(tempo / 200)

            for i in range(qtd):
                ang = rot_speed + (2 * math.pi / qtd) * i
                ox = cx + math.cos(ang) * dist_orbit
                oy = cy + math.sin(ang) * dist_orbit

                # Linha conectora sutil
                pygame.draw.line(self.tela, (50,50,70), (int(cx),int(cy)), (int(ox),int(oy)), _zw(1))

                # Ã¢â€â‚¬Ã¢â€â‚¬ ESCUDO Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                if "escudo" in estilo_norm or "defensivo" in estilo_norm:
                    arc_r = tam_orbe * 1.6
                    # Arco sÃ³lido como escudo curvo
                    start_ang = math.degrees(ang) + 60
                    try:
                        pygame.draw.arc(self.tela, cor_escura,
                                        (int(ox-arc_r), int(oy-arc_r), int(arc_r*2), int(arc_r*2)),
                                        math.radians(start_ang), math.radians(start_ang+120), tam_orbe//2+2)
                        pygame.draw.arc(self.tela, cor,
                                        (int(ox-arc_r), int(oy-arc_r), int(arc_r*2), int(arc_r*2)),
                                        math.radians(start_ang), math.radians(start_ang+120), tam_orbe//2)
                        pygame.draw.arc(self.tela, cor_clara,
                                        (int(ox-arc_r+2), int(oy-arc_r+2), int(arc_r*2-4), int(arc_r*2-4)),
                                        math.radians(start_ang+10), math.radians(start_ang+50), 1)
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    if raridade_norm != 'comum':
                        try:
                            gs = self._get_surface(tam_orbe*4, tam_orbe*4, pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor_raridade, int(60*pulso)), (tam_orbe*2,tam_orbe*2), tam_orbe*2)
                            self.tela.blit(gs, (int(ox)-tam_orbe*2, int(oy)-tam_orbe*2))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                # Ã¢â€â‚¬Ã¢â€â‚¬ DRONE Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif "drone" in estilo_norm or "ofensivo" in estilo_norm:
                    # HexÃ¡gono metÃ¡lico
                    hex_pts = []
                    for j in range(6):
                        ha = ang*30 + j*math.pi/3
                        hex_pts.append((int(ox+math.cos(ha)*tam_orbe), int(oy+math.sin(ha)*tam_orbe)))
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, hex_pts)
                        pygame.draw.polygon(self.tela, cor, hex_pts, _zw(2))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.circle(self.tela, cor_raridade, (int(ox),int(oy)), max(3,tam_orbe//3))
                    # Propulsor
                    thrust_x = int(ox + math.cos(ang+math.pi)*tam_orbe*1.4)
                    thrust_y = int(oy + math.sin(ang+math.pi)*tam_orbe*1.4)
                    pygame.draw.line(self.tela, (100,180,255), (int(ox),int(oy)), (thrust_x,thrust_y), max(2,larg_base-1))
                    try:
                        gs = self._get_surface(8,8, pygame.SRCALPHA)
                        pygame.draw.circle(gs, (100,180,255,int(120*pulso)), (4,4), 4)
                        self.tela.blit(gs, (thrust_x-4, thrust_y-4))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                # Ã¢â€â‚¬Ã¢â€â‚¬ LÃƒâ€šMINAS ORBITAIS Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif "lamina" in estilo_norm:
                    blade_len = tam_orbe * 1.5
                    ba = ang + tempo/600
                    perp_bx = math.cos(ba + math.pi/2)
                    perp_by = math.sin(ba + math.pi/2)
                    tip1x = ox + math.cos(ba)*blade_len; tip1y = oy + math.sin(ba)*blade_len
                    tip2x = ox - math.cos(ba)*blade_len; tip2y = oy - math.sin(ba)*blade_len
                    w = max(2, larg_base-2)
                    blade_pts = [
                        (int(tip1x),int(tip1y)),
                        (int(ox+perp_bx*w),int(oy+perp_by*w)),
                        (int(tip2x),int(tip2y)),
                        (int(ox-perp_bx*w),int(oy-perp_by*w)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, blade_pts)
                        pygame.draw.polygon(self.tela, cor, blade_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.line(self.tela, cor_clara, (int(tip1x),int(tip1y)), (int(tip2x),int(tip2y)), _zw(1))
                    if raridade_norm != 'comum':
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip1x),int(tip1y)), max(2,larg_base-2))
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip2x),int(tip2y)), max(2,larg_base-2))

                # Ã¢â€â‚¬Ã¢â€â‚¬ ORBE MÃGICO (default) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                else:
                    for glow_r in range(3,0,-1):
                        alpha_cor = tuple(min(255, c+glow_r*18) for c in cor)
                        pygame.draw.circle(self.tela, alpha_cor, (int(ox),int(oy)), tam_orbe+glow_r)
                    pygame.draw.circle(self.tela, cor, (int(ox),int(oy)), tam_orbe)
                    pygame.draw.circle(self.tela, cor_clara, (int(ox),int(oy)), tam_orbe//2)
                    pygame.draw.circle(self.tela, cor_raridade, (int(ox),int(oy)), tam_orbe, _zw(2))
                    # Highlight
                    pygame.draw.circle(self.tela, (255,255,255), (int(ox-tam_orbe//3),int(oy-tam_orbe//3)), max(2,tam_orbe//4))

        # === MÃGICA (Espadas Espectrais, Runas, TentÃ¡culos, Cristais) ===
        elif tipo_norm == "magica":
            estilo_arma = getattr(arma, 'estilo', '')
            qtd       = min(5, int(getattr(arma, 'quantidade', 3)))
            tam_base  = max(12, int(raio_char * 0.65))
            dist_base = raio_char * 1.4
            float_off = math.sin(tempo/250) * raio_char * 0.1
            rot_off   = tempo / 1500
            pulso     = 0.5 + 0.5 * math.sin(tempo/200)

            for i in range(qtd):
                offset_ang = (i-(qtd-1)/2)*22 + math.degrees(rot_off)
                r_m = rad + math.radians(offset_ang)
                dist = dist_base + float_off*(1 + i*0.2)
                px = cx + math.cos(r_m)*dist
                py = cy + math.sin(r_m)*dist

                # Ã¢â€â‚¬Ã¢â€â‚¬ ESPADAS ESPECTRAIS Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                if "espada" in estilo_norm or "espectral" in estilo_norm:
                    sword_ex = px + math.cos(r_m)*tam_base
                    sword_ey = py + math.sin(r_m)*tam_base
                    perp_mx = math.cos(r_m+math.pi/2)*max(2,larg_base//2)
                    perp_my = math.sin(r_m+math.pi/2)*max(2,larg_base//2)
                    blade_pts = [
                        (int(px-perp_mx),int(py-perp_my)),
                        (int(px+perp_mx),int(py+perp_my)),
                        (int(sword_ex+perp_mx*0.3),int(sword_ey+perp_my*0.3)),
                        (int(sword_ex),int(sword_ey)),
                        (int(sword_ex-perp_mx*0.3),int(sword_ey-perp_my*0.3)),
                    ]
                    try:
                        gs = pygame.Surface((int(tam_base*4), int(tam_base*4)), pygame.SRCALPHA)
                        local_pts = [(p[0]-int(px)+int(tam_base*2), p[1]-int(py)+int(tam_base*2)) for p in blade_pts]
                        pygame.draw.polygon(gs, (*cor, 160), local_pts)
                        self.tela.blit(gs, (int(px)-int(tam_base*2), int(py)-int(tam_base*2)))
                        pygame.draw.polygon(self.tela, cor, blade_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.line(self.tela, cor_clara, (int(px),int(py)), (int(sword_ex),int(sword_ey)), _zw(1))
                    # Guarda
                    pygame.draw.line(self.tela, cor_raridade,
                                     (int(px-perp_mx*2.5),int(py-perp_my*2.5)),
                                     (int(px+perp_mx*2.5),int(py+perp_my*2.5)), max(2,larg_base-1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(sword_ex),int(sword_ey)), 3)

                # Ã¢â€â‚¬Ã¢â€â‚¬ RUNAS FLUTUANTES Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif "runa" in estilo_norm:
                    r2 = max(8, int(tam_base*0.65))
                    pygame.draw.circle(self.tela, cor_escura, (int(px),int(py)), r2+2)
                    pygame.draw.circle(self.tela, cor, (int(px),int(py)), r2, max(2,larg_base-1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(px),int(py)), r2, _zw(1))
                    # Cruz + diagonais rÃºnicas
                    ang_r = rot_off + i * math.pi / qtd
                    for ra in [ang_r, ang_r+math.pi/4, ang_r+math.pi/2, ang_r+3*math.pi/4]:
                        pygame.draw.line(self.tela, cor_clara,
                                         (int(px+math.cos(ra)*(r2-3)),int(py+math.sin(ra)*(r2-3))),
                                         (int(px-math.cos(ra)*(r2-3)),int(py-math.sin(ra)*(r2-3))), 1)
                    pygame.draw.circle(self.tela, cor_raridade, (int(px),int(py)), max(2,r2//3))
                    if raridade_norm != 'comum':
                        try:
                            gs = self._get_surface(r2*4,r2*4, pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor_raridade, int(80*pulso)), (r2*2,r2*2), r2*2)
                            self.tela.blit(gs, (int(px)-r2*2, int(py)-r2*2))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01

                # Ã¢â€â‚¬Ã¢â€â‚¬ TENTÃCULOS SOMBRIOS Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                elif "tentaculo" in estilo_norm:
                    tent_len = tam_base * 2.0
                    t_pts = []
                    for s in range(9):
                        t = s / 8
                        wave = math.sin(t*math.pi*2.5 + tempo/100 + i) * tam_base*0.4*(1-t*0.3)
                        tx2 = px + math.cos(r_m)*tent_len*t + math.cos(r_m+math.pi/2)*wave
                        ty2 = py + math.sin(r_m)*tent_len*t + math.sin(r_m+math.pi/2)*wave
                        t_pts.append((int(tx2),int(ty2)))
                    if len(t_pts) > 1:
                        try: pygame.draw.lines(self.tela, cor, False, t_pts, max(2,larg_base-1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                        try: pygame.draw.lines(self.tela, cor_clara, False, t_pts, _zw(1))
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    # Ventosas
                    for si in range(1,4):
                        sv = t_pts[si*2] if si*2 < len(t_pts) else t_pts[-1]
                        pygame.draw.circle(self.tela, cor_raridade, sv, max(2,larg_base-2))

                # Ã¢â€â‚¬Ã¢â€â‚¬ CRISTAIS ARCANOS Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
                else:
                    r2 = max(7, int(tam_base*0.6))
                    crystal_pts = [
                        (int(px+math.cos(rot_off+i)*r2*1.4), int(py+math.sin(rot_off+i)*r2*1.4)),
                        (int(px+math.cos(rot_off+i+2.1)*r2), int(py+math.sin(rot_off+i+2.1)*r2)),
                        (int(px+math.cos(rot_off+i+2.5)*r2*0.6), int(py+math.sin(rot_off+i+2.5)*r2*0.6)),
                        (int(px+math.cos(rot_off+i+3.8)*r2), int(py+math.sin(rot_off+i+3.8)*r2)),
                        (int(px+math.cos(rot_off+i-2.1)*r2), int(py+math.sin(rot_off+i-2.1)*r2)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, crystal_pts)
                        pygame.draw.polygon(self.tela, cor, crystal_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    pygame.draw.circle(self.tela, cor_clara, (int(px),int(py)), max(2,r2//3))
                    if raridade_norm != 'comum':
                        pygame.draw.circle(self.tela, cor_raridade, crystal_pts[0], 3)

        # === TRANSFORMÃVEL (EspadaÃ¢â€ â€LanÃ§a, CompactaÃ¢â€ â€Estendida, ChicoteÃ¢â€ â€Espada, ArcoÃ¢â€ â€LÃ¢minas) ===
        elif tipo_norm == "transformavel":
            estilo_arma = getattr(arma, 'estilo', '')
            forma = getattr(arma, 'forma_atual', 1)
            larg = max(_zw(3), int(larg_base * 1.1))
            pulso = 0.5 + 0.5 * math.sin(tempo / 200)

            if forma == 1:
                cabo_len   = raio_char * 0.50
                lamina_len = raio_char * 1.20 * anim_scale
            else:
                cabo_len   = raio_char * 0.85
                lamina_len = raio_char * 1.55 * anim_scale

            cabo_end_x = cx + math.cos(rad)*cabo_len
            cabo_end_y = cy + math.sin(rad)*cabo_len
            lamina_end_x = cx + math.cos(rad)*(cabo_len+lamina_len)
            lamina_end_y = cy + math.sin(rad)*(cabo_len+lamina_len)
            perp_x = math.cos(rad+math.pi/2)
            perp_y = math.sin(rad+math.pi/2)

            # Mecanismo de transformaÃ§Ã£o (engrenagem/pivot) Ã¢â‚¬â€ igual para todos
            mec_col = (int(120+80*pulso), int(100+60*pulso), int(90+50*pulso))
            pygame.draw.circle(self.tela, (40,40,50), (int(cabo_end_x),int(cabo_end_y)), larg+2)
            pygame.draw.circle(self.tela, mec_col, (int(cabo_end_x),int(cabo_end_y)), larg, _zw(2))
            # Cabo com faixas
            pygame.draw.line(self.tela, (30,18,8), (int(cx)+1,int(cy)+1),(int(cabo_end_x)+1,int(cabo_end_y)+1), larg+2)
            pygame.draw.line(self.tela, (90,55,25), (int(cx),int(cy)),(int(cabo_end_x),int(cabo_end_y)), larg)

            # Ã¢â€â‚¬Ã¢â€â‚¬ ESPADA Ã¢â€ â€ LANÃƒâ€¡A Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            if "lanca" in estilo_norm and "espada" in estilo_norm:
                if forma == 1:  # Espada
                    blade_pts = [
                        (int(cabo_end_x-perp_x*larg*0.7),int(cabo_end_y-perp_y*larg*0.7)),
                        (int(cabo_end_x+perp_x*larg*0.7),int(cabo_end_y+perp_y*larg*0.7)),
                        (int(lamina_end_x-perp_x*larg*0.3),int(lamina_end_y-perp_y*larg*0.3)),
                        (int(lamina_end_x),int(lamina_end_y)),
                        (int(lamina_end_x+perp_x*larg*0.3),int(lamina_end_y+perp_y*larg*0.3)),
                    ]
                    # Guarda
                    pygame.draw.line(self.tela, (160,165,175),
                                     (int(cabo_end_x-perp_x*(larg+4)),int(cabo_end_y-perp_y*(larg+4))),
                                     (int(cabo_end_x+perp_x*(larg+4)),int(cabo_end_y+perp_y*(larg+4))), max(2,larg-1))
                else:  # LanÃ§a
                    blade_pts = [
                        (int(cabo_end_x-perp_x*larg*0.5),int(cabo_end_y-perp_y*larg*0.5)),
                        (int(cabo_end_x+perp_x*larg*0.5),int(cabo_end_y+perp_y*larg*0.5)),
                        (int(lamina_end_x+perp_x),int(lamina_end_y+perp_y)),
                        (int(lamina_end_x),int(lamina_end_y)),
                        (int(lamina_end_x-perp_x),int(lamina_end_y-perp_y)),
                    ]
                try:
                    pygame.draw.polygon(self.tela, cor, blade_pts)
                    pygame.draw.polygon(self.tela, cor_escura, blade_pts, _zw(1))
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                pygame.draw.line(self.tela, cor_clara, (int(cabo_end_x),int(cabo_end_y)),(int(lamina_end_x),int(lamina_end_y)), _zw(1))

            # Ã¢â€â‚¬Ã¢â€â‚¬ CHICOTE Ã¢â€ â€ ESPADA Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            elif "chicote" in estilo_norm:
                if forma == 1:  # Espada
                    blade_pts = [
                        (int(cabo_end_x-perp_x*larg*0.7),int(cabo_end_y-perp_y*larg*0.7)),
                        (int(cabo_end_x+perp_x*larg*0.7),int(cabo_end_y+perp_y*larg*0.7)),
                        (int(lamina_end_x-perp_x*larg*0.3),int(lamina_end_y-perp_y*larg*0.3)),
                        (int(lamina_end_x),int(lamina_end_y)),
                        (int(lamina_end_x+perp_x*larg*0.3),int(lamina_end_y+perp_y*larg*0.3)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor, blade_pts)
                        pygame.draw.polygon(self.tela, cor_escura, blade_pts, _zw(1))
                    except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                else:  # Chicote
                    num_seg = 14
                    wpts = []
                    for s in range(num_seg+1):
                        t = s/num_seg
                        amp = raio_char*0.2*(1-t*0.7)
                        wave = math.sin(t*math.pi*3+tempo/100)*amp
                        wx2 = cabo_end_x + math.cos(rad)*lamina_len*t
                        wy2 = cabo_end_y + math.sin(rad)*lamina_len*t + math.cos(rad+math.pi/2)*wave
                        wpts.append((int(wx2),int(wy2)))
                    for j in range(len(wpts)-1):
                        thick = max(1, int(larg*(1-j/num_seg)+0.5))
                        try: pygame.draw.line(self.tela, cor, wpts[j], wpts[j+1], thick)
                        except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                    if wpts: pygame.draw.circle(self.tela, cor_raridade, wpts[-1], max(2,larg-2))

            # Ã¢â€â‚¬Ã¢â€â‚¬ ARCo Ã¢â€ â€ LÃƒâ€šMINAS / COMPACTA Ã¢â€ â€ ESTENDIDA (default) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            else:
                blade_pts = [
                    (int(cabo_end_x-perp_x*larg*0.6),int(cabo_end_y-perp_y*larg*0.6)),
                    (int(cabo_end_x+perp_x*larg*0.6),int(cabo_end_y+perp_y*larg*0.6)),
                    (int(lamina_end_x-perp_x*larg*0.3),int(lamina_end_y-perp_y*larg*0.3)),
                    (int(lamina_end_x),int(lamina_end_y)),
                    (int(lamina_end_x+perp_x*larg*0.3),int(lamina_end_y+perp_y*larg*0.3)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor, blade_pts)
                    pygame.draw.polygon(self.tela, cor_escura, blade_pts, _zw(1))
                except Exception as _e: _log.debug("Render: %s", _e)  # QC-01
                pygame.draw.line(self.tela, cor_clara,(int(cabo_end_x),int(cabo_end_y)),(int(lamina_end_x),int(lamina_end_y)),1)

            # Glow de raridade comum
            if raridade_norm not in ['comum', 'incomum']:
                pygame.draw.circle(self.tela, cor_raridade, (int(lamina_end_x),int(lamina_end_y)), max(4,larg//2))


        
        # === FALLBACK ===
        else:
            cabo_len   = raio_char * 0.55
            lamina_len = raio_char * 1.20 * anim_scale
            
            cabo_end_x = cx + math.cos(rad) * cabo_len
            cabo_end_y = cy + math.sin(rad) * cabo_len
            lamina_end_x = cx + math.cos(rad) * (cabo_len + lamina_len)
            lamina_end_y = cy + math.sin(rad) * (cabo_len + lamina_len)
            
            pygame.draw.line(self.tela, (80, 50, 30), (int(cx), int(cy)), (int(cabo_end_x), int(cabo_end_y)), larg_base)
            pygame.draw.line(self.tela, cor, (int(cabo_end_x), int(cabo_end_y)), (int(lamina_end_x), int(lamina_end_y)), larg_base)


    def desenhar_hitbox_debug(self):
        """Desenha visualizaÃ§Ã£o de debug das hitboxes"""
        debug_info = get_debug_visual()
        fonte = self._get_font("Arial", 10)
        
        # Desenha hitboxes em tempo real para cada lutador
        for idx, p in enumerate(self.fighters):
            if p.morto:
                continue
            
            cor_debug = (*CORES_TIME_RENDER[p.team_id % len(CORES_TIME_RENDER)], 128)
            
            # Calcula hitbox atual
            hitbox = sistema_hitbox.calcular_hitbox_arma(p)
            if not hitbox:
                continue
            
            # PosiÃ§Ã£o na tela
            cx_screen, cy_screen = self.cam.converter(hitbox.centro[0], hitbox.centro[1])
            off_y = self.cam.converter_tam(p.z * PPM)
            cy_screen -= off_y
            
            # Surface transparente para desenho
            s = self._get_surface(self.screen_width, self.screen_height, pygame.SRCALPHA)
            
            # Desenha raio de alcance
            alcance_screen = self.cam.converter_tam(hitbox.alcance)
            pygame.draw.circle(s, (*cor_debug[:3], 30), (cx_screen, cy_screen), alcance_screen, 2)
            
            # Se tem pontos (arma de lÃ¢mina ou corrente)
            if hitbox.pontos:
                # Corrente: desenha como arco
                if hitbox.tipo == "Corrente":
                    # Desenha os segmentos do arco
                    cor_arco = (255, 128, 0, 200) if hitbox.ativo else (100, 100, 100, 100)
                    pontos_screen = []
                    for ponto in hitbox.pontos:
                        ps = self.cam.converter(ponto[0], ponto[1])
                        pontos_screen.append((ps[0], ps[1] - off_y))
                    
                    # Desenha linhas conectando os pontos do arco
                    if len(pontos_screen) > 1:
                        for i in range(len(pontos_screen) - 1):
                            pygame.draw.line(s, cor_arco, pontos_screen[i], pontos_screen[i+1], 3)
                    
                    # Desenha cÃ­rculo na posiÃ§Ã£o real da bola (centro do arco, no Ã¢ngulo da arma)
                    rad_bola = math.radians(hitbox.angulo)
                    bola_x = hitbox.centro[0] + math.cos(rad_bola) * hitbox.alcance
                    bola_y = hitbox.centro[1] + math.sin(rad_bola) * hitbox.alcance
                    bola_screen = self.cam.converter(bola_x, bola_y)
                    bola_screen = (bola_screen[0], bola_screen[1] - off_y)
                    pygame.draw.circle(s, (255, 50, 50, 255), bola_screen, 10, 3)  # CÃ­rculo vermelho na bola
                    
                    # Linha do centro atÃ© a bola
                    pygame.draw.line(s, (255, 128, 0, 100), (cx_screen, cy_screen), bola_screen, 1)
                    
                    # Desenha raio mÃ­nimo da corrente (onde ela NÃƒÆ’O acerta)
                    alcance_min = hitbox.alcance * 0.4
                    alcance_min_screen = self.cam.converter_tam(alcance_min)
                    pygame.draw.circle(s, (100, 100, 100, 50), (cx_screen, cy_screen), alcance_min_screen, 1)
                    
                    # Label
                    label = f"{p.dados.nome}: Corrente"
                    if hitbox.ativo:
                        label += f" [GIRANDO t={p.timer_animacao:.2f}]"
                    txt = fonte.render(label, True, BRANCO)
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
                
                # Armas Ranged: desenha linhas de trajetÃ³ria
                elif hitbox.tipo in ["Arremesso", "Arco"]:
                    cor_traj = (0, 200, 255, 150) if hitbox.ativo else (100, 100, 100, 80)
                    
                    # MÃºltiplos projÃ©teis ou linha Ãºnica
                    if len(hitbox.pontos) > 2:
                        # MÃºltiplos pontos = mÃºltiplos projÃ©teis
                        for ponto in hitbox.pontos:
                            ps = self.cam.converter(ponto[0], ponto[1])
                            ps = (ps[0], ps[1] - off_y)
                            # Linha tracejada do centro atÃ© destino
                            pygame.draw.line(s, cor_traj, (cx_screen, cy_screen), ps, 1)
                            pygame.draw.circle(s, cor_traj, ps, 5)
                    else:
                        # Linha Ãºnica
                        if len(hitbox.pontos) == 2:
                            p1_screen = self.cam.converter(hitbox.pontos[0][0], hitbox.pontos[0][1])
                            p2_screen = self.cam.converter(hitbox.pontos[1][0], hitbox.pontos[1][1])
                            p1_screen = (p1_screen[0], p1_screen[1] - off_y)
                            p2_screen = (p2_screen[0], p2_screen[1] - off_y)
                            pygame.draw.line(s, cor_traj, p1_screen, p2_screen, 2)
                            pygame.draw.circle(s, (255, 100, 100), p2_screen, 6)
                    
                    # Label
                    label = f"{p.dados.nome}: {hitbox.tipo} [RANGED]"
                    if hitbox.ativo:
                        label += " DISPARANDO!"
                    txt = fonte.render(label, True, (0, 200, 255))
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
                    
                else:
                    # Arma de lÃ¢mina normal
                    p1_screen = self.cam.converter(hitbox.pontos[0][0], hitbox.pontos[0][1])
                    p2_screen = self.cam.converter(hitbox.pontos[1][0], hitbox.pontos[1][1])
                    p1_screen = (p1_screen[0], p1_screen[1] - off_y)
                    p2_screen = (p2_screen[0], p2_screen[1] - off_y)
                    
                    # Linha da lÃ¢mina
                    cor_linha = (255, 0, 0, 200) if hitbox.ativo else (100, 100, 100, 100)
                    pygame.draw.line(s, cor_linha, p1_screen, p2_screen, 4)
                    
                    # Pontos nas extremidades
                    pygame.draw.circle(s, (255, 255, 0), p1_screen, 5)
                    pygame.draw.circle(s, (255, 0, 0), p2_screen, 5)
                    
                    # Label
                    label = f"{p.dados.nome}: {hitbox.tipo}"
                    if hitbox.ativo:
                        label += f" [ATACANDO t={p.timer_animacao:.2f}]"
                    txt = fonte.render(label, True, BRANCO)
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
            
            # Arma de Ã¡rea
            else:
                # Desenha arco de Ã¢ngulo
                rad = math.radians(hitbox.angulo)
                rad_min = rad - math.radians(hitbox.largura_angular / 2)
                rad_max = rad + math.radians(hitbox.largura_angular / 2)
                
                # Linha central
                fx = cx_screen + math.cos(rad) * alcance_screen
                fy = cy_screen + math.sin(rad) * alcance_screen
                pygame.draw.line(s, (*cor_debug[:3], 150), (cx_screen, cy_screen), (int(fx), int(fy)), 2)
                
                # Limites do arco
                fx_min = cx_screen + math.cos(rad_min) * alcance_screen
                fy_min = cy_screen + math.sin(rad_min) * alcance_screen
                fx_max = cx_screen + math.cos(rad_max) * alcance_screen
                fy_max = cy_screen + math.sin(rad_max) * alcance_screen
                pygame.draw.line(s, (*cor_debug[:3], 100), (cx_screen, cy_screen), (int(fx_min), int(fy_min)), 1)
                pygame.draw.line(s, (*cor_debug[:3], 100), (cx_screen, cy_screen), (int(fx_max), int(fy_max)), 1)
            
            self.tela.blit(s, (0, 0))
        
        # Desenha painel de debug no canto
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


    def _desenhar_hud_multi(self):
        """v13.0: HUD compacto para multi-fighter - barras empilhadas por time."""
        # Agrupa fighters por time
        times = {}
        for f in self.fighters:
            times.setdefault(f.team_id, []).append(f)
        
        num_times = len(times)
        bar_w = min(200, (self.screen_width - 40) // max(num_times, 1) - 10)
        bar_h = 16
        mana_h = 6
        nome_h = 14
        slot_h = bar_h + mana_h + nome_h + 8  # total height per fighter slot
        
        for t_idx, (team_id, members) in enumerate(sorted(times.items())):
            cor_time = CORES_TIME_RENDER[team_id % len(CORES_TIME_RENDER)]
            
            # Distribui times: metade esquerda, metade direita
            if t_idx < (num_times + 1) // 2:
                base_x = 15 + t_idx * (bar_w + 15)
            else:
                right_idx = t_idx - (num_times + 1) // 2
                base_x = self.screen_width - (bar_w + 15) * (right_idx + 1)
            
            # Header do time
            ft_team = self._get_font("Arial", 12, bold=True)
            team_label = ft_team.render(f"TIME {team_id + 1}", True, cor_time)
            self.tela.blit(team_label, (base_x, 5))
            
            for m_idx, f in enumerate(members):
                y = 20 + m_idx * slot_h
                vida_vis = self.vida_visual.get(f, f.vida)
                
                # Nome
                ft_nome = self._get_font("Arial", 11, bold=True)
                cor_nome = (150, 150, 150) if f.morto else BRANCO
                self.tela.blit(ft_nome.render(f.dados.nome, True, cor_nome), (base_x + 2, y))
                
                y_bar = y + nome_h
                
                # Barra de HP
                pygame.draw.rect(self.tela, (20, 20, 20), (base_x, y_bar, bar_w, bar_h))
                pct_vis = max(0, vida_vis / f.vida_max) if f.vida_max > 0 else 0
                pct_real = max(0, f.vida / f.vida_max) if f.vida_max > 0 else 0
                if pct_vis > pct_real:
                    pygame.draw.rect(self.tela, BRANCO, (base_x, y_bar, int(bar_w * pct_vis), bar_h))
                cor_hp = (100, 100, 100) if f.morto else cor_time
                pygame.draw.rect(self.tela, cor_hp, (base_x, y_bar, int(bar_w * pct_real), bar_h))
                pygame.draw.rect(self.tela, BRANCO, (base_x, y_bar, bar_w, bar_h), 1)
                
                # Barra de Mana (compacta)
                y_mana = y_bar + bar_h + 2
                pct_mana = max(0, f.mana / f.mana_max) if f.mana_max > 0 else 0
                pygame.draw.rect(self.tela, (20, 20, 20), (base_x, y_mana, bar_w, mana_h))
                pygame.draw.rect(self.tela, AZUL_MANA, (base_x, y_mana, int(bar_w * pct_mana), mana_h))

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




