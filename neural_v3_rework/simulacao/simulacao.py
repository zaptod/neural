import pygame
import logging
_log = logging.getLogger("simulacao")  # QC-02
from dataclasses import dataclass
import json
import math
import random
import sys
import os

# Adiciona o diretÃ³rio pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilitarios.config import (
    PPM, LARGURA, ALTURA, LARGURA_PORTRAIT, ALTURA_PORTRAIT, FPS,
    BRANCO, VERMELHO_SANGUE, SANGUE_ESCURO, AMARELO_FAISCA,
    AZUL_MANA, COR_CORPO, COR_P1, COR_P2, COR_FUNDO, COR_GRID,
    COR_UI_BG, COR_TEXTO_TITULO, COR_TEXTO_INFO,
)
from efeitos import (Particula, FloatingText, Decal, Shockwave, Camera, EncantamentoEffect,
                     ImpactFlash, MagicClash, BlockEffect, DashTrail, HitSpark,
                     MovementAnimationManager, MovementType,  # v8.0 Movement Animations
                     AttackAnimationManager, calcular_knockback_com_forca, get_impact_tier,  # v8.0 Attack Animations
                     MagicVFXManager, get_element_from_skill)  # v11.0 Magic VFX
from efeitos.audio import AudioManager  # v10.0 Sistema de Ãudio
from nucleo.entities import Lutador
from nucleo.physics import colisao_linha_circulo, intersect_line_circle, colisao_linha_linha, normalizar_angulo
from nucleo.hitbox import sistema_hitbox, verificar_hit, get_debug_visual, atualizar_debug, DEBUG_VISUAL
from nucleo.arena import Arena, ARENAS, get_arena, set_arena  # v9.0 Sistema de Arena
from ia import CombatChoreographer  # Sistema de Coreografia v5.0
from nucleo.game_feel import GameFeelManager, HitStopManager  # Sistema de Game Feel v8.0
from utilitarios.estado_espectador import resolver_destaque_cinematico
from utilitarios.encounter_config import normalize_match_config
from simulacao.horde_runtime import HordeWaveManager

# â”€â”€ Mixin imports â”€â”€
from simulacao.sim_renderer import SimuladorRenderer
from simulacao.sim_combat import SimuladorCombat
from simulacao.sim_effects import SimuladorEffects


@dataclass(frozen=True)
class FrameUpdateContext:
    dt: float
    dt_efetivo: float
    early_exit: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ProjectileImpactContext:
    cor_impacto: tuple
    dx: float
    dy: float
    dist: float
    direcao_impacto: float


@dataclass(frozen=True)
class ProjectileDamageProfile:
    dano_final: float
    tipo_efeito: str
    bonus_condicao: float
    source_type: str


class Simulador(SimuladorRenderer, SimuladorCombat, SimuladorEffects):


    def executar(self):
        """Alias legado para entrypoints que ainda chamam executar()."""
        return self.run()


    def run(self):
        self._slow_mo_ended = False  # Flag para tocar som de vitÃ³ria uma vez
        while self.rodando:
            try:
                self._run_single_frame()
            except Exception as e:
                self._handle_runtime_loop_exception(e)
        self._cleanup_runtime_loop()

    def _run_single_frame(self) -> None:
        raw_dt = self.clock.tick(FPS) / 1000.0
        self._update_slow_motion_state(raw_dt)
        dt = raw_dt * self.time_scale
        self.processar_inputs()
        self.update(dt)
        self.desenhar()
        pygame.display.flip()

    def _update_slow_motion_state(self, raw_dt: float) -> None:
        if self.slow_mo_timer <= 0:
            return

        self.slow_mo_timer -= raw_dt
        if self.slow_mo_timer <= 0:
            self.time_scale = 1.0
            self._play_slow_mo_end_feedback_once()

    def _play_slow_mo_end_feedback_once(self) -> None:
        if self._slow_mo_ended or not self.vencedor:
            return

        if self.audio:
            self.audio.play_special("slowmo_end", 0.5)
            self.audio.play_special("arena_victory", 1.0)
        self._slow_mo_ended = True
        self._salvar_memorias_rivais()
        self._flush_match_stats()

    def _handle_runtime_loop_exception(self, e: Exception) -> None:
        # B05: era _log.debug â€” invisÃ­vel em produÃ§Ã£o. Agora _log.exception
        # inclui automaticamente o traceback completo no log.
        _log.exception("ERRO CRÃTICO NO LOOP DE SIMULAÃ‡ÃƒO: %s", e)
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Erro", f"SimulaÃ§Ã£o falhou:\n{e}")
            root.destroy()
        except Exception as _e:
            _log.warning("Falha ao exibir diÃ¡logo de erro: %s", _e)
        self.rodando = False

    def _cleanup_runtime_loop(self) -> None:
        # Cleanup pygame display sem destruir o subsistema inteiro,
        # para que a prÃ³xima luta possa reinicializar sem invalidar caches globais.
        try:
            pygame.display.quit()
            pygame.mixer.quit()
        except Exception as _e_cleanup:  # E02 Sprint 11: pygame cleanup â€” nÃ£o-fatal
            _log.debug("pygame cleanup ignorado (nÃ£o-fatal): %s", _e_cleanup)


    def _check_portrait_mode(self) -> bool:
        """Verifica se o modo retrato estÃ¡ ativado no config"""
        try:
            from dados.app_state import AppState
            return AppState.get().match_config.get("portrait_mode", False)
        except Exception:  # QC-01
            return False

    def _update_frame_transients(self, dt: float) -> None:
        for texto in self.textos:
            texto.update(dt)
        self.textos = [texto for texto in self.textos if texto.vida > 0]

        for shockwave in self.shockwaves:
            shockwave.update(dt)
        self.shockwaves = [shockwave for shockwave in self.shockwaves if shockwave.vida > 0]

    def _update_hit_stop_visuals(self, dt: float) -> None:
        for efeito in self.impact_flashes:
            efeito.update(dt * 0.3)
        for efeito in self.hit_sparks:
            efeito.update(dt * 0.3)

    def _prepare_frame_update(self, dt: float) -> FrameUpdateContext:
        self._update_runtime_camera_and_debug(dt)
        paused_frame = self._prepare_paused_frame(dt)
        if paused_frame:
            return paused_frame
        self._update_frame_transients(dt)
        return self._resolve_runtime_frame_dt(dt)

    def _update_runtime_camera_and_debug(self, dt: float) -> None:
        self.cam.atualizar(dt, self.p1, self.p2, fighters=self.fighters)
        atualizar_debug(dt)

    def _prepare_paused_frame(self, dt: float):
        if self.paused:
            return FrameUpdateContext(dt=dt, dt_efetivo=dt, early_exit=True, reason="paused")
        return None

    def _resolve_runtime_frame_dt(self, dt: float) -> FrameUpdateContext:
        if self.game_feel:
            return self._resolve_game_feel_frame_dt(dt)
        return self._resolve_legacy_hit_stop_frame_dt(dt)

    def _resolve_game_feel_frame_dt(self, dt: float) -> FrameUpdateContext:
        dt_efetivo = self.game_feel.update(dt)
        if dt_efetivo == 0:
            self._update_hit_stop_visuals(dt)
            return FrameUpdateContext(dt=dt, dt_efetivo=dt_efetivo, early_exit=True, reason="game_feel_hit_stop")
        return FrameUpdateContext(dt=dt, dt_efetivo=dt_efetivo)

    def _resolve_legacy_hit_stop_frame_dt(self, dt: float) -> FrameUpdateContext:
        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt
            return FrameUpdateContext(dt=dt, dt_efetivo=0.0, early_exit=True, reason="legacy_hit_stop")
        return FrameUpdateContext(dt=dt, dt_efetivo=dt)

    def _collect_pending_runtime_objects(self) -> None:
        for lutador in self.fighters:
            self._collect_fighter_pending_runtime_objects(lutador)

    def _collect_fighter_pending_runtime_objects(self, lutador) -> None:
        self._collect_runtime_buffer(lutador, 'buffer_projeteis', 'projeteis')
        self._prepare_pending_orbs_runtime(lutador)
        self._collect_runtime_buffer(lutador, 'buffer_areas', 'areas')
        self._collect_runtime_buffer(lutador, 'buffer_beams', 'beams')
        self._collect_pending_summons(lutador)
        self._collect_runtime_buffer(lutador, 'buffer_traps', 'traps')

    def _collect_runtime_buffer(self, lutador, buffer_attr: str, target_attr: str) -> None:
        buffer = getattr(lutador, buffer_attr, None)
        if not buffer:
            return

        if not hasattr(self, target_attr):
            setattr(self, target_attr, [])
        getattr(self, target_attr).extend(buffer)
        setattr(lutador, buffer_attr, [])

    def _prepare_pending_orbs_runtime(self, lutador) -> None:
        if hasattr(lutador, 'buffer_orbes') and lutador.buffer_orbes and not hasattr(self, 'orbes'):
            self.orbes = []

    def _collect_pending_summons(self, lutador) -> None:
        summons = getattr(lutador, 'buffer_summons', None)
        if not summons:
            return

        if not hasattr(self, 'summons'):
            self.summons = []
        for summon in summons:
            self._spawn_summon_entry_vfx(summon)
        self.summons.extend(summons)
        lutador.buffer_summons = []

    def _spawn_summon_entry_vfx(self, summon) -> None:
        if not (hasattr(self, 'magic_vfx') and self.magic_vfx):
            return
        elemento = self._resolve_summon_spawn_element(summon)
        self.magic_vfx.spawn_summon(summon.x * PPM, summon.y * PPM, elemento)

    def _resolve_summon_spawn_element(self, summon) -> str:
        nome = getattr(summon, 'nome', '').lower()
        if any(word in nome for word in ["fogo", "fire", "chama"]):
            return "FOGO"
        if any(word in nome for word in ["gelo", "ice"]):
            return "GELO"
        if any(word in nome for word in ["raio", "light"]):
            return "RAIO"
        if any(word in nome for word in ["trevas", "shadow"]):
            return "TREVAS"
        return "ARCANO"

    def _update_runtime_effects(self, dt: float) -> None:
        for efeito in self.impact_flashes:
            efeito.update(dt)
        self.impact_flashes = [efeito for efeito in self.impact_flashes if efeito.vida > 0]

        for efeito in self.magic_clashes:
            efeito.update(dt)
        self.magic_clashes = [efeito for efeito in self.magic_clashes if efeito.vida > 0]

        for efeito in self.block_effects:
            efeito.update(dt)
        self.block_effects = [efeito for efeito in self.block_effects if efeito.vida > 0]

        for efeito in self.dash_trails:
            efeito.update(dt)
        self.dash_trails = [efeito for efeito in self.dash_trails if efeito.vida > 0]

        for efeito in self.hit_sparks:
            efeito.update(dt)
        self.hit_sparks = [efeito for efeito in self.hit_sparks if efeito.vida > 0]

    def _update_magic_vfx_runtime(self, dt: float) -> None:
        if not (hasattr(self, 'magic_vfx') and self.magic_vfx):
            return

        self.magic_vfx.update(dt)
        for proj in self.projeteis:
            elemento_trail = self._get_projetil_elemento(proj)
            trail_vfx = self.magic_vfx.get_or_create_trail(id(proj), elemento_trail)
            vel_proj = getattr(proj, 'vel', getattr(proj, 'vel_disparo', 10.0))
            try:
                vel_proj = float(vel_proj)
            except (TypeError, ValueError):
                vel_proj = 10.0
            if not math.isfinite(vel_proj) or vel_proj <= 0:
                vel_proj = 10.0
            trail_vfx.update(dt, proj.x * PPM, proj.y * PPM, vel_proj * 0.1)

    def _call_runtime_update_with_targets(self, runtime_obj, dt: float, targets):
        if not hasattr(runtime_obj, 'atualizar'):
            return None

        cls = type(runtime_obj)
        if cls not in self._atualizar_sig_cache:
            import inspect

            sig = inspect.signature(runtime_obj.atualizar)
            self._atualizar_sig_cache[cls] = len(sig.parameters) > 1

        if self._atualizar_sig_cache[cls]:
            return runtime_obj.atualizar(dt, targets)

        runtime_obj.atualizar(dt)
        return None

    def _projetil_eh_perfurante(self, proj) -> bool:
        return (
            getattr(proj, 'perfura', False) or
            getattr(proj, 'perfurante', False)
        )

    def _cleanup_orphan_projectile_trails(self) -> None:
        if not (hasattr(self, 'magic_vfx') and self.magic_vfx):
            return

        ids_vivos = {id(proj) for proj in self.projeteis}
        for trail_id in list(self.magic_vfx.trails.keys()):
            if trail_id not in ids_vivos:
                self.magic_vfx.remove_trail(trail_id)

    def __init__(self):
        self._bootstrap_pygame_runtime()
        self._configure_display_runtime()
        self._initialize_runtime_state_defaults()
        self.recarregar_tudo()

    def _bootstrap_pygame_runtime(self) -> None:
        pygame.init()

        # Limpa caches de classe que contÃªm objetos pygame invalidados por pygame.quit()
        SimuladorRenderer._font_cache.clear()

        # Reseta sistema de hitbox global (impede referÃªncias a lutadores antigos)
        from nucleo.hitbox import sistema_hitbox
        sistema_hitbox.ultimo_ataque_info.clear()
        sistema_hitbox.hits_registrados = []

    def _configure_display_runtime(self) -> None:
        # Carrega config primeiro para saber o modo de tela
        self.portrait_mode = self._check_portrait_mode()

        # Define dimensÃµes da tela baseado no modo
        if self.portrait_mode:
            from utilitarios.config import LARGURA_PORTRAIT, ALTURA_PORTRAIT
            self.screen_width = LARGURA_PORTRAIT
            self.screen_height = ALTURA_PORTRAIT
        else:
            self.screen_width = LARGURA
            self.screen_height = ALTURA
        
        self.tela = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Neural Fights - v9.0 ARENA EDITION")
        self.clock = pygame.time.Clock()
        self.rodando = True

    def _initialize_runtime_state_defaults(self) -> None:
        self._initialize_runtime_effect_state()
        self._initialize_runtime_ui_state()
        self._initialize_runtime_match_state()
        self._initialize_runtime_service_refs()

    def _initialize_runtime_effect_state(self) -> None:
        self.cam = Camera(self.screen_width, self.screen_height)
        self.particulas = [] 
        self.decals = [] 
        self.textos = [] 
        self.shockwaves = [] 
        self.projeteis = []
        
        # === NOVOS EFEITOS v7.0 ===
        self.impact_flashes = []
        self.magic_clashes = []
        self.block_effects = []
        self.dash_trails = []
        self.hit_sparks = []

    def _initialize_runtime_ui_state(self) -> None:
        self.paused = False
        self.show_hud = True
        self.show_analysis = False
        self.show_hitbox_debug = DEBUG_VISUAL  # Toggle com tecla H
        self.time_scale = 1.0
        self.slow_mo_timer = 0.0
        self.hit_stop_timer = 0.0 
        self.vencedor = None
        self.rastros = {} 
        self.vida_visual_p1 = 100; self.vida_visual_p2 = 100
        self.direcao_cinematica = {
            "tipo": None,
            "rotulo": "",
            "cor": (255, 220, 120),
            "cor_secundaria": (255, 244, 188),
            "intensidade": 0.0,
            "overlay": 0.0,
            "overlay_timer": 0.0,
            "duracao_overlay": 0.3,
            "evento_id": None,
        }

    def _initialize_runtime_match_state(self) -> None:
        # v13.0: SISTEMA MULTI-COMBATENTE
        self.fighters = []  # Lista de TODOS os lutadores
        self.teams = {}     # {team_id: [lutadores]}
        self.vida_visual = {}  # {lutador: vida_visual} (generalizado)
        self.modo_multi = False  # True quando hÃ¡ mais de 2 lutadores
        self.modo_partida = "duelo"
        self.encounter_config = {}
        self.horde_manager = None
        self.campaign_context = {}
        self.objective_config = {}

        # DES-4: Timer de luta â€” previne lutas infinitas (vencedor por HP ao expirar)
        self.tempo_luta = 0.0
        self.TEMPO_MAX_LUTA = 120.0
        self.pressao_ritmo = {
            "ativa": False,
            "intensidade": 0.0,
            "tempo_sem_dano": 0.0,
            "tempo_ativo": 0.0,
            "ultimo_hp_total": 0.0,
            "ultimo_evento": 0.0,
        }

        # FP-1: cache por classe para saber se atualizar() aceita alvos â€” evita inspect no hot path
        self._atualizar_sig_cache = {}

    def _initialize_runtime_service_refs(self) -> None:
        # Sistema de Coreografia
        self.choreographer = None
        
        # === SISTEMA DE GAME FEEL v8.0 ===
        # Gerencia Hit Stop, Super Armor, Channeling e Camera Feel
        self.game_feel = None
        
        # === SISTEMA DE ARENA v9.0 ===
        self.arena = None
        
        # === SISTEMA DE ÃUDIO v10.0 ===
        self.audio = None

    def _ativar_direcao_cinematica(self, perfil):
        if not isinstance(perfil, dict):
            return

        intensidade = self._resolve_cinematic_direction_intensity(perfil)
        if intensidade <= 0.08:
            return

        evento_id = self._resolve_cinematic_direction_event_id(perfil, intensidade)
        atual = getattr(self, "direcao_cinematica", {})
        if self._refresh_existing_cinematic_direction(atual, evento_id, intensidade, perfil):
            return

        self.direcao_cinematica = self._build_cinematic_direction_state(perfil, intensidade, evento_id)
        self._apply_cinematic_direction_feedback(perfil, intensidade)

    def _resolve_cinematic_direction_intensity(self, perfil) -> float:
        return max(0.0, min(1.0, float(perfil.get("intensidade", 0.0) or 0.0)))

    def _resolve_cinematic_direction_event_id(self, perfil, intensidade: float):
        return (
            perfil.get("tipo"),
            getattr(getattr(perfil.get("lutador"), "dados", None), "nome", None),
            round(intensidade, 2),
        )

    def _refresh_existing_cinematic_direction(self, atual, evento_id, intensidade: float, perfil) -> bool:
        if atual.get("evento_id") != evento_id:
            return False
        atual["intensidade"] = max(atual.get("intensidade", 0.0), intensidade)
        atual["overlay_timer"] = max(atual.get("overlay_timer", 0.0), float(perfil.get("duracao_overlay", 0.25) or 0.25))
        atual["overlay"] = max(atual.get("overlay", 0.0), float(perfil.get("overlay", 0.0) or 0.0))
        return True

    def _build_cinematic_direction_state(self, perfil, intensidade: float, evento_id):
        return {
            "tipo": perfil.get("tipo"),
            "rotulo": perfil.get("rotulo", ""),
            "cor": tuple(perfil.get("cor", (255, 220, 120))),
            "cor_secundaria": tuple(perfil.get("cor_secundaria", (255, 244, 188))),
            "intensidade": intensidade,
            "overlay": float(perfil.get("overlay", 0.0) or 0.0),
            "overlay_timer": float(perfil.get("duracao_overlay", 0.25) or 0.25),
            "duracao_overlay": float(perfil.get("duracao_overlay", 0.25) or 0.25),
            "evento_id": evento_id,
        }

    def _apply_cinematic_direction_feedback(self, perfil, intensidade: float) -> None:
        shake = float(perfil.get("shake", 0.0) or 0.0) * intensidade
        zoom = float(perfil.get("zoom", 0.0) or 0.0) * max(0.5, intensidade)
        if shake > 0.1:
            self.cam.aplicar_shake(shake, 0.08 + intensidade * 0.08)
        if zoom > 0.005:
            self.cam.zoom_punch(zoom, 0.12 + intensidade * 0.08)

        slow_scale = float(perfil.get("slow_scale", 1.0) or 1.0)
        slow_duracao = float(perfil.get("slow_duracao", 0.0) or 0.0)
        if slow_duracao > 0.0 and self.slow_mo_timer <= 0.12:
            self.time_scale = min(self.time_scale, slow_scale)
            self.slow_mo_timer = max(self.slow_mo_timer, slow_duracao)

    def _atualizar_direcao_cinematica(self, dt):
        destaque = resolver_destaque_cinematico(getattr(self, "fighters", []))
        if destaque:
            self._ativar_direcao_cinematica(destaque)

        atual = getattr(self, "direcao_cinematica", None)
        if not isinstance(atual, dict):
            return

        atual["overlay_timer"] = max(0.0, float(atual.get("overlay_timer", 0.0) or 0.0) - dt)
        atual["intensidade"] = max(0.0, float(atual.get("intensidade", 0.0) or 0.0) - dt * 0.9)
        atual["overlay"] = max(0.0, float(atual.get("overlay", 0.0) or 0.0) - dt * 0.75)

        if atual["overlay_timer"] <= 0.0 and atual["intensidade"] <= 0.03:
            atual.update({
                "tipo": None,
                "rotulo": "",
                "intensidade": 0.0,
                "overlay": 0.0,
                "overlay_timer": 0.0,
                "evento_id": None,
            })

    def _resetar_pressao_ritmo(self):
        self.pressao_ritmo = {
            "ativa": False,
            "intensidade": 0.0,
            "tempo_sem_dano": 0.0,
            "tempo_ativo": 0.0,
            "ultimo_hp_total": self._calcular_hp_total_ativo(),
            "ultimo_evento": 0.0,
        }
        for f in getattr(self, "fighters", []) or []:
            brain = getattr(f, "brain", None) or getattr(f, "ai", None)
            if brain is not None:
                brain.pressao_ritmo = 0.0

    def _calcular_hp_total_ativo(self):
        total = 0.0
        for f in getattr(self, "fighters", []) or []:
            if not getattr(f, "morto", False):
                total += float(getattr(f, "vida", 0.0) or 0.0)
        return total

    def _aplicar_pressao_ritmo(self, dt):
        estado = getattr(self, "pressao_ritmo", None)
        if not isinstance(estado, dict):
            return

        hp_total = self._calcular_hp_total_ativo()
        self._update_pressao_ritmo_damage_window(estado, hp_total, dt)
        self._update_pressao_ritmo_activation_state(estado, dt)

        intensidade = float(estado.get("intensidade", 0.0) or 0.0)
        if not estado["ativa"] or intensidade <= 0.01:
            self._reset_fighter_pressao_ritmo()
            return

        centro_x, centro_y = self._resolve_pressao_ritmo_center()
        for f in getattr(self, "fighters", []) or []:
            self._apply_pressao_ritmo_to_fighter(f, intensidade, dt, centro_x, centro_y)

    def _update_pressao_ritmo_damage_window(self, estado, hp_total: float, dt: float) -> None:
        delta_hp = estado.get("ultimo_hp_total", hp_total) - hp_total
        if delta_hp > 0.05:
            self._handle_pressao_ritmo_damage_break(estado)
        else:
            estado["tempo_sem_dano"] += dt
            estado["ultimo_evento"] += dt

        estado["ultimo_hp_total"] = hp_total

    def _handle_pressao_ritmo_damage_break(self, estado) -> None:
        estado["tempo_sem_dano"] = 0.0
        estado["ultimo_evento"] = 0.0
        if estado["ativa"]:
            self.textos.append(FloatingText(
                self.screen_width // 2, self.screen_height // 2 - 40,
                "PRESSAO QUEBRADA!", (120, 240, 200), 24
            ))
        estado["ativa"] = False
        estado["intensidade"] = 0.0
        estado["tempo_ativo"] = 0.0

    def _update_pressao_ritmo_activation_state(self, estado, dt: float) -> None:
        ativar_em = 6.0
        if estado["tempo_sem_dano"] >= ativar_em:
            self._activate_pressao_ritmo(estado, dt, ativar_em)
            return
        self._deactivate_pressao_ritmo(estado, dt)

    def _activate_pressao_ritmo(self, estado, dt: float, ativar_em: float) -> None:
        if not estado["ativa"]:
            self.textos.append(FloatingText(
                self.screen_width // 2, self.screen_height // 2 - 40,
                "PRESSAO DA ARENA!", (255, 196, 92), 26
            ))
        estado["ativa"] = True
        estado["tempo_ativo"] += dt
        estado["intensidade"] = min(1.0, 0.22 + (estado["tempo_sem_dano"] - ativar_em) * 0.085)

    def _deactivate_pressao_ritmo(self, estado, dt: float) -> None:
        estado["ativa"] = False
        estado["tempo_ativo"] = 0.0
        estado["intensidade"] = max(0.0, estado["intensidade"] - dt * 1.2)

    def _reset_fighter_pressao_ritmo(self) -> None:
        for f in getattr(self, "fighters", []) or []:
            brain = getattr(f, "brain", None) or getattr(f, "ai", None)
            if brain is not None:
                brain.pressao_ritmo = 0.0

    def _resolve_pressao_ritmo_center(self):
        centro_x = getattr(self.arena, "centro_x", 0.0) if getattr(self, "arena", None) else 0.0
        centro_y = getattr(self.arena, "centro_y", 0.0) if getattr(self, "arena", None) else 0.0
        if self.arena or not getattr(self, "fighters", None):
            return centro_x, centro_y

        vivos = [f for f in self.fighters if not getattr(f, "morto", False)]
        if not vivos:
            return centro_x, centro_y
        return (
            sum(f.pos[0] for f in vivos) / len(vivos),
            sum(f.pos[1] for f in vivos) / len(vivos),
        )

    def _apply_pressao_ritmo_to_fighter(self, f, intensidade: float, dt: float, centro_x: float, centro_y: float) -> None:
        if getattr(f, "morto", False):
            return

        brain = getattr(f, "brain", None) or getattr(f, "ai", None)
        if brain is not None:
            brain.pressao_ritmo = intensidade
            brain.tedio = max(0.0, getattr(brain, "tedio", 0.0) - dt * (0.20 + intensidade * 0.25))
            brain.excitacao = min(1.0, getattr(brain, "excitacao", 0.0) + dt * (0.05 + intensidade * 0.08))
            brain._agressividade_temp_mod = min(0.45, getattr(brain, "_agressividade_temp_mod", 0.0) + dt * (0.03 + intensidade * 0.05))

        dx = centro_x - f.pos[0]
        dy = centro_y - f.pos[1]
        dist = math.hypot(dx, dy) or 1.0
        if dist > 1.2:
            pull = (0.6 + intensidade * 1.4) * dt
            f.vel[0] += (dx / dist) * pull
            f.vel[1] += (dy / dist) * pull


    def processar_inputs(self):
        for event in pygame.event.get():
            self._handle_runtime_event(event)

        self._apply_manual_camera_controls(pygame.key.get_pressed())

    def _handle_runtime_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.rodando = False
            return
        if event.type == pygame.KEYDOWN:
            self._handle_runtime_keydown(event.key)
            return
        if event.type == pygame.MOUSEWHEEL:
            self._adjust_camera_zoom_from_mousewheel(event.y)

    def _handle_runtime_keydown(self, key) -> None:
        if key == pygame.K_ESCAPE:
            self._play_ui_sound("back")
            self.rodando = False
            return
        if key == pygame.K_r:
            self._play_ui_sound("confirm")
            self.recarregar_tudo()
            return
        if self._handle_runtime_toggle_key(key):
            return
        self._handle_runtime_camera_key(key)

    def _handle_runtime_toggle_key(self, key) -> bool:
        toggle_actions = {
            pygame.K_SPACE: lambda: setattr(self, "paused", not self.paused),
            pygame.K_g: lambda: setattr(self, "show_hud", not self.show_hud),
            pygame.K_h: lambda: setattr(self, "show_hitbox_debug", not self.show_hitbox_debug),
            pygame.K_TAB: lambda: setattr(self, "show_analysis", not self.show_analysis),
            pygame.K_t: lambda: setattr(self, "time_scale", 0.2 if self.time_scale == 1.0 else 1.0),
            pygame.K_f: lambda: setattr(self, "time_scale", 3.0 if self.time_scale == 1.0 else 1.0),
        }
        action = toggle_actions.get(key)
        if not action:
            return False
        self._play_ui_sound("select")
        action()
        return True

    def _handle_runtime_camera_key(self, key) -> None:
        camera_modes = {
            pygame.K_1: "P1",
            pygame.K_2: "P2",
            pygame.K_3: "AUTO",
        }
        mode = camera_modes.get(key)
        if not mode:
            return
        self._play_ui_sound("select")
        self.cam.modo = mode

    def _play_ui_sound(self, sound_name: str) -> None:
        if self.audio:
            self.audio.play_ui(sound_name)

    def _adjust_camera_zoom_from_mousewheel(self, delta: int) -> None:
        self.cam.target_zoom += delta * 0.1
        self.cam.target_zoom = max(0.5, min(self.cam.target_zoom, 3.0))

    def _apply_manual_camera_controls(self, keys) -> None:
        move_speed = 15 / self.cam.zoom
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.cam.y -= move_speed
            self.cam.modo = "MANUAL"
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.cam.y += move_speed
            self.cam.modo = "MANUAL"
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.cam.x -= move_speed
            self.cam.modo = "MANUAL"
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.cam.x += move_speed
            self.cam.modo = "MANUAL"


    def recarregar_tudo(self):
        try:
            self._reload_match_payload()
            self._reset_runtime_state_for_reload()
            self._rebuild_runtime_match_groups()
            self._initialize_runtime_managers_after_reload()
            self._configure_arena_after_reload()
            self._initialize_runtime_tracking_after_reload()
            self._initialize_match_services_after_reload()
                
        except Exception as e:
            # B05: era _log.debug â€” agora visÃ­vel em produÃ§Ã£o
            _log.exception("Erro ao inicializar arena/audio: %s", e)

    def _reload_match_payload(self) -> None:
        self.p1, self.p2, self.cenario, _ = self.carregar_luta_dados()

    def _reset_runtime_state_for_reload(self) -> None:
        self.particulas = []
        self.decals = []
        self.textos = []
        self.shockwaves = []
        self.projeteis = []
        self.impact_flashes = []
        self.magic_clashes = []
        self.block_effects = []
        self.dash_trails = []
        self.hit_sparks = []
        self.summons = []
        self.traps = []
        self.beams = []
        self.areas = []
        self.time_scale = 1.0
        self.slow_mo_timer = 0.0
        self.hit_stop_timer = 0.0
        self.vencedor = None
        self.paused = False
        self.tempo_luta = 0.0
        self._resetar_pressao_ritmo()

    def _rebuild_runtime_match_groups(self) -> None:
        if not self.fighters:
            self.fighters = [f for f in [self.p1, self.p2] if f]

        self.teams = {}
        for lutador in self.fighters:
            team_id = getattr(lutador, 'team_id', 0)
            if team_id not in self.teams:
                self.teams[team_id] = []
            self.teams[team_id].append(lutador)

        self.rastros = {lutador: [] for lutador in self.fighters}
        self.vida_visual = {}
        for lutador in self.fighters:
            if lutador:
                self.vida_visual[lutador] = lutador.vida_max

        if self.p1:
            self.vida_visual_p1 = self.p1.vida_max
        if self.p2:
            self.vida_visual_p2 = self.p2.vida_max

    def _initialize_runtime_managers_after_reload(self) -> None:
        CombatChoreographer.reset()
        self.choreographer = CombatChoreographer.get_instance()
        if self.p1 and self.p2:
            self.choreographer.registrar_lutadores(self.p1, self.p2)

        from ia.team_ai import TeamCoordinatorManager

        TeamCoordinatorManager.reset()
        if self.modo_multi and self.teams and len(self.teams) >= 2:
            TeamCoordinatorManager.get().initialize(self.fighters, self.teams)

        GameFeelManager.reset()
        self.game_feel = GameFeelManager.get_instance()
        self.game_feel.set_camera(self.cam)
        if self.p1 and self.p2:
            self.game_feel.registrar_lutadores(self.p1, self.p2)

        MovementAnimationManager.reset()
        self.movement_anims = MovementAnimationManager.get_instance()
        self.movement_anims.set_ppm(PPM)

        AttackAnimationManager.reset()
        self.attack_anims = AttackAnimationManager()
        self.attack_anims.set_ppm(PPM)

    def _configure_arena_after_reload(self) -> None:
        cenario_nome = getattr(self, 'cenario', 'Arena') or 'Arena'
        if self.modo_multi and cenario_nome == 'Arena':
            cenario_nome = 'Coliseu'
        self.arena = set_arena(cenario_nome)

        self.cam.set_arena_bounds(
            self.arena.centro_x,
            self.arena.centro_y,
            self.arena.largura,
            self.arena.altura,
        )

        if len(self.fighters) >= 2:
            spawn_points = self.arena.get_spawn_points_multi(len(self.fighters), self.teams)
            for i, lutador in enumerate(self.fighters):
                if i < len(spawn_points):
                    lutador.pos[0] = spawn_points[i][0]
                    lutador.pos[1] = spawn_points[i][1]

    def _initialize_runtime_tracking_after_reload(self) -> None:
        self._prev_z = {lutador: 0 for lutador in self.fighters}
        self._prev_acao_ai = {lutador: '' for lutador in self.fighters}

        AudioManager.reset()
        self.audio = AudioManager.get_instance()
        self._prev_stagger = {lutador: False for lutador in self.fighters}
        self._prev_dash = {lutador: 0 for lutador in self.fighters}

        from dados.match_stats import MatchStatsCollector

        self.stats_collector = MatchStatsCollector()
        for lutador in self.fighters:
            if lutador and hasattr(lutador, 'dados'):
                self.stats_collector.register(lutador.dados.nome)
                lutador.stats_collector = self.stats_collector
            lutador.encounter_mode = self.modo_partida
            lutador.objective_config = dict(self.objective_config or {})
            lutador.campaign_context = dict(self.campaign_context or {})
            brain = getattr(lutador, "brain", None)
            if brain is not None:
                brain.encounter_mode = self.modo_partida
                brain.objective_config = dict(self.objective_config or {})
                brain.campaign_context = dict(self.campaign_context or {})

    def _initialize_match_services_after_reload(self) -> None:
        self.horde_manager = None
        if self.modo_partida == "horda":
            self.horde_manager = HordeWaveManager(self, self.encounter_config.get("horda_config") or {})
            self.horde_manager.start()

        MagicVFXManager.reset()
        self.magic_vfx = MagicVFXManager.get_instance()
        self.audio.play_special("arena_start", 0.8)


    def carregar_luta_dados(self):
        try:
            state, config = self._load_match_state_payload()
            self._apply_loaded_match_config(config)
        except Exception as e:
            # B05: era _log.debug â€” agora visÃ­vel em produÃ§Ã£o
            _log.warning("[simulacao] Erro ao ler match_config via AppState: %s", e)
            return None, None, "Arena", False
        montar = self._create_match_character_resolver(state)
        cenario, portrait_mode = self._resolve_match_scene_settings(config)
        team_pair = self._build_team_match_payload(config, montar)
        if team_pair:
            return team_pair[0], team_pair[1], cenario, portrait_mode

        l1, l2 = self._build_duel_match_payload(config, montar)
        self._load_duel_rival_memories(l1, l2)
        return l1, l2, cenario, portrait_mode

    def _load_match_state_payload(self):
        from dados.app_state import AppState

        state = AppState.get()
        config = normalize_match_config(state.match_config)
        teams_config = config.get("teams") or []
        has_duel = bool(config.get("p1_nome") and config.get("p2_nome"))
        has_teams = bool(teams_config)
        if not has_duel and not has_teams:
            raise ValueError("match_config vazio â€” nenhum personagem ou equipe selecionada")
        return state, config

    def _apply_loaded_match_config(self, config) -> None:
        self.encounter_config = config
        self.modo_partida = config.get("modo_partida", "duelo")
        self.campaign_context = dict(config.get("campaign_context") or {})
        self.objective_config = dict(config.get("objective_config") or {})

    def _create_match_character_resolver(self, state):
        todos = state.characters
        armas = state.weapons

        def montar(nome):
            personagem = next((x for x in todos if x.nome == nome), None)
            if personagem and personagem.nome_arma:
                personagem.arma_obj = next((a for a in armas if a.nome == personagem.nome_arma), None)
                if personagem.arma_obj and hasattr(personagem.arma_obj, 'durabilidade_max'):
                    personagem.arma_obj.durabilidade = personagem.arma_obj.durabilidade_max
                    personagem.arma_obj._aviso_quebrada_exibido = False
            return personagem

        return montar

    def _resolve_match_scene_settings(self, config):
        return config.get("cenario", "Arena"), config.get("portrait_mode", False)

    def _build_team_match_payload(self, config, montar):
        teams_config = config.get("teams") or []
        if not (teams_config and isinstance(teams_config, list)):
            return None

        all_fighters = []
        for team_cfg in teams_config:
            tid = team_cfg.get("team_id", 0)
            for nome in team_cfg.get("members", []):
                dados = montar(nome)
                if dados:
                    all_fighters.append(Lutador(dados, 0, 0, team_id=tid))

        if not all_fighters:
            return None

        self.fighters = all_fighters
        teams_distintos = {f.team_id for f in all_fighters}
        self.modo_multi = len(all_fighters) > 2 or len(teams_distintos) > 1
        l1 = all_fighters[0]
        l2 = next(
            (f for f in all_fighters if f.team_id != l1.team_id),
            all_fighters[1] if len(all_fighters) > 1 else all_fighters[0],
        )
        return l1, l2

    def _build_duel_match_payload(self, config, montar):
        l1 = Lutador(montar(config["p1_nome"]), 5.0, 8.0, team_id=0)
        l2 = Lutador(montar(config["p2_nome"]), 19.0, 8.0, team_id=1)
        self.fighters = [l1, l2]
        self.modo_partida = "duelo"
        self.modo_multi = False
        return l1, l2

    def _load_duel_rival_memories(self, l1, l2) -> None:
        self._load_single_rival_memory(l1, l2, "l1")
        self._load_single_rival_memory(l2, l1, "l2")

    def _load_single_rival_memory(self, origem, rival, label: str) -> None:
        try:
            brain = getattr(origem, 'brain', None)
            if brain and hasattr(brain, 'carregar_memoria_rival'):
                brain.carregar_memoria_rival(rival)
        except Exception as _e:
            _log.warning("[IA] carregar_memoria_rival %s falhou: %s", label, _e)


    def update(self, dt):
        frame = self._prepare_frame_update(dt)
        if frame.early_exit:
            return

        self._collect_pending_runtime_objects()
        self._update_runtime_effects(frame.dt)
        self._update_magic_vfx_runtime(frame.dt)
        self._update_projectile_phase(frame.dt)
        self._update_orb_phase(frame.dt)
        self._update_area_phase(frame.dt)
        self._update_beam_phase(frame.dt)
        self._update_summon_phase(frame.dt)
        self._update_trap_phase(frame.dt)
        self._update_transformation_phase(frame.dt)
        self._update_channel_phase(frame.dt)
        self._update_active_match_state(frame.dt)
        self._update_post_frame_systems(frame.dt)

    def _update_projectile_phase(self, dt):
        self._process_projectile_clash_phase()
        novos_projeteis = self._run_projectile_updates(dt)
        self._finalize_projectile_phase(novos_projeteis)

    def _process_projectile_clash_phase(self) -> None:
        self._verificar_clash_projeteis()

    def _run_projectile_updates(self, dt: float):
        novos_projeteis = []
        for proj in self.projeteis:
            self._update_single_projectile(proj, dt, novos_projeteis)
        return novos_projeteis

    def _update_single_projectile(self, proj, dt: float, novos_projeteis) -> None:
        resultado = self._call_runtime_update_with_targets(proj, dt, self.fighters)
        self._process_projectile_special_result(proj, resultado, novos_projeteis)

        alvo = self._encontrar_alvo_mais_proximo(proj.x, proj.y, proj.dono)
        if alvo is None:
            return

        if self._projectile_neutralized_before_hit(proj, alvo):
            return

        if not self._projectile_collides_with_target(proj, alvo):
            return

        self._apply_projectile_hit(proj, alvo, novos_projeteis)

    def _apply_projectile_hit(self, proj, alvo, novos_projeteis) -> None:
        if not proj.ativo:
            return

        impacto = self._create_projectile_impact_context(proj, alvo)
        self._apply_projectile_initial_feedback(proj, impacto)
        perfil = self._build_projectile_damage_profile(proj, alvo)
        if not self._resolve_projectile_penetration_policy(proj, alvo):
            return
        self._apply_projectile_damage_and_primary_outcome(proj, alvo, impacto, perfil)
        self._apply_projectile_post_hit_effects(proj, alvo, impacto, perfil, novos_projeteis)

    def _create_projectile_impact_context(self, proj, alvo) -> ProjectileImpactContext:
        cor_impacto = proj.cor if hasattr(proj, 'cor') else BRANCO
        dx = alvo.pos[0] - proj.x
        dy = alvo.pos[1] - proj.y
        dist = math.hypot(dx, dy) or 1
        direcao_impacto = math.atan2(dy, dx)
        return ProjectileImpactContext(
            cor_impacto=cor_impacto,
            dx=dx,
            dy=dy,
            dist=dist,
            direcao_impacto=direcao_impacto,
        )

    def _apply_projectile_initial_feedback(self, proj, impacto: ProjectileImpactContext) -> None:
        if self.audio:
            tipo_proj = proj.tipo if hasattr(proj, 'tipo') else "energy"
            listener_x = self.cam.x / PPM
            self.audio.play_skill("PROJETIL", tipo_proj, proj.x, listener_x, phase="impact")

        self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, impacto.cor_impacto, 1.2, "magic"))
        self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, impacto.cor_impacto, tamanho=1.2))
        self.hit_sparks.append(
            HitSpark(proj.x * PPM, proj.y * PPM, impacto.cor_impacto, impacto.direcao_impacto, 1.0)
        )
        self._spawn_projectile_magic_impact_vfx(proj)

    def _spawn_projectile_magic_impact_vfx(self, proj) -> None:
        if not (hasattr(self, 'magic_vfx') and self.magic_vfx):
            return

        elemento = self._resolve_projectile_impact_element(proj)
        dano_proj = getattr(proj, 'dano', 10)
        self.magic_vfx.spawn_explosion(
            proj.x * PPM, proj.y * PPM,
            elemento=elemento,
            tamanho=0.6 + dano_proj * 0.02,
            dano=dano_proj
        )

    def _resolve_projectile_impact_element(self, proj) -> str:
        elemento = self._resolve_projectile_impact_element_from_keywords(proj)
        if elemento:
            return elemento
        elemento = self._resolve_projectile_impact_element_from_color(proj)
        if elemento:
            return elemento
        return "DEFAULT"

    def _resolve_projectile_impact_element_from_keywords(self, proj):
        tipo_proj_str = str(getattr(proj, 'tipo', '')).lower()
        nome_skill = str(getattr(proj, 'nome', '')).lower()
        combined = nome_skill + tipo_proj_str
        if any(w in combined for w in ["fogo", "fire", "chama", "meteoro", "inferno", "brasas"]):
            return "FOGO"
        if any(w in combined for w in ["gelo", "ice", "glacial", "nevasca", "congelar"]):
            return "GELO"
        if any(w in combined for w in ["raio", "lightning", "thunder", "eletric", "relampago"]):
            return "RAIO"
        if any(w in combined for w in ["trevas", "shadow", "dark", "sombra", "necro"]):
            return "TREVAS"
        if any(w in combined for w in ["luz", "light", "holy", "sagrado", "divino"]):
            return "LUZ"
        if any(w in combined for w in ["natureza", "nature", "veneno", "poison", "planta"]):
            return "NATUREZA"
        if any(w in combined for w in ["arcano", "arcane", "mana"]):
            return "ARCANO"
        if any(w in combined for w in ["sangue", "blood", "vampir"]):
            return "SANGUE"
        if any(w in combined for w in ["void", "vazio"]):
            return "VOID"
        return None

    def _resolve_projectile_impact_element_from_color(self, proj):
        if not (hasattr(proj, 'cor') and proj.cor):
            return None
        r, g, b = proj.cor[:3]
        if r > 200 and g < 100:
            return "FOGO"
        if b > 200 and r < 150:
            return "RAIO" if g > 150 else "GELO"
        if g > 180 and r < 150 and b < 150:
            return "NATUREZA"
        if r > 180 and b > 180 and g < 100:
            return "ARCANO"
        return None

    def _build_projectile_damage_profile(self, proj, alvo) -> ProjectileDamageProfile:
        bonus_condicao = self._resolve_projectile_condition_bonus(proj, alvo)
        reacao_nome, reacao_efeito, mult_reacao = self._resolve_projectile_elemental_reaction(proj, alvo)
        perfil = self._finalize_projectile_damage_profile(
            proj,
            bonus_condicao,
            reacao_nome,
            reacao_efeito,
            mult_reacao,
        )
        self._apply_projectile_reaction_feedback(alvo, reacao_nome)
        self._apply_projectile_damage_tempo_feedback(perfil.dano_final)
        return perfil

    def _resolve_projectile_condition_bonus(self, proj, alvo) -> float:
        if hasattr(proj, 'verificar_condicao'):
            return proj.verificar_condicao(alvo)
        return 1.0

    def _resolve_projectile_elemental_reaction(self, proj, alvo):
        elem_proj = getattr(proj, 'elemento', None)
        if not elem_proj:
            return None, None, 1.0

        elem_alvo = self._resolve_target_element_from_status_effects(alvo)
        if not elem_alvo or elem_alvo == elem_proj:
            return None, None, 1.0

        try:
            from nucleo.magic_system import verificar_reacao_elemental, Elemento

            e1 = Elemento[elem_proj] if elem_proj in Elemento.__members__ else None
            e2 = Elemento[elem_alvo] if elem_alvo in Elemento.__members__ else None
            if e1 and e2:
                reacao = verificar_reacao_elemental(e1, e2)
                if reacao:
                    return reacao
        except Exception as _e_reacao:
            _log.debug("ReaÃ§Ã£o elemental indisponÃ­vel: %s", _e_reacao)

        return None, None, 1.0

    def _resolve_target_element_from_status_effects(self, alvo):
        for se in getattr(alvo, 'status_effects', []):
            nome_status = getattr(se, 'nome', '').upper()
            if nome_status in ("QUEIMANDO", "QUEIMADURA_SEVERA"):
                return "FOGO"
            if nome_status in ("LENTO", "CONGELADO"):
                return "GELO"
            if nome_status == "PARALISIA":
                return "RAIO"
            if nome_status == "ENVENENADO":
                return "NATUREZA"
            if nome_status == "SANGRANDO":
                return "SANGUE"
        return None

    def _finalize_projectile_damage_profile(
        self,
        proj,
        bonus_condicao: float,
        reacao_nome,
        reacao_efeito,
        mult_reacao: float,
    ) -> ProjectileDamageProfile:
        dono_proj = getattr(proj, 'dono', None)
        dano_base = (
            dono_proj.get_dano_modificado(proj.dano)
            if dono_proj and hasattr(dono_proj, 'get_dano_modificado')
            else proj.dano
        )
        dano_final = dano_base * bonus_condicao
        if reacao_nome:
            dano_final *= mult_reacao

        tipo_efeito = getattr(proj, 'tipo_efeito', "NORMAL")
        if reacao_efeito and reacao_efeito not in ("DANO_BONUS", "PURGE"):
            tipo_efeito = reacao_efeito

        return ProjectileDamageProfile(
            dano_final=dano_final,
            tipo_efeito=tipo_efeito,
            bonus_condicao=bonus_condicao,
            source_type=self._resolve_projectile_source_type(proj),
        )

    def _resolve_projectile_source_type(self, proj) -> str:
        if proj.__class__.__name__ in {"ArmaProjetil", "FlechaProjetil", "OrbeMagico"}:
            return "weapon"
        return "skill"

    def _apply_projectile_reaction_feedback(self, alvo, reacao_nome) -> None:
        if not reacao_nome:
            return

        self.textos.append(FloatingText(
            alvo.pos[0] * PPM, alvo.pos[1] * PPM - 70,
            reacao_nome, (255, 220, 80), 24
        ))

    def _apply_projectile_damage_tempo_feedback(self, dano_final: float) -> None:
        if dano_final > 8:
            shake_intensity = min(10.0, 2.0 + dano_final * 0.15)
            self.cam.aplicar_shake(shake_intensity, 0.07)
        self.hit_stop_timer = 0.02

    def _resolve_projectile_penetration_policy(self, proj, alvo) -> bool:
        eh_perfurante = self._projetil_eh_perfurante(proj)
        if eh_perfurante:
            if hasattr(proj, 'pode_atingir') and not proj.pode_atingir(alvo):
                return False
            if not hasattr(proj, 'alvos_perfurados') or proj.alvos_perfurados is None:
                proj.alvos_perfurados = set()
            if id(alvo) in proj.alvos_perfurados:
                return False
            proj.alvos_perfurados.add(id(alvo))
            return True

        proj.ativo = False
        self._remover_trail_projetil(proj)
        return True

    def _apply_projectile_damage_and_primary_outcome(
        self,
        proj,
        alvo,
        impacto: ProjectileImpactContext,
        perfil: ProjectileDamageProfile,
    ) -> None:
        self._registrar_hit_stats(
            proj.dono, alvo, perfil.dano_final,
            elemento=perfil.tipo_efeito,
            source_type=perfil.source_type,
            source_name=getattr(proj, 'nome', ''),
        )
        if alvo.tomar_dano(perfil.dano_final, impacto.dx / impacto.dist, impacto.dy / impacto.dist, perfil.tipo_efeito):
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, proj.dono.dados.nome)
        else:
            if perfil.bonus_condicao >= 5.0:
                self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "EXECUÃ‡ÃƒO!", (200, 50, 50), 32))

            if hasattr(proj, 'tipo') and proj.tipo in ["faca", "shuriken", "chakram", "flecha"]:
                cor_txt = proj.cor if hasattr(proj, 'cor') else BRANCO
            else:
                cor_txt = self._get_cor_efeito(perfil.tipo_efeito)
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(perfil.dano_final), cor_txt))
            self._spawn_particulas_efeito(alvo.pos[0] * PPM, alvo.pos[1] * PPM, perfil.tipo_efeito)

    def _apply_projectile_post_hit_effects(
        self,
        proj,
        alvo,
        impacto: ProjectileImpactContext,
        perfil: ProjectileDamageProfile,
        novos_projeteis,
    ) -> None:
        self._apply_projectile_lifesteal_effect(proj, perfil)
        self._spawn_projectile_explosion_effect(proj, impacto, perfil)
        self._apply_projectile_shatter_effect(proj, alvo, perfil)
        self._apply_projectile_chain_effect(proj, alvo, novos_projeteis)

    def _apply_projectile_lifesteal_effect(self, proj, perfil: ProjectileDamageProfile) -> None:
        if hasattr(proj, 'lifesteal') and proj.lifesteal > 0:
            cura = perfil.dano_final * proj.lifesteal
            proj.dono.vida = min(proj.dono.vida_max, proj.dono.vida + cura)
            self.textos.append(FloatingText(
                proj.dono.pos[0] * PPM, proj.dono.pos[1] * PPM - 30,
                f"+{int(cura)}", (200, 100, 200), 16
            ))
            return

        if perfil.tipo_efeito == "DRENAR":
            cura = perfil.dano_final * 0.15
            proj.dono.vida = min(proj.dono.vida_max, proj.dono.vida + cura)
            self.textos.append(FloatingText(
                proj.dono.pos[0] * PPM, proj.dono.pos[1] * PPM - 30,
                f"+{int(cura)}", (100, 255, 150), 16
            ))

    def _spawn_projectile_explosion_effect(
        self,
        proj,
        impacto: ProjectileImpactContext,
        perfil: ProjectileDamageProfile,
    ) -> None:
        if not (hasattr(proj, 'raio_explosao') and proj.raio_explosao > 0):
            return

        from nucleo.combat import AreaEffect

        explosao = AreaEffect(proj.nome + " ExplosÃ£o", proj.x, proj.y, proj.dono)
        explosao.raio_max = proj.raio_explosao
        explosao.dano = proj.dano * 0.5
        explosao.tipo_efeito = perfil.tipo_efeito
        if hasattr(self, 'areas'):
            self.areas.append(explosao)
        self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, impacto.cor_impacto, 2.0, "explosion"))
        self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, impacto.cor_impacto, tamanho=2.5))
        self._spawn_particulas_efeito(proj.x * PPM, proj.y * PPM, "EXPLOSAO")

    def _apply_projectile_shatter_effect(self, proj, alvo, perfil: ProjectileDamageProfile) -> None:
        if not (hasattr(proj, 'remove_congelamento') and proj.remove_congelamento):
            return
        if not getattr(alvo, 'congelado', False):
            return

        alvo.congelado = False
        dano_shatter = perfil.dano_final * 0.5
        self._registrar_hit_stats(
            proj.dono, alvo, dano_shatter,
            elemento="GELO",
            source_type="status",
            source_name=f"{getattr(proj, 'nome', 'Projetil')} (Shatter)",
        )
        if alvo.tomar_dano(dano_shatter, 0, 0, "GELO"):
            self._registrar_kill(alvo, proj.dono.dados.nome)
        self.textos.append(FloatingText(
            alvo.pos[0] * PPM, alvo.pos[1] * PPM - 60,
            "SHATTER!", (180, 220, 255), 24
        ))

    def _apply_projectile_chain_effect(self, proj, alvo, novos_projeteis) -> None:
        if not (hasattr(proj, 'chain') and proj.chain > 0 and proj.chain_count < proj.chain):
            return

        prox_alvo, dx, dy = self._find_projectile_chain_target(proj, alvo)
        if not prox_alvo:
            return

        self._spawn_projectile_chain_link(proj, alvo, prox_alvo, dx, dy, novos_projeteis)

    def _find_projectile_chain_target(self, proj, alvo):
        alvos_possiveis = [
            lutador for lutador in self.fighters
            if lutador != alvo and not lutador.morto and id(lutador) not in proj.chain_targets
        ]
        if not alvos_possiveis:
            return None, 0.0, 0.0

        prox_alvo = alvos_possiveis[0]
        dx = prox_alvo.pos[0] - alvo.pos[0]
        dy = prox_alvo.pos[1] - alvo.pos[1]
        dist = math.hypot(dx, dy)
        chain_range = getattr(proj, 'raio_contagio', 5.0)
        if dist > chain_range:
            return None, dx, dy
        return prox_alvo, dx, dy

    def _spawn_projectile_chain_link(self, proj, alvo, prox_alvo, dx, dy, novos_projeteis) -> None:
        from nucleo.combat import Projetil

        proj.chain_count += 1
        proj.chain_targets.add(id(alvo))
        chain_proj = Projetil(proj.nome, alvo.pos[0], alvo.pos[1], math.atan2(dy, dx), proj.dono)
        chain_proj.dano = proj.dano * proj.chain_decay
        chain_proj.chain = proj.chain
        chain_proj.chain_count = proj.chain_count
        chain_proj.chain_targets = proj.chain_targets.copy()
        chain_proj.cor = proj.cor if hasattr(proj, 'cor') else (150, 200, 255)
        novos_projeteis.append(chain_proj)
        self._spawn_particulas_efeito(alvo.pos[0] * PPM, alvo.pos[1] * PPM, "ELETRICO")

    def _process_projectile_special_result(self, proj, resultado, novos_projeteis) -> None:
        if not resultado:
            return

        if resultado.get("duplicar"):
            from nucleo.combat import Projetil

            novo = Projetil(proj.nome, resultado["x"], resultado["y"], resultado["angulo"], proj.dono)
            novo.dano = proj.dano * 0.7
            novo.duplicado = True
            novos_projeteis.append(novo)
        elif resultado.get("split"):
            from nucleo.combat import Projetil

            novo = Projetil(proj.nome, resultado["x"], resultado["y"], resultado["angulo"], proj.dono)
            novo.dano = proj.dano * 0.5
            novo.split_aleatorio = False
            novos_projeteis.append(novo)
        elif resultado.get("explodir"):
            from nucleo.combat import AreaEffect

            area = AreaEffect(proj.nome, resultado["x"], resultado["y"], proj.dono)
            area.raio = resultado.get("raio", 2.0)
            if hasattr(self, 'areas'):
                self.areas.append(area)
            self.impact_flashes.append(ImpactFlash(resultado["x"] * PPM, resultado["y"] * PPM, proj.cor, 2.0, "explosion"))
            self.shockwaves.append(Shockwave(resultado["x"] * PPM, resultado["y"] * PPM, proj.cor, tamanho=2.5))
            self._spawn_particulas_efeito(resultado["x"] * PPM, resultado["y"] * PPM, "EXPLOSAO")

    def _projectile_neutralized_before_hit(self, proj, alvo) -> bool:
        bloqueado = self._verificar_bloqueio_projetil(proj, alvo)
        if bloqueado:
            proj.ativo = False
            self._remover_trail_projetil(proj)
            return True

        if not self.arena:
            return False

        obs_hit = self.arena.colide_obstaculo(proj.x, proj.y, getattr(proj, 'raio', 0.3))
        if not (obs_hit and obs_hit.solido):
            return False

        destruido = self.arena.danificar_obstaculo(obs_hit, getattr(proj, 'dano', 10))
        proj.ativo = False
        self._remover_trail_projetil(proj)
        if destruido:
            self._spawn_particulas_efeito(obs_hit.x * PPM, obs_hit.y * PPM, "EXPLOSAO")
            self.textos.append(FloatingText(obs_hit.x * PPM, obs_hit.y * PPM - 30, "DESTRUÃDO!", (255, 180, 50), 22))
        return True

    def _projectile_collides_with_target(self, proj, alvo) -> bool:
        if hasattr(proj, 'colidir'):
            return proj.colidir(alvo)

        dx = alvo.pos[0] - proj.x
        dy = alvo.pos[1] - proj.y
        dist = math.hypot(dx, dy)
        return dist < (alvo.raio_fisico + proj.raio) and proj.ativo

    def _finalize_projectile_phase(self, novos_projeteis) -> None:
        self.projeteis.extend(novos_projeteis)
        self.projeteis = [proj for proj in self.projeteis if proj.ativo]
        self._cleanup_orphan_projectile_trails()

    def _update_orb_phase(self, dt):
        for orbe in self._iter_runtime_orbs():
            self._update_single_orb(orbe)

    def _iter_runtime_orbs(self):
        for lutador in self.fighters:
            for orbe in getattr(lutador, 'buffer_orbes', []):
                yield orbe

    def _update_single_orb(self, orbe) -> None:
        if not (orbe.ativo and orbe.estado == "disparando"):
            return
        alvo = self._resolve_orb_target(orbe)
        if alvo is None or not orbe.colidir(alvo):
            return
        self._apply_orb_hit(orbe, alvo)

    def _resolve_orb_target(self, orbe):
        return self._encontrar_alvo_mais_proximo(orbe.x, orbe.y, orbe.dono)

    def _apply_orb_hit(self, orbe, alvo) -> None:
        orbe.ativo = False
        if self.audio:
            listener_x = self.cam.x / PPM
            self.audio.play_skill("PROJETIL", "orbe_magico", orbe.x, listener_x, phase="impact")

        self.shockwaves.append(Shockwave(orbe.x * PPM, orbe.y * PPM, orbe.cor, tamanho=1.5))
        dx = alvo.pos[0] - orbe.x
        dy = alvo.pos[1] - orbe.y
        dist = math.hypot(dx, dy) or 1
        dano_final = orbe.dono.get_dano_modificado(orbe.dano) if hasattr(orbe.dono, 'get_dano_modificado') else orbe.dano

        self._registrar_hit_stats(
            orbe.dono, alvo, dano_final,
            elemento="NORMAL",
            source_type="weapon",
            source_name="Orbe Magico",
        )
        if alvo.tomar_dano(dano_final, dx / dist, dy / dist, "NORMAL"):
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, orbe.dono.dados.nome)
        else:
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano_final), orbe.cor))
            self._spawn_particulas_efeito(alvo.pos[0] * PPM, alvo.pos[1] * PPM, "NORMAL")


    def _update_area_phase(self, dt):
        if not hasattr(self, 'areas'):
            return

        novas_areas = self._run_area_updates(dt)
        self._finalize_area_phase(novas_areas)

    def _run_area_updates(self, dt: float):
        novas_areas = []
        for area in self.areas:
            self._update_single_area(area, dt, novas_areas)
        return novas_areas

    def _update_single_area(self, area, dt: float, novas_areas) -> None:
        resultado = self._call_runtime_update_with_targets(area, dt, self.fighters)
        self._process_area_results(area, resultado, dt, novas_areas)
        self._process_area_collisions(area)

    def _process_area_results(self, area, resultado, dt: float, novas_areas) -> None:
        if not resultado:
            return

        for res in resultado:
            self._process_single_area_result(area, res, dt, novas_areas)

    def _process_single_area_result(self, area, res, dt: float, novas_areas) -> None:
        if res.get("nova_onda"):
            self._handle_area_nova_wave_result(area, res, novas_areas)
        elif res.get("meteoro"):
            self._handle_area_meteor_result(area, res, novas_areas)
        elif res.get("pull"):
            self._handle_area_pull_result(area, res, dt)
        elif res.get("dot_tick"):
            self._handle_area_dot_tick_result(area, res)

    def _handle_area_nova_wave_result(self, area, res, novas_areas) -> None:
        from nucleo.combat import AreaEffect

        _nx = res.get("x", area.x)
        _ny = res.get("y", area.y)
        nova = AreaEffect(area.nome + " Onda", _nx, _ny, area.dono)
        nova.raio = res.get("raio", area.raio * 1.5)
        nova.dano = area.dano * 0.7
        nova.tipo_efeito = area.tipo_efeito
        novas_areas.append(nova)

    def _handle_area_meteor_result(self, area, res, novas_areas) -> None:
        from nucleo.combat import AreaEffect

        meteoro = AreaEffect("Meteoro", res["x"], res["y"], area.dono)
        meteoro.raio = res.get("raio", 3.0)
        meteoro.dano = res.get("dano", 30)
        meteoro.tipo_efeito = "FOGO"
        novas_areas.append(meteoro)
        self.impact_flashes.append(ImpactFlash(res["x"] * PPM, res["y"] * PPM, (255, 100, 50), 2.0, "explosion"))
        self.shockwaves.append(Shockwave(res["x"] * PPM, res["y"] * PPM, (255, 100, 50), tamanho=2.5))
        self._spawn_particulas_efeito(res["x"] * PPM, res["y"] * PPM, "FOGO")

    def _handle_area_pull_result(self, area, res, dt: float) -> None:
        alvo = res["alvo"]
        forca = res.get("forca", 5.0)
        dx = area.x - alvo.pos[0]
        dy = area.y - alvo.pos[1]
        dist = math.hypot(dx, dy) or 1
        if hasattr(alvo, 'vel'):
            alvo.vel[0] += (dx / dist) * forca * dt
            alvo.vel[1] += (dy / dist) * forca * dt

    def _handle_area_dot_tick_result(self, area, res) -> None:
        alvo = res["alvo"]
        dano_dot = res.get("dano", 5)
        tipo_dot = res.get("tipo", "FOGO")
        self._registrar_hit_stats(
            area.dono, alvo, dano_dot,
            elemento=tipo_dot,
            source_type="status",
            source_name=f"{getattr(area, 'nome', 'Area')} (DoT)",
        )
        if alvo.tomar_dano(dano_dot, 0, 0, tipo_dot):
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, area.dono.dados.nome)
        else:
            cor_dot = self._get_cor_efeito(tipo_dot)
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano_dot), cor_dot, 14))

    def _process_area_collisions(self, area) -> None:
        if not (area.ativo and getattr(area, 'ativado', True)):
            return

        for alvo, dx, dy, dist in self._iter_area_collision_targets(area):
            self._apply_area_collision_hit(area, alvo, dx, dy, dist)

    def _iter_area_collision_targets(self, area):
        for alvo in self.fighters:
            if alvo == area.dono or alvo in area.alvos_atingidos:
                continue
            dx = alvo.pos[0] - area.x
            dy = alvo.pos[1] - area.y
            dist = math.hypot(dx, dy)
            if dist >= area.raio_atual + alvo.raio_fisico:
                continue
            yield alvo, dx, dy, dist

    def _apply_area_collision_hit(self, area, alvo, dx: float, dy: float, dist: float) -> None:
        area.alvos_atingidos.add(alvo)
        if self.audio:
            listener_x = self.cam.x / PPM
            skill_name = getattr(area, 'nome_skill', '')
            self.audio.play_skill("AREA", skill_name, area.x, listener_x, phase="impact")

        dano = area.dono.get_dano_modificado(area.dano) if hasattr(area.dono, 'get_dano_modificado') else area.dano
        self._registrar_hit_stats(
            area.dono, alvo, dano,
            elemento=area.tipo_efeito,
            source_type="skill",
            source_name=getattr(area, 'nome', ''),
        )
        if alvo.tomar_dano(dano, dx / (dist or 1), dy / (dist or 1), area.tipo_efeito):
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, area.dono.dados.nome)
        else:
            cor_txt = self._get_cor_efeito(area.tipo_efeito)
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano), cor_txt))

    def _finalize_area_phase(self, novas_areas) -> None:
        self.areas.extend(novas_areas)
        self.areas = [area for area in self.areas if area.ativo]

    def _update_beam_phase(self, dt):
        if not hasattr(self, 'beams'):
            return
        for beam in self.beams:
            self._update_single_beam(beam, dt)
        self._finalize_beam_phase()

    def _update_single_beam(self, beam, dt: float) -> None:
        beam.atualizar(dt)
        if not (beam.ativo and not beam.hit_aplicado):
            return
        alvo = self._resolve_beam_target(beam)
        if alvo is None or not self._beam_colide_alvo(beam, alvo):
            return
        self._apply_beam_hit(beam, alvo)

    def _resolve_beam_target(self, beam):
        return self._encontrar_alvo_mais_proximo(beam.dono.pos[0], beam.dono.pos[1], beam.dono)

    def _apply_beam_hit(self, beam, alvo) -> None:
        beam.hit_aplicado = True
        if self.audio:
            listener_x = self.cam.x / PPM
            skill_name = getattr(beam, 'nome_skill', '')
            self.audio.play_skill("BEAM", skill_name, beam.dono.pos[0], listener_x, phase="impact")

        dano = beam.dono.get_dano_modificado(beam.dano) if hasattr(beam.dono, 'get_dano_modificado') else beam.dano
        dx = alvo.pos[0] - beam.dono.pos[0]
        dy = alvo.pos[1] - beam.dono.pos[1]
        dist = math.hypot(dx, dy) or 1
        self._apply_beam_shield_penetration(beam, alvo)
        self._registrar_hit_stats(
            beam.dono, alvo, dano,
            elemento=beam.tipo_efeito,
            source_type="skill",
            source_name=getattr(beam, 'nome', ''),
        )
        if alvo.tomar_dano(dano, dx / dist, dy / dist, beam.tipo_efeito):
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, beam.dono.dados.nome)
        else:
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano), (255, 255, 100)))
            self.cam.aplicar_shake(5.0, 0.06)

    def _apply_beam_shield_penetration(self, beam, alvo) -> None:
        if not getattr(beam, 'penetra_escudo', False):
            return
        for buff in getattr(alvo, 'buffs_ativos', []):
            if getattr(buff, 'escudo_atual', 0) > 0:
                buff.escudo_atual = 0

    def _finalize_beam_phase(self) -> None:
        self.beams = [b for b in self.beams if b.ativo]

    def _update_summon_phase(self, dt):
        if not hasattr(self, 'summons'):
            return

        self._run_summon_updates(dt)
        self._process_projectile_vs_summon_phase()
        self._finalize_summon_phase()

    def _run_summon_updates(self, dt: float) -> None:
        for summon in self.summons:
            self._update_single_summon(summon, dt)

    def _update_single_summon(self, summon, dt: float) -> None:
        resultados = summon.atualizar(dt, self.fighters)
        for res in resultados:
            self._process_single_summon_result(summon, res)

    def _process_single_summon_result(self, summon, res) -> None:
        if res.get("tipo") == "ataque":
            self._handle_summon_attack_result(summon, res)
        elif res.get("tipo") == "aura":
            self._handle_summon_aura_result(summon, res)
        elif res.get("revive"):
            self._handle_summon_revive_result(res)

    def _handle_summon_attack_result(self, summon, res) -> None:
        alvo = res["alvo"]
        dano = res["dano"]
        efeito = res.get("efeito", "NORMAL")
        dx = alvo.pos[0] - summon.x
        dy = alvo.pos[1] - summon.y
        dist = math.hypot(dx, dy) or 1
        self._registrar_hit_stats(
            summon.dono, alvo, dano,
            elemento=efeito,
            source_type="summon",
            source_name=getattr(summon, 'nome', 'Summon'),
        )
        if alvo.tomar_dano(dano, dx / dist, dy / dist, efeito):
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, summon.dono.dados.nome)
        else:
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano), summon.cor))
            self.cam.aplicar_shake(3.0, 0.05)

    def _handle_summon_aura_result(self, summon, res) -> None:
        alvo = res["alvo"]
        dano = res["dano"]
        efeito = res.get("efeito", "NORMAL")
        self._registrar_hit_stats(
            summon.dono, alvo, dano,
            elemento=efeito,
            source_type="summon",
            source_name=f"{getattr(summon, 'nome', 'Summon')} (Aura)",
        )
        if alvo.tomar_dano(dano, 0, 0, efeito):
            self._registrar_kill(alvo, summon.dono.dados.nome)

    def _handle_summon_revive_result(self, res) -> None:
        self.textos.append(FloatingText(res["x"] * PPM, res["y"] * PPM - 30, "REVIVE!", (255, 200, 50), 28))
        self._spawn_particulas_efeito(res["x"] * PPM, res["y"] * PPM, "FOGO")

    def _process_projectile_vs_summon_phase(self) -> None:
        for proj in self.projeteis:
            self._process_single_projectile_vs_summons(proj)

    def _process_single_projectile_vs_summons(self, proj) -> None:
        if not proj.ativo:
            return
        for summon in self.summons:
            if self._resolve_projectile_vs_single_summon(proj, summon):
                return

    def _resolve_projectile_vs_single_summon(self, proj, summon) -> bool:
        if not summon.ativo or proj.dono == summon.dono:
            return False
        if not self._projectile_hits_summon(proj, summon):
            return False
        dano_proj = self._calcular_dano_projetil_vs_summon(proj)
        evento = summon.tomar_dano(dano_proj)
        self._finalize_projectile_after_summon_hit(proj)
        self._emit_projectile_vs_summon_feedback(proj, summon, dano_proj)
        self._handle_summon_damage_event(evento)
        return True

    def _projectile_hits_summon(self, proj, summon) -> bool:
        dist = math.hypot(proj.x - summon.x, proj.y - summon.y)
        return dist < (summon.raio_fisico + getattr(proj, 'raio', 0.3))

    def _calcular_dano_projetil_vs_summon(self, proj):
        if hasattr(proj.dono, 'get_dano_modificado'):
            return proj.dono.get_dano_modificado(proj.dano)
        return proj.dano

    def _finalize_projectile_after_summon_hit(self, proj) -> None:
        if self._projetil_eh_perfurante(proj):
            return
        proj.ativo = False
        self._remover_trail_projetil(proj)

    def _emit_projectile_vs_summon_feedback(self, proj, summon, dano_proj) -> None:
        self.textos.append(FloatingText(summon.x * PPM, summon.y * PPM - 20, int(dano_proj), (255, 180, 180), 16))
        cor_imp = getattr(proj, 'cor', BRANCO)
        self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, cor_imp, 0.8, "magic"))

    def _handle_summon_damage_event(self, evento) -> None:
        if not evento:
            return
        if evento.get("revive"):
            self.textos.append(FloatingText(evento["x"] * PPM, evento["y"] * PPM - 40, "REVIVE!", (255, 200, 50), 28))
            self._spawn_particulas_efeito(evento["x"] * PPM, evento["y"] * PPM, "FOGO")
            return
        if evento.get("morreu"):
            self.textos.append(FloatingText(evento["x"] * PPM, evento["y"] * PPM - 40, "DESTRUÃDO!", (200, 200, 200), 22))
            self._spawn_particulas_efeito(evento["x"] * PPM, evento["y"] * PPM, "EXPLOSAO")

    def _finalize_summon_phase(self) -> None:
        self.summons = [summon for summon in self.summons if summon.ativo]

    def _update_trap_phase(self, dt):
        if not hasattr(self, 'traps'):
            return

        self._run_trap_updates(dt)
        self._process_projectile_vs_trap_phase()
        self._finalize_trap_phase()

    def _run_trap_updates(self, dt: float) -> None:
        for trap in self.traps:
            self._update_single_trap(trap, dt)

    def _update_single_trap(self, trap, dt: float) -> None:
        trap.atualizar(dt)
        if not trap.ativo:
            return

        for lutador in self.fighters:
            self._update_single_trap_vs_fighter(trap, lutador, dt)

    def _update_single_trap_vs_fighter(self, trap, lutador, dt: float) -> None:
        if lutador.morto:
            return

        if trap.bloqueia_movimento:
            self._resolve_wall_trap_contact(trap, lutador, dt)
            return

        self._resolve_trigger_trap_contact(trap, lutador)

    def _resolve_wall_trap_contact(self, trap, lutador, dt: float) -> None:
        if lutador == trap.dono:
            return
        if not trap.colidir_ponto(lutador.pos[0], lutador.pos[1]):
            return

        dx, dy, dist = self._reposition_fighter_from_wall_trap(trap, lutador)
        dano_contato = trap.dano_wall_contato(dt)
        if dano_contato <= 0:
            return

        efeito = trap.efeito if trap.efeito != "NORMAL" else "NORMAL"
        self._registrar_hit_stats(
            trap.dono, lutador, dano_contato,
            elemento=efeito,
            source_type="trap",
            source_name=f"{getattr(trap, 'nome', 'Trap')} (Wall)",
        )
        if lutador.tomar_dano(dano_contato, dx / dist, dy / dist, efeito):
            self.textos.append(FloatingText(lutador.pos[0] * PPM, lutador.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(lutador, trap.dono.dados.nome)

    def _reposition_fighter_from_wall_trap(self, trap, lutador):
        dx = lutador.pos[0] - trap.x
        dy = lutador.pos[1] - trap.y
        dist = math.hypot(dx, dy) or 1
        lutador.pos[0] = trap.x + (dx / dist) * (trap.largura / 2 + 0.5)
        lutador.pos[1] = trap.y + (dy / dist) * (trap.altura / 2 + 0.5)
        return dx, dy, dist

    def _resolve_trigger_trap_contact(self, trap, lutador) -> None:
        resultado = trap.tentar_trigger(lutador)
        if not resultado:
            return
        contexto = self._build_trigger_trap_contact_context(trap, resultado)
        fatal = self._apply_trigger_trap_damage(contexto)
        self._emit_trigger_trap_feedback(contexto, fatal)

    def _build_trigger_trap_contact_context(self, trap, resultado):
        alvo = resultado["alvo"]
        dx = alvo.pos[0] - trap.x
        dy = alvo.pos[1] - trap.y
        dist = math.hypot(dx, dy) or 1
        return {
            "trap": trap,
            "resultado": resultado,
            "alvo": alvo,
            "dano": resultado["dano"],
            "efeito": resultado.get("efeito", "NORMAL"),
            "dx": dx,
            "dy": dy,
            "dist": dist,
        }

    def _apply_trigger_trap_damage(self, contexto) -> bool:
        trap = contexto["trap"]
        alvo = contexto["alvo"]
        dano = contexto["dano"]
        efeito = contexto["efeito"]
        dist = contexto["dist"]
        self._registrar_hit_stats(
            trap.dono, alvo, dano,
            elemento=efeito,
            source_type="trap",
            source_name=getattr(trap, 'nome', 'Trap'),
        )
        fatal = alvo.tomar_dano(dano, contexto["dx"] / dist, contexto["dy"] / dist, efeito)
        if fatal:
            self._registrar_kill(alvo, trap.dono.dados.nome)
        return fatal

    def _emit_trigger_trap_feedback(self, contexto, fatal: bool) -> None:
        trap = contexto["trap"]
        alvo = contexto["alvo"]
        dano = contexto["dano"]
        if fatal:
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
        else:
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano), trap.cor))
            self.cam.aplicar_shake(4.0, 0.06)
        self._spawn_particulas_efeito(trap.x * PPM, trap.y * PPM, trap.elemento if trap.elemento else "EXPLOSAO")
        self.impact_flashes.append(ImpactFlash(trap.x * PPM, trap.y * PPM, trap.cor, 1.5, "explosion"))
        self.shockwaves.append(Shockwave(trap.x * PPM, trap.y * PPM, trap.cor, tamanho=1.8))
        self.textos.append(FloatingText(trap.x * PPM, trap.y * PPM - 50, "TRAP!", (255, 200, 100), 22))

    def _process_projectile_vs_trap_phase(self) -> None:
        for proj in self.projeteis:
            self._process_single_projectile_vs_traps(proj)

    def _process_single_projectile_vs_traps(self, proj) -> None:
        if not proj.ativo:
            return
        for trap in self.traps:
            if self._resolve_projectile_vs_single_trap(proj, trap):
                return

    def _resolve_projectile_vs_single_trap(self, proj, trap) -> bool:
        if not self._projectile_can_hit_trap(proj, trap):
            return False
        dano_proj = self._calcular_dano_projetil_vs_trap(proj)
        destruida = trap.tomar_dano(dano_proj)
        self._finalize_projectile_after_trap_hit(proj, trap)
        self._emit_projectile_vs_trap_feedback(proj, trap, dano_proj)
        self._handle_trap_destroyed_by_projectile(trap, destruida)
        return True

    def _projectile_can_hit_trap(self, proj, trap) -> bool:
        if not trap.ativo or proj.dono == trap.dono:
            return False
        return trap.colidir_ponto(proj.x, proj.y)

    def _calcular_dano_projetil_vs_trap(self, proj):
        if hasattr(proj.dono, 'get_dano_modificado'):
            return proj.dono.get_dano_modificado(proj.dano)
        return proj.dano

    def _finalize_projectile_after_trap_hit(self, proj, trap) -> None:
        if not trap.bloqueia_movimento or not trap.bloqueia_projeteis:
            return
        if self._projetil_eh_perfurante(proj):
            return
        proj.ativo = False
        self._remover_trail_projetil(proj)

    def _emit_projectile_vs_trap_feedback(self, proj, trap, dano_proj) -> None:
        self.textos.append(FloatingText(trap.x * PPM, trap.y * PPM - 20, int(dano_proj), (200, 200, 255), 14))
        cor_imp = getattr(proj, 'cor', BRANCO)
        self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, cor_imp, 0.6, "magic"))

    def _handle_trap_destroyed_by_projectile(self, trap, destruida) -> None:
        if not destruida:
            return
        self.textos.append(FloatingText(trap.x * PPM, trap.y * PPM - 40, "DESTRUÃDA!", (200, 200, 200), 20))
        self._spawn_particulas_efeito(trap.x * PPM, trap.y * PPM, "EXPLOSAO")
        self.shockwaves.append(Shockwave(trap.x * PPM, trap.y * PPM, trap.cor, tamanho=1.5))

    def _finalize_trap_phase(self) -> None:
        self.traps = [trap for trap in self.traps if trap.ativo]

    def _update_transformation_phase(self, dt):
        # === ATUALIZA TRANSFORMAÃ‡Ã•ES v2.0 ===
        for lutador in self.fighters:
            if hasattr(lutador, 'transformacao_ativa') and lutador.transformacao_ativa:
                transform = lutador.transformacao_ativa
                alvos = self.fighters
                resultados = transform.atualizar(dt, alvos)
                
                for res in resultados:
                    if res.get("tipo") == "contato":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        self._registrar_hit_stats(
                            lutador, alvo, dano,
                            elemento="NORMAL",
                            source_type="status",
                            source_name=getattr(transform, 'nome', 'Transform'),
                        )
                        if alvo.tomar_dano(dano, 0, 0, "NORMAL"):
                            self._registrar_kill(alvo, lutador.dados.nome)
                    elif res.get("tipo") == "slow":
                        alvo = res["alvo"]
                        alvo.slow_timer = max(alvo.slow_timer, 0.1)
                        alvo.slow_fator = min(alvo.slow_fator, res["fator"])
                
                if not transform.ativo:
                    lutador.transformacao_ativa = None

    def _update_channel_phase(self, dt):
        for lutador in self.fighters:
            self._update_single_channel(lutador, dt)

    def _update_single_channel(self, lutador, dt: float) -> None:
        channel = getattr(lutador, 'channel_ativo', None)
        if not channel:
            return
        resultados = channel.atualizar(dt, self.fighters)
        for res in resultados:
            self._process_single_channel_result(lutador, channel, res)
        if not channel.ativo:
            lutador.channel_ativo = None

    def _process_single_channel_result(self, lutador, channel, res) -> None:
        if res.get("tipo") == "cura":
            self._handle_channel_heal_result(lutador, res)
        elif res.get("tipo") == "dano":
            self._handle_channel_damage_result(lutador, channel, res)

    def _handle_channel_heal_result(self, lutador, res) -> None:
        valor = res["valor"]
        self.textos.append(FloatingText(lutador.pos[0] * PPM, lutador.pos[1] * PPM - 30, f"+{int(valor)}", (100, 255, 150), 14))

    def _handle_channel_damage_result(self, lutador, channel, res) -> None:
        contexto = self._build_channel_damage_context(lutador, channel, res)
        self._registrar_channel_damage_stats(contexto)
        fatal = self._apply_channel_damage(contexto)
        self._emit_channel_damage_feedback(contexto, fatal)

    def _build_channel_damage_context(self, lutador, channel, res):
        return {
            "lutador": lutador,
            "channel": channel,
            "res": res,
            "alvo": res["alvo"],
            "dano": res["dano"],
            "efeito": res.get("efeito", "NORMAL"),
        }

    def _registrar_channel_damage_stats(self, contexto) -> None:
        self._registrar_hit_stats(
            contexto["lutador"],
            contexto["alvo"],
            contexto["dano"],
            elemento=contexto["efeito"],
            source_type="status",
            source_name=getattr(contexto["channel"], 'nome', 'Channel'),
        )

    def _apply_channel_damage(self, contexto) -> bool:
        return contexto["alvo"].tomar_dano(contexto["dano"], 0, 0, contexto["efeito"])

    def _emit_channel_damage_feedback(self, contexto, fatal: bool) -> None:
        alvo = contexto["alvo"]
        dano = contexto["dano"]
        if fatal:
            self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
            self._registrar_kill(alvo, contexto["lutador"].dados.nome)
            return
        cor = self._get_cor_efeito(contexto["efeito"])
        self.textos.append(FloatingText(alvo.pos[0] * PPM, alvo.pos[1] * PPM - 30, int(dano), cor, 12))

    # =========================================================================
    # v14.0: MÃ‰TODOS AUXILIARES MULTI-COMBATENTE + PERFORMANCE
    # =========================================================================

    def _update_active_match_state(self, dt: float) -> None:
        if self.vencedor:
            return

        self._update_match_timer_and_victory(dt)
        self._update_match_choreography(dt)
        self._update_match_fighter_runtime(dt)
        self._update_match_arena_runtime(dt)
        self._finalize_match_visual_runtime(dt)

    def _update_match_timer_and_victory(self, dt: float) -> None:
        self.tempo_luta += dt
        if hasattr(self, 'stats_collector'):
            self.stats_collector.set_frame(int(self.tempo_luta * 60))
        if self.tempo_luta >= self.TEMPO_MAX_LUTA:
            self.vencedor = self._determinar_vencedor_por_tempo()
            self.textos.append(FloatingText(
                self.screen_width // 2, self.screen_height // 2 - 80,
                "TEMPO ESGOTADO!", (255, 200, 50), 36
            ))
            self.ativar_slow_motion()

        if self.modo_partida == "horda" and self.horde_manager:
            self.horde_manager.update(dt)

        if not self.vencedor:
            if self.modo_partida == "horda":
                self.vencedor = self._verificar_vitoria_horda()
            else:
                self.vencedor = self._verificar_last_team_standing()

    def _update_match_choreography(self, dt: float) -> None:
        if self.choreographer:
            momento_anterior = self.choreographer.momento_atual
            self.choreographer.update(dt)

            if self.choreographer.momento_atual == "CLASH" and momento_anterior != "CLASH":
                self._executar_sword_clash()

            novo_momento = self.choreographer.momento_atual
            if novo_momento != momento_anterior:
                if novo_momento == "FINAL_SHOWDOWN":
                    self.time_scale = 0.6
                    self.slow_mo_timer = 1.2
                elif novo_momento == "NEAR_MISS":
                    self.time_scale = 0.35
                    self.slow_mo_timer = 0.18
                elif novo_momento == "CLIMAX_CHARGE":
                    self.time_scale = 0.7
                    self.slow_mo_timer = 0.8
                elif novo_momento == "PURSUIT":
                    self.time_scale = 0.8
                    self.slow_mo_timer = 0.6

    def _update_match_fighter_runtime(self, dt: float) -> None:
        self._aplicar_pressao_ritmo(dt)

        if self.modo_multi:
            from ia.team_ai import TeamCoordinatorManager
            TeamCoordinatorManager.get().update(dt, self.fighters)

        for lutador in self.fighters:
            if not lutador.morto:
                inimigo = self._encontrar_inimigo_mais_proximo(lutador)
                if inimigo:
                    lutador.update(dt, inimigo, todos_lutadores=self.fighters)
                else:
                    lutador.update(dt, None, todos_lutadores=self.fighters)

        self._atualizar_aliases_principais()
        self._atualizar_direcao_cinematica(dt)

    def _update_match_arena_runtime(self, dt: float) -> None:
        if hasattr(self, '_wall_sound_cooldown'):
            for lutador_id in list(self._wall_sound_cooldown.keys()):
                self._wall_sound_cooldown[lutador_id] = max(0, self._wall_sound_cooldown[lutador_id] - dt)

        if self.arena:
            for lutador in self.fighters:
                impacto = self.arena.aplicar_limites(lutador, dt)
                if impacto > 0:
                    self._criar_efeito_colisao_parede(lutador, impacto)

            self.arena.limpar_colisoes()

            if self.arena.efeitos_ativos:
                self._processar_efeitos_arena(dt)

        self.resolver_fisica_corpos(dt)
        self.verificar_colisoes_combate()
        self.atualizar_rastros()

    def _finalize_match_visual_runtime(self, dt: float) -> None:
        self._update_visual_health_runtime(dt)
        self._finalize_match_motion_events()

    def _update_visual_health_runtime(self, dt: float) -> None:
        self._update_fighter_visual_health_runtime(dt)
        self._update_primary_visual_health_runtime(dt)

    def _update_fighter_visual_health_runtime(self, dt: float) -> None:
        for lutador in self.fighters:
            if lutador in self.vida_visual:
                self.vida_visual[lutador] = self._lerp_visual_health(
                    self.vida_visual[lutador], lutador.vida, dt
                )

    def _update_primary_visual_health_runtime(self, dt: float) -> None:
        self.vida_visual_p1 = self._lerp_visual_health(self.vida_visual_p1, self.p1.vida, dt)
        self.vida_visual_p2 = self._lerp_visual_health(self.vida_visual_p2, self.p2.vida, dt)

    def _lerp_visual_health(self, atual: float, alvo: float, dt: float) -> float:
        return atual + (alvo - atual) * 5 * dt

    def _finalize_match_motion_events(self) -> None:
        self._detectar_eventos_movimento()

    def _update_post_frame_systems(self, dt: float) -> None:
        if self.movement_anims:
            self.movement_anims.update(dt)

        if self.attack_anims:
            self.attack_anims.update(dt)

        max_particulas = 600
        if len(self.particulas) > max_particulas:
            self.particulas = self.particulas[-max_particulas:]

        alive_particulas = []
        for particula in self.particulas:
            particula.atualizar(dt)
            if particula.vida <= 0:
                if particula.cor == VERMELHO_SANGUE and random.random() < 0.3:
                    self.decals.append(Decal(particula.x, particula.y, particula.tamanho * 2, SANGUE_ESCURO))
            else:
                alive_particulas.append(particula)
        self.particulas = alive_particulas
        if len(self.decals) > 100:
            self.decals.pop(0)

    def _flush_match_stats(self):
        """
        B01: Persiste o stats_collector no BattleDB imediatamente.

        Chama flush_to_db() com o match_id da Ãºltima luta registrada.
        Funciona tanto no modo standalone (view_luta) quanto no pipeline
        de vÃ­deo headless (fight_recorder), pois nÃ£o depende de quem
        chama record_fight_result() depois â€” o flush acontece antes.

        Nota: se o match_id ainda nÃ£o existir (flush chamado antes de
        record_fight_result), armazena em AppState.pending_stats para
        que record_fight_result() faÃ§a o flush logo apÃ³s inserir no DB.
        """
        try:
            if not self._has_match_stats_to_flush():
                return
            state = self._get_match_stats_app_state()
            match_id = self._resolve_match_stats_match_id(state)
            if match_id is not None:
                self._flush_match_stats_to_known_match(match_id)
            else:
                self._queue_pending_match_stats(state)
        except Exception as e:
            _log.warning("_flush_match_stats falhou (nÃ£o-fatal): %s", e)

    def _has_match_stats_to_flush(self) -> bool:
        return hasattr(self, 'stats_collector')

    def _get_match_stats_app_state(self):
        from dados.app_state import AppState
        return AppState.get()

    def _resolve_match_stats_match_id(self, state):
        return getattr(state, '_last_match_id', None)

    def _flush_match_stats_to_known_match(self, match_id) -> None:
        self.stats_collector.flush_to_db(match_id=match_id)
        _log.debug("Match stats persistidos para match_id=%s", match_id)

    def _queue_pending_match_stats(self, state) -> None:
        state.pending_stats_collector = self.stats_collector
        _log.debug("Match stats enfileirados (match_id pendente)")

    def _atualizar_aliases_principais(self):
        """Mantem p1/p2 coerentes para camera, HUD e sistemas legados."""
        if not self.fighters:
            return
        aliados_principais = [f for f in self.fighters if f.team_id == 0]
        if aliados_principais:
            self.p1 = next((f for f in aliados_principais if not f.morto), aliados_principais[0])
        else:
            self.p1 = self.fighters[0]

        if self.modo_partida == "horda":
            inimigos = [f for f in self.fighters if f.team_id != getattr(self.p1, "team_id", 0) and not f.morto]
            self.p2 = inimigos[0] if inimigos else (aliados_principais[1] if len(aliados_principais) > 1 else self.p1)
            return

        inimigo = next(
            (f for f in self.fighters if f.team_id != getattr(self.p1, "team_id", 0)),
            None,
        )
        self.p2 = inimigo or (self.fighters[1] if len(self.fighters) > 1 else self.p1)

    def _verificar_vitoria_horda(self):
        if not self.horde_manager:
            return None
        herois_vivos = [f for f in self.fighters if f.team_id != self.horde_manager.team_id and not f.morto]
        monstros_vivos = [f for f in self.fighters if f.team_id == self.horde_manager.team_id and not f.morto]
        if not herois_vivos:
            return self.horde_manager.label
        if self.horde_manager.completed and not monstros_vivos:
            if len(herois_vivos) == 1:
                return herois_vivos[0].dados.nome
            nomes = ", ".join(f.dados.nome for f in herois_vivos)
            return f"Expedicao ({nomes})"
        if self.horde_manager.failed:
            return self.horde_manager.label
        return None
    
    def _processar_efeitos_arena(self, dt: float) -> None:
        """
        C02: Processa efeitos_especiais da arena sobre os lutadores.

        Handlers por efeito:
            "neve"          â†’ partÃ­culas visuais (via sim_effects) + "escorregadio"
            "escorregadio"  â†’ reduz aceleraÃ§Ã£o lateral de todos os fighters
            "calor"         â†’ degeneraÃ§Ã£o leve de estamina
            "neblina"       â†’ reduz percepÃ§Ã£o de range da IA
            "chuva"         â†’ partÃ­culas visuais periÃ³dicas
            "luzes_piscando"â†’ oscila brilho do fundo (visual apenas)
            "poeira"        â†’ partÃ­culas periÃ³dicas de poeira
        """
        for efeito in self.arena.efeitos_ativos:
            self._process_single_arena_effect(efeito, dt)

    def _process_single_arena_effect(self, efeito: str, dt: float) -> None:
        if efeito == "calor":
            self._apply_arena_heat_effect(dt)
        elif efeito in ("neve", "escorregadio"):
            self._apply_arena_slippery_effect(dt)
        elif efeito == "neblina":
            self._apply_arena_fog_effect()
        elif efeito == "chuva":
            self._apply_arena_rain_effect(dt)
        elif efeito == "poeira":
            self._apply_arena_dust_effect(dt)

    def _apply_arena_heat_effect(self, dt: float) -> None:
        for f in self.fighters:
            if not f.morto:
                f.estamina = max(0, f.estamina - 0.5 * dt)

    def _apply_arena_slippery_effect(self, dt: float) -> None:
        for f in self.fighters:
            if not f.morto and not getattr(f, 'no_ar', False):
                f.vel[0] *= max(0.0, 1.0 - dt * 4.0)

    def _apply_arena_fog_effect(self) -> None:
        if getattr(self, '_neblina_aplicada', False):
            return

        for f in self.fighters:
            if hasattr(f, 'brain') and f.brain:
                f.brain._neblina_fator = 0.70
        self._neblina_aplicada = True

    def _apply_arena_rain_effect(self, dt: float) -> None:
        if not self._advance_arena_effect_timer('_chuva_timer', dt, 0.08):
            return
        self._spawn_arena_rain_particles()

    def _apply_arena_dust_effect(self, dt: float) -> None:
        if not self._advance_arena_effect_timer('_poeira_timer', dt, 0.15):
            return
        self._spawn_arena_dust_particles()

    def _advance_arena_effect_timer(self, timer_attr: str, dt: float, threshold: float) -> bool:
        if not hasattr(self, timer_attr):
            setattr(self, timer_attr, 0.0)
        timer_value = getattr(self, timer_attr) + dt
        if timer_value < threshold:
            setattr(self, timer_attr, timer_value)
            return False
        setattr(self, timer_attr, 0.0)
        return True

    def _spawn_arena_rain_particles(self) -> None:
        for _ in range(3):
            rx = random.uniform(0, self.arena.largura) * PPM
            vy = random.uniform(8, 14) * PPM
            self.particulas.append(Particula(rx, 0, (150, 180, 220), 0, vy, 1, 0.4))

    def _spawn_arena_dust_particles(self) -> None:
        for _ in range(2):
            rx = random.uniform(0, self.arena.largura) * PPM
            ry = (self.arena.altura - 0.5) * PPM
            vx = random.uniform(-2, 2) * PPM
            self.particulas.append(Particula(rx, ry, (180, 160, 120), vx, -1, 2, 0.6))

    def _registrar_kill(self, morto, killer_nome_fallback):
        """Registra uma morte e determina se a luta acabou.
        
        v14.0: Team-aware â€” em multi-fighter, a luta sÃ³ acaba
        quando todos os membros de um time sÃ£o eliminados.
        Evita que fights acabem 'do nada' quando um membro morre
        mas seu time ainda estÃ¡ vivo.
        """
        if hasattr(self, 'stats_collector') and morto and hasattr(morto, 'dados'):
            self.stats_collector.record_death(morto.dados.nome, killer=killer_nome_fallback or "")
        self.ativar_slow_motion()
        resultado = self._determinar_vencedor_por_morte(morto)
        if resultado:
            self.vencedor = resultado

    def _registrar_hit_stats(self, atacante, defensor, dano, *, critico=False, elemento="", source_type="weapon", source_name=""):
        """Helper central para contabilizar hits fora do combate melee."""
        collector = getattr(self, 'stats_collector', None)
        if not collector or atacante is None or defensor is None:
            return
        nome_atacante = getattr(getattr(atacante, 'dados', None), 'nome', '')
        nome_defensor = getattr(getattr(defensor, 'dados', None), 'nome', '')
        if not nome_atacante or not nome_defensor:
            return
        collector.record_hit(
            nome_atacante,
            nome_defensor,
            dano,
            critico=critico,
            elemento=elemento,
            source_type=source_type,
            source_name=source_name,
        )
    
    def _get_projetil_elemento(self, proj):
        """Retorna o elemento cacheado de um projÃ©til (perf: evita re-parse de strings por frame)."""
        cached = getattr(proj, '_cached_elemento', None)
        if cached:
            return cached
        elem = self._get_direct_projectile_element(proj)
        if not elem:
            elem = self._resolve_projectile_keyword_element(proj) or "ARCANO"
        proj._cached_elemento = elem
        return elem

    def _get_direct_projectile_element(self, proj):
        return getattr(proj, 'elemento', '')

    def _resolve_projectile_keyword_element(self, proj):
        nome = str(getattr(proj, 'nome', '')).lower()
        tipo = str(getattr(proj, 'tipo', '')).lower()
        combined = nome + tipo
        keyword_groups = [
            ("FOGO", ["fogo", "fire", "chama", "meteoro", "inferno", "brasas", "combustao"]),
            ("GELO", ["gelo", "ice", "glacial", "nevasca", "cristal", "congelar"]),
            ("RAIO", ["raio", "lightning", "thunder", "eletric", "relampago"]),
            ("TREVAS", ["trevas", "shadow", "dark", "sombra", "necro"]),
            ("LUZ", ["luz", "light", "holy", "sagrado", "divino"]),
            ("SANGUE", ["sangue", "blood", "vampir"]),
            ("ARCANO", ["arcano", "arcane", "mana", "runa"]),
            ("NATUREZA", ["veneno", "poison", "natureza", "nature"]),
            ("VOID", ["void", "vazio", "abismo"]),
            ("TEMPO", ["tempo", "temporal", "relogio", "paradoxo"]),
            ("GRAVITACAO", ["gravit", "gravity", "buraco negro", "pulso"]),
            ("CAOS", ["caos", "chaos", "caotico"]),
        ]
        for elemento, keywords in keyword_groups:
            if any(keyword in combined for keyword in keywords):
                return elemento
        return None
    
    def _encontrar_alvo_mais_proximo(self, x, y, dono):
        """Encontra o lutador vivo mais prÃ³ximo das coordenadas, excluindo o dono.
        
        Friendly fire ON: retorna qualquer lutador, incluindo aliados.
        """
        melhor = None
        melhor_dist = float('inf')
        for f in self.fighters:
            if f is dono or f.morto:
                continue
            d = math.hypot(f.pos[0] - x, f.pos[1] - y)
            if d < melhor_dist:
                melhor_dist = d
                melhor = f
        return melhor
    
    def _encontrar_inimigo_mais_proximo(self, lutador):
        """Encontra o inimigo vivo mais prÃ³ximo (time diferente)."""
        melhor = None
        melhor_dist = float('inf')
        for f in self.fighters:
            if f is lutador or f.morto or f.team_id == lutador.team_id:
                continue
            d = math.hypot(f.pos[0] - lutador.pos[0], f.pos[1] - lutador.pos[1])
            if d < melhor_dist:
                melhor_dist = d
                melhor = f
        return melhor
    
    def _verificar_last_team_standing(self):
        """Verifica se apenas um time tem lutadores vivos. Retorna nome do vencedor ou None."""
        teams_vivos = set()
        for f in self.fighters:
            if not f.morto:
                teams_vivos.add(f.team_id)
        
        if len(teams_vivos) == 1:
            tid = teams_vivos.pop()
            # Retorna o nome do(s) vencedor(es)
            vivos = [f for f in self.fighters if f.team_id == tid and not f.morto]
            if len(vivos) == 1:
                return vivos[0].dados.nome
            else:
                nomes = ", ".join(f.dados.nome for f in vivos)
                return f"Time {tid + 1} ({nomes})"
        elif len(teams_vivos) == 0:
            return "Empate"
        
        return None  # Luta continua
    
    def _determinar_vencedor_por_tempo(self):
        """Determina vencedor por HP% quando o tempo esgota."""
        if self.modo_partida == "horda" and self.horde_manager:
            return self._determinar_vencedor_horda_por_tempo()
        if not self.modo_multi:
            return self._determinar_vencedor_duelo_por_tempo()
        return self._determinar_vencedor_multi_por_tempo()

    def _determinar_vencedor_horda_por_tempo(self):
        herois = [f for f in self.fighters if f.team_id != self.horde_manager.team_id]
        monstros = [f for f in self.fighters if f.team_id == self.horde_manager.team_id]
        pct_herois = self._calcular_grupo_hp_percentual(herois)
        pct_monstros = self._calcular_grupo_hp_percentual(monstros)
        if pct_herois >= pct_monstros:
            vivos = [f for f in herois if not f.morto]
            if len(vivos) == 1:
                return vivos[0].dados.nome
            nomes = ", ".join(f.dados.nome for f in vivos) if vivos else "Expedicao"
            return f"Expedicao ({nomes})"
        return self.horde_manager.label

    def _determinar_vencedor_duelo_por_tempo(self):
        pct_p1 = self.p1.vida / max(self.p1.vida_max, 1)
        pct_p2 = self.p2.vida / max(self.p2.vida_max, 1)
        if pct_p1 > pct_p2:
            return self.p1.dados.nome
        if pct_p2 > pct_p1:
            return self.p2.dados.nome
        return "Empate"

    def _determinar_vencedor_multi_por_tempo(self):
        team_hp = self._agrupar_hp_por_time()
        melhor_tid = max(team_hp.keys(), key=lambda t: team_hp[t]["total"] / team_hp[t]["max"])
        melhor_pct = team_hp[melhor_tid]["total"] / team_hp[melhor_tid]["max"]
        empatados = [t for t, hp in team_hp.items() if abs(hp["total"] / hp["max"] - melhor_pct) < 0.01]
        if len(empatados) > 1:
            return "Empate"

        vivos = [f for f in self.fighters if f.team_id == melhor_tid and not f.morto]
        if len(vivos) == 1:
            return vivos[0].dados.nome
        nomes = ", ".join(f.dados.nome for f in vivos if not f.morto)
        return f"Time {melhor_tid + 1} ({nomes})"

    def _calcular_grupo_hp_percentual(self, fighters) -> float:
        hp_total = sum(max(0, f.vida) for f in fighters)
        hp_max = sum(max(1, f.vida_max) for f in fighters)
        return hp_total / max(hp_max, 1)

    def _agrupar_hp_por_time(self):
        team_hp = {}
        for f in self.fighters:
            tid = f.team_id
            if tid not in team_hp:
                team_hp[tid] = {"total": 0, "max": 0}
            team_hp[tid]["total"] += max(0, f.vida)
            team_hp[tid]["max"] += max(1, f.vida_max)
        return team_hp
    
    def _determinar_vencedor_por_morte(self, morto):
        """Determina quem venceu quando alguÃ©m morre (para traps/channels/etc)."""
        # Verifica se o time do morto ainda tem gente viva
        aliados_vivos = [f for f in self.fighters if f.team_id == morto.team_id and not f.morto and f is not morto]
        if aliados_vivos:
            return None  # Time ainda nÃ£o foi eliminado
        
        # Time do morto foi eliminado - encontra time vencedor
        for f in self.fighters:
            if f.team_id != morto.team_id and not f.morto:
                # Retorna o vencedor
                vivos = [v for v in self.fighters if v.team_id == f.team_id and not v.morto]
                if len(vivos) == 1:
                    return vivos[0].dados.nome
                nomes = ", ".join(v.dados.nome for v in vivos)
                return f"Time {f.team_id + 1} ({nomes})"
        
        return "Empate"

if __name__ == "__main__":
    Simulador().run()


