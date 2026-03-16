"""
NEURAL FIGHTS — Post-Fight Results Screen (v14.0 Fase 2)
==========================================================
Modal dialog shown after every fight.
Displays: winner, ELO delta, tier badge, fight stats side-by-side.
"""
import tkinter as tk
from typing import Optional

from ui.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_P1, COR_P2, COR_DANGER,
)

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
        self.geometry("720x600")
        self.minsize(600, 500)
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
        header = tk.Frame(self, bg=COR_HEADER, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        winner_tier = r.get("winner_tier", "BRONZE")
        tier_cor, tier_emoji = TIER_VISUAL.get(winner_tier, ("#cd7f32", "🥉"))

        tk.Label(
            header, text=f"🏆 VITÓRIA — {winner} 🏆",
            font=("Impact", 22), bg=COR_HEADER, fg=COR_SUCCESS,
        ).pack(pady=(10, 0))

        ko_type = r.get("ko_type", "")
        duration = r.get("duration", 0.0)
        sub_text = f"{ko_type} • {duration:.1f}s"
        tk.Label(
            header, text=sub_text,
            font=("Arial", 11), bg=COR_HEADER, fg=COR_TEXTO_DIM,
        ).pack()

        # ── Main scrollable area ───────────────────────────────────────
        canvas = tk.Canvas(self, bg=COR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="top", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=COR_BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="n")

        def _on_frame_cfg(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_cfg(event):
            canvas.itemconfig(win_id, width=event.width)

        inner.bind("<Configure>", _on_frame_cfg)
        canvas.bind("<Configure>", _on_canvas_cfg)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── ELO Section ────────────────────────────────────────────────
        elo_frame = tk.Frame(inner, bg=COR_BG_SECUNDARIO, padx=15, pady=12)
        elo_frame.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(
            elo_frame, text="⚡ ELO RATING",
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_ACCENT,
        ).pack(anchor="w")

        elo_row = tk.Frame(elo_frame, bg=COR_BG_SECUNDARIO)
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
        stats_frame = tk.Frame(inner, bg=COR_BG_SECUNDARIO, padx=15, pady=12)
        stats_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            stats_frame, text="📊 ESTATÍSTICAS DA LUTA",
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_ACCENT,
        ).pack(anchor="w")

        stats_row = tk.Frame(stats_frame, bg=COR_BG_SECUNDARIO)
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

        # Header
        tk.Label(stats_row, text=winner, font=("Arial", 10, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_P1).grid(row=0, column=0, sticky="ew", pady=2)
        tk.Label(stats_row, text="VS", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).grid(row=0, column=1, padx=10)
        tk.Label(stats_row, text=loser, font=("Arial", 10, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_P2).grid(row=0, column=2, sticky="ew", pady=2)

        for i, (label, val_w, val_l) in enumerate(stat_rows, start=1):
            bg = COR_BG if i % 2 == 0 else COR_BG_SECUNDARIO
            tk.Label(stats_row, text=val_w, font=("Consolas", 10),
                     bg=bg, fg=COR_TEXTO, anchor="e").grid(row=i, column=0, sticky="ew", pady=1, padx=5)
            tk.Label(stats_row, text=label, font=("Arial", 9),
                     bg=bg, fg=COR_TEXTO_DIM, anchor="center").grid(row=i, column=1, padx=10, pady=1)
            tk.Label(stats_row, text=val_l, font=("Consolas", 10),
                     bg=bg, fg=COR_TEXTO, anchor="w").grid(row=i, column=2, sticky="ew", pady=1, padx=5)

        # ── Continue Button ────────────────────────────────────────────
        btn_frame = tk.Frame(inner, bg=COR_BG)
        btn_frame.pack(fill="x", padx=20, pady=20)

        tk.Button(
            btn_frame, text="▶ CONTINUAR",
            font=("Arial", 14, "bold"), bg=COR_ACCENT, fg=COR_TEXTO,
            bd=0, padx=40, pady=10,
            activebackground="#c73e55", activeforeground=COR_TEXTO,
            command=self._close,
        ).pack()

    # ── ELO Card Builder ──────────────────────────────────────────────────────

    def _build_elo_card(self, parent, col: int, name: str,
                        elo_before: float, elo_after: float,
                        tier: str, is_winner: bool):
        card = tk.Frame(parent, bg=COR_BG, padx=10, pady=8)
        card.grid(row=0, column=col, sticky="nsew", padx=5)

        tier_cor, tier_emoji = TIER_VISUAL.get(tier, ("#cd7f32", "🥉"))
        name_color = COR_P1 if is_winner else COR_P2

        tk.Label(
            card, text=name, font=("Arial", 11, "bold"),
            bg=COR_BG, fg=name_color,
        ).pack()

        # Tier badge
        tk.Label(
            card, text=f"{tier_emoji} {tier}",
            font=("Arial", 10), bg=COR_BG, fg=tier_cor,
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
            font=("Arial", 11, "bold"), bg=COR_BG, fg=delta_color,
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
