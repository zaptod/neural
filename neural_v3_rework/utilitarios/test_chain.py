"""Test chain weapon system integration."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nucleo.entities import Lutador
from nucleo.hitbox import get_hitbox_profile, HITBOX_PROFILES
from efeitos.weapon_animations import WeaponAnimator
from simulacao.sim_combat import SimuladorCombat
from ia.brain_perception import PerceptionMixin

# Verify chain hitbox profiles exist
chain_profiles = ['Mangual', 'Kusarigama_foice', 'Kusarigama_peso',
                  'Chicote', 'Meteor Hammer', 'Corrente com Peso']
for p in chain_profiles:
    assert p in HITBOX_PROFILES, f'Missing profile: {p}'
    prof = HITBOX_PROFILES[p]
    arc = prof.get("arc", 360)
    rm = prof["range_mult"]
    print(f"  {p}: arc={arc}deg range={rm}x")

# Verify chain state variables on Lutador
from modelos.characters import Personagem
dados = Personagem('Test', 1.0, 5.0, 5.0, '', 0, 200, 50, 50, 'Guerreiro (ForÃ§a Bruta)')
lut = Lutador(dados, 0, True)
chain_attrs = ['chain_momentum', 'chain_spin_speed', 'chain_spinning',
               'chain_spin_dmg_timer', 'chain_combo', 'chain_combo_timer',
               'chain_mode', 'chain_pull_target', 'chain_pull_timer',
               'chain_whip_crack', 'chain_whip_stacks', 'chain_recovery_mult']
for attr in chain_attrs:
    assert hasattr(lut, attr), f'Missing attr: {attr}'

# Verify get_hitbox_profile resolves chain styles
for estilo in ['Mangual', 'Kusarigama', 'Chicote', 'Meteor Hammer', 'Corrente com Peso']:
    profile = get_hitbox_profile("Corrente", estilo)
    print(f"  get_hitbox_profile('Corrente', '{estilo}') -> range_mult={profile['range_mult']}")

print()
print("ALL CHAIN WEAPON SYSTEMS OK!")
print(f"  Profiles: {len(chain_profiles)} chain hitbox profiles")
print(f"  State vars: {len(chain_attrs)} chain state variables")

