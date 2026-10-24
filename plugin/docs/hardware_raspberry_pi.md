---
title: Raspberry Pi host
parent: Hardware and setup
nav_order: 4
---

# 树莓派 4 神秘礼物主机

带 TP-Link Archer T3U／AC1300（`2357:012d`，`rtw88_8822bu`）的 64 位树莓派 4 可托管神秘礼物。打过补丁的 LDN 实现在 `vendor/LDN`；切勿在树莓派上安装未打补丁的 PyPI 包。适配器内核设置见[适配器](hardware_adapters.md)。

部署经 SSH 别名把已提交的 Git 对象推到树莓派上的裸仓库，不经 GitHub、不用 `rsync`，也不传被忽略的文件（参考仓库、`.venv`、抓包、宝可梦文件、Switch 密钥）。

## 首次部署

在桌面端、已提交的检出中，带 SSH 别名与树莓派登录用户：

```bash
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER
```

`deploy_pi.sh` 拒绝脏的桌面检出，运行配置与文档测试，必要时创建 `/home/PI_USER/repos/pokeldn.git`，把当前提交推到其 `deploy` 分支，并创建或快进 `/home/PI_USER/pokeldn`。它从不强制重置，并拒绝带有未提交文件的树莓派检出。若 SSH 别名已含远程用户，直接给路径：

```bash
./scripts/deploy_pi.sh --host pi-ldn \
  --path /home/PI_USER/pokeldn \
  --repo /home/PI_USER/repos/pokeldn.git
```

然后在树莓派上引导：

```bash
ssh pi-ldn
cd ~/pokeldn
./scripts/setup_pi.sh
```

`setup_pi.sh` 需要 64 位 Raspberry Pi OS（`aarch64`）与 Python 3.11 或更新（Bookworm 3.11、Trixie 3.13）。它从 `requirements.txt` 构建虚拟环境，安装系统工具（`--no-apt` 可跳过），并把 `ldnclient`、`ldn`、`ldn-mon`、`ldn-tap` 排除出 NetworkManager（`--no-networkmanager` 可跳过）。请把 SSH 留在以太网或板载 Wi-Fi：托管会独占 TP-Link 适配器。

## 配置与 Switch 密钥

跟踪的 `config/host.toml` 是 TP-Link 实时配置：

```toml
[host]
live = true
skip_encryption = true
accept_decrypted_ccmp = true

[ldn]
phy = "auto"
```

被忽略的 `config/host.local.toml` 保存密钥绝对路径（主机在 `sudo` 下运行）；如何安装 `prod.keys` 见[树莓派上的 Switch 密钥](hardware_switch_keys.md)。

## 验证与运行

插入 TP-Link 适配器后：

```bash
cd ~/pokeldn
./scripts/preflight_pi.sh
./scripts/run_mystery_gift.sh
```

预检只读。它检查 Python 与内置 LDN 包，加载 `config/host.toml` 与可选的 `config/host.local.toml`，检查 TP-Link USB id 与 `rtw88_8822bu`、AP 与监听支持、NetworkManager 排除，以及密钥文件模式为 `0600`。若调用关闭了 `skip_encryption` 或 `accept_decrypted_ccmp`（含经 `run_mystery_gift.sh` 传入的参数）会被拒绝。它自行加入 Debian 的 `sbin` 路径，因此在 shell 与一行 SSH 命令中行为一致。

`run_mystery_gift.sh` 先跑一次预检，再监督短命的 root 主机进程：每次随机 TID/SID，在交付成功、尝试失败，或五分钟无 Switch 加入／无 Pia／RFU 流量后重启。按一次 Ctrl-C 停止。它始终传入 `--end-on-success`（交付后关闭即结束）与 `--idle-timeout 300`（无 Switch 流量该秒数后结束），并自行管理 `--id`，因此已保存的 `--id` 不会复用旧身份。其它 `bin/frlg_mg_host.py` 选项原样转发；`--help` 与 `--print-effective-config` 不需预检或 root。

每次加入尝试追加到被忽略的每日账本 `logs/mystery-gift-attempts-YYYY-MM-DD.csv`，列含 `attempt`、`received_result`（仅在送出奇妙卡片或印章时为 `true`）、`time`、`trainer_name`、`trainer_ot`（来自 Switch LinkPlayer 块的名字与五位训练家 ID；若在此之前失败则为空）。`bin/frlg_mg_host.py --attempt-log-dir logs` 写同一账本。

活动控制：`--gift`、`--flag-id`、`--verbose`、`--capture`、`--ot`、`--version`、`--id`。`--client-ready-idle-frames N` 是硬件测试用的时序诊断，其它情况请勿设置。`--make-artifact` 在 `artifacts/` 下写出确定性 `.ram.lst` 清单（`--artifact-dir DIR` 可改目录）：编译后的 RAM 脚本字节、解码指令、校验、分支与消息目标，以及交付阶段摘要；`--no-make-artifact` 在已保存命令中禁用它。

```bash
./scripts/run_mystery_gift.sh --gift solrock-stamp --client-ready-idle-frames 45 \
  --capture solrock-45.jsonl
./scripts/run_mystery_gift.sh --gift worlds-xp --make-artifact
```

除非诊断其它硬件，请把 `--phy`、`--adapter`、`--skip-encryption`、`--accept-decrypted-ccmp` 留在 TP-Link 默认。对 ALFA `mt76x0u`，传入当前 PHY（`iw dev`；重插后会变）并加 `--no-accept-decrypted-ccmp`；预检随后检查该 PHY 的 AP／监听模式与 `mt76x0u` CCMP 配置。

MT7601U 自定义 AP 驱动等细节见上游英文原文。
