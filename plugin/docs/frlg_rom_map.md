---
title: The ROM map
parent: FireRed and LeafGreen
nav_order: 4
---

保留 YAML frontmatter 原样（若有，本段并无）。

---

# ROM 映射

本页描绘火红/叶绿卡带 ROM：镜像、函数表、脚本读取器、宝可梦种类表、法语 Easy Chat 词库以及十二个国际版本。除表格另有说明外，地址均为法语火红（BPRF，版本 0x0A）；叶绿的地址见
[LeafGreen](frlg_leafgreen.md)。`pokeldn/frlg/rom/rom_map.py` 记录每个地址的取得方式，
`tests/test_rom_map.py` 用实机转储结果对其进行校验。

## 卡带镜像

Switch 发行版把 GBA ROM 作为其 RomFS 中的唯一文件携带。

| title id | RomFS 文件 | 大小 | sha1 |
|---|---|---|---|
| 01004B3023412000 | `/FireRed_f.gba` | 16777216 | `07566b82dbd2a91321698f730f6400ae4c56ddf1` |
| 010087C02342E000 | `/LeafGreen_f.gba` | 16777216 | `9f774956dfbad7f69ddb91fb91d2c26e54408f75` |
| 0100554023408000 | `/FireRed_e.gba` | 16777216 | `baa452d0b24629dd7782cfc07a8984085dde1311` |
| 010034D02340E000 | `/LeafGreen_e.gba` | 16777216 | `62b9fc77549dbc67032eb6cbd0ea6ad3b825690f` |

0xA0 处的文件头读作 `POKEMON FIRE` `BPRF` 与 `POKEMON LEAF` `BPGF`，版本 0x0A，校验和有效。法语火红 1.0.1 更新除包装层的三处载入期补丁外，不改动客户 ROM
（[frlg_rom.md](frlg_rom.md)，断点钩子一节）；`0x09000000..0x0A000000` 读作开放总线（每个半字地址折半为其自身）。英文版（`BPRE`、`BPGE`）与
`pret/pokefirered` 的 `pokefirered_switch.gba` 和 `pokeleafgreen_switch.gba` 逐字节相同。

`scratchpad/base_romfs.py` 读取 Program NCA 的单个 CTR RomFS 节：

    ./.venv/bin/python scratchpad/base_romfs.py "$NSP" --list
    ./.venv/bin/python scratchpad/base_romfs.py "$NSP" --extract /FireRed_f.gba --out scratchpad/FireRed_f.gba

## EWRAM 在两个版本中位于相同地址

英文 ELF 的 EWRAM 符号即法语卡带的符号（`gDecompressionBuffer` 0x0201C000、
`gPlayerParty` 0x02024280、`gPlayerPartyCount` 0x02024025）。IWRAM 不同。没有符号占用
0x0203FBAC（符号最高结束地址）到 0x02040000（`scratchpad/ram_survey.py`）。

## 英文卡带

`pokeldn/frlg/rom/builds.py` 为每张卡带维护一张表（`BPRF`、`BPGF`、`BPRE`、`BPGE`、`BPRS`、
`BPGS`、`BPRD`、`BPGD`、`BPRI`、`BPGI`、`BPRJ`、`BPGJ`）：IWRAM 全局变量、ROM 函数载荷、
钩子、桩与 `call-chain` 用法，以及礼物携带的数据指针。主机在发送任何依赖地址的内容之前，
从 `MysteryGiftLinkGameData` [mystery_gift.c:369] 中的游戏代码选择一张表；没有对应表的主机，
或被 `--console-build CODE` 或 `--version` 排除的主机，会被拒绝且不发送任何内容。

英文地址来自 ELF，且均与零售镜像核验一致。

| 区域 | 法文到英文 |
|---|---|
| EWRAM | 不变 |
| IWRAM 0x03000000..0x03001B6F | 不变 |
| IWRAM 0x03002370..0x0300602F 英文段，从 `gMain` 起（法文 0x030022D0，英文 0x03002380） | +0xB0 |
| IWRAM 0x03006090..0x03007583 英文段，`gSoundInfo`（法文 0x03005F80）至 `gFlash` | +0x110 |
| IWRAM 0x03007590 及以上：栈、中断向量 | 不变 |
| ROM | 无单一偏移；每个函数单独查找 |

英文值：`gRngValue` 0x030042D0、`gSaveBlock1Ptr` 0x030042D8、`gSaveBlock2Ptr` 0x030042DC、
`gIntrTable[4]` 0x030027E0、`gLastWrittenSector` 0x03004650、`gSaveCounter` 0x03004660。英文
叶绿的 RAM 与英文火红相同；常驻钩子的地址中只有 `m4aSoundMain` 发生移动
（0x081E07C4 对 0x081E07E8）。`tests/test_frlg_english_cartridges.py` 通过每个镜像的
`Client_RunBufferScript` 运行载荷（缺少 `scratchpad/frlg_en/` 时跳过）。

## BIOS 包装器

`libagbsyscall.s` 按反编译的顺序链接为 THUMB `svc N ; bx lr` 对，叶绿上低 0x24：

| wrapper | svc | 火红 | 叶绿 |
|---|---|---|---|
| `ArcTan2` | 0x0A | 0x081E21D4 | 0x081E21B0 |
| `BgAffineSet` | 0x0E | 0x081E21D8 | 0x081E21B4 |
| `CpuFastSet` | 0x0C | 0x081E21DC | 0x081E21B8 |
| `CpuSet` | 0x0B | 0x081E21E0 | 0x081E21BC |
| `Div` | 0x06 | 0x081E21E4 | 0x081E21C0 |
| `LZ77UnCompVram` | 0x12 | 0x081E21E8 | 0x081E21C4 |
| `LZ77UnCompWram` | 0x11 | 0x081E21EC | 0x081E21C8 |

游戏的 LZ77 流是 VRAM 安全的，并与 `gbagfx` 输出一致。LZ77 不会缩小载荷代码；它仅对超过
1024 字节的数据有帮助。

## 第一个锚点

`anchors` 返回 `0x08148C75`，即 `Client_RunBufferScript`
[mystery_gift_client.c:274] 中的返回地址。其字面量池：

    0x08148C88 -> 0x0201C000   gDecompressionBuffer
    0x08148C8C -> 0x0300422C   &gSaveBlock2Ptr
    0x08148C90 -> 0x03004228   &gSaveBlock1Ptr

0x08148C94 处的 `MysteryGiftClient_CallFunc` 按 `client->funcId` 索引 `sClientFuncs`（0x0845DBD0，八项）。其他每个地址都从字面量池、`bl` 目标与指针表到达，且都落在已知的函数序言上（`scratchpad/rom_read.py`）。

## 四个函数表

    gScriptCmdTable              0x08163650   214 项   野外脚本命令
    gSpecialVars                 0x081639A8    21 项
    gSpecials                    0x081639FC   444 项   gSpecialsEnd 0x081640EC
    gStdScripts                  0x081640EC    10 项
    gMysteryEventScriptCmdTable  0x081DE144    17 项

`script_data` 从 0x08163650 延伸到 0x081DE188，即 `lib_text`（`libgcnmultiboot`）的起始处
[ld_script_rev10.ld:318-330]。

- `gSpecialVars`：十二个字，每个比上一个大 2（`gSpecialVar_0x8000` = 0x020370B4，是一个
  `EWRAM_DATA` 全局变量）[event_data.c:16]。
- `gScriptCmdTable`：214 个 THUMB 指针；第 0 和第 213 项都是 `ScrCmd_nop`。
  `pokeldn/frlg/rom/scrcmd_names.py` 为每一项命名（`scrcmd_names.handler("additem")`）。

      0x23 callnative   0x0806D854      0x44 additem      0x0806DED0
      0x25 special      0x0806D7EC      0x79 givemon      0x0806F834
      0x29 setflag      0x0806E0EC      0x90 addmoney     0x0806F998

- `gSpecials`：来自 `ScrCmd_special` 字面量池 [scrcmd.c:101] 的 444 项，经由
  0x081E2224 调用；其中 171 项是 `NullFieldSpecial`。`rom_map.SPECIAL_ADDRESSES` 保存它们，
  `rom_map.special_function("HealPlayerParty")` 解析其中一项。
- `gStdScripts`：指向 0x081A76xx..0x081AB5xx 的十个字。
- `gMysteryEventScriptCmdTable`：通过 `sMysteryEventScriptContext`（0x0203AA38）找到，其表对位于 +0x5C/+0x60 [mystery_event_script.c:27,52]
  （同一次启动中收到神秘事件礼物后，对 EWRAM 使用 `table-scan --table-delta 0x44 --table-runlen 2`）。

| # | 命令 | 处理函数 | | # | 命令 | 处理函数 |
|---|---|---|---|---|---|---|
| 0 | `nop` | 0x080DE451 | | 9 | `givenationaldex` | 0x080DE61D |
| 1 | `checkcompat` | 0x080DE401 | | 10 | `addrareword` | 0x080DE641 |
| 2 | `end` | 0x080DE3F5 | | 11 | `setrecordmixinggift` | 0x080DE66D |
| 3 | `setmsg` | 0x080DE465 | | 12 | `givepokemon` | 0x080DE681 |
| 4 | `setstatus` | 0x080DE455 | | 13 | `addtrainer` | 0x080DE78D |
| 5 | `runscript` | 0x080DE49D | | 14 | `enableresetrtc` | 0x080DE7D5 |
| 6 | `initramscript` | 0x080DE5B5 | | 15 | `checksum` | 0x080DE7E9 |
| 7 | `setenigmaberry` | 0x080DE4B9 | | 16 | `crc` | 0x080DE831 |
| 8 | `giveribbon` | 0x080DE581 | | | | |

## 从表项到其背后的函数

处理函数的 `bl` 目标按地址顺序排列，对应反编译中按源码顺序排列的调用
[scrcmd.c:463-590]：

    ScriptReadHalfword   0x0806D1E8      AddBagItem           0x0809DA70
    VarGet               0x08071DDC      RemoveBagItem        0x0809DBC4
    GetVarPointer        0x08071CC8      CheckBagHasSpace     0x0809D9EC
    FlagSet              0x08071EF4      CheckBagHasItem      0x0809D92C
    FlagClear            0x08071F1C      AddPCItem            0x0809DDB4
    FlagGet              0x08071F44      IncrementGameStat    0x080587A4

`gSpecialVar_Result` 为 0x020370CC；`Random` 为 0x080486B0。`scratchpad/handler_workers.py` 打印处理函数的 `bl` 目标；`tools/frlg/rom_functions.py --table specials|field|mystery-event|callable`
对整张表执行此操作，并规划下一批 `--dump-address` 窗口。

ROM 由 agbcc 构建，并以 `pop {r4,r5,r6}; pop {r1}; bx r1`（BC70 BC02 4708）结束 THUMB 函数，从不使用 `pop {..., pc}`。`pokeldn/frlg/rom/thumb.py` 匹配 `bx Rn`，仅当其后跟有函数序言时才把一次返回视为块的结束。

### 离线命名 300 个工人

`scripts/gen_worker_names.py` 把每个已转储函数体与反编译结果比对，并写入
`pokeldn/frlg/rom/worker_names.py`，经过四项校验：

| 校验 | 排除的情况 |
|---|---|
| 长度 | 内联、`__umodsi3`、被当作调用的宏读取 |
| 锚点 | 未对齐的函数体：每个已测地址必须回落到自身名称上 |
| 一致性 | 被两个调用者以不同名称命名的目标 |
| 链接顺序 | 名称在 ROM 中位置错误（保留最长的升序链） |

锚点之间若夹着一个未命名目标和一个源码调用，则强制认定为目标。阅读源码可知：

- `firered_switch` 是 `GAME_REVISION=10 MODERN=0` [Makefile:227]：`#if REVISION >= 0xA` 代码块生效。
- `VarGet(ScriptReadHalfword(ctx))` 是 `bl ScriptReadHalfword` 后接 `bl VarGet`。
- `ScriptReadByte` 是宏，不产生 `bl` [include/script.h:24]。
- `NDEBUG` 生效：没有 assert 调用。

| `rom_map` 名称 | 反编译中的名称 | 函数体一致数 |
|---|---|---|
| `GET_MON_DATA` | `GetMonData3` | 15 |
| `SCRIPT_CONTEXT_SET_NATIVE` | `SetupNativeScript` | 11 |
| `SET_RESPAWN` | `SetLastHealLocationWarp` | 1 |
| `SCRIPT_MOVEMENT_START` | `ScriptMovement_StartObjectMovementScript` | 2 |
| `CHANGE_AMOUNT_MONEY_BOX` | `ChangeAmountInMoneyBox` | 2 |
| `ME_CHECK_COMPATIBILITY` / `ME_SET_INCOMPATIBLE` | `CheckCompatibility` / `SetIncompatible` | 1 / 3 |

`GetMonData2` 别名 `GetMonData3` [pokemon.c:2970]。`0x0806D0EC` 是 `StopScript(ctx)` [script.c:76]；`ScriptContext_Stop(void)` [:360] 是 0x0806D418。

### 两个混合镜像隐患

- 切勿把两张卡带的转储当作单一镜像读取：叶绿中这段代码偏移 −0x2C，混合镜像会误标调用。`script_read.every_dump` 只接收一张卡带。
- 一次性读取每个转储：`scrcmd.Memory` 合并重叠转储
  （`tools/frlg/script_read.py --with-every-dump`）。

### 测量了什么

每张表背后的每个函数体都被读取：213 条野外命令、17 个神秘事件操作码、27 个可调用函数、272 个 special。`NullFieldSpecial` 是 0x080CE8DC 处的 `bx lr`；`GetLeadMonIndex` 是
0x080CE818；`DoDiveWarp` 0x08081CC8，`DoFallWarp` 0x08081DA0。

神秘事件 VM 的工人：

| 工人 | 地址 | 被谁调用 |
|---|---|---|
| `StringExpandPlaceholders` | 0x0800CADC | 每个留下消息的处理函数的最后一次调用 |
| `RunScriptImmediately` | 0x0806D438 | `runscript` |
| `InitRamScript` | 0x0806D5F0 | `initramscript` |
| `GiveGiftRibbonToParty` | 0x080A43B0 | `giveribbon` |
| `EnableRareWord` | 0x080C1658 | `addrareword` |
| `CheckCompatibility` | 0x080DE300 | `checkcompat` |
| `SetIncompatible` | 0x080DE330 | `checkcompat` 的 else 分支 |
| `memcpy` | 0x081E44F4 | `addtrainer` |
| `CalcCRC16` | 0x080489A0 | `crc` |
| `StringCopyN` | 0x0800C8CC | `setenigmaberry`、`givepokemon` |
| `StringCompare`、`SetEnigmaBerry` | 0x0800C938、0x080A01B0 | `setenigmaberry` |
| `VarSet` | 0x08071DF8 | `setenigmaberry`；无 ScrCmd 调用它 |
| `SpeciesToNationalPokedexNum` | 0x08046994 | `givepokemon` |
| `GetSetPokedexFlag` | 0x0808C860 | `givepokemon` |
| `ItemIsMail`、`GiveMailToMon2`、`CompactPartySlots` | 0x0809BB18、0x0809B964、0x080971FC | `givepokemon` |

调用跳板每处四字节，从 0x081E2224 的 `_call_via_r0` 起（r4 0x081E2234，r6 0x081E223C）。

## 保存备份与恢复

`LoadGameSave` [save.c:803] 和 `gRfu.sendQueue.count` [link_rfu_2.c:3131] 存在于每个卡带中。
`LoadGameSave` 打开 `70 b5 00 06` 并读取 `gDecompressionBuffer`；队列计数由叶子代码 `ldr r0, =gRfu; ldr r1, =0x8D2; adds r0, r0, r1; ldrb r0, [r0]; bx lr` 读取。

| 卡带 | `LoadGameSave` | `gRfu` | `gRfu.sendQueue.count` |
|---|---|---|---|
| `BPRE` | `0x080DDBF4` | `0x03005590` | `0x03005E62` |
| `BPGE` | `0x080DDBC8` | `0x03005590` | `0x03005E62` |
| `BPRF` | `0x080DDFD4` | `0x030054E0` | `0x03005DB2` |
| `BPGF` | `0x080DDFA8` | `0x030054E0` | `0x03005DB2` |
| `BPRD`、`BPRI` | `0x080DDF14` | `0x030054E0` | `0x03005DB2` |
| `BPGD`、`BPGI` | `0x080DDEE8` | `0x030054E0` | `0x03005DB2` |
| `BPRS` | `0x080DDFFC` | `0x030054E0` | `0x03005DB2` |
| `BPGS` | `0x080DDFD0` | `0x030054E0` | `0x03005DB2` |
| `BPRJ` | `0x080DED68` | `0x03005520` | `0x03005DF2` |
| `BPGJ` | `0x080DED3C` | `0x03005520` | `0x03005DF2` |

`sSaveSlotLayout` 在全部十二个卡带上一致，除了扇区 ID 4：拉丁语系卡带为 3816 字节，日语卡带为 3776 字节。

# 读取控制台脚本

`scripts/gen_scrcmd_args.py` 根据反编译工程中的宏生成操作数宽度，输出到
`pokeldn/frlg/rom/scrcmd_args.py`；`memory-dump` 与 `scrcmd.disassemble` 随后可读取任意脚本：

    0x081A7624  6A  lock
    0x081A7625  5A  faceplayer
    0x081A7626  67  message 0x00000000
    0x081A762B  66  waitmessage
    0x081A762C  6D  waitbuttonpress
    0x081A762D  6C  release
    0x081A762E  03  return

这是 `Std_MsgboxNPC`。从每个 `gStdScripts` 条目出发的遍历会在下一条目的前一字节处遇到终止符。

## 条件宏

| 命令 | 宽度 | 结构 |
|---|---|---|
| `applymovement` | 7 字节 | `.ifb \map` 分支 |
| `waitmovement`、`removeobject`、`addobject` | 3 字节 | `.ifb \map` 分支 |
| `applymovementat`、`waitmovementat`、`removeobjectat`、`addobjectat` | 9、5、5、5 字节 | 备用分支 |
| `warp` 及其他八个传送命令 | 8 字节 | `formatwarp` 子宏 |
| 十个 `buffer*` 命令 | 4 字节 | `stringvar` 子宏 |
| `showobjectat`、`hideobjectat`、`resetobjectsubpriority` | 5 字节 | `map` 子宏 |
| `trainerbattle` | 6 + 4..16 字节 | 依类型而定的分支 |

仅当每条路径都以自身的操作码字节开始，并且不会到达其他命令宏时，宏才是命令宏（`giveitem` 是两条指令）。`trainerbattle` 是 `scrcmd_args.VARIABLE`；未知类型会让 `scrcmd.shape` 返回 `None`。`goto` 与 `end` 和 `return` 一样是终止符。266 字节的训练家对战区域 0x081A7699..0x081A77A3 是 `tests/test_script_cmd_table.py` 中的固定测试数据。

## 命名操作数

`tools/frlg/script_read.py DUMP.bin --base ADDR`：

    0x081A76A8  4F  applymovement 0x800F (VAR_LAST_TALKED), 0x081A77B0
    0x081A76B2  26  specialvar 0x800D (VAR_RESULT), 0x0036 (Script_HasTrainerBeenFought)
    0x081A76BC  06  goto_if 0x05 (!=), 0x081A76CD
    0x081A76C2  25  special 0x0038 (PlayTrainerEncounterMusic)

- 任何命令中，0x4000 或以上的操作数都是变量引用 [event_data.c:214,235]。
  `pokeldn/frlg/rom/symbol_names.py` 包含 274 个变量名和 1470 个标志名。
- `scrcmd_args.PARAMS` 为每个操作数命名，并据此选择表（`special` u16 进入 `gSpecials`，
  `callstd` u8 进入 `gStdScripts`）。
- 条件为 <、=、>、<=、>=、!= [scrcmd.c:65]。

## 追踪脚本到达之处

`scrcmd.follow` 追踪每个 `goto`、`call`、`goto_if` 和 `call_if`，并收集未持有的地址；数据指针只报告，不追踪。`scrcmd.dump_plan` 将未命中项转换为 `--dump-address` 行。`charmap.decode` 用于名称，`charmap.decode_message` 用于对话。运行超出转储末尾的命令会被报告为短转储。

# 物种表

`gSpeciesInfo` = 0x0824CDFC，步长 28（反编译工程的 26 字节加两个 `00 00` 填充字节）。其数据与英文反编译工程一致。解析反编译工程时的陷阱：一行的 `[SPECIES_NONE] = {0},`、`PERCENT_FEMALE(x)`、`noFlip` 位域，以及十六进制 `#define` 定义。

## 从中查找 `CreateMon`

`pokemon.o` 中第一个 `&gSpeciesInfo` 常量池属于 `CreateMon` [pokemon.c:1755]：

| 符号 | 地址 | 方式 |
|---|---|---|
| `CreateMon` | `0x08041150` | 反汇编（`f0b5 4746 80b4 87b0`） |
| `ZeroMonData` | `0x08041090` | 其第一次调用 |
| `CreateBoxMon` | `0x080411C0` | 其在 ZeroMonData 和 SetMonData 之间的调用 |
| `SetMonData` | `0x08043A78` | 以 56（`MON_DATA_LEVEL`）调用，随后以 255 调用 64（`MON_DATA_MAIL`） |
| `CalculateMonStats` | `0x08041B78` | 其最后一次调用 |

## 西班牙语火红卡带

西班牙语火红基础版 v0（`0100EB702342C000`）包含 `FireRed_s.gba`，游戏代码 `BPRS`，修订版本 0x0A。`builds.BPRS` 和 `vendor/gblink-cards/symbols.json`（语言 ID 7）保存其地址。

| 符号 | 西班牙语火红 |
|---|---|
| `gRngValue`、`gSaveBlock1Ptr`、`gSaveBlock2Ptr` | 0x03004220、0x03004228、0x0300422C |
| `gMain`、`gIntrTable[4]`、`gSoundInfo` | 0x030022D0、0x03002730、0x03005F80 |
| `VBlankIntr`、`Client_RunBufferScript` | 0x0800071C、0x08148CD0 |
| `CreateMon`、`GetMonData3`、`Random` | 0x08041164、0x080432F8、0x080486C4 |
| `CB1_Overworld`、`CB2_Overworld`、`RunTextPrinters` | 0x08059E5C、0x08059EDC、0x08002D50 |
| `m4aSoundMain`、`ReadFlash` | 0x081E089C、0x081E224C |
| `MapGridGetElevationAt`、`MapGridGetCollisionAt` | 0x0805C658、0x0805C6D8 |
| 居合斩、碎岩、怪力消息返回指针 | 0x081C1909、0x081C19FD、0x081C1AE6 |
| `GetMoney`、`SpeciesToNationalPokedexNum`（表） | 0x080A376C、0x080469A8（0x0824B9DE） |

徽章检查指向位于 0x081C1901、0x081C19F5 和 0x081C1ADE 的消息脚本；`EventScript_CurrentTooFast` 从 `0x081AA346`（`lockall`）开始。翻译后的文本会移动每个恢复脚本。`tests/test_frlg_english_cartridges.py`、`tests/test_noclip.py` 和 `tests/test_follower.py` 在存在 `scratchpad/frlg_es/FireRed_s.gba` 时使用它。

# 法语易聊词汇

所有 1006 个依赖语言的易聊词汇都从控制台的 ROM 中读取到 `pokeldn/frlg/text/easychat_french_words.py`；`easychat_french.french(id)` 从中返回答案。

## 槽位问题

易聊 ID 为 `(group << 9) | index`。`pokeldn/frlg/text/easychat_words.py` 为英文 ROM 中每个槽位的内容命名；法语 ROM 保存的是其他词汇（`EC_WORD_ENJOY` 渲染为 STRESSE，`EC_WORD_DONE` 为 FURAX，`SPEECH/12` 为 LES）。邮件、训练家卡片签名、来访训练家、`--denied-message` 和问卷闸门都依赖法语表。

## 查找表

`sEasyChatGroups[]` 是 22 个条目，类型为 `{ const void *wordData; u16 numWords; u16 numEnabledWords; }` [src/data/easy_chat/easy_chat_groups.h:26]，位于 0x083E3700。其计数与英文构建相同，因此同一 ID 在两种语言中对应同一个槽位。单词数组和文本跨 0x083DE2C8..0x083E3700。`tests/test_easychat_french.py` 要求渲染结果与 ROM 证据一致。`TRAINER/11` 是 DRESSEUR；DRESSEURS 不在表中。

## 表的内容

- `EC_GROUP_STATUS`（109 个特性）几乎是直译（`stench` PUANTEUR、`thick_fat` ISOGRAISSE、`air_lock` AIR LOCK）。
- `EC_GROUP_FEELINGS` 被重新分箱：槽位 13（`disappoints`）是 RAVI，44（`eat`）是 HUMILIE，51（`drink`）是 HONTEUX。
- `EC_GROUP_SPEECH`：LES 和 L' 占用了英文用于 `case` 和 `miss` 的槽位。

807 个槽位（`EC_GROUP_POKEMON`、`POKEMON_2`、`MOVE_1`、`MOVE_2`）从 `gSpeciesNames` / `gMoveNames` [easy_chat.c:155] 输出，由控制台本地化；`easychat.species_word(55)`、`easychat.move_word(177)` 和 `easychat.is_language_safe` 处理它们。

## 使用它

```python
from pokeldn.frlg.text import easychat, easychat_french
easychat_french.french(easychat.WORDS["enjoy"])     # 'STRESSE'
easychat_french.render(ids)                          # the line as the console will print it
easychat_french.check(ids, strict=True)              # raises on anything unread or out of range
```

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script string-gather --gather-address 0x083DF5C0 --gather-count 42 \
        --gather-stride 12 --dump-file DUMP.bin --version firered    # one group per run
    ./.venv/bin/python scratchpad/ec_words.py --group 4 DUMP.bin

叶绿的易聊区域位于火红对应区域 −0x1C4 处，词汇相同。

## 0x0A 国际版卡带

主程序为两个版本都准备了英语、法语、德语、意大利语、西班牙语和日语的地址表。函数通过独特的指令窗口与英文 ELF 配对，相对调用和指针字面量被屏蔽；RAM 全局变量来自字面量池；野外招式脚本按命令序列配对。`SpeciesToNationalPokedexNum` 通过与其共享指令序列的相邻项配对。

| 卡带 | ROM 文件 | SHA-256 |
|---|---|---|
| `BPRD` | `FireRed_d.gba` | `04f43a43f7cf9109561cd1744d108f50202c931ce31b30abaa6f18950824d20d` |
| `BPRE` | `FireRed_e.gba` | `d32c8df8702293716ad8de68755fe5903161f4829a0a2e486bfa7e74a0b62e94` |
| `BPRF` | `FireRed_f.gba` | `9edf7a3137536b0ccf024a732025da9a0ea1330eb9fd13b2ffed19f5e008c147` |
| `BPRI` | `FireRed_i.gba` | `cf7fa25cf57fbf12f24709efdd1d1aa8056efb4e9b6520ac7d068d3de13ff135` |
| `BPRJ` | `FireRed_j.gba` | `e2cdfb0415ef09e887e9d27b925ff02a713a92f004843490cf6b88b68db6cd01` |
| `BPRS` | `FireRed_s.gba` | `d4dee5aeb5313e073d6067bee37278b0204886958467633978bb746bbe3d5b76` |
| `BPGD` | `LeafGreen_d.gba` | `eb0e340b5efb3ccb7bab104183d2050fa834261dd816c5ad8221e4e98c04342b` |
| `BPGE` | `LeafGreen_e.gba` | `993a8a5695a4f7e4dfe8ceec55beb43e020e82b492854d457d4aa3f864d20f08` |
| `BPGF` | `LeafGreen_f.gba` | `751346c16c0cf3a3ec601d6c2d3c482b54609c5d00ca74f2f668d75b31b8efde` |
| `BPGI` | `LeafGreen_i.gba` | `b99b9c58c83a61b5bd8a1a69b6f21ce0cfab8d1f6065b53b81a323801c9b2895` |
| `BPGJ` | `LeafGreen_j.gba` | `a2aa939a23a36610902be51169042efac78f2f6db6a433e06443a2ee09d4f19e` |
| `BPGS` | `LeafGreen_s.gba` | `a943ecfd6560115b184dc244daed71ba328a67334f343eb35b39932c3ce7c731` |

| 符号 | 德文火红 | 德文叶绿 | 意大利文火红 | 意大利文叶绿 | 西班牙文叶绿 |
|---|---|---|---|---|---|
| `gmain` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` |
| `sb1ptr` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` |
| `sb2ptr` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` |
| `rng` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` |
| `vblank_intr` | `0x08000730` | `0x08000730` | `0x08000730` | `0x08000730` | `0x0800071C` |
| `create_mon` | `0x08041178` | `0x08041178` | `0x08041164` | `0x08041164` | `0x08041164` |
| `client_run_buffer_script` | `0x08148BA4` | `0x08148B80` | `0x08148BE4` | `0x08148BC0` | `0x08148CAC` |
| `save_slot_layout` | `0x083FCEC0` | `0x083FCCFC` | `0x083F464C` | `0x083F4488` | `0x083F7674` |

基于 ROM 的测试在 Unicorn 下运行每个卡带的 `Client_RunBufferScript`、`CreateMon`、`GetVarPointer`、`VBlankIntr`、存档钩子加载器和碰撞函数，并在 mGBA 下运行每张卡带。

### 日文布局

日文火红／叶绿使用不同的 EWRAM 布局：

| 符号 | 日文 |
|---|---|
| 队伍、队伍数量 | `0x020241E0`、`0x02023F85` |
| 玩家角色、对象事件 | `0x02036FA8`、`0x02036D68` |
| 调色板渐隐、野外遇敌禁用字节 | `0x020379E8`、`0x02038624` |
| `gSpecialVar_0x8000` | `0x02036FE8` |
| `gMain`、`gIntrTable[4]` | `0x030022E0`、`0x03002740` |
| `gRngValue`、`gSaveBlock1Ptr`、`gSaveBlock2Ptr` | `0x03004230`、`0x03004238`、`0x0300423C` |

`RunTextPrinters`（`0x08002D38`）以 `0x20` 的步幅读取位于 `0x02020030` 的数组（国际版为 `0x24`）。

SaveBlock1 为 `0x3D40` 字节（国际版为 `0x3D68`）；扇区 id 4 覆盖 `0xEC0` 字节（`0xEE8`）。`RamScript` 保存校验和 `0x361C`、魔数 `0x3620`、主体 `0x3624`。

神秘卡片为 164 字节，神秘新闻为 224 字节。`SaveWonderCard` 为 `0x081481F4`（`BPRJ`）／`0x081481CC`（`BPGJ`），验证地址为 `0x08148250`／`0x08148228`。卡片 CRC 位于 SaveBlock1 `+0x3204`，数据位于 `+0x3208`，新闻位于 `+0x3124`。`BufferCardText`（`0x08149934`）读取标题字节 10..27、副标题字节 28..40、41..120 的四行 20 字节正文以及 121..160 的两行 20 字节脚注。原生 `.wc3` 布局见[礼物文件](gifts.md#native-formats)。

神秘卡片和神秘新闻的接受列表保存活动 6 和 7（`BPRJ` 为 `0x08410EC4`、`0x08410EC8`；`BPGJ` 为 `0x08410E4C`、`0x08410E50`），而其他所有卡带保存的是 21 和 22 [src/data/union_room.h:405-406]。被接受的 RFU 序列号为 `{0x0002, 0x7F7F}`（`BPRJ` 的 `0x083FC378`）。全部十二个标题都将 `0x01006fa0233f8000` 列为其首个本地通信 ID。

日文名称使用假名表，训练家姓名限制为五个字符；拉丁重音符号与假名共享字节值，因此内置礼物文本会去掉重音，并按每页两行、每行 26 个字符换行。`CreateMon` 将编号 25 的宝可梦命名为 ピカチュウ。日文队伍卡片使用其来源的日文结构体大小；两个提示文本被缩短。

### 零售实机验证

| 卡带 | 已在零售实机验证 | 来源 |
|---|---|---|
| 意大利文叶绿（`BPGI`，修订版 `0x0A`） | 全部 41 个 `Build` 字段与主机内存一致；跟随者安装；大师球卡片与道具发放 | [贡献者验证](https://github.com/Decryptu/pokeldn/issues/13) |
