"""
ARENA DE COMBATE - NEURAL FIGHTS
Tela de selecao de lutadores para batalha.
"""

import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dados.app_state import AppState
from interface.headless_summary import load_latest_headless_inspection_target, load_latest_headless_report_summary
from interface.theme import (
    CORES_CLASSE,
    COR_ACCENT,
    COR_BG,
    COR_BG_SECUNDARIO,
    COR_HEADER,
    COR_P1,
    COR_P2,
    COR_TEXTO,
    COR_TEXTO_DIM,
)
from interface.ui_components import UICard, HeadlessSummaryCard, ScrollableWorkspace, build_page_header, make_primary_button
from simulacao import simulacao

_log = logging.getLogger("interface.view_luta")


class TelaLuta(tk.Frame):
    """Tela de selecao de lutadores."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_BG)
        self.controller = controller
        self.personagem_p1 = None
        self.personagem_p2 = None
        self._canvas_owner = {}

        self.setup_ui()

        AppState.get().subscribe("characters_changed", self._on_data_changed)
        AppState.get().subscribe("weapons_changed", self._on_data_changed)

    def _on_data_changed(self, _data=None):
        if hasattr(self, "atualizar_dados"):
            self.atualizar_dados()

    def setup_ui(self):
        header, _title_wrap, right_slot = build_page_header(
            self,
            "ARENA DE COMBATE",
            "Monte o confronto, configure o mapa e dispare a simulacao principal.",
            lambda: self.controller.show_frame("MenuPrincipal"),
            button_bg=COR_BG_SECUNDARIO,
            button_fg=COR_TEXTO,
            height=92,
        )

        self.lbl_matchup = tk.Label(
            right_slot,
            text="Aguardando selecao",
            font=("Segoe UI", 10, "bold"),
            bg=COR_HEADER,
            fg=COR_ACCENT,
            justify="right",
            anchor="e",
        )
        self.lbl_matchup.pack(anchor="e", pady=16)

        footer = tk.Frame(self, bg=COR_BG, height=78)
        footer.pack(fill="x", side="bottom", padx=20, pady=(0, 14))
        footer.pack_propagate(False)

        footer_info = tk.Frame(footer, bg=COR_BG)
        footer_info.pack(side="left", fill="y")

        self.lbl_status = tk.Label(
            footer_info,
            text="Selecione dois campeoes diferentes para habilitar a luta.",
            font=("Segoe UI", 10),
            bg=COR_BG,
            fg=COR_TEXTO_DIM,
            anchor="w",
        )
        self.lbl_status.pack(anchor="w", pady=(18, 4))

        tk.Label(
            footer_info,
            text="Use rounds maiores e mapas tematicos para sentir melhor spacing, ritmo e leitura visual.",
            font=("Segoe UI", 9),
            bg=COR_BG,
            fg=COR_TEXTO_DIM,
            anchor="w",
        ).pack(anchor="w")

        self.btn_iniciar = make_primary_button(
            footer,
            "INICIAR BATALHA",
            self.iniciar_luta,
            font=("Bahnschrift SemiBold", 15),
            bg=COR_TEXTO_DIM,
            fg=COR_TEXTO,
            padx=30,
            pady=13,
            state="disabled",
        )
        self.btn_iniciar.pack(side="right", pady=14)

        workspace = ScrollableWorkspace(self, bg=COR_BG, xscroll=True, yscroll=True)
        workspace.pack(fill="both", expand=True, padx=20, pady=(16, 10))
        main = workspace.content
        self._main_area = main
        self._workspace = workspace

        paned = tk.PanedWindow(
            main,
            orient="horizontal",
            sashwidth=8,
            sashrelief="flat",
            showhandle=False,
            bd=0,
            relief="flat",
            bg=COR_BG,
        )
        paned.pack(fill="both", expand=True)
        self._paned_main = paned

        frame_p1 = self._criar_coluna_jogador(main, "LUTADOR A", COR_P1, "p1")
        frame_center = self._criar_coluna_central(main)
        frame_p2 = self._criar_coluna_jogador(main, "LUTADOR B", COR_P2, "p2")
        self._frame_center = frame_center

        paned.add(frame_p1, minsize=300, stretch="always")
        paned.add(frame_center, minsize=260, stretch="never")
        paned.add(frame_p2, minsize=300, stretch="always")

        self.after(100, lambda: paned.sash_place(0, 430, 0))
        self.after(150, lambda: paned.sash_place(1, 860, 0))
        main.bind("<Configure>", self._on_main_resize)

    def _on_main_resize(self, event=None):
        """Rebalanceia o layout da arena em janelas menores."""
        width = event.width if event else self._main_area.winfo_width()
        if width < 760 or not hasattr(self, "_paned_main"):
            return

        center_w = max(240, min(int(width * 0.25), 320))
        left = max(260, min(int((width - center_w) / 2), 460))
        right = min(width - max(260, left), left + center_w)
        right = max(left + center_w, width - max(260, int(width * 0.32)))

        try:
            self._paned_main.sash_place(0, left, 0)
            self._paned_main.sash_place(1, right, 0)
        except Exception:
            pass

        self._ajustar_wraps_centro()

    def _criar_coluna_jogador(self, parent, titulo, accent, prefixo):
        frame = UICard(parent, bg=COR_BG_SECUNDARIO, border="#27405f")

        head = tk.Frame(frame, bg=COR_BG_SECUNDARIO)
        head.pack(fill="x", padx=16, pady=(16, 10))
        tk.Frame(head, bg=accent, width=54, height=6).pack(anchor="w")
        tk.Label(
            head,
            text=titulo,
            font=("Bahnschrift SemiBold", 18),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO,
            anchor="w",
        ).pack(fill="x", pady=(10, 2))
        tk.Label(
            head,
            text="Preview em tempo real, estatisticas rapidas e roster disponivel.",
            font=("Segoe UI", 9),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            anchor="w",
        ).pack(fill="x")

        canvas = tk.Canvas(
            frame,
            height=220,
            bg=COR_BG,
            highlightthickness=1,
            highlightbackground="#34517a",
        )
        canvas.pack(fill="x", padx=16, pady=(0, 10))

        lbl_nome = tk.Label(
            frame,
            text="-",
            font=("Segoe UI", 14, "bold"),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO,
        )
        lbl_nome.pack()

        lbl_stats = tk.Label(
            frame,
            text="",
            font=("Consolas", 9),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            justify="center",
        )
        lbl_stats.pack(pady=(6, 10))

        tk.Label(
            frame,
            text="Roster disponivel",
            font=("Segoe UI", 9, "bold"),
            bg=COR_BG_SECUNDARIO,
            fg=accent,
            anchor="w",
        ).pack(fill="x", padx=16)

        list_wrap = tk.Frame(frame, bg=COR_BG_SECUNDARIO)
        list_wrap.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        listbox = tk.Listbox(
            list_wrap,
            bg=COR_BG,
            fg=COR_TEXTO,
            selectbackground=accent,
            selectforeground=COR_TEXTO,
            font=("Segoe UI", 10),
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2c4268",
            highlightcolor=accent,
            activestyle="none",
        )
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if prefixo == "p1":
            self.canvas_p1 = canvas
            self.lbl_nome_p1 = lbl_nome
            self.lbl_stats_p1 = lbl_stats
            self.listbox_p1 = listbox
            self.listbox_p1.bind("<<ListboxSelect>>", lambda _e: self._on_select_p1())
        else:
            self.canvas_p2 = canvas
            self.lbl_nome_p2 = lbl_nome
            self.lbl_stats_p2 = lbl_stats
            self.listbox_p2 = listbox
            self.listbox_p2.bind("<<ListboxSelect>>", lambda _e: self._on_select_p2())

        self._canvas_owner[canvas] = prefixo
        canvas.bind("<Configure>", self._redesenhar_preview_por_resize)
        return frame

    def _criar_coluna_central(self, parent):
        frame = tk.Frame(parent, bg=COR_BG)

        matchup = UICard(frame, bg=COR_BG_SECUNDARIO, border="#27405f")
        matchup.pack(fill="x", pady=(0, 14))
        tk.Label(
            matchup,
            text="MATCHUP",
            font=("Segoe UI", 9, "bold"),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
        ).pack(pady=(16, 4))
        tk.Label(
            matchup,
            text="VS",
            font=("Bahnschrift SemiBold", 40),
            bg=COR_BG_SECUNDARIO,
            fg=COR_ACCENT,
        ).pack()
        self.lbl_round_hint = tk.Label(
            matchup,
            text="Escolha os dois lados para montar o confronto.",
            font=("Segoe UI", 9),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            wraplength=220,
            justify="center",
        )
        self.lbl_round_hint.pack(pady=(2, 16))

        cfg = UICard(frame, bg=COR_BG_SECUNDARIO, border="#27405f")
        cfg.pack(fill="x")

        tk.Label(
            cfg,
            text="CONFIGURACAO DA PARTIDA",
            font=("Segoe UI", 10, "bold"),
            bg=COR_BG_SECUNDARIO,
            fg=COR_ACCENT,
        ).pack(pady=(18, 14))

        row_rounds = tk.Frame(cfg, bg=COR_BG_SECUNDARIO)
        row_rounds.pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(row_rounds, text="Rounds", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w")
        self.var_best_of = tk.StringVar(value="1")
        ttk.Combobox(
            row_rounds,
            textvariable=self.var_best_of,
            values=["1", "3", "5"],
            state="readonly",
            width=10,
        ).pack(anchor="w", pady=(6, 0))

        row_portrait = tk.Frame(cfg, bg=COR_BG_SECUNDARIO)
        row_portrait.pack(fill="x", padx=16, pady=(0, 12))
        self.var_portrait = tk.BooleanVar(value=False)
        self.chk_portrait = tk.Checkbutton(
            row_portrait,
            text="Modo retrato 9:16",
            variable=self.var_portrait,
            font=("Segoe UI", 10),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO,
            selectcolor=COR_BG,
            activebackground=COR_BG_SECUNDARIO,
            activeforeground=COR_ACCENT,
        )
        self.chk_portrait.pack(anchor="w")
        tk.Label(
            row_portrait,
            text="Bom para TikTok, Reels e captura vertical.",
            font=("Segoe UI", 8),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
        ).pack(anchor="w", pady=(2, 0))

        row_mapa = tk.Frame(cfg, bg=COR_BG_SECUNDARIO)
        row_mapa.pack(fill="x", padx=16, pady=(0, 18))
        tk.Label(row_mapa, text="Mapa", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w")

        self.var_cenario = tk.StringVar(value="Arena")
        self.btn_mapa = tk.Button(
            row_mapa,
            text="Arena Classica",
            font=("Segoe UI", 10, "bold"),
            bg=COR_BG,
            fg=COR_TEXTO,
            bd=0,
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
            command=self._abrir_seletor_mapa,
        )
        self.btn_mapa.pack(fill="x", pady=(6, 8))

        self.lbl_mapa_info = tk.Label(
            row_mapa,
            text="30x20m | retangular | 0 obstaculos",
            font=("Segoe UI", 8),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            justify="left",
            wraplength=220,
        )
        self.lbl_mapa_info.pack(anchor="w")

        self.headless_diag_card = HeadlessSummaryCard(
            frame,
            title="Leitura Tatica Recente",
            compact=True,
            open_command=self._abrir_ultimo_relatorio_headless,
            action_text="Aplicar Alvo",
            action_command=self._aplicar_alvo_inspecao_headless,
        )
        self.headless_diag_card.pack(fill="x", pady=(14, 0))

        return frame

    def _ajustar_wraps_centro(self):
        largura = 220
        if hasattr(self, "_frame_center"):
            largura = max(min(self._frame_center.winfo_width() - 40, 320), 150)
        if hasattr(self, "lbl_round_hint"):
            self.lbl_round_hint.config(wraplength=largura)
        if hasattr(self, "lbl_mapa_info"):
            self.lbl_mapa_info.config(wraplength=largura)

    def _redesenhar_preview_por_resize(self, event):
        dono = self._canvas_owner.get(event.widget)
        if dono == "p1" and self.personagem_p1:
            self._desenhar_preview(self.personagem_p1, self.canvas_p1, self.lbl_nome_p1, self.lbl_stats_p1, COR_P1)
        elif dono == "p2" and self.personagem_p2:
            self._desenhar_preview(self.personagem_p2, self.canvas_p2, self.lbl_nome_p2, self.lbl_stats_p2, COR_P2)

    def atualizar_dados(self):
        self._refresh_headless_summary()
        self.listbox_p1.delete(0, tk.END)
        self.listbox_p2.delete(0, tk.END)
        self.personagem_p1 = None
        self.personagem_p2 = None

        personagens = self.controller.lista_personagens
        if not personagens:
            self.listbox_p1.insert(tk.END, "(Nenhum personagem)")
            self.listbox_p2.insert(tk.END, "(Nenhum personagem)")
            self._atualizar_botao()
            return

        for personagem in personagens:
            classe = getattr(personagem, "classe", "Guerreiro")
            elo_tag = ""
            try:
                from dados.battle_db import BattleDB

                cs = BattleDB.get().get_character_stats(personagem.nome)
                if cs and cs.get("matches_played", 0) > 0:
                    elo_tag = f" [{cs['elo']:.0f}]"
            except Exception as exc:
                _log.debug("ELO lookup listbox falhou (nao-critico): %s", exc)

            texto = f"{personagem.nome} ({classe}){elo_tag}"
            self.listbox_p1.insert(tk.END, texto)
            self.listbox_p2.insert(tk.END, texto)

        if len(personagens) >= 1:
            self.listbox_p1.selection_set(0)
            self._on_select_p1()
        if len(personagens) >= 2:
            self.listbox_p2.selection_set(1)
            self._on_select_p2()
        elif len(personagens) == 1:
            self.listbox_p2.selection_set(0)
            self._on_select_p2()

    def _refresh_headless_summary(self):
        if hasattr(self, "headless_diag_card"):
            self._latest_headless_summary = load_latest_headless_report_summary()
            self.headless_diag_card.set_summary(self._latest_headless_summary)

    def _abrir_ultimo_relatorio_headless(self):
        resumo = getattr(self, "_latest_headless_summary", None) or load_latest_headless_report_summary()
        path = str(resumo.get("path", "") or "")
        if not path or not os.path.exists(path):
            messagebox.showinfo(
                "Diagnostico Headless",
                "Ainda nao existe relatorio headless pronto.\n\nRode o harness tatico ou o posto headless primeiro.",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Diagnostico Headless", f"Nao foi possivel abrir o relatorio.\n\n{exc}")

    def _selecionar_personagem_por_nome(self, listbox, nome, callback):
        personagens = self.controller.lista_personagens
        idx = next((i for i, personagem in enumerate(personagens) if personagem.nome == nome), None)
        if idx is None:
            return False
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(idx)
        listbox.activate(idx)
        listbox.see(idx)
        callback()
        return True

    def _aplicar_alvo_inspecao_headless(self):
        alvo = load_latest_headless_inspection_target()
        if not alvo.get("found"):
            messagebox.showinfo(
                "Aplicar Alvo",
                "Ainda nao existe alvo de inspecao pronto.\n\nRode o harness tatico primeiro.",
            )
            return

        team_a = list(alvo.get("team_a_members", []) or [])
        team_b = list(alvo.get("team_b_members", []) or [])
        if len(team_a) != 1 or len(team_b) != 1:
            messagebox.showinfo(
                "Aplicar Alvo",
                "O ultimo diagnostico nao descreve um duelo 1v1 direto.\n\nUse a Arena 1v1 para diagnosticos de duelo ou abra Equipes/Horda para os outros modos.",
            )
            return

        ok_a = self._selecionar_personagem_por_nome(self.listbox_p1, team_a[0], self._on_select_p1)
        ok_b = self._selecionar_personagem_por_nome(self.listbox_p2, team_b[0], self._on_select_p2)
        if not (ok_a and ok_b):
            messagebox.showwarning(
                "Aplicar Alvo",
                "Os personagens do relatorio nao estao disponiveis no roster atual.",
            )
            return

        if alvo.get("cenario"):
            self.var_cenario.set(alvo["cenario"])
            self._selecionar_mapa(alvo["cenario"])
        self.lbl_status.config(
            text=f"Inspecao aplicada: {alvo.get('template_nome') or alvo.get('template_id') or 'duelo'}",
            fg=COR_ACCENT,
        )

    def _on_select_p1(self):
        sel = self.listbox_p1.curselection()
        if not sel:
            return
        idx = sel[0]
        personagens = self.controller.lista_personagens
        if idx < len(personagens):
            self.personagem_p1 = personagens[idx]
            self._desenhar_preview(self.personagem_p1, self.canvas_p1, self.lbl_nome_p1, self.lbl_stats_p1, COR_P1)
        self._atualizar_botao()

    def _on_select_p2(self):
        sel = self.listbox_p2.curselection()
        if not sel:
            return
        idx = sel[0]
        personagens = self.controller.lista_personagens
        if idx < len(personagens):
            self.personagem_p2 = personagens[idx]
            self._desenhar_preview(self.personagem_p2, self.canvas_p2, self.lbl_nome_p2, self.lbl_stats_p2, COR_P2)
        self._atualizar_botao()

    def _desenhar_preview(self, personagem, canvas, lbl_nome, lbl_stats, cor_borda):
        canvas.delete("all")

        if not personagem:
            lbl_nome.config(text="-")
            lbl_stats.config(text="")
            return

        lbl_nome.config(text=personagem.nome)

        cw = max(canvas.winfo_width(), 240)
        ch = max(canvas.winfo_height(), 220)
        cx = cw / 2
        cy = ch * 0.48

        cor = f"#{personagem.cor_r:02x}{personagem.cor_g:02x}{personagem.cor_b:02x}"
        classe = getattr(personagem, "classe", "Guerreiro")
        cor_classe = CORES_CLASSE.get(classe, "#8092a8")

        aura_raio = min(cw, ch) * 0.28
        corpo_raio = min(max(personagem.tamanho * 8, 16), 48)

        canvas.create_oval(
            cx - aura_raio,
            cy - aura_raio,
            cx + aura_raio,
            cy + aura_raio,
            outline=cor_classe,
            width=2,
            dash=(4, 3),
        )
        canvas.create_oval(
            cx - corpo_raio,
            cy - corpo_raio,
            cx + corpo_raio,
            cy + corpo_raio,
            fill=cor,
            outline=cor_borda,
            width=3,
        )
        canvas.create_text(
            cx,
            ch * 0.82,
            text=classe,
            font=("Segoe UI", 10, "bold"),
            fill=cor_classe,
        )

        if personagem.nome_arma:
            arma = next((a for a in self.controller.lista_armas if a.nome == personagem.nome_arma), None)
            if arma:
                cor_arma = f"#{arma.r:02x}{arma.g:02x}{arma.b:02x}"
                canvas.create_line(
                    cx + corpo_raio,
                    cy,
                    cx + corpo_raio + 52,
                    cy,
                    fill=cor_arma,
                    width=5,
                    capstyle=tk.ROUND,
                )

        arma_txt = personagem.nome_arma if personagem.nome_arma else "Maos Vazias"
        stats = f"VEL {personagem.velocidade:.1f} | RES {personagem.resistencia:.1f}\nARMA {arma_txt}"

        try:
            from dados.battle_db import BattleDB

            db = BattleDB.get()
            char_stats = db.get_character_stats(personagem.nome)
            if char_stats and char_stats.get("matches_played", 0) > 0:
                elo = char_stats["elo"]
                tier = char_stats["tier"]
                wins = char_stats["wins"]
                losses = char_stats["losses"]
                mp = max(char_stats["matches_played"], 1)
                wr = wins / mp * 100
                stats += f"\n{tier} | ELO {elo:.0f}"
                stats += f"\n{wins}W - {losses}L ({wr:.0f}%)"
        except Exception as exc:
            _log.debug("Stats block falhou (nao-critico): %s", exc)

        lbl_stats.config(text=stats)

    def _atualizar_botao(self):
        if self.personagem_p1 and self.personagem_p2:
            if self.personagem_p1.nome == self.personagem_p2.nome:
                self.btn_iniciar.config(state="disabled", bg=COR_TEXTO_DIM)
                self.lbl_status.config(text="Escolha dois campeoes diferentes para evitar espelho.")
                self.lbl_matchup.config(text=f"{self.personagem_p1.nome} x {self.personagem_p2.nome}")
                self.lbl_round_hint.config(text="Espelho detectado. Troque um dos lados para continuar.")
            else:
                self.btn_iniciar.config(state="normal", bg=COR_ACCENT)
                self.lbl_status.config(text="Confronto pronto. Revise rounds, mapa e modo retrato antes de iniciar.")
                self.lbl_matchup.config(text=f"{self.personagem_p1.nome}  VS  {self.personagem_p2.nome}")
                self.lbl_round_hint.config(text=f"Best of {self.var_best_of.get()} no mapa {self.var_cenario.get()}.")
        else:
            self.btn_iniciar.config(state="disabled", bg=COR_TEXTO_DIM)
            self.lbl_status.config(text="Selecione dois campeoes diferentes para habilitar a luta.")
            self.lbl_matchup.config(text="Aguardando selecao")
            self.lbl_round_hint.config(text="Escolha os dois lados para montar o confronto.")

    def _abrir_seletor_mapa(self):
        SeletorMapa(self, self._on_mapa_selecionado)

    def _on_mapa_selecionado(self, mapa_key: str, mapa_info: dict):
        self.var_cenario.set(mapa_key)
        self.btn_mapa.config(text=mapa_info["nome"])
        info_text = f"{mapa_info['tamanho']} | {mapa_info['formato']} | {mapa_info['obstaculos']} obstaculos"
        self.lbl_mapa_info.config(text=info_text)
        self._atualizar_botao()

    def iniciar_luta(self):
        if not self.personagem_p1 or not self.personagem_p2:
            messagebox.showwarning("Atencao", "Selecione dois campeoes.")
            return

        if self.personagem_p1.nome == self.personagem_p2.nome:
            messagebox.showwarning("Atencao", "Selecione dois campeoes diferentes.")
            return

        match_data = {
            "p1_nome": self.personagem_p1.nome,
            "p2_nome": self.personagem_p2.nome,
            "cenario": self.var_cenario.get(),
            "best_of": int(self.var_best_of.get()),
            "portrait_mode": self.var_portrait.get(),
        }

        try:
            AppState.get().set_match_config(match_data)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao salvar configuracao:\n{exc}")
            return

        self.controller.withdraw()

        try:
            import time

            t_start = time.time()
            sim = simulacao.Simulador()
            sim.run()
            duration = time.time() - t_start

            post_fight_result = None

            if sim.vencedor:
                loser = sim.p2.dados.nome if sim.vencedor == sim.p1.dados.nome else sim.p1.dados.nome
                ko = any(f.morto for f in sim.fighters if f.dados.nome == loser)

                elo_before_w, elo_before_l = 1600.0, 1600.0
                db = None
                try:
                    from dados.battle_db import BattleDB

                    db = BattleDB.get()
                    ws = db.get_character_stats(sim.vencedor)
                    ls = db.get_character_stats(loser)
                    if ws:
                        elo_before_w = ws["elo"]
                    if ls:
                        elo_before_l = ls["elo"]
                except Exception as exc:
                    _log.debug("ELO before falhou: %s", exc)

                try:
                    match_id = AppState.get().record_fight_result(
                        winner=sim.vencedor,
                        loser=loser,
                        duration=duration,
                        ko=ko,
                        arena=sim.cenario if hasattr(sim, "cenario") else "",
                    )
                    if match_id and hasattr(sim, "stats_collector"):
                        sim.stats_collector.flush_to_db(match_id)
                except Exception as exc:
                    print(f"[view_luta] BattleDB/ELO write failed (non-fatal): {exc}")

                elo_after_w, elo_after_l = elo_before_w, elo_before_l
                tier_w, tier_l = "BRONZE", "BRONZE"
                try:
                    if db:
                        ws2 = db.get_character_stats(sim.vencedor)
                        ls2 = db.get_character_stats(loser)
                        if ws2:
                            elo_after_w = ws2["elo"]
                            tier_w = ws2["tier"]
                        if ls2:
                            elo_after_l = ls2["elo"]
                            tier_l = ls2["tier"]
                except Exception as exc:
                    _log.debug("ELO after read falhou: %s", exc)

                w_stats, l_stats = {}, {}
                if hasattr(sim, "stats_collector"):
                    try:
                        summary = sim.stats_collector.get_summary()
                        w_stats = summary.get(sim.vencedor, {})
                        l_stats = summary.get(loser, {})
                    except Exception as exc:
                        _log.debug("stats_collector summary falhou: %s", exc)

                post_fight_result = {
                    "winner": sim.vencedor,
                    "loser": loser,
                    "ko_type": "KO" if ko else "TIMEOUT",
                    "duration": duration,
                    "winner_elo_before": elo_before_w,
                    "winner_elo_after": elo_after_w,
                    "winner_tier": tier_w,
                    "loser_elo_before": elo_before_l,
                    "loser_elo_after": elo_after_l,
                    "loser_tier": tier_l,
                    "winner_stats": w_stats,
                    "loser_stats": l_stats,
                }

                try:
                    from dados.world_bridge import WorldBridge

                    res = WorldBridge.get().on_fight_result(sim.vencedor, loser, duration, "KO")
                    if res.ok and res.zone_id:
                        zone_label = res.zone_id.replace("_", " ").title()
                        messagebox.showinfo(
                            "Conquista de Territorio",
                            f"{sim.vencedor} venceu.\n\nSeu deus conquistou:\n{zone_label}",
                        )
                    elif not res.ok:
                        _log.warning("WorldBridge inativo: %s", res.reason)
                except Exception as exc:
                    _log.exception("WorldBridge erro: %s", exc)

        except Exception as exc:
            messagebox.showerror("Erro", f"Simulacao falhou:\n{exc}")
            post_fight_result = None

        self.controller.deiconify()

        if post_fight_result:
            try:
                from interface.view_resultado import show_post_fight

                show_post_fight(self.controller, post_fight_result)
            except Exception as exc:
                print(f"[view_luta] PostFight screen failed (non-fatal): {exc}")

    def atualizar_previews(self, event=None):
        pass


class SeletorMapa(tk.Toplevel):
    """Janela de selecao de mapa com preview visual."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback

        self.title("Selecionar mapa")
        self.geometry("900x650")
        self.minsize(640, 480)
        self.configure(bg=COR_BG)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        from nucleo.arena import ARENAS, LISTA_MAPAS, get_mapa_info

        self.ARENAS = ARENAS
        self.LISTA_MAPAS = LISTA_MAPAS
        self.get_mapa_info = get_mapa_info
        self.mapa_selecionado = "Arena"

        self._setup_ui()
        self._selecionar_mapa("Arena")

    def _setup_ui(self):
        header = tk.Frame(self, bg=COR_HEADER, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="ESCOLHA O CAMPO DE BATALHA",
            font=("Bahnschrift SemiBold", 18),
            bg=COR_HEADER,
            fg=COR_TEXTO,
        ).pack(pady=14)

        main = tk.Frame(self, bg=COR_BG)
        main.pack(fill="both", expand=True, padx=15, pady=10)
        main.grid_columnconfigure(0, weight=1, minsize=220)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        frame_lista = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        frame_lista.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(
            frame_lista,
            text="Mapas disponiveis",
            font=("Segoe UI", 11, "bold"),
            bg=COR_BG_SECUNDARIO,
            fg=COR_ACCENT,
        ).pack(pady=10)

        canvas_container = tk.Frame(frame_lista, bg=COR_BG_SECUNDARIO)
        canvas_container.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        canvas = tk.Canvas(canvas_container, bg=COR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        self.frame_mapas = tk.Frame(canvas, bg=COR_BG)

        canvas.create_window((0, 0), window=self.frame_mapas, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.botoes_mapa = {}
        for mapa_key in self.LISTA_MAPAS:
            info = self.get_mapa_info(mapa_key)
            if not info:
                continue

            btn = tk.Button(
                self.frame_mapas,
                text=info["nome"],
                font=("Segoe UI", 10),
                bg=COR_BG_SECUNDARIO,
                fg=COR_TEXTO,
                bd=0,
                relief="flat",
                anchor="w",
                padx=12,
                pady=10,
                cursor="hand2",
                command=lambda k=mapa_key: self._selecionar_mapa(k),
            )
            btn.pack(fill="x", pady=3, padx=6)
            self.botoes_mapa[mapa_key] = btn

        self.frame_mapas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        frame_preview = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        frame_preview.grid(row=0, column=1, sticky="nsew")

        self.lbl_nome_mapa = tk.Label(
            frame_preview,
            text="Arena Classica",
            font=("Bahnschrift SemiBold", 24),
            bg=COR_BG_SECUNDARIO,
            fg=COR_ACCENT,
        )
        self.lbl_nome_mapa.pack(pady=(15, 5))

        self.canvas_preview = tk.Canvas(
            frame_preview,
            bg=COR_BG,
            highlightthickness=1,
            highlightbackground=COR_ACCENT,
        )
        self.canvas_preview.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas_preview.bind("<Configure>", lambda _e: self._redraw_map_preview())

        self.lbl_descricao = tk.Label(
            frame_preview,
            text="Arena padrao sem obstaculos",
            font=("Segoe UI", 11),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO,
            wraplength=350,
        )
        self.lbl_descricao.pack(pady=5)

        self.lbl_stats = tk.Label(
            frame_preview,
            text="",
            font=("Segoe UI", 10),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            justify="center",
        )
        self.lbl_stats.pack(pady=10)

        footer = tk.Frame(self, bg=COR_BG)
        footer.pack(fill="x", pady=15)

        tk.Button(
            footer,
            text="Cancelar",
            font=("Segoe UI", 10, "bold"),
            bg=COR_TEXTO_DIM,
            fg=COR_TEXTO,
            bd=0,
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2",
            command=self.destroy,
        ).pack(side="left", padx=20)

        tk.Button(
            footer,
            text="Confirmar mapa",
            font=("Segoe UI", 11, "bold"),
            bg=COR_ACCENT,
            fg=COR_TEXTO,
            bd=0,
            relief="flat",
            padx=22,
            pady=10,
            cursor="hand2",
            command=self._confirmar,
        ).pack(side="right", padx=20)

    def _selecionar_mapa(self, mapa_key: str):
        self.mapa_selecionado = mapa_key
        info = self.get_mapa_info(mapa_key)
        config = self.ARENAS.get(mapa_key)
        if not info or not config:
            return

        for key, btn in self.botoes_mapa.items():
            if key == mapa_key:
                btn.config(bg=COR_ACCENT, fg=COR_TEXTO)
            else:
                btn.config(bg=COR_BG_SECUNDARIO, fg=COR_TEXTO)

        self.lbl_nome_mapa.config(text=info["nome"])
        self.lbl_descricao.config(text=info["descricao"])
        self.lbl_stats.config(
            text=(
                f"Tamanho: {info['tamanho']}\n"
                f"Formato: {info['formato']}\n"
                f"Obstaculos: {info['obstaculos']}\n"
                f"Tema: {info['tema'].capitalize()}"
            )
        )
        self._desenhar_preview(config)

    def _redraw_map_preview(self):
        config = self.ARENAS.get(self.mapa_selecionado)
        if config:
            self._desenhar_preview(config)

    def _desenhar_preview(self, config):
        canvas = self.canvas_preview
        canvas.delete("all")

        cw = canvas.winfo_width() or 400
        ch = canvas.winfo_height() or 300
        padding = 20

        escala_x = (cw - padding * 2) / config.largura
        escala_y = (ch - padding * 2) / config.altura
        escala = min(escala_x, escala_y)
        offset_x = (cw - config.largura * escala) / 2
        offset_y = (ch - config.altura * escala) / 2

        def to_canvas(x, y):
            return offset_x + x * escala, offset_y + y * escala

        cor_chao = f"#{config.cor_chao[0]:02x}{config.cor_chao[1]:02x}{config.cor_chao[2]:02x}"
        cor_borda = f"#{config.cor_borda[0]:02x}{config.cor_borda[1]:02x}{config.cor_borda[2]:02x}"

        if config.formato == "circular":
            cx, cy = to_canvas(config.largura / 2, config.altura / 2)
            raio = min(config.largura, config.altura) / 2 * escala * 0.9
            canvas.create_oval(cx - raio, cy - raio, cx + raio, cy + raio, fill=cor_chao, outline=cor_borda, width=3)
        elif config.formato == "octogono":
            pontos = [
                to_canvas(config.largura * 0.2, 0),
                to_canvas(config.largura * 0.8, 0),
                to_canvas(config.largura, config.altura * 0.2),
                to_canvas(config.largura, config.altura * 0.8),
                to_canvas(config.largura * 0.8, config.altura),
                to_canvas(config.largura * 0.2, config.altura),
                to_canvas(0, config.altura * 0.8),
                to_canvas(0, config.altura * 0.2),
            ]
            canvas.create_polygon([coord for p in pontos for coord in p], fill=cor_chao, outline=cor_borda, width=3)
        else:
            x1, y1 = to_canvas(0, 0)
            x2, y2 = to_canvas(config.largura, config.altura)
            canvas.create_rectangle(x1, y1, x2, y2, fill=cor_chao, outline=cor_borda, width=3)

        grid_cor = f"#{min(255, config.cor_chao[0] + 15):02x}{min(255, config.cor_chao[1] + 15):02x}{min(255, config.cor_chao[2] + 15):02x}"

        x = 0
        while x <= config.largura:
            p1 = to_canvas(x, 0)
            p2 = to_canvas(x, config.altura)
            canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=grid_cor, dash=(2, 4))
            x += 4.0

        y = 0
        while y <= config.altura:
            p1 = to_canvas(0, y)
            p2 = to_canvas(config.largura, y)
            canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=grid_cor, dash=(2, 4))
            y += 4.0

        for obs in config.obstaculos:
            cx, cy = to_canvas(obs.x, obs.y)
            half_w = obs.largura * escala / 2
            half_h = obs.altura * escala / 2

            cor = f"#{obs.cor[0]:02x}{obs.cor[1]:02x}{obs.cor[2]:02x}"
            cor_escura = f"#{max(0, obs.cor[0]-40):02x}{max(0, obs.cor[1]-40):02x}{max(0, obs.cor[2]-40):02x}"

            if obs.tipo in ["lava", "fogo"]:
                canvas.create_oval(cx - half_w, cy - half_h, cx + half_w, cy + half_h, fill="#FF4500", outline="#FFD700", width=2)
            elif obs.tipo == "cristal":
                pontos = [
                    (cx, cy - half_h),
                    (cx + half_w * 0.8, cy - half_h * 0.5),
                    (cx + half_w * 0.8, cy + half_h * 0.5),
                    (cx, cy + half_h),
                    (cx - half_w * 0.8, cy + half_h * 0.5),
                    (cx - half_w * 0.8, cy - half_h * 0.5),
                ]
                canvas.create_polygon([coord for p in pontos for coord in p], fill=cor, outline="white", width=1)
            elif obs.tipo in ["arvore", "palmeira"]:
                canvas.create_rectangle(cx - half_w * 0.2, cy - half_h * 0.3, cx + half_w * 0.2, cy + half_h * 0.5, fill=cor, outline="")
                canvas.create_oval(cx - half_w, cy - half_h, cx + half_w, cy, fill="#228B22", outline="#006400", width=1)
            elif obs.tipo in ["pilar", "pilar_quebrado"]:
                canvas.create_oval(cx - half_w, cy - half_h, cx + half_w, cy + half_h, fill=cor, outline=cor_escura, width=2)
            elif obs.tipo == "gelo":
                canvas.create_rectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h, fill="#ADD8E6", outline="#87CEEB", width=2)
            elif obs.tipo == "nucleo":
                canvas.create_oval(cx - half_w * 1.3, cy - half_h * 1.3, cx + half_w * 1.3, cy + half_h * 1.3, fill="#1E3A5F", outline="")
                canvas.create_oval(cx - half_w, cy - half_h, cx + half_w, cy + half_h, fill=cor, outline="white", width=2)
            else:
                canvas.create_rectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h, fill=cor, outline=cor_escura, width=1)

        p1_x, p1_y = to_canvas(config.largura * 0.2, config.altura / 2)
        p2_x, p2_y = to_canvas(config.largura * 0.8, config.altura / 2)

        canvas.create_oval(p1_x - 8, p1_y - 8, p1_x + 8, p1_y + 8, fill="#3498DB", outline="white", width=2)
        canvas.create_text(p1_x, p1_y, text="1", fill="white", font=("Arial", 8, "bold"))
        canvas.create_oval(p2_x - 8, p2_y - 8, p2_x + 8, p2_y + 8, fill="#E74C3C", outline="white", width=2)
        canvas.create_text(p2_x, p2_y, text="2", fill="white", font=("Arial", 8, "bold"))
        canvas.create_text(cw / 2, ch - 10, text="P1 spawn   |   P2 spawn", fill="#8a93a5", font=("Segoe UI", 8))

    def _confirmar(self):
        info = self.get_mapa_info(self.mapa_selecionado)
        self.callback(self.mapa_selecionado, info)
        self.destroy()
