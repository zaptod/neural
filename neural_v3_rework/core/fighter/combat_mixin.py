"""
NEURAL FIGHTS — core/fighter/combat_mixin.py  [D03/D04 Sprint 8]
=================================================================
CombatMixin: dano, status effects, buffs/DoTs, morte.

Contém também StatusSnapshot (movida de entities.py para aqui para
quebrar a dependência de importação circular).

Imports inline eliminados (D04): DotEffect, ENCANTAMENTOS e todos os
helpers de balance_config ficam no topo do módulo.
"""

import math
import random
import logging

from utils.config import PPM
from utils.balance_config import (
    CRITICO_CHANCE_BONUS_RAGE, CRITICO_MULT_BASE,
    DANO_MULT_FLANQUEAR, DANO_MULT_COSTAS, DANO_MULT_AERIAL, DANO_MULT_EXECUCAO,
    DANO_ECO_RATIO, SLOW_FATOR_DEFAULT, SLOW_DURACAO_DEFAULT,
)
from core.combat import DotEffect
from models import ENCANTAMENTOS

_log = logging.getLogger("entities")


# ---------------------------------------------------------------------------
# A05: classe leve que substitui os objetos anônimos criados via type()
# ---------------------------------------------------------------------------
class StatusSnapshot:
    """Snapshot imutável de um status effect para leitura pela IA e magic_system."""
    __slots__ = (
        'nome', 'mod_velocidade', 'mod_dano_causado',
        'mod_dano_recebido', 'pode_mover', 'pode_atacar',
        'pode_usar_skill', 'dano_por_tick',
    )

    def __init__(self, nome, mod_velocidade=1.0, mod_dano_causado=1.0,
                 mod_dano_recebido=1.0, pode_mover=True, pode_atacar=True,
                 pode_usar_skill=True, dano_por_tick=0):
        self.nome              = nome
        self.mod_velocidade    = mod_velocidade
        self.mod_dano_causado  = mod_dano_causado
        self.mod_dano_recebido = mod_dano_recebido
        self.pode_mover        = pode_mover
        self.pode_atacar       = pode_atacar
        self.pode_usar_skill   = pode_usar_skill
        self.dano_por_tick     = dano_por_tick


# ---------------------------------------------------------------------------
# CombatMixin
# ---------------------------------------------------------------------------
class CombatMixin:
    """Mixin com toda a lógica de combate de Lutador."""

    # ------------------------------------------------------------------
    # Cálculo de dano
    # ------------------------------------------------------------------

    def calcular_dano_ataque(self, dano_base):
        """Calcula dano final com crítico, encantamentos e PASSIVA da arma."""
        dano = dano_base * self.mod_dano

        # FP-2: penalidade de FRACO
        if getattr(self, 'dano_reduzido', 1.0) != 1.0:
            dano *= self.dano_reduzido

        passiva = self.arma_passiva or {}

        if passiva.get("efeito") == "dano_bonus":
            dano *= 1.0 + passiva.get("valor", 0) / 100.0

        if passiva.get("efeito") == "berserk":
            if self.vida / max(self.vida_max, 1) < 0.30:
                dano *= 1.0 + passiva.get("valor", 0) / 100.0

        if passiva.get("efeito") == "all_stats":
            dano *= 1.0 + passiva.get("valor", 0) / 100.0

        critico_chance = self.arma_critico
        if "Assassino" in self.classe_nome:
            critico_chance += CRITICO_CHANCE_BONUS_RAGE
        if passiva.get("efeito") == "crit_chance":
            critico_chance += passiva.get("valor", 0) / 100.0

        is_critico = random.random() < critico_chance
        if is_critico:
            mult_critico = CRITICO_MULT_BASE
            if passiva.get("efeito") == "crit_damage":
                mult_critico += passiva.get("valor", 0) / 100.0
            dano *= mult_critico

        for enc_nome in self.arma_encantamentos:
            if enc_nome in ENCANTAMENTOS:
                dano += ENCANTAMENTOS[enc_nome].get("dano_bonus", 0)

        # v15.0 — Bônus por mecânica de arma
        tipo_arma = getattr(self.dados, 'tipo_arma', '')

        if tipo_arma == 'Dupla':
            if getattr(self, 'dual_cross_slash', False):
                dano *= DANO_MULT_FLANQUEAR
            elif getattr(self, 'dual_frenzy', False):
                dano *= DANO_MULT_COSTAS

        if tipo_arma == 'Reta':
            if getattr(self, 'reta_combo', 0) >= 2:
                dano *= DANO_MULT_AERIAL

        if tipo_arma == 'Transformável':
            if getattr(self, 'transform_bonus_timer', 0) > 0:
                dano *= DANO_MULT_EXECUCAO

        return dano, is_critico

    def aplicar_passiva_em_hit(self, dano_aplicado, alvo, pos_impacto_px=None):
        """
        Processa efeitos de passiva de arma disparados ao acertar um golpe.
        Retorna dict com flags para simulacao.py processar efeitos visuais.
        """
        passiva = self.arma_passiva or {}
        efeito = passiva.get("efeito")
        valor = passiva.get("valor", 0)
        resultado = {}

        if efeito == "lifesteal":
            cura = dano_aplicado * (valor / 100.0)
            self.vida = min(self.vida_max, self.vida + cura)
            resultado["lifesteal"] = cura

        if efeito == "execute":
            if alvo.vida / max(alvo.vida_max, 1) < (valor / 100.0):
                alvo.vida = 0
                alvo.morrer()
                resultado["execute"] = True

        if efeito == "double_hit" and random.random() < (valor / 100.0):
            if not alvo.morto:
                dano_eco = dano_aplicado * DANO_ECO_RATIO
                alvo.vida = max(0, alvo.vida - dano_eco)
                resultado["double_hit"] = dano_eco

        if efeito == "aoe_damage":
            resultado["aoe_damage"] = {"dano": dano_aplicado * (valor / 100.0),
                                       "x": alvo.pos[0], "y": alvo.pos[1]}

        if efeito == "teleport" and random.random() < (valor / 100.0):
            ang = math.atan2(alvo.pos[1] - self.pos[1], alvo.pos[0] - self.pos[0])
            self.pos[0] = alvo.pos[0] - math.cos(ang) * 1.2
            self.pos[1] = alvo.pos[1] - math.sin(ang) * 1.2
            resultado["teleport"] = True

        if efeito == "random_element":
            elemento = random.choice(["QUEIMANDO", "ENVENENADO", "CONGELADO", "PARALISIA"])
            cores = {"QUEIMANDO": (255, 100, 0), "ENVENENADO": (100, 255, 100),
                     "CONGELADO": (150, 220, 255), "PARALISIA": (255, 255, 100)}
            dot = DotEffect(elemento, alvo, dano_aplicado * 0.1, 3.0, cores.get(elemento, (255, 255, 255)))
            if not alvo.morto:
                alvo.dots_ativos.append(dot)
            resultado["random_element"] = elemento

        # v15.0 — Efeitos on-hit por tipo de arma
        tipo_arma = getattr(self.dados, 'tipo_arma', '')

        if tipo_arma == 'Dupla' and getattr(self, 'dual_combo', 0) >= 4:
            if not alvo.morto:
                bleed = DotEffect("Sangrando", alvo, dano_aplicado * 0.06, 2.5, (200, 30, 30))
                alvo.dots_ativos.append(bleed)
                resultado["dual_bleed"] = True

        if tipo_arma == 'Reta' and getattr(self, 'reta_combo', 0) >= 2:
            if not alvo.morto:
                alvo.stun_timer = max(getattr(alvo, 'stun_timer', 0), 0.3)
                resultado["reta_stun"] = True

        if tipo_arma == 'Corrente':
            if not alvo.morto:
                dx = self.pos[0] - alvo.pos[0]
                dy = self.pos[1] - alvo.pos[1]
                d = math.hypot(dx, dy)
                if d > 0.1:
                    pull = 0.3
                    alvo.vel[0] += (dx / d) * pull
                    alvo.vel[1] += (dy / d) * pull
                    resultado["chain_pull"] = True

        return resultado

    def aplicar_efeitos_encantamento(self, alvo, dano_aplicado=0):
        """Aplica efeitos de encantamentos no alvo."""
        for enc_nome in self.arma_encantamentos:
            if enc_nome not in ENCANTAMENTOS:
                continue

            enc = ENCANTAMENTOS[enc_nome]
            efeito = enc.get("efeito")

            if random.random() > 0.5:
                continue

            if efeito == "burn":
                dot = DotEffect("Queimando", alvo, 5, 3.0, (255, 100, 0))
                alvo.dots_ativos.append(dot)
            elif efeito == "slow":
                alvo.slow_timer = SLOW_DURACAO_DEFAULT
                alvo.slow_fator = SLOW_FATOR_DEFAULT
            elif efeito == "poison":
                dot = DotEffect("Envenenado", alvo, enc.get("dot_dano", 3),
                               enc.get("dot_duracao", 5.0), (100, 255, 100))
                alvo.dots_ativos.append(dot)
            elif efeito == "lifesteal":
                percent = enc.get("lifesteal_percent", 10) / 100.0
                cura = dano_aplicado * percent
                self.vida = min(self.vida_max, self.vida + cura)

    # ------------------------------------------------------------------
    # Atualização de efeitos
    # ------------------------------------------------------------------

    def _atualizar_buffs(self, dt):
        """Atualiza buffs ativos."""
        for buff in self.buffs_ativos[:]:
            buff.atualizar(dt)
            if not buff.ativo:
                self.buffs_ativos.remove(buff)

    def _atualizar_dots(self, dt):
        """Atualiza DoTs ativos e sincroniza status_effects / cc_effects."""
        for dot in self.dots_ativos[:]:
            dot.atualizar(dt)
            if not dot.ativo:
                self.dots_ativos.remove(dot)

        # A05: usa StatusSnapshot em vez de type() anônimo
        self.status_effects = [
            StatusSnapshot(nome=dot.tipo, dano_por_tick=dot.dano_por_tick)
            for dot in self.dots_ativos
        ]
        if self.stun_timer > 0:
            self.status_effects.append(StatusSnapshot(
                nome='congelado' if getattr(self, 'congelado', False) else 'atordoado',
                mod_velocidade=0.0, pode_mover=False, pode_atacar=False,
            ))
        elif self.slow_timer > 0:
            self.status_effects.append(StatusSnapshot(
                nome='lento',
                mod_velocidade=self.slow_fator,
            ))

        # D02: cc_effects — lista observável dos CCs ativos
        cc = []
        if self.stun_timer > 0:
            cc.append(StatusSnapshot(
                nome='congelado' if getattr(self, 'congelado', False) else 'atordoado',
                mod_velocidade=0.0, pode_mover=False, pode_atacar=False,
            ))
        elif self.slow_timer > 0:
            cc.append(StatusSnapshot(nome='lento', mod_velocidade=self.slow_fator))
        if getattr(self, 'enraizado_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='enraizado', mod_velocidade=0.0, pode_mover=False))
        if getattr(self, 'silenciado_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='silenciado', pode_usar_skill=False))
        if getattr(self, 'cego_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='cego'))
        if getattr(self, 'medo_timer', 0) > 0:
            cc.append(StatusSnapshot(nome='medo'))
        self.cc_effects = cc

    # ------------------------------------------------------------------
    # Receber dano
    # ------------------------------------------------------------------

    def tomar_dano(self, dano, empurrao_x, empurrao_y, tipo_efeito="NORMAL", atacante=None):
        """Recebe dano com suporte a efeitos e reflexão."""
        if self.morto or self.invencivel_timer > 0:
            return False

        if getattr(self, 'dormindo', False):
            self.dormindo = False
            self.stun_timer = 0

        dano_final = dano

        if "Cavaleiro" in self.classe_nome:
            dano_final *= 0.75

        if "Ladino" in self.classe_nome and random.random() < 0.2:
            return False

        if atacante is not None and getattr(atacante, 'cego_timer', 0) > 0:
            if random.random() < 0.5:
                return False

        esquivas = getattr(self, 'esquivas_garantidas', 0)
        if esquivas > 0:
            self.esquivas_garantidas -= 1
            return False

        for buff in self.buffs_ativos:
            dano_recebido = getattr(buff, 'dano_recebido_bonus', 1.0)
            if dano_recebido != 1.0:
                dano_final *= dano_recebido

        if getattr(self, 'vulnerabilidade', 1.0) != 1.0:
            dano_final *= self.vulnerabilidade

        if getattr(self, 'exposto_timer', 0) > 0:
            dano_final *= 2.0

        if getattr(self, 'marcado', False):
            dano_final *= 1.3
            self.marcado = False

        if getattr(self, 'congelado', False):
            dano_final *= 1.5

        for buff in self.buffs_ativos:
            if buff.escudo_atual > 0:
                dano_final = buff.absorver_dano(dano_final)

        dano_refletido = 0
        for buff in self.buffs_ativos:
            if hasattr(buff, 'refletir') and buff.refletir > 0:
                dano_refletido += dano_final * buff.refletir

        if dano_refletido > 0 and atacante is not None and not atacante.morto:
            atacante.vida -= dano_refletido
            atacante.flash_timer = 0.15
            atacante.flash_cor = (200, 200, 255)
            if atacante.vida <= 0:
                atacante.morrer()

        self.vida -= dano_final
        self.invencivel_timer = 0.3

        passiva = getattr(self, 'arma_passiva', None) or {}
        if passiva.get("efeito") == "sobreviver" and self.vida <= 0:
            if not getattr(self, '_sobreviver_usado', False):
                self.vida = 1
                self._sobreviver_usado = True

        self.flash_timer = min(0.25, 0.1 + dano_final * 0.005)

        self.flash_cor = {
            "NORMAL": (255, 255, 255),
            "FOGO": (255, 150, 50), "QUEIMAR": (255, 100, 0), "QUEIMANDO": (255, 120, 20),
            "GELO": (150, 220, 255), "CONGELAR": (100, 200, 255), "CONGELADO": (180, 230, 255),
            "LENTO": (150, 200, 255),
            "VENENO": (100, 255, 100), "ENVENENADO": (80, 220, 80), "NATUREZA": (100, 200, 50),
            "SANGRAMENTO": (255, 50, 50), "SANGRANDO": (200, 30, 30), "SANGUE": (180, 0, 50),
            "RAIO": (255, 255, 100), "PARALISIA": (255, 255, 150),
            "TREVAS": (150, 50, 200), "MALDITO": (100, 0, 150), "NECROSE": (50, 50, 50),
            "DRENAR": (120, 0, 150),
            "LUZ": (255, 255, 220), "CEGO": (255, 255, 200),
            "ARCANO": (150, 100, 255), "SILENCIADO": (180, 150, 255),
            "TEMPO": (200, 180, 255), "TEMPO_PARADO": (220, 200, 255),
            "GRAVITACAO": (100, 50, 150), "PUXADO": (120, 70, 180), "VORTEX": (80, 30, 130),
            "CAOS": (255, 100, 200),
            "ATORDOAR": (255, 255, 100), "ATORDOADO": (255, 255, 100),
            "ENRAIZADO": (139, 90, 43), "MEDO": (150, 0, 150), "CHARME": (255, 150, 200),
            "SONO": (100, 100, 200), "KNOCK_UP": (200, 200, 255),
            "FRACO": (150, 150, 150), "VULNERAVEL": (255, 150, 150), "EXAUSTO": (100, 100, 100),
            "MARCADO": (255, 200, 50), "EXPOSTO": (255, 180, 100), "CORROENDO": (150, 100, 50),
            "EXPLOSAO": (255, 200, 100), "EMPURRAO": (200, 200, 200),
            "BOMBA_RELOGIO": (255, 150, 0), "POSSESSO": (100, 0, 100),
        }.get(tipo_efeito, (255, 255, 255))

        if self.brain is not None:
            self.brain.raiva += 0.2

        kb = 15.0 + (1.0 - (self.vida / self.vida_max)) * 10.0
        kb += dano_final * 0.2
        self.vel[0] += empurrao_x * kb
        self.vel[1] += empurrao_y * kb

        self._aplicar_efeito_status(tipo_efeito)

        if self.vida < self.vida_max * 0.3:
            self.modo_adrenalina = True

        if self.vida <= 0:
            self.morrer()
            return True
        return False

    # ------------------------------------------------------------------
    # Status effects (CCs e DoTs)
    # ------------------------------------------------------------------

    def aplicar_cc(self, efeito: str, duracao: float = None, intensidade: float = 1.0) -> None:
        """
        D02: Ponto de entrada PÚBLICO para aplicar qualquer CC ou status.
        Alias de _aplicar_efeito_status().
        """
        self._aplicar_efeito_status(efeito, duracao=duracao, intensidade=intensidade)

    def _aplicar_efeito_status(self, efeito, duracao=None, intensidade=1.0):
        """Aplica efeitos de status do dano — Sistema v2.0 COLOSSAL."""
        # DoTs
        if efeito in ("VENENO", "ENVENENADO"):
            self.dots_ativos.append(DotEffect("ENVENENADO", self, 1.5 * intensidade, duracao or 4.0, (100, 255, 100)))
        elif efeito in ("SANGRAMENTO", "SANGRANDO"):
            self.dots_ativos.append(DotEffect("SANGRANDO", self, 2.0 * intensidade, duracao or 3.0, (180, 0, 30)))
        elif efeito in ("QUEIMAR", "QUEIMANDO"):
            self.dots_ativos.append(DotEffect("QUEIMANDO", self, 2.5 * intensidade, duracao or 2.5, (255, 100, 0)))
        elif efeito == "CORROENDO":
            self.dots_ativos.append(DotEffect("CORROENDO", self, 1.5 * intensidade, duracao or 4.0, (150, 100, 50)))
            self.mod_defesa *= 0.8
        elif efeito == "NECROSE":
            self.dots_ativos.append(DotEffect("NECROSE", self, 3.0 * intensidade, duracao or 5.0, (50, 50, 50)))
            self.cura_bloqueada = duracao or 5.0
        elif efeito == "MALDITO":
            self.dots_ativos.append(DotEffect("MALDITO", self, 1.0 * intensidade, duracao or 6.0, (100, 0, 100)))
            self.vulnerabilidade = 1.3
            self.vulnerabilidade_timer = duracao or 6.0

        # CCs
        elif efeito in ("CONGELAR", "CONGELADO"):
            self.stun_timer = max(self.stun_timer, duracao or 2.0)
            self.slow_timer = max(self.slow_timer, (duracao or 2.0) + 1.0)
            self.slow_fator = 0.3
            self.congelado = True
            self.congelado_timer = max(getattr(self, 'congelado_timer', 0), duracao or 2.0)
        elif efeito == "LENTO":
            self.slow_timer = max(self.slow_timer, duracao or 2.0)
            self.slow_fator = min(self.slow_fator, 0.5 / intensidade)
        elif efeito in ("ATORDOAR", "ATORDOADO"):
            self.stun_timer = max(self.stun_timer, (duracao or 0.8) * intensidade)
        elif efeito == "PARALISIA":
            self.stun_timer = max(self.stun_timer, (duracao or 0.5) * intensidade)
            self.flash_cor = (255, 255, 100)
            self.flash_timer = 0.3
        elif efeito == "ENRAIZADO":
            self.enraizado_timer = max(self.enraizado_timer, duracao or 2.5)
            self.slow_fator = 0.0
        elif efeito == "SILENCIADO":
            self.silenciado_timer = duracao or 3.0
        elif efeito == "CEGO":
            self.cego_timer = duracao or 2.0
        elif efeito == "MEDO":
            self.medo_timer = duracao or 2.5
        elif efeito == "CHARME":
            self.charme_timer = duracao or 3.0
        elif efeito == "SONO":
            self.dormindo = True
            self.stun_timer = max(self.stun_timer, duracao or 4.0)
        elif efeito == "KNOCK_UP":
            self.vel_z = max(self.vel_z, 18.0 * intensidade)
            self.stun_timer = max(self.stun_timer, 0.4)
        elif efeito == "DRENAR":
            drain_dano = (duracao or 3.0) * 2.0 * intensidade
            self.dots_ativos.append(DotEffect("DRENAR", self, drain_dano / (duracao or 3.0), duracao or 3.0, (120, 0, 150)))
        elif efeito == "FRACO":
            self.dano_reduzido = 0.7
            self.fraco_timer = duracao or 3.0
        elif efeito == "VULNERAVEL":
            self.vulnerabilidade = 1.5
            self.vulnerabilidade_timer = duracao or 2.5
        elif efeito == "EXAUSTO":
            self.exausto_timer = duracao or 3.0
            self.regen_mana_base *= 0.3
        elif efeito == "MARCADO":
            self.marcado = True
        elif efeito == "EXPOSTO":
            self.exposto_timer = duracao or 2.0
        elif efeito == "BOMBA_RELOGIO":
            self.bomba_relogio_timer = duracao or 5.0
            self.bomba_relogio_dano = 80.0 * intensidade
        elif efeito == "POSSESSO":
            if not hasattr(self, 'possesso_timer'):
                self.possesso_timer = 0
            self.possesso_timer = duracao or 3.0

    # ------------------------------------------------------------------
    # Colisão / morte
    # ------------------------------------------------------------------

    def tomar_clash(self, ex, ey):
        """Recebe impacto de clash de armas."""
        self.stun_timer = 0.5
        self.atacando = False
        self.vel[0] += ex * 25
        self.vel[1] += ey * 25

    def morrer(self):
        """Processa morte do lutador."""
        # CM-14: FP1 — verifica buffs com ativa_ao_morrer
        for buff in list(self.buffs_ativos):
            if getattr(buff, 'ativa_ao_morrer', False):
                cura_pct = getattr(buff, 'cura_percent', 0.5)
                self.vida = self.vida_max * cura_pct
                self.buffs_ativos.remove(buff)
                self.morto = False
                return

        for sk in getattr(self, 'skills_arma', []):
            data = sk.get("data", {})
            if data.get("ativa_ao_morrer") and not getattr(self, '_ultimo_suspiro_usado', False):
                self.vida = self.vida_max * data.get("cura_percent", 0.5)
                self._ultimo_suspiro_usado = True
                self.morto = False
                self.invencivel_timer = 1.0
                return

        for sk in getattr(self, 'skills_classe', []):
            data = sk.get("data", {})
            if data.get("ativa_ao_morrer") and not getattr(self, '_ultimo_suspiro_usado', False):
                self.vida = self.vida_max * data.get("cura_percent", 0.5)
                self._ultimo_suspiro_usado = True
                self.morto = False
                self.invencivel_timer = 1.0
                return

        self.morto = True
        self.vida = 0
        self.arma_droppada_pos = list(self.pos)
        self.arma_droppada_ang = self.angulo_arma_visual

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_escudo_info(self):
        """Retorna info do escudo orbital."""
        arma = self.dados.arma_obj
        if not arma or "Orbital" not in arma.tipo:
            return None
        cx, cy = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        dist_base_px = int(((arma.distancia / 100) * PPM) * self.fator_escala)
        raio_char_px = int((self.dados.tamanho / 2) * PPM)
        return (cx, cy), dist_base_px + raio_char_px, self.angulo_arma_visual, arma.largura
