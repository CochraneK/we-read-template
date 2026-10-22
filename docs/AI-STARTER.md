# WeRead Intelligence — AI 入口（一句话 + API Key 即可出图）

本文件是给 **任意 AI 助手** 的操作手册。用户把本仓库克隆到本地，再给你（AI）一句话目标和一个 WeRead API Key，你就按下面流程把整套本地优先的阅读智能流水线跑起来，产出可视化页面。

> 如果你用的是 WorkBuddy：把本文件复制/软链到 `.workbuddy/skills/weread-starter/SKILL.md` 即可被自动发现；下面的内容就是那份 Skill 的正文。本文件放在 `docs/` 之下，是为了让模板保持「不跟踪任何 `.workbuddy/` 内容」的隐私红线（CI 会校验）。

## 项目结构（必读）
- 入口：`scripts/weread.py`（零依赖 CLI 编排器），所有命令都从这里走。
- 真实数据目录：`WEREAD_DATA_DIR`（默认 `~/.local/share/we-read`），**永远在仓库外、不提交**。
- 配置：仓库根 `.env`（由 `.env.example` 复制而来），脚本启动时会自动 load。
- 公开档案产物：`site/index.html`（热力图 / 节律 / 类别偏好 / 知识图谱 / 书架探索 / 盲点阅读等）。
- 私有实验室产物：`$WEREAD_DATA_DIR/analysis/private_lab/index.html`（本地搜索 / 复习 / 引用卡 / Alchemy / 叙事回顾等）。

## 先决条件
- Python ≥ 3.11。
- 仓库根目录能找到 `scripts/weread.py`。如果当前不在仓库根，先切到仓库根。
- 真实数据需要 `WEREAD_API_KEY`（格式以 `wrk-` 开头）。没有 Key 也能跑**合成数据 demo**。

## 操作流程（按用户意图分支）

### A. 用户只想先看效果 / 没给 Key → 合成 demo（无需 Key、无需联网）
```
python scripts/weread.py sample
```
产物：`site/index.html`。告诉用户用浏览器打开它即可看到完整可视化（合成数据）。

### B. 用户给了一个 WeRead API Key，想要自己的数据
1. 把 Key 写进 `.env`（没有就先从 `.env.example` 复制）：确保 `.env` 里有 `WEREAD_API_KEY=wrk-xxxx`。可跑 `python scripts/weread.py setup` 生成 `.env` 骨架，再把 Key 填进去；或由你负责把用户给的 Key 写进 `.env`。
2. 拉取真实数据：
```
python scripts/weread.py sync
```
（会清空 notebooks 缓存后依次跑 fetch_shelf / export_notes / fetch_enrich；需要联网访问 WeRead Agent Gateway。）
3. 生成公开可视化档案：
```
python scripts/weread.py build-public
```
产物：`site/index.html`。
4.（可选）生成私有实验室（引用卡 / 搜索 / 复习 / Alchemy）：
```
python scripts/weread.py build-private --include-private --with-text
```
产物：`$WEREAD_DATA_DIR/analysis/private_lab/index.html`。

### C. 用户要「全部来一套」
```
python scripts/weread.py all --include-private --with-text
```
= sync + build-public + build-private。

### D. 先自检环境
```
python scripts/weread.py doctor
python scripts/weread.py doctor --require-key   # 强制要求 Key
```

## 一句话 → 命令 速查
- 「可视化我的阅读 / 做个阅读档案 / 热力图 / 类别偏好 / 知识图谱」 → **B**（sync + build-public）
- 「给我引用卡 / 名言卡 / 私人实验室 / 搜索我的笔记」 → **B** 的 `build-private --include-private --with-text`
- 「先来个 demo / 我还没 Key / 看看能做成啥样」 → **A**（sample）
- 「全都要 / 完整跑一遍」 → **C**（all）

更多自然语言示例见 [examples/nl-requests.md](../examples/nl-requests.md)。

## 隐私边界（必须遵守）
- 默认 `WEREAD_PAGES_INCLUDE_PRIVATE=0`：私密书排除、不发布划线正文、不发布你的想法正文、不发布本地搜索索引与私有实验室。
- 真实数据落在仓库外的 `WEREAD_DATA_DIR`，**不要**把它提交进仓库（仓库 `.gitignore` 已保护 `data/*` 与 `site/*`）。
- 绝不拿旧缓存伪装实时；没有 Key 时实时类功能（Advisor / Reading Path）要明确失败而不是骗用户。
- 远程写操作（改书架等）本模板不做；如未来要做，必须 plan-first + 显式确认。

## 交付给用户
- 跑完告诉用户产物路径（`site/index.html` 或私有实验室 html），并主动提出帮他用浏览器打开 / 起本地静态服务器预览。
- 如果命令失败：先读错误信息；常见是 Python 版本不够、Key 缺失或格式错（`wrk-` 开头）、数据未 sync。按 `doctor` 的输出逐项排查。

## 注意
- 运行命令时 cwd 应为仓库根；`scripts/weread.py` 内部用 `cwd=ROOT` 调用子脚本，所以从根目录调用即可。
- 基础 sync / build 仅用标准库；可选的语义文本挖掘按 README 的 `requirements-text-mining.txt` 安装，与基础可视化无关。
- 本指南是模板自带（template-owned），不是第三方 Skill 捆绑包；它只描述本仓库已有的命令，不引入外部依赖。
