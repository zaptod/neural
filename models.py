# models.py

# --- LISTAS DE DEFINIÇÃO ---
LISTA_CLASSES = [
    "Guerreiro (Passiva)",   # Foca em Estamina/Força
    "Mago (Mana)",           # Foca em Magias
    "Ladino (Híbrido)",      # Critico e Velocidade
    "Paladino (Defensivo)"   # Cura e Defesa
]

class Arma:
    def __init__(self, nome, tipo, dano, peso, 
                 comp_cabo=0, comp_lamina=0, largura=0, distancia=0,
                 r=200, g=200, b=200, 
                 estilo="Padrao", cabo_dano=False, 
                 habilidade="Nenhuma", custo_mana=0, # <--- CAMPOS DE MAGIA
                 **kwargs): 
        
        self.nome = nome
        self.tipo = tipo
        self.dano = float(dano)
        self.peso = float(peso)
        
        # Geometria
        self.comp_cabo = float(comp_cabo)
        self.comp_lamina = float(comp_lamina)
        self.largura = float(largura)
        self.distancia = float(distancia)

        # Comportamento
        self.estilo = estilo
        self.cabo_dano = bool(cabo_dano)
        
        # Sistema de Habilidades
        self.habilidade = habilidade
        self.custo_mana = float(custo_mana)

        # Cores
        self.r = int(r); self.g = int(g); self.b = int(b)
        
        # Migração de dados antigos (Segurança)
        tamanho_antigo = float(kwargs.get('tamanho', 0))
        if self.comp_cabo == 0 and tamanho_antigo > 0:
            if "Reta" in tipo:
                self.comp_cabo = tamanho_antigo * 0.3
                self.comp_lamina = tamanho_antigo * 0.7
                self.largura = 5
            else:
                self.largura = tamanho_antigo
                self.distancia = 30

    def to_dict(self):
        return {
            "nome": self.nome,
            "tipo": self.tipo,
            "dano": self.dano,
            "peso": self.peso,
            "comp_cabo": self.comp_cabo,
            "comp_lamina": self.comp_lamina,
            "largura": self.largura,
            "distancia": self.distancia,
            "r": self.r, "g": self.g, "b": self.b,
            "estilo": self.estilo,
            "cabo_dano": self.cabo_dano,
            "habilidade": self.habilidade,
            "custo_mana": self.custo_mana
        }

class Personagem:
    def __init__(self, nome, tamanho, forca, mana, nome_arma="", peso_arma_cache=0, r=200, g=50, b=50, classe="Guerreiro (Passiva)"):
        self.nome = nome
        self.tamanho = float(tamanho)
        self.forca = float(forca)
        self.mana = float(mana)
        self.nome_arma = nome_arma
        self.cor_r = int(r); self.cor_g = int(g); self.cor_b = int(b)
        self.classe = classe # <--- CAMPO DE CLASSE
        
        self.velocidade = 0.0
        self.resistencia = 0.0
        self.calcular_status(peso_arma_cache)

    def calcular_status(self, peso_arma=0):
        massa_total = self.tamanho + peso_arma
        if massa_total > 0:
            self.velocidade = (self.forca * 2) / massa_total
        else:
            self.velocidade = 0
        self.resistencia = self.tamanho * self.forca

    def to_dict(self):
        return {
            "nome": self.nome,
            "tamanho": self.tamanho,
            "forca": self.forca,
            "mana": self.mana,
            "nome_arma": self.nome_arma,
            "cor_r": self.cor_r, "cor_g": self.cor_g, "cor_b": self.cor_b,
            "classe": self.classe
        }