from modelos import Arma, Personagem
from nucleo.entities import Lutador
from ia.brain import AIBrain
from utilitarios.estado_espectador import resolver_badges_estado


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


def test_rival_memory_loads_relational_biases_from_history():
    fighter = _make_fighter("Astra")
    enemy = _make_fighter("Nyx", team_id=1)
    chave = fighter.brain._id_oponente(enemy)
    historico_original = dict(AIBrain._historico_combates)

    try:
        AIBrain._historico_combates.clear()
        AIBrain._historico_combates[chave] = {
            "lutas": 7,
            "vitorias": 2,
            "hits_sofridos_total": 42,
            "max_combo_total": 27,
            "fugas_total": 3,
            "rivalidade_total": 3.2,
        }

        fighter.brain.carregar_memoria_rival(enemy)
        bucket = fighter.brain._obter_vies_oponente(enemy)

        assert bucket["relacao_respeito"] > 0.3
        assert bucket["relacao_obsessao"] > 0.3
        assert bucket["relacao_dominante"] in {"respeito", "obsessao", "vinganca"}
    finally:
        AIBrain._historico_combates.clear()
        AIBrain._historico_combates.update(historico_original)


def test_hit_received_from_enemy_builds_revenge_relation():
    fighter = _make_fighter("Astra")
    enemy = _make_fighter("Nyx", team_id=1)

    fighter.brain.on_hit_recebido_de(enemy)
    bucket = fighter.brain._obter_vies_oponente(enemy)

    assert bucket["relacao_vinganca"] > 0.0
    assert bucket["relacao_respeito"] > 0.0


def test_rival_relation_increases_target_priority():
    fighter = _make_fighter("Astra", team_id=0)
    rival = _make_fighter("Nyx", team_id=1, x=2.0)
    other = _make_fighter("Vesper", team_id=1, x=2.0)

    fighter.brain._registrar_relacao_oponente(rival, "obsessao", 0.8, evento="teste")
    fighter.brain._registrar_relacao_oponente(rival, "vinganca", 0.5, evento="teste")

    rival_info = {"lutador": rival, "vida_pct": 0.8, "distancia": 2.0, "ameaca": 0.4}
    other_info = {"lutador": other, "vida_pct": 0.8, "distancia": 2.0, "ameaca": 0.4}

    assert fighter.brain._score_alvo(rival_info) > fighter.brain._score_alvo(other_info)


def test_status_badges_surface_relational_dominant_state():
    fighter = _make_fighter("Astra")
    enemy = _make_fighter("Nyx", team_id=1)

    fighter.brain._registrar_relacao_oponente(enemy, "vinganca", 0.9, evento="teste")
    fighter.brain.memoria_oponente["id_atual"] = fighter.brain._id_oponente(enemy)

    textos = [badge["texto"] for badge in resolver_badges_estado(fighter, max_badges=3)]

    assert "REVANCHE" in textos


def test_respect_relation_softens_punish_plan():
    fighter = _make_fighter("Astra", family="lamina")
    enemy = _make_fighter("Nyx", team_id=1, family="lamina")

    fighter.brain._alvo_atual = enemy
    fighter.brain._registrar_relacao_oponente(enemy, "respeito", 0.82, evento="teste")

    opener, followup, timer, boost_excitacao, _ = fighter.brain._modular_plano_punish_por_rivalidade(
        "MATAR", "ESMAGAR", 0.30, 0.12, 0.08, "lamina"
    )

    assert opener == "CONTRA_ATAQUE"
    assert followup == "COMBATE"
    assert timer >= 0.48
    assert boost_excitacao >= 0.06


def test_revenge_relation_hardens_punish_plan():
    fighter = _make_fighter("Astra", family="lamina")
    enemy = _make_fighter("Nyx", team_id=1, family="lamina")

    fighter.brain._alvo_atual = enemy
    fighter.brain._registrar_relacao_oponente(enemy, "vinganca", 0.86, evento="teste")

    opener, followup, timer, boost_excitacao, boost_adrenalina = fighter.brain._modular_plano_punish_por_rivalidade(
        "COMBATE", "COMBATE", 0.48, 0.04, 0.02, "lamina"
    )

    assert opener == "MATAR"
    assert followup == "ESMAGAR"
    assert timer <= 0.34
    assert boost_excitacao >= 0.15
    assert boost_adrenalina >= 0.10


def test_rival_relation_updates_humor_toward_focused_or_determined():
    fighter = _make_fighter("Astra")
    enemy = _make_fighter("Nyx", team_id=1)

    fighter.brain._alvo_atual = enemy
    fighter.brain.cd_mudanca_humor = 0.0
    fighter.brain.raiva = 0.15
    fighter.brain.medo = 0.10
    fighter.brain.adrenalina = 0.22
    fighter.brain.excitacao = 0.18
    fighter.brain.confianca = 0.58
    fighter.brain.frustracao = 0.05
    fighter.brain.tedio = 0.0
    fighter.brain.humor = "CALMO"
    fighter.brain._registrar_relacao_oponente(enemy, "respeito", 0.80, evento="teste")

    fighter.brain._atualizar_humor(0.1)

    assert fighter.brain.humor == "FOCADO"

    fighter.brain.cd_mudanca_humor = 0.0
    fighter.brain.humor = "CALMO"
    fighter.brain.confianca = 0.52
    bucket = fighter.brain._obter_vies_oponente(enemy)
    bucket["relacao_respeito"] = 0.0
    bucket["relacao_dominante"] = None
    fighter.brain._registrar_relacao_oponente(enemy, "vinganca", 0.90, evento="teste")

    fighter.brain._atualizar_humor(0.1)

    assert fighter.brain.humor == "DETERMINADO"
