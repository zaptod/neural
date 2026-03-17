# ðŸ§  ROADMAP: AI OVERHAUL â€” "O Ecossistema Vivo"

## DIAGNÃ“STICO ATUAL

### Problemas Identificados

| # | Problema | Severidade | Onde |
|---|---------|-----------|------|
| 1 | Personalidades influenciam IA apenas Â±0.1~0.2 nos pesos | CRÃTICO | brain_combat.py |
| 2 | Classes sÃ³ afetam stats numÃ©ricos, passivas sÃ£o texto decorativo | CRÃTICO | constants.py |
| 3 | Sem habilidades de classe implementadas no combate | CRÃTICO | â€” (nÃ£o existe) |
| 4 | Sem sinergias classe+personalidade+arma+encantamento | ALTO | â€” (nÃ£o existe) |
| 5 | Berserker e Cauteloso lutam 90% parecido | ALTO | brain_combat.py |
| 6 | TraÃ§os existem (120+) mas maioria nunca Ã© checada na IA | MÃ‰DIO | brain_combat.py |
| 7 | Apenas 17 classes, sem subclasses ou variaÃ§Ãµes | MÃ‰DIO | constants.py |
| 8 | Sem mecÃ¢nicas roguelike (mutaÃ§Ãµes, eventos, evoluÃ§Ã£o) | MÃ‰DIO | â€” (nÃ£o existe) |
| 9 | Quirks definidos mas poucos implementados de verdade | MÃ‰DIO | brain_emotions.py |

---

## ARQUITETURA DE SEGURANÃ‡A

### PrincÃ­pio: "Addon, NÃ£o Override"
Cada fase adiciona novos mÃ³dulos/funÃ§Ãµes. O cÃ³digo existente NÃƒO Ã© deletado â€” apenas recebe hooks opcionais.

### Mecanismo de Fallback
```python
# Exemplo: toda nova funcionalidade tem guard
try:
    bonus = synergy_engine.calculate(fighter)
except Exception:
    bonus = SynergyBonus()  # neutro, zero impacto
```

### Testes por Fase
Cada fase inclui testes que validam:
1. âœ… O jogo roda sem erros
2. âœ… Personalidades antigas continuam funcionando
3. âœ… Novos sistemas podem ser desligados (feature flags)

---

## FASE 1: "IDENTIDADE" â€” Personalidades com Alma
> Tornar cada personalidade REALMENTE diferente no combate

### 1.1 â€” Personality Weight Amplifier 
**O quÃª**: Multiplicar o impacto dos traÃ§os de 0.1~0.2 para 0.4~1.5
**Onde**: `brain_combat.py` â†’ `_estrategia_generica()`
**SeguranÃ§a**: Pesos capped em [0, 5.0], normalizaÃ§Ã£o final

### 1.2 â€” Personality Behavior Profiles
**O quÃª**: Cada personalidade preset ganha um "perfil de comportamento" que define regras exclusivas
**Onde**: NOVO `ia/behavior_profiles.py`
**Dados**:
```python
BEHAVIOR_PROFILES = {
    "Agressivo": {
        "recuar_threshold": 0.15,     # SÃ³ recua com <15% HP (vs 35% normal)
        "ataque_min_chance": 0.7,     # Chance mÃ­nima de atacar se no alcance
        "perseguir_sempre": True,     # Nunca desiste de perseguir
        "dano_recebido_reacao": "RAIVA",  # Leva dano â†’ fica mais agressivo
        "bloqueio_mult": 0.3,        # Quase nunca bloqueia
        "esquiva_mult": 0.5,         # Raramente esquiva
        "combo_tendencia": 1.5,      # Tenta combos agressivos
    },
    "Defensivo": {
        "recuar_threshold": 0.50,     # Recua com 50% HP
        "ataque_min_chance": 0.3,     # Ataca pouco
        "perseguir_sempre": False,    
        "dano_recebido_reacao": "RECUAR",
        "bloqueio_mult": 2.0,        # Bloqueia muito
        "esquiva_mult": 1.5,         # Esquiva bastante
        "combo_tendencia": 0.5,      # Combos conservadores
    },
    # ... cada preset dos 24 existentes
}
```

### 1.3 â€” Trait Impact Overhaul
**O quÃª**: Cada um dos 120+ traÃ§os ganha impacto real e mensurÃ¡vel
**Onde**: `brain_combat.py` seÃ§Ã£o 2 e 4 da estratÃ©gia genÃ©rica
**MÃ©todo**: Tabela de lookup `TRAIT_EFFECTS[trait] â†’ {action: weight}`

### 1.4 â€” Fidelidade Emocional
**O quÃª**: EmoÃ§Ãµes (raiva, medo, etc.) passam a ter impacto 3x maior.
Um Berserker com raiva mÃ¡xima Ã© DRASTICAMENTE mais perigoso.
**Onde**: `brain_emotions.py`, `brain_combat.py`

**Testes**: `test_personality_fidelity.py` â€” valida que Agressivo ataca 2x mais que Defensivo

---

## FASE 2: "PODERES" â€” Habilidades de Classe e Personalidade
> Cada classe e personalidade ganha habilidades ativas e passivas Ãºnicas

### 2.1 â€” Class Ability System
**O quÃª**: NOVO sistema de habilidades vinculadas Ã  classe
**Onde**: NOVO `ia/class_abilities.py`
**Estrutura**:
```python
CLASS_ABILITIES = {
    "Guerreiro (ForÃ§a Bruta)": {
        "passiva": {
            "nome": "Golpe Devastador",
            "efeito": "physical_damage_mult",
            "valor": 1.10,  # +10% dano fÃ­sico
        },
        "ativa": {
            "nome": "Grito de Guerra",
            "tipo": "BUFF",
            "efeito": "attack_speed_boost",
            "valor": 0.25, # +25% velocidade de ataque
            "duracao": 5.0,
            "cooldown": 20.0,
            "custo_mana": 15,
            "trigger": "combat_start",  # Quando usar automaticamente
        },
        "ultimate": {  # SÃ³ ativa com condiÃ§Ã£o especial
            "nome": "FÃºria do Guerreiro",
            "tipo": "BUFF",
            "efeito": "damage_and_speed_burst",
            "valor": 0.50,
            "duracao": 3.0,
            "cooldown": 45.0,
            "custo_mana": 30,
            "trigger": "hp_below_30",
        },
    },
    # ... 16 classes restantes + NOVAS classes
}
```

### 2.2 â€” Personality Passive Abilities
**O quÃª**: Cada personalidade preset ganha 1-2 passivas temÃ¡ticas
**Exemplos**:
- Berserker: "Sede de Sangue" (dano +2% por cada 10% de HP perdido)
- Fantasma: "IntocÃ¡vel" (cada esquiva dÃ¡ +5% velocidade por 2s, stacks 3x)
- Samurai: "Iai" (primeiro ataque causa 50% mais dano)
- Psicopata: "Sangue Frio" (emoÃ§Ãµes nÃ£o afetam decisÃµes, +15% dano em targets abaixo de 30% HP)

### 2.3 â€” Ability Integration na IA
**Onde**: `brain_skills.py` â€” novo priority slot para class abilities

**Testes**: `test_class_abilities.py` â€” valida que cada classe tem passiva+ativa funcionando

---

## FASE 3: "SINERGIA" â€” O Ecossistema Completo
> Classe + Personalidade + Arma + Skills + Encantamento formam um todo coerente

### 3.1 â€” Synergy Engine
**Onde**: NOVO `ia/synergy_engine.py`
```python
class SynergyEngine:
    def calculate(self, fighter) -> SynergyBonus:
        """Analisa TUDO do fighter e retorna bÃ´nus/estratÃ©gias"""
        # Classe â†” Arma: Mago + Arma MÃ¡gica = +20% dano
        # Classe â†” Encantamento: Piromante + Chamas = +15% fire dmg  
        # Personalidade â†” Classe: Berserker(pers) + Berserker(class) = "Pure Berserker" buff
        # Arma â†” Skills: Arco + skills de range = +10% range
        # ComposiÃ§Ã£o completa: avalia harmonia geral â†’ bÃ´nus ou penalidade
```

### 3.2 â€” AI Strategy Advisor
**O quÃª**: IA calcula a melhor estratÃ©gia baseada em TUDO que tem disponÃ­vel
**Onde**: Novo mÃ©todo `_calcular_estrategia_sinergica()` em brain_combat.py
- Piromante + Chamas + Bola de Fogo â†’ IA prioriza combos de fogo
- Ninja + Dupla + Assassino â†’ IA prioriza hit-and-run
- Cavaleiro + Orbital + Defensivo â†’ IA prioriza posiÃ§Ã£o e bloqueio

### 3.3 â€” Anti-Synergy Penalties
- Criomante + Encantamento de Fogo â†’ conflito elemental, -5% eficiÃªncia
- Berserker(classe) + Defensivo(personalidade) â†’ identidade confusa, decisÃµes mais lentas

**Testes**: `test_synergy_engine.py` â€” tabela de sinergias conhecidas validada

---

## FASE 4: "EXPANSÃƒO" â€” Mais Classes, Mais Personalidades
> Vasta gama de opÃ§Ãµes

### 4.1 â€” Novas Classes (17 â†’ 40+)
Grupos novos a adicionar:

**Elementais (6)**:
- Aeromante (Vento), Geomante (Terra), TempestÃ¡rio (Tempestade)  
- Cronomante (Tempo), Graviturgo (Gravidade), Alquimista (TransmutaÃ§Ã£o)

**Combate Especializado (6)**:
- BÃ¡rbaro (FÃºria Primitiva), Espadachim (LÃ¢mina), Lanceiro (Alcance)
- Arqueiro (PrecisÃ£o), Cavaleiro Negro (CorrupÃ§Ã£o), Patrulheiro (Rastreio)

**ExÃ³ticos (6)**:
- XamÃ£ (EspÃ­ritos), Bardo (MÃºsica), RÃºnico (Runas)
- PsÃ­quico (Mente), ArtÃ­fice (Construtos), Invocador (Criaturas)

**HÃ­bridos AvanÃ§ados (5)**:
- Arcano Guerreiro (Magia+Espada), Sacerdote Sombrio (Cura+Trevas)
- CaÃ§ador de DemÃ´nios (Anti-magia), Cavaleiro DragÃ£o (Draconico)
- Sentinela do Tempo (Tempo+Defesa)

### 4.2 â€” Novas Personalidades (24 â†’ 50+)
Presets novos:
- Estrategista, Provocador, Covarde TÃ¡tico, SÃ¡dico, Monge Zen
- Gladiador (Showoff), MercenÃ¡rio (PrÃ¡tico), Selvagem, Resistente
- Kamikaze, Trapaceiro, Imortal, Senhor da Guerra, Eremita
- Mestre dos Venenos, Cavaleiro Errante, Mestre Chi, Pistoleiro
- RelÃ¢mpago Humano, LeÃ£o, EscorpiÃ£o, Cobra, FÃªnix, Tartaruga
- VÃ³rtice, Maremoto, Avalanche

### 4.3 â€” Skill Tree Visualization
**Onde**: NOVO `interface/view_skill_tree.py`
- Ãrvore visual de habilidades por classe
- Mostra sinergias com cores e conexÃµes
- Combos possÃ­veis destacados

**Testes**: `test_new_classes.py` â€” valida que todas as novas classes tÃªm dados completos

---

## FASE 5: "ROGUELIKE" â€” Imprevisibilidade e EvoluÃ§Ã£o
> MecÃ¢nicas que tornam cada luta Ãºnica

### 5.1 â€” MutaÃ§Ãµes de Combate
Cada luta/round do torneio, personagens ganham 1-2 mutaÃ§Ãµes randÃ´micas:
```python
MUTACOES = {
    "MÃ£os de Vidro": {"dano_mult": 1.5, "vida_mult": 0.7},
    "Vampirismo": {"lifesteal": 0.15, "regen": -0.5},
    "Sobrecarga Arcana": {"skill_dano_mult": 1.3, "skill_custo_mult": 1.5},
    "Escudo de Ferro": {"defesa_mult": 1.4, "velocidade_mult": 0.8},
    "Berserker Curse": {"dano_mult": 1.0 + (1.0 - hp_pct) * 0.5},
    # ... 50+ mutaÃ§Ãµes
}
```

### 5.2 â€” Eventos de Combate
Eventos aleatÃ³rios durante a luta:
- Chuva de Meteoros (zona de perigo no mapa)
- Buff de Arena (item aparece no chÃ£o)
- Terremoto (empurra todos)
- Eclipse (visÃ£o reduzida, dano sombrio +30%)
- MarÃ© de Mana (mana regenera 3x mais rÃ¡pido)

### 5.3 â€” EvoluÃ§Ã£o por Torneio
Cada vitÃ³ria no torneio permite escolher 1 upgrade:
- +10% dano, +15% HP, nova skill, mutaÃ§Ã£o permanente, etc.
- Sistema de "relÃ­quias" (itens passivos cumulativos)

### 5.4 â€” Builds LendÃ¡rias  
CombinaÃ§Ãµes raras que desbloqueiam habilidades Ãºnicas:
```python
LEGENDARY_BUILDS = {
    "Avatar do Fogo": {
        "requer": {"classe": "Piromante", "encantamento": "Chamas", "trait": "BERSERKER"},
        "bonus": "Transforma em Avatar de Fogo (todas as skills sÃ£o fogo, imune a queimadura)",
    },
    "Assassino Perfeito": {
        "requer": {"classe": "Assassino", "personalidade": "Sombrio", "arma_tipo": "Dupla"},
        "bonus": "Primeiro hit Ã© sempre crÃ­tico, invisibilidade por 1s apÃ³s kill",
    },
}
```

**Testes**: `test_roguelike.py` â€” mutaÃ§Ãµes aplicam/removem corretamente, eventos nÃ£o crasham

---

## ORDEM DE IMPLEMENTAÃ‡ÃƒO

```
FASE 1 â”€â”€â†’ FASE 2 â”€â”€â†’ FASE 3 â”€â”€â†’ FASE 4 â”€â”€â†’ FASE 5
 (IA)      (Poderes)  (Sinergia) (ExpansÃ£o)  (Roguelike)
 
 Cada fase sÃ³ comeÃ§a apÃ³s testes da anterior passarem.
 Feature flags permitem desligar qualquer fase.
```

### Estimativa de Complexidade

| Fase | Arquivos Novos | Arquivos Editados | Risco |
|------|---------------|-------------------|-------|
| 1 | 1 (behavior_profiles.py) | 3 (brain_combat, brain_emotions, personalities) | BAIXO |
| 2 | 1 (class_abilities.py) | 3 (constants, brain_skills, brain.py) | BAIXO |
| 3 | 1 (synergy_engine.py) | 2 (brain_combat, brain_personality) | MÃ‰DIO |
| 4 | 0 | 2 (constants, personalities) | BAIXO |
| 5 | 2 (mutations.py, combat_events.py) | 3 (simulacao, brain, entities) | MÃ‰DIO |

### Feature Flags (SeguranÃ§a)
```python
# Em utilitarios/config.py ou novo feature_flags.py
AI_BEHAVIOR_PROFILES_ENABLED = True   # Fase 1
AI_CLASS_ABILITIES_ENABLED = True     # Fase 2
AI_SYNERGY_ENGINE_ENABLED = True      # Fase 3
AI_ROGUELIKE_MUTATIONS_ENABLED = True # Fase 5
```
Se qualquer flag = False, o sistema usa o comportamento original (fallback).

---

## STATUS

| Fase | Status | Progresso |
|------|--------|-----------|
| 1 - Identidade | ðŸ”„ EM PROGRESSO | 0% |
| 2 - Poderes | â¬œ NÃ£o iniciado | 0% |
| 3 - Sinergia | â¬œ NÃ£o iniciado | 0% |
| 4 - ExpansÃ£o | â¬œ NÃ£o iniciado | 0% |
| 5 - Roguelike | â¬œ NÃ£o iniciado | 0% |

