# 🎮 NEURAL FIGHTS - PROMPT CONTEXTUALIZADO PARA IA

## 📋 DOCUMENTO DE CONTEXTO COMPLETO DO PROJETO

---

## 🎯 VISÃO GERAL DO PROJETO

**Neural Fights** é um **simulador de combate 2D em tempo real** desenvolvido em **Python** utilizando **Pygame** para renderização e **Tkinter** para interface de gerenciamento. O projeto combina:

- **Simulação de física 2D** com gravidade, colisões e knockback
- **Sistema de IA procedural** com centenas de milhares de personalidades únicas
- **Sistema de armas detalhado** com 8 tipos diferentes e sistema de raridade
- **Sistema de classes RPG** com modificadores de atributos
- **Efeitos visuais e sonoros** procedurais para feedback de combate
- **Sistema de arenas** com múltiplos mapas temáticos e obstáculos

A versão atual é a **v10.0 AUDIO EDITION**, focada em feedback sonoro e percepção de armas pela IA.

---

## 🏗️ ARQUITETURA DO PROJETO

### Estrutura de Diretórios

```
neural_fights/
├── run.py                  # Ponto de entrada principal
├── match_config.json       # Configuração da luta atual
├── ai/                     # Sistema de Inteligência Artificial
│   ├── brain.py            # Cérebro da IA (3400+ linhas)
│   ├── choreographer.py    # Coreografia de combate cinematográfico
│   ├── combat_tactics.py   # Táticas de combate
│   ├── emotions.py         # Sistema emocional da IA
│   ├── personalities.py    # Traços, arquétipos e quirks
│   └── spatial.py          # Consciência espacial
├── core/                   # Núcleo do jogo
│   ├── arena.py            # Sistema de arenas e mapas
│   ├── combat.py           # Projéteis e mecânicas de combate
│   ├── entities.py         # Classe Lutador principal
│   ├── game_feel.py        # Hit Stop, Super Armor, Channeling
│   ├── hitbox.py           # Sistema de detecção de colisão
│   ├── physics.py          # Funções de física e geometria
│   ├── skills.py           # Catálogo de 40+ habilidades
│   └── weapon_analysis.py  # Análise tática de armas para IA
├── data/                   # Persistência de dados
│   ├── database.py         # Funções de leitura/escrita JSON
│   ├── personagens.json    # Dados de 300+ personagens
│   └── armas.json          # Dados de 100+ armas
├── effects/                # Efeitos visuais e sonoros
│   ├── audio.py            # Sistema de áudio procedural
│   ├── camera.py           # Câmera dinâmica com shake
│   ├── particles.py        # Partículas e faíscas
│   ├── visual.py           # Efeitos visuais diversos
│   ├── impact.py           # Efeitos de impacto
│   ├── movement.py         # Animações de movimento
│   ├── attack.py           # Animações de ataque
│   └── weapon_animations.py # Animações específicas de armas
├── models/                 # Modelos de dados
│   ├── characters.py       # Classe Personagem
│   ├── weapons.py          # Classe Arma
│   └── constants.py        # Raridades, tipos, encantamentos
├── simulation/             # Motor de simulação
│   └── simulacao.py        # Loop principal (2200+ linhas)
├── ui/                     # Interface gráfica (Tkinter)
│   ├── main.py             # Launcher principal
│   ├── view_armas.py       # Tela de forjar armas
│   ├── view_chars.py       # Tela de criar personagens
│   ├── view_luta.py        # Tela de configurar lutas
│   └── view_sons.py        # Tela de configurar sons
├── utils/                  # Utilitários
│   ├── config.py           # Constantes globais (física, cores)
│   └── helpers.py          # Funções auxiliares
└── sounds/                 # Arquivos de áudio
    └── sound_config.json   # Configuração de sons customizados
```

---

## 🧠 SISTEMA DE INTELIGÊNCIA ARTIFICIAL

### AIBrain (ai/brain.py) - O Cérebro da IA

O sistema de IA é extremamente sofisticado, com **centenas de milhares de combinações únicas** de personalidade:

#### Componentes da Personalidade

1. **70+ Traços de Personalidade** divididos em categorias:
   - **Agressividade**: IMPRUDENTE, BERSERKER, PREDADOR, SANGUINARIO, ENCURRALADOR...
   - **Defensivo**: CAUTELOSO, REATIVO, TANQUE, COBERTURA_MESTRE...
   - **Mobilidade**: ACROBATA, FLANQUEADOR, ARENA_MASTER, NAVEGADOR...
   - **Skills**: SPAMMER, CALCULISTA, ZONE_CONTROLLER...
   - **Mental**: VINGATIVO, ADAPTAVEL, CLUTCH_PLAYER, TILTER...
   - **Especiais**: SHOWMAN, TRICKSTER, WALL_FIGHTER, PILLAR_DANCER...

2. **25+ Arquétipos de Combate**:
   - Magos: MAGO, PIROMANTE, CRIOMANTE, INVOCADOR
   - Assassinos: NINJA, LADINO, SOMBRA
   - Guerreiros: BERSERKER, DUELISTA, GLADIADOR
   - Defensivos: SENTINELA, PALADINO, COLOSSO
   - Híbridos: LANCEIRO, ARQUEIRO, SAMURAI

3. **15+ Estilos de Luta**:
   - RANGED, BURST, TANK, HIT_RUN, COUNTER, BERSERK, OPPORTUNIST...

4. **30+ Quirks (Comportamentos Únicos)**:
   - Tiques, manias, reações específicas a situações

5. **14+ Filosofias de Combate**:
   - EQUILIBRIO, DOMINACAO, SOBREVIVENCIA, CAOS...

6. **Sistema de Humor Dinâmico**:
   - CALMO, FOCADO, IRRITADO, DESESPERADO, CONFIANTE, TILTED...

#### Sistema Emocional

```python
# Emoções da IA (0.0 a 1.0)
self.medo = 0.0
self.raiva = 0.0
self.confianca = 0.5
self.frustracao = 0.0
self.adrenalina = 0.0
self.excitacao = 0.0
self.tedio = 0.0
```

#### Recursos Avançados v10.0

- **Percepção de Armas**: A IA analisa a arma do oponente e adapta estratégia
- **Zonas de Ameaça**: Calcula áreas perigosas baseado no alcance da arma inimiga
- **Sweet Spots**: Reconhece distâncias ideais para cada tipo de arma
- **Consciência Espacial**: Usa paredes, obstáculos e bordas taticamente
- **Antecipação de Ataques**: Lê padrões do oponente e prevê movimentos
- **Sistema de Baiting**: Cria falsas aberturas para atrair ataques
- **Momentum e Pressão**: Mantém ou cede pressão baseado na situação

---

## ⚔️ SISTEMA DE COMBATE

### Classe Lutador (core/entities.py)

```python
class Lutador:
    # Posição e física
    pos = [x, y]        # Posição em metros
    vel = [vx, vy]      # Velocidade
    z = 0.0             # Altura (pulo)
    vel_z = 0.0         # Velocidade vertical
    raio_fisico         # Raio de colisão do corpo
    
    # Status
    vida / vida_max
    mana / mana_max
    estamina / estamina_max
    
    # Modificadores de classe
    mod_dano            # Multiplicador de dano
    mod_velocidade      # Multiplicador de velocidade
    mod_defesa          # Multiplicador de defesa
    
    # Skills
    skills_arma = []    # Skills da arma equipada
    skills_classe = []  # Skills da classe
    cd_skills = {}      # Cooldowns
    
    # Buffs e efeitos
    buffs_ativos = []
    dots_ativos = []    # Damage over time
    
    # Estados
    morto, invencivel_timer, stun_timer
    canalizando         # Para magos carregando magia
    atacando, modo_ataque_aereo
    
    # IA
    brain = AIBrain(self)
```

### Sistema de Hitbox (core/hitbox.py)

Detecção de colisão precisa baseada no tipo de arma:

```python
HITBOX_PROFILES = {
    "Reta": {       # Espadas, lanças
        "shape": "arc",
        "base_arc": 90,
        "range_mult": 2.0,
        "sweet_spot_start": 0.6,
        "sweet_spot_end": 1.0,
    },
    "Corrente": {   # Chicotes, mangual
        "shape": "sweep_arc",
        "base_arc": 180,
        "range_mult": 4.0,
        "has_dead_zone": True,  # Não acerta muito perto
    },
    "Dupla": {      # Adagas gêmeas
        "shape": "dual_arc",
        "base_arc": 60,
        "range_mult": 1.5,
    },
    # ... mais tipos
}
```

### Sistema de Skills (core/skills.py)

40+ habilidades organizadas por elemento:

```python
SKILL_DB = {
    # 🔥 FOGO
    "Bola de Fogo": {
        "tipo": "PROJETIL", "dano": 35.0, "velocidade": 11.0,
        "efeito": "EXPLOSAO", "custo": 25.0, "cooldown": 5.0
    },
    "Meteoro": {"tipo": "PROJETIL", "dano": 60.0, ...},
    "Explosão Nova": {"tipo": "AREA", "dano": 45.0, ...},
    
    # ❄️ GELO
    "Estilhaço de Gelo": {"tipo": "PROJETIL", "efeito": "CONGELAR", ...},
    "Nevasca": {"tipo": "AREA", "efeito": "CONGELAR", "duracao": 3.0},
    
    # ⚡ RAIO
    "Relâmpago": {"tipo": "BEAM", "efeito": "ATORDOAR", ...},
    "Teleporte Relâmpago": {"tipo": "DASH", "invencivel": True, ...},
    
    # 🌑 TREVAS
    "Esfera Sombria": {"tipo": "PROJETIL", "efeito": "DRENAR", ...},
    "Maldição": {"tipo": "PROJETIL", "efeito": "VENENO", "dot_dano": 5.0},
    
    # 💚 NATUREZA/VENENO
    "Espinhos": {"tipo": "PROJETIL", "multi_shot": 3, ...},
    "Raízes": {"tipo": "AREA", "efeito": "ATORDOAR", ...},
    
    # ⚔️ FÍSICO
    "Avanço Brutal": {"tipo": "DASH", "dano": 25.0, ...},
    "Fúria Giratória": {"tipo": "AREA", ...},
    
    # 🛡️ DEFESA/SUPORTE
    "Escudo Arcano": {"tipo": "BUFF", "escudo": 30.0, ...},
    "Cura Menor": {"tipo": "BUFF", "cura": 25.0, ...},
}
```

**Tipos de Skills**: PROJETIL, BUFF, AREA, DASH, SUMMON, BEAM

**Efeitos**: NORMAL, EMPURRAO, SANGRAMENTO, VENENO, EXPLOSAO, CONGELAR, ATORDOAR, QUEIMAR, DRENAR, PERFURAR

---

## 🗡️ SISTEMA DE ARMAS

### Classe Arma (models/weapons.py)

```python
class Arma:
    # Identificação
    nome: str
    tipo: str           # Reta, Dupla, Corrente, Arremesso, Arco, Orbital, Mágica, Transformável
    raridade: str       # Comum → Mítico (6 níveis)
    
    # Atributos base (modificados pela raridade)
    dano: float
    peso: float
    
    # Geometria por tipo
    # Reta: comp_cabo, comp_lamina, largura
    # Corrente: comp_corrente, comp_ponta
    # Arremesso: tamanho_projetil, quantidade
    # Arco: tamanho_arco, forca_arco, tamanho_flecha
    # Orbital: quantidade_orbitais, distancia
    # Mágica: tamanho, distancia_max
    # Transformável: forma1_*, forma2_*
    
    # Habilidades (múltiplas baseado na raridade)
    habilidades = []    # Até 4 skills para Mítico
    encantamentos = []  # Até 5 encantamentos para Mítico
    passiva = {}        # Passiva única
    
    # Stats extras
    critico: float              # Chance de crítico
    velocidade_ataque: float    # Multiplicador
    afinidade_elemento: str     # Elemento associado
    durabilidade: float
```

### Sistema de Raridade (models/constants.py)

```python
RARIDADES = {
    "Comum":     {"cor": (180, 180, 180), "slots_habilidade": 1, "mod_dano": 0.6},
    "Incomum":   {"cor": (100, 200, 100), "slots_habilidade": 1, "mod_dano": 0.7},
    "Raro":      {"cor": (80, 140, 255),  "slots_habilidade": 2, "mod_dano": 0.8},
    "Épico":     {"cor": (180, 80, 220),  "slots_habilidade": 2, "mod_dano": 0.9},
    "Lendário":  {"cor": (255, 180, 50),  "slots_habilidade": 3, "mod_dano": 1.0},
    "Mítico":    {"cor": (255, 100, 100), "slots_habilidade": 4, "mod_dano": 1.2},
}
```

### Tipos de Armas

| Tipo | Categoria | Descrição | Alcance Base |
|------|-----------|-----------|--------------|
| Reta | Melee | Espadas, lanças, maças | 1.5m |
| Dupla | Melee | Adagas gêmeas, kamas | 1.0m |
| Corrente | Melee | Chicotes, mangual | 3.0m |
| Arremesso | Ranged | Facas, chakrams | 8.0m |
| Arco | Ranged | Arcos, bestas | 12.0m |
| Orbital | Defensive | Escudos, orbes | 2.0m |
| Mágica | Magic | Espadas espectrais, runas | 4.0m |
| Transformável | Special | Muda de forma | 2.0m |

---

## 👤 SISTEMA DE CLASSES

### Classes Disponíveis (models/constants.py)

```python
CLASSES = {
    # GUERREIROS
    "Guerreiro (Força Bruta)": {
        "mod_forca": 1.3, "mod_vida": 1.2, "mod_velocidade": 0.9,
        "cor_aura": (200, 100, 50)
    },
    "Berserker (Fúria)": {
        "mod_forca": 1.5, "mod_vida": 1.0, "mod_velocidade": 1.1,
        "skills_afinidade": ["Fúria Berserker", "Execução"]
    },
    
    # ASSASSINOS
    "Assassino (Crítico)": {
        "mod_forca": 1.1, "mod_vida": 0.8, "mod_velocidade": 1.4,
        "mod_critico": 0.2
    },
    "Ninja (Velocidade)": {
        "mod_velocidade": 1.6, "skills_afinidade": ["Teleporte"]
    },
    
    # MAGOS
    "Mago (Arcano)": {
        "mod_mana": 1.5, "mod_forca": 0.7, "regen_mana": 5.0,
        "skills_afinidade": ["Disparo de Mana", "Escudo Arcano"]
    },
    "Piromante (Fogo)": {
        "mod_mana": 1.3, "skills_afinidade": ["Bola de Fogo", "Meteoro"]
    },
    
    # DEFENSIVOS
    "Cavaleiro (Defesa)": {
        "mod_vida": 1.5, "mod_defesa": 0.7, "mod_velocidade": 0.8
    },
    
    # ... 20+ classes totais
}
```

---

## 🏟️ SISTEMA DE ARENAS

### Arenas Disponíveis (core/arena.py)

```python
ARENAS = {
    "Arena": ArenaConfig(
        nome="Arena Clássica", largura=30.0, altura=20.0,
        formato="retangular", tema="classico", icone="🏟️"
    ),
    "Coliseu": ArenaConfig(
        nome="Coliseu Romano", largura=35.0, altura=35.0,
        formato="circular", tema="romano", icone="🏛️",
        obstaculos=[
            Obstaculo("pilar", 13.0, 17.5, 1.5, 1.5),
            Obstaculo("pilar", 22.0, 17.5, 1.5, 1.5),
            # ... 4 pilares
        ]
    ),
    "Floresta": ArenaConfig(
        nome="Clareira Sombria", largura=32.0, altura=24.0,
        tema="floresta", icone="🌲",
        obstaculos=[
            Obstaculo("arvore", 6.0, 6.0, 2.0, 2.0),
            Obstaculo("pedra", 10.0, 12.0, 1.2, 0.8),
            # ... múltiplas árvores e pedras
        ]
    ),
    "Vulcao": ArenaConfig(nome="Cratera Vulcânica", ...),
    "Dojo": ArenaConfig(nome="Dojo Sagrado", formato="octogono", ...),
    "Caverna": ArenaConfig(nome="Caverna de Cristais", ...),
    "Castelo": ArenaConfig(nome="Salão do Trono", ...),
    # ... 15+ arenas totais
}
```

---

## 🎬 SISTEMA DE GAME FEEL

### HitStopManager (core/game_feel.py)

Congela o jogo momentaneamente em impactos para dar peso aos golpes:

```python
HITSTOP_FRAMES = {
    "LEVE": 2,       # ~33ms - golpes leves
    "MEDIO": 4,      # ~66ms - golpes normais
    "PESADO": 8,     # ~133ms - golpes pesados
    "DEVASTADOR": 12, # ~200ms - finalizadores
    "EPICO": 18,     # ~300ms - execuções
}

# Multiplicadores por classe
CLASS_HITSTOP_MULT = {
    "Berserker (Fúria)": 1.8,    # Impacto máximo
    "Assassino (Crítico)": 0.5,  # Mínimo para manter fluidez
    # ...
}
```

### Super Armor System

Permite que certas classes absorvam golpes sem interrupção:

```python
SUPER_ARMOR_CONFIG = {
    "Berserker (Fúria)": {
        "ativacao": "ataque",
        "reducao_dano": 0.5,
        "knockback_resist": 1.0,
    },
    "Cavaleiro (Defesa)": {
        "ativacao": "sempre_ativo",
        "reducao_dano": 0.25,
    },
}
```

### Channeling System

Sistema de carga para magias poderosas:

```python
CHANNELING_CONFIG = {
    "Piromante (Fogo)": {
        "tempo_base": 2.0,
        "bonus_dano_max": 3.0,
        "interruptivel": True,
    },
}
```

---

## 🔊 SISTEMA DE ÁUDIO

### AudioManager (effects/audio.py)

Sistema de áudio procedural com fallback sintético:

```python
# Categorias de Sons
SOUND_CATEGORIES = {
    # Golpes Físicos
    "punch": ["punch_light", "punch_medium", "punch_heavy"],
    "kick": ["kick_light", "kick_heavy", "kick_spin"],
    "slash": ["slash_light", "slash_heavy", "slash_critical"],
    
    # Magias
    "fireball": ["fireball_cast", "fireball_fly", "fireball_impact"],
    "ice": ["ice_cast", "ice_shard", "ice_impact"],
    "lightning": ["lightning_charge", "lightning_bolt", "lightning_impact"],
    
    # Skills Especiais
    "dash": ["dash_whoosh", "dash_impact"],
    "teleport": ["teleport_out", "teleport_in"],
    "buff": ["buff_activate", "buff_pulse"],
    "shield": ["shield_up", "shield_block", "shield_break"],
    
    # Eventos
    "ko_impact", "combo_hit", "counter_hit", "perfect_block"
}
```

**Recursos**:
- 32 canais simultâneos
- Áudio posicional (pan estéreo baseado na posição)
- Atenuação por distância
- Geração procedural de sons se arquivos não existirem

---

## 📹 SISTEMA DE CÂMERA

### Câmera (effects/camera.py)

Sistema de câmera dinâmica "bulletproof" que nunca perde os lutadores:

```python
class Câmera:
    # Modos
    modo = "AUTO"  # AUTO, P1, P2, FIXO, MANUAL
    
    # Zoom
    zoom = 0.8
    zoom_min = 0.15  # Pode mostrar arena ENORME
    zoom_max = 1.6   # Zoom máximo
    
    # Shake
    shake_magnitude = 0.0
    shake_timer = 0.0
    
    # Margem de segurança
    margem_segura = 120      # Margem ideal
    margem_critica = 20      # Se passar, zoom imediato
    
    # Velocidades
    velocidade_zoom_out = 15.0  # Rápido para não perder lutador
    velocidade_zoom_in = 2.0    # Suave
```

---

## 🎭 SISTEMA DE COREOGRAFIA

### CombatChoreographer (ai/choreographer.py)

Coordena momentos cinematográficos entre as IAs:

```python
class CombatChoreographer:
    # Estados de momento
    momento_atual = "NEUTRO"  # NEUTRO, TENSAO, TROCA, CLIMAX, RESOLUCAO
    
    # Intensidade (0.0 a 1.0)
    intensidade = 0.0
    climax_atingido = False
    
    # Ritmo da luta
    ritmo_atual = "NEUTRO"  # NEUTRO, AGRESSIVO, CAUTELOSO, EXPLOSIVO
    
    # Fluxo de combate
    fluxo_direcao = 0  # -1 = L1 recuando, 0 = neutro, 1 = L2 recuando
    
    # Momentos Cinematográficos Detectados:
    # - "CLASH_MAGICO": Dois projéteis colidem
    # - "TROCA_DE_GOLPES": Ambos acertam simultaneamente
    # - "EXECUCAO": Golpe final com estilo
    # - "REVERSAO": Lutador perdendo vira o jogo
    # - "ULTIMO_SUSPIRO": Quase morrendo, golpe desesperado
```

---

## 🖥️ INTERFACE DO USUÁRIO

### Launcher (ui/main.py)

Interface Tkinter com múltiplas telas:

1. **Menu Principal**: Navegação entre seções
2. **Forjar Armas** (view_armas.py): Criar/editar armas
3. **Criar Personagens** (view_chars.py): Criar/editar lutadores
4. **Configurar Luta** (view_luta.py): Selecionar lutadores e arena
5. **Configurar Sons** (view_sons.py): Personalizar efeitos sonoros

### Comandos da Simulação

| Tecla | Ação |
|-------|------|
| ESC | Sair |
| R | Recarregar luta |
| SPACE | Pausar/Resumir |
| G | Toggle HUD |
| H | Toggle Debug de Hitbox |
| TAB | Toggle Análise |
| T | Slow Motion (0.2x) |
| F | Fast Forward (3.0x) |
| 1/2/3 | Câmera P1/P2/AUTO |
| WASD | Mover câmera manual |
| Scroll | Zoom |

---

## 📊 CONFIGURAÇÕES GLOBAIS

### Física (utils/config.py)

```python
PPM = 50              # Pixels por metro
GRAVIDADE_Z = 35.0    # Gravidade para pulos
ATRITO = 8.0          # Coeficiente de atrito
ALTURA_PADRAO = 1.70  # Altura base de referência

LARGURA, ALTURA = 1200, 800  # Resolução da tela
FPS = 60
```

---

## 🔧 COMO ADICIONAR/MODIFICAR

### Adicionar Nova Arma

1. Edite `data/armas.json` ou use a UI
2. Campos obrigatórios: nome, tipo, dano, peso
3. Campos opcionais dependem do tipo

### Adicionar Nova Skill

1. Edite `core/skills.py` → `SKILL_DB`
2. Defina: tipo, dano, custo, cooldown, efeito

### Adicionar Novo Traço de IA

1. Edite `ai/personalities.py`
2. Adicione à lista apropriada (TRACOS_AGRESSIVIDADE, etc)
3. Implemente comportamento em `ai/brain.py`

### Adicionar Nova Arena

1. Edite `core/arena.py` → `ARENAS`
2. Defina: nome, dimensões, obstáculos, tema

### Adicionar Nova Classe

1. Edite `models/constants.py` → `CLASSES`
2. Defina modificadores e skills de afinidade

---

## 📁 ARQUIVOS DE DADOS

### personagens.json
```json
{
    "nome": "Magnus",
    "tamanho": 1.87,
    "forca": 9.0,
    "mana": 5.0,
    "nome_arma": "Chicote de Couro",
    "cor_r": 220, "cor_g": 120, "cor_b": 60,
    "classe": "Guerreiro (Força Bruta)"
}
```

### armas.json
```json
{
    "nome": "Espada Flamejante",
    "tipo": "Reta",
    "dano": 6.0,
    "peso": 4.0,
    "raridade": "Raro",
    "comp_cabo": 18.0,
    "comp_lamina": 60.0,
    "habilidades": ["Fireball", "Dash"],
    "encantamentos": ["Chamas"],
    "passiva": {"nome": "Queimadura", "tier": "minor"},
    "critico": 7.2,
    "velocidade_ataque": 1.05
}
```

### match_config.json
```json
{
    "p1_nome": "Magnus",
    "p2_nome": "Thorkell",
    "cenario": "Coliseu"
}
```

---

## 🎯 RESUMO TÉCNICO

| Aspecto | Tecnologia/Abordagem |
|---------|---------------------|
| **Linguagem** | Python 3.x |
| **Renderização** | Pygame |
| **UI** | Tkinter |
| **Persistência** | JSON |
| **Arquitetura IA** | Procedural + Comportamental |
| **Física** | 2D com simulação de altura (Z) |
| **Áudio** | Pygame mixer + Geração procedural |
| **Padrões** | Singleton (managers), Entity-Component |

---

## 📝 NOTAS PARA A IA

1. **O projeto é modular** - cada sistema pode ser modificado independentemente
2. **A IA é o coração** - brain.py tem 3400+ linhas de comportamento
3. **Dados são JSON** - fácil de editar manualmente ou via UI
4. **Physics usa metros** - conversão para pixels via PPM
5. **Skills são data-driven** - adicionar nova skill é só adicionar ao SKILL_DB
6. **Arenas suportam obstáculos** - colisões são calculadas automaticamente
7. **O sistema de raridade escala tudo** - dano, velocidade, slots de skill
8. **Audio tem fallback** - se arquivo não existe, gera som procedural
9. **Câmera é "bulletproof"** - nunca perde os lutadores de vista
10. **Game Feel é crítico** - hit stop, shake, super armor fazem diferença

---

*Documento gerado para contextualização de IA - Neural Fights v10.0*
