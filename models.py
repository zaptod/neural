# models.py

# ============================================================================
# SISTEMA DE CLASSES - NEURAL FIGHTS
# ============================================================================
# Cada classe define:
# - Passiva: Bônus permanente
# - Afinidade: Elemento/estilo preferido
# - Stats base modificados
# ============================================================================

LISTA_CLASSES = [
    # === FÍSICOS ===
    "Guerreiro (Força Bruta)",
    "Berserker (Fúria)",
    "Gladiador (Combate)",
    "Cavaleiro (Defesa)",
    
    # === ÁGEIS ===
    "Assassino (Crítico)",
    "Ladino (Evasão)",
    "Ninja (Velocidade)",
    "Duelista (Precisão)",
    
    # === MÁGICOS ===
    "Mago (Arcano)",
    "Piromante (Fogo)",
    "Criomante (Gelo)",
    "Necromante (Trevas)",
    
    # === HÍBRIDOS ===
    "Paladino (Sagrado)",
    "Druida (Natureza)",
    "Feiticeiro (Caos)",
    "Monge (Chi)",
]

# Dados detalhados de cada classe
CLASSES_DATA = {
    # === FÍSICOS ===
    "Guerreiro (Força Bruta)": {
        "descricao": "Mestre do combate corpo-a-corpo tradicional",
        "passiva": "Golpes físicos causam 20% mais dano",
        "mod_forca": 1.2,
        "mod_mana": 0.6,
        "mod_vida": 1.1,
        "mod_velocidade": 1.0,
        "regen_mana": 2.0,
        "skills_afinidade": ["Impacto Sônico", "Avanço Brutal", "Fúria Giratória", "Golpe do Executor"],
        "cor_aura": (200, 150, 100),
    },
    "Berserker (Fúria)": {
        "descricao": "Quanto mais ferido, mais perigoso",
        "passiva": "Dano aumenta conforme perde vida (até +50%)",
        "mod_forca": 1.3,
        "mod_mana": 0.4,
        "mod_vida": 1.2,
        "mod_velocidade": 1.1,
        "regen_mana": 1.5,
        "skills_afinidade": ["Avanço Brutal", "Fúria Giratória", "Explosão Nova", "Golpe do Executor"],
        "cor_aura": (255, 50, 50),
    },
    "Gladiador (Combate)": {
        "descricao": "Especialista em duelos prolongados",
        "passiva": "Regenera estamina 30% mais rápido",
        "mod_forca": 1.1,
        "mod_mana": 0.7,
        "mod_vida": 1.15,
        "mod_velocidade": 1.05,
        "regen_mana": 2.5,
        "skills_afinidade": ["Impacto Sônico", "Reflexo Espelhado", "Fúria Giratória", "Velocidade Arcana"],
        "cor_aura": (180, 130, 80),
    },
    "Cavaleiro (Defesa)": {
        "descricao": "Tanque impenetrável com escudo",
        "passiva": "Recebe 25% menos dano",
        "mod_forca": 1.0,
        "mod_mana": 0.8,
        "mod_vida": 1.4,
        "mod_velocidade": 0.85,
        "regen_mana": 3.0,
        "skills_afinidade": ["Escudo Arcano", "Reflexo Espelhado", "Fúria Giratória", "Cura Menor"],
        "cor_aura": (150, 150, 200),
    },
    
    # === ÁGEIS ===
    "Assassino (Crítico)": {
        "descricao": "Mestre dos golpes fatais",
        "passiva": "25% chance de crítico (2x dano)",
        "mod_forca": 1.0,
        "mod_mana": 0.8,
        "mod_vida": 0.8,
        "mod_velocidade": 1.3,
        "regen_mana": 3.0,
        "skills_afinidade": ["Lâmina de Sangue", "Teleporte Relâmpago", "Avanço Brutal", "Execução"],
        "cor_aura": (100, 0, 100),
    },
    "Ladino (Evasão)": {
        "descricao": "Impossível de acertar",
        "passiva": "20% chance de esquivar ataques",
        "mod_forca": 0.9,
        "mod_mana": 0.9,
        "mod_vida": 0.85,
        "mod_velocidade": 1.25,
        "regen_mana": 3.5,
        "skills_afinidade": ["Dardo Venenoso", "Teleporte Relâmpago", "Velocidade Arcana", "Espinhos"],
        "cor_aura": (80, 80, 80),
    },
    "Ninja (Velocidade)": {
        "descricao": "Velocidade sobre-humana",
        "passiva": "Move 40% mais rápido, ataca 20% mais rápido",
        "mod_forca": 0.85,
        "mod_mana": 0.9,
        "mod_vida": 0.75,
        "mod_velocidade": 1.4,
        "regen_mana": 4.0,
        "skills_afinidade": ["Teleporte Relâmpago", "Corrente Elétrica", "Espinhos", "Avanço Brutal"],
        "cor_aura": (50, 50, 50),
    },
    "Duelista (Precisão)": {
        "descricao": "Cada golpe conta",
        "passiva": "Ataques nunca erram, +15% dano em 1v1",
        "mod_forca": 1.05,
        "mod_mana": 0.85,
        "mod_vida": 0.9,
        "mod_velocidade": 1.15,
        "regen_mana": 3.0,
        "skills_afinidade": ["Lança de Gelo", "Relâmpago", "Impacto Sônico", "Golpe do Executor"],
        "cor_aura": (255, 215, 0),
    },
    
    # === MÁGICOS ===
    "Mago (Arcano)": {
        "descricao": "Mestre de todas as magias",
        "passiva": "Magias custam 20% menos mana",
        "mod_forca": 0.6,
        "mod_mana": 1.5,
        "mod_vida": 0.7,
        "mod_velocidade": 0.9,
        "regen_mana": 8.0,
        "skills_afinidade": ["Disparo de Mana", "Bola de Fogo", "Relâmpago", "Escudo Arcano"],
        "cor_aura": (100, 150, 255),
    },
    "Piromante (Fogo)": {
        "descricao": "Destruição pelo fogo",
        "passiva": "Magias de fogo causam 30% mais dano",
        "mod_forca": 0.7,
        "mod_mana": 1.4,
        "mod_vida": 0.75,
        "mod_velocidade": 0.95,
        "regen_mana": 6.0,
        "skills_afinidade": ["Bola de Fogo", "Meteoro", "Lança de Fogo", "Explosão Nova"],
        "cor_aura": (255, 100, 0),
    },
    "Criomante (Gelo)": {
        "descricao": "Controle através do frio",
        "passiva": "Magias de gelo sempre aplicam slow",
        "mod_forca": 0.65,
        "mod_mana": 1.35,
        "mod_vida": 0.8,
        "mod_velocidade": 0.9,
        "regen_mana": 6.5,
        "skills_afinidade": ["Estilhaço de Gelo", "Lança de Gelo", "Nevasca", "Prisão de Gelo"],
        "cor_aura": (150, 220, 255),
    },
    "Necromante (Trevas)": {
        "descricao": "Poder sobre vida e morte",
        "passiva": "Drena 15% do dano causado como vida",
        "mod_forca": 0.7,
        "mod_mana": 1.4,
        "mod_vida": 0.85,
        "mod_velocidade": 0.85,
        "regen_mana": 5.0,
        "skills_afinidade": ["Esfera Sombria", "Lâmina de Sangue", "Maldição", "Explosão Necrótica"],
        "cor_aura": (80, 0, 120),
    },
    
    # === HÍBRIDOS ===
    "Paladino (Sagrado)": {
        "descricao": "Guerreiro sagrado equilibrado",
        "passiva": "Cura 2% da vida máxima por segundo",
        "mod_forca": 1.0,
        "mod_mana": 1.0,
        "mod_vida": 1.2,
        "mod_velocidade": 0.95,
        "regen_mana": 4.0,
        "skills_afinidade": ["Cura Menor", "Escudo Arcano", "Avanço Brutal", "Relâmpago"],
        "cor_aura": (255, 215, 100),
    },
    "Druida (Natureza)": {
        "descricao": "Poder da natureza selvagem",
        "passiva": "Venenos duram 50% mais",
        "mod_forca": 0.9,
        "mod_mana": 1.2,
        "mod_vida": 1.0,
        "mod_velocidade": 1.0,
        "regen_mana": 5.0,
        "skills_afinidade": ["Dardo Venenoso", "Nuvem Tóxica", "Espinhos", "Raízes"],
        "cor_aura": (100, 200, 50),
    },
    "Feiticeiro (Caos)": {
        "descricao": "Magia imprevisível e poderosa",
        "passiva": "Magias têm 20% chance de lançar duas vezes",
        "mod_forca": 0.6,
        "mod_mana": 1.6,
        "mod_vida": 0.65,
        "mod_velocidade": 0.95,
        "regen_mana": 7.0,
        "skills_afinidade": ["Bola de Fogo", "Tempestade", "Maldição", "Invocação: Espírito"],
        "cor_aura": (200, 50, 200),
    },
    "Monge (Chi)": {
        "descricao": "Artes marciais místicas",
        "passiva": "Ataques desarmados causam dano mágico",
        "mod_forca": 1.1,
        "mod_mana": 1.1,
        "mod_vida": 0.95,
        "mod_velocidade": 1.2,
        "regen_mana": 6.0,
        "skills_afinidade": ["Velocidade Arcana", "Teleporte Relâmpago", "Cura Menor", "Fúria Giratória"],
        "cor_aura": (255, 255, 200),
    },
}

def get_class_data(nome_classe):
    """Retorna os dados de uma classe"""
    return CLASSES_DATA.get(nome_classe, CLASSES_DATA["Guerreiro (Força Bruta)"])

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
    def __init__(self, nome, tamanho, forca, mana, nome_arma="", peso_arma_cache=0, r=200, g=50, b=50, classe="Guerreiro (Força Bruta)"):
        self.nome = nome
        self.tamanho = float(tamanho)
        self.forca = float(forca)
        self.mana = float(mana)
        self.nome_arma = nome_arma
        self.cor_r = int(r); self.cor_g = int(g); self.cor_b = int(b)
        self.classe = classe
        
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

    def get_vida_max(self):
        """Retorna vida máxima calculada"""
        base = 100.0 + (self.resistencia * 10)
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
            "cor_r": self.cor_r, "cor_g": self.cor_g, "cor_b": self.cor_b,
            "classe": self.classe
        }