import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from efeitos.camera import Camera
from pipeline_video.fight_recorder import FightRecorder
from simulacao.sim_renderer import SimuladorRenderer
from simulacao.simulacao import Simulador
from utilitarios.estado_espectador import resolver_destaque_cinematico


pygame.init()
pygame.font.init()


class _DummyRenderer(SimuladorRenderer):
    def __init__(self):
        self.tela = pygame.Surface((800, 600), pygame.SRCALPHA)
        self.cam = Camera(800, 600)
        self.cam.set_arena_bounds(15, 10, 30, 20)
        self.screen_width = 800
        self.screen_height = 600
        self.portrait_mode = False
        self.fighters = []
        self.direcao_cinematica = None


def _make_fighter(nome="Astra", cena="virada", intensidade=0.8, duracao=1.4):
    return SimpleNamespace(
        dados=SimpleNamespace(nome=nome),
        brain=SimpleNamespace(
            memoria_cena={"tipo": cena, "intensidade": intensidade, "duracao": duracao},
        ),
    )


def test_resolver_destaque_cinematico_prefers_stronger_scene():
    fighters = [
        _make_fighter("Astra", "dominando", 0.8, 1.5),
        _make_fighter("Nyx", "final_showdown", 0.65, 1.7),
    ]

    destaque = resolver_destaque_cinematico(fighters)

    assert destaque["tipo"] == "final_showdown"
    assert destaque["rotulo"] == "FINAL SHOWDOWN"


def test_resolver_destaque_cinematico_uses_rivalry_when_scene_is_quiet():
    fighters = [
        SimpleNamespace(
            dados=SimpleNamespace(nome="Astra"),
            brain=SimpleNamespace(
                memoria_cena={"tipo": None, "intensidade": 0.0, "duracao": 0.0},
                memoria_oponente={
                    "id_atual": "rival-1",
                    "adaptacao_por_oponente": {
                        "rival-1": {
                            "relacao_dominante": "vinganca",
                            "relacao_vinganca": 0.82,
                        }
                    },
                },
            ),
        )
    ]

    destaque = resolver_destaque_cinematico(fighters)

    assert destaque["tipo"] == "rivalidade_vinganca"
    assert destaque["rotulo"] == "REVANCHE"


def test_renderer_draws_cinematic_overlay_from_direction_state():
    renderer = _DummyRenderer()
    renderer.direcao_cinematica = {
        "tipo": "virada",
        "rotulo": "VIRADA",
        "cor": (94, 210, 255),
        "cor_secundaria": (188, 238, 255),
        "intensidade": 0.9,
        "overlay": 0.5,
        "overlay_timer": 0.3,
        "duracao_overlay": 0.4,
    }

    renderer._desenhar_overlay_cinematico()

    assert renderer.tela.get_bounding_rect().width > 0


def test_recorder_draws_cinematic_overlay_from_sim_state():
    recorder = FightRecorder(
        {"nome": "Astra", "cor_r": 90, "cor_g": 180, "cor_b": 255},
        {"nome": "Lanca Solar"},
        {"nome": "Vesper", "cor_r": 255, "cor_g": 96, "cor_b": 130},
        {"nome": "Lamina Lunar"},
    )
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)
    sim = SimpleNamespace(
        direcao_cinematica={
            "tipo": "quase_morte",
            "rotulo": "NO LIMITE",
            "cor": (255, 92, 112),
            "cor_secundaria": (255, 204, 214),
            "intensidade": 0.86,
            "overlay": 0.54,
            "overlay_timer": 0.32,
            "duracao_overlay": 0.46,
        }
    )

    recorder._draw_cinematic_overlay(surface, sim)

    assert pygame.surfarray.array_alpha(surface).sum() > 0


def test_simulador_activation_applies_camera_reactive_effects():
    chamadas = {"shake": [], "zoom": []}
    sim = Simulador.__new__(Simulador)
    sim.cam = SimpleNamespace(
        aplicar_shake=lambda intensidade, duracao: chamadas["shake"].append((intensidade, duracao)),
        zoom_punch=lambda intensidade, duracao: chamadas["zoom"].append((intensidade, duracao)),
    )
    sim.slow_mo_timer = 0.0
    sim.time_scale = 1.0
    sim.direcao_cinematica = {}

    perfil = {
        "tipo": "virada",
        "rotulo": "VIRADA",
        "cor": (94, 210, 255),
        "cor_secundaria": (188, 238, 255),
        "intensidade": 0.85,
        "overlay": 0.5,
        "duracao_overlay": 0.4,
        "shake": 5.6,
        "zoom": 0.04,
        "slow_scale": 0.88,
        "slow_duracao": 0.09,
        "lutador": _make_fighter(),
    }

    sim._ativar_direcao_cinematica(perfil)

    assert chamadas["shake"]
    assert chamadas["zoom"]
    assert sim.time_scale < 1.0
    assert sim.slow_mo_timer > 0.0
