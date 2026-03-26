"""
NEURAL FIGHTS — Post-Fight Results Screen (v14.0 Fase 2)
==========================================================
Modal dialog shown after every fight.
Displays: winner, ELO delta, tier badge, fight stats side-by-side.
"""
import tkinter as tk
from typing import Optional

from interface.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_P1, COR_P2, COR_DANGER,
    COR_BG_CARD, COR_BORDA, COR_TEXTO_SUB,
)
from interface.ui_components import ScrollableWorkspace, UICard, make_primary_button

# Tier → (cor, emoji)
TIER_VISUAL = {
    "MASTER":   ("#ff4444", "👑"),
    "DIAMOND":  ("#b9f2ff", "💎"),
    "PLATINUM": ("#e5e4e2", "🏆"),
    "GOLD":     ("#ffd700", "🥇"),
    "SILVER":   ("#c0c0c0", "🥈"),
    "BRONZE":   ("#cd7f32", "🥉"),
}


class PostFightScreen(tk.Toplevel):
    """
    Modal popup that shows post-fight results.

    Parameters
    ----------
    parent : tk widget
    result : dict with keys:
        winner, loser,
        winner_elo_before, winner_elo_after, winner_tier,
        loser_elo_before, loser_elo_after, loser_tier,
        duration, ko_type,
        winner_stats (dict), loser_stats (dict)  — from MatchStatsCollector.get_summary()
    on_close : callable (optional) — called when user clicks "Continuar"
    """

    def __init__(self, parent, result: dict, on_close=None):
        super().__init__(parent)
        self._result = result
        self._on_close = on_close

        self.title("Resultado da Luta")
        self.geometry("840x680")
        self.minsize(680, 560)
        self.configure(bg=COR_BG)
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build_ui()

        # Center on parent
        self.update_idletasks()
        if parent.winfo_exists():
            x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _close(self):
        self.grab_release()
        self.destroy()
        if self._on_close:
            self._on_close()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        r = self._result
        winner = r.get("winner", "???")
        loser = r.get("loser", "???")

        # ── Header: WINNER banner ──────────────────────────────────────
        header = tk.Frame(self, bg=COR_HEADER, height=96)
        header.pack(fill="x")
        header.pack_propagate(False)

        winner_tier = r.get("winner_tier", "BRONZE")
        tier_cor, tier_emoji = TIER_VISUAL.get(winner_tier, ("#cd7f32", "🥉"))

        tk.Label(
            header, text=f"🏆 VITÓRIA — {winner} 🏆",
            font=("Bahnschrift SemiBold", 24), bg=COR_HEADER, fg=COR_SUCCESS,
        ).pack(pady=(10, 0))

        ko_type = r.get("ko_type", "")
        duration = r.get("duration", 0.0)
        sub_text = f"{ko_type} • {duration:.1f}s"
        tk.Label(
            header, text=sub_text,
            font=("Segoe UI", 11), bg=COR_HEADER, fg=COR_TEXTO_SUB,
        ).pack()

        # ── Main scrollable area ───────────────────────────────────────
        workspace = ScrollableWorkspace(self, bg=COR_BG, xscroll=False, yscroll=True)
        workspace.pack(side="top", fill="both", expand=True)
        inner = workspace.content

        # ── ELO Section ────────────────────────────────────────────────
        elo_frame = UICard(inner, bg=COR_BG_CARD, border=COR_BORDA, padx=15, pady=14)
        elo_frame.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(
            elo_frame, text="⚡ ELO RATING",
            font=("Segoe UI", 12, "bold"), bg=COR_BG_CARD, fg=COR_ACCENT,
        ).pack(anchor="w")

        elo_row = tk.Frame(elo_frame, bg=COR_BG_CARD)
        elo_row.pack(fill="x", pady=5)
        elo_row.grid_columnconfigure(0, weight=1)
        elo_row.grid_columnconfigure(1, weight=1)

        # Winner ELO
        self._build_elo_card(
            elo_row, col=0, name=winner,
            elo_before=r.get("winner_elo_before", 1600),
            elo_after=r.get("winner_elo_after", 1600),
            tier=winner_tier, is_winner=True,
        )

        # Loser ELO
        loser_tier = r.get("loser_tier", "BRONZE")
        self._build_elo_card(
            elo_row, col=1, name=loser,
            elo_before=r.get("loser_elo_before", 1600),
            elo_after=r.get("loser_elo_after", 1600),
            tier=loser_tier, is_winner=False,
        )

        # ── Stats Section (side-by-side) ───────────────────────────────
        stats_frame = UICard(inner, bg=COR_BG_CARD, border=COR_BORDA, padx=15, pady=14)
        stats_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            stats_frame, text="📊 ESTATÍSTICAS DA LUTA",
            font=("Segoe UI", 12, "bold"), bg=COR_BG_CARD, fg=COR_ACCENT,
        ).pack(anchor="w")

        stats_row = tk.Frame(stats_frame, bg=COR_BG_CARD)
        stats_row.pack(fill="x", pady=5)
        stats_row.grid_columnconfigure(0, weight=1)
        stats_row.grid_columnconfigure(1, weight=0)
        stats_row.grid_columnconfigure(2, weight=1)

        w_stats = r.get("winner_stats") or {}
        l_stats = r.get("loser_stats") or {}

        stat_rows = [
            ("Dano Total",     _fmt_num(w_stats.get("damage_dealt", 0)),    _fmt_num(l_stats.get("damage_dealt", 0))),
            ("Hits Acertados", str(w_stats.get("hits_landed", 0)),          str(l_stats.get("hits_landed", 0))),
            ("Precisão",       _fmt_pct(w_stats.get("accuracy", 0)),        _fmt_pct(l_stats.get("accuracy", 0))),
            ("Críticos",       str(w_stats.get("crits_landed", 0)),         str(l_stats.get("crits_landed", 0))),
            ("Max Combo",      str(w_stats.get("max_combo", 0)),            str(l_stats.get("max_combo", 0))),
            ("DPS",            _fmt_num(w_stats.get("dps", 0)),             _fmt_num(l_stats.get("dps", 0))),
            ("Skills Usadas",  str(w_stats.get("skills_cast", 0)),          str(l_stats.get("skills_cast", 0))),
            ("Mana Gasta",     _fmt_num(w_stats.get("mana_spent", 0)),      _fmt_num(l_stats.get("mana_spent", 0))),
            ("Bloqueios",      str(w_stats.get("blocks", 0)),               str(l_stats.get("blocks", 0))),
            ("Esquivas",       str(w_stats.get("dodges", 0)),               str(l_stats.get("dodges", 0))),
        ]

        dano_especial_w = (
            w_stats.get("summon_damage", 0) +
            w_stats.get("trap_damage", 0) +
            w_stats.get("status_damage", 0)
        )
        dano_especial_l = (
            l_stats.get("summon_damage", 0) +
            l_stats.get("trap_damage", 0) +
            l_stats.get("status_damage", 0)
        )
        hits_especiais_w = (
            w_stats.get("summon_hits", 0) +
            w_stats.get("trap_hits", 0) +
            w_stats.get("status_hits", 0)
        )
        hits_especiais_l = (
            l_stats.get("summon_hits", 0) +
            l_stats.get("trap_hits", 0) +
            l_stats.get("status_hits", 0)
        )
        stat_rows = [
            stat_rows[0],
            ("Dano de Arma",   _fmt_num(w_stats.get("weapon_damage", 0)),   _fmt_num(l_stats.get("weapon_damage", 0))),
            ("Dano de Skill",  _fmt_num(w_stats.get("skill_damage", 0)),    _fmt_num(l_stats.get("skill_damage", 0))),
            ("Dano Especial",  _fmt_num(dano_especial_w),                   _fmt_num(dano_especial_l)),
            ("Hits Totais",    str(w_stats.get("hits_landed", 0)),          str(l_stats.get("hits_landed", 0))),
            ("Hits de Arma",   str(w_stats.get("weapon_hits", 0)),          str(l_stats.get("weapon_hits", 0))),
            ("Hits de Skill",  str(w_stats.get("skill_hits", 0)),           str(l_stats.get("skill_hits", 0))),
            ("Hits Especiais", str(hits_especiais_w),                       str(hits_especiais_l)),
            *stat_rows[2:],
        ]

        # Header
        tk.Label(stats_row, text=winner, font=("Segoe UI", 10, "bold"),
                 bg=COR_BG_CARD, fg=COR_P1).grid(row=0, column=0, sticky="ew", pady=2)
        tk.Label(stats_row, text="VS", font=("Segoe UI", 9, "bold"),
                 bg=COR_BG_CARD, fg=COR_TEXTO_DIM).grid(row=0, column=1, padx=10)
        tk.Label(stats_row, text=loser, font=("Segoe UI", 10, "bold"),
                 bg=COR_BG_CARD, fg=COR_P2).grid(row=0, column=2, sticky="ew", pady=2)

        for i, (label, val_w, val_l) in enumerate(stat_rows, start=1):
            bg = COR_BG if i % 2 == 0 else COR_BG_CARD
            tk.Label(stats_row, text=val_w, font=("Consolas", 10),
                     bg=bg, fg=COR_TEXTO, anchor="e").grid(row=i, column=0, sticky="ew", pady=1, padx=5)
            tk.Label(stats_row, text=label, font=("Segoe UI", 9),
                     bg=bg, fg=COR_TEXTO_DIM, anchor="center").grid(row=i, column=1, padx=10, pady=1)
            tk.Label(stats_row, text=val_l, font=("Consolas", 10),
                     bg=bg, fg=COR_TEXTO, anchor="w").grid(row=i, column=2, sticky="ew", pady=1, padx=5)

        # ── Continue Button ────────────────────────────────────────────
        btn_frame = tk.Frame(inner, bg=COR_BG)
        btn_frame.pack(fill="x", padx=20, pady=20)

        make_primary_button(
            btn_frame,
            "▶ CONTINUAR",
            self._close,
            bg=COR_ACCENT,
            fg=COR_TEXTO,
            font=("Bahnschrift SemiBold", 14),
            padx=42,
            pady=12,
            activebackground="#c73e55",
            activeforeground=COR_TEXTO,
        ).pack()

    # ── ELO Card Builder ──────────────────────────────────────────────────────

    def _build_elo_card(self, parent, col: int, name: str,
                        elo_before: float, elo_after: float,
                        tier: str, is_winner: bool):
        card = UICard(parent, bg=COR_BG, border=COR_BORDA, padx=12, pady=10)
        card.grid(row=0, column=col, sticky="nsew", padx=5)

        tier_cor, tier_emoji = TIER_VISUAL.get(tier, ("#cd7f32", "🥉"))
        name_color = COR_P1 if is_winner else COR_P2

        tk.Label(
            card, text=name, font=("Segoe UI", 11, "bold"),
            bg=COR_BG, fg=name_color,
        ).pack()

        # Tier badge
        tk.Label(
            card, text=f"{tier_emoji} {tier}",
            font=("Segoe UI", 10), bg=COR_BG, fg=tier_cor,
        ).pack()

        # ELO transition
        delta = elo_after - elo_before
        if delta >= 0:
            arrow = "▲"
            delta_color = COR_SUCCESS
            sign = "+"
        else:
            arrow = "▼"
            delta_color = COR_DANGER
            sign = ""

        tk.Label(
            card, text=f"{elo_before:.0f} → {elo_after:.0f}",
            font=("Consolas", 12, "bold"), bg=COR_BG, fg=COR_TEXTO,
        ).pack()

        tk.Label(
            card, text=f"{arrow} {sign}{delta:.1f}",
            font=("Segoe UI", 11, "bold"), bg=COR_BG, fg=delta_color,
        ).pack()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_num(val) -> str:
    try:
        return f"{float(val):,.1f}"
    except (ValueError, TypeError):
        return "0"


def _fmt_pct(val) -> str:
    try:
        return f"{float(val) * 100:.1f}%"
    except (ValueError, TypeError):
        return "0.0%"


def show_post_fight(parent, result: dict, on_close=None):
    """Convenience function to show the post-fight screen."""
    PostFightScreen(parent, result, on_close)

