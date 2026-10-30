---
title: Code organization
---

# 代码组织

GUI 和命令行共享工具预设和宝可梦准备；游戏模块保留其线上格式和时序，共享组件位于任何游戏目录之外。

| Location | Responsibility |
| --- | --- |
| `pokeldn/app/` | 工具目录、参数组装、解析器检查、设置、路径和子进程 |
| `pokeldn/popup.py` | 程序在应用中显示的[弹出窗口](gui.md#pop-ups)；由 `pokeldn/app/popups.py` 决定显示哪些 |
| `pokeldn/pokemon.py` | PKHeX 服务、导入、最终提供验证和接收文件 |
| `pokeldn/gifts.py` | 共享[神秘礼物文件](gifts.md)信封、读取器、写入器和原生转换 |
| `pokeldn/receiver_gift.py` | 交易主机为控制台存档生成的神秘礼物宝可梦（[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)） |
| `services/pkhex/` | 锁定的 PKHeX.Core；合法遭遇生成和兼容性检查 |
| `pokeldn/ldn/` | 无线电传输、IP、Pia、可靠性和频道表 |
| `pokeldn/online/` | [在线交易](online.md)：中继、匹配和加密的伙伴频道 |
| `pokeldn/gba/` | GBA 无线链路协议 |
| `pokeldn/gen8.py`、`pokeldn/gen9.py` | 共享宝可梦记录编解码器 |
| `pokeldn/<game>/` | 游戏身份、消息、状态机和协议变体 |
| `bin/` | 解析器和会话编排 |
| `gui/` | 视图、小部件、主题和板卡控件 |

应用一次运行一个会话，因为一块板卡服务一个进程。在另一个工具上启动会停止正在运行的会话，等待其退出，然后启动；启动还会等待正在运行的刷写。

## 宝可梦准备

每个交易启动器在打开无线电之前都会通过 PKHeX 服务准备所提供的文件。不兼容的格式、不可用的物种和非法的最终记录都会被拒绝。会话的训练家身份永远不会覆盖导入宝可梦的初训家。

| behaviour | rule |
|---|---|
| incomplete analysis | `LegalityAnalysis.Parsed` 为 false 会重启助手并在服务锁下重试一次；第二次失败会抛出异常 |
| fresh identity | 启用新 PID 和加密常数；在该设置下非法的记录保留自身并记录 `the offer kept its own PID` |
| shiny, single gender | 从遭遇中请求，因此第三世代的 PID 保持其 RNG 关联 |
| random rolls | PID、个体值和野生槽位等级，每次遭遇最多八次掷点 |
| evolved species | 当没有遭遇符合捕获情况时，提升到其进化等级；当无性别时取进化后的性别（脱壳忍者），当遭遇的形态不存在时取形态 0（葱游兵） |

在等级或物种变更后失败的记录会按顺序修复，每一步都在上一步基础上进行；保留第一个合法结果：

1. 当设置为“made”时，仅限 HOME 的活动（剑／盾中的捷拉奥拉、美录梅塔）会获得 HOME 追踪器（[HOME 追踪器设置](gui.md#the-home-tracker-setting)）。
2. 招式、回忆招式、TM/TR 记录标志、附加招式和精通标志以及传说 阿尔宙斯尺寸会被重新适配。
3. 进化记录的特性会在其捕获槽位中刷新。这必须在重新适配之后进行（传说 Z-A 中的赛富豪）。
4. 没有处理训练家的记录会获得 `POKELDN`。
5. 计数进化（命中要害、受到伤害、愤怒之拳使用次数、金币）从其计数开始。
6. 晶灿钻石／明亮珍珠中的美丽度进化（美纳斯，170）设置该美丽度以及其宝芬暗示的最低光泽度。

无法满足的请求会以原因拒绝。普通构建仅在晶灿钻石／明亮珍珠中的 2 个物种（时拉比、代欧奇希斯）、剑／盾中的 2 个（蒂安希、美录坦）、传说 Z-A 中的 1 个（美纳斯，其游戏记录拒绝华丽大赛属性）以及朱／紫中的 31 个（仅限 HOME 的传说宝可梦，以及诡角鹿，PKHeX 没有给出第九世代进化）上失败。

未指定形态的请求采用第一个能构建的形态。仅以较后形态存在的物种：

| game | species | forms PKHeX builds |
|---|---|---|
| 剑／盾 | 基格尔德 | 10%-C, 50%-C (Power Construct) |
| 剑／盾 | 玛机雅娜 | Original Color, an event |
| 传说 阿尔宙斯 | 骑拉帝纳 | Origin |
| 朱／紫 | 月月熊 | Bloodmoon |
| 传说 Z-A | 基格尔德 | 10%-C, 50%-C, Complete |
| 传说 Z-A | 粉蝶虫、粉蝶蛹 | Garden, Meadow |
| 传说 Z-A | 彩粉蝶 | Garden, Meadow, Marine |

### 遭遇顺序

一次构建会逐个版本尝试 PKHeX 的遭遇（`EncounterMovesetGenerator`），优先玩家自己的版本，每个版本内按种类尝试，每种截取其前 80 个遭遇：

| order | kind | the record built from it |
|---|---|---|
| 1 | wild slot | 在槽位位置和等级捕获，任何可捕获的球 |
| 2 | static encounter | 礼物、传说宝可梦、团体战或极巨巢穴宝可梦 |
| 3 | in-game trade | NPC 的宝可梦 |
| 4 | egg | 孵化，使用亲代遗传的球 |
| 5 | Mystery Gift | 在所有其他种类和版本之后，因为活动的固定 PID 会使新 PID 的提供非法 |

低于其进化等级的已进化宝可梦会在 100 级测试，然后二分法找到最低合法等级。朱／紫中的裹蜜龙仅在不连续等级上合法。

### 提供选项

一次构建可以要求形态、性格、特性、性别、携带物品、球、亲密度、最多四个招式、个体值和努力值、遭遇，并且在传说 阿尔宙斯和传说 Z-A 中还可以要求是否为头目，霜奶仙的糖饰，在剑／盾中可要求超极巨化因子和极巨化等级，在朱／紫中可要求太晶属性。招式、形态、遭遇和头目会缩小遭遇搜索范围；性格、特性、性别和个体值进入遭遇条件。当遭遇掷出其他结果时，记录会像玩家那样更改：

| differs | change |
|---|---|
| nature | 薄荷，第八世代起 |
| ability | 特性胶囊或特性膏药 |
| an IV asked to be 31 | 极限特训，100 级（第七、八世代）或 50 级（第九世代） |
| form | 设置在玩家可改变形态的物种上，如洛托姆 |

携带物品、球、亲密度、努力值、糖饰、超极巨化因子、极巨化等级和太晶属性在构建后设置，如同使用极巨汤、极巨糖果和太晶碎块。糖饰是霜奶仙的形态参数，0 草莓到 6 蝴蝶结；太晶属性是覆盖字节，星晶为 99（`TeraTypeUtil.SetTeraType`）。第三或第四世代超过 100 的努力值需要自相遇以来获得经验，因此记录会获得 1 点经验。传说 阿尔宙斯的奋斗等级按游戏内显示取值，个体值偏置（个体值 20 为 1、26 为 2、31 时为 3）会在存储前减去。

亲密度是初训家的。接收控制台只有在玩家是初训家时才会保留它，因此设置中的[你的训练家](gui.md#your-trainer)必须是玩家本人；各版本交易页面会说明交易会重写什么。火红／叶绿会给每只接收的非蛋宝可梦设置 70 [trade_scene.c:1071]。

| option | listed when |
|---|---|
| ball | PKHeX 至少允许一个遭遇使用它 |
| Alpha | 传说 阿尔宙斯或传说 Z-A 有该物种的头目遭遇（`IAlphaReadOnly.IsAlpha`） |
| ability | 存在携带该特性的合法构建；传说 Z-A 不列出任何特性 |
| held item | 该游戏已发布的携带物品；Let's Go 和传说 阿尔宙斯没有 |
| effort | 每项努力值 252，总计 510；Let's Go 中的觉醒值每项 200；传说 阿尔宙斯中的奋斗等级每项 10 |
| sweet | 霜奶仙，且该游戏的记录保留形态参数 |
| Gigantamax | 该物种与形态的 `Gigantamax.CanToggle` |
| Dynamax level | 剑／盾，札茜安、藏玛然特和无极汰那除外 |
| Tera Type | 朱／紫，太晶属性可改的物种（`TeraTypeUtil.CanChangeTeraType`）；18 种属性与星晶 |

「满个体值」将六项全部设为 31，「满亲密度」为 255。「满努力值」将每项填到上限；总计 510 时，该物种两项最高种族值各得 252，第三项得剩余的 6。

### 选择遭遇

`encounters` 按[遭遇顺序](#encounter-order)列出该物种与形态构建可来自的每一次遭遇，并分组：同一版本、同一地点的同一种遭遇，其所有槽位与等级合在一起，或一张神秘礼物卡片（`EncounterKey`）。每组带有地点名（`ILocation.GetEncounterLocation`，礼物则为卡片标题）、等级范围、相遇时若为进化前形态则给出该物种，以及是否可为异色。构建若指定某组的键，则只尝试该组；构建的回复会给出其 `encounter_place`。

在[遭遇顺序](#encounter-order)中第一个合法承载所有请求的遭遇会被保留；否则拒绝会指出没有遭遇能承载的第一个请求。

### Showdown 配置集

导入粘贴会使用 `ShowdownParsing.GetShowdownSets` 读取 Showdown、Smogon 或 PKHeX 配置，支持 PKHeX 导出的任何语言和 PKHeX 的拼写。没有 `Level:` 行表示 100；`IVs:` 中缺少的个体值为 31。

| the set names | result |
|---|---|
| 无法读取的行，或游戏缺少的物种、形态、特性、物品或招式，努力值超过 510 | 拒绝；不填充任何内容 |
| 朱／紫中的太晶属性；剑／盾中的超极巨化以及非 10 的极巨化等级 | 设置（[提供选项](#offer-options)） |
| 其他游戏中的太晶属性、超极巨化或极巨化等级，觉醒力量属性；Let's Go 或传说 阿尔宙斯中的努力值；传说 Z-A 中的特性 | 省略并附注 |
| 没有 `IVs:` 或 `Friendship:` 行 | 遭遇自身的值 |
| 交易队列中的多个配置集 | 从粘贴选择器中每项各交易一次，最多到队列上限；任何拒绝都会拒绝整个粘贴 |
| 队列外的多个配置集 | 第一个填充表单 |

剑／盾神秘礼物会使用 PKHeX 验证 WC8 封印并检查物种、形态、招式和物品；自定义卡片属于分发，而不是官方活动。

### Let's Go 链接代码

Let's Go 主机的代码由三个槽位组成，每个槽位从控制台的十个选择器宝可梦中挑选，并以三个逗号分隔的英文名称传给 `--code`。启动会等待直到三个槽位都设置完毕。

### 交易队列

在一个席位完成多次交易的工具最多接受六只宝可梦，按顺序提供：

| tool | offers as | after the last |
|---|---|---|
| 火红／叶绿主机和加入方 | 队伍文件，`--trades N` | 主机拒绝（`PLAYER_CANCEL_TRADE`）并等待 Cancel 和 Yes；加入方取消 |
| Let's Go 主机 | `--offer`，然后 `--next-offer` | 不再回应交易（`pokeldn/lgpe/trade.py`） |
| Let's Go 加入方 | `--offer`，重复 | 不再回应交易 |
| 晶灿钻石／明亮珍珠 | `--offer` / `--trade-template`，重复 | 再次提供最后一个 |
| 传说 阿尔宙斯 | `--trade-box-record` / `--offer`，重复 | 再次提供最后一个 |
| 朱／紫 | `--trade-offer`，重复 | 不再发送消息（`pokeldn/sv/trade.py`，`done`） |
| 剑／盾 | `--offer-file`，重复 | 再次提供最后一个 |
| 传说 Z-A | `--trade-offer`，重复 | 再次提供最后一个，在 `--fresh-pid` 下使用新 PID |

每次完成的交易都会调用 `pokeldn.ldn.show_done()`，它会闪烁 LED 并打印 `[done] trade N complete`；会话面板会统计该行。交易编号 N 大于 1 时会以以下后缀写入输出路径：`_tradeN_` 和物种（火红／叶绿）、`.N`（朱／紫）、`_N`（晶灿钻石／明亮珍珠主机）、`-N`（传说 Z-A、剑／盾）。

### 交换回来

`--trade-back` 可在每个交易主机和加入方上使用（应用的“发回”开关），在每次排队的交易后跟一次提供控制台刚发送宝可梦的交易，因此通过交换进化的宝可梦会在控制台上进化。玩家在第二次交易中提供我们的宝可梦。`pokeldn/trade_back.py` 保存顺序：

| trade | offers |
|---|---|
| 1、3、5、… | 排队的提供 1、2、3、… |
| 2、4、6、… | 控制台在上一次交易中发送的记录，逐字节 |

返回的记录永远不会接受 `--fresh-pid` 或任何其他提供编辑。在最后一次排队交易后停止的启动器会在两倍次数后停止；再次提供最后一个的启动器会继续交替。

| launcher | how the record comes back |
|---|---|
| native hosts | `TradeBack` 代替在线伙伴（`pokeldn.online.link.Partner`）：`done` 之前控制台的最后一次提供会成为下一轮的记录 |
| FireRed/LeafGreen host and join | 每个提供的队伍槽位会再次被提供；TradeMons 已将收到的宝可梦放在那里 [trade_scene.c:1054-1083]。一次会话最多运行 12 次交易 |
| native joiners | `Rounds` 在启动器自己的提供路径中选择每次交易的记录 |

由 `bin/frlg_trade_host.py --over-ip --trade-back` 托管的法语火红模拟会话在交易 1 中交易了其勇基拉，在交易 2 中收回并进化为胡地；存档保留了一只合法的胡地。由 `bin/swsh_host.py --ip-host --trade-back` 托管的盾模拟会话用其熊徒弟交换了提供的大岩蛇，然后在交易 2 中用大岩蛇换回了熊徒弟，并按 B 键离开。

`--trade-back` 会拒绝 `--online`、为接收玩家制作的礼物以及团体战、极巨巢穴和联合环模式。神秘礼物 - 模拟从不提供它。

### 结束一次运行

| role | ends when |
|---|---|
| host | 控制台在至少一次交易后离开（`pokeldn.ldn.left_after_trade`） |
| FireRed/LeafGreen host | 控制台离开 |
| joiner | 主机关闭或将角色移交；朱／紫、传说 阿尔宙斯和传说 Z-A 会在没有交易的席位后再次搜索 |

`--seconds` 和 `--hold` 会限制控制台从不离开的运行。

## 本地文件与发布

`host.local.toml`、密钥、笔记、日志和构建产物保留在本地；生产环境默认不会读取 `scratchpad/`。设置和准备好的提供内容位于平台的数据文件夹中，并可由 `POKELDN_DATA` 覆盖。清理通过 `pokeldn.app.storage` 运行（[本地存储](gui.md#local-storage)）。

打包程序会将受跟踪的运行时文件、PKHeX 可执行文件以及适用于 ESP32、S3、C3 和 C6 的固件打包在一起；缺少任一映像都会中止构建。Windows 构建会保留标准流用于子进程日志，并隐藏控制台。

## 验证

```sh
pip install -r requirements-dev.txt
dotnet build -c Release services/pkhex -warnaserror
python -m pytest tests/ -q -W error -n auto --dist worksteal
```

CI 会在 Linux、macOS 和 Windows 上运行这些。发布构建会对冻结后的可执行文件运行 `scripts/check_app.py`；它不需要密钥或开发板。
