from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "documentacao" / "auditoria"

TEXT_EXTENSIONS = {
    ".py",
    ".pyi",
    ".md",
    ".toml",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".c",
}
GENERATED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    ".git",
    "saidas",
    "_db_shadow",
    ".tmp.driveupload",
    "_tmp_ui_reports",
    ".tmp_ui",
}
GENERATED_EXTENSIONS = {
    ".pyc",
    ".db",
    ".log",
    ".mp3",
    ".wav",
    ".mp4",
    ".xlsx",
    ".zip",
}
MOJIBAKE_MARKERS = ("Ã", "â", "ð", "\ufffd")
SEVERITY_RANK = {
    "nenhuma": 0,
    "baixa": 1,
    "media": 2,
    "alta": 3,
    "critica": 4,
}


@dataclass
class FileEntry:
    path: str
    kind: str
    severity: str
    confidence: str
    regression_risk: str
    approx_test_coverage: str
    recommended_action: str
    size_bytes: int
    notes: list[str]
    metrics: dict[str, Any]


@dataclass
class FunctionEntry:
    path: str
    function: str
    line: int
    end_line: int
    parent: str | None
    kind: str
    severity: str
    confidence: str
    regression_risk: str
    approx_test_coverage: str
    recommended_action: str
    notes: list[str]
    metrics: dict[str, Any]


def _timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def iter_workspace_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root, onerror=lambda _err: None):
        current = Path(current_root)
        dirnames[:] = [name for name in dirnames if name not in GENERATED_DIR_NAMES]
        for name in filenames:
            files.append(current / name)
    return files


def classify_path(rel_path: Path) -> str:
    parts = rel_path.parts
    if any(part in GENERATED_DIR_NAMES for part in parts):
        return "gerado"
    if rel_path.suffix.lower() in GENERATED_EXTENSIONS:
        return "gerado"
    if not parts:
        return "legado"
    if parts[0] == "neural H":
        return "legado"
    if parts[0] == "neural":
        if len(parts) >= 2 and parts[1] == "world_map_pygame":
            return "integracao"
        return "ativo"
    return "legado"


def approx_test_coverage(rel_path: Path, test_text: str) -> str:
    if rel_path.suffix.lower() != ".py":
        return "n/a"
    candidates = {
        rel_path.stem.lower(),
        str(rel_path.with_suffix("")).replace("\\", "/").lower(),
        ".".join(rel_path.with_suffix("").parts[-2:]).lower(),
    }
    if any(token and token in test_text for token in candidates):
        return "referenciado"
    return "nao_referenciado"


def _max_severity(current: str, candidate: str) -> str:
    return candidate if SEVERITY_RANK[candidate] > SEVERITY_RANK[current] else current


def _risk_for(kind: str, severity: str) -> str:
    if severity in {"alta", "critica"}:
        return "alto"
    if severity == "media":
        return "medio"
    if kind == "ativo":
        return "medio"
    if kind == "integracao":
        return "medio"
    if kind == "gerado":
        return "baixo"
    return "baixo"


def _action_for(kind: str, severity: str) -> str:
    if kind == "gerado":
        return "manter"
    if kind == "legado":
        return "arquivar"
    if severity in {"alta", "critica"}:
        return "corrigir"
    if severity == "media":
        return "refatorar"
    return "manter"


def _mojibake_hits(text: str) -> int:
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)


def _count_regex(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _iter_function_nodes(tree: ast.AST) -> list[tuple[ast.AST, ast.FunctionDef | ast.AsyncFunctionDef]]:
    parents = _parent_map(tree)
    out: list[tuple[ast.AST, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((parents.get(node), node))
    return out


def _node_note_bundle(source_lines: list[str], node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, list[str], dict[str, Any]]:
    start = node.lineno
    end = getattr(node, "end_lineno", node.lineno)
    snippet = "\n".join(source_lines[start - 1 : end])
    length = end - start + 1
    except_count = _count_regex(r"\bexcept\s+Exception\b", snippet)
    todo_count = _count_regex(r"TODO|FIXME|XXX", snippet)

    severity = "nenhuma"
    notes: list[str] = []
    if length > 250:
        severity = _max_severity(severity, "alta")
        notes.append(f"funcao longa ({length} linhas)")
    elif length > 80:
        severity = _max_severity(severity, "media")
        notes.append(f"funcao extensa ({length} linhas)")
    if except_count:
        severity = _max_severity(severity, "media" if except_count < 3 else "alta")
        notes.append(f"captura generica de excecao x{except_count}")
    if todo_count:
        severity = _max_severity(severity, "baixa")
        notes.append(f"pendencias TODO/FIXME x{todo_count}")
    metrics = {
        "length": length,
        "except_exception_count": except_count,
        "todo_count": todo_count,
    }
    return severity, notes, metrics


def build_ledger(root: Path) -> dict[str, Any]:
    all_files = iter_workspace_files(root)
    test_root = PROJECT_ROOT / "tests"
    test_text = ""
    if test_root.exists():
        chunks: list[str] = []
        for path in test_root.rglob("test_*.py"):
            try:
                chunks.append(_read_text(path).lower())
            except OSError:
                continue
        test_text = "\n".join(chunks)

    file_entries: list[FileEntry] = []
    function_entries: list[FunctionEntry] = []
    summary_counter = Counter()

    for path in sorted(all_files):
        rel_path = path.relative_to(root)
        kind = classify_path(rel_path)
        summary_counter[kind] += 1
        notes: list[str] = []
        severity = "nenhuma"
        confidence = "alta"
        metrics: dict[str, Any] = {
            "suffix": path.suffix.lower(),
        }
        text = ""

        if kind == "gerado":
            notes.append("artefato gerado ou dado efemero fora da fonte de verdade")
        if path.suffix.lower() in TEXT_EXTENSIONS:
            try:
                text = _read_text(path)
            except OSError as exc:
                severity = "alta"
                confidence = "alta"
                notes.append(f"falha de leitura: {exc}")
                text = ""
            if text:
                line_count = text.count("\n") + 1
                metrics["line_count"] = line_count
                mojibake_hits = _mojibake_hits(text)
                if mojibake_hits:
                    severity = _max_severity(severity, "media")
                    confidence = "media"
                    notes.append(f"possivel mojibake/encoding inconsistente ({mojibake_hits} marcadores)")
                    metrics["mojibake_hits"] = mojibake_hits
        else:
            metrics["line_count"] = None

        coverage = approx_test_coverage(rel_path, test_text)
        if kind in {"ativo", "integracao"} and path.suffix.lower() == ".py" and coverage == "nao_referenciado":
            severity = _max_severity(severity, "baixa")
            confidence = "media"
            notes.append("sem referencia aproximada na suite de testes")

        if path.suffix.lower() == ".py" and text:
            except_count = _count_regex(r"\bexcept\s+Exception\b", text)
            todo_count = _count_regex(r"TODO|FIXME|XXX", text)
            metrics["except_exception_count"] = except_count
            metrics["todo_count"] = todo_count
            if except_count:
                severity = _max_severity(severity, "media" if except_count < 6 else "alta")
                notes.append(f"captura generica de excecao x{except_count}")
            if todo_count:
                severity = _max_severity(severity, "baixa")
                notes.append(f"pendencias TODO/FIXME x{todo_count}")

            try:
                tree = ast.parse(text, filename=str(path))
                function_nodes = _iter_function_nodes(tree)
                metrics["function_count"] = len(function_nodes)
                metrics["class_count"] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                long_functions = 0
                source_lines = text.splitlines()
                for parent, node in function_nodes:
                    fn_severity, fn_notes, fn_metrics = _node_note_bundle(source_lines, node)
                    long_functions += 1 if fn_metrics["length"] > 80 else 0
                    parent_name = parent.name if isinstance(parent, ast.ClassDef) else None
                    function_entries.append(
                        FunctionEntry(
                            path=str(rel_path).replace("\\", "/"),
                            function=node.name,
                            line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            parent=parent_name,
                            kind=kind,
                            severity=fn_severity,
                            confidence="alta" if fn_severity != "baixa" else "media",
                            regression_risk=_risk_for(kind, fn_severity),
                            approx_test_coverage=coverage,
                            recommended_action=_action_for(kind, fn_severity),
                            notes=fn_notes or ["sem finding automatico relevante"],
                            metrics=fn_metrics,
                        )
                    )
                    severity = _max_severity(severity, fn_severity)
                metrics["long_function_count"] = long_functions
            except SyntaxError as exc:
                severity = _max_severity(severity, "critica")
                confidence = "alta"
                notes.append(f"erro de sintaxe: {exc.msg} (linha {exc.lineno})")
                metrics["syntax_error"] = exc.msg

        if not notes:
            notes.append("sem finding automatico relevante")

        file_entries.append(
            FileEntry(
                path=str(rel_path).replace("\\", "/"),
                kind=kind,
                severity=severity,
                confidence=confidence,
                regression_risk=_risk_for(kind, severity),
                approx_test_coverage=coverage,
                recommended_action=_action_for(kind, severity),
                size_bytes=path.stat().st_size,
                notes=notes,
                metrics=metrics,
            )
        )

    severity_counter = Counter(entry.severity for entry in file_entries)
    top_files = sorted(
        file_entries,
        key=lambda entry: (
            SEVERITY_RANK[entry.severity],
            entry.metrics.get("except_exception_count", 0),
            entry.metrics.get("line_count") or 0,
        ),
        reverse=True,
    )[:25]
    top_functions = sorted(
        function_entries,
        key=lambda entry: (
            SEVERITY_RANK[entry.severity],
            entry.metrics.get("length", 0),
            entry.metrics.get("except_exception_count", 0),
        ),
        reverse=True,
    )[:50]

    return {
        "generated_at": _timestamp(),
        "workspace_root": str(root),
        "project_root": str(PROJECT_ROOT),
        "summary": {
            "total_files": len(file_entries),
            "total_functions": len(function_entries),
            "by_kind": dict(summary_counter),
            "by_severity": dict(severity_counter),
        },
        "top_file_hotspots": [asdict(entry) for entry in top_files],
        "top_function_hotspots": [asdict(entry) for entry in top_functions],
        "files": [asdict(entry) for entry in file_entries],
        "functions": [asdict(entry) for entry in function_entries],
    }


def write_outputs(ledger: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "audit_ledger.json"
    json_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Audit Summary",
        "",
        f"- Generated at: `{ledger['generated_at']}`",
        f"- Workspace root: `{ledger['workspace_root']}`",
        f"- Total files: `{ledger['summary']['total_files']}`",
        f"- Total functions: `{ledger['summary']['total_functions']}`",
        "",
        "## Breakdown",
        "",
    ]
    for kind, count in sorted(ledger["summary"]["by_kind"].items()):
        lines.append(f"- `{kind}`: {count}")
    lines.extend(["", "## Severity", ""])
    for severity, count in sorted(ledger["summary"]["by_severity"].items(), key=lambda item: SEVERITY_RANK[item[0]], reverse=True):
        lines.append(f"- `{severity}`: {count}")

    lines.extend(["", "## Top File Hotspots", ""])
    for entry in ledger["top_file_hotspots"][:15]:
        joined_notes = "; ".join(entry["notes"][:3])
        lines.append(f"- `{entry['path']}` [{entry['severity']}] -> {joined_notes}")

    lines.extend(["", "## Top Function Hotspots", ""])
    for entry in ledger["top_function_hotspots"][:20]:
        parent = f"{entry['parent']}." if entry["parent"] else ""
        joined_notes = "; ".join(entry["notes"][:3])
        lines.append(
            f"- `{entry['path']}:{entry['line']}` `{parent}{entry['function']}` "
            f"[{entry['severity']}] -> {joined_notes}"
        )

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- Raw ledger: `audit_ledger.json`",
            "- Checklist report is generated by `scripts/run_audit_checklist.py`.",
        ]
    )
    (output_dir / "audit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# Auditoria Automatizada\n\n"
        "- `audit_ledger.json`: ledger completo por arquivo e funcao.\n"
        "- `audit_summary.md`: resumo humano dos hotspots.\n"
        "- `audit_checklist.json` / `audit_checklist.md`: saude executavel do projeto.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a project-wide audit ledger.")
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    ledger = build_ledger(args.workspace_root)
    write_outputs(ledger, args.output_dir)
    print(f"[audit] ledger written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
