"""
Fundacao data-first para campanha.

Entrega deste ciclo:
- carregamento de mapas/missoes por JSON
- grade de navegacao simples
- pathfinding A* sobre metadados de mapa
"""

from __future__ import annotations

from collections import deque
from heapq import heappop, heappush
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
FILE_MAPAS_CAMPANHA = ROOT / "dados" / "mapas_campanha.json"
FILE_MISSOES_CAMPANHA = ROOT / "dados" / "missoes_campanha.json"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_campaign_maps() -> dict:
    return _load_json(FILE_MAPAS_CAMPANHA, {"mapas": []})


def load_campaign_missions() -> dict:
    return _load_json(FILE_MISSOES_CAMPANHA, {"missoes": []})


def build_navigation_grid(map_data: dict) -> dict:
    bounds = map_data.get("bounds", {})
    largura = int(bounds.get("largura", 0) or 0)
    altura = int(bounds.get("altura", 0) or 0)
    nav = map_data.get("nav", {}) or {}
    cell_size = float(nav.get("cell_size", 1.0) or 1.0)
    bloqueados: set[tuple[int, int]] = set()
    for bloco in nav.get("blocos", []):
        bx = int(bloco.get("x", 0) or 0)
        by = int(bloco.get("y", 0) or 0)
        bw = int(bloco.get("w", 0) or 0)
        bh = int(bloco.get("h", 0) or 0)
        for x in range(bx, bx + bw):
            for y in range(by, by + bh):
                bloqueados.add((x, y))
    return {
        "largura": largura,
        "altura": altura,
        "cell_size": cell_size,
        "bloqueados": bloqueados,
    }


def _neighbors(node: tuple[int, int], grid: dict) -> list[tuple[int, int]]:
    width = grid["largura"]
    height = grid["altura"]
    blocked = grid["bloqueados"]
    out = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = node[0] + dx, node[1] + dy
        if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in blocked:
            out.append((nx, ny))
    return out


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(map_data: dict, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    grid = build_navigation_grid(map_data)
    blocked = grid["bloqueados"]
    if start in blocked or goal in blocked:
        return []
    frontier = []
    heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}

    while frontier:
        _, current = heappop(frontier)
        if current == goal:
            break
        for nxt in _neighbors(current, grid):
            new_cost = cost_so_far[current] + 1
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                priority = new_cost + _heuristic(goal, nxt)
                heappush(frontier, (priority, nxt))
                came_from[nxt] = current

    if goal not in came_from:
        return []

    path = deque()
    current = goal
    while current is not None:
        path.appendleft(current)
        current = came_from[current]
    return list(path)

