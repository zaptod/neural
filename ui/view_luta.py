"""
ARENA DE COMBATE - NEURAL FIGHTS
Tela de seleção de lutadores para batalha
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simulacao
from ui.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_P1, COR_P2, CORES_CLASSE
)


class TelaLuta(tk.Frame):
    """Tela de seleção de lutadores"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)
        
        self.personagem_p1 = None
        self.personagem_p2 = None
        
        self.setup_ui()

    def setup_ui(self):
        """Configura a interface"""
        # === HEADER ===
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
            header, text="⚔️ ARENA DE COMBATE",
            font=("Arial", 18, "bold"), bg=COR_HEADER, fg=COR_TEXTO
        ).pack(side="left", padx=20)

        # === FOOTER (botão iniciar) ===
        footer = tk.Frame(self, bg=COR_BG)
        footer.pack(fill="x", side="bottom", pady=15)
        
        self.btn_iniciar = tk.Button(
            footer, text="⚔️  INICIAR BATALHA  ⚔️",
            font=("Arial", 16, "bold"), 
            bg=COR_TEXTO_DIM, fg=COR_TEXTO,
            bd=0, padx=40, pady=12,
            state="disabled",
            command=self.iniciar_luta
        )
        self.btn_iniciar.pack()

        # === ÁREA PRINCIPAL ===
        main = tk.Frame(self, bg=COR_BG)
        main.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configura 3 colunas com grid
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_columnconfigure(2, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # === PLAYER 1 ===
        frame_p1 = tk.Frame(main, bg=COR_BG_SECUNDARIO, bd=2, relief="ridge")
        frame_p1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Título P1
        tk.Label(frame_p1, text="PLAYER 1", font=("Impact", 20), 
                 bg=COR_P1, fg=COR_TEXTO).pack(fill="x", pady=5)
        
        # Preview P1
        self.canvas_p1 = tk.Canvas(frame_p1, width=200, height=200, bg=COR_BG, highlightthickness=0)
        self.canvas_p1.pack(pady=10)
        
        self.lbl_nome_p1 = tk.Label(frame_p1, text="—", font=("Arial", 12, "bold"),
                                     bg=COR_BG_SECUNDARIO, fg=COR_TEXTO)
        self.lbl_nome_p1.pack()
        
        self.lbl_stats_p1 = tk.Label(frame_p1, text="", font=("Arial", 9),
                                      bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, justify="center")
        self.lbl_stats_p1.pack(pady=5)
        
        # Lista P1
        tk.Label(frame_p1, text="Selecione:", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", padx=10)
        
        frame_lista_p1 = tk.Frame(frame_p1, bg=COR_BG_SECUNDARIO)
        frame_lista_p1.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.listbox_p1 = tk.Listbox(
            frame_lista_p1, bg=COR_BG, fg=COR_TEXTO,
            selectbackground=COR_P1, selectforeground=COR_TEXTO,
            font=("Arial", 11), bd=0, highlightthickness=1,
            highlightcolor=COR_P1, activestyle="none"
        )
        scroll_p1 = ttk.Scrollbar(frame_lista_p1, orient="vertical", command=self.listbox_p1.yview)
        self.listbox_p1.configure(yscrollcommand=scroll_p1.set)
        
        self.listbox_p1.pack(side="left", fill="both", expand=True)
        scroll_p1.pack(side="right", fill="y")
        
        self.listbox_p1.bind("<<ListboxSelect>>", lambda e: self._on_select_p1())

        # === VS CENTRAL ===
        frame_vs = tk.Frame(main, bg=COR_BG, width=100)
        frame_vs.grid(row=0, column=1, sticky="ns", padx=10)
        
        tk.Label(frame_vs, text="", bg=COR_BG).pack(expand=True)  # Espaçador
        tk.Label(frame_vs, text="VS", font=("Impact", 50), bg=COR_BG, fg=COR_ACCENT).pack()
        
        # Config rápida
        frame_cfg = tk.Frame(frame_vs, bg=COR_BG_SECUNDARIO)
        frame_cfg.pack(pady=20)
        
        tk.Label(frame_cfg, text="Rounds:", font=("Arial", 9), 
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack()
        self.var_best_of = tk.StringVar(value="1")
        ttk.Combobox(frame_cfg, textvariable=self.var_best_of,
                     values=["1", "3", "5"], state="readonly", width=5).pack(pady=5)
        
        self.var_cenario = tk.StringVar(value="Arena")
        tk.Label(frame_vs, text="", bg=COR_BG).pack(expand=True)  # Espaçador

        # === PLAYER 2 ===
        frame_p2 = tk.Frame(main, bg=COR_BG_SECUNDARIO, bd=2, relief="ridge")
        frame_p2.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        # Título P2
        tk.Label(frame_p2, text="PLAYER 2", font=("Impact", 20), 
                 bg=COR_P2, fg=COR_TEXTO).pack(fill="x", pady=5)
        
        # Preview P2
        self.canvas_p2 = tk.Canvas(frame_p2, width=200, height=200, bg=COR_BG, highlightthickness=0)
        self.canvas_p2.pack(pady=10)
        
        self.lbl_nome_p2 = tk.Label(frame_p2, text="—", font=("Arial", 12, "bold"),
                                     bg=COR_BG_SECUNDARIO, fg=COR_TEXTO)
        self.lbl_nome_p2.pack()
        
        self.lbl_stats_p2 = tk.Label(frame_p2, text="", font=("Arial", 9),
                                      bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, justify="center")
        self.lbl_stats_p2.pack(pady=5)
        
        # Lista P2
        tk.Label(frame_p2, text="Selecione:", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", padx=10)
        
        frame_lista_p2 = tk.Frame(frame_p2, bg=COR_BG_SECUNDARIO)
        frame_lista_p2.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.listbox_p2 = tk.Listbox(
            frame_lista_p2, bg=COR_BG, fg=COR_TEXTO,
            selectbackground=COR_P2, selectforeground=COR_TEXTO,
            font=("Arial", 11), bd=0, highlightthickness=1,
            highlightcolor=COR_P2, activestyle="none"
        )
        scroll_p2 = ttk.Scrollbar(frame_lista_p2, orient="vertical", command=self.listbox_p2.yview)
        self.listbox_p2.configure(yscrollcommand=scroll_p2.set)
        
        self.listbox_p2.pack(side="left", fill="both", expand=True)
        scroll_p2.pack(side="right", fill="y")
        
        self.listbox_p2.bind("<<ListboxSelect>>", lambda e: self._on_select_p2())

    def atualizar_dados(self):
        """Atualiza listas de personagens"""
        # Limpa
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
        
        # Popula listas
        for p in personagens:
            classe = getattr(p, 'classe', 'Guerreiro')
            texto = f"{p.nome} ({classe})"
            self.listbox_p1.insert(tk.END, texto)
            self.listbox_p2.insert(tk.END, texto)
        
        # Auto-seleciona
        if len(personagens) >= 1:
            self.listbox_p1.selection_set(0)
            self._on_select_p1()
        if len(personagens) >= 2:
            self.listbox_p2.selection_set(1)
            self._on_select_p2()
        elif len(personagens) == 1:
            self.listbox_p2.selection_set(0)
            self._on_select_p2()

    def _on_select_p1(self):
        """Callback quando P1 seleciona"""
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
        """Callback quando P2 seleciona"""
        sel = self.listbox_p2.curselection()
        if not sel:
            return
        idx = sel[0]
        personagens = self.controller.lista_personagens
        if idx < len(personagens):
            self.personagem_p2 = personagens[idx]
            self._desenhar_preview(self.personagem_p2, self.canvas_p2, self.lbl_nome_p2, self.lbl_stats_p2, COR_P2)
        self._atualizar_botao()

    def _desenhar_preview(self, p, canvas, lbl_nome, lbl_stats, cor_borda):
        """Desenha preview do personagem"""
        canvas.delete("all")
        
        if not p:
            lbl_nome.config(text="—")
            lbl_stats.config(text="")
            return
        
        lbl_nome.config(text=p.nome)
        
        cx, cy = 100, 100
        cor = f"#{p.cor_r:02x}{p.cor_g:02x}{p.cor_b:02x}"
        classe = getattr(p, 'classe', 'Guerreiro')
        cor_classe = CORES_CLASSE.get(classe, "#808080")
        
        # Aura
        canvas.create_oval(cx-60, cy-60, cx+60, cy+60, outline=cor_classe, width=2, dash=(4,2))
        
        # Personagem
        raio = min(p.tamanho * 6, 40)
        canvas.create_oval(cx-raio, cy-raio, cx+raio, cy+raio, fill=cor, outline=cor_borda, width=3)
        
        # Classe
        canvas.create_text(cx, cy+70, text=classe, font=("Arial", 10, "bold"), fill=cor_classe)
        
        # Arma
        if p.nome_arma:
            arma = next((a for a in self.controller.lista_armas if a.nome == p.nome_arma), None)
            if arma:
                cor_arma = f"#{arma.r:02x}{arma.g:02x}{arma.b:02x}"
                canvas.create_line(cx+raio, cy, cx+raio+40, cy, fill=cor_arma, width=4)
        
        # Stats
        arma_txt = p.nome_arma if p.nome_arma else "Mãos Vazias"
        stats = f"VEL: {p.velocidade:.1f} | RES: {p.resistencia:.1f}\n🗡️ {arma_txt}"
        lbl_stats.config(text=stats)

    def _atualizar_botao(self):
        """Atualiza estado do botão"""
        if self.personagem_p1 and self.personagem_p2:
            self.btn_iniciar.config(state="normal", bg=COR_ACCENT)
        else:
            self.btn_iniciar.config(state="disabled", bg=COR_TEXTO_DIM)

    def iniciar_luta(self):
        """Inicia a simulação"""
        if not self.personagem_p1 or not self.personagem_p2:
            messagebox.showwarning("Atenção", "Selecione dois campeões!")
            return
        
        match_data = {
            "p1_nome": self.personagem_p1.nome,
            "p2_nome": self.personagem_p2.nome,
            "cenario": self.var_cenario.get(),
            "best_of": int(self.var_best_of.get()),
        }
        
        try:
            with open("match_config.json", "w", encoding="utf-8") as f:
                json.dump(match_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")
            return
        
        self.controller.withdraw()
        
        try:
            sim = simulacao.Simulador()
            sim.run()
        except Exception as e:
            messagebox.showerror("Erro", f"Simulação falhou:\n{e}")
        
        self.controller.deiconify()

    # Compatibilidade
    def atualizar_previews(self, event=None):
        pass