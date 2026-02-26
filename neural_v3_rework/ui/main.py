# main.py  —  Neural Fights Launcher
# AppState replaces controller.lista_armas / lista_personagens / recarregar_dados()
import tkinter as tk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.app_state import AppState

# ── WORLDMAP ROOT (pasta projeto1.0/world_map_pygame) ────────────────────────
_WM_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "world_map_pygame"
)
_WM_RUNNER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "RUN_WORLDMAP.py"
)

def _setup_worldmap_hook():
    """
    Inicializa o WorldBridge para que a ponte game→world_map esteja pronta
    antes de qualquer luta ser iniciada.
    """
    try:
        from data.world_bridge import WorldBridge
        WorldBridge.get()  # instancia o singleton (detecta world_map_pygame/)
    except Exception:
        pass  # WorldMap ausente — falha silenciosa

_setup_worldmap_hook()

# --- IMPORTING SCREENS (VIEWS) ---
from ui.view_armas import TelaArmas
from ui.view_chars import TelaPersonagens
from ui.view_luta import TelaLuta
from ui.view_sons import TelaSons
from ui.view_worldmap import TelaWorldMap

COR_FUNDO = "#2C3E50"
COR_TEXTO = "#ECF0F1"


class SistemaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neural Fights - Launcher & Gerenciador")
        self.geometry("1050x780")
        self.minsize(820, 600)          # prevents buttons from going off-screen
        self.resizable(True, True)
        self.configure(bg=COR_FUNDO)

        # ── Single source of truth ────────────────────────────────────────────
        self._state = AppState.get()

        # ── Backward-compat properties (views still use controller.lista_*) ──
        # These are live properties that always reflect the current AppState.
        # No more stale copies.

        container = tk.Frame(self, bg=COR_FUNDO)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MenuPrincipal, TelaArmas, TelaPersonagens, TelaLuta, TelaInteracoes, TelaSons, TelaWorldMap):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MenuPrincipal")
        self.tournament_window = None

    # ── Properties that mirror AppState (backward compat for old views) ───────

    @property
    def lista_armas(self):
        return self._state.weapons

    @lista_armas.setter
    def lista_armas(self, value):
        self._state.set_weapons(value)

    @property
    def lista_personagens(self):
        return self._state.characters

    @lista_personagens.setter
    def lista_personagens(self, value):
        self._state.set_characters(value)

    # ── Legacy method kept — but now it's nearly free (no disk I/O) ──────────
    def recarregar_dados(self):
        """
        Kept for backward compatibility.
        AppState is already the live store; this is now a no-op
        unless you explicitly need a full reload from disk.
        """
        pass  # AppState was already loaded at startup and is kept in sync

    def forcar_reload_disco(self):
        """Force a full re-read from disk (use only if external process wrote files)."""
        self._state.reload_all()

    def show_frame(self, page_name):
        """Navigate to a screen. No disk I/O — AppState is always current."""
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "atualizar_dados"):
            frame.atualizar_dados()


class MenuPrincipal(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.configure(bg=COR_FUNDO)

        # Scrollable canvas so every button is always reachable
        canvas = tk.Canvas(self, bg=COR_FUNDO, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=COR_FUNDO)
        win_id = canvas.create_window((0, 0), window=inner, anchor="n")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(win_id, width=event.width)

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Content
        tk.Label(inner, text="NEURAL FIGHTS", font=("Impact", 40),
                 bg=COR_FUNDO, fg="#E74C3C").pack(pady=(40, 6))
        tk.Label(inner, text="Sistema de Gerenciamento e Simulacao",
                 font=("Helvetica", 13), bg=COR_FUNDO, fg="#BDC3C7").pack(pady=(0, 28))

        btn_style = {
            "font": ("Helvetica", 13, "bold"),
            "width": 30, "pady": 8,
            "bg": "#34495E", "fg": "white",
            "activebackground": "#2980B9",
            "activeforeground": "white",
            "relief": "flat",
        }

        buttons = [
            ("Forjar Armas",          lambda: controller.show_frame("TelaArmas")),
            ("Criar Personagens",      lambda: controller.show_frame("TelaPersonagens")),
            ("Simulacao (Luta)",       lambda: controller.show_frame("TelaLuta")),
            ("Modo Torneio",           lambda: self.abrir_torneio(controller)),
            ("Configurar Sons",        lambda: controller.show_frame("TelaSons")),
            ("Interacoes Sociais",     lambda: controller.show_frame("TelaInteracoes")),
            ("World Map - God War",    lambda: controller.show_frame("TelaWorldMap")),
        ]

        for text, cmd in buttons:
            tk.Button(inner, text=text, command=cmd, **btn_style).pack(pady=6)

        tk.Button(inner, text="SAIR", command=controller.quit,
                  font=("Helvetica", 12, "bold"), bg="#C0392B", fg="white",
                  width=15, pady=6, relief="flat").pack(pady=(20, 40))

    def abrir_worldmap(self):
        import subprocess, sys
        if os.path.exists(_WM_RUNNER):
            subprocess.Popen([sys.executable, _WM_RUNNER])
        else:
            messagebox.showwarning(
                "World Map",
                f"Launcher não encontrado em:\n{_WM_RUNNER}\n\n"
                "Execute RUN_WORLDMAP.py na raiz do projeto.",
            )

    def abrir_torneio(self, controller):
        try:
            import customtkinter as ctk
            from ui.view_torneio import TournamentWindow

            if controller.tournament_window is not None:
                try:
                    controller.tournament_window.lift()
                    controller.tournament_window.focus_force()
                    return
                except Exception:
                    pass

            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            controller.tournament_window = TournamentWindow()

        except ImportError as e:
            messagebox.showerror("Erro",
                f"CustomTkinter não instalado!\n\nExecute: pip install customtkinter\n\nErro: {e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir torneio: {e}")


class TelaInteracoes(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.configure(bg=COR_FUNDO)
        tk.Label(self, text="Interações Sociais & Feedback",
                 font=("Helvetica", 24, "bold"), bg=COR_FUNDO, fg="white").pack(pady=50)
        tk.Label(self, text="Módulo em desenvolvimento...\nAqui você verá likes, comentários e evolução da IA.",
                 font=("Helvetica", 12), bg=COR_FUNDO, fg="#BDC3C7").pack(pady=20)
        tk.Button(self, text="Voltar ao Menu", font=("Arial", 12), bg="#E67E22", fg="white",
                  command=lambda: controller.show_frame("MenuPrincipal")).pack(pady=50)


def main():
    app = SistemaApp()
    app.mainloop()


if __name__ == "__main__":
    main()
