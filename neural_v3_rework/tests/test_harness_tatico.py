from pathlib import Path
import json

from ferramentas.harness_tatico import (
    FILE_PAPEIS,
    FILE_TEMPLATES,
    agregar_relatorio,
    comparar_templates,
    calcular_score_saude_template,
    gerar_plano_ajuste_template,
    gerar_recomendacoes_balanceamento,
    listar_templates,
    montar_template_selecionado,
    normalizar_texto,
)


def test_templates_taticos_tem_tres_modos():
    assert Path(FILE_TEMPLATES).exists()
    templates = listar_templates()
    modos = {item["modo"] for item in templates}
    assert {"1v1", "grupo_vs_grupo", "grupo_vs_horda"} <= modos


def test_catalogo_tatico_inclui_papeis_e_templates_orbitais():
    papeis = json.loads(Path(FILE_PAPEIS).read_text(encoding="utf-8"))
    papel_ids = {item["id"] for item in papeis.get("papeis", [])}
    assert {"bastiao_orbital", "artilheiro_orbital", "maestro_astral"} <= papel_ids

    templates = json.loads(Path(FILE_TEMPLATES).read_text(encoding="utf-8"))
    template_ids = {item["id"] for item in templates.get("templates", [])}
    assert {"corte_astral_2v2", "triade_astral_3v3", "falange_prismatica_horda"} <= template_ids


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
    assert "pacote_arquetipo" in selecao["team_a"][0]


def test_montar_template_selecionado_honra_personagem_e_pacote_fixos():
    selecao = montar_template_selecionado("corte_astral_2v2")

    assert selecao["team_a"][0]["personagem"].nome == "Lyss Aurel"
    assert selecao["team_a"][0]["pacote_arquetipo"] == "bastiao_prismatico"
    assert selecao["team_a"][1]["personagem"].nome == "Iona Hex"
    assert selecao["team_b"][0]["personagem"].nome == "Cassian Orion da Brasa"


def test_agregar_relatorio_consolida_metricas():
    template = {
        "template_meta": {"id": "fake", "modo": "1v1"},
        "team_a": [{"papel": "duelista", "pacote_arquetipo": "duelista_elemental", "pacote_nome": "Duelista Elemental", "personagem": type("P", (), {"nome": "A"})()}],
        "team_b": [{"papel": "bruiser", "pacote_arquetipo": "vanguarda_brutal", "pacote_nome": "Vanguarda Brutal", "personagem": type("P", (), {"nome": "B"})()}],
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
    assert resumo["pacotes"]["duelista_elemental"]["presencas"] == 2
    assert "alertas" in resumo
    assert "team_metric_avg" in resumo


def test_agregar_relatorio_sinaliza_duelo_curto_e_dominancia():
    template = {
        "template_meta": {"id": "curto", "modo": "1v1"},
        "team_a": [{"papel": "duelista", "personagem": type("P", (), {"nome": "A"})()}],
        "team_b": [{"papel": "bruiser", "personagem": type("P", (), {"nome": "B"})()}],
    }
    runs = [
        {
            "vencedor": "A",
            "frames": 360,
            "tempo_simulado": 6.0,
            "tempo_real": 0.4,
            "team_stats": {
                "team_a": {"damage_dealt": 40.0, "damage_taken": 5.0, "kills": 1, "deaths": 0, "skills_cast": 2, "mana_spent": 10.0},
                "team_b": {"damage_dealt": 5.0, "damage_taken": 40.0, "kills": 0, "deaths": 1, "skills_cast": 1, "mana_spent": 4.0},
            },
            "team_status": {
                "team_a": {"names": ["A"], "vivos": 1, "mortos": 0},
                "team_b": {"names": ["B"], "vivos": 0, "mortos": 1},
            },
            "fighters": {"A": {"damage_dealt": 40.0, "kills": 1}, "B": {"damage_dealt": 5.0, "kills": 0}},
        },
        {
            "vencedor": "A",
            "frames": 420,
            "tempo_simulado": 7.0,
            "tempo_real": 0.5,
            "team_stats": {
                "team_a": {"damage_dealt": 45.0, "damage_taken": 8.0, "kills": 1, "deaths": 0, "skills_cast": 2, "mana_spent": 11.0},
                "team_b": {"damage_dealt": 8.0, "damage_taken": 45.0, "kills": 0, "deaths": 1, "skills_cast": 1, "mana_spent": 5.0},
            },
            "team_status": {
                "team_a": {"names": ["A"], "vivos": 1, "mortos": 0},
                "team_b": {"names": ["B"], "vivos": 0, "mortos": 1},
            },
            "fighters": {"A": {"damage_dealt": 45.0, "kills": 1}, "B": {"damage_dealt": 8.0, "kills": 0}},
        },
    ]
    resumo = agregar_relatorio(template, runs)
    codigos = {alerta["codigo"] for alerta in resumo["alertas"]}
    assert "TEMPO_MUITO_CURTO" in codigos
    assert "DOMINANCIA_EXCESSIVA" in codigos


def test_agregar_relatorio_sinaliza_horda_sem_defensor_e_baixa_conclusao():
    template = {
        "template_meta": {"id": "horda", "modo": "grupo_vs_horda"},
        "team_a": [
            {"papel": "curandeiro", "personagem": type("P", (), {"nome": "Suporte"})()},
            {"papel": "atirador", "personagem": type("P", (), {"nome": "Arqueiro"})()},
        ],
        "team_b": [],
    }
    runs = [
        {
            "vencedor": "Horda",
            "frames": 1200,
            "tempo_simulado": 20.0,
            "tempo_real": 1.2,
            "team_stats": {
                "team_a": {"damage_dealt": 20.0, "damage_taken": 50.0, "kills": 3, "deaths": 2, "skills_cast": 4, "mana_spent": 18.0},
                "team_b": {"damage_dealt": 30.0, "damage_taken": 12.0, "kills": 2, "deaths": 5, "skills_cast": 0, "mana_spent": 0.0},
            },
            "team_status": {
                "team_a": {"names": ["Suporte", "Arqueiro"], "vivos": 0, "mortos": 2},
                "team_b": {"names": [], "vivos": 0, "mortos": 0},
            },
            "fighters": {"Suporte": {"damage_dealt": 8.0, "kills": 1}, "Arqueiro": {"damage_dealt": 12.0, "kills": 2}},
            "horda": {"wave_atual": 1, "total_killed": 3, "total_spawned": 8, "completed": False, "failed": True},
        }
    ]
    resumo = agregar_relatorio(template, runs)
    codigos = {alerta["codigo"] for alerta in resumo["alertas"]}
    assert "SEM_DEFENSOR_NA_HORDA" in codigos
    assert "BAIXA_CONCLUSAO_DE_ONDAS" in codigos
    assert "SUSTAIN_BAIXO_HORDA" in codigos


def test_comparar_templates_ranqueia_e_resume_alertas():
    report_a = {
        "template_id": "alpha",
        "modo": "1v1",
        "team_win_rate": {"team_a": 0.5, "team_b": 0.5},
        "avg_tempo_simulado": 30.0,
        "resumo_alertas": {},
        "alertas": [],
        "papeis": {
            "duelista": {"damage_dealt": 40.0, "kills": 2},
            "bruiser": {"damage_dealt": 35.0, "kills": 1},
        },
        "pacotes": {
            "duelista_elemental": {"damage_dealt": 40.0, "kills": 2},
            "vanguarda_brutal": {"damage_dealt": 35.0, "kills": 1},
        },
        "team_a": [{"papel": "duelista", "familia_arma": "lamina", "pacote_arquetipo": "duelista_elemental"}],
        "team_b": [{"papel": "bruiser", "familia_arma": "haste", "pacote_arquetipo": "vanguarda_brutal"}],
        "team_survival_avg": {"team_a": 0.5, "team_b": 0.5},
    }
    report_b = {
        "template_id": "beta",
        "modo": "grupo_vs_horda",
        "team_win_rate": {"team_a": 1.0, "team_b": 0.0},
        "avg_tempo_simulado": 20.0,
        "resumo_alertas": {"aviso": 2},
        "alertas": [
            {"codigo": "SEM_DEFENSOR_NA_HORDA", "nivel": "aviso"},
            {"codigo": "SUSTAIN_BAIXO_HORDA", "nivel": "aviso"},
        ],
        "papeis": {
            "curandeiro": {"damage_dealt": 10.0, "kills": 0},
            "horda": {"damage_dealt": 5.0, "kills": 0},
        },
        "pacotes": {
            "curador_de_cerco": {"damage_dealt": 10.0, "kills": 0},
        },
        "team_a": [{"papel": "curandeiro", "familia_arma": "foco", "pacote_arquetipo": "curador_de_cerco"}],
        "team_b": [{"papel": "horda", "familia_arma": "lamina", "pacote_arquetipo": ""}],
        "team_survival_avg": {"team_a": 0.0, "team_b": 0.0},
        "horda": {"completion_rate": 0.0, "failure_rate": 1.0, "avg_wave_alcancada": 1.0},
    }
    comparativo = comparar_templates([report_a, report_b])
    assert comparativo["melhor_template"]["template_id"] == "alpha"
    assert comparativo["pior_template"]["template_id"] == "beta"
    assert comparativo["alertas_mais_comuns"]["SEM_DEFENSOR_NA_HORDA"] == 1
    assert comparativo["ranking_templates"][0]["score_saude"] >= comparativo["ranking_templates"][1]["score_saude"]
    assert comparativo["pacotes_impacto"][0]["pacote"] in {"duelista_elemental", "curador_de_cerco", "vanguarda_brutal"}
    assert "recomendacoes_balanceamento" in comparativo


def test_calcular_score_saude_template_pune_alerta_e_desequilibrio():
    score_ok = calcular_score_saude_template(
        {
            "modo": "1v1",
            "team_win_rate": {"team_a": 0.5, "team_b": 0.5},
            "team_survival_avg": {"team_a": 0.5, "team_b": 0.5},
            "avg_tempo_simulado": 30.0,
            "resumo_alertas": {},
        }
    )
    score_ruim = calcular_score_saude_template(
        {
            "modo": "1v1",
            "team_win_rate": {"team_a": 1.0, "team_b": 0.0},
            "team_survival_avg": {"team_a": 1.0, "team_b": 0.0},
            "avg_tempo_simulado": 6.0,
            "resumo_alertas": {"aviso": 2},
        }
    )
    assert score_ok > score_ruim


def test_gerar_recomendacoes_balanceamento_detecta_eixos_principais():
    comparativo = {
        "total_templates": 2,
        "alertas_mais_comuns": {
            "TEMPO_MUITO_CURTO": 1,
            "BAIXA_CONCLUSAO_DE_ONDAS": 1,
            "SEM_DEFENSOR_NA_HORDA": 1,
        },
    }
    reports = [
        {
            "template_id": "t1",
            "modo": "1v1",
            "team_win_rate": {"team_a": 1.0, "team_b": 0.0},
            "team_a": [{"papel": "assassino", "familia_arma": "dupla", "pacote_arquetipo": "assassino_termico"}],
            "team_b": [{"papel": "bruiser", "familia_arma": "lamina", "pacote_arquetipo": "vanguarda_brutal"}],
        },
        {
            "template_id": "t2",
            "modo": "grupo_vs_horda",
            "team_win_rate": {"team_a": 1.0, "team_b": 0.0},
            "team_a": [{"papel": "assassino", "familia_arma": "dupla", "pacote_arquetipo": "assassino_termico"}],
            "team_b": [{"papel": "horda", "familia_arma": "lamina", "pacote_arquetipo": ""}],
        },
    ]
    recs = gerar_recomendacoes_balanceamento(reports, comparativo)
    codigos = {item["codigo"] for item in recs}
    assert "AJUSTAR_BURST_GLOBAL" in codigos
    assert "FORTALECER_PACOTES_DE_HORDA" in codigos
    assert "FRONTLINE_RECOMENDADA_NA_HORDA" in codigos
    assert "REVISAR_PAPEL_DOMINANTE" in codigos
    assert "REVISAR_PACOTE_DOMINANTE" in codigos


def test_gerar_plano_ajuste_template_classifica_areas():
    report = {
        "template_id": "rush_alpha",
        "modo": "grupo_vs_grupo",
        "team_win_rate": {"team_a": 1.0, "team_b": 0.0},
        "resumo_alertas": {"aviso": 2},
        "alertas": [
            {"codigo": "TEMPO_MUITO_CURTO", "nivel": "aviso"},
            {"codigo": "DOMINANCIA_EXCESSIVA", "nivel": "aviso"},
            {"codigo": "CURA_SOBRESSAIU", "nivel": "info"},
        ],
        "team_a": [
            {"papel": "curandeiro", "familia_arma": "foco", "pacote_arquetipo": "curador_de_cerco"},
            {"papel": "assassino", "familia_arma": "dupla", "pacote_arquetipo": "assassino_termico"},
        ],
        "team_b": [
            {"papel": "bruiser", "familia_arma": "lamina", "pacote_arquetipo": "vanguarda_brutal"},
            {"papel": "duelista", "familia_arma": "haste", "pacote_arquetipo": "duelista_elemental"},
        ],
    }
    plano = gerar_plano_ajuste_template(report)
    areas = {item["area"] for item in plano["sugestoes"]}
    assert plano["template_id"] == "rush_alpha"
    assert plano["prioridade_geral"] == "alta"
    assert "arma" in areas
    assert "skill" in areas
    assert "composicao" in areas
    assert "papel" in areas
    assert "ia" in areas
    assert "pacote_dominante" in plano
