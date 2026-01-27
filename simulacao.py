import pygame
import json
import math
import random
import database
from config import *
from effects import (Particula, FloatingText, Decal, Shockwave, Câmera, EncantamentoEffect,
                     ImpactFlash, MagicClash, BlockEffect, DashTrail, HitSpark,
                     MovementAnimationManager, MovementType,  # v8.0 Movement Animations
                     AttackAnimationManager, calcular_knockback_com_forca, get_impact_tier)  # v8.0 Attack Animations
from entities import Lutador
from physics import colisao_linha_circulo, intersect_line_circle, colisao_linha_linha, normalizar_angulo
from hitbox import sistema_hitbox, verificar_hit, get_debug_visual, atualizar_debug, DEBUG_VISUAL
from ai import CombatChoreographer  # Sistema de Coreografia v5.0
from core.game_feel import GameFeelManager, HitStopManager  # Sistema de Game Feel v8.0
from arena import Arena, ARENAS, get_arena, set_arena  # v9.0 Sistema de Arena

class Simulador:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Neural Fights - v9.0 ARENA EDITION")
        self.clock = pygame.time.Clock()
        self.rodando = True
        
        self.cam = Câmera()
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
        
        # Sistema de Coreografia
        self.choreographer = None
        
        # === SISTEMA DE GAME FEEL v8.0 ===
        # Gerencia Hit Stop, Super Armor, Channeling e Camera Feel
        self.game_feel = None
        
        # === SISTEMA DE ARENA v9.0 ===
        self.arena = None
        
        self.recarregar_tudo()

    def recarregar_tudo(self):
        try:
            self.p1, self.p2 = self.carregar_luta_dados()
            self.particulas = []; self.decals = []; self.textos = []; self.shockwaves = []; self.projeteis = []
            # Reset novos efeitos v7.0
            self.impact_flashes = []; self.magic_clashes = []; self.block_effects = []
            self.dash_trails = []; self.hit_sparks = []
            self.time_scale = 1.0; self.slow_mo_timer = 0.0; self.hit_stop_timer = 0.0
            self.vencedor = None; self.paused = False; self.rastros = {self.p1: [], self.p2: []}
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
            self.arena = set_arena("Arena")  # Arena padrão 30x20 metros
            
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
            self._prev_stagger = {self.p1: False, self.p2: False}
            self._prev_dash = {self.p1: 0, self.p2: 0}
                
        except Exception as e: 
            import traceback
            print(f"Erro: {e}")
            traceback.print_exc()

    def carregar_luta_dados(self):
        try:
            with open("match_config.json", "r", encoding="utf-8") as f: config = json.load(f)
        except: return None, None 
        todos = database.carregar_personagens()
        armas = database.carregar_armas()
        def montar(nome):
            p = next((x for x in todos if x.nome == nome), None)
            if p and p.nome_arma: p.arma_obj = next((a for a in armas if a.nome == p.nome_arma), None)
            return p
        l1 = Lutador(montar(config["p1_nome"]), 5.0, 8.0)
        l2 = Lutador(montar(config["p2_nome"]), 19.0, 8.0)
        return l1, l2

    def processar_inputs(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.rodando = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.rodando = False 
                if event.key == pygame.K_r: self.recarregar_tudo()
                if event.key == pygame.K_SPACE: self.paused = not self.paused
                if event.key == pygame.K_g: self.show_hud = not self.show_hud  # G para HUD
                if event.key == pygame.K_h: self.show_hitbox_debug = not self.show_hitbox_debug  # H para HITBOX DEBUG
                if event.key == pygame.K_TAB: self.show_analysis = not self.show_analysis
                if event.key == pygame.K_t: self.time_scale = 0.2 if self.time_scale == 1.0 else 1.0
                if event.key == pygame.K_f: self.time_scale = 3.0 if self.time_scale == 1.0 else 1.0
                if event.key == pygame.K_1: self.cam.modo = "P1"
                if event.key == pygame.K_2: self.cam.modo = "P2"
                if event.key == pygame.K_3: self.cam.modo = "AUTO"
            if event.type == pygame.MOUSEWHEEL:
                self.cam.target_zoom += event.y * 0.1
                self.cam.target_zoom = max(0.5, min(self.cam.target_zoom, 3.0))

        keys = pygame.key.get_pressed()
        move_speed = 15 / self.cam.zoom
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.cam.y -= move_speed; self.cam.modo = "MANUAL"
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.cam.y += move_speed; self.cam.modo = "MANUAL"
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.cam.x -= move_speed; self.cam.modo = "MANUAL"
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.cam.x += move_speed; self.cam.modo = "MANUAL"

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

        # === CLASH DE PROJÉTEIS (v7.0) ===
        self._verificar_clash_projeteis()

        # === ATUALIZA PROJÉTEIS ===
        for proj in self.projeteis:
            proj.atualizar(dt)
            alvo = self.p2 if proj.dono == self.p1 else self.p1
            
            # === SISTEMA DE BLOQUEIO/DESVIO v7.0 ===
            bloqueado = self._verificar_bloqueio_projetil(proj, alvo)
            if bloqueado:
                proj.ativo = False
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
                proj.ativo = False
                
                # === EFEITOS DE IMPACTO MELHORADOS v7.0 ===
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
                
                # Aplica dano com efeito
                dano_final = proj.dono.get_dano_modificado(proj.dano) if hasattr(proj.dono, 'get_dano_modificado') else proj.dano
                tipo_efeito = proj.tipo_efeito if hasattr(proj, 'tipo_efeito') else "NORMAL"
                
                # Camera shake proporcional ao dano
                shake_intensity = min(15.0, 5.0 + dano_final * 0.3)
                self.cam.aplicar_shake(shake_intensity, 0.1)
                self.hit_stop_timer = 0.03  # Micro hit-stop
                
                if alvo.tomar_dano(dano_final, dx/dist, dy/dist, tipo_efeito):
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                    self.ativar_slow_motion(); self.vencedor = proj.dono.dados.nome
                else:
                    # Cor do texto baseado no efeito ou tipo de projétil
                    if hasattr(proj, 'tipo') and proj.tipo in ["faca", "shuriken", "chakram", "flecha"]:
                        cor_txt = proj.cor if hasattr(proj, 'cor') else BRANCO
                    else:
                        cor_txt = self._get_cor_efeito(tipo_efeito)
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_final), cor_txt))
                    
                    # Partículas baseadas no efeito
                    self._spawn_particulas_efeito(alvo.pos[0]*PPM, alvo.pos[1]*PPM, tipo_efeito)
                
                # Efeito DRENAR recupera vida do atacante
                if tipo_efeito == "DRENAR":
                    proj.dono.vida = min(proj.dono.vida_max, proj.dono.vida + dano_final * 0.15)
                    self.textos.append(FloatingText(proj.dono.pos[0]*PPM, proj.dono.pos[1]*PPM - 30, f"+{int(dano_final*0.15)}", (100, 255, 150), 16))

        self.projeteis = [p for p in self.projeteis if p.ativo]

        # === ATUALIZA ORBES MÁGICOS (colisões) ===
        for p in [self.p1, self.p2]:
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if orbe.ativo and orbe.estado == "disparando":
                        alvo = self.p2 if orbe.dono == self.p1 else self.p1
                        if orbe.colidir(alvo):
                            orbe.ativo = False
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

        # === ATUALIZA ÁREAS ===
        if hasattr(self, 'areas'):
            for area in self.areas:
                area.atualizar(dt)
                if area.ativo:
                    # Verifica colisão com alvos
                    for alvo in [self.p1, self.p2]:
                        if alvo == area.dono or alvo in area.alvos_atingidos:
                            continue
                        dx = alvo.pos[0] - area.x
                        dy = alvo.pos[1] - area.y
                        dist = math.hypot(dx, dy)
                        if dist < area.raio_atual + alvo.raio_fisico:
                            area.alvos_atingidos.add(alvo)
                            dano = area.dono.get_dano_modificado(area.dano) if hasattr(area.dono, 'get_dano_modificado') else area.dano
                            if alvo.tomar_dano(dano, dx/(dist or 1), dy/(dist or 1), area.tipo_efeito):
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                                self.ativar_slow_motion()
                                self.vencedor = area.dono.dados.nome
                            else:
                                cor_txt = self._get_cor_efeito(area.tipo_efeito)
                                self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), cor_txt))
            self.areas = [a for a in self.areas if a.ativo]

        # === ATUALIZA BEAMS ===
        if hasattr(self, 'beams'):
            for beam in self.beams:
                beam.atualizar(dt)
                if beam.ativo and not beam.hit_aplicado:
                    alvo = self.p2 if beam.dono == self.p1 else self.p1
                    # Verifica se beam cruza com alvo
                    if self._beam_colide_alvo(beam, alvo):
                        beam.hit_aplicado = True
                        dano = beam.dono.get_dano_modificado(beam.dano) if hasattr(beam.dono, 'get_dano_modificado') else beam.dano
                        dx = alvo.pos[0] - beam.dono.pos[0]
                        dy = alvo.pos[1] - beam.dono.pos[1]
                        dist = math.hypot(dx, dy) or 1
                        if alvo.tomar_dano(dano, dx/dist, dy/dist, beam.tipo_efeito):
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                            self.ativar_slow_motion()
                            self.vencedor = beam.dono.dados.nome
                        else:
                            self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano), (255, 255, 100)))
                            self.cam.aplicar_shake(8.0, 0.1)
            self.beams = [b for b in self.beams if b.ativo]

        if not self.vencedor:
            # Atualiza Sistema de Coreografia v5.0
            if self.choreographer:
                self.choreographer.update(dt)
            
            self.p1.update(dt, self.p2); self.p2.update(dt, self.p1)
            
            # === APLICA LIMITES DA ARENA v9.0 ===
            if self.arena:
                # Aplica colisão com paredes para ambos os lutadores
                p1_colidiu = self.arena.aplicar_limites(self.p1, dt)
                p2_colidiu = self.arena.aplicar_limites(self.p2, dt)
                
                # Efeitos visuais de colisão com parede
                if p1_colidiu:
                    self._criar_efeito_colisao_parede(self.p1)
                if p2_colidiu:
                    self._criar_efeito_colisao_parede(self.p2)
                
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

    def _criar_efeito_colisao_parede(self, lutador):
        """Cria efeitos visuais quando lutador colide com parede da arena"""
        # Só cria efeito se a velocidade for significativa
        velocidade = math.hypot(lutador.vel[0], lutador.vel[1])
        if velocidade < 3:
            return
        
        # Intensidade baseada na velocidade
        intensidade = min(1.0, velocidade / 15)
        
        # Partículas de poeira/impacto
        x_px = lutador.pos[0] * PPM
        y_px = lutador.pos[1] * PPM
        cor_parede = self.arena.config.cor_borda if self.arena else (100, 100, 120)
        
        num_particulas = int(5 + intensidade * 10)
        for _ in range(num_particulas):
            angulo = random.uniform(0, math.pi * 2)
            vel = random.uniform(30, 80) * intensidade
            # Particula(x, y, cor, vel_x, vel_y, tamanho, vida_util)
            self.particulas.append(Particula(
                x_px + random.uniform(-15, 15),
                y_px + random.uniform(-15, 15),
                cor_parede,
                math.cos(angulo) * vel,
                math.sin(angulo) * vel,
                random.uniform(3, 6),
                random.uniform(0.2, 0.5)
            ))
        
        # Shake da câmera proporcional à intensidade
        if intensidade > 0.5:
            self.cam.aplicar_shake(intensidade * 8, 0.1)
        
        # Flash de impacto se muito forte
        if intensidade > 0.7:
            self.impact_flashes.append(ImpactFlash(x_px, y_px, cor_parede, intensidade * 0.8, "physical"))

    def _get_cor_efeito(self, efeito):
        """Retorna cor do texto baseado no tipo de efeito"""
        cores = {
            "NORMAL": BRANCO,
            "FOGO": (255, 100, 0),
            "QUEIMAR": (255, 150, 50),
            "GELO": (150, 220, 255),
            "CONGELAR": (100, 200, 255),
            "VENENO": (100, 255, 100),
            "SANGRAMENTO": (180, 0, 30),
            "RAIO": (255, 255, 100),
            "ATORDOAR": (255, 255, 150),
            "TREVAS": (150, 0, 200),
            "DRENAR": (80, 0, 120),
            "EMPURRAO": (200, 200, 255),
            "EXPLOSAO": (255, 200, 50),
        }
        return cores.get(efeito, BRANCO)
    
    def _spawn_particulas_efeito(self, x, y, efeito):
        """Spawna partículas específicas do efeito"""
        cores_part = {
            "QUEIMAR": (255, 100, 0),
            "CONGELAR": (150, 220, 255),
            "VENENO": (100, 255, 100),
            "SANGRAMENTO": VERMELHO_SANGUE,
            "ATORDOAR": (255, 255, 100),
            "DRENAR": (80, 0, 120),
            "EXPLOSAO": (255, 200, 50),
        }
        cor = cores_part.get(efeito)
        if cor:
            for _ in range(8):
                vx = random.uniform(-8, 8)
                vy = random.uniform(-8, 8)
                self.particulas.append(Particula(x, y, cor, vx, vy, random.randint(3, 6), 0.5))
    
    def _beam_colide_alvo(self, beam, alvo):
        """Verifica se um beam colide com um alvo"""
        # Usa colisão linha-círculo
        from physics import colisao_linha_circulo
        pt1 = (beam.x1 * PPM, beam.y1 * PPM)
        pt2 = (beam.x2 * PPM, beam.y2 * PPM)
        centro = (alvo.pos[0] * PPM, alvo.pos[1] * PPM)
        raio = alvo.raio_fisico * PPM
        return colisao_linha_circulo(pt1, pt2, centro, raio)

    # =========================================================================
    # SISTEMA DE DETECÇÃO DE EVENTOS DE MOVIMENTO v8.0
    # =========================================================================
    
    def _detectar_eventos_movimento(self):
        """
        Detecta eventos de movimento para disparar animações apropriadas.
        
        Eventos detectados:
        - Aterrissagem (z era > 0, agora é 0)
        - Pulo (z era 0, agora > 0)
        - Dash (dash_timer aumentou)
        - Knockback (velocidade alta após tomar dano)
        - Recuperação de stagger (stun_timer zerou)
        - Corrida rápida (velocidade alta contínua)
        """
        if not self.movement_anims:
            return
        
        for lutador in [self.p1, self.p2]:
            if lutador.morto:
                continue
            
            z_atual = getattr(lutador, 'z', 0)
            z_anterior = self._prev_z.get(lutador, 0)
            
            # === ATERRISSAGEM ===
            if z_anterior > 0.5 and z_atual <= 0.1:
                # Calcula intensidade baseada na velocidade de queda
                vel_queda = abs(getattr(lutador, 'vel_z', 0))
                self.movement_anims.criar_landing_effect(lutador, vel_queda + 5)
            
            # === PULO ===
            elif z_atual > 0.5 and z_anterior <= 0.1:
                self.movement_anims.criar_jump_effect(lutador)
            
            # === DASH ===
            dash_atual = getattr(lutador, 'dash_timer', 0)
            dash_anterior = self._prev_dash.get(lutador, 0)
            
            if dash_atual > dash_anterior and dash_atual > 0.1:
                # Novo dash detectado
                direcao = math.radians(lutador.angulo_olhar)
                
                # Determina tipo de dash baseado na ação
                acao = getattr(lutador.brain, 'acao_atual', "")
                if acao in ["RECUAR", "FUGIR"]:
                    tipo = MovementType.DASH_BACKWARD
                elif acao in ["CIRCULAR", "FLANQUEAR"]:
                    tipo = MovementType.DASH_LATERAL
                else:
                    tipo = MovementType.DASH_FORWARD
                
                self.movement_anims.criar_dash_effect(lutador, direcao, tipo)
            
            # === RECUPERAÇÃO DE STAGGER ===
            stagger_atual = getattr(lutador, 'stun_timer', 0) > 0
            stagger_anterior = self._prev_stagger.get(lutador, False)
            
            if stagger_anterior and not stagger_atual:
                # Acabou de se recuperar
                self.movement_anims.criar_recovery_effect(lutador)
            
            # === CORRIDA RÁPIDA ===
            vel_magnitude = math.hypot(lutador.vel[0], lutador.vel[1])
            if vel_magnitude > 12.0 and z_atual <= 0.1:
                # Correndo rápido no chão
                if random.random() < 0.15:  # Não spammar efeitos
                    direcao = math.atan2(lutador.vel[1], lutador.vel[0])
                    self.movement_anims.criar_sprint_effect(lutador, direcao)
            
            # Atualiza estados anteriores
            self._prev_z[lutador] = z_atual
            self._prev_stagger[lutador] = stagger_atual
            self._prev_dash[lutador] = dash_atual
    
    def _criar_knockback_visual(self, lutador, direcao: float, intensidade: float):
        """
        Cria efeitos visuais de knockback.
        Chamado quando um personagem leva um golpe forte.
        """
        if self.movement_anims:
            self.movement_anims.criar_knockback_effect(lutador, direcao, intensidade)

    # =========================================================================
    # SISTEMA DE CLASH DE PROJÉTEIS v7.0
    # =========================================================================
    
    def _verificar_clash_projeteis(self):
        """Verifica colisão entre projéteis de diferentes donos"""
        projs_p1 = [p for p in self.projeteis if p.dono == self.p1 and p.ativo]
        projs_p2 = [p for p in self.projeteis if p.dono == self.p2 and p.ativo]
        
        # Também checa orbes mágicos
        orbes_p1 = []
        orbes_p2 = []
        if hasattr(self.p1, 'buffer_orbes'):
            orbes_p1 = [o for o in self.p1.buffer_orbes if o.ativo and o.estado == "disparando"]
        if hasattr(self.p2, 'buffer_orbes'):
            orbes_p2 = [o for o in self.p2.buffer_orbes if o.ativo and o.estado == "disparando"]
        
        # Combina projéteis e orbes
        todos_p1 = projs_p1 + orbes_p1
        todos_p2 = projs_p2 + orbes_p2
        
        for p1 in todos_p1:
            for p2 in todos_p2:
                if not (getattr(p1, 'ativo', True) and getattr(p2, 'ativo', True)):
                    continue
                
                # Distância entre projéteis
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dist = math.hypot(dx, dy)
                
                # Raio de colisão (soma dos raios)
                r1 = getattr(p1, 'raio', 0.2)
                r2 = getattr(p2, 'raio', 0.2)
                
                if dist < r1 + r2 + 0.3:  # Margem extra para visual
                    # CLASH DETECTADO!
                    self._executar_clash_magico(p1, p2)
    
    def _executar_clash_magico(self, proj1, proj2):
        """Executa efeito de clash entre dois projéteis/magias"""
        # Desativa ambos
        proj1.ativo = False
        proj2.ativo = False
        
        # Ponto médio do clash
        mx = (proj1.x + proj2.x) / 2
        my = (proj1.y + proj2.y) / 2
        
        # Cores dos projéteis
        cor1 = getattr(proj1, 'cor', (255, 100, 100))
        cor2 = getattr(proj2, 'cor', (100, 100, 255))
        
        # Cria efeito de clash mágico
        self.magic_clashes.append(MagicClash(mx * PPM, my * PPM, cor1, cor2, tamanho=1.5))
        
        # Flash de impacto duplo
        self.impact_flashes.append(ImpactFlash(mx * PPM, my * PPM, cor1, 1.5, "clash"))
        
        # Shockwave grande
        self.shockwaves.append(Shockwave(mx * PPM, my * PPM, BRANCO, tamanho=2.0))
        
        # Texto de CLASH
        self.textos.append(FloatingText(mx * PPM, my * PPM - 40, "CLASH!", AMARELO_FAISCA, 35))
        
        # Camera shake e hit stop dramáticos
        self.cam.aplicar_shake(25.0, 0.25)
        self.hit_stop_timer = 0.15
        
        # Partículas extras
        for _ in range(30):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(80, 200)
            cor = random.choice([cor1, cor2])
            self.particulas.append(Particula(
                mx * PPM, my * PPM, cor,
                math.cos(ang) * vel / 60, math.sin(ang) * vel / 60,
                random.randint(4, 8), 0.4
            ))
    
    # =========================================================================
    # SISTEMA DE BLOQUEIO E DESVIO v7.0
    # =========================================================================
    
    def _verificar_bloqueio_projetil(self, proj, alvo):
        """Verifica se o alvo pode bloquear ou desviar do projétil"""
        if not proj.ativo:
            return False
        
        # Distância do projétil ao alvo
        dx = alvo.pos[0] - proj.x
        dy = alvo.pos[1] - proj.y
        dist = math.hypot(dx, dy)
        
        # Só verifica se projétil está perto
        if dist > alvo.raio_fisico + 1.5:
            return False
        
        # === BLOQUEIO COM ESCUDO ORBITAL ===
        if alvo.dados.arma_obj and "Orbital" in alvo.dados.arma_obj.tipo:
            escudo_info = alvo.get_escudo_info()
            if escudo_info:
                # Verifica se projétil está na área do escudo
                escudo_pos, escudo_raio, escudo_ang, escudo_arco = escudo_info
                dx_e = proj.x * PPM - escudo_pos[0]
                dy_e = proj.y * PPM - escudo_pos[1]
                dist_escudo = math.hypot(dx_e, dy_e)
                
                if dist_escudo < escudo_raio + proj.raio * PPM:
                    # Verifica ângulo
                    ang_proj = math.degrees(math.atan2(dy_e, dx_e))
                    diff_ang = abs(normalizar_angulo(ang_proj - escudo_ang))
                    
                    if diff_ang <= escudo_arco / 2:
                        # BLOQUEADO!
                        self._efeito_bloqueio(proj, alvo, escudo_pos)
                        return True
        
        # === DESVIO COM DASH ===
        if hasattr(alvo, 'dash_timer') and alvo.dash_timer > 0:
            # Durante dash, chance de desviar
            if dist < alvo.raio_fisico + 0.5:
                # Dash evasivo bem-sucedido!
                self._efeito_desvio_dash(proj, alvo)
                return True
        
        # === BLOQUEIO DURANTE ATAQUE (timing perfeito) ===
        if alvo.atacando and alvo.timer_animacao > 0.15:  # Frame inicial do ataque
            if alvo.dados.arma_obj and "Reta" in alvo.dados.arma_obj.tipo:
                # Verifica se arma intercepta projétil
                linha_arma = alvo.get_pos_ponteira_arma()
                if linha_arma:
                    from physics import colisao_linha_circulo
                    if colisao_linha_circulo(linha_arma[0], linha_arma[1], 
                                            (proj.x * PPM, proj.y * PPM), 
                                            proj.raio * PPM + 5):
                        # PARRY!
                        self._efeito_parry(proj, alvo)
                        return True
        
        return False
    
    def _efeito_bloqueio(self, proj, bloqueador, pos_escudo):
        """Efeito visual de bloqueio"""
        # Direção do impacto
        ang = math.atan2(proj.y * PPM - pos_escudo[1], proj.x * PPM - pos_escudo[0])
        
        # Cor do bloqueador
        cor = (bloqueador.dados.cor_r, bloqueador.dados.cor_g, bloqueador.dados.cor_b)
        
        # Efeito de bloqueio
        self.block_effects.append(BlockEffect(proj.x * PPM, proj.y * PPM, cor, ang))
        
        # Texto
        self.textos.append(FloatingText(proj.x * PPM, proj.y * PPM - 30, "BLOCK!", (100, 200, 255), 22))
        
        # Partículas metálicas
        for _ in range(12):
            vx = math.cos(ang + random.uniform(-0.5, 0.5)) * random.uniform(3, 8)
            vy = math.sin(ang + random.uniform(-0.5, 0.5)) * random.uniform(3, 8)
            self.particulas.append(Particula(proj.x * PPM, proj.y * PPM, AMARELO_FAISCA, vx, vy, 3, 0.3))
        
        # Shake leve
        self.cam.aplicar_shake(8.0, 0.1)
        self.hit_stop_timer = 0.05
    
    def _efeito_desvio_dash(self, proj, desviador):
        """Efeito visual de desvio com dash"""
        # Trail do dash
        if hasattr(desviador, 'pos_historico') and len(desviador.pos_historico) > 2:
            posicoes = [(p[0] * PPM, p[1] * PPM) for p in desviador.pos_historico[-8:]]
            cor = (desviador.dados.cor_r, desviador.dados.cor_g, desviador.dados.cor_b)
            self.dash_trails.append(DashTrail(posicoes, cor))
        
        # Texto
        self.textos.append(FloatingText(desviador.pos[0] * PPM, desviador.pos[1] * PPM - 50, "DODGE!", (150, 255, 150), 24))
        
        # Pequeno slow-mo para drama
        self.time_scale = 0.5
        self.slow_mo_timer = 0.3
    
    def _efeito_parry(self, proj, parryer):
        """Efeito visual de parry (defesa com ataque)"""
        # Cor do parryer
        cor = (parryer.dados.cor_r, parryer.dados.cor_g, parryer.dados.cor_b)
        
        # Flash de impacto especial
        self.impact_flashes.append(ImpactFlash(proj.x * PPM, proj.y * PPM, AMARELO_FAISCA, 1.8, "clash"))
        
        # Texto PARRY!
        self.textos.append(FloatingText(proj.x * PPM, proj.y * PPM - 40, "PARRY!", AMARELO_FAISCA, 28))
        
        # Shockwave dourada
        self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, AMARELO_FAISCA, tamanho=1.5))
        
        # Hit sparks dramáticas
        ang = math.atan2(proj.y - parryer.pos[1], proj.x - parryer.pos[0])
        self.hit_sparks.append(HitSpark(proj.x * PPM, proj.y * PPM, AMARELO_FAISCA, ang, 1.5))
        
        # Camera e timing
        self.cam.aplicar_shake(15.0, 0.15)
        self.hit_stop_timer = 0.1

    def atualizar_rastros(self):
        for p in [self.p1, self.p2]:
            if p.morto: self.rastros[p] = []; continue
            if p.atacando and p.dados.arma_obj and "Reta" in p.dados.arma_obj.tipo:
                coords = p.get_pos_ponteira_arma()
                if coords: self.rastros[p].append((coords[1], coords[0]))
            else: self.rastros[p] = []
            if len(self.rastros[p]) > 10: self.rastros[p].pop(0)

    def resolver_fisica_corpos(self, dt):
        """Resolve colisão física entre os dois lutadores impedindo sobreposição"""
        p1, p2 = self.p1, self.p2
        if p1.morto or p2.morto: 
            return
        
        # Múltiplas iterações para garantir separação completa
        for _ in range(3):
            # Calcula distância entre centros
            dx = p2.pos[0] - p1.pos[0]
            dy = p2.pos[1] - p1.pos[1]
            dist = math.hypot(dx, dy)
            
            # Soma dos raios (distância mínima permitida)
            soma_raios = p1.raio_fisico + p2.raio_fisico
            
            # Só processa se estiverem se sobrepondo E na mesma altura (Z)
            if dist >= soma_raios or abs(p1.z - p2.z) >= 1.0:
                break  # Não há sobreposição, sai do loop
                
            # Calcula penetração (quanto estão se sobrepondo)
            penetracao = soma_raios - dist
            
            # Vetor normal de separação (de p1 para p2)
            if dist > 0.001:
                nx, ny = dx / dist, dy / dist
            else:
                # Se estiverem exatamente no mesmo ponto, escolhe direção aleatória
                ang = random.uniform(0, math.pi * 2)
                nx, ny = math.cos(ang), math.sin(ang)
            
            # === SEPARAÇÃO FÍSICA INSTANTÂNEA ===
            # Move cada corpo para fora da sobreposição (metade para cada lado)
            separacao = (penetracao / 2.0) + 0.02  # Margem de segurança
            
            p1.pos[0] -= nx * separacao
            p1.pos[1] -= ny * separacao
            p2.pos[0] += nx * separacao
            p2.pos[1] += ny * separacao
        
        # === VELOCIDADE DE REPULSÃO (aplica uma vez) ===
        # Recalcula distância após separação
        dx = p2.pos[0] - p1.pos[0]
        dy = p2.pos[1] - p1.pos[1]
        dist = math.hypot(dx, dy)
        
        # Se ainda estiverem muito próximos, aplica repulsão
        if dist < soma_raios * 1.2 and dist > 0.001:
            nx, ny = dx / dist, dy / dist
            fator_repulsao = 6.0
            p1.vel[0] -= nx * fator_repulsao
            p1.vel[1] -= ny * fator_repulsao
            p2.vel[0] += nx * fator_repulsao
            p2.vel[1] += ny * fator_repulsao

    def verificar_colisoes_combate(self):
        if self.p1.dados.arma_obj and self.p2.dados.arma_obj:
            if self.checar_clash_geral(self.p1, self.p2):
                self.efeito_clash(self.p1, self.p2); return 
        morreu_1 = self.checar_ataque(self.p1, self.p2)
        morreu_2 = self.checar_ataque(self.p2, self.p1)
        if morreu_1: self.ativar_slow_motion(); self.vencedor = self.p1.dados.nome
        if morreu_2: self.ativar_slow_motion(); self.vencedor = self.p2.dados.nome

    def efeito_clash(self, p1, p2):
        """Efeito visual dramático quando armas colidem"""
        mx = (p1.pos[0] + p2.pos[0]) / 2 * PPM
        my = (p1.pos[1] + p2.pos[1]) / 2 * PPM
        
        # === PARTÍCULAS DE FAÍSCA EM TODAS DIREÇÕES ===
        for _ in range(35):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(80, 180)
            vx = math.cos(ang) * vel / 60
            vy = math.sin(ang) * vel / 60
            self.particulas.append(Particula(mx, my, AMARELO_FAISCA, vx, vy, random.randint(3, 7), 0.5))
        
        # Cores das armas para o efeito
        cor1 = (p1.dados.arma_obj.r, p1.dados.arma_obj.g, p1.dados.arma_obj.b) if hasattr(p1.dados.arma_obj, 'r') else (255, 255, 255)
        cor2 = (p2.dados.arma_obj.r, p2.dados.arma_obj.g, p2.dados.arma_obj.b) if hasattr(p2.dados.arma_obj, 'r') else (255, 255, 255)
        
        # === EFEITOS VISUAIS ESPECIAIS ===
        self.magic_clashes.append(MagicClash(mx, my, cor1, cor2, tamanho=1.2))
        self.impact_flashes.append(ImpactFlash(mx, my, AMARELO_FAISCA, 1.5, "clash"))
        
        # Hit sparks em ambas direções
        ang_p1_p2 = math.atan2(p2.pos[1] - p1.pos[1], p2.pos[0] - p1.pos[0])
        self.hit_sparks.append(HitSpark(mx, my, cor1, ang_p1_p2, 1.5))
        self.hit_sparks.append(HitSpark(mx, my, cor2, ang_p1_p2 + math.pi, 1.5))
        
        # Empurra ambos para trás
        vec_x = p1.pos[0] - p2.pos[0]
        vec_y = p1.pos[1] - p2.pos[1]
        mag = math.hypot(vec_x, vec_y) or 1
        p1.tomar_clash(vec_x/mag, vec_y/mag)
        p2.tomar_clash(-vec_x/mag, -vec_y/mag)
        
        # === EFEITOS DE CÂMERA DRAMÁTICOS ===
        self.cam.aplicar_shake(25.0, 0.25)
        self.cam.zoom_punch(0.15, 0.15)
        self.hit_stop_timer = 0.15  # Pausa dramática
        
        # Shockwave grande
        self.shockwaves.append(Shockwave(mx, my, BRANCO, 1.5))
        
        # Texto CLASH! maior
        self.textos.append(FloatingText(mx, my - 60, "CLASH!", AMARELO_FAISCA, 38))

    def checar_clash_geral(self, p1, p2):
        if "Reta" in p1.dados.arma_obj.tipo and "Reta" in p2.dados.arma_obj.tipo:
            l1 = p1.get_pos_ponteira_arma(); l2 = p2.get_pos_ponteira_arma()
            if l1 and l2: return colisao_linha_linha(l1[0], l1[1], l2[0], l2[1])
        if "Reta" in p1.dados.arma_obj.tipo and "Orbital" in p2.dados.arma_obj.tipo:
            return self.checar_clash_espada_escudo(p1, p2)
        if "Orbital" in p1.dados.arma_obj.tipo and "Reta" in p2.dados.arma_obj.tipo:
            return self.checar_clash_espada_escudo(p2, p1)
        return False

    def checar_clash_espada_escudo(self, atacante, escudeiro):
        linha = atacante.get_pos_ponteira_arma()
        info = escudeiro.get_escudo_info()
        if not linha or not info: return False
        pts = intersect_line_circle(linha[0], linha[1], info[0], info[1])
        if not pts: return False
        for px, py in pts:
            dx = px - info[0][0]; dy = py - info[0][1]
            ang = math.degrees(math.atan2(dy, dx))
            diff = normalizar_angulo(ang - info[2])
            if abs(diff) <= info[3] / 2: return True
        return False

    def checar_ataque(self, atacante, defensor):
        """
        Verifica ataque usando o novo sistema de hitbox com debug.
        
        === INTEGRAÇÃO GAME FEEL v8.0 ===
        - Hit Stop proporcional à classe (Força > Ágil)
        - Super Armor para tanks/berserkers
        - Camera shake baseado em INTENSIDADE, não velocidade
        """
        
        # Armas ranged e mágicas NÃO usam hitbox direta
        # Elas causam dano apenas via projéteis/orbes
        arma = atacante.dados.arma_obj
        if arma and arma.tipo in ["Arremesso", "Arco", "Mágica"]:
            return False  # Dano é feito pelos projéteis/orbes, não pela hitbox
        
        # Usa o novo sistema modular para armas melee
        acertou, motivo = verificar_hit(atacante, defensor)
        
        if acertou:
            dx, dy = int(defensor.pos[0] * PPM), int(defensor.pos[1] * PPM)
            vx = defensor.pos[0] - atacante.pos[0]
            vy = defensor.pos[1] - atacante.pos[1]
            mag = math.hypot(vx, vy) or 1
            
            # Usa o novo sistema de dano modificado
            dano_base = arma.dano * (atacante.dados.forca / 2.0)
            dano, is_critico = atacante.calcular_dano_ataque(dano_base) if hasattr(atacante, 'calcular_dano_ataque') else (dano_base, False)
            
            # Notifica Sistema de Coreografia v5.0
            if self.choreographer:
                self.choreographer.registrar_hit(atacante, defensor)
            
            # === GAME FEEL v8.0 - DETERMINA TIPO DE GOLPE ===
            classe_atacante = getattr(atacante, 'classe_nome', "Guerreiro")
            
            # Classes de FORÇA têm golpes PESADOS
            if any(c in classe_atacante for c in ["Berserker", "Guerreiro", "Cavaleiro", "Gladiador"]):
                tipo_golpe = "PESADO" if dano > 20 else "MEDIO"
                if dano > 35 or is_critico:
                    tipo_golpe = "DEVASTADOR"
            # Classes ÁGEIS têm golpes LEVES (mantém fluidez)
            elif any(c in classe_atacante for c in ["Assassino", "Ninja", "Ladino"]):
                tipo_golpe = "LEVE"
                if is_critico:  # Críticos de assassino são DEVASTADORES
                    tipo_golpe = "DEVASTADOR"
            # Híbridos e outros
            else:
                tipo_golpe = "MEDIO"
                if dano > 25:
                    tipo_golpe = "PESADO"
            
            # === GAME FEEL - VERIFICA SUPER ARMOR DO DEFENSOR ===
            resultado_hit = None
            if self.game_feel:
                # Calcula progresso da animação de ataque do defensor (para super armor)
                progresso_anim = 0.0
                if hasattr(defensor, 'timer_animacao') and defensor.atacando:
                    progresso_anim = 1.0 - (defensor.timer_animacao / 0.25)
                
                # Verifica super armor
                self.game_feel.verificar_super_armor(
                    defensor, progresso_anim, 
                    getattr(defensor.brain, 'acao_atual', "")
                )
                
                # Processa hit através do Game Feel Manager
                resultado_hit = self.game_feel.processar_hit(
                    atacante=atacante,
                    alvo=defensor,
                    dano=dano,
                    posicao=(dx, dy),
                    tipo_golpe=tipo_golpe,
                    is_critico=is_critico,
                    knockback=(vx/mag * 15, vy/mag * 15)
                )
                
                # Usa valores processados pelo Game Feel
                dano = resultado_hit["dano_final"]
                
                # === FEEDBACK VISUAL DE SUPER ARMOR ===
                if resultado_hit["super_armor_ativa"]:
                    # Efeito especial - defensor "tankou" o golpe
                    self.textos.append(FloatingText(dx, dy - 60, "ARMOR!", (255, 200, 50), 22))
                    # Partículas de escudo
                    for _ in range(8):
                        ang = random.uniform(0, math.pi * 2)
                        vel = random.uniform(3, 8)
                        self.particulas.append(Particula(
                            dx, dy, (255, 200, 100), 
                            math.cos(ang) * vel, math.sin(ang) * vel,
                            random.randint(4, 8), 0.4
                        ))
            
            # === EFEITOS DE IMPACTO MELHORADOS v8.0 IMPACT EDITION ===
            direcao_impacto = math.atan2(vy, vx)
            forca_atacante = atacante.dados.forca
            
            # Hit Spark na direção do golpe
            self.hit_sparks.append(HitSpark(dx, dy, AMARELO_FAISCA, direcao_impacto, 1.2))
            
            # Impact Flash colorido
            cor_arma = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else BRANCO
            self.impact_flashes.append(ImpactFlash(dx, dy, cor_arma, 1.0, "normal"))
            
            # === SISTEMA DE KNOCKBACK BASEADO EM FORÇA ===
            # Calcula knockback com a nova fórmula
            pos_impacto = (dx / PPM, dy / PPM)
            kb_base = calcular_knockback_com_forca(atacante, defensor, direcao_impacto, dano)
            kb_x, kb_y = kb_base[0], kb_base[1]
            
            if resultado_hit and not resultado_hit["sofreu_stagger"]:
                # Super Armor ativa - knockback reduzido
                kb_x *= 0.2
                kb_y *= 0.2
            
            # === EFEITOS DE ATAQUE BASEADOS EM FORÇA ===
            if self.attack_anims:
                impact_result = self.attack_anims.criar_attack_impact(
                    atacante=atacante,
                    alvo=defensor,
                    dano=dano,
                    posicao=pos_impacto,
                    direcao=direcao_impacto,
                    tipo_dano="physical",
                    is_critico=is_critico
                )
                
                # Aplica shake/zoom do sistema de ataque se não houver GameFeel
                if not self.game_feel:
                    self.cam.aplicar_shake(impact_result['shake_intensity'], impact_result['shake_duration'])
                    if impact_result['zoom_punch'] > 0:
                        self.cam.zoom_punch(impact_result['zoom_punch'], 0.15)
            
            if defensor.tomar_dano(dano, kb_x, kb_y, "NORMAL"):
                # === MORTE - EFEITOS MÁXIMOS ===
                self.spawn_particulas(dx, dy, vx/mag, vy/mag, VERMELHO_SANGUE, 50)
                
                # Knockback visual épico na morte
                self._criar_knockback_visual(defensor, direcao_impacto, dano * 1.5)
                
                # Game Feel já processou camera shake para morte
                if not self.game_feel:
                    self.cam.aplicar_shake(35.0, 0.5)
                    self.cam.zoom_punch(0.3, 0.2)
                    self.hit_stop_timer = 0.4
                else:
                    # Efeitos adicionais de morte
                    self.cam.zoom_punch(0.35, 0.25)
                
                self.shockwaves.append(Shockwave(dx, dy, VERMELHO_SANGUE, 2.0))
                self.textos.append(FloatingText(dx, dy - 50, "FATAL!", VERMELHO_SANGUE, 45))
                self.ativar_slow_motion()
                self.vencedor = atacante.dados.nome
                return True
            else:
                # === HIT NORMAL - EFEITOS PROPORCIONAIS AO DANO E FORÇA ===
                # Knockback visual proporcional ao dano
                if dano > 8 or forca_atacante > 12:
                    self._criar_knockback_visual(defensor, direcao_impacto, dano)
                
                # Partículas proporcionais
                qtd_part = max(5, min(25, int(dano / 3)))
                self.spawn_particulas(dx, dy, vx/mag, vy/mag, VERMELHO_SANGUE, qtd_part)
                
                # Se Game Feel está gerenciando shake/hitstop, não duplicamos
                if not self.game_feel:
                    shake_intensity = min(20.0, 5.0 + dano * 0.3)
                    self.cam.aplicar_shake(shake_intensity, 0.12)
                    self.hit_stop_timer = min(0.1, 0.02 + dano * 0.002)
                    if dano > 15:
                        self.cam.zoom_punch(0.08, 0.1)
                
                # Shockwave para ataques fortes
                tier = get_impact_tier(forca_atacante)
                if dano > 10 or forca_atacante >= 14:
                    self.shockwaves.append(Shockwave(dx, dy, BRANCO, 0.6 * tier['shockwave_size']))
                
                # === TEXTO DE DANO ESTILIZADO ===
                if is_critico:
                    cor_txt = (255, 50, 50)  # Vermelho intenso - crítico
                    tamanho_txt = 32
                    self.textos.append(FloatingText(dx, dy - 50, "CRÍTICO!", (255, 200, 0), 24))
                elif dano > 25:
                    cor_txt = (255, 100, 100)  # Vermelho claro - dano alto
                    tamanho_txt = 28
                elif dano > 15:
                    cor_txt = (255, 200, 100)  # Laranja - dano médio
                    tamanho_txt = 24
                else:
                    cor_txt = BRANCO
                    tamanho_txt = 20
                
                self.textos.append(FloatingText(dx, dy - 30, int(dano), cor_txt, tamanho_txt))
        return False

    def spawn_particulas(self, x, y, dir_x, dir_y, cor, qtd):
        for _ in range(qtd):
            vx = dir_x * random.uniform(2, 12) + random.uniform(-4, 4)
            vy = dir_y * random.uniform(2, 12) + random.uniform(-4, 4)
            self.particulas.append(Particula(x*PPM, y*PPM, cor, vx, vy, random.randint(3, 8)))

    def ativar_slow_motion(self):
        self.time_scale = 0.2; self.slow_mo_timer = 2.0

    def desenhar(self):
        self.tela.fill(COR_FUNDO)
        
        # === DESENHA ARENA v9.0 (ANTES DE TUDO) ===
        if self.arena:
            self.arena.desenhar(self.tela, self.cam)
        else:
            # Fallback: grid antigo se não houver arena
            self.desenhar_grid()
        
        for d in self.decals: d.draw(self.tela, self.cam)
        
        # === DESENHA ÁREAS ===
        if hasattr(self, 'areas'):
            for area in self.areas:
                if area.ativo:
                    ax, ay = self.cam.converter(area.x * PPM, area.y * PPM)
                    ar = self.cam.converter_tam(area.raio_atual * PPM)
                    if ar > 0:
                        s = pygame.Surface((ar*2, ar*2), pygame.SRCALPHA)
                        cor_com_alpha = (*area.cor, min(255, area.alpha // 2))
                        pygame.draw.circle(s, cor_com_alpha, (ar, ar), ar)
                        self.tela.blit(s, (ax - ar, ay - ar))
                        # Borda
                        pygame.draw.circle(self.tela, area.cor, (ax, ay), ar, 2)
        
        # === DESENHA BEAMS ===
        if hasattr(self, 'beams'):
            for beam in self.beams:
                if beam.ativo:
                    # Desenha segmentos zigzag
                    pts_screen = []
                    for bx, by in beam.segments:
                        sx, sy = self.cam.converter(bx * PPM, by * PPM)
                        pts_screen.append((sx, sy))
                    if len(pts_screen) >= 2:
                        # Glow externo
                        pygame.draw.lines(self.tela, (255, 255, 255), False, pts_screen, beam.largura + 4)
                        # Beam principal
                        pygame.draw.lines(self.tela, beam.cor, False, pts_screen, beam.largura)
                        # Core brilhante
                        pygame.draw.lines(self.tela, BRANCO, False, pts_screen, max(1, beam.largura // 2))
        
        for p in self.particulas:
            sx, sy = self.cam.converter(p.x, p.y); tam = self.cam.converter_tam(p.tamanho)
            pygame.draw.rect(self.tela, p.cor, (sx, sy, tam, tam))
        
        # === DESENHA MARCAS NO CHÃO (CRATERAS, RACHADURAS) - v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_ground(self.tela, self.cam)
        
        lutadores = [self.p1, self.p2]
        lutadores.sort(key=lambda p: 0 if p.morto else 1)
        for l in lutadores: self.desenhar_lutador(l)
        
        # === DESENHA PROJÉTEIS COM TRAIL ===
        for proj in self.projeteis:
            # Trail
            if hasattr(proj, 'trail') and len(proj.trail) > 1:
                for i in range(1, len(proj.trail)):
                    alpha = int(255 * (i / len(proj.trail)) * 0.5)
                    p1 = self.cam.converter(proj.trail[i-1][0] * PPM, proj.trail[i-1][1] * PPM)
                    p2 = self.cam.converter(proj.trail[i][0] * PPM, proj.trail[i][1] * PPM)
                    # Trail colorido
                    cor_trail = proj.cor if hasattr(proj, 'cor') else BRANCO
                    pygame.draw.line(self.tela, cor_trail, p1, p2, max(1, int(proj.raio * PPM * self.cam.zoom * 0.5)))
            
            # Projétil principal - desenho baseado no tipo
            px, py = self.cam.converter(proj.x * PPM, proj.y * PPM)
            pr = self.cam.converter_tam(proj.raio * PPM)
            cor = proj.cor if hasattr(proj, 'cor') else BRANCO
            
            tipo_proj = getattr(proj, 'tipo', 'skill')
            ang_visual = getattr(proj, 'angulo_visual', proj.angulo) if hasattr(proj, 'angulo') else 0
            rad = math.radians(ang_visual)
            
            if tipo_proj == "faca":
                # Desenha faca (triângulo alongado)
                tam = max(pr * 2, 8)
                pts = [
                    (px + math.cos(rad) * tam, py + math.sin(rad) * tam),  # Ponta
                    (px + math.cos(rad + 2.5) * tam * 0.4, py + math.sin(rad + 2.5) * tam * 0.4),
                    (px - math.cos(rad) * tam * 0.3, py - math.sin(rad) * tam * 0.3),  # Base
                    (px + math.cos(rad - 2.5) * tam * 0.4, py + math.sin(rad - 2.5) * tam * 0.4),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, BRANCO, pts, 1)
                
            elif tipo_proj == "shuriken":
                # Desenha shuriken (estrela de 4 pontas girando)
                tam = max(pr * 2, 10)
                pts = []
                for i in range(8):
                    ang_pt = rad + i * (math.pi / 4)
                    dist = tam if i % 2 == 0 else tam * 0.3
                    pts.append((px + math.cos(ang_pt) * dist, py + math.sin(ang_pt) * dist))
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, (50, 50, 50), pts, 1)
                
            elif tipo_proj == "chakram":
                # Desenha chakram (anel girando)
                tam = max(pr * 2, 12)
                pygame.draw.circle(self.tela, cor, (int(px), int(py)), int(tam), 3)
                pygame.draw.circle(self.tela, BRANCO, (int(px), int(py)), int(tam * 0.5), 2)
                # Lâminas
                for i in range(6):
                    ang_blade = rad + i * (math.pi / 3)
                    bx = px + math.cos(ang_blade) * tam
                    by = py + math.sin(ang_blade) * tam
                    pygame.draw.line(self.tela, cor, (px, py), (int(bx), int(by)), 2)
                
            elif tipo_proj == "flecha":
                # Desenha flecha
                tam = max(pr * 3, 15)
                # Corpo da flecha
                x1 = px - math.cos(rad) * tam * 0.7
                y1 = py - math.sin(rad) * tam * 0.7
                x2 = px + math.cos(rad) * tam * 0.3
                y2 = py + math.sin(rad) * tam * 0.3
                pygame.draw.line(self.tela, (139, 90, 43), (int(x1), int(y1)), (int(x2), int(y2)), 2)
                # Ponta da flecha (triângulo)
                pts = [
                    (px + math.cos(rad) * tam * 0.6, py + math.sin(rad) * tam * 0.6),
                    (px + math.cos(rad + 2.7) * tam * 0.2, py + math.sin(rad + 2.7) * tam * 0.2),
                    (px + math.cos(rad - 2.7) * tam * 0.2, py + math.sin(rad - 2.7) * tam * 0.2),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                # Penas (traseira)
                for offset in [-0.3, 0.3]:
                    fx = x1 + math.cos(rad + offset) * tam * 0.15
                    fy = y1 + math.sin(rad + offset) * tam * 0.15
                    pygame.draw.line(self.tela, (200, 200, 200), (int(x1), int(y1)), (int(fx), int(fy)), 1)
                
            else:
                # Projétil de skill (círculo padrão)
                pygame.draw.circle(self.tela, cor, (int(px), int(py)), int(pr))
                pygame.draw.circle(self.tela, BRANCO, (int(px), int(py)), max(1, int(pr)-2))

        # === DESENHA ORBES MÁGICOS ===
        for p in [self.p1, self.p2]:
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if not orbe.ativo:
                        continue
                    
                    ox, oy = self.cam.converter(orbe.x * PPM, orbe.y * PPM)
                    or_visual = self.cam.converter_tam(orbe.raio_visual * PPM)
                    
                    # Trail quando disparando
                    if orbe.estado == "disparando" and len(orbe.trail) > 1:
                        for i in range(1, len(orbe.trail)):
                            alpha = int(255 * (i / len(orbe.trail)) * 0.6)
                            p1 = self.cam.converter(orbe.trail[i-1][0] * PPM, orbe.trail[i-1][1] * PPM)
                            p2 = self.cam.converter(orbe.trail[i][0] * PPM, orbe.trail[i][1] * PPM)
                            cor_trail = tuple(min(255, c + 50) for c in orbe.cor)
                            pygame.draw.line(self.tela, cor_trail, p1, p2, max(2, int(or_visual * 0.5)))
                    
                    # Partículas mágicas
                    for part in orbe.particulas:
                        ppx, ppy = self.cam.converter(part['x'] * PPM, part['y'] * PPM)
                        palpha = int(255 * (part['vida'] / 0.3))
                        s = pygame.Surface((6, 6), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*part['cor'], palpha), (3, 3), 3)
                        self.tela.blit(s, (ppx - 3, ppy - 3))
                    
                    # Glow externo
                    glow_size = int(or_visual * 2.5)
                    if glow_size > 2:
                        s = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                        # Pulso de brilho
                        pulso = 0.7 + 0.3 * math.sin(orbe.pulso)
                        glow_alpha = int(100 * pulso)
                        cor_glow = (*orbe.cor[:3], glow_alpha)
                        pygame.draw.circle(s, cor_glow, (glow_size, glow_size), glow_size)
                        self.tela.blit(s, (ox - glow_size, oy - glow_size))
                    
                    # Orbe principal (núcleo brilhante)
                    if or_visual > 1:
                        # Borda colorida
                        pygame.draw.circle(self.tela, orbe.cor, (int(ox), int(oy)), int(or_visual))
                        # Core branco
                        pygame.draw.circle(self.tela, BRANCO, (int(ox), int(oy)), max(1, int(or_visual * 0.5)))
                    
                    # Estado visual extra
                    if orbe.estado == "carregando":
                        # Anéis de carga
                        carga_pct = orbe.tempo_carga / orbe.carga_max
                        ring_r = int(or_visual * (1.5 + carga_pct))
                        pygame.draw.circle(self.tela, orbe.cor, (int(ox), int(oy)), ring_r, 1)

        # === EFEITOS v7.0 IMPACT EDITION ===
        for ef in self.dash_trails: ef.draw(self.tela, self.cam)
        for ef in self.hit_sparks: ef.draw(self.tela, self.cam)
        for ef in self.magic_clashes: ef.draw(self.tela, self.cam)
        for ef in self.impact_flashes: ef.draw(self.tela, self.cam)
        for ef in self.block_effects: ef.draw(self.tela, self.cam)

        # === ANIMAÇÕES DE MOVIMENTO v8.0 CINEMATIC EDITION ===
        if self.movement_anims:
            self.movement_anims.draw(self.tela, self.cam)

        # === ANIMAÇÕES DE ATAQUE v8.0 IMPACT EDITION ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_effects(self.tela, self.cam)

        for s in self.shockwaves: s.draw(self.tela, self.cam)
        for t in self.textos: t.draw(self.tela, self.cam)

        # === SCREEN EFFECTS (FLASH) v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_screen_effects(self.tela, LARGURA, ALTURA)

        # === DEBUG VISUAL DE HITBOX ===
        if self.show_hitbox_debug:
            self.desenhar_hitbox_debug()

        if self.show_hud:
            if not self.vencedor:
                self.desenhar_barras(self.p1, 20, 20, COR_P1, self.vida_visual_p1)
                self.desenhar_barras(self.p2, LARGURA - 320, 20, COR_P2, self.vida_visual_p2)
                self.desenhar_controles() 
            else: self.desenhar_vitoria()
            if self.paused: self.desenhar_pause()
        if self.show_analysis: self.desenhar_analise()

    def desenhar_grid(self):
        start_x = int((-self.cam.x * self.cam.zoom) % (50 * self.cam.zoom))
        start_y = int((-self.cam.y * self.cam.zoom) % (50 * self.cam.zoom))
        step = int(50 * self.cam.zoom)
        for x in range(start_x, LARGURA, step): pygame.draw.line(self.tela, COR_GRID, (x, 0), (x, ALTURA))
        for y in range(start_y, ALTURA, step): pygame.draw.line(self.tela, COR_GRID, (0, y), (LARGURA, y))

    def desenhar_lutador(self, l):
        px = l.pos[0] * PPM; py = l.pos[1] * PPM
        sx, sy = self.cam.converter(px, py); off_y = self.cam.converter_tam(l.z * PPM); raio = self.cam.converter_tam((l.dados.tamanho / 2) * PPM)
        if l in self.rastros and len(self.rastros[l]) > 2:
            pts_rastro = []
            for ponta, cabo in self.rastros[l]:
                p_conv = self.cam.converter(ponta[0], ponta[1]); c_conv = self.cam.converter(cabo[0], cabo[1])
                p_conv = (p_conv[0], p_conv[1] - off_y); c_conv = (c_conv[0], c_conv[1] - off_y)
                pts_rastro.append(p_conv); pts_rastro.insert(0, c_conv)
            s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            cor_rastro = (l.dados.arma_obj.r, l.dados.arma_obj.g, l.dados.arma_obj.b, 80)
            if len(pts_rastro) > 2: pygame.draw.polygon(s, cor_rastro, pts_rastro); self.tela.blit(s, (0,0))
        if l.morto:
            pygame.draw.ellipse(self.tela, COR_CORPO, (sx-raio, sy-raio, raio*2, raio*2))
            if l.dados.arma_obj:
                ax = l.arma_droppada_pos[0]*PPM; ay = l.arma_droppada_pos[1]*PPM
                asx, asy = self.cam.converter(ax, ay)
                self.desenhar_arma(l.dados.arma_obj, (asx, asy), l.arma_droppada_ang, l.dados.tamanho, raio)
            return
        sombra = pygame.Surface((raio*2, raio*2), pygame.SRCALPHA); pygame.draw.ellipse(sombra, (0,0,0,80), (0,0,raio*2, raio*2))
        tam_s = int(raio * 2 * max(0.4, 1.0 - (l.z/4.0)))
        if tam_s > 0:
            sombra_scaled = pygame.transform.scale(sombra, (tam_s, tam_s)); self.tela.blit(sombra_scaled, (sx-tam_s//2, sy-tam_s//2))
        centro = (sx, sy - off_y)
        
        # === COR DO CORPO COM FLASH DE DANO MELHORADO ===
        if l.flash_timer > 0:
            # Usa cor de flash personalizada se disponível
            flash_cor = getattr(l, 'flash_cor', (255, 255, 255))
            # Intensidade do flash diminui com o tempo
            flash_intensity = l.flash_timer / 0.25
            # Mistura cor original com cor de flash
            cor_original = (l.dados.cor_r, l.dados.cor_g, l.dados.cor_b)
            cor = tuple(int(flash_cor[i] * flash_intensity + cor_original[i] * (1 - flash_intensity)) for i in range(3))
        else:
            cor = (l.dados.cor_r, l.dados.cor_g, l.dados.cor_b)
        
        pygame.draw.circle(self.tela, cor, centro, raio)
        
        # === CONTORNO APRIMORADO ===
        if l.stun_timer > 0:
            contorno = AMARELO_FAISCA
            largura = max(2, self.cam.converter_tam(5))
        elif l.atacando:
            contorno = (255, 255, 255)
            largura = max(2, self.cam.converter_tam(4))
        elif l.flash_timer > 0:
            # Contorno vermelho durante dano
            contorno = (255, 100, 100)
            largura = max(2, self.cam.converter_tam(4))
        else:
            contorno = (50, 50, 50)
            largura = max(1, self.cam.converter_tam(2))
        
        pygame.draw.circle(self.tela, contorno, centro, raio, largura)
        
        # === EFEITO DE GLOW EM VIDA BAIXA (ADRENALINA) ===
        if l.modo_adrenalina and not l.morto:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150)
            glow_size = int(raio * 1.3)
            s = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            glow_alpha = int(60 * pulso)
            pygame.draw.circle(s, (255, 50, 50, glow_alpha), (glow_size, glow_size), glow_size)
            self.tela.blit(s, (centro[0] - glow_size, centro[1] - glow_size))
        
        # === RENDERIZA ARMA COM ANIMAÇÕES APRIMORADAS ===
        if l.dados.arma_obj:
            # Aplica shake da animação
            shake = getattr(l, 'weapon_anim_shake', (0, 0))
            centro_ajustado = (centro[0] + shake[0], centro[1] + shake[1])
            
            # Escala da animação
            anim_scale = getattr(l, 'weapon_anim_scale', 1.0)
            
            # Desenha slash arc se estiver atacando (para armas melee)
            if l.atacando and l.dados.arma_obj.tipo in ["Reta", "Dupla", "Corrente", "Transformável"]:
                self._desenhar_slash_arc(l, centro, raio, anim_scale)
            
            # Desenha trail antes da arma
            self._desenhar_weapon_trail(l)
            
            # Desenha arma com escala
            self.desenhar_arma(l.dados.arma_obj, centro_ajustado, l.angulo_arma_visual, 
                             l.dados.tamanho, raio, anim_scale)
    
    def _desenhar_slash_arc(self, lutador, centro, raio, anim_scale):
        """Desenha arco de corte visível durante ataques melee"""
        arma = lutador.dados.arma_obj
        if not arma:
            return
        
        # Cor do arco baseada na arma
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (255, 255, 255)
        cor_brilho = tuple(min(255, c + 80) for c in cor)
        
        # Progresso da animação
        timer = lutador.timer_animacao
        
        # Perfil da arma para saber a duração total
        from effects.weapon_animations import WEAPON_PROFILES
        profile = WEAPON_PROFILES.get(arma.tipo, WEAPON_PROFILES["Reta"])
        total_time = profile.total_time
        
        # Progresso normalizado (0-1)
        prog = 1.0 - (timer / total_time) if total_time > 0 else 0
        
        # Só desenha durante a fase de ataque principal (não na anticipation ou recovery)
        antecipation_end = profile.anticipation_time / total_time
        attack_end = (profile.anticipation_time + profile.attack_time + profile.impact_time) / total_time
        
        if prog < antecipation_end or prog > attack_end + 0.2:
            return
        
        # Calcula fase dentro do ataque
        attack_prog = (prog - antecipation_end) / max(attack_end - antecipation_end, 0.01)
        attack_prog = max(0, min(1, attack_prog))
        
        # Parâmetros do arco
        angulo_base = lutador.angulo_olhar
        arc_start = angulo_base + profile.anticipation_angle
        arc_end = angulo_base + profile.attack_angle
        
        # Ângulo atual do arco (expande ao longo do ataque)
        current_arc = arc_start + (arc_end - arc_start) * attack_prog
        
        # Raio do arco
        arc_radius = raio * 2.5 * anim_scale
        
        # Alpha diminui conforme avança
        alpha = int(180 * (1 - attack_prog * 0.7))
        
        # Largura do arco
        arc_width = max(3, int(8 * (1 - attack_prog * 0.5)))
        
        # Desenha o arco de corte
        s = pygame.Surface((int(arc_radius * 3), int(arc_radius * 3)), pygame.SRCALPHA)
        arc_center = (int(arc_radius * 1.5), int(arc_radius * 1.5))
        
        # Calcula pontos do arco
        num_points = 15
        points_outer = []
        points_inner = []
        
        for i in range(num_points + 1):
            t = i / num_points
            angle = math.radians(arc_start + (current_arc - arc_start) * t)
            
            # Ponto externo
            ox = arc_center[0] + math.cos(angle) * arc_radius
            oy = arc_center[1] + math.sin(angle) * arc_radius
            points_outer.append((ox, oy))
            
            # Ponto interno (para criar espessura)
            inner_radius = arc_radius * 0.7
            ix = arc_center[0] + math.cos(angle) * inner_radius
            iy = arc_center[1] + math.sin(angle) * inner_radius
            points_inner.append((ix, iy))
        
        # Cria polígono do arco
        if len(points_outer) > 2:
            arc_polygon = points_outer + points_inner[::-1]
            
            # Cor com alpha
            arc_color = (*cor_brilho, alpha)
            pygame.draw.polygon(s, arc_color, arc_polygon)
            
            # Contorno mais brilhante
            pygame.draw.lines(s, (*cor, min(255, alpha + 50)), False, points_outer, 2)
        
        # Blit na posição do lutador
        blit_pos = (centro[0] - arc_center[0], centro[1] - arc_center[1])
        self.tela.blit(s, blit_pos)
    
    def _desenhar_weapon_trail(self, lutador):
        """Desenha o trail da arma durante ataques"""
        trail = getattr(lutador, 'weapon_trail_positions', [])
        if len(trail) < 2:
            return
        
        arma = lutador.dados.arma_obj
        if not arma:
            return
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (200, 200, 200)
        tipo = arma.tipo
        
        # Diferentes estilos de trail por tipo
        for i in range(len(trail) - 1):
            x1, y1, a1 = trail[i]
            x2, y2, a2 = trail[i + 1]
            
            # Converte para tela (coordenadas mundo -> pixels)
            from config import PPM
            p1 = self.cam.converter(x1 * PPM, y1 * PPM)
            p2 = self.cam.converter(x2 * PPM, y2 * PPM)
            
            alpha = min(a1, a2)
            if alpha < 0.1:
                continue
            
            # Largura e cor com fade
            width = max(1, int(5 * (i / len(trail)) * alpha))
            
            if tipo == "Mágica":
                # Trail brilhante para magia
                bright = tuple(min(255, int(c + 80 * alpha)) for c in cor)
                pygame.draw.line(self.tela, bright, p1, p2, width + 2)
                
                # Partícula no final
                if i == len(trail) - 2 and alpha > 0.5:
                    glow_size = int(8 * alpha)
                    s = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                    glow_alpha = int(100 * alpha)
                    pygame.draw.circle(s, (*cor, glow_alpha), (glow_size, glow_size), glow_size)
                    self.tela.blit(s, (p2[0] - glow_size, p2[1] - glow_size))
            else:
                # Trail padrão de corte
                blend = alpha * 0.8
                trail_color = tuple(min(255, int(c * 0.5 + 127 * blend)) for c in cor)
                pygame.draw.line(self.tela, trail_color, p1, p2, width)

    def desenhar_arma(self, arma, centro, angulo, tam_char, raio_char, anim_scale=1.0):
        """
        Renderiza a arma do lutador baseado no tipo.
        
        NOVA LÓGICA COM ANIMAÇÃO v2.0:
        - raio_char já está em pixels de tela (já considera zoom)
        - anim_scale aplica squash/stretch durante ataques
        - Comprimento padrão: 1.5x a 3x o raio do personagem dependendo do tipo
        """
        cx, cy = centro
        rad = math.radians(angulo)
        cor = (arma.r, arma.g, arma.b)
        cor_raridade = getattr(arma, 'cor_raridade', (200, 200, 200))
        tipo = arma.tipo
        
        # Tamanho base da arma em unidades JSON
        if tipo in ["Reta", "Dupla", "Transformável"]:
            tam_base = arma.comp_cabo + arma.comp_lamina
        elif tipo == "Corrente":
            tam_base = getattr(arma, 'comp_corrente', 80)
        elif tipo == "Arremesso":
            tam_base = getattr(arma, 'tamanho_projetil', 15)
        elif tipo == "Arco":
            tam_base = getattr(arma, 'tamanho_arco', 50)
        elif tipo == "Orbital":
            tam_base = arma.distancia
        elif tipo == "Mágica":
            tam_base = getattr(arma, 'tamanho', 15)
        else:
            tam_base = 50
        
        # Fator de escala: quanto do raio do personagem a arma deve ocupar
        # Ex: fator 2.0 = arma tem comprimento de 2x o raio (= 1x o diâmetro)
        fatores = {
            "Reta": 2.5,        # Espada = 2.5x raio
            "Dupla": 2.0,       # Adagas = 2x raio cada
            "Corrente": 4.0,    # Corrente longa
            "Arremesso": 0.8,   # Projéteis menores
            "Arco": 2.0,        # Arco médio
            "Orbital": 1.5,     # Orbitais próximos
            "Mágica": 1.5,      # Espadas mágicas
            "Transformável": 2.5
        }
        fator = fatores.get(tipo, 2.0)
        
        # Comprimento alvo em pixels = raio * fator * escala de animação
        comp_alvo = raio_char * fator * anim_scale
        
        # Escala: quanto cada unidade da arma vale em pixels
        escala = comp_alvo / max(tam_base, 1)
        
        # Largura proporcional ao raio (também escala)
        larg = max(3, int(raio_char * 0.15 * anim_scale))
        
        # === RETA (Espadas, Lanças) com efeito de swing ===
        if tipo == "Reta":
            cabo = arma.comp_cabo * escala
            lamina = arma.comp_lamina * escala
            
            # Ponto do cabo
            ex, ey = cx + math.cos(rad)*cabo, cy + math.sin(rad)*cabo
            # Ponta da lâmina
            fx, fy = cx + math.cos(rad)*(cabo+lamina), cy + math.sin(rad)*(cabo+lamina)
            
            # Cabo (marrom)
            pygame.draw.line(self.tela, (100,50,0), (cx, cy), (int(ex), int(ey)), larg)
            
            # Lâmina com gradiente de brilho quando atacando
            if anim_scale > 1.05:
                # Brilho durante ataque
                cor_brilho = tuple(min(255, c + 60) for c in cor)
                pygame.draw.line(self.tela, cor_brilho, (int(ex), int(ey)), (int(fx), int(fy)), larg + 2)
            pygame.draw.line(self.tela, cor, (int(ex), int(ey)), (int(fx), int(fy)), larg)
            
            # Ponta com glow de raridade
            if cor_raridade != (180, 180, 180):
                pygame.draw.circle(self.tela, cor_raridade, (int(fx), int(fy)), max(3, larg//2))
        
        # === DUPLA (Adagas duplas) - ataques alternados ===
        elif tipo == "Dupla":
            cabo = arma.comp_cabo * escala
            lamina = arma.comp_lamina * escala
            
            for i, offset_ang in enumerate([-25, 25]):
                r = rad + math.radians(offset_ang)
                ex, ey = cx + math.cos(r)*cabo, cy + math.sin(r)*cabo
                fx, fy = cx + math.cos(r)*(cabo+lamina), cy + math.sin(r)*(cabo+lamina)
                pygame.draw.line(self.tela, (100,50,0), (cx, cy), (int(ex), int(ey)), max(2, larg//2))
                pygame.draw.line(self.tela, cor, (int(ex), int(ey)), (int(fx), int(fy)), larg)
                if cor_raridade != (180, 180, 180):
                    pygame.draw.circle(self.tela, cor_raridade, (int(fx), int(fy)), max(3, larg//2))
        
        # === CORRENTE (Kusarigama, Chicote) ===
        elif tipo == "Corrente":
            comp = getattr(arma, 'comp_corrente', 80) * escala
            larg_ponta = max(4, int(raio_char * 0.2))
            
            pts = []
            segs = 10
            for i in range(segs + 1):
                t = i / segs
                wave = math.sin(t * math.pi * 3 + pygame.time.get_ticks() / 200) * (raio_char * 0.15)
                px = cx + math.cos(rad) * (comp * t)
                py = cy + math.sin(rad) * (comp * t) + math.cos(rad + math.pi/2) * wave
                pts.append((int(px), int(py)))
            
            if len(pts) > 1:
                pygame.draw.lines(self.tela, (100, 100, 100), False, pts, max(2, larg//2))
            
            fx, fy = pts[-1]
            pygame.draw.circle(self.tela, cor, (fx, fy), larg_ponta)
            if cor_raridade != (180, 180, 180):
                pygame.draw.circle(self.tela, cor_raridade, (fx, fy), larg_ponta, 2)
        
        # === ARREMESSO (Facas, Chakrams) ===
        elif tipo == "Arremesso":
            tam = max(int(raio_char * 0.4), 8)
            qtd = int(getattr(arma, 'quantidade', 3))
            
            for i in range(qtd):
                offset_ang = (i - (qtd-1)/2) * 20
                r = rad + math.radians(offset_ang)
                dist = raio_char + tam * 1.2
                px = cx + math.cos(r) * dist
                py = cy + math.sin(r) * dist
                
                pts = [
                    (int(px + math.cos(r) * tam), int(py + math.sin(r) * tam)),
                    (int(px + math.cos(r + math.pi/2) * tam*0.4), int(py + math.sin(r + math.pi/2) * tam*0.4)),
                    (int(px - math.cos(r) * tam*0.3), int(py - math.sin(r) * tam*0.3)),
                    (int(px + math.cos(r - math.pi/2) * tam*0.4), int(py + math.sin(r - math.pi/2) * tam*0.4)),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, cor_raridade, pts, 1)
        
        # === ARCO ===
        elif tipo == "Arco":
            tam_arco = raio_char * 1.2
            tam_flecha = raio_char * 1.5
            
            pts = []
            for i in range(9):
                a = rad + math.radians(-40 + i * 10)
                px = cx + math.cos(a) * tam_arco * 0.6
                py = cy + math.sin(a) * tam_arco * 0.6
                pts.append((int(px), int(py)))
            
            if len(pts) > 1:
                pygame.draw.lines(self.tela, cor, False, pts, max(3, larg))
                pygame.draw.line(self.tela, (139, 90, 43), pts[0], pts[-1], 2)
            
            fx = cx + math.cos(rad) * (raio_char + tam_flecha)
            fy = cy + math.sin(rad) * (raio_char + tam_flecha)
            pygame.draw.line(self.tela, (139, 90, 43), (int(cx), int(cy)), (int(fx), int(fy)), max(2, larg//2))
            pygame.draw.circle(self.tela, cor_raridade, (int(fx), int(fy)), max(4, larg//2))
        
        # === ORBITAL (Escudos, Drones) ===
        elif tipo == "Orbital":
            dist = raio_char * 1.5
            qtd = int(getattr(arma, 'quantidade_orbitais', 1))
            rot_offset = pygame.time.get_ticks() / 1000 * 2
            
            for i in range(qtd):
                a = rad + (2 * math.pi / qtd) * i + rot_offset
                ox = cx + math.cos(a) * dist
                oy = cy + math.sin(a) * dist
                
                if arma.largura < 20:
                    raio_orbe = max(5, int(raio_char * 0.25))
                    pygame.draw.circle(self.tela, cor, (int(ox), int(oy)), raio_orbe)
                    pygame.draw.circle(self.tela, cor_raridade, (int(ox), int(oy)), raio_orbe, 2)
                    pygame.draw.line(self.tela, (80,80,80), (int(cx), int(cy)), (int(ox), int(oy)), 1)
                else:
                    pts = []
                    ang_range = min(60, arma.largura)
                    for j in range(11):
                        aa = a + math.radians(-ang_range/2 + (j * ang_range/10))
                        pts.append((int(cx + math.cos(aa)*dist), int(cy + math.sin(aa)*dist)))
                    pygame.draw.lines(self.tela, cor, False, pts, max(4, larg))
                    pygame.draw.lines(self.tela, cor_raridade, False, pts, 1)
        
        # === MÁGICA (Espadas espectrais) ===
        elif tipo == "Mágica":
            qtd = int(getattr(arma, 'quantidade', 3))
            tam = max(int(raio_char * 0.6), 10)
            dist_max = raio_char * 1.3
            float_offset = math.sin(pygame.time.get_ticks() / 300) * (raio_char * 0.1)
            
            for i in range(qtd):
                offset_ang = (i - (qtd-1)/2) * 25
                r = rad + math.radians(offset_ang)
                dist = raio_char + dist_max + float_offset
                
                px = cx + math.cos(r) * dist
                py = cy + math.sin(r) * dist
                
                pts = [
                    (int(px + math.cos(r) * tam), int(py + math.sin(r) * tam)),
                    (int(px + math.cos(r + math.pi/2) * tam*0.25), int(py + math.sin(r + math.pi/2) * tam*0.25)),
                    (int(px - math.cos(r) * tam*0.4), int(py - math.sin(r) * tam*0.4)),
                    (int(px + math.cos(r - math.pi/2) * tam*0.25), int(py + math.sin(r - math.pi/2) * tam*0.25)),
                ]
                
                cor_magica = tuple(min(255, c + 50) for c in cor)
                pygame.draw.polygon(self.tela, cor_magica, pts)
                pygame.draw.polygon(self.tela, cor_raridade, pts, 1)
        
        # === TRANSFORMÁVEL ===
        elif tipo == "Transformável":
            forma = getattr(arma, 'forma_atual', 1)
            if forma == 1:
                cabo_v = getattr(arma, 'forma1_cabo', arma.comp_cabo)
                lamina_v = getattr(arma, 'forma1_lamina', arma.comp_lamina)
            else:
                cabo_v = getattr(arma, 'forma2_cabo', arma.comp_cabo)
                lamina_v = getattr(arma, 'forma2_lamina', arma.comp_lamina)
            
            cabo = cabo_v * escala
            lamina = lamina_v * escala
            ex, ey = cx + math.cos(rad)*cabo, cy + math.sin(rad)*cabo
            fx, fy = cx + math.cos(rad)*(cabo+lamina), cy + math.sin(rad)*(cabo+lamina)
            
            pygame.draw.line(self.tela, (100,50,0), (int(cx), int(cy)), (int(ex), int(ey)), larg)
            pygame.draw.line(self.tela, cor, (int(ex), int(ey)), (int(fx), int(fy)), larg)
            pygame.draw.circle(self.tela, cor_raridade, (int(fx), int(fy)), max(4, larg//2))
        
        # === FALLBACK ===
        else:
            cabo = arma.comp_cabo * escala
            lamina = arma.comp_lamina * escala
            ex, ey = cx + math.cos(rad)*cabo, cy + math.sin(rad)*cabo
            fx, fy = cx + math.cos(rad)*(cabo+lamina), cy + math.sin(rad)*(cabo+lamina)
            pygame.draw.line(self.tela, (100,50,0), (int(cx), int(cy)), (int(ex), int(ey)), larg)
            pygame.draw.line(self.tela, cor, (int(ex), int(ey)), (int(fx), int(fy)), larg)

    def desenhar_hitbox_debug(self):
        """Desenha visualização de debug das hitboxes"""
        debug_info = get_debug_visual()
        fonte = pygame.font.SysFont("Arial", 10)
        
        # Desenha hitboxes em tempo real para cada lutador
        for p in [self.p1, self.p2]:
            if p.morto:
                continue
            
            cor_debug = (0, 255, 0, 128) if p == self.p1 else (255, 255, 0, 128)
            
            # Calcula hitbox atual
            hitbox = sistema_hitbox.calcular_hitbox_arma(p)
            if not hitbox:
                continue
            
            # Posição na tela
            cx_screen, cy_screen = self.cam.converter(hitbox.centro[0], hitbox.centro[1])
            off_y = self.cam.converter_tam(p.z * PPM)
            cy_screen -= off_y
            
            # Surface transparente para desenho
            s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            
            # Desenha raio de alcance
            alcance_screen = self.cam.converter_tam(hitbox.alcance)
            pygame.draw.circle(s, (*cor_debug[:3], 30), (cx_screen, cy_screen), alcance_screen, 2)
            
            # Se tem pontos (arma de lâmina ou corrente)
            if hitbox.pontos:
                # Corrente: desenha como arco
                if hitbox.tipo == "Corrente":
                    # Desenha os segmentos do arco
                    cor_arco = (255, 128, 0, 200) if hitbox.ativo else (100, 100, 100, 100)
                    pontos_screen = []
                    for ponto in hitbox.pontos:
                        ps = self.cam.converter(ponto[0], ponto[1])
                        pontos_screen.append((ps[0], ps[1] - off_y))
                    
                    # Desenha linhas conectando os pontos do arco
                    if len(pontos_screen) > 1:
                        for i in range(len(pontos_screen) - 1):
                            pygame.draw.line(s, cor_arco, pontos_screen[i], pontos_screen[i+1], 3)
                    
                    # Desenha círculo na posição real da bola (centro do arco, no ângulo da arma)
                    rad_bola = math.radians(hitbox.angulo)
                    bola_x = hitbox.centro[0] + math.cos(rad_bola) * hitbox.alcance
                    bola_y = hitbox.centro[1] + math.sin(rad_bola) * hitbox.alcance
                    bola_screen = self.cam.converter(bola_x, bola_y)
                    bola_screen = (bola_screen[0], bola_screen[1] - off_y)
                    pygame.draw.circle(s, (255, 50, 50, 255), bola_screen, 10, 3)  # Círculo vermelho na bola
                    
                    # Linha do centro até a bola
                    pygame.draw.line(s, (255, 128, 0, 100), (cx_screen, cy_screen), bola_screen, 1)
                    
                    # Desenha raio mínimo da corrente (onde ela NÃO acerta)
                    alcance_min = hitbox.alcance * 0.4
                    alcance_min_screen = self.cam.converter_tam(alcance_min)
                    pygame.draw.circle(s, (100, 100, 100, 50), (cx_screen, cy_screen), alcance_min_screen, 1)
                    
                    # Label
                    label = f"{p.dados.nome}: Corrente"
                    if hitbox.ativo:
                        label += f" [GIRANDO t={p.timer_animacao:.2f}]"
                    txt = fonte.render(label, True, BRANCO)
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
                
                # Armas Ranged: desenha linhas de trajetória
                elif hitbox.tipo in ["Arremesso", "Arco"]:
                    cor_traj = (0, 200, 255, 150) if hitbox.ativo else (100, 100, 100, 80)
                    
                    # Múltiplos projéteis ou linha única
                    if len(hitbox.pontos) > 2:
                        # Múltiplos pontos = múltiplos projéteis
                        for ponto in hitbox.pontos:
                            ps = self.cam.converter(ponto[0], ponto[1])
                            ps = (ps[0], ps[1] - off_y)
                            # Linha tracejada do centro até destino
                            pygame.draw.line(s, cor_traj, (cx_screen, cy_screen), ps, 1)
                            pygame.draw.circle(s, cor_traj, ps, 5)
                    else:
                        # Linha única
                        if len(hitbox.pontos) == 2:
                            p1_screen = self.cam.converter(hitbox.pontos[0][0], hitbox.pontos[0][1])
                            p2_screen = self.cam.converter(hitbox.pontos[1][0], hitbox.pontos[1][1])
                            p1_screen = (p1_screen[0], p1_screen[1] - off_y)
                            p2_screen = (p2_screen[0], p2_screen[1] - off_y)
                            pygame.draw.line(s, cor_traj, p1_screen, p2_screen, 2)
                            pygame.draw.circle(s, (255, 100, 100), p2_screen, 6)
                    
                    # Label
                    label = f"{p.dados.nome}: {hitbox.tipo} [RANGED]"
                    if hitbox.ativo:
                        label += " DISPARANDO!"
                    txt = fonte.render(label, True, (0, 200, 255))
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
                    
                else:
                    # Arma de lâmina normal
                    p1_screen = self.cam.converter(hitbox.pontos[0][0], hitbox.pontos[0][1])
                    p2_screen = self.cam.converter(hitbox.pontos[1][0], hitbox.pontos[1][1])
                    p1_screen = (p1_screen[0], p1_screen[1] - off_y)
                    p2_screen = (p2_screen[0], p2_screen[1] - off_y)
                    
                    # Linha da lâmina
                    cor_linha = (255, 0, 0, 200) if hitbox.ativo else (100, 100, 100, 100)
                    pygame.draw.line(s, cor_linha, p1_screen, p2_screen, 4)
                    
                    # Pontos nas extremidades
                    pygame.draw.circle(s, (255, 255, 0), p1_screen, 5)
                    pygame.draw.circle(s, (255, 0, 0), p2_screen, 5)
                    
                    # Label
                    label = f"{p.dados.nome}: {hitbox.tipo}"
                    if hitbox.ativo:
                        label += f" [ATACANDO t={p.timer_animacao:.2f}]"
                    txt = fonte.render(label, True, BRANCO)
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
            
            # Arma de área
            else:
                # Desenha arco de ângulo
                rad = math.radians(hitbox.angulo)
                rad_min = rad - math.radians(hitbox.largura_angular / 2)
                rad_max = rad + math.radians(hitbox.largura_angular / 2)
                
                # Linha central
                fx = cx_screen + math.cos(rad) * alcance_screen
                fy = cy_screen + math.sin(rad) * alcance_screen
                pygame.draw.line(s, (*cor_debug[:3], 150), (cx_screen, cy_screen), (int(fx), int(fy)), 2)
                
                # Limites do arco
                fx_min = cx_screen + math.cos(rad_min) * alcance_screen
                fy_min = cy_screen + math.sin(rad_min) * alcance_screen
                fx_max = cx_screen + math.cos(rad_max) * alcance_screen
                fy_max = cy_screen + math.sin(rad_max) * alcance_screen
                pygame.draw.line(s, (*cor_debug[:3], 100), (cx_screen, cy_screen), (int(fx_min), int(fy_min)), 1)
                pygame.draw.line(s, (*cor_debug[:3], 100), (cx_screen, cy_screen), (int(fx_max), int(fy_max)), 1)
            
            self.tela.blit(s, (0, 0))
        
        # Desenha painel de debug no canto
        self.desenhar_painel_debug()
    
    def desenhar_painel_debug(self):
        """Desenha painel com info de debug"""
        x, y = LARGURA - 300, 80
        w, h = 280, 250
        
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (255, 100, 100), (x, y, w, h), 2)
        
        fonte = pygame.font.SysFont("Arial", 10)
        fonte_bold = pygame.font.SysFont("Arial", 11, bold=True)
        
        self.tela.blit(fonte_bold.render("DEBUG HITBOX [H para toggle]", True, (255, 100, 100)), (x + 10, y + 5))
        
        # Distância entre lutadores
        dist = math.hypot(self.p2.pos[0] - self.p1.pos[0], self.p2.pos[1] - self.p1.pos[1])
        self.tela.blit(fonte_bold.render(f"Distância: {dist:.2f}m", True, (200, 200, 255)), (x + 10, y + 22))
        
        off = 40
        for p in [self.p1, self.p2]:
            cor = (100, 255, 100) if p == self.p1 else (255, 255, 100)
            self.tela.blit(fonte_bold.render(f"=== {p.dados.nome} ===", True, cor), (x + 10, y + off))
            off += 14
            
            arma = p.dados.arma_obj
            if arma:
                self.tela.blit(fonte.render(f"Arma: {arma.nome} ({arma.tipo})", True, BRANCO), (x + 10, y + off))
                off += 11
            
            # Status de ataque
            atk_cor = (0, 255, 0) if p.atacando else (150, 150, 150)
            self.tela.blit(fonte.render(f"Atacando: {p.atacando} Timer: {p.timer_animacao:.3f}", True, atk_cor), (x + 10, y + off))
            off += 11
            self.tela.blit(fonte.render(f"Alcance IA: {p.alcance_ideal:.2f}m CD: {p.cooldown_ataque:.2f}", True, BRANCO), (x + 10, y + off))
            off += 11
            self.tela.blit(fonte.render(f"Ação: {p.brain.acao_atual}", True, BRANCO), (x + 10, y + off))
            off += 16

    def desenhar_barras(self, l, x, y, cor, vida_vis):
        w, h = 300, 30
        pygame.draw.rect(self.tela, (20,20,20), (x, y, w, h))
        pct_vis = max(0, vida_vis / l.vida_max); pygame.draw.rect(self.tela, BRANCO, (x, y, int(w * pct_vis), h))
        pct_real = max(0, l.vida / l.vida_max); pygame.draw.rect(self.tela, cor, (x, y, int(w * pct_real), h))
        pygame.draw.rect(self.tela, BRANCO, (x, y, w, h), 2)
        pct_mana = max(0, l.mana / l.mana_max)
        pygame.draw.rect(self.tela, (20, 20, 20), (x, y + 35, w, 10))
        pygame.draw.rect(self.tela, AZUL_MANA, (x, y + 35, int(w * pct_mana), 10))
        ft = pygame.font.SysFont("Arial", 16, bold=True)
        self.tela.blit(ft.render(f"{l.dados.nome}", True, BRANCO), (x+10, y+5))

    def desenhar_controles(self):
        x, y = 20, 90 
        w, h = 220, 210
        s = pygame.Surface((w, h), pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (100, 100, 100), (x, y, w, h), 1)
        fonte_tit = pygame.font.SysFont("Arial", 14, bold=True); fonte_txt = pygame.font.SysFont("Arial", 12)
        self.tela.blit(fonte_tit.render("COMANDOS", True, COR_TEXTO_TITULO), (x + 10, y + 10))
        comandos = [("WASD / Setas", "Mover Câmera"), ("Scroll", "Zoom"), ("1/2/3", "Modos Cam"), ("SPACE", "Pause"), ("T/F", "Speed"), ("TAB", "Dados"), ("G", "HUD"), ("H", "Debug Hitbox"), ("R", "Reset"), ("ESC", "Sair")]
        off_y = 35
        for t, a in comandos:
            self.tela.blit(fonte_txt.render(t, True, BRANCO), (x + 10, y + off_y))
            self.tela.blit(fonte_txt.render(a, True, COR_TEXTO_INFO), (x + 110, y + off_y))
            off_y += 16

    def desenhar_analise(self):
        s = pygame.Surface((300, ALTURA)); s.fill(COR_UI_BG); self.tela.blit(s, (0,0))
        ft = pygame.font.SysFont("Consolas", 14)
        lines = [
            "--- ANÁLISE ---", f"FPS: {int(self.clock.get_fps())}", f"Cam: {self.cam.modo}", "",
            f"--- {self.p1.dados.nome} ---", f"HP: {int(self.p1.vida)}", f"Mana: {int(self.p1.mana)}", f"Estamina: {int(self.p1.estamina)}",
            f"Action: {self.p1.brain.acao_atual}", f"Skill: {self.p1.skill_arma_nome}", "",
            f"--- {self.p2.dados.nome} ---", f"HP: {int(self.p2.vida)}", f"Mana: {int(self.p2.mana)}", f"Estamina: {int(self.p2.estamina)}",
            f"Action: {self.p2.brain.acao_atual}", f"Skill: {self.p2.skill_arma_nome}"
        ]
        for i, l in enumerate(lines):
            c = COR_TEXTO_TITULO if "---" in l else COR_TEXTO_INFO
            self.tela.blit(ft.render(l, True, c), (20, 20 + i*20))

    def desenhar_pause(self):
        ft = pygame.font.SysFont("Impact", 60); txt = ft.render("PAUSE", True, BRANCO)
        self.tela.blit(txt, (LARGURA//2 - txt.get_width()//2, ALTURA//2 - 50))

    def desenhar_vitoria(self):
        s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (0,0))
        ft = pygame.font.SysFont("Impact", 80); txt = ft.render(f"{self.vencedor} VENCEU!", True, COR_TEXTO_TITULO)
        self.tela.blit(txt, (LARGURA//2 - txt.get_width()//2, ALTURA//2 - 100))
        ft2 = pygame.font.SysFont("Arial", 24); msg = ft2.render("Pressione 'R' para Reiniciar ou 'ESC' para Sair", True, COR_TEXTO_INFO)
        self.tela.blit(msg, (LARGURA//2 - msg.get_width()//2, ALTURA//2 + 20))

    def run(self):
        while self.rodando:
            try:
                raw_dt = self.clock.tick(FPS) / 1000.0
                if self.slow_mo_timer > 0:
                    self.slow_mo_timer -= raw_dt
                    if self.slow_mo_timer <= 0: self.time_scale = 1.0
                dt = raw_dt * self.time_scale
                self.processar_inputs(); self.update(dt); self.desenhar(); pygame.display.flip()
            except Exception as e:
                import traceback
                print(f"ERRO NO LOOP: {e}")
                traceback.print_exc()
                # Mostra diálogo de erro
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()
                    messagebox.showerror("Erro", f"Simulação falhou:\n{e}")
                    root.destroy()
                except:
                    pass
                self.rodando = False
        pygame.quit()

if __name__ == "__main__":
    Simulador().run()