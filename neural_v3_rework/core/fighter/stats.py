"""
NEURAL FIGHTS — core/fighter/stats.py  [D03/D04 Sprint 8]
==========================================================
StatsMixin: cálculos de vida/mana, skills, channeling.

Imports inline eliminados (D04): get_skill_data, get_class_data no topo.
"""

import random
import logging

from utils.balance_config import (
    MANA_BASE, MANA_POR_ATRIBUTO,
    ESTAMINA_CUSTO_SKILL_MULT,
    CD_ARMA_MAX_RATIO, CD_ARMA_MAX_ABSOLUTO,
)
from core.skills import get_skill_data
from models import get_class_data

_log = logging.getLogger("entities")


class StatsMixin:
    """Mixin com cálculos de stats, skills e channeling."""

    # ------------------------------------------------------------------
    # Cálculos de stats base
    # ------------------------------------------------------------------

    def _calcular_vida_max(self):
        """Calcula vida máxima com modificadores de classe."""
        base = 80.0 + (self.dados.resistencia * 5)
        return base * self.class_data.get("mod_vida", 1.0)

    def _calcular_mana_max(self):
        """Calcula mana máxima com modificadores de classe."""
        base = MANA_BASE + (getattr(self.dados, 'mana', 0) * MANA_POR_ATRIBUTO)
        return base * self.class_data.get("mod_mana", 1.0)

    # ------------------------------------------------------------------
    # Gerenciamento de skills
    # ------------------------------------------------------------------

    def trocar_skill(self):
        """Troca para a próxima skill disponível."""
        if len(self.skills_arma) <= 1:
            return
        self.skill_atual_idx = (self.skill_atual_idx + 1) % len(self.skills_arma)
        skill = self.skills_arma[self.skill_atual_idx]
        self.skill_arma_nome = skill["nome"]
        self.custo_skill_arma = skill["custo"]

    def get_skill_atual(self):
        """Retorna dados da skill atualmente selecionada."""
        if not self.skills_arma:
            return None
        return self.skills_arma[self.skill_atual_idx]

    def get_dano_modificado(self, dano_base):
        """Retorna dano com todos os modificadores (buffs, classe, passivas)."""
        dano = dano_base * self.mod_dano
        for buff in self.buffs_ativos:
            dano *= buff.buff_dano
        if "Berserker" in self.classe_nome:
            hp_pct = self.vida / self.vida_max
            dano *= 1.0 + (1.0 - hp_pct) * 0.5
        if "Assassino" in self.classe_nome and random.random() < 0.25:
            dano *= 2.0
        return dano

    # ------------------------------------------------------------------
    # Sistema de Channeling v8.0
    # ------------------------------------------------------------------

    def pode_canalizar_magia(self) -> bool:
        """Verifica se o personagem pode canalizar magias."""
        classes_magicas = ["Mago", "Piromante", "Criomante", "Necromante", "Feiticeiro"]
        return any(c in self.classe_nome for c in classes_magicas)

    def iniciar_canalizacao(self, skill_nome: str, skill_data: dict) -> bool:
        """
        Inicia a canalização de uma magia poderosa.
        Retorna True se a canalização iniciou com sucesso.
        """
        if not self.pode_canalizar_magia():
            return False
        self.canalizando = True
        self.skill_canalizando = skill_nome
        self.tempo_canalizacao = 0.0
        return True

    def interromper_canalizacao(self):
        """Interrompe a canalização atual."""
        self.canalizando = False
        self.skill_canalizando = None
        self.tempo_canalizacao = 0.0

    def atualizar_canalizacao(self, dt: float) -> dict:
        """Atualiza o estado de canalização."""
        if not getattr(self, 'canalizando', False):
            return None
        self.tempo_canalizacao += dt
        return None

    def get_progresso_canalizacao(self) -> float:
        """Retorna o progresso da canalização (0.0 a 1.0)."""
        if not getattr(self, 'canalizando', False):
            return 0.0
        tempo_base = {
            "Mago (Arcano)": 1.5, "Piromante (Fogo)": 2.0,
            "Criomante (Gelo)": 1.2, "Necromante (Trevas)": 2.5,
            "Feiticeiro (Caos)": 1.0,
        }.get(self.classe_nome, 1.5)
        return min(1.0, getattr(self, 'tempo_canalizacao', 0.0) / tempo_base)
