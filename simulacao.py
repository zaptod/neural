import pygame
import json
import math
import random
import database
from config import *
from effects import Particula, FloatingText, Decal, Shockwave, Câmera
from entities import Lutador
from physics import colisao_linha_circulo, intersect_line_circle, colisao_linha_linha, normalizar_angulo

class Simulador:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Neural Fights - Modular v2")
        self.clock = pygame.time.Clock()
        self.rodando = True
        
        self.cam = Câmera()
        self.particulas = [] 
        self.decals = [] 
        self.textos = [] 
        self.shockwaves = [] 
        self.projeteis = []

        self.paused = False
        self.show_hud = True
        self.show_analysis = False
        self.time_scale = 1.0
        self.slow_mo_timer = 0.0
        self.hit_stop_timer = 0.0 
        self.vencedor = None
        self.rastros = {} 
        self.vida_visual_p1 = 100; self.vida_visual_p2 = 100
        self.recarregar_tudo()

    def recarregar_tudo(self):
        try:
            self.p1, self.p2 = self.carregar_luta_dados()
            self.particulas = []; self.decals = []; self.textos = []; self.shockwaves = []; self.projeteis = []
            self.time_scale = 1.0; self.slow_mo_timer = 0.0; self.hit_stop_timer = 0.0
            self.vencedor = None; self.paused = False; self.rastros = {self.p1: [], self.p2: []}
            if self.p1: self.vida_visual_p1 = self.p1.vida_max
            if self.p2: self.vida_visual_p2 = self.p2.vida_max
        except Exception as e: print(f"Erro: {e}")

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
                if event.key == pygame.K_h: self.show_hud = not self.show_hud
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
        if self.paused: return

        for t in self.textos: t.update(dt)
        self.textos = [t for t in self.textos if t.vida > 0]
        for s in self.shockwaves: s.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.vida > 0]

        if self.hit_stop_timer > 0: self.hit_stop_timer -= dt; return

        # === COLETA OBJETOS DOS LUTADORES ===
        for p in [self.p1, self.p2]:
            # Projéteis
            if p.buffer_projeteis:
                self.projeteis.extend(p.buffer_projeteis)
                p.buffer_projeteis = []
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

        # === ATUALIZA PROJÉTEIS ===
        for proj in self.projeteis:
            proj.atualizar(dt)
            alvo = self.p2 if proj.dono == self.p1 else self.p1
            dx = alvo.pos[0] - proj.x; dy = alvo.pos[1] - proj.y
            dist = math.hypot(dx, dy)
            if dist < (alvo.raio_fisico + 0.3) and proj.ativo:
                proj.ativo = False
                self.shockwaves.append(Shockwave(proj.x * PPM, proj.y * PPM, proj.cor))
                
                # Aplica dano com efeito
                dano_final = proj.dono.get_dano_modificado(proj.dano) if hasattr(proj.dono, 'get_dano_modificado') else proj.dano
                tipo_efeito = proj.tipo_efeito if hasattr(proj, 'tipo_efeito') else "NORMAL"
                
                if alvo.tomar_dano(dano_final, dx/(dist or 1), dy/(dist or 1), tipo_efeito):
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                    self.ativar_slow_motion(); self.vencedor = proj.dono.dados.nome
                else:
                    # Cor do texto baseado no efeito
                    cor_txt = self._get_cor_efeito(tipo_efeito)
                    self.textos.append(FloatingText(alvo.pos[0]*PPM, alvo.pos[1]*PPM - 30, int(dano_final), cor_txt))
                    
                    # Partículas baseadas no efeito
                    self._spawn_particulas_efeito(alvo.pos[0]*PPM, alvo.pos[1]*PPM, tipo_efeito)
                
                # Efeito DRENAR recupera vida do atacante
                if tipo_efeito == "DRENAR":
                    proj.dono.vida = min(proj.dono.vida_max, proj.dono.vida + dano_final * 0.15)
                    self.textos.append(FloatingText(proj.dono.pos[0]*PPM, proj.dono.pos[1]*PPM - 30, f"+{int(dano_final*0.15)}", (100, 255, 150), 16))

        self.projeteis = [p for p in self.projeteis if p.ativo]

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
            self.p1.update(dt, self.p2); self.p2.update(dt, self.p1)
            self.resolver_fisica_corpos(dt)
            self.verificar_colisoes_combate()
            self.atualizar_rastros()
            self.vida_visual_p1 += (self.p1.vida - self.vida_visual_p1) * 5 * dt
            self.vida_visual_p2 += (self.p2.vida - self.vida_visual_p2) * 5 * dt
        
        for p in self.particulas[:]:
            p.atualizar(dt)
            if p.vida <= 0: 
                if p.cor == VERMELHO_SANGUE and random.random() < 0.3:
                    self.decals.append(Decal(p.x, p.y, p.tamanho * 2, SANGUE_ESCURO))
                self.particulas.remove(p)
        if len(self.decals) > 100: self.decals.pop(0)

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

    def atualizar_rastros(self):
        for p in [self.p1, self.p2]:
            if p.morto: self.rastros[p] = []; continue
            if p.atacando and p.dados.arma_obj and "Reta" in p.dados.arma_obj.tipo:
                coords = p.get_pos_ponteira_arma()
                if coords: self.rastros[p].append((coords[1], coords[0]))
            else: self.rastros[p] = []
            if len(self.rastros[p]) > 10: self.rastros[p].pop(0)

    def resolver_fisica_corpos(self, dt):
        p1, p2 = self.p1, self.p2
        if p1.morto or p2.morto: return
        dx = p2.pos[0] - p1.pos[0]; dy = p2.pos[1] - p1.pos[1]
        dist = math.hypot(dx, dy)
        soma_raios = p1.raio_fisico + p2.raio_fisico
        if dist < soma_raios and abs(p1.z - p2.z) < 1.0:
            penetracao = soma_raios - dist
            nx, ny = (1, 0) if dist == 0 else (dx/dist, dy/dist)
            fator = 20.0 if penetracao > 0.2 else 5.0
            empurrao = (penetracao / 2.0) * fator
            p1.vel[0] -= nx * empurrao; p1.vel[1] -= ny * empurrao
            p2.vel[0] += nx * empurrao; p2.vel[1] += ny * empurrao

    def verificar_colisoes_combate(self):
        if self.p1.dados.arma_obj and self.p2.dados.arma_obj:
            if self.checar_clash_geral(self.p1, self.p2):
                self.efeito_clash(self.p1, self.p2); return 
        morreu_1 = self.checar_ataque(self.p1, self.p2)
        morreu_2 = self.checar_ataque(self.p2, self.p1)
        if morreu_1: self.ativar_slow_motion(); self.vencedor = self.p1.dados.nome
        if morreu_2: self.ativar_slow_motion(); self.vencedor = self.p2.dados.nome

    def efeito_clash(self, p1, p2):
        mx = (p1.pos[0] + p2.pos[0]) / 2 * PPM; my = (p1.pos[1] + p2.pos[1]) / 2 * PPM
        for _ in range(20):
            vx = random.uniform(-15, 15); vy = random.uniform(-15, 15)
            self.particulas.append(Particula(mx, my, AMARELO_FAISCA, vx, vy, random.randint(3, 6), 0.4))
        vec_x = p1.pos[0] - p2.pos[0]; vec_y = p1.pos[1] - p2.pos[1]
        mag = math.hypot(vec_x, vec_y) or 1
        p1.tomar_clash(vec_x/mag, vec_y/mag); p2.tomar_clash(-vec_x/mag, -vec_y/mag)
        self.cam.aplicar_shake(15.0, 0.2); self.hit_stop_timer = 0.1 
        self.shockwaves.append(Shockwave(mx, my, BRANCO))
        self.textos.append(FloatingText(mx, my - 50, "CLASH!", AMARELO_FAISCA, 30))

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
        if defensor.morto: return False
        if not atacante.dados.arma_obj: return False
        if abs(atacante.z - defensor.z) > 1.2: return False 
        arma = atacante.dados.arma_obj; acertou = False
        ax, ay = int(atacante.pos[0] * PPM), int(atacante.pos[1] * PPM)
        dx, dy = int(defensor.pos[0] * PPM), int(defensor.pos[1] * PPM)
        raio_def = int((defensor.dados.tamanho / 2) * PPM)

        if "Reta" in arma.tipo:
            if atacante.atacando and 0.05 < atacante.timer_animacao < 0.2:
                coords = atacante.get_pos_ponteira_arma()
                if coords and colisao_linha_circulo(coords[0], coords[1], (dx, dy), raio_def): acertou = True
        else: 
            dist_base = int(((arma.distancia/100)*PPM)*atacante.fator_escala)
            dist_total = int((atacante.dados.tamanho/2)*PPM) + dist_base
            dist_inimigo = math.hypot(dx - ax, dy - ay)
            if dist_total - raio_def <= dist_inimigo <= dist_total + raio_def:
                ang_inimigo = math.degrees(math.atan2(dy - ay, dx - ax))
                diff = normalizar_angulo(ang_inimigo - atacante.angulo_arma_visual)
                if abs(diff) <= arma.largura / 2: acertou = True

        if acertou:
            vx = defensor.pos[0] - atacante.pos[0]; vy = defensor.pos[1] - atacante.pos[1]
            mag = math.hypot(vx, vy) or 1
            
            # Usa o novo sistema de dano modificado
            dano_base = arma.dano * (atacante.dados.forca / 2.0)
            dano = atacante.get_dano_modificado(dano_base) if hasattr(atacante, 'get_dano_modificado') else dano_base
            
            if defensor.tomar_dano(dano, vx/mag, vy/mag, "NORMAL"):
                self.spawn_particulas(dx, dy, vx/mag, vy/mag, VERMELHO_SANGUE, 50)
                self.cam.aplicar_shake(30.0, 0.4); self.hit_stop_timer = 0.3
                self.textos.append(FloatingText(dx*PPM, dy*PPM - 50, "FATAL!", VERMELHO_SANGUE, 40))
                self.ativar_slow_motion(); self.vencedor = atacante.dados.nome
                return True
            else:
                self.spawn_particulas(dx, dy, vx/mag, vy/mag, VERMELHO_SANGUE, 10)
                self.cam.aplicar_shake(10.0, 0.1); self.hit_stop_timer = 0.05
                self.textos.append(FloatingText(dx*PPM, dy*PPM - 30, int(dano), BRANCO))
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
                    pygame.draw.line(self.tela, proj.cor, p1, p2, max(1, int(proj.raio * PPM * self.cam.zoom * 0.5)))
            
            # Projétil principal
            px, py = self.cam.converter(proj.x * PPM, proj.y * PPM)
            pr = self.cam.converter_tam(proj.raio * PPM)
            pygame.draw.circle(self.tela, proj.cor, (px, py), pr)
            pygame.draw.circle(self.tela, BRANCO, (px, py), max(1, pr-2))

        for s in self.shockwaves: s.draw(self.tela, self.cam)
        for t in self.textos: t.draw(self.tela, self.cam)

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
        centro = (sx, sy - off_y); cor = (255,255,255) if l.flash_timer > 0 else (l.dados.cor_r, l.dados.cor_g, l.dados.cor_b)
        pygame.draw.circle(self.tela, cor, centro, raio)
        contorno = AMARELO_FAISCA if l.stun_timer > 0 else ((255,255,255) if l.atacando else (50,50,50))
        largura = max(1, self.cam.converter_tam(4 if l.atacando or l.stun_timer > 0 else 2))
        pygame.draw.circle(self.tela, contorno, centro, raio, largura)
        if l.dados.arma_obj: self.desenhar_arma(l.dados.arma_obj, centro, l.angulo_arma_visual, l.dados.tamanho, raio)

    def desenhar_arma(self, arma, centro, angulo, tam_char, raio_char):
        cx, cy = centro; rad = math.radians(angulo)
        cor = (arma.r, arma.g, arma.b); escala = tam_char / ALTURA_PADRAO
        if "Reta" in arma.tipo:
            cabo = self.cam.converter_tam(((arma.comp_cabo/100)*PPM)*escala)
            lamina = self.cam.converter_tam(((arma.comp_lamina/100)*PPM)*escala)
            larg = max(1, self.cam.converter_tam(((arma.largura/100)*PPM)*escala))
            ex, ey = cx + math.cos(rad)*cabo, cy + math.sin(rad)*cabo
            fx, fy = cx + math.cos(rad)*(cabo+lamina), cy + math.sin(rad)*(cabo+lamina)
            pygame.draw.line(self.tela, (100,50,0), (cx, cy), (ex, ey), larg)
            pygame.draw.line(self.tela, cor, (ex, ey), (fx, fy), larg)
        else:
            dist = self.cam.converter_tam(((arma.distancia/100)*PPM)*escala) + raio_char
            if arma.largura < 20:
                ox = cx + math.cos(rad)*dist; oy = cy + math.sin(rad)*dist
                raio_drone = max(2, self.cam.converter_tam(8*escala))
                pygame.draw.circle(self.tela, cor, (int(ox), int(oy)), raio_drone)
                pygame.draw.line(self.tela, (80,80,80), (cx,cy), (ox,oy), 1)
            else:
                pts = []
                for i in range(11):
                    a = rad + math.radians(-arma.largura/2 + (i * arma.largura/10))
                    pts.append((cx + math.cos(a)*dist, cy + math.sin(a)*dist))
                larg_arco = max(2, self.cam.converter_tam(5*escala))
                pygame.draw.lines(self.tela, cor, False, pts, larg_arco)
                pygame.draw.line(self.tela, (50,50,50), (cx,cy), pts[0], 1)
                pygame.draw.line(self.tela, (50,50,50), (cx,cy), pts[-1], 1)

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
        w, h = 220, 190
        s = pygame.Surface((w, h), pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (100, 100, 100), (x, y, w, h), 1)
        fonte_tit = pygame.font.SysFont("Arial", 14, bold=True); fonte_txt = pygame.font.SysFont("Arial", 12)
        self.tela.blit(fonte_tit.render("COMANDOS", True, COR_TEXTO_TITULO), (x + 10, y + 10))
        comandos = [("WASD / Setas", "Mover Câmera"), ("Scroll", "Zoom"), ("1/2/3", "Modos Cam"), ("SPACE", "Pause"), ("T/F", "Speed"), ("TAB", "Dados"), ("H", "HUD"), ("R", "Reset"), ("ESC", "Sair")]
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
            raw_dt = self.clock.tick(FPS) / 1000.0
            if self.slow_mo_timer > 0:
                self.slow_mo_timer -= raw_dt
                if self.slow_mo_timer <= 0: self.time_scale = 1.0
            dt = raw_dt * self.time_scale
            self.processar_inputs(); self.update(dt); self.desenhar(); pygame.display.flip()
        pygame.quit()

if __name__ == "__main__":
    Simulador().run()