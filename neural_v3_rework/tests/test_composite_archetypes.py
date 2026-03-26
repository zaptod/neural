from ia.composite_archetypes import construir_arvore_arquetipo, inferir_arquetipo_composto
from ia.personalities import LISTA_PERSONALIDADES
from modelos import Arma, LISTA_CLASSES, Personagem
from nucleo.entities import Lutador


def _classe():
    return LISTA_CLASSES[0]


def _personalidade():
    return LISTA_PERSONALIDADES[0]


def test_inferir_arquetipo_composto_retorna_pacote_legivel():
    arma = Arma(nome="Katana de Teste", familia="lamina", subtipo="espada", tipo="Reta", dano=10, peso=3)

    perfil = inferir_arquetipo_composto(
        _classe(),
        _personalidade(),
        arma,
        ["Bola de Fogo", "Falange Prismatica"],
    )

    assert perfil["nome_composto"]
    assert perfil["familia_arma"] == "lamina"
    assert perfil["papel_primario"]["nome"]
    assert perfil["padrao_decisao"]
    assert "Bola de Fogo" in perfil["skills"]
    assert "Falange Prismatica" in perfil["skills"]


def test_construir_arvore_arquetipo_expande_blocos_principais():
    arma = Arma(nome="Escudo Astral", familia="orbital", subtipo="escudo", tipo="Orbital", dano=8, peso=4)
    perfil = inferir_arquetipo_composto(
        _classe(),
        _personalidade(),
        arma,
        ["Falange Prismatica", "Mare Prismatica"],
    )

    arvore = construir_arvore_arquetipo(perfil)
    titulos = [bloco["titulo"] for bloco in arvore]

    assert "Nucleo" in titulos
    assert "Leitura Tatica" in titulos
    assert "Padrao De Decisao" in titulos
    assert "Pacote Oficial" in titulos
    assert "Alertas" in titulos


def test_pacote_oficial_detectado_para_bastiao_orbital():
    arma = Arma(nome="Escudo Astral", familia="orbital", subtipo="escudo", tipo="Orbital", dano=8, peso=4)
    perfil = inferir_arquetipo_composto(
        "Paladino (Sagrado)",
        _personalidade(),
        arma,
        ["Falange Prismatica", "Mare Prismatica"],
    )

    assert perfil["pacote_referencia"] is not None
    assert perfil["pacote_referencia"]["id"] in {"bastiao_prismatico", "curador_de_cerco"}


def test_desvios_de_pacote_aparecem_quando_kit_foge_da_referencia():
    arma = Arma(nome="Orbe Torto", familia="orbital", subtipo="escudo", tipo="Orbital", dano=8, peso=4)
    perfil = inferir_arquetipo_composto(
        "Paladino (Sagrado)",
        _personalidade(),
        arma,
        ["Bola de Fogo"],
    )

    assert perfil["pacote_referencia"] is not None
    assert perfil["desvios_pacote"]


def test_lutador_usa_skills_do_personagem_e_expoe_arquetipo_composto():
    arma = Arma(nome="Lamina Viva", familia="lamina", subtipo="espada", tipo="Reta", dano=9, peso=2)
    personagem = Personagem(
        nome="Kai",
        tamanho=1.7,
        forca=6.0,
        mana=7.0,
        nome_arma=arma.nome,
        classe=_classe(),
        personalidade=_personalidade(),
        skills_personagem=[{"nome": "Bola de Fogo"}, {"nome": "Falange Prismatica"}],
    )
    personagem.recalcular_com_arma(arma)

    lutador = Lutador(personagem, 0.0, 0.0)

    assert [skill["nome"] for skill in lutador.skills_arma[:2]] == ["Bola de Fogo", "Falange Prismatica"]
    assert lutador.arquetipo_composto is not None
    assert lutador.arquetipo_composto["familia_arma"] == "lamina"
