import pygame
import logging
_log = logging.getLogger("simulacao")  # QC-02
import json
import math
import random
import sys
import os

# Adiciona o diretório pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import database
from utils.config import (
    PPM, LARGURA, ALTURA, LARGURA_PORTRAIT, ALTURA_PORTRAIT, FPS,
    BRANCO, VERMELHO_SANGUE, SANGUE_ESCURO, AMARELO_FAISCA,
    AZUL_MANA, COR_CORPO, COR_P1, COR_P2, COR_FUNDO, COR_GRID,
    COR_UI_BG, COR_TEXTO_TITULO, COR_TEXTO_INFO,
)
from effects import (Particula, FloatingText, Decal, Shockwave, Câmera, EncantamentoEffect,
                     ImpactFlash, MagicClash, BlockEffect, DashTrail, HitSpark,
                     MovementAnimationManager, MovementType,  # v8.0 Movement Animations
                     AttackAnimationManager, calcular_knockback_com_forca, get_impact_tier,  # v8.0 Attack Animations
                     MagicVFXManager, get_element_from_skill)  # v11.0 Magic VFX
from effects.audio import AudioManager  # v10.0 Sistema de Áudio
from core.entities import Lutador
from core.physics import colisao_linha_circulo, intersect_line_circle, colisao_linha_linha, normalizar_angulo
from core.hitbox import sistema_hitbox, verificar_hit, get_debug_visual, atualizar_debug, DEBUG_VISUAL
from core.arena import Arena, ARENAS, get_arena, set_arena  # v9.0 Sistema de Arena
from ai import CombatChoreographer  # Sistema de Coreografia v5.0
from core.game_feel import GameFeelManager, HitStopManager  # Sistema de Game Feel v8.0

# ── Mixin imports ──
from simulation.sim_renderer import SimuladorRenderer
from simulation.sim_combat import SimuladorCombat
from simulation.sim_effects import SimuladorEffects


class Simulador(SimuladorRenderer, SimuladorCombat, SimuladorEffects):


    def run(self):
        self._slow_mo_ended = False  # Flag para tocar som de vitória uma vez
        while self.rodando:
            try:
                raw_dt = self.clock.tick(FPS) / 1000.0
                if self.slow_mo_timer > 0:
                    self.slow_mo_timer -= raw_dt
                    if self.slow_mo_timer <= 0:
                        self.time_scale = 1.0
                        # Som de fim do slow-mo e vitória
                        if not self._slow_mo_ended and self.vencedor:
                            self.audio.play_special("slowmo_end", 0.5)
                            self.audio.play_special("arena_victory", 1.0)
                            self._slow_mo_ended = True
                            # CB-04: persiste memória de rivalidade para o sistema MEL-AI-07
                            self._salvar_memorias_rivais()
                dt = raw_dt * self.time_scale
                self.processar_inputs(); self.update(dt); self.desenhar(); pygame.display.flip()
            except Exception as e:
                import traceback
                _log.debug(f"ERRO NO LOOP: {e}")
                traceback.print_exc()
                # Mostra diálogo de erro
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()
                    messagebox.showerror("Erro", f"Simulação falhou:\n{e}")
                    root.destroy()
                except Exception:  # QC-01
                    pass
                self.rodando = False
        pygame.quit()


    def _check_portrait_mode(self) -> bool:
        """Verifica se o modo retrato está ativado no config"""
        try:
            from data.app_state import AppState
            return AppState.get().match_config.get("portrait_mode", False)
        except Exception:  # QC-01
            return False

    def __init__(self):
        pygame.init()
        
        # Carrega config primeiro para saber o modo de tela
        self.portrait_mode = self._check_portrait_mode()
        
        # Define dimensões da tela baseado no modo
        if self.portrait_mode:
            from utils.config import LARGURA_PORTRAIT, ALTURA_PORTRAIT
            self.screen_width = LARGURA_PORTRAIT
            self.screen_height = ALTURA_PORTRAIT
        else:
            self.screen_width = LARGURA
            self.screen_height = ALTURA
        
        self.tela = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Neural Fights - v9.0 ARENA EDITION")
        self.clock = pygame.time.Clock()
        self.rodando = True
        
        self.cam = Câmera(self.screen_width, self.screen_height)
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

        # DES-4: Timer de luta — previne lutas infinitas (vencedor por HP ao expirar)
        self.tempo_luta = 0.0
        self.TEMPO_MAX_LUTA = 120.0

        # FP-1: cache por classe para saber se atualizar() aceita alvos — evita inspect no hot path
        self._atualizar_sig_cache = {}
        
        # Sistema de Coreografia
        self.choreographer = None
        
        # === SISTEMA DE GAME FEEL v8.0 ===
        # Gerencia Hit Stop, Super Armor, Channeling e Camera Feel
        self.game_feel = None
        
        # === SISTEMA DE ARENA v9.0 ===
        self.arena = None
        
        # === SISTEMA DE ÁUDIO v10.0 ===
        self.audio = None
        
        self.recarregar_tudo()


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
            # Reset efeitos v2.0 (skills avançadas)
            self.summons = []; self.traps = []; self.beams = []; self.areas = []
            self.time_scale = 1.0; self.slow_mo_timer = 0.0; self.hit_stop_timer = 0.0
            self.vencedor = None; self.paused = False; self.rastros = {self.p1: [], self.p2: []}
            self.tempo_luta = 0.0  # DES-4: reseta timer de luta
            if self.p1: self.vida_visual_p1 = self.p1.vida_max
            if self.p2: self.vida_visual_p2 = self.p2.vida_max
            
            # Inicializa Sistema de Coreografia
            CombatChoreographer.reset()
            self.choreographer = CombatChoreographer.get_instance()
            if self.p1 and self.p2:
                self.choreographer.registrar_lutadores(self.p1, self.p2)
            
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
            self.arena = set_arena(cenario_nome)
            
            # Configura câmera para conhecer os limites da arena
            self.cam.set_arena_bounds(
                self.arena.centro_x, 
                self.arena.centro_y,
                self.arena.largura,
                self.arena.altura
            )
            
            # Posiciona lutadores nos spawn points da arena
            if self.p1 and self.p2:
                spawn1, spawn2 = self.arena.get_spawn_points()
                self.p1.pos[0] = spawn1[0]
                self.p1.pos[1] = spawn1[1]
                self.p2.pos[0] = spawn2[0]
                self.p2.pos[1] = spawn2[1]
            
            # Rastreamento de estados anteriores para detectar mudanças
            self._prev_z = {self.p1: 0, self.p2: 0}
            
            # === INICIALIZA SISTEMA DE ÁUDIO v10.0 ===
            AudioManager.reset()
            self.audio = AudioManager.get_instance()
            self._prev_stagger = {self.p1: False, self.p2: False}
            self._prev_dash = {self.p1: 0, self.p2: 0}
            
            # === INICIALIZA MAGIC VFX v11.0 ===
            MagicVFXManager.reset()
            self.magic_vfx = MagicVFXManager.get_instance()
            
            # Som de início de arena/luta
            self.audio.play_special("arena_start", 0.8)
                
        except Exception as e: 
            import traceback
            _log.debug(f"Erro: {e}")
            traceback.print_exc()


    def carregar_luta_dados(self):
        try:
            from data.app_state import AppState
            state = AppState.get()
            config = state.match_config
            if not config.get("p1_nome") or not config.get("p2_nome"):
                raise ValueError("match_config vazio — nenhum personagem selecionado")
        except Exception as e:
            _log.debug(f"[simulacao] Erro ao ler match_config via AppState: {e}")
            return None, None, "Arena", False
        todos = state.characters   # already in-memory — no disk hit
        armas = state.weapons      # already in-memory — no disk hit
        def montar(nome):
            p = next((x for x in todos if x.nome == nome), None)
            if p and p.nome_arma:
                p.arma_obj = next((a for a in armas if a.nome == p.nome_arma), None)
                # BUG-F5: resetar durabilidade a cada luta para não persistir entre rounds
                if p.arma_obj and hasattr(p.arma_obj, 'durabilidade_max'):
                    p.arma_obj.durabilidade = p.arma_obj.durabilidade_max
                    p.arma_obj._aviso_quebrada_exibido = False
            return p
        l1 = Lutador(montar(config["p1_nome"]), 5.0, 8.0)
        l2 = Lutador(montar(config["p2_nome"]), 19.0, 8.0)
        cenario = config.get("cenario", "Arena")
        portrait_mode = config.get("portrait_mode", False)
        return l1, l2, cenario, portrait_mode


    def update(self, dt):
        self.cam.atualizar(dt, self.p1, self.p2)
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
        for p in [self.p1, self.p2]:
            # Projéteis
            if p.buffer_projeteis:
                self.projeteis.extend(p.buffer_projeteis)
                p.buffer_projeteis = []
            # Orbes mágicos
            if hasattr(p, 'buffer_orbes') and p.buffer_orbes:
                if not hasattr(self, 'orbes'):
                    self.orbes = []
                # Orbes ficam na lista do lutador para atualização de órbita
                # mas também precisamos processar colisões aqui
            # Áreas
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
            # Summons (invocações)
            if hasattr(p, 'buffer_summons') and p.buffer_summons:
                if not hasattr(self, 'summons'):
                    self.summons = []
                # Spawn effect dramático para cada novo summon
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
                _nm = str(getattr(proj, 'nome', '')).lower()
                _tp = str(getattr(proj, 'tipo', '')).lower()
                _comb = _nm + _tp
                if any(w in _comb for w in ["fogo","fire","chama","meteoro","inferno"]):
                    _elem_trail = "FOGO"
                elif any(w in _comb for w in ["gelo","ice","glacial","nevasca"]):
                    _elem_trail = "GELO"
                elif any(w in _comb for w in ["raio","lightning","thunder","eletric"]):
                    _elem_trail = "RAIO"
                elif any(w in _comb for w in ["trevas","shadow","dark","sombra","necro"]):
                    _elem_trail = "TREVAS"
                elif any(w in _comb for w in ["luz","light","holy","sagrado"]):
                    _elem_trail = "LUZ"
                elif any(w in _comb for w in ["sangue","blood"]):
                    _elem_trail = "SANGUE"
                elif any(w in _comb for w in ["arcano","arcane","mana"]):
                    _elem_trail = "ARCANO"
                elif any(w in _comb for w in ["veneno","poison","natureza","nature"]):
                    _elem_trail = "NATUREZA"
                else:
                    _elem_trail = "ARCANO"  # default mágico
                trail_vfx = self.magic_vfx.get_or_create_trail(id(proj), _elem_trail)
                vel_proj = getattr(proj, 'vel', getattr(proj, 'vel_disparo', 10.0))
                trail_vfx.update(dt, proj.x * PPM, proj.y * PPM, vel_proj * 0.1)

        # === CLASH DE PROJÉTEIS (v7.0) ===
        self._verificar_clash_projeteis()

        # === ATUALIZA PROJÉTEIS v2.0 - Suporte a novas mecânicas ===
        novos_projeteis = []  # Para projéteis criados por split/duplicação
        for proj in self.projeteis:
            # Passa lista de alvos para suportar homing
            alvos = [self.p1, self.p2]
            resultado = None
            
            # FP-1: verifica uma vez por classe se atualizar() aceita alvos — sem inspect no hot path
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
                    # Cria projétil duplicado
                    from core.combat import Projetil
                    novo = Projetil(proj.nome, resultado["x"], resultado["y"], resultado["angulo"], proj.dono)
                    novo.dano = proj.dano * 0.7  # Duplicata tem menos dano
                    novo.duplicado = True  # Marca para não duplicar de novo
                    novos_projeteis.append(novo)
                
                elif resultado.get("split"):
                    # Split aleatório (Caos)
                    from core.combat import Projetil
                    novo = Projetil(proj.nome, resultado["x"], resultado["y"], resultado["angulo"], proj.dono)
                    novo.dano = proj.dano * 0.5
                    novo.split_aleatorio = False  # Não continua splitando
                    novos_projeteis.append(novo)
                
                elif resultado.get("explodir"):
                    # Cria efeito de área na posição
                    from core.combat import AreaEffect
                    area = AreaEffect(proj.nome, resultado["x"], resultado["y"], proj.dono)
                    area.raio = resultado.get("raio", 2.0)
                    if hasattr(self, 'areas'):
                        self.areas.append(area)
                    # Efeitos visuais de explosão
                    self.impact_flashes.append(ImpactFlash(resultado["x"] * PPM, resultado["y"] * PPM, proj.cor, 2.0, "explosion"))
                    self.shockwaves.append(Shockwave(resultado["x"] * PPM, resultado["y"] * PPM, proj.cor, tamanho=2.5))
                    self._spawn_particulas_efeito(resultado["x"] * PPM, resultado["y"] * PPM, "EXPLOSAO")
            
            alvo = self.p2 if proj.dono == self.p1 else self.p1
            
            # === SISTEMA DE BLOQUEIO/DESVIO v7.0 ===
            bloqueado = self._verificar_bloqueio_projetil(proj, alvo)
            if bloqueado:
                proj.ativo = False
                self._remover_trail_projetil(proj)  # BUG-SIM-01 fix: remove trail no mesmo frame
                continue
            
            # Verifica colisão - ArmaProjetil tem método próprio
            colidiu = False
            if hasattr(proj, 'colidir'):
                colidiu = proj.colidir(alvo)
            else:
                # Projéteis de skill (antigo)
                dx = alvo.pos[0] - proj.x
                dy = alvo.pos[1] - proj.y
                dist = math.hypot(dx, dy)
                colidiu = dist < (alvo.raio_fisico + proj.raio) and proj.ativo
            
            if colidiu and proj.ativo:
                # Nota: proj.ativo será setado false dentro do bloco se não for perfurante
                
                # === ÁUDIO v10.0 - SOM DE IMPACTO DE PROJÉTIL ===
                if self.audio:
                    # Determina tipo de projétil para som adequado
                    if hasattr(proj, 'tipo'):
                        tipo_proj = proj.tipo  # "faca", "flecha", "shuriken"
                    else:
                        tipo_proj = "energy"  # Projétil de skill
                    
                    listener_x = self.cam.x / PPM
                    self.audio.play_skill("PROJETIL", tipo_proj, proj.x, listener_x, phase="impact")
                
                # === EFEITOS DE IMPACTO MELHORADOS v11.0 DRAMATIC ===
                cor_impacto = proj.cor if hasattr(proj, 'cor') else BRANCO
                self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, cor_impacto, 1.2, "magic"))
                self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, cor_impacto, tamanho=1.2))
                
                # Direção do impacto
                dx = alvo.pos[0] - proj.x
                dy = alvo.pos[1] - proj.y
                dist = math.hypot(dx, dy) or 1
                direcao_impacto = math.atan2(dy, dx)
                
                # Hit Sparks na direção do impacto
                self.hit_sparks.append(HitSpark(proj.x * PPM, proj.y * PPM, cor_impacto, direcao_impacto, 1.0))
                
                # === EXPLOSÃO DRAMÁTICA v11.0 ===
                if hasattr(self, 'magic_vfx') and self.magic_vfx:
                    # Determina elemento pelo nome/tipo do projétil
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
                    # Também usa cor do projétil como dica
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
                
                # === v11.0: VERIFICAÇÕES DE CONDIÇÃO ===
                bonus_condicao = 1.0
                if hasattr(proj, 'verificar_condicao'):
                    bonus_condicao = proj.verificar_condicao(alvo)
                
                # Aplica dano com efeito
                dano_base = proj.dono.get_dano_modificado(proj.dano) if hasattr(proj.dono, 'get_dano_modificado') else proj.dano
                dano_final = dano_base * bonus_condicao
                tipo_efeito = proj.tipo_efeito if hasattr(proj, 'tipo_efeito') else "NORMAL"
                
                # Camera shake proporcional ao dano
                shake_intensity = min(15.0, 5.0 + dano_final * 0.3)
                self.cam.aplicar_shake(shake_intensity, 0.1)
                self.hit_stop_timer = 0.03  # Micro hit-stop
                
                # === v11.0: PERFURAÇÃO - não desativa projétil ===
                # BUG-01 fix: FlechaProjetil usa .perfurante; Projetil genérico usa .perfura
                eh_perfurante = (
                    (hasattr(proj, 'perfura') and proj.perfura) or
                    (hasattr(proj, 'perfurante') and proj.perfurante)
                )
                if eh_perfurante:
                    if hasattr(proj, 'pode_atingir') and not proj.pode_atingir(alvo):
                        continue  # Já atingiu esse alvo
                    # Controla alvos atingidos para FlechaProjetil sem alvos_perfurados
                    if not hasattr(proj, 'alvos_perfurados') or proj.alvos_perfurados is None:
                        proj.alvos_perfurados = set()
                    if id(alvo) in proj.alvos_perfurados:
                        continue
                    proj.alvos_perfurados.add(id(alvo))
                    # Não desativa - continua voando
                else:
                    proj.ativo = False
                    self._remover_trail_projetil(proj)  # BUG-SIM-01 fix: remove trail no mesmo frame
                
                if alvo.tomar_dano(dano_final, dx/dist, dy/dist, tipo_efeito):
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                    self.ativar_slow_motion(); self.vencedor = proj.dono.dados.nome
                else:
                    # Texto especial para execução
                    if bonus_condicao >= 5.0:
                        self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "EXECUÇÃO!", (200, 50, 50), 32))
                    
                    # Cor do texto baseado no efeito ou tipo de projétil
                    if hasattr(proj, 'tipo') and proj.tipo in ["faca", "shuriken", "chakram", "flecha"]:
                        cor_txt = proj.cor if hasattr(proj, 'cor') else BRANCO
                    else:
                        cor_txt = self._get_cor_efeito(tipo_efeito)
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_final), cor_txt))
                    
                    # Partículas baseadas no efeito
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
                
                # === v11.0: EXPLOSÃO NO IMPACTO ===
                if hasattr(proj, 'raio_explosao') and proj.raio_explosao > 0:
                    from core.combat import AreaEffect
                    explosao = AreaEffect(proj.nome + " Explosão", proj.x, proj.y, proj.dono)
                    explosao.raio_max = proj.raio_explosao
                    explosao.dano = proj.dano * 0.5  # Dano de área é 50% do projétil
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
                        alvo.tomar_dano(dano_final * 0.5, 0, 0, "GELO")
                        self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 60, "SHATTER!", (180, 220, 255), 24))
                
                # === v11.0: CHAIN LIGHTNING ===
                if hasattr(proj, 'chain') and proj.chain > 0 and proj.chain_count < proj.chain:
                    # Encontra próximo alvo (pode ser qualquer um exceto o atingido)
                    alvos_possiveis = [a for a in [self.p1, self.p2] if a != alvo and a.vivo and id(a) not in proj.chain_targets]
                    if alvos_possiveis:
                        prox_alvo = alvos_possiveis[0]
                        dx = prox_alvo.pos[0] - alvo.pos[0]
                        dy = prox_alvo.pos[1] - alvo.pos[1]
                        dist = math.hypot(dx, dy)
                        # Chain range baseado na distância original ou padrão de 5.0
                        chain_range = getattr(proj, 'raio_contagio', 5.0)
                        if dist <= chain_range:
                            from core.combat import Projetil
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

        # Adiciona projéteis criados por split/duplicação/chain
        self.projeteis.extend(novos_projeteis)
        self.projeteis = [p for p in self.projeteis if p.ativo]
        
        # === BUG-SIM-01 fix: Remove trails órfãos de projéteis que morreram.
        # A filtragem acima já garante que projéteis inativos saem da lista; esta
        # passagem lida com qualquer trail cujo projétil não está mais presente,
        # incluindo casos onde o trail ficou sem dono por qualquer outro motivo.
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            ids_vivos = {id(proj) for proj in self.projeteis}
            ids_trails = list(self.magic_vfx.trails.keys())  # cópia para iterar com segurança
            for trail_id in ids_trails:
                if trail_id not in ids_vivos:
                    self.magic_vfx.remove_trail(trail_id)

        # === ATUALIZA ORBES MÁGICOS (colisões) ===
        for p in [self.p1, self.p2]:
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if orbe.ativo and orbe.estado == "disparando":
                        alvo = self.p2 if orbe.dono == self.p1 else self.p1
                        if orbe.colidir(alvo):
                            orbe.ativo = False
                            
                            # === ÁUDIO v10.0 - SOM DE ORBE MÁGICO ===
                            if self.audio:
                                listener_x = self.cam.x / PPM
                                self.audio.play_skill("PROJETIL", "orbe_magico", orbe.x, listener_x, phase="impact")
                            
                            # Shockwave mágico
                            self.shockwaves.append(Shockwave(orbe.x * PPM, orbe.y * PPM, orbe.cor, tamanho=1.5))
                            
                            # Direção do impacto
                            dx = alvo.pos[0] - orbe.x
                            dy = alvo.pos[1] - orbe.y
                            dist = math.hypot(dx, dy) or 1
                            
                            # Aplica dano mágico
                            dano_final = orbe.dono.get_dano_modificado(orbe.dano) if hasattr(orbe.dono, 'get_dano_modificado') else orbe.dano
                            
                            if alvo.tomar_dano(dano_final, dx/dist, dy/dist, "NORMAL"):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self.ativar_slow_motion()
                                self.vencedor = orbe.dono.dados.nome
                            else:
                                # Texto mágico colorido
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_final), orbe.cor))
                                # Partículas mágicas
                                self._spawn_particulas_efeito(alvo.pos[0]*PPM, alvo.pos[1]*PPM, "NORMAL")

        # === ATUALIZA ÁREAS v2.0 - Suporte a novas mecânicas ===
        if hasattr(self, 'areas'):
            novas_areas = []  # Para ondas adicionais, meteoros, etc.
            for area in self.areas:
                # Passa lista de alvos para suportar pull, vortex, etc.
                alvos_area = [self.p1, self.p2]
                resultado = None
                
                # FP-1: verifica uma vez por classe se atualizar() aceita alvos — sem inspect no hot path
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
                            from core.combat import AreaEffect
                            nova = AreaEffect(area.nome + " Onda", res["x"], res["y"], area.dono)
                            # BUG-C6: AreaEffect não tem raio_max, usa raio
                            nova.raio = res.get("raio", area.raio * 1.5)
                            nova.dano = area.dano * 0.7
                            nova.tipo_efeito = area.tipo_efeito
                            novas_areas.append(nova)
                        
                        elif res.get("meteoro"):
                            # Cria meteoro caindo
                            from core.combat import AreaEffect
                            meteoro = AreaEffect("Meteoro", res["x"], res["y"], area.dono)
                            # BUG-C6: AreaEffect não tem raio_max, usa raio
                            meteoro.raio = res.get("raio", 3.0)
                            meteoro.dano = res.get("dano", 30)
                            meteoro.tipo_efeito = "FOGO"
                            novas_areas.append(meteoro)
                            # Efeito visual
                            self.impact_flashes.append(ImpactFlash(res["x"] * PPM, res["y"] * PPM, (255, 100, 50), 2.0, "explosion"))
                            self.shockwaves.append(Shockwave(res["x"] * PPM, res["y"] * PPM, (255, 100, 50), tamanho=2.5))
                            self._spawn_particulas_efeito(res["x"] * PPM, res["y"] * PPM, "FOGO")
                        
                        elif res.get("pull"):
                            # Aplica força de puxão no alvo
                            alvo = res["alvo"]
                            forca = res.get("forca", 5.0)
                            dx = area.x - alvo.pos[0]
                            dy = area.y - alvo.pos[1]
                            dist = math.hypot(dx, dy) or 1
                            # Aplica velocidade em direção ao centro
                            if hasattr(alvo, 'vel'):
                                alvo.vel[0] += (dx / dist) * forca * dt
                                alvo.vel[1] += (dy / dist) * forca * dt
                        
                        elif res.get("dot_tick"):
                            # Aplica dano de DoT (Damage over Time)
                            alvo = res["alvo"]
                            dano_dot = res.get("dano", 5)
                            tipo_dot = res.get("tipo", "FOGO")
                            if alvo.tomar_dano(dano_dot, 0, 0, tipo_dot):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self.ativar_slow_motion()
                                self.vencedor = area.dono.dados.nome
                            else:
                                cor_dot = self._get_cor_efeito(tipo_dot)
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_dot), cor_dot, 14))
                
                if area.ativo and getattr(area, 'ativado', True):
                    # Verifica colisão com alvos
                    for alvo in [self.p1, self.p2]:
                        if alvo == area.dono or alvo in area.alvos_atingidos:
                            continue
                        dx = alvo.pos[0] - area.x
                        dy = alvo.pos[1] - area.y
                        dist = math.hypot(dx, dy)
                        if dist < area.raio_atual + alvo.raio_fisico:
                            area.alvos_atingidos.add(alvo)
                            
                            # === ÁUDIO v10.0 - SOM DE ÁREA ===
                            if self.audio:
                                listener_x = self.cam.x / PPM
                                skill_name = getattr(area, 'nome_skill', '')
                                self.audio.play_skill("AREA", skill_name, area.x, listener_x, phase="impact")
                            
                            dano = area.dono.get_dano_modificado(area.dano) if hasattr(area.dono, 'get_dano_modificado') else area.dano
                            if alvo.tomar_dano(dano, dx/(dist or 1), dy/(dist or 1), area.tipo_efeito):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self.ativar_slow_motion()
                                self.vencedor = area.dono.dados.nome
                            else:
                                cor_txt = self._get_cor_efeito(area.tipo_efeito)
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), cor_txt))
            
            # Adiciona novas áreas criadas por ondas/meteoros
            self.areas.extend(novas_areas)
            self.areas = [a for a in self.areas if a.ativo]

        # === ATUALIZA BEAMS ===
        if hasattr(self, 'beams'):
            for beam in self.beams:
                beam.atualizar(dt)
                if beam.ativo and not beam.hit_aplicado:
                    alvo = self.p2 if beam.dono == self.p1 else self.p1
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

                        # CM-07 fix: implementa penetra_escudo — zera escudos antes do dano
                        if getattr(beam, 'penetra_escudo', False):
                            for buff in getattr(alvo, 'buffs_ativos', []):
                                if getattr(buff, 'escudo_atual', 0) > 0:
                                    buff.escudo_atual = 0

                        if alvo.tomar_dano(dano, dx/dist, dy/dist, beam.tipo_efeito):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self.ativar_slow_motion()
                            self.vencedor = beam.dono.dados.nome
                        else:
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), (255, 255, 100)))
                            self.cam.aplicar_shake(8.0, 0.1)
            self.beams = [b for b in self.beams if b.ativo]

        # === ATUALIZA SUMMONS (Invocações) v2.0 ===
        if hasattr(self, 'summons'):
            for summon in self.summons:
                alvos = [self.p1, self.p2]
                resultados = summon.atualizar(dt, alvos)
                
                for res in resultados:
                    if res.get("tipo") == "ataque":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        if alvo.tomar_dano(dano, 0, 0, "NORMAL"):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self.ativar_slow_motion()
                            self.vencedor = summon.dono.dados.nome
                        else:
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), summon.cor))
                    
                    elif res.get("tipo") == "aura":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        alvo.tomar_dano(dano, 0, 0, "NORMAL")
                    
                    elif res.get("revive"):
                        # Fenix reviveu!
                        self.textos.append(FloatingText(res["x"]*PPM, res["y"]*PPM - 30, "REVIVE!", (255, 200, 50), 28))
                        self._spawn_particulas_efeito(res["x"]*PPM, res["y"]*PPM, "FOGO")
            
            self.summons = [s for s in self.summons if s.ativo]
        
        # === ATUALIZA TRAPS (Estruturas) v2.0 ===
        if hasattr(self, 'traps'):
            for trap in self.traps:
                trap.atualizar(dt)
                
                # Verifica colisão com lutadores
                if trap.bloqueia_movimento:
                    for lutador in [self.p1, self.p2]:
                        if lutador == trap.dono:
                            continue
                        if trap.colidir_ponto(lutador.pos[0], lutador.pos[1]):
                            # Empurra para fora
                            dx = lutador.pos[0] - trap.x
                            dy = lutador.pos[1] - trap.y
                            dist = math.hypot(dx, dy) or 1
                            lutador.pos[0] = trap.x + (dx / dist) * (trap.largura / 2 + 0.5)
                            lutador.pos[1] = trap.y + (dy / dist) * (trap.altura / 2 + 0.5)
                            
                            # Dano de contato
                            if trap.dano_contato > 0:
                                lutador.tomar_dano(trap.dano_contato * dt, 0, 0, trap.efeito_contato or "NORMAL")
            
            self.traps = [t for t in self.traps if t.ativo]
        
        # === ATUALIZA TRANSFORMAÇÕES v2.0 ===
        for lutador in [self.p1, self.p2]:
            if hasattr(lutador, 'transformacao_ativa') and lutador.transformacao_ativa:
                transform = lutador.transformacao_ativa
                alvos = [self.p1, self.p2]
                resultados = transform.atualizar(dt, alvos)
                
                for res in resultados:
                    if res.get("tipo") == "contato":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        alvo.tomar_dano(dano, 0, 0, "NORMAL")
                    elif res.get("tipo") == "slow":
                        alvo = res["alvo"]
                        alvo.slow_timer = max(alvo.slow_timer, 0.1)
                        alvo.slow_fator = min(alvo.slow_fator, res["fator"])
                
                if not transform.ativo:
                    lutador.transformacao_ativa = None
        
        # === ATUALIZA CANALIZAÇÕES v2.0 ===
        for lutador in [self.p1, self.p2]:
            if hasattr(lutador, 'channel_ativo') and lutador.channel_ativo:
                channel = lutador.channel_ativo
                alvos = [self.p1, self.p2]
                resultados = channel.atualizar(dt, alvos)
                
                for res in resultados:
                    if res.get("tipo") == "cura":
                        valor = res["valor"]
                        self.textos.append(FloatingText(lutador.pos[0]*PPM, lutador.pos[1]*PPM - 30, f"+{int(valor)}", (100, 255, 150), 14))
                    
                    elif res.get("tipo") == "dano":
                        alvo = res["alvo"]
                        dano = res["dano"]
                        efeito = res.get("efeito", "NORMAL")
                        
                        if alvo.tomar_dano(dano, 0, 0, efeito):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self.ativar_slow_motion()
                            self.vencedor = lutador.dados.nome
                        else:
                            cor = self._get_cor_efeito(efeito)
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), cor, 12))
                
                if not channel.ativo:
                    lutador.channel_ativo = None

        if not self.vencedor:
            # DES-4: Incrementa timer de luta e declara vencedor por HP se tempo esgotar
            self.tempo_luta += dt
            if self.tempo_luta >= self.TEMPO_MAX_LUTA:
                pct_p1 = self.p1.vida / max(self.p1.vida_max, 1)
                pct_p2 = self.p2.vida / max(self.p2.vida_max, 1)
                if pct_p1 > pct_p2:
                    self.vencedor = self.p1.dados.nome
                elif pct_p2 > pct_p1:
                    self.vencedor = self.p2.dados.nome
                else:
                    self.vencedor = "Empate"
                self.textos.append(FloatingText(
                    self.screen_width // 2, self.screen_height // 2 - 80,
                    "TEMPO ESGOTADO!", (255, 200, 50), 36
                ))
                self.ativar_slow_motion()

            # Atualiza Sistema de Coreografia v5.0
            if self.choreographer:
                momento_anterior = self.choreographer.momento_atual
                self.choreographer.update(dt)
                
                # === SWORD CLASH v6.1 - Detecta início do momento CLASH ===
                if self.choreographer.momento_atual == "CLASH" and momento_anterior != "CLASH":
                    self._executar_sword_clash()
            
            self.p1.update(dt, self.p2); self.p2.update(dt, self.p1)
            
            # === ATUALIZA COOLDOWNS DE SOM DE PAREDE ===
            if hasattr(self, '_wall_sound_cooldown'):
                for lutador_id in list(self._wall_sound_cooldown.keys()):
                    self._wall_sound_cooldown[lutador_id] = max(0, self._wall_sound_cooldown[lutador_id] - dt)
            
            # === APLICA LIMITES DA ARENA v9.0 ===
            if self.arena:
                # Aplica colisão com paredes para ambos os lutadores
                # Retorna intensidade do impacto (0.0 se apenas deslizando)
                p1_impacto = self.arena.aplicar_limites(self.p1, dt)
                p2_impacto = self.arena.aplicar_limites(self.p2, dt)
                
                # Debug apenas para impactos reais
                if p1_impacto > 0 or p2_impacto > 0:
                    _log.debug(f"[COLLISION] P1_impacto={p1_impacto:.1f} P2_impacto={p2_impacto:.1f}")
                
                # Efeitos visuais de colisão com parede (apenas impactos reais)
                if p1_impacto > 0:
                    self._criar_efeito_colisao_parede(self.p1, p1_impacto)
                if p2_impacto > 0:
                    self._criar_efeito_colisao_parede(self.p2, p2_impacto)
                
                # Limpa colisões antigas da arena
                self.arena.limpar_colisoes()
            
            self.resolver_fisica_corpos(dt)
            self.verificar_colisoes_combate()
            self.atualizar_rastros()
            self.vida_visual_p1 += (self.p1.vida - self.vida_visual_p1) * 5 * dt
            self.vida_visual_p2 += (self.p2.vida - self.vida_visual_p2) * 5 * dt
            
            # === DETECTA EVENTOS DE MOVIMENTO v8.0 ===
            self._detectar_eventos_movimento()
        
        # === ATUALIZA ANIMAÇÕES DE MOVIMENTO v8.0 ===
        if self.movement_anims:
            self.movement_anims.update(dt)
        
        # === ATUALIZA ANIMAÇÕES DE ATAQUE v8.0 IMPACT EDITION ===
        if self.attack_anims:
            self.attack_anims.update(dt)
        
        for p in self.particulas[:]:
            p.atualizar(dt)
            if p.vida <= 0: 
                if p.cor == VERMELHO_SANGUE and random.random() < 0.3:
                    self.decals.append(Decal(p.x, p.y, p.tamanho * 2, SANGUE_ESCURO))
                self.particulas.remove(p)
        if len(self.decals) > 100: self.decals.pop(0)

if __name__ == "__main__":
    Simulador().run()
