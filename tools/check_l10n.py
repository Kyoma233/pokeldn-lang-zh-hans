#!/usr/bin/env python3
"""Check the zh pack against an upstream pokeldn checkout.

Usage: check_l10n.py [path/to/pokeldn] [--write-todo]

Compares interface strings, documentation page titles (messages.toml),
and docs/*.md (presence + changes since the last packed upstream tag).

Exit 1 if anything still needs translation. Writes todo files with --write-todo.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLUGIN = ROOT / "plugin"

args = [a for a in sys.argv[1:] if a != "--write-todo"]
write_todo = "--write-todo" in sys.argv
repo = Path(args[0] if args else HERE / "work" / "pokeldn")


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def doc_title(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    m = re.search(r"^title:\s*(.+)$", text[3:end], re.M)
    return m.group(1).strip().strip("\"'") if m else None


def pack_upstream_tag() -> str | None:
    text = (PLUGIN / "plugin.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        return None
    base = m.group(1).split("-zh")[0]
    return f"v{base}" if base else None


def git(*git_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *git_args],
        capture_output=True, text=True, check=False,
    )


def current_tag() -> str | None:
    r = git("describe", "--tags", "--exact-match", "HEAD")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def doc_diff(prev: str, curr: str) -> dict[str, list[str]]:
    out = {"A": [], "M": [], "D": []}
    r = git("diff", "--name-status", prev, curr, "--", "docs/")
    if r.returncode != 0:
        return out
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        name = Path(path).name
        if not name.endswith(".md"):
            continue
        kind = status[0]
        if kind in out:
            out[kind].append(name)
    for k in out:
        out[k] = sorted(set(out[k]))
    return out


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def english_doc_hash(name: str) -> str | None:
    path = repo / "docs" / name
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def docs_already_translated(name: str, hashes: dict) -> bool:
    zh = PLUGIN / "docs" / name
    return zh.is_file() and hashes.get(name) == english_doc_hash(name)


en = load_toml(repo / "pokeldn/app/data/strings.en.toml")
zh = load_toml(PLUGIN / "strings.toml")
snap = load_toml(HERE / "strings.en.snapshot.toml")
messages = load_toml(PLUGIN / "messages.toml")

new = sorted(k for k in en if k not in zh)
changed = sorted(k for k in en if k in zh and k in snap and snap[k] != en[k])
gone = sorted(k for k in zh if k not in en)

upstream_docs = sorted((repo / "docs").glob("*.md"))
titles = {p.name: doc_title(p) for p in upstream_docs}
missing_titles = sorted({t for t in titles.values() if t} - set(messages))
plugin_docs = {p.name for p in (PLUGIN / "docs").glob("*.md")}
upstream_names = {p.name for p in upstream_docs}
docs_missing = sorted(upstream_names - plugin_docs)
docs_extra = sorted(n for n in plugin_docs - upstream_names if n != "guide.md")

prev = pack_upstream_tag()
curr = current_tag()
diff = {"A": [], "M": [], "D": []}
diff_error = None
if prev and curr and prev != curr:
    r = git("rev-parse", "--verify", f"{prev}^{{commit}}")
    if r.returncode != 0:
        diff_error = f"previous tag {prev} not in upstream clone (fetch --tags?)"
    else:
        diff = doc_diff(prev, curr)

source_hashes = load_toml(HERE / "docs-source-hash.toml")
docs_todo = sorted(
    n for n in set(diff["A"] + diff["M"] + docs_missing)
    if not docs_already_translated(n, source_hashes)
)

print(
    f"upstream keys: {len(en)}  translated: {len(en) - len(new)}  new/untranslated: {len(new)}  "
    f"English changed: {len(changed)}  obsolete in pack: {len(gone)}"
)
print(
    f"doc titles: {len(titles)}  messages: {len(messages)}  missing titles: {len(missing_titles)}  "
    f"docs missing: {len(docs_missing)}  docs changed: {len(diff['M'])}  docs new: {len(diff['A'])}  "
    f"docs removed upstream: {len(diff['D'])}"
)
if prev or curr:
    print(f"pack upstream: {prev or '?'}  checkout: {curr or '?'}{f'  ({diff_error})' if diff_error else ''}")

pending = False

for title, keys in (("NEW (untranslated)", new), ("ENGLISH CHANGED (re-check)", changed)):
    if keys:
        pending = True
        print(f"\n== {title} ==")
        for k in keys:
            print(f"{json.dumps(k)} = {json.dumps(en[k], ensure_ascii=False)}")
if gone:
    print(f"\n== OBSOLETE (will be dropped by merge_todo.py) ==")
    for k in gone:
        print(json.dumps(k))

if missing_titles:
    pending = True
    print("\n== MISSING DOC TITLES (messages.toml) ==")
    for t in missing_titles:
        print(f"{json.dumps(t, ensure_ascii=False)} = {json.dumps(t, ensure_ascii=False)}")

if docs_todo or diff["D"] or docs_extra or diff_error:
    if docs_todo or diff_error:
        pending = True
    print("\n== DOCS ==")
    for label, names in (
        ("new or missing in pack", sorted(set(diff["A"] + docs_missing))),
        ("English changed", diff["M"]),
        ("removed upstream (delete from pack?)", sorted(set(diff["D"] + docs_extra))),
    ):
        if names:
            print(f"{label}:")
            for n in names:
                print(f"  {n}")
    if diff_error:
        print(diff_error)

if write_todo:
    string_lines = [f"{json.dumps(k)} = {json.dumps(en[k], ensure_ascii=False)}" for k in new + changed]
    write_lines(HERE / "todo.toml", string_lines)
    msg_lines = [f"{json.dumps(t, ensure_ascii=False)} = {json.dumps(t, ensure_ascii=False)}" for t in missing_titles]
    write_lines(HERE / "todo-messages.toml", msg_lines)
    doc_lines = ["# new or changed English docs; run: python3 tools/translate_docs.py", *docs_todo]
    write_lines(HERE / "todo-docs.txt", doc_lines if docs_todo else [])
    print(
        f"\nwrote {HERE / 'todo.toml'} ({len(string_lines)} strings), "
        f"{HERE / 'todo-messages.toml'} ({len(msg_lines)} titles), "
        f"{HERE / 'todo-docs.txt'} ({len(docs_todo)} docs)"
    )

if pending:
    print("\ntranslation incomplete; pack/publish is blocked until this is clean")
    sys.exit(1)
print("\nl10n check clean")
sys.exit(0)
