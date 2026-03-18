from types import SimpleNamespace

from ia.tactical_packages import inferir_papel_tatico
from ia.team_ai import TeamCoordinator, TeamTactic
from modelos import Personagem
from modelos.weapons import Arma
from nucleo.entities import Lutador


def _weapon_for_family(nome, familia):
    tipo_map = {
        "orbital": "Orbital",
        "foco": "Mágica",
        "disparo": "Arco",
        "arremesso": "Arremesso",
        "corrente": "Corrente",
        "hibrida": "Transformável",
        "haste": "Reta",
        "lamina": "Reta",
        "dupla": "Dupla",
    }
    return Arma(nome=nome, tipo=tipo_map.get(familia, "Reta"), familia=familia, dano=8, peso=4)


def _fighter(nome, classe, familia, tracos, team_id=0):
    arma = _weapon_for_family(f"{nome} Arma", familia)
    dados = Personagem(
        nome=nome,
        tamanho=1.75,
        forca=6.0,
        mana=6.0,
        nome_arma=arma.nome,
        peso_arma_cache=arma.peso,
        classe=classe,
        personalidade="Tatico",
    )
    dados.arma_obj = arma
    fighter = Lutador(dados, 0.0, 0.0, team_id=team_id)
    fighter.brain.tracos = list(tracos)
    fighter.brain.arquetipo = ""
    fighter.encounter_mode = "horda"
    fighter.brain.encounter_mode = "horda"
    return fighter


def _monster(nome, monster_tipo="minion", pos=(4.0, 0.0)):
    return SimpleNamespace(
        nome=nome,
        team_id=1,
        morto=False,
        vida=40.0 if monster_tipo == "minion" else 85.0,
        vida_max=40.0 if monster_tipo == "minion" else 85.0,
        pos=list(pos),
        dados=SimpleNamespace(classe="Monstro", nome=nome),
        is_monster=True,
        monster_tipo=monster_tipo,
        atacando=False,
        alvo=None,
        mana=0.0,
        mana_max=0.0,
    )


def test_inferir_papel_tatico_detecta_defensor_pelo_kit():
    fighter = _fighter(
        "Aegis",
        "Paladino (Sagrado)",
        "orbital",
        ["PROTETOR", "MURALHA", "DETERMINADO"],
    )

    pacote = inferir_papel_tatico(fighter)

    assert pacote["papel_id"] == "defensor"
    assert pacote["team_role"] == "VANGUARD"
    assert pacote["confidence"] >= 0.3


def test_team_coordinator_horda_prioriza_proteger_lineup():
    defensor = _fighter(
        "Aegis",
        "Paladino (Sagrado)",
        "orbital",
        ["PROTETOR", "MURALHA", "DETERMINADO"],
    )
    curandeiro = _fighter(
        "Lyra",
        "Druida (Natureza)",
        "foco",
        ["PACIENTE", "SUPPORT", "CONSERVADOR", "FOCADO", "CALCULISTA"],
    )
    minions = [_monster(f"Minion {i}", pos=(4.0 + i, 0.0)) for i in range(4)]

    coord = TeamCoordinator(0, [defensor, curandeiro])
    coord.update(0.16, [defensor, curandeiro, *minions])

    assert coord.tactic == TeamTactic.PROTECT_CARRY
    assert defensor.brain.team_orders["modo_horda"] is True
    assert defensor.brain.team_orders["package_role"] == "defensor"
    assert curandeiro.brain.team_orders["package_role"] == "curandeiro"


def test_team_coordinator_horda_foca_elite_antes_do_minion():
    defensor = _fighter(
        "Aegis",
        "Paladino (Sagrado)",
        "orbital",
        ["PROTETOR", "MURALHA", "DETERMINADO"],
    )
    limpador = _fighter(
        "Pyra",
        "Piromante (Fogo)",
        "foco",
        ["AREA_DENIAL", "INCANSAVEL", "PRESSAO_CONSTANTE", "DESTRUIDOR"],
    )
    minion = _monster("Minion", "minion", pos=(3.5, 0.0))
    elite = _monster("Bruto", "elite", pos=(4.5, 0.0))

    coord = TeamCoordinator(0, [defensor, limpador])
    coord.update(0.16, [defensor, limpador, minion, elite])

    assert coord.primary_target is elite
    assert coord.target_priority.name == "HIGHEST_THREAT"
