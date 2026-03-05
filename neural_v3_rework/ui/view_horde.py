"""
NEURAL FIGHTS — Tela do Modo Horda (Sobrevivência)
====================================================
Permite selecionar um campeão e enfrentar waves progressivas.
Cada wave é uma luta simulada; entre waves o jogador recebe cura.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.app_state import AppState
from simulation.horde_mode import HordeMode, HordeConfig, HordeWave
from ui.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT, COR_SUCCESS,
    COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_DANGER, CORES_CLASSE,
)


class TelaHorde(tk.Frame):
    """Tela de seleção e controle do Modo Horda."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg=COR_BG)

        self.personagem_selecionado = None
        self.horde = HordeMode.get_instance()
        self.resultados_waves: list[dict] = []

        self._build_ui()

        AppState.get().subscribe("characters_changed", self._on_data_changed)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _on_data_changed(self, _data=None):
        self.atualizar_dados()

    def atualizar_dados(self):
        """Atualiza lista de personagens no listbox."""
        chars = AppState.get().characters
        self.listbox.delete(0, tk.END)
        for p in chars:
            tag = f"  [{p.classe.split('(')[0].strip()}]" if hasattr(p, "classe") else ""
            self.listbox.insert(tk.END, f"{p.nome}{tag}")

        # Pinta linhas com cor da classe
        for i, p in enumerate(chars):
            cor = CORES_CLASSE.get(getattr(p, "classe", ""), COR_TEXTO_DIM)
            self.listbox.itemconfig(i, fg=cor)

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── HEADER ──
        header = tk.Frame(self, bg=COR_HEADER, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Button(
            header, text="◄ VOLTAR",
            bg=COR_BG_SECUNDARIO, fg=COR_TEXTO,
            font=("Arial", 10, "bold"), bd=0, padx=15,
            command=lambda: self.controller.show_frame("MenuPrincipal"),
        ).pack(side="left", padx=15, pady=15)

        tk.Label(
            header, text="🏰 MODO HORDA — Sobrevivência",
            font=("Arial", 18, "bold"), bg=COR_HEADER, fg=COR_TEXTO,
        ).pack(side="left", padx=20)

        # ── MAIN AREA ──
        main = tk.Frame(self, bg=COR_BG)
        main.pack(fill="both", expand=True, padx=20, pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # ── LEFT: seleção de campeão ──
        left = tk.Frame(main, bg=COR_BG_SECUNDARIO, bd=1, relief="solid")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(
            left, text="Escolha seu Campeão",
            font=("Arial", 14, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO,
        ).pack(pady=(12, 6))

        # Search
        search_frame = tk.Frame(left, bg=COR_BG_SECUNDARIO)
        search_frame.pack(fill="x", padx=10)
        self.var_busca = tk.StringVar()
        self.var_busca.trace_add("write", self._filtrar_lista)
        tk.Entry(
            search_frame, textvariable=self.var_busca,
            bg=COR_BG, fg=COR_TEXTO, insertbackground=COR_TEXTO,
            font=("Arial", 11), relief="flat",
        ).pack(fill="x", pady=4)

        # Listbox
        lb_frame = tk.Frame(left, bg=COR_BG_SECUNDARIO)
        lb_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        scroll = tk.Scrollbar(lb_frame)
        scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(
            lb_frame, bg=COR_BG, fg=COR_TEXTO,
            font=("Consolas", 11), selectbackground=COR_ACCENT,
            yscrollcommand=scroll.set, relief="flat", bd=0,
        )
        self.listbox.pack(fill="both", expand=True)
        scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Info do selecionado
        self.lbl_info = tk.Label(
            left, text="Nenhum selecionado",
            font=("Arial", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM,
            wraplength=250, justify="left",
        )
        self.lbl_info.pack(pady=(0, 10), padx=10, anchor="w")

        # ── RIGHT: config + log ──
        right = tk.Frame(main, bg=COR_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # ── Config panel ──
        cfg_frame = tk.LabelFrame(
            right, text=" Configuração ",
            font=("Arial", 12, "bold"), fg=COR_SUCCESS, bg=COR_BG_SECUNDARIO,
            labelanchor="n", bd=1,
        )
        cfg_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        cfg_inner = tk.Frame(cfg_frame, bg=COR_BG_SECUNDARIO)
        cfg_inner.pack(fill="x", padx=15, pady=10)

        # Wave cura
        tk.Label(cfg_inner, text="Cura entre waves:", bg=COR_BG_SECUNDARIO,
                 fg=COR_TEXTO, font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=3)
        self.var_cura = tk.StringVar(value="30%")
        ttk.Combobox(cfg_inner, textvariable=self.var_cura, state="readonly",
                     values=["10%", "20%", "30%", "50%", "Sem Cura"],
                     width=12).grid(row=0, column=1, padx=10, pady=3)

        # Dificuldade
        tk.Label(cfg_inner, text="Dificuldade:", bg=COR_BG_SECUNDARIO,
                 fg=COR_TEXTO, font=("Arial", 11)).grid(row=1, column=0, sticky="w", pady=3)
        self.var_dif = tk.StringVar(value="Normal")
        ttk.Combobox(cfg_inner, textvariable=self.var_dif, state="readonly",
                     values=["Fácil", "Normal", "Difícil", "Pesadelo"],
                     width=12).grid(row=1, column=1, padx=10, pady=3)

        # Cenário
        tk.Label(cfg_inner, text="Cenário:", bg=COR_BG_SECUNDARIO,
                 fg=COR_TEXTO, font=("Arial", 11)).grid(row=2, column=0, sticky="w", pady=3)
        self.var_cenario = tk.StringVar(value="Arena")
        ttk.Combobox(cfg_inner, textvariable=self.var_cenario, state="readonly",
                     values=["Arena", "Caverna", "Floresta", "Ruínas", "Coliseu"],
                     width=12).grid(row=2, column=1, padx=10, pady=3)

        # ── Log / Resultado ──
        log_frame = tk.LabelFrame(
            right, text=" Registro de Waves ",
            font=("Arial", 12, "bold"), fg=COR_ACCENT, bg=COR_BG_SECUNDARIO,
            labelanchor="n", bd=1,
        )
        log_frame.grid(row=1, column=0, sticky="nsew")

        self.text_log = tk.Text(
            log_frame, bg=COR_BG, fg=COR_TEXTO,
            font=("Consolas", 10), relief="flat", wrap="word",
            state="disabled", padx=8, pady=8,
        )
        self.text_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Tags de cor
        self.text_log.tag_configure("titulo", foreground=COR_SUCCESS, font=("Consolas", 11, "bold"))
        self.text_log.tag_configure("wave", foreground=COR_ACCENT, font=("Consolas", 10, "bold"))
        self.text_log.tag_configure("vitoria", foreground="#2ecc71")
        self.text_log.tag_configure("derrota", foreground=COR_DANGER)
        self.text_log.tag_configure("cura", foreground="#87ceeb")
        self.text_log.tag_configure("boss", foreground="#ff6600", font=("Consolas", 10, "bold"))
        self.text_log.tag_configure("info", foreground=COR_TEXTO_DIM)
        self.text_log.tag_configure("resumo", foreground="#ffd700", font=("Consolas", 11, "bold"))

        # ── FOOTER botões ──
        footer = tk.Frame(self, bg=COR_BG)
        footer.pack(fill="x", side="bottom", pady=12)

        self.btn_iniciar = tk.Button(
            footer, text="🏰  INICIAR MODO HORDA  🏰",
            font=("Arial", 15, "bold"),
            bg=COR_ACCENT, fg="white",
            bd=0, padx=40, pady=10,
            state="disabled",
            command=self._iniciar_horda,
        )
        self.btn_iniciar.pack(side="left", padx=(20, 10))

        self.btn_parar = tk.Button(
            footer, text="⏹ Parar",
            font=("Arial", 12, "bold"),
            bg=COR_DANGER, fg="white",
            bd=0, padx=20, pady=10,
            state="disabled",
            command=self._parar_horda,
        )
        self.btn_parar.pack(side="left", padx=5)

        self.lbl_status = tk.Label(
            footer, text="Selecione um campeão para começar",
            font=("Arial", 11), bg=COR_BG, fg=COR_TEXTO_DIM,
        )
        self.lbl_status.pack(side="right", padx=20)

    # ── Listbox events ────────────────────────────────────────────────────────

    def _filtrar_lista(self, *_args):
        termo = self.var_busca.get().lower()
        chars = AppState.get().characters
        self.listbox.delete(0, tk.END)
        for p in chars:
            txt = f"{p.nome} {getattr(p, 'classe', '')}".lower()
            if termo in txt:
                tag = f"  [{p.classe.split('(')[0].strip()}]" if hasattr(p, "classe") else ""
                self.listbox.insert(tk.END, f"{p.nome}{tag}")
        # Recolor
        idx = 0
        for p in chars:
            txt = f"{p.nome} {getattr(p, 'classe', '')}".lower()
            if termo in txt:
                cor = CORES_CLASSE.get(getattr(p, "classe", ""), COR_TEXTO_DIM)
                self.listbox.itemconfig(idx, fg=cor)
                idx += 1

    def _on_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        texto = self.listbox.get(sel[0])
        nome = texto.split("  [")[0].strip()
        chars = AppState.get().characters
        char = next((c for c in chars if c.nome == nome), None)
        if char:
            self.personagem_selecionado = char
            classe = getattr(char, "classe", "?")
            hp = char.get_vida_max()
            mana = char.get_mana_max()
            self.lbl_info.config(
                text=f"⚔ {char.nome}\n"
                     f"Classe: {classe}\n"
                     f"Força: {char.forca:.1f}  |  Mana: {char.mana:.1f}\n"
                     f"HP: {hp:.0f}  |  MP: {mana:.0f}\n"
                     f"Arma: {char.nome_arma or 'Nenhuma'}",
                fg=COR_TEXTO,
            )
            self.btn_iniciar.config(state="normal", bg=COR_ACCENT)
        else:
            self.personagem_selecionado = None
            self.btn_iniciar.config(state="disabled", bg=COR_TEXTO_DIM)

    # ── Horde control ─────────────────────────────────────────────────────────

    def _get_config(self) -> HordeConfig:
        """Constrói HordeConfig a partir dos controles da UI."""
        cfg = HordeConfig()

        cura_map = {"10%": 0.10, "20%": 0.20, "30%": 0.30, "50%": 0.50, "Sem Cura": 0.0}
        cfg.cura_entre_waves = cura_map.get(self.var_cura.get(), 0.30)

        dif = self.var_dif.get()
        if dif == "Fácil":
            cfg.hp_mult_por_wave = 0.05
            cfg.dano_mult_por_wave = 0.03
        elif dif == "Difícil":
            cfg.hp_mult_por_wave = 0.12
            cfg.dano_mult_por_wave = 0.08
            cfg.inimigos_max = 5
        elif dif == "Pesadelo":
            cfg.hp_mult_por_wave = 0.18
            cfg.dano_mult_por_wave = 0.12
            cfg.inimigos_max = 6
            cfg.boss_a_cada = 3

        return cfg

    def _log(self, texto: str, tag: str = "info"):
        """Adiciona texto ao log."""
        self.text_log.config(state="normal")
        self.text_log.insert(tk.END, texto + "\n", tag)
        self.text_log.see(tk.END)
        self.text_log.config(state="disabled")

    def _limpar_log(self):
        self.text_log.config(state="normal")
        self.text_log.delete("1.0", tk.END)
        self.text_log.config(state="disabled")

    def _criar_inimigo_dados(self, info: dict):
        """
        Cria um Personagem temporário a partir dos dados de wave do HordeMode.
        Retorna objeto Personagem pronto para ser passado ao Simulador.
        """
        from models.characters import Personagem

        # Gera stats baseados no level
        level = info.get("level", 1)
        base_f = min(10.0, max(1.0, 3.0 + level * 0.3 + random.uniform(-0.5, 0.5)))
        base_m = min(10.0, max(1.0, 3.0 + level * 0.2 + random.uniform(-0.5, 0.5)))
        tamanho = round(random.uniform(1.0, 2.2), 1)

        p = Personagem(
            nome=info["nome"],
            tamanho=tamanho,
            forca=round(base_f, 1),
            mana=round(base_m, 1),
            classe=info["classe"],
            r=random.randint(100, 255),
            g=random.randint(30, 180),
            b=random.randint(30, 180),
        )

        # Tenta equipar uma arma aleatória
        armas = AppState.get().weapons
        if armas:
            tipo_desejado = info.get("tipo_arma", "Reta")
            candidatas = [a for a in armas if getattr(a, "tipo", "") == tipo_desejado]
            if not candidatas:
                candidatas = armas
            arma = random.choice(candidatas)
            p.nome_arma = arma.nome
            p.arma_obj = arma
            p.calcular_status(arma.peso)

        return p

    def _iniciar_horda(self):
        """Inicia o loop do modo horda."""
        if not self.personagem_selecionado:
            messagebox.showwarning("Atenção", "Selecione um campeão!")
            return

        if not self.personagem_selecionado.nome_arma:
            messagebox.showwarning("Atenção", "Seu campeão não possui arma equipada!")
            return

        # UI state
        self.btn_iniciar.config(state="disabled", bg=COR_TEXTO_DIM)
        self.btn_parar.config(state="normal")
        self.listbox.config(state="disabled")
        self._limpar_log()
        self.resultados_waves.clear()
        self._horda_ativa = True

        # Config
        config = self._get_config()
        self.horde.reset()
        self.horde = HordeMode.get_instance()
        self.horde.iniciar(config)

        jogador_nome = self.personagem_selecionado.nome
        cenario = self.var_cenario.get()

        self._log("══════════════════════════════════════", "titulo")
        self._log(f"  MODO HORDA — {jogador_nome}", "titulo")
        self._log(f"  Dificuldade: {self.var_dif.get()}  |  Cura: {self.var_cura.get()}", "info")
        self._log("══════════════════════════════════════\n", "titulo")

        # Processa waves sequencialmente via after() para manter UI responsiva
        self._wave_loop(jogador_nome, cenario)

    def _wave_loop(self, jogador_nome: str, cenario: str):
        """Processa uma wave e agenda a próxima."""
        if not self._horda_ativa:
            return

        wave = self.horde.gerar_proxima_wave()
        if wave is None:
            self._finalizar("Erro ao gerar wave")
            return

        n_inimigos = len(wave.inimigos)
        if wave.boss:
            boss_classe = wave.inimigos[0]["classe"] if wave.inimigos else "?"
            self._log(f"\n⚠ === WAVE {wave.numero} — BOSS: {boss_classe} === ⚠", "boss")
        else:
            self._log(f"\n── Wave {wave.numero} — {n_inimigos} inimigo(s) ──", "wave")

        for info in wave.inimigos:
            self._log(f"  • {info['nome']} ({info['classe']}) Lv.{info['level']}", "info")

        self.lbl_status.config(text=f"Wave {wave.numero} em andamento...")
        self.update_idletasks()

        # Lança a luta via Simulador
        vitoria = self._executar_wave_luta(jogador_nome, wave, cenario)

        if vitoria:
            self._log(f"  ✔ VITÓRIA na wave {wave.numero}!", "vitoria")
            self.resultados_waves.append({"wave": wave.numero, "resultado": "vitoria"})
            if self.horde.state:
                self.horde.state.wave_concluida()

            # Cura entre waves
            cura_pct = self.horde.state.config.cura_entre_waves if self.horde.state else 0.0
            mana_pct = self.horde.state.config.mana_entre_waves if self.horde.state else 0.0
            if cura_pct > 0:
                self._log(f"  💊 Cura: +{int(cura_pct*100)}% HP, +{int(mana_pct*100)}% Mana", "cura")

            self.lbl_status.config(text=f"Wave {wave.numero} concluída! Preparando próxima...")
            self.update_idletasks()

            # Agenda próxima wave (pequeno delay para o jogador ler o log)
            self.after(800, lambda: self._wave_loop(jogador_nome, cenario))
        else:
            self._log(f"\n  ✖ DERROTA na wave {wave.numero}!", "derrota")
            self.resultados_waves.append({"wave": wave.numero, "resultado": "derrota"})
            self._finalizar(f"Caiu na wave {wave.numero}")

    def _executar_wave_luta(self, jogador_nome: str, wave: HordeWave, cenario: str) -> bool:
        """
        Executa a luta de uma wave usando o Simulador padrão.
        O jogador enfrenta cada inimigo da wave sequencialmente (1v1).
        Retorna True se o jogador sobreviveu a todos.
        """
        from simulation import simulacao

        for info in wave.inimigos:
            if not self._horda_ativa:
                return False

            # Cria personagem inimigo temporário
            inimigo = self._criar_inimigo_dados(info)

            # Configura match_config para a luta
            # Precisamos registrar o inimigo temporariamente no AppState
            state = AppState.get()

            # Salva personagens originais
            chars_original = list(state.characters)
            armas_original = list(state.weapons)

            # Adiciona inimigo se não existe
            if not any(c.nome == inimigo.nome for c in state.characters):
                state._characters.append(inimigo)

            match_data = {
                "p1_nome": jogador_nome,
                "p2_nome": inimigo.nome,
                "cenario": cenario,
                "best_of": 1,
                "portrait_mode": False,
                "horde_mode": True,
                "horde_wave": wave.numero,
            }

            try:
                state.set_match_config(match_data)
            except Exception:
                pass

            # Esconde janela principal e executa luta
            self.controller.withdraw()

            vencedor = None
            try:
                sim = simulacao.Simulador()
                sim.run()
                vencedor = sim.vencedor
            except Exception as e:
                self._log(f"  ⚠ Erro na simulação: {e}", "derrota")

            self.controller.deiconify()

            # Restaura personagens originais (remove inimigos temporários)
            state._characters = chars_original
            state._weapons = armas_original

            # Verifica resultado
            if vencedor != jogador_nome:
                # Individual kills already tracked via += 1 above
                return False

            if self.horde.state:
                self.horde.state.inimigos_derrotados += 1
            self._log(f"    → {jogador_nome} derrotou {inimigo.nome}!", "vitoria")
            self.update_idletasks()

        return True

    def _parar_horda(self):
        """Para o modo horda manualmente."""
        self._horda_ativa = False
        self._finalizar("Interrompido pelo jogador")

    def _finalizar(self, motivo: str):
        """Finaliza o modo horda e exibe resumo."""
        self._horda_ativa = False
        self.btn_iniciar.config(state="normal", bg=COR_ACCENT)
        self.btn_parar.config(state="disabled")
        self.listbox.config(state="normal")

        resumo = self.horde.finalizar() if self.horde.state else {}
        waves_ok = resumo.get("waves_completas", 0)
        kills = resumo.get("inimigos_derrotados", 0)

        self._log("\n══════════════════════════════════════", "resumo")
        self._log("           RESULTADO FINAL", "resumo")
        self._log("══════════════════════════════════════", "resumo")
        self._log(f"  Motivo: {motivo}", "info")
        self._log(f"  Waves completadas: {waves_ok}", "resumo")
        self._log(f"  Inimigos derrotados: {kills}", "resumo")
        self._log("══════════════════════════════════════\n", "resumo")

        self.lbl_status.config(
            text=f"Horda finalizada — {waves_ok} waves | {kills} kills",
            fg=COR_SUCCESS if waves_ok > 0 else COR_DANGER,
        )

        if waves_ok >= 10:
            messagebox.showinfo("Modo Horda", f"Impressionante! Você completou {waves_ok} waves!\nKills: {kills}")
        elif waves_ok >= 5:
            messagebox.showinfo("Modo Horda", f"Bom trabalho! {waves_ok} waves completadas.\nKills: {kills}")
