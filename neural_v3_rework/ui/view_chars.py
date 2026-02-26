"""
CRIADOR DE CAMPEÕES - NEURAL FIGHTS
Sistema de criação de personagens com Wizard guiado
Padrão visual alinhado com a Forja de Armas
"""
import tkinter as tk
from tkinter import ttk, messagebox
import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Personagem, LISTA_CLASSES, CLASSES_DATA, get_class_data
from data import carregar_personagens, salvar_lista_chars, carregar_armas, database
from data.app_state import AppState
from ui.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS, 
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_DANGER, CORES_CLASSE, CATEGORIAS_CLASSE
)


class TelaPersonagens(tk.Frame):
    """Tela principal de criação de personagens com sistema Wizard"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)
        self.indice_em_edicao = None
        
        # Estado do Wizard
        self.passo_atual = 1
        self.total_passos = 7  # [PHASE 3] Passo 7: Aliança Divina
        
        # Dados do personagem sendo criado
        self.dados_char = {
            "nome": "",
            "classe": "Guerreiro (Força Bruta)",
            "personalidade": "Aleatório",
            "tamanho": 1.70,
            "forca": 5.0,
            "mana": 5.0,
            "arma": "",
            "cor_r": 200,
            "cor_g": 50,
            "cor_b": 50,
            "god_id": None,  # [PHASE 3] Vínculo divino
        }
        
        self.setup_ui()

        # Subscribe: refresh weapon dropdown when weapons change
        AppState.get().subscribe("weapons_changed", self._on_weapons_changed)

    def _on_weapons_changed(self, _data=None):
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
        main.grid_columnconfigure(2, weight=2, minsize=210)  # lista
        main.grid_rowconfigure(0, weight=1)

        # Esquerda: Wizard Steps
        self.frame_wizard = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        self.frame_wizard.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Centro: Preview e controles
        self.frame_centro = tk.Frame(main, bg=COR_BG)
        self.frame_centro.grid(row=0, column=1, sticky="nsew", padx=5)

        # Direita: Lista de personagens
        self.frame_lista = tk.Frame(main, bg=COR_BG_SECUNDARIO)
        self.frame_lista.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # Configura cada seção
        self.setup_wizard()
        self.setup_preview()
        self.setup_lista()
        
        # Inicia no passo 1
        self.mostrar_passo(1)

    def criar_header(self):
        """Cria o header com navegação e progresso"""
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
            header, text="CRIADOR DE CAMPEÕES", 
            font=("Helvetica", 20, "bold"), bg=COR_HEADER, fg=COR_TEXTO
        ).pack(side="left", padx=20)
        
        # Indicador de progresso
        self.frame_progresso = tk.Frame(header, bg=COR_HEADER)
        self.frame_progresso.pack(side="right", padx=20)
        
        self.labels_progresso = []
        nomes_passos = ["Identidade", "Classe", "Personalidade", "Atributos", "Visual", "Equipamento", "Divindade"]  # [PHASE 3]
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
        self.lbl_passo_titulo.pack(pady=(15, 5))
        
        self.lbl_passo_desc = tk.Label(
            self.frame_wizard, text="", 
            font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM,
            wraplength=300
        )
        self.lbl_passo_desc.pack(pady=(0, 15))
        self.frame_wizard.bind("<Configure>", self._on_wizard_resize)
        
        # Container para conteúdo do passo (com scroll)
        self.frame_conteudo_container = tk.Frame(self.frame_wizard, bg=COR_BG_SECUNDARIO)
        self.frame_conteudo_container.pack(fill="both", expand=True, padx=15)
        
        # Canvas com scroll para conteúdo
        self.canvas_wizard = tk.Canvas(self.frame_conteudo_container, bg=COR_BG_SECUNDARIO, highlightthickness=0)
        self.scrollbar_wizard = ttk.Scrollbar(self.frame_conteudo_container, orient="vertical", command=self.canvas_wizard.yview)
        
        self.frame_conteudo_passo = tk.Frame(self.canvas_wizard, bg=COR_BG_SECUNDARIO)
        
        self.canvas_wizard.create_window((0, 0), window=self.frame_conteudo_passo, anchor="nw")
        self.canvas_wizard.configure(yscrollcommand=self.scrollbar_wizard.set)
        
        self.canvas_wizard.pack(side="left", fill="both", expand=True)
        self.scrollbar_wizard.pack(side="right", fill="y")
        
        self.frame_conteudo_passo.bind("<Configure>", lambda e: self.canvas_wizard.configure(scrollregion=self.canvas_wizard.bbox("all")))
        
        # Scroll inteligente - rastreia qual canvas está ativo
        self.canvas_armas = None  # Será criado no passo de equipamento
        
        def _on_mousewheel(event):
            # Se o canvas de armas existe e está visível, verifica onde está o mouse
            if self.canvas_armas and self.canvas_armas.winfo_ismapped():
                try:
                    # Pega posição do mouse na tela
                    mouse_x = event.x_root
                    mouse_y = event.y_root
                    
                    # Pega as coordenadas do canvas de armas
                    armas_x1 = self.canvas_armas.winfo_rootx()
                    armas_y1 = self.canvas_armas.winfo_rooty()
                    armas_x2 = armas_x1 + self.canvas_armas.winfo_width()
                    armas_y2 = armas_y1 + self.canvas_armas.winfo_height()
                    
                    # Se o mouse está sobre o canvas de armas, rola ele
                    if armas_x1 <= mouse_x <= armas_x2 and armas_y1 <= mouse_y <= armas_y2:
                        self.canvas_armas.yview_scroll(int(-1*(event.delta/120)), "units")
                        return
                except:
                    pass
            
            # Caso contrário, rola o canvas principal
            self.canvas_wizard.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas_wizard.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Botões de navegação
        frame_nav = tk.Frame(self.frame_wizard, bg=COR_BG_SECUNDARIO)
        frame_nav.pack(side="bottom", fill="x", pady=15, padx=15)
        
        self.btn_anterior = tk.Button(
            frame_nav, text="< Anterior", bg=COR_BG, fg=COR_TEXTO,
            font=("Arial", 10), bd=0, padx=20, pady=8,
            command=self.passo_anterior
        )
        self.btn_anterior.pack(side="left")
        
        self.btn_proximo = tk.Button(
            frame_nav, text="Próximo >", bg=COR_ACCENT, fg=COR_TEXTO,
            font=("Arial", 10, "bold"), bd=0, padx=20, pady=8,
            command=self.passo_proximo
        )
        self.btn_proximo.pack(side="right")

    def _on_wizard_resize(self, event=None):
        """Adjust wraplength of description label to match wizard width."""
        w = self.frame_wizard.winfo_width()
        if w > 40:
            self.lbl_passo_desc.config(wraplength=max(w - 40, 100))

    def setup_preview(self):
        """Configura o preview do personagem"""
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
        self.canvas_preview.pack(fill="both", expand=True, pady=10)
        
        # Resumo dos stats
        self.frame_stats = tk.Frame(self.frame_centro, bg=COR_BG_SECUNDARIO)
        self.frame_stats.pack(fill="x", padx=10, pady=10)
        
        self.criar_resumo_stats()
        
        # Info da classe selecionada
        self.frame_classe_info = tk.Frame(self.frame_centro, bg=COR_BG_SECUNDARIO)
        self.frame_classe_info.pack(fill="x", padx=10, pady=5)
        
        self.lbl_classe_passiva = tk.Label(
            self.frame_classe_info, text="",
            font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_SUCCESS,
            wraplength=280
        )
        self.lbl_classe_passiva.pack(pady=5)

    def criar_resumo_stats(self):
        """Cria o resumo de stats do personagem"""
        for widget in self.frame_stats.winfo_children():
            widget.destroy()
        
        # Calcula stats derivados
        classe_data = get_class_data(self.dados_char["classe"])
        vida_base = 100 + (self.dados_char["forca"] * 10)
        vida_mod = vida_base * classe_data.get("mod_vida", 1.0)
        mana_base = 50 + (self.dados_char["mana"] * 10)
        mana_mod = mana_base * classe_data.get("mod_mana", 1.0)
        velocidade = (10 - self.dados_char["tamanho"] * 2) * classe_data.get("mod_velocidade", 1.0)
        dano_mod = self.dados_char["forca"] * classe_data.get("mod_forca", 1.0)
        
        stats = [
            ("Nome", self.dados_char["nome"] or "???"),
            ("Classe", self.dados_char["classe"].split(" (")[0]),  # Pega só o nome
            ("Altura", f"{self.dados_char['tamanho']:.2f}m"),
            ("HP", f"{vida_mod:.0f}"),
            ("Mana", f"{mana_mod:.0f}"),
            ("Dano", f"{dano_mod:.1f}"),
            ("Velocidade", f"{velocidade:.1f}"),
            ("Arma", self.dados_char["arma"] or "Nenhuma"),
        ]
        
        for i, (nome, valor) in enumerate(stats):
            row = i // 2
            col = i % 2
            
            frame = tk.Frame(self.frame_stats, bg=COR_BG_SECUNDARIO)
            frame.grid(row=row, column=col, padx=10, pady=3, sticky="w")
            
            tk.Label(
                frame, text=f"{nome}:", 
                font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
            ).pack(side="left")
            
            cor = CORES_CLASSE.get(self.dados_char["classe"], COR_TEXTO) if nome == "Classe" else COR_TEXTO
            tk.Label(
                frame, text=valor, 
                font=("Arial", 9, "bold"), bg=COR_BG_SECUNDARIO, fg=cor
            ).pack(side="left", padx=5)

    def setup_lista(self):
        """Configura a lista de personagens existentes"""
        tk.Label(
            self.frame_lista, text="CAMPEÕES", 
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(pady=(15, 10))
        
        # Treeview com scroll
        frame_tree = tk.Frame(self.frame_lista, bg=COR_BG_SECUNDARIO)
        frame_tree.pack(fill="both", expand=True, padx=10)
        
        scroll = ttk.Scrollbar(frame_tree)
        scroll.pack(side="right", fill="y")
        
        cols = ("Nome", "Classe", "Arma")
        self.tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings", height=15,
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree.yview)
        
        self.tree.heading("Nome", text="Nome")
        self.tree.column("Nome", width=70)
        self.tree.heading("Classe", text="Classe")
        self.tree.column("Classe", width=100)
        self.tree.heading("Arma", text="Arma")
        self.tree.column("Arma", width=80)
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar_personagem)
        
        # Botões
        frame_btns = tk.Frame(self.frame_lista, bg=COR_BG_SECUNDARIO)
        frame_btns.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            frame_btns, text="Deletar", bg=COR_DANGER, fg=COR_TEXTO,
            font=("Arial", 9), bd=0, padx=10, pady=5,
            command=self.deletar_personagem
        ).pack(side="left")
        
        tk.Button(
            frame_btns, text="Editar", bg=COR_SUCCESS, fg=COR_BG,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=5,
            command=self.editar_personagem
        ).pack(side="right")
        
        tk.Button(
            frame_btns, text="Novo", bg=COR_ACCENT, fg=COR_TEXTO,
            font=("Arial", 9), bd=0, padx=10, pady=5,
            command=self.novo_personagem
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
        
        # Limpa referência ao canvas de armas (será recriado se necessário)
        self.canvas_armas = None
        
        # Reset scroll
        self.canvas_wizard.yview_moveto(0)
        
        # Mostra passo apropriado
        if passo == 1:
            self.passo_identidade()
        elif passo == 2:
            self.passo_classe()
        elif passo == 3:
            self.passo_personalidade()
        elif passo == 4:
            self.passo_atributos()
        elif passo == 5:
            self.passo_visual()
        elif passo == 6:
            self.passo_equipamento()
        elif passo == 7:
            self.passo_divindade()  # [PHASE 3]
        
        # Atualiza botões
        self.btn_anterior.config(state="normal" if passo > 1 else "disabled")
        
        # Texto do botão baseado no contexto
        if passo == 7:
            self.btn_proximo.config(text="⚡ SALVAR CAMPEÃO", bg=COR_WARNING)
        elif passo == 6:
            if self.indice_em_edicao is not None:
                self.btn_proximo.config(text="⚡ SALVAR CAMPEÃO", bg=COR_WARNING)
            else:
                self.btn_proximo.config(text="CRIAR!", bg="#00ff88")
        else:
            self.btn_proximo.config(text="Próximo >", bg=COR_ACCENT)
        
        self.atualizar_preview()
        self.criar_resumo_stats()
        self.atualizar_info_classe()

    def passo_anterior(self):
        """Volta ao passo anterior"""
        if self.passo_atual > 1:
            self.mostrar_passo(self.passo_atual - 1)

    def passo_proximo(self):
        """Avança para o próximo passo ou salva"""
        # Validação básica por passo
        if self.passo_atual == 1:
            if not self.dados_char["nome"].strip():
                messagebox.showwarning("Atenção", "Digite um nome para o personagem!")
                return
        
        if self.passo_atual < 7:
            self.mostrar_passo(self.passo_atual + 1)
        else:
            self.salvar_personagem()

    # -------------------------------------------------------------------------
    # PASSO 1: IDENTIDADE
    # -------------------------------------------------------------------------
    def passo_identidade(self):
        """Passo 1: Nome e identidade do personagem"""
        self.lbl_passo_titulo.config(text="1. IDENTIDADE")
        self.lbl_passo_desc.config(text="Dê um nome único ao seu campeão. Este será seu legado nas arenas de Neural Fights!")
        
        # Nome do personagem
        frame_nome = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_nome.pack(fill="x", pady=(10, 20))
        
        tk.Label(
            frame_nome, text="Nome do Campeão:", 
            font=("Arial", 11, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        tk.Label(
            frame_nome, text="Escolha um nome memorável que será lembrado pelos espectadores", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
        ).pack(anchor="w", pady=(0, 5))
        
        self.entry_nome = tk.Entry(
            frame_nome, font=("Arial", 14), bg=COR_BG, fg=COR_TEXTO,
            insertbackground=COR_TEXTO, width=30
        )
        self.entry_nome.pack(fill="x", pady=5, ipady=5)
        self.entry_nome.insert(0, self.dados_char["nome"])
        self.entry_nome.bind("<KeyRelease>", self._on_nome_change)
        
        # Sugestões de nomes (placeholder para futuro)
        frame_sugestoes = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_sugestoes.pack(fill="x", pady=10)
        
        tk.Label(
            frame_sugestoes, text="Dica: Nomes curtos e marcantes funcionam melhor em vídeos!", 
            font=("Arial", 9, "italic"), bg=COR_BG_SECUNDARIO, fg=COR_WARNING
        ).pack(anchor="w")
        
        # História/Background (placeholder)
        frame_lore = tk.Frame(self.frame_conteudo_passo, bg=COR_BG)
        frame_lore.pack(fill="x", pady=20)
        
        tk.Label(
            frame_lore, text="ORIGEM (Em breve)", 
            font=("Arial", 10, "bold"), bg=COR_BG, fg=COR_TEXTO_DIM
        ).pack(anchor="w", padx=10, pady=5)
        
        tk.Label(
            frame_lore, text="Futuramente você poderá criar a história do seu personagem aqui...", 
            font=("Arial", 9), bg=COR_BG, fg=COR_TEXTO_DIM, wraplength=380
        ).pack(anchor="w", padx=10, pady=(0, 10))

    def _on_nome_change(self, event=None):
        """Callback quando o nome muda"""
        self.dados_char["nome"] = self.entry_nome.get()
        self.criar_resumo_stats()
        self.atualizar_preview()

    # -------------------------------------------------------------------------
    # PASSO 2: CLASSE
    # -------------------------------------------------------------------------
    def passo_classe(self):
        """Passo 2: Escolha da classe"""
        self.lbl_passo_titulo.config(text="2. CLASSE")
        self.lbl_passo_desc.config(text="Sua classe define seu estilo de combate, habilidades passivas e afinidades mágicas.")
        
        self.var_classe = tk.StringVar(value=self.dados_char["classe"])
        
        # Itera por categorias
        for categoria, classes in CATEGORIAS_CLASSE.items():
            # Header da categoria
            frame_cat = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
            frame_cat.pack(fill="x", pady=(10, 5))
            
            tk.Label(
                frame_cat, text=categoria, 
                font=("Arial", 11, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_WARNING
            ).pack(anchor="w")
            
            # Classes da categoria
            for classe in classes:
                dados = get_class_data(classe)
                cor = CORES_CLASSE.get(classe, COR_TEXTO)
                
                frame = tk.Frame(self.frame_conteudo_passo, bg=COR_BG, bd=1, relief="solid")
                frame.pack(fill="x", pady=2, padx=5)
                
                # Header com nome
                header = tk.Frame(frame, bg=COR_BG)
                header.pack(fill="x", padx=8, pady=3)
                
                rb = tk.Radiobutton(
                    header, text=classe, variable=self.var_classe, value=classe,
                    font=("Arial", 10, "bold"), bg=COR_BG, fg=cor,
                    selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
                    command=lambda c=classe: self._selecionar_classe(c)
                )
                rb.pack(side="left")
                
                # Mods resumidos
                mods = f"For:{dados.get('mod_forca', 1.0):.0%} HP:{dados.get('mod_vida', 1.0):.0%} Vel:{dados.get('mod_velocidade', 1.0):.0%}"
                tk.Label(
                    header, text=mods,
                    font=("Arial", 8), bg=COR_BG, fg=COR_TEXTO_DIM
                ).pack(side="right")
                
                # Passiva
                tk.Label(
                    frame, text=f">> {dados.get('passiva', '')}",
                    font=("Arial", 8), bg=COR_BG, fg=COR_SUCCESS, wraplength=370
                ).pack(anchor="w", padx=8, pady=(0, 3))

    def _selecionar_classe(self, classe):
        """Atualiza a classe selecionada"""
        self.dados_char["classe"] = classe
        self.criar_resumo_stats()
        self.atualizar_preview()
        self.atualizar_info_classe()

    def atualizar_info_classe(self):
        """Atualiza info da classe no preview"""
        dados = get_class_data(self.dados_char["classe"])
        passiva = dados.get("passiva", "")
        self.lbl_classe_passiva.config(text=f">> {passiva}")

    # -------------------------------------------------------------------------
    # PASSO 3: PERSONALIDADE
    # -------------------------------------------------------------------------
    def passo_personalidade(self):
        """Passo 3: Seleção de personalidade da IA"""
        from ai.personalities import PERSONALIDADES_PRESETS, LISTA_PERSONALIDADES
        
        self.lbl_passo_titulo.config(text="3. PERSONALIDADE")
        self.lbl_passo_desc.config(text="Defina como seu campeão luta! A personalidade determina o comportamento da IA em combate.")
        
        # Container para lista de personalidades
        frame_lista = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_lista.pack(fill="both", expand=True, pady=10)
        
        # Grid de personalidades (2 colunas)
        self.var_personalidade = tk.StringVar(value=self.dados_char["personalidade"])
        
        row = 0
        col = 0
        for nome_pers in LISTA_PERSONALIDADES:
            preset = PERSONALIDADES_PRESETS[nome_pers]
            
            # Frame para cada personalidade
            frame_item = tk.Frame(frame_lista, bg=COR_BG, bd=1, relief="ridge")
            frame_item.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Configura cor
            cor = preset["cor"]
            cor_hex = f"#{cor[0]:02x}{cor[1]:02x}{cor[2]:02x}"
            
            # Radiobutton
            rb = tk.Radiobutton(
                frame_item, text=f"{preset['icone']} {nome_pers}",
                variable=self.var_personalidade, value=nome_pers,
                font=("Arial", 10, "bold"), bg=COR_BG, fg=cor_hex,
                selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
                activeforeground=cor_hex, anchor="w", padx=10, pady=5,
                command=self._on_personalidade_change
            )
            rb.pack(fill="x")
            
            # Descrição
            tk.Label(
                frame_item, text=preset["descricao"],
                font=("Arial", 8), bg=COR_BG, fg=COR_TEXTO_DIM,
                wraplength=170, justify="left", padx=10
            ).pack(fill="x", pady=(0, 5))
            
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        # Configura grid weights
        frame_lista.grid_columnconfigure(0, weight=1)
        frame_lista.grid_columnconfigure(1, weight=1)
        
        # Info da personalidade selecionada
        frame_info = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO, bd=1, relief="ridge")
        frame_info.pack(fill="x", pady=10, padx=5)
        
        tk.Label(
            frame_info, text="COMPORTAMENTO EM COMBATE:",
            font=("Arial", 9, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_ACCENT
        ).pack(anchor="w", padx=10, pady=(5, 0))
        
        self.lbl_pers_detalhes = tk.Label(
            frame_info, text="",
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO,
            wraplength=380, justify="left"
        )
        self.lbl_pers_detalhes.pack(anchor="w", padx=10, pady=5)
        
        # Atualiza info inicial
        self._atualizar_info_personalidade()
    
    def _on_personalidade_change(self):
        """Callback quando personalidade muda"""
        self.dados_char["personalidade"] = self.var_personalidade.get()
        self._atualizar_info_personalidade()
        self.atualizar_preview()
    
    def _atualizar_info_personalidade(self):
        """Atualiza info detalhada da personalidade"""
        from ai.personalities import PERSONALIDADES_PRESETS
        
        nome = self.dados_char["personalidade"]
        preset = PERSONALIDADES_PRESETS.get(nome, {})
        
        if nome == "Aleatório":
            detalhes = "A cada luta, uma personalidade diferente será gerada proceduralmente com traços, estilo e comportamentos únicos!"
        else:
            tracos = preset.get("tracos_fixos", [])
            estilo = preset.get("estilo_fixo", "Variado")
            filosofia = preset.get("filosofia_fixa", "Variada")
            
            tracos_txt = ", ".join(tracos[:4]) if tracos else "Variados"
            agressividade = preset.get("agressividade_mod", 0)
            agr_txt = "Muito agressivo" if agressividade > 0.2 else "Agressivo" if agressividade > 0 else "Cauteloso" if agressividade < -0.1 else "Equilibrado"
            
            detalhes = f"Estilo: {estilo} | Filosofia: {filosofia}\nTemperamento: {agr_txt}\nTraços: {tracos_txt}"
        
        if hasattr(self, 'lbl_pers_detalhes'):
            self.lbl_pers_detalhes.config(text=detalhes)

    # -------------------------------------------------------------------------
    # PASSO 4: ATRIBUTOS
    # -------------------------------------------------------------------------
    def passo_atributos(self):
        """Passo 4: Configuração de atributos"""
        self.lbl_passo_titulo.config(text="4. ATRIBUTOS")
        self.lbl_passo_desc.config(text="Distribua os atributos do seu campeão. O físico e poderes mentais definirão seu desempenho.")
        
        # Tamanho/Altura
        frame_tam = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_tam.pack(fill="x", pady=10)
        
        tk.Label(
            frame_tam, text="ALTURA", 
            font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        tk.Label(
            frame_tam, text="Personagens maiores são mais lentos mas têm mais alcance. Menores são ágeis mas frágeis.", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, wraplength=380
        ).pack(anchor="w", pady=(0, 5))
        
        self.var_tamanho = tk.DoubleVar(value=self.dados_char["tamanho"])
        
        frame_slider_tam = tk.Frame(frame_tam, bg=COR_BG_SECUNDARIO)
        frame_slider_tam.pack(fill="x")
        
        tk.Label(frame_slider_tam, text="0.8m", font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(side="left")
        
        self.slider_tamanho = tk.Scale(
            frame_slider_tam, from_=0.8, to=2.5, resolution=0.01,
            orient="horizontal", variable=self.var_tamanho,
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, highlightthickness=0,
            troughcolor=COR_BG, activebackground=COR_ACCENT,
            command=self._on_atributo_change
        )
        self.slider_tamanho.pack(side="left", fill="x", expand=True, padx=5)
        
        tk.Label(frame_slider_tam, text="2.5m", font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(side="left")
        
        self.lbl_tamanho_valor = tk.Label(
            frame_tam, text=f"{self.dados_char['tamanho']:.2f}m", 
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_SUCCESS
        )
        self.lbl_tamanho_valor.pack(pady=5)
        
        # Força
        frame_forca = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_forca.pack(fill="x", pady=10)
        
        tk.Label(
            frame_forca, text="FORÇA (Poder Físico)", 
            font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        tk.Label(
            frame_forca, text="Aumenta dano físico, HP e resistência. Essencial para classes físicas.", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, wraplength=380
        ).pack(anchor="w", pady=(0, 5))
        
        self.var_forca = tk.DoubleVar(value=self.dados_char["forca"])
        
        frame_slider_forca = tk.Frame(frame_forca, bg=COR_BG_SECUNDARIO)
        frame_slider_forca.pack(fill="x")
        
        tk.Label(frame_slider_forca, text="1", font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(side="left")
        
        self.slider_forca = tk.Scale(
            frame_slider_forca, from_=1, to=10, resolution=0.5,
            orient="horizontal", variable=self.var_forca,
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, highlightthickness=0,
            troughcolor=COR_BG, activebackground=COR_ACCENT,
            command=self._on_atributo_change
        )
        self.slider_forca.pack(side="left", fill="x", expand=True, padx=5)
        
        tk.Label(frame_slider_forca, text="10", font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(side="left")
        
        self.lbl_forca_valor = tk.Label(
            frame_forca, text=f"{self.dados_char['forca']:.1f}", 
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg="#ff6b6b"
        )
        self.lbl_forca_valor.pack(pady=5)
        
        # Mana/Magia
        frame_mana = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_mana.pack(fill="x", pady=10)
        
        tk.Label(
            frame_mana, text="MAGIA (Poder Mental)", 
            font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        tk.Label(
            frame_mana, text="Aumenta pool de mana e poder de habilidades. Vital para classes mágicas.", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, wraplength=380
        ).pack(anchor="w", pady=(0, 5))
        
        self.var_mana = tk.DoubleVar(value=self.dados_char["mana"])
        
        frame_slider_mana = tk.Frame(frame_mana, bg=COR_BG_SECUNDARIO)
        frame_slider_mana.pack(fill="x")
        
        tk.Label(frame_slider_mana, text="1", font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(side="left")
        
        self.slider_mana = tk.Scale(
            frame_slider_mana, from_=1, to=10, resolution=0.5,
            orient="horizontal", variable=self.var_mana,
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, highlightthickness=0,
            troughcolor=COR_BG, activebackground=COR_ACCENT,
            command=self._on_atributo_change
        )
        self.slider_mana.pack(side="left", fill="x", expand=True, padx=5)
        
        tk.Label(frame_slider_mana, text="10", font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(side="left")
        
        self.lbl_mana_valor = tk.Label(
            frame_mana, text=f"{self.dados_char['mana']:.1f}", 
            font=("Arial", 12, "bold"), bg=COR_BG_SECUNDARIO, fg="#74b9ff"
        )
        self.lbl_mana_valor.pack(pady=5)
        
        # Presets rápidos
        frame_presets = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_presets.pack(fill="x", pady=15)
        
        tk.Label(
            frame_presets, text="Presets Rápidos:", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
        ).pack(anchor="w", pady=(0, 5))
        
        frame_btns_presets = tk.Frame(frame_presets, bg=COR_BG_SECUNDARIO)
        frame_btns_presets.pack(fill="x")
        
        presets = [
            ("Tanque", 2.0, 8, 2),
            ("Assassino", 1.5, 4, 6),
            ("Mago", 1.6, 2, 9),
            ("Equil.", 1.7, 5, 5),
        ]
        
        for nome, tam, forca, mana in presets:
            tk.Button(
                frame_btns_presets, text=nome, 
                font=("Arial", 8), bg=COR_BG, fg=COR_TEXTO,
                bd=0, padx=10, pady=3,
                command=lambda t=tam, f=forca, m=mana: self._aplicar_preset(t, f, m)
            ).pack(side="left", padx=3)

    def _on_atributo_change(self, event=None):
        """Callback quando um atributo muda"""
        self.dados_char["tamanho"] = self.var_tamanho.get()
        self.dados_char["forca"] = self.var_forca.get()
        self.dados_char["mana"] = self.var_mana.get()
        
        # Atualiza labels
        if hasattr(self, 'lbl_tamanho_valor'):
            self.lbl_tamanho_valor.config(text=f"{self.dados_char['tamanho']:.2f}m")
        if hasattr(self, 'lbl_forca_valor'):
            self.lbl_forca_valor.config(text=f"{self.dados_char['forca']:.1f}")
        if hasattr(self, 'lbl_mana_valor'):
            self.lbl_mana_valor.config(text=f"{self.dados_char['mana']:.1f}")
        
        self.criar_resumo_stats()
        self.atualizar_preview()

    def _aplicar_preset(self, tamanho, forca, mana):
        """Aplica um preset de atributos"""
        self.var_tamanho.set(tamanho)
        self.var_forca.set(forca)
        self.var_mana.set(mana)
        self._on_atributo_change()

    # -------------------------------------------------------------------------
    # PASSO 5: VISUAL
    # -------------------------------------------------------------------------
    def passo_visual(self):
        """Passo 5: Customização visual"""
        self.lbl_passo_titulo.config(text="5. APARÊNCIA")
        self.lbl_passo_desc.config(text="Customize as cores do seu campeão. Uma aparência marcante ajuda na identificação!")
        
        # Cor do corpo (RGB)
        frame_cor = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_cor.pack(fill="x", pady=10)
        
        tk.Label(
            frame_cor, text="COR DO CORPO", 
            font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        # Sliders RGB
        self.var_cor_r = tk.IntVar(value=self.dados_char["cor_r"])
        self.var_cor_g = tk.IntVar(value=self.dados_char["cor_g"])
        self.var_cor_b = tk.IntVar(value=self.dados_char["cor_b"])
        
        for cor_nome, var, cor_label in [
            ("Vermelho", self.var_cor_r, "#ff6b6b"),
            ("Verde", self.var_cor_g, "#51cf66"),
            ("Azul", self.var_cor_b, "#339af0"),
        ]:
            frame_rgb = tk.Frame(frame_cor, bg=COR_BG_SECUNDARIO)
            frame_rgb.pack(fill="x", pady=3)
            
            tk.Label(
                frame_rgb, text=f"{cor_nome[0]}:", 
                font=("Arial", 9, "bold"), bg=COR_BG_SECUNDARIO, fg=cor_label, width=3
            ).pack(side="left")
            
            slider = tk.Scale(
                frame_rgb, from_=0, to=255, orient="horizontal", variable=var,
                bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, highlightthickness=0,
                troughcolor=COR_BG, activebackground=COR_ACCENT,
                command=self._on_cor_change
            )
            slider.pack(side="left", padx=5)
            
            lbl_valor = tk.Label(
                frame_rgb, text=str(var.get()), 
                font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, width=4
            )
            lbl_valor.pack(side="left")
            
            # Guarda referência pro update
            if cor_nome == "Vermelho":
                self.lbl_r_valor = lbl_valor
            elif cor_nome == "Verde":
                self.lbl_g_valor = lbl_valor
            else:
                self.lbl_b_valor = lbl_valor
        
        # Preview da cor
        self.canvas_cor_preview = tk.Canvas(
            frame_cor, width=100, height=50, bg=COR_BG, highlightthickness=1,
            highlightbackground=COR_TEXTO_DIM
        )
        self.canvas_cor_preview.pack(pady=10)
        self._atualizar_preview_cor()
        
        # Presets de cores
        frame_presets = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_presets.pack(fill="x", pady=10)
        
        tk.Label(
            frame_presets, text="Presets de Cor:", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
        ).pack(anchor="w", pady=(0, 5))
        
        frame_cores = tk.Frame(frame_presets, bg=COR_BG_SECUNDARIO)
        frame_cores.pack(fill="x")
        
        cores_preset = [
            ("Sangue", 180, 30, 30),
            ("Gelo", 100, 180, 220),
            ("Sombra", 40, 40, 50),
            ("Ouro", 220, 180, 50),
            ("Esmeralda", 50, 180, 80),
            ("Roxo", 150, 50, 180),
            ("Laranja", 230, 120, 30),
            ("Rosa", 230, 100, 150),
        ]
        
        for nome, r, g, b in cores_preset:
            cor_hex = f"#{r:02x}{g:02x}{b:02x}"
            btn = tk.Button(
                frame_cores, text="  ", bg=cor_hex,
                bd=1, relief="solid", width=3, height=1,
                command=lambda r=r, g=g, b=b: self._aplicar_cor(r, g, b)
            )
            btn.pack(side="left", padx=2, pady=2)

    def _on_cor_change(self, event=None):
        """Callback quando uma cor muda"""
        self.dados_char["cor_r"] = self.var_cor_r.get()
        self.dados_char["cor_g"] = self.var_cor_g.get()
        self.dados_char["cor_b"] = self.var_cor_b.get()
        
        if hasattr(self, 'lbl_r_valor'):
            self.lbl_r_valor.config(text=str(self.dados_char["cor_r"]))
        if hasattr(self, 'lbl_g_valor'):
            self.lbl_g_valor.config(text=str(self.dados_char["cor_g"]))
        if hasattr(self, 'lbl_b_valor'):
            self.lbl_b_valor.config(text=str(self.dados_char["cor_b"]))
        
        self._atualizar_preview_cor()
        self.atualizar_preview()

    def _atualizar_preview_cor(self):
        """Atualiza o mini preview de cor"""
        if hasattr(self, 'canvas_cor_preview'):
            r = self.dados_char["cor_r"]
            g = self.dados_char["cor_g"]
            b = self.dados_char["cor_b"]
            cor_hex = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas_cor_preview.delete("all")
            self.canvas_cor_preview.create_rectangle(5, 5, 95, 45, fill=cor_hex, outline="white")

    def _aplicar_cor(self, r, g, b):
        """Aplica uma cor preset"""
        self.var_cor_r.set(r)
        self.var_cor_g.set(g)
        self.var_cor_b.set(b)
        self._on_cor_change()

    # -------------------------------------------------------------------------
    # PASSO 6: EQUIPAMENTO
    # -------------------------------------------------------------------------
    def passo_equipamento(self):
        """Passo 6: Seleção de equipamento"""
        self.lbl_passo_titulo.config(text="6. EQUIPAMENTO")
        self.lbl_passo_desc.config(text="Escolha a arma que seu campeão levará para batalha. Visite a Forja para criar novas armas!")
        
        # Lista de armas disponíveis
        frame_arma = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_arma.pack(fill="x", pady=10)
        
        tk.Label(
            frame_arma, text="ARMA PRINCIPAL", 
            font=("Arial", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO
        ).pack(anchor="w")
        
        tk.Label(
            frame_arma, text="Selecione uma arma da sua coleção ou lute de mãos vazias!", 
            font=("Arial", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
        ).pack(anchor="w", pady=(0, 10))
        
        # Opção: Sem arma
        self.var_arma = tk.StringVar(value=self.dados_char["arma"] or "Nenhuma")
        
        frame_nenhuma = tk.Frame(frame_arma, bg=COR_BG, bd=1, relief="solid")
        frame_nenhuma.pack(fill="x", pady=2)
        
        rb_nenhuma = tk.Radiobutton(
            frame_nenhuma, text="Mãos Vazias (Monge Style)", 
            variable=self.var_arma, value="Nenhuma",
            font=("Arial", 10), bg=COR_BG, fg=COR_TEXTO,
            selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
            command=lambda: self._selecionar_arma("Nenhuma")
        )
        rb_nenhuma.pack(anchor="w", padx=10, pady=5)
        
        # Lista de armas
        frame_lista_armas = tk.Frame(self.frame_conteudo_passo, bg=COR_BG_SECUNDARIO)
        frame_lista_armas.pack(fill="both", expand=True, pady=10)
        
        # Canvas com scroll para armas - altura aumentada para 300
        self.canvas_armas = tk.Canvas(frame_lista_armas, bg=COR_BG_SECUNDARIO, highlightthickness=0, height=300)
        scrollbar = ttk.Scrollbar(frame_lista_armas, orient="vertical", command=self.canvas_armas.yview)
        frame_armas_inner = tk.Frame(self.canvas_armas, bg=COR_BG_SECUNDARIO)
        
        self.canvas_armas.create_window((0, 0), window=frame_armas_inner, anchor="nw", tags="frame_inner")
        self.canvas_armas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas_armas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configura scrollregion quando o frame interno muda de tamanho
        def _on_frame_configure(event):
            self.canvas_armas.configure(scrollregion=self.canvas_armas.bbox("all"))
            # Também ajusta a largura do frame interno para preencher o canvas
            self.canvas_armas.itemconfig("frame_inner", width=self.canvas_armas.winfo_width())
        
        frame_armas_inner.bind("<Configure>", _on_frame_configure)
        
        # Bind direto no canvas para scroll com mouse
        def _scroll_armas(event):
            self.canvas_armas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas_armas.bind("<MouseWheel>", _scroll_armas)
        frame_armas_inner.bind("<MouseWheel>", _scroll_armas)
        
        # Popula com armas
        armas = self.controller.lista_armas
        if armas:
            for arma in armas:
                cor_arma = f"#{arma.r:02x}{arma.g:02x}{arma.b:02x}"
                raridade = getattr(arma, 'raridade', 'Comum')
                
                frame_a = tk.Frame(frame_armas_inner, bg=COR_BG, bd=1, relief="solid")
                frame_a.pack(fill="x", pady=2, padx=2)
                
                # Bind scroll nos frames de cada arma
                frame_a.bind("<MouseWheel>", _scroll_armas)
                
                header = tk.Frame(frame_a, bg=COR_BG)
                header.pack(fill="x", padx=5, pady=3)
                header.bind("<MouseWheel>", _scroll_armas)
                
                rb = tk.Radiobutton(
                    header, text=arma.nome, 
                    variable=self.var_arma, value=arma.nome,
                    font=("Arial", 10, "bold"), bg=COR_BG, fg=cor_arma,
                    selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
                    command=lambda n=arma.nome: self._selecionar_arma(n)
                )
                rb.bind("<MouseWheel>", _scroll_armas)
                rb.pack(side="left")
                
                # Info da arma
                info = f"{arma.tipo} | Dano: {arma.dano:.0f} | {raridade}"
                lbl_info = tk.Label(
                    header, text=info,
                    font=("Arial", 8), bg=COR_BG, fg=COR_TEXTO_DIM
                )
                lbl_info.bind("<MouseWheel>", _scroll_armas)
                lbl_info.pack(side="right")
        else:
            tk.Label(
                frame_armas_inner, 
                text="Nenhuma arma criada ainda.\nVisite a Forja de Armas para criar!",
                font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_WARNING
            ).pack(pady=20)


    # ── [PHASE 3] PASSO 7: ALIANÇA DIVINA ──────────────────────────────────────

    def passo_divindade(self):
        """
        Passo 7 — ALIANÇA DIVINA
        O campeão jura lealdade a um Deus do World Map.
        Se o World Map não estiver ativo, exibe mensagem de instrução.
        """
        self.lbl_passo_titulo.config(text="7. ⚡ ALIANÇA DIVINA")
        self.lbl_passo_desc.config(
            text="Cada campeão pode servir a um Deus. Isso o vincula ao World Map, "
                 "reivindicando territórios e lutando na Guerra dos Deuses!"
        )

        # Tenta carregar o WorldStateSync
        sync = database.get_worldmap_sync() if database.is_worldmap_active() else None

        frame = self.frame_conteudo_passo

        # ── Painel: World Map não ativo ────────────────────────────────────────
        if sync is None:
            self._passo_div_offline(frame)
            return

        # ── Painel: World Map ativo ────────────────────────────────────────────
        self._passo_div_online(frame, sync)

    def _passo_div_offline(self, frame):
        """Exibe instruções quando o World Map module não está instalado."""
        container = tk.Frame(frame, bg=COR_BG_SECUNDARIO, bd=1, relief="solid")
        container.pack(fill="x", pady=10, padx=5)

        tk.Label(container, text="⚠  WORLD MAP NÃO ATIVO",
                 font=("Arial", 13, "bold"), bg=COR_BG_SECUNDARIO,
                 fg=COR_WARNING).pack(pady=(15, 5))

        instrucoes = (
            "O modulo World Map nao foi detectado.\n\n"
            "Para ativar:\n"
            "  1. A pasta world_map_module/ deve estar ao lado\n"
            "     desta pasta (neural_v3_rework/).\n"
            "  2. Reinicie o Neural Fights Launcher.\n\n"
            "Este campeao sera salvo como MORTAL LIVRE\n"
            "sem vinculo com nenhum Deus."
        )

        tk.Label(container, text=instrucoes,
                 font=("Consolas", 10), bg=COR_BG_SECUNDARIO,
                 fg=COR_TEXTO_DIM, justify="left").pack(padx=20, pady=(0, 15))

        # Garante que god_id seja None
        self.dados_char["god_id"] = None

    def _passo_div_online(self, frame, sync):
        """Exibe o painel completo de seleção de deus quando o World Map está ativo."""
        gods = sync.get_all_gods()

        # ── Status atual ───────────────────────────────────────────────────────
        god_atual = sync.get_god(self.dados_char.get("god_id")) if self.dados_char.get("god_id") else None

        status_frame = tk.Frame(frame, bg=COR_HEADER, bd=1, relief="solid")
        status_frame.pack(fill="x", pady=(5, 10), padx=5)

        if god_atual:
            cp = god_atual.color_primary
            status_text = f"⚡  Vinculado a: {god_atual.god_name}  [{god_atual.nature}]"
            status_color = cp
        else:
            status_text = "🔓  Mortal Livre — sem vínculo divino"
            status_color = COR_TEXTO_DIM

        tk.Label(status_frame, text=status_text,
                 font=("Consolas", 11, "bold"), bg=COR_HEADER,
                 fg=status_color).pack(pady=8, padx=12)

        # ── Opção: Mortal Livre ───────────────────────────────────────────────
        self.var_god = tk.StringVar(value=self.dados_char.get("god_id") or "__NONE__")

        frame_nenhum = tk.Frame(frame, bg=COR_BG, bd=1, relief="solid")
        frame_nenhum.pack(fill="x", pady=2, padx=5)

        rb_nenhum = tk.Radiobutton(
            frame_nenhum, text="🔓  Mortal Livre  (sem deus)",
            variable=self.var_god, value="__NONE__",
            font=("Arial", 10), bg=COR_BG, fg=COR_TEXTO_DIM,
            selectcolor=COR_BG_SECUNDARIO, activebackground=COR_BG,
            command=lambda: self._selecionar_deus(None)
        )
        rb_nenhum.pack(anchor="w", padx=12, pady=6)

        # ── Lista de Deuses ───────────────────────────────────────────────────
        if gods:
            tk.Label(frame, text="DEUSES DISPONÍVEIS",
                     font=("Arial", 9, "bold"), bg=COR_BG_SECUNDARIO,
                     fg=COR_TEXTO_DIM).pack(anchor="w", padx=8, pady=(8, 2))

            for god in sorted(gods, key=lambda g: -g.follower_count):
                self._criar_card_deus(frame, god)
        else:
            tk.Label(
                frame,
                text="Nenhum Deus registrado ainda.\n"
                     "Use o World Map ([G]) para criar deuses\n"
                     "ou adicione-os no gods.json.",
                font=("Arial", 10), bg=COR_BG_SECUNDARIO,
                fg=COR_WARNING, justify="center"
            ).pack(pady=20)

        # ── Criar Novo Deus ───────────────────────────────────────────────────
        sep = tk.Frame(frame, bg=COR_HEADER, height=1)
        sep.pack(fill="x", pady=10, padx=5)

        btn_novo = tk.Button(
            frame, text="⚡  REGISTRAR NOVO DEUS",
            font=("Arial", 10, "bold"), bg=COR_ACCENT, fg=COR_TEXTO,
            bd=0, padx=15, pady=8,
            command=lambda: self._abrir_wizard_novo_deus(frame, sync)
        )
        btn_novo.pack(pady=5)

        tk.Label(
            frame,
            text="Ou abra o World Map e pressione [G] para uma interface completa.",
            font=("Arial", 8), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM
        ).pack()

    def _criar_card_deus(self, parent, god):
        """Cria um card de seleção de deus."""
        from data import database

        is_selected = (self.dados_char.get("god_id") == god.god_id)

        # Tenta resolver a cor hex
        try:
            cp_hex = god.color_primary
            # Converte para rgb para verificação
            r = int(cp_hex.lstrip("#")[0:2], 16)
            g = int(cp_hex.lstrip("#")[2:4], 16)
            b = int(cp_hex.lstrip("#")[4:6], 16)
            card_bg = f"#{r//4 + 20:02x}{g//4 + 20:02x}{b//4 + 20:02x}"
        except Exception:
            cp_hex = "#8892b0"
            card_bg = COR_BG

        card = tk.Frame(parent,
                        bg=card_bg if is_selected else COR_BG,
                        bd=2 if is_selected else 1,
                        relief="solid")
        card.pack(fill="x", pady=3, padx=5)

        # Faixa de cor lateral do deus
        faixa = tk.Frame(card, bg=cp_hex, width=5)
        faixa.pack(side="left", fill="y")

        body = tk.Frame(card, bg=card_bg if is_selected else COR_BG)
        body.pack(side="left", fill="both", expand=True, padx=8, pady=6)

        # Linha superior: radio + nome + natureza
        top = tk.Frame(body, bg=body["bg"])
        top.pack(fill="x")

        rb = tk.Radiobutton(
            top, text=f"⚡  {god.god_name}",
            variable=self.var_god, value=god.god_id,
            font=("Arial", 11, "bold"), bg=body["bg"], fg=cp_hex,
            selectcolor=COR_BG_SECUNDARIO, activebackground=body["bg"],
            command=lambda gid=god.god_id: self._selecionar_deus(gid)
        )
        rb.pack(side="left")

        tk.Label(top, text=f"[{god.nature}]",
                 font=("Consolas", 9), bg=body["bg"],
                 fg=cp_hex).pack(side="left", padx=4)

        # Linha inferior: stats
        n_zonas = len(god.owned_zones)
        stats_text = (
            f"  Seguidores: {god.follower_count:,}   |   "
            f"Zonas: {n_zonas}   |   "
            f"Fonte: {god.source}"
        )
        tk.Label(body, text=stats_text,
                 font=("Consolas", 8), bg=body["bg"],
                 fg=COR_TEXTO_DIM).pack(anchor="w")

        # Lore (se existir)
        if god.lore_description:
            lore_short = god.lore_description[:80] + ("..." if len(god.lore_description) > 80 else "")
            tk.Label(body, text=f'  "{lore_short}"',
                     font=("Arial", 8, "italic"), bg=body["bg"],
                     fg=COR_TEXTO_DIM, wraplength=360, justify="left").pack(anchor="w")

    def _selecionar_deus(self, god_id):
        """Callback: atualiza o god_id nos dados do personagem."""
        self.dados_char["god_id"] = god_id
        # Atualiza o preview
        self.atualizar_preview()

    def _abrir_wizard_novo_deus(self, parent_frame, sync):
        """Abre um sub-painel inline para criar um novo deus rapidamente."""
        # Limpa o frame de conteúdo e reconstrói com o mini-wizard de deus
        for w in self.frame_conteudo_passo.winfo_children():
            w.destroy()

        frame = self.frame_conteudo_passo

        tk.Label(frame, text="⚡ NOVO DEUS",
                 font=("Arial", 13, "bold"), bg=COR_BG_SECUNDARIO,
                 fg=COR_SUCCESS).pack(pady=(10, 2))

        tk.Label(frame, text="Registre um novo Deus agora. Após salvar, ele aparecerá no World Map.",
                 font=("Arial", 9), bg=COR_BG_SECUNDARIO,
                 fg=COR_TEXTO_DIM, wraplength=380).pack(pady=(0, 10))

        # Campo nome
        tk.Label(frame, text="NOME DO DEUS", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=10)
        entry_nome = tk.Entry(frame, font=("Consolas", 11),
                              bg=COR_BG, fg=COR_TEXTO, insertbackground=COR_TEXTO,
                              relief="flat", bd=5)
        entry_nome.pack(fill="x", padx=10, pady=3)

        # Natureza
        tk.Label(frame, text="NATUREZA", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=10, pady=(8, 0))

        NATURE_OPTIONS = [
            "balanced", "fire", "ice", "darkness", "nature",
            "chaos", "void", "greed", "fear", "arcane", "blood", "time", "gravity"
        ]
        var_nature = tk.StringVar(value="balanced")
        combo_nature = ttk.Combobox(frame, textvariable=var_nature,
                                    values=NATURE_OPTIONS,
                                    font=("Consolas", 10), state="readonly")
        combo_nature.pack(fill="x", padx=10, pady=3)

        # Seguidores
        tk.Label(frame, text="SEGUIDORES INICIAIS", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=10, pady=(8, 0))
        entry_seg = tk.Entry(frame, font=("Consolas", 11),
                             bg=COR_BG, fg=COR_TEXTO, insertbackground=COR_TEXTO,
                             relief="flat", bd=5)
        entry_seg.insert(0, "0")
        entry_seg.pack(fill="x", padx=10, pady=3)

        # Lore
        tk.Label(frame, text="LORE / DESCRIÇÃO (opcional)", font=("Arial", 9, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=10, pady=(8, 0))
        entry_lore = tk.Entry(frame, font=("Consolas", 10),
                              bg=COR_BG, fg=COR_TEXTO, insertbackground=COR_TEXTO,
                              relief="flat", bd=5)
        entry_lore.pack(fill="x", padx=10, pady=3)

        msg_var = tk.StringVar()
        msg_label = tk.Label(frame, textvariable=msg_var, font=("Arial", 9),
                             bg=COR_BG_SECUNDARIO, fg=COR_SUCCESS)
        msg_label.pack(pady=4)

        def _criar_deus():
            nome = entry_nome.get().strip()
            if not nome:
                msg_var.set("❌ Digite um nome para o deus.")
                msg_label.config(fg=COR_DANGER)
                return
            nature_el = var_nature.get()
            try:
                followers = int(entry_seg.get() or "0")
            except ValueError:
                followers = 0
            lore = entry_lore.get().strip()

            # Capitaliza a natureza para exibição
            nature_display = nature_el.capitalize()

            god = sync.create_god(
                god_name=nome,
                nature=nature_display,
                nature_element=nature_el,
                source="manual",
            )
            god.follower_count = followers
            if lore:
                god.lore_description = lore
            sync.save_all()

            # Seleciona este deus automaticamente
            self._selecionar_deus(god.god_id)

            msg_var.set(f"✔  {god.god_name} — Deus de {god.nature} registrado!")
            msg_label.config(fg=COR_SUCCESS)

            # Volta para o passo 7 com o novo deus listado
            frame.after(1200, lambda: self.mostrar_passo(7))

        btn_criar = tk.Button(
            frame, text="⚡ REGISTRAR DEUS",
            font=("Arial", 10, "bold"), bg=COR_SUCCESS, fg="#000000",
            bd=0, padx=20, pady=8, command=_criar_deus
        )
        btn_criar.pack(pady=10)

        btn_cancel = tk.Button(
            frame, text="Cancelar",
            font=("Arial", 9), bg=COR_BG, fg=COR_TEXTO_DIM,
            bd=0, padx=10, pady=4,
            command=lambda: self.mostrar_passo(7)
        )
        btn_cancel.pack()

    # ── FIM PHASE 3 ─────────────────────────────────────────────────────────

    def _selecionar_arma(self, nome):
        """Seleciona uma arma"""
        if nome == "Nenhuma":
            self.dados_char["arma"] = ""
        else:
            self.dados_char["arma"] = nome
        self.criar_resumo_stats()
        self.atualizar_preview()

    # =========================================================================
    # PREVIEW E RENDERIZAÇÃO
    # =========================================================================
    
    def atualizar_preview(self):
        """Atualiza o preview do personagem"""
        self.canvas_preview.delete("all")
        
        cx, cy = 150, 150
        
        # Cor do personagem
        r = max(0, min(255, self.dados_char["cor_r"]))
        g = max(0, min(255, self.dados_char["cor_g"]))
        b = max(0, min(255, self.dados_char["cor_b"]))
        cor_char = f"#{r:02x}{g:02x}{b:02x}"
        
        # Tamanho baseado na altura (escala visual)
        tamanho = self.dados_char["tamanho"]
        raio = min(40 + (tamanho - 1.0) * 30, 80)  # Entre 40 e 80 pixels
        
        # Aura da classe
        classe_data = get_class_data(self.dados_char["classe"])
        cor_aura = classe_data.get("cor_aura", (200, 200, 200))
        cor_aura_hex = f"#{cor_aura[0]:02x}{cor_aura[1]:02x}{cor_aura[2]:02x}"
        
        # Desenha aura (círculo maior, semi-transparente via stipple)
        self.canvas_preview.create_oval(
            cx - raio - 15, cy - raio - 15, 
            cx + raio + 15, cy + raio + 15,
            outline=cor_aura_hex, width=3, dash=(3, 3)
        )
        
        # Desenha corpo
        self.canvas_preview.create_oval(
            cx - raio, cy - raio, 
            cx + raio, cy + raio,
            fill=cor_char, outline="white", width=2
        )
        
        # Desenha olhos (indicando direção)
        olho_offset = raio * 0.3
        olho_raio = raio * 0.15
        self.canvas_preview.create_oval(
            cx + olho_offset - olho_raio, cy - olho_offset - olho_raio,
            cx + olho_offset + olho_raio, cy - olho_offset + olho_raio,
            fill="white", outline=""
        )
        self.canvas_preview.create_oval(
            cx + olho_offset - olho_raio, cy + olho_offset - olho_raio,
            cx + olho_offset + olho_raio, cy + olho_offset + olho_raio,
            fill="white", outline=""
        )
        
        # Desenha arma se houver
        nome_arma = self.dados_char["arma"]
        if nome_arma:
            arma_obj = next((a for a in self.controller.lista_armas if a.nome == nome_arma), None)
            if arma_obj:
                cor_arma = f"#{arma_obj.r:02x}{arma_obj.g:02x}{arma_obj.b:02x}"
                
                if "Reta" in arma_obj.tipo or "Dupla" in arma_obj.tipo:
                    # Espada/lança
                    comp = min(arma_obj.comp_lamina / 2, 40)
                    self.canvas_preview.create_line(
                        cx + raio, cy, 
                        cx + raio + comp, cy - 10,
                        fill=cor_arma, width=4
                    )
                elif "Arco" in arma_obj.tipo:
                    # Arco
                    self.canvas_preview.create_arc(
                        cx + raio - 10, cy - 25, 
                        cx + raio + 20, cy + 25,
                        start=60, extent=240, style="arc",
                        outline=cor_arma, width=3
                    )
                elif "Orbital" in arma_obj.tipo:
                    # Escudo/orbital
                    self.canvas_preview.create_arc(
                        cx - raio - 20, cy - raio - 20,
                        cx + raio + 20, cy + raio + 20,
                        start=-30, extent=60, style="arc",
                        outline=cor_arma, width=5
                    )
                elif "Mágica" in arma_obj.tipo:
                    # Orbes mágicos
                    for i in range(3):
                        ang = math.radians(120 * i - 30)
                        ox = cx + math.cos(ang) * (raio + 15)
                        oy = cy + math.sin(ang) * (raio + 15)
                        self.canvas_preview.create_oval(
                            ox - 6, oy - 6, ox + 6, oy + 6,
                            fill=cor_arma, outline="white"
                        )
                else:
                    # Genérico
                    self.canvas_preview.create_line(
                        cx + raio, cy, 
                        cx + raio + 30, cy,
                        fill=cor_arma, width=3
                    )
        
        # Nome do personagem
        nome = self.dados_char["nome"] or "???"
        self.canvas_preview.create_text(
            cx, cy + raio + 30,
            text=nome, font=("Impact", 14), fill="white"
        )
        
        # Classe
        classe_nome = self.dados_char["classe"].split(" (")[0]
        self.canvas_preview.create_text(
            cx, cy + raio + 50,
            text=classe_nome, font=("Arial", 10), fill=cor_aura_hex
        )

    # =========================================================================
    # CRUD DE PERSONAGENS
    # =========================================================================
    
    def atualizar_dados(self):
        """Atualiza dados da lista de personagens"""
        # Atualiza tree
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        for p in self.controller.lista_personagens:
            classe = getattr(p, "classe", "Guerreiro (Força Bruta)")
            classe_curta = classe.split(" (")[0]
            self.tree.insert("", "end", values=(
                p.nome, classe_curta, p.nome_arma or "Nenhuma"
            ))
        
        # Atualiza preview se estiver no passo de equipamento
        if self.passo_atual == 5:
            self.mostrar_passo(5)

    def salvar_personagem(self):
        """Salva o personagem atual"""
        try:
            nome = self.dados_char["nome"].strip()
            if not nome:
                messagebox.showerror("Erro", "Digite um nome para o personagem!")
                return
            
            # Verifica duplicatas
            for i, p in enumerate(self.controller.lista_personagens):
                if p.nome.lower() == nome.lower():
                    if self.indice_em_edicao is None or self.indice_em_edicao != i:
                        messagebox.showerror("Erro", f"Já existe um personagem chamado '{nome}'!")
                        return
            
            # Busca arma
            nome_arma = self.dados_char["arma"]
            arma_obj = next((a for a in self.controller.lista_armas if a.nome == nome_arma), None)
            peso_arma = arma_obj.peso if arma_obj else 0
            
            # Cria personagem
            p = Personagem(
                nome,
                self.dados_char["tamanho"],
                self.dados_char["forca"],
                self.dados_char["mana"],
                nome_arma,
                peso_arma,
                self.dados_char["cor_r"],
                self.dados_char["cor_g"],
                self.dados_char["cor_b"],
                self.dados_char["classe"],
                self.dados_char["personalidade"],
                self.dados_char.get("god_id"),  # [PHASE 3]
            )
            
            _state = AppState.get()
            if self.indice_em_edicao is None:
                _state.add_character(p)
                msg = f"Campeão '{nome}' criado com sucesso!"
            else:
                _state.update_character(self.indice_em_edicao, p)
                msg = f"Campeão '{nome}' atualizado!"
            self.atualizar_dados()
            self.novo_personagem()
            messagebox.showinfo("Sucesso", msg)
            
        except ValueError as e:
            messagebox.showerror("Erro", f"Valores inválidos: {e}")

    def deletar_personagem(self):
        """Deleta o personagem selecionado"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um personagem para deletar!")
            return
        
        idx = self.tree.index(sel[0])
        nome = self.controller.lista_personagens[idx].nome
        
        if messagebox.askyesno("Confirmar", f"Deletar o campeão '{nome}'?\n\nEsta ação não pode ser desfeita!"):
            AppState.get().delete_character(idx)
            self.atualizar_dados()
            self.novo_personagem()

    def selecionar_personagem(self, event=None):
        """Callback quando um personagem é selecionado na lista"""
        sel = self.tree.selection()
        if not sel:
            return
        
        idx = self.tree.index(sel[0])
        p = self.controller.lista_personagens[idx]
        
        # Carrega dados
        self.indice_em_edicao = idx
        self.dados_char = {
            "nome": p.nome,
            "classe": getattr(p, "classe", "Guerreiro (Força Bruta)"),
            "personalidade": getattr(p, "personalidade", "Aleatório"),
            "tamanho": p.tamanho,
            "forca": p.forca,
            "mana": p.mana,
            "arma": p.nome_arma or "",
            "cor_r": p.cor_r,
            "cor_g": p.cor_g,
            "cor_b": p.cor_b,
            "god_id": getattr(p, "god_id", None),  # [PHASE 3]
        }
        
        # Atualiza UI
        self.btn_proximo.config(text="⚡ SALVAR CAMPEÃO", bg=COR_WARNING)
        self.mostrar_passo(self.passo_atual)

    def editar_personagem(self):
        """Inicia edição do personagem selecionado"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um personagem para editar!")
            return
        
        self.selecionar_personagem()
        self.mostrar_passo(1)

    def novo_personagem(self):
        """Reseta para criar novo personagem"""
        self.indice_em_edicao = None
        self.dados_char = {
            "nome": "",
            "classe": "Guerreiro (Força Bruta)",
            "personalidade": "Aleatório",
            "tamanho": 1.70,
            "forca": 5.0,
            "mana": 5.0,
            "arma": "",
            "cor_r": 200,
            "cor_g": 50,
            "cor_b": 50,
            "god_id": None,  # [PHASE 3] Vínculo divino
        }
        
        # Limpa seleção
        self.tree.selection_remove(self.tree.selection())
        
        # Reseta wizard
        self.mostrar_passo(1)
