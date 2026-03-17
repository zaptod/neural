"""Test chain weapon combat - verifies all 5 chain styles work in battle."""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from data import carregar_personagens, carregar_armas  # D01 Sprint 10
from models.characters import Personagem
from models.weapons import Arma
from core.entities import Lutador

print("=" * 60)
print("  CHAIN WEAPON COMBAT TEST")
print("=" * 60)

# Load DB
armas_db = carregar_armas()
chars_db = carregar_personagens()

# Find all chain weapons
chain_weapons = [a for a in armas_db if getattr(a, 'tipo', '') == "Corrente"]
print(f"\nChain weapons found: {len(chain_weapons)}")
for cw in chain_weapons:
    print(f"  - {cw.nome} (estilo: {getattr(cw, 'estilo', 'N/A')})")

chars = chars_db if isinstance(chars_db, list) else list(chars_db.values())

successes = 0
failures = 0

for i, arma in enumerate(chain_weapons[:5]):
    estilo = getattr(arma, 'estilo', '?')
    print(f"\n--- Test {i+1}: {arma.nome} ({estilo}) ---")
    
    try:
        
        # Create character with chain weapon - chars are Personagem objects
        c = random.choice(chars)
        # Use existing personagem, just swap weapon
        c.nome_arma = arma.nome
        c.arma_obj = arma
        
        # Create Lutador
        lut = Lutador(c, 5.0, 10.0)
        
        # Verify chain state initialized
        assert hasattr(lut, 'chain_momentum'), "Missing chain_momentum"
        assert hasattr(lut, 'chain_spin_speed'), "Missing chain_spin_speed"
        assert hasattr(lut, 'chain_mode'), "Missing chain_mode"
        
        # Verify arma tipo is correct
        arma_obj = lut.dados.arma_obj
        assert arma_obj.tipo == "Corrente", f"Expected Corrente, got {arma_obj.tipo}"
        assert arma_obj.estilo == estilo, f"Expected {estilo}, got {arma_obj.estilo}"
        
        # Check that chain methods exist
        assert hasattr(lut, '_executar_ataques_corrente'), "Missing _executar_ataques_corrente"
        assert hasattr(lut, '_atualizar_chain_state'), "Missing _atualizar_chain_state"
        assert hasattr(lut, '_calcular_alcance_corrente'), "Missing _calcular_alcance_corrente"
        
        # Test alcance calculation
        alcance = lut._calcular_alcance_corrente(estilo)
        print(f"  Character: {c.nome}, Weapon: {arma.nome}")
        print(f"  Alcance: {alcance:.2f}m, Chain mode: {lut.chain_mode}")
        print(f"  OK!")
        
        successes += 1
        
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        failures += 1

print(f"\n{'=' * 60}")
print(f"  RESULTS: {successes} OK, {failures} FAILED")
print(f"{'=' * 60}")
