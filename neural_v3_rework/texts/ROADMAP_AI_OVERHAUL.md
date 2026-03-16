# 🧠 ROADMAP: AI OVERHAUL — "O Ecossistema Vivo"

## DIAGNÓSTICO ATUAL

### Problemas Identificados

| # | Problema | Severidade | Onde |
|---|---------|-----------|------|
| 1 | Personalidades influenciam IA apenas ±0.1~0.2 nos pesos | CRÍTICO | brain_combat.py |
| 2 | Classes só afetam stats numéricos, passivas são texto decorativo | CRÍTICO | constants.py |
| 3 | Sem habilidades de classe implementadas no combate | CRÍTICO | — (não existe) |
| 4 | Sem sinergias classe+personalidade+arma+encantamento | ALTO | — (não existe) |
| 5 | Berserker e Cauteloso lutam 90% parecido | ALTO | brain_combat.py |
| 6 | Traços existem (120+) mas maioria nunca é checada na IA | MÉDIO | brain_combat.py |
| 7 | Apenas 17 classes, sem subclasses ou variações | MÉDIO | constants.py |
| 8 | Sem mecânicas roguelike (mutações, eventos, evolução) | MÉDIO | — (não existe) |
| 9 | Quirks definidos mas poucos implementados de verdade | MÉDIO | brain_emotions.py |

---

## ARQUITETURA DE SEGURANÇA

### Princípio: "Addon, Não Override"
Cada fase adiciona novos módulos/funções. O código existente NÃO é deletado — apenas recebe hooks opcionais.

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
1. ✅ O jogo roda sem erros
2. ✅ Personalidades antigas continuam funcionando
3. ✅ Novos sistemas podem ser desligados (feature flags)

---

## FASE 1: "IDENTIDADE" — Personalidades com Alma
> Tornar cada personalidade REALMENTE diferente no combate

### 1.1 — Personality Weight Amplifier 
**O quê**: Multiplicar o impacto dos traços de 0.1~0.2 para 0.4~1.5
**Onde**: `brain_combat.py` → `_estrategia_generica()`
**Segurança**: Pesos capped em [0, 5.0], normalização final

### 1.2 — Personality Behavior Profiles
**O quê**: Cada personalidade preset ganha um "perfil de comportamento" que define regras exclusivas
**Onde**: NOVO `ai/behavior_profiles.py`
**Dados**:
```python
BEHAVIOR_PROFILES = {
    "Agressivo": {
        "recuar_threshold": 0.15,     # Só recua com <15% HP (vs 35% normal)
        "ataque_min_chance": 0.7,     # Chance mínima de atacar se no alcance
        "perseguir_sempre": True,     # Nunca desiste de perseguir
        "dano_recebido_reacao": "RAIVA",  # Leva dano → fica mais agressivo
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

### 1.3 — Trait Impact Overhaul
**O quê**: Cada um dos 120+ traços ganha impacto real e mensurável
**Onde**: `brain_combat.py` seção 2 e 4 da estratégia genérica
**Método**: Tabela de lookup `TRAIT_EFFECTS[trait] → {action: weight}`

### 1.4 — Fidelidade Emocional
**O quê**: Emoções (raiva, medo, etc.) passam a ter impacto 3x maior.
Um Berserker com raiva máxima é DRASTICAMENTE mais perigoso.
**Onde**: `brain_emotions.py`, `brain_combat.py`

**Testes**: `test_personality_fidelity.py` — valida que Agressivo ataca 2x mais que Defensivo

---

## FASE 2: "PODERES" — Habilidades de Classe e Personalidade
> Cada classe e personalidade ganha habilidades ativas e passivas únicas

### 2.1 — Class Ability System
**O quê**: NOVO sistema de habilidades vinculadas à classe
**Onde**: NOVO `ai/class_abilities.py`
**Estrutura**:
```python
CLASS_ABILITIES = {
    "Guerreiro (Força Bruta)": {
        "passiva": {
            "nome": "Golpe Devastador",
            "efeito": "physical_damage_mult",
            "valor": 1.10,  # +10% dano físico
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
        "ultimate": {  # Só ativa com condição especial
            "nome": "Fúria do Guerreiro",
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

### 2.2 — Personality Passive Abilities
**O quê**: Cada personalidade preset ganha 1-2 passivas temáticas
**Exemplos**:
- Berserker: "Sede de Sangue" (dano +2% por cada 10% de HP perdido)
- Fantasma: "Intocável" (cada esquiva dá +5% velocidade por 2s, stacks 3x)
- Samurai: "Iai" (primeiro ataque causa 50% mais dano)
- Psicopata: "Sangue Frio" (emoções não afetam decisões, +15% dano em targets abaixo de 30% HP)

### 2.3 — Ability Integration na IA
**Onde**: `brain_skills.py` — novo priority slot para class abilities

**Testes**: `test_class_abilities.py` — valida que cada classe tem passiva+ativa funcionando

---

## FASE 3: "SINERGIA" — O Ecossistema Completo
> Classe + Personalidade + Arma + Skills + Encantamento formam um todo coerente

### 3.1 — Synergy Engine
**Onde**: NOVO `ai/synergy_engine.py`
```python
class SynergyEngine:
    def calculate(self, fighter) -> SynergyBonus:
        """Analisa TUDO do fighter e retorna bônus/estratégias"""
        # Classe ↔ Arma: Mago + Arma Mágica = +20% dano
        # Classe ↔ Encantamento: Piromante + Chamas = +15% fire dmg  
        # Personalidade ↔ Classe: Berserker(pers) + Berserker(class) = "Pure Berserker" buff
        # Arma ↔ Skills: Arco + skills de range = +10% range
        # Composição completa: avalia harmonia geral → bônus ou penalidade
```

### 3.2 — AI Strategy Advisor
**O quê**: IA calcula a melhor estratégia baseada em TUDO que tem disponível
**Onde**: Novo método `_calcular_estrategia_sinergica()` em brain_combat.py
- Piromante + Chamas + Bola de Fogo → IA prioriza combos de fogo
- Ninja + Dupla + Assassino → IA prioriza hit-and-run
- Cavaleiro + Orbital + Defensivo → IA prioriza posição e bloqueio

### 3.3 — Anti-Synergy Penalties
- Criomante + Encantamento de Fogo → conflito elemental, -5% eficiência
- Berserker(classe) + Defensivo(personalidade) → identidade confusa, decisões mais lentas

**Testes**: `test_synergy_engine.py` — tabela de sinergias conhecidas validada

---

## FASE 4: "EXPANSÃO" — Mais Classes, Mais Personalidades
> Vasta gama de opções

### 4.1 — Novas Classes (17 → 40+)
Grupos novos a adicionar:

**Elementais (6)**:
- Aeromante (Vento), Geomante (Terra), Tempestário (Tempestade)  
- Cronomante (Tempo), Graviturgo (Gravidade), Alquimista (Transmutação)

**Combate Especializado (6)**:
- Bárbaro (Fúria Primitiva), Espadachim (Lâmina), Lanceiro (Alcance)
- Arqueiro (Precisão), Cavaleiro Negro (Corrupção), Patrulheiro (Rastreio)

**Exóticos (6)**:
- Xamã (Espíritos), Bardo (Música), Rúnico (Runas)
- Psíquico (Mente), Artífice (Construtos), Invocador (Criaturas)

**Híbridos Avançados (5)**:
- Arcano Guerreiro (Magia+Espada), Sacerdote Sombrio (Cura+Trevas)
- Caçador de Demônios (Anti-magia), Cavaleiro Dragão (Draconico)
- Sentinela do Tempo (Tempo+Defesa)

### 4.2 — Novas Personalidades (24 → 50+)
Presets novos:
- Estrategista, Provocador, Covarde Tático, Sádico, Monge Zen
- Gladiador (Showoff), Mercenário (Prático), Selvagem, Resistente
- Kamikaze, Trapaceiro, Imortal, Senhor da Guerra, Eremita
- Mestre dos Venenos, Cavaleiro Errante, Mestre Chi, Pistoleiro
- Relâmpago Humano, Leão, Escorpião, Cobra, Fênix, Tartaruga
- Vórtice, Maremoto, Avalanche

### 4.3 — Skill Tree Visualization
**Onde**: NOVO `ui/view_skill_tree.py`
- Árvore visual de habilidades por classe
- Mostra sinergias com cores e conexões
- Combos possíveis destacados

**Testes**: `test_new_classes.py` — valida que todas as novas classes têm dados completos

---

## FASE 5: "ROGUELIKE" — Imprevisibilidade e Evolução
> Mecânicas que tornam cada luta única

### 5.1 — Mutações de Combate
Cada luta/round do torneio, personagens ganham 1-2 mutações randômicas:
```python
MUTACOES = {
    "Mãos de Vidro": {"dano_mult": 1.5, "vida_mult": 0.7},
    "Vampirismo": {"lifesteal": 0.15, "regen": -0.5},
    "Sobrecarga Arcana": {"skill_dano_mult": 1.3, "skill_custo_mult": 1.5},
    "Escudo de Ferro": {"defesa_mult": 1.4, "velocidade_mult": 0.8},
    "Berserker Curse": {"dano_mult": 1.0 + (1.0 - hp_pct) * 0.5},
    # ... 50+ mutações
}
```

### 5.2 — Eventos de Combate
Eventos aleatórios durante a luta:
- Chuva de Meteoros (zona de perigo no mapa)
- Buff de Arena (item aparece no chão)
- Terremoto (empurra todos)
- Eclipse (visão reduzida, dano sombrio +30%)
- Maré de Mana (mana regenera 3x mais rápido)

### 5.3 — Evolução por Torneio
Cada vitória no torneio permite escolher 1 upgrade:
- +10% dano, +15% HP, nova skill, mutação permanente, etc.
- Sistema de "relíquias" (itens passivos cumulativos)

### 5.4 — Builds Lendárias  
Combinações raras que desbloqueiam habilidades únicas:
```python
LEGENDARY_BUILDS = {
    "Avatar do Fogo": {
        "requer": {"classe": "Piromante", "encantamento": "Chamas", "trait": "BERSERKER"},
        "bonus": "Transforma em Avatar de Fogo (todas as skills são fogo, imune a queimadura)",
    },
    "Assassino Perfeito": {
        "requer": {"classe": "Assassino", "personalidade": "Sombrio", "arma_tipo": "Dupla"},
        "bonus": "Primeiro hit é sempre crítico, invisibilidade por 1s após kill",
    },
}
```

**Testes**: `test_roguelike.py` — mutações aplicam/removem corretamente, eventos não crasham

---

## ORDEM DE IMPLEMENTAÇÃO

```
FASE 1 ──→ FASE 2 ──→ FASE 3 ──→ FASE 4 ──→ FASE 5
 (IA)      (Poderes)  (Sinergia) (Expansão)  (Roguelike)
 
 Cada fase só começa após testes da anterior passarem.
 Feature flags permitem desligar qualquer fase.
```

### Estimativa de Complexidade

| Fase | Arquivos Novos | Arquivos Editados | Risco |
|------|---------------|-------------------|-------|
| 1 | 1 (behavior_profiles.py) | 3 (brain_combat, brain_emotions, personalities) | BAIXO |
| 2 | 1 (class_abilities.py) | 3 (constants, brain_skills, brain.py) | BAIXO |
| 3 | 1 (synergy_engine.py) | 2 (brain_combat, brain_personality) | MÉDIO |
| 4 | 0 | 2 (constants, personalities) | BAIXO |
| 5 | 2 (mutations.py, combat_events.py) | 3 (simulacao, brain, entities) | MÉDIO |

### Feature Flags (Segurança)
```python
# Em utils/config.py ou novo feature_flags.py
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
| 1 - Identidade | 🔄 EM PROGRESSO | 0% |
| 2 - Poderes | ⬜ Não iniciado | 0% |
| 3 - Sinergia | ⬜ Não iniciado | 0% |
| 4 - Expansão | ⬜ Não iniciado | 0% |
| 5 - Roguelike | ⬜ Não iniciado | 0% |
