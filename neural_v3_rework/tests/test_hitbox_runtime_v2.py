from modelos import Personagem
from modelos.weapons import Arma
from nucleo.entities import Lutador
from nucleo.hitbox import sistema_hitbox


def _make_fighter(nome, arma):
    dados = Personagem(
        nome=nome,
        tamanho=1.5,
        forca=5.0,
        mana=5.0,
        classe="Guerreiro (Força Bruta)",
    )
    dados.recalcular_com_arma(arma)
    return Lutador(dados, 0.0, 0.0, team_id=0)


def test_corrente_spin_hitbox_fica_ativa_em_360_graus():
    arma = Arma(
        nome="Meteor Core",
        tipo="Corrente",
        familia="corrente",
        estilo="Meteor Hammer",
        dano=9,
        peso=4,
        combate={"alcance": 3.5},
    )
    fighter = _make_fighter("Spinner", arma)
    fighter.chain_spinning = True
    fighter.atacando = False

    hitbox = sistema_hitbox.calcular_hitbox_arma(fighter)

    assert hitbox is not None
    assert hitbox.ativo is True
    assert hitbox.largura_angular == 360.0


def test_hitbox_ranged_reflete_spread_e_carga():
    arco = Arma(
        nome="Besta Lunar",
        tipo="Arco",
        familia="disparo",
        dano=9,
        peso=3,
        combate={"alcance": 11.0, "spread": 2.0},
    )
    archer = _make_fighter("Archer", arco)
    archer.bow_charge = 1.2
    archer.atacando = True

    hitbox_arco = sistema_hitbox.calcular_hitbox_arma(archer)

    assert hitbox_arco is not None
    assert hitbox_arco.largura_angular < 12.0

    faca = Arma(
        nome="Punhal Tempestade",
        tipo="Arremesso",
        familia="arremesso",
        dano=8,
        peso=2,
        quantidade=3,
        combate={"alcance": 8.0, "spread": 18.0, "projeteis_por_ataque": 3},
    )
    thrower = _make_fighter("Thrower", faca)
    thrower.atacando = True

    hitbox_throw = sistema_hitbox.calcular_hitbox_arma(thrower)

    assert hitbox_throw is not None
    assert hitbox_throw.largura_angular >= 18.0
    assert len(hitbox_throw.pontos) == 3


def test_hibrida_altera_envelope_de_hitbox_por_forma():
    arma = Arma(
        nome="Ferrão Modular",
        tipo="Transformável",
        familia="hibrida",
        estilo="Espada↔Lança",
        dano=10,
        peso=4,
        combate={"alcance": 4.2, "alcance_minimo": 0.6, "arco": 100.0},
    )
    fighter = _make_fighter("Morph", arma)

    fighter.transform_forma = 0
    hitbox_curta = sistema_hitbox.calcular_hitbox_arma(fighter)

    fighter.transform_forma = 1
    hitbox_longa = sistema_hitbox.calcular_hitbox_arma(fighter)

    assert hitbox_curta is not None and hitbox_longa is not None
    assert hitbox_longa.alcance > hitbox_curta.alcance
    assert hitbox_longa.alcance_minimo > hitbox_curta.alcance_minimo


def test_foco_magico_nao_usa_colisao_convencional():
    foco = Arma(nome="Cetro Vazio", tipo="Mágica", familia="foco", dano=8, peso=2)
    caster = _make_fighter("Caster", foco)
    alvo = _make_fighter("Target", Arma(nome="Espada", tipo="Reta", dano=8, peso=3))

    acertou, motivo = sistema_hitbox.verificar_colisao(caster, alvo)

    assert acertou is False
    assert "projetil" in motivo
