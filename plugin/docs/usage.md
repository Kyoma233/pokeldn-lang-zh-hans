---
title: Command-line usage
---

# 命令行用法

本页列出各作品的命令行入口。请在仓库根目录运行。源码工具需要 Python 3.11+、Switch 的 `prod.keys`（默认 `~/.switch/prod.keys`，或 `--keys PATH`），以及已刷好的 ESP32 开发板。见[支持的开发板](hardware_esp32.md#supported-boards)与[构建与刷写](hardware_esp32.md#building-and-flashing)。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
dotnet build -c Release services/pkhex
export POKELDN_RADIO=esp32:auto
python -m pokeldn --list
python -m pokeldn --radio esp32:auto swsh-host --offer-file offer.pk8
```

交换工具需要 .NET 10 SDK。PyPI 上的 `ldn` 包是另一套库。Windows 上使用 `.venv\Scripts\Activate.ps1` 与 `$env:POKELDN_RADIO = "esp32:auto"`。`esp32:auto` 选用唯一的 USB 串口；`esp32:PORT` 指定某一个（[无线电设置](hardware_esp32.md#running)）。每个入口都接受 `--help`。

## 火红／叶绿

在主机上解锁直连角，并准备至少两只 `.pk3` 队伍成员。

```bash
./.venv/bin/python bin/frlg_trade_join.py --live -o output.pk3 PARTY1.pk3 PARTY2.pk3   # 加入 Switch 的交换
./.venv/bin/python bin/frlg_trade_host.py -o output.pk3 PARTY1.pk3 PARTY2.pk3          # 托管直连角交换
```

主机送出 `PARTY2.pk3`，把收到的写入 `output.pk3`。默认来自 `config/host.toml`，再是 `config/host.local.toml`；命令行标志覆盖两者（`--print-effective-config`）。出现 `Hosting Direct Corner` 后：直连角 → 加入小组 → pokeldn 的训练家 → 选择并确认。`--trades N`（1 到 6）按交换送出槽位 0 到 N-1；最后一笔后选 CANCEL、YES。

| 标志 | 用途 |
|---|---|
| `--keys PATH` | `prod.keys` 位置 |
| `--slot N` | 从零开始的队伍成员序号 |
| `--capture FILE` | JSONL 诊断抓取 |
| `--config` / `--local-config` / `--no-local-config` | 替换或禁用某层配置 |
| `--ot NAME`、`--version firered\|leafgreen`、`--id TID[:SID]` | 本次运行的训练家覆盖（各 0..65535；LinkPlayer ID 为 `(SID << 16) \| TID`） |
| `--verbose` | 逐包输出；仅与 `--replay` 合用时会卡住实时连接 |

其他默认见 [`pokeldn/config.py`](../pokeldn/config.py) 的 `DEFAULT_TRAINER`。协议：[连接协议](frlg_link.md)。

### 联盟房间

`--union-room` 服务中间 NPC；主机约 10 秒后连接。一条连接只承载一笔交换（`union_room.c:1744`）。`--board-type normal` 登记到交换板，`--union-room-chat` 配合 `--chat-message`／`--chat-file` 聊天，`--union-room-battle --battle-fight` 对战（两只非蛋、30 级或以下的宝可梦）。

```bash
./.venv/bin/python bin/frlg_trade_host.py --union-room --union-room-keepalive 120 PARTY1.pk3 PARTY2.pk3
```

### 神秘礼物

`bin/frlg_mg_host.py` 在神秘礼物 → 奇妙卡片 → 朋友路径发送奇妙卡片与交付脚本。`--make-artifact` 写出已发送字节的 `.ram.lst`。目录：[神秘礼物](frlg_gift.md)。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --gift beast-cutscene --flag-id 1005 --capture mystery-gift.jsonl
```

三神兽跟随御三家（妙蛙种子→水君，杰尼龟→炎帝，小火龙→雷公）。

### 奇妙新闻

`--news` 服务神秘礼物 → 奇妙新闻 → 朋友。主机仅在新闻与已有内容不同时保留；`--news-id N` 可强制新编号。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --news berry --news-id 7
```

### 存档备份与恢复

朋友路径把 128 KB 存档拷成 `.sav`（约四分钟）或写回；未完成的恢复会保留原存档（[细节](frlg_gift.md#save-backup-and-restore)）。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-backup backup.sav --save-resume-dir partial
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-restore backup.sav
```

### 主机存档

`save-dump` 读取实时存档；`flash-patch` 重写某扇区的具名字节并更新校验与计数器。写入前请先读[从 RAM 快照合成扇区](frlg_rom.md#composing-a-sector-from-a-ram-snapshot)。载荷：[主机上的代码](frlg_rom.md)。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin
./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script flash-patch --flash-id 0 \
  --flash-patch-offset 0x00 --flash-patch-hex cac9c5bfc6bec8ff --write-unsafe
```

## 去吧！皮卡丘／伊布

pokeldn 可主机或加入。双方送出 232 字节 PB7（`pokeldn.lgpe.pb7`；`--offer echo` 回传主机的）；主机的 `--first echo` 回显主机的身份消息。主机的 `--next-offer` 与加入方重复的 `--offer` 排队后续交换；`--leave-after S` 让加入方离开。

```bash
./.venv/bin/python bin/lgpe_host.py --seconds 600 --player-name POKELDN \
  --first echo --our-trainer 41234:12345 --offer offer.pb7
./.venv/bin/python bin/lgpe_join.py --connect --connect-seconds 300 \
  --ack-peer-clock --ack-re-announce \
  --our-trainer 41234:12345 --offer offer.pb7
```

主机：通信 → 本地通信 → 交换 → 连接暗号皮卡丘 ×3，停在搜索画面。模拟主机：`lgpe_host.py --ip-host --our-ip IP`。见[去吧！](lgpe.md)。

## 剑／盾

主机：Y-Comm → 连接交换 → 本地通信 → 两则提示都按 A，停在搜索画面。

```bash
# 加入主机会话并交换：把主机自己的队伍快照改写后送回
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_connect.py --keys PROD_KEYS \
  --preset trade --offer-slot 1 [--offer-file your.pk8 --offer-file next.pk8 --fresh-pid] \
  --save-offered received.pk8

# 或托管，让主机加入：其快照取自本次交换
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_host.py --keys PROD_KEYS \
  --offer-file your.pk8 --fresh-pid --received received.pk8 --channel 6 --seconds 900
```

`--code 12345678` 为连接暗号搜索托管。重复 `--offer-file` 按交换排队；第 N 笔写入带后缀 `-N`。细节：[交换](swsh_trade.md)。

神秘礼物：神秘礼物 → 接收礼物 → 经本地无线。

```bash
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 \
  --move1 84 --move2 45 --move3 86 --move4 98 --nickname POKELDN --ot POKELDN --seconds 300
./.venv/bin/python bin/swsh_gift_host.py --record card.wc8 --seconds 300
```

`--set FIELD=VALUE` 设置记录字段（`shiny_type=3`、`held_item=236`），`--ribbon N` 添加奖章，`--dump FILE` 在无无线电时写出记录。无表项的道具 id 在显示背包行时会中止游戏。见[神秘礼物](swsh_gift.md)。

## 晶灿钻石／明亮珍珠

pokeldn 作为角色加入主机的联盟房间。主机：任意宝可梦中心 2F、左侧接待员、普通「是」（第一项），然后在联盟房间内远离墙壁等待。

```bash
./.venv/bin/python tools/ldn/ldn_scan.py --channels 1,6,11 --dwell 0.8
./.venv/bin/python bin/bdsp_connect.py --channels 1,6,11 --count 9 --connect 5 --join 6 \
  --hold 420 --reliable-ack --reliable-sweep 3 --room-walk 15 --room-pattern fixed \
  --room-walk-steps 0 --join-avatar 0 --answer-requests --state 0 --recruiting 0 \
  --answer-talk --can-talk 0 --initiate-talk --initiate-delay 3 \
  --after-approach 0x06:0001000000 --trade-reply --complete-trade \
  --trade-template offer.pb8 --trade-nickname POKELDN --src-var 0x2B7F4C12
```

若出现 `Connect failed with status code 1`，重试（[会话](bdsp_session.md)）。重复 `--trade-template` 排队交换，最后一份会再次送出。每次运行使用新的 `--src-var`。`--complete-trade` 允许主机存档；否则停在最后确认。角色走进后：Y → 通信菜单 → 交换宝可梦。

要托管则先启动主机；玩家同样进房，再选 Y → 通信菜单 → 交换宝可梦：

```bash
./.venv/bin/python bin/bdsp_host.py --offer offer.pb8 --complete-trade --capture host.jsonl
```

`--offer` 为存档中尚无其 PID 的合法 PB8；重复则排队。`--password 00000000` 托管密码房间。见[晶灿钻石／明亮珍珠](bdsp.md)。

## 传说 阿尔宙斯

`bin/pla_host.py` 按主机连接暗号托管；`bin/pla_join.py` 加入其搜索，可用重复 `--offer` 按交换送出，并在交接手柄时接管主机角色（[传说 阿尔宙斯](pla.md)）。

```bash
./.venv/bin/python bin/pla_host.py --code 00000000 --channel 6 --seconds 1800 \
  --session-update --sustain --clock --data-exchange --data-exchange-name POKELDN \
  --data-exchange-id 11223344 --game-channel --trade-box --trade-box-record offer.pa8 \
  --offer-out received.pa8
./.venv/bin/python bin/pla_host.py --ip-host --our-ip 172.16.86.128 --code 00000000 ...   # 模拟主机，无需无线电
```

主机：祝庆村的西蒙娜 → 交换 → 附近的人 → 同一八位数字暗号，送出一只宝可梦。

## 朱／紫、传说 Z-A

见英文原文中各启动器用法，以及 [朱／紫](sv.md)、[传说 Z-A](za.md)。桌面应用的「游戏」页覆盖同一套流程。
