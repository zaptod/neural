from nucleo.skills import get_skill_classification, get_skill_data, listar_skills_filtradas


def test_skill_classification_enriches_runtime_data():
    fireball = get_skill_classification("Bola de Fogo")
    fireball_data = get_skill_data("Bola de Fogo")

    assert fireball.elemento == "FOGO"
    assert fireball.classe_forca.value in {"IMPACTO", "CATACLISMO"}
    assert fireball_data["classe_forca"] == fireball.classe_forca.value
    assert fireball_data["classe_utilidade"] == fireball.classe_utilidade.value
    assert fireball_data["classe_magia"]["assinatura_visual"] == fireball.assinatura_visual


def test_skill_classification_distinguishes_role_axes():
    muralha = get_skill_classification("Muralha de Gelo")
    portal = get_skill_classification("Portal do Vazio")
    escudo = get_skill_classification("Escudo Arcano")
    cura = get_skill_classification("Cura Maior")

    assert muralha.classe_utilidade.value in {"CONTROLE", "ZONA"}
    assert portal.classe_utilidade.value == "INVOCACAO"
    assert escudo.classe_utilidade.value == "PROTECAO"
    assert cura.classe_utilidade.value == "CURA"
    assert portal.assinatura_visual == "sigilo"
    assert escudo.assinatura_visual == "domo"


def test_skill_listing_filters_by_new_classes():
    invocacoes = listar_skills_filtradas(utilidade="INVOCACAO")
    protecoes = listar_skills_filtradas(utilidade="PROTECAO")
    fogo_impacto = listar_skills_filtradas(elemento="FOGO", forca="IMPACTO")

    assert "Portal do Vazio" in invocacoes
    assert "Escudo Arcano" in protecoes
    assert "Bola de Fogo" in fogo_impacto
    assert "Cura Maior" not in fogo_impacto
