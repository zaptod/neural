"""
Recorder de encontro generico para equipes e horda.

Reusa a engine principal e o toolkit visual do FightRecorder,
mas injeta um encounter_config canonico em vez do duelo fixo.
"""

from __future__ import annotations

from copy import deepcopy
import math
import os
import time

from pipeline_video.config import (
    END_TEXT,
    END_TEXT_DURATION,
    FADE_OUT_DURATION,
    MIN_FIGHT_DURATION,
    OUTPUT_DIR,
    VIDEO_CODEC,
    VIDEO_FPS,
)
from pipeline_video.fight_recorder import (
    FightRecorder,
    _restore_app_state,
    _setup_headless,
    _snapshot_app_state,
)
from utilitarios.encounter_config import get_encounter_side_labels, normalize_match_config


class _OverlayEncounterState:
    def __init__(self, extra_chars, extra_weapons, encounter_config):
        from dados.app_state import AppState

        self.state = AppState.get()
        self.extra_chars = list(extra_chars or [])
        self.extra_weapons = list(extra_weapons or [])
        self.encounter_config = normalize_match_config(encounter_config)
        self.snapshot = _snapshot_app_state()

    def __enter__(self):
        self.state._characters = list(self.snapshot["characters"]) + self.extra_chars
        self.state._weapons = list(self.snapshot["weapons"]) + self.extra_weapons
        self.state._match = deepcopy(self.encounter_config)
        return self

    def __exit__(self, exc_type, exc, tb):
        _restore_app_state(self.snapshot)
        return False


class EncounterRecorder(FightRecorder):
    def __init__(
        self,
        encounter_config: dict,
        *,
        extra_characters=None,
        extra_weapons=None,
        output_path: str | None = None,
        max_duration: float = 130.0,
        min_fight_duration: float = MIN_FIGHT_DURATION,
    ):
        self.encounter_config = normalize_match_config(encounter_config)
        self.mode = self.encounter_config.get("modo_partida", "equipes")
        self.extra_characters = list(extra_characters or [])
        self.extra_weapons = list(extra_weapons or [])
        side_a, side_b = get_encounter_side_labels(self.encounter_config)
        self.side_a_label = side_a
        self.side_b_label = side_b
        self.side_a_members = list((self.encounter_config.get("teams") or [{}])[0].get("members", []))
        if self.mode == "horda":
            self.side_b_members = [self.side_b_label]
        else:
            teams = self.encounter_config.get("teams") or []
            self.side_b_members = list(teams[1].get("members", [])) if len(teams) > 1 else [self.side_b_label]
        self.team_labels = {
            0: self.side_a_label,
            1: self.side_b_label,
        }

        rep_left = self._representative_card(self.side_a_label, self.side_a_members, team_id=0)
        rep_right = self._representative_card(self.side_b_label, self.side_b_members, team_id=1)
        super().__init__(
            rep_left["char"],
            rep_left["weapon"],
            rep_right["char"],
            rep_right["weapon"],
            cenario=self.encounter_config.get("cenario", "Arena"),
            max_duration=max_duration,
            output_path=output_path,
            min_fight_duration=min_fight_duration,
            story_mode="classic",
            roulette_story=None,
        )

    def _representative_card(self, label: str, members: list[str], *, team_id: int) -> dict:
        source_name = members[0] if members else label
        for char in self.extra_characters:
            if getattr(char, "nome", "") == source_name:
                cor = (
                    int(getattr(char, "r", 220)),
                    int(getattr(char, "g", 100)),
                    int(getattr(char, "b", 100)),
                )
                return {
                    "char": {
                        "nome": label,
                        "classe": f"{len(members) or 1} combatentes",
                        "cor_r": cor[0],
                        "cor_g": cor[1],
                        "cor_b": cor[2],
                    },
                    "weapon": {"nome": "Pacote Tatico"},
                }
        fallback = (94, 210, 255) if team_id == 0 else ((122, 196, 124) if self.mode == "horda" else (255, 96, 130))
        return {
            "char": {
                "nome": label,
                "classe": f"{len(members) or 1} combatentes",
                "cor_r": fallback[0],
                "cor_g": fallback[1],
                "cor_b": fallback[2],
            },
            "weapon": {"nome": "Pacote Tatico"},
        }

    def record(self) -> "EncounterRecorder":
        import cv2
        import pygame
        from pipeline_video.audio_mixer import AudioEventCapture, mix_audio_track, mux_video_audio, reencode_silent_video
        from simulacao.simulacao import Simulador

        _setup_headless()
        if pygame.get_init():
            pygame.quit()

        if self.output_path is None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            fname = f"encounter_{self.mode}_{self.side_a_label}_vs_{self.side_b_label}_{ts}.mp4"
            fname = "".join(c if c.isalnum() or c in "_-." else "_" for c in fname)
            self.output_path = str(OUTPUT_DIR / fname)

        silent_video = self.output_path.replace(".mp4", "_silent.mp4")
        writer = None
        audio_capture = AudioEventCapture()

        try:
            with _OverlayEncounterState(self.extra_characters, self.extra_weapons, self.encounter_config):
                sim = Simulador()
                sim.show_hud = False
                sim.show_hitbox_debug = False
                sim.show_analysis = False
                render_surface = pygame.Surface((sim.screen_width, sim.screen_height))

                audio_capture.start()
                fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
                writer = cv2.VideoWriter(silent_video, fourcc, VIDEO_FPS, (1080, 1920))
                if not writer.isOpened():
                    raise RuntimeError(f"Falha ao abrir VideoWriter: {silent_video}")

                dt = 1.0 / VIDEO_FPS
                elapsed = 0.0
                prelude_elapsed = 0.0
                intro_duration = self._get_intro_duration()
                min_fight_seconds = min(self.min_fight_duration, max(0.0, self.max_duration - 2.0))
                post_victory_max = int(END_TEXT_DURATION * VIDEO_FPS)
                fade_frames = int(FADE_OUT_DURATION * VIDEO_FPS)
                post_victory_frames = 0

                while prelude_elapsed < intro_duration:
                    audio_capture.update_time(prelude_elapsed)
                    self._write_frame(sim, render_surface, writer, None, 1.0 - (prelude_elapsed / max(0.001, intro_duration)))
                    prelude_elapsed += dt

                while elapsed < self.max_duration:
                    audio_capture.update_time(prelude_elapsed + elapsed)
                    sim.update(self._compute_sim_dt(sim, dt))

                    if sim.vencedor:
                        post_victory_frames += 1
                        self._write_frame(sim, render_surface, writer, post_victory_frames / max(1, post_victory_max), None)
                        if post_victory_frames >= post_victory_max and elapsed >= min_fight_seconds:
                            self.winner = str(sim.vencedor)
                            self.fight_ended_at = elapsed
                            break
                    else:
                        intro_progress = 1.0 - (elapsed / max(0.001, intro_duration)) if elapsed < intro_duration else None
                        self._write_frame(sim, render_surface, writer, None, intro_progress)
                    elapsed += dt

                if not self.winner:
                    self.winner = str(sim.vencedor or "Empate")

                if self.total_frames > 0:
                    last_rgb = self._render_frame(sim, render_surface, None)
                    for i in range(fade_frames):
                        alpha = 1.0 - (i / max(1, fade_frames))
                        faded = (last_rgb * alpha).astype("uint8")
                        writer.write(cv2.cvtColor(faded, cv2.COLOR_RGB2BGR))
                        self.total_frames += 1

                self.duration = prelude_elapsed + elapsed
                self.video_file = self.output_path

        finally:
            audio_capture.stop()
            if writer is not None:
                writer.release()
            try:
                pygame.display.quit()
                pygame.mixer.quit()
            except Exception:
                pass

        if self.total_frames > 0 and audio_capture.events:
            wav_path = self.output_path.replace(".mp4", "_audio.wav")
            total_duration = self.total_frames / VIDEO_FPS
            if mix_audio_track(audio_capture.events, total_duration, wav_path):
                if mux_video_audio(silent_video, wav_path, self.output_path, expected_duration_s=total_duration):
                    try:
                        os.remove(silent_video)
                        os.remove(wav_path)
                    except OSError:
                        pass
                else:
                    if not reencode_silent_video(silent_video, self.output_path, expected_duration_s=total_duration):
                        os.replace(silent_video, self.output_path)
            elif os.path.exists(silent_video):
                if not reencode_silent_video(silent_video, self.output_path, expected_duration_s=total_duration):
                    os.replace(silent_video, self.output_path)
        elif os.path.exists(silent_video):
            total_duration = self.total_frames / VIDEO_FPS if self.total_frames > 0 else None
            from pipeline_video.audio_mixer import reencode_silent_video
            if not reencode_silent_video(silent_video, self.output_path, expected_duration_s=total_duration):
                os.replace(silent_video, self.output_path)

        return self

    def _draw_intro_overlay(self, surface, progress):
        import pygame

        w, h = surface.get_size()
        progress = max(0.0, min(1.0, progress))
        reveal = 1.0 - progress
        left_accent, _ = self._palette_from_fighter(None, fallback_name=self.char1.get("nome"))
        right_accent, _ = self._palette_from_fighter(None, fallback_name=self.char2.get("nome"))

        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((6, 10, 18, int(150 * progress)))
        surface.blit(veil, (0, 0))

        left_rect = pygame.Rect(int(w * 0.06), int(h * 0.17), int(w * 0.36), int(h * 0.24))
        right_rect = pygame.Rect(int(w * 0.58), int(h * 0.17), int(w * 0.36), int(h * 0.24))
        center_rect = pygame.Rect(int(w * 0.39), int(h * 0.25), int(w * 0.22), int(h * 0.10))
        self._draw_panel_frame(surface, left_rect, fill=(8, 12, 20, int(224 * progress)), border=(242, 246, 250), accent=left_accent)
        self._draw_panel_frame(surface, right_rect, fill=(8, 12, 20, int(224 * progress)), border=(242, 246, 250), accent=right_accent, align_right=True)
        self._draw_panel_frame(surface, center_rect, fill=(12, 18, 28, int(235 * progress)), border=(255, 228, 148), accent=(255, 186, 84))

        font_tag = self._get_ui_font(max(12, int(w * 0.024)), bold=True)
        font_name = self._get_ui_font(max(18, int(w * 0.04)), bold=True)
        font_meta = self._get_ui_font(max(11, int(w * 0.022)), bold=True)
        font_vs = self._get_ui_font(max(24, int(w * 0.064)), bold=True)

        def _draw_side(card_rect, label, members, accent, align_right=False):
            tag = "HORDA" if self.mode == "horda" and label == self.side_b_label else "ESQUADRA"
            tag_surf = font_tag.render(tag, True, (255, 214, 132))
            name_surf = font_name.render(str(label).upper()[:22], True, (248, 250, 252))
            if align_right:
                x = card_rect.right - 16
                surface.blit(tag_surf, (x - tag_surf.get_width(), card_rect.y + 14))
                self._draw_text_with_shadow(surface, str(label).upper()[:22], font_name, (248, 250, 252), (x - name_surf.get_width(), card_rect.y + 36))
            else:
                x = card_rect.x + 16
                surface.blit(tag_surf, (x, card_rect.y + 14))
                self._draw_text_with_shadow(surface, str(label).upper()[:22], font_name, (248, 250, 252), (x, card_rect.y + 36))

            y = card_rect.y + 36 + name_surf.get_height() + 14
            for member in members[:4]:
                line = font_meta.render(str(member).upper()[:24], True, accent)
                lx = card_rect.right - 16 - line.get_width() if align_right else card_rect.x + 16
                surface.blit(line, (lx, y))
                y += line.get_height() + 6

        _draw_side(left_rect, self.side_a_label, self.side_a_members, left_accent, align_right=False)
        _draw_side(right_rect, self.side_b_label, self.side_b_members, right_accent, align_right=True)
        self._draw_text_with_shadow(surface, "VS", font_vs, (255, 234, 164), (center_rect.centerx - 24, center_rect.y + 12), shadow_offset=3)
        sub = font_tag.render(self.mode.upper(), True, (244, 246, 248))
        surface.blit(sub, (center_rect.centerx - sub.get_width() // 2, center_rect.bottom - 28))

        sweep_x = int((w + 180) * reveal) - 180
        sweep = pygame.Surface((180, h), pygame.SRCALPHA)
        for idx in range(180):
            line_alpha = max(0, int(46 * progress * (1.0 - abs(idx - 90) / 90)))
            pygame.draw.line(sweep, (255, 255, 255, line_alpha), (idx, 0), (idx, h))
        surface.blit(sweep, (sweep_x, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_persistent_hud(self, surface, sim):
        import pygame

        w, h = surface.get_size()
        panel_w = int(w * 0.34)
        panel_h = int(h * 0.12)
        pad = max(10, int(w * 0.04))
        font_title = self._get_ui_font(max(16, int(w * 0.038)), bold=True)
        font_meta = self._get_ui_font(max(11, int(w * 0.022)), bold=True)

        def _side_metrics(team_id: int):
            fighters = [f for f in getattr(sim, "fighters", []) if getattr(f, "team_id", -1) == team_id]
            vivos = [f for f in fighters if not getattr(f, "morto", False)]
            total_hp = sum(max(0.0, getattr(f, "vida", 0.0)) for f in fighters)
            total_hp_max = sum(max(1.0, getattr(f, "vida_max", 1.0)) for f in fighters)
            pct = total_hp / max(total_hp_max, 1.0)
            return fighters, vivos, pct

        def _draw_panel(team_id: int, label: str, members: list[str], align_right=False):
            fighters, vivos, pct = _side_metrics(team_id)
            fighter_ref = fighters[0] if fighters else None
            cor_base, cor_escura = self._palette_from_fighter(fighter_ref, fallback_name=label)
            x = w - panel_w - pad if align_right else pad
            rect = pygame.Rect(x, pad, panel_w, panel_h)
            self._draw_panel_frame(surface, rect, fill=(8, 12, 20, 208), border=(240, 244, 250), accent=cor_base, align_right=align_right)
            title = str(label).upper()[:22]
            title_surf = font_title.render(title, True, cor_base)
            tx = rect.right - title_surf.get_width() - 16 if align_right else rect.x + 16
            self._draw_text_with_shadow(surface, title, font_title, cor_base, (tx, rect.y + 10))
            meta = font_meta.render(f"Vivos {len(vivos)}/{max(1, len(members) or len(fighters))}", True, (214, 220, 228))
            mx = rect.right - meta.get_width() - 16 if align_right else rect.x + 16
            surface.blit(meta, (mx, rect.y + 16 + title_surf.get_height()))

            bar_w = int(panel_w * 0.72)
            bar_h = max(10, int(h * 0.015))
            bx = rect.right - bar_w - 16 if align_right else rect.x + 16
            bg_r = pygame.Rect(bx, rect.bottom - bar_h - 14, bar_w, bar_h)
            pygame.draw.rect(surface, (36, 44, 58), bg_r, border_radius=6)
            hp_w = max(0, int(bar_w * pct))
            if hp_w > 0:
                self._draw_gradient_rect(surface, pygame.Rect(bx, bg_r.y, hp_w, bar_h), cor_escura, cor_base, alpha=255)
            pygame.draw.rect(surface, (196, 202, 210), bg_r, 1, border_radius=6)

        _draw_panel(0, self.side_a_label, self.side_a_members, align_right=False)
        _draw_panel(1, self.side_b_label, self.side_b_members, align_right=True)

        if self.mode == "horda" and getattr(sim, "horde_manager", None):
            summary = sim.horde_manager.export_summary()
            badge = pygame.Rect(int(w * 0.26), h - int(h * 0.12), int(w * 0.48), int(h * 0.07))
            self._draw_panel_frame(surface, badge, fill=(10, 14, 24, 214), border=(255, 232, 164), accent=(124, 220, 154))
            text = f"WAVE {summary['wave_atual']}/{summary['waves_total']}  •  ELIMINADOS {summary['total_killed']}"
            self._draw_text_with_shadow(surface, text, font_meta, (248, 250, 252), (badge.x + 18, badge.y + 16))
        else:
            cta_rect = pygame.Rect(int(w * 0.18), h - int(h * 0.11), int(w * 0.64), int(h * 0.08))
            self._draw_panel_frame(surface, cta_rect, fill=(10, 14, 24, 214), border=(255, 232, 164), accent=(255, 178, 74))
            self._draw_text_with_shadow(surface, END_TEXT.upper(), font_meta, (248, 250, 252), (cta_rect.x + 18, cta_rect.y + 16))
