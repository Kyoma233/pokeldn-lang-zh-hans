---
title: Brilliant Diamond and Shining Pearl
nav_order: 5
has_children: true
---

# 晶灿钻石／明亮珍珠

晶灿钻石／明亮珍珠是 ILCA 的 Unity 作品，其 IL2CPP 游戏代码直接跑在 Pia 上。页面描述的是 1.3.0 版本，场景为联盟房间（宝可梦中心 2F、左侧接待员、普通「是」）与地下大洞窟。

## 状态

在零售硬件上已可用：

| 功能 | 细节 |
|---|---|
| 在主机会话中占席 | 只需 `prod.keys` 与 LDN 口令；每个数据包均可解密；发送路径与主机密文逐字节一致 |
| 传输 | Local、Mesh Station 与 Mesh Protocol 握手、RTT 计时器、双向可靠传输 |
| 联盟房间中的角色 | 行走、显示交换表情、运行游戏问候对话 |
| 交换 | 组装好的宝可梦被接受并保存；同一关联可连续交换（[交换](bdsp_trade.md#the-completed-trade)） |
| 主机 | 进入联盟房间的主机可加入已托管房间并交换（[主机](bdsp_session.md#hosting)） |
| 球胶囊 | 合成胶囊进入收藏，含玩家持有的贴纸（[协议页](bdsp_protocol.md)） |
| 记录混合、对战大厅 | 可达主机记录及其所选六只宝可梦 |
| 地下大洞窟 | 角色在地面行走；可读出主机的秘密基地 |

## 页面

| 页面 | 内容 |
|---|---|
| [加入与 Pia 层](bdsp_session.md) | 广播、口令、席位、数据包格式、密钥层级、mesh 握手与主机 |
| [游戏协议](bdsp_protocol.md) | BDSP 的 65 种消息、联盟房间与角色控制 |
| [交换](bdsp_trade.md) | 交换流程、PB8、存档与断开惩罚 |

## 未解决

- 主机画面上替换的问候名字（[问候中的名字](bdsp_protocol.md#the-name-in-the-greeting)）。
- 当 0x08 到达且未招募对战时，零售主机显示什么。代码写入地址 0x18 且无空检查，游戏模块也无用户异常处理（[对战天梯](bdsp_protocol.md#the-battle-ladder)）。
- 非地下大洞窟会话主机的零售主机是否会采纳来自 pokeldn 的 0x61。公共分发与 `UgNetworkManager` 处理无发送方过滤（[协议页](bdsp_protocol.md#the-grand-underground)）。
