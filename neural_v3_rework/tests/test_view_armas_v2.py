from interface.view_armas import (
    _aplicar_preset_familia,
    _criar_arma_do_estado_ui,
    _default_weapon_ui_state,
    _limites_magia_por_familia,
    _resolver_estilo_preview,
    _sincronizar_dados_arma_v2,
)


def test_estado_padrao_forja_usa_schema_v2():
    dados = _default_weapon_ui_state()

    assert dados["familia"] == "lamina"
    assert dados["categoria"] == "arma_fisica"
    assert dados["subtipo"] == "espada"
    assert dados["tipo"] == "Reta"
    assert dados["raridade"] == "Comum"


def test_sincroniza_familia_a_partir_do_tipo_legado():
    dados = _sincronizar_dados_arma_v2({"tipo": "Arco", "estilo": "", "raridade": ""})

    assert dados["familia"] == "disparo"
    assert dados["categoria"] == "arma_fisica"
    assert dados["tipo"] == "Arco"
    assert dados["subtipo"] == "arco"
    assert dados["raridade"] == "Comum"


def test_limites_de_magia_variam_por_familia():
    assert _limites_magia_por_familia({"familia": "lamina"}) == (2, 0)
    assert _limites_magia_por_familia({"familia": "orbital"}) == (3, 0)
    assert _limites_magia_por_familia({"familia": "foco"}) == (4, 0)


def test_preset_de_familia_aplica_visual_e_mecanica_base():
    dados = _aplicar_preset_familia(_default_weapon_ui_state(), "disparo", subtipo="besta")

    assert dados["familia"] == "disparo"
    assert dados["tipo"] == "Arco"
    assert dados["subtipo"] == "besta"
    assert dados["estilo"] == "Besta"
    assert dados["forca_arco"] > 0
    assert dados["cores"] != _default_weapon_ui_state()["cores"]


def test_resolver_estilo_preview_casa_com_renderizadores_legados():
    assert _resolver_estilo_preview("corrente", "mangual") == "Mangual"
    assert _resolver_estilo_preview("dupla", "adagas") == "Adagas Gêmeas"
    assert _resolver_estilo_preview("hibrida", "dupla_forma") == "Espada↔Lança"


def test_criar_arma_do_estado_ui_remove_skills_embutidas():
    dados = _default_weapon_ui_state()
    dados["familia"] = "lamina"
    dados["subtipo"] = "espada"
    dados["estilo"] = "espada"
    dados["habilidades"] = [
        {"nome": "Bola de Fogo", "custo": 20},
        {"nome": "Lanca de Gelo", "custo": 18},
        {"nome": "Cometa", "custo": 40},
    ]

    arma = _criar_arma_do_estado_ui(dados)

    assert arma.familia == "lamina"
    assert arma.raridade == "Comum"
    assert arma.habilidades == []
