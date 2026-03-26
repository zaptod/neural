import tkinter as tk
from tkinter import ttk

from interface.theme import (
    COR_ACCENT,
    COR_BG,
    COR_BG_CARD,
    COR_BG_CARD_SOFT,
    COR_BG_SECUNDARIO,
    COR_BORDA,
    COR_HEADER,
    COR_SUCCESS,
    COR_TEXTO,
    COR_TEXTO_DIM,
    COR_TEXTO_SUB,
    COR_WARNING,
)


def make_primary_button(parent, text, command, *, bg=COR_ACCENT, fg="#07131f", **kwargs):
    font = kwargs.pop("font", ("Segoe UI", 10, "bold"))
    padx = kwargs.pop("padx", 14)
    pady = kwargs.pop("pady", 9)
    activebackground = kwargs.pop("activebackground", bg)
    activeforeground = kwargs.pop("activeforeground", fg)
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=font,
        bg=bg,
        fg=fg,
        activebackground=activebackground,
        activeforeground=activeforeground,
        relief="flat",
        bd=0,
        padx=padx,
        pady=pady,
        cursor="hand2",
        **kwargs,
    )


def make_secondary_button(parent, text, command, *, bg=COR_BG_SECUNDARIO, fg=COR_TEXTO, **kwargs):
    font = kwargs.pop("font", ("Segoe UI", 10, "bold"))
    padx = kwargs.pop("padx", 14)
    pady = kwargs.pop("pady", 9)
    activebackground = kwargs.pop("activebackground", bg)
    activeforeground = kwargs.pop("activeforeground", fg)
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=font,
        bg=bg,
        fg=fg,
        activebackground=activebackground,
        activeforeground=activeforeground,
        relief="flat",
        bd=0,
        padx=padx,
        pady=pady,
        cursor="hand2",
        **kwargs,
    )


class UICard(tk.Frame):
    def __init__(self, parent, *, bg=COR_BG_CARD, border=COR_BORDA, padx=0, pady=0, **kwargs):
        super().__init__(
            parent,
            bg=bg,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
            bd=0,
            padx=padx,
            pady=pady,
            **kwargs,
        )


class ScrollableWorkspace(tk.Frame):
    def __init__(self, parent, *, bg=COR_BG, xscroll=True, yscroll=True, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._xscroll = xscroll
        self._yscroll = yscroll

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.v_scroll = None
        self.h_scroll = None
        if yscroll:
            self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.v_scroll.pack(side="right", fill="y")
            self.canvas.configure(yscrollcommand=self.v_scroll.set)
        if xscroll:
            self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
            self.h_scroll.pack(side="bottom", fill="x")
            self.canvas.configure(xscrollcommand=self.h_scroll.set)

        self.content = tk.Frame(self.canvas, bg=bg)
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_content_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        if not self._xscroll and event is not None:
            self.canvas.itemconfigure(self._window_id, width=event.width)
        if not self._yscroll and event is not None:
            self.canvas.itemconfigure(self._window_id, height=event.height)

    def _bind_mousewheel(self, _event=None):
        if self._yscroll:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Shift-MouseWheel>")

    def _on_mousewheel(self, event):
        if self._yscroll:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        if self._xscroll:
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


class InlineFeedbackBar(UICard):
    def __init__(self, parent, *, bg=COR_BG, border=COR_BORDA, **kwargs):
        super().__init__(parent, bg=bg, border=border, padx=10, pady=8, **kwargs)
        self._label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 9),
            bg=bg,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
        )
        self._label.pack(fill="x")
        self.set_message("Pronto para editar o catalogo atual.", tone="info")

    def set_message(self, message, *, tone="info"):
        palette = {
            "info": ("#1d3557", COR_TEXTO_DIM),
            "success": ("#0f3d2e", COR_SUCCESS),
            "warning": ("#4d3a12", "#f5c451"),
            "error": ("#4f1f27", "#ff8b8b"),
        }
        bg, fg = palette.get(tone, palette["info"])
        self.configure(bg=bg, highlightbackground=fg, highlightcolor=fg)
        self._label.configure(text=message, bg=bg, fg=fg)


def build_page_header(
    parent,
    title,
    subtitle,
    back_command,
    *,
    back_text="Voltar",
    bg=COR_HEADER,
    button_bg=COR_BG_SECUNDARIO,
    button_fg=COR_TEXTO,
    height=88,
):
    header = tk.Frame(parent, bg=bg, height=height)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    make_secondary_button(
        header,
        back_text,
        back_command,
        bg=button_bg,
        fg=button_fg,
        padx=16,
        pady=8,
    ).pack(side="left", padx=16, pady=20)

    title_wrap = tk.Frame(header, bg=bg)
    title_wrap.pack(side="left", fill="both", expand=True, pady=12)

    tk.Label(
        title_wrap,
        text=title,
        font=("Bahnschrift SemiBold", 24),
        bg=bg,
        fg=COR_TEXTO,
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        title_wrap,
        text=subtitle,
        font=("Segoe UI", 10),
        bg=bg,
        fg=COR_TEXTO_SUB,
        anchor="w",
    ).pack(fill="x", pady=(2, 0))

    right_slot = tk.Frame(header, bg=bg)
    right_slot.pack(side="right", padx=18, pady=12)
    return header, title_wrap, right_slot


def build_section_header(parent, title, subtitle, *, bg=COR_BG, accent=COR_ACCENT):
    wrap = tk.Frame(parent, bg=bg)
    wrap.pack(fill="x", padx=10, pady=(8, 4))

    tk.Frame(wrap, bg=accent, width=48, height=5).pack(anchor="w")
    tk.Label(
        wrap,
        text=title,
        font=("Bahnschrift SemiBold", 18),
        bg=bg,
        fg=COR_TEXTO,
        anchor="w",
    ).pack(fill="x", pady=(10, 2))
    tk.Label(
        wrap,
        text=subtitle,
        font=("Segoe UI", 9),
        bg=bg,
        fg=COR_TEXTO_DIM,
        anchor="w",
    ).pack(fill="x")
    return wrap


def build_labeled_entry(
    parent,
    label,
    *,
    value="",
    help_text=None,
    bg=COR_BG_SECUNDARIO,
    entry_bg=COR_BG,
    entry_fg=COR_TEXTO,
    label_fg=COR_TEXTO,
    help_fg=COR_TEXTO_DIM,
    font=("Arial", 12),
    label_font=("Arial", 10),
    help_font=("Arial", 9),
    entry_kwargs=None,
):
    entry_kwargs = entry_kwargs or {}
    frame = tk.Frame(parent, bg=bg)
    frame.pack(fill="x", pady=(0, 15))

    if label:
        tk.Label(frame, text=label, font=label_font, bg=bg, fg=label_fg).pack(anchor="w")
    if help_text:
        tk.Label(frame, text=help_text, font=help_font, bg=bg, fg=help_fg, anchor="w", justify="left", wraplength=420).pack(anchor="w", pady=(0, 5))

    entry = tk.Entry(
        frame,
        font=font,
        bg=entry_bg,
        fg=entry_fg,
        insertbackground=entry_fg,
        **entry_kwargs,
    )
    entry.pack(fill="x", pady=5)
    if value:
        entry.insert(0, value)
    return frame, entry


def build_labeled_combobox(
    parent,
    label,
    *,
    values,
    current=None,
    on_select=None,
    bg=COR_BG_SECUNDARIO,
    label_fg=COR_TEXTO,
    combo_font=("Arial", 11),
    label_font=("Arial", 10, "bold"),
):
    frame = tk.Frame(parent, bg=bg)
    frame.pack(fill="x", pady=(0, 10))
    if label:
        tk.Label(frame, text=label, font=label_font, bg=bg, fg=label_fg).pack(anchor="w", pady=(0, 4))

    combo = ttk.Combobox(frame, values=values, state="readonly", font=combo_font)
    combo.pack(fill="x", ipady=4)
    if current is not None:
        combo.set(current)
    if on_select:
        combo.bind("<<ComboboxSelected>>", on_select)
    return frame, combo


def build_slider_field(
    parent,
    title,
    description,
    *,
    from_,
    to,
    variable,
    command,
    min_text,
    max_text,
    value_text,
    value_fg=COR_SUCCESS,
    resolution=1.0,
    bg=COR_BG_SECUNDARIO,
):
    frame = tk.Frame(parent, bg=bg)
    frame.pack(fill="x", pady=10)

    if title:
        tk.Label(frame, text=title, font=("Arial", 10, "bold"), bg=bg, fg=COR_TEXTO).pack(anchor="w")
    if description:
        tk.Label(frame, text=description, font=("Arial", 9), bg=bg, fg=COR_TEXTO_DIM, wraplength=380, justify="left").pack(anchor="w", pady=(0, 5))

    slider_row = tk.Frame(frame, bg=bg)
    slider_row.pack(fill="x")
    tk.Label(slider_row, text=min_text, font=("Arial", 8), bg=bg, fg=COR_TEXTO_DIM).pack(side="left")

    slider = tk.Scale(
        slider_row,
        from_=from_,
        to=to,
        resolution=resolution,
        orient="horizontal",
        variable=variable,
        bg=bg,
        fg=COR_TEXTO,
        highlightthickness=0,
        troughcolor=COR_BG,
        activebackground=COR_ACCENT,
        command=command,
    )
    slider.pack(side="left", fill="x", expand=True, padx=5)
    tk.Label(slider_row, text=max_text, font=("Arial", 8), bg=bg, fg=COR_TEXTO_DIM).pack(side="left")

    value_label = tk.Label(frame, text=value_text, font=("Arial", 12, "bold"), bg=bg, fg=value_fg)
    value_label.pack(pady=5)
    return frame, slider, value_label


def build_radio_option_card(
    parent,
    *,
    text,
    value,
    variable,
    description="",
    command=None,
    accent_fg=COR_TEXTO,
    bg=COR_BG,
    select_bg=COR_BG_SECUNDARIO,
    meta_text=None,
    wraplength=180,
    relief="solid",
    borderwidth=1,
    padding=(10, 5),
):
    frame = tk.Frame(parent, bg=bg, bd=borderwidth, relief=relief)

    header = tk.Frame(frame, bg=bg)
    header.pack(fill="x", padx=padding[0], pady=(padding[1], 0))

    rb = tk.Radiobutton(
        header,
        text=text,
        variable=variable,
        value=value,
        font=("Arial", 10, "bold"),
        bg=bg,
        fg=accent_fg,
        selectcolor=select_bg,
        activebackground=bg,
        activeforeground=accent_fg,
        command=command,
        anchor="w",
        padx=0,
    )
    rb.pack(side="left", fill="x", expand=True)

    if meta_text:
        tk.Label(
            header,
            text=meta_text,
            font=("Arial", 8),
            bg=bg,
            fg=COR_TEXTO_DIM,
        ).pack(side="right")

    if description:
        tk.Label(
            frame,
            text=description,
            font=("Arial", 8),
            bg=bg,
            fg=COR_TEXTO_DIM,
            wraplength=wraplength,
            justify="left",
        ).pack(anchor="w", padx=padding[0], pady=(0, padding[1]))

    return frame, rb


class DashboardCard(UICard):
    def __init__(self, parent, accent, title, description, pills, primary_text, primary_command, secondary=None):
        super().__init__(parent, bg=COR_BG_SECUNDARIO, border=COR_BORDA)
        self.grid_propagate(False)
        self.configure(height=226)

        top = tk.Frame(self, bg=COR_BG_SECUNDARIO)
        top.pack(fill="x", padx=18, pady=(16, 10))

        tk.Frame(top, bg=accent, width=44, height=6).pack(anchor="w")
        tk.Label(
            top,
            text=title,
            font=("Bahnschrift SemiBold", 16),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO,
            anchor="w",
        ).pack(fill="x", pady=(10, 6))
        tk.Label(
            top,
            text=description,
            font=("Segoe UI", 10),
            bg=COR_BG_SECUNDARIO,
            fg=COR_TEXTO_DIM,
            justify="left",
            anchor="w",
            wraplength=320,
        ).pack(fill="x")

        pills_wrap = tk.Frame(self, bg=COR_BG_SECUNDARIO)
        pills_wrap.pack(fill="x", padx=18, pady=(2, 10))
        for pill in pills[:3]:
            chip = tk.Label(
                pills_wrap,
                text=pill,
                font=("Segoe UI", 9, "bold"),
                bg=COR_BG_CARD_SOFT,
                fg=accent,
                padx=10,
                pady=4,
            )
            chip.pack(side="left", padx=(0, 8), pady=2)

        tk.Frame(self, bg=COR_BG_SECUNDARIO).pack(fill="both", expand=True)

        footer = tk.Frame(self, bg=COR_BG_SECUNDARIO)
        footer.pack(fill="x", padx=18, pady=(0, 16))

        make_primary_button(
            footer,
            primary_text,
            primary_command,
            bg=accent,
        ).pack(side="left")

        if secondary:
            sec_text, sec_cmd = secondary
            make_secondary_button(footer, sec_text, sec_cmd).pack(side="left", padx=(10, 0))


class ResponsiveCardSection(tk.Frame):
    def __init__(self, parent, title, subtitle, cards):
        super().__init__(parent, bg=COR_BG)
        self.cards = cards
        self.card_widgets = []
        self.current_columns = None

        header = tk.Frame(self, bg=COR_BG)
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header,
            text=title,
            font=("Bahnschrift SemiBold", 20),
            bg=COR_BG,
            fg=COR_TEXTO,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text=subtitle,
            font=("Segoe UI", 10),
            bg=COR_BG,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(4, 0))

        self.grid_host = tk.Frame(self, bg=COR_BG)
        self.grid_host.pack(fill="x")

        for card_data in self.cards:
            self.card_widgets.append(DashboardCard(self.grid_host, **card_data))

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._relayout)

    def _compute_columns(self):
        width = max(self.winfo_width(), self.grid_host.winfo_width(), 1)
        if width < 760:
            return 1
        if width < 1180:
            return 2
        return 3

    def _on_resize(self, _event=None):
        self._relayout()

    def _relayout(self):
        columns = self._compute_columns()
        if columns == self.current_columns:
            return
        self.current_columns = columns

        for widget in self.card_widgets:
            widget.grid_forget()

        for idx in range(columns):
            self.grid_host.grid_columnconfigure(idx, weight=1, uniform=f"cards_{id(self)}")

        for idx, card in enumerate(self.card_widgets):
            row = idx // columns
            col = idx % columns
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)


class StatCard(UICard):
    def __init__(self, parent, label, value="0", *, bg="#0d2c4d", value_fg=COR_TEXTO, label_fg=COR_TEXTO_SUB):
        super().__init__(parent, bg=bg, border=bg, padx=16, pady=12)
        self.value_label = tk.Label(
            self,
            text=value,
            font=("Bahnschrift SemiBold", 22),
            bg=bg,
            fg=value_fg,
            anchor="w",
        )
        self.value_label.pack(anchor="w")
        tk.Label(
            self,
            text=label,
            font=("Segoe UI", 9, "bold"),
            bg=bg,
            fg=label_fg,
            anchor="w",
        ).pack(anchor="w")

    def set_value(self, value):
        self.value_label.configure(text=str(value))


class EmptyState(UICard):
    def __init__(self, parent, title, message, *, accent=COR_TEXTO_DIM):
        super().__init__(parent, bg=COR_BG_CARD, border=COR_BORDA, padx=22, pady=20)
        tk.Frame(self, bg=accent, width=46, height=5).pack(anchor="w", pady=(0, 10))
        tk.Label(
            self,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=COR_BG_CARD,
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
        ).pack(fill="x")
        tk.Label(
            self,
            text=message,
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=360,
        ).pack(fill="x", pady=(6, 0))


class HeadlessSummaryCard(UICard):
    def __init__(self, parent, *, title="Diagnostico Headless", compact=False, open_command=None, action_text=None, action_command=None):
        super().__init__(parent, bg=COR_BG_CARD, border=COR_BORDA, padx=16, pady=14)
        self._compact = compact

        top = tk.Frame(self, bg=COR_BG_CARD)
        top.pack(fill="x")

        self._badge = tk.Label(
            top,
            text="SEM RELATORIO",
            font=("Segoe UI", 8 if compact else 9, "bold"),
            bg="#243244",
            fg=COR_TEXTO_DIM,
            padx=10,
            pady=4,
        )
        self._badge.pack(side="left", anchor="nw")

        actions = tk.Frame(top, bg=COR_BG_CARD)
        actions.pack(side="right", anchor="ne")

        if open_command:
            make_secondary_button(
                actions,
                "Abrir Relatorio",
                open_command,
                padx=12,
                pady=7,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="right", anchor="ne")
        if action_command and action_text:
            make_primary_button(
                actions,
                action_text,
                action_command,
                padx=12,
                pady=7,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="right", anchor="ne", padx=(0, 8))

        tk.Label(
            self,
            text=title,
            font=("Bahnschrift SemiBold", 15 if compact else 18),
            bg=COR_BG_CARD,
            fg=COR_TEXTO,
            anchor="w",
        ).pack(fill="x", pady=(10, 4))

        wrap = 260 if compact else 720
        self._headline = tk.Label(
            self,
            text="Nenhum relatorio headless ainda",
            font=("Segoe UI", 10 if compact else 11, "bold"),
            bg=COR_BG_CARD,
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._headline.pack(fill="x")

        self._subheadline = tk.Label(
            self,
            text="Rode o posto headless para preencher este painel.",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._subheadline.pack(fill="x", pady=(4, 8))

        self._alerts = tk.Label(
            self,
            text="Alertas: -",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._alerts.pack(fill="x", pady=2)

        self._recs = tk.Label(
            self,
            text="Recomendacoes: -",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._recs.pack(fill="x", pady=2)

        self._areas = tk.Label(
            self,
            text="Areas: -",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._areas.pack(fill="x", pady=(2, 0))

        self._packages = tk.Label(
            self,
            text="Pacotes em evidencia: -",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._packages.pack(fill="x", pady=(2, 0))

        self._review_axis = tk.Label(
            self,
            text="Eixo prioritario: -",
            font=("Segoe UI", 9, "bold"),
            bg=COR_BG_CARD,
            fg=COR_WARNING,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._review_axis.pack(fill="x", pady=(8, 0))

        self._review_plan = tk.Label(
            self,
            text="Plano de revisao: -",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._review_plan.pack(fill="x", pady=(2, 0))

        self._inspection_title = tk.Label(
            self,
            text="Alvo de Inspecao",
            font=("Segoe UI", 9, "bold"),
            bg=COR_BG_CARD,
            fg=COR_SUCCESS,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._inspection_title.pack(fill="x", pady=(10, 2))

        self._inspection_text = tk.Label(
            self,
            text="Assim que existir um relatorio recente, este painel aponta o que observar na proxima luta.",
            font=("Segoe UI", 9),
            bg=COR_BG_CARD,
            fg=COR_TEXTO_DIM,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self._inspection_text.pack(fill="x", pady=(0, 0))

    def set_summary(self, resumo):
        tone = str((resumo or {}).get("status_tone", "idle") or "idle")
        palette = {
            "healthy": ("#123227", COR_SUCCESS),
            "warning": ("#4a3815", "#f5c451"),
            "critical": ("#4e1f26", "#ff9494"),
            "idle": ("#243244", COR_TEXTO_DIM),
        }
        bg_badge, fg_badge = palette.get(tone, palette["idle"])
        self._badge.configure(
            text=str((resumo or {}).get("status_text", "SEM RELATORIO") or "SEM RELATORIO"),
            bg=bg_badge,
            fg=fg_badge,
        )
        self._headline.configure(text=str((resumo or {}).get("headline", "-") or "-"))
        self._subheadline.configure(text=str((resumo or {}).get("subheadline", "-") or "-"))
        self._alerts.configure(text=f"Alertas: {str((resumo or {}).get('alert_text', '-') or '-')}")
        self._recs.configure(text=f"Recomendacoes: {str((resumo or {}).get('recommendation_text', '-') or '-')}")
        self._areas.configure(text=f"Areas: {str((resumo or {}).get('areas_text', '-') or '-')}")
        self._packages.configure(text=f"Pacotes em evidencia: {str((resumo or {}).get('package_text', '-') or '-')}")
        self._review_axis.configure(text=f"Eixo prioritario: {str((resumo or {}).get('review_axis_text', '-') or '-')}")
        self._review_plan.configure(text=f"Plano de revisao: {str((resumo or {}).get('review_plan_text', '-') or '-')}")
        self._inspection_title.configure(text=str((resumo or {}).get("inspection_title", "Alvo de Inspecao") or "Alvo de Inspecao"))
        self._inspection_text.configure(text=str((resumo or {}).get("inspection_text", "-") or "-"))


def render_stat_grid(
    parent,
    stats,
    *,
    columns=2,
    bg=COR_BG_SECUNDARIO,
    label_fg=COR_TEXTO_DIM,
    value_fg=COR_TEXTO,
    value_color_resolver=None,
    padx=10,
    pady=5,
    label_font=("Arial", 9),
    value_font=("Arial", 9, "bold"),
):
    for index, (label, value) in enumerate(stats):
        row = index // columns
        col = index % columns
        frame = tk.Frame(parent, bg=bg)
        frame.grid(row=row, column=col, padx=padx, pady=pady, sticky="w")

        tk.Label(
            frame,
            text=f"{label}:",
            font=label_font,
            bg=bg,
            fg=label_fg,
        ).pack(side="left")

        current_value_fg = value_fg
        if value_color_resolver:
            try:
                current_value_fg = value_color_resolver(label, value)
            except Exception:
                current_value_fg = value_fg

        tk.Label(
            frame,
            text=value,
            font=value_font,
            bg=bg,
            fg=current_value_fg,
        ).pack(side="left", padx=5)
