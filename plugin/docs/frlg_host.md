---
title: Host implementation
parent: FireRed and LeafGreen
nav_order: 7
---

# 主机端实现

`bin/frlg_trade_host.py` 是火红／叶绿 Direct Corner 主机端：Switch 加入主机的 LDN 网络，Pia 建立对等会话，Reliable 承载一个模拟的父 RFU 链路，最终进入主机端交换状态机。`bin/frlg_mg_host.py` 复用了活动层以下的全部内容。

## 组件与职责

| 组件 | 负责内容 |
|---|---|
| `TradeRunConfig` | 不可变运行配置：`TrainerProfile`、`TradePlan`、`LdnConfig`、`HostOptions` 或 `JoinerOptions` |
| `HostApplication` | 资源排序：验证、传输启动、信标发布、事件循环、中断、清理；活动钩子提供消息和持久化，因此交换和神秘礼物共享同一循环 |
| `HostTransport` | LDN AP、虚拟接口、参与者事件、UDP :12345；不进行 Pia 解析 |
| `HostPeerProtocol` | 一个对等端的 Pia 状态：Net、Session 接受、RTT、数据包 ID、随机数选择、加密、分帧、Reliable 批处理；发出 `OutboundDatagram` |
| `HostSession` | Reliable + `RFULeader` + 活动引擎（`engine=` 选择交换或神秘礼物）；没有套接字，是离线端到端测试使用的层 |
| `HostTradeEngine` | 领导者房间进入、队伍和卡片交换、选择、确认、动画和保存屏障、取消、离开房间、关闭宽限；`HostTradeTiming` 命名帧计数 |
| `BeaconInjector` | 其原始监控套接字和工作线程 |

数据报依次流经 Switch、`HostTransport`、`HostPeerProtocol`、`HostSession`、`RFULeader`、`HostTradeEngine`（子命令行入，父命令行出）并返回。定时器截止时间来自对等协议，因此 Net/Session 重试、RTT 探测、重传和约 59.727 Hz 的节拍不依赖轮询延迟。

## 启动与会话建立

1. CLI 将 `TradeRunConfig` 交给 `HostApplication`，后者启动一个非活动的 Direct Corner 网络并定期发送信标。
2. Switch 加入；`on_participant_joined()` 发送 Pia Net 连接请求，重试直到收到 ACK。
3. Switch 回复 Net ACK 和 Session 加入请求；主机发送 Session 更新和单播加入响应（诊断设置会反转这一对），Switch 确认。
4. RTT 和 Reliable/RFU 流量开始，应用数据属性被设为活动。

格式错误的 Pia、错误填充、认证失败、不完整的 Reliable 分片和 Session 标识不匹配都会被记录并忽略。只有在其常量 ID、Pia 变量、源 IP 和加密头与当前 LDN 对等端一致时，才接受 Session 请求。

## 交换与退出房间生命周期

```mermaid
stateDiagram-v2
    [*] --> PlayerExchange
    PlayerExchange --> RoomEntry: LinkPlayer and trainer card
    RoomEntry --> PartyExchange: seat route and entry barriers
    PartyExchange --> Selection: party, mail, ribbons
    Selection --> Confirmation: Switch selects; leader offers configured slot
    Confirmation --> Animation: both confirm
    Animation --> Save: trade committed
    Save --> PartyExchange: another configured trade
    Save --> MenuExit: final party refresh
    MenuExit --> RoomExit: both cancel; five-second field wait
    RoomExit --> CloseGrace: Switch confirms room exit
    CloseGrace --> Disconnect: fifteen seconds of peer traffic
    Disconnect --> [*]
```

最后一次交换后，主机等待 Switch 的交换菜单；玩家选择 CANCEL 并确认 YES，主机立即回复 `BOTH_CANCEL_TRADE`。主机完成待机屏障，除非 Switch 先离开，否则等待五秒后离开房间，并在 Switch 确认关闭（`READY_CLOSE_LINK`）后保持正常的对等流量十五秒，然后将 RFU 断开连接入队。它用类型 4 回复 Switch 的 Session 离开请求（[frlg_link.md](frlg_link.md)，离开 Pia 会话）。LDN 离开事件会立即停止对等输出。

## 关闭与清理

断开连接后，主机如果存在接收到的宝可梦，就保存它，加入信标工作线程，关闭套接字和网络，并移除 LDN 虚拟接口。相同的清理会在正常完成、`KeyboardInterrupt`、部分启动失败和信标工作线程失败时执行。

所有主机，无论是交换、对战还是神秘礼物，都会在 Switch 离开 LDN 时停止（`HostApplication.run`）：如果未确认关闭则立即停止，如果已确认则在 2 秒稳定后（`HOST_CLOSE_SETTLE_SECONDS`）停止。`--end-on-success` 会在成功交付的断开连接发出后立即停止神秘礼物主机，无需等待 Switch 离开；其 `--idle-timeout` 会在没有 Switch 流量这么多秒后停止。

## 训练家资料传播

`pokeldn.config.DEFAULT_TRAINER` 是默认身份。每个 CLI 派生一个不可变的每次运行的 `TrainerProfile`（`--ot`、`--version`、十进制 `--id TID[:SID]`），验证 Gen III 名称和范围，并从中派生所有视图：

| 视图 | 携带内容 |
|---|---|
| LDN 发现 | 名称和公开 TID |
| Pia Session | UTF-8 参与者名称 |
| LinkPlayer | `SID << 16 \| TID`、版本、语言、性别和进度标记；Gen III 名称 |
| 训练家卡片 | Gen III 名称；主机用 `0xFF` 填充，加入方保留本机 `0x00` |

## 故障处理

- 预检会拒绝不支持 AP 的无线网卡。
- 在 Linux Wi-Fi 网卡上，AP 必须在 LDN 认证后将站点标记为 `NL80211_STA_FLAG_AUTHORIZED`。驱动配置文件和标志见[适配器](hardware_adapters.md)。
- 传输或信标线程失败会中止运行并回滚已创建的内容。
- 意外的参与者离开会停止输出。十五秒宽限期仅在参与者仍在时才走到结束。
- 宽限期（`HostTradeTiming.post_client_close_grace_frames`）只在 RFU 领导者处于 UNI 状态时计数；Switch 的 `D` 将其移至 DISCONNECTED（`pokeldn/gba/rfu_leader.py`），引擎停止计时。在 13 次零售火红主机交换中，Switch 在其第一个 `READY_CLOSE_LINK` 后 0.1 秒发送 `D`，并在其后 0.5 到 4.0 秒内离开 LDN，因此宽限期在正常关闭时永远不会生效。
- 输出仅针对完整接收到的宝可梦写入；输入 `.pk3`/`.ek3` 文件从不会被修改。

## 扩展主机

在理解它的最低层添加行为：运行配置中的设置，应用程序或传输中的操作系统和网络，`HostPeerProtocol` 中的 Pia，`RFULeader` 中的 RFU，`HostTradeEngine` 中的 Direct Corner 决策。在每一层针对其发出的数据报、负载、帧或命令行进行测试。

主机只服务一个 Switch。更多对等端需要各自一个 `HostPeerProtocol`（自己的 Pia 变量、随机数、数据包 ID）以及一个游戏级 RFU 策略；仅提高 LDN 参与者上限是不够的。

## 源码映射

| 源码 | 职责 |
|---|---|
| `bin/frlg_trade_host.py` | CLI、配置、入口点 |
| `pokeldn/frlg/host_cli.py` | 共享主机 CLI 选项 |
| `pokeldn/frlg/link/host_app.py` | `HostApplication` |
| `pokeldn/frlg/config.py` | 训练家、交换计划、神秘礼物负载、LDN、角色和运行配置 |
| `pokeldn/frlg/link/trade_runtime.py` | CLI 日志、队伍加载、槽位解析、输出保存 |
| `pokeldn/frlg/link/host_beacon.py` | 捕获的交换信标、发现变更、`BeaconInjector` |
| `pokeldn/host_support.py` | 面向操作系统的支持（sudo 感知的密钥路径解析） |
| `pokeldn/ldn/transport.py` | `HostTransport` |
| `pokeldn/ldn/host_pia.py` | Pia 分帧、`HostPeerProtocol` |
| `pokeldn/frlg/link/host_session.py` | `HostSession` |
| `pokeldn/ldn/reliable.py` | Reliable |
| `pokeldn/gba/rfu_leader.py` | `RFULeader`：父分帧、NI/UNI 握手、回声表 |
| `pokeldn/frlg/link/host_trade.py` | `HostTradeEngine`、`HostTradeTiming` |
| `pokeldn/frlg/link/linkplayer.py` | LinkPlayer 和训练家卡编码器 |
| `pokeldn/ldn/ldntrace.py` | 可选 JSONL 诊断 |
