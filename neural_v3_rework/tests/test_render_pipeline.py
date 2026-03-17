import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from efeitos.attack import AttackAnticipation, WeaponTrailEnhanced
from efeitos.camera import Camera
from modelos import Arma
from simulacao.sim_renderer import SimuladorRenderer


pygame.init()
pygame.font.init()


class _DummyRenderer(SimuladorRenderer):
    def __init__(self):
        self.tela = pygame.Surface((800, 600), pygame.SRCALPHA)
        self.cam = Camera(800, 600)
        self.cam.set_arena_bounds(15, 10, 30, 20)


class _DummyFighter:
    def __init__(self):
        self.pos = [5.0, 5.0]
        self.z = 0.0
        self.vel = [0.0, 0.0]
        self.angulo_olhar = 0.0
        self.dados = SimpleNamespace(
            nome="Dummy",
            cor_r=120,
            cor_g=180,
            cor_b=240,
            tamanho=1.8,
            forca=12,
            classe="Guerreiro (Força Bruta)",
        )


def test_renderer_accepts_utf8_weapon_style_and_rarity():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Fauces",
        tipo="Dupla",
        dano=5,
        peso=1,
        estilo="Adagas Gêmeas",
        raridade="Épico",
        r=240,
        g=50,
        b=60,
    )

    renderer.desenhar_arma(arma, (400, 300), 0.0, 1.8, 60, 1.2)

    assert renderer.tela.get_bounding_rect().width > 0


def test_weapon_trail_draw_uses_alpha_surface_path():
    fighter = _DummyFighter()
    trail = WeaponTrailEnhanced(
        fighter,
        {"cor": (255, 80, 80), "brilho": True, "duracao": 0.3, "largura": 6},
    )
    trail.add_point(5.0, 5.0, 8)
    trail.add_point(5.5, 5.2, 8)
    trail.add_point(6.0, 5.4, 8)

    tela = pygame.Surface((800, 600), pygame.SRCALPHA)
    cam = Camera(800, 600)
    cam.set_arena_bounds(15, 10, 30, 20)

    trail.draw(tela, cam, 50)

    assert tela.get_bounding_rect().width > 0


def test_attack_anticipation_draw_renders_visible_lines():
    fighter = _DummyFighter()
    anticipation = AttackAnticipation(fighter, 18)

    tela = pygame.Surface((800, 600), pygame.SRCALPHA)
    cam = Camera(800, 600)
    cam.set_arena_bounds(15, 10, 30, 20)

    anticipation.draw(tela, cam, 50)

    assert tela.get_bounding_rect().width > 0


def test_magic_beam_render_does_not_mutate_particle_state():
    renderer = _DummyRenderer()
    renderer.particulas = []
    beam = SimpleNamespace(
        ativo=True,
        nome="Raio Divino",
        tipo_efeito="ATORDOAR",
        cor=(210, 220, 255),
        largura=8,
        segments=[(4.0, 4.0), (5.5, 4.3), (7.0, 5.0)],
    )

    renderer._desenhar_beam_magico(beam, 1.25)

    assert renderer.tela.get_bounding_rect().width > 0
    assert renderer.particulas == []


def test_magic_projectile_render_draws_dramatic_shape():
    renderer = _DummyRenderer()
    proj = SimpleNamespace(
        nome="Lanca de Luz",
        tipo="skill",
        elemento="LUZ",
        trail=[(4.8, 5.0), (5.1, 5.0), (5.4, 5.0)],
    )

    renderer._desenhar_projetil_magico(
        proj,
        px=400,
        py=280,
        pr=14,
        pulse_time=0.75,
        ang_visual=0.0,
        cor=(255, 235, 140),
    )

    assert renderer.tela.get_bounding_rect().width > 0


def test_magic_visual_profiles_distinguish_role_families():
    renderer = _DummyRenderer()

    controle = renderer._perfil_visual_magia({"classe_utilidade": "CONTROLE", "classe_forca": "IMPACTO"})
    cura = renderer._perfil_visual_magia({"classe_utilidade": "CURA", "classe_forca": "SUPORTE"})
    cataclismo = renderer._perfil_visual_magia({"classe_utilidade": "DANO", "classe_forca": "CATACLISMO"})

    assert controle["motivo"] == "controle"
    assert cura["ornamento"] == "petalas"
    assert cataclismo["ornamento"] == "espinhos"
    assert cataclismo["perigo"] > cura["perigo"]


def test_magic_area_control_render_draws_structured_telegraph():
    renderer = _DummyRenderer()
    area = SimpleNamespace(
        x=5.5,
        y=5.2,
        raio_atual=1.4,
        nome="Prisma de Gravidade",
        tipo_efeito="AREA",
        elemento="ARCANO",
        cor=(120, 180, 255),
        ativado=True,
        alpha=255,
        delay=0.0,
        classe_magia={
            "classe_utilidade": "CONTROLE",
            "classe_forca": "PRESSAO",
            "assinatura_visual": "campo",
        },
    )

    renderer._desenhar_area_magica(area, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_magic_orb_protection_render_draws_shell():
    renderer = _DummyRenderer()
    orbe = SimpleNamespace(
        x=6.0,
        y=5.5,
        raio_visual=0.32,
        nome="Escudo Astral",
        estado="carregando",
        elemento="LUZ",
        cor=(200, 240, 255),
        trail=[],
        particulas=[],
        pulso=1.4,
        tempo_carga=0.8,
        carga_max=1.0,
        classe_magia={
            "classe_utilidade": "PROTECAO",
            "classe_forca": "SUPORTE",
            "assinatura_visual": "domo",
        },
    )

    renderer._desenhar_orbe_magico(orbe)

    assert renderer.tela.get_bounding_rect().width > 0


def test_iconic_magic_signatures_map_by_skill_name():
    renderer = _DummyRenderer()

    assert renderer._assinatura_magia_especifica(nome="Meteoro")["variante"] == "meteoro_brutal"
    assert renderer._assinatura_magia_especifica(nome="Julgamento Celestial")["variante"] == "julgamento_celestial"
    assert renderer._assinatura_magia_especifica(nome="Desintegrar")["variante"] == "desintegrar"


def test_iconic_area_render_supports_void_collapse_signature():
    renderer = _DummyRenderer()
    area = SimpleNamespace(
        x=6.1,
        y=5.0,
        raio_atual=1.6,
        nome="Colapso do Vazio",
        tipo_efeito="AREA",
        elemento="VOID",
        cor=(40, 0, 80),
        ativado=True,
        alpha=255,
        delay=0.0,
        classe_magia={
            "classe_utilidade": "CONTROLE",
            "classe_forca": "CATACLISMO",
            "assinatura_visual": "campo",
        },
    )

    renderer._desenhar_area_magica(area, 1.6)

    assert renderer.tela.get_bounding_rect().width > 0


def test_iconic_beam_render_supports_desintegrate_signature():
    renderer = _DummyRenderer()
    beam = SimpleNamespace(
        ativo=True,
        nome="Desintegrar",
        tipo_efeito="BEAM",
        cor=(220, 120, 255),
        largura=10,
        segments=[(4.2, 4.5), (5.8, 4.7), (7.2, 5.0)],
        classe_magia={
            "classe_utilidade": "DANO",
            "classe_forca": "PRESSAO",
            "assinatura_visual": "fluxo",
        },
    )

    renderer._desenhar_beam_magico(beam, 0.9)

    assert renderer.tela.get_bounding_rect().width > 0


def test_buff_overlay_renders_arcane_shield_signature():
    renderer = _DummyRenderer()
    lutador = SimpleNamespace(
        buffs_ativos=[
            SimpleNamespace(
                ativo=True,
                nome="Escudo Arcano",
                cor=(100, 150, 255),
                elemento="ARCANO",
                vida=4.0,
                duracao=5.0,
                escudo=40.0,
                escudo_atual=28.0,
                classe_magia={
                    "classe_utilidade": "PROTECAO",
                    "classe_forca": "SUPORTE",
                    "assinatura_visual": "domo",
                },
            )
        ]
    )

    renderer._desenhar_buffs_lutador(lutador, (420, 320), 26, 1.2)

    assert renderer.tela.get_bounding_rect().width > 0


def test_transform_overlay_renders_lightning_form_signature():
    renderer = _DummyRenderer()
    lutador = SimpleNamespace(
        transformacao_ativa=SimpleNamespace(
            ativo=True,
            nome="Forma Relampago",
            cor=(255, 255, 180),
            vida=6.0,
            duracao=8.0,
            aura_raio=0.0,
        )
    )

    renderer._desenhar_transformacao_lutador(lutador, (380, 280), 24, 0.85)

    assert renderer.tela.get_bounding_rect().width > 0


def test_summon_render_supports_phoenix_signature():
    renderer = _DummyRenderer()
    summon = SimpleNamespace(
        ativo=True,
        x=5.5,
        y=5.0,
        nome="Fenix",
        cor=(255, 170, 70),
        elemento="FOGO",
        vida=40.0,
        vida_max=80.0,
        vida_timer=6.0,
        alvo=None,
        angulo=0.0,
        flash_timer=0.0,
        revive_count=1,
        classe_magia={
            "classe_utilidade": "INVOCACAO",
            "classe_forca": "PRESSAO",
            "assinatura_visual": "sigilo",
        },
    )

    renderer._desenhar_summon_magico(summon, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_trap_render_supports_light_prison_signature():
    renderer = _DummyRenderer()
    trap = SimpleNamespace(
        ativo=True,
        x=5.2,
        y=5.1,
        nome="Prisao de Luz",
        cor=(255, 255, 180),
        elemento="LUZ",
        raio=0.9,
        bloqueia_movimento=False,
        ativada=False,
        vida=40.0,
        vida_max=50.0,
        vida_timer=6.0,
        flash_timer=0.0,
        classe_magia={
            "classe_utilidade": "CONTROLE",
            "classe_forca": "SUPORTE",
            "assinatura_visual": "campo",
        },
    )

    renderer._desenhar_trap_magica(trap, 1.4)

    assert renderer.tela.get_bounding_rect().width > 0
