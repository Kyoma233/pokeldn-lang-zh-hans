---
title: Mystery Gift files
---

# 神秘礼物文件

`.pokegift` 文件存储完整的 Mystery Gift 分发数据，用于 FireRed/LeafGreen 或 Sword/Shield，或 FRLG ARM 控制台载荷，包含目标游戏和本地记录。

## Desktop app

一个构建器服务于两个游戏（`pokeldn/app/gift_builder.py`；表单位于 `pokeldn/frlg/gift/builder.py`、`pokeldn/swsh/gift_builder.py`）。

| mode | what it sends |
|---|---|
| Use a preset | a built-in gift; FRLG Wonder Cards, Wonder News and console code go to the launcher as flags |
| Official events | a real Sword/Shield event card ([Official event cards](swsh_gift.md#official-event-cards)), compiled like a built gift |
| Build your own | the form, compiled to `session/gifts/<tool>.pokegift` at Start and passed as `--gift-file` |
| Open a file | a shared `.pokegift`, or a `.wc8` on Sword/Shield |

FRLG 游戏增强功能为常驻钩子（[`install-resident`](frlg_rom.md#install-resident)），作为一个链运行（[Several hooks at once](frlg_rom.md#several-hooks-at-once)）在 1024 字节内；设置变为 `--resident-param` 标志。

| boost | settings | parameters |
|---|---|---|
| Speed up the game (`turbo-lite`) | speed x1 to x4; overworld, battles or both; always on or while R, B or Select is held; faster text | `field` and `battle` = speed - 1, `budget=228` from x3, `hold`, `extra=4` |
| Walk through walls | R, B or Select | `hold` |
| Shiny countdown | the slow-down button; x2, x4 or x8 slower | `slow`, `slow_frames` 1, 3 or 7 |
| Shiny legendary (`shiny-press`) | Mewtwo; Articuno, Zapdos or Moltres | `offset` 1 or 2 |
| No wild encounters, Lead's IVs on screen, Pokemon follower | none | |

L 键不提供：只有 R 的帮助系统切换才有一个钩子持有的标志。保存增强功能将设置写入 `filler_B20`（`save-write --resident`）并安装；超过 876 字节的集合和跟随者总是通过存档。妈妈恢复你的增强功能使得与妈妈对话在任何启动后安装保存的集合。再次发送增强功能替换正在运行的集合。

读取存档提供 Trainer ID（TID）和 Secret ID（SID）、训练师详情和游玩时间，以及最后保存的队伍的性格、IV 和 EV，同时保持存档完整（[Reading the save](frlg_rom.md#reading-the-save)）。

`.wc3` 和 `.wc8` 文件即使以 `{` 开头也作为二进制读取。自定义副本将预设复制到表单中，当表单可以表达时：所有 Sword/Shield 预设，以及仅由无条件表单步骤组成的 FRLG 卡片。

FRLG 表单构建 Wonder Card、Wonder News 或控制台代码。

| part | contents |
|---|---|
| card | title, subtitle, four text lines, icon species, card id 1000 to 1019, received again, shareable |
| who hands it over | the delivery man in any Pokemon Center, Mom in the player's house, or the man in south Pallet Town |
| steps | Pokemon (species, level, held item, four moves), item and quantity, egg, wild battle, message |
| news | title, up to ten lines, news id |
| console code | ARM source or a prebuilt `.bin`, the cartridge it is built for, expected answer, bytes sent back |

每个步骤都是自己的交付阶段：完整的队伍或背包在此停止，重试会获得剩余部分。另一个人通过 `initramscript` 绑定保持步骤，这隐藏卡片并每次给出步骤直到被替换。Species 使用内部编号（`pokeldn/frlg/save/species_names.py`）。

控制台代码需要 `arm-none-eabi-as`（PATH、Homebrew 或 Arm 的 Windows 文件夹），或预构建的 `.bin`：

| system | command |
|---|---|
| macOS | `brew install arm-none-eabi-binutils` |
| Fedora | `sudo dnf install arm-none-eabi-binutils-cs` |
| Debian, Ubuntu and derivatives | `sudo apt install binutils-arm-none-eabi` |
| Windows | `winget install Arm.ArmGnuToolchain` |

检查离线运行在模拟控制台上运行代码（`pokeldn/frlg/rom/custom_code.py`），如 Start 和 save 所做的，拒绝故障或从不返回 1 的代码。

Sword/Shield 表单构建 Pokemon（Gigantamax 可选）、蛋、最多六种物品、服装（[Clothing](swsh_gift.md#clothing)、每性别六件）、Battle Points 或金钱，布局为 [record a retail Sword redeemed](swsh_gift.md#a-card-delivered-to-a-retail-console)。

保存礼物文件写入包含所有卡带变体的 `.pokegift`，不需要板或密钥。控制台的游戏代码选择变体；文件中缺少的卡带在发送前被拒绝。

## Command line

两个礼物启动器都接受 `--gift-file FILE`；在 Sword/Shield 上 `--record` 是别名。`--export-gift FILE` 保存选定的礼物并在使用广播之前退出。

```bash
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --export-gift celebi.pokegift
./.venv/bin/python bin/frlg_mg_host.py --news berry --export-gift news.pokegift
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 --export-gift pikachu.pokegift
./.venv/bin/python -m pokeldn.gifts inspect celebi.pokegift
```

FRLG 礼物文件定义卡标志 ID、脚本、问卷和拒绝消息一起。Payload 覆盖如 `--flag-id`、`--questionnaire` 和 `--hunt-*` 与其一起被拒绝；广播、训练师和卡带选择选项仍然适用。

### Console code

内置载荷导出其响应设置：

```bash
./.venv/bin/python bin/frlg_mg_host.py --buffer-script save-dump --dump-size 64 \
  --export-gift save-dump.pokegift
```

原始 ARM 代码与显式卡带目标一起打包：

```bash
arm-none-eabi-as -march=armv4t -mcpu=arm7tdmi -o payload.o payload.s
arm-none-eabi-objcopy -O binary -j .text payload.o payload.bin
./.venv/bin/python -m pokeldn.gifts import --game frlg --code payload.bin \
  --build BPRF --name "Custom payload" --expect 66 -o custom.pokegift
```

最小的 `payload.s` 写入 66 到响应参数并在一次调用中完成：

```asm
.syntax unified
.arm
.text
.global _start
_start:
    mov r3, #66
    str r3, [r0]
    mov r0, #1
    bx lr
```

代码是位置无关的 ARMv4T，字对齐，最多 1024 字节，每次调用一次，参数为 `r0 = &param`, `r1 = gSaveBlock2Ptr`, `r2 = gSaveBlock1Ptr`，直到返回 1（[Console code](frlg_rom.md)）。没有 `--expect` 接受任何答案；字节缓冲响应需要 `--dump-size N`。

接收者在 FRLG Mystery Gift 工具中打开文件或传递 `--gift-file`；`--dump-file PATH` 选择返回转储的位置。打包仅检查结构和大小：在实时运行前用 `buffer_script.emulate_repeating` 运行新载荷。

### Native formats

转换器导入 WC8、FRLG `.wc3` 和 `pokemon-gen3-mysterygift-tool` 的卡/脚本对；`.wc3` 和 `.wc8` 也可以直接打开。

FRLG 脚本没有绝对地址（仅 `vgoto`/`vmessage` 相对于 `setvaddress` [scrcmd.c:171]，物品通过 `callstd`）服务于其布局的所有卡带。一个有 `goto`、`call`、`message`、`callnative` 或其他绝对指针的脚本需要 `--build`，直接打开时被拒绝。

```bash
./.venv/bin/python -m pokeldn.gifts import --game swsh --record event.wc8 -o event.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --wc3 "FL - Item AuroraTicket (FRE).wc3" -o aurora.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --card WonderCard.bin \
  --script Script.bin --name "Event gift" -o event.pokegift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --build BPRF --out-dir native-gift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --wc3 --build BPRJ --out-dir native-gift
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --console-build BPRJ --export-gift celebi.wc3
```

保存到 `.wc3` 或 `.wc8` 路径写入本地文件。`.wc3` 保存一个卡带；不同变体需要 `--build`。其元数据除了图标外均为零，图标重复卡片的。每个接受的国际画廊文件都以相同卡片、脚本和图标字节往返。

国际 `.wc3` 是 1420 字节（`0x58C`）：

| offset | size | content |
| --- | --- | --- |
| `0x000` | 336 | CRC16 of the card, 2 pad bytes, the 332-byte `struct WonderCard` |
| `0x150` | 80 | save-side card metadata; not read |
| `0x1A0` | 1004 | CRC16, 2 pad bytes, `struct RamScriptData` (magic 51, map group, map number, object id, 995-byte script), 1 pad byte |

画廊文件的脚本 CRC 覆盖 1000 字节；游戏的覆盖 999 [script.c:488]；导入接受任一。`--icon N`（应用中的 Card icon）设置 `iconSpecies`（卡片偏移 2），0 到 411；0 不绘制 [mystery_gift_show_card.c:466]。

日文 `.wc3` 文件是 1252 字节（`0x4E4`）：卡结构是 164 字节，其 CRC 包装是 168 字节，元数据从 `0x0A8` 开始，1004 字节的 RAM 脚本结构从 `0x0F8` 开始。日文文件服务于 `BPRJ` 和 `BPGJ`，国际文件服务于十种拉丁卡带。1000 到 1019 之外的标志 ID 被拒绝 [mystery_gift.c:241]。

本地对（卡加 1004 字节脚本）不能携带邮票、拜访训练师、Mystery Event 脚本、问卷门或 Wonder News；导出拒绝它们。导入检查两个 CRC。

## Version 2

文件是 UTF-8 JSON，具有五个必需字段：

| Field | Value |
| --- | --- |
| `format` | `pokeldn.gift` |
| `version` | integer `2` |
| `game` | `frlg` or `swsh` |
| `name` | non-empty display name, up to 180 characters |
| `variants` | object mapping target codes to native data and options |

每个变体有 `data` 和 `options` 对象。`data` 中的组件有 `hex`，即本地字节编码为十六进制，和 `sha256`，即其小写 SHA-256 摘要。导出排序字段。

| Game | Variant keys | Data components | Options |
| --- | --- | --- | --- |
| FRLG gifts | supported cartridge codes | `card`, `ram_script`, `stamp`, `activation_script`, `install_activation_script`, `trainer`, `news`, `mevent` | `questionnaire`, `denied_message` |
| FRLG console code | supported cartridge codes | `buffer_code`, `buffer_lead_1`.. | response settings below |
| Sword/Shield | `swsh` | `wc8` | none |

FRLG 卡变体共享标志 ID 和礼物类型；新闻和控制台代码单独旅行。控制台代码变体有一个 `buffer_code` 和最多八个 `buffer_lead_N` 在其之前运行，编号无间隙。响应设置：`buffer_expect`（u32 或 `trainer-id`）、`buffer_dump_size`（1 到 1024）、`buffer_dump_blocks`（最多 32）、`buffer_dump_address`、`buffer_dump_addresses`（每个块一个）、`buffer_decode`。

读取器接受版本 1 文件（卡、新闻、WC8）；导出为版本 2，增加控制台代码。版本 1 读取器拒绝版本 2 文件。

读取器拒绝未知版本、字段和代码、重复字段、错误哈希、超过 256 KiB 的文件、错误的本地大小和错误的组合；FRLG 还检查卡字段、训练师校验和和 Mystery Event 终止。哈希仅检测损坏；它们不认证任何人。

## Implementation

`pokeldn.gifts` 拥有信封、验证调度、读取器、写入器和转换器。游戏特定编解码器位于 `pokeldn.frlg.gift.file` 和 `pokeldn.swsh.gift_file`。FRLG 适配器构建 `MysteryGiftDistribution`，包含其卡带选择和拒绝路径；Sword/Shield 适配器提供 WC8 广告构建器。
