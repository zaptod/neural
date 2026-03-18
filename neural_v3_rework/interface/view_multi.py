"""
BATALHA MULTI-COMBATENTE v13.0 - NEURAL FIGHTS
Tela de seleção de equipes para batalhas com mais de 2 personagens.
Suporta até 4v4 (8 lutadores) com friendly fire.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulacao import simulacao
from dados.app_state import AppState
from nucleo.arena import ARENAS, MAPAS_MULTI
from interface.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_P1, COR_P2, CORES_CLASSE,
    COR_BG_CARD, COR_BORDA, COR_TEXTO_SUB
)
from interface.ui_components import UICard, make_primary_button, make_secondary_button

# Cores dos times
CORES_TIME = [
    "#E74C3C",  # Time 1 - Vermelho
    "#3498DB",  # Time 2 - Azul
    "#2ECC71",  # Time 3 - Verde
    "#F39C12",  # Time 4 - Amarelo
]

CORES_TIME_BG = [
    "#5D1F1F",  # Time 1 bg
    "#1A3A5C",  # Time 2 bg
    "#1A4D2E",  # Time 3 bg
    "#5C3D0A",  # Time 4 bg
]


class TelaMultiBatalha(tk.Frame):
    """Tela de seleção de equipes para batalha multi-combatente."""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)
        
        self.num_times = 2
        self.membros_por_time = 2
        self.team_slots = {}  # {(team_idx, slot_idx): personagem}
        self.cenario_selecionado = "Campo de Batalha"
        
        self.setup_ui()
        
        AppState.get().subscribe("characters_changed", self._on_data_changed)
        AppState.get().subscribe("weapons_changed", self._on_data_changed)
    
    def _on_data_changed(self, _data=None):
        self._atualizar_combos()
    
    def setup_ui(self):
        """Configura a interface completa."""
        # === HEADER ===
        header = tk.Frame(self, bg=COR_HEADER, height=88)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        make_secondary_button(
            header,
            "Voltar",
            lambda: self.controller.show_frame("MenuPrincipal"),
            padx=16,
            pady=8,
        ).pack(side="left", padx=18, pady=20)

        title_wrap = tk.Frame(header, bg=COR_HEADER)
        title_wrap.pack(side="left", fill="both", expand=True, pady=12)
        tk.Label(
            title_wrap, text="BATALHA MULTI-COMBATENTE",
            font=("Bahnschrift SemiBold", 24), bg=COR_HEADER, fg=COR_TEXTO, anchor="w"
        ).pack(fill="x")
        tk.Label(
            title_wrap, text="Monte esquadras, teste sinergia, pressao de mapa e coordenacao entre papeis.",
            font=("Segoe UI", 10), bg=COR_HEADER, fg=COR_TEXTO_SUB, anchor="w"
        ).pack(fill="x", pady=(2, 0))
        
        # === FOOTER ===
        footer = tk.Frame(self, bg=COR_BG)
        footer.pack(fill="x", side="bottom", pady=10)
        
        self.btn_iniciar = make_primary_button(
            footer,
            "INICIAR BATALHA EM EQUIPE",
            self.iniciar_batalha,
            font=("Bahnschrift SemiBold", 14),
            bg=COR_ACCENT,
            fg=COR_TEXTO,
            padx=30,
            pady=12,
        )
        self.btn_iniciar.pack()
        
        # === CONFIG BAR ===
        config_bar = UICard(self, bg=COR_BG_SECUNDARIO, border=COR_BORDA, pady=10)
        config_bar.pack(fill="x", padx=20, pady=(10, 5))
        
        # Número de times
        tk.Label(config_bar, text="Times:", font=("Segoe UI", 11, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(side="left", padx=(10, 5))
        self.var_num_times = tk.IntVar(value=2)
        for n in [2, 3, 4]:
            tk.Radiobutton(
                config_bar, text=str(n), variable=self.var_num_times, value=n,
                bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, selectcolor=COR_ACCENT,
                font=("Segoe UI", 11), command=self._rebuild_teams
            ).pack(side="left", padx=3)
        
        ttk.Separator(config_bar, orient="vertical").pack(side="left", fill="y", padx=10)
        
        # Membros por time
        tk.Label(config_bar, text="Lutadores/Time:", font=("Segoe UI", 11, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(side="left", padx=(10, 5))
        self.var_membros = tk.IntVar(value=2)
        for n in [1, 2, 3, 4]:
            tk.Radiobutton(
                config_bar, text=str(n), variable=self.var_membros, value=n,
                bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, selectcolor=COR_ACCENT,
                font=("Segoe UI", 11), command=self._rebuild_teams
            ).pack(side="left", padx=3)
        
        ttk.Separator(config_bar, orient="vertical").pack(side="left", fill="y", padx=10)
        
        # Cenário
        tk.Label(config_bar, text="Arena:", font=("Segoe UI", 11, "bold"),
                 bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(side="left", padx=(10, 5))
        self.var_cenario = tk.StringVar(value="Campo de Batalha")
        arenas_disponiveis = list(ARENAS.keys())
        self.combo_cenario = ttk.Combobox(
            config_bar, textvariable=self.var_cenario,
            values=arenas_disponiveis, state="readonly", width=20
        )
        self.combo_cenario.pack(side="left", padx=5)
        
        # Info bar
        self.lbl_info = tk.Label(
            config_bar, text="", font=("Segoe UI", 10),
            bg=COR_BG_SECUNDARIO, fg=COR_WARNING
        )
        self.lbl_info.pack(side="right", padx=10)
        
        # === SCROLLABLE TEAMS AREA ===
        self.scroll_frame = tk.Frame(self, bg=COR_BG)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Canvas com scrollbar
        self.canvas = tk.Canvas(self.scroll_frame, bg=COR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.scroll_frame, orient="vertical", command=self.canvas.yview)
        self.teams_container = tk.Frame(self.canvas, bg=COR_BG)
        
        self.teams_container.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.teams_container, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", 
            lambda ev: self.canvas.yview_scroll(int(-1*(ev.delta/120)), "units")))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        self._rebuild_teams()
    
    def _rebuild_teams(self):
        """Reconstrói os painéis de time."""
        # Limpa
        for widget in self.teams_container.winfo_children():
            widget.destroy()
        
        self.num_times = self.var_num_times.get()
        self.membros_por_time = self.var_membros.get()
        self.team_slots = {}
        self.combo_widgets = {}
        
        total = self.num_times * self.membros_por_time
        self.lbl_info.config(text=f"Total: {total} lutadores ({self.num_times} times × {self.membros_por_time})")
        
        if total > 8:
            self.lbl_info.config(text=f"⚠️ Máximo 8 lutadores! ({total} selecionados)", fg=COR_WARNING)
            return
        
        personagens = AppState.get().characters
        nomes = [p.nome for p in personagens] if personagens else []
        
        # Configura grid 
        cols = min(self.num_times, 4)
        for c in range(cols):
            self.teams_container.grid_columnconfigure(c, weight=1, uniform="team")
        
        for team_idx in range(self.num_times):
            cor_time = CORES_TIME[team_idx % len(CORES_TIME)]
            cor_bg = CORES_TIME_BG[team_idx % len(CORES_TIME_BG)]
            
            team_frame = tk.Frame(self.teams_container, bg=cor_bg, highlightthickness=1, highlightbackground=COR_BORDA)
            team_frame.grid(row=0, column=team_idx, sticky="nsew", padx=5, pady=5)
            
            # Header do time
            tk.Label(
                team_frame, text=f"⚔️ TIME {team_idx + 1}",
                font=("Bahnschrift SemiBold", 16), bg=cor_time, fg="white"
            ).pack(fill="x", pady=(0, 5))
            
            for slot_idx in range(self.membros_por_time):
                slot_frame = tk.Frame(team_frame, bg=cor_bg, pady=3)
                slot_frame.pack(fill="x", padx=8)
                
                tk.Label(
                    slot_frame, text=f"Slot {slot_idx + 1}:",
                    font=("Segoe UI", 10, "bold"), bg=cor_bg, fg=COR_TEXTO
                ).pack(side="left", padx=(5, 8))
                
                var = tk.StringVar(value="")
                combo = ttk.Combobox(
                    slot_frame, textvariable=var,
                    values=nomes, state="readonly", width=18
                )
                combo.pack(side="left", padx=5, fill="x", expand=True)
                
                key = (team_idx, slot_idx)
                self.team_slots[key] = var
                self.combo_widgets[key] = combo
                
                # Auto-select: tenta preencher slots com personagens diferentes
                auto_idx = team_idx * self.membros_por_time + slot_idx
                if auto_idx < len(nomes):
                    var.set(nomes[auto_idx])
                
                # Info label para mostrar classe/arma
                lbl = tk.Label(slot_frame, text="", font=("Segoe UI", 8),
                               bg=cor_bg, fg=COR_TEXTO_DIM)
                lbl.pack(side="left", padx=5)
                
                combo.bind("<<ComboboxSelected>>", 
                    lambda e, l=lbl, v=var: self._on_char_selected(v, l))
                
                # Trigger initial info
                self._on_char_selected(var, lbl)
    
    def _on_char_selected(self, var, lbl):
        """Atualiza info quando um personagem é selecionado."""
        nome = var.get()
        if not nome:
            lbl.config(text="")
            return
        
        personagens = AppState.get().characters
        char = next((p for p in personagens if p.nome == nome), None)
        if char:
            classe = getattr(char, 'classe', '?')
            arma = getattr(char, 'nome_arma', '?') or '?'
            lbl.config(text=f"({classe} / {arma})")
    
    def _atualizar_combos(self):
        """Atualiza as listas de personagens nos combos."""
        personagens = AppState.get().characters
        nomes = [p.nome for p in personagens] if personagens else []
        for combo in self.combo_widgets.values():
            combo['values'] = nomes
    
    def iniciar_batalha(self):
        """Valida seleção e inicia a simulação multi-combatente."""
        teams_data = []
        todos_nomes = set()
        
        for team_idx in range(self.num_times):
            members = []
            for slot_idx in range(self.membros_por_time):
                nome = self.team_slots[(team_idx, slot_idx)].get()
                if not nome:
                    messagebox.showwarning("Atenção", 
                        f"Selecione um personagem para Time {team_idx + 1}, Slot {slot_idx + 1}!")
                    return
                if nome in todos_nomes:
                    messagebox.showwarning("Atenção", 
                        f"Personagem '{nome}' está duplicado! Cada lutador deve ser único.")
                    return
                todos_nomes.add(nome)
                members.append(nome)
            
            teams_data.append({
                "team_id": team_idx,
                "members": members,
            })
        
        # Monta match_config com dados de time
        # p1_nome e p2_nome são obrigatórios para backward compat
        match_data = {
            "p1_nome": teams_data[0]["members"][0],
            "p2_nome": teams_data[1]["members"][0] if len(teams_data) > 1 else teams_data[0]["members"][-1],
            "cenario": self.var_cenario.get(),
            "best_of": 1,
            "portrait_mode": False,
            "teams": teams_data,  # v13.0: dados multi-fighter
        }
        
        try:
            AppState.get().set_match_config(match_data)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar config: {e}")
            return
        
        self.controller.withdraw()
        
        try:
            sim = simulacao.Simulador()
            sim.run()
            
            if sim.vencedor:
                messagebox.showinfo("Resultado", f"🏆 Vencedor: {sim.vencedor}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Simulação falhou:\n{e}")
        
        self.controller.deiconify()

