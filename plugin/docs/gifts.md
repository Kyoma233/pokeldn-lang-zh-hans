---
title: Mystery Gift files
---

# 神秘礼物文件

`.pokegift` 文件保存火红／叶绿或剑／盾的完整神秘礼物发放，或一份 FRLG ARM 主机载荷，含目标游戏与原生记录。

## 桌面应用

同一构建器服务两款游戏（`pokeldn/app/gift_builder.py`；表单在 `pokeldn/frlg/gift/builder.py`、`pokeldn/swsh/gift_builder.py`）。

| 模式 | 发送内容 |
|---|---|
| 使用预设 | 内置礼物；FRLG 奇妙卡片、奇妙新闻与主机代码以标志传给启动器 |
| 官方活动 | 真实剑／盾活动卡片（[官方活动卡片](swsh_gift.md#official-event-cards)），按内置礼物方式编译 |
| 自己制作 | 表单内容，在「开始」时编译到 `session/gifts/<tool>.pokegift` 并以 `--gift-file` 传入 |
| 打开文件 | 分享的 `.pokegift`，或剑／盾上的 `.wc8` |

FRLG「游戏增强」是常驻钩子（[`install-resident`](frlg_rom.md#install-resident)），作为一条链运行（[同时多个钩子](frlg_rom.md#several-hooks-at-once)），限 1024 字节；设置变为 `--resident-param` 标志。

| 增强 | 设置 | 参数 |
|---|---|---|
| 加速游戏（`turbo-lite`） | 速度 ×1 到 ×4；野外、对战或两者；始终开或按住 R／B／Select；更快文字 | `field` 与 `battle` = 速度 - 1，自 ×3 起 `budget=228`，`hold`，`extra=4` |
| 穿墙 | R、B 或 Select | `hold` |
| 闪光倒计时 | 减速键；慢 ×2、×4 或 ×8 | `slow`，`slow_frames` 为 1、3 或 7 |
| 无野生遭遇、带头个体显示、跟随宝可梦 | 无 | |

不提供 L：只有 R 的帮助系统开关有钩子可让出的标志。「稍后恢复增强」把集合写入 `filler_B20`（`save-write --resident`）并安装；超过 876 字节的集合以及跟随宝可梦总会走存档。「妈妈恢复你的增强」使与妈妈对话在任意启动后安装已存集合。再次发送增强会替换正在运行的集合。

「读取存档」提供训练家 ID（TID）与秘密 ID（SID）、训练家详情与游戏时间，以及上次保存队伍的性格、个体与努力值，且不改动存档（[读取存档](frlg_rom.md#reading-the-save)）。

`.wc3` 与 `.wc8` 即使以 `{` 开头也按二进制读取。「自定义」在表单能表达时把预设拷进表单：所有剑／盾预设，以及仅由无条件表单步骤组成的 FRLG 卡片。

FRLG 表单可构建奇妙卡片、奇妙新闻或主机代码。

| 部分 | 内容 |
|---|---|
| 卡片 | 标题、副标题、四行文字、图标物种、卡片 id 1000–1019、可否再收、可否分享 |
| 交付人 | 任意宝可梦中心的配送员、玩家家中的妈妈，或真新镇南侧的男人 |
| 步骤 | 宝可梦（物种、等级、携带物、四个招式）、道具与数量、蛋、野生对战、消息 |
| 新闻 | 标题、最多十行、新闻 id |
| 主机代码 | ARM 源码或预构建 `.bin`、面向的卡带、期望应答、回传字节 |

每一步是独立交付阶段：队伍或背包满会停在该步，重试只给剩余部分。另一人通过 `initramscript` 绑定持有步骤，会隐藏卡片并在替换前每次给予步骤。物种使用内部编号（`pokeldn/frlg/save/species_names.py`）。

主机代码需要 `arm-none-eabi-as`（PATH、Homebrew 或 Arm 的 Windows 目录），或预构建 `.bin`：

| 系统 | 命令 |
|---|---|
| macOS | `brew install arm-none-eabi-binutils` |
| Fedora | `sudo dnf install arm-none-eabi-binutils-cs` |
| Debian、Ubuntu 及衍生版 | `sudo apt install binutils-arm-none-eabi` |
| Windows | `winget install Arm.ArmGnuToolchain` |

「离线检查」在模拟主机上运行代码（`pokeldn/frlg/rom/custom_code.py`），「开始」与保存亦然，会拒绝出错或永不返回 1 的代码。

剑／盾表单可构建宝可梦（可选超极巨化）、蛋、最多六件道具、服装（[服装](swsh_gift.md#clothing)，每性别六件）、对战点数或金钱，版式如[零售剑收下的卡片](swsh_gift.md#a-card-delivered-to-a-retail-console)。

「保存礼物文件」写出含全部卡带变体的 `.pokegift`，无需开发板或密钥。主机的游戏代码选用变体；文件中缺少的卡带会在发送前被拒绝。

## 命令行

两个礼物启动器都接受 `--gift-file FILE`；剑／盾上 `--record` 是别名。`--export-gift FILE` 保存所选礼物并在使用无线电前退出。

```bash
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --export-gift celebi.pokegift
./.venv/bin/python bin/frlg_mg_host.py --news berry --export-gift news.pokegift
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 --export-gift pikachu.pokegift
./.venv/bin/python -m pokeldn.gifts inspect celebi.pokegift
```

FRLG 礼物文件一并定义卡片标志 ID、脚本、问卷与拒绝消息。与之并用时，`--flag-id`、`--questionnaire`、`--hunt-*` 等载荷覆盖会被拒绝；无线电、训练家与卡带选择选项仍可用。

更多原生格式导入、主机代码打包与文件布局见上游英文页；桌面应用的「打开文件」与「保存礼物文件」覆盖日常用法。
