---
title: Switch keys on the Pi
parent: Hardware and setup
nav_order: 2
---

# 在树莓派上安装 Switch 密钥

`prod.keys` 保存用户自己 Switch 的密钥，实时 LDN 主机需要它。切勿提交到版本库、粘贴进配置、放进抓包，或把桌面虚拟环境拷到树莓派；部署流程永远不会传输它。文件放在 `/home/PI_USER/.switch/prod.keys`，树莓派上被忽略的 `config/host.local.toml` 写绝对路径，因为主机在 `sudo` 下运行，`~` 不会解析到登录账户：

```toml
[ldn]
keys_path = "/home/PI_USER/.switch/prod.keys"
```

## 在树莓派本机安装

以树莓派登录用户运行安装器（在 `sudo` 下会切回 `$SUDO_USER`）。它会创建模式为 `0700` 的 `~/.switch`，以模式 `0600` 安装文件，从不显示内容；再次运行时若文件相同则保留并修复权限。来源必须是登录用户可读的绝对路径普通文件：

```bash
cd ~/pokeldn
./scripts/install_switch_keys.sh --source /absolute/path/to/prod.keys
```

`--stdin` 经 SSH 流式传入密钥，不落临时副本：

```bash
# 在桌面端；pi-ldn 是你的 SSH 别名。
ssh pi-ldn 'cd ~/pokeldn && ./scripts/install_switch_keys.sh --stdin' < "$HOME/.switch/prod.keys"
```

## 经 SSH 别名用 SCP

暂存在私有目录，切勿用 `/tmp` 这类共享目录，事后删除副本（`scp -p` 保留本地权限）：

```bash
# 在桌面端。
ssh pi-ldn 'install -d -m 700 "$HOME/.frlg-ldn-provision"'
scp -p "$HOME/.switch/prod.keys" pi-ldn:.frlg-ldn-provision/prod.keys
ssh pi-ldn 'cd ~/pokeldn && \
  ./scripts/install_switch_keys.sh --source "$HOME/.frlg-ldn-provision/prod.keys" && \
  rm -f "$HOME/.frlg-ldn-provision/prod.keys" && \
  rmdir "$HOME/.frlg-ldn-provision"'
```

任一种方法都可这样核对：

```bash
ssh pi-ldn 'stat -c "%a %U %n" "$HOME/.switch" "$HOME/.switch/prod.keys"'
# 期望：700 PI_USER /home/PI_USER/.switch
#       600 PI_USER /home/PI_USER/.switch/prod.keys
```
