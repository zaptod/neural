import tkinter as tk
from tkinter import ttk, messagebox
import json
import simulacao # Importa o módulo da simulação

class TelaLuta(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#2C3E50")
        self.setup_ui()

    def setup_ui(self):
        # --- CABEÇALHO ---
        header = tk.Frame(self, bg="#34495E", height=50)
        header.pack(fill="x", side="top")
        
        btn_voltar = tk.Button(header, text="< VOLTAR", bg="#E67E22", fg="white", font=("Arial", 10, "bold"),
                               command=lambda: self.controller.show_frame("MenuPrincipal"))
        btn_voltar.pack(side="left", padx=10, pady=10)

        tk.Label(header, text="CONFIGURAÇÃO DE BATALHA", font=("Helvetica", 18, "bold"), 
                 bg="#34495E", fg="#ECF0F1").pack(side="left", padx=20)

        # --- ÁREA DE SELEÇÃO (GRID) ---
        container = tk.Frame(self, bg="#2C3E50")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Lado Esquerdo (Player 1)
        f1 = tk.Frame(container, bg="#2C3E50")
        f1.grid(row=0, column=0, padx=20)
        tk.Label(f1, text="PLAYER 1", font=("Impact", 20), bg="#2C3E50", fg="#3498DB").pack()
        
        self.combo_p1 = ttk.Combobox(f1, state="readonly", width=20)
        self.combo_p1.pack(pady=10)
        self.combo_p1.bind("<<ComboboxSelected>>", self.atualizar_previews)
        
        self.cv_p1 = tk.Canvas(f1, width=150, height=150, bg="#34495E", highlightthickness=0)
        self.cv_p1.pack(pady=10)
        
        self.lbl_stats_p1 = tk.Label(f1, text="", bg="#2C3E50", fg="white", justify="left")
        self.lbl_stats_p1.pack()

        # VS
        tk.Label(container, text="VS", font=("Impact", 40), bg="#2C3E50", fg="#E74C3C").grid(row=0, column=1)

        # Lado Direito (Player 2)
        f2 = tk.Frame(container, bg="#2C3E50")
        f2.grid(row=0, column=2, padx=20)
        tk.Label(f2, text="PLAYER 2", font=("Impact", 20), bg="#2C3E50", fg="#E74C3C").pack()
        
        self.combo_p2 = ttk.Combobox(f2, state="readonly", width=20)
        self.combo_p2.pack(pady=10)
        self.combo_p2.bind("<<ComboboxSelected>>", self.atualizar_previews)
        
        self.cv_p2 = tk.Canvas(f2, width=150, height=150, bg="#34495E", highlightthickness=0)
        self.cv_p2.pack(pady=10)
        
        self.lbl_stats_p2 = tk.Label(f2, text="", bg="#2C3E50", fg="white", justify="left")
        self.lbl_stats_p2.pack()

        # Botão Iniciar
        tk.Button(self, text="INICIAR SIMULAÇÃO", font=("Arial", 16, "bold"), bg="#27AE60", fg="white",
                  width=30, height=2, command=self.iniciar_luta).pack(pady=30)

    def atualizar_dados(self):
        nomes = [p.nome for p in self.controller.lista_personagens]
        self.combo_p1['values'] = nomes
        self.combo_p2['values'] = nomes
        
        if len(nomes) >= 2:
            self.combo_p1.current(0)
            self.combo_p2.current(1)
            self.atualizar_previews()

    def desenhar_char(self, cv, nome):
        cv.delete("all")
        p = next((x for x in self.controller.lista_personagens if x.nome == nome), None)
        if not p: return ""
        
        cx, cy = 75, 75
        raio = min(p.tamanho * 10, 60)
        cor = f"#{p.cor_r:02x}{p.cor_g:02x}{p.cor_b:02x}"
        
        cv.create_oval(cx-raio, cy-raio, cx+raio, cy+raio, fill=cor, outline="white")
        
        desc_arma = "Mãos Limpas"
        if p.nome_arma:
            # Busca a arma na lista do controller
            arma = next((a for a in self.controller.lista_armas if a.nome == p.nome_arma), None)
            if arma:
                desc_arma = f"{arma.nome} ({arma.tipo})"
                cor_arma = f"#{arma.r:02x}{arma.g:02x}{arma.b:02x}"
                
                if "Reta" in arma.tipo:
                    # Desenha linha
                    cv.create_line(cx, cy, cx+raio+20, cy, fill=cor_arma, width=4)
                else:
                    # Desenha arco
                    tam = arma.largura
                    cv.create_arc(cx-raio-10, cy-raio-10, cx+raio+10, cy+raio+10,
                                  start=-tam/2, extent=tam, style="arc", outline=cor_arma, width=4)

        return f"Velocidade: {p.velocidade:.2f}\nResistência: {p.resistencia:.2f}\nArma: {desc_arma}"

    def atualizar_previews(self, event=None):
        stats1 = self.desenhar_char(self.cv_p1, self.combo_p1.get())
        self.lbl_stats_p1.config(text=stats1)

        stats2 = self.desenhar_char(self.cv_p2, self.combo_p2.get())
        self.lbl_stats_p2.config(text=stats2)

    def iniciar_luta(self):
        p1 = self.combo_p1.get()
        p2 = self.combo_p2.get()
        
        if not p1 or not p2:
            messagebox.showwarning("Ops", "Selecione dois lutadores!")
            return

        match_data = {
            "p1_nome": p1,
            "p2_nome": p2,
            "cenario": "Arena Padrão"
        }
        
        try:
            with open("match_config.json", "w", encoding="utf-8") as f:
                json.dump(match_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar config: {e}")
            return

        # --- INTEGRAÇÃO: Esconde Launcher e Roda Simulação ---
        self.controller.withdraw()
        
        try:
            sim = simulacao.Simulador()
            sim.run()
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"A simulação falhou: {e}")
        
        # Quando a simulação fechar, volta pro menu
        self.controller.deiconify()