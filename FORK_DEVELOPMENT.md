# Fork 二次开发规范

本规范适用于 `ai-agent-dep/mcp-toolbox`，上游为
`googleapis/mcp-toolbox`。本 Fork 的分支、同步、合并与发布流程以本文为准；
代码风格、接口设计和测试要求继续遵循 [DEVELOPER.md](./DEVELOPER.md)、
[CONTRIBUTING.md](./CONTRIBUTING.md) 和 [GEMINI.md](./GEMINI.md)。
向上游贡献时遵循上游自己的贡献流程。

## 远程与分支职责

| 名称 | 职责 | 规则 |
| --- | --- | --- |
| `origin` | `https://github.com/ai-agent-dep/mcp-toolbox.git` | 团队代码、PR 和发布的目标仓库 |
| `upstream` | `https://github.com/googleapis/mcp-toolbox.git` | 获取官方代码，禁止直接推送 |
| `main` | 跟踪 `upstream/main` | 只允许快进同步，不提交二开代码、规范或合并提交 |
| `develop` | 二开集成分支 | 通过 PR 接收自研功能和经过验证的上游升级 |
| `feature/<topic>` | 单项功能 | 从 `develop` 创建，PR 目标为 `develop` |
| `fix/<topic>`、`docs/<topic>`、`chore/<topic>` | 修复、文档、维护 | 从 `develop` 创建，PR 目标为 `develop` |
| `sync/<version-or-date>` | 一次上游升级 | 从 `develop` 创建，合并选定上游基线，验证后合回 |
| `codex/<topic>` | Codex 创建的任务分支 | 与对应功能或同步分支遵循相同规则，PR 目标为 `develop` |

`feature/*`、`sync/*` 等为命名模式，按任务临时创建，不预建空分支。
共享分支禁止 rebase、强制推送、重建历史；同步发生分叉时先调查原因，
不得通过 `reset --hard` 或强推覆盖。

## 本地配置

首次获取项目：

```bash
git clone https://github.com/ai-agent-dep/mcp-toolbox.git
cd mcp-toolbox
git remote add upstream https://github.com/googleapis/mcp-toolbox.git
git config remote.upstream.fetch '+refs/heads/main:refs/remotes/upstream/main'
git config remote.upstream.pushurl DISABLED
git config remote.pushDefault origin
git config push.default simple
git config pull.ff only
git fetch upstream --tags
```

已有仓库先用 `git remote -v` 核对地址，不要重复添加 remote。
上述配置仅作用于当前本地仓库；`DISABLED` 是防止误推的本地保护，
不替代 GitHub 权限控制。

首次创建 `develop` 时，先确认 Fork 与上游的共同历史、已有二开提交和目标基线。
只有确认 `main` 是干净的上游跟踪分支时，才从它创建 `develop`；
若远程已有 `develop`，使用 `git switch --track origin/develop`。
日常开发先更新 `develop`，再创建任务分支：

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/example
```

以上日常示例以远程 `develop` 已发布为前提。首次仅在本地初始化时，
直接从本地 `develop` 创建任务分支即可。

## 同步上游

上游跟踪与产品升级分开进行。`main` 可以经常跟踪最新代码；
产品升级优先选择上游正式 release tag，不因更新 `main` 自动升级 `develop`。
开始前保持工作区干净，将未提交工作妥善保存在自己的任务分支。

### 更新跟踪分支

```bash
git fetch origin
git fetch upstream --tags
git switch main
git merge --ff-only origin/main
git merge --ff-only upstream/main
# 需要将跟踪分支发布到 Fork 时执行：
git push origin main
```

任一步不能快进时停止并检查差异。禁止把 `develop` 合入 `main`。
GitHub 的 Sync fork 功能只用于干净的上游跟踪分支，不用于升级二开集成分支。

### 升级二开集成分支

以下 `<target-tag>`、`<version-or-date>` 为占位符，执行前替换。

```bash
git switch develop
git pull --ff-only origin develop
git switch -c sync/<version-or-date>
git rev-parse '<target-tag>^{commit}'
git merge --no-ff <target-tag>
```

需要采用尚未发布的上游更新时，记录并合并经过确认的完整 commit SHA，
避免评审期间目标随 `upstream/main` 移动。
解决冲突后按实际改动验证编译、单元测试、相关集成测试、配置和 MCP 行为兼容性。
代码升级通常至少运行：

```bash
go build -o toolbox
go test -race ./cmd/... ./internal/...
```

相关集成测试和 lint 按现有开发规范执行；仅修改根目录 Markdown 的任务
检查差异、链接及格式即可。记录未能执行的检查及原因。

升级 PR 必须记录原基线、目标 tag 与完整 SHA、冲突解决方式、兼容性变化、
验证结果和回滚方案。合入 `develop` 时使用 **Create a merge commit**，
保留上游祖先关系；禁止对同步 PR 使用 squash merge 或 rebase merge。
普通功能 PR 可以 squash merge，提交与 PR 标题遵循 Conventional Commits。
紧急 cherry-pick 使用 `git cherry-pick -x <sha>` 记录来源，并在后续完整升级时复核。

## 二开边界与发布

- 新能力优先使用现有扩展接口和独立模块，环境差异优先通过配置表达。
- 修改上游核心逻辑时保持改动集中，避免无关格式化、重命名和目录搬迁。
- 通用修复与业务定制拆分；适合回馈上游的改动单独提交上游 PR。
- 自研 tag 使用 `fork/v<version>`，避免与拉取的上游 `v<version>` tag 冲突；
  镜像采用团队自己的仓库和不可变版本标签，不覆盖上游 tag。
- 每次自研发布记录自研版本、发布 commit、上游 tag（若有）与完整 SHA、
  自研变化和兼容性说明。首次初始化基线见下文；升级时在 PR 和发布说明中更新记录。
- 保留上游 LICENSE、版权和许可证要求的声明。

## GitHub 仓库设置目标

以下需要在发布 `develop` 后由仓库管理员配置，文档本身不代表已启用：

- 默认分支设为 `develop`，新功能 PR 默认指向它。
- `main` 禁止删除和强推，只允许指定维护者或同步机器人更新；
  若强制通过 PR 更新，必须支持快进方式，不得引入额外合并提交破坏镜像关系。
- `develop` 禁止删除和强推，要求 PR、评审及适用的 CI 检查通过。
- 允许 merge commit；不要给 `develop` 设置强制线性历史，以便保留上游合并关系。
- 审核现有 GitHub Actions 的分支过滤、仓库身份判断、权限和发布目标后，
  再为 `develop` 接入团队 CI；本地创建分支不会自动完成这些设置。

## 本次本地初始化基线

- 日期：2026-11-10（Asia/Shanghai）。
- `origin/main` 与 `upstream/main` 均为
  `4a35c9469df37d2e6f7299de11902b0fdacf9049`，无独有提交。
- 本地 `main`、`develop` 从该提交创建，保留完整提交历史。
- 该提交为本次开发起点，不代表已完成生产发布验证；正式发布仍需选择并验证基线。
