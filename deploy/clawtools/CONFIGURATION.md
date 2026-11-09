# 日常配置操作（现有 v1.16.0 部署）

## 位置和入口

- SSH：`ssh -p 34369 root@61.184.12.13`。本机凭据位置见 [部署记录](README.md)，不要输出密码。
- 生效配置：服务器 `/etc/mcp-toolbox/tools.yaml`；单文件，无 Docker 挂载。
- 密钥环境：`/etc/mcp-toolbox/toolbox.env`，`root:root 0600`；systemd 的可选 `EnvironmentFile` 已接入。
- 服务：`mcp-toolbox.service`；二进制 `/opt/mcp-toolbox/current`。
- 本地 `tools.yaml` 是空环境基线。每次修改先读取服务器当前文件；不能覆盖其他管理员的改动。
- 当前支持 `--config`、`--configs`、`--config-folder`，三者互斥。本部署沿用单文件。

以下命令均在服务器执行。无需开发管理后台，也无需修改核心源码。

## 新增、修改和删除

参考 [多实例模板](examples/multiple-databases.yaml.example)：两个 PostgreSQL 实例和
一个 MySQL 实例，每个 Source 使用独立名称和环境变量。该文件仅供参考，未加载，
没有真实地址或密码；按实际需要选择对象，不要整份直接启用。

空配置继续使用现有 `sources: {}`、`tools: {}`、`toolsets: {}`。首次新增时可把
这三个空映射替换成模板展示的多文档格式（每个对象一个 `kind`，用 `---` 分隔）。
非空旧格式如需转换，先复制为候选，再对候选执行 `toolbox migrate --config`；
不得混用两种格式或直接迁移正式文件。

- 新数据库：新增 `kind: source`，设置 `type: postgres` 或 `mysql`，连接字段用
  `${实例名_HOST}`、`${实例名_PASSWORD}` 等变量。同类型多实例只需新增不同名称。
- 新 SQL 工具：新增 `kind: tool`，`name` 用 snake_case，`type` 用 `postgres-sql`
  或 `mysql-sql`，`source` 引用已有 Source；固定 SQL，不开放任意 SQL 输入。
  PostgreSQL 参数用 `$1`、`$2`，MySQL 用 `?`，按顺序定义 `parameters`。
- 工具组：新增 `kind: group`，`tools` 列出工具名；路由为 `/mcp/组名`。
  现有 `toolsets` 仍受支持。组不承担鉴权，默认 `/mcp` 可发现全部工具。
- 修改只改目标对象；删除工具时同时移除所有组中的引用，删除 Source 前先清理引用工具。
- 只读应使用数据库最小权限账号和当前 Source 支持的只读能力；
  `annotations.readOnlyHint: true` 只是提示，不能代替数据库权限。
  当前公网入口没有登录要求，接入私有数据前须配置并验证原生工具认证；
  未验证认证前不要发布业务查询。写入只按管理员具体授权添加。

例如参数化客户查询（先确认实际表、字段、权限）：

```yaml
kind: tool
name: list_customers
type: postgres-sql
source: pg_business
description: List up to 20 customers matching an exact name.
statement: SELECT id, name FROM customers WHERE name = $1 LIMIT 20
parameters:
  - name: customer_name
    type: string
    description: Exact customer name.
```

在服务器私密编辑 `toolbox.env`，使用 systemd 环境文件的 `NAME=value` 语法，
不用 `export`，不要在终端命令、Git 或聊天中填写明文密码。特殊字符按 systemd
EnvironmentFile 规则引用；该文件不是 shell 脚本，不要直接 `source`。
修改前将环境文件备份到 root 独占目录。仅配置热重载不会重新读取这个环境文件。

## 校验候选

先在 root 独占目录备份当前配置和环境；候选必须独立于正式文件，避免提前触发热重载：

```bash
umask 077
backup_dir=$(mktemp -d /root/mcp-toolbox-config.XXXXXX)
cp -a /etc/mcp-toolbox/tools.yaml "$backup_dir/tools.yaml"
cp -a /etc/mcp-toolbox/toolbox.env "$backup_dir/toolbox.env"
install -m 0640 -o root -g mcp-toolbox /etc/mcp-toolbox/tools.yaml /etc/mcp-toolbox/tools.candidate.yaml
# 私密编辑 /etc/mcp-toolbox/tools.candidate.yaml 和必要的 toolbox.env
systemd-run --quiet --wait --pipe --collect \
  -p User=mcp-toolbox -p Group=mcp-toolbox \
  -p EnvironmentFile=/etc/mcp-toolbox/toolbox.env \
  /usr/bin/python3 /opt/mcp-toolbox/deploy/check-config.py \
  /etc/mcp-toolbox/tools.candidate.yaml
```

校验器用当前官方二进制启动一次性 STDIO 子进程，不监听端口，不调用 SQL 工具，
最多运行 45 秒。原生加载检查 YAML、重复名称、Source/工具/组引用及初始化；
随后检查 MCP 初始化和工具列表，成功输出 `valid: true` 及工具名。
失败返回非零，停止应用；为避免泄漏展开后的密钥，不回显原生错误正文。
需要详细诊断时，在服务器私密终端用同一用户和环境运行原生命令，勿复制敏感输出。
新 Source 初始化可能尝试连接数据库，但加载成功不等于实际查询已经验证。

## 应用和核验

确认校验成功、完整工具名符合预期，并比较正式文件与本次备份，确保期间无人修改：

```bash
cmp -s /etc/mcp-toolbox/tools.yaml "$backup_dir/tools.yaml"
# cmp 非零时停止，重新读取当前配置合并修改、备份、校验。
mv /etc/mcp-toolbox/tools.candidate.yaml /etc/mcp-toolbox/tools.yaml
```

当前服务默认监听文件变化，数秒内热重载，无需重启。若改了环境变量则执行
`systemctl restart mcp-toolbox`；若改了服务单元，先 `systemd-analyze verify` 和
`systemctl daemon-reload`。不要只凭健康接口判断新配置已生效；加载失败时旧配置
可能仍正常服务。逐项确认初始化版本、完整工具名和每个受影响组：

```bash
systemctl is-active mcp-toolbox
curl -fsS https://mcp-toolbox.clawtools.cc/healthz
curl -fsS https://mcp-toolbox.clawtools.cc/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"config-check","version":"1"}}}'
curl -fsS https://mcp-toolbox.clawtools.cc/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
# 把最后一个 URL 换成 /mcp/实际组名，核对组内完整列表。
journalctl -u mcp-toolbox --since '5 minutes ago' --no-pager
```

工具较多时跟随 `nextCursor` 取完整列表。带认证后用实际授权客户端执行上述检查，
不要把令牌放进可公开的命令或日志。日志可能含数据库错误或连接信息，只在私密会话查看。
有真实数据库后，按授权调用固定的 `SELECT 1` 工具测试连接，再验证业务参数查询；
不为测试创建业务表、数据或执行写入。

任一步失败，立即恢复本次备份（即使旧配置仍在内存中运行，也不能留下磁盘上的坏配置）：

```bash
install -m 0600 -o root -g root "$backup_dir/toolbox.env" /etc/mcp-toolbox/toolbox.env
install -m 0640 -o root -g mcp-toolbox "$backup_dir/tools.yaml" /etc/mcp-toolbox/tools.restore
mv /etc/mcp-toolbox/tools.restore /etc/mcp-toolbox/tools.yaml
systemctl restart mcp-toolbox
# 重复健康、初始化、完整工具和组列表检查，确认恢复。
```

成功后同步非敏感配置与说明到仓库和 `/opt/mcp-toolbox/deploy/`；不复制密钥环境文件。

## 本次验证（2026-11-10）

- 实际版本为 `1.16.0+binary.linux.amd64.06ea49d`，服务启动方式、文件权限与部署记录一致。
- 已接入空的 `toolbox.env`（0600），校验 systemd 单元、重启并验证正式服务。
- 一次性校验：空配置通过；YAML 错误、重复组名、无效工具引用、无效 Source 引用均被拒绝。
- 热重载实测：临时空组出现；无效 YAML 被拒绝且保留已加载组；恢复原配置后组消失，PID 不变。
- 最终恢复空环境；公网健康、MCP 初始化和空工具列表均通过。
- 尚无数据库凭据，未执行数据库连接、业务 SQL、读写权限或认证后的访问测试。
  接入时需提供数据库类型、地址/端口、库名、账号与密钥的安全位置、TLS 要求、
  授权的 SQL/表字段及工具组，以及 MCP 调用方和认证信息。

按已部署 tag 核对的官方说明：
[配置](https://github.com/googleapis/mcp-toolbox/blob/v1.16.0/docs/en/documentation/configuration/_index.md)、
[CLI 与热重载](https://github.com/googleapis/mcp-toolbox/blob/v1.16.0/docs/en/reference/cli.md)、
[组](https://github.com/googleapis/mcp-toolbox/blob/v1.16.0/docs/en/documentation/configuration/groups/_index.md)。
