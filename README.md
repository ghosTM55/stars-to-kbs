# stars-to-kbs

把 GitHub Stars 自动整理成个人知识库 Markdown 笔记。

`stars-to-kbs` 会拉取你的 starred repositories，调用本机已登录的 AI CLI（Hermes / Codex / Claude）做分类和总结，然后写入 Obsidian 或其他 KBS 目录。

[English](README.en.md)

## 特点

- GitHub Stars 自动分页拉取
- 支持 `hermes` / `codex` / `claude` / `none`
- 不直接集成 LLM API Key
- 配置文件放在用户目录，适合公开仓库
- 分批总结 + 全局合并 + 完整性校验
- 输出 Obsidian-friendly Markdown

## 安装

```bash
git clone https://github.com/ghosTM55/stars-to-kbs.git
cd stars-to-kbs
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

要求：

- Python `>= 3.11`
- GitHub token，或已登录的 `gh` CLI
- 可选 AI CLI：`hermes`、`codex`、`claude`

## 配置

初始化配置：

```bash
stars-to-kbs init
```

默认配置文件：

```text
~/.config/stars-to-kbs/config.toml
```

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
path = "/absolute/path/to/your/notes"

[output]
cache_dir = ".cache"
work_dir = ".work"
```

说明：

| 配置项 | 说明 |
| --- | --- |
| `github.username` | GitHub 用户名；留空时使用当前认证用户 |
| `github.token_env` | token 环境变量名，默认 `GH_TOKEN` |
| `github.include_readme` | 是否拉取 README 摘要；更慢，也会发送更多文本给 AI CLI |
| `github.max_repos` | 最多处理多少 repo；`0` 表示全部 |
| `agent.provider` | `hermes` / `codex` / `claude` / `none` |
| `agent.batch_size` | 每批交给 AI CLI 的 repo 数量 |
| `agent.language` | 输出语言 |
| `kbs.path` | KBS 目录或最终 Markdown 文件路径 |

## 使用

先跑小样本：

```bash
stars-to-kbs run --agent none --max-repos 20
stars-to-kbs run --agent hermes --max-repos 20
```

全量运行：

```bash
stars-to-kbs run --agent hermes
```

失败后复用已有 batch 输出：

```bash
stars-to-kbs run --agent hermes --resume
```

## 命令

```bash
stars-to-kbs fetch
stars-to-kbs summarize --agent hermes
stars-to-kbs merge --agent hermes
stars-to-kbs validate
stars-to-kbs write-note
```

完整流程：

```text
fetch -> summarize -> merge -> validate -> write-note
```

输出文件：

| 阶段 | 文件 |
| --- | --- |
| fetch | `.cache/starred.json` |
| summarize | `.work/batch-summaries.md` |
| merge | `.work/combined-summary.md` |
| write-note | `<kbs.path>/GitHub Stars Index.md` |

## 大量 Stars

GitHub API 每页拉取 100 个 starred repositories。总结阶段按 `batch_size` 分批，再由 `merge` 阶段做全局分类合并。

推荐：

```toml
[agent]
batch_size = 50

[github]
include_readme = false
```

`validate` 会检查最终 Markdown 是否包含所有 repo，并报告：

- missing repositories
- unexpected repositories
- duplicate repositories

## 隐私

默认不会把本地配置和输出提交到 Git。

不要提交：

- `.env`
- `config.toml`
- `.cache/`
- `.work/`
- `output/`

注意：本项目不直接保存 LLM API Key，但使用 `hermes` / `codex` / `claude` 时，repo 元数据仍可能发送到对应工具的后端。

## 开发

```bash
python -m pytest -q
ruff check .
python -m build
```

## License

MIT
