# combat.py
import math
from config import *
from skills import get_skill_data

class Projetil:
    def __init__(self, nome_skill, x, y, angulo, dono):
        self.nome = nome_skill
        # Carrega dados do SKILL_DB
        data = get_skill_data(nome_skill)
        
        self.x = x
        self.y = y
        self.angulo = angulo
        self.dono = dono
        
        # Atributos carregados
        self.tipo_efeito = data.get("efeito", "NORMAL")
        self.vel = data.get("velocidade", 10.0)
        self.raio = data.get("raio", 0.3)
        self.dano = data.get("dano", 10.0)
        self.cor = data.get("cor", BRANCO)
        self.vida = data.get("vida", 2.0)
        
        self.ativo = True

    def atualizar(self, dt):
        rad = math.radians(self.angulo)
        self.x += math.cos(rad) * self.vel * dt
        self.y += math.sin(rad) * self.vel * dt
        self.vida -= dt
        if self.vida <= 0: self.ativo = False