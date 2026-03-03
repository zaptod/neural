"""Auto-generated mixin — see scripts/split_simulacao.py"""
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


class SimuladorCombat:
    """Mixin de combate: detecção de hits, clashes, bloqueios e física."""


    def checar_ataque(self, atacante, defensor):
        """
        Verifica ataque usando o novo sistema de hitbox com debug.
        
        === INTEGRAÇÃO GAME FEEL v8.0 ===
        - Hit Stop proporcional à classe (Força > Ágil)
        - Super Armor para tanks/berserkers
        - Camera shake baseado em INTENSIDADE, não velocidade
        
        === v10.1: PREVENÇÃO DE MULTI-HIT ===
        - Cada ataque só pode acertar cada alvo UMA vez
        - Evita o bug de múltiplos hits durante um único swing
        """
        
        # Armas ranged e mágicas NÃO usam hitbox direta
        # Elas causam dano apenas via projéteis/orbes
        arma = atacante.dados.arma_obj
        if arma and arma.tipo in ["Arremesso", "Arco", "Mágica"]:
            return False  # Dano é feito pelos projéteis/orbes, não pela hitbox
        
        # === v10.1: VERIFICA SE JÁ ACERTOU ESTE ALVO NESTE ATAQUE ===
        defensor_id = id(defensor)
        if hasattr(atacante, 'alvos_atingidos_neste_ataque'):
            if defensor_id in atacante.alvos_atingidos_neste_ataque:
                # Já acertou este alvo neste ataque, ignora
                return False
        
        # Usa o novo sistema modular para armas melee
        acertou, motivo = verificar_hit(atacante, defensor)
        
        if acertou:
            # === v10.1: MARCA ALVO COMO ATINGIDO NESTE ATAQUE ===
            if hasattr(atacante, 'alvos_atingidos_neste_ataque'):
                atacante.alvos_atingidos_neste_ataque.add(defensor_id)
            
            dx, dy = int(defensor.pos[0] * PPM), int(defensor.pos[1] * PPM)
            vx = defensor.pos[0] - atacante.pos[0]
            vy = defensor.pos[1] - atacante.pos[1]
            mag = math.hypot(vx, vy) or 1

            # Usa o novo sistema de dano modificado
            dano_base = arma.dano * (atacante.dados.forca / 2.0)
            dano, is_critico = atacante.calcular_dano_ataque(dano_base) if hasattr(atacante, 'calcular_dano_ataque') else (dano_base, False)

            # CM-09 fix: desgasta durabilidade da arma a cada hit confirmado
            if hasattr(arma, 'durabilidade'):
                desgaste = 0.5 if not is_critico else 1.0
                arma.durabilidade = max(0.0, arma.durabilidade - desgaste)
                # Arma quebrada: aplica penalidade de 50% no dano
                if arma.durabilidade <= 0:
                    dano *= 0.5
                    if not getattr(arma, '_aviso_quebrada_exibido', False):
                        self.textos.append(FloatingText(
                            atacante.pos[0] * PPM, atacante.pos[1] * PPM - 70,
                            "ARMA QUEBRADA!", (200, 50, 50), 22
                        ))
                        arma._aviso_quebrada_exibido = True

            # === ÁUDIO v10.0 - SOM DE ATAQUE (baseado no dano) ===
            tipo_ataque = arma.tipo if arma else "SOCO"
            if self.audio:
                listener_x = self.cam.x / PPM
                self.audio.play_attack(tipo_ataque, atacante.pos[0], listener_x, damage=dano, is_critical=is_critico)
            
            # Notifica Sistema de Coreografia v5.0
            if self.choreographer:
                self.choreographer.registrar_hit(atacante, defensor, dano)
            
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
            
            if defensor.tomar_dano(dano, kb_x, kb_y, "NORMAL", atacante=atacante):
                # === PASSIVA em hit — processa lifesteal, execute, double_hit, etc (BUG-03) ===
                if hasattr(atacante, 'aplicar_passiva_em_hit'):
                    atacante.aplicar_passiva_em_hit(dano, defensor)
                # === ÁUDIO v10.0 - SOM DE MORTE ===
                if self.audio:
                    self.audio.play_special("ko", volume=1.0)
                
                # === MORTE - EFEITOS MÁXIMOS ===
                # BUG-C5: spawn_particulas espera coords de mundo (metros), não pixels
                self.spawn_particulas(defensor.pos[0], defensor.pos[1], vx/mag, vy/mag, VERMELHO_SANGUE, 50)
                
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
                # === ÁUDIO v10.0 - SOM DE IMPACTO ===
                if self.audio:
                    listener_x = self.cam.x / PPM
                    is_counter = resultado_hit and resultado_hit.get("counter_hit", False)
                    self.audio.play_impact(dano, defensor.pos[0], listener_x, is_critico, is_counter)
                
                # === HIT NORMAL - EFEITOS PROPORCIONAIS AO DANO E FORÇA ===
                # Knockback visual proporcional ao dano
                if dano > 8 or forca_atacante > 12:
                    self._criar_knockback_visual(defensor, direcao_impacto, dano)
                
                # Partículas proporcionais
                qtd_part = max(5, min(25, int(dano / 3)))
                # BUG-C5: spawn_particulas espera coords de mundo (metros), não pixels
                self.spawn_particulas(defensor.pos[0], defensor.pos[1], vx/mag, vy/mag, VERMELHO_SANGUE, qtd_part)
                
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


    def verificar_colisoes_combate(self):
        if self.p1.dados.arma_obj and self.p2.dados.arma_obj:
            if self.checar_clash_geral(self.p1, self.p2):
                self.efeito_clash(self.p1, self.p2); return 
        morreu_1 = self.checar_ataque(self.p1, self.p2)
        morreu_2 = self.checar_ataque(self.p2, self.p1)
        if morreu_1: self.ativar_slow_motion(); self.vencedor = self.p1.dados.nome
        if morreu_2: self.ativar_slow_motion(); self.vencedor = self.p2.dados.nome


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


    def checar_clash_geral(self, p1, p2):
        # BUG-F2: Guarda contra arma_obj = None
        if not p1.dados.arma_obj or not p2.dados.arma_obj:
            return False
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
        
        # Cores das armas para o efeito — BUG-F2: guarda contra arma_obj = None
        cor1 = (p1.dados.arma_obj.r, p1.dados.arma_obj.g, p1.dados.arma_obj.b) if p1.dados.arma_obj and hasattr(p1.dados.arma_obj, 'r') else (255, 255, 255)
        cor2 = (p2.dados.arma_obj.r, p2.dados.arma_obj.g, p2.dados.arma_obj.b) if p2.dados.arma_obj and hasattr(p2.dados.arma_obj, 'r') else (255, 255, 255)
        
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
        
        # SOM DE CLASH
        listener_x = (self.p1.pos[0] + self.p2.pos[0]) / 2
        self.audio.play_positional("clash_magic", mx, listener_x, volume=1.0)
        
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

    
    def _executar_sword_clash(self):
        """Executa efeito de clash de espadas entre dois lutadores (momento cinematográfico)"""
        if not self.p1 or not self.p2:
            return
        
        # === CANCELA OS ATAQUES DE AMBOS (evita que alguém tome dano) ===
        self.p1.atacando = False
        self.p2.atacando = False
        self.p1.timer_animacao = 0
        self.p2.timer_animacao = 0
        # Reseta cooldown de ataque para que possam atacar novamente após o clash
        self.p1.cooldown_ataque = 0.3
        self.p2.cooldown_ataque = 0.3
        # Limpa alvos atingidos para evitar hits fantasmas
        self.p1.alvos_atingidos_neste_ataque.clear()
        self.p2.alvos_atingidos_neste_ataque.clear()
        
        # Ponto médio do clash (entre os dois lutadores)
        mx = (self.p1.pos[0] + self.p2.pos[0]) / 2
        my = (self.p1.pos[1] + self.p2.pos[1]) / 2
        
        # Cores das armas/lutadores
        cor1 = self.p1.dados.cor if hasattr(self.p1, 'dados') and hasattr(self.p1.dados, 'cor') else (255, 180, 80)
        cor2 = self.p2.dados.cor if hasattr(self.p2, 'dados') and hasattr(self.p2.dados, 'cor') else (80, 180, 255)
        
        # === EFEITOS VISUAIS ===
        # Flash de impacto principal
        self.impact_flashes.append(ImpactFlash(mx * PPM, my * PPM, AMARELO_FAISCA, 2.0, "clash"))
        
        # Shockwave dramático
        self.shockwaves.append(Shockwave(mx * PPM, my * PPM, BRANCO, tamanho=2.5))
        
        # Texto épico
        textos_clash = ["CLASH!", "CLANG!", "⚔ CLASH ⚔", "STEEL!", "IMPACTO!"]
        texto = random.choice(textos_clash)
        self.textos.append(FloatingText(mx * PPM, my * PPM - 50, texto, AMARELO_FAISCA, 40))
        
        # === SOM DE CLASH DE ESPADAS - FORÇA TOCAR ===
        _log.debug(f"[SWORD CLASH] Tentando tocar som clash_swords...")
        try:
            # Tenta via AudioManager
            if hasattr(self.audio, 'sounds') and 'clash_swords' in self.audio.sounds:
                sound = self.audio.sounds['clash_swords']
                sound.set_volume(1.0)
                sound.play()
                _log.debug(f"[SWORD CLASH] Som tocado diretamente!")
            else:
                # Fallback: tenta carregar e tocar
                import os
                sound_path = os.path.join("sounds", "clash_swords.mp3")
                if os.path.exists(sound_path):
                    sound = pygame.mixer.Sound(sound_path)
                    sound.set_volume(1.0)
                    sound.play()
                    _log.debug(f"[SWORD CLASH] Som carregado e tocado via fallback!")
                else:
                    _log.debug(f"[SWORD CLASH] ERRO: Arquivo de som não encontrado!")
        except Exception as e:
            _log.debug(f"[SWORD CLASH] ERRO ao tocar som: {e}")
        
        # === CAMERA SHAKE E HIT STOP DRAMÁTICOS ===
        self.cam.aplicar_shake(20.0, 0.3)
        self.hit_stop_timer = 0.2  # Pausa dramática
        
        # === PARTÍCULAS DE FAÍSCAS ===
        for _ in range(40):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(100, 250)
            cor = random.choice([AMARELO_FAISCA, BRANCO, cor1, cor2, (255, 200, 100)])
            self.particulas.append(Particula(
                mx * PPM, my * PPM, cor,
                math.cos(ang) * vel / 60, math.sin(ang) * vel / 60,
                random.randint(3, 7), random.uniform(0.3, 0.6)
            ))
        
        # === EFEITO ADICIONAL - Hit Sparks nas armas ===
        # Direção aleatória para as faíscas
        direcao_faiscas = random.uniform(0, math.pi * 2)
        self.hit_sparks.append(HitSpark(mx * PPM, my * PPM, AMARELO_FAISCA, direcao_faiscas, 1.5))
        
        _log.debug(f"[SWORD CLASH] Épico clash de espadas em ({mx:.1f}, {my:.1f})!")


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
                    from core.physics import colisao_linha_circulo
                    if colisao_linha_circulo(linha_arma[0], linha_arma[1], 
                                            (proj.x * PPM, proj.y * PPM), 
                                            proj.raio * PPM + 5):
                        # PARRY!
                        self._efeito_parry(proj, alvo)
                        return True
        
        return False

    
    def _efeito_bloqueio(self, proj, bloqueador, pos_escudo):
        """Efeito visual de bloqueio"""
        # === ÁUDIO v10.0 - SOM DE BLOQUEIO ===
        if self.audio:
            listener_x = self.cam.x / PPM
            self.audio.play_special("shield_block", volume=0.7)
        
        # CB-01: notifica IA do bloqueio bem-sucedido (abre janela pos_bloqueio)
        if hasattr(bloqueador, 'ai') and bloqueador.ai:
            if hasattr(bloqueador.ai, 'on_bloqueio_sucesso'):
                bloqueador.ai.on_bloqueio_sucesso()
        
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
        # CB-01: notifica IA do parry (também conta como bloqueio — abre janela pos_bloqueio)
        if hasattr(parryer, 'ai') and parryer.ai:
            if hasattr(parryer.ai, 'on_bloqueio_sucesso'):
                parryer.ai.on_bloqueio_sucesso()
        
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
