#!/usr/bin/env python3
"""Merge translated todo files into the pack and refresh the English snapshot.

Usage: merge_todo.py [path/to/pokeldn]

Reads tools/todo.toml (strings) and tools/todo-messages.toml (doc titles).
Drops obsolete string keys no longer in upstream. Refuses placeholder mismatches.
"""
import json, string, sys, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLUGIN = ROOT / "plugin"
repo = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "work" / "pokeldn")


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def fields(s):
    return sorted((n, sp, c) for _, n, sp, c in string.Formatter().parse(s) if n is not None)


def dump_toml(comment: str, data: dict) -> str:
    lines = [comment]
    lines += [f"{json.dumps(k, ensure_ascii=False)} = {json.dumps(data[k], ensure_ascii=False)}" for k in sorted(data)]
    return "\n".join(lines) + "\n"


en = load_toml(repo / "pokeldn/app/data/strings.en.toml")
zh = load_toml(PLUGIN / "strings.toml")
todo_file = HERE / "todo.toml"
todo = load_toml(todo_file)

bad = [k for k, v in todo.items() if k in en and fields(v) != fields(en[k])]
if bad:
    sys.exit("placeholder mismatch, fix these in todo.toml:\n" + "\n".join(bad))

zh.update({k: v for k, v in todo.items() if k in en and v != en[k]})
untranslated = [k for k, v in todo.items() if k in en and v == en[k]]
kept = {k: v for k, v in zh.items() if k in en}
(PLUGIN / "strings.toml").write_text(
    dump_toml(
        "# 简体中文 (zh-Hans) translations for pokeldn. key = English key from pokeldn/app/data/strings.en.toml",
        kept,
    ),
    encoding="utf-8",
)
(HERE / "strings.en.snapshot.toml").write_text(
    (repo / "pokeldn/app/data/strings.en.toml").read_text(encoding="utf-8"),
    encoding="utf-8",
)
todo_file.unlink(missing_ok=True)
if untranslated:
    print(f"{len(untranslated)} string todo entries still English (left untranslated)")
print(f"merged strings; pack now has {len(kept)} strings")

msg_todo_file = HERE / "todo-messages.toml"
msg_todo = load_toml(msg_todo_file)
if msg_todo or msg_todo_file.exists():
    messages = load_toml(PLUGIN / "messages.toml")
    still = [k for k, v in msg_todo.items() if v == k]
    messages.update({k: v for k, v in msg_todo.items() if v != k})
    (PLUGIN / "messages.toml").write_text(
        dump_toml(
            "# English documentation page titles → 简体中文 (shown in Docs nav via i18n.message)",
            messages,
        ),
        encoding="utf-8",
    )
    msg_todo_file.unlink(missing_ok=True)
    if still:
        print(f"{len(still)} message titles still English (left untranslated)")
    print(f"merged messages; pack now has {len(messages)} titles")
