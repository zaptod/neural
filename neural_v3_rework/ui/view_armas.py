"""
FORJA DE ARMAS - NEURAL FIGHTS
Sistema de criação de armas com Wizard guiado
"""
import tkinter as tk
from tkinter import ttk, messagebox
import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    Arma, TIPOS_ARMA, LISTA_TIPOS_ARMA, RARIDADES, LISTA_RARIDADES,
    ENCANTAMENTOS, LISTA_ENCANTAMENTOS, get_raridade_data, get_tipo_arma_data,
    validar_arma_personagem
)
from data import carregar_armas, salvar_lista_armas, carregar_personagens
from data.app_state import AppState
from core import SKILL_DB
from ui.theme import COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS, COR_TEXTO, COR_TEXTO_DIM, CORES_RARIDADE

class TelaArmas(tk.Frame):
    """Tela principal da Forja de Armas com sistema Wizard"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)
        self.indice_em_edicao = None
        
        # Estado do Wizard
        self.passo_atual = 1
        self.total_passos = 6
        
        # Dados da arma sendo criada
        self.dados_arma = {
            "nome": "",
            "tipo": "Reta",
            "raridade": "Comum",
            "estilo": "",
            "dano": 10,
            "peso": 5,
            "cores": {"r": 200, "g": 200, "b": 200},
            "habilidades": [],
            "encantamentos": [],
            "cabo_dano": False,
            "afinidade_elemento": None,
        }
        
        self.setup_ui()

        # Subscribe: refresh when characters change (weapon validation needs them)
        AppState.get().subscribe("characters_changed", self._on_chars_changed)

    def _on_chars_changed(self, _data=None):
        if hasattr(self, "atualizar_dados"):
            self.atualizar_dados()

    def setup_ui(self):
        """Configura a interface principal"""
        # Header
        self.criar_header()
        
        # Container principal dividido em 3 partes — grid responsivo
        main = tk.Frame(self, bg=COR_BG)
        main.pack(fill="both", expand=True, padx=10, pady=5)
        main.grid_columnconfigure(0, weight=3, minsize=300)  # wizard
        main.grid_columnconfigure(1, weight=4, minsize=200)  # centro/preview
        main.grid_columnconfigure(2, weight=2, minsize=220)  # lista
        main.grid_rowconfigure(0, weight=1)

        # Esquerda: Wizard Steps
        self.frame_wizard = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        self.frame_wizard.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.frame_wizard.grid_rowconfigure(1, weight=1)
        self.frame_wizard.grid_columnconfigure(0, weight=1)

        # Centro: Preview e controles
        self.frame_centro = tk.Frame(main, bg=COR_BG)
        self.frame_centro.grid(row=0, column=1, sticky="nsew", padx=5)

        # Direita: Lista de armas
        self.frame_lista = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        self.frame_lista.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # Configura cada seção
        self.setup_wizard()
        self.setup_preview()
        self.setup_lista()
        
        # Inicia no passo 1
        self.mostrar_passo(1)

    def criar_header(self):
        """Cria o header com navegação"""
        header = tk.Frame(self, bg=COR_HEADER, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # Botão voltar
        btn_voltar = tk.Button(
            header, text="< VOLTAR", bg=COR_ACCENT, fg=COR_TEXTO,
            font=("Arial", 10, "bold"), bd=0, padx=15,
            command=lambda: self.controller.show_frame("MenuPrincipal")
        )
        btn_voltar.pack(side="left", padx=10, pady=15)
        
        # Título
        tk.Label(
            header, text="FORJA DE ARMAS", 
            font=("Helvetica", 20, "bold"), bg=COR_HEADER, fg=COR_TEXTO
        ).pack(side="left", padx=20)
        
        # Indicador de progresso
        self.frame_progresso = tk.Frame(header, bg=COR_HEADER)
        self.frame_progresso.pack(side="right", padx=20)
        
        self.labels_progresso = []
        nomes_passos = ["Tipo", "Raridade", "Visual", "Habilidades", "Finalizar"]
        for i, nome in enumerate(nomes_passos, 1):
            cor = COR_SUCCESS if i == 1 else COR_TEXTO_DIM
            lbl = tk.Label(
                self.frame_progresso, text=f"{i}.{nome}",
                font=("Arial", 9), bg=COR_HEADER, fg=cor
            )
            lbl.pack(side="left", padx=5)
            self.labels_progresso.append(lbl)

    def atualizar_progresso(self):
        """Atualiza os indicadores de progresso"""
        for i, lbl in enumerate(self.labels_progresso, 1):
            if i < self.passo_atual:
                lbl.config(fg="#00ff88")  # Completo
            elif i == self.passo_atual:
                lbl.config(fg=COR_SUCCESS)  # Atual
            else:
                lbl.config(fg=COR_TEXTO_DIM)  # Futuro

    def setup_wizard(self):
        """Configura o frame do wizard"""
        # Título do passo
        self.lbl_passo_titulo = tk.Label(
            self.frame_wizard, text="", 
            font=("Helvetica", 14, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        )
        self.lbl_passo_titulo.grid(row=0, column=0, pady=(15, 5), sticky="ew")
        
        self.lbl_passo_desc = tk.Label(
            self.frame_wizard, text="", 
            font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM,
            wraplength=300
        )
        self.lbl_passo_desc.grid(row=0, column=0, pady=(40, 0), sticky="ew")
        # wraplength will be updated dynamically on resize
        self.frame_wizard.bind("<Configure>", self._on_wizard_resize)

        # Container scrollável para conteúdo do passo (evita overflow em telas pequenas)
        scroll_container = tk.Frame(self.frame_wizard, bg=COR_BG_SECUNDARIO)
        scroll_container.grid(row=1, column=0, sticky="nsew", padx=5)
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)

        self._canvas_wizard = tk.Canvas(scroll_container, bg=COR_BG_SECUNDARIO, highlightthickness=0)
        _scrollbar_wizard = ttk.Scrollbar(scroll_container, orient="vertical", command=self._canvas_wizard.yview)
        self._canvas_wizard.configure(yscrollcommand=_scrollbar_wizard.set)

        self._canvas_wizard.grid(row=0, column=0, sticky="nsew")
        _scrollbar_wizard.grid(row=0, column=1, sticky="ns")
        scroll_container.grid_columnconfigure(0, weight=1)

        self.frame_conteudo_passo = tk.Frame(self._canvas_wizard, bg=COR_BG_SECUNDARIO)
        self._window_id = self._canvas_wizard.create_window((0, 0), window=self.frame_conteudo_passo, anchor="nw")

        def _update_scroll(event=None):
            self._canvas_wizard.configure(scrollregion=self._canvas_wizard.bbox("all"))
            # keep inner frame width in sync with canvas width
            canvas_w = self._canvas_wizard.winfo_width()
            if canvas_w > 1:
                self._canvas_wizard.itemconfig(self._window_id, width=canvas_w)

        self.frame_conteudo_passo.bind("<Configure>", _update_scroll)
        self._canvas_wizard.bind("<Configure>", _update_scroll)

        # Mousewheel scroll
        def _on_mousewheel(event):
            self._canvas_wizard.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._canvas_wizard.bind_all("<MouseWheel>", _on_mousewheel)

        # Botões de navegação — fixos na base, sempre visíveis
        frame_nav = tk.Frame(self.frame_wizard, bg=COR_BG_SECUNDARIO)
        frame_nav.grid(row=2, column=0, sticky="ew", pady=10, padx=10)
        frame_nav.grid_columnconfigure(0, weight=1)
        frame_nav.grid_columnconfigure(1, weight=1)
        
        self.btn_anterior = tk.Button(
            frame_nav, text="< Anterior", bg=COR_BG, fg=COR_TEXTO,
            font=("Arial", 10), bd=0, padx=20, pady=8,
            command=self.passo_anterior
        )
        self.btn_anterior.grid(row=0, column=0, sticky="w")
        
        self.btn_proximo = tk.Button(
            frame_nav, text="Proximo >", bg=COR_ACCENT, fg=COR_TEXTO,
            font=("Arial", 10, "bold"), bd=0, padx=20, pady=8,
            command=self.passo_proximo
        )
        self.btn_proximo.grid(row=0, column=1, sticky="e")

    def _on_wizard_resize(self, event=None):
        """Adjust wraplength of description label to match wizard width."""
        w = self.frame_wizard.winfo_width()
        if w > 40:
            self.lbl_passo_desc.config(wraplength=max(w - 40, 100))

    def setup_preview(self):
        """Configura o preview da arma"""
        # Título
        tk.Label(
            self.frame_centro, text="PREVIEW", 
            font=("Arial", 12, "bold"), bg=COR_BG, fg=COR_TEXTO
        ).pack(pady=(10, 5))
        
        # Canvas do preview — expande com a janela
        self.canvas_preview = tk.Canvas(
            self.frame_centro, bg=COR_BG_SECUNDARIO, 
            highlightthickness=2, highlightbackground=COR_ACCENT
        )
        self.canvas_preview.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Info da validação de tamanho
        self.frame_validacao = tk.Frame(self.frame_centro, bg=COR_BG)
        self.frame_validacao.pack(fill="x", padx=10, pady=5)
        
        self.lbl_validacao = tk.Label(
            self.frame_validacao, text="", 
            font=("Arial", 10), bg=COR_BG, fg=COR_TEXTO_DIM
        )
        self.lbl_validacao.pack()
        
        # Resumo dos stats
        self.frame_stats = tk.Frame(self.frame_centro, bg=COR_BG_SECUNDARIO)
        self.frame_stats.pack(fill="x", padx=10, pady=5)
        
        self.criar_resumo_stats()

    def criar_resumo_stats(self):
        """Cria o resumo de stats da arma"""
        for widget in self.frame_stats.winfo_children():
            widget.destroy()
        
        # Grid de stats
        stats = [
            ("Nome", self.dados_arma["nome"] or "???"),
            ("Tipo", self.dados_arma["tipo"]),
            ("Raridade", self.dados_arma["raridade"]),
            ("Dano", f"{self.dados_arma['dano']:.0f}"),
            ("Peso", f"{self.dados_arma['peso']:.1f} kg"),
            ("Skills", str(len(self.dados_arma["habilidades"]))),
        ]
        
        for i, (nome, valor) in enumerate(stats):
            row = i // 3
            col = i % 3
            
            frame = tk.Frame(self.frame_stats, bg=COR_BG_SECUNDARIO)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            
            tk.Label(
                frame, text=f"{nome}:", 
                font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
            ).pack(side="left")
            
            cor = CORES_RARIDADE.get(valor, COR_TEXTO) if nome == "Raridade" else COR_TEXTO
            tk.Label(
                frame, text=valor, 
                font=("Arial", 9, "bold"), bg=COR_BG_SECUNDARIO, fg=cor
            ).pack(side="left", padx=5)

    def setup_lista(self):
        """Configura a lista de armas existentes"""
        tk.Label(
            self.frame_lista, text="ARSENAL", 
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(pady=(15, 10))
        
        # Treeview com scroll
        frame_tree = tk.Frame(self.frame_lista, bg=COR_BG_SECUNDARIO)
        frame_tree.pack(fill="both", expand=True, padx=10)
        
        scroll = ttk.Scrollbar(frame_tree)
        scroll.pack(side="right", fill="y")
        
        cols = ("Nome", "Tipo", "Raridade")
        self.tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings", height=15,
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree.yview)
        
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90)
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar_arma)
        
        # Botões
        frame_btns = tk.Frame(self.frame_lista, bg=COR_BG_SECUNDARIO)
        frame_btns.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            frame_btns, text="Deletar", bg="#cc3333", fg=COR_TEXTO,
            font=("Arial", 9), bd=0, padx=10, pady=5,
            command=self.deletar_arma
        ).pack(side="left")
        
        tk.Button(
            frame_btns, text="Editar", bg=COR_SUCCESS, fg=COR_BG,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=5,
            command=self.editar_arma
        ).pack(side="right")
        
        tk.Button(
            frame_btns, text="Nova", bg=COR_ACCENT, fg=COR_TEXTO,
            font=("Arial", 9), bd=0, padx=10, pady=5,
            command=self.nova_arma
        ).pack(side="right", padx=5)

    # =========================================================================
    # PASSOS DO WIZARD
    # =========================================================================
    
    def mostrar_passo(self, passo):
        """Mostra o passo especificado do wizard"""
        self.passo_atual = passo
        self.atualizar_progresso()
        
        # Limpa conteúdo anterior
        for widget in self.frame_conteudo_passo.winfo_children():
            widget.destroy()
        
        # Mostra passo apropriado
        if passo == 1:
            self.passo_tipo()
        elif passo == 2:
            self.passo_raridade()
        elif passo == 3:
            self.passo_visual()
        elif passo == 4:
            self.passo_habilidades()
        elif passo == 5:
            self.passo_finalizar()
        
        # Atualiza botões
        self.btn_anterior.config(state="normal" if passo > 1 else "disabled")
        self.btn_proximo.config(
            text="FORJAR!" if passo == 5 else "Proximo >",
            bg="#00ff88" if passo == 5 else COR_ACCENT
        )
        
        self.atualizar_preview()
        self.criar_resumo_stats()

    def passo_anterior(self):
        """Volta ao passo anterior"""
        if self.passo_atual > 1:
            self.mostrar_passo(self.passo_atual - 1)

    def passo_proximo(self):
        """Avança para o próximo passo"""
        if self.passo_atual < 5:
            self.mostrar_passo(self.passo_atual + 1)
        else:
            self.salvar_arma()

    # -------------------------------------------------------------------------
    # PASSO 1: TIPO DA ARMA
    # -------------------------------------------------------------------------
    def passo_tipo(self):
        """Passo 1: Escolha do tipo de arma"""
        self.lbl_passo_titulo.config(text="1. TIPO DE ARMA")
        self.lbl_passo_desc.config(text="Escolha a categoria base da sua arma. Cada tipo tem comportamento unico em combate.")
        
        # Nome da arma
        frame_nome = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_nome.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            frame_nome, text="Nome da Arma:", 
            font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        self.entry_nome = tk.Entry(
            frame_nome, font=("Arial", 12), bg=COR_BG, fg=COR_TEXTO,
            insertbackground=COR_TEXTO
        )
        self.entry_nome.pack(fill="x", pady=5)
        self.entry_nome.insert(0, self.dados_arma["nome"])
        self.entry_nome.bind("<KeyRelease>", lambda e: self.atualizar_dado("nome", self.entry_nome.get()))
        
        # Grid de tipos
        tk.Label(
            self.frame_conteudo_passo, text="Categoria:", 
            font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w", pady=(10, 5))
        
        frame_tipos = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_tipos.pack(fill="x")
        
        self.var_tipo = tk.StringVar(value=self.dados_arma["tipo"])
        
        # Organiza em grid 2x4
        for i, tipo in enumerate(LISTA_TIPOS_ARMA):
            dados = TIPOS_ARMA[tipo]
            row = i // 2
            col = i % 2
            
            frame = tk.Frame(frame_tipos, bg=COR_BG, bd=1, relief="solid")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            rb = tk.Radiobutton(
                frame, text=tipo, variable=self.var_tipo, value=tipo,
                font=("Arial", 11, "bold"), bg=COR_BG, fg=COR_TEXTO,
                selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
                command=lambda t=tipo: self.selecionar_tipo(t)
            )
            rb.pack(anchor="w", padx=10, pady=(5, 0))
            
            tk.Label(
                frame, text=dados["descricao"],
                font=("Arial", 8), bg=COR_BG, fg=COR_TEXTO_DIM,
                wraplength=160, justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 5))
        
        frame_tipos.columnconfigure(0, weight=1)
        frame_tipos.columnconfigure(1, weight=1)

        # ── Seletor de Estilo (atualiza dinamicamente ao escolher o tipo) ──
        tk.Label(
            self.frame_conteudo_passo, text="Estilo / Variante:",
            font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w", pady=(14, 4))

        frame_estilo_t1 = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_estilo_t1.pack(fill="x")

        self.combo_estilo_t1 = ttk.Combobox(frame_estilo_t1, state="readonly", font=("Arial", 11))
        self.combo_estilo_t1.pack(fill="x", ipady=4)

        def _atualizar_estilos_t1(tipo):
            estilos = TIPOS_ARMA[tipo]["estilos"]
            self.combo_estilo_t1["values"] = estilos
            estilo_atual = self.dados_arma.get("estilo") or estilos[0]
            self.combo_estilo_t1.set(estilo_atual if estilo_atual in estilos else estilos[0])
            self.dados_arma["estilo"] = self.combo_estilo_t1.get()
            self.atualizar_preview()
            self.criar_resumo_stats()

        self.combo_estilo_t1.bind("<<ComboboxSelected>>", lambda e: (
            self.dados_arma.update({"estilo": self.combo_estilo_t1.get()}),
            self.atualizar_preview(),
            self.criar_resumo_stats(),
        ))

        # Popula com o tipo já selecionado
        _atualizar_estilos_t1(self.dados_arma["tipo"])

        # Guarda referência para que selecionar_tipo() possa atualizar o combo
        self._atualizar_estilos_t1 = _atualizar_estilos_t1

    def selecionar_tipo(self, tipo):
        """Atualiza o tipo selecionado"""
        self.dados_arma["tipo"] = tipo
        dados_tipo = TIPOS_ARMA[tipo]
        self.dados_arma["estilo"] = dados_tipo["estilos"][0]
        # Atualiza o combo de estilo do Passo 1 se ele existir
        if hasattr(self, "_atualizar_estilos_t1"):
            self._atualizar_estilos_t1(tipo)
        self.atualizar_preview()
        self.criar_resumo_stats()


    # -------------------------------------------------------------------------
    # PASSO 2: RARIDADE
    # -------------------------------------------------------------------------
    def passo_raridade(self):
        """Passo 2: Escolha da raridade"""
        self.lbl_passo_titulo.config(text="2. RARIDADE")
        self.lbl_passo_desc.config(text="A raridade define o poder base, slots de habilidade e efeitos visuais da arma.")
        
        self.var_raridade = tk.StringVar(value=self.dados_arma["raridade"])
        
        for raridade in LISTA_RARIDADES:
            dados = RARIDADES[raridade]
            cor = CORES_RARIDADE[raridade]
            
            frame = tk.Frame(self.frame_conteudo_passo, bg=COR_BG, bd=2, relief="ridge")
            frame.pack(fill="x", pady=3)
            
            # Header com nome e cor
            header = tk.Frame(frame, bg=COR_BG)
            header.pack(fill="x", padx=10, pady=5)
            
            rb = tk.Radiobutton(
                header, text=raridade, variable=self.var_raridade, value=raridade,
                font=("Arial", 12, "bold"), bg=COR_BG, fg=cor,
                selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
                command=lambda r=raridade: self.selecionar_raridade(r)
            )
            rb.pack(side="left")
            
            # Stats
            stats_text = f"Dano:{dados['mod_dano']:.0%} Crit:{dados['mod_critico']:.0%} Vel:{dados['mod_velocidade_ataque']:.0%} Slots:{dados['slots_habilidade']}"
            tk.Label(
                header, text=stats_text,
                font=("Arial", 9), bg=COR_BG, fg=COR_TEXTO_DIM
            ).pack(side="right")
            
            # Descrição
            tk.Label(
                frame, text=dados["descricao"],
                font=("Arial", 9), bg=COR_BG, fg=COR_TEXTO_DIM
            ).pack(anchor="w", padx=10, pady=(0, 5))

    def selecionar_raridade(self, raridade):
        """Atualiza a raridade selecionada"""
        self.dados_arma["raridade"] = raridade
        # Aplica modificadores
        rar_data = RARIDADES[raridade]
        self.dados_arma["dano"] = 10 * rar_data["mod_dano"]
        self.atualizar_preview()
        self.criar_resumo_stats()

    # -------------------------------------------------------------------------
    # PASSO 4: VISUAL
    # -------------------------------------------------------------------------
    def passo_visual(self):
        """Passo 4: Cores e aparência"""
        self.lbl_passo_titulo.config(text="4. VISUAL")
        self.lbl_passo_desc.config(text="Personalize as cores da sua arma.")
        
        # Sliders RGB
        cores = self.dados_arma["cores"]
        
        frame_cores = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_cores.pack(fill="x", pady=10)
        
        self.scales_cor = {}
        for i, (comp, nome) in enumerate([("r", "Vermelho"), ("g", "Verde"), ("b", "Azul")]):
            tk.Label(
                frame_cores, text=nome, 
                bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, font=("Arial", 10)
            ).grid(row=i, column=0, sticky="w", pady=5)
            
            scale = tk.Scale(
                frame_cores, from_=0, to=255, orient="horizontal",
                bg=COR_BG_SECUNDARIO, fg=COR_TEXTO,
                command=lambda v, c=comp: self.atualizar_cor(c, int(v))
            )
            scale.set(cores[comp])
            scale.grid(row=i, column=1, sticky="ew", pady=5)
            self.scales_cor[comp] = scale
        
        frame_cores.columnconfigure(1, weight=1)
        
        # Preview de cor
        self.frame_cor_preview = tk.Frame(
            self.frame_conteudo_passo, bg=f"#{cores['r']:02x}{cores['g']:02x}{cores['b']:02x}",
            height=50, bd=2, relief="ridge"
        )
        self.frame_cor_preview.pack(fill="x", pady=10)
        
        # Presets de cores
        tk.Label(
            self.frame_conteudo_passo, text="Presets:", 
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w", pady=(10, 5))
        
        frame_presets = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_presets.pack(fill="x")
        
        presets = [
            ("Aco", 200, 200, 210),
            ("Bronze", 205, 127, 50),
            ("Ouro", 255, 215, 0),
            ("Obsidiana", 30, 30, 40),
            ("Jade", 0, 168, 107),
            ("Rubi", 224, 17, 95),
            ("Safira", 15, 82, 186),
            ("Ametista", 153, 102, 204),
        ]
        
        for nome, r, g, b in presets:
            btn = tk.Button(
                frame_presets, text=nome, 
                bg=f"#{r:02x}{g:02x}{b:02x}", 
                fg="white" if (r + g + b) < 400 else "black",
                font=("Arial", 8), bd=0, padx=8, pady=3,
                command=lambda r=r, g=g, b=b: self.aplicar_preset_cor(r, g, b)
            )
            btn.pack(side="left", padx=2, pady=2)

    def atualizar_cor(self, componente, valor):
        """Atualiza uma cor"""
        self.dados_arma["cores"][componente] = valor
        cores = self.dados_arma["cores"]
        self.frame_cor_preview.config(bg=f"#{cores['r']:02x}{cores['g']:02x}{cores['b']:02x}")
        self.atualizar_preview()

    def aplicar_preset_cor(self, r, g, b):
        """Aplica um preset de cor"""
        self.dados_arma["cores"] = {"r": r, "g": g, "b": b}
        for comp, val in [("r", r), ("g", g), ("b", b)]:
            self.scales_cor[comp].set(val)
        self.frame_cor_preview.config(bg=f"#{r:02x}{g:02x}{b:02x}")
        self.atualizar_preview()

    # -------------------------------------------------------------------------
    # PASSO 5: HABILIDADES (Visual Edition)
    # -------------------------------------------------------------------------

    # ── Constantes de cor por elemento (hex) ──
    _ELEMENTO_CORES = {
        "FOGO": "#FF6400", "GELO": "#64D4FF", "RAIO": "#FFFF64",
        "TREVAS": "#7800B4", "LUZ": "#FFFFC8", "NATUREZA": "#50DC50",
        "ARCANO": "#C864FF", "CAOS": "#FF32C8", "SANGUE": "#B4001E",
        "VOID": "#320050", "TEMPO": "#C8B4FF", "GRAVITACAO": "#6432C8",
    }
    _TIPO_ICONES = {
        "PROJETIL": "\u27B3", "BEAM": "\u2588\u2588", "AREA": "\u25CE",
        "DASH": "\u21E8", "BUFF": "\u2B06", "SUMMON": "\u2726",
        "TRAP": "\u25A9", "TRANSFORM": "\u21BB", "CHANNEL": "\u223F",
        "NADA": "\u2013",
    }

    def passo_habilidades(self):
        """Passo 5: Habilidades e encantamentos — versão visual"""
        self.lbl_passo_titulo.config(text="5. HABILIDADES")

        raridade = self.dados_arma["raridade"]
        rar_data = RARIDADES[raridade]
        max_slots = rar_data["slots_habilidade"]
        max_enc = rar_data["max_encantamentos"]

        self.lbl_passo_desc.config(
            text=f"Raridade {raridade}: {max_slots} slot(s) de habilidade, {max_enc} encantamento(s)"
        )

        # ── Container principal: esquerda (slots) | direita (detalhes) ──
        main = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(0, weight=1, minsize=220)
        main.grid_columnconfigure(1, weight=2, minsize=300)
        main.grid_rowconfigure(0, weight=1)

        # ===============================================================
        # COLUNA ESQUERDA — slots + filtros
        # ===============================================================
        left = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        tk.Label(left, text="Habilidades:", font=("Arial", 11, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", pady=(5, 2))

        # Filtro por elemento
        filt_f = tk.Frame(left, bg=COR_BG_SECUNDARIO)
        filt_f.pack(fill="x", pady=(0, 6))
        tk.Label(filt_f, text="Filtro:", bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM,
                 font=("Arial", 9)).pack(side="left")
        elementos = ["Todos"] + sorted({v.get("elemento", "") for v in SKILL_DB.values() if v.get("elemento")})
        self._filtro_elemento = ttk.Combobox(filt_f, values=elementos, state="readonly", width=14)
        self._filtro_elemento.set("Todos")
        self._filtro_elemento.pack(side="left", padx=4)

        tipos = ["Todos"] + sorted({v.get("tipo", "") for v in SKILL_DB.values() if v.get("tipo") and v["tipo"] != "NADA"})
        self._filtro_tipo = ttk.Combobox(filt_f, values=tipos, state="readonly", width=12)
        self._filtro_tipo.set("Todos")
        self._filtro_tipo.pack(side="left", padx=2)

        self._filtro_elemento.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro_skills())
        self._filtro_tipo.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro_skills())

        # Slots de skill (comboboxes com preview ao hover/select)
        self.combos_skill = []
        self._skill_custo_labels = []
        for i in range(max_slots):
            sf = tk.Frame(left, bg=COR_BG)
            sf.pack(fill="x", pady=3, padx=2)

            tk.Label(sf, text=f"Slot {i+1}:", bg=COR_BG, fg=COR_TEXTO,
                     font=("Arial", 10, "bold"), width=6).pack(side="left", padx=(4, 2))

            combo = ttk.Combobox(sf, values=self._lista_skills_filtrada(), state="readonly", width=22)
            combo.pack(side="left", padx=2)

            # preenche com dados existentes
            if i < len(self.dados_arma["habilidades"]):
                hab = self.dados_arma["habilidades"][i]
                combo.set(hab.get("nome", "Nenhuma") if isinstance(hab, dict) else (str(hab) if hab else "Nenhuma"))
            else:
                combo.set("Nenhuma")

            combo.bind("<<ComboboxSelected>>", lambda e, idx=i: self._on_skill_selected(idx))
            self.combos_skill.append(combo)

            lbl_custo = tk.Label(sf, text="", bg=COR_BG, fg=COR_SUCCESS,
                                 font=("Arial", 9))
            lbl_custo.pack(side="left", padx=4)
            self._skill_custo_labels.append(lbl_custo)

        # Atualiza labels de custo iniciais
        for i in range(max_slots):
            self._atualizar_custo_label(i)

        # ── Encantamentos ──
        if max_enc > 0:
            tk.Label(left, text="Encantamentos:", font=("Arial", 11, "bold"),
                     bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", pady=(12, 4))

            frame_enc = tk.Frame(left, bg=COR_BG_SECUNDARIO)
            frame_enc.pack(fill="x")

            self.vars_encantamento = {}
            for enc_nome in LISTA_ENCANTAMENTOS[:8]:
                dados_enc = ENCANTAMENTOS[enc_nome]
                var = tk.BooleanVar(value=enc_nome in self.dados_arma["encantamentos"])
                self.vars_encantamento[enc_nome] = var

                fr = tk.Frame(frame_enc, bg=COR_BG)
                fr.pack(fill="x", pady=2)

                cor = f"#{dados_enc['cor'][0]:02x}{dados_enc['cor'][1]:02x}{dados_enc['cor'][2]:02x}"
                chk = tk.Checkbutton(
                    fr, text=enc_nome, variable=var,
                    bg=COR_BG, fg=cor, selectcolor=COR_BG_SECUNDARIO,
                    font=("Arial", 10),
                    command=lambda n=enc_nome: self.toggle_encantamento(n)
                )
                chk.pack(side="left")
                tk.Label(fr, text=dados_enc["descricao"], bg=COR_BG,
                         fg=COR_TEXTO_DIM, font=("Arial", 8)).pack(side="left", padx=8)

        # ===============================================================
        # COLUNA DIREITA — painel de detalhes da skill selecionada
        # ===============================================================
        self._skill_detail_frame = tk.Frame(main, bg=COR_BG, bd=2, relief="groove")
        self._skill_detail_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Mostra o primeiro slot selecionado ou placeholder
        first_skill = self.combos_skill[0].get() if self.combos_skill else "Nenhuma"
        self._mostrar_detalhes_skill(first_skill)

    # ─────────────────────────────────────────────────────
    # Filtro de skills
    # ─────────────────────────────────────────────────────
    def _lista_skills_filtrada(self):
        """Retorna lista de nomes de skills filtrada."""
        elem = getattr(self, '_filtro_elemento', None)
        tipo = getattr(self, '_filtro_tipo', None)
        elem_val = elem.get() if elem else "Todos"
        tipo_val = tipo.get() if tipo else "Todos"

        resultado = ["Nenhuma"]
        for nome, dados in SKILL_DB.items():
            if nome == "Nenhuma":
                continue
            if elem_val != "Todos" and dados.get("elemento") != elem_val:
                continue
            if tipo_val != "Todos" and dados.get("tipo") != tipo_val:
                continue
            resultado.append(nome)
        return resultado

    def _aplicar_filtro_skills(self):
        """Reaplica filtro a todos os combos."""
        lista = self._lista_skills_filtrada()
        for combo in self.combos_skill:
            atual = combo.get()
            combo["values"] = lista
            if atual not in lista:
                combo.set("Nenhuma")

    # ─────────────────────────────────────────────────────
    # Callbacks de seleção
    # ─────────────────────────────────────────────────────
    def _on_skill_selected(self, idx):
        """Quando uma skill é escolhida no combobox."""
        nome = self.combos_skill[idx].get()
        self._atualizar_custo_label(idx)
        self.atualizar_skill_slot(idx)
        self._mostrar_detalhes_skill(nome)

    def _atualizar_custo_label(self, idx):
        """Atualiza label de custo de mana ao lado do combo."""
        if idx >= len(self._skill_custo_labels):
            return
        nome = self.combos_skill[idx].get()
        dados = SKILL_DB.get(nome, {})
        custo = dados.get("custo", 0)
        if custo > 0:
            self._skill_custo_labels[idx].config(text=f"{custo:.0f} mana", fg=COR_SUCCESS)
        else:
            self._skill_custo_labels[idx].config(text="")

    # ─────────────────────────────────────────────────────
    # Painel de detalhes completo
    # ─────────────────────────────────────────────────────
    def _mostrar_detalhes_skill(self, nome):
        """Constrói o painel de detalhes visuais de uma skill."""
        frame = self._skill_detail_frame
        for w in frame.winfo_children():
            w.destroy()

        dados = SKILL_DB.get(nome, {})
        tipo = dados.get("tipo", "NADA")
        elemento = dados.get("elemento", "")
        descricao = dados.get("descricao", "Nenhuma habilidade selecionada.")
        cor_elem = self._ELEMENTO_CORES.get(elemento, COR_TEXTO_DIM)
        icone_tipo = self._TIPO_ICONES.get(tipo, "?")
        cor_skill = dados.get("cor", (180, 180, 180))
        if isinstance(cor_skill, (list, tuple)) and len(cor_skill) >= 3:
            hex_skill = f"#{int(cor_skill[0]):02x}{int(cor_skill[1]):02x}{int(cor_skill[2]):02x}"
        else:
            hex_skill = COR_TEXTO_DIM

        if nome == "Nenhuma" or tipo == "NADA":
            tk.Label(frame, text="Selecione uma habilidade\npara ver os detalhes",
                     font=("Arial", 12), bg=COR_BG, fg=COR_TEXTO_DIM,
                     justify="center").pack(expand=True)
            return

        # ── Header: ícone + nome + badges ──
        hdr = tk.Frame(frame, bg=COR_BG)
        hdr.pack(fill="x", padx=12, pady=(12, 4))

        # Ícone circular colorido
        icon_cv = tk.Canvas(hdr, width=40, height=40, bg=COR_BG, highlightthickness=0)
        icon_cv.pack(side="left", padx=(0, 8))
        icon_cv.create_oval(4, 4, 36, 36, fill=hex_skill, outline=cor_elem, width=2)
        icon_cv.create_text(20, 20, text=icone_tipo, fill="white",
                            font=("Arial", 12, "bold"))

        info_col = tk.Frame(hdr, bg=COR_BG)
        info_col.pack(side="left", fill="x", expand=True)

        tk.Label(info_col, text=nome, font=("Arial", 14, "bold"),
                 bg=COR_BG, fg=COR_TEXTO, anchor="w").pack(anchor="w")

        badges_f = tk.Frame(info_col, bg=COR_BG)
        badges_f.pack(anchor="w")
        # Tipo badge
        self._criar_badge(badges_f, tipo, "#2a2a4e", COR_SUCCESS)
        # Elemento badge
        if elemento:
            self._criar_badge(badges_f, elemento, "#2a2a4e", cor_elem)
        # Efeito badge
        efeito = dados.get("efeito", "")
        if efeito and efeito != "NORMAL":
            self._criar_badge(badges_f, efeito, "#2a2a4e", "#f39c12")

        # ── Separador ──
        tk.Frame(frame, bg=COR_TEXTO_DIM, height=1).pack(fill="x", padx=12, pady=6)

        # ── Descrição ──
        tk.Label(frame, text=descricao, font=("Arial", 10, "italic"),
                 bg=COR_BG, fg=COR_TEXTO_DIM, wraplength=280,
                 justify="left", anchor="w").pack(fill="x", padx=14, pady=(0, 8))

        # ── Stats bars ──
        stats_f = tk.Frame(frame, bg=COR_BG)
        stats_f.pack(fill="x", padx=12)

        dano = dados.get("dano", 0)
        custo = dados.get("custo", 0)
        cooldown = dados.get("cooldown", 0)
        vel = dados.get("velocidade", 0)
        raio = dados.get("raio_area", dados.get("raio", 0))
        alcance = dados.get("alcance", dados.get("distancia", 0))

        bars = []
        if dano > 0:
            bars.append(("Dano", dano, 150, "#e74c3c"))
        if custo > 0:
            bars.append(("Custo Mana", custo, 80, "#3498db"))
        if cooldown > 0:
            bars.append(("Cooldown", cooldown, 60, "#f39c12"))
        if vel > 0:
            bars.append(("Velocidade", vel, 30, "#2ecc71"))
        if alcance > 0:
            bars.append(("Alcance", alcance, 12, "#9b59b6"))
        if raio > 0:
            bars.append(("Raio", raio, 6, "#1abc9c"))

        for label, valor, maximo, cor_bar in bars:
            self._criar_stat_bar(stats_f, label, valor, maximo, cor_bar)

        # ── Propriedades especiais ──
        especiais = []
        if dados.get("perfura"):
            especiais.append("Perfurante")
        if dados.get("homing"):
            especiais.append("Teleguiado")
        if dados.get("multi_shot"):
            especiais.append(f"Multi-tiro x{dados['multi_shot']}")
        if dados.get("canalizavel"):
            especiais.append(f"Canalizável ({dados.get('duracao_max', '?')}s)")
        if dados.get("lifesteal"):
            especiais.append(f"Roubo de vida {dados['lifesteal']*100:.0f}%")
        if dados.get("escudo"):
            especiais.append(f"Escudo +{dados['escudo']:.0f}")
        if dados.get("cura"):
            especiais.append(f"Cura +{dados['cura']:.0f}")
        if dados.get("buff_dano"):
            especiais.append(f"Buff dano x{dados['buff_dano']}")
        if dados.get("retorna"):
            especiais.append("Retorna ao lançador")
        if dados.get("condicao"):
            cond = dados["condicao"].replace("ALVO_", "").replace("_", " ").title()
            especiais.append(f"Condição: {cond}")
        if dados.get("duracao"):
            especiais.append(f"Duração: {dados['duracao']}s")
        if dados.get("invencivel"):
            especiais.append("Invencível durante uso")
        if dados.get("chain"):
            especiais.append(f"Cadeia: salta {dados['chain']}x")
        if dados.get("bloqueia_movimento"):
            especiais.append("Bloqueia movimento")
        if dados.get("aura_slow"):
            especiais.append(f"Aura slow {dados['aura_slow']*100:.0f}%")
        if dados.get("reflete_projeteis"):
            especiais.append("Reflete projéteis")
        if dados.get("remove_todos_debuffs"):
            especiais.append("Remove todos debuffs")
        if dados.get("taunt"):
            especiais.append("Provoca inimigos")
        if dados.get("dano_contato"):
            especiais.append(f"Dano contato: {dados['dano_contato']:.0f}")
        if dados.get("dano_por_segundo"):
            especiais.append(f"DPS: {dados['dano_por_segundo']:.0f}/s")

        if especiais:
            tk.Frame(frame, bg=COR_TEXTO_DIM, height=1).pack(fill="x", padx=12, pady=6)
            esp_f = tk.Frame(frame, bg=COR_BG)
            esp_f.pack(fill="x", padx=12)
            tk.Label(esp_f, text="Propriedades Especiais:",
                     font=("Arial", 9, "bold"), bg=COR_BG, fg=COR_TEXTO).pack(anchor="w")
            for prop in especiais:
                tk.Label(esp_f, text=f"  \u2022 {prop}", font=("Arial", 9),
                         bg=COR_BG, fg=cor_elem, anchor="w").pack(anchor="w")

        # ── Mini-preview animado ──
        tk.Frame(frame, bg=COR_TEXTO_DIM, height=1).pack(fill="x", padx=12, pady=6)
        tk.Label(frame, text="Preview Visual", font=("Arial", 9, "bold"),
                 bg=COR_BG, fg=COR_TEXTO).pack(padx=12, anchor="w")

        preview = tk.Canvas(frame, width=280, height=120, bg="#0d0d1a",
                            highlightthickness=1, highlightbackground=COR_TEXTO_DIM)
        preview.pack(padx=12, pady=(4, 12))
        self._animar_skill_preview(preview, nome, dados)

    # ─────────────────────────────────────────────────────
    # Widgets auxiliares
    # ─────────────────────────────────────────────────────
    def _criar_badge(self, parent, texto, bg_badge, fg_badge):
        """Cria um badge (tag) colorido."""
        lbl = tk.Label(parent, text=f" {texto} ", font=("Arial", 8, "bold"),
                       bg=bg_badge, fg=fg_badge, bd=1, relief="solid", padx=3, pady=1)
        lbl.pack(side="left", padx=(0, 4), pady=1)

    def _criar_stat_bar(self, parent, label, valor, maximo, cor_bar):
        """Cria uma barra de stat horizontal com label e valor numérico."""
        row = tk.Frame(parent, bg=COR_BG)
        row.pack(fill="x", pady=2)

        tk.Label(row, text=label, font=("Arial", 9), bg=COR_BG,
                 fg=COR_TEXTO_DIM, width=10, anchor="w").pack(side="left")

        bar_bg = tk.Canvas(row, width=140, height=14, bg="#1a1a2e",
                           highlightthickness=0)
        bar_bg.pack(side="left", padx=4)
        pct = min(1.0, valor / maximo) if maximo > 0 else 0
        bar_w = int(140 * pct)
        if bar_w > 0:
            bar_bg.create_rectangle(0, 0, bar_w, 14, fill=cor_bar, outline="")
            # Brilho no topo
            bar_bg.create_rectangle(0, 0, bar_w, 4, fill="", outline="")
            bar_bg.create_line(0, 1, bar_w, 1, fill=self._lighten(cor_bar), width=1)

        tk.Label(row, text=f"{valor:.1f}" if isinstance(valor, float) else str(valor),
                 font=("Arial", 9, "bold"), bg=COR_BG, fg=COR_TEXTO, width=6,
                 anchor="w").pack(side="left")

    @staticmethod
    def _lighten(hex_color, amt=60):
        """Clareia uma cor hex."""
        hex_color = hex_color.lstrip("#")
        r = min(255, int(hex_color[0:2], 16) + amt)
        g = min(255, int(hex_color[2:4], 16) + amt)
        b = min(255, int(hex_color[4:6], 16) + amt)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ─────────────────────────────────────────────────────
    # Mini-preview animado (canvas estático representativo)
    # ─────────────────────────────────────────────────────
    def _animar_skill_preview(self, canvas, nome, dados):
        """Desenha uma representação visual do comportamento da skill."""
        import math as _m
        import random as _r

        canvas.delete("all")
        w, h = 280, 120
        cx, cy = w // 2, h // 2
        tipo = dados.get("tipo", "NADA")
        cor = dados.get("cor", (180, 180, 180))
        if isinstance(cor, (list, tuple)) and len(cor) >= 3:
            hex_c = f"#{int(cor[0]):02x}{int(cor[1]):02x}{int(cor[2]):02x}"
            hex_dim = f"#{max(0,int(cor[0])//2):02x}{max(0,int(cor[1])//2):02x}{max(0,int(cor[2])//2):02x}"
        else:
            hex_c = "#b4b4b4"
            hex_dim = "#5a5a5a"

        elem = dados.get("elemento", "")
        cor_elem = self._ELEMENTO_CORES.get(elem, "#888888")

        # Personagem lançador (esquerda)
        px, py = 40, cy
        canvas.create_oval(px - 8, py - 8, px + 8, py + 8,
                           fill="#4488ff", outline="#6699ff", width=2)
        canvas.create_text(px, py, text="P", fill="white", font=("Arial", 8, "bold"))

        # Inimigo (direita)
        ex, ey = w - 40, cy
        canvas.create_oval(ex - 8, ey - 8, ex + 8, ey + 8,
                           fill="#ff4444", outline="#ff6666", width=2)
        canvas.create_text(ex, ey, text="E", fill="white", font=("Arial", 8, "bold"))

        if tipo == "PROJETIL":
            # Projétil voando com trilha
            multi = dados.get("multi_shot", 1)
            for shot in range(min(multi, 5)):
                offset_y = (shot - multi // 2) * 12
                # Trilha
                for i in range(6):
                    t = i / 6
                    tx = px + 20 + t * 130
                    ty = py + offset_y
                    alpha_r = max(3, int(8 * (1 - t)))
                    canvas.create_oval(tx - alpha_r, ty - alpha_r,
                                       tx + alpha_r, ty + alpha_r,
                                       fill=hex_dim, outline="")
                # Projétil principal
                proj_x = px + 20 + 130 * 0.65
                proj_y = py + offset_y
                raio_p = max(4, int(dados.get("raio", 0.3) * 12))
                canvas.create_oval(proj_x - raio_p, proj_y - raio_p,
                                   proj_x + raio_p, proj_y + raio_p,
                                   fill=hex_c, outline=cor_elem, width=2)
                # Glow
                canvas.create_oval(proj_x - raio_p - 3, proj_y - raio_p - 3,
                                   proj_x + raio_p + 3, proj_y + raio_p + 3,
                                   outline=hex_dim, width=1)
            # Seta de direção
            canvas.create_line(px + 16, py, px + 28, py,
                               fill=hex_c, width=2, arrow="last")

        elif tipo == "BEAM":
            # Raio contínuo do lançador ao inimigo
            canvas.create_line(px + 12, py, ex - 12, ey,
                               fill=hex_c, width=4)
            canvas.create_line(px + 12, py, ex - 12, ey,
                               fill="white", width=1)
            # Faíscas
            for _ in range(8):
                sx = _r.randint(px + 20, ex - 20)
                sy = py + _r.randint(-10, 10)
                canvas.create_line(sx, sy, sx + _r.randint(-6, 6),
                                   sy + _r.randint(-6, 6),
                                   fill=cor_elem, width=1)
            # Impacto
            canvas.create_oval(ex - 18, ey - 12, ex - 6, ey + 12,
                               outline=hex_c, width=2)

        elif tipo == "AREA":
            # Área centrada no lançador ou no centro
            raio_a = max(20, int(dados.get("raio_area", 2.0) * 10))
            area_cx = cx if dados.get("delay") else px
            area_cy = cy
            # Ondas concêntricas
            for ring in range(3):
                r = raio_a - ring * 8
                if r < 6:
                    break
                canvas.create_oval(area_cx - r, area_cy - r,
                                   area_cx + r, area_cy + r,
                                   outline=hex_c if ring == 0 else hex_dim,
                                   width=2 - ring * 0.5, dash=(4, 3) if ring > 0 else ())
            # Partículas dentro da área
            for _ in range(12):
                angle = _r.random() * _m.pi * 2
                dist = _r.random() * raio_a * 0.8
                ppx = area_cx + _m.cos(angle) * dist
                ppy = area_cy + _m.sin(angle) * dist
                sz = _r.randint(2, 4)
                canvas.create_oval(ppx - sz, ppy - sz, ppx + sz, ppy + sz,
                                   fill=hex_c, outline="")
            # Label do raio
            canvas.create_text(area_cx, area_cy + raio_a + 10,
                               text=f"Raio: {dados.get('raio_area', '?')}m",
                               fill=COR_TEXTO_DIM, font=("Arial", 7))

        elif tipo == "DASH":
            # Trilha de dash
            dist_d = min(160, int(dados.get("distancia", 4) * 20))
            # Afterimages
            for i in range(5):
                t = i / 5
                dx = px + t * dist_d
                canvas.create_oval(dx - 6, py - 6, dx + 6, py + 6,
                                   outline=hex_dim, width=1, dash=(2, 2))
            # Posição final
            fx = px + dist_d
            canvas.create_oval(fx - 8, py - 8, fx + 8, py + 8,
                               fill="#4488ff", outline=cor_elem, width=2)
            canvas.create_text(fx, py, text="P", fill="white",
                               font=("Arial", 8, "bold"))
            # Linha de trajeto
            canvas.create_line(px, py, fx, py, fill=cor_elem,
                               width=1, dash=(6, 3))
            # Dano na chegada
            if dados.get("dano_chegada") or dados.get("dano"):
                canvas.create_oval(fx - 14, py - 14, fx + 14, py + 14,
                                   outline=hex_c, width=1, dash=(3, 3))

        elif tipo == "BUFF":
            # Aura ao redor do lançador
            for ring in range(4):
                r = 14 + ring * 6
                canvas.create_oval(px - r, py - r, px + r, py + r,
                                   outline=hex_c if ring < 2 else hex_dim,
                                   width=2 if ring == 0 else 1,
                                   dash=() if ring == 0 else (3, 3))
            # Setas para cima (buff)
            for dx in [-6, 0, 6]:
                ax = px + dx
                canvas.create_line(ax, py - 16, ax, py - 28,
                                   fill=cor_elem, width=2, arrow="first")
            # Texto do efeito
            buff_txt = dados.get("efeito_buff", "BUFF")
            canvas.create_text(px, py + 30, text=buff_txt,
                               fill=hex_c, font=("Arial", 8, "bold"))

        elif tipo == "SUMMON":
            # Círculo de invocação
            summon_x = cx
            canvas.create_oval(summon_x - 16, cy - 16, summon_x + 16, cy + 16,
                               fill=hex_dim, outline=cor_elem, width=2)
            canvas.create_text(summon_x, cy, text="\u2726",
                               fill=hex_c, font=("Arial", 14))
            # Pentagrama decorativo
            for i in range(5):
                a1 = _m.radians(i * 72 - 90)
                a2 = _m.radians(((i + 2) % 5) * 72 - 90)
                canvas.create_line(
                    summon_x + _m.cos(a1) * 22, cy + _m.sin(a1) * 22,
                    summon_x + _m.cos(a2) * 22, cy + _m.sin(a2) * 22,
                    fill=hex_dim, width=1)
            # Info
            vida_s = dados.get("summon_vida", "?")
            dano_s = dados.get("summon_dano", "?")
            canvas.create_text(summon_x, cy + 34,
                               text=f"HP:{vida_s}  DMG:{dano_s}",
                               fill=COR_TEXTO_DIM, font=("Arial", 7))

        elif tipo == "TRAP":
            # Armadilha no chão
            trap_x = cx + 20
            # Zona de perigo
            canvas.create_rectangle(trap_x - 18, cy - 18, trap_x + 18, cy + 18,
                                    outline=hex_c, width=2, dash=(4, 4))
            canvas.create_line(trap_x - 12, cy - 12, trap_x + 12, cy + 12,
                               fill="#ff4444", width=1)
            canvas.create_line(trap_x + 12, cy - 12, trap_x - 12, cy + 12,
                               fill="#ff4444", width=1)
            canvas.create_text(trap_x, cy, text="\u26A0",
                               fill=hex_c, font=("Arial", 14))
            canvas.create_text(trap_x, cy + 28,
                               text="ARMADILHA", fill=COR_TEXTO_DIM,
                               font=("Arial", 7, "bold"))

        elif tipo == "TRANSFORM":
            # Transformação com antes/depois
            canvas.create_oval(px - 8, py - 8, px + 8, py + 8,
                               outline="#4488ff", width=1, dash=(2, 2))
            # Seta de transição
            canvas.create_line(px + 16, py, cx - 8, py,
                               fill=cor_elem, width=2, arrow="last")
            # Forma transformada (maior, brilhante)
            canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14,
                               fill=hex_c, outline=cor_elem, width=2)
            canvas.create_text(cx, cy, text="\u21BB",
                               fill="white", font=("Arial", 12, "bold"))
            # Partículas de transformação
            for _ in range(8):
                a = _r.random() * _m.pi * 2
                d = _r.randint(16, 30)
                ptx = cx + _m.cos(a) * d
                pty = cy + _m.sin(a) * d
                canvas.create_oval(ptx - 2, pty - 2, ptx + 2, pty + 2,
                                   fill=hex_c, outline="")

        elif tipo == "CHANNEL":
            # Canalização contínua
            canvas.create_oval(px - 14, py - 14, px + 14, py + 14,
                               outline=cor_elem, width=2)
            # Ondas saindo
            for ring in range(4):
                r = 18 + ring * 10
                canvas.create_arc(px - r, py - r, px + r, py + r,
                                  start=_r.randint(0, 360), extent=60,
                                  style="arc", outline=hex_dim, width=1)
            # Linha de energia
            canvas.create_line(px + 14, py, ex - 12, ey,
                               fill=hex_c, width=2, dash=(6, 4))
            canvas.create_text(cx, cy + 40,
                               text=f"Duração: {dados.get('duracao_max', '?')}s",
                               fill=COR_TEXTO_DIM, font=("Arial", 7))
        else:
            canvas.create_text(cx, cy, text="Sem preview",
                               fill=COR_TEXTO_DIM, font=("Arial", 10))

    def atualizar_skill_slot(self, idx):
        """Atualiza um slot de habilidade"""
        nome = self.combos_skill[idx].get()
        
        # Reconstrói lista de habilidades
        habilidades = []
        for combo in self.combos_skill:
            skill_nome = combo.get()
            if skill_nome != "Nenhuma":
                custo = SKILL_DB.get(skill_nome, {}).get("custo", 0)
                habilidades.append({"nome": skill_nome, "custo": custo})
        
        self.dados_arma["habilidades"] = habilidades
        self.criar_resumo_stats()

    def toggle_encantamento(self, nome):
        """Toggle de encantamento"""
        max_enc = RARIDADES[self.dados_arma["raridade"]]["max_encantamentos"]
        
        if self.vars_encantamento[nome].get():
            if len(self.dados_arma["encantamentos"]) < max_enc:
                if nome not in self.dados_arma["encantamentos"]:
                    self.dados_arma["encantamentos"].append(nome)
            else:
                self.vars_encantamento[nome].set(False)
                messagebox.showwarning("Limite", f"Maximo de {max_enc} encantamentos para esta raridade!")
        else:
            if nome in self.dados_arma["encantamentos"]:
                self.dados_arma["encantamentos"].remove(nome)

    # -------------------------------------------------------------------------
    # PASSO 6: FINALIZAR
    # -------------------------------------------------------------------------
    def passo_finalizar(self):
        """Passo 6: Resumo e confirmação"""
        self.lbl_passo_titulo.config(text="6. FINALIZAR")
        self.lbl_passo_desc.config(text="Revise sua arma antes de forjar!")
        
        # Resumo completo
        dados = self.dados_arma
        raridade = dados["raridade"]
        cor_rar = CORES_RARIDADE[raridade]
        
        # Frame do resumo
        frame_resumo = tk.Frame(self.frame_conteudo_passo, bg=COR_BG, bd=2, relief="ridge")
        frame_resumo.pack(fill="both", expand=True, pady=10)
        
        # Nome em destaque
        tk.Label(
            frame_resumo, text=dados["nome"] or "Arma Sem Nome",
            font=("Arial", 18, "bold"), bg=COR_BG, fg=cor_rar
        ).pack(pady=(15, 5))
        
        tk.Label(
            frame_resumo, text=f"{dados['tipo']} {raridade}",
            font=("Arial", 12), bg=COR_BG, fg=COR_TEXTO_DIM
        ).pack()
        
        # Stats
        stats_frame = tk.Frame(frame_resumo, bg=COR_BG)
        stats_frame.pack(pady=15)
        
        rar_data = RARIDADES[raridade]
        dano_final = dados["dano"] * rar_data["mod_dano"]
        
        stats = [
            ("Dano", f"{dano_final:.0f}"),
            ("Peso", f"{dados['peso']:.1f}kg"),
            ("Critico", f"+{rar_data['mod_critico']:.0%}"),
            ("Vel.Ataque", f"{rar_data['mod_velocidade_ataque']:.0%}"),
        ]
        
        for i, (nome, valor) in enumerate(stats):
            tk.Label(
                stats_frame, text=f"{nome}: {valor}",
                font=("Arial", 11), bg=COR_BG, fg=COR_TEXTO
            ).grid(row=i//2, column=i%2, padx=20, pady=3, sticky="w")
        
        # Habilidades
        if dados["habilidades"]:
            tk.Label(
                frame_resumo, text="Habilidades:",
                font=("Arial", 10, "bold"), bg=COR_BG, fg=COR_SUCCESS
            ).pack(anchor="w", padx=15)
            
            for hab in dados["habilidades"]:
                # Suporta tanto string quanto dict
                if isinstance(hab, dict):
                    nome = hab.get('nome', 'Desconhecida')
                    custo = hab.get('custo', 0)
                    texto = f"  - {nome} ({custo} mana)"
                else:
                    texto = f"  - {hab}"
                tk.Label(
                    frame_resumo, text=texto,
                    font=("Arial", 9), bg=COR_BG, fg=COR_TEXTO
                ).pack(anchor="w", padx=15)
        
        # Encantamentos
        if dados["encantamentos"]:
            tk.Label(
                frame_resumo, text="Encantamentos:",
                font=("Arial", 10, "bold"), bg=COR_BG, fg="#FFD700"
            ).pack(anchor="w", padx=15, pady=(10, 0))
            
            for enc in dados["encantamentos"]:
                cor = ENCANTAMENTOS[enc]["cor"]
                cor_hex = f"#{cor[0]:02x}{cor[1]:02x}{cor[2]:02x}"
                tk.Label(
                    frame_resumo, text=f"  - {enc}",
                    font=("Arial", 9), bg=COR_BG, fg=cor_hex
                ).pack(anchor="w", padx=15)

    # =========================================================================
    # PREVIEW
    # =========================================================================
    
    def atualizar_preview(self):
        """Atualiza o preview visual da arma"""
        self.canvas_preview.delete("all")
        
        w = self.canvas_preview.winfo_width()
        h = self.canvas_preview.winfo_height()
        cx, cy = w/2, h/2
        
        if w < 50:
            return
        
        # Desenha personagem fantasma para referência
        raio_char = 30
        self.canvas_preview.create_oval(
            cx - raio_char, cy - raio_char, cx + raio_char, cy + raio_char,
            outline="#444", dash=(4, 4), width=2
        )
        self.canvas_preview.create_text(
            cx, cy, text="P", font=("Arial", 16, "bold"), fill="#555"
        )
        
        tipo = self.dados_arma["tipo"]
        cores = self.dados_arma["cores"]
        cor_hex = f"#{cores['r']:02x}{cores['g']:02x}{cores['b']:02x}"
        cor_raridade = CORES_RARIDADE[self.dados_arma["raridade"]]
        estilo = self.dados_arma.get("estilo", "")
        
        # Renderiza baseado no tipo — todos recebem estilo para diferenciar variantes
        if tipo == "Reta":
            self.desenhar_arma_reta(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Dupla":
            self.desenhar_arma_dupla(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Corrente":
            self.desenhar_arma_corrente(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Arremesso":
            self.desenhar_arma_arremesso(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Arco":
            self.desenhar_arma_arco(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Orbital":
            self.desenhar_arma_orbital(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Mágica":
            self.desenhar_arma_magica(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        elif tipo == "Transformável":
            self.desenhar_arma_transformavel(cx, cy, raio_char, cor_hex, cor_raridade, estilo)
        
        # Borda de raridade
        self.canvas_preview.create_rectangle(
            5, 5, w-5, h-5, outline=cor_raridade, width=2
        )
        
        # Nome da raridade
        self.canvas_preview.create_text(
            w - 10, 15, text=self.dados_arma["raridade"],
            font=("Arial", 10, "bold"), fill=cor_raridade, anchor="e"
        )

    def desenhar_arma_reta(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Reta por estilo.
        Estilos: Corte (Espada), Estocada (Lança), Contusão (Maça), Misto.
        """
        import math as _math
        cabo  = 20
        lam   = 50
        larg  = 5
        cv    = self.canvas_preview
        bx    = cx + raio  # base X (encosta no personagem)

        # ── ESTOCADA (Lança) — haste longa, ponta fina triangular ──────────
        if "Lança" in estilo or "Estocada" in estilo:
            # Haste de madeira
            cv.create_rectangle(bx, cy - max(2, larg//3),
                                 bx + cabo, cy + max(2, larg//3),
                                 fill="#6B3A1F", outline="#4A2810")
            # Ponta de metal — triângulo estreito e longo
            cv.create_polygon(
                bx + cabo, cy - larg*0.6,
                bx + cabo + lam * 0.15, cy - larg*0.25,
                bx + cabo + lam, cy,
                bx + cabo + lam * 0.15, cy + larg*0.25,
                bx + cabo, cy + larg*0.6,
                fill=cor, outline=cor_rar, width=1
            )
            # Fio central
            cv.create_line(bx + cabo, cy, bx + cabo + lam, cy, fill="#DDEEFF", width=1)
            # Anel (virola)
            cv.create_rectangle(bx + cabo - 3, cy - larg*0.7, bx + cabo + 3, cy + larg*0.7,
                                 fill="#A0A5B0", outline="#C8C8D0")

        # ── CONTUSÃO (Maça) — cabo curto, cabeça larga com espigões ───────
        elif "Maça" in estilo or "Contusão" in estilo:
            # Cabo
            cv.create_rectangle(bx, cy - max(2, larg//3),
                                 bx + cabo, cy + max(2, larg//3),
                                 fill="#5C3317", outline="#4A2810")
            # Cabeça da maça — cilindro largo
            head_w = larg * 1.6
            cv.create_rectangle(bx + cabo, cy - head_w,
                                 bx + cabo + lam * 0.55, cy + head_w,
                                 fill=cor, outline=cor_rar, width=2)
            # Espigões (4 faces)
            spike_x = bx + cabo + lam * 0.28
            for sy_off in [-head_w - 6, head_w + 6]:
                cv.create_polygon(
                    spike_x - 5, cy + sy_off * 0.5,
                    spike_x + 5, cy + sy_off * 0.5,
                    spike_x, cy + sy_off,
                    fill=cor_rar, outline=cor_rar
                )
            # Highlight
            cv.create_rectangle(bx + cabo + 2, cy - head_w + 2,
                                 bx + cabo + lam * 0.25, cy - head_w//2,
                                 fill="#FFFFFF", outline="")

        # ── CORTE (Espada) — lâmina larga com guarda e fio ─────────────────
        elif "Espada" in estilo or "Corte" in estilo:
            # Cabo com faixas de grip
            cv.create_rectangle(bx, cy - max(2, larg//3),
                                 bx + cabo, cy + max(2, larg//3),
                                 fill="#6B3A1F", outline="#4A2810")
            for gi in range(1, 4):
                gx = bx + cabo * gi // 4
                cv.create_line(gx, cy - larg//2, gx, cy + larg//2, fill="#3A1A08", width=1)
            # Guarda (crossguard)
            cv.create_rectangle(bx + cabo - 2, cy - larg - 3,
                                 bx + cabo + 5, cy + larg + 3,
                                 fill="#A0A5B0", outline="#C8C8D0", width=1)
            # Lâmina com fio
            cv.create_polygon(
                bx + cabo + 5, cy - larg,
                bx + cabo + 5 + lam * 0.9, cy - larg * 0.25,
                bx + cabo + 5 + lam, cy,
                bx + cabo + 5 + lam * 0.9, cy + larg * 0.25,
                bx + cabo + 5, cy + larg,
                fill=cor, outline=cor_rar, width=2
            )
            cv.create_line(bx + cabo + 5, cy, bx + cabo + 5 + lam * 0.85, cy, fill="#DDEEFF", width=1)

        # ── MISTO — cabo médio, lâmina levemente curva, sem guarda ─────────
        else:
            cv.create_rectangle(bx, cy - max(2, larg//3),
                                 bx + cabo, cy + max(2, larg//3),
                                 fill="#6B3A1F", outline="#4A2810")
            # Lâmina curva (bezier aproximado 5 pontos)
            ctrl_y = cy - larg * 0.6
            cv.create_polygon(
                bx + cabo, cy - larg * 0.7,
                bx + cabo + lam * 0.5, ctrl_y,
                bx + cabo + lam, cy,
                bx + cabo + lam * 0.5, cy + larg * 0.2,
                bx + cabo, cy + larg * 0.7,
                smooth=True, fill=cor, outline=cor_rar, width=1
            )
            cv.create_line(bx + cabo, cy, bx + cabo + lam * 0.85, cy - larg*0.2, fill="#DDEEFF", width=1)

        # Ponta brilhante comum
        tip_x = bx + cabo + lam if "Maça" not in estilo and "Contusão" not in estilo else bx + cabo + lam * 0.55
        cv.create_oval(tip_x - 3, cy - 3, tip_x + 3, cy + 3, fill=cor_rar, outline=cor_rar)


    def desenhar_arma_dupla(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Dupla — renderizador por estilo.
        
        Estilos: Adagas Gêmeas (karambit), Kamas (foice), Sai (tridente),
                 Garras (garra), Tonfas (bastão-L), Facas Táticas (faca militar).
        """
        import math as _math
        cabo  = 15
        lam   = 35
        larg  = 4
        sep   = 20

        cv = self.canvas_preview

        # Posições base: duas armas lado a lado (superior / inferior)
        offsets = [-sep * 0.65, sep * 0.65]

        # ── ADAGAS GÊMEAS (karambit) ─────────────────────────────────────
        if estilo == "Adagas Gêmeas":
            for i, offset in enumerate(offsets):
                lado = -1 if i == 0 else 1
                bx = cx + raio + 10
                by = cy + offset
                cv.create_oval(bx-4, by-4, bx+4, by+4, outline="#C8C8D0", width=2)
                cabo_ex = bx + cabo * 0.7
                cabo_ey = by + cabo * 0.2 * lado
                cv.create_line(bx, by, cabo_ex, cabo_ey, fill="#6B3A1F", width=larg)
                arc_r  = lam * 0.6
                arc_cx = cabo_ex + arc_r * 0.3
                arc_cy = cabo_ey - arc_r * lado * 0.5
                cv.create_arc(
                    arc_cx-arc_r, arc_cy-arc_r, arc_cx+arc_r, arc_cy+arc_r,
                    start=150 if lado < 0 else 180, extent=100,
                    style="arc", outline=cor, width=larg
                )
                tip_x = arc_cx + _math.cos(_math.radians(240 if lado < 0 else 280)) * arc_r
                tip_y = arc_cy + _math.sin(_math.radians(240 if lado < 0 else 280)) * arc_r
                cv.create_oval(tip_x-3, tip_y-3, tip_x+3, tip_y+3, fill=cor_rar, outline=cor_rar)

        # ── KAMAS (foice japonesa — cabo + lâmina curva perpendicular) ────
        elif estilo == "Kamas":
            for i, offset in enumerate(offsets):
                lado = -1 if i == 0 else 1
                bx = cx + raio + 8
                by = cy + offset
                # Cabo vertical
                cv.create_line(bx, by, bx + cabo, by, fill="#6B3A1F", width=larg)
                # Lâmina curva partindo do final do cabo para cima/baixo
                # Arco em 180°: retrato de foice
                arc_r = lam * 0.5
                arc_ox = bx + cabo
                arc_oy = by - arc_r * lado * 0.4
                cv.create_arc(
                    arc_ox - arc_r * 0.5, arc_oy - arc_r,
                    arc_ox + arc_r * 0.5, arc_oy + arc_r,
                    start=270 if lado < 0 else 90,
                    extent=(-160 if lado < 0 else 160),
                    style="arc", outline=cor, width=larg
                )
                # Guarda (crossguard) no topo do cabo
                cv.create_line(bx + cabo - 2, by - 5, bx + cabo - 2, by + 5,
                                fill="#A0A5B0", width=larg)
                # Ponta da foice
                tip_x = arc_ox + arc_r * 0.4 * lado
                tip_y = by - arc_r * lado * 0.9
                cv.create_oval(tip_x-3, tip_y-3, tip_x+3, tip_y+3, fill=cor_rar, outline=cor_rar)

        # ── SAI (tridente japonês — foinha central + duas guardas laterais) ─
        elif estilo == "Sai":
            for i, offset in enumerate(offsets):
                lado = -1 if i == 0 else 1
                bx = cx + raio + 8
                by = cy + offset
                tip_main = bx + cabo + lam
                # Cabo
                cv.create_line(bx, by, bx + cabo, by, fill="#6B3A1F", width=larg)
                # Lâmina central (foinha principal)
                cv.create_line(bx + cabo, by, tip_main, by, fill=cor, width=larg)
                # Ponta
                cv.create_oval(tip_main-3, by-3, tip_main+3, by+3, fill=cor_rar, outline=cor_rar)
                # Guardas laterais (asas do Sai)
                asa = lam * 0.35
                cv.create_line(bx + cabo, by, bx + cabo + asa * 0.7, by - asa * lado,
                                fill="#A0A5B0", width=max(1, larg-1))
                cv.create_line(bx + cabo, by, bx + cabo + asa * 0.7, by + asa * lado,
                                fill="#A0A5B0", width=max(1, larg-1))
                # Ponta das guardas
                cv.create_oval(bx + cabo + asa*0.7 - 2, by - asa*lado - 2,
                                bx + cabo + asa*0.7 + 2, by - asa*lado + 2, fill="#C8C8D0")
                cv.create_oval(bx + cabo + asa*0.7 - 2, by + asa*lado - 2,
                                bx + cabo + asa*0.7 + 2, by + asa*lado + 2, fill="#C8C8D0")

        # ── GARRAS (knuckle-duster com 3 lâminas curtas em leque) ──────────
        elif estilo == "Garras":
            for i, offset in enumerate(offsets):
                lado = -1 if i == 0 else 1
                bx = cx + raio + 8
                by = cy + offset
                # Base (knuckle): retângulo
                cv.create_rectangle(bx, by - larg - 2, bx + cabo, by + larg + 2,
                                    fill="#4A2810", outline="#6B3A1F", width=1)
                # 3 garras em leque: central, acima, abaixo
                for ang_deg in [-30 * lado, 0, 30 * lado]:
                    ang = _math.radians(ang_deg)
                    gx  = bx + cabo + _math.cos(ang) * lam * 0.8
                    gy  = by + _math.sin(ang) * lam * 0.8
                    cv.create_line(bx + cabo, by, gx, gy, fill=cor, width=max(1, larg-1))
                    cv.create_oval(gx-2, gy-2, gx+2, gy+2, fill=cor_rar, outline=cor_rar)
                # Nós dos dedos (estética)
                for k in range(3):
                    kx = bx + cabo * (k+1) / 4
                    cv.create_oval(kx-2, by-2, kx+2, by+2, fill="#8B6040", outline="")

        # ── TONFAS (bastão-L: cabo curto perpendicular + braço longo) ──────
        elif estilo == "Tonfas":
            for i, offset in enumerate(offsets):
                lado = -1 if i == 0 else 1
                bx = cx + raio + 8
                by = cy + offset
                # Braço horizontal principal
                cv.create_line(bx, by, bx + lam, by, fill=cor, width=larg)
                # Cabo perpendicular (bastão-L — desce a partir de 1/4 do braço)
                pivot_x = bx + lam * 0.25
                cv.create_line(pivot_x, by, pivot_x, by + cabo * lado,
                                fill="#6B3A1F", width=max(2, larg-1))
                # Ponta brilhante do braço
                cv.create_oval(bx + lam - 3, by - 3, bx + lam + 3, by + 3,
                                fill=cor_rar, outline=cor_rar)
                # Ponta do cabo
                cv.create_oval(pivot_x - 2, by + cabo*lado - 2,
                                pivot_x + 2, by + cabo*lado + 2,
                                fill="#A0A5B0", outline="")
                # Faixa de grip no cabo
                for fi in [0.3, 0.6]:
                    fy = by + cabo * lado * fi
                    cv.create_line(pivot_x - larg, fy, pivot_x + larg, fy,
                                   fill="#3A1A08", width=1)

        # ── FACAS TÁTICAS (lâmina militarista reta, serrilhada) ────────────
        else:  # "Facas Táticas" ou fallback genérico
            for i, offset in enumerate(offsets):
                lado = -1 if i == 0 else 1
                bx = cx + raio + 8
                by = cy + offset
                # Cabo texturizado
                cv.create_rectangle(bx, by - larg - 1, bx + cabo, by + larg + 1,
                                    fill="#3A1A08", outline="#6B3A1F", width=1)
                # Guarda
                cv.create_line(bx + cabo, by - larg - 3, bx + cabo, by + larg + 3,
                                fill="#A0A5B0", width=2)
                # Lâmina principal reta
                tip_x = bx + cabo + lam
                cv.create_polygon(
                    bx + cabo, by - larg,
                    bx + cabo + lam * 0.85, by - max(1, larg//2),
                    tip_x, by,
                    bx + cabo + lam * 0.85, by + max(1, larg//2),
                    bx + cabo, by + larg,
                    fill=cor, outline=cor_rar
                )
                # Fio (highlight central)
                cv.create_line(bx + cabo, by, tip_x, by, fill="#DDEEFF", width=1)
                # Serrilha no dorso (3 dentes)
                for si in range(1, 4):
                    sx = bx + cabo + lam * si / 4.5
                    cv.create_line(sx, by - larg, sx - 3, by - larg - 4,
                                   fill="#B0B5C0", width=1)
                # Ponta brilhante
                cv.create_oval(tip_x-3, by-3, tip_x+3, by+3, fill=cor_rar, outline=cor_rar)


    def desenhar_arma_corrente(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Corrente por estilo.
        Estilos: Kusarigama, Flail (Mangual), Chicote, Corrente com Peso.
        """
        import math as _math
        cv   = self.canvas_preview
        bx   = cx + raio

        # ── KUSARIGAMA — foice pequena + corrente + peso ────────────────────
        if "Kusarigama" in estilo:
            comp   = 80 * 0.55
            ponta  = max(10, int(18 * 0.7))
            cabo_t = 15 * 0.4
            # Cabo curto da foice
            cv.create_rectangle(bx, cy - 3, bx + cabo_t, cy + 3, fill="#6B3A1F", outline="#4A2810")
            # Lâmina da foice (arco)
            cv.create_arc(bx + cabo_t - 5, cy - ponta, bx + cabo_t + ponta, cy + ponta,
                           start=90, extent=180, style="arc", outline=cor, width=3)
            # Corrente (linha ondulada)
            chain_pts = []
            for i in range(12):
                t = i / 11
                ex = bx + cabo_t + 6 + comp * t
                ey = cy + _math.sin(t * _math.pi * 3) * 8
                chain_pts.append((ex, ey))
            if len(chain_pts) > 1:
                for j in range(0, len(chain_pts)-1, 2):
                    cv.create_oval(chain_pts[j][0]-3, chain_pts[j][1]-2,
                                   chain_pts[j][0]+3, chain_pts[j][1]+2,
                                   outline="#8A8C98", width=1)
            # Peso (bola pequena)
            wx = bx + cabo_t + 6 + comp
            wy = cy
            cv.create_oval(wx - 7, wy - 7, wx + 7, wy + 7, fill=cor, outline=cor_rar, width=2)

        # ── FLAIL (MANGUAL) — cabo + corrente + bola espigada ──────────────
        elif "Mangual" in estilo or "Flail" in estilo:
            comp   = 80 * 0.6
            ponta  = max(12, int(20 * 0.8))
            cabo_t = 18 * 0.45
            # Cabo
            cv.create_rectangle(bx, cy - 5, bx + cabo_t, cy + 5, fill="#6B3A1F", outline="#4A2810")
            cv.create_oval(bx + cabo_t - 4, cy - 5, bx + cabo_t + 4, cy + 5, outline="#A0A5B0", width=2)
            # Elos da corrente
            elo_x = bx + cabo_t + 4
            for i in range(8):
                t = i / 7
                ex = elo_x + comp * t
                ey = cy + _math.sin(t * _math.pi) * 14
                ew, eh = (8, 4) if i % 2 == 0 else (5, 7)
                cv.create_rectangle(ex - ew//2, ey - eh//2, ex + ew//2, ey + eh//2,
                                     fill="#6A6C78", outline="#9A9CA8")
            # Bola espigada
            bx2 = elo_x + comp + 4
            by2 = cy + _math.sin(_math.pi * 0.9) * 14
            cv.create_oval(bx2 - ponta, by2 - ponta, bx2 + ponta, by2 + ponta, fill=cor, outline=cor_rar, width=2)
            for sa in [0, 90, 180, 270]:
                sr = _math.radians(sa)
                cv.create_line(bx2 + _math.cos(sr) * (ponta-1), by2 + _math.sin(sr) * (ponta-1),
                                bx2 + _math.cos(sr) * (ponta+7), by2 + _math.sin(sr) * (ponta+7),
                                fill=cor, width=3)
            cv.create_oval(bx2 - ponta//3, by2 - ponta//3, bx2, by2, fill="#FFFFFF", outline="")

        # ── CHICOTE — longo, fino, sinuoso, sem ponta pesada ───────────────
        elif "Chicote" in estilo:
            comp = 120 * 0.65
            cabo_t = 15 * 0.5
            # Cabo de couro
            cv.create_rectangle(bx, cy - 4, bx + cabo_t, cy + 4, fill="#3A1A08", outline="#5C3317")
            # Ondas do chicote (afunilando)
            num_seg = 20
            pts = []
            for i in range(num_seg + 1):
                t = i / num_seg
                ex = bx + cabo_t + comp * t
                amplitude = 14 * (1 - t * 0.8)
                ey = cy + _math.sin(t * _math.pi * 3.5) * amplitude
                pts.append((ex, ey))
            for j in range(len(pts) - 1):
                thick = max(1, int(4 * (1 - j / num_seg)))
                shade = int(80 + 60 * (j / num_seg))
                color_str = f"#{shade:02x}{shade//2:02x}00"
                cv.create_line(pts[j][0], pts[j][1], pts[j+1][0], pts[j+1][1],
                                fill=color_str, width=thick)
            # Ponta (nó)
            if pts:
                cv.create_oval(pts[-1][0]-3, pts[-1][1]-3, pts[-1][0]+3, pts[-1][1]+3, fill=cor_rar, outline="")

        # ── CORRENTE COM PESO — corrente grossa + peso retangular ──────────
        else:
            comp   = 90 * 0.6
            ponta  = max(10, int(20 * 0.7))
            cabo_t = 15 * 0.4
            # Argola de pulso
            cv.create_oval(bx, cy - 6, bx + 12, cy + 6, outline="#A0A5B0", width=2)
            # Elos grandes e quadrados
            for i in range(7):
                t = i / 6
                ex = bx + 12 + comp * t
                ey = cy + _math.sin(t * _math.pi * 2) * 10
                cv.create_rectangle(ex - 5, ey - 3, ex + 5, ey + 3, fill="#5A5C68", outline="#8A8C98")
                cv.create_rectangle(ex - 3, ey - 5, ex + 3, ey + 5, fill="#5A5C68", outline="#8A8C98")
            # Peso — bloco metálico
            wx = bx + 12 + comp
            wy = cy
            cv.create_rectangle(wx - ponta, wy - ponta*0.8, wx + ponta, wy + ponta*0.8,
                                  fill=cor, outline=cor_rar, width=2)
            cv.create_rectangle(wx - ponta + 2, wy - ponta*0.8 + 2, wx - ponta//3, wy - ponta*0.3,
                                  fill="#FFFFFF", outline="")


    def desenhar_arma_arremesso(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Arremesso por estilo.
        Estilos: Machado (Não Retorna), Faca (Rápida), Chakram (Retorna), Bumerangue.
        """
        import math as _math
        cv  = self.canvas_preview
        tam = 15
        qtd = max(1, min(5, int(self.dados_arma.get("quantidade", 3))))

        for i in range(qtd):
            oy = cy + (i - (qtd - 1) / 2) * 28
            bx = cx + raio + 20

            # ── MACHADO (Não Retorna) — lâmina de machado assimétrica ──────
            if "Machado" in estilo:
                # Cabo
                cv.create_line(bx, oy, bx + tam * 0.4, oy, fill="#6B3A1F", width=3)
                # Cabeça de machado
                head_x = bx + tam * 0.4
                cv.create_polygon(
                    head_x, oy - tam * 0.8,
                    head_x + tam * 0.7, oy - tam * 0.4,
                    head_x + tam * 0.8, oy,
                    head_x + tam * 0.7, oy + tam * 0.2,
                    head_x, oy + tam * 0.3,
                    fill=cor, outline=cor_rar, width=1
                )
                cv.create_oval(head_x + tam*0.1, oy - tam*0.1, head_x + tam*0.35, oy + tam*0.1, fill="#FFFFFF", outline="")

            # ── CHAKRAM (Retorna) — anel circular com fio interno ──────────
            elif "Chakram" in estilo:
                r = max(8, int(tam * 0.6))
                # Anel exterior
                cv.create_oval(bx - r, oy - r, bx + r, oy + r, outline=cor, width=max(3, r//3))
                cv.create_oval(bx - r, oy - r, bx + r, oy + r, outline=cor_rar, width=1)
                # Raios internos
                for ang_d in [0, 60, 120]:
                    ang_r = _math.radians(ang_d)
                    cv.create_line(bx + _math.cos(ang_r)*r*0.4, oy + _math.sin(ang_r)*r*0.4,
                                   bx - _math.cos(ang_r)*r*0.4, oy - _math.sin(ang_r)*r*0.4,
                                   fill=cor_rar, width=1)
                cv.create_oval(bx - 3, oy - 3, bx + 3, oy + 3, fill=cor_rar, outline="")

            # ── BUMERANGUE — forma curvada em V assimétrico ─────────────────
            elif "Bumerangue" in estilo:
                cv.create_polygon(
                    bx, oy,
                    bx + tam * 0.5, oy - tam * 0.7,
                    bx + tam * 0.7, oy - tam * 0.55,
                    bx + tam * 0.35, oy + tam * 0.1,
                    bx + tam * 0.85, oy + tam * 0.55,
                    bx + tam * 0.65, oy + tam * 0.7,
                    smooth=True, fill=cor, outline=cor_rar, width=2
                )
                cv.create_oval(bx - 2, oy - 2, bx + 4, oy + 4, fill=cor_rar, outline="")

            # ── FACA (Rápida) — lâmina de throwing knife esbelta ───────────
            else:
                # Lâmina estreita e pontiaguda
                cv.create_polygon(
                    bx, oy - max(2, int(tam * 0.2)),
                    bx + tam * 0.25, oy - max(2, int(tam * 0.15)),
                    bx + tam * 1.2, oy,
                    bx + tam * 0.25, oy + max(2, int(tam * 0.15)),
                    bx, oy + max(2, int(tam * 0.2)),
                    fill=cor, outline=cor_rar, width=1
                )
                # Cabo pequeno
                cv.create_rectangle(bx - tam * 0.3, oy - max(2, int(tam * 0.18)),
                                     bx, oy + max(2, int(tam * 0.18)),
                                     fill="#3A1A08", outline="#6B3A1F")
                cv.create_oval(bx + tam*1.1 - 2, oy - 2, bx + tam*1.2 + 2, oy + 2, fill=cor_rar, outline="")


    def desenhar_arma_arco(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Arco por estilo.
        Estilos: Arco Curto, Arco Longo, Besta, Besta de Repetição.
        """
        import math as _math
        cv    = self.canvas_preview
        tam   = 60
        flecha = 40

        # ── BESTA / BESTA DE REPETIÇÃO — horizontal, limbo e gatilho ───────
        if "Besta" in estilo:
            # Coronha (stock)
            cv.create_rectangle(cx - tam*0.2, cy - 5, cx + tam*0.35, cy + 5, fill="#6B3A1F", outline="#4A2810")
            # Limbo horizontal (os "braços" da besta)
            mid_x = cx + tam * 0.28
            cv.create_arc(mid_x - tam*0.35, cy - tam*0.38, mid_x + tam*0.35, cy + tam*0.38,
                           start=80, extent=20, style="arc", outline=cor, width=4)
            cv.create_arc(mid_x - tam*0.35, cy - tam*0.38, mid_x + tam*0.35, cy + tam*0.38,
                           start=-100, extent=20, style="arc", outline=cor, width=4)
            # Corda
            cv.create_line(mid_x - tam*0.32, cy - tam*0.28, mid_x + flecha * 0.4, cy, fill="#C8B060", width=2)
            cv.create_line(mid_x - tam*0.32, cy + tam*0.28, mid_x + flecha * 0.4, cy, fill="#C8B060", width=2)
            # Virote (bolto)
            bolt_end = cx + tam * 0.35 + flecha * 0.6
            cv.create_line(cx + tam*0.35, cy, bolt_end, cy, fill="#8B4513", width=2)
            cv.create_polygon(bolt_end, cy, bolt_end - 8, cy - 4, bolt_end - 8, cy + 4, fill=cor_rar)
            # Pente (repetição)
            if "Repetição" in estilo:
                cv.create_rectangle(mid_x - 8, cy - 16, mid_x + 8, cy - 6,
                                     fill="#5A3010", outline="#8B5020", width=1)
                for ri in range(3):
                    cv.create_line(mid_x - 5, cy - 14 + ri*3, mid_x + 5, cy - 14 + ri*3, fill="#8B5020", width=1)

        # ── ARCO LONGO — alto, curvatura suave, sem decoração ──────────────
        elif "Longo" in estilo:
            span = tam * 0.85
            cv.create_arc(cx - span*0.6, cy - span, cx + span*0.6, cy + span,
                           start=55, extent=70, style="arc", outline=cor, width=5)
            # Corda tensionada
            y1 = cy - _math.sin(_math.radians(55)) * span
            y2 = cy + _math.sin(_math.radians(55)) * span
            x_str = cx - _math.cos(_math.radians(55)) * span * 0.6
            cv.create_line(x_str, cy - abs(y1 - cy), x_str, cy + abs(y2 - cy), fill="#C8B060", width=2)
            # Flecha
            cv.create_line(cx, cy, cx + raio + flecha, cy, fill="#8B4513", width=2)
            cv.create_polygon(cx + raio + flecha, cy, cx + raio + flecha - 10, cy - 5,
                               cx + raio + flecha - 10, cy + 5, fill=cor_rar)
            # Penas
            px = cx + 18
            cv.create_line(px, cy, px - 8, cy - 6, fill="#CC4444", width=2)
            cv.create_line(px, cy, px - 8, cy + 6, fill="#CC4444", width=2)

        # ── ARCO CURTO (default) — compacto, mais curvado ──────────────────
        else:
            span = tam * 0.55
            cv.create_arc(cx - span, cy - span, cx + span, cy + span,
                           start=-60, extent=120, style="arc", outline=cor, width=4)
            # Corda
            x1 = cx + span * _math.cos(_math.radians(60))
            y1 = cy - span * _math.sin(_math.radians(60))
            x2 = cx + span * _math.cos(_math.radians(-60))
            y2 = cy - span * _math.sin(_math.radians(-60))
            cv.create_line(x1, y1, x2, y2, fill="#C8B060", width=2)
            # Flecha
            cv.create_line(cx, cy, cx + raio + flecha, cy, fill="#8B4513", width=2)
            cv.create_polygon(cx + raio + flecha, cy, cx + raio + flecha - 8, cy - 4,
                               cx + raio + flecha - 8, cy + 4, fill=cor_rar)
            px = cx + 14
            cv.create_line(px, cy, px - 6, cy - 5, fill="#CC4444", width=2)
            cv.create_line(px, cy, px - 6, cy + 5, fill="#CC4444", width=2)


    def desenhar_arma_orbital(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Orbital por estilo.
        Estilos: Defensivo (Escudo), Ofensivo (Drone), Mágico (Orbe), Lâminas Orbitais.
        """
        import math as _math
        cv   = self.canvas_preview
        dist = 30
        qtd  = max(1, min(6, int(self.dados_arma.get("quantidade_orbitais", 2))))
        raio_orb = raio + dist * 0.7

        # Órbita pontilhada (comum a todos)
        cv.create_oval(cx - raio_orb, cy - raio_orb, cx + raio_orb, cy + raio_orb,
                        outline="#333344", dash=(3, 5))

        for i in range(qtd):
            ang = _math.radians((360 / qtd) * i + 30)
            ox  = cx + _math.cos(ang) * raio_orb
            oy  = cy + _math.sin(ang) * raio_orb

            # ── ESCUDO — arco sólido em volta da posição ─────────────────
            if "Escudo" in estilo or "Defensivo" in estilo:
                larg = 40
                arc_span = min(90, larg)
                cv.create_arc(ox - larg*0.35, oy - larg*0.35, ox + larg*0.35, oy + larg*0.35,
                               start=_math.degrees(ang) + 90 - arc_span/2,
                               extent=arc_span, style="arc", outline=cor, width=6)
                cv.create_arc(ox - larg*0.35, oy - larg*0.35, ox + larg*0.35, oy + larg*0.35,
                               start=_math.degrees(ang) + 90 - arc_span/2,
                               extent=arc_span, style="arc", outline=cor_rar, width=1)

            # ── DRONE — forma hexagonal com propulsor ───────────────────
            elif "Drone" in estilo or "Ofensivo" in estilo:
                r2 = 9
                pts = []
                for j in range(6):
                    a = _math.radians(j * 60 + ang * 30)
                    pts.extend([ox + _math.cos(a)*r2, oy + _math.sin(a)*r2])
                cv.create_polygon(pts, fill=cor, outline=cor_rar, width=1)
                cv.create_oval(ox - 3, oy - 3, ox + 3, oy + 3, fill=cor_rar, outline="")
                # Propulsor
                cv.create_line(ox, oy, ox + _math.cos(ang + _math.pi)*14,
                                oy + _math.sin(ang + _math.pi)*14, fill="#88CCFF", width=2)

            # ── LÂMINAS ORBITAIS — mini espadas girando ──────────────────
            elif "Lâminas" in estilo:
                blade_len = 20 * 0.5
                blade_ang = ang + _math.pi / 4
                bx1 = ox + _math.cos(blade_ang) * blade_len
                by1 = oy + _math.sin(blade_ang) * blade_len
                bx2 = ox - _math.cos(blade_ang) * blade_len
                by2 = oy - _math.sin(blade_ang) * blade_len
                perp = blade_ang + _math.pi/2
                w = max(2, int(blade_len * 0.3))
                cv.create_polygon(
                    int(bx1), int(by1),
                    int(ox + _math.cos(perp)*w), int(oy + _math.sin(perp)*w),
                    int(bx2), int(by2),
                    int(ox - _math.cos(perp)*w), int(oy - _math.sin(perp)*w),
                    fill=cor, outline=cor_rar, width=1
                )
                cv.create_oval(ox - 2, oy - 2, ox + 2, oy + 2, fill=cor_rar, outline="")

            # ── ORBE MÁGICO (default) — esfera com glow ─────────────────
            else:
                r2 = max(6, int(20 * 0.22))
                cv.create_oval(ox - r2 - 3, oy - r2 - 3, ox + r2 + 3, oy + r2 + 3, fill="#222244", outline="")
                cv.create_oval(ox - r2, oy - r2, ox + r2, oy + r2, fill=cor, outline=cor_rar, width=2)
                cv.create_oval(ox - r2//2, oy - r2//2, ox, oy, fill="#FFFFFF", outline="")


    def desenhar_arma_magica(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Mágica por estilo.
        Estilos: Espadas Espectrais, Runas Flutuantes, Tentáculos Sombrios, Cristais Arcanos.
        """
        import math as _math
        cv   = self.canvas_preview
        qtd  = max(1, min(5, int(self.dados_arma.get("quantidade", 3))))
        tam  = 15
        dist = 60 * 0.55

        for i in range(qtd):
            if qtd > 1:
                ang_d = -35 + (70 / (qtd - 1)) * i
            else:
                ang_d = 0
            ang = _math.radians(ang_d)
            d   = raio + dist * (0.6 + i * 0.12)
            ox  = cx + d * _math.cos(ang)
            oy  = cy + d * _math.sin(ang)

            # ── ESPADAS ESPECTRAIS — mini espada translúcida ────────────
            if "Espada" in estilo or "Espectral" in estilo:
                blade = tam * 1.8
                px = _math.cos(ang)
                py = _math.sin(ang)
                perp_x = _math.cos(ang + _math.pi/2) * tam * 0.35
                perp_y = _math.sin(ang + _math.pi/2) * tam * 0.35
                tip_x = ox + px * blade
                tip_y = oy + py * blade
                cv.create_polygon(
                    int(ox - perp_x), int(oy - perp_y),
                    int(ox + perp_x), int(oy + perp_y),
                    int(tip_x + perp_x*0.2), int(tip_y + perp_y*0.2),
                    int(tip_x), int(tip_y),
                    int(tip_x - perp_x*0.2), int(tip_y - perp_y*0.2),
                    fill=cor, outline=cor_rar, width=1, stipple="gray75"
                )
                # Guarda
                cv.create_line(
                    int(ox - perp_x*2), int(oy - perp_y*2),
                    int(ox + perp_x*2), int(oy + perp_y*2),
                    fill=cor_rar, width=2
                )
                cv.create_oval(int(tip_x)-2, int(tip_y)-2, int(tip_x)+2, int(tip_y)+2, fill=cor_rar, outline="")

            # ── RUNAS FLUTUANTES — símbolo rúnico geométrico ────────────
            elif "Runa" in estilo:
                r2 = max(8, int(tam * 0.7))
                cv.create_oval(ox-r2, oy-r2, ox+r2, oy+r2, outline=cor, width=2)
                # Cruz rúnica interior
                cv.create_line(ox, oy-r2+2, ox, oy+r2-2, fill=cor_rar, width=1)
                cv.create_line(ox-r2+2, oy, ox+r2-2, oy, fill=cor_rar, width=1)
                # Diagonais
                d2 = int(r2 * 0.6)
                cv.create_line(ox-d2, oy-d2, ox+d2, oy+d2, fill=cor, width=1)
                cv.create_line(ox+d2, oy-d2, ox-d2, oy+d2, fill=cor, width=1)
                cv.create_oval(ox-2, oy-2, ox+2, oy+2, fill=cor_rar, outline="")

            # ── TENTÁCULOS SOMBRIOS — forma sinuosa com ventosas ─────────
            elif "Tentáculo" in estilo:
                length = tam * 2.2
                px = _math.cos(ang)
                py = _math.sin(ang)
                pts = []
                for s in range(8):
                    t = s / 7
                    wave = _math.sin(t * _math.pi * 2.5) * tam * 0.4 * (1 - t * 0.3)
                    wx = ox + px * length * t + _math.cos(ang + _math.pi/2) * wave
                    wy = oy + py * length * t + _math.sin(ang + _math.pi/2) * wave
                    pts.extend([int(wx), int(wy)])
                if len(pts) >= 4:
                    cv.create_line(pts, fill=cor, width=max(2, int(tam*0.3)), smooth=True)
                # Ventosas
                for s in range(1, 4):
                    t = s / 4
                    wx = int(ox + px * length * t)
                    wy = int(oy + py * length * t)
                    cv.create_oval(wx-2, wy-2, wx+2, wy+2, fill=cor_rar, outline="")

            # ── CRISTAIS ARCANOS — forma de gema multifacetada ──────────
            else:
                r2 = max(6, int(tam * 0.65))
                cv.create_polygon(
                    int(ox), int(oy - r2 * 1.4),
                    int(ox + r2), int(oy - r2 * 0.3),
                    int(ox + r2 * 0.6), int(oy + r2),
                    int(ox - r2 * 0.6), int(oy + r2),
                    int(ox - r2), int(oy - r2 * 0.3),
                    fill=cor, outline=cor_rar, width=1
                )
                # Facetas
                cv.create_line(int(ox), int(oy - r2*1.4), int(ox + r2*0.6), int(oy + r2), fill=cor_rar, width=1)
                cv.create_line(int(ox), int(oy - r2*1.4), int(ox - r2*0.6), int(oy + r2), fill=cor_rar, width=1)
                cv.create_line(int(ox - r2), int(oy - r2*0.3), int(ox + r2), int(oy - r2*0.3), fill="#FFFFFF", width=1)
                cv.create_oval(ox-2, oy-r2//2-2, ox+2, oy-r2//2+2, fill="#FFFFFF", outline="")

    def desenhar_arma_transformavel(self, cx, cy, raio, cor, cor_rar, estilo=""):
        """Desenha arma do tipo Transformável — mostra ambas as formas com seta de transformação.
        Estilos: Espada↔Lança, Compacta↔Estendida, Chicote↔Espada, Arco↔Lâminas.
        """
        import math as _math
        cv   = self.canvas_preview
        bx   = cx + raio
        larg = 5

        # Geometria das duas formas
        cabo1 = 20
        lam1  = 50
        cabo2 = 30
        lam2  = 80

        # Seta de transformação no centro
        cv.create_text(cx - 45, cy, text="⟳", fill=cor_rar, font=("Arial", 14, "bold"))
        cv.create_line(cx - 30, cy - 22, cx - 30, cy + 22, fill="#555566", width=1, dash=(3,3))

        # ── ESPADA ↔ LANÇA ─────────────────────────────────────────────────
        if "Lança" in estilo and "Espada" in estilo:
            # Forma 1: Espada (acima)
            cv.create_text(bx + 2, cy - 35, text="Espada", fill="#888", font=("Arial", 7), anchor="w")
            cv.create_rectangle(bx, cy-28-larg//3, bx+cabo1, cy-28+larg//3, fill="#6B3A1F", outline="#4A2810")
            cv.create_rectangle(bx+cabo1-2, cy-28-larg-2, bx+cabo1+4, cy-28+larg+2, fill="#A0A5B0")
            cv.create_polygon(bx+cabo1+4, cy-28-larg, bx+cabo1+4+lam1*0.9, cy-28-larg//3,
                               bx+cabo1+4+lam1, cy-28, bx+cabo1+4+lam1*0.9, cy-28+larg//3,
                               bx+cabo1+4, cy-28+larg, fill=cor, outline=cor_rar, width=1)
            # Forma 2: Lança (abaixo)
            cv.create_text(bx + 2, cy + 20, text="Lança", fill="#888", font=("Arial", 7), anchor="w")
            cv.create_rectangle(bx, cy+26-larg//4, bx+cabo2, cy+26+larg//4, fill="#6B3A1F", outline="#4A2810")
            cv.create_polygon(bx+cabo2, cy+26-larg*0.6, bx+cabo2+lam2*0.12, cy+26-larg*0.2,
                               bx+cabo2+lam2, cy+26, bx+cabo2+lam2*0.12, cy+26+larg*0.2,
                               bx+cabo2, cy+26+larg*0.6, fill=cor, outline=cor_rar, width=1)

        # ── CHICOTE ↔ ESPADA ────────────────────────────────────────────────
        elif "Chicote" in estilo and "Espada" in estilo:
            cv.create_text(bx + 2, cy - 35, text="Espada", fill="#888", font=("Arial", 7), anchor="w")
            cv.create_rectangle(bx, cy-28-larg//3, bx+cabo1, cy-28+larg//3, fill="#6B3A1F")
            cv.create_polygon(bx+cabo1, cy-28-larg, bx+cabo1+lam1*0.9, cy-28-larg//3,
                               bx+cabo1+lam1, cy-28, bx+cabo1+lam1*0.9, cy-28+larg//3,
                               bx+cabo1, cy-28+larg, fill=cor, outline=cor_rar, width=1)
            cv.create_text(bx + 2, cy + 20, text="Chicote", fill="#888", font=("Arial", 7), anchor="w")
            cv.create_rectangle(bx, cy+26-larg//3, bx+cabo2*0.4, cy+26+larg//3, fill="#3A1A08")
            # Chicote ondulado
            num = 14
            pts = []
            for j in range(num+1):
                t = j/num
                ex = bx + cabo2*0.4 + lam2*0.9*t
                amplitude = 10*(1-t*0.7)
                ey = cy+26 + _math.sin(t*_math.pi*3)*amplitude
                pts.extend([ex, ey])
            cv.create_line(pts, fill=cor, width=max(1, larg-1), smooth=True)

        # ── ARco ↔ LÂMINAS ──────────────────────────────────────────────────
        elif "Arco" in estilo:
            cv.create_text(bx + 2, cy - 35, text="Arco", fill="#888", font=("Arial", 7), anchor="w")
            span = lam1 * 0.4
            cv.create_arc(bx-span*0.4, cy-28-span, bx+span*0.4, cy-28+span,
                           start=55, extent=70, style="arc", outline=cor, width=4)
            cv.create_line(bx-span*0.35, cy-28-span*0.8, bx-span*0.35, cy-28+span*0.8,
                           fill="#C8B060", width=2)
            cv.create_line(bx-span*0.35+2, cy-28, bx+lam1*0.6, cy-28, fill="#8B4513", width=2)
            cv.create_text(bx + 2, cy + 20, text="Lâminas", fill="#888", font=("Arial", 7), anchor="w")
            for j, oy_off in enumerate([-8, 8]):
                cv.create_polygon(bx, cy+26+oy_off-larg//2,
                                   bx+lam2*0.8, cy+26+oy_off//2,
                                   bx+lam2, cy+26+oy_off,
                                   bx+lam2*0.8, cy+26+oy_off*1.5,
                                   bx, cy+26+oy_off+larg//2,
                                   fill=cor, outline=cor_rar, width=1)

        # ── COMPACTA ↔ ESTENDIDA (generic) ─────────────────────────────────
        else:
            cv.create_text(bx + 2, cy - 35, text="Compacta", fill="#888", font=("Arial", 7), anchor="w")
            cv.create_rectangle(bx, cy-28-larg//3, bx+cabo1, cy-28+larg//3, fill="#6B3A1F")
            cv.create_rectangle(bx+cabo1, cy-28-larg//2, bx+cabo1+lam1, cy-28+larg//2, fill=cor, outline=cor_rar, width=2)
            cv.create_text(bx + 2, cy + 20, text="Estendida", fill="#888", font=("Arial", 7), anchor="w")
            cv.create_rectangle(bx, cy+26-larg//4, bx+cabo2, cy+26+larg//4, fill="#6B3A1F")
            cv.create_polygon(bx+cabo2, cy+26-larg*0.6, bx+cabo2+lam2, cy+26, bx+cabo2, cy+26+larg*0.6,
                               fill=cor, outline=cor_rar, width=1)
            # Mecanismo (círculo no pivô)
        cv.create_oval(bx+cabo1-4, cy-28-4, bx+cabo1+4, cy-28+4, outline=cor_rar, width=2)


    # =========================================================================
    # ACOES
    # =========================================================================
    
    def atualizar_dado(self, chave, valor):
        """Atualiza um dado da arma"""
        self.dados_arma[chave] = valor
        self.atualizar_preview()
        self.criar_resumo_stats()

    def salvar_arma(self):
        """Salva a arma no banco de dados"""
        dados = self.dados_arma
        
        if not dados["nome"]:
            messagebox.showerror("Erro", "A arma precisa de um nome!")
            return

        # BUG-F1: Verificar duplicata de nome (salvar_personagem já faz isso, armas não tinham)
        _state_check = AppState.get()
        for i, a in enumerate(_state_check.weapons):
            if a.nome.lower() == dados["nome"].lower():
                if self.indice_em_edicao is None or self.indice_em_edicao != i:
                    messagebox.showerror("Erro", f"Já existe uma arma chamada '{dados['nome']}'!")
                    return



        cores = dados["cores"]
        
        try:
            nova = Arma(
                nome=dados["nome"],
                quantidade=dados.get("quantidade", 1),
                quantidade_orbitais=dados.get("quantidade_orbitais", 1),
                forca_arco=dados.get("forca_arco", 0),
                tipo=dados["tipo"],
                dano=dados["dano"],
                peso=dados["peso"],
                raridade=dados["raridade"],
                estilo=dados.get("estilo", ""),
                # Geometria basica
                # Geometria extra
                # Cores
                r=cores["r"], g=cores["g"], b=cores["b"],
                # Habilidades
                habilidades=dados["habilidades"],
                encantamentos=dados["encantamentos"],
                cabo_dano=dados["cabo_dano"],
                afinidade_elemento=dados["afinidade_elemento"],
            )
            
            _state = AppState.get()
            if self.indice_em_edicao is not None:
                _state.update_weapon(self.indice_em_edicao, nova)
                self.indice_em_edicao = None
            else:
                _state.add_weapon(nova)
            self.atualizar_lista()
            self.nova_arma()
            
            messagebox.showinfo(
                "Arma Forjada!", 
                f"{nova.nome} foi forjada com sucesso!\n"
                f"Raridade: {nova.raridade}\n"
                f"Dano: {nova.dano:.0f}"
            )
            
        except Exception as e:
            messagebox.showerror("Erro ao Forjar", str(e))

    def atualizar_lista(self):
        """Atualiza a lista de armas"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for arma in self.controller.lista_armas:
            raridade = getattr(arma, 'raridade', 'Comum')
            self.tree.insert("", "end", values=(arma.nome, arma.tipo, raridade))

    def _normalizar_habilidades(self, habilidades):
        """Converte lista de habilidades para formato padrão (lista de dicts)"""
        if not habilidades:
            return []
        
        resultado = []
        for hab in habilidades:
            if isinstance(hab, dict):
                # Já está no formato correto
                resultado.append(hab)
            elif isinstance(hab, str):
                # String simples - converte para dict
                custo = SKILL_DB.get(hab, {}).get("custo", 0)
                resultado.append({"nome": hab, "custo": custo})
            else:
                # Outro formato - tenta converter
                resultado.append({"nome": str(hab), "custo": 0})
        
        return resultado

    def selecionar_arma(self, event):
        """Seleciona uma arma da lista"""
        sel = self.tree.selection()
        if not sel:
            return
        
        idx = self.tree.index(sel[0])
        arma = self.controller.lista_armas[idx]
        
        # Preenche dados para edicao
        self.dados_arma = {
            "nome": arma.nome,
            "tipo": arma.tipo,
            "raridade": getattr(arma, 'raridade', 'Comum'),
            "estilo": arma.estilo,
            "dano": arma.dano_base if hasattr(arma, 'dano_base') else arma.dano,
            "peso": arma.peso_base if hasattr(arma, 'peso_base') else arma.peso,
            "geometria": {
                "largura": arma.largura,
                "distancia": arma.distancia,
                "quantidade": getattr(arma, 'quantidade', 1),
                "forca_arco": getattr(arma, 'forca_arco', 0),
                "quantidade_orbitais": getattr(arma, 'quantidade_orbitais', 1),
                "tamanho": getattr(arma, 'tamanho', 0),
            },
            "cores": {"r": arma.r, "g": arma.g, "b": arma.b},
            "habilidades": self._normalizar_habilidades(getattr(arma, 'habilidades', [])),
            "encantamentos": getattr(arma, 'encantamentos', []),
            "cabo_dano": arma.cabo_dano,
            "afinidade_elemento": getattr(arma, 'afinidade_elemento', None),
        }
        
        self.indice_em_edicao = idx
        self.mostrar_passo(1)

    def editar_arma(self):
        """Inicia edicao da arma selecionada"""
        self.selecionar_arma(None)

    def deletar_arma(self):
        """Deleta a arma selecionada"""
        sel = self.tree.selection()
        if not sel:
            return
        
        idx = self.tree.index(sel[0])
        arma = self.controller.lista_armas[idx]
        
        if messagebox.askyesno("Confirmar", f"Deletar '{arma.nome}'?"):
            AppState.get().delete_weapon(idx)
            self.atualizar_lista()

    def nova_arma(self):
        """Inicia criacao de nova arma"""
        self.indice_em_edicao = None
        self.dados_arma = {
            "nome": "",
            "tipo": "Reta",
            "raridade": "Comum",
            "estilo": "",
            "dano": 10,
            "peso": 5,
            "cores": {"r": 200, "g": 200, "b": 200},
            "habilidades": [],
            "encantamentos": [],
            "cabo_dano": False,
            "afinidade_elemento": None,
        }
        self.mostrar_passo(1)

    def atualizar_dados(self):
        """Chamado quando a tela e exibida"""
        self.atualizar_lista()
