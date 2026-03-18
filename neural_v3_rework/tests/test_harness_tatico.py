from pathlib import Path

from ferramentas.harness_tatico import (
    FILE_TEMPLATES,
    agregar_relatorio,
    listar_templates,
    montar_template_selecionado,
    normalizar_texto,
)


def test_templates_taticos_tem_tres_modos():
    assert Path(FILE_TEMPLATES).exists()
    templates = listar_templates()
    modos = {item["modo"] for item in templates}
    assert {"1v1", "grupo_vs_grupo", "grupo_vs_horda"} <= modos


def test_normalizar_texto_remove_ruido():
    assert normalizar_texto("Força Bruta") == "FORCA BRUTA"
    assert normalizar_texto("  ÁREA  ") == "AREA"


def test_montar_template_selecionado_resolve_slots_reais():
    selecao = montar_template_selecionado("duelo_papeis_basicos")
    assert selecao["template"]["modo"] == "1v1"
    assert len(selecao["team_a"]) == 1
    assert len(selecao["team_b"]) == 1
    assert selecao["team_a"][0]["personagem"].nome != selecao["team_b"][0]["personagem"].nome
    assert selecao["team_a"][0]["score"] >= 0.0


def test_agregar_relatorio_consolida_metricas():
    template = {
        "template_meta": {"id": "fake", "modo": "1v1"},
        "team_a": [{"papel": "duelista", "personagem": type("P", (), {"nome": "A"})()}],
        "team_b": [{"papel": "bruiser", "personagem": type("P", (), {"nome": "B"})()}],
    }
    runs = [
        {
            "vencedor": "A",
            "frames": 120,
            "tempo_simulado": 2.0,
            "tempo_real": 0.5,
            "team_stats": {
                "team_a": {"damage_dealt": 30.0},
                "team_b": {"damage_dealt": 25.0},
            },
            "team_status": {
                "team_a": {"names": ["A"]},
                "team_b": {"names": ["B"]},
            },
            "fighters": {
                "A": {"damage_dealt": 30.0, "kills": 1},
                "B": {"damage_dealt": 25.0, "kills": 0},
            },
        },
        {
            "vencedor": "Time 2 (B)",
            "frames": 180,
            "tempo_simulado": 3.0,
            "tempo_real": 0.7,
            "team_stats": {
                "team_a": {"damage_dealt": 18.0},
                "team_b": {"damage_dealt": 26.0},
            },
            "team_status": {
                "team_a": {"names": ["A"]},
                "team_b": {"names": ["B"]},
            },
            "fighters": {
                "A": {"damage_dealt": 18.0, "kills": 0},
                "B": {"damage_dealt": 26.0, "kills": 1},
            },
        },
    ]
    resumo = agregar_relatorio(template, runs)
    assert resumo["runs"] == 2
    assert resumo["team_wins"]["team_a"] == 1
    assert resumo["team_wins"]["team_b"] == 1
    assert resumo["avg_frames"] == 150.0
    assert resumo["papeis"]["duelista"]["presencas"] == 2
