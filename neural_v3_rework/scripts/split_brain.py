#!/usr/bin/env python3
"""
split_brain.py — Splits ai/brain.py (5000+ lines) into mixin modules.
Run from the neural_v3_rework directory:
    python scripts/split_brain.py

Creates:
  ai/brain_personality.py   — PersonalityMixin
  ai/brain_perception.py    — PerceptionMixin
  ai/brain_evasion.py       — EvasionMixin
  ai/brain_combat.py        — CombatMixin
  ai/brain_skills.py        — SkillsMixin
  ai/brain_spatial.py       — SpatialMixin
  ai/brain_emotions.py      — EmotionsMixin
  ai/brain_choreography.py  — ChoreographyMixin
  ai/brain.py               — Thin orchestrator (overwritten)
  ai/brain_original.py      — Backup of original
"""
import ast
import os
import re
import shutil
import sys
import textwrap

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAIN_PATH = os.path.join(BASE_DIR, "ai", "brain.py")
AI_DIR = os.path.join(BASE_DIR, "ai")

# ═══════════════════════════════════════════════════════════════════════════════
# METHOD → MIXIN ASSIGNMENT
# ═══════════════════════════════════════════════════════════════════════════════
# Methods NOT listed here stay in the orchestrator: __init__, processar
MIXIN_DEFS = {
    "PersonalityMixin": {
        "file": "brain_personality.py",
        "doc": "Mixin de geração e configuração de personalidade procedural.",
        "methods": [
            "_gerar_personalidade",
            "_gerar_personalidade_aleatoria",
            "_gerar_tracos",
            "_resolver_conflitos_tracos",
            "_definir_arquetipo",
            "_definir_arquetipo_por_arma",
            "_selecionar_estilo",
            "_selecionar_filosofia",
            "_gerar_quirks",
            "_gerar_instintos",
            "_gerar_ritmo",
            "_calcular_agressividade",
            "_aplicar_modificadores_iniciais",
            "_aplicar_preset",
            "_categorizar_skills",
            "_adicionar_skill",
            "_inicializar_skill_strategy",
        ],
        "extra_imports": [
            "import re as _re_arquetipo",
            "from models import get_class_data",
            "from ai.choreographer import CombatChoreographer",
        ],
    },
    "PerceptionMixin": {
        "file": "brain_perception.py",
        "doc": "Mixin de leitura de oponente e percepção de armas.",
        "methods": [
            "_atualizar_leitura_oponente",
            "_atualizar_percepcao_armas",
            "_calcular_estrategia_armas",
            "_aplicar_modificadores_armas",
            "_observar_oponente",
            "_gerar_reacao_inteligente",
            "_id_oponente",
            "carregar_memoria_rival",
            "salvar_memoria_rival",
        ],
        "extra_imports": [],
    },
    "EvasionMixin": {
        "file": "brain_evasion.py",
        "doc": "Mixin de esquiva inteligente, pulos evasivos e detecção de projéteis.",
        "methods": [
            "_processar_desvio_inteligente",
            "_calcular_direcao_desvio",
            "_executar_desvio",
            "_analisar_areas_perigo",
            "_analisar_projeteis_vindo",
            "_tentar_pulo_evasivo",
            "_tentar_dash_emergencia",
            "_detectar_projetil_vindo",
        ],
        "extra_imports": [],
    },
    "CombatMixin": {
        "file": "brain_combat.py",
        "doc": "Mixin de decisão de ataque, combos, baiting, momentum e movimento tático.",
        "methods": [
            "_avaliar_e_executar_ataque",
            "_executar_ataque_oportunidade",
            "_executar_ataque",
            "_tentar_followup",
            "_atualizar_combo_state",
            "_processar_baiting",
            "_executar_contra_bait",
            "_atualizar_momentum",
            "_atualizar_janelas_oportunidade",
            "_decidir_movimento",
            "_estrategia_ranged",
            "_estrategia_corrente",
            "_estrategia_dupla",
            "_estrategia_generica",
            "_calcular_alcance_efetivo",
            "_calcular_timer_decisao",
        ],
        "extra_imports": [],
    },
    "SkillsMixin": {
        "file": "brain_skills.py",
        "doc": "Mixin de uso inteligente de skills (estratégico + legado).",
        "methods": [
            "_processar_skills",
            "_processar_skills_estrategico",
            "_executar_skill_por_nome",
            "_pos_uso_skill_estrategica",
            "_tentar_dash_ofensivo",
            "_tentar_usar_buff",
            "_tentar_usar_ofensiva",
            "_tentar_usar_summon",
            "_tentar_usar_trap",
            "_tentar_usar_transform",
            "_usar_skill",
            "_avaliar_uso_skill",
            "_pos_uso_skill_ofensiva",
            "_contar_summons_ativos",
            "_contar_traps_ativos",
            "_verificar_inimigo_stunado",
            "_verificar_inimigo_debuffado",
            "_usar_tudo",
        ],
        "extra_imports": [
            "from core.skills import get_skill_data",
        ],
    },
    "SpatialMixin": {
        "file": "brain_spatial.py",
        "doc": "Mixin de consciência espacial, paredes, obstáculos e táticas de posicionamento.",
        "methods": [
            "_atualizar_consciencia_espacial",
            "_avaliar_taticas_espaciais",
            "_aplicar_modificadores_espaciais",
            "_ajustar_direcao_por_ambiente",
        ],
        "extra_imports": [],
    },
    "EmotionsMixin": {
        "file": "brain_emotions.py",
        "doc": "Mixin de emoções, humor, estados humanos, quirks, reações, ritmo e instintos.",
        "methods": [
            "_atualizar_estados_humanos",
            "_verificar_hesitacao",
            "_registrar_acao",
            "_atualizar_cooldowns",
            "_detectar_dano",
            "_reagir_ao_dano",
            "_atualizar_emocoes",
            "_atualizar_humor",
            "_processar_modos_especiais",
            "_processar_quirks",
            "_executar_quirk",
            "_processar_reacoes",
            "_tentar_cura_emergencia",
            "_tentar_contra_ataque",
            "_atualizar_ritmo",
            "_processar_instintos",
            "_executar_instinto",
            "get_agressividade_efetiva",
            "_rand",
        ],
        "extra_imports": [],
    },
    "ChoreographyMixin": {
        "file": "brain_choreography.py",
        "doc": "Mixin de coreografia de combate, reações ao oponente e callbacks.",
        "methods": [
            "_processar_reacao_oponente",
            "_executar_acao_sincronizada",
            "on_momento_cinematografico",
            "on_hit_recebido_de",
            "on_bloqueio_sucesso",
            "on_hit_dado",
            "on_hit_recebido",
            "on_skill_usada",
            "on_inimigo_fugiu",
            "on_esquiva_sucesso",
        ],
        "extra_imports": [],
    },
}

# Reverse map
METHOD_TO_MIXIN = {}
for mname, mdata in MIXIN_DEFS.items():
    for method in mdata["methods"]:
        METHOD_TO_MIXIN[method] = mname

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED IMPORTS BLOCK (used by every mixin file)
# ═══════════════════════════════════════════════════════════════════════════════
SHARED_IMPORTS = '''\
"""Auto-generated mixin — see scripts/split_brain.py"""
import random
import math
import logging

_log = logging.getLogger("neural_ai")

from utils.config import PPM
from utils.config import (
    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,
    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,
    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,
    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,
    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,
    AI_RAND_POOL_SIZE,
)
from ai.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,
    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES
)

try:
    from core.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
    WEAPON_ANALYSIS_AVAILABLE = True
except ImportError:
    WEAPON_ANALYSIS_AVAILABLE = False

try:
    from ai.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority
    SKILL_STRATEGY_AVAILABLE = True
except ImportError:
    SKILL_STRATEGY_AVAILABLE = False

try:
    from core.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

try:
    from core.arena import get_arena as _get_arena
except ImportError:
    _get_arena = None
'''


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Parse brain.py with AST to find exact method boundaries
# ═══════════════════════════════════════════════════════════════════════════════

with open(BRAIN_PATH, "r", encoding="utf-8") as f:
    source = f.read()
source_lines = source.split("\n")

tree = ast.parse(source)

# Find AIBrain class
aibrain_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "AIBrain":
        aibrain_node = node
        break

if aibrain_node is None:
    print("ERROR: AIBrain class not found!")
    sys.exit(1)

# Get all method definitions directly inside AIBrain (not nested)
method_nodes = []
for item in aibrain_node.body:
    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
        method_nodes.append(item)

print(f"Found {len(method_nodes)} methods in AIBrain")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Extract method bodies with preceding comments
# ═══════════════════════════════════════════════════════════════════════════════
# For each method, we want:
#   - Any section comments/blank lines preceding the `def` line
#   - The method body itself (up to end_lineno from AST)
#
# We detect "preceding comments" by walking backwards from the `def` line
# until we hit a non-comment, non-blank line (which belongs to the end of
# the previous method body).

method_blocks = {}  # name -> list of source lines (already with 4-space indent)

for i, mnode in enumerate(method_nodes):
    name = mnode.name
    # AST line numbers are 1-based
    def_line = mnode.lineno - 1       # 0-based index of `def` line
    end_line = mnode.end_lineno - 1   # 0-based index of last line in method

    # Walk backwards to find preceding section comments
    first_line = def_line
    j = def_line - 1
    while j >= 0:
        stripped = source_lines[j].rstrip()
        # Include blank lines and comment lines at 4-space indent (or deeper)
        if stripped == "" or stripped.startswith("    #") or stripped.startswith("    # "):
            first_line = j
            j -= 1
        else:
            break

    # Extract lines from first_line to end_line (inclusive)
    block = source_lines[first_line : end_line + 1]
    method_blocks[name] = block

# Report
all_method_names = set(method_blocks.keys())
assigned_names = set(METHOD_TO_MIXIN.keys())
orchestrator_methods = {"__init__", "processar"}
unassigned = all_method_names - assigned_names - orchestrator_methods
if unassigned:
    print(f"WARNING: Unassigned methods (will stay in orchestrator): {unassigned}")
    for u in sorted(unassigned):
        print(f"  - {u}")

missing = assigned_names - all_method_names
if missing:
    print(f"ERROR: Methods in map but not found in brain.py: {missing}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Generate mixin files
# ═══════════════════════════════════════════════════════════════════════════════

for mixin_name, mixin_data in MIXIN_DEFS.items():
    filename = mixin_data["file"]
    filepath = os.path.join(AI_DIR, filename)
    doc = mixin_data["doc"]
    methods = mixin_data["methods"]
    extra_imports = mixin_data.get("extra_imports", [])

    lines_out = []

    # ── File header with shared imports ──
    lines_out.append(SHARED_IMPORTS)
    lines_out.append("")

    # ── Extra imports specific to this mixin ──
    if extra_imports:
        for imp in extra_imports:
            lines_out.append(imp)
        lines_out.append("")

    # ── Class definition ──
    lines_out.append("")
    lines_out.append(f"class {mixin_name}:")
    lines_out.append(f'    """{doc}"""')
    lines_out.append("")

    # ── Method bodies ──
    for method_name in methods:
        if method_name not in method_blocks:
            print(f"  SKIP: {method_name} not found in brain.py")
            continue
        block = method_blocks[method_name]
        for line in block:
            lines_out.append(line)
        lines_out.append("")  # blank line between methods

    # Write file
    content = "\n".join(lines_out)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    n_methods = sum(1 for m in methods if m in method_blocks)
    n_lines = len(lines_out)
    print(f"  Created {filename}: {n_methods} methods, {n_lines} lines")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Generate new brain.py orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

# First, backup the original
backup_path = os.path.join(AI_DIR, "brain_original.py")
shutil.copy2(BRAIN_PATH, backup_path)
print(f"\n  Backup saved to: brain_original.py")

# Build the orchestrator
# It keeps: module docstring, imports, class AIBrain with __init__ and processar,
# plus any unassigned methods

# Get the original module docstring (everything before the first import)
header_end = 0
for i, line in enumerate(source_lines):
    if line.startswith("import ") or line.startswith("from "):
        header_end = i
        break

module_docstring = "\n".join(source_lines[:header_end])

# Get __init__ and processar blocks
init_block = method_blocks.get("__init__", [])
processar_block = method_blocks.get("processar", [])

# Unassigned methods that stay in the orchestrator
extra_method_blocks = []
for name in sorted(unassigned):
    extra_method_blocks.append(method_blocks[name])

# Build the mixin import lines
mixin_imports = []
for mixin_name, mixin_data in MIXIN_DEFS.items():
    module = mixin_data["file"].replace(".py", "")
    mixin_imports.append(f"from ai.{module} import {mixin_name}")

# Build the bases string
bases = ", ".join(MIXIN_DEFS.keys())

# Get class-level code between class def and __init__
# Find class def line and __init__ def line
class_def_line = aibrain_node.lineno - 1  # 0-based
init_node = None
for mnode in method_nodes:
    if mnode.name == "__init__":
        init_node = mnode
        break

class_level_code = []
if init_node:
    # Lines between "class AIBrain:" and the first method (__init__)
    # But skip the class def line itself
    start = class_def_line + 1
    # Walk backwards from __init__ to find where class-level code ends
    first_method_line = init_node.lineno - 1
    # Find beginning of __init__'s preceding comments
    j = first_method_line - 1
    while j >= start:
        stripped = source_lines[j].rstrip()
        if stripped == "" or stripped.startswith("    #"):
            j -= 1
        else:
            break
    class_body_end = j + 1

    for i in range(start, class_body_end):
        class_level_code.append(source_lines[i])

orchestrator = []

# ── Module docstring ──
orchestrator.append(module_docstring.rstrip())
orchestrator.append("")

# ── Original imports ──
orchestrator.append("import random")
orchestrator.append("import math")
orchestrator.append("import re as _re_arquetipo")
orchestrator.append("import logging")
orchestrator.append("")
orchestrator.append('_log = logging.getLogger("neural_ai")')
orchestrator.append("")
orchestrator.append("from utils.config import PPM")
orchestrator.append("from utils.config import (")
orchestrator.append("    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,")
orchestrator.append("    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,")
orchestrator.append("    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,")
orchestrator.append("    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,")
orchestrator.append("    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,")
orchestrator.append("    AI_RAND_POOL_SIZE,")
orchestrator.append(")")
orchestrator.append("from core.physics import normalizar_angulo")
orchestrator.append("from core.skills import get_skill_data")
orchestrator.append("from models import get_class_data")
orchestrator.append("from ai.choreographer import CombatChoreographer")
orchestrator.append("from ai.personalities import (")
orchestrator.append("    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,")
orchestrator.append("    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,")
orchestrator.append("    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,")
orchestrator.append("    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES")
orchestrator.append(")")
orchestrator.append("")
orchestrator.append("try:")
orchestrator.append("    from core.weapon_analysis import (")
orchestrator.append("        analisador_armas, get_weapon_profile, compare_weapons,")
orchestrator.append("        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle")
orchestrator.append("    )")
orchestrator.append("    WEAPON_ANALYSIS_AVAILABLE = True")
orchestrator.append("except ImportError:")
orchestrator.append("    WEAPON_ANALYSIS_AVAILABLE = False")
orchestrator.append("")
orchestrator.append("try:")
orchestrator.append("    from ai.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority")
orchestrator.append("    SKILL_STRATEGY_AVAILABLE = True")
orchestrator.append("except ImportError:")
orchestrator.append("    SKILL_STRATEGY_AVAILABLE = False")
orchestrator.append("")
orchestrator.append("try:")
orchestrator.append("    from core.hitbox import HITBOX_PROFILES")
orchestrator.append("except ImportError:")
orchestrator.append("    HITBOX_PROFILES = {}")
orchestrator.append("")
orchestrator.append("try:")
orchestrator.append("    from core.arena import get_arena as _get_arena")
orchestrator.append("except ImportError:")
orchestrator.append("    _get_arena = None")
orchestrator.append("")

# ── Mixin imports ──
orchestrator.append("# ── Mixin imports ──")
for line in mixin_imports:
    orchestrator.append(line)
orchestrator.append("")
orchestrator.append("")

# ── Class definition ──
orchestrator.append(f"class AIBrain({bases}):")

# ── Class-level code (docstring, class variable, etc.) ──
for line in class_level_code:
    orchestrator.append(line)

# ── __init__ ──
orchestrator.append("")
for line in init_block:
    orchestrator.append(line)

# ── processar ──
orchestrator.append("")
for line in processar_block:
    orchestrator.append(line)

# ── Unassigned extra methods ──
for block in extra_method_blocks:
    orchestrator.append("")
    for line in block:
        orchestrator.append(line)

orchestrator.append("")

# Write new brain.py
new_content = "\n".join(orchestrator)
with open(BRAIN_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

total_orchestrator = len(orchestrator)
print(f"  Created brain.py orchestrator: {total_orchestrator} lines")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n=== SPLIT COMPLETE ===")
print(f"Original: {len(source_lines)} lines")
print(f"Orchestrator: {total_orchestrator} lines")
print(f"Mixins: {len(MIXIN_DEFS)} files")
total_mixin_lines = 0
for mixin_name, mixin_data in MIXIN_DEFS.items():
    fpath = os.path.join(AI_DIR, mixin_data["file"])
    with open(fpath, "r", encoding="utf-8") as f:
        n = len(f.readlines())
    total_mixin_lines += n
    print(f"  {mixin_data['file']}: {n} lines")
print(f"Total mixin lines: {total_mixin_lines}")
print(f"Backup: brain_original.py")
print("\nDone! Run your tests to verify correctness.")
