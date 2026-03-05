"""
NEURAL FIGHTS - Sistema de Armas
Classe Arma e funções de validação/sugestão
"""

import random
from .constants import (
    RARIDADES, TIPOS_ARMA, ENCANTAMENTOS, PASSIVAS_ARMA,
    get_raridade_data, get_tipo_arma_data
)


def gerar_passiva_arma(raridade):
    """Gera uma passiva aleatória baseada na raridade"""
    rar_data = get_raridade_data(raridade)
    tipo_passiva = rar_data.get("passiva")
    if tipo_passiva and tipo_passiva in PASSIVAS_ARMA:
        return random.choice(PASSIVAS_ARMA[tipo_passiva])
    return None


class Arma:
    """
    Classe de Arma expandida com sistema completo de:
    - Raridade (Comum → Mítico)
    - Múltiplos tipos (8 tipos)
    - Múltiplas habilidades (baseado em raridade)
    - Encantamentos empilháveis
    - Passivas únicas
    - Crítico e velocidade de ataque
    - Afinidade elemental
    """
    def __init__(self, nome, tipo, dano, peso,
                 r=200, g=200, b=200,
                 estilo="Padrao", cabo_dano=False,
                 habilidade="Nenhuma", custo_mana=0,
                 raridade="Comum",
                 habilidades=None,
                 encantamentos=None,
                 passiva=None,
                 critico=0.0,
                 velocidade_ataque=1.0,
                 afinidade_elemento=None,
                 durabilidade=100.0,
                 durabilidade_max=100.0,
                 quantidade=1,
                 quantidade_orbitais=1,
                 forca_arco=0,
                 **kwargs):
        
        self.nome = nome
        self.tipo = tipo
        self.raridade = raridade
        self.dano_base = float(dano)
        self.peso_base = float(peso)
        
        # Aplica modificadores de raridade
        rar_data = get_raridade_data(raridade)
        self.dano = self.dano_base * rar_data["mod_dano"]
        self.peso = self.peso_base * rar_data["mod_peso"]

        # Aplica modificadores de TIPO da arma (BUG-02: antes ignorado)
        tipo_data = get_tipo_arma_data(tipo)
        self.dano *= tipo_data.get("mod_dano", 1.0)
        self.peso *= tipo_data.get("mod_peso", 1.0)
        
        # Gameplay
        self.quantidade = int(quantidade)
        self.quantidade_orbitais = int(quantidade_orbitais)
        self.forca_arco = float(forca_arco)
        # BUG-08 fix: restaura forma salva (padrão = 1)
        self.forma_atual = int(kwargs.get('forma_atual', 1))

        # Comportamento
        self.estilo = estilo
        self.cabo_dano = bool(cabo_dano)
        
        # === SISTEMA DE HABILIDADES MÚLTIPLAS ===
        if habilidades is None:
            if habilidade != "Nenhuma":
                self.habilidades = [{"nome": habilidade, "custo": float(custo_mana)}]
            else:
                self.habilidades = []
        else:
            self.habilidades = habilidades
        
        # Mantém compatibilidade com código antigo
        if self.habilidades:
            first_hab = self.habilidades[0]
            if isinstance(first_hab, dict):
                self.habilidade = first_hab.get("nome", "Nenhuma")
                self.custo_mana = first_hab.get("custo", custo_mana)
            else:
                self.habilidade = str(first_hab)
                self.custo_mana = float(custo_mana)
        else:
            self.habilidade = "Nenhuma"
            self.custo_mana = float(custo_mana)
        
        # === SISTEMA DE ENCANTAMENTOS ===
        self.encantamentos = encantamentos or []
        
        # === PASSIVA ===
        if passiva is None and rar_data.get("passiva"):
            self.passiva = gerar_passiva_arma(raridade)
        else:
            self.passiva = passiva
        
        # === STATS EXTRAS ===
        self.critico = float(critico) + rar_data["mod_critico"]
        self.velocidade_ataque = float(velocidade_ataque) * rar_data["mod_velocidade_ataque"]
        self.afinidade_elemento = afinidade_elemento
        
        # === DURABILIDADE ===
        self.durabilidade_max = float(durabilidade_max) * rar_data["mod_durabilidade"]
        self.durabilidade = min(float(durabilidade), self.durabilidade_max)

        # Cores
        self.r = int(r); self.g = int(g); self.b = int(b)
        
        # Cor da raridade
        self.cor_raridade = rar_data["cor"]
        self.efeito_visual = rar_data.get("efeito_visual")
        
        # Flag de aviso de arma quebrada (setado externamente pela simulação)
        self._aviso_quebrada_exibido: bool = False
        


    def get_dano_total(self):
        """Calcula dano total incluindo encantamentos"""
        dano = self.dano
        for enc_nome in self.encantamentos:
            if enc_nome in ENCANTAMENTOS:
                dano += ENCANTAMENTOS[enc_nome].get("dano_bonus", 0)
        return dano
    
    def get_slots_disponiveis(self):
        """Retorna quantos slots de habilidade ainda estão livres"""
        max_slots = get_raridade_data(self.raridade)["slots_habilidade"]
        return max_slots - len(self.habilidades)
    
    def adicionar_habilidade(self, nome_skill, custo):
        """Adiciona uma habilidade se houver slot"""
        if self.get_slots_disponiveis() > 0:
            self.habilidades.append({"nome": nome_skill, "custo": float(custo)})
            if len(self.habilidades) == 1:
                self.habilidade = nome_skill
                self.custo_mana = float(custo)
            return True
        return False
    
    def adicionar_encantamento(self, nome_enc):
        """Adiciona um encantamento se possível"""
        max_enc = get_raridade_data(self.raridade)["max_encantamentos"]
        if len(self.encantamentos) < max_enc and nome_enc in ENCANTAMENTOS:
            self.encantamentos.append(nome_enc)
            return True
        return False
    
    def trocar_forma(self):
        """Troca a forma (apenas para armas Transformáveis)"""
        if self.tipo == "Transformável":
            self.forma_atual = 2 if self.forma_atual == 1 else 1

    def to_dict(self):
        return {
            "nome": self.nome,
            "tipo": self.tipo,
            "dano": self.dano_base,
            "peso": self.peso_base,
            "raridade": self.raridade,
            "quantidade": self.quantidade,
            "quantidade_orbitais": self.quantidade_orbitais,
            "forca_arco": self.forca_arco,
            "forma_atual": self.forma_atual,  # BUG-08 fix
            "r": self.r, "g": self.g, "b": self.b,
            "estilo": self.estilo,
            "cabo_dano": self.cabo_dano,
            "habilidades": self.habilidades,
            "encantamentos": self.encantamentos,
            "passiva": self.passiva,
            "critico": self.critico - get_raridade_data(self.raridade)["mod_critico"],
            "velocidade_ataque": self.velocidade_ataque / get_raridade_data(self.raridade)["mod_velocidade_ataque"],
            "afinidade_elemento": self.afinidade_elemento,
            "durabilidade": self.durabilidade,
            "durabilidade_max": self.durabilidade_max / get_raridade_data(self.raridade)["mod_durabilidade"],
            "habilidade": self.habilidade,
            "custo_mana": self.custo_mana,
        }


def validar_arma_personagem(arma, personagem):
    """
    Valida se a arma é apropriada para o tamanho do personagem.
    """
    if arma is None or personagem is None:
        return {
            "valido": True,
            "mensagem": "Sem arma equipada",
            "sugestao": None,
            "proporcao": 0
        }
    
    tamanho_arma = (arma.peso_base if hasattr(arma, 'peso_base') else arma.peso) * 0.1
    tamanho_char = personagem.tamanho / 10.0
    
    if tamanho_char <= 0:
        tamanho_char = 1.0
    
    proporcao = tamanho_arma / tamanho_char
    
    MIN_PROPORCAO = 0.2
    MAX_PROPORCAO = 3.0
    IDEAL_MIN = 0.4
    IDEAL_MAX = 1.5
    
    resultado = {
        "proporcao": proporcao,
        "tamanho_arma": tamanho_arma,
        "tamanho_char": tamanho_char
    }
    
    if proporcao < MIN_PROPORCAO:
        resultado["valido"] = False
        resultado["mensagem"] = f"⚠️ Arma MUITO PEQUENA ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = f"Aumente o tamanho da arma ou use personagem menor"
        resultado["nivel"] = "critico"
    elif proporcao < IDEAL_MIN:
        resultado["valido"] = True
        resultado["mensagem"] = f"⚡ Arma pequena ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = "Arma funcional, mas pode parecer pequena visualmente"
        resultado["nivel"] = "aviso"
    elif proporcao > MAX_PROPORCAO:
        resultado["valido"] = False
        resultado["mensagem"] = f"⚠️ Arma MUITO GRANDE ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = f"Diminua o tamanho da arma ou use personagem maior"
        resultado["nivel"] = "critico"
    elif proporcao > IDEAL_MAX:
        resultado["valido"] = True
        resultado["mensagem"] = f"⚡ Arma grande ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = "Arma funcional, pode parecer exagerada"
        resultado["nivel"] = "aviso"
    else:
        resultado["valido"] = True
        resultado["mensagem"] = f"✓ Proporção ideal ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = None
        resultado["nivel"] = "ok"
    
    return resultado
