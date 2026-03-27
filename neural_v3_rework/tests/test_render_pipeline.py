import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from efeitos.attack import AttackAnticipation, WeaponTrailEnhanced
from efeitos.camera import Camera
from modelos import Arma
import simulacao.sim_renderer as sim_renderer_module
from simulacao.sim_renderer import SimuladorRenderer
from utilitarios.config import COR_FUNDO


pygame.init()
pygame.font.init()


class _DummyRenderer(SimuladorRenderer):
    def __init__(self):
        self.tela = pygame.Surface((800, 600), pygame.SRCALPHA)
        self.cam = Camera(800, 600)
        self.cam.set_arena_bounds(15, 10, 30, 20)
        self.rastros = {}


class _DummyFrameRenderer(_DummyRenderer):
    def __init__(self):
        super().__init__()
        self.screen_width = 800
        self.screen_height = 600
        self.arena = None
        self.decals = []
        self.areas = []
        self.beams = []
        self.particulas = []
        self.summons = []
        self.traps = []
        self.fighters = []
        self.projeteis = []
        self.dash_trails = []
        self.hit_sparks = []
        self.magic_clashes = []
        self.impact_flashes = []
        self.block_effects = []
        self.shockwaves = []
        self.textos = []
        self.attack_anims = None
        self.magic_vfx = None
        self.movement_anims = None
        self.show_hitbox_debug = False
        self.show_hud = False
        self.show_analysis = False
        self.vencedor = None
        self.paused = False
        self.modo_multi = False
        self.modo_partida = "duelo"
        self.portrait_mode = False
        self.tempo_luta = 0
        self.TEMPO_MAX_LUTA = 99
        self.vida_visual_p1 = 100
        self.vida_visual_p2 = 100
        self.p1 = SimpleNamespace()
        self.p2 = SimpleNamespace()


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


def _make_render_fighter(*, arma=None, morto=False, atacando=False, adrenalina=False):
    return SimpleNamespace(
        pos=[5.0, 5.0],
        z=0.0,
        morto=morto,
        dados=SimpleNamespace(
            tamanho=1.8,
            nome="Dummy",
            cor_r=120,
            cor_g=180,
            cor_b=240,
            arma_obj=arma,
        ),
        arma_droppada_pos=[5.3, 5.1],
        arma_droppada_ang=25.0,
        flash_timer=0.0,
        flash_cor=(255, 255, 255),
        stun_timer=0.0,
        atacando=atacando,
        brain=None,
        modo_adrenalina=adrenalina,
        weapon_anim_shake=(3, -2),
        weapon_anim_scale=1.14,
        angulo_olhar=20.0,
        angulo_arma_visual=40.0,
        vida=75.0,
        vida_max=100.0,
        timer_animacao=0.15,
        weapon_trail_positions=[],
    )


def _make_hitbox_debug_fighter(*, nome="Dummy", team_id=0):
    return SimpleNamespace(
        morto=False,
        team_id=team_id,
        z=0.2,
        dados=SimpleNamespace(nome=nome, arma_obj=None),
        timer_animacao=0.15,
        atacando=False,
        alcance_ideal=1.5,
        cooldown_ataque=0.3,
        brain=None,
        pos=[5.0, 5.0],
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


def _make_weapon_presence_fighter(
    *,
    familia="foco",
    tipo="Magica",
    ornamento="anel_runico",
    brilho=0.42,
):
    arma = SimpleNamespace(
        tipo=tipo,
        estilo="Catalisador",
        familia=familia,
        perfil_visual={"ornamento": ornamento, "brilho": brilho},
        afinidade_elemento="ARCANO",
        r=120,
        g=180,
        b=255,
    )
    return SimpleNamespace(
        dados=SimpleNamespace(arma_obj=arma),
        angulo_arma_visual=35.0,
    )


def test_weapon_presence_context_captures_family_tip_and_ornament():
    renderer = _DummyRenderer()
    fighter = _make_weapon_presence_fighter()

    contexto = renderer._criar_contexto_presenca_arma(fighter, (400, 300), 48, 1.18)

    assert contexto is not None
    assert contexto.familia == "foco"
    assert contexto.ornamento == "anel_runico"
    assert contexto.tip_x != contexto.centro[0]
    assert contexto.glow_r > 0
    assert contexto.paleta["core"] != contexto.cor


def test_weapon_presence_render_runs_context_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    fighter = _make_weapon_presence_fighter()
    contexto = SimpleNamespace()
    calls = []

    monkeypatch.setattr(renderer, "_criar_contexto_presenca_arma", lambda *args: contexto)
    monkeypatch.setattr(renderer, "_desenhar_aura_presenca_arma", lambda ctx: calls.append("aura"))
    monkeypatch.setattr(renderer, "_desenhar_forma_presenca_arma", lambda ctx: calls.append("forma"))
    monkeypatch.setattr(renderer, "_desenhar_ornamento_presenca_arma", lambda ctx: calls.append("ornamento"))

    renderer._desenhar_presenca_arma(fighter, (400, 300), 48, 1.18)

    assert calls == ["aura", "forma", "ornamento"]


def test_weapon_presence_render_draws_runic_focus():
    renderer = _DummyRenderer()
    fighter = _make_weapon_presence_fighter()

    renderer._desenhar_presenca_arma(fighter, (400, 300), 48, 1.18)

    assert renderer.tela.get_bounding_rect().width > 0


def test_fighter_render_context_captures_geometry_and_weapon_stage():
    renderer = _DummyRenderer()
    arma = SimpleNamespace(tipo="Reta", r=220, g=80, b=60)
    fighter = _make_render_fighter(arma=arma, atacando=True)

    contexto = renderer._criar_contexto_lutador(fighter)

    assert contexto.raio > 0
    assert contexto.centro_arma != contexto.centro
    assert contexto.tipo_arma_norm == "reta"
    assert contexto.desenha_slash_arc is True
    assert contexto.cor_corpo == (120, 180, 240)


def test_fighter_render_runs_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    fighter = _make_render_fighter()
    contexto = SimpleNamespace()
    calls = []

    monkeypatch.setattr(renderer, "_criar_contexto_lutador", lambda lutador: contexto)
    monkeypatch.setattr(renderer, "_desenhar_rastro_lutador", lambda ctx: calls.append("rastro"))
    monkeypatch.setattr(renderer, "_desenhar_sombra_lutador", lambda ctx: calls.append("sombra"))
    monkeypatch.setattr(renderer, "_desenhar_corpo_lutador", lambda ctx: calls.append("corpo"))
    monkeypatch.setattr(renderer, "_desenhar_emocoes_lutador", lambda ctx: calls.append("emocoes"))
    monkeypatch.setattr(renderer, "_desenhar_adrenalina_lutador", lambda ctx: calls.append("adrenalina"))
    monkeypatch.setattr(renderer, "_desenhar_efeitos_lutador", lambda ctx: calls.append("efeitos"))
    monkeypatch.setattr(renderer, "_desenhar_arma_lutador", lambda ctx: calls.append("arma"))
    monkeypatch.setattr(renderer, "_desenhar_nome_lutador", lambda ctx: calls.append("nome"))

    renderer.desenhar_lutador(fighter)

    assert calls == ["rastro", "sombra", "corpo", "emocoes", "adrenalina", "efeitos", "arma", "nome"]


def test_fighter_render_draws_body_and_name_without_weapon():
    renderer = _DummyRenderer()
    fighter = _make_render_fighter()

    renderer.desenhar_lutador(fighter)

    assert renderer.tela.get_bounding_rect().width > 0


def test_slash_arc_context_captures_sweep_geometry():
    from efeitos.weapon_animations import WEAPON_PROFILES

    renderer = _DummyRenderer()
    arma = SimpleNamespace(tipo="Reta", estilo="Espada", r=220, g=80, b=60)
    fighter = _make_render_fighter(arma=arma, atacando=True)
    profile = WEAPON_PROFILES["Reta"]
    antecipation_end = profile.anticipation_time / profile.total_time
    attack_end = (profile.anticipation_time + profile.attack_time + profile.impact_time) / profile.total_time
    fighter.timer_animacao = profile.total_time * (1 - ((antecipation_end + attack_end) / 2))

    contexto = renderer._criar_contexto_slash_arc(fighter, (400, 300), 52, 1.2)

    assert contexto is not None
    assert contexto.arc_radius > 0
    assert contexto.current_arc != contexto.arc_start
    assert contexto.surf_size > 10


def test_slash_arc_render_runs_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    fighter = _make_render_fighter()
    contexto = SimpleNamespace(surf_size=64, arc_center=(32, 32), centro=(400, 300))
    calls = []

    monkeypatch.setattr(renderer, "_criar_contexto_slash_arc", lambda *args: contexto)
    monkeypatch.setattr(renderer, "_desenhar_glow_slash_arc", lambda ctx, surf: calls.append("glow"))
    monkeypatch.setattr(renderer, "_desenhar_corpo_slash_arc", lambda ctx, surf: calls.append("corpo"))
    monkeypatch.setattr(renderer, "_desenhar_borda_slash_arc", lambda ctx, surf: calls.append("borda"))
    monkeypatch.setattr(renderer, "_desenhar_ponta_slash_arc", lambda ctx, surf: calls.append("ponta"))

    renderer._desenhar_slash_arc(fighter, (400, 300), 52, 1.2)

    assert calls == ["glow", "corpo", "borda", "ponta"]


def test_slash_arc_render_draws_visible_sweep():
    from efeitos.weapon_animations import WEAPON_PROFILES

    renderer = _DummyRenderer()
    arma = SimpleNamespace(tipo="Reta", estilo="Espada", r=220, g=80, b=60)
    fighter = _make_render_fighter(arma=arma, atacando=True)
    profile = WEAPON_PROFILES["Reta"]
    antecipation_end = profile.anticipation_time / profile.total_time
    attack_end = (profile.anticipation_time + profile.attack_time + profile.impact_time) / profile.total_time
    fighter.timer_animacao = profile.total_time * (1 - ((antecipation_end + attack_end) / 2))

    renderer._desenhar_slash_arc(fighter, (400, 300), 52, 1.2)

    assert renderer.tela.get_bounding_rect().width > 0


def test_weapon_trail_context_captures_screen_points_and_profile():
    renderer = _DummyRenderer()
    arma = SimpleNamespace(tipo="Magica", estilo="Catalisador", r=120, g=180, b=255)
    fighter = _make_render_fighter(arma=arma)
    fighter.weapon_trail_positions = [(5.0, 5.0, 0.2), (5.4, 5.2, 0.7), (5.8, 5.4, 1.0)]

    contexto = renderer._criar_contexto_weapon_trail(fighter)

    assert contexto is not None
    assert contexto.tipo_norm == "magica"
    assert len(contexto.screen_pts) == 3
    assert contexto.profile is not None


def test_weapon_trail_render_runs_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    fighter = _make_render_fighter()
    contexto = SimpleNamespace()
    calls = []

    monkeypatch.setattr(renderer, "_criar_contexto_weapon_trail", lambda *args: contexto)
    monkeypatch.setattr(renderer, "_desenhar_trail_avancado_arma", lambda ctx: calls.append("avancado"))
    monkeypatch.setattr(renderer, "_desenhar_segmentos_weapon_trail", lambda ctx: calls.append("segmentos"))

    renderer._desenhar_weapon_trail(fighter)

    assert calls == ["avancado", "segmentos"]


def test_weapon_trail_render_draws_magical_segment():
    renderer = _DummyRenderer()
    arma = SimpleNamespace(tipo="Magica", estilo="Catalisador", r=120, g=180, b=255)
    fighter = _make_render_fighter(arma=arma)
    fighter.weapon_trail_positions = [(5.0, 5.0, 0.4), (5.4, 5.2, 0.8), (5.8, 5.4, 1.0)]

    renderer._desenhar_weapon_trail(fighter)

    assert renderer.tela.get_bounding_rect().width > 0


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


def test_magic_beam_context_captures_variant_and_local_points():
    renderer = _DummyRenderer()
    beam = SimpleNamespace(
        ativo=True,
        nome="Raio Sagrado",
        tipo_efeito="ATORDOAR",
        cor=(210, 220, 255),
        largura=8,
        segments=[(4.0, 4.0), (5.5, 4.3), (7.0, 5.0)],
    )

    contexto = renderer._criar_contexto_beam_magico(beam, 1.25)

    assert contexto is not None
    assert contexto.assinatura["variante"] == "raio_sagrado"
    assert len(contexto.pts_screen) == 3
    assert len(contexto.local_pts) == 3
    assert contexto.width > 0
    assert contexto.height > 0


def test_magic_beam_render_runs_context_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    beam = SimpleNamespace(
        ativo=True,
        nome="Raio Sagrado",
        tipo_efeito="ATORDOAR",
        cor=(210, 220, 255),
        largura=8,
        segments=[(4.0, 4.0), (5.5, 4.3), (7.0, 5.0)],
    )
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_corpo_beam_magico", lambda contexto, surf: calls.append("corpo"))
    monkeypatch.setattr(renderer, "_desenhar_variante_beam_magico", lambda contexto, surf: calls.append("variante"))
    monkeypatch.setattr(renderer, "_desenhar_terminais_beam_magico", lambda contexto: calls.append("terminais"))

    renderer._desenhar_beam_magico(beam, 1.25)

    assert calls == ["corpo", "variante", "terminais"]


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


def test_magic_projectile_context_captures_variant_and_tail_geometry():
    renderer = _DummyRenderer()
    proj = SimpleNamespace(
        nome="Lanca de Luz",
        tipo="skill",
        elemento="LUZ",
        trail=[],
    )

    contexto = renderer._criar_contexto_projetil_magico(
        proj,
        px=400,
        py=280,
        pr=14,
        pulse_time=0.75,
        ang_visual=0.0,
        cor=(255, 235, 140),
    )

    assert contexto.variante == "lanca_luz"
    assert contexto.elemento == "LUZ"
    assert contexto.tail_x < contexto.px
    assert contexto.tail_y == pytest.approx(contexto.py)


def test_magic_projectile_prefers_explicit_variant_before_other_shape_routes(monkeypatch):
    renderer = _DummyRenderer()
    proj = SimpleNamespace(
        nome="Lanca de Luz",
        tipo="skill",
        elemento="LUZ",
        trail=[],
    )
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_preludio_projetil_magico", lambda contexto: calls.append("preludio"))
    monkeypatch.setattr(
        renderer,
        "_desenhar_variante_explicita_projetil_magico",
        lambda contexto: calls.append(("variante", contexto.variante)) or True,
    )
    monkeypatch.setattr(renderer, "_desenhar_motivo_projetil_magico", lambda contexto: calls.append("motivo") or False)
    monkeypatch.setattr(renderer, "_desenhar_assinatura_projetil_magico", lambda contexto: calls.append("assinatura") or False)
    monkeypatch.setattr(renderer, "_desenhar_fallback_projetil_magico", lambda contexto: calls.append("fallback"))
    monkeypatch.setattr(renderer, "_desenhar_overlay_elemental_projetil_magico", lambda contexto: calls.append("overlay"))
    monkeypatch.setattr(renderer, "_desenhar_nucleo_projetil_magico", lambda contexto: calls.append("nucleo"))

    renderer._desenhar_projetil_magico(
        proj,
        px=400,
        py=280,
        pr=14,
        pulse_time=0.75,
        ang_visual=0.0,
        cor=(255, 235, 140),
    )

    assert ("variante", "lanca_luz") in calls
    assert "motivo" not in calls
    assert "assinatura" not in calls
    assert "fallback" not in calls
    assert calls[-2:] == ["overlay", "nucleo"]


def test_magic_projectile_uses_motivo_route_when_no_named_variant(monkeypatch):
    renderer = _DummyRenderer()
    proj = SimpleNamespace(
        nome="Pulso Vital",
        tipo="skill",
        elemento="NATUREZA",
        trail=[],
        classe_magia={
            "classe_utilidade": "CURA",
            "classe_forca": "SUPORTE",
            "assinatura_visual": "anel",
        },
    )
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_preludio_projetil_magico", lambda contexto: calls.append("preludio"))
    monkeypatch.setattr(renderer, "_desenhar_variante_explicita_projetil_magico", lambda contexto: calls.append("variante") or False)
    monkeypatch.setattr(renderer, "_desenhar_motivo_projetil_magico", lambda contexto: calls.append(("motivo", contexto.perfil["motivo"])) or True)
    monkeypatch.setattr(renderer, "_desenhar_assinatura_projetil_magico", lambda contexto: calls.append("assinatura") or False)
    monkeypatch.setattr(renderer, "_desenhar_fallback_projetil_magico", lambda contexto: calls.append("fallback"))
    monkeypatch.setattr(renderer, "_desenhar_overlay_elemental_projetil_magico", lambda contexto: calls.append("overlay"))
    monkeypatch.setattr(renderer, "_desenhar_nucleo_projetil_magico", lambda contexto: calls.append("nucleo"))

    renderer._desenhar_projetil_magico(
        proj,
        px=396,
        py=284,
        pr=12,
        pulse_time=0.5,
        ang_visual=15.0,
        cor=(140, 220, 140),
    )

    assert ("motivo", "cura") in calls
    assert "assinatura" not in calls
    assert "fallback" not in calls


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


def test_magic_area_context_captures_role_and_activation_state():
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

    contexto = renderer._criar_contexto_area_magica(area, 1.1)

    assert contexto is not None
    assert contexto.zonal is True
    assert contexto.suporte is False
    assert contexto.classe["assinatura_visual"] == "campo"
    assert contexto.perfil["motivo"] == "controle"
    assert contexto.raio_visual > 0


def test_magic_area_render_runs_context_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    area = SimpleNamespace(
        x=5.5,
        y=5.2,
        raio_atual=1.4,
        nome="Prisma de Gravidade",
        tipo_efeito="AREA",
        elemento="ARCANO",
        cor=(120, 180, 255),
        ativado=False,
        alpha=255,
        delay=0.4,
        classe_magia={
            "classe_utilidade": "CONTROLE",
            "classe_forca": "PRESSAO",
            "assinatura_visual": "campo",
        },
    )
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_base_area_magica", lambda contexto: calls.append("base"))
    monkeypatch.setattr(renderer, "_desenhar_aneis_area_magica", lambda contexto: calls.append("aneis"))
    monkeypatch.setattr(renderer, "_desenhar_marcadores_area_magica", lambda contexto: calls.append("marcadores"))
    monkeypatch.setattr(renderer, "_desenhar_centro_area_magica", lambda contexto: calls.append("centro"))
    monkeypatch.setattr(renderer, "_desenhar_variante_area_magica", lambda contexto: calls.append("variante"))
    monkeypatch.setattr(renderer, "_desenhar_nucleo_area_magica", lambda contexto: calls.append("nucleo"))
    monkeypatch.setattr(renderer, "_desenhar_aviso_area_magica", lambda contexto: calls.append("aviso"))

    renderer._desenhar_area_magica(area, 1.1)

    assert calls == ["base", "aneis", "marcadores", "centro", "variante", "nucleo", "aviso"]


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


def test_magic_orb_context_captures_signature_and_pulse():
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
    ox, oy = renderer.cam.converter(orbe.x * 32, orbe.y * 32)
    or_visual = renderer.cam.converter_tam(orbe.raio_visual * 32)

    contexto = renderer._criar_contexto_orbe_magico(orbe, ox, oy, or_visual)

    assert contexto.assinatura == "domo"
    assert contexto.perfil["motivo"] == "protecao"
    assert 0.7 <= contexto.pulso <= 1.0


def test_magic_orb_render_runs_context_pipeline_in_order(monkeypatch):
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
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_trilha_orbe_magico", lambda contexto: calls.append("trilha"))
    monkeypatch.setattr(renderer, "_desenhar_particulas_orbe_magico", lambda contexto: calls.append("particulas"))
    monkeypatch.setattr(renderer, "_desenhar_corpo_orbe_magico", lambda contexto: calls.append("corpo"))
    monkeypatch.setattr(renderer, "_desenhar_carga_orbe_magico", lambda contexto: calls.append("carga"))

    renderer._desenhar_orbe_magico(orbe)

    assert calls == ["trilha", "particulas", "corpo", "carga"]


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


def test_orbital_shield_weapon_render_draws_guardian_shape():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Egide Prismatica",
        tipo="Orbital",
        familia="orbital",
        subtipo="escudo",
        estilo="Bastiao Prismatico",
        dano=7,
        peso=4,
        quantidade_orbitais=2,
        r=150,
        g=220,
        b=255,
        raridade="Epico",
    )

    renderer.desenhar_arma(arma, (400, 300), 0.0, 1.8, 60, 1.15)

    assert renderer.tela.get_bounding_rect().width > 0


def test_weapon_render_context_captures_visual_contract(monkeypatch):
    renderer = _DummyRenderer()
    renderer.cam.zoom = 1.5
    arma = Arma(
        nome="Lamina Astral",
        tipo="Magica",
        estilo="Espada Espectral",
        dano=9,
        peso=2,
        raridade="Epico",
        r=120,
        g=160,
        b=210,
    )
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 900)

    contexto = renderer._criar_contexto_render_arma(arma, (320, 240), 30.0, 1.8, 60, 1.2)

    assert contexto.centro == (320, 240)
    assert contexto.rad == pytest.approx(0.5235987756)
    assert contexto.zoom == 1.5
    assert contexto.tipo_norm == "magica"
    assert contexto.estilo_norm == "espada espectral"
    assert contexto.cor == (120, 160, 210)
    assert contexto.cor_clara == (180, 220, 255)
    assert contexto.cor_escura == (80, 120, 170)
    assert contexto.raridade_norm == "epico"
    assert contexto.cor_raridade == (148, 0, 211)
    assert contexto.larg_base == 8
    assert contexto.atacando is True
    assert contexto.tempo == 900
    assert contexto.zw(2) == 3


def test_weapon_render_dispatch_routes_orbital_to_extracted_helper(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Sentinela Prismatica",
        tipo="Orbital",
        estilo="Bastiao",
        dano=5,
        peso=3,
        raridade="Raro",
        r=140,
        g=220,
        b=255,
    )
    chamadas = []

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_orbital",
        lambda contexto: chamadas.append(contexto),
    )

    renderer.desenhar_arma(arma, (400, 280), 45.0, 1.8, 60, 1.1)

    assert len(chamadas) == 1
    assert chamadas[0].tipo_norm == "orbital"
    assert chamadas[0].centro == (400, 280)


def test_weapon_render_dispatch_routes_reta_to_extracted_helper(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Lanca Solar",
        tipo="Reta",
        estilo="Lanca de Estocada",
        dano=7,
        peso=3,
        raridade="Raro",
        r=210,
        g=190,
        b=120,
    )
    chamadas = []

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_reta",
        lambda contexto: chamadas.append(contexto),
    )

    renderer.desenhar_arma(arma, (360, 260), 15.0, 1.8, 60, 1.1)

    assert len(chamadas) == 1
    assert chamadas[0].tipo_norm == "reta"
    assert chamadas[0].estilo_norm == "lanca de estocada"


def test_weapon_reta_dispatch_routes_maca_branch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Rompe Ossos", tipo="Reta", estilo="Maca de Contusao", dano=8, peso=4, raridade="Raro", r=180, g=170, b=120)
    contexto = renderer._criar_contexto_render_arma(arma, (360, 260), 15.0, 1.8, 60, 1.1)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_arma_reta_maca", lambda *args: calls.append("maca"))

    renderer._desenhar_arma_reta(contexto)

    assert calls == ["maca"]


def test_weapon_arremesso_dispatch_routes_chakram_branch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Disco Solar", tipo="Arremesso", estilo="Chakram", dano=6, peso=1, raridade="Raro", r=220, g=180, b=90)
    contexto = renderer._criar_contexto_render_arma(arma, (360, 260), 15.0, 1.8, 60, 1.1)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_arma_arremesso_chakram", lambda *args: calls.append("chakram"))

    renderer._desenhar_arma_arremesso(contexto)

    assert calls == ["chakram"] * min(5, int(getattr(arma, "quantidade", 3)))


def test_weapon_arco_dispatch_routes_besta_branch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Vigia", tipo="Arco", estilo="Besta de Repeticao", dano=7, peso=3, raridade="Raro", r=150, g=120, b=90)
    contexto = renderer._criar_contexto_render_arma(arma, (360, 260), 15.0, 1.8, 60, 1.1)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_arma_arco_besta", lambda *args: calls.append("besta"))

    renderer._desenhar_arma_arco(contexto)

    assert calls == ["besta"]


def test_weapon_magica_dispatch_routes_runa_branch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Sigilo Prismal", tipo="Magica", estilo="Runa Arcana", dano=7, peso=1, raridade="Epico", r=110, g=180, b=255)
    contexto = renderer._criar_contexto_render_arma(arma, (360, 260), 15.0, 1.8, 60, 1.1)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_arma_magica_runa", lambda *args: calls.append("runa"))

    renderer._desenhar_arma_magica(contexto)

    assert calls == ["runa"] * min(5, int(getattr(arma, "quantidade", 3)))


def test_weapon_render_dispatch_routes_transformavel_to_extracted_helper(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Aegis Mutante", tipo="Transformavel", estilo="Lanca Espada", dano=8, peso=3, raridade="Raro", r=180, g=200, b=220)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_arma_transformavel", lambda contexto: calls.append(contexto))

    renderer.desenhar_arma(arma, (380, 275), 12.0, 1.8, 60, 1.1)

    assert len(calls) == 1
    assert calls[0].tipo_norm == "transformavel"


def test_transformable_weapon_routes_lanca_espada_branch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Aegis Mutante", tipo="Transformavel", estilo="Lanca Espada", dano=8, peso=3, raridade="Raro", r=180, g=200, b=220)
    arma.forma_atual = 1
    contexto = renderer._criar_contexto_render_arma(arma, (380, 275), 12.0, 1.8, 60, 1.1)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_base_transformavel", lambda *args: calls.append("base"))
    monkeypatch.setattr(renderer, "_desenhar_transformavel_lanca_espada", lambda *args: calls.append("lanca_espada"))

    renderer._desenhar_arma_transformavel(contexto)

    assert calls == ["base", "lanca_espada"]


def test_transformable_weapon_routes_chicote_branch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Aco Serpente", tipo="Transformavel", estilo="Chicote Modular", dano=7, peso=2, raridade="Raro", r=190, g=140, b=100)
    arma.forma_atual = 2
    contexto = renderer._criar_contexto_render_arma(arma, (380, 275), 12.0, 1.8, 60, 1.1)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_base_transformavel", lambda *args: calls.append("base"))
    monkeypatch.setattr(renderer, "_desenhar_transformavel_chicote", lambda *args: calls.append("chicote"))

    renderer._desenhar_arma_transformavel(contexto)

    assert calls == ["base", "chicote"]


def test_transformable_weapon_still_draws_after_pipeline_extraction():
    renderer = _DummyRenderer()
    arma = Arma(nome="Aegis Mutante", tipo="Transformavel", estilo="Lanca Espada", dano=8, peso=3, raridade="Raro", r=180, g=200, b=220)
    arma.forma_atual = 1

    renderer.desenhar_arma(arma, (380, 275), 12.0, 1.8, 60, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_weapon_render_dispatch_routes_dupla_to_extracted_helper(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Fauces",
        tipo="Dupla",
        estilo="Adagas Gemeas",
        dano=6,
        peso=1,
        raridade="Epico",
        r=220,
        g=80,
        b=90,
    )
    chamadas = []

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla",
        lambda contexto: chamadas.append(contexto),
    )

    renderer.desenhar_arma(arma, (390, 275), 20.0, 1.8, 60, 1.1)

    assert len(chamadas) == 1
    assert chamadas[0].tipo_norm == "dupla"
    assert chamadas[0].estilo_norm == "adagas gemeas"


def test_weapon_render_dispatch_routes_corrente_to_extracted_helper(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Mangual do Crepusculo",
        tipo="Corrente",
        estilo="Mangual",
        dano=9,
        peso=4,
        raridade="Lendario",
        r=120,
        g=120,
        b=160,
    )
    chamadas = []

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_corrente",
        lambda contexto: chamadas.append(contexto),
    )

    renderer.desenhar_arma(arma, (420, 285), -15.0, 1.8, 60, 1.2)

    assert len(chamadas) == 1
    assert chamadas[0].tipo_norm == "corrente"
    assert chamadas[0].estilo_norm == "mangual"


def test_dual_weapon_adagas_gemeas_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Fauces",
        tipo="Dupla",
        estilo="Adagas Gemeas",
        dano=6,
        peso=1,
        raridade="Epico",
        r=220,
        g=80,
        b=90,
    )

    renderer.desenhar_arma(arma, (392, 278), 18.0, 1.8, 60, 1.14)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_style_routes_adagas_gemeas_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="adagas gemeas")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla_adagas_gemeas",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_dupla(contexto)

    assert calls == [contexto]


def test_dual_weapon_adagas_gemeas_runs_internal_pipeline(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Fauces", tipo="Dupla", estilo="Adagas Gemeas", dano=6, peso=1, raridade="Epico", r=220, g=80, b=90)
    contexto = renderer._criar_contexto_render_arma(arma, (392, 278), 18.0, 1.8, 60, 1.14)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_empunhadura_adagas_gemeas", lambda *args: calls.append("empunhadura"))
    monkeypatch.setattr(renderer, "_desenhar_lamina_adagas_gemeas", lambda *args: calls.append("lamina"))
    monkeypatch.setattr(renderer, "_desenhar_fx_adagas_gemeas", lambda *args: calls.append("fx"))

    renderer._desenhar_arma_dupla_adagas_gemeas(contexto)

    assert calls == ["empunhadura", "lamina", "fx", "empunhadura", "lamina", "fx"]


def test_dual_weapon_kamas_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Luas Cortantes",
        tipo="Dupla",
        estilo="Kamas",
        dano=7,
        peso=2,
        raridade="Raro",
        r=120,
        g=190,
        b=120,
    )

    renderer.desenhar_arma(arma, (395, 281), 16.0, 1.8, 60, 1.12)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_style_routes_kamas_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="kamas")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla_kamas",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_dupla(contexto)

    assert calls == [contexto]


def test_dual_weapon_sai_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Sai do Vigia",
        tipo="Dupla",
        estilo="Sai",
        dano=6,
        peso=2,
        raridade="Incomum",
        r=160,
        g=170,
        b=190,
    )

    renderer.desenhar_arma(arma, (398, 284), 17.0, 1.8, 60, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_style_routes_sai_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="sai")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla_sai",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_dupla(contexto)

    assert calls == [contexto]


def test_dual_weapon_garras_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Garras da Serra",
        tipo="Dupla",
        estilo="Garras",
        dano=7,
        peso=2,
        raridade="Raro",
        r=170,
        g=130,
        b=90,
    )

    renderer.desenhar_arma(arma, (401, 286), 19.0, 1.8, 60, 1.13)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_style_routes_garras_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="garras")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla_garras",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_dupla(contexto)

    assert calls == [contexto]


def test_dual_weapon_tonfas_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Tonfas de Bronze",
        tipo="Dupla",
        estilo="Tonfas",
        dano=6,
        peso=2,
        raridade="Incomum",
        r=160,
        g=120,
        b=90,
    )

    renderer.desenhar_arma(arma, (404, 288), 21.0, 1.8, 60, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_style_routes_tonfas_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="tonfas")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla_tonfas",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_dupla(contexto)

    assert calls == [contexto]


def test_dual_weapon_default_variant_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Espadas Curtas do Eclipse",
        tipo="Dupla",
        estilo="Espadas Curtas",
        dano=7,
        peso=2,
        raridade="Raro",
        r=140,
        g=150,
        b=190,
    )

    renderer.desenhar_arma(arma, (406, 289), 14.0, 1.8, 60, 1.11)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_style_routes_default_variant_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="espadas curtas")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_dupla_padrao",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_dupla(contexto)

    assert calls == [contexto]


def test_inline_legacy_weapon_wrapper_forwards_to_canonical_dispatch(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Reliquia Antiga",
        tipo="Reta",
        estilo="Espada Longa",
        dano=6,
        peso=2,
        raridade="Comum",
        r=150,
        g=150,
        b=170,
    )
    chamadas = []

    monkeypatch.setattr(
        renderer,
        "desenhar_arma",
        lambda *args: chamadas.append(args),
    )

    renderer._desenhar_arma_inline_legacy(arma, (401, 299), 12.5, 1.8, 60, 1.05)

    assert chamadas == [(arma, (401, 299), 12.5, 1.8, 60, 1.05)]


def test_throwing_weapon_render_still_draws_after_helper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Machado de Guerra",
        tipo="Arremesso",
        estilo="Machado",
        dano=8,
        peso=3,
        quantidade=2,
        raridade="Raro",
        r=170,
        g=170,
        b=180,
    )

    renderer.desenhar_arma(arma, (400, 300), 25.0, 1.8, 60, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_dual_weapon_alt_style_still_draws_after_helper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Presas de Jade",
        tipo="Dupla",
        estilo="Sai",
        dano=7,
        peso=2,
        raridade="Raro",
        r=120,
        g=200,
        b=180,
    )

    renderer.desenhar_arma(arma, (405, 295), 35.0, 1.8, 60, 1.15)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_alt_style_still_draws_after_helper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Laco Rubro",
        tipo="Corrente",
        estilo="Chicote",
        dano=7,
        peso=2,
        raridade="Raro",
        r=180,
        g=90,
        b=70,
    )

    renderer.desenhar_arma(arma, (415, 300), -22.0, 1.8, 60, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_mangual_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Mangual do Crepusculo",
        tipo="Corrente",
        estilo="Mangual",
        dano=9,
        peso=4,
        raridade="Lendario",
        r=120,
        g=120,
        b=160,
    )

    renderer.desenhar_arma(arma, (420, 285), -15.0, 1.8, 60, 1.2)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_style_routes_mangual_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="mangual")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_corrente_mangual",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_corrente(contexto)

    assert calls == [contexto]


def test_chain_weapon_mangual_runs_internal_pipeline(monkeypatch):
    renderer = _DummyRenderer()
    arma = Arma(nome="Mangual do Crepusculo", tipo="Corrente", estilo="Mangual", dano=9, peso=4, raridade="Lendario", r=120, g=120, b=160)
    contexto = renderer._criar_contexto_render_arma(arma, (420, 285), -15.0, 1.8, 60, 1.2)
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_cabo_mangual", lambda *args: calls.append("cabo"))
    monkeypatch.setattr(renderer, "_desenhar_pivo_mangual", lambda *args: calls.append("pivo"))
    monkeypatch.setattr(renderer, "_coletar_pontos_corrente_mangual", lambda *args: calls.append("coleta") or [(420, 285)])
    monkeypatch.setattr(renderer, "_desenhar_elos_mangual", lambda *args: calls.append("elos"))
    monkeypatch.setattr(renderer, "_desenhar_cabeca_mangual", lambda *args: calls.append("cabeca"))

    renderer._desenhar_arma_corrente_mangual(contexto)

    assert calls == ["cabo", "pivo", "coleta", "elos", "cabeca"]


def test_chain_weapon_meteor_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Meteor Hammer de Cinzas",
        tipo="Corrente",
        estilo="Meteor Hammer",
        dano=10,
        peso=4,
        raridade="Epico",
        r=170,
        g=90,
        b=60,
    )

    renderer.desenhar_arma(arma, (430, 292), -18.0, 1.8, 60, 1.18)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_style_routes_meteor_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="meteor")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_corrente_meteor",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_corrente(contexto)

    assert calls == [contexto]


def test_chain_weapon_kusarigama_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Kusarigama das Sombras",
        tipo="Corrente",
        estilo="Kusarigama",
        dano=9,
        peso=3,
        raridade="Raro",
        r=110,
        g=160,
        b=120,
    )

    renderer.desenhar_arma(arma, (426, 288), -20.0, 1.8, 60, 1.12)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_style_routes_kusarigama_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="kusarigama")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_corrente_kusarigama",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_corrente(contexto)

    assert calls == [contexto]


def test_chain_weapon_chicote_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Chicote do Eclipse",
        tipo="Corrente",
        estilo="Chicote",
        dano=8,
        peso=2,
        raridade="Raro",
        r=180,
        g=100,
        b=80,
    )

    renderer.desenhar_arma(arma, (418, 296), -24.0, 1.8, 60, 1.16)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_style_routes_chicote_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="chicote")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_corrente_chicote",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_corrente(contexto)

    assert calls == [contexto]


def test_chain_weapon_default_variant_still_draws_after_subhelper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Corrente de Vigia",
        tipo="Corrente",
        estilo="Corrente com Peso",
        dano=8,
        peso=3,
        raridade="Incomum",
        r=120,
        g=130,
        b=150,
    )

    renderer.desenhar_arma(arma, (424, 294), -17.0, 1.8, 60, 1.1)

    assert renderer.tela.get_bounding_rect().width > 0


def test_chain_weapon_style_routes_default_variant_to_subhelper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []
    contexto = SimpleNamespace(estilo_norm="corrente com peso")

    monkeypatch.setattr(
        renderer,
        "_desenhar_arma_corrente_padrao",
        lambda current: calls.append(current),
    )

    renderer._desenhar_arma_corrente(contexto)

    assert calls == [contexto]


def test_bow_weapon_render_still_draws_after_helper_extraction():
    renderer = _DummyRenderer()
    arma = Arma(
        nome="Arco do Caçador",
        tipo="Arco",
        estilo="Arco Longo",
        dano=6,
        peso=2,
        raridade="Incomum",
        r=120,
        g=90,
        b=50,
    )

    renderer.desenhar_arma(arma, (410, 290), -10.0, 1.8, 60, 1.05)

    assert renderer.tela.get_bounding_rect().width > 0


def test_render_frame_context_captures_background_pulse_and_sorted_fighters(monkeypatch):
    renderer = _DummyFrameRenderer()
    morto = SimpleNamespace(morto=True)
    vivo = SimpleNamespace(morto=False)
    renderer.fighters = [vivo, morto]
    renderer.arena = SimpleNamespace(config=SimpleNamespace(cor_ambiente=(12, 8, 4)))
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1250)

    contexto = renderer._criar_contexto_render_frame()

    assert contexto.fundo == tuple(
        min(255, COR_FUNDO[idx] + delta)
        for idx, delta in enumerate((12, 8, 4))
    )
    assert contexto.pulse_time == 1.25
    assert contexto.lutadores_ordenados == [morto, vivo]


def test_projectile_frame_context_captures_type_angle_and_radius():
    renderer = _DummyFrameRenderer()
    proj = SimpleNamespace(
        x=5.2,
        y=4.8,
        raio=0.18,
        cor=(220, 120, 80),
        tipo="faca",
        angulo=45.0,
    )

    contexto = renderer._criar_contexto_projetil_frame(proj, 1.25)

    assert contexto.tipo_proj == "faca"
    assert contexto.pr > 0
    assert contexto.rad == pytest.approx(0.7853981634)
    assert contexto.cor == (220, 120, 80)


def test_projectile_frame_render_runs_internal_pipeline(monkeypatch):
    renderer = _DummyFrameRenderer()
    proj = SimpleNamespace(x=5.2, y=4.8, raio=0.18, cor=(220, 120, 80), tipo="faca", angulo=45.0)
    renderer.projeteis = [proj]
    calls = []
    contexto_proj = SimpleNamespace()

    monkeypatch.setattr(renderer, "_desenhar_trail_legado_projetil", lambda current: calls.append(("trail", current)))
    monkeypatch.setattr(renderer, "_criar_contexto_projetil_frame", lambda current, pulse: calls.append(("contexto", current, pulse)) or contexto_proj)
    monkeypatch.setattr(renderer, "_desenhar_glow_projetil_frame", lambda current: calls.append(("glow", current)))
    monkeypatch.setattr(renderer, "_desenhar_corpo_projetil_frame", lambda current: calls.append(("corpo", current)))

    renderer._desenhar_projeteis_frame(SimpleNamespace(pulse_time=1.25))

    assert calls == [
        ("trail", proj),
        ("contexto", proj, 1.25),
        ("glow", contexto_proj),
        ("corpo", contexto_proj),
    ]


def test_projectile_frame_draws_physical_projectile_and_legacy_trail():
    renderer = _DummyFrameRenderer()
    renderer.projeteis = [
        SimpleNamespace(
            x=5.2,
            y=4.8,
            raio=0.18,
            cor=(220, 120, 80),
            tipo="faca",
            angulo=45.0,
            nome="Adaga de Aco",
            trail=[(4.8, 4.5), (5.0, 4.6), (5.2, 4.8)],
        )
    ]

    renderer._desenhar_projeteis_frame(SimpleNamespace(pulse_time=1.25))

    assert renderer.tela.get_bounding_rect().width > 0


def test_hitbox_debug_context_captures_screen_center_and_reach(monkeypatch):
    renderer = _DummyFrameRenderer()
    fighter = _make_hitbox_debug_fighter(team_id=1)
    hitbox = SimpleNamespace(
        centro=(160, 120),
        alcance=48,
        pontos=[(150, 110), (170, 130)],
        tipo="Reta",
        ativo=True,
        angulo=30.0,
        largura_angular=40.0,
    )

    monkeypatch.setattr(sim_renderer_module.sistema_hitbox, "calcular_hitbox_arma", lambda lutador: hitbox)

    contexto = renderer._criar_contexto_hitbox_debug(fighter)

    assert contexto is not None
    assert contexto.hitbox is hitbox
    assert contexto.alcance_screen > 0
    assert contexto.cor_debug[3] == 128
    assert contexto.cy_screen < renderer.cam.converter(hitbox.centro[0], hitbox.centro[1])[1]


def test_hitbox_debug_runs_pipeline_for_live_contexts_and_panel(monkeypatch):
    renderer = _DummyFrameRenderer()
    vivo = _make_hitbox_debug_fighter(nome="Vivo")
    morto = _make_hitbox_debug_fighter(nome="Morto")
    morto.morto = True
    renderer.fighters = [vivo, morto]
    calls = []
    contexto = SimpleNamespace()

    monkeypatch.setattr(renderer, "_criar_contexto_hitbox_debug", lambda lutador: contexto if lutador is vivo else None)
    monkeypatch.setattr(renderer, "_desenhar_hitbox_lutador_debug", lambda current, fonte: calls.append(("lutador", current)))
    monkeypatch.setattr(renderer, "desenhar_painel_debug", lambda: calls.append(("painel", None)))

    renderer.desenhar_hitbox_debug()

    assert calls == [("lutador", contexto), ("painel", None)]


def test_hitbox_debug_draws_ranged_overlay(monkeypatch):
    renderer = _DummyFrameRenderer()
    fighter = _make_hitbox_debug_fighter()
    renderer.fighters = [fighter]
    hitbox = SimpleNamespace(
        centro=(160, 120),
        alcance=52,
        pontos=[(160, 120), (220, 160)],
        tipo="Arremesso",
        ativo=True,
        angulo=35.0,
        largura_angular=25.0,
    )

    monkeypatch.setattr(sim_renderer_module.sistema_hitbox, "calcular_hitbox_arma", lambda lutador: hitbox)
    monkeypatch.setattr(renderer, "desenhar_painel_debug", lambda: None)

    renderer.desenhar_hitbox_debug()

    assert renderer.tela.get_bounding_rect().width > 0


def test_desenhar_runs_frame_pipeline_in_order(monkeypatch):
    renderer = _DummyFrameRenderer()
    contexto = object()
    ordem = []
    etapas = [
        "_desenhar_fundo_frame",
        "_desenhar_camadas_magicas_frame",
        "_desenhar_particulas_frame",
        "_desenhar_invocacoes_traps_frame",
        "_desenhar_lutadores_frame",
        "_desenhar_projeteis_frame",
        "_desenhar_orbes_frame",
        "_desenhar_efeitos_frame",
        "_desenhar_interface_frame",
    ]

    monkeypatch.setattr(renderer, "_criar_contexto_render_frame", lambda: contexto)
    for etapa in etapas:
        monkeypatch.setattr(
            renderer,
            etapa,
            lambda ctx, etapa=etapa: ordem.append((etapa, ctx)),
        )

    renderer.desenhar()

    assert ordem == [(etapa, contexto) for etapa in etapas]


def test_magic_circular_motif_routes_motivo_before_ornamento(monkeypatch):
    renderer = _DummyRenderer()
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_motivo_protecao_circular_magia", lambda contexto: calls.append(("motivo", contexto.motivo)))
    monkeypatch.setattr(renderer, "_desenhar_ornamento_mira_circular_magia", lambda contexto: calls.append(("ornamento", contexto.ornamento)))
    monkeypatch.setattr(renderer, "_desenhar_fallback_circular_magia", lambda contexto: calls.append(("fallback", None)))

    renderer._desenhar_motivo_circular_magia(
        400,
        300,
        32,
        {"mid": [(120, 180, 255), (160, 220, 255)], "core": (220, 240, 255), "spark": (255, 255, 255)},
        {"motivo": "protecao", "ornamento": "mira"},
        1.2,
    )

    assert calls == [("motivo", "protecao")]


def test_beam_ornaments_route_known_motivo_to_segment_helper(monkeypatch):
    renderer = _DummyRenderer()
    calls = []

    monkeypatch.setattr(renderer, "_iterar_segmentos_ornamento_feixe", lambda pontos: [(0,)])
    monkeypatch.setattr(renderer, "_desenhar_ornamento_controle_feixe", lambda surf, segmento, paleta, pulse_time, largura: calls.append(("controle", segmento, largura)))

    renderer._desenhar_ornamentos_feixe(
        renderer.tela,
        [(0, 0), (10, 0)],
        {"mid": [(120, 180, 255), (160, 220, 255)], "core": (220, 240, 255), "spark": (255, 255, 255)},
        {"motivo": "controle", "ornamento": "mira"},
        0.9,
        12,
    )

    assert calls == [("controle", (0,), 12)]


def test_magic_area_variant_routes_named_signature_to_helper(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace(assinatura={"variante": "pilar_fogo"})
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_area_pilar_fogo", lambda current: calls.append(current))

    renderer._desenhar_variante_area_magica(contexto)

    assert calls == [contexto]


def test_magic_beam_variant_routes_named_signature_to_helper(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace(assinatura={"variante": "raio_sagrado"})
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_beam_raio_sagrado", lambda current, surf: calls.append((current, surf)))

    renderer._desenhar_variante_beam_magico(contexto, renderer.tela)

    assert calls == [(contexto, renderer.tela)]


def test_magic_projectile_explicit_variant_routes_named_signature_to_helper(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace(variante="lanca_luz")
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_projetil_lanca_luz", lambda current: calls.append(current) or True)

    assert renderer._desenhar_variante_explicita_projetil_magico(contexto) is True
    assert calls == [contexto]


def test_buff_overlay_runs_context_pipeline_for_each_slot(monkeypatch):
    renderer = _DummyRenderer()
    buff = SimpleNamespace()
    contexto = SimpleNamespace()
    calls = []

    monkeypatch.setattr(renderer, "_coletar_buffs_visuais_ativos", lambda lutador: [buff])
    monkeypatch.setattr(renderer, "_criar_contexto_buff_lutador", lambda *args: calls.append("contexto") or contexto)
    monkeypatch.setattr(renderer, "_desenhar_base_buff_lutador", lambda current: calls.append(("base", current)))
    monkeypatch.setattr(renderer, "_desenhar_escudo_buff_lutador", lambda current: calls.append(("escudo", current)))
    monkeypatch.setattr(renderer, "_desenhar_variante_buff_lutador", lambda current: calls.append(("variante", current)))

    renderer._desenhar_buffs_lutador(SimpleNamespace(), (420, 320), 26, 1.2)

    assert calls == ["contexto", ("base", contexto), ("escudo", contexto), ("variante", contexto)]


def test_summon_render_runs_context_pipeline_in_order(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace()
    calls = []

    monkeypatch.setattr(renderer, "_criar_contexto_summon_magico", lambda summon, pulse_time: calls.append(("contexto", summon, pulse_time)) or contexto)
    monkeypatch.setattr(renderer, "_desenhar_base_summon_magico", lambda current: calls.append(("base", current)))
    monkeypatch.setattr(renderer, "_desenhar_flash_summon_magico", lambda current: calls.append(("flash", current)))
    monkeypatch.setattr(renderer, "_desenhar_variante_summon_magico", lambda current: calls.append(("variante", current)))
    monkeypatch.setattr(renderer, "_desenhar_overlay_summon_magico", lambda current: calls.append(("overlay", current)))

    summon = SimpleNamespace(nome="Fenix")
    renderer._desenhar_summon_magico(summon, 1.1)

    assert calls == [("contexto", summon, 1.1), ("base", contexto), ("flash", contexto), ("variante", contexto), ("overlay", contexto)]


def test_trap_render_routes_barrier_branch_after_flash(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace(trap=SimpleNamespace(bloqueia_movimento=True))
    calls = []

    monkeypatch.setattr(renderer, "_criar_contexto_trap_magica", lambda trap, pulse_time: calls.append(("contexto", trap, pulse_time)) or contexto)
    monkeypatch.setattr(renderer, "_desenhar_flash_trap_magica", lambda current: calls.append(("flash", current)))
    monkeypatch.setattr(renderer, "_desenhar_trap_bloqueio_movimento", lambda current: calls.append(("barreira", current)))
    monkeypatch.setattr(renderer, "_desenhar_trap_ativada", lambda current: calls.append(("ativada", current)))
    monkeypatch.setattr(renderer, "_desenhar_trap_inativa", lambda current: calls.append(("inativa", current)))

    trap = SimpleNamespace(nome="Muralha")
    renderer._desenhar_trap_magica(trap, 0.8)

    assert calls == [("contexto", trap, 0.8), ("flash", contexto), ("barreira", contexto)]


def test_dual_weapon_default_runs_internal_pipeline(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace(raio_char=28, zw=lambda px: px, larg_base=5, anim_scale=1.1, tempo=60, atacando=False)
    calls = []

    monkeypatch.setattr(renderer, "_iterar_laminas_duplas_padrao", lambda *args: [(1, 2, 3, 4, 5, 6, 0.7)])
    monkeypatch.setattr(renderer, "_desenhar_empunhadura_dupla_padrao", lambda *args: calls.append("empunhadura"))
    monkeypatch.setattr(renderer, "_desenhar_guarda_dupla_padrao", lambda *args: calls.append("guarda"))
    monkeypatch.setattr(renderer, "_desenhar_lamina_dupla_padrao", lambda *args: calls.append("lamina"))
    monkeypatch.setattr(renderer, "_desenhar_glow_dupla_padrao", lambda *args: calls.append("glow"))
    monkeypatch.setattr(renderer, "_desenhar_ponta_dupla_padrao", lambda *args: calls.append("ponta"))

    renderer._desenhar_arma_dupla_padrao(contexto)

    assert calls == ["empunhadura", "guarda", "lamina", "glow", "ponta"]


def test_mangual_head_runs_internal_pipeline(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace()
    calls = []

    monkeypatch.setattr(renderer, "_desenhar_glow_cabeca_mangual", lambda *args: calls.append("glow"))
    monkeypatch.setattr(renderer, "_desenhar_corpo_cabeca_mangual", lambda *args: calls.append("corpo"))
    monkeypatch.setattr(renderer, "_desenhar_spikes_cabeca_mangual", lambda *args: calls.append("spikes"))
    monkeypatch.setattr(renderer, "_desenhar_runas_cabeca_mangual", lambda *args: calls.append("runas"))
    monkeypatch.setattr(renderer, "_desenhar_impacto_cabeca_mangual", lambda *args: calls.append("impacto"))
    monkeypatch.setattr(renderer, "_desenhar_aura_raridade_cabeca_mangual", lambda *args: calls.append("raridade"))

    renderer._desenhar_cabeca_mangual(contexto, 420, 280, 14, 0.6, 0.8)

    assert calls == ["glow", "corpo", "spikes", "runas", "impacto", "raridade"]


def test_meteor_chain_runs_internal_pipeline(monkeypatch):
    renderer = _DummyRenderer()
    contexto = SimpleNamespace(raio_char=28, anim_scale=1.1, tempo=90)
    calls = []

    monkeypatch.setattr(renderer, "_coletar_pontos_corrente_meteor", lambda *args: calls.append("coleta") or [(410, 280), (430, 290)])
    monkeypatch.setattr(renderer, "_desenhar_elos_corrente_meteor", lambda *args: calls.append("elos"))
    monkeypatch.setattr(renderer, "_desenhar_cabeca_corrente_meteor", lambda *args: calls.append("cabeca"))
    monkeypatch.setattr(renderer, "_desenhar_orbitas_corrente_meteor", lambda *args: calls.append("orbitas"))

    renderer._desenhar_arma_corrente_meteor(contexto)

    assert calls == ["coleta", "elos", "cabeca", "orbitas"]


def test_hud_multi_runs_team_and_member_pipeline(monkeypatch):
    renderer = _DummyFrameRenderer()
    fighter_a = SimpleNamespace(team_id=0)
    fighter_b = SimpleNamespace(team_id=1)
    layout = SimpleNamespace(times={0: [fighter_a], 1: [fighter_b]})
    calls = []

    monkeypatch.setattr(renderer, "_criar_layout_hud_multi", lambda: layout)
    monkeypatch.setattr(renderer, "_criar_contexto_time_hud_multi", lambda current_layout, team_index, team_id, members: f"time-{team_id}")
    monkeypatch.setattr(renderer, "_desenhar_header_time_hud_multi", lambda contexto_time: calls.append(("header", contexto_time)))
    monkeypatch.setattr(renderer, "_desenhar_slot_lutador_hud_multi", lambda contexto_time, fighter, member_index: calls.append(("slot", contexto_time, fighter, member_index)))

    renderer._desenhar_hud_multi()

    assert calls == [
        ("header", "time-0"),
        ("slot", "time-0", fighter_a, 0),
        ("header", "time-1"),
        ("slot", "time-1", fighter_b, 0),
    ]


def test_hud_multi_draws_team_panels_and_bars(monkeypatch):
    renderer = _DummyFrameRenderer()
    renderer.vida_visual = {}
    renderer.fighters = [
        SimpleNamespace(team_id=0, dados=SimpleNamespace(nome="Alpha"), morto=False, vida=80, vida_max=100, mana=30, mana_max=50),
        SimpleNamespace(team_id=1, dados=SimpleNamespace(nome="Beta"), morto=False, vida=60, vida_max=100, mana=20, mana_max=40),
    ]

    monkeypatch.setattr(renderer, "_desenhar_badges_estado", lambda *args, **kwargs: None)

    renderer._desenhar_hud_multi()

    assert renderer.tela.get_bounding_rect().width > 0
