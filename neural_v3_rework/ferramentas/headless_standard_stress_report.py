import json
import math
import os
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ia.behavior_profiles import BEHAVIOR_PROFILES
from dados.app_state import AppState, DEFAULT_MATCH_CONFIG
from modelos.characters import Personagem
from modelos.constants import (
    CLASSES_DATA,
    ENCANTAMENTOS,
    LISTA_CLASSES,
    LISTA_RARIDADES,
    LISTA_TIPOS_ARMA,
    TIPOS_ARMA,
)
from modelos.weapons import Arma
from simulacao.simulacao import Simulador


OUTPUT_DIR = BASE_DIR.parent / "stress_test_data"
OUTPUT_FILE = OUTPUT_DIR / os.environ.get("NF_STRESS_REPORT_NAME", "headless_standard_report.json")
RNG_SEED = int(os.environ.get("NF_STRESS_SEED", "16032026"))
FIGHTER_COUNT = int(os.environ.get("NF_STRESS_FIGHTERS", "1000"))
WEAPON_COUNT = int(os.environ.get("NF_STRESS_WEAPONS", "280"))
ROUNDS = int(os.environ.get("NF_STRESS_ROUNDS", "2"))
MAX_FRAMES = int(os.environ.get("NF_STRESS_MAX_FRAMES", "5400"))
FPS = 60.0


FIRST_PARTS = [
    "Aeron", "Bael", "Caelum", "Darian", "Eldrin", "Faelar", "Garen", "Helios", "Icar", "Joren",
    "Kael", "Lorien", "Maelor", "Narek", "Orin", "Pavel", "Quorin", "Riven", "Sylas", "Theron",
    "Ulric", "Vael", "Weylin", "Xeran", "Yorik", "Zeph", "Alar", "Bram", "Cass", "Draven",
    "Eryx", "Fen", "Gideon", "Hadar", "Isen", "Jax", "Korin", "Lucan", "Marek", "Nyx",
]

LAST_PARTS = [
    "Ash", "Briar", "Cinder", "Dawn", "Ember", "Frost", "Gale", "Hollow", "Iron", "Jade",
    "Keen", "Lumen", "Mourn", "Night", "Omen", "Pyre", "Quill", "Rune", "Shade", "Thorn",
    "Umber", "Vale", "Ward", "Xen", "Yew", "Zenith", "Astra", "Blight", "Crown", "Drift",
    "Echo", "Flint", "Grave", "Harbor", "Ivory", "Knell", "Lotus", "Mist", "Nova", "Onyx",
]

TITLE_PARTS = [
    "of Iron", "of Dawn", "of the Vale", "of Cinders", "the Silent", "the Bold", "the Hollow",
    "the Keen", "the Last", "the Swift", "the Unbroken", "the Pale", "the Emberborn", "the Grim",
    "the Red", "the Azure", "the Stalwart", "the Veiled", "the Prime", "the Stormbound",
]


def personality_names():
    names = []
    for name, profile in BEHAVIOR_PROFILES.items():
        if isinstance(profile, dict) and "recuar_threshold" in profile:
            names.append(name)
    return sorted(names)


def build_unique_names(count):
    names = []
    used = set()
    for first in FIRST_PARTS:
        for last in LAST_PARTS:
            for title in TITLE_PARTS:
                name = f"{first} {last} {title}"
                if name not in used:
                    used.add(name)
                    names.append(name)
                if len(names) >= count:
                    return names
    raise ValueError(f"Unable to build {count} unique names")


def sample_enchantments(rng, rarity):
    if rarity == "Comum":
        return []
    max_allowed = {
        "Incomum": 1,
        "Raro": 2,
        "Ã‰pico": 3,
        "LendÃ¡rio": 4,
        "MÃ­tico": 5,
    }.get(rarity, 0)
    pool = list(ENCANTAMENTOS.keys())
    rng.shuffle(pool)
    amount = rng.randint(0, min(max_allowed, 2 if rarity in {"Incomum", "Raro"} else 3))
    return pool[:amount]


def generate_weapons(count, rng):
    weapons = []
    weapon_lookup = {}
    styles_by_type = {weapon_type: data.get("estilos", [weapon_type]) for weapon_type, data in TIPOS_ARMA.items()}
    geometry_defaults = {
        "comp_cabo": 15.0,
        "comp_lamina": 50.0,
        "largura": 8.0,
        "distancia": 20.0,
        "comp_corrente": 0.0,
        "comp_ponta": 0.0,
        "largura_ponta": 0.0,
        "tamanho_projetil": 0.0,
        "tamanho_arco": 0.0,
        "tamanho_flecha": 0.0,
        "tamanho": 8.0,
        "distancia_max": 0.0,
        "separacao": 0.0,
        "forma1_cabo": 0.0,
        "forma1_lamina": 0.0,
        "forma2_cabo": 0.0,
        "forma2_lamina": 0.0,
    }
    for index in range(count):
        weapon_type = rng.choice(LISTA_TIPOS_ARMA)
        rarity = rng.choices(LISTA_RARIDADES, weights=[22, 24, 20, 16, 12, 6], k=1)[0]
        base_damage = round(rng.uniform(4.8, 8.8), 2)
        base_weight = round(rng.uniform(0.8, 4.9), 2)
        critico = round(rng.uniform(0.0, 12.0), 2)
        velocidade = round(rng.uniform(0.8, 1.35), 2)
        style = rng.choice(styles_by_type[weapon_type])
        affinity = rng.choice(["FOGO", "GELO", "RAIO", "NATUREZA", "LUZ", "TREVAS", "ARCANO"])
        abilities = [{"nome": f"Skill-{index:03d}-A", "custo": round(rng.uniform(20.0, 55.0), 1)}]
        if rarity in {"Raro", "Ã‰pico", "LendÃ¡rio", "MÃ­tico"} and rng.random() < 0.55:
            abilities.append({"nome": f"Skill-{index:03d}-B", "custo": round(rng.uniform(25.0, 65.0), 1)})
        weapon = Arma(
            nome=f"StressWeapon-{index:04d}",
            tipo=weapon_type,
            dano=base_damage,
            peso=base_weight,
            r=rng.randint(40, 255),
            g=rng.randint(40, 255),
            b=rng.randint(40, 255),
            estilo=style,
            cabo_dano=rng.random() < 0.15,
            habilidade=abilities[0]["nome"],
            custo_mana=abilities[0]["custo"],
            raridade=rarity,
            habilidades=abilities,
            encantamentos=sample_enchantments(rng, rarity),
            passiva=None,
            critico=critico,
            velocidade_ataque=velocidade,
            afinidade_elemento=affinity,
            durabilidade=100.0,
            durabilidade_max=100.0,
            quantidade=1,
            quantidade_orbitais=1 if weapon_type != "Orbital" else rng.randint(1, 3),
            forca_arco=round(rng.uniform(6.0, 9.0), 2) if weapon_type == "Arco" else 0.0,
            forma_atual=1,
        )
        for attr, default in geometry_defaults.items():
            setattr(weapon, attr, default)
        weapon.distancia = {
            "Reta": 18.0,
            "Dupla": 13.0,
            "Corrente": 28.0,
            "Arremesso": 20.0,
            "Arco": 24.0,
            "Orbital": 16.0,
            "MÃ¡gica": 22.0,
            "TransformÃ¡vel": 20.0,
        }.get(weapon_type, 20.0)
        weapon.largura = {
            "Reta": 10.0,
            "Dupla": 7.0,
            "Corrente": 12.0,
            "Arremesso": 8.0,
            "Arco": 8.0,
            "Orbital": 14.0,
            "MÃ¡gica": 11.0,
            "TransformÃ¡vel": 10.0,
        }.get(weapon_type, 8.0)
        weapons.append(weapon)
        weapon_lookup[weapon.nome] = weapon
    return weapons, weapon_lookup


def generate_characters(count, weapons, rng):
    names = build_unique_names(count)
    personalities = personality_names()
    characters = []
    for index, name in enumerate(names):
        weapon = weapons[index % len(weapons)]
        class_name = rng.choice(LISTA_CLASSES)
        personality = rng.choice(personalities)
        size = round(rng.uniform(1.45, 2.65), 2)
        force = round(rng.uniform(4.8, 10.0), 1)
        mana = round(rng.uniform(4.5, 10.0), 1)
        character = Personagem(
            nome=name,
            tamanho=size,
            forca=force,
            mana=mana,
            nome_arma=weapon.nome,
            peso_arma_cache=weapon.peso,
            r=rng.randint(30, 255),
            g=rng.randint(30, 255),
            b=rng.randint(30, 255),
            classe=class_name,
            personalidade=personality,
            god_id=None,
            lore=f"Stress test fighter {index:04d}",
        )
        characters.append(character)
    return characters


def make_schedule(names, rounds, rng):
    schedule = []
    for round_index in range(rounds):
        shuffled = list(names)
        rng.shuffle(shuffled)
        if len(shuffled) % 2 == 1:
            shuffled.append(shuffled[0])
        for idx in range(0, len(shuffled), 2):
            p1 = shuffled[idx]
            p2 = shuffled[idx + 1]
            if p1 != p2:
                schedule.append((round_index, p1, p2))
    return schedule


def run_duel(state, p1_name, p2_name, weapon_lookup):
    state._match = {
        **DEFAULT_MATCH_CONFIG,
        "p1_nome": p1_name,
        "p2_nome": p2_name,
        "cenario": "Arena",
        "best_of": 1,
    }

    sim = Simulador()
    p1 = sim.p1
    p2 = sim.p2
    if not p1 or not p2:
        raise RuntimeError("Simulador failed to create fighters")

    frames = 0
    dt = 1.0 / FPS
    while frames < MAX_FRAMES and not p1.morto and not p2.morto:
        sim.update(dt)
        frames += 1

    if p1.morto and not p2.morto:
        winner = p2.dados.nome
        loser = p1.dados.nome
        finish = "KO"
    elif p2.morto and not p1.morto:
        winner = p1.dados.nome
        loser = p2.dados.nome
        finish = "KO"
    elif p1.morto and p2.morto:
        winner = "double_ko"
        loser = "double_ko"
        finish = "DOUBLE_KO"
    else:
        winner = "timeout"
        loser = "timeout"
        finish = "TIMEOUT"

    p1_weapon = weapon_lookup[p1.dados.nome_arma]
    p2_weapon = weapon_lookup[p2.dados.nome_arma]
    p1_damage_taken = max(0.0, p1.vida_max - p1.vida)
    p2_damage_taken = max(0.0, p2.vida_max - p2.vida)

    return {
        "p1_name": p1.dados.nome,
        "p2_name": p2.dados.nome,
        "p1_personality": p1.dados.personalidade,
        "p2_personality": p2.dados.personalidade,
        "p1_class": p1.dados.classe,
        "p2_class": p2.dados.classe,
        "p1_weapon": p1.dados.nome_arma,
        "p2_weapon": p2.dados.nome_arma,
        "p1_weapon_type": p1_weapon.tipo,
        "p2_weapon_type": p2_weapon.tipo,
        "p1_weapon_rarity": p1_weapon.raridade,
        "p2_weapon_rarity": p2_weapon.raridade,
        "p1_force": p1.dados.forca,
        "p2_force": p2.dados.forca,
        "p1_mana": p1.dados.mana,
        "p2_mana": p2.dados.mana,
        "frames": frames,
        "seconds": round(frames / FPS, 2),
        "finish": finish,
        "winner": winner,
        "loser": loser,
        "p1_damage_dealt": round(p2_damage_taken, 2),
        "p2_damage_dealt": round(p1_damage_taken, 2),
        "p1_hp_left_pct": round(max(0.0, p1.vida) / max(1.0, p1.vida_max), 4),
        "p2_hp_left_pct": round(max(0.0, p2.vida) / max(1.0, p2.vida_max), 4),
    }


def aggregate_rate_table(results, key_name, sample_floor=20):
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "timeouts": 0, "appearances": 0, "frames": []})
    for item in results:
        for slot in ("p1", "p2"):
            key = item[f"{slot}_{key_name}"]
            stats[key]["appearances"] += 1
            stats[key]["frames"].append(item["frames"])
            if item["winner"] == item[f"{slot}_name"]:
                stats[key]["wins"] += 1
            elif item["finish"] == "TIMEOUT":
                stats[key]["timeouts"] += 1
            elif item["finish"] == "DOUBLE_KO":
                stats[key]["timeouts"] += 1
            else:
                stats[key]["losses"] += 1

    rows = []
    for key, entry in stats.items():
        appearances = entry["appearances"]
        if appearances == 0:
            continue
        avg_frames = statistics.mean(entry["frames"])
        win_rate = entry["wins"] / appearances
        timeout_rate = entry["timeouts"] / appearances
        row = {
            "name": key,
            "appearances": appearances,
            "wins": entry["wins"],
            "losses": entry["losses"],
            "timeouts": entry["timeouts"],
            "win_rate": round(win_rate, 4),
            "timeout_rate": round(timeout_rate, 4),
            "avg_seconds": round(avg_frames / FPS, 2),
            "eligible": appearances >= sample_floor,
        }
        rows.append(row)
    rows.sort(key=lambda row: (-row["eligible"], -row["appearances"], -row["win_rate"], row["name"]))
    return rows


def pair_duration_table(results, min_samples=16):
    grouped = defaultdict(list)
    for item in results:
        pair = tuple(sorted((item["p1_weapon_type"], item["p2_weapon_type"])))
        grouped[pair].append(item["seconds"])
    rows = []
    for pair, samples in grouped.items():
        if len(samples) < min_samples:
            continue
        rows.append(
            {
                "pair": f"{pair[0]} vs {pair[1]}",
                "samples": len(samples),
                "avg_seconds": round(statistics.mean(samples), 2),
                "median_seconds": round(statistics.median(samples), 2),
            }
        )
    rows.sort(key=lambda row: (row["avg_seconds"], -row["samples"], row["pair"]))
    return rows


def find_concerns(results, personality_rows, weapon_type_rows, rarity_rows, pair_rows):
    concerns = []
    durations = [item["seconds"] for item in results]
    avg_seconds = statistics.mean(durations)
    timeout_rate = sum(1 for item in results if item["finish"] == "TIMEOUT") / max(1, len(results))

    if avg_seconds < 45.0:
        concerns.append(
            {
                "kind": "fight_duration",
                "severity": "high",
                "message": f"Average fight duration is {avg_seconds:.2f}s, well below the expected normal combat pace.",
            }
        )
    if timeout_rate > 0.2:
        concerns.append(
            {
                "kind": "timeouts",
                "severity": "medium",
                "message": f"Timeout rate is {timeout_rate:.1%}, suggesting pacing or finish-pressure issues.",
            }
        )

    for row in personality_rows:
        if not row["eligible"]:
            continue
        if row["win_rate"] <= 0.30:
            concerns.append(
                {
                    "kind": "personality_underperform",
                    "severity": "medium",
                    "message": f"Personality {row['name']} is underperforming with {row['win_rate']:.1%} win rate over {row['appearances']} appearances.",
                }
            )
        elif row["win_rate"] >= 0.70:
            concerns.append(
                {
                    "kind": "personality_overperform",
                    "severity": "medium",
                    "message": f"Personality {row['name']} is overperforming with {row['win_rate']:.1%} win rate over {row['appearances']} appearances.",
                }
            )

    for row in weapon_type_rows:
        if not row["eligible"]:
            continue
        if row["avg_seconds"] < avg_seconds * 0.75:
            concerns.append(
                {
                    "kind": "weapon_pacing",
                    "severity": "medium",
                    "message": f"Weapon type {row['name']} is associated with short fights ({row['avg_seconds']:.2f}s average).",
                }
            )
        if row["win_rate"] >= 0.65 or row["win_rate"] <= 0.35:
            concerns.append(
                {
                    "kind": "weapon_balance",
                    "severity": "medium",
                    "message": f"Weapon type {row['name']} has suspicious win rate {row['win_rate']:.1%} across {row['appearances']} appearances.",
                }
            )

    for row in rarity_rows:
        if not row["eligible"]:
            continue
        if row["win_rate"] >= 0.64:
            concerns.append(
                {
                    "kind": "rarity_balance",
                    "severity": "low",
                    "message": f"Rarity {row['name']} is outperforming at {row['win_rate']:.1%} win rate.",
                }
            )

    for row in pair_rows[:6]:
        if row["avg_seconds"] < avg_seconds * 0.7:
            concerns.append(
                {
                    "kind": "weapon_pair_pacing",
                    "severity": "medium",
                    "message": f"Pair {row['pair']} resolves very quickly ({row['avg_seconds']:.2f}s average over {row['samples']} battles).",
                }
            )
    return concerns


def build_report(results, fighters, weapons, started_at, schedule_size):
    durations = [item["seconds"] for item in results]
    frames = [item["frames"] for item in results]
    finishes = Counter(item["finish"] for item in results)
    weapon_type_rows = aggregate_rate_table(results, "weapon_type")
    rarity_rows = aggregate_rate_table(results, "weapon_rarity")
    personality_rows = aggregate_rate_table(results, "personality")
    class_rows = aggregate_rate_table(results, "class")
    pair_rows = pair_duration_table(results)
    concerns = find_concerns(results, personality_rows, weapon_type_rows, rarity_rows, pair_rows)

    report = {
        "meta": {
            "seed": RNG_SEED,
            "fighters_generated": len(fighters),
            "weapons_generated": len(weapons),
            "battles_scheduled": schedule_size,
            "battles_completed": len(results),
            "max_frames_per_battle": MAX_FRAMES,
            "max_seconds_per_battle": round(MAX_FRAMES / FPS, 2),
            "elapsed_wall_clock_seconds": round(time.time() - started_at, 2),
            "engine": "standard_headless_simulador",
        },
        "summary": {
            "avg_duration_seconds": round(statistics.mean(durations), 2) if durations else 0.0,
            "median_duration_seconds": round(statistics.median(durations), 2) if durations else 0.0,
            "p90_duration_seconds": round(sorted(durations)[math.floor(0.9 * (len(durations) - 1))], 2) if durations else 0.0,
            "min_duration_seconds": round(min(durations), 2) if durations else 0.0,
            "max_duration_seconds": round(max(durations), 2) if durations else 0.0,
            "avg_duration_frames": round(statistics.mean(frames), 2) if frames else 0.0,
            "ko_rate": round(finishes.get("KO", 0) / max(1, len(results)), 4),
            "timeout_rate": round(finishes.get("TIMEOUT", 0) / max(1, len(results)), 4),
            "double_ko_rate": round(finishes.get("DOUBLE_KO", 0) / max(1, len(results)), 4),
        },
        "top_personalities": {
            "strongest": [row for row in personality_rows if row["eligible"]][:8],
            "weakest": sorted([row for row in personality_rows if row["eligible"]], key=lambda row: (row["win_rate"], -row["appearances"], row["name"]))[:8],
        },
        "weapon_types": weapon_type_rows,
        "weapon_rarities": rarity_rows,
        "classes": class_rows,
        "fastest_weapon_pairs": pair_rows[:12],
        "concerns": concerns,
        "sample_battles": results[:24],
    }
    return report


def print_report(report):
    summary = report["summary"]
    print("\n=== HEADLESS STRESS REPORT ===")
    print(f"fighters={report['meta']['fighters_generated']} weapons={report['meta']['weapons_generated']} battles={report['meta']['battles_completed']}")
    print(
        "duration_avg={:.2f}s median={:.2f}s p90={:.2f}s timeout_rate={:.1%} ko_rate={:.1%}".format(
            summary["avg_duration_seconds"],
            summary["median_duration_seconds"],
            summary["p90_duration_seconds"],
            summary["timeout_rate"],
            summary["ko_rate"],
        )
    )
    print("\nTop concerns:")
    if report["concerns"]:
        for concern in report["concerns"][:12]:
            print(f"- [{concern['severity']}] {concern['message']}")
    else:
        print("- none")

    print("\nWeapon types:")
    for row in report["weapon_types"][:8]:
        if row["eligible"]:
            print(f"- {row['name']}: win_rate={row['win_rate']:.1%} avg={row['avg_seconds']:.2f}s appearances={row['appearances']}")

    print("\nWeak personalities:")
    for row in report["top_personalities"]["weakest"][:6]:
        print(f"- {row['name']}: win_rate={row['win_rate']:.1%} avg={row['avg_seconds']:.2f}s appearances={row['appearances']}")


def main():
    rng = random.Random(RNG_SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    state = AppState.get()
    original_weapons = list(state._weapons)
    original_characters = list(state._characters)
    original_match = dict(state._match)
    started_at = time.time()

    weapons, weapon_lookup = generate_weapons(WEAPON_COUNT, rng)
    fighters = generate_characters(FIGHTER_COUNT, weapons, rng)
    schedule = make_schedule([fighter.nome for fighter in fighters], ROUNDS, rng)
    results = []
    errors = []

    try:
        state._weapons = weapons
        state._characters = fighters
        for index, (_, p1_name, p2_name) in enumerate(schedule, start=1):
            try:
                duel = run_duel(state, p1_name, p2_name, weapon_lookup)
                results.append(duel)
            except Exception as exc:
                errors.append({"battle": index, "p1": p1_name, "p2": p2_name, "error": str(exc)})
            if index % 100 == 0 or index == len(schedule):
                print(f"progress {index}/{len(schedule)} completed={len(results)} errors={len(errors)}")
    finally:
        state._weapons = original_weapons
        state._characters = original_characters
        state._match = original_match if original_match else dict(DEFAULT_MATCH_CONFIG)

    report = build_report(results, fighters, weapons, started_at, len(schedule))
    report["errors"] = errors[:50]
    report["meta"]["error_count"] = len(errors)

    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print_report(report)
    print(f"\nreport_file={OUTPUT_FILE}")


if __name__ == "__main__":
    main()
