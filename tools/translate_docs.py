#!/usr/bin/env python3
"""Translate pokeldn docs Markdown EN → zh-Hans via OpenRouter free models.

Paid DeepSeek API is banned (Kyoma 2026-10-26). Do not call api.deepseek.com.
"""
from __future__ import annotations
import json, os, re, sys, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request
import urllib.error

def _load_openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    secret = Path("/home/box/.secrets/openrouter.txt")
    if not key and secret.is_file():
        key = secret.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing (also checked /home/box/.secrets/openrouter.txt)")
    return key

API = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("TRANSLATE_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
if "deepseek.com" in API.lower() or (MODEL.lower().startswith("deepseek") and ":free" not in MODEL):
    raise SystemExit(f"REFUSING paid DeepSeek config: API={API!r} MODEL={MODEL!r}")
if not MODEL.endswith(":free") and os.environ.get("ALLOW_PAID_TRANSLATE") != "1":
    raise SystemExit(f"REFUSING non-free model {MODEL!r}; set TRANSLATE_MODEL to an OpenRouter :free model")
KEY = _load_openrouter_key()
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/work/pokeldn/docs"
DST = ROOT / "plugin/docs"
LOG = ROOT / "tools/work/translate_logs"
TODO = ROOT / "tools/todo-docs.txt"
MESSAGES_FILE = ROOT / "plugin/messages.toml"
LOG.mkdir(parents=True, exist_ok=True)

def load_messages() -> dict:
    import tomllib
    if not MESSAGES_FILE.exists():
        return {}
    return tomllib.loads(MESSAGES_FILE.read_text(encoding="utf-8"))

def save_messages(messages: dict) -> None:
    import json
    lines = ["# English documentation page titles → 简体中文 (shown in Docs nav via i18n.message)"]
    for k in sorted(messages):
        lines.append(f"{json.dumps(k, ensure_ascii=False)} = {json.dumps(messages[k], ensure_ascii=False)}")
    MESSAGES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

TITLE_ZH = {
    'Adapters': '适配器',
    'Brilliant Diamond and Shining Pearl': '晶灿钻石／明亮珍珠',
    'Code on the console': '主机上的代码',
    'Code organization': '代码组织',
    'Code signing policy': '代码签名策略',
    'Command-line usage': '命令行用法',
    'Controller board': '手柄板',
    'Desktop builds': '桌面版构建',
    'ESP32 radio': 'ESP32 无线电',
    'FireRed and LeafGreen': '火红／叶绿',
    'Hardware and setup': '硬件与设置',
    'Home': '首页',
    'Host implementation': '主机端实现',
    'Joining and the Pia layer': '加入与 Pia 层',
    'LeafGreen': '叶绿',
    'Legends Arceus': '传说 阿尔宙斯',
    'Legends Z-A': '传说 Z-A',
    "Let's Go Pikachu and Eevee": '去吧！皮卡丘／去吧！伊布',
    'Max Raid Battles': '极巨团体战',
    'Mystery Gift': '神秘礼物',
    'Mystery Gift files': '神秘礼物文件',
    'Online trade': '在线交换',
    'Plugins': '插件',
    'Raspberry Pi host': '树莓派主机',
    'Reverse-engineering a Switch title': '逆向分析 Switch 游戏',
    'Ruby, Sapphire and Emerald': '红宝石／蓝宝石／绿宝石',
    'Scarlet and Violet': '朱／紫',
    'Simulated Mystery Gifts': '模拟神秘礼物',
    'Switch keys on the Pi': '树莓派上的 Switch 密钥',
    'Sword and Shield': '剑／盾',
    'Tera Raids': '太晶团体战',
    "The Let's Go cartridge and session": '去吧！卡带与会话',
    'The Link Trade': '连接交换',
    'The Mystery Gift menu': '神秘礼物菜单',
    'The Pia layer': 'Pia 层',
    'The ROM map': 'ROM 映射',
    'The Union Room trade': '联盟房间交换',
    'The cartridge and the session': '卡带与会话',
    'The game protocol': '游戏协议',
    'The link protocol': '连接协议',
    'The random number generator': '随机数生成器',
    'The sync framework': '同步框架',
    'The wireless layer': '无线层',
    'Union Circle': '联合环',
}

SYSTEM = """你是资深技术文档译者，把 pokeldn（宝可梦本地无线工具）的英文 Markdown 文档译为简体中文。

硬性规则：
1. 保留 YAML frontmatter 原样（title 等字段不要改成中文）。
2. 正文一级标题 # 译成中文；二级及以下标题也译成中文。
3. 代码块（``` 或缩进 4 空格的代码）、行内代码 `...`、URL、文件路径、十六进制地址、寄存器名、类名/函数名/字段名、命令行、JSON、表中代码列 —— 一律不翻译。
4. Markdown 链接语法保留：链接文字可译，链接目标（文件名/锚点）保留英文原样。锚点若指向英文标题的 slug，保留原 slug。
5. 宝可梦官方简中译名：Pokémon→宝可梦，Mystery Gift→神秘礼物，Wonder Card→神秘卡片，Link Trade→连接交换，Union Room→联盟房间，Union Circle→联合环，Tera Raid→太晶团体战，Max Raid→极巨团体战，Dynamax Adventure→极巨大冒险，Max Lair→极巨巢穴，Gigantamax→超极巨化，Dynamax→极巨化，FireRed/LeafGreen→火红／叶绿，Ruby/Sapphire/Emerald→红宝石／蓝宝石／绿宝石，Sword/Shield→剑／盾，Scarlet/Violet→朱／紫，Brilliant Diamond/Shining Pearl→晶灿钻石／明亮珍珠，Legends Arceus→传说 阿尔宙斯，Legends Z-A→传说 Z-A，Let's Go Pikachu/Eevee→去吧！皮卡丘／去吧！伊布，shiny→异色。
6. 语气贴近已有汉化：简洁、技术准确、用「／」连接并列游戏名。不要添加原文没有的解释，不要删减技术细节。
7. 只输出译好的 Markdown 全文，不要包裹在代码围栏里，不要前言后语。
"""

# Chunk large docs by ## headings when over this many chars
CHUNK_CHARS = 12000


def chat(messages: list[dict], temperature: float = 0.2, retries: int = 5) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": int(os.environ.get("TRANSLATE_MAX_TOKENS", "8192")),
    }).encode()
    for attempt in range(retries):
        req = urllib.request.Request(
            API, data=body, method="POST",
            headers={
                "Authorization": f"Bearer {KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Kyoma233/pokeldn-lang-zh-hans",
                "X-Title": "pokeldn-zh-docs-translate",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.load(r)
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"HTTP {e.code}: {err[:500]}") from e
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


def split_frontmatter(text: str) -> tuple[str, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5], text[end + 5 :]
    return "", text


def chunk_body(body: str) -> list[str]:
    if len(body) <= CHUNK_CHARS:
        return [body]
    parts: list[str] = []
    # Split on ## headings but keep heading with its section
    sections = re.split(r"(?m)(?=^## )", body)
    buf = ""
    for sec in sections:
        if not sec:
            continue
        if buf and len(buf) + len(sec) > CHUNK_CHARS:
            parts.append(buf)
            buf = sec
        else:
            buf += sec
    if buf:
        parts.append(buf)
    # If a single section is still huge, hard-split by paragraphs
    out: list[str] = []
    for p in parts:
        if len(p) <= CHUNK_CHARS * 1.5:
            out.append(p)
            continue
        paras = re.split(r"\n\n+", p)
        buf = ""
        for para in paras:
            piece = para if not buf else "\n\n" + para
            if buf and len(buf) + len(piece) > CHUNK_CHARS:
                out.append(buf)
                buf = para
            else:
                buf = (buf + piece) if buf else para
        if buf:
            out.append(buf)
    return out


def translate_body(name: str, body: str, title_zh: str = "") -> str:
    chunks = chunk_body(body)
    translated: list[str] = []
    for i, chunk in enumerate(chunks):
        hint = f"一级标题建议译为：{title_zh}\n" if title_zh and i == 0 else ""
        user = (
            f"文件名: {name}\n"
            f"{hint}"
            f"这是第 {i+1}/{len(chunks)} 段（请只翻译本段，保持与前后段衔接的标题层级）。\n\n"
            f"{chunk}"
        )
        out = chat([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ])
        # Strip accidental outer fences
        out = out.strip()
        if out.startswith("```") and out.endswith("```"):
            out = re.sub(r"^```(?:markdown|md)?\n?", "", out)
            out = re.sub(r"\n?```$", "", out)
        translated.append(out)
        print(f"  {name}: chunk {i+1}/{len(chunks)} ok ({len(chunk)}→{len(out)})", flush=True)
    # Join chunks. Sections starting with ## need a separating newline.
    out = translated[0]
    for c in translated[1:]:
        if not out.endswith("\n"):
            out += "\n"
        if c.lstrip().startswith("#") and not out.endswith("\n\n"):
            out += "\n"
        out += c
    return out


def translate_file(name: str) -> str:
    if not name.endswith(".md"):
        name = name + ".md"
    en_path = SRC / name
    text = en_path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    print(f"START {name} ({len(text)} bytes, body {len(body)})", flush=True)
    en_title = ""
    title_hint = ""
    if fm:
        mt = re.search(r"^title:\s*(.+)$", fm, re.M)
        if mt:
            en_title = mt.group(1).strip().strip('"').strip("'")
            messages = load_messages()
            title_hint = messages.get(en_title) or TITLE_ZH.get(en_title, "")
    zh_body = translate_body(name, body, title_hint)
    if zh_body and not zh_body.startswith("\n"):
        zh_body = "\n" + zh_body
    if not zh_body.endswith("\n"):
        zh_body += "\n"
    result = fm + zh_body
    out = DST / name
    out.write_text(result, encoding="utf-8")
    (LOG / f"{name}.ok").write_text(f"{len(text)}->{len(result)}\n", encoding="utf-8")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", result))
    print(f"DONE  {name}: {len(result)} bytes, cjk={cjk}", flush=True)
    if cjk < 50 and len(body) > 500:
        raise RuntimeError(f"{name}: suspiciously few CJK chars ({cjk})")
    if en_title:
        h1 = re.search(r"^# (.+)$", zh_body, re.M)
        zh_title = (h1.group(1).strip() if h1 else "") or title_hint
        if zh_title and zh_title != en_title:
            messages = load_messages()
            if messages.get(en_title) != zh_title:
                messages[en_title] = zh_title
                save_messages(messages)
                print(f"  messages.toml: {en_title!r} → {zh_title!r}", flush=True)
    return name


def docs_from_todo() -> list[str]:
    if not TODO.exists():
        return []
    names = []
    for line in TODO.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line if line.endswith(".md") else line + ".md")
    return names


def main():
    if len(sys.argv) > 1:
        todo = [a if a.endswith(".md") else a + ".md" for a in sys.argv[1:]]
    else:
        todo = docs_from_todo()
    if not todo:
        raise SystemExit("usage: translate_docs.py [gui.md ...]  (or write tools/todo-docs.txt)")
    missing = [n for n in todo if not (SRC / n).is_file()]
    if missing:
        raise SystemExit("English docs not found: " + ", ".join(missing))
    todo.sort(key=lambda n: (SRC / n).stat().st_size)
    print(f"todo {len(todo)} files", flush=True)
    workers = int(os.environ.get("TRANSLATE_WORKERS", "4"))
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(translate_file, n): n for n in todo}
        for fut in as_completed(futs):
            n = futs[fut]
            try:
                fut.result()
            except Exception as e:
                (LOG / f"{n}.err").write_text(repr(e), encoding="utf-8")
                print(f"FAIL  {n}: {e}", flush=True)
                failed.append(n)
    if failed:
        print("FAILED:", failed, flush=True)
        sys.exit(1)
    TODO.unlink(missing_ok=True)
    print("ALL OK", flush=True)


if __name__ == "__main__":
    main()
