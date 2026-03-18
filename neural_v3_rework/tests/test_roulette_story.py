from pipeline_video.metadata_generator import generate_story_metadata
from pipeline_video.roulette_status import gerar_story_roleta_status, get_story_segment


def test_story_generation_creates_full_comment_roulette_package():
    story = gerar_story_roleta_status("Eu serei Deus de outro mundo")

    assert story["mode"] == "roleta_status"
    assert story["comment"] == "Eu serei Deus de outro mundo"
    assert len(story["rolls"]) == 9
    assert story["fighter1"]["nome"]
    assert story["fighter2"]["nome"]
    assert story["timeline_duration"] > 0.0


def test_story_timeline_starts_with_hook_and_ends_with_versus():
    story = gerar_story_roleta_status("Monta minha build lendaria")

    assert story["timeline"][0]["kind"] == "hook"
    assert story["timeline"][-1]["kind"] == "versus_reveal"
    assert get_story_segment(story, 0.1)["kind"] == "hook"
    assert get_story_segment(story, story["timeline_duration"] - 0.05)["kind"] == "versus_reveal"


def test_story_metadata_mentions_comment_and_build():
    story = gerar_story_roleta_status("Quero nascer quebrado")
    meta = generate_story_metadata(story, vencedor=story["hero_name"], platform="tiktok")

    assert story["comment"] in meta["title"] or story["comment"] in meta["description"]
    assert story["hero_name"] in meta["description"]
    assert "#RoletaDeStatus" in meta["hashtags"]
