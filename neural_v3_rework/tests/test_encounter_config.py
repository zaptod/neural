from utilitarios.encounter_config import (
    build_horde_match_config,
    build_team_match_config,
    get_encounter_side_labels,
    normalize_match_config,
)


def test_normalize_match_config_infers_team_mode():
    config = normalize_match_config(
        {
            "cenario": "Arena",
            "teams": [
                {"team_id": 0, "members": ["A"]},
                {"team_id": 1, "members": ["B", "C"]},
            ],
        }
    )

    assert config["modo_partida"] == "equipes"
    assert config["p1_nome"] == "A"
    assert config["p2_nome"] == "B"


def test_build_horde_match_config_expands_preset_and_labels():
    config = build_horde_match_config(
        [{"team_id": 0, "label": "Expedicao", "members": ["Astra", "Nyx"]}],
        {"preset_id": "sobrevivencia_basica"},
        cenario="Campo de Batalha",
    )

    assert config["modo_partida"] == "horda"
    assert config["horda_config"]["preset_id"] == "sobrevivencia_basica"
    assert len(config["horda_config"]["waves"]) >= 1
    assert get_encounter_side_labels(config) == ("Expedicao", config["horda_config"]["label"])


def test_build_team_match_config_keeps_labels():
    config = build_team_match_config(
        [
            {"team_id": 0, "label": "Guardioes", "members": ["Astra", "Borin"]},
            {"team_id": 1, "label": "Ruptura", "members": ["Nyx", "Kara"]},
        ]
    )

    assert config["modo_partida"] == "equipes"
    assert get_encounter_side_labels(config) == ("Guardioes", "Ruptura")
