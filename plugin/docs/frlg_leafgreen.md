---
title: LeafGreen
parent: FireRed and LeafGreen
nav_order: 6
---

# 叶绿

法文版叶绿（BPGF，版本 0x0A，`POKEMON LEAF`）以分段常量的 ROM 偏移运行法文版火红的代码。所有 payload 都能原样运行；ROM 地址则不行。

## 实测地址

| 符号 | 叶绿 | 火红 |
|---|---|---|
| `gDecompressionBuffer` | 0x0201C000 | 相同 |
| 神秘礼物调用点 | 0x08148C50 | 0x08148C74 |
| `Random` | 0x080486B0 | 相同 |
| `SeedRng` | 0x080486D0 | 相同 |
| `gRngValue` | 0x03004220 | 相同 |
| `gPlayerParty` | 0x02024280 | 相同 |
| `gPlayerPartyCount` | 0x02024025 | 相同 |
| `gEnemyParty` | 0x02024028 | 相同 |
| `gSpeciesInfo` | 0x0824CDD8 | 0x0824CDFC |
| `CreateMon` | 0x08041150 | 相同 |
| `sEasyChatGroups` | 0x083E353C | 0x083E3700 |
| `gSpecialVar_0x8000` | 0x020370B4 | 相同 |
| `gSpecialVars` | 0x08163984 | 0x081639A8 |
| `gSaveBlock1Ptr` | 0x03004228 | 相同 |
| `gSaveBlock2Ptr` | 0x0300422C | 相同 |

`rom_map.LEAFGREEN` 保存这些地址及其证据；`rom_map.leafgreen(symbol)` 会在表中没有该符号时抛出异常。每个 IWRAM 和 EWRAM 地址都相同；每个 0x080486C8 以上的 ROM 地址都不同。新的 ROM 符号必须实测，绝不要预测。

## 按区域划分的差值

火红到叶绿的偏移是分段常量的，而且不是单调的：

    +0x0   -0x2C   -0x28   -0x24   -0x20   -0x1C4   -0x124C   -0x1240   -0x12D8

`rom_map.leafgreen_guess(firered_address)` 在已测量段内给出答案，并拒绝空白间隙。`pokeldn/frlg/rom/leafgreen_twins.py` 保存了 738 个已测量配对（约 200 个已命名函数）；`leafgreen_twins.leafgreen(address)` 在有配对时精确回答，否则回退到猜测。

### 分叉区间

    step             span                          what is in it
    0     -> -0x2c   644 B, 0x0807CF68..0x0807D1EC  title_screen.o
    -0x2c -> -0x28    62 B, 0x080DE2E4..0x080DE322  mystery_event_script.o
    -0x28 -> -0x24    90 B, 0x081480CE..0x08148128  mystery_gift.o
    -0x24 -> -0x20    31 B, 0x08251D8E..0x08251DAD  pokemon.o rodata
    -0x20 -> -0x1c4 1209 B, 0x083B7B47..0x083B8000  title_screen.o rodata
    -0x1c4 -> -0x124c  30 KB, 0x0843AFFF..0x08442800  graphics
    -0x124c -> -0x1240 17 KB, 0x08442BFF..0x08447000  graphics
    -0x1240 -> -0x12d8 63 KB, 0x0844F3FF..0x0845F000  graphics

每个区间都是版本分叉的；其中没有单一差值适用。`rom_map.LEAFGREEN_DELTA_BOUNDARIES` 保存这些区间，并用测试对照段表检查它们。0x0843C800 以上，两块卡带保存的图形不同。`gMPlayTable` 在火红上是 0x0849758C，在叶绿上是 0x084962B4，而 `gSongTable` 在两者上都位于其上方 0x30 处。

## 配对卡带

`tools/frlg/cartridge_pair.py` 读取两块卡带上每个窗口中的字面量池和 `bl` 目标，并将它们配对（1592 个点，每个位置都已配对）。`memory-dump-scatter` 把相同的地址发送到两台主机；对两个块进行互相关可读出该差值，逐窗口测试哪个差值匹配，就能把步进定位到字节。从一台主机的转储中取一个四个字节均不同的唯一字，在另一台上扫描，就能在 ROM 中的任何位置得到一个点。

陷阱：

- 按代码偏移配对池，绝不能按索引配对：索引配对会在第一次不匹配之后捏造出差值。
- 差值 0 也可能是扫错主机时得到的答案；在步进边缘之上加一个控制点，它必须返回偏移后的结果。
- 图形数据自身相似：把每个候选差值与其他候选互相评分，如果分数接近则记录为“无结论”。

## 按火红的表读取叶绿转储

`tools/frlg/rom_functions.py --console leafgreen` 通过 twins 映射移动条目、函数体和名称，并丢弃位于分叉区间内的条目。脚本层在 0x0807AF04（`rom_map.SHARED_WITH_LEAFGREEN_THROUGH`）以下完全相同：`gScriptCmdTable` 处理程序块（0x0806D7C0..0x080700B8）、脚本引擎、`GetVarPointer`、`VarGet`、`FlagSet`、`FlagClear`、`FlagGet` 和 `_call_via_r0`。

## 野外世界与异色超梦

[搜索 stub](frlg_rng.md) 无需移植即可运行。`initramscript` 将 RAM 脚本绑定到地图对象，`GetRamScript` 会运行该脚本，而不是对象自身的 [field_control_avatar.c:458]。华蓝洞窟 B1F 是第 1 组地图 74；超梦是对象 3 [data/maps/CeruleanCave_B1F/map.json]。在那里绑定的 `rng-mon-hunt-both` 使用 `setwildbattle` 物种 150、等级 70，可开始一场定向超梦战斗（在零售版叶绿上是异色超梦）。

- 该绑定在断电重启后仍然存在。
- 一次神秘卡片会话会通过 `InitRamScript_NoObjectEvent` 重新绑定槽位，而超梦自己的脚本会返回；缓冲脚本则不会影响它。
- 在绑定期间，主机不会报告任何神秘卡片（[唯一的 RAM 脚本槽](frlg_gift.md#the-one-ram-script-slot)）。

## 被转储的区域不得变动

对帧间会变化的区域（如 `gRngValue`）执行 `memory-dump`，其 CRC 会失败并最终显示 *erreur de connexion*，因为 CRC 和发送发生在不同帧（[主机上的代码](frlg_rom.md#repointing-the-consoles-outgoing-message)）。它上面的两个存档块指针会一起按一个 4 对齐偏移在 0..124 内移动 [load_save.c:75]。

## 英文构建

`pret/pokefirered` 使用 binutils 和 `pret/agbcc` 在 REVISION 10 构建两种卡带：

    make firered_switch     -> pokefirered_switch.gba    baa452d0b24629dd7782cfc07a8984085dde1311
    make leafgreen_switch   -> pokeleafgreen_switch.gba  62b9fc77549dbc67032eb6cbd0ea6ad3b825690f

与这些 sha1 不匹配的构建无法使用；ROM 从未提交。这是英文版，是第二对卡带，其中每个符号都已知。

### 偏移：法文地址到英文地址

法文到英文的偏移是分段常量的，在对象在不同语言间大小发生变化的地方步进。`gSpecials`、`gScriptCmdTable` 和 `gMysteryEventScriptCmdTable` 条目（675 个点）以及唯一 16 字节窗口在两者都适用的每个位置都一致。

    ./.venv/bin/python tools/frlg/english_build.py --offsets

### 对照验证

通过偏移命名后，英文 ELF 与 `worker_names` 中的全部 232 个名称一致，无一不同。

    ./.venv/bin/python tools/frlg/english_build.py --check

`pokeldn/frlg/rom/english_names.py`（由 `scripts/gen_english_names.py` 生成）保存了 7573 个这样命名的法文函数地址，`rom_functions` 最后读取它们并标记为 `[english]`，因此从英文构建推断出的名称绝不会覆盖主机命名的函数体（`gen_worker_names` 传入 `with_english=False`）。位于偏移段之间的目标，当恰好有一个相邻偏移落在函数开头时，会归入 `english_names.BRACKETED`（`[english?]`）。`__divsi3`、`__modsi3` 和 `__umodsi3` 是 agbcc 的除法辅助函数。

### 英文卡带对自身的差值映射

两个英文 ROM 给出同样顺序的六个差值，每一步都落在版本分叉对象内部：

    +0x0   -0x2c   -0x28   -0x24   -0x20   -0x1c4

所有五个预测的法文步进位置都落在硬件上实测得到的区间内。

    ./.venv/bin/python tools/frlg/english_build.py --boundaries

### 陷阱

- `.gcc2_compiled.` 符号会遮蔽其文件的第一个函数；跳过以 `.` 或 `$` 开头的名称。
- 填充匹配每一个差值。窗口中必须出现 16 个不同的字节值，匹配才计入。
- 偏移（法文到英文，单块卡带）不是差值（火红到叶绿）：`french delta = offsetFR - offsetLG + english delta`。
- 任何新转储之后都要重新生成 `english_names.py`。

## 无法使用的引用

`gSongTable` 在 9 KB 内压缩存放了 122 个歌曲头，因此它只能定位一个位置。火红的 ROM 数据结束于 0x086ABE68 到 0x08800000 之间；0x08800000 读取全部为 `0xFF`，0x08E00000 读取全部为 `0x00`。
