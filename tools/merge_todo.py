#!/usr/bin/env python3
"""Merge translated todo.toml into plugin/strings.toml, check placeholders, refresh the English snapshot.
Usage: merge_todo.py [/path/to/pokeldn]"""
import json, string, sys, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
repo = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "work" / "pokeldn")
en = tomllib.loads((repo / "pokeldn/app/data/strings.en.toml").read_text(encoding="utf-8"))
zh = tomllib.loads((HERE.parent / "plugin/strings.toml").read_text(encoding="utf-8"))
todo_file = HERE / "todo.toml"
todo = tomllib.loads(todo_file.read_text(encoding="utf-8")) if todo_file.exists() else {}

def fields(s):
    return sorted((n, sp, c) for _, n, sp, c in string.Formatter().parse(s) if n is not None)

bad = [k for k, v in todo.items() if k in en and fields(v) != fields(en[k])]
if bad:
    sys.exit("placeholder mismatch, fix these in todo.toml:\n" + "\n".join(bad))
zh.update({k: v for k, v in todo.items() if k in en and v != en[k]})
out = ["# 简体中文 (zh-Hans) translations for pokeldn. key = English key from pokeldn/app/data/strings.en.toml"]
out += [f"{json.dumps(k, ensure_ascii=False)} = {json.dumps(zh[k], ensure_ascii=False)}" for k in sorted(zh) if k in en]
(HERE.parent / "plugin/strings.toml").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "strings.en.snapshot.toml").write_text((repo / "pokeldn/app/data/strings.en.toml").read_text(encoding="utf-8"), encoding="utf-8")
untranslated = [k for k, v in todo.items() if k in en and v == en[k]]
if untranslated:
    print(f"{len(untranslated)} todo entries still English (left untranslated)")
todo_file.unlink(missing_ok=True)
print(f"merged; pack now has {len(out) - 1} strings")
