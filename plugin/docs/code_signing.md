---
title: Code signing policy
nav_order: 12
---

# 代码签名策略

免费代码签名由 [SignPath.io](https://about.signpath.io) 提供，证书由 [SignPath Foundation](https://signpath.org) 签发。

桌面应用的 Windows 发行包 `pokeldn-windows-x64.zip`（见 [Releases](https://github.com/Decryptu/pokeldn/releases) 页）对本仓库源码构建的二进制带有 Authenticode 签名：`pokeldn.exe`、PKHeX 辅助程序 `pokeldn-pkhex.exe`，以及 Unicorn 库 `unicorn.dll`。GitHub Actions 从本仓库的 `v*` 标签构建它们（[release.yml](https://github.com/Decryptu/pokeldn/blob/main/.github/workflows/release.yml)）；SignPath 只签署该构建产出的文件，不会签署别处构建的产物。制品配置见 [.github/signpath/artifact-configuration.xml](https://github.com/Decryptu/pokeldn/blob/main/.github/signpath/artifact-configuration.xml)。原样捆绑的第三方文件保留各自发行方的签名，或没有签名。

## 团队角色

| 角色 | 成员 |
|---|---|
| 提交者与审阅者 | [Decryptu](https://github.com/Decryptu) |
| 批准者 | [Decryptu](https://github.com/Decryptu) |

每次发行版的签名请求都经人工批准。其他人的贡献只会以拉取请求进入仓库，并由提交者审阅。

## 隐私政策

除非用户或安装／运行者明确要求，本程序不会向其他联网系统传输任何信息。它发起的请求如下：

| 何时 | 目标 | 发送内容 |
|---|---|---|
| 启动时，若「设置」→「更新」开启（默认开启） | GitHub API，以及每个已安装插件的更新地址 | 查询最新发行版；不含玩家或其游戏信息 |
| 玩家下载无线电固件或活动团体战数据 | GitHub | 下载请求 |
| 玩家使用「交换（在线）」或 GTS | 公共 Nostr 中继（[在线交换](online.md)） | 加密的交换事件，含送出的宝可梦 |
| 玩家安装或更新插件，或浏览插件源 | 该插件或源的地址 | 下载请求 |

发往 GitHub 的请求适用 GitHub 隐私声明。各中继运营商的政策覆盖对应中继。应用不发送分析数据，也不发送崩溃报告。
