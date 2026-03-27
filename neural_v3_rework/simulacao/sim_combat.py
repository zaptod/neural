"""Auto-generated mixin â€” gerado por scripts/split_simulacao.py (arquivado em _archive/scripts/)"""
from dataclasses import dataclass
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
    BUDGET_PARTICULAS_CLASH, BUDGET_PARTICULAS_CLASH_MAGICO,  # A04 Sprint 9
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


@dataclass
class AttackImpactVector:
    dx_px: int
    dy_px: int
    vx: float
    vy: float
    mag: float
    direcao_impacto: float
    posicao_mundo: tuple[float, float]


@dataclass
class ChainAttackResolution:
    dano: float
    knockback_mult: float = 1.0
    label: str | None = None


@dataclass
class GameFeelHitResolution:
    dano: float
    resultado_hit: dict | None = None


@dataclass
class AttackKnockbackResolution:
    posicao_impacto: tuple[float, float]
    kb_x: float
    kb_y: float


@dataclass
class AttackPreparationContext:
    arma: object | None
    vetor_impacto: AttackImpactVector
    dano: float
    is_critico: bool
    chain_kb_mult: float = 1.0
    chain_label: str | None = None


@dataclass
class ClashVisualContext:
    mx: float
    my: float
    cor1: tuple[int, int, int]
    cor2: tuple[int, int, int]
    ang_p1_p2: float
    vec_x: float
    vec_y: float
    mag: float


@dataclass
class BodyCollisionContext:
    p1: object
    p2: object
    dist: float
    nx: float
    ny: float
    soma_raios: float


@dataclass
class MagicProjectileClashContext:
    mx: float
    my: float
    mx_px: float
    my_px: float
    cor1: tuple[int, int, int]
    cor2: tuple[int, int, int]


@dataclass
class SwordClashContext:
    mx: float
    my: float
    mx_px: float
    my_px: float
    cor1: tuple[int, int, int]
    cor2: tuple[int, int, int]
    texto: str


@dataclass
class ProjectileDefenseVisualContext:
    proj_x_px: float
    proj_y_px: float
    cor_lutador: tuple[int, int, int]
    ang_impacto: float


@dataclass
class DashDodgeVisualContext:
    pos_x_px: float
    pos_y_px: float
    cor_lutador: tuple[int, int, int]
    trilha_posicoes: list[tuple[float, float]]


@dataclass
class DefensiveTempoFeedback:
    shake_intensity: float = 0.0
    shake_duration: float = 0.0
    hit_stop: float = 0.0
    time_scale: float | None = None
    slow_mo_timer: float = 0.0


@dataclass
class ProjectileClashContext:
    proj1: object
    proj2: object
    dist: float
    raio_colisao: float


class SimuladorCombat:
    """Mixin de combate: detecÃ§Ã£o de hits, clashes, bloqueios e fÃ­sica."""

    def _arma_usa_hitbox_direta(self, arma):
        return not arma or arma.tipo not in ["Arremesso", "Arco", "MÃ¡gica"]

    def _ja_acertou_alvo_neste_ataque(self, atacante, defensor):
        alvos_atingidos = getattr(atacante, 'alvos_atingidos_neste_ataque', None)
        return alvos_atingidos is not None and id(defensor) in alvos_atingidos

    def _marcar_alvo_atingido_neste_ataque(self, atacante, defensor):
        alvos_atingidos = getattr(atacante, 'alvos_atingidos_neste_ataque', None)
        if alvos_atingidos is not None:
            alvos_atingidos.add(id(defensor))

    def _calcular_vetor_impacto(self, atacante, defensor):
        dx_px = int(defensor.pos[0] * PPM)
        dy_px = int(defensor.pos[1] * PPM)
        vx = defensor.pos[0] - atacante.pos[0]
        vy = defensor.pos[1] - atacante.pos[1]
        mag = math.hypot(vx, vy) or 1
        return AttackImpactVector(
            dx_px=dx_px,
            dy_px=dy_px,
            vx=vx,
            vy=vy,
            mag=mag,
            direcao_impacto=math.atan2(vy, vx),
            posicao_mundo=(dx_px / PPM, dy_px / PPM),
        )

    def _calcular_dano_ataque_melee(self, atacante, arma):
        dano_base = arma.dano * (0.78 + atacante.dados.forca / 3.1)
        if hasattr(atacante, 'calcular_dano_ataque'):
            return atacante.calcular_dano_ataque(dano_base)
        return dano_base, False

    def _aplicar_desgaste_durabilidade_arma(self, atacante, arma, dano, is_critico):
        if not hasattr(arma, 'durabilidade'):
            return dano

        desgaste = 0.5 if not is_critico else 1.0
        arma.durabilidade = max(0.0, arma.durabilidade - desgaste)
        if arma.durabilidade > 0:
            return dano

        dano *= 0.5
        if not getattr(arma, '_aviso_quebrada_exibido', False):
            self.textos.append(FloatingText(
                atacante.pos[0] * PPM, atacante.pos[1] * PPM - 70,
                "ARMA QUEBRADA!", (200, 50, 50), 22
            ))
            arma._aviso_quebrada_exibido = True
        return dano

    def _aplicar_mecanicas_corrente(self, atacante, defensor, arma, dano, vetor_impacto):
        if not arma or arma.tipo != "Corrente":
            return ChainAttackResolution(dano=dano)

        chain_estilo = getattr(arma, 'estilo', '')
        chain_result = ChainAttackResolution(dano=dano)
        dist_hit = math.hypot(vetor_impacto.vx, vetor_impacto.vy)

        if "Mangual" in chain_estilo or "Flail" in chain_estilo:
            momentum = getattr(atacante, 'chain_momentum', 0)
            chain_result.dano *= (1.0 + momentum * 0.6)
            chain_result.knockback_mult = 1.0 + momentum * 0.8
            atacante.chain_momentum = min(1.0, momentum + 0.25)
            if momentum >= 0.7:
                chain_result.label = "MOMENTUM!"
            return chain_result

        if chain_estilo == "Kusarigama":
            mode = getattr(atacante, 'chain_mode', 0)
            if mode == 0:
                chain_result.dano *= 0.75
                from nucleo.combat import DotEffect
                dot = DotEffect("SANGRANDO", defensor, arma.dano * 0.3, 3.0, (180, 40, 40))
                defensor.dots_ativos.append(dot)
                chain_result.label = "CORTE!"
            else:
                defensor.stun_timer = max(defensor.stun_timer, 0.4)
                chain_result.knockback_mult = 1.3
                chain_result.label = "STUN!"
            return chain_result

        if chain_estilo == "Chicote":
            alcance_total = getattr(atacante, 'raio_fisico', 0.5) * 6.0
            ratio_dist = dist_hit / max(alcance_total, 0.1)
            if ratio_dist >= 0.65:
                chain_result.dano *= 2.0
                chain_result.label = "CRACK!"
                if defensor.atacando:
                    defensor.atacando = False
                    defensor.cooldown_ataque = 0.3
            else:
                chain_result.dano *= 0.6
            chain_result.knockback_mult = 0.5
            return chain_result

        if chain_estilo == "Meteor Hammer":
            spin_speed = getattr(atacante, 'chain_spin_speed', 0)
            chain_result.dano *= (1.0 + min(spin_speed, 3.0) * 0.33)
            chain_result.knockback_mult = 0.8
            if spin_speed >= 2.0:
                chain_result.label = "ORBITA!"
            return chain_result

        if "Corrente com Peso" in chain_estilo:
            defensor.slow_timer = max(defensor.slow_timer, 1.5)
            defensor.slow_fator = min(defensor.slow_fator, 0.6)
            pull_force = 4.0
            pull_dx = atacante.pos[0] - defensor.pos[0]
            pull_dy = atacante.pos[1] - defensor.pos[1]
            pull_mag = math.hypot(pull_dx, pull_dy) or 1
            defensor.vel[0] += (pull_dx / pull_mag) * pull_force
            defensor.vel[1] += (pull_dy / pull_mag) * pull_force
            chain_result.knockback_mult = 0.3
            chain_result.label = "PUXÃƒO!"
            return chain_result

        return chain_result

    def _determinar_tipo_golpe(self, atacante, dano, is_critico):
        classe_atacante = getattr(atacante, 'classe_nome', "Guerreiro")
        if any(c in classe_atacante for c in ["Berserker", "Guerreiro", "Cavaleiro", "Gladiador"]):
            tipo_golpe = "PESADO" if dano > 20 else "MEDIO"
            if dano > 35 or is_critico:
                tipo_golpe = "DEVASTADOR"
            return tipo_golpe
        if any(c in classe_atacante for c in ["Assassino", "Ninja", "Ladino"]):
            return "DEVASTADOR" if is_critico else "LEVE"
        if dano > 25:
            return "PESADO"
        return "MEDIO"

    def _registrar_tentativa_ataque_stats(self, atacante):
        if hasattr(self, 'stats_collector'):
            self.stats_collector.record_attack_attempt(atacante.dados.nome)

    def _preparar_contexto_ataque_melee(self, atacante, defensor):
        arma = atacante.dados.arma_obj
        if not self._arma_usa_hitbox_direta(arma):
            return None

        if self._ja_acertou_alvo_neste_ataque(atacante, defensor):
            return None

        acertou, _ = verificar_hit(atacante, defensor)
        self._registrar_tentativa_ataque_stats(atacante)
        if not acertou:
            return None

        self._marcar_alvo_atingido_neste_ataque(atacante, defensor)

        vetor_impacto = self._calcular_vetor_impacto(atacante, defensor)
        dano, is_critico = self._calcular_dano_ataque_melee(atacante, arma)
        dano = self._aplicar_desgaste_durabilidade_arma(atacante, arma, dano, is_critico)
        chain_result = self._aplicar_mecanicas_corrente(atacante, defensor, arma, dano, vetor_impacto)

        return AttackPreparationContext(
            arma=arma,
            vetor_impacto=vetor_impacto,
            dano=chain_result.dano,
            is_critico=is_critico,
            chain_kb_mult=chain_result.knockback_mult,
            chain_label=chain_result.label,
        )

    def _registrar_hit_match_stats(self, atacante, defensor, dano, arma, is_critico, fatal=False):
        if not hasattr(self, 'stats_collector'):
            return

        self.stats_collector.record_hit(
            atacante.dados.nome, defensor.dados.nome, dano,
            critico=is_critico,
            elemento=getattr(arma, 'elemento', '') if arma else '',
            source_type="weapon",
            source_name=getattr(arma, 'nome', '') if arma else '',
        )
        if fatal:
            self.stats_collector.record_death(defensor.dados.nome, killer=atacante.dados.nome)

    def _reproduzir_audio_ataque(self, atacante, arma, dano, is_critico):
        if not self.audio:
            return

        tipo_ataque = arma.tipo if arma else "SOCO"
        listener_x = self.cam.x / PPM
        self.audio.play_attack(tipo_ataque, atacante.pos[0], listener_x, damage=dano, is_critical=is_critico)

    def _notificar_coreografia_hit(self, atacante, defensor, dano):
        choreographer = getattr(self, 'choreographer', None)
        if choreographer:
            choreographer.registrar_hit(atacante, defensor, dano)

    def _aplicar_feedback_visual_super_armor(self, vetor_impacto):
        self.textos.append(FloatingText(vetor_impacto.dx_px, vetor_impacto.dy_px - 60, "ARMOR!", (255, 200, 50), 22))
        for _ in range(8):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(3, 8)
            self.particulas.append(Particula(
                vetor_impacto.dx_px, vetor_impacto.dy_px, (255, 200, 100),
                math.cos(ang) * vel, math.sin(ang) * vel,
                random.randint(4, 8), 0.4
            ))

    def _processar_hit_game_feel(self, atacante, defensor, dano, tipo_golpe, is_critico, vetor_impacto):
        if not self.game_feel:
            return GameFeelHitResolution(dano=dano)

        progresso_anim = 0.0
        if hasattr(defensor, 'timer_animacao') and defensor.atacando:
            progresso_anim = 1.0 - (defensor.timer_animacao / 0.25)

        self.game_feel.verificar_super_armor(
            defensor,
            progresso_anim,
            getattr(defensor.brain, 'acao_atual', "")
        )

        resultado_hit = self.game_feel.processar_hit(
            atacante=atacante,
            alvo=defensor,
            dano=dano,
            posicao=(vetor_impacto.dx_px, vetor_impacto.dy_px),
            tipo_golpe=tipo_golpe,
            is_critico=is_critico,
            knockback=(vetor_impacto.vx / vetor_impacto.mag * 15, vetor_impacto.vy / vetor_impacto.mag * 15)
        )

        if resultado_hit["super_armor_ativa"]:
            self._aplicar_feedback_visual_super_armor(vetor_impacto)

        return GameFeelHitResolution(
            dano=resultado_hit["dano_final"],
            resultado_hit=resultado_hit,
        )

    def _aplicar_feedback_impacto_ataque(self, arma, chain_label, vetor_impacto):
        self.hit_sparks.append(HitSpark(vetor_impacto.dx_px, vetor_impacto.dy_px, AMARELO_FAISCA, vetor_impacto.direcao_impacto, 1.2))

        cor_arma = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else BRANCO
        self.impact_flashes.append(ImpactFlash(vetor_impacto.dx_px, vetor_impacto.dy_px, cor_arma, 1.0, "normal"))

        if chain_label:
            cor_chain = {
                "MOMENTUM!": (255, 180, 50),
                "CORTE!": (180, 40, 40),
                "STUN!": (100, 100, 255),
                "CRACK!": (255, 255, 100),
                "ORBITA!": (200, 100, 255),
                "PUXÃƒO!": (100, 255, 100),
            }.get(chain_label, (255, 255, 255))
            self.textos.append(FloatingText(
                vetor_impacto.dx_px, vetor_impacto.dy_px - 45, chain_label, cor_chain, 20
            ))

    def _calcular_knockback_ataque(self, atacante, defensor, dano, chain_kb_mult, resultado_hit, vetor_impacto):
        pos_impacto = vetor_impacto.posicao_mundo
        kb_x, kb_y = calcular_knockback_com_forca(atacante, defensor, vetor_impacto.direcao_impacto, dano)
        kb_x *= chain_kb_mult
        kb_y *= chain_kb_mult

        if resultado_hit and not resultado_hit["sofreu_stagger"]:
            kb_x *= 0.2
            kb_y *= 0.2

        return AttackKnockbackResolution(
            posicao_impacto=pos_impacto,
            kb_x=kb_x,
            kb_y=kb_y,
        )

    def _aplicar_feedback_attack_animation(self, atacante, defensor, dano, is_critico, pos_impacto, vetor_impacto):
        attack_anims = getattr(self, 'attack_anims', None)
        if not attack_anims:
            return

        impact_result = attack_anims.criar_attack_impact(
            atacante=atacante,
            alvo=defensor,
            dano=dano,
            posicao=pos_impacto,
            direcao=vetor_impacto.direcao_impacto,
            tipo_dano="physical",
            is_critico=is_critico
        )

        if not self.game_feel:
            self.cam.aplicar_shake(impact_result['shake_intensity'], impact_result['shake_duration'])
            if impact_result['zoom_punch'] > 0:
                self.cam.zoom_punch(impact_result['zoom_punch'], 0.15)

    def _finalizar_hit_fatal(self, atacante, defensor, arma, dano, is_critico, vetor_impacto):
        self._registrar_hit_match_stats(atacante, defensor, dano, arma, is_critico, fatal=True)

        if hasattr(atacante, 'aplicar_passiva_em_hit'):
            atacante.aplicar_passiva_em_hit(dano, defensor)

        if self.audio:
            self.audio.play_special("ko", volume=1.0)

        self.spawn_particulas(
            defensor.pos[0],
            defensor.pos[1],
            vetor_impacto.vx / vetor_impacto.mag,
            vetor_impacto.vy / vetor_impacto.mag,
            VERMELHO_SANGUE,
            50,
        )
        self._criar_knockback_visual(defensor, vetor_impacto.direcao_impacto, dano * 1.5)

        if not self.game_feel:
            self.cam.aplicar_shake(18.0, 0.3)
            self.cam.zoom_punch(0.15, 0.15)
            self.hit_stop_timer = 0.25
        else:
            self.cam.zoom_punch(0.18, 0.18)

        self.shockwaves.append(Shockwave(vetor_impacto.dx_px, vetor_impacto.dy_px, VERMELHO_SANGUE, 2.0))
        self.textos.append(FloatingText(vetor_impacto.dx_px, vetor_impacto.dy_px - 50, "FATAL!", VERMELHO_SANGUE, 45))
        self.ativar_slow_motion()
        self.vencedor = atacante.dados.nome
        return True

    def _finalizar_hit_normal(self, atacante, defensor, arma, dano, is_critico, forca_atacante, resultado_hit, vetor_impacto):
        self._registrar_hit_match_stats(atacante, defensor, dano, arma, is_critico)

        if self.audio:
            listener_x = self.cam.x / PPM
            is_counter = resultado_hit and resultado_hit.get("counter_hit", False)
            self.audio.play_impact(dano, defensor.pos[0], listener_x, is_critico, is_counter)

        if dano > 8 or forca_atacante > 12:
            self._criar_knockback_visual(defensor, vetor_impacto.direcao_impacto, dano)

        qtd_part = max(5, min(25, int(dano / 3)))
        self.spawn_particulas(
            defensor.pos[0],
            defensor.pos[1],
            vetor_impacto.vx / vetor_impacto.mag,
            vetor_impacto.vy / vetor_impacto.mag,
            VERMELHO_SANGUE,
            qtd_part,
        )

        if not self.game_feel:
            if dano > 8:
                shake_intensity = min(12.0, 2.0 + dano * 0.15)
                self.cam.aplicar_shake(shake_intensity, 0.08)
            self.hit_stop_timer = min(0.08, 0.015 + dano * 0.001)
            if dano > 25:
                self.cam.zoom_punch(0.05, 0.08)

        tier = get_impact_tier(forca_atacante)
        if dano > 10 or forca_atacante >= 14:
            self.shockwaves.append(Shockwave(vetor_impacto.dx_px, vetor_impacto.dy_px, BRANCO, 0.6 * tier['shockwave_size']))

        if is_critico:
            cor_txt = (255, 50, 50)
            tamanho_txt = 32
            self.textos.append(FloatingText(vetor_impacto.dx_px, vetor_impacto.dy_px - 50, "CRÃTICO!", (255, 200, 0), 24))
        elif dano > 25:
            cor_txt = (255, 100, 100)
            tamanho_txt = 28
        elif dano > 15:
            cor_txt = (255, 200, 100)
            tamanho_txt = 24
        else:
            cor_txt = BRANCO
            tamanho_txt = 20

        self.textos.append(FloatingText(vetor_impacto.dx_px, vetor_impacto.dy_px - 30, int(dano), cor_txt, tamanho_txt))
        return False

    def _obter_lutadores_combate(self):
        fighters = getattr(self, 'fighters', None)
        if fighters is not None:
            return fighters
        return [self.p1, self.p2]

    def _obter_lutadores_vivos_para_fisica(self):
        return [f for f in self._obter_lutadores_combate() if not f.morto]

    def _obter_tipo_arma(self, lutador):
        arma = getattr(getattr(lutador, 'dados', None), 'arma_obj', None)
        return getattr(arma, 'tipo', '') or ''

    def _arma_eh_tipo(self, lutador, marcador):
        return marcador in self._obter_tipo_arma(lutador)

    def _iterar_pares_lutadores(self, fighters):
        for i in range(len(fighters)):
            for j in range(i + 1, len(fighters)):
                yield fighters[i], fighters[j]

    def _iterar_ataques_validos(self, fighters):
        for atacante in fighters:
            if atacante.morto or not atacante.atacando:
                continue
            for defensor in fighters:
                if defensor is atacante or defensor.morto:
                    continue
                yield atacante, defensor

    def _processar_clashes_combate(self, fighters):
        for a, b in self._iterar_pares_lutadores(fighters):
            if a.morto or b.morto:
                continue
            if not a.dados.arma_obj or not b.dados.arma_obj:
                continue
            if self.checar_clash_geral(a, b):
                self.efeito_clash(a, b)

    def _finalizar_morte_em_colisoes(self, atacante, defensor):
        self.ativar_slow_motion()
        self.vencedor = self._determinar_vencedor_por_morte(defensor) if hasattr(self, '_determinar_vencedor_por_morte') else atacante.dados.nome

    def _processar_ataques_combate(self, fighters):
        for atacante, defensor in self._iterar_ataques_validos(fighters):
            morreu = self.checar_ataque(atacante, defensor)
            if morreu:
                self._finalizar_morte_em_colisoes(atacante, defensor)

    def _checar_clash_duas_retas(self, p1, p2):
        l1 = p1.get_pos_ponteira_arma()
        l2 = p2.get_pos_ponteira_arma()
        if not l1 or not l2:
            return False
        return colisao_linha_linha(l1[0], l1[1], l2[0], l2[1])

    def _criar_contexto_visual_clash(self, p1, p2):
        mx = (p1.pos[0] + p2.pos[0]) / 2 * PPM
        my = (p1.pos[1] + p2.pos[1]) / 2 * PPM
        arma1 = getattr(getattr(p1, 'dados', None), 'arma_obj', None)
        arma2 = getattr(getattr(p2, 'dados', None), 'arma_obj', None)
        cor1 = (arma1.r, arma1.g, arma1.b) if arma1 and hasattr(arma1, 'r') else (255, 255, 255)
        cor2 = (arma2.r, arma2.g, arma2.b) if arma2 and hasattr(arma2, 'r') else (255, 255, 255)
        ang_p1_p2 = math.atan2(p2.pos[1] - p1.pos[1], p2.pos[0] - p1.pos[0])
        vec_x = p1.pos[0] - p2.pos[0]
        vec_y = p1.pos[1] - p2.pos[1]
        mag = math.hypot(vec_x, vec_y) or 1
        return ClashVisualContext(
            mx=mx,
            my=my,
            cor1=cor1,
            cor2=cor2,
            ang_p1_p2=ang_p1_p2,
            vec_x=vec_x,
            vec_y=vec_y,
            mag=mag,
        )

    def _emitir_particulas_clash(self, contexto):
        _slots = max(0, 600 - len(self.particulas))
        _n_clash = min(BUDGET_PARTICULAS_CLASH, _slots)
        for _ in range(_n_clash):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(80, 180)
            vx = math.cos(ang) * vel / 60
            vy = math.sin(ang) * vel / 60
            self.particulas.append(Particula(contexto.mx, contexto.my, AMARELO_FAISCA, vx, vy, random.randint(3, 7), 0.5))

    def _aplicar_vfx_clash(self, contexto):
        self.magic_clashes.append(MagicClash(contexto.mx, contexto.my, contexto.cor1, contexto.cor2, tamanho=1.2))
        self.impact_flashes.append(ImpactFlash(contexto.mx, contexto.my, AMARELO_FAISCA, 1.5, "clash"))
        self.hit_sparks.append(HitSpark(contexto.mx, contexto.my, contexto.cor1, contexto.ang_p1_p2, 1.5))
        self.hit_sparks.append(HitSpark(contexto.mx, contexto.my, contexto.cor2, contexto.ang_p1_p2 + math.pi, 1.5))
        self.shockwaves.append(Shockwave(contexto.mx, contexto.my, BRANCO, 1.5))
        self.textos.append(FloatingText(contexto.mx, contexto.my - 60, "CLASH!", AMARELO_FAISCA, 38))

    def _aplicar_empurrao_clash(self, p1, p2, contexto):
        p1.tomar_clash(contexto.vec_x / contexto.mag, contexto.vec_y / contexto.mag)
        p2.tomar_clash(-contexto.vec_x / contexto.mag, -contexto.vec_y / contexto.mag)

    def _aplicar_feedback_camera_audio_clash(self, contexto):
        self.cam.aplicar_shake(14.0, 0.15)
        self.cam.zoom_punch(0.08, 0.1)
        self.hit_stop_timer = 0.12

        audio = getattr(self, 'audio', None)
        if audio:
            p1 = getattr(self, 'p1', None)
            p2 = getattr(self, 'p2', None)
            listener_x = (p1.pos[0] + p2.pos[0]) / 2 if p1 and p2 else (contexto.mx / PPM)
            audio.play_positional("clash_swords", contexto.mx / PPM, listener_x, volume=1.0)

    def checar_ataque(self, atacante, defensor):
        """
        Verifica ataque usando o novo sistema de hitbox com debug.
        
        === INTEGRAÃ‡ÃƒO GAME FEEL v8.0 ===
        - Hit Stop proporcional Ã  classe (ForÃ§a > Ãgil)
        - Super Armor para tanks/berserkers
        - Camera shake baseado em INTENSIDADE, nÃ£o velocidade
        
        === v10.1: PREVENÃ‡ÃƒO DE MULTI-HIT ===
        - Cada ataque sÃ³ pode acertar cada alvo UMA vez
        - Evita o bug de mÃºltiplos hits durante um Ãºnico swing
        """
        
        ataque = self._preparar_contexto_ataque_melee(atacante, defensor)
        if not ataque:
            return False

        arma = ataque.arma
        vetor_impacto = ataque.vetor_impacto
        dano = ataque.dano
        is_critico = ataque.is_critico

        self._reproduzir_audio_ataque(atacante, arma, dano, is_critico)
        self._notificar_coreografia_hit(atacante, defensor, dano)

        tipo_golpe = self._determinar_tipo_golpe(atacante, dano, is_critico)

        game_feel_resolution = self._processar_hit_game_feel(
            atacante,
            defensor,
            dano,
            tipo_golpe,
            is_critico,
            vetor_impacto,
        )
        dano = game_feel_resolution.dano
        resultado_hit = game_feel_resolution.resultado_hit

        forca_atacante = atacante.dados.forca
        self._aplicar_feedback_impacto_ataque(arma, ataque.chain_label, vetor_impacto)

        knockback = self._calcular_knockback_ataque(
            atacante,
            defensor,
            dano,
            ataque.chain_kb_mult,
            resultado_hit,
            vetor_impacto,
        )
        self._aplicar_feedback_attack_animation(
            atacante,
            defensor,
            dano,
            is_critico,
            knockback.posicao_impacto,
            vetor_impacto,
        )

        if defensor.tomar_dano(dano, knockback.kb_x, knockback.kb_y, "NORMAL", atacante=atacante):
            return self._finalizar_hit_fatal(atacante, defensor, arma, dano, is_critico, vetor_impacto)

        return self._finalizar_hit_normal(
            atacante,
            defensor,
            arma,
            dano,
            is_critico,
            forca_atacante,
            resultado_hit,
            vetor_impacto,
        )


    def verificar_colisoes_combate(self):
        """v13.0: Verifica colisÃµes de combate entre TODOS os pares de lutadores.
        
        Friendly fire ON: Ataques afetam qualquer lutador, incluindo aliados.
        """
        fighters = self._obter_lutadores_combate()
        self._processar_clashes_combate(fighters)
        self._processar_ataques_combate(fighters)

    def _criar_contexto_colisao_corpos(self, p1, p2):
        dx = p2.pos[0] - p1.pos[0]
        dy = p2.pos[1] - p1.pos[1]
        soma_raios = p1.raio_fisico + p2.raio_fisico
        dist2 = dx * dx + dy * dy
        soma2 = soma_raios * soma_raios
        if dist2 >= soma2 or abs(p1.z - p2.z) >= 1.0:
            return None

        dist = math.sqrt(dist2)
        if dist > 0.001:
            nx, ny = dx / dist, dy / dist
        else:
            ang = random.uniform(0, math.pi * 2)
            nx, ny = math.cos(ang), math.sin(ang)

        return BodyCollisionContext(
            p1=p1,
            p2=p2,
            dist=dist,
            nx=nx,
            ny=ny,
            soma_raios=soma_raios,
        )

    def _aplicar_separacao_corpos(self, contexto):
        penetracao = contexto.soma_raios - contexto.dist
        separacao = (penetracao / 2.0) + 0.02
        contexto.p1.pos[0] -= contexto.nx * separacao
        contexto.p1.pos[1] -= contexto.ny * separacao
        contexto.p2.pos[0] += contexto.nx * separacao
        contexto.p2.pos[1] += contexto.ny * separacao

    def _aplicar_repulsao_corpos(self, contexto, fator_repulsao):
        if contexto.dist >= contexto.soma_raios * 1.2:
            return

        contexto.p1.vel[0] -= contexto.nx * fator_repulsao
        contexto.p1.vel[1] -= contexto.ny * fator_repulsao
        contexto.p2.vel[0] += contexto.nx * fator_repulsao
        contexto.p2.vel[1] += contexto.ny * fator_repulsao

    def _resolver_iteracao_fisica_corpos(self, vivos, fator_repulsao):
        houve_colisao = False

        for p1, p2 in self._iterar_pares_lutadores(vivos):
            contexto = self._criar_contexto_colisao_corpos(p1, p2)
            if not contexto:
                continue

            houve_colisao = True
            self._aplicar_separacao_corpos(contexto)
            self._aplicar_repulsao_corpos(contexto, fator_repulsao)

        return houve_colisao


    def resolver_fisica_corpos(self, dt):
        """
        A03: Resolve colisÃ£o fÃ­sica entre TODOS os pares de lutadores.

        OtimizaÃ§Ãµes em relaÃ§Ã£o Ã  versÃ£o original:
        - SeparaÃ§Ã£o + repulsÃ£o fundidos em um Ãºnico loop O(nÂ²) por iteraÃ§Ã£o
          (era O(nÂ²)Ã—3 separaÃ§Ã£o + O(nÂ²) repulsÃ£o = 4 passes; agora 3 passes)
        - Early-exit: se nenhum par colidiu na iteraÃ§Ã£o i, para antes de chegar em 3
        - distÂ² usado para check inicial (sem sqrt para pares claramente separados)
        """
        vivos = self._obter_lutadores_vivos_para_fisica()

        if len(vivos) < 2:
            return

        fator_repulsao = 6.0

        for _ in range(3):
            if not self._resolver_iteracao_fisica_corpos(vivos, fator_repulsao):
                break


    def checar_clash_geral(self, p1, p2):
        # BUG-F2: Guarda contra arma_obj = None
        if not p1.dados.arma_obj or not p2.dados.arma_obj:
            return False

        if self._arma_eh_tipo(p1, "Reta") and self._arma_eh_tipo(p2, "Reta"):
            return self._checar_clash_duas_retas(p1, p2)
        if self._arma_eh_tipo(p1, "Reta") and self._arma_eh_tipo(p2, "Orbital"):
            return self.checar_clash_espada_escudo(p1, p2)
        if self._arma_eh_tipo(p1, "Orbital") and self._arma_eh_tipo(p2, "Reta"):
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
        """Efeito visual dramÃ¡tico quando armas colidem"""
        contexto = self._criar_contexto_visual_clash(p1, p2)
        self._emitir_particulas_clash(contexto)
        self._aplicar_vfx_clash(contexto)
        self._aplicar_empurrao_clash(p1, p2, contexto)
        self._aplicar_feedback_camera_audio_clash(contexto)

    def _desativar_projeteis_clash_magico(self, proj1, proj2):
        proj1.ativo = False
        proj2.ativo = False

    def _criar_contexto_clash_magico(self, proj1, proj2):
        mx = (proj1.x + proj2.x) / 2
        my = (proj1.y + proj2.y) / 2
        cor1 = getattr(proj1, 'cor', (255, 100, 100))
        cor2 = getattr(proj2, 'cor', (100, 100, 255))
        return MagicProjectileClashContext(
            mx=mx,
            my=my,
            mx_px=mx * PPM,
            my_px=my * PPM,
            cor1=cor1,
            cor2=cor2,
        )

    def _aplicar_vfx_clash_magico(self, contexto):
        self.magic_clashes.append(MagicClash(contexto.mx_px, contexto.my_px, contexto.cor1, contexto.cor2, tamanho=1.5))
        self.impact_flashes.append(ImpactFlash(contexto.mx_px, contexto.my_px, contexto.cor1, 1.5, "clash"))
        self.shockwaves.append(Shockwave(contexto.mx_px, contexto.my_px, BRANCO, tamanho=2.0))
        self.textos.append(FloatingText(contexto.mx_px, contexto.my_px - 40, "CLASH!", AMARELO_FAISCA, 35))

    def _aplicar_feedback_camera_audio_clash_magico(self, contexto):
        audio = getattr(self, 'audio', None)
        if audio:
            p1 = getattr(self, 'p1', None)
            p2 = getattr(self, 'p2', None)
            listener_x = (p1.pos[0] + p2.pos[0]) / 2 if p1 and p2 else contexto.mx
            audio.play_positional("clash_magic", contexto.mx, listener_x, volume=1.0)

        self.cam.aplicar_shake(25.0, 0.25)
        self.hit_stop_timer = 0.15

    def _emitir_particulas_clash_magico(self, contexto):
        _slots = max(0, 600 - len(self.particulas))
        _n_magico = min(BUDGET_PARTICULAS_CLASH_MAGICO, _slots)
        for _ in range(_n_magico):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(80, 200)
            cor = random.choice([contexto.cor1, contexto.cor2])
            self.particulas.append(Particula(
                contexto.mx_px, contexto.my_px, cor,
                math.cos(ang) * vel / 60, math.sin(ang) * vel / 60,
                random.randint(4, 8), 0.4
            ))

    
    def _executar_clash_magico(self, proj1, proj2):
        """Executa efeito de clash entre dois projÃ©teis/magias"""
        self._desativar_projeteis_clash_magico(proj1, proj2)
        contexto = self._criar_contexto_clash_magico(proj1, proj2)
        self._aplicar_vfx_clash_magico(contexto)
        self._aplicar_feedback_camera_audio_clash_magico(contexto)
        self._emitir_particulas_clash_magico(contexto)

    def _cancelar_estado_sword_clash(self, p1, p2):
        p1.atacando = False
        p2.atacando = False
        p1.timer_animacao = 0
        p2.timer_animacao = 0
        p1.cooldown_ataque = 0.3
        p2.cooldown_ataque = 0.3
        p1.alvos_atingidos_neste_ataque.clear()
        p2.alvos_atingidos_neste_ataque.clear()

    def _criar_contexto_sword_clash(self, p1, p2):
        mx = (p1.pos[0] + p2.pos[0]) / 2
        my = (p1.pos[1] + p2.pos[1]) / 2
        cor1 = p1.dados.cor if hasattr(p1, 'dados') and hasattr(p1.dados, 'cor') else (255, 180, 80)
        cor2 = p2.dados.cor if hasattr(p2, 'dados') and hasattr(p2.dados, 'cor') else (80, 180, 255)
        textos_clash = ["CLASH!", "CLANG!", "STEEL!", "IMPACTO!"]
        return SwordClashContext(
            mx=mx,
            my=my,
            mx_px=mx * PPM,
            my_px=my * PPM,
            cor1=cor1,
            cor2=cor2,
            texto=random.choice(textos_clash),
        )

    def _aplicar_vfx_sword_clash(self, contexto):
        self.impact_flashes.append(ImpactFlash(contexto.mx_px, contexto.my_px, AMARELO_FAISCA, 2.0, "clash"))
        self.shockwaves.append(Shockwave(contexto.mx_px, contexto.my_px, BRANCO, tamanho=2.5))
        self.textos.append(FloatingText(contexto.mx_px, contexto.my_px - 50, contexto.texto, AMARELO_FAISCA, 40))

    def _aplicar_feedback_camera_audio_sword_clash(self, contexto):
        audio = getattr(self, 'audio', None)
        p1 = getattr(self, 'p1', None)
        p2 = getattr(self, 'p2', None)
        if audio and p1 and p2:
            listener_x = (p1.pos[0] + p2.pos[0]) / 2
            audio.play_positional("clash_swords", contexto.mx, listener_x, volume=1.0)

        self.cam.aplicar_shake(12.0, 0.15)
        self.hit_stop_timer = 0.12

    def _emitir_particulas_sword_clash(self, contexto):
        for _ in range(40):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(100, 250)
            cor = random.choice([AMARELO_FAISCA, BRANCO, contexto.cor1, contexto.cor2, (255, 200, 100)])
            self.particulas.append(Particula(
                contexto.mx_px, contexto.my_px, cor,
                math.cos(ang) * vel / 60, math.sin(ang) * vel / 60,
                random.randint(3, 7), random.uniform(0.3, 0.6)
            ))

    def _aplicar_hit_spark_sword_clash(self, contexto):
        direcao_faiscas = random.uniform(0, math.pi * 2)
        self.hit_sparks.append(HitSpark(contexto.mx_px, contexto.my_px, AMARELO_FAISCA, direcao_faiscas, 1.5))

    
    def _executar_sword_clash(self):
        """Executa efeito de clash de espadas entre dois lutadores (momento cinematogrÃ¡fico)"""
        if not self.p1 or not self.p2:
            return

        self._cancelar_estado_sword_clash(self.p1, self.p2)
        contexto = self._criar_contexto_sword_clash(self.p1, self.p2)
        self._aplicar_vfx_sword_clash(contexto)
        self._aplicar_feedback_camera_audio_sword_clash(contexto)
        self._emitir_particulas_sword_clash(contexto)
        self._aplicar_hit_spark_sword_clash(contexto)

        _log.debug(f"[SWORD CLASH] Ã‰pico clash de espadas em ({contexto.mx:.1f}, {contexto.my:.1f})!")


    # =========================================================================
    # SISTEMA DE CLASH DE PROJÃ‰TEIS v7.0
    # =========================================================================

    def _coletar_projeteis_ativos_do_dono(self, dono):
        return [p for p in getattr(self, 'projeteis', []) if getattr(p, 'dono', None) == dono and getattr(p, 'ativo', True)]

    def _coletar_orbes_disparando(self, lutador):
        if not hasattr(lutador, 'buffer_orbes'):
            return []
        return [o for o in lutador.buffer_orbes if getattr(o, 'ativo', True) and getattr(o, 'estado', None) == "disparando"]

    def _coletar_fontes_clash_projeteis(self, lutador):
        return self._coletar_projeteis_ativos_do_dono(lutador) + self._coletar_orbes_disparando(lutador)

    def _projeteis_ativos_para_clash(self, proj1, proj2):
        return getattr(proj1, 'ativo', True) and getattr(proj2, 'ativo', True)

    def _criar_contexto_clash_projeteis(self, proj1, proj2):
        dx = proj1.x - proj2.x
        dy = proj1.y - proj2.y
        dist = math.hypot(dx, dy)
        r1 = getattr(proj1, 'raio', 0.2)
        r2 = getattr(proj2, 'raio', 0.2)
        return ProjectileClashContext(
            proj1=proj1,
            proj2=proj2,
            dist=dist,
            raio_colisao=r1 + r2 + 0.3,
        )

    def _projeteis_colidem_para_clash(self, contexto):
        return contexto.dist < contexto.raio_colisao

    def _processar_clash_projeteis_entre_grupos(self, grupo1, grupo2):
        for proj1 in grupo1:
            for proj2 in grupo2:
                if not self._projeteis_ativos_para_clash(proj1, proj2):
                    continue

                contexto = self._criar_contexto_clash_projeteis(proj1, proj2)
                if self._projeteis_colidem_para_clash(contexto):
                    self._executar_clash_magico(contexto.proj1, contexto.proj2)
    
    def _verificar_clash_projeteis(self):
        """Verifica colisÃ£o entre projÃ©teis de diferentes donos"""
        p1 = getattr(self, 'p1', None)
        p2 = getattr(self, 'p2', None)
        if not p1 or not p2:
            return

        grupo_p1 = self._coletar_fontes_clash_projeteis(p1)
        grupo_p2 = self._coletar_fontes_clash_projeteis(p2)
        self._processar_clash_projeteis_entre_grupos(grupo_p1, grupo_p2)

    
    # =========================================================================
    # SISTEMA DE BLOQUEIO E DESVIO v7.0
    # =========================================================================
    
    def _verificar_bloqueio_projetil(self, proj, alvo):
        """Verifica se o alvo pode bloquear ou desviar do projÃ©til"""
        if not proj.ativo:
            return False

        dist = self._calcular_distancia_projetil_alvo(proj, alvo)
        if not self._projetil_esta_perto_para_defesa(dist, alvo):
            return False

        pos_escudo = self._detectar_bloqueio_escudo_orbital(proj, alvo)
        if pos_escudo:
            self._efeito_bloqueio(proj, alvo, pos_escudo)
            return True

        if self._detectar_desvio_dash(proj, alvo, dist):
            self._efeito_desvio_dash(proj, alvo)
            choreographer = getattr(self, 'choreographer', None)
            if choreographer:
                choreographer.registrar_esquiva(alvo, proj.dono if hasattr(proj, 'dono') else None)
            return True

        if self._detectar_parry_projetil(proj, alvo):
            self._efeito_parry(proj, alvo)
            return True
        
        return False

    def _calcular_distancia_projetil_alvo(self, proj, alvo):
        dx = alvo.pos[0] - proj.x
        dy = alvo.pos[1] - proj.y
        return math.hypot(dx, dy)

    def _projetil_esta_perto_para_defesa(self, dist, alvo):
        return dist <= alvo.raio_fisico + 1.5

    def _detectar_bloqueio_escudo_orbital(self, proj, alvo):
        if not alvo.dados.arma_obj or "Orbital" not in alvo.dados.arma_obj.tipo:
            return None

        escudo_info = alvo.get_escudo_info()
        if not escudo_info:
            return None

        escudo_pos, escudo_raio, escudo_ang, escudo_arco = escudo_info
        dx_escudo = proj.x * PPM - escudo_pos[0]
        dy_escudo = proj.y * PPM - escudo_pos[1]
        dist_escudo = math.hypot(dx_escudo, dy_escudo)
        if dist_escudo >= escudo_raio + proj.raio * PPM:
            return None

        ang_proj = math.degrees(math.atan2(dy_escudo, dx_escudo))
        diff_ang = abs(normalizar_angulo(ang_proj - escudo_ang))
        if diff_ang <= escudo_arco / 2:
            return escudo_pos
        return None

    def _detectar_desvio_dash(self, proj, alvo, dist):
        return hasattr(alvo, 'dash_timer') and alvo.dash_timer > 0 and dist < alvo.raio_fisico + 0.5

    def _detectar_parry_projetil(self, proj, alvo):
        if not alvo.atacando or alvo.timer_animacao <= 0.15:
            return False
        if not alvo.dados.arma_obj or "Reta" not in alvo.dados.arma_obj.tipo:
            return False

        linha_arma = alvo.get_pos_ponteira_arma()
        if not linha_arma:
            return False

        return colisao_linha_circulo(
            linha_arma[0],
            linha_arma[1],
            (proj.x * PPM, proj.y * PPM),
            proj.raio * PPM + 5,
        )

    
    def _efeito_bloqueio(self, proj, bloqueador, pos_escudo):
        """Efeito visual de bloqueio"""
        self._registrar_bloco_defensivo(bloqueador)
        self._reproduzir_audio_bloqueio()
        contexto = self._criar_contexto_visual_bloqueio(proj, bloqueador, pos_escudo)
        self.block_effects.append(BlockEffect(contexto.proj_x_px, contexto.proj_y_px, contexto.cor_lutador, contexto.ang_impacto))
        self._adicionar_texto_feedback_defensivo(contexto.proj_x_px, contexto.proj_y_px, "BLOCK!", (100, 200, 255), 22, -30)
        self._emitir_particulas_bloqueio(contexto)
        self._aplicar_feedback_temporal_defensivo(DefensiveTempoFeedback(
            shake_intensity=5.0,
            shake_duration=0.06,
            hit_stop=0.03,
        ))

    
    def _efeito_desvio_dash(self, proj, desviador):
        """Efeito visual de desvio com dash"""
        self._registrar_esquiva_stats(desviador)
        contexto = self._criar_contexto_visual_desvio_dash(desviador)
        self._aplicar_trail_desvio_dash(contexto)
        self._aplicar_feedback_desvio_dash(contexto)

    
    def _efeito_parry(self, proj, parryer):
        """Efeito visual de parry (defesa com ataque)"""
        self._registrar_bloco_defensivo(parryer)
        contexto = self._criar_contexto_visual_parry(proj, parryer)
        self.impact_flashes.append(ImpactFlash(contexto.proj_x_px, contexto.proj_y_px, AMARELO_FAISCA, 1.8, "clash"))
        self._adicionar_texto_feedback_defensivo(contexto.proj_x_px, contexto.proj_y_px, "PARRY!", AMARELO_FAISCA, 28, -40)
        self.shockwaves.append(Shockwave(contexto.proj_x_px, contexto.proj_y_px, AMARELO_FAISCA, tamanho=1.5))
        self.hit_sparks.append(HitSpark(contexto.proj_x_px, contexto.proj_y_px, AMARELO_FAISCA, contexto.ang_impacto, 1.5))
        self._aplicar_feedback_temporal_defensivo(DefensiveTempoFeedback(
            shake_intensity=8.0,
            shake_duration=0.1,
            hit_stop=0.06,
            time_scale=0.4,
            slow_mo_timer=0.25,
        ))

    def _registrar_bloco_defensivo(self, lutador):
        if hasattr(self, 'stats_collector'):
            self.stats_collector.record_block(lutador.dados.nome)

        brain = getattr(lutador, 'brain', None)
        if brain and hasattr(brain, 'on_bloqueio_sucesso'):
            brain.on_bloqueio_sucesso()

    def _reproduzir_audio_bloqueio(self):
        audio = getattr(self, 'audio', None)
        if audio:
            audio.play_special("shield_block", volume=0.7)

    def _obter_cor_lutador_rgb(self, lutador):
        return (lutador.dados.cor_r, lutador.dados.cor_g, lutador.dados.cor_b)

    def _criar_contexto_visual_bloqueio(self, proj, bloqueador, pos_escudo):
        return ProjectileDefenseVisualContext(
            proj_x_px=proj.x * PPM,
            proj_y_px=proj.y * PPM,
            cor_lutador=self._obter_cor_lutador_rgb(bloqueador),
            ang_impacto=math.atan2(proj.y * PPM - pos_escudo[1], proj.x * PPM - pos_escudo[0]),
        )

    def _criar_contexto_visual_parry(self, proj, parryer):
        return ProjectileDefenseVisualContext(
            proj_x_px=proj.x * PPM,
            proj_y_px=proj.y * PPM,
            cor_lutador=self._obter_cor_lutador_rgb(parryer),
            ang_impacto=math.atan2(proj.y - parryer.pos[1], proj.x - parryer.pos[0]),
        )

    def _emitir_particulas_bloqueio(self, contexto):
        for _ in range(12):
            vx = math.cos(contexto.ang_impacto + random.uniform(-0.5, 0.5)) * random.uniform(3, 8)
            vy = math.sin(contexto.ang_impacto + random.uniform(-0.5, 0.5)) * random.uniform(3, 8)
            self.particulas.append(Particula(contexto.proj_x_px, contexto.proj_y_px, AMARELO_FAISCA, vx, vy, 3, 0.3))

    def _registrar_esquiva_stats(self, desviador):
        if hasattr(self, 'stats_collector'):
            self.stats_collector.record_dodge(desviador.dados.nome)

    def _criar_contexto_visual_desvio_dash(self, desviador):
        trilha_posicoes = []
        if hasattr(desviador, 'pos_historico') and len(desviador.pos_historico) > 2:
            trilha_posicoes = [(p[0] * PPM, p[1] * PPM) for p in desviador.pos_historico[-8:]]

        return DashDodgeVisualContext(
            pos_x_px=desviador.pos[0] * PPM,
            pos_y_px=desviador.pos[1] * PPM,
            cor_lutador=self._obter_cor_lutador_rgb(desviador),
            trilha_posicoes=trilha_posicoes,
        )

    def _aplicar_trail_desvio_dash(self, contexto):
        if contexto.trilha_posicoes:
            self.dash_trails.append(DashTrail(contexto.trilha_posicoes, contexto.cor_lutador))

    def _aplicar_feedback_desvio_dash(self, contexto):
        self._adicionar_texto_feedback_defensivo(contexto.pos_x_px, contexto.pos_y_px, "DODGE!", (150, 255, 150), 24, -50)
        self._aplicar_feedback_temporal_defensivo(DefensiveTempoFeedback(
            time_scale=0.5,
            slow_mo_timer=0.3,
        ))

    def _adicionar_texto_feedback_defensivo(self, x_px, y_px, texto, cor, tamanho, offset_y):
        self.textos.append(FloatingText(x_px, y_px + offset_y, texto, cor, tamanho))

    def _aplicar_feedback_temporal_defensivo(self, contexto):
        if contexto.shake_intensity > 0 and contexto.shake_duration > 0:
            self.cam.aplicar_shake(contexto.shake_intensity, contexto.shake_duration)
        if contexto.hit_stop > 0:
            self.hit_stop_timer = contexto.hit_stop
        if contexto.time_scale is not None:
            self.time_scale = contexto.time_scale
            self.slow_mo_timer = contexto.slow_mo_timer


