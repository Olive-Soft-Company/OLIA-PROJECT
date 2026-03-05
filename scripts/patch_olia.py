#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

EXCLUDE_DIRS = {
    ".git", "node_modules", "dist", "build", ".svelte-kit", ".next",
    "venv", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache",
}

INCLUDE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".svelte",
    ".py", ".sh", ".ps1",
    ".yml", ".yaml", ".json", ".toml", ".ini",
    ".md", ".txt", ".html", ".css",
    ".env",
}

CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")

def run(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return any(d in parts for d in EXCLUDE_DIRS)

def is_text_candidate(path: Path) -> bool:
    if path.name in {".env", ".env.example"}:
        return True
    return path.suffix.lower() in INCLUDE_EXTS

def load_rules(rules_file: Path) -> List[Tuple[re.Pattern, str]]:
    data = json.loads(rules_file.read_text(encoding="utf-8"))
    rules: List[Tuple[re.Pattern, str]] = []
    for item in data:
        rules.append((re.compile(item["pattern"]), item["replace"]))
    return rules

def get_changed_files(base_ref: str) -> List[Path]:
    out = run(["git", "diff", "--name-only", "--diff-filter=AM", f"{base_ref}...HEAD"])
    if not out:
        return []
    return [Path(p) for p in out.splitlines()]

def apply_rules(text: str, rules: List[Tuple[re.Pattern, str]]) -> Tuple[str, int]:
    total = 0
    new_text = text
    for pattern, repl in rules:
        new_text, n = pattern.subn(repl, new_text)
        total += n
    return new_text, total

def main():
    ap = argparse.ArgumentParser(
        description="Patch Open WebUI names/vars to OLIA in changed/added files (post-merge)."
    )
    ap.add_argument("--base", required=True, help="Git ref to compare against (e.g., upstream/main, origin/main, SHA)")
    ap.add_argument("--rules", default="scripts/olia_rules.json", help="Path to JSON rules file")
    ap.add_argument("--check", action="store_true", help="Dry-run: no writes. Exit code 2 if changes would be made.")
    ap.add_argument("--backup", action="store_true", help="Create .bak backups before writing.")
    args = ap.parse_args()

    rules_file = Path(args.rules)
    rules = load_rules(rules_file)

    files = get_changed_files(args.base)
    if not files:
        print("No changed/added files detected. Nothing to patch.")
        return

    files_changed = 0
    total_repls = 0
    files_skipped_conflict = 0

    for rel in files:
        if should_skip(rel) or not is_text_candidate(rel):
            continue
        if not rel.exists():
            continue

        try:
            old = rel.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # Skip unresolved merge conflicts
        if any(m in old for m in CONFLICT_MARKERS):
            print(f"[SKIP] {rel} (contains conflict markers)")
            files_skipped_conflict += 1
            continue

        new, n = apply_rules(old, rules)
        if n > 0 and new != old:
            files_changed += 1
            total_repls += n
            print(f"[PATCH] {rel}  ({n} replacements)")

            if not args.check:
                if args.backup:
                    rel.with_suffix(rel.suffix + ".bak").write_text(old, encoding="utf-8")
                rel.write_text(new, encoding="utf-8")

    print("\nSummary:")
    print(f"  Files considered (from git diff): {len(files)}")
    print(f"  Files changed: {files_changed}")
    print(f"  Total replacements: {total_repls}")
    print(f"  Files skipped (conflicts): {files_skipped_conflict}")

    if args.check and files_changed > 0:
        raise SystemExit(2)

if __name__ == "__main__":
    main()