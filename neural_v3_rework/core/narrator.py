"""
NEURAL FIGHTS — Narrador / Comentarista de IA v1.0
====================================================
Detecta eventos dramáticos durante a luta e gera mensagens
cinematográficas para exibição no HUD.
"""

import random
import math
from typing import Dict, List, Optional, Tuple


class NarratorEvent:
    """Um evento narrado com texto, cor, prioridade e duração."""
    __slots__ = ("texto", "cor", "prioridade", "duracao", "timer", "tamanho", "posicao")
    
    def __init__(self, texto: str, cor: Tuple[int,int,int] = (255,255,220),
                 prioridade: int = 1, duracao: float = 2.5, tamanho: int = 20,
                 posicao: str = "topo"):
        self.texto = texto
        self.cor = cor
        self.prioridade = prioridade  # Maior = mais importante
        self.duracao = duracao
        self.timer = duracao
        self.tamanho = tamanho
        self.posicao = posicao  # "topo", "meio", "baixo"


# Templates de comentários por tipo de evento
COMENTARIOS = {
    "primeiro_sangue": [
        "{atacante} tira o primeiro sangue!",
        "Primeiro golpe pra {atacante}!",
        "E {atacante} começa a pressionar {defensor}!",
        "{atacante} abre o combate!",
    ],
    "combo_alto": [
        "COMBO {hits} HITS! {atacante} está imparável!",
        "{atacante} conecta uma sequência de {hits} golpes!",
        "Sequência devastadora de {atacante}! {hits}x!",
    ],
    "quase_morte": [
        "{lutador} está por um fio! {hp_pct:.0f}% de vida!",
        "Um golpe e {lutador} cai! Apenas {hp_pct:.0f}%!",
        "{lutador} se recusa a morrer! {hp_pct:.0f}%!",
    ],
    "comeback": [
        "{lutador} está REVERTENDO! De {hp_min:.0f}% para o ataque!",
        "COMEBACK! {lutador} não vai desistir!",
        "A virada de {lutador}! Que luta!",
    ],
    "domination": [
        "{atacante} está DOMINANDO! {defensor} não consegue reagir!",
        "Domínio total de {atacante}!",
        "{atacante} não dá chances para {defensor}!",
    ],
    "clash": [
        "OS GOLPES SE CHOCAM! Momento épico!",
        "CLASH! Os lutadores medem forças!",
        "Encontro de lâminas! Quem vai ceder?",
    ],
    "execucao": [
        "EXECUÇÃO! {atacante} finaliza {defensor}!",
        "{atacante} aplica o golpe final!",
        "FATALITY! {defensor} eliminado por {atacante}!",
    ],
    "skill_epica": [
        "{lutador} lança {skill}!",
        "{skill} de {lutador}! Impacto massivo!",
        "{lutador} usa {skill}!",
    ],
    "esquiva_perfeita": [
        "ESQUIVA PERFEITA! {defensor} desvia por milímetros!",
        "{defensor} lê o golpe e escapa!",
        "Reflexos sobre-humanos de {defensor}!",
    ],
    "double_ko": [
        "DOUBLE KO! Ambos caem ao mesmo tempo!",
        "Nocaute duplo! Que final!",
    ],
    "luta_longa": [
        "Esta luta está se prolongando! Quem vai ceder primeiro?",
        "Os dois lutadores parecem equilibrados!",
        "Nenhum dos dois desiste!",
    ],
    "streak_kill": [
        "{atacante} com {streak} vitórias seguidas! Racha de terror!",
        "Streak de {streak} para {atacante}! Dominância!",
    ],
    "upset": [
        "UPSET! {vencedor} derruba o favorito {perdedor}!",
        "E o azarão vence! {vencedor} surpreende!",
    ],
    "blessing_ativada": [
        "{lutador} invoca o poder de {deus}!",
        "A bênção de {deus} responde a {lutador}!",
    ],
    "tempo_esgotando": [
        "30 segundos restantes! Quem vai se impor?",
        "O tempo está acabando! A urgência aumenta!",
    ],
    "ko_rapido": [
        "KO RÁPIDO! {atacante} finaliza em {tempo:.1f}s!",
        "Nem deu tempo! {atacante} com KO em {tempo:.1f}s!",
    ],
}


class NarratorSystem:
    """
    Sistema de narração — detecta eventos e gera comentários.
    Singleton consistente com o padrão do projeto.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        cls._instance = None
    
    def __init__(self):
        # Fila de eventos (ordenados por prioridade)
        self.eventos_ativos: List[NarratorEvent] = []
        self.max_eventos = 3
        
        # Cooldown entre mensagens do mesmo tipo
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_padrao = 8.0  # Mínimo 8s entre msgs do mesmo tipo
        
        # Estado de tracking
        self._primeiro_sangue_ocorreu = False
        self._hp_minimos: Dict[str, float] = {}  # nome → menor HP%
        self._hp_atuais: Dict[str, float] = {}
        self._hits_sem_resposta: Dict[str, int] = {}  # rastreia domination
        self._tempo_aviso_dado = False
        self._combos_anteriores: Dict[str, int] = {}
        
        # Configuração
        self.ativo = True
    
    def registrar_lutadores(self, *lutadores):
        """Inicializa tracking para lutadores"""
        for l in lutadores:
            nome = l.dados.nome
            self._hp_minimos[nome] = 100.0
            self._hp_atuais[nome] = 100.0
            self._hits_sem_resposta[nome] = 0
            self._combos_anteriores[nome] = 0
    
    def _pode_narrar(self, tipo: str) -> bool:
        """Verifica se pode narrar (cooldown)"""
        return self.cooldowns.get(tipo, 0) <= 0
    
    def _registrar_cooldown(self, tipo: str, duracao: Optional[float] = None):
        """Registra cooldown para um tipo de evento"""
        self.cooldowns[tipo] = duracao or self.cooldown_padrao
    
    def _adicionar_evento(self, tipo: str, texto: str, cor: Tuple[int,int,int] = (255, 255, 220),
                         prioridade: int = 1, duracao: float = 2.5, tamanho: int = 20):
        """Adiciona evento narrado"""
        if not self._pode_narrar(tipo):
            return
        
        evento = NarratorEvent(texto, cor, prioridade, duracao, tamanho)
        self.eventos_ativos.append(evento)
        
        # Ordena por prioridade e mantém limite
        self.eventos_ativos.sort(key=lambda e: e.prioridade, reverse=True)
        while len(self.eventos_ativos) > self.max_eventos:
            self.eventos_ativos.pop()
        
        self._registrar_cooldown(tipo)
    
    def _template(self, tipo: str, **kwargs) -> str:
        """Pega template aleatório e formata"""
        templates = COMENTARIOS.get(tipo, ["{tipo} ocorreu!"])
        return random.choice(templates).format(**kwargs)
    
    # ===============================================================
    # Callbacks — chamados pela simulação quando eventos ocorrem
    # ===============================================================
    
    def on_hit(self, atacante_nome: str, defensor_nome: str, dano: float, critico: bool = False):
        """Chamado quando um golpe conecta"""
        if not self.ativo:
            return
        
        # Primeiro sangue
        if not self._primeiro_sangue_ocorreu:
            self._primeiro_sangue_ocorreu = True
            texto = self._template("primeiro_sangue", atacante=atacante_nome, defensor=defensor_nome)
            self._adicionar_evento("primeiro_sangue", texto, (255, 200, 50), prioridade=3, duracao=3.0, tamanho=24)
        
        # Domination tracking
        self._hits_sem_resposta[atacante_nome] = self._hits_sem_resposta.get(atacante_nome, 0) + 1
        self._hits_sem_resposta[defensor_nome] = 0
        
        # Verifica domination (7+ hits sem resposta)
        if self._hits_sem_resposta.get(atacante_nome, 0) >= 7:
            texto = self._template("domination", atacante=atacante_nome, defensor=defensor_nome)
            self._adicionar_evento("domination", texto, (200, 50, 50), prioridade=2, duracao=3.0, tamanho=22)
            self._hits_sem_resposta[atacante_nome] = 0
    
    def on_hp_change(self, nome: str, hp_pct: float):
        """Chamado quando HP muda"""
        if not self.ativo:
            return
        
        self._hp_atuais[nome] = hp_pct
        
        # Atualiza mínimo
        if hp_pct < self._hp_minimos.get(nome, 100.0):
            self._hp_minimos[nome] = hp_pct
        
        # Quase-morte (< 15%)
        if hp_pct < 15.0 and hp_pct > 0:
            texto = self._template("quase_morte", lutador=nome, hp_pct=hp_pct)
            self._adicionar_evento("quase_morte", texto, (255, 50, 50), prioridade=3, duracao=2.0, tamanho=22)
        
        # Comeback — HP estava < 25% e agora está causando dano (detecta na próxima chamada on_hit)
        if hp_pct > 0 and self._hp_minimos.get(nome, 100) < 25.0:
            # Se o cara com HP baixo acerta, é um comeback
            hits_dele = self._hits_sem_resposta.get(nome, 0)
            if hits_dele >= 3:
                texto = self._template("comeback", lutador=nome, hp_min=self._hp_minimos[nome])
                self._adicionar_evento("comeback", texto, (50, 255, 50), prioridade=4, duracao=3.5, tamanho=26)
    
    def on_combo(self, atacante_nome: str, combo_hits: int):
        """Chamado quando combo alcança threshold"""
        if not self.ativo:
            return
        
        # Notifica a cada 3+ hits (e apenas quando o combo CRESCE)
        prev = self._combos_anteriores.get(atacante_nome, 0)
        if combo_hits >= 3 and combo_hits > prev:
            texto = self._template("combo_alto", atacante=atacante_nome, hits=combo_hits)
            self._adicionar_evento("combo_alto", texto, (255, 150, 50), prioridade=2, duracao=2.0, tamanho=22)
        self._combos_anteriores[atacante_nome] = combo_hits
    
    def on_clash(self):
        """Chamado quando ocorre um clash"""
        if not self.ativo:
            return
        texto = self._template("clash")
        self._adicionar_evento("clash", texto, (255, 255, 100), prioridade=3, duracao=2.0, tamanho=26)
    
    def on_kill(self, atacante_nome: str, defensor_nome: str, tempo_luta: float):
        """Chamado quando alguém morre"""
        if not self.ativo:
            return
        
        # KO rápido (< 15s)
        if tempo_luta < 15.0:
            texto = self._template("ko_rapido", atacante=atacante_nome, tempo=tempo_luta)
            self._adicionar_evento("ko_rapido", texto, (255, 200, 0), prioridade=5, duracao=4.0, tamanho=28)
        else:
            texto = self._template("execucao", atacante=atacante_nome, defensor=defensor_nome)
            self._adicionar_evento("execucao", texto, (255, 50, 50), prioridade=4, duracao=3.0, tamanho=26)
    
    def on_skill_use(self, lutador_nome: str, skill_nome: str):
        """Chamado quando uma skill é usada"""
        if not self.ativo:
            return
        # Só narra skills de classe (as mais dramáticas)
        texto = self._template("skill_epica", lutador=lutador_nome, skill=skill_nome)
        self._adicionar_evento("skill_epica", texto, (150, 150, 255), prioridade=1, duracao=2.0, tamanho=18)
    
    def on_esquiva(self, defensor_nome: str):
        """Chamado quando acontece esquiva perfeita"""
        if not self.ativo:
            return
        texto = self._template("esquiva_perfeita", defensor=defensor_nome)
        self._adicionar_evento("esquiva_perfeita", texto, (100, 255, 200), prioridade=2, duracao=1.5, tamanho=20)
    
    def on_blessing(self, lutador_nome: str, deus_nome: str):
        """Chamado quando bênção divina é ativada"""
        if not self.ativo:
            return
        texto = self._template("blessing_ativada", lutador=lutador_nome, deus=deus_nome)
        self._adicionar_evento("blessing_ativada", texto, (255, 215, 0), prioridade=3, duracao=3.0, tamanho=24)
    
    def update(self, dt: float, tempo_luta: float = 0):
        """Atualiza timers e remove eventos expirados"""
        # Atualiza cooldowns
        for tipo in list(self.cooldowns.keys()):
            self.cooldowns[tipo] -= dt
            if self.cooldowns[tipo] <= 0:
                del self.cooldowns[tipo]
        
        # Atualiza eventos ativos
        for ev in self.eventos_ativos[:]:
            ev.timer -= dt
            if ev.timer <= 0:
                self.eventos_ativos.remove(ev)
        
        # Aviso de tempo esgotando
        if not self._tempo_aviso_dado and tempo_luta >= 90.0:
            self._tempo_aviso_dado = True
            texto = random.choice(COMENTARIOS["tempo_esgotando"])
            self._adicionar_evento("tempo_esgotando", texto, (255, 200, 100), prioridade=2, duracao=3.0, tamanho=22)
        
        # Luta longa (> 60s sem kill)
        if tempo_luta > 60.0 and not self._primeiro_sangue_ocorreu:
            texto = random.choice(COMENTARIOS["luta_longa"])
            self._adicionar_evento("luta_longa", texto, (200, 200, 200), prioridade=1, duracao=3.0, tamanho=18)
    
    def get_eventos_renderizar(self) -> List[NarratorEvent]:
        """Retorna eventos ativos para renderização"""
        return self.eventos_ativos
