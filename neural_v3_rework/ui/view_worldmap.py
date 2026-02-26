"""
NEURAL FIGHTS — TelaWorldMap
============================
Tela integrada do World Map dentro do launcher Tkinter.
Mostra classificação dos deuses, territórios conquistados e eventos recentes.
Permite lançar o mapa completo (pygame) como janela separada.

Atualiza automaticamente via AppState (events: territory_changed, gods_changed).
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.app_state import AppState
from data.world_bridge import WorldBridge, WORLDMAP_AVAILABLE
from ui.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING
)

# Caminho do launcher pygame
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WM_RUNNER = os.path.join(_ROOT, "RUN_WORLDMAP.py")

# Mapa de nature → cor hex legível
_NATURE_COLORS = {
    "balanced": "#00d9ff", "fire": "#ff5a14", "ice": "#a0e1ff",
    "darkness": "#8228dc", "nature": "#3cc850", "chaos": "#dc28b4",
    "void": "#2850dc", "greed": "#e6b914", "fear": "#a01edc",
    "arcane": "#7896f0", "blood": "#e61414", "ancient": "#c89728",
    "unclaimed": "#6e7873",
}


class TelaWorldMap(tk.Frame):
    """Tela integrada do God War Map."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)

        self._build_ui()

        # Subscreve no AppState para auto-refresh
        state = AppState.get()
        state.subscribe("territory_changed", self._on_update)
        state.subscribe("gods_changed",       self._on_update)
        state.subscribe("characters_changed", self._on_update)

    def _on_update(self, _data=None):
        """Callback do AppState — agenda refresh no thread da UI."""
        try:
            self.after(0, self._refresh_data)
        except Exception:
            pass

    def atualizar_dados(self):
        """Chamado pelo show_frame() do controller."""
        self._refresh_data()

    # ─── Build UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=COR_HEADER, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Button(
            header, text="◄ VOLTAR",
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO,
            font=("Arial", 10, "bold"), bd=0, padx=15,
            command=lambda: self.controller.show_frame("MenuPrincipal")
        ).pack(side="left", padx=15, pady=15)

        tk.Label(
            header, text="🌍  AETHERMOOR — GOD WAR MAP",
            font=("Arial", 18, "bold"), bg=COR_HEADER, fg=COR_TEXTO
        ).pack(side="left", padx=10)

        self._lbl_status = tk.Label(
            header, text="", font=("Arial", 10),
            bg=COR_HEADER, fg=COR_TEXTO_DIM
        )
        self._lbl_status.pack(side="right", padx=20)

        # Botão abrir mapa completo
        tk.Button(
            header, text="🗺  ABRIR MAPA COMPLETO",
            bg=COR_ACCENT, fg="white",
            font=("Arial", 10, "bold"), bd=0, padx=14, pady=6,
            command=self._launch_fullmap
        ).pack(side="right", padx=10, pady=10)

        # ── Sem WorldMap disponível ───────────────────────────────────────────
        if not WORLDMAP_AVAILABLE:
            tk.Label(
                self,
                text="⚠️  Módulo world_map_pygame/ não encontrado.\n"
                     "Certifique que a pasta existe ao lado de neural_v3_rework/.",
                font=("Arial", 13), bg=COR_BG, fg=COR_WARNING,
                justify="center"
            ).pack(expand=True)
            return

        # ── Layout principal ──────────────────────────────────────────────────
        main = tk.Frame(self, bg=COR_BG)
        main.pack(fill="both", expand=True, padx=16, pady=10)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # Coluna esquerda: ranking de deuses
        left = tk.Frame(main, bg=COR_BG_SECUNDARIO, relief="flat", bd=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            left, text="⚔  RANKING DOS DEUSES",
            font=("Arial", 14, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(pady=(12, 6), padx=16, anchor="w")

        self._frame_ranking = tk.Frame(left, bg=COR_BG_SECUNDARIO)
        self._frame_ranking.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Coluna direita: mapa de barras + eventos
        right = tk.Frame(main, bg=COR_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=2)
        right.grid_rowconfigure(1, weight=3)

        # Bar chart de territórios
        bar_frame = tk.Frame(right, bg=COR_BG_SECUNDARIO)
        bar_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        tk.Label(
            bar_frame, text="🏴  DOMÍNIO TERRITORIAL",
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(pady=(10, 4), padx=12, anchor="w")

        self._canvas_bars = tk.Canvas(
            bar_frame, bg=COR_BG_SECUNDARIO,
            highlightthickness=0, height=120
        )
        self._canvas_bars.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Eventos recentes
        evt_frame = tk.Frame(right, bg=COR_BG_SECUNDARIO)
        evt_frame.grid(row=1, column=0, sticky="nsew")

        tk.Label(
            evt_frame, text="📜  EVENTOS RECENTES",
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(pady=(10, 4), padx=12, anchor="w")

        # Scrollable events list
        events_scroll = tk.Frame(evt_frame, bg=COR_BG_SECUNDARIO)
        events_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._events_text = tk.Text(
            events_scroll,
            font=("Consolas", 9), bg="#1a2535", fg=COR_TEXTO,
            relief="flat", state="disabled", wrap="word",
            height=10
        )
        scrollbar = tk.Scrollbar(events_scroll, command=self._events_text.yview)
        self._events_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._events_text.pack(side="left", fill="both", expand=True)

        # Rodapé com totais
        footer = tk.Frame(self, bg=COR_HEADER, height=32)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self._lbl_footer = tk.Label(
            footer, text="", font=("Arial", 9),
            bg=COR_HEADER, fg=COR_TEXTO_DIM
        )
        self._lbl_footer.pack(side="left", padx=16, pady=6)

        # Primeiro refresh
        self._refresh_data()

    # ─── Refresh data ────────────────────────────────────────────────────────

    def _refresh_data(self):
        if not WORLDMAP_AVAILABLE:
            return
        try:
            bridge = WorldBridge.get()
            standings = bridge.get_god_standings()
            total_zones = bridge.get_total_zones()
            events = bridge.get_recent_events(10)

            self._render_ranking(standings, total_zones)
            self._render_bars(standings, total_zones)
            self._render_events(events)

            claimed = sum(s["territories"] for s in standings)
            self._lbl_footer.config(
                text=f"Zonas: {claimed}/{total_zones} reclamadas  ·  "
                     f"Deuses ativos: {len(standings)}"
            )
            self._lbl_status.config(text="● ao vivo")
        except Exception as e:
            self._lbl_status.config(text=f"⚠ {e}")

    def _render_ranking(self, standings: list, total_zones: int):
        # Limpa
        for w in self._frame_ranking.winfo_children():
            w.destroy()

        if not standings:
            tk.Label(
                self._frame_ranking,
                text="Nenhum deus registrado ainda.\nDispute lutas para conquistar territórios!",
                font=("Arial", 11), bg=COR_BG_SECUNDARIO,
                fg=COR_TEXTO_DIM, justify="center"
            ).pack(expand=True, pady=40)
            return

        # Cabeçalho
        hdr = tk.Frame(self._frame_ranking, bg=COR_BG_SECUNDARIO)
        hdr.pack(fill="x", pady=(0, 4))
        for text, width, anchor in [
            ("#", 2, "center"), ("Deus", 16, "w"),
            ("Natureza", 10, "w"), ("Territórios", 10, "center"),
            ("Seguidores", 10, "center"),
        ]:
            tk.Label(
                hdr, text=text, width=width, anchor=anchor,
                font=("Arial", 9, "bold"), bg=COR_BG_SECUNDARIO,
                fg=COR_TEXTO_DIM
            ).pack(side="left", padx=2)

        tk.Frame(self._frame_ranking, bg=COR_TEXTO_DIM, height=1).pack(fill="x", pady=2)

        for rank, god in enumerate(standings, 1):
            row = tk.Frame(self._frame_ranking, bg=COR_BG_SECUNDARIO)
            row.pack(fill="x", pady=1)

            nature_key = god["nature"].lower()
            color = _NATURE_COLORS.get(nature_key, "#aaaaaa")

            # Medalha para top 3
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

            tk.Label(row, text=medal, width=2, anchor="center",
                     font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
                     ).pack(side="left", padx=2)

            # Barra colorida com nome
            name_frame = tk.Frame(row, bg=color, width=4)
            name_frame.pack(side="left", fill="y", padx=(2, 0))

            tk.Label(row, text=god["god_name"][:20], width=16, anchor="w",
                     font=("Arial", 11, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
                     ).pack(side="left", padx=4)

            tk.Label(row, text=god["nature"][:10], width=10, anchor="w",
                     font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=color
                     ).pack(side="left", padx=2)

            pct = f"{god['territories']}/{total_zones}"
            tk.Label(row, text=pct, width=10, anchor="center",
                     font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
                     ).pack(side="left", padx=2)

            tk.Label(row, text=str(god["followers"]), width=10, anchor="center",
                     font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
                     ).pack(side="left", padx=2)

    def _render_bars(self, standings: list, total_zones: int):
        self._canvas_bars.delete("all")
        if not standings or total_zones == 0:
            self._canvas_bars.create_text(
                80, 50, text="Sem dados", fill=COR_TEXTO_DIM,
                font=("Arial", 10)
            )
            return

        w = self._canvas_bars.winfo_width() or 260
        h = self._canvas_bars.winfo_height() or 120
        bar_h = 18
        gap = 6
        max_t = max(s["territories"] for s in standings) or 1

        for i, god in enumerate(standings[:5]):
            y = 10 + i * (bar_h + gap)
            t = god["territories"]
            bar_w = int((t / total_zones) * (w - 100)) if total_zones else 0
            nature_key = god["nature"].lower()
            color = _NATURE_COLORS.get(nature_key, "#aaaaaa")

            # Nome
            self._canvas_bars.create_text(
                0, y + bar_h // 2,
                text=god["god_name"][:12], anchor="nw",
                fill=COR_TEXTO, font=("Arial", 8, "bold")
            )

            # Barra
            if bar_w > 0:
                self._canvas_bars.create_rectangle(
                    80, y, 80 + bar_w, y + bar_h,
                    fill=color, outline=""
                )

            # Valor
            self._canvas_bars.create_text(
                82 + bar_w + 4, y + bar_h // 2,
                text=str(t), anchor="w",
                fill=COR_TEXTO_DIM, font=("Arial", 8)
            )

    def _render_events(self, events: list):
        self._events_text.config(state="normal")
        self._events_text.delete("1.0", tk.END)

        if not events:
            self._events_text.insert(tk.END, "Nenhum evento registrado.\nInicie uma luta para ver os resultados aqui.")
        else:
            for evt in events:
                t = evt.get("type", "event")
                if t == "territory_conquered":
                    champion = evt.get("champion", "?")
                    defeated = evt.get("defeated", "?")
                    zone = evt.get("zone_id", "?").replace("_", " ").title()
                    god = evt.get("god_id", "?")
                    ts = evt.get("timestamp", "")[:16].replace("T", " ")
                    line = f"[{ts}] ⚔ {champion} derrotou {defeated}\n   🏴 {god} conquista {zone}\n\n"
                elif t == "territory_claimed":
                    zone = evt.get("territory_id", "?").replace("_", " ").title()
                    god = evt.get("god_id", "?")
                    line = f"🏴 {god} reivindica {zone}\n"
                else:
                    line = f"• {t}: {evt}\n"
                self._events_text.insert(tk.END, line)

        self._events_text.see(tk.END)
        self._events_text.config(state="disabled")

    # ─── Launch full map ─────────────────────────────────────────────────────

    def _launch_fullmap(self):
        if os.path.exists(_WM_RUNNER):
            subprocess.Popen([sys.executable, _WM_RUNNER])
        else:
            messagebox.showwarning(
                "World Map",
                f"Launcher não encontrado:\n{_WM_RUNNER}"
            )
