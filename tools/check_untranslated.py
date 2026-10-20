#!/usr/bin/env python3
"""List upstream strings that are new or whose English changed since the translation.
Usage: check_untranslated.py /path/to/pokeldn [--write-todo]
Writes todo.toml (English text of keys to translate) when --write-todo is given."""
import json
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
repo = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else HERE / "work" / "pokeldn")
en = tomllib.loads((repo / "pokeldn/app/data/strings.en.toml").read_text(encoding="utf-8"))
zh = tomllib.loads((HERE.parent / "plugin/strings.toml").read_text(encoding="utf-8"))
snap_file = HERE / "strings.en.snapshot.toml"
snap = tomllib.loads(snap_file.read_text(encoding="utf-8")) if snap_file.exists() else {}
new = sorted(k for k in en if k not in zh)
changed = sorted(k for k in en if k in zh and k in snap and snap[k] != en[k])
gone = sorted(k for k in zh if k not in en)
print(f"upstream keys: {len(en)}  translated: {len(en) - len(new)}  new/untranslated: {len(new)}  "
      f"English changed: {len(changed)}  obsolete in pack: {len(gone)}")
for title, keys in (("NEW (untranslated)", new), ("ENGLISH CHANGED (re-check)", changed)):
    if keys:
        print(f"\n== {title} ==")
        for k in keys:
            print(f"{json.dumps(k)} = {json.dumps(en[k], ensure_ascii=False)}")
if "--write-todo" in sys.argv:
    lines = [f"{json.dumps(k)} = {json.dumps(en[k], ensure_ascii=False)}" for k in new + changed]
    (HERE / "todo.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {HERE / 'todo.toml'} ({len(lines)} entries): translate the values, then run merge_todo.py")
sys.exit(0)
