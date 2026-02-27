"""
NEURAL FIGHTS - Sistema de Personagens
Classe Personagem e funções relacionadas
"""

from .constants import get_class_data


class Personagem:
    """
    Classe de Personagem com sistema de classes e personalidade.
    """
    def __init__(self, nome, tamanho, forca, mana, nome_arma="", peso_arma_cache=0, 
                 r=200, g=50, b=50, classe="Guerreiro (Força Bruta)", personalidade="Aleatório",
                 god_id=None, lore=""):  # [PHASE 3] Campo de vínculo divino
        # MEL-C7: Validação de parâmetros — evita divisão por zero e valores fora dos sliders
        if not nome or not str(nome).strip():
            raise ValueError("Nome não pode ser vazio")
        if not (0.5 <= float(tamanho) <= 3.0):
            raise ValueError(f"Tamanho {tamanho} fora do intervalo [0.5, 3.0]")
        if not (1.0 <= float(forca) <= 10.0):
            raise ValueError(f"Força {forca} fora do intervalo [1, 10]")
        if not (1.0 <= float(mana) <= 10.0):
            raise ValueError(f"Mana {mana} fora do intervalo [1, 10]")

        self.nome = nome
        self.lore = str(lore) if lore else ""   # Background/história opcional
        self.tamanho = float(tamanho)
        self.forca = float(forca)
        self.mana = float(mana)
        self.nome_arma = nome_arma
        self.cor_r = int(r)
        self.cor_g = int(g)
        self.cor_b = int(b)
        self.classe = classe
        self.personalidade = personalidade  # Personalidade da IA
        self.god_id = god_id                # [PHASE 3] ID do deus que este campeão serve (None = mortal livre)
        self.arma_obj = None               # BUG-C1: Resolvido em runtime pelo simulador (evita AttributeError)

        # Carrega dados da classe
        self.class_data = get_class_data(classe)
        
        self.velocidade = 0.0
        self.resistencia = 0.0
        self.calcular_status(peso_arma_cache)

    def calcular_status(self, peso_arma=0):
        """Calcula status com modificadores da classe"""
        cd = self.class_data
        
        # Força efetiva com modificador de classe
        forca_eff = self.forca * cd.get("mod_forca", 1.0)
        
        massa_total = self.tamanho + peso_arma
        if massa_total > 0:
            base_vel = (forca_eff * 2) / massa_total
            self.velocidade = base_vel * cd.get("mod_velocidade", 1.0)
        else:
            self.velocidade = 0
        
        # Resistência base * modificador de vida
        self.resistencia = self.tamanho * self.forca * cd.get("mod_vida", 1.0)

    def recalcular_com_arma(self, arma_obj):
        """INC-4: Recalcula status usando o peso da arma atual.
        Deve ser chamado sempre que nome_arma mudar em runtime.
        """
        self.nome_arma = arma_obj.nome if arma_obj else self.nome_arma
        self.arma_obj = arma_obj
        self.calcular_status(arma_obj.peso if arma_obj else 0)

    def get_vida_max(self):
        """Retorna vida máxima calculada — INC-2: alinhado com Lutador._calcular_vida_max"""
        base = 80.0 + (self.resistencia * 5)
        return base * self.class_data.get("mod_vida", 1.0)
    
    def get_mana_max(self):
        """Retorna mana máxima calculada"""
        base = 50.0 + (self.mana * 10)
        return base * self.class_data.get("mod_mana", 1.0)
    
    def get_regen_mana(self):
        """Retorna regeneração de mana por segundo"""
        return self.class_data.get("regen_mana", 3.0)
    
    def get_cor_aura(self):
        """Retorna cor de aura da classe"""
        return self.class_data.get("cor_aura", (200, 200, 200))

    def to_dict(self):
        return {
            "nome": self.nome,
            "tamanho": self.tamanho,
            "forca": self.forca,
            "mana": self.mana,
            "nome_arma": self.nome_arma,
            "cor_r": self.cor_r, 
            "cor_g": self.cor_g, 
            "cor_b": self.cor_b,
            "classe": self.classe,
            "personalidade": self.personalidade,
            "god_id": self.god_id,          # [PHASE 3] Persiste o vínculo divino
            "lore": self.lore,              # MEL-C3: Background/história opcional
        }
