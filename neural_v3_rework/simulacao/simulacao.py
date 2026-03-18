import pygame
import logging
_log = logging.getLogger("simulacao")  # QC-02
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


class Simulador(SimuladorRenderer, SimuladorCombat, SimuladorEffects):


    def executar(self):
        """Alias legado para entrypoints que ainda chamam executar()."""
        return self.run()


    def run(self):
        self._slow_mo_ended = False  # Flag para tocar som de vitÃ³ria uma vez
        while self.rodando:
            try:
                raw_dt = self.clock.tick(FPS) / 1000.0
                if self.slow_mo_timer > 0:
                    self.slow_mo_timer -= raw_dt
                    if self.slow_mo_timer <= 0:
                        self.time_scale = 1.0
                        # Som de fim do slow-mo e vitÃ³ria
                        if not self._slow_mo_ended and self.vencedor:
                            self.audio.play_special("slowmo_end", 0.5)
                            self.audio.play_special("arena_victory", 1.0)
                            self._slow_mo_ended = True
                            # CB-04: persiste memÃ³ria de rivalidade para o sistema MEL-AI-07
                            self._salvar_memorias_rivais()
                            # v14.0: Flush match stats to DB
                            self._flush_match_stats()
                dt = raw_dt * self.time_scale
                self.processar_inputs(); self.update(dt); self.desenhar(); pygame.display.flip()
            except Exception as e:
                # B05: era _log.debug â€” invisÃ­vel em produÃ§Ã£o. Agora _log.exception
                # inclui automaticamente o traceback completo no log.
                _log.exception("ERRO CRÃTICO NO LOOP DE SIMULAÃ‡ÃƒO: %s", e)
                # Mostra diÃ¡logo de erro
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

    def __init__(self):
        pygame.init()
        
        # Limpa caches de classe que contÃªm objetos pygame invalidados por pygame.quit()
        SimuladorRenderer._font_cache.clear()
        
        # Reseta sistema de hitbox global (impede referÃªncias a lutadores antigos)
        from nucleo.hitbox import sistema_hitbox
        sistema_hitbox.ultimo_ataque_info.clear()
        sistema_hitbox.hits_registrados = []
        
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
        
        # Sistema de Coreografia
        self.choreographer = None
        
        # === SISTEMA DE GAME FEEL v8.0 ===
        # Gerencia Hit Stop, Super Armor, Channeling e Camera Feel
        self.game_feel = None
        
        # === SISTEMA DE ARENA v9.0 ===
        self.arena = None
        
        # === SISTEMA DE ÃUDIO v10.0 ===
        self.audio = None
        
        self.recarregar_tudo()

    def _ativar_direcao_cinematica(self, perfil):
        if not isinstance(perfil, dict):
            return

        intensidade = max(0.0, min(1.0, float(perfil.get("intensidade", 0.0) or 0.0)))
        if intensidade <= 0.08:
            return

        evento_id = (
            perfil.get("tipo"),
            getattr(perfil.get("lutador"), "dados", None).nome if getattr(perfil.get("lutador"), "dados", None) else None,
            round(intensidade, 2),
        )
        atual = getattr(self, "direcao_cinematica", {})
        if atual.get("evento_id") == evento_id:
            atual["intensidade"] = max(atual.get("intensidade", 0.0), intensidade)
            atual["overlay_timer"] = max(atual.get("overlay_timer", 0.0), float(perfil.get("duracao_overlay", 0.25) or 0.25))
            atual["overlay"] = max(atual.get("overlay", 0.0), float(perfil.get("overlay", 0.0) or 0.0))
            return

        self.direcao_cinematica = {
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
        delta_hp = estado.get("ultimo_hp_total", hp_total) - hp_total
        if delta_hp > 0.05:
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
        else:
            estado["tempo_sem_dano"] += dt
            estado["ultimo_evento"] += dt

        estado["ultimo_hp_total"] = hp_total

        ativar_em = 6.0
        if estado["tempo_sem_dano"] >= ativar_em:
            if not estado["ativa"]:
                self.textos.append(FloatingText(
                    self.screen_width // 2, self.screen_height // 2 - 40,
                    "PRESSAO DA ARENA!", (255, 196, 92), 26
                ))
            estado["ativa"] = True
            estado["tempo_ativo"] += dt
            estado["intensidade"] = min(1.0, 0.22 + (estado["tempo_sem_dano"] - ativar_em) * 0.085)
        else:
            estado["ativa"] = False
            estado["tempo_ativo"] = 0.0
            estado["intensidade"] = max(0.0, estado["intensidade"] - dt * 1.2)

        intensidade = float(estado.get("intensidade", 0.0) or 0.0)
        if not estado["ativa"] or intensidade <= 0.01:
            for f in getattr(self, "fighters", []) or []:
                brain = getattr(f, "brain", None) or getattr(f, "ai", None)
                if brain is not None:
                    brain.pressao_ritmo = 0.0
            return

        centro_x = getattr(self.arena, "centro_x", 0.0) if getattr(self, "arena", None) else 0.0
        centro_y = getattr(self.arena, "centro_y", 0.0) if getattr(self, "arena", None) else 0.0
        if not self.arena and getattr(self, "fighters", None):
            vivos = [f for f in self.fighters if not getattr(f, "morto", False)]
            if vivos:
                centro_x = sum(f.pos[0] for f in vivos) / len(vivos)
                centro_y = sum(f.pos[1] for f in vivos) / len(vivos)

        for f in getattr(self, "fighters", []) or []:
            if getattr(f, "morto", False):
                continue
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
            if event.type == pygame.QUIT: self.rodando = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: 
                    if self.audio: self.audio.play_ui("back")
                    self.rodando = False 
                if event.key == pygame.K_r: 
                    if self.audio: self.audio.play_ui("confirm")
                    self.recarregar_tudo()
                if event.key == pygame.K_SPACE: 
                    if self.audio: self.audio.play_ui("select")
                    self.paused = not self.paused
                if event.key == pygame.K_g: 
                    if self.audio: self.audio.play_ui("select")
                    self.show_hud = not self.show_hud  # G para HUD
                if event.key == pygame.K_h: 
                    if self.audio: self.audio.play_ui("select")
                    self.show_hitbox_debug = not self.show_hitbox_debug  # H para HITBOX DEBUG
                if event.key == pygame.K_TAB: 
                    if self.audio: self.audio.play_ui("select")
                    self.show_analysis = not self.show_analysis
                if event.key == pygame.K_t: 
                    if self.audio: self.audio.play_ui("select")
                    self.time_scale = 0.2 if self.time_scale == 1.0 else 1.0
                if event.key == pygame.K_f: 
                    if self.audio: self.audio.play_ui("select")
                    self.time_scale = 3.0 if self.time_scale == 1.0 else 1.0
                if event.key == pygame.K_1: 
                    if self.audio: self.audio.play_ui("select")
                    self.cam.modo = "P1"
                if event.key == pygame.K_2: 
                    if self.audio: self.audio.play_ui("select")
                    self.cam.modo = "P2"
                if event.key == pygame.K_3: 
                    if self.audio: self.audio.play_ui("select")
                    self.cam.modo = "AUTO"
            if event.type == pygame.MOUSEWHEEL:
                self.cam.target_zoom += event.y * 0.1
                self.cam.target_zoom = max(0.5, min(self.cam.target_zoom, 3.0))

        keys = pygame.key.get_pressed()
        move_speed = 15 / self.cam.zoom
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.cam.y -= move_speed; self.cam.modo = "MANUAL"
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.cam.y += move_speed; self.cam.modo = "MANUAL"
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.cam.x -= move_speed; self.cam.modo = "MANUAL"
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.cam.x += move_speed; self.cam.modo = "MANUAL"


    def recarregar_tudo(self):
        try:
            self.p1, self.p2, self.cenario, _ = self.carregar_luta_dados()
            self.particulas = []; self.decals = []; self.textos = []; self.shockwaves = []; self.projeteis = []
            # Reset novos efeitos v7.0
            self.impact_flashes = []; self.magic_clashes = []; self.block_effects = []
            self.dash_trails = []; self.hit_sparks = []
            # Reset efeitos v2.0 (skills avanÃ§adas)
            self.summons = []; self.traps = []; self.beams = []; self.areas = []
            self.time_scale = 1.0; self.slow_mo_timer = 0.0; self.hit_stop_timer = 0.0
            self.vencedor = None; self.paused = False
            self.tempo_luta = 0.0  # DES-4: reseta timer de luta
            self._resetar_pressao_ritmo()
            
            # v13.0: Garante fighters list e teams dict
            if not self.fighters:
                self.fighters = [f for f in [self.p1, self.p2] if f]
            
            # ConstrÃ³i self.teams a partir dos fighters
            self.teams = {}
            for f in self.fighters:
                tid = getattr(f, 'team_id', 0)
                if tid not in self.teams:
                    self.teams[tid] = []
                self.teams[tid].append(f)
            
            # v13.0: Inicializa rastros e vida visual para todos os fighters
            self.rastros = {f: [] for f in self.fighters}
            self.vida_visual = {}
            for f in self.fighters:
                if f:
                    self.vida_visual[f] = f.vida_max
            
            # Backward compat
            if self.p1: self.vida_visual_p1 = self.p1.vida_max
            if self.p2: self.vida_visual_p2 = self.p2.vida_max
            
            # Inicializa Sistema de Coreografia
            CombatChoreographer.reset()
            self.choreographer = CombatChoreographer.get_instance()
            if self.p1 and self.p2:
                self.choreographer.registrar_lutadores(self.p1, self.p2)
            
            # === INICIALIZA TEAM AI COORDINATOR v13.0 ===
            from ia.team_ai import TeamCoordinatorManager
            TeamCoordinatorManager.reset()
            if self.modo_multi and self.teams and len(self.teams) >= 2:
                TeamCoordinatorManager.get().initialize(self.fighters, self.teams)
            
            # === INICIALIZA GAME FEEL v8.0 ===
            GameFeelManager.reset()
            self.game_feel = GameFeelManager.get_instance()
            self.game_feel.set_camera(self.cam)
            if self.p1 and self.p2:
                self.game_feel.registrar_lutadores(self.p1, self.p2)
            
            # === INICIALIZA MOVEMENT ANIMATIONS v8.0 ===
            MovementAnimationManager.reset()
            self.movement_anims = MovementAnimationManager.get_instance()
            self.movement_anims.set_ppm(PPM)
            
            # === INICIALIZA ATTACK ANIMATIONS v8.0 IMPACT EDITION ===
            AttackAnimationManager.reset()
            self.attack_anims = AttackAnimationManager()
            self.attack_anims.set_ppm(PPM)
            
            # === INICIALIZA ARENA v9.0 ===
            cenario_nome = getattr(self, 'cenario', 'Arena') or 'Arena'
            # v13.0: Usa arena maior para multi-fighter
            if self.modo_multi and cenario_nome == 'Arena':
                cenario_nome = 'Coliseu'  # Default para arena maior em multi
            self.arena = set_arena(cenario_nome)
            
            # Configura cÃ¢mera para conhecer os limites da arena
            self.cam.set_arena_bounds(
                self.arena.centro_x, 
                self.arena.centro_y,
                self.arena.largura,
                self.arena.altura
            )
            
            # v13.0: Posiciona TODOS os lutadores nos spawn points da arena
            if len(self.fighters) >= 2:
                spawn_points = self.arena.get_spawn_points_multi(len(self.fighters), self.teams)
                for i, f in enumerate(self.fighters):
                    if i < len(spawn_points):
                        f.pos[0] = spawn_points[i][0]
                        f.pos[1] = spawn_points[i][1]
            
            # Rastreamento de estados anteriores para detectar mudanÃ§as
            self._prev_z = {f: 0 for f in self.fighters}
            self._prev_acao_ai = {f: '' for f in self.fighters}  # Sprint1: rastreia transiÃ§Ãµes de aÃ§Ã£o para VFX
            
            # === INICIALIZA SISTEMA DE ÃUDIO v10.0 ===
            AudioManager.reset()
            self.audio = AudioManager.get_instance()
            self._prev_stagger = {f: False for f in self.fighters}
            self._prev_dash = {f: 0 for f in self.fighters}
            
            # === INICIALIZA MATCH STATS COLLECTOR v14.0 ===
            from dados.match_stats import MatchStatsCollector
            self.stats_collector = MatchStatsCollector()
            for f in self.fighters:
                if f and hasattr(f, 'dados'):
                    self.stats_collector.register(f.dados.nome)
                    f.stats_collector = self.stats_collector
                f.encounter_mode = self.modo_partida
                f.objective_config = dict(self.objective_config or {})
                f.campaign_context = dict(self.campaign_context or {})
                brain = getattr(f, "brain", None)
                if brain is not None:
                    brain.encounter_mode = self.modo_partida
                    brain.objective_config = dict(self.objective_config or {})
                    brain.campaign_context = dict(self.campaign_context or {})

            # === HORDA v1.0 ===
            self.horde_manager = None
            if self.modo_partida == "horda":
                self.horde_manager = HordeWaveManager(self, self.encounter_config.get("horda_config") or {})
                self.horde_manager.start()

            # === INICIALIZA MAGIC VFX v11.0 ===
            MagicVFXManager.reset()
            self.magic_vfx = MagicVFXManager.get_instance()
            
            # Som de inÃ­cio de arena/luta
            self.audio.play_special("arena_start", 0.8)
                
        except Exception as e:
            # B05: era _log.debug â€” agora visÃ­vel em produÃ§Ã£o
            _log.exception("Erro ao inicializar arena/audio: %s", e)


    def carregar_luta_dados(self):
        try:
            from dados.app_state import AppState
            state = AppState.get()
            config = normalize_match_config(state.match_config)
            self.encounter_config = config
            self.modo_partida = config.get("modo_partida", "duelo")
            self.campaign_context = dict(config.get("campaign_context") or {})
            self.objective_config = dict(config.get("objective_config") or {})
            teams_config = config.get("teams") or []
            has_duel = bool(config.get("p1_nome") and config.get("p2_nome"))
            has_teams = bool(teams_config)
            if not has_duel and not has_teams:
                raise ValueError("match_config vazio â€” nenhum personagem ou equipe selecionada")
        except Exception as e:
            # B05: era _log.debug â€” agora visÃ­vel em produÃ§Ã£o
            _log.warning("[simulacao] Erro ao ler match_config via AppState: %s", e)
            return None, None, "Arena", False
        todos = state.characters   # already in-memory â€” no disk hit
        armas = state.weapons      # already in-memory â€” no disk hit
        def montar(nome):
            p = next((x for x in todos if x.nome == nome), None)
            if p and p.nome_arma:
                p.arma_obj = next((a for a in armas if a.nome == p.nome_arma), None)
                # BUG-F5: resetar durabilidade a cada luta para nÃ£o persistir entre rounds
                if p.arma_obj and hasattr(p.arma_obj, 'durabilidade_max'):
                    p.arma_obj.durabilidade = p.arma_obj.durabilidade_max
                    p.arma_obj._aviso_quebrada_exibido = False
            return p
        
        cenario = config.get("cenario", "Arena")
        portrait_mode = config.get("portrait_mode", False)

        if teams_config and isinstance(teams_config, list):
            all_fighters = []
            for team_cfg in teams_config:
                tid = team_cfg.get("team_id", 0)
                for nome in team_cfg.get("members", []):
                    dados = montar(nome)
                    if dados:
                        lutador = Lutador(dados, 0, 0, team_id=tid)
                        all_fighters.append(lutador)

            if all_fighters:
                self.fighters = all_fighters
                teams_distintos = {f.team_id for f in all_fighters}
                self.modo_multi = len(all_fighters) > 2 or len(teams_distintos) > 1
                l1 = all_fighters[0]
                l2 = next(
                    (f for f in all_fighters if f.team_id != l1.team_id),
                    all_fighters[1] if len(all_fighters) > 1 else all_fighters[0],
                )
                return l1, l2, cenario, portrait_mode
        
        # Modo legado: 2 lutadores
        l1 = Lutador(montar(config["p1_nome"]), 5.0, 8.0, team_id=0)
        l2 = Lutador(montar(config["p2_nome"]), 19.0, 8.0, team_id=1)
        self.fighters = [l1, l2]
        self.modo_partida = "duelo"
        self.modo_multi = False
        # CRIT-02 fix: carregar_memoria_rival nunca era chamado em nenhum lugar do
        # cÃ³digo de produÃ§Ã£o, tornando o sistema de aprendizado entre lutas inoperante
        # apesar de salvar_memoria_rival funcionar corretamente.
        # Carrega aqui, apÃ³s a personalidade ter sido gerada (acontece em Lutador.__init__
        # via AIBrain.__init__ â†’ _gerar_personalidade).
        try:
            if hasattr(l1, 'brain') and l1.brain and hasattr(l1.brain, 'carregar_memoria_rival'):
                l1.brain.carregar_memoria_rival(l2)
        except Exception as _e:
            _log.warning("[IA] carregar_memoria_rival l1 falhou: %s", _e)
        try:
            if hasattr(l2, 'brain') and l2.brain and hasattr(l2.brain, 'carregar_memoria_rival'):
                l2.brain.carregar_memoria_rival(l1)
        except Exception as _e:
            _log.warning("[IA] carregar_memoria_rival l2 falhou: %s", _e)
        return l1, l2, cenario, portrait_mode


    def update(self, dt):
        self.cam.atualizar(dt, self.p1, self.p2, fighters=self.fighters)
        # Atualiza sistema de debug de hitbox
        atualizar_debug(dt)
        
        if self.paused: return

        for t in self.textos: t.update(dt)
        self.textos = [t for t in self.textos if t.vida > 0]
        for s in self.shockwaves: s.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.vida > 0]

        # === GAME FEEL v8.0 - HIT STOP GERENCIADO ===
        # O Game Feel Manager pode zerar o dt durante hit stop
        dt_efetivo = dt
        if self.game_feel:
            dt_efetivo = self.game_feel.update(dt)
            # Durante hit stop, apenas efeitos visuais atualizam
            if dt_efetivo == 0:
                # Atualiza apenas efeitos visuais durante hit stop
                for ef in self.impact_flashes: ef.update(dt * 0.3)  # Slow mo nos efeitos
                for ef in self.hit_sparks: ef.update(dt * 0.3)
                return
        else:
            # Fallback para sistema antigo de hit stop
            if self.hit_stop_timer > 0: 
                self.hit_stop_timer -= dt
                return

        # === COLETA OBJETOS DOS LUTADORES ===
        for p in self.fighters:
            # ProjÃ©teis
            if p.buffer_projeteis:
                self.projeteis.extend(p.buffer_projeteis)
                p.buffer_projeteis = []
            # Orbes mÃ¡gicos
            if hasattr(p, 'buffer_orbes') and p.buffer_orbes:
                if not hasattr(self, 'orbes'):
                    self.orbes = []
                # Orbes ficam na lista do lutador para atualizaÃ§Ã£o de Ã³rbita
                # mas tambÃ©m precisamos processar colisÃµes aqui
            # Ãreas
            if hasattr(p, 'buffer_areas') and p.buffer_areas:
                if not hasattr(self, 'areas'):
                    self.areas = []
                self.areas.extend(p.buffer_areas)
                p.buffer_areas = []
            # Beams
            if hasattr(p, 'buffer_beams') and p.buffer_beams:
                if not hasattr(self, 'beams'):
                    self.beams = []
                self.beams.extend(p.buffer_beams)
                p.buffer_beams = []
            
            # === NOVOS TIPOS v2.0 ===
            # Summons (invocaÃ§Ãµes)
            if hasattr(p, 'buffer_summons') and p.buffer_summons:
                if not hasattr(self, 'summons'):
                    self.summons = []
                # Spawn effect dramÃ¡tico para cada novo summon
                for summon in p.buffer_summons:
                    if hasattr(self, 'magic_vfx') and self.magic_vfx:
                        # Determina elemento pelo nome/cor do summon
                        elemento = "ARCANO"
                        nome = getattr(summon, 'nome', '').lower()
                        if any(w in nome for w in ["fogo", "fire", "chama"]):
                            elemento = "FOGO"
                        elif any(w in nome for w in ["gelo", "ice"]):
                            elemento = "GELO"
                        elif any(w in nome for w in ["raio", "light"]):
                            elemento = "RAIO"
                        elif any(w in nome for w in ["trevas", "shadow"]):
                            elemento = "TREVAS"
                        
                        self.magic_vfx.spawn_summon(summon.x * PPM, summon.y * PPM, elemento)
                
                self.summons.extend(p.buffer_summons)
                p.buffer_summons = []
            
            # Traps (armadilhas/estruturas)
            if hasattr(p, 'buffer_traps') and p.buffer_traps:
                if not hasattr(self, 'traps'):
                    self.traps = []
                self.traps.extend(p.buffer_traps)
                p.buffer_traps = []

        # === ATUALIZA NOVOS EFEITOS v7.0 ===
        for ef in self.impact_flashes: ef.update(dt)
        self.impact_flashes = [ef for ef in self.impact_flashes if ef.vida > 0]
        for ef in self.magic_clashes: ef.update(dt)
        self.magic_clashes = [ef for ef in self.magic_clashes if ef.vida > 0]
        for ef in self.block_effects: ef.update(dt)
        self.block_effects = [ef for ef in self.block_effects if ef.vida > 0]
        for ef in self.dash_trails: ef.update(dt)
        self.dash_trails = [ef for ef in self.dash_trails if ef.vida > 0]
        for ef in self.hit_sparks: ef.update(dt)
        self.hit_sparks = [ef for ef in self.hit_sparks if ef.vida > 0]
        
        # === ATUALIZA MAGIC VFX v11.0 ===
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            self.magic_vfx.update(dt)
            # === ATUALIZA TRAILS ELEMENTAIS v11.0 (movido de desenhar para ter acesso a dt) ===
            for proj in self.projeteis:
                # v14.0: Usa cache de elemento (evita string parsing por frame)
                _elem_trail = self._get_projetil_elemento(proj)
                trail_vfx = self.magic_vfx.get_or_create_trail(id(proj), _elem_trail)
                vel_proj = getattr(proj, 'vel', getattr(proj, 'vel_disparo', 10.0))
                try:
                    vel_proj = float(vel_proj)
                except (TypeError, ValueError):
                    vel_proj = 10.0
                if not math.isfinite(vel_proj) or vel_proj <= 0:
                    vel_proj = 10.0
                trail_vfx.update(dt, proj.x * PPM, proj.y * PPM, vel_proj * 0.1)

        # === CLASH DE PROJÃ‰TEIS (v7.0) ===
        self._verificar_clash_projeteis()

        # === ATUALIZA PROJÃ‰TEIS v2.0 - Suporte a novas mecÃ¢nicas ===
        novos_projeteis = []  # Para projÃ©teis criados por split/duplicaÃ§Ã£o
        for proj in self.projeteis:
            # Passa lista de alvos para suportar homing
            alvos = self.fighters  # v13.0: Todos os lutadores como alvos de homing
            resultado = None
            
            # FP-1: verifica uma vez por classe se atualizar() aceita alvos â€” sem inspect no hot path
            if hasattr(proj, 'atualizar'):
                cls = type(proj)
                if cls not in self._atualizar_sig_cache:
                    import inspect
                    sig = inspect.signature(proj.atualizar)
                    self._atualizar_sig_cache[cls] = len(sig.parameters) > 1
                if self._atualizar_sig_cache[cls]:
                    resultado = proj.atualizar(dt, alvos)
                else:
                    proj.atualizar(dt)
            
            # Processa resultados especiais
            if resultado:
                if resultado.get("duplicar"):
                    # Cria projÃ©til duplicado
                    from nucleo.combat import Projetil
                    novo = Projetil(proj.nome, resultado["x"], resultado["y"], resultado["angulo"], proj.dono)
                    novo.dano = proj.dano * 0.7  # Duplicata tem menos dano
                    novo.duplicado = True  # Marca para nÃ£o duplicar de novo
                    novos_projeteis.append(novo)
                
                elif resultado.get("split"):
                    # Split aleatÃ³rio (Caos)
                    from nucleo.combat import Projetil
                    novo = Projetil(proj.nome, resultado["x"], resultado["y"], resultado["angulo"], proj.dono)
                    novo.dano = proj.dano * 0.5
                    novo.split_aleatorio = False  # NÃ£o continua splitando
                    novos_projeteis.append(novo)
                
                elif resultado.get("explodir"):
                    # Cria efeito de Ã¡rea na posiÃ§Ã£o
                    from nucleo.combat import AreaEffect
                    area = AreaEffect(proj.nome, resultado["x"], resultado["y"], proj.dono)
                    area.raio = resultado.get("raio", 2.0)
                    if hasattr(self, 'areas'):
                        self.areas.append(area)
                    # Efeitos visuais de explosÃ£o
                    self.impact_flashes.append(ImpactFlash(resultado["x"] * PPM, resultado["y"] * PPM, proj.cor, 2.0, "explosion"))
                    self.shockwaves.append(Shockwave(resultado["x"] * PPM, resultado["y"] * PPM, proj.cor, tamanho=2.5))
                    self._spawn_particulas_efeito(resultado["x"] * PPM, resultado["y"] * PPM, "EXPLOSAO")
            
            # v13.0: Friendly fire ON - projÃ©til pode atingir QUALQUER lutador exceto o dono
            # Encontra o alvo mais prÃ³ximo do projÃ©til (candidato a colisÃ£o)
            alvo = self._encontrar_alvo_mais_proximo(proj.x, proj.y, proj.dono)
            if alvo is None:
                continue
            # === SISTEMA DE BLOQUEIO/DESVIO v7.0 ===
            bloqueado = self._verificar_bloqueio_projetil(proj, alvo)
            if bloqueado:
                proj.ativo = False
                self._remover_trail_projetil(proj)  # BUG-SIM-01 fix: remove trail no mesmo frame
                continue
            
            # C04: verifica colisÃ£o com obstÃ¡culos destruÃ­veis antes de checar lutadores
            if self.arena:
                obs_hit = self.arena.colide_obstaculo(proj.x, proj.y, getattr(proj, 'raio', 0.3))
                if obs_hit and obs_hit.solido:
                    destruido = self.arena.danificar_obstaculo(obs_hit, getattr(proj, 'dano', 10))
                    proj.ativo = False
                    self._remover_trail_projetil(proj)
                    if destruido:
                        self._spawn_particulas_efeito(obs_hit.x * PPM, obs_hit.y * PPM, "EXPLOSAO")
                        self.textos.append(FloatingText(obs_hit.x * PPM, obs_hit.y * PPM - 30,
                                                        "DESTRUÃDO!", (255, 180, 50), 22))
                    continue

            # Verifica colisÃ£o - ArmaProjetil tem mÃ©todo prÃ³prio
            colidiu = False
            if hasattr(proj, 'colidir'):
                colidiu = proj.colidir(alvo)
            else:
                # ProjÃ©teis de skill (antigo)
                dx = alvo.pos[0] - proj.x
                dy = alvo.pos[1] - proj.y
                dist = math.hypot(dx, dy)
                colidiu = dist < (alvo.raio_fisico + proj.raio) and proj.ativo
            
            if colidiu and proj.ativo:
                # Nota: proj.ativo serÃ¡ setado false dentro do bloco se nÃ£o for perfurante
                
                # === ÃUDIO v10.0 - SOM DE IMPACTO DE PROJÃ‰TIL ===
                if self.audio:
                    # Determina tipo de projÃ©til para som adequado
                    if hasattr(proj, 'tipo'):
                        tipo_proj = proj.tipo  # "faca", "flecha", "shuriken"
                    else:
                        tipo_proj = "energy"  # ProjÃ©til de skill
                    
                    listener_x = self.cam.x / PPM
                    self.audio.play_skill("PROJETIL", tipo_proj, proj.x, listener_x, phase="impact")
                
                # === EFEITOS DE IMPACTO MELHORADOS v11.0 DRAMATIC ===
                cor_impacto = proj.cor if hasattr(proj, 'cor') else BRANCO
                self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, cor_impacto, 1.2, "magic"))
                self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, cor_impacto, tamanho=1.2))
                
                # DireÃ§Ã£o do impacto
                dx = alvo.pos[0] - proj.x
                dy = alvo.pos[1] - proj.y
                dist = math.hypot(dx, dy) or 1
                direcao_impacto = math.atan2(dy, dx)
                
                # Hit Sparks na direÃ§Ã£o do impacto
                self.hit_sparks.append(HitSpark(proj.x * PPM, proj.y * PPM, cor_impacto, direcao_impacto, 1.0))
                
                # === EXPLOSÃƒO DRAMÃTICA v11.0 ===
                if hasattr(self, 'magic_vfx') and self.magic_vfx:
                    # Determina elemento pelo nome/tipo do projÃ©til
                    elemento = "DEFAULT"
                    tipo_proj_str = str(getattr(proj, 'tipo', '')).lower()
                    nome_skill = str(getattr(proj, 'nome', '')).lower()
                    
                    _combined = nome_skill + tipo_proj_str
                    if any(w in _combined for w in ["fogo", "fire", "chama", "meteoro", "inferno", "brasas"]):
                        elemento = "FOGO"
                    elif any(w in _combined for w in ["gelo", "ice", "glacial", "nevasca", "congelar"]):
                        elemento = "GELO"
                    elif any(w in _combined for w in ["raio", "lightning", "thunder", "eletric", "relampago"]):
                        elemento = "RAIO"
                    elif any(w in _combined for w in ["trevas", "shadow", "dark", "sombra", "necro"]):
                        elemento = "TREVAS"
                    elif any(w in _combined for w in ["luz", "light", "holy", "sagrado", "divino"]):
                        elemento = "LUZ"
                    elif any(w in _combined for w in ["natureza", "nature", "veneno", "poison", "planta"]):
                        elemento = "NATUREZA"
                    elif any(w in _combined for w in ["arcano", "arcane", "mana"]):
                        elemento = "ARCANO"
                    elif any(w in _combined for w in ["sangue", "blood", "vampir"]):
                        elemento = "SANGUE"
                    elif any(w in _combined for w in ["void", "vazio"]):
                        elemento = "VOID"
                    # TambÃ©m usa cor do projÃ©til como dica
                    elif hasattr(proj, 'cor') and proj.cor:
                        r, g, b = proj.cor[:3]
                        if r > 200 and g < 100:
                            elemento = "FOGO"
                        elif b > 200 and r < 150:
                            elemento = "RAIO" if g > 150 else "GELO"
                        elif g > 180 and r < 150 and b < 150:
                            elemento = "NATUREZA"
                        elif r > 180 and b > 180 and g < 100:
                            elemento = "ARCANO"
                    
                    dano_proj = getattr(proj, 'dano', 10)
                    self.magic_vfx.spawn_explosion(
                        proj.x * PPM, proj.y * PPM, 
                        elemento=elemento, 
                        tamanho=0.6 + dano_proj * 0.02,
                        dano=dano_proj
                    )
                
                # === v11.0: VERIFICAÃ‡Ã•ES DE CONDIÃ‡ÃƒO ===
                bonus_condicao = 1.0
                if hasattr(proj, 'verificar_condicao'):
                    bonus_condicao = proj.verificar_condicao(alvo)
                
                # F04: reaÃ§Ã£o elemental â€” verifica se elemento do projÃ©til reage com
                # elemento ativo no alvo (Ãºltimo dot/efeito). Multiplica dano se houver reaÃ§Ã£o.
                reacao_nome = None
                reacao_efeito = None
                elem_proj = getattr(proj, 'elemento', None)
                if elem_proj:
                    # Pega o elemento do primeiro status effect ativo no alvo (se houver)
                    elem_alvo = None
                    for se in getattr(alvo, 'status_effects', []):
                        _n = getattr(se, 'nome', '').upper()
                        if _n in ("QUEIMANDO", "QUEIMADURA_SEVERA"):
                            elem_alvo = "FOGO"
                        elif _n in ("LENTO", "CONGELADO"):
                            elem_alvo = "GELO"
                        elif _n == "PARALISIA":
                            elem_alvo = "RAIO"
                        elif _n in ("ENVENENADO",):
                            elem_alvo = "NATUREZA"
                        elif _n in ("SANGRANDO",):
                            elem_alvo = "SANGUE"
                        if elem_alvo:
                            break
                    if elem_alvo and elem_alvo != elem_proj:
                        try:
                            from nucleo.magic_system import verificar_reacao_elemental, Elemento  # archived â†’ _archive/nucleo/
                            e1 = Elemento[elem_proj] if elem_proj in Elemento.__members__ else None
                            e2 = Elemento[elem_alvo] if elem_alvo in Elemento.__members__ else None
                            if e1 and e2:
                                reacao = verificar_reacao_elemental(e1, e2)
                                if reacao:
                                    reacao_nome, reacao_efeito, mult_reacao = reacao
                        except Exception as _e_reacao:  # E02 Sprint 11: magic_system arquivado
                            _log.debug("ReaÃ§Ã£o elemental indisponÃ­vel: %s", _e_reacao)

                # Aplica dano com efeito
                dano_base = proj.dono.get_dano_modificado(proj.dano) if hasattr(proj.dono, 'get_dano_modificado') else proj.dano
                dano_final = dano_base * bonus_condicao
                # F04: aplica multiplicador de reaÃ§Ã£o elemental se detectada
                if reacao_nome:
                    dano_final *= mult_reacao
                    self.textos.append(FloatingText(
                        alvo.pos[0] * PPM, alvo.pos[1] * PPM - 70,
                        reacao_nome, (255, 220, 80), 24
                    ))
                tipo_efeito = proj.tipo_efeito if hasattr(proj, 'tipo_efeito') else "NORMAL"
                # F04: se a reaÃ§Ã£o gerou um efeito especial, sobrepÃµe o efeito padrÃ£o
                if reacao_efeito and reacao_efeito not in ("DANO_BONUS", "PURGE"):
                    tipo_efeito = reacao_efeito
                
                # v15.0: Camera shake proporcional ao dano com threshold
                if dano_final > 8:
                    shake_intensity = min(10.0, 2.0 + dano_final * 0.15)
                    self.cam.aplicar_shake(shake_intensity, 0.07)
                self.hit_stop_timer = 0.02  # Micro hit-stop
                
                # === v11.0: PERFURAÃ‡ÃƒO - nÃ£o desativa projÃ©til ===
                # BUG-01 fix: FlechaProjetil usa .perfurante; Projetil genÃ©rico usa .perfura
                eh_perfurante = (
                    (hasattr(proj, 'perfura') and proj.perfura) or
                    (hasattr(proj, 'perfurante') and proj.perfurante)
                )
                if eh_perfurante:
                    if hasattr(proj, 'pode_atingir') and not proj.pode_atingir(alvo):
                        continue  # JÃ¡ atingiu esse alvo
                    # Controla alvos atingidos para FlechaProjetil sem alvos_perfurados
                    if not hasattr(proj, 'alvos_perfurados') or proj.alvos_perfurados is None:
                        proj.alvos_perfurados = set()
                    if id(alvo) in proj.alvos_perfurados:
                        continue
                    proj.alvos_perfurados.add(id(alvo))
                    # NÃ£o desativa - continua voando
                else:
                    proj.ativo = False
                    self._remover_trail_projetil(proj)  # BUG-SIM-01 fix: remove trail no mesmo frame
                
                fonte_proj = "weapon" if proj.__class__.__name__ in {"ArmaProjetil", "FlechaProjetil", "OrbeMagico"} else "skill"
                self._registrar_hit_stats(
                    proj.dono, alvo, dano_final,
                    elemento=tipo_efeito,
                    source_type=fonte_proj,
                    source_name=getattr(proj, 'nome', ''),
                )
                if alvo.tomar_dano(dano_final, dx/dist, dy/dist, tipo_efeito):
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                    self._registrar_kill(alvo, proj.dono.dados.nome)
                else:
                    # Texto especial para execuÃ§Ã£o
                    if bonus_condicao >= 5.0:
                        self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "EXECUÃ‡ÃƒO!", (200, 50, 50), 32))
                    
                    # Cor do texto baseado no efeito ou tipo de projÃ©til
                    if hasattr(proj, 'tipo') and proj.tipo in ["faca", "shuriken", "chakram", "flecha"]:
                        cor_txt = proj.cor if hasattr(proj, 'cor') else BRANCO
                    else:
                        cor_txt = self._get_cor_efeito(tipo_efeito)
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_final), cor_txt))
                    
                    # PartÃ­culas baseadas no efeito
                    self._spawn_particulas_efeito(alvo.pos[0]*PPM, alvo.pos[1]*PPM, tipo_efeito)
                
                # === v11.0: LIFESTEAL ===
                if hasattr(proj, 'lifesteal') and proj.lifesteal > 0:
                    cura = dano_final * proj.lifesteal
                    proj.dono.vida = min(proj.dono.vida_max, proj.dono.vida + cura)
                    self.textos.append(FloatingText(proj.dono.pos[0]*PPM, proj.dono.pos[1]*PPM - 30, f"+{int(cura)}", (200, 100, 200), 16))
                
                # Efeito DRENAR recupera vida do atacante
                elif tipo_efeito == "DRENAR":
                    proj.dono.vida = min(proj.dono.vida_max, proj.dono.vida + dano_final * 0.15)
                    self.textos.append(FloatingText(proj.dono.pos[0]*PPM, proj.dono.pos[1]*PPM - 30, f"+{int(dano_final*0.15)}", (100, 255, 150), 16))
                
                # === v11.0: EXPLOSÃƒO NO IMPACTO ===
                if hasattr(proj, 'raio_explosao') and proj.raio_explosao > 0:
                    from nucleo.combat import AreaEffect
                    explosao = AreaEffect(proj.nome + " ExplosÃ£o", proj.x, proj.y, proj.dono)
                    explosao.raio_max = proj.raio_explosao
                    explosao.dano = proj.dano * 0.5  # Dano de Ã¡rea Ã© 50% do projÃ©til
                    explosao.tipo_efeito = tipo_efeito
                    if hasattr(self, 'areas'):
                        self.areas.append(explosao)
                    self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, cor_impacto, 2.0, "explosion"))
                    self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, cor_impacto, tamanho=2.5))
                    self._spawn_particulas_efeito(proj.x * PPM, proj.y * PPM, "EXPLOSAO")
                
                # === v11.0: REMOVE CONGELAMENTO (Shatter) ===
                if hasattr(proj, 'remove_congelamento') and proj.remove_congelamento:
                    if getattr(alvo, 'congelado', False):
                        alvo.congelado = False
                        # Dano bonus por quebrar gelo
                        dano_shatter = dano_final * 0.5
                        self._registrar_hit_stats(
                            proj.dono, alvo, dano_shatter,
                            elemento="GELO",
                            source_type="status",
                            source_name=f"{getattr(proj, 'nome', 'Projetil')} (Shatter)",
                        )
                        if alvo.tomar_dano(dano_shatter, 0, 0, "GELO"):
                            self._registrar_kill(alvo, proj.dono.dados.nome)
                        self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 60, "SHATTER!", (180, 220, 255), 24))
                
                # === v11.0: CHAIN LIGHTNING ===
                if hasattr(proj, 'chain') and proj.chain > 0 and proj.chain_count < proj.chain:
                    # Encontra prÃ³ximo alvo (pode ser qualquer um exceto o atingido)
                    alvos_possiveis = [a for a in self.fighters if a != alvo and not a.morto and id(a) not in proj.chain_targets]
                    if alvos_possiveis:
                        prox_alvo = alvos_possiveis[0]
                        dx = prox_alvo.pos[0] - alvo.pos[0]
                        dy = prox_alvo.pos[1] - alvo.pos[1]
                        dist = math.hypot(dx, dy)
                        # Chain range baseado na distÃ¢ncia original ou padrÃ£o de 5.0
                        chain_range = getattr(proj, 'raio_contagio', 5.0)
                        if dist <= chain_range:
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
                            # Efeito visual de chain
                            self._spawn_particulas_efeito(alvo.pos[0]*PPM, alvo.pos[1]*PPM, "ELETRICO")

        # Adiciona projÃ©teis criados por split/duplicaÃ§Ã£o/chain
        self.projeteis.extend(novos_projeteis)
        self.projeteis = [p for p in self.projeteis if p.ativo]
        
        # === BUG-SIM-01 fix: Remove trails Ã³rfÃ£os de projÃ©teis que morreram.
        # A filtragem acima jÃ¡ garante que projÃ©teis inativos saem da lista; esta
        # passagem lida com qualquer trail cujo projÃ©til nÃ£o estÃ¡ mais presente,
        # incluindo casos onde o trail ficou sem dono por qualquer outro motivo.
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            ids_vivos = {id(proj) for proj in self.projeteis}
            ids_trails = list(self.magic_vfx.trails.keys())  # cÃ³pia para iterar com seguranÃ§a
            for trail_id in ids_trails:
                if trail_id not in ids_vivos:
                    self.magic_vfx.remove_trail(trail_id)

        # === ATUALIZA ORBES MÃGICOS (colisÃµes) ===
        for p in self.fighters:
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if orbe.ativo and orbe.estado == "disparando":
                        alvo = self._encontrar_alvo_mais_proximo(orbe.x, orbe.y, orbe.dono)
                        if alvo is None:
                            continue
                        if orbe.colidir(alvo):
                            orbe.ativo = False
                            
                            # === ÃUDIO v10.0 - SOM DE ORBE MÃGICO ===
                            if self.audio:
                                listener_x = self.cam.x / PPM
                                self.audio.play_skill("PROJETIL", "orbe_magico", orbe.x, listener_x, phase="impact")
                            
                            # Shockwave mÃ¡gico
                            self.shockwaves.append(Shockwave(orbe.x * PPM, orbe.y * PPM, orbe.cor, tamanho=1.5))
                            
                            # DireÃ§Ã£o do impacto
                            dx = alvo.pos[0] - orbe.x
                            dy = alvo.pos[1] - orbe.y
                            dist = math.hypot(dx, dy) or 1
                            
                            # Aplica dano mÃ¡gico
                            dano_final = orbe.dono.get_dano_modificado(orbe.dano) if hasattr(orbe.dono, 'get_dano_modificado') else orbe.dano
                            
                            self._registrar_hit_stats(
                                orbe.dono, alvo, dano_final,
                                elemento="NORMAL",
                                source_type="weapon",
                                source_name="Orbe Magico",
                            )
                            if alvo.tomar_dano(dano_final, dx/dist, dy/dist, "NORMAL"):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self._registrar_kill(alvo, orbe.dono.dados.nome)
                            else:
                                # Texto mÃ¡gico colorido
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_final), orbe.cor))
                                # PartÃ­culas mÃ¡gicas
                                self._spawn_particulas_efeito(alvo.pos[0]*PPM, alvo.pos[1]*PPM, "NORMAL")

        # === ATUALIZA ÃREAS v2.0 - Suporte a novas mecÃ¢nicas ===
        if hasattr(self, 'areas'):
            novas_areas = []  # Para ondas adicionais, meteoros, etc.
            for area in self.areas:
                # Passa lista de alvos para suportar pull, vortex, etc.
                alvos_area = self.fighters
                resultado = None
                
                # FP-1: verifica uma vez por classe se atualizar() aceita alvos â€” sem inspect no hot path
                if hasattr(area, 'atualizar'):
                    cls = type(area)
                    if cls not in self._atualizar_sig_cache:
                        import inspect
                        sig = inspect.signature(area.atualizar)
                        self._atualizar_sig_cache[cls] = len(sig.parameters) > 1
                    if self._atualizar_sig_cache[cls]:
                        resultado = area.atualizar(dt, alvos_area)
                    else:
                        area.atualizar(dt)
                
                # Processa resultados especiais
                if resultado:
                    for res in resultado:
                        if res.get("nova_onda"):
                            # Cria nova onda expandindo
                            from nucleo.combat import AreaEffect
                            # bugfix: garante x/y mesmo em dicts legados sem a chave
                            _nx = res.get("x", area.x)
                            _ny = res.get("y", area.y)
                            nova = AreaEffect(area.nome + " Onda", _nx, _ny, area.dono)
                            # BUG-C6: AreaEffect nÃ£o tem raio_max, usa raio
                            nova.raio = res.get("raio", area.raio * 1.5)
                            nova.dano = area.dano * 0.7
                            nova.tipo_efeito = area.tipo_efeito
                            novas_areas.append(nova)
                        
                        elif res.get("meteoro"):
                            # Cria meteoro caindo
                            from nucleo.combat import AreaEffect
                            meteoro = AreaEffect("Meteoro", res["x"], res["y"], area.dono)
                            # BUG-C6: AreaEffect nÃ£o tem raio_max, usa raio
                            meteoro.raio = res.get("raio", 3.0)
                            meteoro.dano = res.get("dano", 30)
                            meteoro.tipo_efeito = "FOGO"
                            novas_areas.append(meteoro)
                            # Efeito visual
                            self.impact_flashes.append(ImpactFlash(res["x"] * PPM, res["y"] * PPM, (255, 100, 50), 2.0, "explosion"))
                            self.shockwaves.append(Shockwave(res["x"] * PPM, res["y"] * PPM, (255, 100, 50), tamanho=2.5))
                            self._spawn_particulas_efeito(res["x"] * PPM, res["y"] * PPM, "FOGO")
                        
                        elif res.get("pull"):
                            # Aplica forÃ§a de puxÃ£o no alvo
                            alvo = res["alvo"]
                            forca = res.get("forca", 5.0)
                            dx = area.x - alvo.pos[0]
                            dy = area.y - alvo.pos[1]
                            dist = math.hypot(dx, dy) or 1
                            # Aplica velocidade em direÃ§Ã£o ao centro
                            if hasattr(alvo, 'vel'):
                                alvo.vel[0] += (dx / dist) * forca * dt
                                alvo.vel[1] += (dy / dist) * forca * dt
                        
                        elif res.get("dot_tick"):
                            # Aplica dano de DoT (Damage over Time)
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
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self._registrar_kill(alvo, area.dono.dados.nome)
                            else:
                                cor_dot = self._get_cor_efeito(tipo_dot)
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_dot), cor_dot, 14))
                
                if area.ativo and getattr(area, 'ativado', True):
                    # Verifica colisÃ£o com alvos
                    for alvo in self.fighters:
                        if alvo == area.dono or alvo in area.alvos_atingidos:
                            continue
                        dx = alvo.pos[0] - area.x
                        dy = alvo.pos[1] - area.y
                        dist = math.hypot(dx, dy)
                        if dist < area.raio_atual + alvo.raio_fisico:
                            area.alvos_atingidos.add(alvo)
                            
                            # === ÃUDIO v10.0 - SOM DE ÃREA ===
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
                            if alvo.tomar_dano(dano, dx/(dist or 1), dy/(dist or 1), area.tipo_efeito):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self._registrar_kill(alvo, area.dono.dados.nome)
                            else:
                                cor_txt = self._get_cor_efeito(area.tipo_efeito)
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), cor_txt))
            
            # Adiciona novas Ã¡reas criadas por ondas/meteoros
            self.areas.extend(novas_areas)
            self.areas = [a for a in self.areas if a.ativo]

        # === ATUALIZA BEAMS ===
        if hasattr(self, 'beams'):
            for beam in self.beams:
                beam.atualizar(dt)
                if beam.ativo and not beam.hit_aplicado:
                    alvo = self._encontrar_alvo_mais_proximo(beam.dono.pos[0], beam.dono.pos[1], beam.dono)
                    if alvo is None:
                        continue
                    if self._beam_colide_alvo(beam, alvo):
                        beam.hit_aplicado = True

                        if self.audio:
                            listener_x = self.cam.x / PPM
                            skill_name = getattr(beam, 'nome_skill', '')
                            self.audio.play_skill("BEAM", skill_name, beam.dono.pos[0], listener_x, phase="impact")

                        dano = beam.dono.get_dano_modificado(beam.dano) if hasattr(beam.dono, 'get_dano_modificado') else beam.dano
                        dx = alvo.pos[0] - beam.dono.pos[0]
                        dy = alvo.pos[1] - beam.dono.pos[1]
                        dist = math.hypot(dx, dy) or 1

                        # CM-07 fix: implementa penetra_escudo â€” zera escudos antes do dano
                        if getattr(beam, 'penetra_escudo', False):
                            for buff in getattr(alvo, 'buffs_ativos', []):
                                if getattr(buff, 'escudo_atual', 0) > 0:
                                    buff.escudo_atual = 0

                        self._registrar_hit_stats(
                            beam.dono, alvo, dano,
                            elemento=beam.tipo_efeito,
                            source_type="skill",
                            source_name=getattr(beam, 'nome', ''),
                        )
                        if alvo.tomar_dano(dano, dx/dist, dy/dist, beam.tipo_efeito):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self._registrar_kill(alvo, beam.dono.dados.nome)
                        else:
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), (255, 255, 100)))
                            self.cam.aplicar_shake(5.0, 0.06)
            self.beams = [b for b in self.beams if b.ativo]

        # === ATUALIZA SUMMONS (InvocaÃ§Ãµes) v3.0 ===
        if hasattr(self, 'summons'):
            for summon in self.summons:
                alvos = self.fighters
                resultados = summon.atualizar(dt, alvos)
                
                for res in resultados:
                    if res.get("tipo") == "ataque":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        efeito = res.get("efeito", "NORMAL")
                        # DireÃ§Ã£o do knockback
                        dx = alvo.pos[0] - summon.x
                        dy = alvo.pos[1] - summon.y
                        dist = math.hypot(dx, dy) or 1
                        self._registrar_hit_stats(
                            summon.dono, alvo, dano,
                            elemento=efeito,
                            source_type="summon",
                            source_name=getattr(summon, 'nome', 'Summon'),
                        )
                        if alvo.tomar_dano(dano, dx/dist, dy/dist, efeito):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self._registrar_kill(alvo, summon.dono.dados.nome)
                        else:
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), summon.cor))
                            self.cam.aplicar_shake(3.0, 0.05)
                    
                    elif res.get("tipo") == "aura":
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
                    
                    elif res.get("revive"):
                        # Fenix reviveu!
                        self.textos.append(FloatingText(res["x"]*PPM, res["y"]*PPM - 30, "REVIVE!", (255, 200, 50), 28))
                        self._spawn_particulas_efeito(res["x"]*PPM, res["y"]*PPM, "FOGO")
            
            # === PROJÃ‰TIL vs SUMMON â€” Summons podem ser atingidos! ===
            for proj in self.projeteis:
                if not proj.ativo:
                    continue
                for summon in self.summons:
                    if not summon.ativo:
                        continue
                    # NÃ£o acerta summons do mesmo dono
                    if proj.dono == summon.dono:
                        continue
                    dist = math.hypot(proj.x - summon.x, proj.y - summon.y)
                    if dist < (summon.raio_fisico + getattr(proj, 'raio', 0.3)):
                        dano_proj = proj.dono.get_dano_modificado(proj.dano) if hasattr(proj.dono, 'get_dano_modificado') else proj.dano
                        evento = summon.tomar_dano(dano_proj)
                        
                        # Desativa projÃ©til (exceto perfurantes)
                        eh_perfurante = getattr(proj, 'perfura', False) or getattr(proj, 'perfurante', False)
                        if not eh_perfurante:
                            proj.ativo = False
                            self._remover_trail_projetil(proj)
                        
                        # VFX e texto
                        self.textos.append(FloatingText(summon.x*PPM, summon.y*PPM - 20, int(dano_proj), (255, 180, 180), 16))
                        cor_imp = getattr(proj, 'cor', BRANCO)
                        self.impact_flashes.append(ImpactFlash(proj.x*PPM, proj.y*PPM, cor_imp, 0.8, "magic"))
                        
                        if evento:
                            if evento.get("revive"):
                                self.textos.append(FloatingText(evento["x"]*PPM, evento["y"]*PPM - 40, "REVIVE!", (255, 200, 50), 28))
                                self._spawn_particulas_efeito(evento["x"]*PPM, evento["y"]*PPM, "FOGO")
                            elif evento.get("morreu"):
                                self.textos.append(FloatingText(evento["x"]*PPM, evento["y"]*PPM - 40, "DESTRUÃDO!", (200, 200, 200), 22))
                                self._spawn_particulas_efeito(evento["x"]*PPM, evento["y"]*PPM, "EXPLOSAO")
                        break  # Cada projÃ©til atinge no mÃ¡ximo um summon por frame
            
            self.summons = [s for s in self.summons if s.ativo]
        
        # === ATUALIZA TRAPS (Estruturas/Armadilhas) v3.0 ===
        if hasattr(self, 'traps'):
            for trap in self.traps:
                trap.atualizar(dt)
                
                if not trap.ativo:
                    continue
                
                for lutador in self.fighters:
                    if lutador.morto:
                        continue
                    
                    if trap.bloqueia_movimento:
                        # === WALL MODE: Muralha de Gelo etc ===
                        if lutador == trap.dono:
                            continue
                        if trap.colidir_ponto(lutador.pos[0], lutador.pos[1]):
                            # Empurra para fora
                            dx = lutador.pos[0] - trap.x
                            dy = lutador.pos[1] - trap.y
                            dist = math.hypot(dx, dy) or 1
                            lutador.pos[0] = trap.x + (dx / dist) * (trap.largura / 2 + 0.5)
                            lutador.pos[1] = trap.y + (dy / dist) * (trap.altura / 2 + 0.5)
                            
                            # Dano de contato por segundo
                            dano_contato = trap.dano_wall_contato(dt)
                            if dano_contato > 0:
                                efeito = trap.efeito if trap.efeito != "NORMAL" else "NORMAL"
                                self._registrar_hit_stats(
                                    trap.dono, lutador, dano_contato,
                                    elemento=efeito,
                                    source_type="trap",
                                    source_name=f"{getattr(trap, 'nome', 'Trap')} (Wall)",
                                )
                                if lutador.tomar_dano(dano_contato, dx/dist, dy/dist, efeito):
                                    self.textos.append(FloatingText(lutador.pos[0]*PPM, lutador.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                    self._registrar_kill(lutador, trap.dono.dados.nome)
                    else:
                        # === TRIGGER MODE: Armadilhas ===
                        resultado = trap.tentar_trigger(lutador)
                        if resultado:
                            alvo = resultado["alvo"]
                            dano = resultado["dano"]
                            efeito = resultado.get("efeito", "NORMAL")
                            
                            # Knockback do centro da armadilha
                            dx = alvo.pos[0] - trap.x
                            dy = alvo.pos[1] - trap.y
                            dist = math.hypot(dx, dy) or 1
                            
                            self._registrar_hit_stats(
                                trap.dono, alvo, dano,
                                elemento=efeito,
                                source_type="trap",
                                source_name=getattr(trap, 'nome', 'Trap'),
                            )
                            if alvo.tomar_dano(dano, dx/dist, dy/dist, efeito):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self._registrar_kill(alvo, trap.dono.dados.nome)
                            else:
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), trap.cor))
                                self.cam.aplicar_shake(4.0, 0.06)
                            
                            # VFX de explosÃ£o da armadilha
                            self._spawn_particulas_efeito(trap.x*PPM, trap.y*PPM, 
                                                          trap.elemento if trap.elemento else "EXPLOSAO")
                            self.impact_flashes.append(ImpactFlash(trap.x*PPM, trap.y*PPM, trap.cor, 1.5, "explosion"))
                            self.shockwaves.append(Shockwave(trap.x*PPM, trap.y*PPM, trap.cor, tamanho=1.8))
                            self.textos.append(FloatingText(trap.x*PPM, trap.y*PPM - 50, "TRAP!", (255, 200, 100), 22))
            
            # === PROJÃ‰TIL vs TRAP â€” ProjÃ©teis podem destruir estruturas ===
            for proj in self.projeteis:
                if not proj.ativo:
                    continue
                for trap in self.traps:
                    if not trap.ativo:
                        continue
                    # NÃ£o atinge traps do mesmo dono
                    if proj.dono == trap.dono:
                        continue
                    if trap.colidir_ponto(proj.x, proj.y):
                        dano_proj = proj.dono.get_dano_modificado(proj.dano) if hasattr(proj.dono, 'get_dano_modificado') else proj.dano
                        destruida = trap.tomar_dano(dano_proj)
                        
                        # ProjÃ©teis sÃ£o bloqueados por walls (nÃ£o por trigger traps)
                        if trap.bloqueia_movimento and trap.bloqueia_projeteis:
                            eh_perfurante = getattr(proj, 'perfura', False) or getattr(proj, 'perfurante', False)
                            if not eh_perfurante:
                                proj.ativo = False
                                self._remover_trail_projetil(proj)
                        
                        # VFX
                        self.textos.append(FloatingText(trap.x*PPM, trap.y*PPM - 20, int(dano_proj), (200, 200, 255), 14))
                        cor_imp = getattr(proj, 'cor', BRANCO)
                        self.impact_flashes.append(ImpactFlash(proj.x*PPM, proj.y*PPM, cor_imp, 0.6, "magic"))
                        
                        if destruida:
                            self.textos.append(FloatingText(trap.x*PPM, trap.y*PPM - 40, "DESTRUÃDA!", (200, 200, 200), 20))
                            self._spawn_particulas_efeito(trap.x*PPM, trap.y*PPM, "EXPLOSAO")
                            self.shockwaves.append(Shockwave(trap.x*PPM, trap.y*PPM, trap.cor, tamanho=1.5))
                        break
            
            self.traps = [t for t in self.traps if t.ativo]
        
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
        
        # === ATUALIZA CANALIZAÃ‡Ã•ES v2.0 ===
        for lutador in self.fighters:
            if hasattr(lutador, 'channel_ativo') and lutador.channel_ativo:
                channel = lutador.channel_ativo
                alvos = self.fighters
                resultados = channel.atualizar(dt, alvos)
                
                for res in resultados:
                    if res.get("tipo") == "cura":
                        valor = res["valor"]
                        self.textos.append(FloatingText(lutador.pos[0]*PPM, lutador.pos[1]*PPM - 30, f"+{int(valor)}", (100, 255, 150), 14))
                    
                    elif res.get("tipo") == "dano":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        efeito = res.get("efeito", "NORMAL")
                        
                        self._registrar_hit_stats(
                            lutador, alvo, dano,
                            elemento=efeito,
                            source_type="status",
                            source_name=getattr(channel, 'nome', 'Channel'),
                        )
                        if alvo.tomar_dano(dano, 0, 0, efeito):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self._registrar_kill(alvo, lutador.dados.nome)
                        else:
                            cor = self._get_cor_efeito(efeito)
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), cor, 12))
                
                if not channel.ativo:
                    lutador.channel_ativo = None

        if not self.vencedor:
            # DES-4: Incrementa timer de luta e declara vencedor por HP se tempo esgotar
            self.tempo_luta += dt
            # v14.0: Update stats collector frame (approx frame from elapsed time)
            if hasattr(self, 'stats_collector'):
                self.stats_collector.set_frame(int(self.tempo_luta * 60))
            if self.tempo_luta >= self.TEMPO_MAX_LUTA:
                # v13.0: Winner por HP no timeout - time com mais HP% total ganha
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
                    # v13.0: Verifica se algum time foi eliminado (last team standing)
                    self.vencedor = self._verificar_last_team_standing()

            # Atualiza Sistema de Coreografia v5.0
            if self.choreographer:
                momento_anterior = self.choreographer.momento_atual
                self.choreographer.update(dt)
                
                # === SWORD CLASH v6.1 - Detecta inÃ­cio do momento CLASH ===
                if self.choreographer.momento_atual == "CLASH" and momento_anterior != "CLASH":
                    self._executar_sword_clash()

                # === Sprint3: slow-mo para momentos cinematogrÃ¡ficos alÃ©m da morte ===
                # Antes: ativar_slow_motion() sÃ³ em morte e timeout.
                # FINAL_SHOWDOWN, NEAR_MISS e CLIMAX_CHARGE sÃ£o momentos
                # dramaticamente tÃ£o intensos quanto morte mas nunca tinham slow-mo.
                novo_momento = self.choreographer.momento_atual
                if novo_momento != momento_anterior:
                    if novo_momento == "FINAL_SHOWDOWN":
                        # Ãšltimo confronto: slow-mo suave e longo
                        self.time_scale = 0.6
                        self.slow_mo_timer = 1.2
                    elif novo_momento == "NEAR_MISS":
                        # Quase-acerto: micro-freeze dramÃ¡tico
                        self.time_scale = 0.35
                        self.slow_mo_timer = 0.18
                    elif novo_momento == "CLIMAX_CHARGE":
                        # Ambos preparando golpe final: tensÃ£o crescente
                        self.time_scale = 0.7
                        self.slow_mo_timer = 0.8
                    elif novo_momento == "PURSUIT":
                        # PerseguiÃ§Ã£o: levemente mais lento para ampliar distÃ¢ncia visual
                        self.time_scale = 0.8
                        self.slow_mo_timer = 0.6

            self._aplicar_pressao_ritmo(dt)
            
            # v13.0: Atualiza TeamCoordinator ANTES dos lutadores individuais
            if self.modo_multi:
                from ia.team_ai import TeamCoordinatorManager
                TeamCoordinatorManager.get().update(dt, self.fighters)

            # v13.0: Atualiza TODOS os lutadores com consciÃªncia multi-combatente
            for f in self.fighters:
                if not f.morto:
                    # Encontra nearest enemy para este lutador
                    inimigo = self._encontrar_inimigo_mais_proximo(f)
                    if inimigo:
                        f.update(dt, inimigo, todos_lutadores=self.fighters)
                    else:
                        # No enemy alive â€” skip AI processing to avoid self-targeting bugs
                        f.update(dt, None, todos_lutadores=self.fighters)

            self._atualizar_aliases_principais()

            self._atualizar_direcao_cinematica(dt)
            
            # === ATUALIZA COOLDOWNS DE SOM DE PAREDE ===
            if hasattr(self, '_wall_sound_cooldown'):
                for lutador_id in list(self._wall_sound_cooldown.keys()):
                    self._wall_sound_cooldown[lutador_id] = max(0, self._wall_sound_cooldown[lutador_id] - dt)
            
            # === APLICA LIMITES DA ARENA v9.0 ===
            if self.arena:
                # v13.0: Aplica limites para TODOS os lutadores
                for f in self.fighters:
                    impacto = self.arena.aplicar_limites(f, dt)
                    if impacto > 0:
                        self._criar_efeito_colisao_parede(f, impacto)
                
                # Limpa colisÃµes antigas da arena
                self.arena.limpar_colisoes()

                # C02: processa efeitos especiais da arena sobre os lutadores
                if self.arena.efeitos_ativos:
                    self._processar_efeitos_arena(dt)

            self.resolver_fisica_corpos(dt)
            self.verificar_colisoes_combate()
            self.atualizar_rastros()
            
            # v13.0: Atualiza vida visual de todos os fighters
            for f in self.fighters:
                if f in self.vida_visual:
                    self.vida_visual[f] += (f.vida - self.vida_visual[f]) * 5 * dt
            # Backward compat
            self.vida_visual_p1 += (self.p1.vida - self.vida_visual_p1) * 5 * dt
            self.vida_visual_p2 += (self.p2.vida - self.vida_visual_p2) * 5 * dt
            
            # === DETECTA EVENTOS DE MOVIMENTO v8.0 ===
            self._detectar_eventos_movimento()
        
        # === ATUALIZA ANIMAÃ‡Ã•ES DE MOVIMENTO v8.0 ===
        if self.movement_anims:
            self.movement_anims.update(dt)
        
        # === ATUALIZA ANIMAÃ‡Ã•ES DE ATAQUE v8.0 IMPACT EDITION ===
        if self.attack_anims:
            self.attack_anims.update(dt)
        
        # v14.0: Limita partÃ­culas para performance com muitos lutadores
        MAX_PARTICULAS = 600
        if len(self.particulas) > MAX_PARTICULAS:
            # Remove as mais antigas (inÃ­cio da lista) para manter o limite
            self.particulas = self.particulas[-MAX_PARTICULAS:]
        
        alive_particulas = []
        for p in self.particulas:
            p.atualizar(dt)
            if p.vida <= 0: 
                if p.cor == VERMELHO_SANGUE and random.random() < 0.3:
                    self.decals.append(Decal(p.x, p.y, p.tamanho * 2, SANGUE_ESCURO))
            else:
                alive_particulas.append(p)
        self.particulas = alive_particulas
        if len(self.decals) > 100: self.decals.pop(0)

    # =========================================================================
    # v14.0: MÃ‰TODOS AUXILIARES MULTI-COMBATENTE + PERFORMANCE
    # =========================================================================

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
            if not hasattr(self, 'stats_collector'):
                return
            from dados.app_state import AppState
            state = AppState.get()
            # Tenta obter o match_id da luta mais recente
            match_id = getattr(state, '_last_match_id', None)
            if match_id is not None:
                self.stats_collector.flush_to_db(match_id=match_id)
                _log.debug("Match stats persistidos para match_id=%s", match_id)
            else:
                # match_id ainda nÃ£o existe (record_fight_result nÃ£o foi chamado)
                # Armazena para flush posterior via AppState.flush_pending_stats()
                state.pending_stats_collector = self.stats_collector
                _log.debug("Match stats enfileirados (match_id pendente)")
        except Exception as e:
            _log.warning("_flush_match_stats falhou (nÃ£o-fatal): %s", e)

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
        efeitos = self.arena.efeitos_ativos

        for efeito in efeitos:

            if efeito == "calor":
                # DegeneraÃ§Ã£o de estamina leve (0.5/s)
                for f in self.fighters:
                    if not f.morto:
                        f.estamina = max(0, f.estamina - 0.5 * dt)

            elif efeito in ("neve", "escorregadio"):
                # Reduz aceleraÃ§Ã£o lateral â€” simula chÃ£o escorregadio
                for f in self.fighters:
                    if not f.morto and not getattr(f, 'no_ar', False):
                        # Atenua vel_x em vez de zerar â€” comportamento de gelo
                        f.vel[0] *= max(0.0, 1.0 - dt * 4.0)

            elif efeito == "neblina":
                # Reduz alcance de percepÃ§Ã£o da IA (setado no brain uma vez)
                # Usa flag para nÃ£o re-setar todo frame
                if not getattr(self, '_neblina_aplicada', False):
                    for f in self.fighters:
                        if hasattr(f, 'brain') and f.brain:
                            # Reduz distÃ¢ncia percebida em 30%
                            f.brain._neblina_fator = 0.70
                    self._neblina_aplicada = True

            elif efeito == "chuva":
                # PartÃ­culas de chuva periÃ³dicas (a cada 0.1s)
                if not hasattr(self, '_chuva_timer'):
                    self._chuva_timer = 0.0
                self._chuva_timer += dt
                if self._chuva_timer >= 0.08:
                    self._chuva_timer = 0.0
                    import random as _r
                    for _ in range(3):
                        rx = _r.uniform(0, self.arena.largura) * PPM
                        vy = _r.uniform(8, 14) * PPM
                        self.particulas.append(
                            Particula(rx, 0, (150, 180, 220), 0, vy, 1, 0.4)
                        )

            elif efeito == "poeira":
                if not hasattr(self, '_poeira_timer'):
                    self._poeira_timer = 0.0
                self._poeira_timer += dt
                if self._poeira_timer >= 0.15:
                    self._poeira_timer = 0.0
                    import random as _r
                    for _ in range(2):
                        rx = _r.uniform(0, self.arena.largura) * PPM
                        ry = (self.arena.altura - 0.5) * PPM
                        vx = _r.uniform(-2, 2) * PPM
                        self.particulas.append(
                            Particula(rx, ry, (180, 160, 120), vx, -1, 2, 0.6)
                        )

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
        # Tenta campo direto primeiro
        _el = getattr(proj, 'elemento', '')
        if _el:
            proj._cached_elemento = _el
            return _el
        _nm = str(getattr(proj, 'nome', '')).lower()
        _tp = str(getattr(proj, 'tipo', '')).lower()
        _comb = _nm + _tp
        if any(w in _comb for w in ["fogo","fire","chama","meteoro","inferno","brasas","combustao"]):
            elem = "FOGO"
        elif any(w in _comb for w in ["gelo","ice","glacial","nevasca","cristal","congelar"]):
            elem = "GELO"
        elif any(w in _comb for w in ["raio","lightning","thunder","eletric","relampago"]):
            elem = "RAIO"
        elif any(w in _comb for w in ["trevas","shadow","dark","sombra","necro"]):
            elem = "TREVAS"
        elif any(w in _comb for w in ["luz","light","holy","sagrado","divino"]):
            elem = "LUZ"
        elif any(w in _comb for w in ["sangue","blood","vampir"]):
            elem = "SANGUE"
        elif any(w in _comb for w in ["arcano","arcane","mana","runa"]):
            elem = "ARCANO"
        elif any(w in _comb for w in ["veneno","poison","natureza","nature"]):
            elem = "NATUREZA"
        elif any(w in _comb for w in ["void","vazio","abismo"]):
            elem = "VOID"
        elif any(w in _comb for w in ["tempo","temporal","relogio","paradoxo"]):
            elem = "TEMPO"
        elif any(w in _comb for w in ["gravit","gravity","buraco negro","pulso"]):
            elem = "GRAVITACAO"
        elif any(w in _comb for w in ["caos","chaos","caotico"]):
            elem = "CAOS"
        else:
            elem = "ARCANO"
        proj._cached_elemento = elem
        return elem
    
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
            herois = [f for f in self.fighters if f.team_id != self.horde_manager.team_id]
            monstros = [f for f in self.fighters if f.team_id == self.horde_manager.team_id]
            hp_herois = sum(max(0, f.vida) for f in herois)
            hp_herois_max = sum(max(1, f.vida_max) for f in herois)
            hp_monstros = sum(max(0, f.vida) for f in monstros)
            hp_monstros_max = sum(max(1, f.vida_max) for f in monstros) or 1
            pct_herois = hp_herois / max(hp_herois_max, 1)
            pct_monstros = hp_monstros / hp_monstros_max
            if pct_herois >= pct_monstros:
                vivos = [f for f in herois if not f.morto]
                if len(vivos) == 1:
                    return vivos[0].dados.nome
                nomes = ", ".join(f.dados.nome for f in vivos) if vivos else "Expedicao"
                return f"Expedicao ({nomes})"
            return self.horde_manager.label
        if not self.modo_multi:
            # Modo legado
            pct_p1 = self.p1.vida / max(self.p1.vida_max, 1)
            pct_p2 = self.p2.vida / max(self.p2.vida_max, 1)
            if pct_p1 > pct_p2:
                return self.p1.dados.nome
            elif pct_p2 > pct_p1:
                return self.p2.dados.nome
            return "Empate"
        
        # Modo multi: soma HP% por time
        team_hp = {}
        for f in self.fighters:
            tid = f.team_id
            if tid not in team_hp:
                team_hp[tid] = {"total": 0, "max": 0}
            team_hp[tid]["total"] += max(0, f.vida)
            team_hp[tid]["max"] += max(1, f.vida_max)
        
        melhor_tid = max(team_hp.keys(), key=lambda t: team_hp[t]["total"] / team_hp[t]["max"])
        melhor_pct = team_hp[melhor_tid]["total"] / team_hp[melhor_tid]["max"]
        
        # Verifica empate
        empatados = [t for t, hp in team_hp.items() 
                     if abs(hp["total"] / hp["max"] - melhor_pct) < 0.01]
        if len(empatados) > 1:
            return "Empate"
        
        vivos = [f for f in self.fighters if f.team_id == melhor_tid and not f.morto]
        if len(vivos) == 1:
            return vivos[0].dados.nome
        nomes = ", ".join(f.dados.nome for f in vivos if not f.morto)
        return f"Time {melhor_tid + 1} ({nomes})"
    
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


