# ðŸ”Š Sistema de Ãudio Neural Fights v10.0

## ðŸ“‹ VisÃ£o Geral

Sistema completo de Ã¡udio procedural integrado ao Neural Fights, adicionando feedback sonoro para todos os aspectos do combate: golpes fÃ­sicos, magias, skills, impactos, bloqueios e eventos especiais.

## ðŸŽµ CaracterÃ­sticas

### âœ¨ GeraÃ§Ã£o Procedural de Sons
- **Sons sintÃ©ticos** gerados em tempo real quando arquivos de Ã¡udio nÃ£o estÃ£o disponÃ­veis
- Cada categoria tem perfis Ãºnicos de onda sonora
- Sistema baseado em **numpy** para sÃ­ntese de audio
- **Fallback inteligente**: usa sons procedurais se arquivos reais nÃ£o existirem

### ðŸŽ¯ Ãudio Posicional
- **Pan estÃ©reo** baseado na posiÃ§Ã£o do som na tela
- **AtenuaÃ§Ã£o por distÃ¢ncia** automÃ¡tica
- Som segue a posiÃ§Ã£o da cÃ¢mera (listener)
- Suporte para atÃ© **32 canais simultÃ¢neos**

### ðŸŽ® Categorias de Sons

#### 1. **Golpes FÃ­sicos**
- `punch` (soco leve, mÃ©dio, pesado)
- `kick` (chute leve, pesado, giratÃ³rio)
- `slash` (cortes de espada leve, pesado, crÃ­tico)
- `stab` (estocadas rÃ¡pidas e profundas)

#### 2. **Impactos**
- `impact` (impacto em carne, pesado, crÃ­tico)
- Volume e intensidade baseados no dano causado
- Sons diferentes para hits crÃ­ticos e counters

#### 3. **Magias e ProjÃ©teis**
- `fireball` (cast, voar, impacto)
- `ice` (cast, estilhaÃ§o, impacto)
- `lightning` (carregar, raio, impacto)
- `energy` (carregar, disparo, impacto)
- `beam` (carregar, disparar, fim)

#### 4. **Skills Especiais**
- `dash` (whoosh, impacto)
- `teleport` (saÃ­da, entrada)
- `buff` (ativar, pulso)
- `heal` (cast, completar)
- `shield` (subir, bloquear, quebrar)

#### 5. **Movimentos**
- `jump` (inÃ­cio, aterrissagem)
- `footstep` (4 variaÃ§Ãµes)
- `dodge` (whoosh, deslizar)

#### 6. **Ambiente**
- `wall_hit` (impacto leve/pesado na parede)
- `ground_slam` (impacto no chÃ£o)

#### 7. **Eventos Especiais**
- `ko_impact` (nocaute fatal)
- `combo_hit` (combo)
- `counter_hit` (contra-ataque)
- `perfect_block` (bloqueio perfeito)
- `stagger` (atordoamento)

## ðŸ› ï¸ API do AudioManager

### InicializaÃ§Ã£o
```python
from audio import AudioManager

# Singleton - sempre retorna a mesma instÃ¢ncia
audio = AudioManager.get_instance()

# Reset (Ãºtil para recarregar)
AudioManager.reset()
```

### MÃ©todos Principais

#### `play(sound_name, volume=1.0, pan=0.0)`
Toca um som bÃ¡sico.
```python
audio.play("punch", volume=0.8)  # 80% do volume
audio.play("fireball_cast", volume=1.0, pan=-0.5)  # Pan para esquerda
```

#### `play_positional(sound_name, pos_x, listener_x, max_distance=20.0, volume=1.0)`
Toca som com posicionamento espacial.
```python
# Som na posiÃ§Ã£o x=10, ouvinte em x=5
audio.play_positional("impact", 10.0, 5.0, volume=0.9)
```

#### `play_attack(attack_type, pos_x=0, listener_x=0)`
Toca som de ataque baseado no tipo.
```python
audio.play_attack("SOCO", pos_x=5.0, listener_x=0.0)
audio.play_attack("ESPADADA", pos_x=lutador.pos[0], listener_x=camera.x)
```

**Tipos suportados:**
- `"SOCO"` â†’ punch
- `"CHUTE"` â†’ kick
- `"ESPADADA"` â†’ slash
- `"MACHADADA"` â†’ slash
- `"FACADA"` â†’ stab
- `"ARCO"` â†’ energy
- `"MAGIA"` â†’ energy

#### `play_impact(damage, pos_x=0, listener_x=0, is_critical=False, is_counter=False)`
Toca som de impacto proporcional ao dano.
```python
# Impacto normal
audio.play_impact(25.0, lutador.pos[0], camera.x)

# Impacto crÃ­tico
audio.play_impact(45.0, lutador.pos[0], camera.x, is_critical=True)

# Contra-ataque
audio.play_impact(30.0, lutador.pos[0], camera.x, is_counter=True)
```

**LÃ³gica automÃ¡tica:**
- Dano > 50 â†’ `impact_heavy`
- CrÃ­tico â†’ `impact_critical`
- Counter â†’ `counter_hit`
- Normal â†’ `impact`

#### `play_skill(skill_type, skill_name="", pos_x=0, listener_x=0, phase="cast")`
Toca som de skill baseado no tipo e fase.
```python
# Cast de projÃ©til
audio.play_skill("PROJETIL", "Bola de Fogo", pos_x=5.0, phase="cast")

# Impacto de Ã¡rea
audio.play_skill("AREA", "ExplosÃ£o", pos_x=10.0, phase="impact")

# Beam ativo
audio.play_skill("BEAM", "Laser", pos_x=5.0, phase="active")
```

**Tipos suportados:**
- `"PROJETIL"` â†’ fireball/ice/lightning/energy (depende do nome)
- `"BEAM"` â†’ beam_charge/fire/end
- `"AREA"` â†’ energy_impact/fireball_impact/ice_impact
- `"DASH"` â†’ dash_whoosh/impact
- `"BUFF"` â†’ buff_activate/heal_cast/shield_up
- `"TELEPORT"` â†’ teleport_out/in

**Fases:**
- `"cast"` - InÃ­cio da skill
- `"fly"/"active"` - Durante a execuÃ§Ã£o
- `"impact"` - Acerto no alvo

#### `play_movement(movement_type, pos_x=0, listener_x=0)`
Sons de movimento.
```python
audio.play_movement("jump", pos_x=lutador.pos[0])
audio.play_movement("dodge", pos_x=lutador.pos[0])
audio.play_movement("footstep", pos_x=lutador.pos[0])
```

#### `play_special(event_type, volume=0.8)`
Eventos especiais do jogo.
```python
audio.play_special("ko", volume=1.0)
audio.play_special("perfect_block", volume=0.9)
audio.play_special("wall_hit", volume=0.6)
```

### Controles de Volume

```python
# Volume mestre (afeta tudo)
audio.set_master_volume(0.7)  # 70%

# Volume de efeitos sonoros
audio.set_sfx_volume(0.8)  # 80%

# Liga/desliga Ã¡udio
audio.toggle_enable()

# Para todos os sons
audio.stop_all()
```

## ðŸŽ¨ IntegraÃ§Ã£o no CÃ³digo

### No Simulador (simulacao.py)
```python
from audio import AudioManager

class Simulador:
    def __init__(self):
        # ...
        self.audio = None
    
    def recarregar_tudo(self):
        # ...
        AudioManager.reset()
        self.audio = AudioManager.get_instance()
```

### Em Ataques FÃ­sicos
```python
# Quando ataque acerta
if acertou:
    if self.audio:
        listener_x = self.cam.x / PPM
        self.audio.play_attack(tipo_ataque, atacante.pos[0], listener_x)
    
    # ApÃ³s aplicar dano
    if self.audio:
        self.audio.play_impact(dano, defensor.pos[0], listener_x, 
                              is_critico, is_counter)
```

### Em Skills (entities.py)
```python
def usar_skill_arma(self, skill_idx=None):
    from audio import AudioManager
    # ...
    
    if tipo == "PROJETIL":
        audio = AudioManager.get_instance()
        if audio:
            audio.play_skill("PROJETIL", nome_skill, self.pos[0], phase="cast")
        # Cria projÃ©til...
```

### Em ProjÃ©teis (simulacao.py)
```python
if colidiu and proj.ativo:
    if self.audio:
        listener_x = self.cam.x / PPM
        self.audio.play_skill("PROJETIL", tipo_proj, proj.x, 
                             listener_x, phase="impact")
```

### Em Eventos Especiais
```python
# Bloqueio
if bloqueou:
    if self.audio:
        self.audio.play_special("shield_block", volume=0.7)

# ColisÃ£o com parede
if colidiu_parede:
    if self.audio:
        volume = min(1.0, velocidade / 15) * 0.6
        self.audio.play_special("wall_hit", volume=volume)

# KO
if morreu:
    if self.audio:
        self.audio.play_special("ko", volume=1.0)
```

## ðŸ“ Estrutura de Arquivos

### Arquivos de Som (Opcional)
Se vocÃª quiser usar sons reais ao invÃ©s dos procedurais, crie:
```
neural/
â”œâ”€â”€ sounds/
â”‚   â”œâ”€â”€ punch_light.wav
â”‚   â”œâ”€â”€ punch_medium.wav
â”‚   â”œâ”€â”€ kick_heavy.wav
â”‚   â”œâ”€â”€ fireball_cast.wav
â”‚   â”œâ”€â”€ ice_impact.wav
â”‚   â”œâ”€â”€ beam_fire.wav
â”‚   â””â”€â”€ ...
```

**Formatos suportados:** `.wav`, `.ogg`, `.mp3`

### Arquivos do Sistema
- `audio.py` - AudioManager e sistema completo
- `simulacao.py` - IntegraÃ§Ã£o com combate
- `nucleo/entities.py` - IntegraÃ§Ã£o com skills

## ðŸ”§ PersonalizaÃ§Ã£o

### Adicionando Novos Sons

1. **Som procedural:**
   Adicione lÃ³gica em `_generate_procedural_sound()`:
   ```python
   elif "novo_som" in name:
       # Sua lÃ³gica de sÃ­ntese aqui
       wave = np.sin(2 * np.pi * 440 * t)
   ```

2. **Som de arquivo:**
   - Coloque o arquivo em `sounds/`
   - Nome: `categoria_variante.wav`
   - O sistema carrega automaticamente

### Adicionando Grupos de Sons

```python
def _setup_sounds(self):
    # Adicione um novo grupo
    self._register_sound_group("meu_grupo", [
        "som_1", "som_2", "som_3"
    ])
```

### Alterando Volume Base

```python
# No cÃ³digo
audio.play_skill("AREA", "ExplosÃ£o", volume=1.2)  # 120% (mÃ¡ximo)

# Globalmente
audio.set_sfx_volume(0.5)  # 50% de todos os efeitos
```

## ðŸŽ¯ Boas PrÃ¡ticas

1. **Use Ã¡udio posicional** quando relevante:
   ```python
   audio.play_positional("impact", lutador.pos[0], camera.x)
   ```

2. **Ajuste volume por contexto:**
   - Passos: 0.3
   - Hits normais: 0.6-0.8
   - Skills: 0.7-0.9
   - KO/eventos especiais: 1.0

3. **Sempre cheque se audio existe:**
   ```python
   if self.audio:
       self.audio.play(...)
   ```

4. **Use nomes descritivos de skills:**
   - Ajuda o sistema escolher sons adequados
   - "Bola de Fogo" â†’ som de fogo
   - "LanÃ§a de Gelo" â†’ som de gelo

## ðŸ› Troubleshooting

### Sem som?
1. Verifique se pygame.mixer inicializou: `pygame.mixer.get_init()`
2. Verifique volume: `audio.master_volume` e `audio.sfx_volume`
3. Verifique se estÃ¡ habilitado: `audio.enabled`

### Sons cortando?
- Aumente nÃºmero de canais: `pygame.mixer.set_num_channels(64)`

### Performance ruim?
- Desabilite sons procedurais (use arquivos)
- Reduza nÃºmero de sons simultÃ¢neos
- Simplifique sÃ­ntese em `_generate_procedural_sound()`

### Numpy nÃ£o instalado?
- Sons procedurais nÃ£o funcionarÃ£o
- Sistema usa silÃªncio como fallback
- Instale: `pip install numpy`

## ðŸ“Š EstatÃ­sticas do Sistema

- **Grupos de sons:** 14 categorias principais
- **Variantes:** 40+ sons diferentes
- **Canais simultÃ¢neos:** 32
- **Formato interno:** 44.1kHz, 16-bit, estÃ©reo
- **Buffer:** 512 samples (baixa latÃªncia)
- **AtenuaÃ§Ã£o:** AtÃ© 20 metros de distÃ¢ncia

## ðŸŽ¬ Exemplos Completos

### Exemplo 1: Combo System
```python
# A cada hit do combo
audio.play_attack("SOCO", lutador.pos[0], camera.x)
audio.play_impact(dano, alvo.pos[0], camera.x)

# No Ãºltimo hit
if combo_finalizado:
    audio.play_special("combo", volume=1.0)
```

### Exemplo 2: Skill Completa
```python
# Cast
audio.play_skill("PROJETIL", "Bola de Fogo", pos_x, phase="cast")

# ProjÃ©til voando (opcional)
# audio.play_skill("PROJETIL", "Bola de Fogo", pos_x, phase="fly")

# Impacto
audio.play_skill("PROJETIL", "Bola de Fogo", pos_x, phase="impact")
```

### Exemplo 3: Boss Fight
```python
# Entrada do boss
audio.play_special("ground_slam", volume=1.0)

# Ataques especiais
if boss_ataque_especial:
    audio.play_skill("BEAM", "Laser Destruidor", boss.pos[0], phase="cast")
    # ... depois
    audio.play_skill("BEAM", "Laser Destruidor", boss.pos[0], phase="active")
```

## ðŸš€ Melhorias Futuras

- [ ] Sistema de mÃºsica ambiente por arena
- [ ] Efeitos de reverb baseados no ambiente
- [ ] Filtros de Ã¡udio em slow-motion
- [ ] Sons especÃ­ficos por arma/personagem
- [ ] Sistema de vozes (grunts, gritos)
- [ ] Carregar sons de mod packs
- [ ] Editor de sons procedurais in-game

---

## ðŸ“ž Suporte

Para dÃºvidas sobre o sistema de Ã¡udio:
1. Leia este documento
2. Veja exemplos em `simulacao.py` e `entities.py`
3. Teste com `audio = AudioManager.get_instance()`

**Neural Fights v10.0 - AUDIO EDITION** ðŸŽµ

