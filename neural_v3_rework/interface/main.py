# main.py - Neural Fights Launcher
import json
import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox

_log = logging.getLogger("interface.main")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dados.app_state import AppState

# World map root
_WM_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "world_map_pygame",
)
_WM_RUNNER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "RUN_WORLDMAP.py",
)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPEIS_TATICOS_PATH = os.path.join(ROOT_DIR, "dados", "papeis_taticos.json")
PLANO_TESTES_PATH = os.path.join(ROOT_DIR, "dados", "plano_testes_taticos.json")
PLANO_TATICO_MD_PATH = os.path.join(ROOT_DIR, "documentacao", "plano_balanceamento_tatico.md")

COR_BG = "#09111f"
COR_BG_ALT = "#0f1b31"
COR_CARD = "#12233f"
COR_CARD_SOFT = "#162b4b"
COR_BORDER = "#274b75"
COR_HERO = "#173b69"
COR_ACCENT = "#ff6b57"
COR_ACCENT_ALT = "#35d6ff"
COR_SUCCESS = "#7fffd4"
COR_WARNING = "#f5c451"
COR_TEXT = "#f5f7fb"
COR_TEXT_DIM = "#9fb1c9"


def _setup_worldmap_hook():
    try:
        from dados.world_bridge import WorldBridge

        WorldBridge.get()
    except Exception:
        pass


_setup_worldmap_hook()

from interface.view_armas import TelaArmas
from interface.view_chars import TelaPersonagens
from interface.view_luta import TelaLuta
from interface.view_multi import TelaMultiBatalha
from interface.view_ranking import TelaLeaderboard
from interface.view_sons import TelaSons
from interface.view_worldmap import TelaWorldMap


def _load_json_count(path, key):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        value = data.get(key, [])
        return len(value) if isinstance(value, list) else 0
    except Exception:
        return 0


class DashboardCard(tk.Frame):
    def __init__(self, parent, accent, title, description, pills, primary_text, primary_command, secondary=None):
        super().__init__(
            parent,
            bg=COR_CARD,
            highlightthickness=1,
            highlightbackground=COR_BORDER,
            highlightcolor=COR_BORDER,
            bd=0,
        )
        self.grid_propagate(False)
        self.configure(height=226)

        top = tk.Frame(self, bg=COR_CARD)
        top.pack(fill="x", padx=18, pady=(16, 10))

        tk.Frame(top, bg=accent, width=44, height=6).pack(anchor="w")
        tk.Label(
            top,
            text=title,
            font=("Bahnschrift SemiBold", 16),
            bg=COR_CARD,
            fg=COR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(10, 6))
        tk.Label(
            top,
            text=description,
            font=("Segoe UI", 10),
            bg=COR_CARD,
            fg=COR_TEXT_DIM,
            justify="left",
            anchor="w",
            wraplength=320,
        ).pack(fill="x")

        pills_wrap = tk.Frame(self, bg=COR_CARD)
        pills_wrap.pack(fill="x", padx=18, pady=(2, 10))
        for pill in pills[:3]:
            chip = tk.Label(
                pills_wrap,
                text=pill,
                font=("Segoe UI", 9, "bold"),
                bg=COR_CARD_SOFT,
                fg=accent,
                padx=10,
                pady=4,
            )
            chip.pack(side="left", padx=(0, 8), pady=2)

        spacer = tk.Frame(self, bg=COR_CARD)
        spacer.pack(fill="both", expand=True)

        footer = tk.Frame(self, bg=COR_CARD)
        footer.pack(fill="x", padx=18, pady=(0, 16))

        primary = tk.Button(
            footer,
            text=primary_text,
            command=primary_command,
            font=("Segoe UI", 10, "bold"),
            bg=accent,
            fg="#07131f",
            activebackground=accent,
            activeforeground="#07131f",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
        )
        primary.pack(side="left")

        if secondary:
            sec_text, sec_cmd = secondary
            tk.Button(
                footer,
                text=sec_text,
                command=sec_cmd,
                font=("Segoe UI", 10, "bold"),
                bg=COR_BG_ALT,
                fg=COR_TEXT,
                activebackground=COR_BG_ALT,
                activeforeground=COR_TEXT,
                relief="flat",
                bd=0,
                padx=14,
                pady=9,
                cursor="hand2",
            ).pack(side="left", padx=(10, 0))


class ResponsiveCardSection(tk.Frame):
    def __init__(self, parent, title, subtitle, cards):
        super().__init__(parent, bg=COR_BG)
        self.cards = cards
        self.card_widgets = []
        self.current_columns = None

        header = tk.Frame(self, bg=COR_BG)
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header,
            text=title,
            font=("Bahnschrift SemiBold", 20),
            bg=COR_BG,
            fg=COR_TEXT,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text=subtitle,
            font=("Segoe UI", 10),
            bg=COR_BG,
            fg=COR_TEXT_DIM,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(4, 0))

        self.grid_host = tk.Frame(self, bg=COR_BG)
        self.grid_host.pack(fill="x")

        for card_data in self.cards:
            card = DashboardCard(self.grid_host, **card_data)
            self.card_widgets.append(card)

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._relayout)

    def _compute_columns(self):
        width = max(self.winfo_width(), self.grid_host.winfo_width(), 1)
        if width < 760:
            return 1
        if width < 1180:
            return 2
        return 3

    def _on_resize(self, _event=None):
        self._relayout()

    def _relayout(self):
        columns = self._compute_columns()
        if columns == self.current_columns:
            return
        self.current_columns = columns

        for widget in self.card_widgets:
            widget.grid_forget()

        for idx in range(columns):
            self.grid_host.grid_columnconfigure(idx, weight=1, uniform=f"cards_{id(self)}")

        for idx, card in enumerate(self.card_widgets):
            row = idx // columns
            col = idx % columns
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)


class SistemaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neural Fights - Central de Operacoes")
        self.geometry("1360x900")
        self.minsize(980, 700)
        self.resizable(True, True)
        self.configure(bg=COR_BG)

        self._state = AppState.get()

        container = tk.Frame(self, bg=COR_BG)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (
            MenuPrincipal,
            TelaArmas,
            TelaPersonagens,
            TelaLuta,
            TelaMultiBatalha,
            TelaInteracoes,
            TelaSons,
            TelaWorldMap,
            TelaLeaderboard,
        ):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MenuPrincipal")
        self.tournament_window = None

    @property
    def lista_armas(self):
        return self._state.weapons

    @lista_armas.setter
    def lista_armas(self, value):
        self._state.set_weapons(value)

    @property
    def lista_personagens(self):
        return self._state.characters

    @lista_personagens.setter
    def lista_personagens(self, value):
        self._state.set_characters(value)

    def recarregar_dados(self):
        pass

    def forcar_reload_disco(self):
        self._state.reload_all()

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "atualizar_dados"):
            frame.atualizar_dados()


class MenuPrincipal(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_BG)
        self.controller = controller
        self._stats_labels = {}

        canvas = tk.Canvas(self, bg=COR_BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(canvas, bg=COR_BG)
        self._win_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", self._on_canvas_resize)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._build_ui()

    def _on_canvas_resize(self, event):
        event.widget.itemconfigure(self._win_id, width=event.width)

    def _build_ui(self):
        hero = tk.Frame(self.inner, bg=COR_HERO, highlightthickness=1, highlightbackground="#29598f")
        hero.pack(fill="x", padx=24, pady=(24, 18))

        hero_top = tk.Frame(hero, bg=COR_HERO)
        hero_top.pack(fill="x", padx=24, pady=(24, 16))

        left = tk.Frame(hero_top, bg=COR_HERO)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(
            left,
            text="NEURAL FIGHTS",
            font=("Bahnschrift SemiBold", 34),
            bg=COR_HERO,
            fg=COR_TEXT,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text="Central de combate, criacao, balanceamento e testes taticos.",
            font=("Segoe UI", 12),
            bg=COR_HERO,
            fg="#d6e5ff",
            anchor="w",
        ).pack(fill="x", pady=(4, 14))
        tk.Label(
            left,
            text="Use este hub para entrar na arena, montar conteudo e acompanhar o framework de papeis para 1v1, esquadras e horda.",
            font=("Segoe UI", 10),
            bg=COR_HERO,
            fg="#bdd2f5",
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x")

        right = tk.Frame(hero_top, bg=COR_HERO)
        right.pack(side="right", anchor="ne", padx=(16, 0))

        quick_actions = [
            ("Abrir Arena", lambda: self.controller.show_frame("TelaLuta"), COR_ACCENT),
            ("Equipe", lambda: self.controller.show_frame("TelaMultiBatalha"), COR_ACCENT_ALT),
            ("Forja", lambda: self.controller.show_frame("TelaArmas"), COR_WARNING),
        ]
        for text, cmd, color in quick_actions:
            tk.Button(
                right,
                text=text,
                command=cmd,
                font=("Segoe UI", 10, "bold"),
                bg=color,
                fg="#06101a",
                activebackground=color,
                activeforeground="#06101a",
                relief="flat",
                bd=0,
                padx=16,
                pady=10,
                cursor="hand2",
            ).pack(fill="x", pady=4)

        stats_bar = tk.Frame(hero, bg=COR_HERO)
        stats_bar.pack(fill="x", padx=24, pady=(0, 24))

        for key, label in (
            ("personagens", "Personagens"),
            ("armas", "Armas"),
            ("papeis", "Papeis"),
            ("modos", "Modos"),
        ):
            box = tk.Frame(stats_bar, bg="#0d2c4d", padx=16, pady=12)
            box.pack(side="left", padx=(0, 12), pady=4)
            value = tk.Label(box, text="0", font=("Bahnschrift SemiBold", 22), bg="#0d2c4d", fg=COR_SUCCESS)
            value.pack(anchor="w")
            tk.Label(box, text=label, font=("Segoe UI", 9, "bold"), bg="#0d2c4d", fg="#bed6f7").pack(anchor="w")
            self._stats_labels[key] = value

        sections_wrap = tk.Frame(self.inner, bg=COR_BG)
        sections_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        sec_criacao = ResponsiveCardSection(
            sections_wrap,
            "Criacao e Simulacao",
            "Os modulos que voce usa o tempo todo para montar conteudo e disparar batalhas.",
            [
                {
                    "accent": COR_WARNING,
                    "title": "Forja de Armas",
                    "description": "Edite familias, subtipos, perfil mecanico e foco magico no schema novo.",
                    "pills": ["armas", "visual", "v2"],
                    "primary_text": "Abrir Forja",
                    "primary_command": lambda: self.controller.show_frame("TelaArmas"),
                },
                {
                    "accent": COR_ACCENT_ALT,
                    "title": "Personagens",
                    "description": "Monte o roster, ajuste classe, arma, personalidade e preview de kit.",
                    "pills": ["roster", "classe", "500+"],
                    "primary_text": "Abrir Personagens",
                    "primary_command": lambda: self.controller.show_frame("TelaPersonagens"),
                },
                {
                    "accent": COR_ACCENT,
                    "title": "Arena 1v1",
                    "description": "Selecione dois lutadores, mapa, rounds e rode a simulacao principal.",
                    "pills": ["duelo", "mapa", "luta"],
                    "primary_text": "Abrir Arena",
                    "primary_command": lambda: self.controller.show_frame("TelaLuta"),
                },
                {
                    "accent": COR_SUCCESS,
                    "title": "Equipe e Torneio",
                    "description": "Acesse multi-batalha, torneio e leaderboard para validar sinergia e ranking.",
                    "pills": ["2v2+", "time", "ranking"],
                    "primary_text": "Batalha em Equipe",
                    "primary_command": lambda: self.controller.show_frame("TelaMultiBatalha"),
                    "secondary": ("Torneio", lambda: self.abrir_torneio(self.controller)),
                },
            ],
        )
        sec_criacao.pack(fill="x", pady=(0, 18))

        sec_tatico = ResponsiveCardSection(
            sections_wrap,
            "Balanceamento e IA",
            "Atalhos para o framework tatico novo, pensado para videos, esquadras, hordas e missoes.",
            [
                {
                    "accent": COR_ACCENT,
                    "title": "Plano Tatico",
                    "description": "Documento oficial com loop de iteracao, criterios e metas por modo de combate.",
                    "pills": ["plano", "roadmap", "meta"],
                    "primary_text": "Abrir Documento",
                    "primary_command": lambda: self._abrir_arquivo(PLANO_TATICO_MD_PATH, "Plano tatico"),
                },
                {
                    "accent": COR_WARNING,
                    "title": "Papeis Oficiais",
                    "description": "Veja os pacotes-base: defensor, curandeiro, assassino, suporte, horda e mais.",
                    "pills": ["roles", "pacotes", "json"],
                    "primary_text": "Abrir Papeis",
                    "primary_command": lambda: self._abrir_arquivo(PAPEIS_TATICOS_PATH, "Papeis taticos"),
                },
                {
                    "accent": COR_ACCENT_ALT,
                    "title": "Plano de Testes",
                    "description": "Regras oficiais para 1v1, grupo vs grupo e grupo vs horda com metricas e alertas.",
                    "pills": ["1v1", "squad", "horda"],
                    "primary_text": "Abrir Testes",
                    "primary_command": lambda: self._abrir_arquivo(PLANO_TESTES_PATH, "Plano de testes"),
                },
                {
                    "accent": COR_SUCCESS,
                    "title": "Feedback Social",
                    "description": "Modulo para comentarios, reacoes e sinais que alimentam o projeto de conteudo.",
                    "pills": ["midia", "comentarios", "pipeline"],
                    "primary_text": "Abrir Modulo",
                    "primary_command": lambda: self.controller.show_frame("TelaInteracoes"),
                },
            ],
        )
        sec_tatico.pack(fill="x", pady=(0, 18))

        sec_sistema = ResponsiveCardSection(
            sections_wrap,
            "Sistema e Mundo",
            "Ferramentas auxiliares para deixar o projeto inteiro acessivel a partir do launcher.",
            [
                {
                    "accent": COR_ACCENT_ALT,
                    "title": "Configurar Sons",
                    "description": "Ajuste audio, efeitos e a camada de apresentacao da experiencia.",
                    "pills": ["audio", "mix", "efeitos"],
                    "primary_text": "Abrir Sons",
                    "primary_command": lambda: self.controller.show_frame("TelaSons"),
                },
                {
                    "accent": COR_WARNING,
                    "title": "World Map",
                    "description": "Ponte para o mapa externo e o fluxo maior da campanha.",
                    "pills": ["campanha", "mundo", "bridge"],
                    "primary_text": "Abrir World Map",
                    "primary_command": lambda: self.controller.show_frame("TelaWorldMap"),
                },
                {
                    "accent": COR_SUCCESS,
                    "title": "Rankings",
                    "description": "Compare resultados e acompanhe o desempenho dos campeoes e composicoes.",
                    "pills": ["rank", "wins", "meta"],
                    "primary_text": "Abrir Ranking",
                    "primary_command": lambda: self.controller.show_frame("TelaLeaderboard"),
                },
                {
                    "accent": COR_ACCENT,
                    "title": "Encerrar Sessao",
                    "description": "Feche o launcher principal com seguranca quando terminar a rodada de ajustes.",
                    "pills": ["saida", "launcher", "fim"],
                    "primary_text": "Sair",
                    "primary_command": self.controller.quit,
                },
            ],
        )
        sec_sistema.pack(fill="x")

    def atualizar_dados(self):
        personagens = len(self.controller.lista_personagens or [])
        armas = len(self.controller.lista_armas or [])
        papeis = _load_json_count(PAPEIS_TATICOS_PATH, "papeis")
        modos = _load_json_count(PLANO_TESTES_PATH, "modos")

        stats = {
            "personagens": personagens,
            "armas": armas,
            "papeis": papeis,
            "modos": modos,
        }
        for key, value in stats.items():
            if key in self._stats_labels:
                self._stats_labels[key].configure(text=str(value))

    def _abrir_arquivo(self, path, titulo):
        if not os.path.exists(path):
            messagebox.showwarning(titulo, f"Arquivo nao encontrado:\n{path}")
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(titulo, f"Nao foi possivel abrir o arquivo.\n\n{exc}")

    def abrir_torneio(self, controller):
        try:
            import customtkinter as ctk
            from interface.view_torneio import TournamentWindow

            if controller.tournament_window is not None:
                try:
                    controller.tournament_window.lift()
                    controller.tournament_window.focus_force()
                    return
                except Exception as exc:
                    _log.debug("%s", exc)

            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            controller.tournament_window = TournamentWindow()
        except ImportError as exc:
            messagebox.showerror(
                "Erro",
                f"CustomTkinter nao instalado.\n\nExecute: pip install customtkinter\n\nErro: {exc}",
            )
        except Exception as exc:
            messagebox.showerror("Erro", f"Erro ao abrir torneio: {exc}")


class TelaInteracoes(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_BG)
        panel = tk.Frame(self, bg=COR_CARD, highlightthickness=1, highlightbackground=COR_BORDER)
        panel.pack(fill="both", expand=True, padx=48, pady=48)

        tk.Label(
            panel,
            text="Interacoes, Comentarios e Pipeline",
            font=("Bahnschrift SemiBold", 28),
            bg=COR_CARD,
            fg=COR_TEXT,
        ).pack(pady=(42, 12))
        tk.Label(
            panel,
            text="Este modulo continua em expansao. Aqui vao entrar comentarios, feedback social, selecao de prompts e sinais para o formato principal de video.",
            font=("Segoe UI", 12),
            bg=COR_CARD,
            fg=COR_TEXT_DIM,
            justify="center",
            wraplength=860,
        ).pack(pady=(0, 24))

        bullets = tk.Frame(panel, bg=COR_CARD)
        bullets.pack(pady=(0, 32))
        for line in (
            "Feed de comentarios e temas de video",
            "Banco de memes e reacoes por contexto",
            "Monitor de pipeline para batches e overlays",
        ):
            tk.Label(
                bullets,
                text=f"- {line}",
                font=("Segoe UI", 11),
                bg=COR_CARD,
                fg=COR_TEXT,
                anchor="w",
            ).pack(fill="x", pady=4)

        actions = tk.Frame(panel, bg=COR_CARD)
        actions.pack()
        tk.Button(
            actions,
            text="Voltar ao Hub",
            command=lambda: controller.show_frame("MenuPrincipal"),
            font=("Segoe UI", 10, "bold"),
            bg=COR_ACCENT,
            fg="#07131f",
            activebackground=COR_ACCENT,
            activeforeground="#07131f",
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
        ).pack(side="left", padx=8)
        tk.Button(
            actions,
            text="Abrir Plano Tatico",
            command=lambda: os.startfile(PLANO_TATICO_MD_PATH) if os.path.exists(PLANO_TATICO_MD_PATH) else None,
            font=("Segoe UI", 10, "bold"),
            bg=COR_BG_ALT,
            fg=COR_TEXT,
            activebackground=COR_BG_ALT,
            activeforeground=COR_TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
        ).pack(side="left", padx=8)


def main():
    app = SistemaApp()
    app.mainloop()


if __name__ == "__main__":
    main()
