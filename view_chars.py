import tkinter as tk
from tkinter import ttk, messagebox
from models import Personagem, LISTA_CLASSES
import database

class TelaPersonagens(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#2C3E50")
        self.indice_em_edicao = None
        self.setup_ui()

    def setup_ui(self):
        tk.Label(self, text="Gerenciador de Personagens & Classes", font=("Helvetica", 20, "bold"), bg="#2C3E50", fg="white").pack(pady=10)
        
        frame_top = tk.Frame(self, bg="#2C3E50")
        frame_top.pack(fill="x", padx=20)
        
        # Esquerda: Inputs
        frame_form = tk.Frame(frame_top, bg="#2C3E50")
        frame_form.pack(side="left")

        self.ent_nome = self.criar_input(frame_form, "Nome:", 0)
        self.ent_tam = self.criar_input(frame_form, "Tamanho (m):", 1)
        self.ent_forca = self.criar_input(frame_form, "Força (Físico):", 2)
        self.ent_mana = self.criar_input(frame_form, "Magia (Mental):", 3)

        # Seleção de Classe (NOVO)
        tk.Label(frame_form, text="Classe:", bg="#2C3E50", fg="#F1C40F").grid(row=4, column=0, sticky="e")
        self.combo_classe = ttk.Combobox(frame_form, values=LISTA_CLASSES, state="readonly")
        self.combo_classe.grid(row=4, column=1, pady=5)
        self.combo_classe.current(0)

        # Seleção de Arma
        tk.Label(frame_form, text="Arma:", bg="#2C3E50", fg="white").grid(row=5, column=0, sticky="e")
        self.combo_arma = ttk.Combobox(frame_form, state="readonly")
        self.combo_arma.grid(row=5, column=1, pady=5)
        self.combo_arma.bind("<<ComboboxSelected>>", self.preview)

        # Inputs de Cor (RGB)
        tk.Label(frame_form, text="Cor RGB:", bg="#2C3E50", fg="white").grid(row=6, column=0, sticky="e")
        frgb = tk.Frame(frame_form, bg="#2C3E50")
        frgb.grid(row=6, column=1, sticky="w")
        
        self.er, self.eg, self.eb = [tk.Entry(frgb, width=4) for _ in range(3)]
        for e in [self.er, self.eg, self.eb]: 
            e.pack(side="left", padx=2)
            e.insert(0, "50")
            e.bind("<KeyRelease>", self.preview)

        # Direita: Canvas (Visualizador)
        frame_vis = tk.Frame(frame_top, bg="#2C3E50")
        frame_vis.pack(side="right", padx=20)
        
        tk.Label(frame_vis, text="Preview", bg="#2C3E50", fg="#BDC3C7", font=("Arial", 8)).pack()
        self.cv = tk.Canvas(frame_vis, width=150, height=150, bg="#34495E", highlightthickness=0)
        self.cv.pack()

        # --- BOTÕES ---
        f_btn = tk.Frame(self, bg="#2C3E50")
        f_btn.pack(pady=10)
        
        self.btn_salvar = tk.Button(f_btn, text="Salvar Novo", bg="#27AE60", fg="white", width=15, command=self.salvar)
        self.btn_salvar.pack(side="left", padx=5)
        
        self.btn_limpar = tk.Button(f_btn, text="Limpar / Novo", width=12, command=self.limpar)
        self.btn_limpar.pack(side="left", padx=5)

        self.btn_excluir = tk.Button(f_btn, text="Excluir", bg="#C0392B", fg="white", width=10, command=self.excluir)
        self.btn_excluir.pack(side="left", padx=5)
        self.btn_excluir.config(state="disabled") 

        # --- TABELA ---
        cols = ("Nome", "Classe", "For", "Mag", "Arma")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=6)
        
        self.tree.heading("Nome", text="Nome"); self.tree.column("Nome", width=80)
        self.tree.heading("Classe", text="Classe"); self.tree.column("Classe", width=100)
        self.tree.heading("For", text="For"); self.tree.column("For", width=40)
        self.tree.heading("Mag", text="Mag"); self.tree.column("Mag", width=40)
        self.tree.heading("Arma", text="Arma"); self.tree.column("Arma", width=80)
            
        self.tree.pack(fill="x", padx=20, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar)

        tk.Button(self, text="Voltar ao Menu", command=lambda: self.controller.show_frame("MenuPrincipal")).pack(pady=5)

    def criar_input(self, frame, txt, row):
        tk.Label(frame, text=txt, bg="#2C3E50", fg="white").grid(row=row, column=0, sticky="e", pady=5)
        e = tk.Entry(frame)
        e.grid(row=row, column=1, pady=5)
        e.bind("<KeyRelease>", self.preview)
        return e

    def atualizar_dados(self):
        nomes = ["Nenhuma"] + [a.nome for a in self.controller.lista_armas]
        self.combo_arma['values'] = nomes
        if not self.combo_arma.get(): self.combo_arma.current(0)
        
        for i in self.tree.get_children(): self.tree.delete(i)
        for p in self.controller.lista_personagens:
            # Compatibilidade com jsons antigos
            classe = getattr(p, "classe", "Guerreiro (Passiva)")
            self.tree.insert("", "end", values=(
                p.nome, classe, p.forca, p.mana, p.nome_arma
            ))

    def preview(self, event=None):
        self.cv.delete("all")
        cx, cy = 75, 75
        try:
            tam = float(self.ent_tam.get() or 1.0)
            r = int(self.er.get() or 50)
            g = int(self.eg.get() or 50)
            b = int(self.eb.get() or 50)
            cor = f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"
            
            raio = tam * 10
            raio_vis = min(raio, 70) 
            self.cv.create_oval(cx-raio_vis, cy-raio_vis, cx+raio_vis, cy+raio_vis, fill=cor, outline="white")

            nome_arma = self.combo_arma.get()
            arma_obj = next((a for a in self.controller.lista_armas if a.nome == nome_arma), None)
            
            if arma_obj:
                cor_arma = f"#{arma_obj.r:02x}{arma_obj.g:02x}{arma_obj.b:02x}"
                if "Reta" in arma_obj.tipo:
                    self.cv.create_line(cx, cy, cx + raio_vis + 20, cy, fill=cor_arma, width=3)
                else:
                    self.cv.create_arc(cx-raio_vis-5, cy-raio_vis-5, cx+raio_vis+5, cy+raio_vis+5,
                                       start=0, extent=60, style="arc", outline=cor_arma, width=3)
        except ValueError:
            pass

    def salvar(self):
        try:
            nome = self.ent_nome.get()
            if not nome: return
            
            for i, p in enumerate(self.controller.lista_personagens):
                if p.nome.lower() == nome.lower():
                    if self.indice_em_edicao is None or self.indice_em_edicao != i:
                        messagebox.showerror("Erro", f"Já existe um personagem chamado '{nome}'.")
                        return

            tam = float(self.ent_tam.get())
            forca = float(self.ent_forca.get())
            mana = float(self.ent_mana.get())
            r = self.er.get(); g = self.eg.get(); b = self.eb.get()

            nome_arma = self.combo_arma.get()
            if nome_arma == "Nenhuma": nome_arma = ""
            
            arma_obj = next((a for a in self.controller.lista_armas if a.nome == nome_arma), None)
            peso_arma = arma_obj.peso if arma_obj else 0

            # Salva a CLASSE SELECIONADA
            classe_selecionada = self.combo_classe.get()

            p = Personagem(nome, tam, forca, mana, nome_arma, peso_arma, r, g, b, classe_selecionada)

            if self.indice_em_edicao is None:
                self.controller.lista_personagens.append(p)
                msg = "Personagem Criado!"
            else:
                self.controller.lista_personagens[self.indice_em_edicao] = p
                msg = "Personagem Atualizado!"

            database.salvar_lista_chars(self.controller.lista_personagens)
            self.atualizar_dados()
            self.limpar()
            messagebox.showinfo("Sucesso", msg)
            
        except ValueError:
            messagebox.showerror("Erro", "Verifique valores numéricos!")

    def excluir(self):
        if self.indice_em_edicao is not None:
            if messagebox.askyesno("Confirmar", "Excluir personagem?"):
                del self.controller.lista_personagens[self.indice_em_edicao]
                database.salvar_lista_chars(self.controller.lista_personagens)
                self.atualizar_dados()
                self.limpar()

    def selecionar(self, event):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        self.indice_em_edicao = idx
        p = self.controller.lista_personagens[idx]

        self.ent_nome.delete(0, 'end'); self.ent_nome.insert(0, p.nome)
        self.ent_tam.delete(0, 'end'); self.ent_tam.insert(0, str(p.tamanho))
        self.ent_forca.delete(0, 'end'); self.ent_forca.insert(0, str(p.forca))
        self.ent_mana.delete(0, 'end'); self.ent_mana.insert(0, str(p.mana))
        
        self.combo_arma.set(p.nome_arma if p.nome_arma else "Nenhuma")
        self.combo_classe.set(getattr(p, "classe", "Guerreiro (Passiva)"))
        
        self.er.delete(0, 'end'); self.er.insert(0, str(p.cor_r))
        self.eg.delete(0, 'end'); self.eg.insert(0, str(p.cor_g))
        self.eb.delete(0, 'end'); self.eb.insert(0, str(p.cor_b))

        self.btn_salvar.config(text="Salvar Alterações", bg="#E67E22")
        self.btn_excluir.config(state="normal")
        self.preview()

    def limpar(self):
        self.indice_em_edicao = None
        self.ent_nome.delete(0, 'end')
        self.ent_tam.delete(0, 'end')
        self.ent_forca.delete(0, 'end')
        self.ent_mana.delete(0, 'end')
        self.er.delete(0, 'end'); self.er.insert(0, "50")
        self.eg.delete(0, 'end'); self.eg.insert(0, "50")
        self.eb.delete(0, 'end'); self.eb.insert(0, "50")
        self.combo_arma.current(0)
        self.combo_classe.current(0)
        self.tree.selection_remove(self.tree.selection())
        self.btn_salvar.config(text="Salvar Novo", bg="#27AE60")
        self.btn_excluir.config(state="disabled")
        self.preview()