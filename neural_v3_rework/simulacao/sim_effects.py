"""Auto-generated mixin â€” see scripts/split_simulacao.py"""
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


class SimuladorEffects:
    """Mixin de efeitos visuais: partÃ­culas, trails, colisÃµes, slow motion."""


    def _criar_efeito_colisao_parede(self, lutador, intensidade_colisao: float):
        """
        Cria efeitos visuais e sonoros quando lutador colide com parede da arena.
        
        Args:
            lutador: O lutador que colidiu
            intensidade_colisao: Intensidade do impacto (velocidade perpendicular Ã  parede)
                                 Valores tÃ­picos: 2-5 leve, 5-10 mÃ©dio, 10-20+ forte
        
        BUGFIX v2.0:
        - Threshold de som reduzido de 8 â†’ 3 (impactos leves tambÃ©m tocam)
        - Fallback para 'wall_hit' caso wall_impact_light/heavy nÃ£o existam
        - Cooldown reduzido de 0.3s â†’ 0.2s para ser mais responsivo
        - Limiar de efeitos visuais reduzido de 5 â†’ 2 (mais responsivo)
        """
        # Limiar mÃ­nimo para processar a colisÃ£o (muito leve = deslizamento)
        if intensidade_colisao < 2:
            return
        
        # === COOLDOWN DE SOM POR LUTADOR ===
        lutador_id = id(lutador)
        if not hasattr(self, '_wall_sound_cooldown'):
            self._wall_sound_cooldown = {}
        
        sound_on_cooldown = self._wall_sound_cooldown.get(lutador_id, 0) > 0
        
        # === ÃUDIO - BUGFIX: threshold reduzido + fallback de som ===
        # BUG ANTERIOR: threshold de 8 era alto demais, maioria dos impactos eram silenciosos
        # CORREÃ‡ÃƒO: qualquer impacto >= 3 toca som; usa fallback se sons especÃ­ficos nÃ£o carregados
        if self.audio and self.audio.enabled and intensidade_colisao >= 2 and not sound_on_cooldown:
            # Volume: intensidade 3 = 0.3, intensidade 15+ = 1.0
            volume = 0.3 + (intensidade_colisao - 3) * 0.058
            volume = max(0.3, min(1.0, volume))
            
            # Tenta tocar som especÃ­fico, com fallback em cadeia
            som_tocado = False
            if intensidade_colisao > 12:
                # Impacto muito forte
                for nome_som in ["wall_impact_heavy", "wall_impact_light", "wall_hit"]:
                    if nome_som in self.audio.sounds:
                        self.audio.play(nome_som, volume=volume)
                        som_tocado = True
                        break
            elif intensidade_colisao > 5:
                # Impacto mÃ©dio
                for nome_som in ["wall_impact_light", "wall_hit", "wall_impact_heavy"]:
                    if nome_som in self.audio.sounds:
                        self.audio.play(nome_som, volume=volume * 0.8)
                        som_tocado = True
                        break
            else:
                # Impacto leve
                for nome_som in ["wall_hit", "wall_impact_light"]:
                    if nome_som in self.audio.sounds:
                        self.audio.play(nome_som, volume=volume * 0.55)
                        som_tocado = True
                        break
            
            if som_tocado:
                # Cooldown reduzido: 0.2s (era 0.3s)
                self._wall_sound_cooldown[lutador_id] = 0.2
                _log.debug(f"[AUDIO] Wall hit! intensidade={intensidade_colisao:.1f}, volume={volume:.2f}")
            else:
                _log.debug(f"[AUDIO] Wall hit sem som disponÃ­vel (intensidade={intensidade_colisao:.1f})")
        
        # SÃ³ cria efeitos visuais se intensidade suficiente
        if intensidade_colisao < 5:
            return
        
        # Intensidade normalizada para efeitos visuais (0.0 a 1.0)
        intensidade = min(1.0, intensidade_colisao / 15)
        
        # PartÃ­culas de poeira/impacto
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
        
        # Shake da cÃ¢mera proporcional Ã  intensidade (v15.0: reduzido)
        if intensidade > 0.7:
            self.cam.aplicar_shake(intensidade * 4, 0.06)
        
        # Flash de impacto se muito forte
        if intensidade > 0.7:
            self.impact_flashes.append(ImpactFlash(x_px, y_px, cor_parede, intensidade * 0.8, "physical"))


    def _get_cor_efeito(self, efeito):
        """Retorna cor do texto baseado no tipo de efeito - v2.0 COLOSSAL"""
        cores = {
            # Base
            "NORMAL": BRANCO,
            # Fogo
            "FOGO": (255, 100, 0),
            "QUEIMAR": (255, 150, 50),
            "QUEIMANDO": (255, 120, 20),
            # Gelo
            "GELO": (150, 220, 255),
            "CONGELAR": (100, 200, 255),
            "CONGELADO": (180, 230, 255),
            "LENTO": (150, 200, 255),
            # Natureza/Veneno
            "VENENO": (100, 255, 100),
            "ENVENENADO": (80, 220, 80),
            "NATUREZA": (100, 200, 50),
            # Sangue
            "SANGRAMENTO": (180, 0, 30),
            "SANGRANDO": (200, 30, 30),
            "SANGUE": (180, 0, 50),
            # Raio
            "RAIO": (255, 255, 100),
            "PARALISIA": (255, 255, 150),
            # Trevas
            "TREVAS": (150, 0, 200),
            "DRENAR": (80, 0, 120),
            "MALDITO": (100, 0, 150),
            "NECROSE": (50, 50, 50),
            # Luz
            "LUZ": (255, 255, 220),
            "CEGO": (255, 255, 200),
            # Arcano
            "ARCANO": (150, 100, 255),
            "SILENCIADO": (180, 150, 255),
            # Tempo
            "TEMPO": (200, 180, 255),
            "TEMPO_PARADO": (220, 200, 255),
            # GravitaÃ§Ã£o
            "GRAVITACAO": (100, 50, 150),
            "PUXADO": (120, 70, 180),
            "VORTEX": (80, 30, 130),
            # Caos
            "CAOS": (255, 100, 200),
            # CC
            "ATORDOAR": (255, 255, 150),
            "ATORDOADO": (255, 255, 100),
            "ENRAIZADO": (139, 90, 43),
            "MEDO": (150, 0, 150),
            "CHARME": (255, 150, 200),
            "SONO": (100, 100, 200),
            "KNOCK_UP": (200, 200, 255),
            # Debuffs
            "FRACO": (150, 150, 150),
            "VULNERAVEL": (255, 150, 150),
            "EXAUSTO": (100, 100, 100),
            "MARCADO": (255, 200, 50),
            "EXPOSTO": (255, 180, 100),
            "CORROENDO": (150, 100, 50),
            # Buffs
            "ACELERADO": (255, 200, 100),
            "FORTALECIDO": (255, 150, 50),
            "BLINDADO": (200, 200, 200),
            "REGENERANDO": (100, 255, 100),
            "ESCUDO_MAGICO": (150, 150, 255),
            "FURIA": (255, 50, 50),
            "INVISIVEL": (200, 200, 200),
            "INTANGIVEL": (180, 180, 255),
            "DETERMINADO": (255, 200, 100),
            "ABENÃ‡OADO": (255, 255, 200),
            "IMORTAL": (255, 215, 0),
            # Especiais
            "EMPURRAO": (200, 200, 255),
            "EXPLOSAO": (255, 200, 50),
            "BOMBA_RELOGIO": (255, 150, 0),
            "POSSESSO": (100, 0, 100),
            "LINK_ALMA": (255, 100, 255),
            "ESPELHADO": (200, 200, 255),
            "PERFURAR": (200, 200, 200),
        }
        return cores.get(efeito, BRANCO)

    
    def _remover_trail_projetil(self, proj):
        """Remove o trail visual de um projÃ©til imediatamente ao desativÃ¡-lo.
        BUG-SIM-01 fix: evita que o trail apareÃ§a por 1 frame extra apÃ³s o projÃ©til morrer.
        Seguro chamar mesmo que magic_vfx nÃ£o exista ou o projÃ©til nÃ£o tenha trail.
        """
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            try:
                self.magic_vfx.remove_trail(id(proj))
            except Exception:
                pass  # Trail pode nÃ£o existir â€” sem problema


    def _spawn_particulas_efeito(self, x, y, efeito):
        """Spawna partÃ­culas especÃ­ficas do efeito - v2.0 COLOSSAL"""
        cores_part = {
            # Fogo
            "QUEIMAR": (255, 100, 0),
            "QUEIMANDO": (255, 120, 20),
            "FOGO": (255, 150, 50),
            # Gelo
            "CONGELAR": (150, 220, 255),
            "CONGELADO": (180, 240, 255),
            "LENTO": (150, 200, 255),
            "GELO": (100, 200, 255),
            # Natureza/Veneno
            "VENENO": (100, 255, 100),
            "ENVENENADO": (80, 220, 80),
            "NATUREZA": (100, 200, 50),
            # Sangue
            "SANGRAMENTO": VERMELHO_SANGUE,
            "SANGRANDO": (200, 30, 30),
            "SANGUE": (180, 0, 50),
            # Raio
            "RAIO": (255, 255, 100),
            "PARALISIA": (255, 255, 150),
            # Trevas
            "TREVAS": (100, 0, 150),
            "DRENAR": (80, 0, 120),
            "MALDITO": (100, 0, 150),
            "NECROSE": (50, 50, 50),
            # Luz
            "LUZ": (255, 255, 220),
            "CEGO": (255, 255, 200),
            # Arcano
            "ARCANO": (150, 100, 255),
            "SILENCIADO": (180, 150, 255),
            # Tempo
            "TEMPO": (200, 180, 255),
            "TEMPO_PARADO": (220, 200, 255),
            # GravitaÃ§Ã£o
            "GRAVITACAO": (100, 50, 150),
            "PUXADO": (120, 70, 180),
            "VORTEX": (80, 30, 130),
            # Caos
            "CAOS": (255, 100, 200),
            # CC
            "ATORDOAR": (255, 255, 100),
            "ATORDOADO": (255, 255, 100),
            "ENRAIZADO": (139, 90, 43),
            "KNOCK_UP": (200, 200, 255),
            # Especiais
            "EXPLOSAO": (255, 200, 50),
            "BOMBA_RELOGIO": (255, 150, 0),
        }
        cor = cores_part.get(efeito)
        if cor:
            # Quantidade de partÃ­culas varia por tipo
            qtd = 8
            if efeito in ["EXPLOSAO", "FOGO", "QUEIMANDO"]:
                qtd = 15
            elif efeito in ["RAIO", "PARALISIA"]:
                qtd = 12
            elif efeito in ["VORTEX", "GRAVITACAO"]:
                qtd = 20
            elif efeito in ["CAOS"]:
                qtd = 18
            
            for _ in range(qtd):
                vx = random.uniform(-8, 8)
                vy = random.uniform(-8, 8)
                tamanho = random.randint(3, 7)
                vida = random.uniform(0.4, 0.8)
                self.particulas.append(Particula(x, y, cor, vx, vy, tamanho, vida))

    
    def _beam_colide_alvo(self, beam, alvo):
        """Verifica se um beam colide com um alvo"""
        # Usa colisÃ£o linha-cÃ­rculo
        from nucleo.physics import colisao_linha_circulo
        pt1 = (beam.x1 * PPM, beam.y1 * PPM)
        pt2 = (beam.x2 * PPM, beam.y2 * PPM)
        centro = (alvo.pos[0] * PPM, alvo.pos[1] * PPM)
        raio = alvo.raio_fisico * PPM
        return colisao_linha_circulo(pt1, pt2, centro, raio)


    # =========================================================================
    # SISTEMA DE DETECÃ‡ÃƒO DE EVENTOS DE MOVIMENTO v8.0
    # =========================================================================
    
    def _detectar_eventos_movimento(self):
        """
        Detecta eventos de movimento para disparar animaÃ§Ãµes apropriadas.
        
        Eventos detectados:
        - Aterrissagem (z era > 0, agora Ã© 0)
        - Pulo (z era 0, agora > 0)
        - Dash (dash_timer aumentou)
        - Knockback (velocidade alta apÃ³s tomar dano)
        - RecuperaÃ§Ã£o de stagger (stun_timer zerou)
        - Corrida rÃ¡pida (velocidade alta contÃ­nua)
        """
        for lutador in [self.p1, self.p2]:
            if lutador.morto:
                continue
            
            z_atual = getattr(lutador, 'z', 0)
            z_anterior = self._prev_z.get(lutador, 0)
            
            # PosiÃ§Ã£o X para sons posicionais
            pos_x = lutador.pos[0]
            listener_x = (self.p1.pos[0] + self.p2.pos[0]) / 2  # Centro entre lutadores
            
            # === ATERRISSAGEM ===
            # Detecta quando z cai para o chÃ£o (aterrissando)
            # Trigger mais cedo: quando z cai de qualquer altura para perto do chÃ£o
            if z_anterior > 0.15 and z_atual <= 0.05:
                # Som de aterrissagem
                if self.audio:
                    self.audio.play_movement("land", pos_x, listener_x)
                    _log.debug(f"[SOUND] Land triggered for {lutador.dados.nome}, z: {z_anterior:.2f} -> {z_atual:.2f}")
                # Efeito visual (se disponÃ­vel)
                if self.movement_anims:
                    vel_queda = abs(getattr(lutador, 'vel_z', 0))
                    self.movement_anims.criar_landing_effect(lutador, vel_queda + 5)
            
            # === PULO ===
            # Detecta quando z comeÃ§a a subir do chÃ£o (iniciando pulo)
            # Threshold baixo: vel_z ~10 * dt ~0.017 = ~0.17 de aumento por frame
            elif z_anterior <= 0.05 and z_atual > 0.1:
                # Som de pulo
                if self.audio:
                    self.audio.play_movement("jump", pos_x, listener_x)
                    _log.debug(f"[SOUND] Jump triggered for {lutador.dados.nome}, z: {z_anterior:.2f} -> {z_atual:.2f}")
                # Efeito visual (se disponÃ­vel)
                if self.movement_anims:
                    self.movement_anims.criar_jump_effect(lutador)
            
            # === DASH ===
            dash_atual = getattr(lutador, 'dash_timer', 0)
            dash_anterior = self._prev_dash.get(lutador, 0)
            
            if dash_atual > dash_anterior and dash_atual > 0.1:
                # Novo dash detectado
                direcao = math.radians(lutador.angulo_olhar)
                
                # Som de dash
                if self.audio:
                    self.audio.play_skill("DASH", "", pos_x, listener_x, phase="cast")
                
                # Efeito visual (se disponÃ­vel)
                if self.movement_anims:
                    # Determina tipo de dash baseado na aÃ§Ã£o
                    acao = getattr(lutador.brain, 'acao_atual', "")
                    if acao in ["RECUAR", "FUGIR"]:
                        tipo = MovementType.DASH_BACKWARD
                    elif acao in ["CIRCULAR", "FLANQUEAR"]:
                        tipo = MovementType.DASH_LATERAL
                    else:
                        tipo = MovementType.DASH_FORWARD
                    self.movement_anims.criar_dash_effect(lutador, direcao, tipo)
            
            # === RECUPERAÃ‡ÃƒO DE STAGGER ===
            stagger_atual = getattr(lutador, 'stun_timer', 0) > 0
            stagger_anterior = self._prev_stagger.get(lutador, False)
            
            if stagger_anterior and not stagger_atual:
                # Acabou de se recuperar - efeito visual
                if self.movement_anims:
                    self.movement_anims.criar_recovery_effect(lutador)
            
            # === CORRIDA RÃPIDA ===
            vel_magnitude = math.hypot(lutador.vel[0], lutador.vel[1])
            if vel_magnitude > 12.0 and z_atual <= 0.1 and self.movement_anims:
                # Correndo rÃ¡pido no chÃ£o
                if random.random() < 0.15:  # NÃ£o spammar efeitos
                    direcao = math.atan2(lutador.vel[1], lutador.vel[0])
                    self.movement_anims.criar_sprint_effect(lutador, direcao)
            
            # === DESVIO AI â€” trail lateral + som + cÃ¢mera suave ===
            # Sprint1: acao_atual == "DESVIO" nunca gerava nenhum VFX/som.
            # DashTrail sÃ³ disparava via dash_timer (skill). Agora rastreamos
            # a transiÃ§Ã£o de aÃ§Ã£o para DESVIO como evento de movimento dedicado.
            acao_atual_ai = getattr(getattr(lutador, 'brain', None), 'acao_atual', '')
            acao_anterior_ai = self._prev_acao_ai.get(lutador, '')
            if acao_atual_ai == "DESVIO" and acao_anterior_ai != "DESVIO":
                # Novo desvio detectado â€” efeitos cinematogrÃ¡ficos
                if self.movement_anims:
                    direcao_vel = math.atan2(lutador.vel[1], lutador.vel[0])
                    self.movement_anims.criar_dash_effect(
                        lutador, direcao_vel, MovementType.DASH_LATERAL
                    )
                if self.audio:
                    self.audio.play_movement("dodge", pos_x, listener_x)
                # Camera: shake leve â€” o desvio deve ser sentido, nÃ£o apenas visto
                if hasattr(self, 'cam'):
                    self.cam.aplicar_shake(2.0, 0.06)

            # === CONTRA_ATAQUE AI â€” flash de contorno dourado ===
            # Sprint1: CONTRA_ATAQUE era visualmente idÃªntico a MATAR.
            # Ao iniciar um contra-ataque, emite um flash dourado rÃ¡pido para
            # sinalizar que a aÃ§Ã£o foi uma resposta reactiva, nÃ£o ofensiva pura.
            if acao_atual_ai == "CONTRA_ATAQUE" and acao_anterior_ai not in ("CONTRA_ATAQUE", "MATAR"):
                lutador.flash_timer = 0.12
                lutador.flash_cor = (255, 220, 60)   # dourado
                if self.audio:
                    self.audio.play_movement("counter", pos_x, listener_x)

            self._prev_acao_ai[lutador] = acao_atual_ai

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


    def atualizar_rastros(self):
        for p in [self.p1, self.p2]:
            if p.morto: self.rastros[p] = []; continue
            if p.atacando and p.dados.arma_obj and "Reta" in p.dados.arma_obj.tipo:
                coords = p.get_pos_ponteira_arma()
                if coords: self.rastros[p].append((coords[1], coords[0]))
            else: self.rastros[p] = []
            if len(self.rastros[p]) > 10: self.rastros[p].pop(0)


    def spawn_particulas(self, x, y, dir_x, dir_y, cor, qtd):
        for _ in range(qtd):
            vx = dir_x * random.uniform(2, 12) + random.uniform(-4, 4)
            vy = dir_y * random.uniform(2, 12) + random.uniform(-4, 4)
            self.particulas.append(Particula(x*PPM, y*PPM, cor, vx, vy, random.randint(3, 8)))


    def ativar_slow_motion(self):
        self.time_scale = 0.2; self.slow_mo_timer = 2.0
        # Som de slow motion
        self.audio.play_special("slowmo_start", 0.6)


    def _salvar_memorias_rivais(self):
        """CB-04: Persiste memÃ³ria de rivalidade ao fim da luta (MEL-AI-07)."""
        p1, p2 = self.p1, self.p2
        if not (hasattr(p1, 'brain') and p1.brain and hasattr(p2, 'brain') and p2.brain):
            return
        if not self.vencedor:
            return
        venceu_p1 = (self.vencedor == p1.dados.nome)
        venceu_p2 = (self.vencedor == p2.dados.nome)
        try:
            p1.brain.salvar_memoria_rival(p2, venceu=venceu_p1)
        except Exception as e:
            _log.debug("[IA] salvar_memoria_rival p1 falhou: %s", e)
        try:
            p2.brain.salvar_memoria_rival(p1, venceu=venceu_p2)
        except Exception as e:
            _log.debug("[IA] salvar_memoria_rival p2 falhou: %s", e)


