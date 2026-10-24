---
title: Reverse-engineering a Switch title
nav_order: 3
---

# 逆向工程一个 Switch 游戏

本页介绍如何就地读取零售版 Switch 游戏的代码，适用于 Unity/IL2CPP（BDSP）和原生 C++（剑／盾）游戏。

## 工作顺序

1. 搜索已发布的资料中的常量，包括 NintendoClients wiki 的逐游戏页面：

       gh search code "<a constant, a field name, a class name>" --limit 20
       gh api repos/kinnay/NintendoClientsWiki/contents/<Page>.md --jq .content | base64 -d

2. 查找现有的反编译成果（BDSP 的 `TeamLumi/opendpr`）以及共享该游戏密钥的客户端。
3. 在某个构建的可执行文件和元数据中为所有内容命名。
4. 在二进制中验证。
5. 最后再搜索密钥空间：一次错误输入就能得到明确的否定结果。

## 提取可执行文件

### 从 NSP 提取

NSP 是包含 NCA 的 PFS0。标题密钥位于 `<rights id>.tik` 中：加密密钥在 `+0x180`，权限 ID 在 `+0x2A0`；其最后一个字节 *n* 选择 `titlekek_{n-1}`。一个稀疏文件（用 `dd` 将所需范围写入 `truncate` 过的文件）可通过 hactool 的边界检查。

### 从 XCI 提取

`tools/switch/xci_read.py` 遍历 HFS0/PFS0，解密 NCA 头并打印每个分区的偏移、计数器和密钥；卡带 NCA 的主体密钥是位于 `key_area_key_application_<max(crypto_type, crypto_type2) - 1>` 下的密钥区槽位 2。

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca <id> --exefs 0 --extract main

陷阱：`fs_type` 位于 +0x2，哈希类型位于 +0x3（hactool 交换了名称）；分区计数器是反向使用的。

### 从 RomFS 提取

分区使用 AES-128-CTR（计数器：分区 CTR 与 `offset >> 4` 的大端表示），因此任意范围都能单独解密。`tools/switch/romfs_read.py` 会遍历并提取，拒绝大小字段不为 `0x50` 的头。陷阱：hactool 在 `prod.keys` 中遇到 34 个十六进制数字的行时会中止，在稀疏文件上使用 `--listromfs` 会导致段错误。

## 先为一切命名

- IL2CPP：`global-metadata.dat` 加上同一构建的可执行文件，可让 Il2CppDumper 获取每个 C# 方法。
- C++ RTTI：`tools/switch/rtti_names.py` 根据重定位为 `nn::pia` 类命名（BDSP 中 279 个，剑／盾中 252 个）。`LocalProtocol` 与 `LanProtocol` 区分了 LDN 与 LAN 密钥派生。

## 仅存在于元数据中的常量

`[Serializable]` C# 类的 `byte[]` 默认值仅存在于 `global-metadata.dat` 中，形式为 `Field$<PrivateImplementationDetails>.<SHA-1>`，通过构造函数中的 `InitializeArray` 访问。BDSP 的游戏密钥种子就是以这种方式存储的。

## 检查你转储的是哪个版本

BDSP 基础版定义了 24 条网络消息，1.3.0 定义了 65 条：

| 结构体 | 基础版 | 1.3.0（[协议页](bdsp_protocol.md#framing)） |
|---|---|---|
| `PosData` | `Vector3 pos, short rotY`，16 字节 | `ushort posX, ushort posZ, short rotY`，6 字节 |
| `JoinData` | 少两个字段，已对齐 | `byte, byte, byte, short, Vector3`，17 字节未对齐 |

使用基础版转储的布局去解码 1.3.0 的抓包，会得到看似合理的乱码。`strings global-metadata.dat | grep NetPlayerNameData` 只会找到 1.3.0。常量在更新后仍然存在；结构体则不会。

## 读取游戏更新档的 RomFS

更新档的 RomFS 是基础版之上的 BKTR 分区；`tools/switch/bktr_read.py` 会组合其重定位表和子分区表：

    ./.venv/bin/python tools/switch/bktr_read.py UPDATE.nsp --base BASE.nsp \
        --extract /Data/Managed/Metadata/global-metadata.dat

陷阱：XCI 的更新分区存放的是系统标题的 Program NCA；请根据更新档的标题来选择基础版。

## 查找调用者

扫描 `bl` 和尾调用 `b`：BDSP 的 `ANetData<SelectData>$$SendReliableData` 只有 `b` 调用者。没有任何分支跳转到它的方法，可能是通过 ADRP/ADD 注册的委托（`arm64_xref.py`）。

陷阱：`arm64_xref.function_start` 可能会越过 `udf` 填充进入前一个函数；以“入口后 N 字节”为边界限定函数，可能会越过其 `ret`；`mov w0,
#0x80` 是 ORR 立即数，在字节扫描中不可见。

## 调用 nnSdk

nnSdk 调用会经过一个由 JUMP_SLOT 重定位命名的 GOT 槽位（`tools/switch/nso_imports.py`）。

## 工具

全部离线，基于 `pokeldn.switch`：

    tools/switch/nso_read.py     an NSO's segments decompressed at their memory offsets
    tools/switch/nso_relocs.py   RELA and RELR relocations (modern titles use RELR)
    tools/switch/arm64_xref.py   ADRP cross-references, BL call graph, function starts
    tools/switch/arm64_dis.py    capstone disassembly
