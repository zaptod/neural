"""
Fight Recorder — Grava lutas headless em frames para encoding de vídeo.

Abordagem:
  1. Inicializa pygame com display dummy (headless)
  2. Alimenta AppState com lutadores gerados
  3. Instancia Simulador normal (reusa toda a engine)
  4. Roda loop: update → desenhar → captura surface (portrait nativo)
  5. Escreve frames direto no VideoWriter (streaming)
"""
import os, sys, math, time, logging
import numpy as np

_log = logging.getLogger("fight_recorder")

# Garante path do projeto
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from video_pipeline.config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_CODEC,
    OUTPUT_DIR,
    END_TEXT, END_TEXT_DURATION, FADE_OUT_DURATION,
    MIN_FIGHT_DURATION,
)


def _setup_headless():
    """Configura pygame para rodar sem janela visível."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"


def _inject_match_config(char1: dict, arma1: dict, char2: dict, arma2: dict,
                         cenario: str = "Arena"):
    """Injeta os dois lutadores no AppState para que Simulador.carregar_luta_dados() os encontre."""
    from models import Personagem, Arma
    from data.app_state import AppState

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
        # Geometry attrs — Arma.__init__ uses **kwargs and discards them,
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
            classe=cd.get("classe", "Guerreiro (Força Bruta)"),
            personalidade=cd.get("personalidade", "Aleatório"),
        )
        p.arma_obj = arma
        return p

    a1 = _build_arma(arma1)
    a2 = _build_arma(arma2)
    p1 = _build_char(char1, a1)
    p2 = _build_char(char2, a2)

    # Substitui listas de personagens/armas e configura match_config
    state.set_characters([p1, p2])
    state.set_weapons([a1, a2])
    state.update_match_config(
        p1_nome=p1.nome,
        p2_nome=p2.nome,
        cenario=cenario,
        portrait_mode=True,
        teams=None,
    )


def _surface_to_numpy(surface) -> np.ndarray:
    """Converte pygame.Surface → numpy array RGB (H, W, 3)."""
    import pygame
    # pygame surfarray retorna (W, H, 3) — precisa transpor
    arr = pygame.surfarray.array3d(surface)   # shape (W, H, 3), RGB
    arr = np.transpose(arr, (1, 0, 2))        # shape (H, W, 3)
    return arr





class FightRecorder:
    """Grava uma luta completa em frames numpy."""

    def __init__(self, char1: dict, arma1: dict, char2: dict, arma2: dict,
                 cenario: str = "Arena", max_duration: float = 130.0,
                 output_path: str = None,
                 min_fight_duration: float = MIN_FIGHT_DURATION):
        """
        Args:
            char1, arma1: Dicts do personagem/arma 1 (formato character_generator)
            char2, arma2: Dicts do personagem/arma 2
            cenario: Nome do cenário/arena
            max_duration: Duração máxima em segundos (safety)
            output_path: Caminho do MP4 de saída. Se None, gera automático.
            min_fight_duration: Duração mínima obrigatória da luta em segundos.
        """
        self.char1 = char1
        self.arma1 = arma1
        self.char2 = char2
        self.arma2 = arma2
        self.cenario = cenario
        self.max_duration = max_duration
        self.output_path = output_path
        self.min_fight_duration = min_fight_duration

        self.winner = None
        self.duration = 0.0
        self.total_frames = 0
        self.fight_ended_at = None  # timestamp quando vencedor é declarado
        self.video_file = None      # caminho do vídeo gerado

    def record(self) -> "FightRecorder":
        """Executa a luta e grava frames direto em MP4 (streaming). Retorna self."""
        import pygame
        import cv2
        import time as _time

        _setup_headless()

        # Forçar recarregar pygame (limpo)
        if pygame.get_init():
            pygame.quit()

        _inject_match_config(self.char1, self.arma1, self.char2, self.arma2, self.cenario)

        # Não fazemos monkey-patch de LARGURA/ALTURA.
        # portrait_mode=True no match_config faz o Simulador usar
        # LARGURA_PORTRAIT × ALTURA_PORTRAIT (540×960) nativamente —
        # a câmera e toda a engine já funcionam perfeitamente nessa resolução.

        # Prepara output
        if self.output_path is None:
            ts = _time.strftime("%Y%m%d_%H%M%S")
            n1 = self.char1["nome"].split()[0]
            n2 = self.char2["nome"].split()[0]
            fname = f"fight_{n1}_vs_{n2}_{ts}.mp4"
            fname = "".join(c if c.isalnum() or c in "_-." else "_" for c in fname)
            self.output_path = str(OUTPUT_DIR / fname)

        # Caminho temporário do vídeo silencioso
        silent_video = self.output_path.replace(".mp4", "_silent.mp4")

        # === CAPTURA DE ÁUDIO ===
        from video_pipeline.audio_mixer import AudioEventCapture
        audio_capture = AudioEventCapture()
        # Hook é instalado APÓS sim = Simulador() porque o Simulador
        # faz AudioManager.reset() + get_instance() internamente

        writer = None

        try:
            from simulation.simulacao import Simulador

            def _new_round_simulator():
                _inject_match_config(self.char1, self.arma1, self.char2, self.arma2, self.cenario)
                sim_local = Simulador()
                sim_local.show_hud = False
                sim_local.show_hitbox_debug = False
                sim_local.show_analysis = False
                surface_local = pygame.Surface((sim_local.screen_width, sim_local.screen_height))
                return sim_local, surface_local

            sim, render_surface = _new_round_simulator()

            # Instala hook no AudioManager AGORA (após o Simulador criar a instância)
            audio_capture.start()

            # Abre VideoWriter na resolução HD de saída (1080×1920)
            fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
            writer = cv2.VideoWriter(silent_video, fourcc, VIDEO_FPS,
                                     (VIDEO_WIDTH, VIDEO_HEIGHT))
            if not writer.isOpened():
                raise RuntimeError(f"Falha ao abrir VideoWriter: {silent_video}")

            dt = 1.0 / VIDEO_FPS
            elapsed = 0.0
            min_fight_seconds = min(self.min_fight_duration, max(0.0, self.max_duration - 2.0))
            post_victory_max = int(END_TEXT_DURATION * VIDEO_FPS)  # frames após vitória
            fade_frames = int(FADE_OUT_DURATION * VIDEO_FPS)

            p1_name = self.char1["nome"]
            p2_name = self.char2["nome"]
            wins = {p1_name: 0, p2_name: 0}
            best_of = 1
            round_number = 1
            round_winner = None
            post_victory_frames = 0
            series_finished = False

            _log.info("Iniciando gravação: %s vs %s → %s",
                      self.char1["nome"], self.char2["nome"], self.output_path)

            while elapsed < self.max_duration:
                # Atualiza timestamp do áudio
                audio_capture.update_time(elapsed)

                # --- UPDATE ---
                sim.cam.atualizar(dt, sim.p1, sim.p2, fighters=sim.fighters)

                # Game feel (hit stop)
                dt_efetivo = dt
                if sim.game_feel:
                    dt_efetivo = sim.game_feel.update(dt)
                    if dt_efetivo == 0:
                        # Durante hit stop, atualiza efeitos visuais lentamente
                        for ef in sim.impact_flashes:
                            ef.update(dt * 0.3)
                        for ef in sim.hit_sparks:
                            ef.update(dt * 0.3)
                        # Ainda captura frame (slow-mo visual é bom para vídeo)
                        self._write_frame(sim, render_surface, writer, None)
                        elapsed += dt
                        continue
                else:
                    if sim.hit_stop_timer > 0:
                        sim.hit_stop_timer -= dt
                        self._write_frame(sim, render_surface, writer, None)
                        elapsed += dt
                        continue

                # Update da simulação (sem processar_inputs — headless)
                sim.update(dt_efetivo)

                # --- CAPTURA ---
                if sim.vencedor and round_winner is None:
                    round_winner = sim.vencedor

                # Pós-vitória: mantém capturando por mais alguns segundos
                if round_winner is not None:
                    post_victory_frames += 1
                    progress = post_victory_frames / max(1, post_victory_max)
                    self._write_frame(sim, render_surface, writer, progress)
                    if post_victory_frames >= post_victory_max:
                        if round_winner == p1_name:
                            wins[p1_name] += 1
                        elif round_winner == p2_name:
                            wins[p2_name] += 1

                        needed_wins = best_of // 2 + 1
                        leader_name = p1_name if wins[p1_name] >= wins[p2_name] else p2_name
                        has_series_winner = wins[leader_name] >= needed_wins

                        _log.info(
                            "Round %d concluído — vencedor: %s | Série MD%d: %s %d x %d %s",
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
                            # BUG-C4 fix: impede expansão infinita de best_of em
                            # matchups de alto DPS (Berserker vs Berserker, etc.).
                            # MD9 é o teto absoluto — além disso aceita o resultado.
                            MAX_BEST_OF = 9
                            if best_of < MAX_BEST_OF:
                                best_of += 2
                                _log.info(
                                    "Luta curta (%.1fs < %.1fs) — expandindo série para MD%d",
                                    elapsed,
                                    min_fight_seconds,
                                    best_of,
                                )
                            else:
                                _log.info(
                                    "Série atingiu MD%d (teto) — aceitando resultado com %.1fs",
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
                    self._write_frame(sim, render_surface, writer, None)

                elapsed += dt

            if not series_finished:
                if wins[p1_name] == wins[p2_name]:
                    # MED-6 fix: fallback anterior declarava p1_name como vencedor
                    # em empate/timeout, poluindo estatísticas e metadados de vídeo.
                    self.winner = round_winner or sim.vencedor or "Empate"
                else:
                    self.winner = p1_name if wins[p1_name] > wins[p2_name] else p2_name

            # Fade out final
            if self.total_frames > 0:
                # Captura último frame para fade
                last_rgb = self._render_frame(sim, render_surface, None)
                for i in range(fade_frames):
                    alpha = 1.0 - (i / max(1, fade_frames))
                    faded = (last_rgb * alpha).astype(np.uint8)
                    bgr = cv2.cvtColor(faded, cv2.COLOR_RGB2BGR)
                    writer.write(bgr)
                    self.total_frames += 1

            self.duration = elapsed
            self.video_file = self.output_path
            _log.info("Gravação finalizada: %d frames (%.1fs), vencedor: %s",
                      self.total_frames, self.duration, self.winner)

        finally:
            audio_capture.stop()
            if writer is not None:
                writer.release()
            try:
                pygame.display.quit()
                pygame.mixer.quit()
            except Exception:
                pass

        # === PÓS-PROCESSAMENTO: ÁUDIO ===
        if self.total_frames > 0 and audio_capture.events:
            from video_pipeline.audio_mixer import mix_audio_track, mux_video_audio, reencode_silent_video
            import tempfile

            wav_path = self.output_path.replace(".mp4", "_audio.wav")
            total_duration = self.total_frames / VIDEO_FPS

            if mix_audio_track(audio_capture.events, total_duration, wav_path):
                if mux_video_audio(silent_video, wav_path, self.output_path,
                                  expected_duration_s=total_duration):
                    # Limpa arquivos temporários
                    try:
                        os.remove(silent_video)
                        os.remove(wav_path)
                    except OSError:
                        pass
                else:
                    # Fallback: re-encoda sem o áudio que falhou
                    _log.warning("Falha no mux — recodificando vídeo sem áudio")
                    if not reencode_silent_video(silent_video, self.output_path,
                                                 expected_duration_s=total_duration):
                        os.replace(silent_video, self.output_path)
                    else:
                        try: os.remove(silent_video)
                        except OSError: pass
            else:
                _log.warning("Nenhum áudio mixado — recodificando vídeo sem áudio")
                if not reencode_silent_video(silent_video, self.output_path,
                                             expected_duration_s=total_duration):
                    os.replace(silent_video, self.output_path)
                else:
                    try: os.remove(silent_video)
                    except OSError: pass
        elif os.path.exists(silent_video):
            from video_pipeline.audio_mixer import reencode_silent_video
            total_duration = self.total_frames / VIDEO_FPS if self.total_frames > 0 else None
            if not reencode_silent_video(silent_video, self.output_path,
                                         expected_duration_s=total_duration):
                os.replace(silent_video, self.output_path)
            else:
                try: os.remove(silent_video)
                except OSError: pass

        return self

    def _render_frame(self, sim, render_surface, post_victory_progress) -> np.ndarray:
        """Renderiza 1 frame → numpy RGB (VIDEO_HEIGHT, VIDEO_WIDTH, 3)."""
        import pygame
        import cv2

        # Redireciona rendering para nosso surface
        original_tela = sim.tela
        sim.tela = render_surface

        # Renderiza a cena (apenas mundo + lutadores + efeitos, sem HUD)
        sim.desenhar()

        # --- Overlays de vídeo ---
        if post_victory_progress is not None:
            self._draw_victory_overlay(render_surface, sim.vencedor, post_victory_progress)

        sim.tela = original_tela

        # Surface → numpy (resolução nativa 540×960)
        frame = _surface_to_numpy(render_surface)

        # Upscale para resolução HD de saída (1080×1920)
        if frame.shape[1] != VIDEO_WIDTH or frame.shape[0] != VIDEO_HEIGHT:
            frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT),
                               interpolation=cv2.INTER_LINEAR)

        return frame

    def _write_frame(self, sim, render_surface, writer, post_victory_progress):
        """Renderiza + escreve 1 frame direto no VideoWriter."""
        import cv2
        rgb = self._render_frame(sim, render_surface, post_victory_progress)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        writer.write(bgr)
        self.total_frames += 1

    def _draw_victory_overlay(self, surface, vencedor, progress):
        """Desenha overlay de vitória + CTA no final do vídeo."""
        import pygame

        w, h = surface.get_size()

        # Fundo semi-transparente gradual
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        alpha = min(180, int(progress * 180))
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))

        # Nome do vencedor
        font_big = pygame.font.SysFont("Impact", 30)
        txt = font_big.render(f"{vencedor} VENCEU!", True, (255, 215, 0))
        tx = w // 2 - txt.get_width() // 2
        ty = h // 3
        surface.blit(txt, (tx, ty))

        # CTA text (aparece gradualmente)
        if progress > 0.3:
            cta_alpha = min(255, int((progress - 0.3) / 0.3 * 255))
            font_cta = pygame.font.SysFont("Arial", 16, bold=True)
            cta_surf = font_cta.render(END_TEXT, True, (255, 255, 255))
            # Fundo do CTA
            cta_bg = pygame.Surface((cta_surf.get_width() + 40, cta_surf.get_height() + 20), pygame.SRCALPHA)
            cta_bg.fill((0, 0, 0, min(200, cta_alpha)))
            cx = w // 2 - cta_bg.get_width() // 2
            cy = int(h * 0.65)
            surface.blit(cta_bg, (cx, cy))
            # Texto CTA com alpha
            cta_final = pygame.Surface(cta_surf.get_size(), pygame.SRCALPHA)
            cta_final.blit(cta_surf, (0, 0))
            cta_final.set_alpha(cta_alpha)
            surface.blit(cta_final, (cx + 20, cy + 10))
