"""
Explorador de arquétipos compostos.

Permite inspecionar combinacoes de:
- classe
- personalidade
- arma
- ate 3 skills do personagem

A arvore e lazy para representar todas as combinacoes sem travar a UI.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ia.composite_archetypes import (
    LISTA_CLASSES,
    LISTA_PERSONALIDADES,
    construir_arvore_arquetipo,
    inferir_arquetipo_composto,
)
from interface.headless_summary import load_latest_headless_archetype_focus, load_latest_headless_balance_focus
from nucleo.skills import listar_skills_filtradas
from interface.theme import COR_ACCENT, COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_SUCCESS, COR_TEXTO, COR_TEXTO_DIM, COR_WARNING
from interface.ui_components import (
    EmptyState,
    ScrollableWorkspace,
    UICard,
    build_labeled_combobox,
    build_page_header,
    build_section_header,
    make_primary_button,
    make_secondary_button,
    render_stat_grid,
)


def resolve_archetype_review_targets(area):
    area_norm = str(area or "").strip().lower()
    mapping = {
        "arma": {
            "targets": ["arma"],
            "message": "Revise familia, subtipo, alcance, ritmo e leitura visual da arma antes de mexer no resto do pacote.",
        },
        "skill": {
            "targets": ["skill_1", "skill_2", "skill_3"],
            "message": "Revise o kit magico do personagem, principalmente sobreposicao de funcao, burst, custo e cobertura tática.",
        },
        "papel": {
            "targets": ["classe", "arma", "skill_1", "skill_2", "skill_3"],
            "message": "Revise o pacote tatico inteiro para garantir que ele cumpre o papel certo e nao invade funcoes demais.",
        },
        "ia": {
            "targets": ["personalidade", "classe", "arma"],
            "message": "Revise personalidade, abertura e distancia preferida. O problema parece mais de decisao do que de numero puro.",
        },
        "composicao": {
            "targets": ["classe", "personalidade", "arma", "skill_1", "skill_2", "skill_3"],
            "message": "Revise como esse pacote entra no time. O desvio parece de sinergia ou redundancia de funcao.",
        },
        "geral": {
            "targets": ["classe", "personalidade", "arma", "skill_1", "skill_2", "skill_3"],
            "message": "Revise o conjunto inteiro e veja onde a identidade do pacote comeca a quebrar.",
        },
    }
    return mapping.get(area_norm, mapping["geral"])


class TelaArquetipos(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_BG)
        self.controller = controller
        self._tree_meta = {}
        self._ultimo_perfil = None
        self._ultimo_foco_balance = {}
        self._field_wraps = {}
        self._skill_names = []
        self._weapon_names = []
        self._character_names = []

        self.var_personagem = tk.StringVar(value="")
        self.var_classe = tk.StringVar(value=LISTA_CLASSES[0] if LISTA_CLASSES else "")
        self.var_personalidade = tk.StringVar(value=LISTA_PERSONALIDADES[0] if LISTA_PERSONALIDADES else "")
        self.var_arma = tk.StringVar(value="Nenhuma")
        self.var_skill_1 = tk.StringVar(value="Nenhuma")
        self.var_skill_2 = tk.StringVar(value="Nenhuma")
        self.var_skill_3 = tk.StringVar(value="Nenhuma")

        self._setup_ui()
        self.atualizar_dados()

    def _setup_ui(self):
        build_page_header(
            self,
            "ARVORE DE ARQUETIPOS",
            "Veja o pacote completo de decisao da IA por classe, personalidade, arma e skills do campeao.",
            lambda: self.controller.show_frame("MenuPrincipal"),
            button_bg=COR_ACCENT,
            button_fg=COR_TEXTO,
            back_text="Voltar",
        )

        workspace = ScrollableWorkspace(self, bg=COR_BG, xscroll=True, yscroll=True)
        workspace.pack(fill="both", expand=True, padx=14, pady=10)
        main = workspace.content
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

        self.frame_arvore = UICard(main, bg=COR_BG_SECUNDARIO, border="#284564")
        self.frame_detail = tk.Frame(main, bg=COR_BG)
        paned.add(self.frame_arvore, minsize=340, stretch="always")
        paned.add(self.frame_detail, minsize=620, stretch="always")
        self.after(100, lambda: paned.sash_place(0, 410, 0))

        self._build_tree_panel()
        self._build_detail_panel()

    def _build_tree_panel(self):
        build_section_header(
            self.frame_arvore,
            "Catalogo Total",
            "Expanda a arvore por classe, personalidade, arma e skills. A arvore e lazy para suportar todas as combinacoes.",
            bg=COR_BG_SECUNDARIO,
            accent=COR_ACCENT,
        )

        top = tk.Frame(self.frame_arvore, bg=COR_BG_SECUNDARIO)
        top.pack(fill="x", padx=12, pady=(4, 8))
        make_secondary_button(top, "Recarregar Arvore", self._seed_tree, bg=COR_BG).pack(side="left")
        make_secondary_button(top, "Usar Seletores", self._analisar_manual, bg=COR_BG).pack(side="left", padx=8)
        make_primary_button(top, "Usar Alvo Headless", lambda: self.aplicar_alvo_headless(silencioso=False), bg=COR_SUCCESS, fg="#07131f").pack(side="right")

        tree_wrap = tk.Frame(self.frame_arvore, bg=COR_BG_SECUNDARIO)
        tree_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        self.tree_catalogo = ttk.Treeview(tree_wrap, show="tree")
        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree_catalogo.yview)
        self.tree_catalogo.configure(yscrollcommand=scroll.set)
        self.tree_catalogo.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree_catalogo.bind("<<TreeviewOpen>>", self._on_tree_open)
        self.tree_catalogo.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _build_detail_panel(self):
        top = UICard(self.frame_detail, bg=COR_BG_SECUNDARIO, border="#284564")
        top.pack(fill="x", pady=(0, 10))
        build_section_header(
            top,
            "Montador De Pacote",
            "Monte uma combinacao manual, carregue um personagem pronto ou clique em uma folha da arvore.",
            bg=COR_BG_SECUNDARIO,
            accent=COR_SUCCESS,
        )

        form = tk.Frame(top, bg=COR_BG_SECUNDARIO)
        form.pack(fill="x", padx=14, pady=(4, 12))

        row0 = tk.Frame(form, bg=COR_BG_SECUNDARIO)
        row0.pack(fill="x")
        wrap_char, self.combo_personagem = build_labeled_combobox(
            row0,
            "Personagem existente",
            values=[],
            current="",
            bg=COR_BG_SECUNDARIO,
        )
        wrap_char.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._field_wraps["personagem"] = wrap_char
        make_secondary_button(row0, "Carregar Personagem", self._carregar_personagem, bg=COR_BG).pack(side="left", pady=(18, 0))

        row1 = tk.Frame(form, bg=COR_BG_SECUNDARIO)
        row1.pack(fill="x", pady=(8, 0))
        wrap_classe, self.combo_classe = build_labeled_combobox(
            row1, "Classe", values=list(LISTA_CLASSES), current=self.var_classe.get(), bg=COR_BG_SECUNDARIO
        )
        wrap_classe.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._field_wraps["classe"] = wrap_classe
        wrap_pers, self.combo_personalidade = build_labeled_combobox(
            row1, "Personalidade", values=list(LISTA_PERSONALIDADES), current=self.var_personalidade.get(), bg=COR_BG_SECUNDARIO
        )
        wrap_pers.pack(side="left", fill="x", expand=True, padx=6)
        self._field_wraps["personalidade"] = wrap_pers
        wrap_arma, self.combo_arma = build_labeled_combobox(
            row1, "Arma", values=["Nenhuma"], current="Nenhuma", bg=COR_BG_SECUNDARIO
        )
        wrap_arma.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self._field_wraps["arma"] = wrap_arma

        row2 = tk.Frame(form, bg=COR_BG_SECUNDARIO)
        row2.pack(fill="x", pady=(8, 0))
        wrap_s1, self.combo_skill_1 = build_labeled_combobox(
            row2, "Skill 1", values=["Nenhuma"], current="Nenhuma", bg=COR_BG_SECUNDARIO
        )
        wrap_s1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._field_wraps["skill_1"] = wrap_s1
        wrap_s2, self.combo_skill_2 = build_labeled_combobox(
            row2, "Skill 2", values=["Nenhuma"], current="Nenhuma", bg=COR_BG_SECUNDARIO
        )
        wrap_s2.pack(side="left", fill="x", expand=True, padx=6)
        self._field_wraps["skill_2"] = wrap_s2
        wrap_s3, self.combo_skill_3 = build_labeled_combobox(
            row2, "Skill 3", values=["Nenhuma"], current="Nenhuma", bg=COR_BG_SECUNDARIO
        )
        wrap_s3.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self._field_wraps["skill_3"] = wrap_s3

        actions = tk.Frame(form, bg=COR_BG_SECUNDARIO)
        actions.pack(fill="x", pady=(10, 0))
        make_primary_button(actions, "Analisar Conjunto", self._analisar_manual, bg=COR_ACCENT, fg="#07131f").pack(side="left")
        make_secondary_button(actions, "Limpar Skills", self._limpar_skills, bg=COR_BG).pack(side="left", padx=8)
        make_secondary_button(actions, "Aplicar Preset De Revisao", self._aplicar_preset_revisao_headless, bg=COR_BG).pack(side="left", padx=8)
        make_secondary_button(actions, "Limpar Preset", self._limpar_preset_revisao, bg=COR_BG).pack(side="left", padx=8)

        self.card_revisao = UICard(self.frame_detail, bg=COR_BG_SECUNDARIO, border="#284564")
        self.card_revisao.pack(fill="x", pady=(0, 10))
        build_section_header(
            self.card_revisao,
            "Preset De Revisao",
            "Transforma o foco do headless em campos concretos para revisar neste montador.",
            bg=COR_BG_SECUNDARIO,
            accent=COR_WARNING,
        )
        self.lbl_preset = tk.Label(
            self.card_revisao,
            text="Nenhum preset aplicado.",
            font=("Segoe UI", 10),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=900,
        )
        self.lbl_preset.pack(fill="x", padx=14, pady=(4, 12))

        self.card_resumo = UICard(self.frame_detail, bg=COR_BG_SECUNDARIO, border="#284564")
        self.card_resumo.pack(fill="x", pady=(0, 10))
        self.lbl_nome = tk.Label(
            self.card_resumo,
            text="Nenhum conjunto analisado",
            font=("Bahnschrift SemiBold", 22),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
        )
        self.lbl_nome.pack(fill="x", padx=14, pady=(14, 4))
        self.lbl_resumo = tk.Label(
            self.card_resumo,
            text="Selecione uma combinacao ou carregue um personagem para inferir o arquétipo composto.",
            font=("Segoe UI", 10),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=880,
        )
        self.lbl_resumo.pack(fill="x", padx=14, pady=(0, 12))
        self.frame_stats = tk.Frame(self.card_resumo, bg=COR_BG_SECUNDARIO)
        self.frame_stats.pack(fill="x", padx=10, pady=(0, 12))

        lower = tk.Frame(self.frame_detail, bg=COR_BG)
        lower.pack(fill="both", expand=True)
        lower.grid_columnconfigure(0, weight=3)
        lower.grid_columnconfigure(1, weight=2)
        lower.grid_rowconfigure(0, weight=1)

        card_tree = UICard(lower, bg=COR_BG_SECUNDARIO, border="#284564")
        card_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        build_section_header(
            card_tree,
            "Arvore De Decisao",
            "Resumo navegavel do nucleo, leitura tatica, padrao de decisao e alertas.",
            bg=COR_BG_SECUNDARIO,
            accent=COR_ACCENT,
        )
        tree_wrap = tk.Frame(card_tree, bg=COR_BG_SECUNDARIO)
        tree_wrap.pack(fill="both", expand=True, padx=10, pady=(4, 12))
        self.tree_detalhes = ttk.Treeview(tree_wrap, show="tree")
        detail_scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree_detalhes.yview)
        self.tree_detalhes.configure(yscrollcommand=detail_scroll.set)
        self.tree_detalhes.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")

        card_side = UICard(lower, bg=COR_BG_SECUNDARIO, border="#284564")
        card_side.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        build_section_header(
            card_side,
            "Leitura De Balanceamento",
            "Onde esse pacote tende a brilhar, quebrar ou puxar a IA para um comportamento especifico.",
            bg=COR_BG_SECUNDARIO,
            accent=COR_SUCCESS,
        )
        self.lbl_roles = tk.Label(card_side, text="Papeis: -", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, anchor="w", justify="left", wraplength=340)
        self.lbl_roles.pack(fill="x", padx=14, pady=(6, 6))
        self.lbl_pacote = tk.Label(card_side, text="Pacote oficial: -", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_SUCCESS, anchor="w", justify="left", wraplength=340)
        self.lbl_pacote.pack(fill="x", padx=14, pady=4)
        self.lbl_forcas = tk.Label(card_side, text="Forcas: -", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, anchor="w", justify="left", wraplength=340)
        self.lbl_forcas.pack(fill="x", padx=14, pady=4)
        self.lbl_fraquezas = tk.Label(card_side, text="Fraquezas: -", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, anchor="w", justify="left", wraplength=340)
        self.lbl_fraquezas.pack(fill="x", padx=14, pady=4)
        self.lbl_alertas = tk.Label(card_side, text="Alertas: -", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, anchor="w", justify="left", wraplength=340)
        self.lbl_alertas.pack(fill="x", padx=14, pady=4)
        self.lbl_headless = tk.Label(card_side, text="Direcao headless: -", font=("Segoe UI", 10), bg=COR_BG_SECUNDARIO, fg=COR_WARNING, anchor="w", justify="left", wraplength=340)
        self.lbl_headless.pack(fill="x", padx=14, pady=4)
        self.lbl_eixos = tk.Label(card_side, text="Eixos: -", font=("Consolas", 9), bg=COR_BG_SECUNDARIO, fg=COR_TEXTO_DIM, anchor="w", justify="left", wraplength=340)
        self.lbl_eixos.pack(fill="x", padx=14, pady=(8, 14))

    def atualizar_dados(self):
        self._skill_names = list(listar_skills_filtradas(incluir_nenhuma=False))
        self._ultimo_foco_balance = load_latest_headless_balance_focus()
        self._weapon_names = sorted({arma.nome for arma in (self.controller.lista_armas or [])})
        self._character_names = sorted({p.nome for p in (self.controller.lista_personagens or [])})

        self.combo_personagem["values"] = self._character_names
        self.combo_arma["values"] = ["Nenhuma"] + self._weapon_names
        skill_values = ["Nenhuma"] + self._skill_names
        self.combo_skill_1["values"] = skill_values
        self.combo_skill_2["values"] = skill_values
        self.combo_skill_3["values"] = skill_values

        if self.combo_arma.get() not in self.combo_arma["values"]:
            self.combo_arma.set("Nenhuma")
        for combo in (self.combo_skill_1, self.combo_skill_2, self.combo_skill_3):
            if combo.get() not in combo["values"]:
                combo.set("Nenhuma")

        self._seed_tree()
        self._limpar_preset_revisao()

    def aplicar_alvo_headless(self, silencioso=False):
        foco = load_latest_headless_archetype_focus()
        if not foco.get("found"):
            if not silencioso:
                messagebox.showinfo(
                    "Arquetipos",
                    "Ainda nao existe foco de arquetipo vindo do headless.\n\nRode o harness tatico primeiro.",
                )
            return False

        personagem = self._resolver_personagem_foco(
            str(foco.get("personagem_nome", "") or ""),
            str(foco.get("pacote_foco", "") or ""),
        )
        if personagem is None:
            if not silencioso:
                pacote = str(foco.get("pacote_nome", "") or foco.get("pacote_foco", "") or "pacote dominante")
                messagebox.showwarning(
                    "Arquetipos",
                    f"Nao encontrei um personagem do roster atual para abrir o foco em {pacote}.",
                )
            return False

        self.combo_personagem.set(personagem.nome)
        self._carregar_personagem()
        return True

    def _resolver_personagem_foco(self, nome_personagem, pacote_foco):
        personagens = list(self.controller.lista_personagens or [])
        if nome_personagem:
            personagem = next((p for p in personagens if p.nome == nome_personagem), None)
            if personagem is not None:
                return personagem

        if not pacote_foco:
            return None

        melhor = None
        melhor_score = -1.0
        for personagem in personagens:
            arma = self._resolve_weapon(getattr(personagem, "nome_arma", "") or "")
            perfil = inferir_arquetipo_composto(
                getattr(personagem, "classe", ""),
                getattr(personagem, "personalidade", ""),
                arma,
                getattr(personagem, "skills_personagem", []) or [],
            )
            pacote = perfil.get("pacote_referencia") or {}
            if str(pacote.get("id", "") or "") != pacote_foco:
                continue
            score = float(((perfil.get("papel_primario") or {}).get("score", 0.0) or 0.0))
            if score > melhor_score:
                melhor = personagem
                melhor_score = score
        return melhor

    def _seed_tree(self):
        self.tree_catalogo.delete(*self.tree_catalogo.get_children())
        self._tree_meta.clear()
        for classe in LISTA_CLASSES:
            iid = self.tree_catalogo.insert("", "end", text=classe, open=False)
            self._tree_meta[iid] = {"level": "classe", "classe": classe}
            self._add_lazy_child(iid)

    def _add_lazy_child(self, parent_id):
        child = self.tree_catalogo.insert(parent_id, "end", text="Carregando...")
        self._tree_meta[child] = {"level": "lazy"}

    def _on_tree_open(self, _event=None):
        node = self.tree_catalogo.focus()
        if not node:
            return
        children = self.tree_catalogo.get_children(node)
        if len(children) == 1 and self._tree_meta.get(children[0], {}).get("level") == "lazy":
            for child in children:
                self.tree_catalogo.delete(child)
                self._tree_meta.pop(child, None)
            self._populate_tree_node(node)

    def _populate_tree_node(self, node):
        meta = self._tree_meta.get(node, {})
        level = meta.get("level")
        if level == "classe":
            for personalidade in LISTA_PERSONALIDADES:
                iid = self.tree_catalogo.insert(node, "end", text=personalidade)
                self._tree_meta[iid] = {
                    "level": "personalidade",
                    "classe": meta["classe"],
                    "personalidade": personalidade,
                }
                self._add_lazy_child(iid)
            return

        if level == "personalidade":
            if not self._weapon_names:
                iid = self.tree_catalogo.insert(node, "end", text="Nenhuma arma cadastrada")
                self._tree_meta[iid] = {"level": "vazio"}
                return
            for weapon_name in self._weapon_names:
                iid = self.tree_catalogo.insert(node, "end", text=weapon_name)
                self._tree_meta[iid] = {
                    "level": "arma",
                    "classe": meta["classe"],
                    "personalidade": meta["personalidade"],
                    "arma": weapon_name,
                    "skills": [],
                }
                self._add_lazy_child(iid)
            return

        if level in {"arma", "skill1", "skill2"}:
            current_skills = list(meta.get("skills", []))
            remaining = [nome for nome in self._skill_names if nome not in current_skills]
            options = ["Nenhuma"] + remaining
            next_level = {"arma": "skill1", "skill1": "skill2", "skill2": "skill3"}[level]
            label_idx = len(current_skills) + 1
            for nome_skill in options:
                new_skills = list(current_skills)
                if nome_skill != "Nenhuma":
                    new_skills.append(nome_skill)
                label = f"Skill {label_idx}: {nome_skill}"
                iid = self.tree_catalogo.insert(node, "end", text=label)
                self._tree_meta[iid] = {
                    "level": next_level,
                    "classe": meta["classe"],
                    "personalidade": meta["personalidade"],
                    "arma": meta["arma"],
                    "skills": new_skills,
                }
                if next_level != "skill3":
                    self._add_lazy_child(iid)

    def _on_tree_select(self, _event=None):
        node = self.tree_catalogo.focus()
        meta = self._tree_meta.get(node, {})
        if meta.get("level") not in {"arma", "skill1", "skill2", "skill3"}:
            return
        self._set_manual_selection(
            meta.get("classe"),
            meta.get("personalidade"),
            meta.get("arma"),
            meta.get("skills", []),
        )
        self._analisar_manual()

    def _set_manual_selection(self, classe, personalidade, arma, skills):
        if classe:
            self.combo_classe.set(classe)
        if personalidade:
            self.combo_personalidade.set(personalidade)
        if arma and arma in (self.combo_arma["values"] or []):
            self.combo_arma.set(arma)
        else:
            self.combo_arma.set("Nenhuma")

        nomes = list(skills or [])[:3]
        combos = [self.combo_skill_1, self.combo_skill_2, self.combo_skill_3]
        for idx, combo in enumerate(combos):
            combo.set(nomes[idx] if idx < len(nomes) else "Nenhuma")

    def _resolve_weapon(self, weapon_name):
        if not weapon_name or weapon_name == "Nenhuma":
            return None
        return next((arma for arma in (self.controller.lista_armas or []) if arma.nome == weapon_name), None)

    def _skills_from_form(self):
        skills = []
        for combo in (self.combo_skill_1, self.combo_skill_2, self.combo_skill_3):
            nome = combo.get().strip()
            if not nome or nome == "Nenhuma":
                continue
            if nome not in skills:
                skills.append(nome)
        return skills

    def _carregar_personagem(self):
        nome = self.combo_personagem.get().strip()
        personagem = next((p for p in (self.controller.lista_personagens or []) if p.nome == nome), None)
        if personagem is None:
            return
        skills = []
        for item in getattr(personagem, "skills_personagem", []) or []:
            if isinstance(item, dict):
                nome_skill = str(item.get("nome", "") or "").strip()
            else:
                nome_skill = str(item or "").strip()
            if nome_skill:
                skills.append(nome_skill)

        self._set_manual_selection(
            getattr(personagem, "classe", LISTA_CLASSES[0] if LISTA_CLASSES else ""),
            getattr(personagem, "personalidade", LISTA_PERSONALIDADES[0] if LISTA_PERSONALIDADES else ""),
            getattr(personagem, "nome_arma", "") or "Nenhuma",
            skills,
        )
        self._analisar_manual()

    def _limpar_skills(self):
        for combo in (self.combo_skill_1, self.combo_skill_2, self.combo_skill_3):
            combo.set("Nenhuma")
        self._analisar_manual()

    def _set_wrap_highlight(self, key, active):
        wrap = self._field_wraps.get(key)
        if wrap is None:
            return
        bg = "#3f3412" if active else COR_BG_SECUNDARIO
        fg = COR_WARNING if active else COR_TEXTO
        wrap.configure(bg=bg)
        for child in wrap.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=bg, fg=fg)

    def _limpar_preset_revisao(self):
        for key in self._field_wraps:
            self._set_wrap_highlight(key, False)
        if hasattr(self, "lbl_preset"):
            self.lbl_preset.config(text="Nenhum preset aplicado.", fg=COR_TEXTO_DIM)

    def _aplicar_preset_revisao_headless(self):
        foco = dict(self._ultimo_foco_balance or {})
        self._limpar_preset_revisao()
        if not foco.get("found"):
            self.lbl_preset.config(
                text="Ainda nao existe foco de balanceamento vindo do headless. Rode o harness tatico primeiro.",
                fg=COR_TEXTO_DIM,
            )
            return

        preset = resolve_archetype_review_targets(foco.get("area", "geral"))
        targets = list(preset.get("targets", []) or [])
        for key in targets:
            self._set_wrap_highlight(key, True)

        combo_map = {
            "classe": self.combo_classe,
            "personalidade": self.combo_personalidade,
            "arma": self.combo_arma,
            "skill_1": self.combo_skill_1,
            "skill_2": self.combo_skill_2,
            "skill_3": self.combo_skill_3,
            "personagem": self.combo_personagem,
        }
        for key in targets:
            combo = combo_map.get(key)
            if combo is not None:
                try:
                    combo.focus_set()
                except Exception:
                    pass
                break

        area = foco.get("area_text", "Geral")
        alvo = foco.get("alvo_text", "") or area
        acao = str(foco.get("acao", "") or "").strip()
        motivo = str(foco.get("motivo", "") or "").strip()
        pacote = str(foco.get("pacote_foco", "") or "").strip()
        partes = [f"Preset ativo: revisar {area} -> {alvo}."]
        partes.append(str(preset.get("message", "") or ""))
        if pacote:
            partes.append(f"Pacote foco: {pacote}.")
        if acao:
            partes.append(f"Acao sugerida: {acao}.")
        if motivo:
            partes.append(f"Motivo: {motivo}.")
        self.lbl_preset.config(text=" ".join(partes), fg=COR_WARNING)

    def _analisar_manual(self):
        classe = self.combo_classe.get().strip()
        personalidade = self.combo_personalidade.get().strip()
        arma = self._resolve_weapon(self.combo_arma.get().strip())

        if not classe or not personalidade:
            self._render_empty_result("Escolha pelo menos classe e personalidade para inferir o pacote.")
            return

        perfil = inferir_arquetipo_composto(classe, personalidade, arma, self._skills_from_form())
        self._ultimo_perfil = perfil
        self._render_profile(perfil)

    def _render_empty_result(self, message):
        self.lbl_nome.config(text="Nenhum conjunto analisado")
        self.lbl_resumo.config(text=message)
        for widget in self.frame_stats.winfo_children():
            widget.destroy()
        self.tree_detalhes.delete(*self.tree_detalhes.get_children())
        self.lbl_roles.config(text="Papeis: -")
        self.lbl_pacote.config(text="Pacote oficial: -")
        self.lbl_forcas.config(text="Forcas: -")
        self.lbl_fraquezas.config(text="Fraquezas: -")
        self.lbl_alertas.config(text="Alertas: -")
        self.lbl_headless.config(text="Direcao headless: -")
        self.lbl_eixos.config(text="Eixos: -")

    def _render_profile(self, perfil):
        self.lbl_nome.config(text=perfil["nome_composto"])
        self.lbl_resumo.config(text=perfil["resumo"])

        for widget in self.frame_stats.winfo_children():
            widget.destroy()
        papel_sec = perfil["papel_secundario"]["nome"] if perfil["papel_secundario"] else "n/a"
        render_stat_grid(
            self.frame_stats,
            [
                ("Papel Primario", perfil["papel_primario"]["nome"]),
                ("Papel Secundario", papel_sec),
                ("Distancia", perfil["distancia_preferida"]),
                ("Postura", perfil["postura"]),
                ("Abertura", perfil["abertura_preferida"]),
                ("Familia", perfil["familia_arma"]),
            ],
            columns=3,
            bg=COR_BG_SECUNDARIO,
        )

        self.tree_detalhes.delete(*self.tree_detalhes.get_children())
        for bloco in construir_arvore_arquetipo(perfil):
            root = self.tree_detalhes.insert("", "end", text=bloco["titulo"], open=True)
            for filho in bloco["filhos"]:
                self.tree_detalhes.insert(root, "end", text=str(filho))

        top_scores = ", ".join(f"{item['nome']} ({item['score']:.1f})" for item in perfil.get("score_papeis", [])[:3]) or "-"
        forcas = ", ".join(perfil.get("forte_em", []) or []) or "-"
        fraquezas = ", ".join(perfil.get("fraco_em", []) or []) or "-"
        alertas = " | ".join(perfil.get("alertas_balanceamento", []) or ["Sem alertas imediatos"])
        eixos = ", ".join(f"{k}:{v:.2f}" for k, v in perfil.get("eixos", {}).items()) or "-"
        pacote = perfil.get("pacote_referencia") or {}
        pacote_texto = pacote.get("nome", "Sem referencia forte")
        if perfil.get("desvios_pacote"):
            pacote_texto = f"{pacote_texto} | desvios: {' | '.join(perfil['desvios_pacote'])}"

        foco_headless_texto = "Sem foco headless ativo."
        foco = dict(self._ultimo_foco_balance or {})
        if foco.get("found"):
            area = str(foco.get("area_text", "") or "Geral")
            alvo = str(foco.get("alvo_text", "") or area)
            pacote_foco = str(foco.get("pacote_foco", "") or "")
            pacote_atual = str((pacote.get("id", "") or ""))
            marcador = "ALINHADO" if pacote_foco and pacote_atual and pacote_foco == pacote_atual else "REFERENCIA"
            partes = [f"{marcador}: revisar {area} -> {alvo}"]
            if foco.get("acao"):
                partes.append(str(foco["acao"]))
            if foco.get("motivo"):
                partes.append(f"Motivo: {foco['motivo']}")
            foco_headless_texto = " | ".join(partes)

        self.lbl_roles.config(text=f"Papeis: {top_scores}")
        self.lbl_pacote.config(text=f"Pacote oficial: {pacote_texto}")
        self.lbl_forcas.config(text=f"Forcas: {forcas}")
        self.lbl_fraquezas.config(text=f"Fraquezas: {fraquezas}")
        self.lbl_alertas.config(text=f"Alertas: {alertas}")
        self.lbl_headless.config(text=f"Direcao headless: {foco_headless_texto}")
        self.lbl_eixos.config(text=f"Eixos: {eixos}")
