from nucleo.campanha import find_path, load_campaign_maps, load_campaign_missions


def test_campaign_catalogs_load():
    mapas = load_campaign_maps()
    missoes = load_campaign_missions()

    assert mapas["mapas"]
    assert missoes["missoes"]


def test_campaign_pathfinding_finds_a_route():
    mapa = load_campaign_maps()["mapas"][0]
    path = find_path(mapa, (6, 13), (31, 13))

    assert path
    assert path[0] == (6, 13)
    assert path[-1] == (31, 13)
