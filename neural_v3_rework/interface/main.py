# main.py - Neural Fights Launcher
import json
import logging
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

_log = logging.getLogger("interface.main")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dados.app_state import AppState
from interface.headless_summary import (
    load_latest_headless_archetype_focus,
    load_latest_headless_inspection_target,
    load_latest_headless_report_summary,
)
from interface.theme import (
    apply_ttk_theme,
    COR_ACCENT,
    COR_BG,
    COR_BG_CARD,
    COR_BG_SECUNDARIO,
    COR_BORDA,
    COR_HEADER,
    COR_SUCCESS as COR_ACCENT_ALT,
    COR_TEXTO as COR_TEXT,
    COR_TEXTO_DIM as COR_TEXT_DIM,
    COR_WARNING,
)
from interface.ui_components import (
    ResponsiveCardSection,
    StatCard,
    UICard,
    build_section_header,
    build_page_header,
    make_primary_button,
    make_secondary_button,
)

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
RUN_POSTOS_PATH = os.path.join(ROOT_DIR, "run_postos.py")
SAIDAS_DIR = os.path.join(ROOT_DIR, "saidas")
SAIDAS_HEADLESS_DIR = os.path.join(SAIDAS_DIR, "headless")
SAIDAS_PIPELINE_DIR = os.path.join(SAIDAS_DIR, "pipeline")
PAPEIS_TATICOS_PATH = os.path.join(ROOT_DIR, "dados", "papeis_taticos.json")
PLANO_TESTES_PATH = os.path.join(ROOT_DIR, "dados", "plano_testes_taticos.json")
PLANO_TATICO_MD_PATH = os.path.join(ROOT_DIR, "documentacao", "plano_balanceamento_tatico.md")

COR_BG_ALT = COR_BG_SECUNDARIO
COR_CARD = COR_BG_SECUNDARIO
COR_BORDER = COR_BORDA
COR_HERO = COR_HEADER
COR_SUCCESS = "#7fffd4"


def _setup_worldmap_hook():
    try:
        from dados.world_bridge import WorldBridge

        WorldBridge.get()
    except Exception:
        pass


_setup_worldmap_hook()

from interface.view_armas import TelaArmas
from interface.view_arquetipos import TelaArquetipos
from interface.view_chars import TelaPersonagens
from interface.view_luta import TelaLuta
from interface.view_multi import TelaMultiBatalha
from interface.view_horda import TelaHorda
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


def resolve_visual_frame_for_headless_mode(modo):
    modo_norm = str(modo or "").strip().lower()
    mapping = {
        "duelo": "TelaLuta",
        "1v1": "TelaLuta",
        "grupo_vs_grupo": "TelaMultiBatalha",
        "equipes": "TelaMultiBatalha",
        "grupo_vs_horda": "TelaHorda",
        "horda": "TelaHorda",
    }
    return mapping.get(modo_norm, "")


def build_pipeline_args_for_headless_target(target):
    alvo = dict(target or {})
    if not alvo.get("found"):
        return []

    modo = str(alvo.get("modo", "") or "").strip().lower()
    cenario = str(alvo.get("cenario", "") or "").strip()
    template_id = str(alvo.get("template_id", "") or "").strip()
    team_a = [str(item).strip() for item in alvo.get("team_a_members", []) or [] if str(item).strip()]
    team_b = [str(item).strip() for item in alvo.get("team_b_members", []) or [] if str(item).strip()]

    args = ["pipeline", "--fights", "1", "--video-format", "classic"]
    if modo in {"duelo", "1v1"}:
        if len(team_a) != 1 or len(team_b) != 1:
            return []
        args.extend(["--encounter-mode", "duelo", "--fighter1", team_a[0], "--fighter2", team_b[0]])
        if cenario:
            args.extend(["--cenario", cenario])
        return args
    if modo in {"grupo_vs_grupo", "equipes"}:
        if not template_id:
            return []
        args.extend(["--encounter-mode", "equipes", "--template", template_id])
        return args
    if modo in {"grupo_vs_horda", "horda"}:
        if not template_id:
            return []
        args.extend(["--encounter-mode", "horda", "--template", template_id])
        return args
    return []


class SistemaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neural Fights - Central de Operacoes")
        self.geometry("1360x900")
        self.minsize(980, 700)
        self.resizable(True, True)
        self.configure(bg=COR_BG)
        apply_ttk_theme(self)

        self._state = AppState.get()

        container = tk.Frame(self, bg=COR_BG)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (
            MenuPrincipal,
            TelaArmas,
            TelaArquetipos,
            TelaPersonagens,
            TelaLuta,
            TelaMultiBatalha,
            TelaHorda,
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
        self._diag_labels = {}
        self._latest_headless_path = ""

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
            ("Horda", lambda: self.controller.show_frame("TelaHorda"), COR_SUCCESS),
            ("Forja", lambda: self.controller.show_frame("TelaArmas"), COR_WARNING),
            ("Arquétipos", lambda: self.controller.show_frame("TelaArquetipos"), COR_ACCENT_ALT),
        ]
        quick_actions[-1] = (quick_actions[-1][0], self._abrir_arquetipos_do_headless, quick_actions[-1][2])
        for text, cmd, color in quick_actions:
            make_primary_button(
                right,
                text,
                cmd,
                bg=color,
                fg="#06101a",
                padx=16,
                pady=10,
            ).pack(fill="x", pady=4)

        stats_bar = tk.Frame(hero, bg=COR_HERO)
        stats_bar.pack(fill="x", padx=24, pady=(0, 24))

        for key, label in (
            ("personagens", "Personagens"),
            ("armas", "Armas"),
            ("papeis", "Papeis"),
            ("modos", "Modos"),
        ):
            card = StatCard(stats_bar, label, "0", bg="#0d2c4d", value_fg=COR_SUCCESS, label_fg="#bed6f7")
            card.pack(side="left", padx=(0, 12), pady=4)
            self._stats_labels[key] = card

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
                {
                    "accent": COR_ACCENT_ALT,
                    "title": "Modo Horda",
                    "description": "Enfrente ondas no motor principal com solo ou expedicao e presets de monstros.",
                    "pills": ["ondas", "survival", "motor unico"],
                    "primary_text": "Abrir Horda",
                    "primary_command": lambda: self.controller.show_frame("TelaHorda"),
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
                    "title": "Arvore de Arquetipos",
                    "description": "Cruze classe, personalidade, arma e skills para enxergar o pacote inteiro de decisao da IA.",
                    "pills": ["ia", "pacotes", "combinacoes"],
                    "primary_text": "Abrir Explorador",
                    "primary_command": self._abrir_arquetipos_do_headless,
                },
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

        sec_postos = ResponsiveCardSection(
            sections_wrap,
            "Postos Operacionais",
            "Execute os tres postos principais direto do hub: coleta headless, simulacao completa e pipeline de video.",
            [
                {
                    "accent": COR_ACCENT,
                    "title": "Posto Headless",
                    "description": "Suite rapida para smoke, erros e coleta consolidada sem abrir janela.",
                    "pills": ["headless", "rapido", "logs"],
                    "primary_text": "Rodar Rapido",
                    "primary_command": lambda: self._executar_posto("Headless Rapido", ["headless", "--mode", "rapido"]),
                    "secondary": ("Abrir Saidas", lambda: self._abrir_arquivo(SAIDAS_HEADLESS_DIR, "Saidas Headless")),
                },
                {
                    "accent": COR_WARNING,
                    "title": "Harness Tatico",
                    "description": "Roda 1v1, esquadra e horda usando templates reais por papel tatico.",
                    "pills": ["tatico", "1v1", "squad", "horda"],
                    "primary_text": "Rodar Template",
                    "primary_command": lambda: self._executar_posto(
                        "Harness Tatico",
                        [
                            "headless", "--tatico",
                            "--modo", "1v1",
                            "--template", "duelo_papeis_basicos",
                            "--runs", "3",
                        ],
                    ),
                    "secondary": ("Abrir Testes", lambda: self._abrir_arquivo(PLANO_TESTES_PATH, "Plano de testes")),
                },
                {
                    "accent": COR_ACCENT_ALT,
                    "title": "Simulacao Completa",
                    "description": "Abre a simulacao do posto visual para assistir, rir e pegar bugs que o headless nao mostra.",
                    "pills": ["visual", "arena", "vfx"],
                    "primary_text": "Abrir Simulacao",
                    "primary_command": lambda: self._executar_posto("Simulacao Completa", ["simulacao", "--modo", "sim"]),
                    "secondary": ("Launcher", lambda: self._executar_posto("Launcher", ["simulacao", "--modo", "launcher"])),
                },
                {
                    "accent": COR_SUCCESS,
                    "title": "Pipeline de Video",
                    "description": "Dispara um batch curto do pipeline para postagem e validacao rapida.",
                    "pills": ["pipeline", "video", "postagem"],
                    "primary_text": "Rodar Pipeline",
                    "primary_command": lambda: self._executar_posto("Pipeline", ["pipeline", "--fights", "1"]),
                    "secondary": ("Abrir Saidas", lambda: self._abrir_arquivo(SAIDAS_PIPELINE_DIR, "Saidas Pipeline")),
                },
            ],
        )
        sec_postos.pack(fill="x", pady=(0, 18))

        sec_diag = UICard(sections_wrap, bg=COR_CARD, border=COR_BORDER)
        sec_diag.pack(fill="x", pady=(0, 18))
        build_section_header(
            sec_diag,
            "Ultimo Diagnostico Headless",
            "Resumo do ultimo relatorio tatico para voce enxergar os problemas mais urgentes sem abrir o JSON.",
            bg=COR_CARD,
            accent=COR_WARNING,
        )

        diag_body = tk.Frame(sec_diag, bg=COR_CARD)
        diag_body.pack(fill="x", padx=18, pady=(6, 18))

        diag_left = tk.Frame(diag_body, bg=COR_CARD)
        diag_left.pack(side="left", fill="both", expand=True)

        badge = tk.Label(
            diag_left,
            text="SEM RELATORIO",
            font=("Segoe UI", 9, "bold"),
            bg="#243244",
            fg=COR_TEXT,
            padx=10,
            pady=5,
        )
        badge.pack(anchor="w", pady=(0, 10))
        self._diag_labels["badge"] = badge

        title = tk.Label(
            diag_left,
            text="Nenhum relatorio headless ainda",
            font=("Bahnschrift SemiBold", 20),
            bg=COR_CARD,
            fg=COR_TEXT,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        title.pack(fill="x")
        self._diag_labels["title"] = title

        meta = tk.Label(
            diag_left,
            text="Rode o posto headless ou o harness tatico para preencher este painel.",
            font=("Segoe UI", 10),
            bg=COR_CARD,
            fg=COR_TEXT_DIM,
            anchor="w",
            justify="left",
            wraplength=860,
        )
        meta.pack(fill="x", pady=(4, 12))
        self._diag_labels["meta"] = meta

        for key, label in (
            ("alerts", "Alertas principais"),
            ("recs", "Recomendacoes"),
            ("areas", "Areas mais citadas"),
            ("packages", "Pacotes em evidencia"),
            ("review", "Eixo prioritario"),
        ):
            line = tk.Label(
                diag_left,
                text=f"{label}: -",
                font=("Segoe UI", 10),
                bg=COR_CARD,
                fg=COR_TEXT,
                anchor="w",
                justify="left",
                wraplength=860,
            )
            line.pack(fill="x", pady=3)
            self._diag_labels[key] = line

        diag_right = tk.Frame(diag_body, bg=COR_CARD)
        diag_right.pack(side="right", anchor="ne", padx=(16, 0))
        make_primary_button(
            diag_right,
            "Abrir Relatorio",
            self._abrir_ultimo_relatorio_headless,
            bg=COR_WARNING,
            fg="#07131f",
        ).pack(fill="x", pady=4)
        make_primary_button(
            diag_right,
            "Abrir Inspecao Visual",
            self._abrir_inspecao_visual_do_headless,
            bg=COR_SUCCESS,
            fg="#07131f",
        ).pack(fill="x", pady=4)
        make_primary_button(
            diag_right,
            "Gravar Video do Alvo",
            self._gravar_video_do_headless,
            bg=COR_ACCENT,
            fg="#07131f",
        ).pack(fill="x", pady=4)
        make_secondary_button(
            diag_right,
            "Editar Personagem",
            self._abrir_personagem_do_headless,
        ).pack(fill="x", pady=4)
        make_secondary_button(
            diag_right,
            "Abrir Forja",
            self._abrir_arma_do_headless,
        ).pack(fill="x", pady=4)
        make_secondary_button(
            diag_right,
            "Abrir Saidas",
            lambda: self._abrir_arquivo(SAIDAS_HEADLESS_DIR, "Saidas Headless"),
        ).pack(fill="x", pady=4)
        make_primary_button(
            diag_right,
            "Rodar Comparativo",
            lambda: self._executar_posto("Harness Tatico", ["headless", "--tatico", "--modo", "grupo_vs_grupo", "--runs", "1"]),
            bg=COR_ACCENT_ALT,
            fg="#07131f",
        ).pack(fill="x", pady=4)

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
                self._stats_labels[key].set_value(value)
        self._atualizar_diagnostico_headless()

    def _atualizar_diagnostico_headless(self):
        resumo = load_latest_headless_report_summary()
        self._latest_headless_path = resumo.get("path", "") or ""
        tone = resumo.get("status_tone", "idle")
        palette = {
            "healthy": ("#123227", COR_SUCCESS),
            "warning": ("#4a3815", "#f5c451"),
            "critical": ("#4e1f26", "#ff9494"),
            "idle": ("#243244", COR_TEXT_DIM),
        }
        bg_badge, fg_badge = palette.get(tone, palette["idle"])
        if "badge" in self._diag_labels:
            self._diag_labels["badge"].configure(
                text=resumo.get("status_text", "SEM RELATORIO"),
                bg=bg_badge,
                fg=fg_badge,
            )
        if "title" in self._diag_labels:
            self._diag_labels["title"].configure(text=resumo.get("headline", "-"))
        if "meta" in self._diag_labels:
            self._diag_labels["meta"].configure(text=resumo.get("subheadline", "-"))
        if "alerts" in self._diag_labels:
            self._diag_labels["alerts"].configure(text=f"Alertas principais: {resumo.get('alert_text', '-')}")
        if "recs" in self._diag_labels:
            self._diag_labels["recs"].configure(text=f"Recomendacoes: {resumo.get('recommendation_text', '-')}")
        if "areas" in self._diag_labels:
            self._diag_labels["areas"].configure(text=f"Areas mais citadas: {resumo.get('areas_text', '-')}")
        if "packages" in self._diag_labels:
            self._diag_labels["packages"].configure(text=f"Pacotes em evidencia: {resumo.get('package_text', '-')}")
        if "review" in self._diag_labels:
            self._diag_labels["review"].configure(text=f"Eixo prioritario: {resumo.get('review_axis_text', '-')} | {resumo.get('review_plan_text', '-')}")

    def _abrir_arquetipos_do_headless(self):
        self.controller.show_frame("TelaArquetipos")
        frame = self.controller.frames.get("TelaArquetipos")
        if frame is None or not hasattr(frame, "aplicar_alvo_headless"):
            return
        frame.aplicar_alvo_headless(silencioso=True)

    def _abrir_inspecao_visual_do_headless(self):
        alvo = load_latest_headless_inspection_target()
        if not alvo.get("found"):
            messagebox.showinfo(
                "Inspecao Visual",
                "Ainda nao existe alvo de inspecao vindo do headless.\n\nRode o harness tatico primeiro.",
            )
            return
        page_name = resolve_visual_frame_for_headless_mode(alvo.get("modo", ""))
        if not page_name:
            messagebox.showinfo(
                "Inspecao Visual",
                "O ultimo relatorio nao aponta um modo visual suportado automaticamente.",
            )
            return
        self.controller.show_frame(page_name)
        frame = self.controller.frames.get(page_name)
        if frame is None or not hasattr(frame, "_aplicar_alvo_inspecao_headless"):
            messagebox.showwarning(
                "Inspecao Visual",
                f"A tela {page_name} nao suporta aplicacao automatica do alvo.",
            )
            return
        frame._aplicar_alvo_inspecao_headless()

    def _gravar_video_do_headless(self):
        alvo = load_latest_headless_inspection_target()
        if not alvo.get("found"):
            messagebox.showinfo(
                "Pipeline do Alvo",
                "Ainda nao existe alvo de inspecao vindo do headless.\n\nRode o harness tatico primeiro.",
            )
            return
        args = build_pipeline_args_for_headless_target(alvo)
        if not args:
            messagebox.showinfo(
                "Pipeline do Alvo",
                "O ultimo alvo nao pode ser convertido automaticamente em uma gravacao da pipeline.\n\nVerifique se o relatorio tem template ou duelo direto valido.",
            )
            return
        self._executar_posto("Pipeline do Alvo", args)

    def _abrir_personagem_do_headless(self):
        foco = load_latest_headless_archetype_focus()
        if not foco.get("found"):
            messagebox.showinfo(
                "Foco Headless",
                "Ainda nao existe foco de pacote vindo do headless.\n\nRode o harness tatico primeiro.",
            )
            return
        nome = str(foco.get("personagem_nome", "") or "")
        self.controller.show_frame("TelaPersonagens")
        frame = self.controller.frames.get("TelaPersonagens")
        if frame is None or not hasattr(frame, "focar_personagem_nome") or not nome:
            return
        if not frame.focar_personagem_nome(nome, abrir_edicao=True):
            messagebox.showwarning(
                "Foco Headless",
                f"O personagem '{nome}' nao esta disponivel no roster atual.",
            )

    def _abrir_arma_do_headless(self):
        foco = load_latest_headless_archetype_focus()
        if not foco.get("found"):
            messagebox.showinfo(
                "Foco Headless",
                "Ainda nao existe foco de pacote vindo do headless.\n\nRode o harness tatico primeiro.",
            )
            return
        nome = str(foco.get("arma_nome", "") or "")
        self.controller.show_frame("TelaArmas")
        frame = self.controller.frames.get("TelaArmas")
        if frame is None or not hasattr(frame, "focar_arma_nome") or not nome:
            return
        if not frame.focar_arma_nome(nome):
            messagebox.showwarning(
                "Foco Headless",
                f"A arma '{nome}' nao esta disponivel no arsenal atual.",
            )

    def _abrir_ultimo_relatorio_headless(self):
        if not self._latest_headless_path or not os.path.exists(self._latest_headless_path):
            messagebox.showinfo(
                "Ultimo Diagnostico",
                "Ainda nao existe relatorio headless pronto.\n\nRode o posto headless ou o harness tatico primeiro.",
            )
            return
        self._abrir_arquivo(self._latest_headless_path, "Ultimo Diagnostico Headless")

    def _abrir_arquivo(self, path, titulo):
        if not os.path.exists(path):
            messagebox.showwarning(titulo, f"Arquivo nao encontrado:\n{path}")
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(titulo, f"Nao foi possivel abrir o arquivo.\n\n{exc}")

    def _executar_posto(self, titulo, args):
        if not os.path.exists(RUN_POSTOS_PATH):
            messagebox.showerror(titulo, f"run_postos.py nao encontrado:\n{RUN_POSTOS_PATH}")
            return
        try:
            subprocess.Popen(
                [sys.executable, RUN_POSTOS_PATH, *args],
                cwd=ROOT_DIR,
            )
            messagebox.showinfo(
                titulo,
                "Execucao iniciada em segundo plano.\n\n"
                "Acompanhe as saidas na pasta `saidas/` ou pelo terminal.",
            )
        except Exception as exc:
            messagebox.showerror(titulo, f"Nao foi possivel iniciar o posto.\n\n{exc}")

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
        build_page_header(
            self,
            "INTERACOES E PIPELINE",
            "Comentarios, memes, roteiro de video e sinais de contexto para o formato principal.",
            lambda: controller.show_frame("MenuPrincipal"),
            button_bg=COR_ACCENT,
            button_fg="#07131f",
        )

        panel = UICard(self, bg=COR_CARD, border=COR_BORDER)
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
        make_primary_button(
            actions,
            "Voltar ao Hub",
            lambda: controller.show_frame("MenuPrincipal"),
        ).pack(side="left", padx=8)
        make_secondary_button(
            actions,
            "Abrir Plano Tatico",
            lambda: os.startfile(PLANO_TATICO_MD_PATH) if os.path.exists(PLANO_TATICO_MD_PATH) else None,
        ).pack(side="left", padx=8)


def main():
    app = SistemaApp()
    app.mainloop()


if __name__ == "__main__":
    main()
