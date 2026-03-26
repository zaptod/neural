"""
Tests for v14.0 Fase 2 â€” UI Visibility Features
=================================================
Tests the data layer integration used by the new UI screens.
Does NOT require a running Tk/Pygame instance.
"""
import os
import sys
import json
import shutil
import uuid
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPostFightResult(unittest.TestCase):
    """Test the post-fight result dict construction used by view_resultado."""

    def setUp(self):
        self.tmpdir = None
        self.db_path = ":memory:"

        from dados.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

        from dados.app_state import AppState
        AppState.reset()

    def tearDown(self):
        from dados.battle_db import BattleDB
        BattleDB.reset()
        if self.tmpdir:
            try:
                os.unlink(self.db_path)
            except OSError:
                pass
            try:
                os.rmdir(self.tmpdir)
            except OSError:
                pass

    def test_elo_before_after_captured(self):
        """ELO before/after values should differ after a fight."""
        from nucleo.elo_system import calculate_elo, get_tier

        # Initial: both at 1600
        self.db.ensure_character("Alpha")
        self.db.ensure_character("Beta")
        s1 = self.db.get_character_stats("Alpha")
        self.assertEqual(s1["elo"], 1600.0)

        # Simulate what view_luta does: capture before, record, capture after
        elo_before_w = self.db.get_character_stats("Alpha")["elo"]
        elo_before_l = self.db.get_character_stats("Beta")["elo"]

        delta_w, delta_l = calculate_elo(elo_before_w, elo_before_l, 0, 0, True, 15.0)
        self.db.update_character_stats("Alpha", won=True, elo_delta=delta_w,
                                       tier=get_tier(elo_before_w + delta_w))
        self.db.update_character_stats("Beta", won=False, elo_delta=delta_l,
                                       tier=get_tier(max(0, elo_before_l + delta_l)))

        elo_after_w = self.db.get_character_stats("Alpha")["elo"]
        elo_after_l = self.db.get_character_stats("Beta")["elo"]

        self.assertGreater(elo_after_w, elo_before_w)
        self.assertLess(elo_after_l, elo_before_l)

        # Build result dict like view_luta
        result = {
            "winner": "Alpha",
            "loser": "Beta",
            "winner_elo_before": elo_before_w,
            "winner_elo_after": elo_after_w,
            "loser_elo_before": elo_before_l,
            "loser_elo_after": elo_after_l,
            "winner_tier": get_tier(elo_after_w),
            "loser_tier": get_tier(elo_after_l),
            "ko_type": "KO",
            "duration": 15.0,
        }
        self.assertEqual(result["winner"], "Alpha")
        self.assertIn(result["winner_tier"], ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER"])

    def test_stats_summary_integration(self):
        """MatchStatsCollector summary should contain expected fields."""
        from dados.match_stats import MatchStatsCollector

        stats = MatchStatsCollector()
        stats.register("W")
        stats.register("L")
        stats.record_hit("W", "L", 50.0, critico=True)
        stats.record_hit("W", "L", 30.0, critico=False)
        stats.record_hit("L", "W", 20.0)
        stats.record_skill("W", "Fireball", 15.0)
        stats.record_block("L")
        stats.record_dodge("L")

        summary = stats.get_summary()

        self.assertIn("W", summary)
        self.assertIn("L", summary)

        ws = summary["W"]
        self.assertEqual(ws["hits_landed"], 2)
        self.assertEqual(ws["crits_landed"], 1)
        self.assertAlmostEqual(ws["damage_dealt"], 80.0, places=1)
        self.assertEqual(ws["skills_cast"], 1)
        self.assertAlmostEqual(ws["mana_spent"], 15.0, places=1)

        ls = summary["L"]
        self.assertEqual(ls["blocks"], 1)
        self.assertEqual(ls["dodges"], 1)
        self.assertEqual(ls["hits_landed"], 1)

    def test_empty_stats_no_crash(self):
        """PostFight screen should handle empty stats gracefully."""
        result = {
            "winner": "X", "loser": "Y",
            "winner_elo_before": 1600, "winner_elo_after": 1620,
            "loser_elo_before": 1600, "loser_elo_after": 1580,
            "winner_tier": "GOLD", "loser_tier": "SILVER",
            "ko_type": "KO", "duration": 10.0,
            "winner_stats": {}, "loser_stats": {},
        }
        # The dict should be safely consumable
        self.assertEqual(result.get("winner_stats", {}).get("damage_dealt", 0), 0)
        self.assertEqual(result.get("loser_stats", {}).get("hits_landed", 0), 0)


class TestHubDiagnosticSummary(unittest.TestCase):
    def test_resolve_archetype_review_targets(self):
        from interface.view_arquetipos import resolve_archetype_review_targets

        self.assertEqual(resolve_archetype_review_targets("arma")["targets"], ["arma"])
        self.assertEqual(resolve_archetype_review_targets("skill")["targets"], ["skill_1", "skill_2", "skill_3"])
        self.assertEqual(resolve_archetype_review_targets("ia")["targets"], ["personalidade", "classe", "arma"])
        self.assertIn("papel", resolve_archetype_review_targets("papel")["message"].lower())

    def test_resolve_visual_frame_for_headless_mode(self):
        from interface.main import resolve_visual_frame_for_headless_mode

        self.assertEqual(resolve_visual_frame_for_headless_mode("duelo"), "TelaLuta")
        self.assertEqual(resolve_visual_frame_for_headless_mode("1v1"), "TelaLuta")
        self.assertEqual(resolve_visual_frame_for_headless_mode("grupo_vs_grupo"), "TelaMultiBatalha")
        self.assertEqual(resolve_visual_frame_for_headless_mode("equipes"), "TelaMultiBatalha")
        self.assertEqual(resolve_visual_frame_for_headless_mode("grupo_vs_horda"), "TelaHorda")
        self.assertEqual(resolve_visual_frame_for_headless_mode("horda"), "TelaHorda")
        self.assertEqual(resolve_visual_frame_for_headless_mode("campanha"), "")

    def test_build_pipeline_args_for_headless_target_duelo(self):
        from interface.main import build_pipeline_args_for_headless_target

        args = build_pipeline_args_for_headless_target(
            {
                "found": True,
                "modo": "duelo",
                "cenario": "Arena",
                "team_a_members": ["Alpha"],
                "team_b_members": ["Beta"],
            }
        )
        self.assertEqual(
            args,
            [
                "pipeline",
                "--fights",
                "1",
                "--video-format",
                "classic",
                "--encounter-mode",
                "duelo",
                "--fighter1",
                "Alpha",
                "--fighter2",
                "Beta",
                "--cenario",
                "Arena",
            ],
        )

    def test_build_pipeline_args_for_headless_target_equipes(self):
        from interface.main import build_pipeline_args_for_headless_target

        args = build_pipeline_args_for_headless_target(
            {
                "found": True,
                "modo": "grupo_vs_grupo",
                "template_id": "esquadrao_balanceado_3v3",
            }
        )
        self.assertEqual(
            args,
            [
                "pipeline",
                "--fights",
                "1",
                "--video-format",
                "classic",
                "--encounter-mode",
                "equipes",
                "--template",
                "esquadrao_balanceado_3v3",
            ],
        )

    def test_build_pipeline_args_for_headless_target_horda(self):
        from interface.main import build_pipeline_args_for_headless_target

        args = build_pipeline_args_for_headless_target(
            {
                "found": True,
                "modo": "grupo_vs_horda",
                "template_id": "corredor_contra_horda",
            }
        )
        self.assertEqual(
            args,
            [
                "pipeline",
                "--fights",
                "1",
                "--video-format",
                "classic",
                "--encounter-mode",
                "horda",
                "--template",
                "corredor_contra_horda",
            ],
        )

    def test_load_latest_headless_report_summary_vazio(self):
        from interface.main import load_latest_headless_report_summary

        base_tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_tmp_ui_reports")
        os.makedirs(base_tmp, exist_ok=True)
        tmp = os.path.join(base_tmp, f"case_{uuid.uuid4().hex}")
        os.makedirs(tmp, exist_ok=True)
        try:
            resumo = load_latest_headless_report_summary(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertFalse(resumo["found"])
        self.assertIn("Nenhum", resumo["headline"])
        self.assertIn("Nenhum pacote", resumo["package_text"])

    def test_load_latest_headless_report_summary_comparativo(self):
        from interface.main import load_latest_headless_report_summary

        base_tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_tmp_ui_reports")
        os.makedirs(base_tmp, exist_ok=True)
        tmp = os.path.join(base_tmp, f"case_{uuid.uuid4().hex}")
        os.makedirs(tmp, exist_ok=True)
        try:
            older = os.path.join(tmp, "harness_tatico_grupo_vs_grupo_20260318_120000.json")
            newer = os.path.join(tmp, "harness_tatico_grupo_vs_grupo_20260318_123000.json")
            with open(older, "w", encoding="utf-8") as handle:
                json.dump({"template_id": "old", "modo": "grupo_vs_grupo", "alertas": []}, handle)
            with open(newer, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "modo": "grupo_vs_grupo",
                        "comparativo": {
                            "total_templates": 3,
                            "melhor_template": {"template_id": "esquadrao_balanceado_3v3"},
                            "pior_template": {"template_id": "dupla_tatica_2v2"},
                            "alertas_mais_comuns": {"DOMINANCIA_EXCESSIVA": 2},
                            "pacotes_impacto": [
                                {"pacote": "vanguarda_brutal", "score_saude_medio": 81.0},
                                {"pacote": "bastiao_prismatico", "score_saude_medio": 76.0},
                            ],
                            "resumo_plano_ajuste": {"areas_mais_citadas": {"composicao": 2, "ia": 1}},
                            "recomendacoes_balanceamento": [{"codigo": "REVISAR_FAMILIA_DOMINANTE"}],
                            "planos_ajuste_templates": [
                                {
                                    "template_id": "dupla_tatica_2v2",
                                    "prioridade_geral": "alta",
                                    "score_saude": 42.0,
                                    "pacote_dominante": "vanguarda_brutal",
                                    "sugestoes": [
                                        {"area": "arma", "prioridade": "alta", "alvo": "corrente"},
                                    ],
                                }
                            ],
                        },
                    },
                    handle,
                )
            resumo = load_latest_headless_report_summary(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertTrue(resumo["found"])
        self.assertIn("3 templates", resumo["headline"])
        self.assertIn("Esquadrao", resumo["subheadline"])
        self.assertEqual(resumo["status_tone"], "warning")
        self.assertIn("Dominancia", resumo["alert_text"])
        self.assertIn("Revisar Familia Dominante", resumo["recommendation_text"])
        self.assertIn("Composicao", resumo["areas_text"])
        self.assertIn("Vanguarda Brutal", resumo["package_text"])
        self.assertIn("Arma", resumo["review_axis_text"])
        self.assertIn("Pacote", resumo["review_plan_text"])
        self.assertIn("Inspecionar", resumo["inspection_title"])
        self.assertIn("Pacote", resumo["inspection_text"])
        self.assertTrue(resumo["inspection_text"])

    def test_load_latest_headless_balance_focus(self):
        from interface.headless_summary import load_latest_headless_balance_focus

        base_tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_tmp_ui_reports")
        os.makedirs(base_tmp, exist_ok=True)
        tmp = os.path.join(base_tmp, f"case_{uuid.uuid4().hex}")
        os.makedirs(tmp, exist_ok=True)
        try:
            report_file = os.path.join(tmp, "harness_tatico_grupo_vs_grupo_20260318_150000.json")
            with open(report_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "modo": "grupo_vs_grupo",
                        "comparativo": {
                            "planos_ajuste_templates": [
                                {
                                    "template_id": "dupla_tatica_2v2",
                                    "prioridade_geral": "alta",
                                    "score_saude": 42.0,
                                    "pacote_dominante": "vanguarda_brutal",
                                    "sugestoes": [
                                        {
                                            "area": "arma",
                                            "prioridade": "alta",
                                            "alvo": "corrente",
                                            "acao": "Reduzir pressao continua",
                                            "motivo": "Conversao excessiva no midrange",
                                        }
                                    ],
                                }
                            ]
                        },
                    },
                    handle,
                )
            foco = load_latest_headless_balance_focus(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertTrue(foco["found"])
        self.assertEqual(foco["template_id"], "dupla_tatica_2v2")
        self.assertEqual(foco["pacote_foco"], "vanguarda_brutal")
        self.assertEqual(foco["area"], "arma")
        self.assertEqual(foco["alvo"], "corrente")
        self.assertIn("Reduzir", foco["acao"])
        self.assertIn("Conversao", foco["motivo"])

    def test_load_latest_headless_inspection_target_comparativo(self):
        from interface.headless_summary import load_latest_headless_inspection_target

        base_tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_tmp_ui_reports")
        os.makedirs(base_tmp, exist_ok=True)
        tmp = os.path.join(base_tmp, f"case_{uuid.uuid4().hex}")
        os.makedirs(tmp, exist_ok=True)
        templates_file = os.path.join(tmp, "templates.json")
        try:
            with open(templates_file, "w", encoding="utf-8") as handle:
                json.dump({"templates": []}, handle)

            report_file = os.path.join(tmp, "harness_tatico_grupo_vs_grupo_20260318_150000.json")
            with open(report_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "modo": "grupo_vs_grupo",
                        "templates": [
                            {
                                "template_id": "dupla_tatica_2v2",
                                "modo": "grupo_vs_grupo",
                                "template_meta": {"nome": "Dupla Tatica 2v2", "cenario": "Arena"},
                                "team_a": [{"nome": "Alpha"}],
                                "team_b": [{"nome": "Beta"}],
                            }
                        ],
                        "comparativo": {
                            "planos_ajuste_templates": [
                                {
                                    "template_id": "dupla_tatica_2v2",
                                    "prioridade_geral": "alta",
                                    "score_saude": 42.0,
                                    "sugestoes": [{"area": "arma", "prioridade": "alta", "alvo": "hibrida"}],
                                }
                            ]
                        },
                    },
                    handle,
                )
            alvo = load_latest_headless_inspection_target(tmp, templates_path=templates_file)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertTrue(alvo["found"])
        self.assertEqual(alvo["modo"], "grupo_vs_grupo")
        self.assertEqual(alvo["template_id"], "dupla_tatica_2v2")
        self.assertEqual(alvo["team_a_members"], ["Alpha"])
        self.assertEqual(alvo["team_b_members"], ["Beta"])

    def test_load_latest_headless_inspection_target_horda_resolve_preset(self):
        from interface.headless_summary import load_latest_headless_inspection_target

        base_tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_tmp_ui_reports")
        os.makedirs(base_tmp, exist_ok=True)
        tmp = os.path.join(base_tmp, f"case_{uuid.uuid4().hex}")
        os.makedirs(tmp, exist_ok=True)
        templates_file = os.path.join(tmp, "templates.json")
        try:
            with open(templates_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "templates": [
                            {
                                "id": "corredor_contra_horda",
                                "modo": "grupo_vs_horda",
                                "nome": "Corredor Contra Horda",
                                "cenario": "Coliseu",
                                "horda": {"preset_id": "corredor_infectado"},
                            }
                        ]
                    },
                    handle,
                )

            report_file = os.path.join(tmp, "harness_tatico_corredor_contra_horda_20260318_150500.json")
            with open(report_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "template_id": "corredor_contra_horda",
                        "modo": "grupo_vs_horda",
                        "template_meta": {"nome": "Corredor Contra Horda", "cenario": "Coliseu"},
                        "team_a": [{"nome": "Zarya"}, {"nome": "Elda"}],
                        "pacotes": {"bastiao_prismatico": {"nome": "Bastiao Prismático", "damage_dealt": 88.0}},
                    },
                    handle,
                )
            alvo = load_latest_headless_inspection_target(tmp, templates_path=templates_file)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertTrue(alvo["found"])
        self.assertEqual(alvo["modo"], "grupo_vs_horda")
        self.assertEqual(alvo["cenario"], "Coliseu")
        self.assertEqual(alvo["horde_preset_id"], "corredor_infectado")
        self.assertEqual(alvo["pacote_foco"], "bastiao_prismatico")

    def test_load_latest_headless_archetype_focus_prefere_pacote_dominante(self):
        from interface.headless_summary import load_latest_headless_archetype_focus

        base_tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_tmp_ui_reports")
        os.makedirs(base_tmp, exist_ok=True)
        tmp = os.path.join(base_tmp, f"case_{uuid.uuid4().hex}")
        os.makedirs(tmp, exist_ok=True)
        try:
            report_file = os.path.join(tmp, "harness_tatico_grupo_vs_grupo_20260318_151000.json")
            with open(report_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "modo": "grupo_vs_grupo",
                        "templates": [
                            {
                                "template_id": "triade_astral_3v3",
                                "modo": "grupo_vs_grupo",
                                "template_meta": {"nome": "Triade Astral 3v3"},
                                "team_a": [
                                    {
                                        "nome": "Elda",
                                        "pacote_arquetipo": "bastiao_prismatico",
                                        "pacote_nome": "Bastiao Prismático",
                                    },
                                    {
                                        "nome": "Iona",
                                        "pacote_arquetipo": "artilheiro_de_orbita",
                                        "pacote_nome": "Artilheiro de Órbita",
                                    },
                                ],
                                "team_b": [
                                    {
                                        "nome": "Cassian",
                                        "arma": "Raiz do Pântano",
                                        "pacote_arquetipo": "vanguarda_brutal",
                                        "pacote_nome": "Vanguarda Brutal",
                                    }
                                ],
                                "pacotes": {
                                    "bastiao_prismatico": {"nome": "Bastiao Prismático", "damage_dealt": 120.0},
                                    "vanguarda_brutal": {"nome": "Vanguarda Brutal", "damage_dealt": 240.0},
                                },
                            }
                        ],
                        "comparativo": {
                            "planos_ajuste_templates": [
                                {
                                    "template_id": "triade_astral_3v3",
                                    "prioridade_geral": "alta",
                                    "score_saude": 38.0,
                                    "pacote_dominante": "vanguarda_brutal",
                                    "sugestoes": [{"area": "pacote", "prioridade": "alta", "alvo": "vanguarda_brutal"}],
                                }
                            ]
                        },
                    },
                    handle,
                )
            foco = load_latest_headless_archetype_focus(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertTrue(foco["found"])
        self.assertEqual(foco["template_id"], "triade_astral_3v3")
        self.assertEqual(foco["pacote_foco"], "vanguarda_brutal")
        self.assertEqual(foco["pacote_nome"], "Vanguarda Brutal")
        self.assertEqual(foco["personagem_nome"], "Cassian")
        self.assertEqual(foco["arma_nome"], "Raiz do Pântano")


class TestLeaderboardData(unittest.TestCase):
    """Test leaderboard data queries used by view_ranking."""

    def setUp(self):
        self.tmpdir = None
        self.db_path = ":memory:"

        from dados.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

    def tearDown(self):
        from dados.battle_db import BattleDB
        BattleDB.reset()
        if self.tmpdir:
            try:
                os.unlink(self.db_path)
            except OSError:
                pass
            try:
                os.rmdir(self.tmpdir)
            except OSError:
                pass

    def test_leaderboard_empty(self):
        """Leaderboard should return empty list when no data."""
        board = self.db.get_leaderboard()
        self.assertEqual(board, [])

    def test_leaderboard_ordering(self):
        """Leaderboard should be ordered by ELO descending."""
        self.db.ensure_character("Low")
        self.db.ensure_character("High")
        self.db.update_character_stats("High", won=True, elo_delta=200, tier="PLATINUM")
        self.db.update_character_stats("Low", won=False, elo_delta=-100, tier="SILVER")

        board = self.db.get_leaderboard()
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0]["name"], "High")
        self.assertEqual(board[1]["name"], "Low")
        self.assertGreater(board[0]["elo"], board[1]["elo"])

    def test_class_winrates(self):
        """Class winrates should be computed correctly."""
        self.db.insert_match(
            p1="A", p2="B", winner="A", loser="B",
            duration=10, ko_type="KO", p1_class="Guerreiro", p2_class="Mago"
        )
        self.db.insert_match(
            p1="C", p2="D", winner="C", loser="D",
            duration=15, ko_type="KO", p1_class="Guerreiro", p2_class="Mago"
        )

        rates = self.db.get_class_winrates()
        guerreiro = next((r for r in rates if "Guerreiro" in r["class_name"]), None)
        mago = next((r for r in rates if "Mago" in r["class_name"]), None)

        self.assertIsNotNone(guerreiro)
        self.assertEqual(guerreiro["total_wins"], 2)
        self.assertEqual(guerreiro["total_losses"], 0)

        self.assertIsNotNone(mago)
        self.assertEqual(mago["total_wins"], 0)
        self.assertEqual(mago["total_losses"], 2)

    def test_weapon_matchups(self):
        """Weapon matchups should track win rates."""
        self.db.insert_match(
            p1="A", p2="B", winner="A", loser="B",
            duration=10, ko_type="KO",
            p1_weapon="Espada", p2_weapon="Arco"
        )

        matchups = self.db.get_weapon_matchups()
        self.assertEqual(len(matchups), 1)
        self.assertEqual(matchups[0]["weapon_a"], "Espada")
        self.assertEqual(matchups[0]["weapon_b"], "Arco")
        self.assertAlmostEqual(matchups[0]["a_winrate"], 1.0)

    def test_match_history(self):
        """Match history should return most recent first."""
        for i in range(5):
            self.db.insert_match(
                p1=f"P{i}", p2=f"Q{i}", winner=f"P{i}", loser=f"Q{i}",
                duration=10+i, ko_type="KO"
            )

        history = self.db.get_match_history(limit=3)
        self.assertEqual(len(history), 3)
        # Most recent should be first
        self.assertEqual(history[0]["p1"], "P4")

    def test_match_history_character_filter(self):
        """Match history should filter by character name."""
        self.db.insert_match(p1="Alice", p2="Bob", winner="Alice", loser="Bob", duration=10, ko_type="KO")
        self.db.insert_match(p1="Charlie", p2="Dave", winner="Charlie", loser="Dave", duration=10, ko_type="KO")

        history = self.db.get_match_history(character="Alice")
        self.assertEqual(len(history), 1)
        self.assertIn("Alice", [history[0]["p1"], history[0]["p2"]])

    def test_summary_counts(self):
        """Summary should reflect actual counts."""
        self.db.insert_match(p1="A", p2="B", winner="A", loser="B", duration=10, ko_type="KO")
        self.db.ensure_character("A")
        self.db.ensure_character("B")

        summary = self.db.get_summary()
        self.assertEqual(summary["total_matches"], 1)
        self.assertEqual(summary["total_characters"], 2)


class TestELOInSelection(unittest.TestCase):
    """Test logic for showing ELO in character selection."""

    def setUp(self):
        self.tmpdir = None
        self.db_path = ":memory:"

        from dados.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

    def tearDown(self):
        from dados.battle_db import BattleDB
        BattleDB.reset()
        if self.tmpdir:
            try:
                os.unlink(self.db_path)
            except OSError:
                pass
            try:
                os.rmdir(self.tmpdir)
            except OSError:
                pass

    def test_elo_tag_new_character(self):
        """New character with no fights should show no ELO tag."""
        cs = self.db.get_character_stats("NewGuy")
        self.assertIsNone(cs)  # No stats = no ELO shown

    def test_elo_tag_veteran_character(self):
        """Character with fights should have ELO and tier in stats."""
        self.db.ensure_character("Veteran")
        self.db.update_character_stats("Veteran", won=True, elo_delta=50, tier="GOLD")
        self.db.update_character_stats("Veteran", won=True, elo_delta=30, tier="GOLD")
        self.db.update_character_stats("Veteran", won=False, elo_delta=-20, tier="GOLD")

        cs = self.db.get_character_stats("Veteran")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["matches_played"], 3)
        self.assertEqual(cs["wins"], 2)
        self.assertEqual(cs["losses"], 1)
        self.assertAlmostEqual(cs["elo"], 1660.0, places=1)

    def test_tier_visual_mapping(self):
        """All tiers should have visual properties defined."""
        from interface.view_resultado import TIER_VISUAL

        for tier_name, _ in [("MASTER", 2200), ("DIAMOND", 2000), ("PLATINUM", 1800),
                              ("GOLD", 1600), ("SILVER", 1400), ("BRONZE", 0)]:
            self.assertIn(tier_name, TIER_VISUAL)
            cor, emoji = TIER_VISUAL[tier_name]
            self.assertTrue(cor.startswith("#"))
            self.assertTrue(len(emoji) > 0)


class TestFormatHelpers(unittest.TestCase):
    """Test format helpers in view_resultado."""

    def test_fmt_num(self):
        from interface.view_resultado import _fmt_num
        self.assertEqual(_fmt_num(1234.56), "1,234.6")
        self.assertEqual(_fmt_num(0), "0.0")
        self.assertEqual(_fmt_num(None), "0")
        self.assertEqual(_fmt_num("abc"), "0")

    def test_fmt_pct(self):
        from interface.view_resultado import _fmt_pct
        self.assertEqual(_fmt_pct(0.756), "75.6%")
        self.assertEqual(_fmt_pct(1.0), "100.0%")
        self.assertEqual(_fmt_pct(0), "0.0%")
        self.assertEqual(_fmt_pct(None), "0.0%")


class TestTierColors(unittest.TestCase):
    """Test that tier visual constants in view_ranking match elo_system tiers."""

    def test_all_tiers_have_colors(self):
        from nucleo.elo_system import TIERS
        from interface.view_ranking import TIER_COLORS, TIER_EMOJI

        for tier_name, _ in TIERS:
            self.assertIn(tier_name, TIER_COLORS, f"Missing color for tier {tier_name}")
            self.assertIn(tier_name, TIER_EMOJI, f"Missing emoji for tier {tier_name}")


class TestSecuritySanitization(unittest.TestCase):
    """Security tests: ensure no SQL injection via character names."""

    def setUp(self):
        self.tmpdir = None
        self.db_path = ":memory:"

        from dados.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

    def tearDown(self):
        from dados.battle_db import BattleDB
        BattleDB.reset()
        if self.tmpdir:
            try:
                os.unlink(self.db_path)
            except OSError:
                pass
            try:
                os.rmdir(self.tmpdir)
            except OSError:
                pass

    def test_sql_injection_character_name(self):
        """Names with SQL special chars should be safely handled."""
        evil_name = "Robert'); DROP TABLE matches;--"
        self.db.insert_match(
            p1=evil_name, p2="Victim", winner=evil_name, loser="Victim",
            duration=10, ko_type="KO"
        )
        # Table should still exist
        count = self.db.count_matches()
        self.assertEqual(count, 1)

        # Should be retrievable
        history = self.db.get_match_history()
        self.assertEqual(history[0]["winner"], evil_name)

    def test_sql_injection_stats(self):
        """Stats queries with special chars should not crash."""
        evil = "'; DELETE FROM character_stats;--"
        self.db.ensure_character(evil)
        cs = self.db.get_character_stats(evil)
        self.assertIsNotNone(cs)
        self.assertEqual(cs["name"], evil)

    def test_xss_in_names(self):
        """HTML/script tags in names should be stored as plain text (no injection)."""
        xss_name = "<script>alert('xss')</script>"
        self.db.ensure_character(xss_name)
        cs = self.db.get_character_stats(xss_name)
        self.assertEqual(cs["name"], xss_name)


if __name__ == "__main__":
    unittest.main()

