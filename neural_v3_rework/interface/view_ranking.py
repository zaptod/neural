"""
NEURAL FIGHTS — Leaderboard & Rankings Screen (v14.0 Fase 2)
==============================================================
Tela de rankings acessível pelo menu principal.
Abas: Leaderboard, Winrates por Classe, Matchups de Arma, Histórico.
"""
import tkinter as tk
from tkinter import ttk

from dados.app_state import AppState
from dados.battle_db import BattleDB
from nucleo.elo_system import get_tier, get_tier_info, TIERS
from interface.ui_components import ScrollableWorkspace
from interface.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_P1, COR_P2, COR_DANGER,
)

# Tier → cor
TIER_COLORS = {
    "MASTER":   "#ff4444",
    "DIAMOND":  "#b9f2ff",
    "PLATINUM": "#e5e4e2",
    "GOLD":     "#ffd700",
    "SILVER":   "#c0c0c0",
    "BRONZE":   "#cd7f32",
}

TIER_EMOJI = {
    "MASTER": "👑", "DIAMOND": "💎", "PLATINUM": "🏆",
    "GOLD": "🥇", "SILVER": "🥈", "BRONZE": "🥉",
}


class TelaLeaderboard(tk.Frame):
    """Rankings & statistics screen accessible from the main menu."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)

        self._build_header()
        self._build_tabs()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = tk.Frame(self, bg=COR_HEADER, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Button(
            header, text="◄ VOLTAR",
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO,
            font=("Arial", 10, "bold"), bd=0, padx=15,
            command=lambda: self.controller.show_frame("MenuPrincipal"),
        ).pack(side="left", padx=15, pady=15)

        tk.Label(
            header, text="🏆 RANKINGS & ESTATÍSTICAS",
            font=("Arial", 18, "bold"), bg=COR_HEADER, fg=COR_TEXTO,
        ).pack(side="left", padx=20)

        # Summary label
        self.lbl_summary = tk.Label(
            header, text="", font=("Arial", 10),
            bg=COR_HEADER, fg=COR_TEXTO_DIM,
        )
        self.lbl_summary.pack(side="right", padx=20)

    # ── Tab System ────────────────────────────────────────────────────────────

    def _build_tabs(self):
        # Tab bar
        tab_bar = tk.Frame(self, bg=COR_BG)
        tab_bar.pack(fill="x", padx=20, pady=(10, 0))

        self._tab_frames = {}
        self._tab_buttons = {}

        tabs = [
            ("leaderboard", "🏅 Leaderboard"),
            ("classes",     "⚔️ Classes"),
            ("weapons",     "🗡️ Armas"),
            ("history",     "📜 Histórico"),
        ]

        for key, label in tabs:
            btn = tk.Button(
                tab_bar, text=label, font=("Arial", 11, "bold"),
                bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, bd=0, padx=18, pady=8,
                command=lambda k=key: self._show_tab(k),
            )
            btn.pack(side="left", padx=2)
            self._tab_buttons[key] = btn

        # Content area
        self._content = tk.Frame(self, bg=COR_BG)
        self._content.pack(fill="both", expand=True, padx=20, pady=10)

        # Build tab content frames
        self._build_leaderboard_tab()
        self._build_classes_tab()
        self._build_weapons_tab()
        self._build_history_tab()

        self._show_tab("leaderboard")

    def _show_tab(self, key: str):
        for k, f in self._tab_frames.items():
            f.pack_forget()
            self._tab_buttons[k].configure(bg=COR_BG_SECUNDARIO)
        self._tab_frames[key].pack(fill="both", expand=True)
        self._tab_buttons[key].configure(bg=COR_ACCENT)

    # ── Tab: Leaderboard ──────────────────────────────────────────────────────

    def _build_leaderboard_tab(self):
        frame = tk.Frame(self._content, bg=COR_BG)
        self._tab_frames["leaderboard"] = frame

        workspace = ScrollableWorkspace(frame, bg=COR_BG, xscroll=False, yscroll=True)
        workspace.pack(side="left", fill="both", expand=True)
        self._lb_inner = workspace.content

    def _populate_leaderboard(self):
        for w in self._lb_inner.winfo_children():
            w.destroy()

        try:
            db = BattleDB.get()
            board = db.get_leaderboard(limit=50)
        except Exception:
            board = []

        if not board:
            tk.Label(
                self._lb_inner, text="Nenhum dado ainda.\nJogue algumas lutas!",
                font=("Arial", 14), bg=COR_BG, fg=COR_TEXTO_DIM,
            ).pack(pady=50)
            return

        # Header row
        hdr = tk.Frame(self._lb_inner, bg=COR_HEADER, padx=10, pady=6)
        hdr.pack(fill="x", pady=(0, 2))
        hdr.grid_columnconfigure(1, weight=1)

        cols = [("#", 30), ("Nome", 0), ("ELO", 65), ("Tier", 80), ("W", 40), ("L", 40), ("WR%", 55)]
        for i, (text, width) in enumerate(cols):
            anchor = "w" if i == 1 else "center"
            weight = 1 if i == 1 else 0
            hdr.grid_columnconfigure(i, weight=weight, minsize=width)
            tk.Label(hdr, text=text, font=("Arial", 10, "bold"),
                     bg=COR_HEADER, fg=COR_TEXTO, anchor=anchor).grid(row=0, column=i, padx=4, sticky="ew")

        for rank, s in enumerate(board, 1):
            mp = max(s["matches_played"], 1)
            wr = s["wins"] / mp * 100
            tier = s.get("tier", "BRONZE")
            tier_cor = TIER_COLORS.get(tier, "#cd7f32")
            tier_emoji = TIER_EMOJI.get(tier, "🥉")

            bg = COR_BG_SECUNDARIO if rank % 2 == 0 else COR_BG
            row = tk.Frame(self._lb_inner, bg=bg, padx=10, pady=4)
            row.pack(fill="x")
            row.grid_columnconfigure(1, weight=1)

            for i, (_, width) in enumerate(cols):
                weight = 1 if i == 1 else 0
                row.grid_columnconfigure(i, weight=weight, minsize=width)

            # Rank
            rank_color = {1: "#ffd700", 2: "#c0c0c0", 3: "#cd7f32"}.get(rank, COR_TEXTO)
            tk.Label(row, text=str(rank), font=("Arial", 10, "bold"),
                     bg=bg, fg=rank_color, anchor="center").grid(row=0, column=0, padx=4, sticky="ew")
            # Name
            tk.Label(row, text=s["name"], font=("Arial", 10, "bold"),
                     bg=bg, fg=COR_TEXTO, anchor="w").grid(row=0, column=1, padx=4, sticky="ew")
            # ELO
            tk.Label(row, text=f"{s['elo']:.0f}", font=("Consolas", 10, "bold"),
                     bg=bg, fg=COR_SUCCESS, anchor="center").grid(row=0, column=2, padx=4, sticky="ew")
            # Tier
            tk.Label(row, text=f"{tier_emoji} {tier}", font=("Arial", 9),
                     bg=bg, fg=tier_cor, anchor="center").grid(row=0, column=3, padx=4, sticky="ew")
            # W
            tk.Label(row, text=str(s["wins"]), font=("Arial", 10),
                     bg=bg, fg=COR_SUCCESS, anchor="center").grid(row=0, column=4, padx=4, sticky="ew")
            # L
            tk.Label(row, text=str(s["losses"]), font=("Arial", 10),
                     bg=bg, fg=COR_DANGER, anchor="center").grid(row=0, column=5, padx=4, sticky="ew")
            # WR%
            wr_color = COR_SUCCESS if wr >= 50 else COR_DANGER
            tk.Label(row, text=f"{wr:.0f}%", font=("Arial", 10, "bold"),
                     bg=bg, fg=wr_color, anchor="center").grid(row=0, column=6, padx=4, sticky="ew")

    # ── Tab: Classes ──────────────────────────────────────────────────────────

    def _build_classes_tab(self):
        frame = tk.Frame(self._content, bg=COR_BG)
        self._tab_frames["classes"] = frame

        workspace = ScrollableWorkspace(frame, bg=COR_BG, xscroll=False, yscroll=True)
        workspace.pack(side="left", fill="both", expand=True)
        self._cls_inner = workspace.content

    def _populate_classes(self):
        for w in self._cls_inner.winfo_children():
            w.destroy()

        try:
            db = BattleDB.get()
            rates = db.get_class_winrates()
        except Exception:
            rates = []

        if not rates:
            tk.Label(self._cls_inner, text="Nenhum dado de classe.",
                     font=("Arial", 14), bg=COR_BG, fg=COR_TEXTO_DIM).pack(pady=50)
            return

        tk.Label(self._cls_inner, text="⚔️ TIER LIST — WINRATE POR CLASSE",
                 font=("Arial", 14, "bold"), bg=COR_BG, fg=COR_ACCENT).pack(pady=(10, 15))

        for i, r in enumerate(rates):
            wr = r["winrate"] * 100
            total = r["total_wins"] + r["total_losses"]
            bg = COR_BG_SECUNDARIO if i % 2 == 0 else COR_BG

            row = tk.Frame(self._cls_inner, bg=bg, padx=15, pady=8)
            row.pack(fill="x")
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)

            # Class name
            from interface.theme import CORES_CLASSE
            cls_cor = CORES_CLASSE.get(r["class_name"], COR_TEXTO)
            tk.Label(row, text=r["class_name"], font=("Arial", 11, "bold"),
                     bg=bg, fg=cls_cor, anchor="w").grid(row=0, column=0, sticky="w")

            # Stats
            stats_text = f"{r['total_wins']}W / {r['total_losses']}L ({total} lutas)"
            tk.Label(row, text=stats_text, font=("Arial", 9),
                     bg=bg, fg=COR_TEXTO_DIM, anchor="w").grid(row=1, column=0, sticky="w")

            # Winrate bar
            bar_frame = tk.Frame(row, bg=bg)
            bar_frame.grid(row=0, column=1, rowspan=2, padx=(20, 0), sticky="e")

            wr_color = COR_SUCCESS if wr >= 50 else COR_DANGER
            tk.Label(bar_frame, text=f"{wr:.1f}%", font=("Consolas", 14, "bold"),
                     bg=bg, fg=wr_color).pack(side="right")

    # ── Tab: Weapons ──────────────────────────────────────────────────────────

    def _build_weapons_tab(self):
        frame = tk.Frame(self._content, bg=COR_BG)
        self._tab_frames["weapons"] = frame

        workspace = ScrollableWorkspace(frame, bg=COR_BG, xscroll=False, yscroll=True)
        workspace.pack(side="left", fill="both", expand=True)
        self._wpn_inner = workspace.content

    def _populate_weapons(self):
        for w in self._wpn_inner.winfo_children():
            w.destroy()

        try:
            db = BattleDB.get()
            matchups = db.get_weapon_matchups()
        except Exception:
            matchups = []

        if not matchups:
            tk.Label(self._wpn_inner, text="Nenhum dado de armas.",
                     font=("Arial", 14), bg=COR_BG, fg=COR_TEXTO_DIM).pack(pady=50)
            return

        tk.Label(self._wpn_inner, text="🗡️ MATCHUPS DE ARMA — A vs B",
                 font=("Arial", 14, "bold"), bg=COR_BG, fg=COR_ACCENT).pack(pady=(10, 15))

        # Header
        hdr = tk.Frame(self._wpn_inner, bg=COR_HEADER, padx=10, pady=6)
        hdr.pack(fill="x", pady=(0, 2))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_columnconfigure(1, weight=1)

        for i, text in enumerate(["Arma A", "Arma B", "Lutas", "WR A", "WR B"]):
            w = 1 if i < 2 else 0
            hdr.grid_columnconfigure(i, weight=w, minsize=60)
            tk.Label(hdr, text=text, font=("Arial", 10, "bold"),
                     bg=COR_HEADER, fg=COR_TEXTO).grid(row=0, column=i, padx=4, sticky="ew")

        for idx, m in enumerate(matchups):
            bg = COR_BG_SECUNDARIO if idx % 2 == 0 else COR_BG
            a_wr = m["a_winrate"] * 100
            b_wr = (1 - m["a_winrate"]) * 100

            row = tk.Frame(self._wpn_inner, bg=bg, padx=10, pady=4)
            row.pack(fill="x")
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=1)

            tk.Label(row, text=m["weapon_a"], font=("Arial", 10, "bold"),
                     bg=bg, fg=COR_TEXTO, anchor="w").grid(row=0, column=0, padx=4, sticky="ew")
            tk.Label(row, text=m["weapon_b"], font=("Arial", 10, "bold"),
                     bg=bg, fg=COR_TEXTO, anchor="w").grid(row=0, column=1, padx=4, sticky="ew")
            tk.Label(row, text=str(m["total"]), font=("Arial", 10),
                     bg=bg, fg=COR_TEXTO_DIM).grid(row=0, column=2, padx=4)
            
            a_color = COR_SUCCESS if a_wr >= 50 else COR_DANGER
            tk.Label(row, text=f"{a_wr:.0f}%", font=("Consolas", 10, "bold"),
                     bg=bg, fg=a_color).grid(row=0, column=3, padx=4)
            b_color = COR_SUCCESS if b_wr >= 50 else COR_DANGER
            tk.Label(row, text=f"{b_wr:.0f}%", font=("Consolas", 10, "bold"),
                     bg=bg, fg=b_color).grid(row=0, column=4, padx=4)

    # ── Tab: History ──────────────────────────────────────────────────────────

    def _build_history_tab(self):
        frame = tk.Frame(self._content, bg=COR_BG)
        self._tab_frames["history"] = frame

        workspace = ScrollableWorkspace(frame, bg=COR_BG, xscroll=False, yscroll=True)
        workspace.pack(side="left", fill="both", expand=True)
        self._hist_inner = workspace.content

    def _populate_history(self):
        for w in self._hist_inner.winfo_children():
            w.destroy()

        try:
            db = BattleDB.get()
            matches = db.get_match_history(limit=50)
        except Exception:
            matches = []

        if not matches:
            tk.Label(self._hist_inner, text="Nenhuma luta registrada.",
                     font=("Arial", 14), bg=COR_BG, fg=COR_TEXTO_DIM).pack(pady=50)
            return

        tk.Label(self._hist_inner, text="📜 ÚLTIMAS LUTAS",
                 font=("Arial", 14, "bold"), bg=COR_BG, fg=COR_ACCENT).pack(pady=(10, 15))

        for idx, m in enumerate(matches):
            bg = COR_BG_SECUNDARIO if idx % 2 == 0 else COR_BG
            row = tk.Frame(self._hist_inner, bg=bg, padx=12, pady=6)
            row.pack(fill="x")
            row.grid_columnconfigure(1, weight=1)

            # Date
            date_str = m.get("created_at", "")[:16]
            tk.Label(row, text=date_str, font=("Arial", 8),
                     bg=bg, fg=COR_TEXTO_DIM, anchor="w").grid(row=0, column=0, padx=(0, 10), sticky="w")

            # Match text
            winner = m["winner"]
            loser = m["loser"]
            ko = m.get("ko_type", "")
            dur = m.get("duration", 0)

            match_text = f"🏆 {winner}  vs  {loser}"
            tk.Label(row, text=match_text, font=("Arial", 10, "bold"),
                     bg=bg, fg=COR_TEXTO, anchor="w").grid(row=0, column=1, sticky="w")

            # Details
            details = f"{ko} • {dur:.1f}s"
            tk.Label(row, text=details, font=("Arial", 9),
                     bg=bg, fg=COR_TEXTO_DIM).grid(row=0, column=2, padx=10)

            # ELO deltas
            w_before = m.get("p1_elo_before", 0)
            w_after = m.get("p1_elo_after", 0)
            if m["winner"] == m["p1"]:
                w_before = m.get("p1_elo_before", 0)
                w_after = m.get("p1_elo_after", 0)
            else:
                w_before = m.get("p2_elo_before", 0)
                w_after = m.get("p2_elo_after", 0)

            delta = w_after - w_before
            sign = "+" if delta >= 0 else ""
            d_color = COR_SUCCESS if delta >= 0 else COR_DANGER
            tk.Label(row, text=f"{sign}{delta:.1f}", font=("Consolas", 10, "bold"),
                     bg=bg, fg=d_color).grid(row=0, column=3, padx=5)

    # ── Refresh data (called when screen is shown) ────────────────────────────

    def atualizar_dados(self):
        """Refresh all tabs with current DB data."""
        try:
            db = BattleDB.get()
            summary = db.get_summary()
            self.lbl_summary.config(
                text=f"💾 {summary['total_matches']} lutas • {summary['total_characters']} lutadores"
            )
        except Exception:
            self.lbl_summary.config(text="")

        self._populate_leaderboard()
        self._populate_classes()
        self._populate_weapons()
        self._populate_history()

