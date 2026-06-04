<p align="center">
  <img src="assets/logo.svg" alt="Quorum" width="160" />
</p>

<h1 align="center">Quorum</h1>

<p align="center">
  <strong>你的开源咨询事务所。任何市场，任何行业，几分钟交付。</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/EvanSnowdon/quorum/actions/workflows/ci.yml"><img src="https://github.com/EvanSnowdon/quorum/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

---

Quorum 把世界知名战略思想家的公开方法论封装为智能体技能，再把它们组建成一家多智能体咨询事务所。输入任意地区与行业，产出一份有据可查、经过事实核查的咨询级市场报告。

项目分为两层：

- **第一层：技能库（Skills Library）。** 15 个独立的方法论分析师（波特五力、JTBD、7 Powers、Playing to Win 等），以纯文本 `SKILL.md` 形式打包。可一键安装到 Claude Code、Codex、Gemini CLI 等任何兼容 skills 的智能体中，单独使用。
- **第二层：事务所（The Firm）。** 多智能体咨询引擎。指定 `region × industry × depth`，项目经理拆解任务，并行调度方法论专家团队，以官方统计数据为脊柱，每份草稿都要通过事实核查、红队、主编三道质量关，最终报告落盘交付。

## 为什么选择 Quorum

商业研究机构的一份分析师级市场报告通常售价 **$800–$2,850**，采购周期以天计。同等覆盖范围的 Quorum 项目只需约 **$4 的模型 token 成本**，几分钟完成——且每条结论都有标注、有来源、可审计。

| | 商业报告 | Quorum |
|---|---|---|
| 价格 | 每份 $800–$2,850 | 约 $4 token 成本（standard 深度） |
| 周期 | 数天到数周 | 数分钟 |
| 覆盖 | 受限于目录 | 任意地区 × 任意行业 |
| 方法论 | 黑箱 | 开放可审查的 SKILL.md |
| 数据来源 | 信任品牌 | 官方统计优先，每条结论标注 `[DATA]` 或 `[INFERENCE]` 及置信度 |
| 定制 | 不可 | MIT 协议，随便 fork |

Quorum 不能替代付费专家网络和人类判断（见[诚实的局限](#诚实的局限)），但它可以替代那条「定价过高、来源不明的市场综述」长尾。

## 快速开始

### 模式一：仅安装技能

```bash
npx skills add EvanSnowdon/quorum
```

或在 Claude Code 内：

```
/plugin marketplace add EvanSnowdon/quorum
```

之后直接调用任一分析师，例如让智能体「对欧洲电池回收市场做一次五力分析」，`five-forces-analyst` 技能会接管结构、证据标准与输出格式。

### 模式二：完整事务所

```bash
git clone https://github.com/EvanSnowdon/quorum.git
cd quorum
pip install -e .

export ANTHROPIC_API_KEY=sk-...   # 或 OPENAI_API_KEY，或指向本地模型

quorum --region CN --industry "electric vehicles" --depth standard
```

完整项目跑完后，报告包写入 `engagements/<timestamp>-cn-electric-vehicles/`，包含最终报告、各专家工作底稿、数据来源台账与质量关审查记录。

### 模型自选

Quorum 模型无关，每次运行都可指定任意供应商与模型：

```bash
# Anthropic（默认）
export ANTHROPIC_API_KEY=sk-ant-...
quorum --region CN --industry "electric vehicles"

# OpenAI
export OPENAI_API_KEY=sk-...
quorum --region CN --industry "electric vehicles" --provider openai --model gpt-4o

# DeepSeek、Qwen、Kimi、vLLM —— 任意 OpenAI 兼容 API
export OPENAI_API_KEY=<你的供应商key>
quorum --region CN --industry "electric vehicles" \
  --provider openai --base-url https://api.deepseek.com --model deepseek-chat

# 完全本地（Ollama）—— 免费，数据不出本机
export OPENAI_API_KEY=ollama   # 任意非空值即可，本地服务不校验
quorum --region CN --industry "electric vehicles" \
  --provider openai --base-url http://localhost:11434/v1 --model qwen3
```

用 `--lead-model` / `--worker-model` 可拆分角色——编排/红队/主编用强模型，并行分析师用便宜的快模型。同名环境变量（`QUORUM_PROVIDER`、`QUORUM_MODEL`、`QUORUM_LEAD_MODEL`、`QUORUM_WORKER_MODEL`、`QUORUM_BASE_URL`）或 `.env` 亦可配置；命令行参数优先。

## 功能特性

| 特性 | 说明 |
|---|---|
| 15 个方法论分析师 | 经典战略框架的可移植、可审计技能化 |
| 并行专家团队 | orchestrator-worker 架构，专家并发执行，任务契约明确 |
| 官方数据脊柱 | 优先查询官方统计 API；网络来源补缺口，不替代一手数据 |
| 结论标注 | 每条结论标 `[DATA]`（有来源）或 `[INFERENCE]`（推理所得）及置信度 |
| 三道质量关 | 事实核查、红队、主编逐一过审 |
| 深度分档 | `scan` / `standard` / `due_diligence`，算力随风险等级伸缩 |
| 项目记忆 | 历史项目以 markdown-in-git 持久化，事务所越用越懂你的市场 |
| 模型无关 | Anthropic、OpenAI 或任意 OpenAI 兼容本地端点 |
| 国家信源包 | 按国家组织的官方统计信源 YAML 包，社区可扩展 |

## 架构

```
        quorum CLI（region × industry × depth）
                       │
              项目经理（编排：scoping / MECE 拆解 / 任务契约）
                       │
        ┌──────────────┼──────────────┐
   专家 Worker 1   专家 Worker 2   专家 Worker N（并行）
        └──────┬───────┴───────┬──────┘
               │               │
          数据脊柱          记忆层
     （官方统计 API，    （markdown-in-git，
   [DATA]/[INFERENCE]）    历史项目沉淀）
               │
        三道质量关：事实核查 → 红队 → 主编
               │
        engagements/<id>/（报告 + 底稿 + 来源台账）
```

完整工程设计见 [docs/architecture.md](docs/architecture.md)（英文）。

## 技能库

15 个分析师，每个都是一份独立 `SKILL.md`，编码该方法论的核心问题、证据标准、常见失效模式与输出结构：

`five-forces-analyst` · `value-chain-analyst` · `jtbd-disruption-analyst` · `seven-powers-analyst` · `good-strategy-critic` · `playing-to-win-analyst` · `blue-ocean-analyst` · `crossing-the-chasm-analyst` · `pestel-analyst` · `tam-sam-som-analyst` · `ansoff-analyst` · `three-horizons-analyst` · `pyramid-editor` · `valuation-analyst` · `mece-engagement-manager`

每个技能均附 `DISCLAIMER`，声明其编码的是该方法论已公开发表的形式，不包含原作者或其所属机构的专有内容。

## 开源版 vs 云版

Quorum 采用 open-core 模式。本仓库内的一切——技能库、咨询引擎、质量关、信源包——永久 MIT 开源、可自托管。带团队工作区、定时项目与托管数据连接器的云版本在规划中，见 [docs/roadmap.md](docs/roadmap.md)。开源核心内的功能不会被移入云版。

## 诚实的局限

- **不含专有内容。** Quorum 编码的是各方法论*已公开发表*的形式，不会复制付费报告、专有数据库或专家访谈内容。
- **不替代人类判断。** 报告是决策输入，不是决策本身。高风险决策需要一个为结果负责的人。
- **数据质量取决于脊柱。** 官方统计越开放、越机器可读的地区，覆盖越强。缺口会被明确标出，不会被掩盖。
- **推理之所以要标注，是因为推理可能出错。** `[INFERENCE]` 标签的存在，就是让你知道该重点质疑哪些结论。

Quorum 真正的优势在于：公开信息的广度、任何分析师团队都比不了的地理覆盖、分钟级速度、低两个数量级的成本，以及每条结论推导过程的完全透明。

## 参与贡献

最高杠杆的两条贡献路径：

1. **新方法论技能。** 技能格式就是带一小段 frontmatter 的纯 markdown，不需要写 Python。
2. **新国家信源包。** 为尚未覆盖的国家整理官方统计信源，一个 YAML 文件即可把事务所的能力扩展到一整个经济体。

两条路径的分步指南见 [CONTRIBUTING.md](CONTRIBUTING.md)（英文）。我们承诺所有 PR 与 issue 在 48 小时内首次响应。

## 许可证

MIT，见 [LICENSE](LICENSE)。
