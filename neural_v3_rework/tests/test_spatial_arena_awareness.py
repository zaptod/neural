from modelos import Arma, Personagem
from nucleo.arena import Arena, ArenaConfig, Obstaculo
from nucleo.entities import Lutador


def _make_fighter(nome, weapon_type="Espada Reta", family=None, team_id=0, x=0.0, y=0.0):
    arma = Arma(
        nome=f"{weapon_type} de Teste",
        tipo=weapon_type,
        familia=family,
        dano=8,
        peso=2,
        velocidade_ataque=1.0,
    )
    dados = Personagem(
        nome=nome,
        tamanho=1.5,
        forca=5.0,
        mana=5.0,
        classe="Guerreiro (Forca Bruta)",
    )
    dados.recalcular_com_arma(arma)
    return Lutador(dados, x, y, team_id=team_id)


def test_spatial_awareness_uses_circular_border_distance(monkeypatch):
    from ia import brain_spatial

    arena = Arena(
        ArenaConfig(
            nome="Circulo",
            largura=20.0,
            altura=20.0,
            formato="circular",
        )
    )
    fighter = _make_fighter("WallReader", x=18.8, y=10.0)
    enemy = _make_fighter("Enemy", team_id=1, x=11.0, y=10.0)

    monkeypatch.setattr(brain_spatial, "_get_arena", lambda: arena)

    fighter.brain._atualizar_consciencia_espacial(0.25, 7.8, enemy)

    assert fighter.brain.consciencia_espacial["parede_proxima"] == "leste"
    assert fighter.brain.consciencia_espacial["distancia_parede"] < 1.1
    assert fighter.brain.consciencia_espacial["caminho_livre"]["tras"] is False


def test_spatial_awareness_marks_enemy_near_obstacle_and_forces_corner(monkeypatch):
    from ia import brain_spatial

    arena = Arena(
        ArenaConfig(
            nome="Obstaculos",
            largura=30.0,
            altura=20.0,
            obstaculos=[Obstaculo("pilar", 21.6, 10.0, 1.8, 1.8)],
        )
    )
    fighter = _make_fighter("Hunter", x=16.5, y=10.0)
    enemy = _make_fighter("Pinned", team_id=1, x=20.6, y=10.0)

    monkeypatch.setattr(brain_spatial, "_get_arena", lambda: arena)

    fighter.brain._atualizar_consciencia_espacial(0.25, 4.1, enemy)

    assert fighter.brain.consciencia_espacial["oponente_perto_obstaculo"] is True
    assert fighter.brain.tatica_espacial["forcar_canto"] is True
    assert fighter.brain.consciencia_espacial["pressao_borda"] >= 0.0


def test_spatial_modifier_retomar_centro_breaks_retreat_near_wall(monkeypatch):
    from ia import brain_spatial

    arena = Arena(
        ArenaConfig(
            nome="Arena",
            largura=30.0,
            altura=20.0,
        )
    )
    fighter = _make_fighter("Cornered", x=1.4, y=10.0)
    enemy = _make_fighter("Enemy", team_id=1, x=9.0, y=10.0)

    monkeypatch.setattr(brain_spatial, "_get_arena", lambda: arena)
    monkeypatch.setattr("random.choice", lambda seq: seq[0])

    fighter.brain._atualizar_consciencia_espacial(0.25, 7.6, enemy)
    fighter.brain.acao_atual = "RECUAR"
    fighter.brain._aplicar_modificadores_espaciais(7.6, enemy)

    assert fighter.brain.tatica_espacial["retomar_centro"] is True
    assert fighter.brain.acao_atual in {"CIRCULAR", "FLANQUEAR", "APROXIMAR"}


def test_spatial_awareness_flags_danger_zone_and_forces_escape(monkeypatch):
    from ia import brain_spatial

    arena = Arena(
        ArenaConfig(
            nome="Lava",
            largura=30.0,
            altura=20.0,
            obstaculos=[Obstaculo("lava", 6.0, 10.0, 3.0, 3.0, (255, 100, 0), solido=False)],
        )
    )
    fighter = _make_fighter("Burning", x=6.0, y=10.0)
    enemy = _make_fighter("Enemy", team_id=1, x=10.0, y=10.0)

    monkeypatch.setattr(brain_spatial, "_get_arena", lambda: arena)

    fighter.brain._atualizar_consciencia_espacial(0.25, 4.0, enemy)
    fighter.brain.acao_atual = "BLOQUEAR"
    fighter.brain._aplicar_modificadores_espaciais(4.0, enemy)

    assert fighter.brain.consciencia_espacial["zona_perigo_atual"] == "lava"
    assert fighter.brain.tatica_espacial["escapar_zona_perigo"] is True
    assert fighter.brain.acao_atual in {"CIRCULAR", "APROXIMAR"}
