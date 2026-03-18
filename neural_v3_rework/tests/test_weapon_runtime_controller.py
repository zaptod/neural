from modelos import Personagem
from modelos.weapons import Arma
from nucleo.armas import get_weapon_runtime_controller
from nucleo.entities import Lutador


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


def test_runtime_controller_maps_new_families_to_runtime_handlers():
    foco = Arma(nome="Cetro", tipo="Mágica", dano=8, peso=2)
    disparo = Arma(nome="Arco Longo", tipo="Arco", dano=7, peso=3)
    arremesso = Arma(nome="Punhal Veloz", tipo="Arremesso", dano=6, peso=2)
    hibrida = Arma(nome="Ferrão Modular", tipo="Transformável", dano=9, peso=4)

    assert get_weapon_runtime_controller(foco).familia == "foco"
    assert get_weapon_runtime_controller(foco).handler == "foco"
    assert get_weapon_runtime_controller(foco).animation_key == "Mágica"

    assert get_weapon_runtime_controller(disparo).familia == "disparo"
    assert get_weapon_runtime_controller(disparo).handler == "disparo"
    assert get_weapon_runtime_controller(disparo).allows_reposition_attack is True

    assert get_weapon_runtime_controller(arremesso).handler == "arremesso"
    assert get_weapon_runtime_controller(hibrida).handler == "transformavel"


def test_runtime_controller_uses_weapon_profile_for_range_and_cooldown():
    arma = Arma(
        nome="Lança do Sol",
        tipo="Reta",
        dano=10,
        peso=5,
        familia="haste",
        combate={"alcance": 2.8, "startup": 0.14, "ativo": 0.09, "recovery": 0.21},
    )
    fighter = _make_fighter("Astra", arma)
    controller = get_weapon_runtime_controller(arma)

    attack_range = controller.attack_range(fighter, arma)
    cooldown = controller.base_cooldown(fighter, arma)

    assert attack_range > 2.8
    assert cooldown > 0.40


def test_focus_handler_uses_controller_family_for_orb_generation():
    arma = Arma(nome="Foco Vazio", tipo="Mágica", dano=8, peso=2, habilidades=[])
    fighter = _make_fighter("Caster", arma)
    enemy = _make_fighter("Target", Arma(nome="Espada", tipo="Reta", dano=8, peso=3))
    fighter.brain.acao_atual = "COMBATE"
    fighter.cooldown_ataque = 0.0
    fighter.atacando = False
    fighter.pos = [0.0, 0.0]
    enemy.pos = [4.0, 0.0]
    enemy.z = 0.0
    fighter.z = 0.0

    fighter.executar_ataques(0.016, 4.0, enemy)

    assert fighter.atacando is True
    assert fighter.buffer_orbes


def test_arremesso_handler_entra_em_rajada_e_dispara_projeteis():
    arma = Arma(nome="Punhal Veloz", tipo="Arremesso", dano=8, peso=2, habilidades=[])
    fighter = _make_fighter("Thrower", arma)
    enemy = _make_fighter("Target", Arma(nome="Espada", tipo="Reta", dano=8, peso=3))
    fighter.brain.acao_atual = "COMBATE"
    fighter.cooldown_ataque = 0.0
    fighter.atacando = False
    fighter.pos = [0.0, 0.0]
    enemy.pos = [5.0, 0.0]
    enemy.z = 0.0
    fighter.z = 0.0

    fighter.executar_ataques(0.016, 5.0, enemy)

    assert fighter.atacando is True
    assert fighter.buffer_projeteis
    assert fighter.throw_consecutive >= 1.0


def test_disparo_handler_carrega_antes_de_soltar_flecha():
    arma = Arma(nome="Besta Lunar", tipo="Arco", dano=9, peso=3, habilidades=[])
    fighter = _make_fighter("Archer", arma)
    enemy = _make_fighter("Target", Arma(nome="Espada", tipo="Reta", dano=8, peso=3))
    fighter.brain.acao_atual = "COMBATE"
    fighter.cooldown_ataque = 0.0
    fighter.atacando = False
    fighter.pos = [0.0, 0.0]
    enemy.pos = [8.0, 0.0]
    enemy.z = 0.0
    fighter.z = 0.0

    fighter.executar_ataques(0.016, 8.0, enemy)

    assert fighter.bow_charging is True
    assert fighter.atacando is False

    fighter.executar_ataques(0.60, 8.0, enemy)

    assert fighter.atacando is True
    assert fighter.buffer_projeteis


def test_corrente_kusarigama_entra_em_modo_longo_e_marca_pull():
    arma = Arma(
        nome="Kusarigama Eclipse",
        tipo="Corrente",
        familia="corrente",
        estilo="Kusarigama",
        dano=9,
        peso=4,
        habilidades=[],
        combate={"alcance": 3.8},
    )
    fighter = _make_fighter("Chain", arma)
    enemy = _make_fighter("Target", Arma(nome="Espada", tipo="Reta", dano=8, peso=3))
    fighter.brain.acao_atual = "COMBATE"
    fighter.cooldown_ataque = 0.0
    fighter.atacando = False
    fighter.pos = [0.0, 0.0]
    enemy.pos = [3.2, 0.0]
    enemy.z = 0.0
    fighter.z = 0.0

    fighter.executar_ataques(0.016, 3.2, enemy)

    assert fighter.atacando is True
    assert fighter.chain_mode == 1
    assert fighter.chain_pull_target is enemy
    assert fighter.chain_pull_timer > 0.0


def test_hibrida_troca_para_forma_longa_quando_alvo_afasta():
    arma = Arma(
        nome="Ferrão Modular",
        tipo="Transformável",
        familia="hibrida",
        estilo="Espada↔Lança",
        dano=10,
        peso=4,
        habilidades=[],
        combate={"alcance": 4.6, "alcance_minimo": 0.6},
    )
    fighter = _make_fighter("Morph", arma)
    enemy = _make_fighter("Target", Arma(nome="Espada", tipo="Reta", dano=8, peso=3))
    fighter.brain.acao_atual = "COMBATE"
    fighter.cooldown_ataque = 0.0
    fighter.transform_cd = 0.0
    fighter.transform_forma = 0
    fighter.atacando = False
    fighter.pos = [0.0, 0.0]
    enemy.pos = [4.0, 0.0]
    enemy.z = 0.0
    fighter.z = 0.0

    fighter.executar_ataques(0.016, 4.0, enemy)

    assert fighter.transform_forma == 1
    assert fighter.transform_bonus_timer > 0.0
    assert fighter.atacando is True
