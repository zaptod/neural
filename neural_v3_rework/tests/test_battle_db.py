"""Tests for data/battle_db.py — SQLite battle log persistence."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.battle_db import BattleDB


def get_test_db() -> BattleDB:
    """Create a fresh in-memory test database."""
    db = BattleDB(":memory:")
    return db


def test_schema_creation():
    db = get_test_db()
    summary = db.get_summary()
    assert summary["total_matches"] == 0
    assert summary["total_events"] == 0
    assert summary["total_characters"] == 0
    db.close()
    print("  OK  T1: Schema creation")


def test_insert_and_query_match():
    db = get_test_db()
    mid = db.insert_match(
        p1="Caleb", p2="Bjorn", winner="Caleb", loser="Bjorn",
        duration=23.5, ko_type="KO", arena="Arena Padrão",
        p1_class="Guerreiro", p2_class="Mago",
        p1_weapon="Espada Reta", p2_weapon="Cajado"
    )
    assert mid == 1
    match = db.get_match(mid)
    assert match is not None
    assert match["p1"] == "Caleb"
    assert match["winner"] == "Caleb"
    assert match["duration"] == 23.5
    assert match["ko_type"] == "KO"
    assert match["p1_class"] == "Guerreiro"
    assert db.count_matches() == 1
    db.close()
    print("  OK  T2: Insert and query match")


def test_match_history():
    db = get_test_db()
    db.insert_match(p1="A", p2="B", winner="A", loser="B", duration=10.0)
    db.insert_match(p1="C", p2="A", winner="C", loser="A", duration=15.0)
    db.insert_match(p1="B", p2="C", winner="B", loser="C", duration=8.0)

    all_history = db.get_match_history(limit=10)
    assert len(all_history) == 3

    a_history = db.get_match_history(character="A")
    assert len(a_history) == 2  # A was in matches 1 and 2

    b_history = db.get_match_history(character="B")
    assert len(b_history) == 2  # B was in matches 1 and 3
    db.close()
    print("  OK  T3: Match history filtering")


def test_events():
    db = get_test_db()
    mid = db.insert_match(p1="X", p2="Y", winner="X", loser="Y", duration=5.0)

    eid1 = db.insert_event(mid, frame=10, event_type="hit",
                           data={"attacker": "X", "damage": 12.5})
    eid2 = db.insert_event(mid, frame=30, event_type="skill",
                           data={"caster": "Y", "skill": "Bola de Fogo", "cost": 15})
    eid3 = db.insert_event(mid, frame=50, event_type="hit",
                           data={"attacker": "X", "damage": 8.0})

    all_events = db.get_events(mid)
    assert len(all_events) == 3
    assert all_events[0]["event_type"] == "hit"
    assert all_events[0]["data"]["damage"] == 12.5

    hits = db.get_events(mid, event_type="hit")
    assert len(hits) == 2

    skills = db.get_events(mid, event_type="skill")
    assert len(skills) == 1
    assert skills[0]["data"]["skill"] == "Bola de Fogo"
    db.close()
    print("  OK  T4: Events insert and query")


def test_batch_events():
    db = get_test_db()
    mid = db.insert_match(p1="A", p2="B", winner="A", loser="B", duration=3.0)

    events = [
        (mid, 1, "hit", {"attacker": "A", "damage": 5.0}),
        (mid, 2, "hit", {"attacker": "B", "damage": 3.0}),
        (mid, 3, "skill", {"caster": "A", "skill": "Dash"}),
        (mid, 4, "ko", {"victim": "B"}),
    ]
    db.insert_events_batch(events)

    all_events = db.get_events(mid)
    assert len(all_events) == 4
    db.close()
    print("  OK  T5: Batch events")


def test_character_stats():
    db = get_test_db()

    db.update_character_stats("Caleb", won=True, elo_delta=16.5, damage=120.0, tier="SILVER")
    stats = db.get_character_stats("Caleb")
    assert stats is not None
    assert stats["wins"] == 1
    assert stats["losses"] == 0
    assert stats["elo"] == 1616.5  # 1600 + 16.5
    assert stats["tier"] == "SILVER"
    assert stats["total_damage"] == 120.0

    db.update_character_stats("Caleb", won=False, elo_delta=-14.0, damage=80.0)
    stats = db.get_character_stats("Caleb")
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert abs(stats["elo"] - 1602.5) < 0.01  # 1616.5 - 14.0
    assert stats["peak_elo"] == 1616.5  # Peak unchanged
    assert stats["matches_played"] == 2
    db.close()
    print("  OK  T6: Character stats update")


def test_elo_never_negative():
    db = get_test_db()
    # Force ELO way below zero
    db.update_character_stats("Weak", won=False, elo_delta=-2000.0)
    stats = db.get_character_stats("Weak")
    assert stats["elo"] >= 0, f"ELO went negative: {stats['elo']}"
    db.close()
    print("  OK  T7: ELO never negative")


def test_leaderboard():
    db = get_test_db()
    db.update_character_stats("Low", won=True, elo_delta=10.0)
    db.update_character_stats("Mid", won=True, elo_delta=50.0)
    db.update_character_stats("High", won=True, elo_delta=100.0)

    board = db.get_leaderboard(limit=3)
    assert len(board) == 3
    assert board[0]["name"] == "High"
    assert board[1]["name"] == "Mid"
    assert board[2]["name"] == "Low"
    db.close()
    print("  OK  T8: Leaderboard ordering")


def test_winrate():
    db = get_test_db()
    db.update_character_stats("Test", won=True, elo_delta=0)
    db.update_character_stats("Test", won=True, elo_delta=0)
    db.update_character_stats("Test", won=False, elo_delta=0)

    wr = db.get_winrate("Test")
    assert abs(wr - 2 / 3) < 0.01
    assert db.get_winrate("NonExistent") == 0.0
    db.close()
    print("  OK  T9: Winrate calculation")


def test_foreign_key_cascade():
    db = get_test_db()
    mid = db.insert_match(p1="A", p2="B", winner="A", loser="B", duration=1.0)
    db.insert_event(mid, 1, "hit", {"damage": 5})
    db.insert_event(mid, 2, "hit", {"damage": 3})

    events_before = db.get_events(mid)
    assert len(events_before) == 2

    # Delete the match — events should cascade
    with db._cursor() as cur:
        cur.execute("DELETE FROM matches WHERE id = ?", (mid,))

    events_after = db.get_events(mid)
    assert len(events_after) == 0
    db.close()
    print("  OK  T10: Foreign key cascade delete")


def test_file_persistence():
    """Test that data survives close → reopen on a real file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name

    try:
        db = BattleDB(path)
        mid = db.insert_match(p1="X", p2="Y", winner="X", loser="Y", duration=5.0)
        db.update_character_stats("X", won=True, elo_delta=10)
        db.close()

        # Reopen
        db2 = BattleDB(path)
        assert db2.count_matches() == 1
        assert db2.get_character_stats("X")["wins"] == 1
        db2.close()
    finally:
        os.unlink(path)
    print("  OK  T11: File persistence across close/reopen")


def test_sql_injection_safety():
    """Verify parameterized queries protect against injection."""
    db = get_test_db()
    evil_name = "'; DROP TABLE matches; --"
    db.insert_match(p1=evil_name, p2="Safe", winner=evil_name, loser="Safe", duration=1.0)
    # If injection worked, this would crash
    assert db.count_matches() == 1
    match = db.get_match_history(character=evil_name)
    assert len(match) == 1
    assert match[0]["p1"] == evil_name
    db.close()
    print("  OK  T12: SQL injection safety")


def test_concurrent_access():
    """Multiple inserts in quick succession shouldn't corrupt."""
    db = get_test_db()
    for i in range(100):
        db.insert_match(p1=f"P{i}", p2=f"Q{i}", winner=f"P{i}", loser=f"Q{i}",
                        duration=float(i))
    assert db.count_matches() == 100
    db.close()
    print("  OK  T13: Rapid sequential access (100 inserts)")


def test_class_winrates_query():
    db = get_test_db()
    db.insert_match(p1="A", p2="B", winner="A", loser="B",
                    p1_class="Guerreiro", p2_class="Mago")
    db.insert_match(p1="C", p2="D", winner="D", loser="C",
                    p1_class="Guerreiro", p2_class="Mago")
    rates = db.get_class_winrates()
    assert len(rates) >= 1
    db.close()
    print("  OK  T14: Class winrates aggregation")


def test_weapon_matchups_query():
    db = get_test_db()
    db.insert_match(p1="A", p2="B", winner="A", loser="B",
                    p1_weapon="Espada", p2_weapon="Arco")
    db.insert_match(p1="C", p2="D", winner="D", loser="C",
                    p1_weapon="Espada", p2_weapon="Arco")
    matchups = db.get_weapon_matchups()
    assert len(matchups) >= 1
    db.close()
    print("  OK  T15: Weapon matchups aggregation")


if __name__ == "__main__":
    tests = [
        test_schema_creation,
        test_insert_and_query_match,
        test_match_history,
        test_events,
        test_batch_events,
        test_character_stats,
        test_elo_never_negative,
        test_leaderboard,
        test_winrate,
        test_foreign_key_cascade,
        test_file_persistence,
        test_sql_injection_safety,
        test_concurrent_access,
        test_class_winrates_query,
        test_weapon_matchups_query,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1

    print(f"\n=== BattleDB Tests: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed ===")
    if failed == 0:
        print("ALL TESTS PASSED!")
    sys.exit(failed)
