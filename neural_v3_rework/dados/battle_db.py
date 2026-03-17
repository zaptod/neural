"""
NEURAL FIGHTS â€” Battle Database (SQLite)
==========================================
Persistent storage for match history, combat events, and character statistics.
Foundation layer for: ELO system, Replay, Balance analysis.

Usage:
    from dados.battle_db import BattleDB
    db = BattleDB()

    # Record a match
    match_id = db.insert_match(
        p1="Caleb", p2="Bjorn", winner="Caleb", loser="Bjorn",
        duration=23.5, ko_type="KO", arena="Arena PadrÃ£o"
    )

    # Record combat events within a match
    db.insert_event(match_id, frame=120, event_type="hit",
                    data={"attacker": "Caleb", "damage": 15.3})

    # Update character stats
    db.update_character_stats("Caleb", won=True, elo_delta=+16.5)

    # Query
    history = db.get_match_history(limit=50)
    stats   = db.get_character_stats("Caleb")
"""

import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("battle_db")

# â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "battle_log.db")

# â”€â”€ Schema version â€” bump when tables change â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SCHEMA_VERSION = 1


class BattleDB:
    """Thread-safe SQLite wrapper for battle persistence."""

    _instance: "BattleDB | None" = None

    @classmethod
    def get(cls) -> "BattleDB":
        """Singleton access â€” reuses a single instance across the app."""
        if cls._instance is None:
            cls._instance = cls(DB_PATH)
        return cls._instance

    @classmethod
    def reset(cls):
        """Destroy singleton (for tests)."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None

    # â”€â”€ Init â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_connection()
        self._ensure_schema()

    # â”€â”€ Connection management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _ensure_connection(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")

    @contextmanager
    def _cursor(self):
        """Yields a cursor inside a transaction. Commits on success, rolls back on error."""
        self._ensure_connection()
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # â”€â”€ Schema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _ensure_schema(self):
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)
            row = cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            current = row["version"] if row else 0

            if current < 1:
                self._create_v1(cur)
                cur.execute("DELETE FROM schema_version")
                cur.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

    def _create_v1(self, cur: sqlite3.Cursor):
        """Version 1 schema â€” core tables."""
        cur.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                p1          TEXT    NOT NULL,
                p2          TEXT    NOT NULL,
                winner      TEXT    NOT NULL,
                loser       TEXT    NOT NULL,
                duration    REAL    NOT NULL DEFAULT 0.0,
                ko_type     TEXT    NOT NULL DEFAULT '',
                arena       TEXT    NOT NULL DEFAULT '',
                p1_class    TEXT    NOT NULL DEFAULT '',
                p2_class    TEXT    NOT NULL DEFAULT '',
                p1_weapon   TEXT    NOT NULL DEFAULT '',
                p2_weapon   TEXT    NOT NULL DEFAULT '',
                p1_elo_before REAL  NOT NULL DEFAULT 1600.0,
                p2_elo_before REAL  NOT NULL DEFAULT 1600.0,
                p1_elo_after  REAL  NOT NULL DEFAULT 1600.0,
                p2_elo_after  REAL  NOT NULL DEFAULT 1600.0,
                tournament_id TEXT  DEFAULT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS match_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id    INTEGER NOT NULL,
                frame       INTEGER NOT NULL DEFAULT 0,
                event_type  TEXT    NOT NULL,
                data_json   TEXT    NOT NULL DEFAULT '{}',
                FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS character_stats (
                name            TEXT PRIMARY KEY,
                wins            INTEGER NOT NULL DEFAULT 0,
                losses          INTEGER NOT NULL DEFAULT 0,
                elo             REAL    NOT NULL DEFAULT 1600.0,
                peak_elo        REAL    NOT NULL DEFAULT 1600.0,
                matches_played  INTEGER NOT NULL DEFAULT 0,
                total_damage    REAL    NOT NULL DEFAULT 0.0,
                total_kills     INTEGER NOT NULL DEFAULT 0,
                tier            TEXT    NOT NULL DEFAULT 'BRONZE',
                last_updated    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # Indexes for common queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matches_loser ON matches(loser)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matches_created ON matches(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_match ON match_events(match_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON match_events(event_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_stats_elo ON character_stats(elo DESC)")

        _log.info("Battle DB schema v1 created at %s", self._db_path)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MATCHES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def insert_match(self, p1: str, p2: str, winner: str, loser: str,
                     duration: float = 0.0, ko_type: str = "",
                     arena: str = "", p1_class: str = "", p2_class: str = "",
                     p1_weapon: str = "", p2_weapon: str = "",
                     p1_elo_before: float = 1600.0, p2_elo_before: float = 1600.0,
                     p1_elo_after: float = 1600.0, p2_elo_after: float = 1600.0,
                     tournament_id: str = None) -> int:
        """Insert a completed match. Returns the match ID."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO matches
                    (p1, p2, winner, loser, duration, ko_type, arena,
                     p1_class, p2_class, p1_weapon, p2_weapon,
                     p1_elo_before, p2_elo_before, p1_elo_after, p2_elo_after,
                     tournament_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (p1, p2, winner, loser, duration, ko_type, arena,
                  p1_class, p2_class, p1_weapon, p2_weapon,
                  p1_elo_before, p2_elo_before, p1_elo_after, p2_elo_after,
                  tournament_id))
            return cur.lastrowid

    def get_match(self, match_id: int) -> Optional[Dict]:
        """Get a single match by ID."""
        self._ensure_connection()
        row = self._conn.execute(
            "SELECT * FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_match_history(self, limit: int = 50, offset: int = 0,
                          character: str = None) -> List[Dict]:
        """Get recent matches, optionally filtered by character name."""
        self._ensure_connection()
        if character:
            rows = self._conn.execute(
                """SELECT * FROM matches
                   WHERE p1 = ? OR p2 = ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (character, character, limit, offset)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM matches ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows]

    def count_matches(self) -> int:
        self._ensure_connection()
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM matches").fetchone()
        return row["cnt"]

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MATCH EVENTS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def insert_event(self, match_id: int, frame: int, event_type: str,
                     data: Dict = None) -> int:
        """Insert a single combat event within a match."""
        json_str = json.dumps(data or {}, ensure_ascii=False)
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO match_events (match_id, frame, event_type, data_json)
                VALUES (?,?,?,?)
            """, (match_id, frame, event_type, json_str))
            return cur.lastrowid

    def insert_events_batch(self, events: List[Tuple[int, int, str, Dict]]):
        """Batch insert events: [(match_id, frame, event_type, data), ...]."""
        with self._cursor() as cur:
            cur.executemany("""
                INSERT INTO match_events (match_id, frame, event_type, data_json)
                VALUES (?,?,?,?)
            """, [
                (mid, frame, etype, json.dumps(data or {}, ensure_ascii=False))
                for mid, frame, etype, data in events
            ])

    def get_events(self, match_id: int, event_type: str = None) -> List[Dict]:
        """Get events for a match, optionally filtered by type."""
        self._ensure_connection()
        if event_type:
            rows = self._conn.execute(
                """SELECT * FROM match_events
                   WHERE match_id = ? AND event_type = ?
                   ORDER BY frame""",
                (match_id, event_type)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM match_events WHERE match_id = ? ORDER BY frame",
                (match_id,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d.pop("data_json"))
            result.append(d)
        return result

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # CHARACTER STATS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def ensure_character(self, name: str):
        """Create a character_stats row if it doesn't exist."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT OR IGNORE INTO character_stats (name) VALUES (?)
            """, (name,))

    def update_character_stats(self, name: str, won: bool,
                               elo_delta: float = 0.0, damage: float = 0.0,
                               tier: str = None):
        """Update character stats after a match."""
        self.ensure_character(name)
        with self._cursor() as cur:
            if won:
                cur.execute("""
                    UPDATE character_stats SET
                        wins = wins + 1,
                        matches_played = matches_played + 1,
                        elo = elo + ?,
                        peak_elo = MAX(peak_elo, elo + ?),
                        total_damage = total_damage + ?,
                        total_kills = total_kills + 1,
                        tier = COALESCE(?, tier),
                        last_updated = datetime('now','localtime')
                    WHERE name = ?
                """, (elo_delta, elo_delta, damage, tier, name))
            else:
                cur.execute("""
                    UPDATE character_stats SET
                        losses = losses + 1,
                        matches_played = matches_played + 1,
                        elo = MAX(0, elo + ?),
                        total_damage = total_damage + ?,
                        tier = COALESCE(?, tier),
                        last_updated = datetime('now','localtime')
                    WHERE name = ?
                """, (elo_delta, damage, tier, name))

    def get_character_stats(self, name: str) -> Optional[Dict]:
        """Get stats for a single character."""
        self._ensure_connection()
        row = self._conn.execute(
            "SELECT * FROM character_stats WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def get_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Top characters by ELO."""
        self._ensure_connection()
        rows = self._conn.execute(
            "SELECT * FROM character_stats ORDER BY elo DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_character_stats(self) -> List[Dict]:
        """All character stats ordered by ELO."""
        self._ensure_connection()
        rows = self._conn.execute(
            "SELECT * FROM character_stats ORDER BY elo DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_winrate(self, name: str) -> float:
        """Win percentage for a character (0.0 to 1.0)."""
        stats = self.get_character_stats(name)
        if not stats or stats["matches_played"] == 0:
            return 0.0
        return stats["wins"] / stats["matches_played"]

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # AGGREGATION QUERIES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def get_class_winrates(self) -> List[Dict]:
        """Win rates grouped by character class."""
        self._ensure_connection()
        rows = self._conn.execute("""
            SELECT
                class_name,
                SUM(wins) as total_wins,
                SUM(losses) as total_losses,
                ROUND(CAST(SUM(wins) AS REAL) / MAX(SUM(wins) + SUM(losses), 1), 3) as winrate
            FROM (
                SELECT p1_class as class_name, 
                       CASE WHEN winner = p1 THEN 1 ELSE 0 END as wins,
                       CASE WHEN winner != p1 THEN 1 ELSE 0 END as losses
                FROM matches WHERE p1_class != ''
                UNION ALL
                SELECT p2_class as class_name,
                       CASE WHEN winner = p2 THEN 1 ELSE 0 END as wins,
                       CASE WHEN winner != p2 THEN 1 ELSE 0 END as losses
                FROM matches WHERE p2_class != ''
            )
            GROUP BY class_name
            ORDER BY winrate DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def get_weapon_matchups(self) -> List[Dict]:
        """Win rates for weapon-vs-weapon matchups."""
        self._ensure_connection()
        rows = self._conn.execute("""
            SELECT
                p1_weapon as weapon_a,
                p2_weapon as weapon_b,
                COUNT(*) as total,
                SUM(CASE WHEN winner = p1 THEN 1 ELSE 0 END) as a_wins,
                SUM(CASE WHEN winner = p2 THEN 1 ELSE 0 END) as b_wins,
                ROUND(CAST(SUM(CASE WHEN winner = p1 THEN 1 ELSE 0 END) AS REAL) / MAX(COUNT(*), 1), 3) as a_winrate
            FROM matches
            WHERE p1_weapon != '' AND p2_weapon != ''
            GROUP BY p1_weapon, p2_weapon
            ORDER BY total DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self) -> Dict:
        """Overall database summary."""
        self._ensure_connection()
        m = self._conn.execute("SELECT COUNT(*) as cnt FROM matches").fetchone()
        e = self._conn.execute("SELECT COUNT(*) as cnt FROM match_events").fetchone()
        c = self._conn.execute("SELECT COUNT(*) as cnt FROM character_stats").fetchone()
        return {
            "total_matches": m["cnt"],
            "total_events": e["cnt"],
            "total_characters": c["cnt"],
        }

