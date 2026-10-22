# 一句话需求 → 命令 示例

本文件给 AI（以及人类）示范：用户用自然语言提的需求，如何映射到 `scripts/weread.py` 的命令。

> 约定：`python` = Python ≥ 3.11；命令都在仓库根目录执行。
> 真实数据需要先在 `.env` 里配置 `WEREAD_API_KEY=wrk-...`。

## 类别 1：先看效果（无需 Key、无需联网）

| 用户原话 | 执行的命令 |
|---|---|
| "先来个 demo 看看能做成啥样" | `python scripts/weread.py sample` |
| "没有 Key，能跑吗" | `python scripts/weread.py sample` |
| "给我看个示例档案" | `python scripts/weread.py sample` |

产物：`site/index.html`（合成数据，可浏览器直接打开）。

## 类别 2：用我的真实数据做可视化档案

| 用户原话 | 执行的命令 |
|---|---|
| "可视化我的微信读书阅读数据" | `sync` → `build-public` |
| "做个阅读热力图 / 阅读节律" | `sync` → `build-public` |
| "我的类别偏好 / 年度透镜 / 知识图谱" | `sync` → `build-public` |
| "把我的书架生成个可浏览的档案" | `sync` → `build-public` |

步骤：
```
python scripts/weread.py sync
python scripts/weread.py build-public
```
产物：`site/index.html`。

## 类别 3：引用卡 / 私人实验室

| 用户原话 | 执行的命令 |
|---|---|
| "把我的划线做成名言卡 / 引用卡" | `sync` → `build-private --include-private --with-text` |
| "帮我本地搜索我的读书笔记" | `sync` → `build-private --include-private --with-text` |
| "做个私人阅读实验室" | `sync` → `build-private --include-private --with-text` |

产物：`$WEREAD_DATA_DIR/analysis/private_lab/index.html`。

## 类别 4：全都要

| 用户原话 | 执行的命令 |
|---|---|
| "完整跑一遍，档案和实验室都要" | `python scripts/weread.py all --include-private --with-text` |

## 类别 5：配置与自检

| 用户原话 | 执行的命令 |
|---|---|
| "先检查一下环境" | `python scripts/weread.py doctor` |
| "我 Key 填好了吗 / 为什么跑不了" | `python scripts/weread.py doctor --require-key` |
| "初始化一下项目" | `python scripts/weread.py setup` |

## 隐私红线（AI 也要遵守）
- 默认不发布私密书、不发布划线/想法正文、不发布本地搜索索引。
- 真实数据在仓库外的 `WEREAD_DATA_DIR`，不要提交进仓库。
- 没有 Key 时，实时类功能（Advisor / Reading Path）应明确告知无法运行，而非编造结果。
