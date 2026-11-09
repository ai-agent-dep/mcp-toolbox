# Clawtools 部署记录

## 当前部署

| 项目 | 值 |
| --- | --- |
| 部署日期 | 2026-11-10，Asia/Shanghai |
| UI | https://mcp-toolbox.clawtools.cc/ui/ |
| MCP Streamable HTTP | https://mcp-toolbox.clawtools.cc/mcp |
| 健康检查 | https://mcp-toolbox.clawtools.cc/healthz |
| 服务器 | `root@61.184.12.13:34369`，Ubuntu 24.04，amd64 |
| 应用 | 官方正式版 `v1.16.0`，`1.16.0+binary.linux.amd64.06ea49d` |
| 上游发布 commit | `06ea49d9a487a72c22419b5a8d5c22c11f0d7485` |
| 二进制 SHA-256 | `ca04ab10581c019ed3e905d0331b51faaed8e48f92d97fe592ce2312acf3769f` |
| 运行方式 | systemd `mcp-toolbox.service`，开机启动、失败自动重启 |
| 服务用户 | 独立系统用户 `mcp-toolbox` |
| 监听 | `127.0.0.1:15000`，由现有 Caddy 反向代理 |
| 工具配置 | 空工具集，无数据库、工具或认证服务 |
| HTTPS | Caddy 管理 Let's Encrypt 证书与自动续期 |

本次采用正式 release，未构建本地 Fork 的开发分支；本地初始化的
`4a35c9469df37d2e6f7299de11902b0fdacf9049` 比该 release 多 4 个上游提交。
本地规范改动不影响运行时代码。后续自研功能需构建自研产物并单独记录版本与基线。

官方二进制来源：
https://storage.googleapis.com/mcp-toolbox-for-databases/v1.16.0/linux/amd64/toolbox

官方镜像仓库连接超时，本次使用官方二进制；下载后已比对官方对象响应头
ETag 对应的 MD5 `fb96bb185f9f3648023d677bf46bca71`，并记录上述 SHA-256。

## 配置与文件

本目录保留与服务器一致的非敏感配置：

- `tools.yaml` → `/etc/mcp-toolbox/tools.yaml`，`root:mcp-toolbox`，权限 `0640`。
- `mcp-toolbox.service` → `/etc/systemd/system/mcp-toolbox.service`。
- `Caddyfile` → 主 Caddyfile 中 `BEGIN MCP Toolbox` / `END MCP Toolbox` 区块。
- 二进制 → `/opt/mcp-toolbox/releases/toolbox-v1.16.0`。
- 当前版本软链接 → `/opt/mcp-toolbox/current`。
- 工作目录 → `/var/lib/mcp-toolbox`，由 systemd 创建。

服务器上的 `/opt/mcp-toolbox/deploy/` 保存本目录的配置副本。
SSH 密码保存在 macOS 登录钥匙串，服务项为 `ssh://61.184.12.13:34369`，
账号为 `root`；不在仓库中保存密码或私钥。

服务只监听回环地址，限制 Host 与浏览器 Origin 为部署域名，启用 UI，
保持原生 `/api` 默认关闭。当前无登录要求，公开暴露的是空工具集；
接入私有数据库时需同时设计并验证工具访问认证。

## 运维

以下命令在服务器执行：

```bash
systemctl status mcp-toolbox
journalctl -u mcp-toolbox -n 100 --no-pager
curl -fsS http://127.0.0.1:15000/healthz
```

配置更新：先备份 `/etc/mcp-toolbox/tools.yaml`，安装新配置后执行
`systemctl restart mcp-toolbox`，再验证健康检查、MCP 初始化和预期工具列表。
空配置存储格式是上游兼容格式，后续可按上游规范迁移。

服务单元更新后执行：

```bash
systemd-analyze verify /etc/systemd/system/mcp-toolbox.service
systemctl daemon-reload
systemctl restart mcp-toolbox
```

Caddy 配置修改后执行：

```bash
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl reload caddy
```

版本升级时，将已校验的新二进制保存到新的版本路径，保留旧文件，
将 `current` 软链接切换到新版本并重启服务。验证失败时切回旧二进制，
如有配置变更同时恢复兼容的配置备份，再重启并验证。

本次启用站点前的 Caddy 备份：
`/etc/caddy/Caddyfile.before-mcp-toolbox-20261110`。
首次部署撤销时，停止并禁用 `mcp-toolbox`，移除主 Caddyfile 中本服务区块，
校验后 reload。整文件备份只适合确认之后没有其他站点变更时恢复。

## 上线验证

- HTTP 自动 308 跳转到 HTTPS，根路径 302 跳转到 `/ui/`。
- HTTPS 证书校验通过，颁发者 Let's Encrypt，域名匹配。
- `/ui/` 返回 200；浏览器工具页加载完成后显示 `No tools found.`。
- `/healthz` 返回 200 和 `{"status":"ok"}`。
- `/mcp` 的 `initialize` 返回正式版版本号及协商的 MCP 协议版本。
- `/mcp` 的 `tools/list` 返回 `{"tools":[]}`。
- systemd 服务启用且运行中，应用端口仅绑定回环地址。

可从外部重验空工具集：

```bash
curl -fsS https://mcp-toolbox.clawtools.cc/healthz
curl -fsS https://mcp-toolbox.clawtools.cc/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```
