"""
Fight Recorder â€” Grava lutas headless em frames para encoding de vÃ­deo.

Abordagem:
  1. Inicializa pygame com display dummy (headless)
  2. Alimenta AppState com lutadores gerados
  3. Instancia Simulador normal (reusa toda a engine)
  4. Roda loop: update â†’ desenhar â†’ captura surface (portrait nativo)
  5. Escreve frames direto no VideoWriter (streaming)
"""
import os, sys, math, time, logging
import numpy as np

_log = logging.getLogger("fight_recorder")
INTRO_OVERLAY_DURATION = 2.4

# Garante path do projeto
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pipeline_video.config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_CODEC,
    OUTPUT_DIR,
    END_TEXT, END_TEXT_DURATION, FADE_OUT_DURATION,
    MIN_FIGHT_DURATION,
)
from pipeline_video.roulette_status import get_story_segment
from utilitarios.estado_espectador import resolver_badges_estado, resolver_destaque_cinematico


def _setup_headless():
    """Configura pygame para rodar sem janela visÃ­vel."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"


def _inject_match_config(char1: dict, arma1: dict, char2: dict, arma2: dict,
                         cenario: str = "Arena"):
    """Injeta dados da luta no AppState apenas em memÃ³ria (sem persistir em disco)."""
    from modelos import Personagem, Arma
    from dados.app_state import AppState

    state = AppState.get()

    def _build_arma(d: dict) -> Arma:
        arma = Arma(
            nome=d["nome"], tipo=d.get("tipo", "Reta"),
            dano=d.get("dano", 5.0), peso=d.get("peso", 3.0),
            r=d.get("r", 200), g=d.get("g", 200), b=d.get("b", 200),
            estilo=d.get("estilo", "Misto"), cabo_dano=d.get("cabo_dano", False),
            habilidade=d.get("habilidade", "Nenhuma"),
            custo_mana=d.get("custo_mana", 0.0),
            raridade=d.get("raridade", "Comum"),
            habilidades=d.get("habilidades", []),
            encantamentos=d.get("encantamentos", []),
            passiva=d.get("passiva"),
            critico=d.get("critico", 0.0),
            velocidade_ataque=d.get("velocidade_ataque", 1.0),
            afinidade_elemento=d.get("afinidade_elemento"),
            durabilidade=d.get("durabilidade", 100.0),
            durabilidade_max=d.get("durabilidade_max", 100.0),
            quantidade=d.get("quantidade", 1),
            forca_arco=d.get("forca_arco", 0.0),
            quantidade_orbitais=d.get("quantidade_orbitais", 1),
        )
        for attr in (
            "familia",
            "subtipo",
            "elemento",
            "foco_magico",
            "perfil_mecanico",
            "perfil_visual",
            "tags",
        ):
            if attr in d:
                setattr(arma, attr, d.get(attr))
        # Geometry attrs â€” Arma.__init__ uses **kwargs and discards them,
        # but the engine accesses them at runtime (e.g. arma.distancia)
        _geom = {
            "comp_cabo": 15.0, "comp_lamina": 50.0, "largura": 8.0,
            "distancia": 20.0, "comp_corrente": 0.0, "comp_ponta": 0.0,
            "largura_ponta": 0.0, "tamanho_projetil": 0.0,
            "tamanho_arco": 0.0, "tamanho_flecha": 0.0,
            "tamanho": 8.0, "distancia_max": 0.0, "separacao": 0.0,
            "forma1_cabo": 0.0, "forma1_lamina": 0.0,
            "forma2_cabo": 0.0, "forma2_lamina": 0.0,
        }
        for attr, default in _geom.items():
            setattr(arma, attr, d.get(attr, default))
        return arma

    def _build_char(cd: dict, arma: Arma) -> Personagem:
        p = Personagem(
            nome=cd["nome"],
            tamanho=cd.get("tamanho", 1.7),
            forca=cd.get("forca", 5.0),
            mana=cd.get("mana", 5.0),
            nome_arma=arma.nome,
            peso_arma_cache=arma.peso,
            r=cd.get("cor_r", 200), g=cd.get("cor_g", 50), b=cd.get("cor_b", 50),
            classe=cd.get("classe", "Guerreiro (ForÃ§a Bruta)"),
            personalidade=cd.get("personalidade", "AleatÃ³rio"),
        )
        p.arma_obj = arma
        return p

    a1 = _build_arma(arma1)
    a2 = _build_arma(arma2)
    p1 = _build_char(char1, a1)
    p2 = _build_char(char2, a2)

    # B02 Sprint fix: usa API pÃºblica em vez de atributos privados.
    # Substitui listas/config APENAS em memÃ³ria para nÃ£o poluir JSON global.
    state.set_characters([p1, p2])
    state.set_weapons([a1, a2])
    state.set_match_config({
        **state.match_config,
        "p1_nome": p1.nome,
        "p2_nome": p2.nome,
        "cenario": cenario,
        "portrait_mode": True,
        "teams": None,
    })


def _snapshot_app_state() -> dict:
    """
    B02: Captura o AppState atual usando APENAS a API pÃºblica.
    NÃ£o acessa atributos privados (_characters, _match, _weapons).
    """
    from dados.app_state import AppState
    state = AppState.get()
    return {
        "characters": list(state.characters),
        "weapons":    list(state.weapons),
        "match":      dict(state.match_config),
    }


def _restore_app_state(snapshot: dict) -> None:
    """
    B02: Restaura o AppState em memÃ³ria usando APENAS a API pÃºblica.
    NÃ£o acessa atributos privados (_characters, _match, _weapons).
    Chamado no bloco finally de record() â€” apÃ³s a gravaÃ§Ã£o terminar.
    """
    from dados.app_state import AppState
    if snapshot is None:
        return
    state = AppState.get()
    if "characters" in snapshot and snapshot["characters"] is not None:
        state.set_characters(snapshot["characters"])
    if "weapons" in snapshot and snapshot["weapons"] is not None:
        state.set_weapons(snapshot["weapons"])
    if "match" in snapshot:
        state.set_match_config(snapshot["match"])


def _surface_to_numpy(surface) -> np.ndarray:
    """Converte pygame.Surface â†’ numpy array RGB (H, W, 3)."""
    import pygame
    # pygame surfarray retorna (W, H, 3) â€” precisa transpor
    arr = pygame.surfarray.array3d(surface)   # shape (W, H, 3), RGB
    arr = np.transpose(arr, (1, 0, 2))        # shape (H, W, 3)
    return arr





class FightRecorder:
    """Grava uma luta completa em frames numpy."""

    def __init__(self, char1: dict, arma1: dict, char2: dict, arma2: dict,
                 cenario: str = "Arena", max_duration: float = 130.0,
                 output_path: str = None,
                 min_fight_duration: float = MIN_FIGHT_DURATION,
                 story_mode: str = "classic",
                 roulette_story: dict | None = None):
        """
        Args:
            char1, arma1: Dicts do personagem/arma 1 (formato character_generator)
            char2, arma2: Dicts do personagem/arma 2
            cenario: Nome do cenÃ¡rio/arena
            max_duration: DuraÃ§Ã£o mÃ¡xima em segundos (safety)
            output_path: Caminho do MP4 de saÃ­da. Se None, gera automÃ¡tico.
            min_fight_duration: DuraÃ§Ã£o mÃ­nima obrigatÃ³ria da luta em segundos.
        """
        self.char1 = char1
        self.arma1 = arma1
        self.char2 = char2
        self.arma2 = arma2
        self.cenario = cenario
        self.max_duration = max_duration
        self.output_path = output_path
        self.min_fight_duration = min_fight_duration
        self.story_mode = (story_mode or "classic").strip().lower()
        self.roulette_story = roulette_story if isinstance(roulette_story, dict) else None

        self.winner = None
        self.duration = 0.0
        self.total_frames = 0
        self.fight_ended_at = None  # timestamp quando vencedor Ã© declarado
        self.video_file = None      # caminho do vÃ­deo gerado

    def record(self) -> "FightRecorder":
        """Executa a luta e grava frames direto em MP4 (streaming). Retorna self."""
        import pygame
        import cv2
        import time as _time

        _setup_headless()

        # ForÃ§ar recarregar pygame (limpo)
        if pygame.get_init():
            pygame.quit()

        app_state_snapshot = _snapshot_app_state()
        _inject_match_config(self.char1, self.arma1, self.char2, self.arma2, self.cenario)

        # NÃ£o fazemos monkey-patch de LARGURA/ALTURA.
        # portrait_mode=True no match_config faz o Simulador usar
        # LARGURA_PORTRAIT Ã— ALTURA_PORTRAIT (540Ã—960) nativamente â€”
        # a cÃ¢mera e toda a engine jÃ¡ funcionam perfeitamente nessa resoluÃ§Ã£o.

        # Prepara output
        if self.output_path is None:
            ts = _time.strftime("%Y%m%d_%H%M%S")
            n1 = self.char1["nome"].split()[0]
            n2 = self.char2["nome"].split()[0]
            fname = f"fight_{n1}_vs_{n2}_{ts}.mp4"
            fname = "".join(c if c.isalnum() or c in "_-." else "_" for c in fname)
            self.output_path = str(OUTPUT_DIR / fname)

        # Caminho temporÃ¡rio do vÃ­deo silencioso
        silent_video = self.output_path.replace(".mp4", "_silent.mp4")

        # === CAPTURA DE ÃUDIO ===
        from pipeline_video.audio_mixer import AudioEventCapture
        audio_capture = AudioEventCapture()
        # Hook Ã© instalado APÃ“S sim = Simulador() porque o Simulador
        # faz AudioManager.reset() + get_instance() internamente

        writer = None

        try:
            from simulacao.simulacao import Simulador

            def _new_round_simulator():
                _inject_match_config(self.char1, self.arma1, self.char2, self.arma2, self.cenario)
                sim_local = Simulador()
                sim_local.show_hud = False
                sim_local.show_hitbox_debug = False
                sim_local.show_analysis = False
                surface_local = pygame.Surface((sim_local.screen_width, sim_local.screen_height))
                return sim_local, surface_local

            sim, render_surface = _new_round_simulator()

            # Instala hook no AudioManager AGORA (apÃ³s o Simulador criar a instÃ¢ncia)
            audio_capture.start()

            # Abre VideoWriter na resoluÃ§Ã£o HD de saÃ­da (1080Ã—1920)
            fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
            writer = cv2.VideoWriter(silent_video, fourcc, VIDEO_FPS,
                                     (VIDEO_WIDTH, VIDEO_HEIGHT))
            if not writer.isOpened():
                raise RuntimeError(f"Falha ao abrir VideoWriter: {silent_video}")

            dt = 1.0 / VIDEO_FPS
            elapsed = 0.0
            prelude_elapsed = 0.0
            min_fight_seconds = min(self.min_fight_duration, max(0.0, self.max_duration - 2.0))
            post_victory_max = int(END_TEXT_DURATION * VIDEO_FPS)  # frames apÃ³s vitÃ³ria
            fade_frames = int(FADE_OUT_DURATION * VIDEO_FPS)
            intro_duration = self._get_intro_duration()

            p1_name = self.char1["nome"]
            p2_name = self.char2["nome"]
            wins = {p1_name: 0, p2_name: 0}
            best_of = 1
            round_number = 1
            round_winner = None
            post_victory_frames = 0
            series_finished = False

            _log.info("Iniciando gravaÃ§Ã£o: %s vs %s â†’ %s",
                      self.char1["nome"], self.char2["nome"], self.output_path)

            while prelude_elapsed < intro_duration:
                audio_capture.update_time(prelude_elapsed)
                self._write_frame(
                    sim,
                    render_surface,
                    writer,
                    None,
                    None if self.story_mode == "roleta_status" else 1.0 - (prelude_elapsed / max(0.001, intro_duration)),
                    story_time=prelude_elapsed if self.story_mode == "roleta_status" else None,
                )
                prelude_elapsed += dt

            while elapsed < self.max_duration:
                # Atualiza timestamp do Ã¡udio
                audio_capture.update_time(prelude_elapsed + elapsed)

                # AvanÃ§a frame no mesmo modelo temporal do loop normal
                dt_efetivo = self._compute_sim_dt(sim, dt)
                sim.update(dt_efetivo)

                # --- CAPTURA ---
                if sim.vencedor and round_winner is None:
                    round_winner = sim.vencedor

                intro_progress = None
                if self.story_mode != "roleta_status" and elapsed < INTRO_OVERLAY_DURATION:
                    intro_progress = 1.0 - (elapsed / max(0.001, INTRO_OVERLAY_DURATION))

                # PÃ³s-vitÃ³ria: mantÃ©m capturando por mais alguns segundos
                if round_winner is not None:
                    post_victory_frames += 1
                    progress = post_victory_frames / max(1, post_victory_max)
                    self._write_frame(sim, render_surface, writer, progress, intro_progress)
                    if post_victory_frames >= post_victory_max:
                        if round_winner == p1_name:
                            wins[p1_name] += 1
                        elif round_winner == p2_name:
                            wins[p2_name] += 1

                        needed_wins = best_of // 2 + 1
                        leader_name = p1_name if wins[p1_name] >= wins[p2_name] else p2_name
                        has_series_winner = wins[leader_name] >= needed_wins

                        _log.info(
                            "Round %d concluÃ­do â€” vencedor: %s | SÃ©rie MD%d: %s %d x %d %s",
                            round_number,
                            round_winner,
                            best_of,
                            p1_name,
                            wins[p1_name],
                            wins[p2_name],
                            p2_name,
                        )

                        if has_series_winner and elapsed >= min_fight_seconds:
                            self.winner = leader_name
                            self.fight_ended_at = elapsed
                            series_finished = True
                            break

                        if has_series_winner and elapsed < min_fight_seconds:
                            # BUG-C4 fix: impede expansÃ£o infinita de best_of em
                            # matchups de alto DPS (Berserker vs Berserker, etc.).
                            # MD9 Ã© o teto absoluto â€” alÃ©m disso aceita o resultado.
                            MAX_BEST_OF = 9
                            if best_of < MAX_BEST_OF:
                                best_of += 2
                                _log.info(
                                    "Luta curta (%.1fs < %.1fs) â€” expandindo sÃ©rie para MD%d",
                                    elapsed,
                                    min_fight_seconds,
                                    best_of,
                                )
                            else:
                                _log.info(
                                    "SÃ©rie atingiu MD%d (teto) â€” aceitando resultado com %.1fs",
                                    MAX_BEST_OF, elapsed,
                                )
                                self.winner = leader_name
                                self.fight_ended_at = elapsed
                                series_finished = True
                                break

                        round_number += 1
                        round_winner = None
                        post_victory_frames = 0

                        audio_capture.stop()
                        sim, render_surface = _new_round_simulator()
                        audio_capture.start()
                        continue
                else:
                    self._write_frame(sim, render_surface, writer, None, intro_progress)

                elapsed += dt

            if not series_finished:
                if wins[p1_name] == wins[p2_name]:
                    # MED-6 fix: fallback anterior declarava p1_name como vencedor
                    # em empate/timeout, poluindo estatÃ­sticas e metadados de vÃ­deo.
                    self.winner = round_winner or sim.vencedor or "Empate"
                else:
                    self.winner = p1_name if wins[p1_name] > wins[p2_name] else p2_name

            # Fade out final
            if self.total_frames > 0:
                # Captura Ãºltimo frame para fade
                last_rgb = self._render_frame(sim, render_surface, None)
                for i in range(fade_frames):
                    alpha = 1.0 - (i / max(1, fade_frames))
                    faded = (last_rgb * alpha).astype(np.uint8)
                    bgr = cv2.cvtColor(faded, cv2.COLOR_RGB2BGR)
                    writer.write(bgr)
                    self.total_frames += 1

            self.duration = prelude_elapsed + elapsed
            self.video_file = self.output_path
            _log.info("GravaÃ§Ã£o finalizada: %d frames (%.1fs), vencedor: %s",
                      self.total_frames, self.duration, self.winner)

        finally:
            audio_capture.stop()
            if writer is not None:
                writer.release()
            _restore_app_state(app_state_snapshot)
            try:
                pygame.display.quit()
                pygame.mixer.quit()
            except Exception as _e:  # E02 Sprint 12
                import logging as _lg; _lg.getLogger('video_pipeline').debug('pygame cleanup (nÃ£o-fatal): %s', _e)

        # === PÃ“S-PROCESSAMENTO: ÃUDIO ===
        if self.total_frames > 0 and audio_capture.events:
            from pipeline_video.audio_mixer import mix_audio_track, mux_video_audio, reencode_silent_video
            import tempfile

            wav_path = self.output_path.replace(".mp4", "_audio.wav")
            total_duration = self.total_frames / VIDEO_FPS

            if mix_audio_track(audio_capture.events, total_duration, wav_path):
                if mux_video_audio(silent_video, wav_path, self.output_path,
                                  expected_duration_s=total_duration):
                    # Limpa arquivos temporÃ¡rios
                    try:
                        os.remove(silent_video)
                        os.remove(wav_path)
                    except OSError:
                        pass
                else:
                    # Fallback: re-encoda sem o Ã¡udio que falhou
                    _log.warning("Falha no mux â€” recodificando vÃ­deo sem Ã¡udio")
                    if not reencode_silent_video(silent_video, self.output_path,
                                                 expected_duration_s=total_duration):
                        os.replace(silent_video, self.output_path)
                    else:
                        try: os.remove(silent_video)
                        except OSError: pass
            else:
                _log.warning("Nenhum Ã¡udio mixado â€” recodificando vÃ­deo sem Ã¡udio")
                if not reencode_silent_video(silent_video, self.output_path,
                                             expected_duration_s=total_duration):
                    os.replace(silent_video, self.output_path)
                else:
                    try: os.remove(silent_video)
                    except OSError: pass
        elif os.path.exists(silent_video):
            from pipeline_video.audio_mixer import reencode_silent_video
            total_duration = self.total_frames / VIDEO_FPS if self.total_frames > 0 else None
            if not reencode_silent_video(silent_video, self.output_path,
                                         expected_duration_s=total_duration):
                os.replace(silent_video, self.output_path)
            else:
                try: os.remove(silent_video)
                except OSError: pass

        return self

    def _get_intro_duration(self) -> float:
        if self.story_mode == "roleta_status" and self.roulette_story:
            return max(0.0, float(self.roulette_story.get("timeline_duration", 0.0) or 0.0))
        return INTRO_OVERLAY_DURATION

    def _compute_sim_dt(self, sim, raw_dt: float) -> float:
        """Replica o avanÃ§o temporal do Simulador.run sem processar input/display."""
        # MantÃ©m comportamento de slow-mo do loop normal.
        if getattr(sim, "slow_mo_timer", 0.0) > 0:
            sim.slow_mo_timer -= raw_dt
            if sim.slow_mo_timer <= 0:
                sim.time_scale = 1.0
                if getattr(sim, "vencedor", None):
                    slowmo_end_played = getattr(sim, "_slow_mo_ended", False)
                    if not slowmo_end_played:
                        try:
                            if getattr(sim, "audio", None):
                                sim.audio.play_special("slowmo_end", 0.5)
                                sim.audio.play_special("arena_victory", 1.0)
                        except Exception as _e:  # E02 Sprint 12
                            import logging as _lg; _lg.getLogger('video_pipeline').debug('audio pÃ³s-luta (nÃ£o-fatal): %s', _e)
                        try:
                            sim._salvar_memorias_rivais()
                        except Exception as _e:  # E02 Sprint 12
                            import logging as _lg; _lg.getLogger('video_pipeline').debug('audio pÃ³s-luta (nÃ£o-fatal): %s', _e)
                        try:
                            sim._flush_match_stats()
                        except Exception as _e:  # E02 Sprint 12
                            import logging as _lg; _lg.getLogger('video_pipeline').debug('audio pÃ³s-luta (nÃ£o-fatal): %s', _e)
                        sim._slow_mo_ended = True

        return raw_dt * getattr(sim, "time_scale", 1.0)

    def _render_frame(self, sim, render_surface, post_victory_progress, intro_progress=None, story_time=None) -> np.ndarray:
        """Renderiza 1 frame â†’ numpy RGB (VIDEO_HEIGHT, VIDEO_WIDTH, 3)."""
        import pygame
        import cv2

        # Redireciona rendering para nosso surface
        original_tela = sim.tela
        sim.tela = render_surface

        # Renderiza a cena (apenas mundo + lutadores + efeitos, sem HUD)
        sim.desenhar()

        # --- HUD persistente: barras de HP + CTA ---
        self._draw_persistent_hud(render_surface, sim)
        self._draw_cinematic_overlay(render_surface, sim)

        # --- Overlays de vÃ­deo ---
        if story_time is not None and self.story_mode == "roleta_status" and self.roulette_story:
            self._draw_story_intro_overlay(render_surface, story_time)
        elif intro_progress is not None:
            self._draw_intro_overlay(render_surface, intro_progress)
        if post_victory_progress is not None:
            self._draw_victory_overlay(render_surface, sim.vencedor, post_victory_progress)

        sim.tela = original_tela

        # Surface â†’ numpy (resoluÃ§Ã£o nativa 540Ã—960)
        frame = _surface_to_numpy(render_surface)

        # Upscale para resoluÃ§Ã£o HD de saÃ­da (1080Ã—1920)
        if frame.shape[1] != VIDEO_WIDTH or frame.shape[0] != VIDEO_HEIGHT:
            frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT),
                               interpolation=cv2.INTER_LINEAR)

        return frame

    def _write_frame(self, sim, render_surface, writer, post_victory_progress, intro_progress=None, story_time=None):
        """Renderiza + escreve 1 frame direto no VideoWriter."""
        import cv2
        rgb = self._render_frame(sim, render_surface, post_victory_progress, intro_progress, story_time=story_time)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        writer.write(bgr)
        self.total_frames += 1

    def _get_ui_font(self, size: int, *, bold: bool = False):
        """Seleciona uma fonte de display legivel e consistente para overlays."""
        import pygame

        font_candidates = [
            "Bahnschrift",
            "Arial Black",
            "Impact",
            "Verdana",
            "Arial",
        ]
        for name in font_candidates:
            if pygame.font.match_font(name, bold=bold):
                return pygame.font.SysFont(name, size, bold=bold)
        return pygame.font.SysFont(None, size, bold=bold)

    def _draw_text_with_shadow(self, surface, text, font, color, pos, *, shadow_offset=2):
        """Desenha texto com sombra curta para leitura em cima do combate."""
        import pygame

        shadow = font.render(text, True, (10, 14, 20))
        main = font.render(text, True, color)
        surface.blit(shadow, (pos[0] + shadow_offset, pos[1] + shadow_offset))
        surface.blit(main, pos)
        return main

    def _draw_gradient_rect(self, surface, rect, color_a, color_b, *, vertical=False, alpha=255):
        """Desenha um retangulo com gradiente simples e barato."""
        import pygame

        grad = pygame.Surface((max(1, rect.width), max(1, rect.height)), pygame.SRCALPHA)
        span = rect.height if vertical else rect.width
        span = max(1, span)
        for idx in range(span):
            t = idx / max(1, span - 1)
            color = (
                int(color_a[0] + (color_b[0] - color_a[0]) * t),
                int(color_a[1] + (color_b[1] - color_a[1]) * t),
                int(color_a[2] + (color_b[2] - color_a[2]) * t),
                alpha,
            )
            if vertical:
                pygame.draw.line(grad, color, (0, idx), (rect.width, idx))
            else:
                pygame.draw.line(grad, color, (idx, 0), (idx, rect.height))
        surface.blit(grad, rect.topleft)

    def _draw_panel_frame(self, surface, rect, *, fill=(8, 12, 20, 190), border=(255, 255, 255),
                          accent=(255, 220, 90), align_right=False):
        """Painel com brilho sutil e recorte diagonal para o HUD de video."""
        import pygame

        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=18)

        accent_poly = [
            (0, 0),
            (rect.width * 0.72, 0),
            (rect.width if not align_right else rect.width * 0.86, rect.height),
            (0 if not align_right else rect.width * 0.14, rect.height),
        ]
        if align_right:
            accent_poly = [(rect.width - x, y) for x, y in accent_poly]
        pygame.draw.polygon(panel, (*accent, 32), accent_poly)
        pygame.draw.rect(panel, (*border, 180), panel.get_rect(), 2, border_radius=18)
        surface.blit(panel, rect.topleft)

        glow_rect = rect.inflate(8, 8)
        glow = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*accent, 40), glow.get_rect(), 4, border_radius=22)
        surface.blit(glow, glow_rect.topleft)

    def _palette_from_fighter(self, fighter=None, *, fallback_name=None):
        """Resolve paleta primaria/secundaria do lutador para o overlay."""
        if fighter is not None:
            base = (
                int(getattr(fighter.dados, "r", 220)),
                int(getattr(fighter.dados, "g", 100)),
                int(getattr(fighter.dados, "b", 100)),
            )
            return base, tuple(max(30, min(255, int(c * 0.38))) for c in base)

        for source in (getattr(self, "char1", None), getattr(self, "char2", None)):
            if source and source.get("nome") == fallback_name:
                base = (
                    int(source.get("cor_r", 220)),
                    int(source.get("cor_g", 100)),
                    int(source.get("cor_b", 100)),
                )
                return base, tuple(max(30, min(255, int(c * 0.38))) for c in base)

        return (255, 214, 102), (90, 52, 18)

    def _draw_status_badges(self, surface, fighter, x, y, *, align_right=False, max_badges=2):
        """Desenha pills curtas para expor o estado dramático/tático ao espectador."""
        import pygame

        badges = resolver_badges_estado(fighter, max_badges=max_badges)
        if not badges:
            return

        font = self._get_ui_font(11, bold=True)
        badge_h = 18
        pad_x = 8
        spacing = 5
        total_w = 0
        rendered = []
        for badge in badges:
            surf = font.render(str(badge.get("texto", "")), True, badge.get("fg", (248, 250, 252)))
            rect_w = surf.get_width() + pad_x * 2
            total_w += rect_w
            rendered.append((badge, surf, rect_w))
        total_w += spacing * max(0, len(rendered) - 1)

        cursor_x = x - total_w if align_right else x
        for badge, surf, rect_w in rendered:
            rect = pygame.Rect(cursor_x, y, rect_w, badge_h)
            fill = badge.get("bg", (18, 24, 36))
            border = badge.get("borda", (220, 226, 234))
            pygame.draw.rect(surface, fill, rect, border_radius=badge_h // 2)
            pygame.draw.rect(surface, border, rect, 1, border_radius=badge_h // 2)
            surface.blit(surf, (rect.x + pad_x, rect.y + (badge_h - surf.get_height()) // 2 - 1))
            cursor_x += rect_w + spacing

    def _draw_story_intro_overlay(self, surface, story_time):
        """Desenha a sequencia principal de comentario + roleta + build + versus."""
        import pygame

        story = self.roulette_story or {}
        segment = get_story_segment(story, story_time)
        if not segment:
            return

        w, h = surface.get_size()
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((5, 8, 16, 188))
        surface.blit(veil, (0, 0))

        hero_accent, hero_dark = self._palette_from_fighter(None, fallback_name=story.get("hero_name"))
        enemy_accent, enemy_dark = self._palette_from_fighter(None, fallback_name=story.get("enemy_name"))
        self._draw_gradient_rect(surface, pygame.Rect(0, 0, w, int(h * 0.12)), hero_dark, enemy_dark, alpha=126)
        self._draw_gradient_rect(surface, pygame.Rect(0, h - int(h * 0.12), w, int(h * 0.12)), enemy_dark, hero_dark, alpha=96)

        kind = segment.get("kind")
        payload = segment.get("payload", {})
        local_progress = (story_time - segment["start"]) / max(0.001, segment["duration"])
        local_progress = max(0.0, min(1.0, local_progress))

        if kind == "hook":
            self._draw_story_hook(surface, payload, local_progress, hero_accent)
        elif kind == "roulette_spin":
            self._draw_roulette_spin(surface, payload.get("roll", {}), local_progress, hero_accent, hero_dark)
        elif kind == "roulette_result":
            self._draw_roulette_result(surface, payload.get("roll", {}), local_progress, hero_accent)
        elif kind == "roulette_reaction":
            self._draw_roulette_reaction(surface, payload.get("roll", {}), local_progress, hero_accent)
        elif kind == "build_summary":
            self._draw_build_summary(surface, story, local_progress, hero_accent, enemy_accent)
        elif kind == "versus_reveal":
            self._draw_story_versus(surface, story, local_progress, hero_accent, enemy_accent)

    def _draw_story_hook(self, surface, payload, progress, accent):
        import pygame

        w, h = surface.get_size()
        card = pygame.Rect(int(w * 0.09), int(h * 0.17), int(w * 0.82), int(h * 0.26))
        self._draw_panel_frame(surface, card, fill=(8, 12, 22, 232), border=(248, 250, 252), accent=accent)

        tag_font = self._get_ui_font(max(13, int(w * 0.026)), bold=True)
        title_font = self._get_ui_font(max(23, int(w * 0.05)), bold=True)
        body_font = self._get_ui_font(max(15, int(w * 0.03)), bold=True)

        tag = "RESPONDENDO AO COMENTARIO"
        comment = str(payload.get("comment", "")).upper()
        title = "ROLETA DE STATUS"
        self._draw_text_with_shadow(surface, tag, tag_font, (255, 218, 134), (card.x + 22, card.y + 18))
        self._draw_text_with_shadow(surface, title, title_font, (248, 250, 252), (card.x + 22, card.y + 50), shadow_offset=3)

        wrap = self._wrap_text(comment, max_chars=22)
        y = card.y + 104
        for line in wrap[:3]:
            surf = body_font.render(f'"{line}"', True, (218, 224, 232))
            surface.blit(surf, (card.x + 22, y))
            y += surf.get_height() + 6

        pulse = 0.62 + 0.38 * math.sin(progress * math.pi)
        glow = pygame.Surface((card.width + 36, card.height + 36), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*accent, int(44 * pulse)), glow.get_rect(), 4, border_radius=26)
        surface.blit(glow, (card.x - 18, card.y - 18))

    def _draw_roulette_spin(self, surface, roll, progress, accent, accent_dark):
        import pygame

        w, h = surface.get_size()
        frame = pygame.Rect(int(w * 0.09), int(h * 0.14), int(w * 0.82), int(h * 0.46))
        self._draw_panel_frame(surface, frame, fill=(8, 12, 22, 236), border=(242, 246, 250), accent=accent)

        title_font = self._get_ui_font(max(18, int(w * 0.043)), bold=True)
        item_font = self._get_ui_font(max(16, int(w * 0.036)), bold=True)
        tag_font = self._get_ui_font(max(12, int(w * 0.024)), bold=True)

        label = str(roll.get("label", "STATUS")).upper()
        self._draw_text_with_shadow(surface, "ROLETA GIRANDO", tag_font, (255, 210, 124), (frame.x + 20, frame.y + 18))
        self._draw_text_with_shadow(surface, label, title_font, (248, 250, 252), (frame.x + 20, frame.y + 44))

        options = list(roll.get("visible_options", []))
        if not options:
            options = [str(roll.get("selected", "???"))]
        center_idx = int(progress * max(1, len(options) * 3)) % len(options)
        slot_h = int(h * 0.07)
        base_y = frame.y + 116
        for offset in range(-2, 3):
            idx = (center_idx + offset) % len(options)
            text = options[idx].upper()
            slot = pygame.Rect(frame.x + 26, base_y + (offset + 2) * slot_h, frame.width - 52, slot_h - 8)
            alpha = 218 if offset == 0 else 108
            fill = (18, 24, 38, alpha)
            border = accent if offset == 0 else accent_dark
            pygame.draw.rect(surface, fill, slot, border_radius=14)
            pygame.draw.rect(surface, border, slot, 2 if offset == 0 else 1, border_radius=14)
            surf = item_font.render(text[:38], True, (248, 250, 252) if offset == 0 else (198, 206, 220))
            surface.blit(surf, (slot.x + 18, slot.y + (slot.height - surf.get_height()) // 2 - 1))

        marker = pygame.Rect(frame.x + 16, base_y + 2 * slot_h - 4, frame.width - 32, slot_h)
        pygame.draw.rect(surface, (*accent, 28), marker, border_radius=18)

    def _draw_roulette_result(self, surface, roll, progress, accent):
        import pygame

        w, h = surface.get_size()
        card = pygame.Rect(int(w * 0.08), int(h * 0.23), int(w * 0.84), int(h * 0.20))
        self._draw_panel_frame(surface, card, fill=(10, 16, 28, 238), border=(248, 250, 252), accent=accent)

        label_font = self._get_ui_font(max(13, int(w * 0.027)), bold=True)
        result_font = self._get_ui_font(max(24, int(w * 0.05)), bold=True)

        label = str(roll.get("label", "STATUS")).upper()
        result = str(roll.get("selected", "???")).upper()
        self._draw_text_with_shadow(surface, "RESULTADO", label_font, (255, 220, 136), (card.x + 22, card.y + 18))
        self._draw_text_with_shadow(surface, label, label_font, (214, 220, 228), (card.x + 22, card.y + 44))
        self._draw_text_with_shadow(surface, result[:34], result_font, (248, 250, 252), (card.x + 22, card.y + 78), shadow_offset=3)

        burst = pygame.Surface((w, h), pygame.SRCALPHA)
        radius = int(140 + 70 * progress)
        pygame.draw.circle(burst, (*accent, int(28 * (1.0 - progress * 0.5))), (w // 2, int(h * 0.33)), radius)
        surface.blit(burst, (0, 0))

    def _draw_roulette_reaction(self, surface, roll, progress, accent):
        import pygame

        w, h = surface.get_size()
        card = pygame.Rect(int(w * 0.12), int(h * 0.22), int(w * 0.76), int(h * 0.24))
        self._draw_panel_frame(surface, card, fill=(8, 12, 24, 236), border=(248, 250, 252), accent=accent)

        react_font = self._get_ui_font(max(26, int(w * 0.06)), bold=True)
        note_font = self._get_ui_font(max(14, int(w * 0.029)), bold=True)
        mini_font = self._get_ui_font(max(12, int(w * 0.023)), bold=True)

        react = str(roll.get("reaction_label", "PESADO")).upper()
        note = str(roll.get("reaction_note", "A roleta decidiu o rumo da build.")).upper()
        self._draw_text_with_shadow(surface, "REACT", mini_font, (255, 210, 128), (card.x + 20, card.y + 16))
        self._draw_text_with_shadow(surface, react, react_font, (248, 250, 252), (card.x + 20, card.y + 48), shadow_offset=3)

        wrap = self._wrap_text(note, max_chars=22)
        y = card.y + 108
        for line in wrap[:2]:
            surf = note_font.render(line, True, (216, 222, 230))
            surface.blit(surf, (card.x + 20, y))
            y += surf.get_height() + 6

        emoji_rect = pygame.Rect(card.right - 110, card.y + 44, 76, 76)
        pygame.draw.circle(surface, (*accent, 52), emoji_rect.center, 40)
        pygame.draw.circle(surface, accent, emoji_rect.center, 34, 3)
        pygame.draw.circle(surface, (248, 250, 252), (emoji_rect.centerx - 10, emoji_rect.centery - 6), 5)
        pygame.draw.circle(surface, (248, 250, 252), (emoji_rect.centerx + 10, emoji_rect.centery - 6), 5)
        pygame.draw.arc(surface, (248, 250, 252), pygame.Rect(emoji_rect.x + 16, emoji_rect.y + 20, 40, 30), 3.4, 5.9, 4)

    def _draw_build_summary(self, surface, story, progress, hero_accent, enemy_accent):
        import pygame

        w, h = surface.get_size()
        card = pygame.Rect(int(w * 0.08), int(h * 0.12), int(w * 0.84), int(h * 0.55))
        self._draw_panel_frame(surface, card, fill=(8, 12, 22, 236), border=(248, 250, 252), accent=hero_accent)
        font_tag = self._get_ui_font(max(12, int(w * 0.024)), bold=True)
        font_title = self._get_ui_font(max(22, int(w * 0.05)), bold=True)
        font_line = self._get_ui_font(max(13, int(w * 0.026)), bold=True)

        self._draw_text_with_shadow(surface, "BUILD FINAL", font_tag, (255, 216, 132), (card.x + 20, card.y + 18))
        self._draw_text_with_shadow(surface, str(story.get("hero_name", "PROTAGONISTA")).upper(), font_title, (248, 250, 252), (card.x + 20, card.y + 44), shadow_offset=3)

        lines = list(story.get("build_lines", []))
        y = card.y + 108
        for idx, line in enumerate(lines[:9]):
            tone = hero_accent if idx % 2 == 0 else enemy_accent
            bullet = pygame.Rect(card.x + 20, y + 6, 10, 10)
            pygame.draw.circle(surface, tone, bullet.center, 5)
            text = font_line.render(line[:52].upper(), True, (220, 226, 234))
            surface.blit(text, (card.x + 38, y))
            y += text.get_height() + 10

    def _draw_story_versus(self, surface, story, progress, hero_accent, enemy_accent):
        import pygame

        w, h = surface.get_size()
        left = pygame.Rect(int(w * 0.08), int(h * 0.22), int(w * 0.32), int(h * 0.18))
        right = pygame.Rect(int(w * 0.60), int(h * 0.22), int(w * 0.32), int(h * 0.18))
        center = pygame.Rect(int(w * 0.40), int(h * 0.25), int(w * 0.20), int(h * 0.10))
        self._draw_panel_frame(surface, left, fill=(8, 12, 20, 228), border=(248, 250, 252), accent=hero_accent)
        self._draw_panel_frame(surface, right, fill=(8, 12, 20, 228), border=(248, 250, 252), accent=enemy_accent, align_right=True)
        self._draw_panel_frame(surface, center, fill=(12, 18, 28, 238), border=(255, 224, 142), accent=(255, 182, 84))

        font_tag = self._get_ui_font(max(12, int(w * 0.024)), bold=True)
        font_name = self._get_ui_font(max(18, int(w * 0.04)), bold=True)
        font_vs = self._get_ui_font(max(28, int(w * 0.064)), bold=True)

        self._draw_text_with_shadow(surface, "BUILD FECHADA", font_tag, (255, 210, 128), (left.x + 16, left.y + 14))
        self._draw_text_with_shadow(surface, str(story.get("hero_name", "HEROI")).upper()[:20], font_name, (248, 250, 252), (left.x + 16, left.y + 46), shadow_offset=3)
        self._draw_text_with_shadow(surface, "CHEFE FINAL", font_tag, (255, 210, 128), (right.x + 16, right.y + 14))
        self._draw_text_with_shadow(surface, str(story.get("enemy_name", "RIVAL")).upper()[:20], font_name, (right.x + 16, right.y + 46), shadow_offset=3)
        self._draw_text_with_shadow(surface, "VS", font_vs, (255, 236, 170), (center.x + center.width // 2 - 26, center.y + 12), shadow_offset=3)

        footer_font = self._get_ui_font(max(14, int(w * 0.028)), bold=True)
        footer = footer_font.render("CLIMAX: A BUILD VAI PARA A ARENA", True, (248, 250, 252))
        surface.blit(footer, (w // 2 - footer.get_width() // 2, int(h * 0.71)))

    def _wrap_text(self, text, *, max_chars=24):
        palavras = str(text or "").split()
        linhas = []
        atual = []
        for palavra in palavras:
            teste = " ".join(atual + [palavra])
            if len(teste) <= max_chars or not atual:
                atual.append(palavra)
            else:
                linhas.append(" ".join(atual))
                atual = [palavra]
        if atual:
            linhas.append(" ".join(atual))
        return linhas

    def _draw_cinematic_overlay(self, surface, sim):
        """Adiciona pulso visual e rotulo curto para momentos dramáticos."""
        import pygame

        destaque = getattr(sim, "direcao_cinematica", None)
        if not isinstance(destaque, dict) or not destaque.get("tipo"):
            destaque = resolver_destaque_cinematico(getattr(sim, "fighters", []))
        if not isinstance(destaque, dict):
            return

        intensidade = max(0.0, min(1.0, float(destaque.get("intensidade", 0.0) or 0.0)))
        overlay_timer = max(0.0, float(destaque.get("overlay_timer", destaque.get("duracao_overlay", 0.0)) or 0.0))
        if intensidade <= 0.08 and overlay_timer <= 0.0:
            return

        w, h = surface.get_size()
        cor = tuple(int(c) for c in destaque.get("cor", (255, 220, 120)))
        cor_sec = tuple(int(c) for c in destaque.get("cor_secundaria", (255, 244, 188)))
        pulso = 0.78 + 0.22 * math.sin(time.time() * 7.5)
        mix = max(intensidade * 0.75, min(1.0, overlay_timer / max(float(destaque.get("duracao_overlay", 0.25) or 0.25), 0.01)))
        alpha = int((24 + 76 * float(destaque.get("overlay", 0.4) or 0.4)) * mix * pulso)

        top = pygame.Rect(0, 0, w, int(h * 0.055))
        bottom = pygame.Rect(0, h - int(h * 0.055), w, int(h * 0.055))
        self._draw_gradient_rect(surface, top, cor, cor_sec, alpha=min(110, alpha))
        self._draw_gradient_rect(surface, bottom, cor_sec, cor, alpha=min(88, alpha))

        border = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(border, (*cor, min(96, alpha)), border.get_rect(), width=max(4, int(w * 0.008)), border_radius=24)
        surface.blit(border, (0, 0))

        label = str(destaque.get("rotulo", "")).upper()
        if label:
            font = self._get_ui_font(max(12, int(w * 0.026)), bold=True)
            surf = font.render(label, True, cor_sec)
            badge = pygame.Rect(w // 2 - (surf.get_width() + 24) // 2, int(h * 0.105), surf.get_width() + 24, surf.get_height() + 8)
            pygame.draw.rect(surface, (10, 14, 22, 210), badge, border_radius=badge.height // 2)
            pygame.draw.rect(surface, cor, badge, 2, border_radius=badge.height // 2)
            surface.blit(surf, (badge.x + 12, badge.y + 3))

    def _draw_intro_overlay(self, surface, progress):
        """Card de abertura do duelo para os primeiros segundos do video."""
        import pygame

        w, h = surface.get_size()
        progress = max(0.0, min(1.0, progress))
        reveal = 1.0 - progress
        p1_accent, p1_dark = self._palette_from_fighter(None, fallback_name=self.char1.get("nome"))
        p2_accent, p2_dark = self._palette_from_fighter(None, fallback_name=self.char2.get("nome"))

        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((6, 10, 18, int(150 * progress)))
        surface.blit(veil, (0, 0))

        band_h = int(h * 0.18)
        top_band = pygame.Rect(0, int(h * 0.06), w, band_h)
        bottom_band = pygame.Rect(0, int(h * 0.72), w, band_h)
        self._draw_gradient_rect(surface, top_band, p1_dark, p2_dark, alpha=int(120 * progress))
        self._draw_gradient_rect(surface, bottom_band, p2_dark, p1_dark, alpha=int(104 * progress))

        left_rect = pygame.Rect(int(w * 0.06), int(h * 0.17), int(w * 0.34), int(h * 0.18))
        right_rect = pygame.Rect(int(w * 0.60), int(h * 0.17), int(w * 0.34), int(h * 0.18))
        center_rect = pygame.Rect(int(w * 0.37), int(h * 0.235), int(w * 0.26), int(h * 0.11))

        self._draw_panel_frame(surface, left_rect, fill=(8, 12, 20, int(224 * progress)),
                               border=(242, 246, 250), accent=p1_accent, align_right=False)
        self._draw_panel_frame(surface, right_rect, fill=(8, 12, 20, int(224 * progress)),
                               border=(242, 246, 250), accent=p2_accent, align_right=True)
        self._draw_panel_frame(surface, center_rect, fill=(12, 18, 28, int(235 * progress)),
                               border=(255, 228, 148), accent=(255, 186, 84), align_right=False)

        font_tag = self._get_ui_font(max(12, int(w * 0.024)), bold=True)
        font_name = self._get_ui_font(max(19, int(w * 0.044)), bold=True)
        font_meta = self._get_ui_font(max(12, int(w * 0.025)), bold=True)
        font_weapon = self._get_ui_font(max(11, int(w * 0.022)), bold=True)
        font_vs = self._get_ui_font(max(24, int(w * 0.064)), bold=True)
        font_bottom = self._get_ui_font(max(12, int(w * 0.025)), bold=True)

        def _draw_intro_side(card_rect, char_data, arma_data, accent, align_right=False):
            name = str(char_data.get("nome", "Combatente")).upper()
            classe = str(char_data.get("classe", "Classe desconhecida")).upper()
            arma = str(arma_data.get("nome", "Arma desconhecida")).upper()
            tag = "DESAFIANTE"

            tag_surf = font_tag.render(tag, True, (255, 214, 132))
            name_surf = font_name.render(name, True, (248, 250, 252))
            class_surf = font_meta.render(classe[:28], True, (214, 220, 228))
            weapon_surf = font_weapon.render(f"ARMA: {arma[:24]}", True, accent)

            if align_right:
                tx = card_rect.right - tag_surf.get_width() - 16
                nx = card_rect.right - name_surf.get_width() - 16
                cx = card_rect.right - class_surf.get_width() - 16
                wx = card_rect.right - weapon_surf.get_width() - 16
            else:
                tx = nx = cx = wx = card_rect.x + 16

            surface.blit(tag_surf, (tx, card_rect.y + 14))
            self._draw_text_with_shadow(surface, name, font_name, (248, 250, 252), (nx, card_rect.y + 34))
            surface.blit(class_surf, (cx, card_rect.y + 34 + name_surf.get_height()))
            surface.blit(weapon_surf, (wx, card_rect.bottom - 28))

        _draw_intro_side(left_rect, self.char1, self.arma1, p1_accent, align_right=False)
        _draw_intro_side(right_rect, self.char2, self.arma2, p2_accent, align_right=True)

        vs_text = "VS"
        vs_surf = font_vs.render(vs_text, True, (255, 234, 164))
        self._draw_text_with_shadow(
            surface,
            vs_text,
            font_vs,
            (255, 234, 164),
            (center_rect.centerx - vs_surf.get_width() // 2, center_rect.y + 12),
            shadow_offset=3,
        )
        sub = font_tag.render("IA SEM ROTEIRO", True, (244, 246, 248))
        surface.blit(sub, (center_rect.centerx - sub.get_width() // 2, center_rect.bottom - 28))

        footer = "MATCHUP LENDARIO  •  DECISAO EM TEMPO REAL  •  RESULTADO IMPREVISIVEL"
        footer_surf = font_bottom.render(footer, True, (248, 250, 252))
        footer_surf.set_alpha(int(255 * progress))
        surface.blit(footer_surf, (w // 2 - footer_surf.get_width() // 2, int(h * 0.79)))

        sweep_x = int((w + 180) * reveal) - 180
        sweep = pygame.Surface((180, h), pygame.SRCALPHA)
        for idx in range(180):
            line_alpha = max(0, int(46 * progress * (1.0 - abs(idx - 90) / 90)))
            pygame.draw.line(sweep, (255, 255, 255, line_alpha), (idx, 0), (idx, h))
        surface.blit(sweep, (sweep_x, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_persistent_hud(self, surface, sim):
        """Desenha HUD permanente: barras de HP nos cantos superior + CTA central."""
        import pygame

        w, h = surface.get_size()
        p1 = getattr(sim, 'p1', None)
        p2 = getattr(sim, 'p2', None)
        if not p1 or not p2:
            return

        pad        = max(10, int(w * 0.04))
        panel_w    = int(w * 0.34)
        panel_h    = int(h * 0.132)
        bar_w      = int(panel_w * 0.72)
        bar_h      = max(10, int(h * 0.015))
        name_size  = max(16, int(w * 0.042))
        meta_size  = max(11, int(w * 0.022))
        hp_size    = max(12, int(w * 0.026))
        font_name  = self._get_ui_font(name_size, bold=True)
        font_meta  = self._get_ui_font(meta_size, bold=True)
        font_hp    = self._get_ui_font(hp_size, bold=True)

        def _draw_hp_panel(fighter, align_right=False):
            nome    = getattr(fighter.dados, 'nome', '???')
            classe  = getattr(fighter.dados, 'classe', 'Combatente')
            vida    = max(0.0, getattr(fighter, 'vida', 0))
            vida_max = max(1.0, getattr(fighter, 'vida_max', 1))
            pct     = vida / vida_max
            cor_base, cor_escura = self._palette_from_fighter(fighter)
            px = (w - panel_w - pad) if align_right else pad
            panel_rect = pygame.Rect(px, pad, panel_w, panel_h)
            self._draw_panel_frame(
                surface,
                panel_rect,
                fill=(8, 12, 20, 208),
                border=(240, 244, 250),
                accent=cor_base,
                align_right=align_right,
            )

            title = nome.upper()
            title_surf = font_name.render(title, True, (248, 249, 252))
            title_x = panel_rect.right - title_surf.get_width() - 16 if align_right else panel_rect.x + 16
            self._draw_text_with_shadow(surface, title, font_name, cor_base, (title_x, panel_rect.y + 10))

            classe_txt = classe.upper()[:28]
            class_surf = font_meta.render(classe_txt, True, (214, 220, 228))
            class_x = panel_rect.right - class_surf.get_width() - 16 if align_right else panel_rect.x + 16
            surface.blit(class_surf, (class_x, panel_rect.y + 16 + title_surf.get_height()))

            badge_y = panel_rect.y + 20 + title_surf.get_height() + class_surf.get_height()
            badge_anchor_x = panel_rect.right - 16 if align_right else panel_rect.x + 16
            self._draw_status_badges(surface, fighter, badge_anchor_x, badge_y, align_right=align_right, max_badges=2)

            label = font_hp.render("HP", True, (245, 247, 250))
            label_x = panel_rect.right - label.get_width() - 16 if align_right else panel_rect.x + 16
            label_y = panel_rect.bottom - bar_h - 20
            surface.blit(label, (label_x, label_y - 18))

            current_hp = f"{int(round(vida))}/{int(round(vida_max))}"
            hp_text = font_hp.render(current_hp, True, (230, 235, 240))
            hp_x = panel_rect.x + 16 if align_right else panel_rect.right - hp_text.get_width() - 16
            surface.blit(hp_text, (hp_x, label_y - 18))

            bx = panel_rect.right - bar_w - 16 if align_right else panel_rect.x + 16
            bg_r = pygame.Rect(bx, panel_rect.bottom - bar_h - 14, bar_w, bar_h)
            pygame.draw.rect(surface, (36, 44, 58), bg_r, border_radius=6)

            if pct > 0.5:
                cor_hp = (int(60 + 170 * (1 - pct) * 1.7), 228, 96)
            elif pct > 0.25:
                cor_hp = (255, int(200 * (pct / 0.5)), 54)
            else:
                cor_hp = (255, 72, 72)
            hp_w = max(0, int(bar_w * pct))
            if hp_w > 0:
                fill_rect = pygame.Rect(bx, bg_r.y, hp_w, bar_h)
                self._draw_gradient_rect(surface, fill_rect, cor_hp, cor_base, alpha=255)
                pygame.draw.rect(surface, (255, 255, 255), fill_rect, 1, border_radius=6)
            pygame.draw.rect(surface, (196, 202, 210), bg_r, 1, border_radius=6)

            accent_line = pygame.Rect(
                panel_rect.right - 8 if align_right else panel_rect.x + 4,
                panel_rect.y + 10,
                4,
                panel_rect.height - 20,
            )
            pygame.draw.rect(surface, cor_escura, accent_line, border_radius=4)

        _draw_hp_panel(p1, align_right=False)
        _draw_hp_panel(p2, align_right=True)

        # --- CTA inferior em estilo card de highlight ---
        cta_rect = pygame.Rect(int(w * 0.14), h - int(h * 0.13), int(w * 0.72), int(h * 0.085))
        self._draw_panel_frame(
            surface,
            cta_rect,
            fill=(10, 14, 24, 214),
            border=(255, 232, 164),
            accent=(255, 178, 74),
            align_right=False,
        )

        font_tag = self._get_ui_font(max(12, int(w * 0.024)), bold=True)
        font_cta = self._get_ui_font(max(18, int(w * 0.043)), bold=True)
        tag_text = "PROXIMO DESAFIANTE?"
        action_text = END_TEXT.upper()
        tag_surf = font_tag.render(tag_text, True, (255, 208, 120))
        action_surf = font_cta.render(action_text, True, (250, 250, 252))
        surface.blit(tag_surf, (cta_rect.x + 20, cta_rect.y + 10))
        self._draw_text_with_shadow(
            surface,
            action_text,
            font_cta,
            (250, 250, 252),
            (cta_rect.x + 20, cta_rect.y + 16 + tag_surf.get_height()),
        )

        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(time.time() * 3.5))
        badge_r = max(10, int(w * 0.02))
        badge_center = (cta_rect.right - 26, cta_rect.centery)
        glow = pygame.Surface((badge_r * 4, badge_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 188, 86, int(42 * pulse)), (badge_r * 2, badge_r * 2), int(badge_r * 1.6))
        surface.blit(glow, (badge_center[0] - badge_r * 2, badge_center[1] - badge_r * 2))
        pygame.draw.circle(surface, (255, 196, 88), badge_center, badge_r)
        pygame.draw.circle(surface, (255, 248, 214), badge_center, max(3, badge_r // 3))

    def _draw_victory_overlay(self, surface, vencedor, progress):
        """Desenha overlay de vitÃ³ria + CTA no final do vÃ­deo."""
        import pygame

        w, h = surface.get_size()
        progress = max(0.0, min(1.0, progress))
        accent, accent_dark = self._palette_from_fighter(None, fallback_name=vencedor)

        # Fundo com vignette e cor do vencedor.
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        alpha = min(210, int(progress * 210))
        overlay.fill((4, 6, 12, alpha))
        surface.blit(overlay, (0, 0))

        ring = pygame.Surface((int(w * 0.82), int(w * 0.82)), pygame.SRCALPHA)
        center = (ring.get_width() // 2, ring.get_height() // 2)
        pygame.draw.circle(ring, (*accent, int(18 + 34 * progress)), center, int(ring.get_width() * 0.38))
        pygame.draw.circle(ring, (*accent_dark, int(50 + 50 * progress)), center, int(ring.get_width() * 0.25))
        surface.blit(ring, (w // 2 - ring.get_width() // 2, h // 2 - ring.get_height() // 2))

        card_w = int(w * 0.78)
        card_h = int(h * 0.27)
        card_rect = pygame.Rect(w // 2 - card_w // 2, int(h * 0.23), card_w, card_h)
        self._draw_panel_frame(
            surface,
            card_rect,
            fill=(10, 14, 24, min(235, 160 + int(progress * 70))),
            border=(248, 250, 252),
            accent=accent,
            align_right=False,
        )

        title_font = self._get_ui_font(max(18, int(w * 0.05)), bold=True)
        winner_font = self._get_ui_font(max(28, int(w * 0.072)), bold=True)
        sub_font = self._get_ui_font(max(14, int(w * 0.028)), bold=True)

        title = "VITORIA DECISIVA"
        winner_name = str(vencedor).upper()
        subtitle = "DOMINOU A ARENA E ENCERROU O DUELO"

        title_surf = title_font.render(title, True, (255, 210, 116))
        title_x = w // 2 - title_surf.get_width() // 2
        self._draw_text_with_shadow(surface, title, title_font, (255, 210, 116), (title_x, card_rect.y + 20))

        winner_surf = winner_font.render(winner_name, True, (248, 250, 252))
        winner_x = w // 2 - winner_surf.get_width() // 2
        self._draw_text_with_shadow(surface, winner_name, winner_font, (248, 250, 252), (winner_x, card_rect.y + 62), shadow_offset=3)

        subtitle_surf = sub_font.render(subtitle, True, (214, 222, 230))
        surface.blit(subtitle_surf, (w // 2 - subtitle_surf.get_width() // 2, card_rect.bottom - 42))

        line_rect = pygame.Rect(card_rect.x + 36, card_rect.bottom - 22, card_rect.width - 72, 6)
        self._draw_gradient_rect(surface, line_rect, accent_dark, accent, alpha=255)

        if progress > 0.2:
            cta_alpha = min(255, int((progress - 0.2) / 0.3 * 255))
            cta_rect = pygame.Rect(int(w * 0.16), int(h * 0.66), int(w * 0.68), int(h * 0.11))
            cta_panel = pygame.Surface((cta_rect.width, cta_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(cta_panel, (6, 10, 18, min(225, cta_alpha)), cta_panel.get_rect(), border_radius=18)
            pygame.draw.rect(cta_panel, (*accent, min(255, cta_alpha)), cta_panel.get_rect(), 2, border_radius=18)
            surface.blit(cta_panel, cta_rect.topleft)

            cta_tag_font = self._get_ui_font(max(12, int(w * 0.024)), bold=True)
            cta_font = self._get_ui_font(max(18, int(w * 0.042)), bold=True)
            tag_text = "AGORA E A SUA VEZ"
            body_text = END_TEXT.upper()

            tag = cta_tag_font.render(tag_text, True, (255, 208, 120))
            body = cta_font.render(body_text, True, (248, 250, 252))
            tag.set_alpha(cta_alpha)
            body.set_alpha(cta_alpha)

            surface.blit(tag, (cta_rect.x + 20, cta_rect.y + 12))
            surface.blit(body, (cta_rect.x + 20, cta_rect.y + 16 + tag.get_height()))

