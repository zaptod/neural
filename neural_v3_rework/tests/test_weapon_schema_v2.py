from modelos.weapons import Arma


def test_legacy_weapon_is_migrated_to_schema_v2_and_normalizes_crit():
    arma = Arma(
        nome="Aurora Celeste",
        tipo="Reta",
        dano=8.6,
        peso=4.4,
        estilo="Corte (Espada)",
        critico=12.0,
        velocidade_ataque=1.12,
        afinidade_elemento="LUZ",
        raridade="Lendário",
        encantamentos=["Sagrado"],
        passiva={"efeito": "execute", "valor": 15},
    )

    assert arma.schema_version == 2
    assert arma.familia == "lamina"
    assert arma.tipo == "Reta"
    assert arma.critico == 0.12
    assert arma.encantamentos == []
    assert arma.passiva is None
    assert arma.meta_legado["encantamentos"] == ["Sagrado"]
    assert arma.meta_legado["passiva"]["efeito"] == "execute"


def test_magic_weapon_becomes_focus_and_separates_magic_profile():
    arma = Arma(
        nome="Cetro do Eclipse",
        tipo="Mágica",
        dano=8.1,
        peso=2.8,
        afinidade_elemento="VOID",
        habilidades=[{"nome": "Buraco Negro", "custo": 34.0}],
    )

    assert arma.familia == "foco"
    assert arma.categoria == "foco_magico"
    assert arma.usa_foco_magico is True
    assert arma.perfil_magico["afinidade"] == "VOID"
    assert arma.habilidade == "Buraco Negro"


def test_to_dict_persists_new_sections_and_runtime_compatibility_fields():
    arma = Arma(
        nome="Vigia Orbital",
        tipo="Orbital",
        dano=6.5,
        peso=3.0,
        quantidade_orbitais=3,
        raridade="Épico",
    )

    data = arma.to_dict()

    assert data["schema_version"] == 2
    assert data["familia"] == "orbital"
    assert "combate" in data
    assert "visual" in data
    assert "magia" in data
    assert data["tipo"] == "Orbital"
    assert data["quantidade_orbitais"] == 3
