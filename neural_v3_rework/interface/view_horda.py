import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dados.app_state import AppState
from interface.theme import (
    COR_ACCENT,
    COR_BG,
    COR_BG_SECUNDARIO,
    COR_BORDA,
    COR_HEADER,
    COR_SUCCESS,
    COR_TEXTO,
    COR_TEXTO_DIM,
)
from interface.ui_components import UICard, build_page_header, make_primary_button, make_secondary_button
from nucleo.arena import ARENAS
from simulacao import simulacao
from utilitarios.encounter_config import build_horde_match_config, load_horde_presets


class TelaHorda(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_BG)
        self.controller = controller
        self.state = AppState.get()
        self.horde_presets = load_horde_presets()
        self.slot_vars = []
        self._preset_desc = tk.StringVar(value="")
        self._build_ui()
        self.state.subscribe("characters_changed", self._on_data_changed)

    def _build_ui(self):
        build_page_header(
            self,
            "MODO HORDA",
            "Monte um sobrevivente ou esquadra e enfrente ondas usando o motor principal.",
            lambda: self.controller.show_frame("MenuPrincipal"),
            button_bg=COR_ACCENT,
            button_fg="#07131f",
        )

        config = UICard(self, bg=COR_BG_SECUNDARIO, border=COR_BORDA)
        config.pack(fill="x", padx=24, pady=(18, 12))

        tk.Label(config, text="Lutadores", font=("Segoe UI", 11, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).grid(row=0, column=0, sticky="w", padx=14, pady=10)
        self.var_slots = tk.IntVar(value=3)
        for idx, amount in enumerate((1, 2, 3, 4)):
            tk.Radiobutton(
                config,
                text=str(amount),
                value=amount,
                variable=self.var_slots,
                command=self._rebuild_slots,
                bg=COR_BG_SECUNDARIO,
                fg=COR_TEXTO,
                selectcolor=COR_ACCENT,
            ).grid(row=0, column=idx + 1, sticky="w")

        tk.Label(config, text="Preset de ondas", font=("Segoe UI", 11, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).grid(row=1, column=0, sticky="w", padx=14, pady=10)
        self.var_preset = tk.StringVar(value=next(iter(self.horde_presets.keys()), ""))
        self.combo_preset = ttk.Combobox(config, textvariable=self.var_preset, values=list(self.horde_presets.keys()), state="readonly", width=24)
        self.combo_preset.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 10))
        self.combo_preset.bind("<<ComboboxSelected>>", lambda _e: self._update_preset_info())

        tk.Label(config, text="Arena", font=("Segoe UI", 11, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).grid(row=1, column=3, sticky="e", padx=8)
        self.var_cenario = tk.StringVar(value="Campo de Batalha")
        ttk.Combobox(config, textvariable=self.var_cenario, values=list(ARENAS.keys()), state="readonly", width=18).grid(row=1, column=4, sticky="ew", padx=(0, 14))

        tk.Label(config, textvariable=self._preset_desc, justify="left", wraplength=820, bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, font=("Segoe UI", 10)).grid(row=2, column=0, columnspan=5, sticky="ew", padx=14, pady=(0, 12))

        body = tk.Frame(self, bg=COR_BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        self.slots_card = UICard(body, bg=COR_BG_SECUNDARIO, border=COR_BORDA)
        self.slots_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.summary_card = UICard(body, bg=COR_BG_SECUNDARIO, border=COR_BORDA)
        self.summary_card.grid(row=0, column=1, sticky="nsew")

        actions = tk.Frame(self, bg=COR_BG)
        actions.pack(fill="x", padx=24, pady=(0, 24))
        make_primary_button(actions, "Iniciar Horda", self.iniciar_horda, bg=COR_SUCCESS, fg="#07131f", padx=18, pady=10).pack(side="left")
        make_secondary_button(actions, "Atualizar Lista", self._rebuild_slots).pack(side="left", padx=8)

        self._rebuild_slots()
        self._update_preset_info()

    def _on_data_changed(self, _data=None):
        self._rebuild_slots()

    def _rebuild_slots(self):
        for widget in self.slots_card.winfo_children():
            widget.destroy()
        for widget in self.summary_card.winfo_children():
            widget.destroy()

        nomes = [p.nome for p in self.state.characters]
        self.slot_vars = []
        tk.Label(self.slots_card, text="Expedicao", font=("Bahnschrift SemiBold", 20), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(self.slots_card, text="Escolha quem vai tentar sobreviver as ondas.", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=16, pady=(0, 12))

        for idx in range(self.var_slots.get()):
            row = tk.Frame(self.slots_card, bg=COR_BG_SECUNDARIO)
            row.pack(fill="x", padx=16, pady=6)
            tk.Label(row, text=f"Slot {idx + 1}", width=8, anchor="w", bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, font=("Segoe UI", 10, "bold")).pack(side="left")
            var = tk.StringVar(value=nomes[idx] if idx < len(nomes) else "")
            combo = ttk.Combobox(row, textvariable=var, values=nomes, state="readonly")
            combo.pack(side="left", fill="x", expand=True)
            combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_summary())
            self.slot_vars.append(var)

        self._refresh_summary()

    def _update_preset_info(self):
        preset = self.horde_presets.get(self.var_preset.get()) or {}
        waves = preset.get("waves", [])
        total_spawns = sum(int(entry.get("quantidade", 0) or 0) for wave in waves for entry in wave.get("entries", []))
        descricao = (
            f"{preset.get('nome', 'Preset sem nome')}  |  Waves: {len(waves)}  |  Spawns planejados: {total_spawns}\n"
            f"Delay entre waves: {preset.get('inter_wave_delay', 0)}s  |  Spawn interval: {preset.get('spawn_interval', 0)}s"
        )
        self._preset_desc.set(descricao)
        if preset.get("cenario_padrao") and self.var_cenario.get() not in ARENAS:
            self.var_cenario.set(preset["cenario_padrao"])
        self._refresh_summary()

    def _refresh_summary(self):
        for widget in self.summary_card.winfo_children():
            widget.destroy()

        tk.Label(self.summary_card, text="Resumo", font=("Bahnschrift SemiBold", 20), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", padx=16, pady=(16, 6))
        membros = [var.get() for var in self.slot_vars if var.get()]
        preset = self.horde_presets.get(self.var_preset.get()) or {}
        info = [
            f"Lutadores: {len(membros)}",
            f"Arena: {self.var_cenario.get()}",
            f"Preset: {preset.get('nome', self.var_preset.get() or '-')}",
            f"Waves: {len(preset.get('waves', []))}",
        ]
        for line in info:
            tk.Label(self.summary_card, text=line, font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", padx=16, pady=4)

        if membros:
            tk.Label(self.summary_card, text="Expedicao ativa", font=("Segoe UI", 10, "bold"), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO).pack(anchor="w", padx=16, pady=(12, 4))
            for nome in membros:
                tk.Label(self.summary_card, text=f"- {nome}", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=24, pady=2)
        else:
            tk.Label(self.summary_card, text="Nenhum lutador selecionado.", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM).pack(anchor="w", padx=16, pady=8)

    def iniciar_horda(self):
        membros = [var.get() for var in self.slot_vars if var.get()]
        if not membros:
            messagebox.showwarning("Modo Horda", "Selecione pelo menos um lutador para iniciar a horda.")
            return
        if len(set(membros)) != len(membros):
            messagebox.showwarning("Modo Horda", "Nao repita o mesmo lutador em dois slots.")
            return

        preset = self.horde_presets.get(self.var_preset.get())
        if not preset:
            messagebox.showwarning("Modo Horda", "Selecione um preset de ondas valido.")
            return

        config = build_horde_match_config(
            [{"team_id": 0, "label": "Expedicao", "members": membros}],
            preset,
            cenario=self.var_cenario.get() or preset.get("cenario_padrao", "Campo de Batalha"),
        )
        self.state.set_match_config(config)
        sim = simulacao.Simulador()
        sim.run()

