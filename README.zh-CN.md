# stars-to-kbs 中文说明

`stars-to-kbs` 是一个本地优先的 GitHub Stars 整理工具。它会拉取你的 GitHub starred repositories，调用你本机已经登录的 AI CLI（`hermes`、`codex` 或 `claude`）进行分类和总结，然后把结果写成适合 Obsidian / 个人知识库使用的 Markdown 笔记。

英文说明见：[README.md](README.md)。

## 这个项目解决什么问题

很多人的 GitHub Stars 越积越多，但长期不整理之后很难再利用。这个工具的目标是把 Stars 转成一个可搜索、可阅读、可放进个人 KBS 的索引。

它参考了 [`amirhmoradi/starred`](https://github.com/amirhmoradi/starred) 的思路，但有一个重要区别：

- 不直接调用 OpenAI / Anthropic 等 LLM API；
- 不要求在项目里保存 LLM API Key；
- 而是调用本机已经配置好的 `hermes` / `codex` / `claude`；
- 私有配置放在用户目录，不放进公开仓库；
- 输出为一个 Markdown 笔记，方便放入 Obsidian 或其他个人知识库。

这适合已经订阅或配置了 AI CLI 工具，希望复用现有工具能力，而不是另外走 API 计价的人。

## 当前状态与大规模 Stars 处理方式

当前流程已经把分批总结、全局合并和最终校验拆开：

```text
fetch -> summarize-batches -> merge-summaries -> validate -> write-note
```

也就是说：先拉取 GitHub Stars，再按 `batch_size` 分批调用 AI CLI；随后 `merge` 阶段会把所有 batch 输出合并成统一 taxonomy，`validate` 阶段会检查每个 `full_name` 是否在最终 Markdown 中出现且只出现一次。

大规模推荐配置：

```toml
[agent]
batch_size = 50
language = "zh-CN"

[github]
include_readme = false
max_repos = 0
```

对于 400+ 或 1000+ Stars，这比简单拼接 batch 输出更可靠。但最终质量仍取决于所选 AI CLI 的上下文窗口和输出稳定性。如果校验失败，可以检查 `.work/combined-summary.md`，降低 `batch_size`，或者修复失败 batch 后使用 `--resume` 重跑。

## 隐私与安全模型

这个项目设计为可以公开放在 GitHub 上，但私有内容必须留在本地。

默认配置文件路径是：

```text
$HOME/.config/stars-to-kbs/config.toml
```

以下文件或目录默认不应该提交：

- `.env`：本地 token 或环境变量；
- `config.toml` / `*.local.toml`：本地配置；
- `.cache/`：拉取到的 GitHub Stars 数据；
- `.work/`：prompt 和 AI CLI 输出；
- `output/` / `agent-output/`：本地生成文件；
- `.venv/`、`dist/`、测试和 lint 缓存。

重要提醒：

- GitHub token 会从环境变量或 `gh auth token` 读取；
- 本项目不保存 LLM API Key；
- 但是使用 `hermes`、`codex`、`claude` 时，repo 元数据仍可能按照对应工具的账号、隐私和数据策略发送到它们的后端；
- 如果设置 `include_readme = true`，会把更多 repo 内容发送给 AI CLI，同时运行速度也会明显变慢；
- 如果你的 Stars 暴露了私人研究方向，不要把 `.cache/`、`.work/`、生成笔记提交到公开仓库。

## 安装要求

- Python `>= 3.11`
- GitHub 访问方式二选一：
  - 设置 `GH_TOKEN` 或自定义 token 环境变量；
  - 已经登录 `gh` CLI：`gh auth login`
- 可选 AI CLI：
  - `hermes`
  - `codex`
  - `claude`

如果只想测试流程，可以使用 `none` agent，不需要安装 AI CLI。

## 安装

```bash
git clone https://github.com/ghosTM55/stars-to-kbs.git
cd stars-to-kbs
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

验证命令是否可用：

```bash
stars-to-kbs --help
```

如果使用 `gh` 读取 token，先确认：

```bash
gh auth status
```

## 配置

初始化本地配置：

```bash
stars-to-kbs init
```

默认会创建：

```text
$HOME/.config/stars-to-kbs/config.toml
```

运行前需要编辑这个文件。

示例：

```toml
[github]
username = "YOUR_GITHUB_USERNAME"
token_env = "GH_TOKEN"
include_readme = false
max_repos = 0

[agent]
provider = "hermes"
batch_size = 50
language = "zh-CN"

[kbs]
path = "/absolute/path/to/your/Obsidian/Personal Notes"

[output]
cache_dir = ".cache"
work_dir = ".work"
```

### 配置项说明

| 配置项 | 含义 |
| --- | --- |
| `github.username` | 要拉取 Stars 的 GitHub 用户名。留空时使用当前认证用户。 |
| `github.token_env` | 保存 GitHub token 的环境变量名，默认 `GH_TOKEN`。 |
| `github.include_readme` | 是否拉取 README 摘要。总结质量可能更好，但更慢，也会发送更多文本给 AI CLI。 |
| `github.max_repos` | 最多处理多少个 repo。`0` 表示全部。测试时可以设为 20。 |
| `agent.provider` | AI 处理工具，可选 `hermes`、`codex`、`claude`、`none`。 |
| `agent.batch_size` | 每批交给 AI CLI 的 repo 数量。越大越省调用次数，但更容易超上下文或影响质量。 |
| `agent.language` | 希望 AI 输出的语言。默认 `zh-CN`。 |
| `kbs.path` | 个人知识库目录或最终 Markdown 文件路径。若是目录，会在其中生成 `GitHub Stars Index.md`。 |
| `output.cache_dir` | 本地缓存目录，默认 `.cache`，不应提交。 |
| `output.work_dir` | 本地工作目录，默认 `.work`，存放 prompt 和 agent 输出，不应提交。 |

也可以手动指定配置文件：

```bash
stars-to-kbs --config /path/to/config.toml run
```

## 快速开始

建议先跑小规模测试：

```bash
stars-to-kbs run --agent none --max-repos 20
```

确认路径和输出格式没问题后，再用 AI CLI：

```bash
stars-to-kbs run --agent hermes --max-repos 20
```

最后处理全部 Stars：

```bash
stars-to-kbs run --agent hermes
```

## 命令说明

```bash
stars-to-kbs init
stars-to-kbs fetch
stars-to-kbs summarize --agent hermes
stars-to-kbs merge --agent hermes
stars-to-kbs validate
stars-to-kbs write-note
stars-to-kbs run --agent hermes
```

### `init`

从 `config.example.toml` 创建本地配置文件。

```bash
stars-to-kbs init
stars-to-kbs init --force
```

### `fetch`

拉取 GitHub Stars，写入缓存。

```bash
stars-to-kbs fetch
stars-to-kbs fetch --max-repos 50
stars-to-kbs fetch --with-readme
```

### `summarize`

读取缓存，根据 `batch_size` 分批调用 AI CLI。

```bash
stars-to-kbs summarize --agent hermes
stars-to-kbs summarize --agent codex --batch-size 50
stars-to-kbs summarize --agent none
```

当前输出文件：

```text
.work/batch-summaries.md
```

可以使用 `--resume` 复用已有的非空 `.work/batch-XXX.summary.md` 文件。

### `merge`

把多个 batch summary 合并成一个全局 taxonomy，并写出最终 summary。

```bash
stars-to-kbs merge --agent hermes
stars-to-kbs merge --agent codex --resume
```

当前输出文件：

```text
.work/combined-summary.md
```

### `validate`

检查最终 summary 中是否每个 fetched repo 都作为 `#### owner/repo` 标题出现且只出现一次。

```bash
stars-to-kbs validate
```

### `write-note`

把校验后的 summary 写入配置中的 KBS 路径。

```bash
stars-to-kbs write-note
```

### `run`

依次执行：

```text
fetch -> summarize -> merge -> validate -> write-note
```

示例：

```bash
stars-to-kbs run --agent hermes
stars-to-kbs run --agent none --max-repos 20
```

## 支持的 Agent

| Provider | 命令形式 | 说明 |
| --- | --- | --- |
| `hermes` | `hermes chat -Q -q <prompt>` | 使用 Hermes quiet mode，捕获 stdout。 |
| `codex` | `codex exec --skip-git-repo-check -o <file> <prompt>` | 支持输出到文件。 |
| `claude` | `claude -p <prompt>` | 捕获 stdout。 |
| `none` | 不调用 subprocess | 离线 / 测试用的确定性 fallback。 |

本项目假设这些 CLI 已经由用户自行安装并登录，不负责安装或配置它们。

## 输出格式

生成的笔记包含 frontmatter 和正文，例如：

```markdown
---
title: GitHub Stars Index
type: github-stars-index
...
---

# GitHub Stars Index

## 概览

## 分类目录

### AI / Agents

#### owner/repo
- GitHub 链接：https://github.com/owner/repo
- stars：12345
- 一句话总结：...
- 为什么值得关注：...
- 适合用途：...
```

每个 repo 条目预期只包含：

- GitHub 链接；
- stars；
- 一句话总结；
- 为什么值得关注；
- 适合用途。

Prompt 会要求 AI 不要在每个条目里输出语言、`starred_at` 或标签。

## 大量 Stars 的建议

GitHub API 每页最多拉取 100 个 starred repositories。本工具会自动分页，直到拉完或达到 `max_repos`。

建议：

- 先用 `--max-repos 20` 测试；
- 大规模 Stars 默认关闭 `include_readme`；
- 400+ Stars 建议从 `batch_size = 50` 开始；
- 使用 `--resume` 在失败后复用已有的非空 batch 或 merged 输出；
- 如果某个 batch 失败，查看 `.work/batch-XXX.prompt.md` 和 `.work/batch-XXX.summary.md`；
- 如果 validate 失败，检查 `.work/combined-summary.md`；校验器会打印 missing、extra 和 duplicate repo headings。

## 常见问题

### `Config already exists`

`stars-to-kbs init` 默认不会覆盖已有配置。需要覆盖时使用：

```bash
stars-to-kbs init --force
```

### GitHub 认证失败

设置 token：

```bash
export GH_TOKEN=...
```

或者登录 GitHub CLI：

```bash
gh auth login
gh auth status
```

### 找不到 Agent 命令

先确认你安装并登录了对应 CLI。也可以先不用 AI 跑 smoke test：

```bash
stars-to-kbs run --agent none --max-repos 20
```

### validate 失败

最终 `validate` 会把 cache 里的 repository `full_name` 和 `.work/combined-summary.md` 里的 `#### owner/repo` 标题做对比。如果出现 missing、extra 或 duplicate，可以重跑 merge，降低 `batch_size`，或手动检查 merged summary：

```bash
stars-to-kbs merge --agent hermes
stars-to-kbs validate
```

### 笔记写到了错误位置

检查配置：

```toml
[kbs]
path = "/absolute/path/to/your/notes"
```

如果 `path` 是目录，最终文件会是：

```text
GitHub Stars Index.md
```

## 开发

安装开发依赖：

```bash
pip install -e '.[dev]'
```

运行测试和 lint：

```bash
python -m pytest -q
ruff check .
```

构建：

```bash
python -m build
```

提交前检查不要包含私有数据：

```bash
git status --short
git diff --cached
```

## Roadmap

优先级较高的改进：

- 为超大规模 Stars 增加 hierarchical merge，避免最终 merge prompt 过长；
- 增加 prompt size 估算和自动 batch-size 建议；
- 为临时 GitHub / 网络错误增加更完整的 retry/backoff；
- 增加可选过滤条件，例如 archived repos、forks、最低 stars；
- 发布正式 release，简化安装流程。

## License

MIT
