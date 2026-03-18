import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from efeitos.camera import Camera
from pipeline_video.fight_recorder import FightRecorder
from simulacao.sim_renderer import SimuladorRenderer
from utilitarios.estado_espectador import resolver_badges_estado


pygame.init()
pygame.font.init()


class _BadgeRenderer(SimuladorRenderer):
    def __init__(self):
        self.tela = pygame.Surface((800, 600), pygame.SRCALPHA)
        self.cam = Camera(800, 600)
        self.cam.set_arena_bounds(15, 10, 30, 20)
        self.portrait_mode = False


def _make_fighter(*, nome="Astra", cena=None, followup=None, acao="MATAR", momentum=0.65,
                  confianca=0.8, medo=0.12, excitacao=0.4, hp=84.0, burst=False, orbes=0):
    buffer_orbes = [SimpleNamespace(ativo=True, estado="orbitando") for _ in range(orbes)]
    return SimpleNamespace(
        vida=hp,
        vida_max=100.0,
        mana=54.0,
        mana_max=100.0,
        orbital_burst_cd=0.0 if burst else 999.0,
        buffer_orbes=buffer_orbes,
        dados=SimpleNamespace(
            nome=nome,
            classe="Duelista (Precisao)",
            cor_r=90,
            cor_g=180,
            cor_b=255,
            r=90,
            g=180,
            b=255,
        ),
        brain=SimpleNamespace(
            memoria_cena={"tipo": cena, "intensidade": 0.82 if cena else 0.0, "duracao": 1.6 if cena else 0.0},
            combo_state={"followup_forcado": followup, "timer": 0.32 if followup else 0.0},
            acao_atual=acao,
            momentum=momentum,
            confianca=confianca,
            medo=medo,
            excitacao=excitacao,
        ),
    )


def test_resolver_badges_prioritizes_scene_and_followup():
    fighter = _make_fighter(cena="virada", followup="PRESSIONAR")

    badges = resolver_badges_estado(fighter, max_badges=2)
    textos = [badge["texto"] for badge in badges]

    assert textos[0] == "VIRADA"
    assert "PRESSAO" in textos


def test_resolver_badges_surfaces_weapon_windows_without_raw_emotion_labels():
    fighter = _make_fighter(cena=None, followup=None, acao="CONTRA_ATAQUE", burst=True, orbes=2)

    badges = resolver_badges_estado(fighter, max_badges=2)
    textos = [badge["texto"] for badge in badges]

    assert "BURST" in textos
    assert "LEITURA" in textos or "ORBES" in textos


def test_sim_renderer_draws_status_badges_on_health_bar():
    renderer = _BadgeRenderer()
    fighter = _make_fighter(cena="sequencia_perfeita", followup="PRESSIONAR")

    renderer.desenhar_barras(fighter, 28, 24, (90, 180, 255), fighter.vida)

    assert renderer.tela.get_bounding_rect().width > 0


def test_fight_recorder_draws_status_badges_for_pipeline_overlay():
    recorder = FightRecorder(
        {"nome": "Astra", "cor_r": 90, "cor_g": 180, "cor_b": 255},
        {"nome": "Lanca Solar"},
        {"nome": "Vesper", "cor_r": 255, "cor_g": 96, "cor_b": 130},
        {"nome": "Lamina Lunar"},
    )
    fighter = _make_fighter(nome="Vesper", cena="quase_morte", followup="COMBATE", acao="RECUAR", hp=18.0)
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)

    recorder._draw_status_badges(surface, fighter, 32, 42, align_right=False, max_badges=2)

    assert pygame.surfarray.array_alpha(surface).sum() > 0
