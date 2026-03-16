"""
Character Generator for Stress Testing
Creates hundreds of diverse characters with different attributes, weapons, and personalities.
"""
import json
import random
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# All available personalities (20 found in behavior_profiles.py)
PERSONALITIES = [
    "Agressivo", "Berserker", "Perseguidor", "Destruidor", "Viking",
    "Zerg Rush", "Pugilista", "Predador Alfa",
    "Defensivo", "Protetor", "Fantasma", "Masoquista",
    "Tático", "Samurai", "Contemplativo", "Psicopata",
    "Sombrio", "Assassino", "Acrobático", "Capoeirista", "Showman"
]

CLASSES = [
    "Paladino (Sagrado)", "Duelista (Precisão)", "Mago (Arcano)",
    "Guerreiro (Força)", "Arqueiro (Agilidade)", "Clérigo (Cura)",
    "Assassino (Sombra)", "Berserker (Caos)", "Monge (Disciplina)",
    "Necromante (Morte)", "Druida (Natureza)", "Bardo (Ilusão)"
]

# Base weapon templates (will create variations)
WEAPON_TEMPLATES = {
    "Espada": {
        "tipo": "Reta",
        "dano_base": 6.0,
        "peso_base": 1.8,
        "velocidade_base": 1.1,
        "critico_base": 5.0,
    },
    "Machado": {
        "tipo": "Pesada",
        "dano_base": 7.5,
        "peso_base": 2.5,
        "velocidade_base": 0.85,
        "critico_base": 8.0,
    },
    "Adaga": {
        "tipo": "Leve",
        "dano_base": 4.0,
        "peso_base": 0.9,
        "velocidade_base": 1.4,
        "critico_base": 12.0,
    },
    "Lança": {
        "tipo": "Alcance",
        "dano_base": 5.5,
        "peso_base": 1.5,
        "velocidade_base": 1.0,
        "critico_base": 4.0,
    },
    "Corrente": {
        "tipo": "Corrente",
        "dano_base": 6.5,
        "peso_base": 2.2,
        "velocidade_base": 1.15,
        "critico_base": 10.0,
    },
    "Arco": {
        "tipo": "Arco",
        "dano_base": 6.0,
        "peso_base": 4.0,
        "velocidade_base": 0.95,
        "critico_base": 4.0,
    },
}

ENCHANTMENTS = [
    "Trevas", "Crítico", "Execução", "Velocidade", "Recarga", "Dano",
    "Fogo", "Gelo", "Raio", "Veneno", "Bênção", "Maldição"
]

FIRST_NAMES = [
    "Aragorn", "Gandalf", "Legolas", "Gimli", "Frodo",
    "Boromir", "Galadriel", "Elrond", "Saruman", "Lurtz",
    "Arwen", "Éowyn", "Grimbold", "Gothmog", "Denethor",
    "Pippin", "Merry", "Sam", "Gollum", "Smaug",
    "Thorin", "Bilbo", "Dori", "Balin", "Glorfindel",
    "Tauriel", "Beorn", "Thranduil", "Radagast", "Círdan",
    "Maeglin", "Rían", "Hador", "Finwë", "Olwë",
    "Eöl", "Elu", "Dior", "Gil", "Beren",
    "Lúthien", "Yavanna", "Manwë", "Ulmo", "Nessa",
    "Oromë", "Irmo", "Aulë", "Varda", "Tulkas"
]

LAST_NAMES = [
    "da Aurora", "do Amanhecer", "da Escuridão", "do Caos", "da Ordem",
    "da Tempestade", "da Floresta", "da Montanha", "do Vale", "do Mar",
    "de Fogo", "de Gelo", "de Aço", "de Ouro", "de Prata",
    "Imortal", "Eterno", "Infinito", "Supremo", "Absoluto",
    "Conquistador", "Protetor", "Guardião", "Predador", "Sentinela",
    "Destruidor", "Criador", "Transformador", "Iluminado", "Amaldiçoado"
]

def generate_character_name():
    """Generate a random character name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def generate_weapon(weapon_type: str = None, variation: float = 0.15):
    """Generate a weapon with variations."""
    if weapon_type is None:
        weapon_type = random.choice(list(WEAPON_TEMPLATES.keys()))
    
    template = WEAPON_TEMPLATES.get(weapon_type, WEAPON_TEMPLATES["Espada"])
    
    # Apply random variations
    dano = template["dano_base"] * random.uniform(1 - variation, 1 + variation)
    peso = template["peso_base"] * random.uniform(0.9, 1.1)
    velocidade = template["velocidade_base"] * random.uniform(0.95, 1.05)
    critico = template["critico_base"] * random.uniform(0.9, 1.1)
    
    enchantments = random.sample(ENCHANTMENTS, k=random.randint(1, 3))
    
    weapon = {
        "nome": f"{weapon_type} {random.choice(['Lendário', 'Épico', 'Raro', 'Incomum', 'Comum'])}",
        "tipo": template["tipo"],
        "dano": round(dano, 2),
        "peso": round(peso, 2),
        "raridade": random.choice(["Comum", "Incomum", "Raro", "Épico"]),
        "quantidade": 1,
        "quantidade_orbitais": random.randint(0, 2),
        "forca_arco": random.uniform(6.0, 8.0) if template["tipo"] == "Arco" else 0.0,
        "forma_atual": 1,
        "r": random.randint(50, 255),
        "g": random.randint(50, 255),
        "b": random.randint(50, 255),
        "estilo": f"{weapon_type} Estilo {random.randint(1, 5)}",
        "cabo_dano": random.choice([True, False]),
        "habilidades": [
            {"nome": f"Habilidade {random.randint(1, 100)}", "custo": random.uniform(30.0, 60.0)}
            for _ in range(random.randint(1, 2))
        ],
        "encantamentos": enchantments,
        "passiva": {
            "nome": f"Passiva {random.randint(1, 100)}",
            "efeito": random.choice(["velocidade", "dano", "defesa", "resistência"]),
            "valor": random.randint(10, 30),
            "descricao": f"+{random.randint(10, 30)}% algum efeito"
        } if random.random() > 0.3 else None,
        "critico": round(critico, 2),
        "velocidade_ataque": round(velocidade, 2),
        "afinidade_elemento": random.choice(["FOGO", "GELO", "RAIO", "VENENO", "LUZ", "ESCURIDÃO"]),
        "durabilidade": 100.0,
        "durabilidade_max": 100.0,
        "habilidade": f"Habilidade {random.randint(1, 100)}",
        "custo_mana": random.uniform(30.0, 60.0),
    }
    
    return weapon

def generate_character(weapon_pool: list = None):
    """Generate a random character."""
    name = generate_character_name()
    
    # Random attributes
    tamanho = round(random.uniform(1.5, 2.5), 2)
    forca = round(random.uniform(5.0, 10.0), 1)
    mana = round(random.uniform(5.0, 10.0), 1)
    
    # Select weapon
    if weapon_pool:
        weapon = random.choice(weapon_pool)
        nome_arma = weapon["nome"]
    else:
        weapon = generate_weapon()
        nome_arma = weapon["nome"]
    
    # Random personality and class
    personalidade = random.choice(PERSONALITIES)
    classe = random.choice(CLASSES)
    
    character = {
        "nome": name,
        "tamanho": tamanho,
        "forca": forca,
        "mana": mana,
        "nome_arma": nome_arma,
        "cor_r": random.randint(30, 255),
        "cor_g": random.randint(30, 255),
        "cor_b": random.randint(30, 255),
        "classe": classe,
        "personalidade": personalidade,
        "god_id": None,
        "lore": f"Character with {personalidade} personality and {classe} class.",
        "_weapon_obj": weapon if not weapon_pool else None
    }
    
    return character

def generate_character_pool(num_characters: int = 500, num_weapons: int = 50):
    """Generate a pool of characters and weapons."""
    print(f"Generating {num_weapons} unique weapons...")
    weapons = []
    for _ in range(num_weapons):
        weapon = generate_weapon()
        weapons.append(weapon)
    
    print(f"Generating {num_characters} characters...")
    characters = []
    for i in range(num_characters):
        character = generate_character(weapons)
        characters.append(character)
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1}/{num_characters} characters")
    
    return characters, weapons

def save_character_pool(characters: list, weapons: list, output_dir: str = "stress_test_data"):
    """Save characters and weapons to JSON files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Remove weapon objects before saving
    chars_to_save = []
    for char in characters:
        char_copy = {k: v for k, v in char.items() if k != "_weapon_obj"}
        chars_to_save.append(char_copy)
    
    chars_file = os.path.join(output_dir, "test_characters.json")
    weapons_file = os.path.join(output_dir, "test_weapons.json")
    
    with open(chars_file, "w", encoding="utf-8") as f:
        json.dump(chars_to_save, f, indent=2, ensure_ascii=False)
    
    with open(weapons_file, "w", encoding="utf-8") as f:
        json.dump(weapons, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(characters)} characters to {chars_file}")
    print(f"✓ Saved {len(weapons)} weapons to {weapons_file}")
    
    return chars_file, weapons_file

def print_character_pool_stats(characters: list):
    """Print statistics about the generated character pool."""
    print("\n" + "=" * 80)
    print("CHARACTER POOL STATISTICS")
    print("=" * 80)
    
    # Personality distribution
    from collections import Counter
    personality_counts = Counter(c["personalidade"] for c in characters)
    class_counts = Counter(c["classe"] for c in characters)
    
    print(f"\nTotal Characters: {len(characters)}")
    print(f"\nPersonality Distribution:")
    for pers, count in personality_counts.most_common():
        pct = count / len(characters) * 100
        print(f"  {pers:20s}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\nClass Distribution:")
    for cls, count in class_counts.most_common():
        pct = count / len(characters) * 100
        print(f"  {cls:30s}: {count:4d} ({pct:5.1f}%)")
    
    # Attribute statistics
    tamanhos = [c["tamanho"] for c in characters]
    forcas = [c["forca"] for c in characters]
    manas = [c["mana"] for c in characters]
    
    print(f"\nAttribute Ranges:")
    print(f"  Tamanho:  min={min(tamanhos):.2f}  max={max(tamanhos):.2f}  avg={sum(tamanhos)/len(tamanhos):.2f}")
    print(f"  Força:    min={min(forcas):.2f}  max={max(forcas):.2f}  avg={sum(forcas)/len(forcas):.2f}")
    print(f"  Mana:     min={min(manas):.2f}  max={max(manas):.2f}  avg={sum(manas)/len(manas):.2f}")

if __name__ == "__main__":
    # Generate character pool
    characters, weapons = generate_character_pool(num_characters=500, num_weapons=50)
    
    # Print statistics
    print_character_pool_stats(characters)
    
    # Save to files
    chars_file, weapons_file = save_character_pool(characters, weapons)
    
    print(f"\n✓ Character generation complete!")
    print(f"  Files: {chars_file}, {weapons_file}")
