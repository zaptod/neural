import tkinter as tk
from tkinter import ttk, messagebox
from models import Arma
import database
from skills import SKILL_DB # Importa a lista de magias

class TelaArmas(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#2C3E50")
        self.indice_em_edicao = None
        self.setup_ui()

    def setup_ui(self):
        header = tk.Frame(self, bg="#34495E", height=50)
        header.pack(fill="x", side="top")
        
        btn_voltar = tk.Button(header, text="< VOLTAR", bg="#E67E22", fg="white", font=("Arial", 10, "bold"),
                               command=lambda: self.controller.show_frame("MenuPrincipal"))
        btn_voltar.pack(side="left", padx=10, pady=10)

        tk.Label(header, text="FORJA DE ARMAS", font=("Helvetica", 18, "bold"), bg="#34495E", fg="white").pack(side="left", padx=20)

        main_container = tk.Frame(self, bg="#2C3E50")
        main_container.pack(fill="both", expand=True, padx=20, pady=10)

        # === LADO ESQUERDO ===
        left_frame = tk.Frame(main_container, bg="#2C3E50")
        left_frame.pack(side="left", fill="y", padx=(0, 20))

        # 1. Definições
        self.criar_titulo(left_frame, "Definições da Arma")
        f_def = tk.Frame(left_frame, bg="#2C3E50")
        f_def.pack(fill="x")
        
        self.ent_nome = self.criar_entry(f_def, "Nome:", 0)
        
        tk.Label(f_def, text="Tipo Físico:", bg="#2C3E50", fg="white").grid(row=1, column=0, sticky="e")
        self.combo_tipo = ttk.Combobox(f_def, values=["Reta", "Orbital"], state="readonly", width=18)
        self.combo_tipo.grid(row=1, column=1, pady=2)
        self.combo_tipo.current(0)
        self.combo_tipo.bind("<<ComboboxSelected>>", self.ao_mudar_tipo)

        tk.Label(f_def, text="Estilo:", bg="#2C3E50", fg="#F39C12").grid(row=2, column=0, sticky="e")
        self.combo_estilo = ttk.Combobox(f_def, state="readonly", width=18)
        self.combo_estilo.grid(row=2, column=1, pady=2)

        self.ent_dano = self.criar_entry(f_def, "Dano Base:", 3)
        self.ent_peso = self.criar_entry(f_def, "Peso (kg):", 4)

        # 2. ENCANTAMENTO (AQUI ESTAVA FALTANDO!)
        self.criar_titulo(left_frame, "Encantamento (Mana)")
        f_mag = tk.Frame(left_frame, bg="#2C3E50")
        f_mag.pack(fill="x")
        
        tk.Label(f_mag, text="Habilidade:", bg="#2C3E50", fg="#3498DB", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="e")
        # Carrega a lista do skills.py
        lista_skills = list(SKILL_DB.keys())
        self.combo_skill = ttk.Combobox(f_mag, values=lista_skills, state="readonly", width=18)
        self.combo_skill.grid(row=0, column=1, pady=2)
        self.combo_skill.current(0)
        self.combo_skill.bind("<<ComboboxSelected>>", self.atualizar_custo_auto)
        
        self.ent_custo = self.criar_entry(f_mag, "Custo Mana:", 1)

        # 3. Cores
        self.criar_titulo(left_frame, "Material (Cor RGB)")
        f_cor = tk.Frame(left_frame, bg="#2C3E50")
        f_cor.pack(fill="x")
        self.er = self.criar_scale(f_cor, "R", 200)
        self.eg = self.criar_scale(f_cor, "G", 200)
        self.eb = self.criar_scale(f_cor, "B", 200)

        # 4. Geometria
        self.criar_titulo(left_frame, "Geometria & Hitbox")
        self.frame_geo = tk.Frame(left_frame, bg="#2C3E50")
        self.frame_geo.pack(fill="x")

        self.sld_cabo = self.criar_scale_geo("Comp. Cabo")
        self.sld_lamina = self.criar_scale_geo("Comp. Lâmina")
        self.sld_largura = self.criar_scale_geo("Espessura/Tamanho")
        self.sld_distancia = self.criar_scale_geo("Distância Órbita", 20, 100)
        
        self.var_cabo_dano = tk.BooleanVar()
        self.chk_cabo = tk.Checkbutton(self.frame_geo, text="Cabo Causa Dano?", variable=self.var_cabo_dano, 
                                       bg="#2C3E50", fg="#E74C3C", selectcolor="#2C3E50", command=self.preview)

        # Botões
        f_btn = tk.Frame(left_frame, bg="#2C3E50")
        f_btn.pack(pady=20, fill="x")
        self.btn_salvar = tk.Button(f_btn, text="FORJAR ARMA", bg="#27AE60", fg="white", font=("Arial", 10, "bold"), height=2, command=self.salvar)
        self.btn_salvar.pack(fill="x")
        tk.Button(f_btn, text="Limpar / Novo", command=self.limpar).pack(fill="x", pady=5)

        # === LADO DIREITO ===
        right_frame = tk.Frame(main_container, bg="#2C3E50")
        right_frame.pack(side="right", fill="both", expand=True)

        tk.Label(right_frame, text="Preview Visual", bg="#2C3E50", fg="#BDC3C7").pack()
        self.cv = tk.Canvas(right_frame, bg="#34495E", highlightthickness=2, highlightbackground="#7F8C8D")
        self.cv.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("Nome", "Tipo", "Habilidade", "Mana")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=8)
        self.tree.heading("Nome", text="Nome"); self.tree.column("Nome", width=100)
        self.tree.heading("Tipo", text="Tipo"); self.tree.column("Tipo", width=60)
        self.tree.heading("Habilidade", text="Skill"); self.tree.column("Habilidade", width=100)
        self.tree.heading("Mana", text="Mana"); self.tree.column("Mana", width=40)
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.selecionar)

        self.ao_mudar_tipo()

    def criar_titulo(self, parent, texto):
        tk.Label(parent, text=texto, font=("Arial", 10, "bold"), bg="#2C3E50", fg="#BDC3C7").pack(anchor="w", pady=(10,2))

    def criar_entry(self, parent, txt, row):
        tk.Label(parent, text=txt, bg="#2C3E50", fg="white").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        e = tk.Entry(parent, width=18)
        e.grid(row=row, column=1, pady=2)
        return e

    def criar_scale(self, parent, txt, vpadrao):
        f = tk.Frame(parent, bg="#2C3E50")
        f.pack(side="left", padx=2)
        tk.Label(f, text=txt, bg="#2C3E50", fg="white", font=("Arial", 8)).pack()
        s = tk.Scale(f, from_=0, to=255, orient="vertical", bg="#2C3E50", fg="white", length=80, command=self.preview)
        s.set(vpadrao)
        s.pack()
        return s

    def criar_scale_geo(self, txt, vmin=1, vmax=120):
        f = tk.Frame(self.frame_geo, bg="#2C3E50")
        tk.Label(f, text=txt, bg="#2C3E50", fg="white", font=("Arial", 9)).pack(anchor="w")
        s = tk.Scale(f, from_=vmin, to=vmax, orient="horizontal", bg="#34495E", fg="white", length=220, command=self.preview)
        s.set(10)
        s.pack(fill="x")
        return f 

    def ao_mudar_tipo(self, event=None):
        tipo = self.combo_tipo.get()
        self.sld_cabo.pack_forget(); self.sld_lamina.pack_forget(); self.sld_largura.pack_forget()
        self.sld_distancia.pack_forget(); self.chk_cabo.pack_forget()

        if "Reta" in tipo:
            self.combo_estilo['values'] = ["Corte (Espada)", "Estocada (Lança)", "Contusão (Maça)", "Misto"]
            self.combo_estilo.current(0)
            self.sld_cabo.pack(fill="x"); self.chk_cabo.pack(anchor="w", padx=10)
            self.sld_lamina.pack(fill="x"); self.sld_largura.pack(fill="x")
            self.sld_largura.children['!label'].config(text="Espessura da Lâmina")
        else:
            self.combo_estilo['values'] = ["Defensivo (Escudo)", "Ofensivo (Drone)", "Mágico (Orbe)"]
            self.combo_estilo.current(0)
            self.sld_distancia.pack(fill="x"); self.sld_largura.pack(fill="x")
            self.sld_largura.children['!label'].config(text="Tamanho do Escudo/Arco")
        
        self.preview()

    def atualizar_custo_auto(self, event=None):
        # Preenche o custo de mana automaticamente ao escolher a skill
        skill = self.combo_skill.get()
        if skill in SKILL_DB:
            custo = SKILL_DB[skill].get("custo", 0)
            self.ent_custo.delete(0, 'end')
            self.ent_custo.insert(0, str(custo))

    def preview(self, event=None):
        self.cv.delete("all")
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        cx, cy = w/2, h/2
        if w < 10: return

        self.cv.create_oval(cx-20, cy-20, cx+20, cy+20, outline="#555", dash=(4,4))
        r, g, b = self.er.get(), self.eg.get(), self.eb.get()
        cor_hex = f"#{r:02x}{g:02x}{b:02x}"
        tipo = self.combo_tipo.get()

        if "Reta" in tipo:
            cabo = self.sld_cabo.winfo_children()[1].get()
            lamina = self.sld_lamina.winfo_children()[1].get()
            largura = self.sld_largura.winfo_children()[1].get()
            cabo_dano = self.var_cabo_dano.get()
            fim_cabo_x = cx + cabo
            cor_borda_cabo = "#E74C3C" if cabo_dano else "" 
            largura_borda_cabo = 2 if cabo_dano else 0
            
            self.cv.create_rectangle(cx, cy-(largura/2 * 0.5), fim_cabo_x, cy+(largura/2 * 0.5), 
                                     fill="#8B4513", outline=cor_borda_cabo, width=largura_borda_cabo)
            fim_lamina_x = fim_cabo_x + lamina
            self.cv.create_rectangle(fim_cabo_x, cy-(largura/2), fim_lamina_x, cy+(largura/2), 
                                     fill=cor_hex, outline="#E74C3C", width=2)
        else:
            dist = self.sld_distancia.winfo_children()[1].get()
            tamanho = self.sld_largura.winfo_children()[1].get()
            raio = 20 + dist
            self.cv.create_arc(cx-raio, cy-raio, cx+raio, cy+raio, start=-tamanho/2, extent=tamanho, 
                               style="arc", outline=cor_hex, width=6)
            self.cv.create_arc(cx-raio, cy-raio, cx+raio, cy+raio, start=-tamanho/2, extent=tamanho, 
                               style="arc", outline="#E74C3C", width=1, dash=(2,2))

    def salvar(self):
        try:
            nome = self.ent_nome.get()
            if not nome: return
            
            nova = Arma(
                nome=nome,
                tipo=self.combo_tipo.get(),
                dano=self.ent_dano.get() or 0,
                peso=self.ent_peso.get() or 0,
                comp_cabo=self.sld_cabo.winfo_children()[1].get(), 
                comp_lamina=self.sld_lamina.winfo_children()[1].get(), 
                largura=self.sld_largura.winfo_children()[1].get(), 
                distancia=self.sld_distancia.winfo_children()[1].get(),
                r=self.er.get(), g=self.eg.get(), b=self.eb.get(),
                estilo=self.combo_estilo.get(),
                cabo_dano=self.var_cabo_dano.get(),
                habilidade=self.combo_skill.get(),
                custo_mana=self.ent_custo.get() or 0
            )
            
            if self.indice_em_edicao is None:
                self.controller.lista_armas.append(nova)
            else:
                self.controller.lista_armas[self.indice_em_edicao] = nova
            
            database.salvar_lista_armas(self.controller.lista_armas)
            self.atualizar_dados()
            self.limpar()
            messagebox.showinfo("Sucesso", "Arma Encantada!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def atualizar_dados(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for a in self.controller.lista_armas:
            hab = getattr(a, 'habilidade', 'Nenhuma')
            mana = getattr(a, 'custo_mana', 0)
            self.tree.insert("", "end", values=(a.nome, a.tipo, hab, int(mana)))

    def selecionar(self, e):
        sel = self.tree.selection()
        if not sel: return
        self.indice_em_edicao = self.tree.index(sel[0])
        a = self.controller.lista_armas[self.indice_em_edicao]

        self.ent_nome.delete(0,'end'); self.ent_nome.insert(0, a.nome)
        self.ent_dano.delete(0,'end'); self.ent_dano.insert(0, str(a.dano))
        self.ent_peso.delete(0,'end'); self.ent_peso.insert(0, str(a.peso))
        
        self.combo_skill.set(getattr(a, 'habilidade', 'Nenhuma'))
        self.ent_custo.delete(0, 'end'); self.ent_custo.insert(0, str(getattr(a, 'custo_mana', 0)))

        self.combo_tipo.set(a.tipo)
        self.ao_mudar_tipo()
        
        estilo = getattr(a, 'estilo', '')
        if estilo in self.combo_estilo['values']: self.combo_estilo.set(estilo)
        
        self.sld_cabo.winfo_children()[1].set(a.comp_cabo)
        self.sld_lamina.winfo_children()[1].set(a.comp_lamina)
        self.sld_largura.winfo_children()[1].set(a.largura)
        self.sld_distancia.winfo_children()[1].set(a.distancia)
        self.var_cabo_dano.set(getattr(a, 'cabo_dano', False))
        
        self.er.set(a.r); self.eg.set(a.g); self.eb.set(a.b)
        self.btn_salvar.config(text="Re-forjar (Salvar)", bg="orange")
        self.preview()

    def limpar(self):
        self.indice_em_edicao = None
        self.ent_nome.delete(0,'end')
        self.ent_dano.delete(0,'end')
        self.ent_peso.delete(0,'end')
        self.ent_custo.delete(0, 'end')
        self.combo_skill.current(0)
        self.var_cabo_dano.set(False)
        self.btn_salvar.config(text="FORJAR ARMA", bg="#27AE60")
        self.preview()