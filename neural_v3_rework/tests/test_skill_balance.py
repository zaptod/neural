from nucleo.skills import SKILL_DB


def test_offensive_skill_budgets_stay_within_reasonable_caps():
    max_por_tipo = {
        "PROJETIL": 60.0,
        "AREA": 80.0,
        "BEAM": 40.0,
        "TRAP": 35.0,
        "DASH": 24.0,
    }
    for nome, dados in SKILL_DB.items():
        tipo = dados.get("tipo")
        if tipo in max_por_tipo:
            assert float(dados.get("dano", 0) or 0) <= max_por_tipo[tipo], nome


def test_extreme_skills_receive_balance_metadata():
    for nome in ("Bola de Fogo", "Cometa", "Muralha de Gelo", "Portal do Vazio"):
        assert SKILL_DB[nome]["balance_profile"]["versao"] == "v3_runtime"


def test_beam_and_channel_have_saner_damage_over_time():
    for nome, dados in SKILL_DB.items():
        if dados.get("tipo") == "BEAM" and dados.get("dano_por_segundo"):
            assert float(dados["dano_por_segundo"]) <= 24.0, nome
        if dados.get("tipo") == "CHANNEL" and dados.get("dano_por_segundo"):
            assert float(dados["dano_por_segundo"]) <= 18.0, nome


def test_projectile_spam_skills_pay_more_for_burst_or_multishot():
    for nome, dados in SKILL_DB.items():
        if dados.get("tipo") != "PROJETIL":
            continue
        dano = float(dados.get("dano", 0) or 0)
        multi = int(dados.get("multi_shot", 1) or 1)
        cooldown = float(dados.get("cooldown", 0) or 0)
        custo = float(dados.get("custo", 0) or 0)
        if multi > 1:
            assert cooldown >= 4.3, nome
            assert custo >= 14.0, nome
        if dano >= 32.0:
            assert cooldown >= 5.6, nome
            assert custo >= 22.0, nome


def test_large_or_heavy_area_skills_have_real_commitment():
    for nome, dados in SKILL_DB.items():
        if dados.get("tipo") != "AREA":
            continue
        dano = float(dados.get("dano", 0) or 0)
        raio = float(dados.get("raio_area", 0) or 0)
        cooldown = float(dados.get("cooldown", 0) or 0)
        custo = float(dados.get("custo", 0) or 0)
        if raio >= 2.2:
            assert cooldown >= 9.5, nome
            assert custo >= 24.0, nome
        if dano >= 48.0 or raio >= 3.2:
            assert cooldown >= 11.5, nome
            assert custo >= 30.0, nome
