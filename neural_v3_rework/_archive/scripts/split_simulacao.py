#!/usr/bin/env python3
"""
split_simulacao.py — Splits simulation/simulacao.py (4570+ lines) into mixin modules.
Run from the neural_v3_rework directory:
    python scripts/split_simulacao.py
"""
import ast
import os
import re
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_PATH = os.path.join(BASE_DIR, "simulation", "simulacao.py")
SIM_DIR = os.path.join(BASE_DIR, "simulation")

# ═══════════════════════════════════════════════════════════════════════════════
# METHOD → MIXIN ASSIGNMENT
# ═══════════════════════════════════════════════════════════════════════════════
MIXIN_DEFS = {
    "SimuladorRenderer": {
        "file": "sim_renderer.py",
        "doc": "Mixin de renderização: desenho de lutadores, armas, UI e debug.",
        "methods": [
            "desenhar",
            "desenhar_grid",
            "desenhar_lutador",
            "_desenhar_nome_tag",
            "_desenhar_slash_arc",
            "_desenhar_weapon_trail",
            "desenhar_arma",
            "desenhar_hitbox_debug",
            "desenhar_painel_debug",
            "desenhar_barras",
            "desenhar_controles",
            "desenhar_analise",
            "desenhar_pause",
            "desenhar_vitoria",
        ],
    },
    "SimuladorCombat": {
        "file": "sim_combat.py",
        "doc": "Mixin de combate: detecção de hits, clashes, bloqueios e física.",
        "methods": [
            "checar_ataque",
            "verificar_colisoes_combate",
            "resolver_fisica_corpos",
            "checar_clash_geral",
            "checar_clash_espada_escudo",
            "efeito_clash",
            "_executar_clash_magico",
            "_executar_sword_clash",
            "_verificar_clash_projeteis",
            "_verificar_bloqueio_projetil",
            "_efeito_bloqueio",
            "_efeito_desvio_dash",
            "_efeito_parry",
        ],
    },
    "SimuladorEffects": {
        "file": "sim_effects.py",
        "doc": "Mixin de efeitos visuais: partículas, trails, colisões, slow motion.",
        "methods": [
            "_criar_efeito_colisao_parede",
            "_get_cor_efeito",
            "_remover_trail_projetil",
            "_spawn_particulas_efeito",
            "_beam_colide_alvo",
            "_detectar_eventos_movimento",
            "_criar_knockback_visual",
            "atualizar_rastros",
            "spawn_particulas",
            "ativar_slow_motion",
            "_salvar_memorias_rivais",
        ],
    },
}

METHOD_TO_MIXIN = {}
for mname, mdata in MIXIN_DEFS.items():
    for method in mdata["methods"]:
        METHOD_TO_MIXIN[method] = mname

# ═══════════════════════════════════════════════════════════════════════════════
# PARSE
# ═══════════════════════════════════════════════════════════════════════════════
with open(SIM_PATH, "r", encoding="utf-8") as f:
    source = f.read()
source_lines = source.split("\n")

tree = ast.parse(source)

# Find Simulador class
sim_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "Simulador":
        sim_node = node
        break

if sim_node is None:
    print("ERROR: Simulador class not found!")
    sys.exit(1)

method_nodes = []
for item in sim_node.body:
    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
        method_nodes.append(item)

print(f"Found {len(method_nodes)} methods in Simulador")

# Extract method blocks with preceding comments
method_blocks = {}
for i, mnode in enumerate(method_nodes):
    name = mnode.name
    def_line = mnode.lineno - 1
    end_line = mnode.end_lineno - 1

    first_line = def_line
    j = def_line - 1
    while j >= 0:
        stripped = source_lines[j].rstrip()
        if stripped == "" or stripped.startswith("    #") or stripped.startswith("    # "):
            first_line = j
            j -= 1
        else:
            break

    block = source_lines[first_line : end_line + 1]
    method_blocks[name] = block

all_method_names = set(method_blocks.keys())
assigned_names = set(METHOD_TO_MIXIN.keys())
orchestrator_methods = {"__init__", "_check_portrait_mode", "recarregar_tudo",
                        "carregar_luta_dados", "processar_inputs", "update", "run"}
unassigned = all_method_names - assigned_names - orchestrator_methods
if unassigned:
    print(f"WARNING: Unassigned methods (stay in orchestrator): {sorted(unassigned)}")
missing = assigned_names - all_method_names
if missing:
    print(f"ERROR: Missing methods: {missing}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# READ IMPORTS FROM ORIGINAL FILE
# ═══════════════════════════════════════════════════════════════════════════════
# Find all import lines before the class definition
imports_end = sim_node.lineno - 1
import_lines = source_lines[:imports_end]
# Trim trailing blank lines
while import_lines and import_lines[-1].strip() == "":
    import_lines.pop()
import_block = "\n".join(import_lines)

# ═══════════════════════════════════════════════════════════════════════════════
# GENERATE MIXIN FILES
# ═══════════════════════════════════════════════════════════════════════════════
for mixin_name, mixin_data in MIXIN_DEFS.items():
    filename = mixin_data["file"]
    filepath = os.path.join(SIM_DIR, filename)
    doc = mixin_data["doc"]
    methods = mixin_data["methods"]

    lines_out = []
    lines_out.append(f'"""Auto-generated mixin — see scripts/split_simulacao.py"""')
    lines_out.append(import_block)
    lines_out.append("")
    lines_out.append("")
    lines_out.append(f"class {mixin_name}:")
    lines_out.append(f'    """{doc}"""')
    lines_out.append("")

    for method_name in methods:
        if method_name not in method_blocks:
            print(f"  SKIP: {method_name} not found")
            continue
        block = method_blocks[method_name]
        for line in block:
            lines_out.append(line)
        lines_out.append("")

    content = "\n".join(lines_out)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    n_methods = sum(1 for m in methods if m in method_blocks)
    print(f"  Created {filename}: {n_methods} methods, {len(lines_out)} lines")

# ═══════════════════════════════════════════════════════════════════════════════
# GENERATE NEW simulacao.py ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════
backup_path = os.path.join(SIM_DIR, "simulacao_original.py")
shutil.copy2(SIM_PATH, backup_path)
print(f"\n  Backup saved to: simulacao_original.py")

# Build orchestrator
orch = []
orch.append(import_block)
orch.append("")
orch.append("# ── Mixin imports ──")
for mixin_name, mixin_data in MIXIN_DEFS.items():
    module = mixin_data["file"].replace(".py", "")
    orch.append(f"from simulation.{module} import {mixin_name}")
orch.append("")
orch.append("")

# Class definition with mixin bases
bases = ", ".join(MIXIN_DEFS.keys())
orch.append(f"class Simulador({bases}):")

# Class-level code between class def and first method
class_def_line = sim_node.lineno - 1
if method_nodes:
    first_method_line = method_nodes[0].lineno - 1
    j = first_method_line - 1
    while j > class_def_line:
        stripped = source_lines[j].rstrip()
        if stripped == "" or stripped.startswith("    #"):
            j -= 1
        else:
            break
    class_body_end = j + 1
    for i in range(class_def_line + 1, class_body_end):
        orch.append(source_lines[i])

# Add orchestrator methods
for method_name in list(orchestrator_methods):
    if method_name in method_blocks:
        orch.append("")
        for line in method_blocks[method_name]:
            orch.append(line)

# Add unassigned methods
for name in sorted(unassigned):
    if name in method_blocks:
        orch.append("")
        for line in method_blocks[name]:
            orch.append(line)

# Add __main__ block if exists
main_pattern = "if __name__"
for i, line in enumerate(source_lines):
    if main_pattern in line and i > sim_node.end_lineno:
        orch.append("")
        for remaining_line in source_lines[i:]:
            orch.append(remaining_line)
        break

orch.append("")

content = "\n".join(orch)
with open(SIM_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"  Created simulacao.py orchestrator: {len(orch)} lines")

# Summary
print("\n=== SPLIT COMPLETE ===")
print(f"Original: {len(source_lines)} lines")
print(f"Orchestrator: {len(orch)} lines")
total_mixin = 0
for mixin_name, mixin_data in MIXIN_DEFS.items():
    fpath = os.path.join(SIM_DIR, mixin_data["file"])
    with open(fpath, "r") as f:
        n = len(f.readlines())
    total_mixin += n
    print(f"  {mixin_data['file']}: {n} lines")
print(f"Total mixin lines: {total_mixin}")
