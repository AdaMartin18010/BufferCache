# AGENTS.md — BufferCache 项目协作者指南

> 本文件是人与 AI 协作者（agent）在本项目中的**持久化工作约定**。任何会话开始工作时先读本文件与 [docs/00-项目总览/STATUS.md](docs/00-项目总览/STATUS.md)；**执行轨代理（hermes）另读 [Testing/hermes-queue.md](Testing/hermes-queue.md) 取当前工作项**，规划轨读 [测试与验证执行计划](Testing/测试与验证执行计划.md) §7/§8；本文件描述与项目实际状态冲突时，以实际目录与 STATUS.md 为准并修正本文件。

## 1. 项目定位

BufferCache 是**中文文档型知识体系项目**（非代码库）：系统分析 Buffer Cache 算法、Redis 原理与缓存架构，从硬件到算法、从理论到工程。
约 25 万字、250 篇文档，五层知识体系 + 运维/分布式扩展。

- 读者：学生、开发者、架构师、研究者
- 语言：正文中文；论文引用、命令、代码保持原文
- 许可证：MIT（内容），引用的算法与数据各有出处

## 2. 目录结构与导航

```text
docs/
├── 00-项目总览/          导航 + 概念体系 + 思维表征 + 质量机制
│   ├── (archive/ 已于 2026-11 正式删除，历史保留在 git 历史)
│   ├── STATUS.md         ★ 项目状态唯一权威来源
│   └── 公式-文献对照表.md ★ 全部数学公式唯一权威索引
├── 01-理论基础/          01.01 基础算法 / 01.02 高级算法 / 01.03 分布式算法
│                         / 01.04 学习驱动算法 / 01.05 对比·证明·TLA+
├── 02-系统实现/          02.01 OS缓存 / 02.02 CPU缓存 / 02.03 数据库(含云DB)
│                         / 02.04 现代内核与新存储栈 / 02.05 系统级优化 / 02.06 程序设计
├── 03-Redis组件/         03.01 数据结构 / 03.02 持久化 / 03.03 高可用 / 03.04 内存
│                         / 03.05 版本演进与开源生态 / 03.06 网络 / 03.07 源码
├── 04-架构设计/          04.01 模式 / 04.02 缓存安全 / 04.03 行业场景(含LLM KV Cache)
│                         / 04.04 问题治理 / 04.05 成本 / 04.06 工具 / 04.07 案例
├── 05-全栈分析/          硬件→网络→控制流→数据流→算法→动态特征→瓶颈
├── 06-扩展计划/          总计划 + 国际前沿对齐与质量治理执行计划
├── 07-运维与部署/        部署/CI-CD/监控/故障/集群/可观测/自动化/多租户
│                         /弹性伸缩与自愈(07.09)
├── 08-分布式架构/        一致性/事务/协调/限流/配置
├── ARCHIVE.md            归档说明
└── INDEX.md              主索引（人与 agent 的入口）
scripts/
├── code_test_framework.py 文档代码块测试（Python/Go/Rust/Bash 已实现：Go/Rust 编译运行完整程序，Bash 语法检查）
├── benchmark/trace_benchmark.py  Trace 驱动算法基准（LRU/LFU/S3-FIFO）
└── formal/               TLA+ 规约（LRU/ARC 已通过 TLC）+ run.bat
reports/                  code_scan_report.md / code_test_report.md（实测数据）
AI_Skill/                 AI 协作技能库：SKILL.md 兼容格式，16 个技能（项目主题映射+国际前沿专项）
                          + 制作规范/模板/示例模型/用例/权威来源索引（季度评审对齐第三批）
Testing/                  测试与自我验证体系：cases/ 七组 36 用例（文档质量/形式化基准/运维部署/集群/集成）
                          + 08-能力矩阵/（维度化矩阵层：MX-A~MX-G 200 格，●/○四态适用矩阵，matrix_gen 对账门）
                          + self_verify.py 统一入口 26 检查项（全量 25 PASS + 1 SKIP 常态；验证→纠正→修正→回归→登记闭环）
                          + hermes-queue.md 执行工作队列（执行轨唯一入口，见 §4.0 协作宪章）
```

## 3. 文档规范（质量门禁，强制执行）

### 3.1 编号

- 子主题：`NN.MM-名称/`；文档：`NN.MM.SS-名称.md`（SS 在子主题内连续，允许历史空缺）
- 新建子主题优先填补空缺编号（当前空缺：03.05 已填、04.02 已填、01.04/02.04 已填）

### 3.2 新文档必须满足

1. **公式**：每个数学公式标注文献出处，或标注"推导自 XXX"；完成后登记 [公式-文献对照表](docs/00-项目总览/公式-文献对照表.md)（A=文献直接来源 / B=可复核推导 / C=项目经验模型）
2. **代码**：示例应可被 `code_test_framework.py` 提取；教学片段在文档中显式声明"函数级教学片段"
3. **链接**：相对路径必须真实存在；新文档必须挂入所属子目录 README 与 docs/INDEX.md
4. **参考**：论文含会议/年份；在线资源含 URL；不编造文献（不确定的出处宁可不写）
5. **结构**：沿用项目模板（概述 → 核心原理 → 实现/机制 → 性能分析 → 场景 → 扩展阅读 → 权威参考）

### 3.3 语言标注

代码块语言标注必须真实：Prometheus 查询用 `promql`、配置文件用 `ini`/`yaml`、伪代码用 `text`。禁止把非 Python 内容标为 `python`（历史上有过 4 处，已修）。

## 4. 工作方式与禁令

### 4.0 协作宪章（Kimi 主控 / hermes 执行 / 用户裁决，2026-11-21 用户裁定）

**角色三分**：主控（Kimi/AI 协作者）=规划/测试用例/治理工具/台账/审计，**不执行实跑**（越权须报用户裁决，A1 先例）；hermes（执行代理）=按工作队列自治执行实跑类任务，不改规划层文件，不自行扩队列；用户=裁决与背书，**不指定单项任务**（队列自驱动）。

**入口流**：任何代理开工——① 本文件 + STATUS.md；② 执行轨读 `Testing/hermes-queue.md` 取当前项；③ 规划轨读 `测试与验证执行计划.md` §7/§8；④ 容器类任务先按容器运行时适配规范 §1 探测锁定运行时。

**文件所有权矩阵（互斥铁律）**：

| 文件/区域 | 唯一写者 |
| ---- | ---- |
| docs/ 正文、AGENTS.md、STATUS.md、执行计划、测试框架规范、用例全景统计、08-能力矩阵规划层（README/维度定义/适用矩阵/模板/matrix_gen.py）、cases 用例文件（结构与判据节）、self_verify.py | 主控 |
| matrix-registry.tsv 的 status/note 列、cases 用例文件的"## 执行记录"节（追加式） | hermes |
| Testing/output/ 与一切实跑产物、基准基线 | hermes |
| reports/ | self_verify 运行自然刷新，提交方负责带上 |

共同底账 = git；同时刻同文件冲突以 git 为准；计划性冲突（主控规划到 hermes 正在执行的区域）由主控避让。

**工作队列协议**：唯一执行入口 = `Testing/hermes-queue.md`；新任务由主控规划入队。队列项自治级：**A**=全自治（执行+回填+简报）；**P**=执行后须主控审计再入库；**U**=用户门（破坏性/长耗时/正文内容变更）。hermes 完成一项 = 产物落 Testing/output/ + 执行记录节回填 + registry status 流转 + 简报；主控抽审 1/3 可回放。hermes 发现计划外工作 → 队列"观察区"登记，主控裁定后入队，不得自行执行。

**执行三件套（每项必做）**：①产物落 `Testing/output/`（gitignore 证据）②用例文件"## 执行记录"节追加（时间/命令/关键值/判定）③`matrix-registry.tsv` status 列流转（seed/gen→done）。环境值一律从 `Testing/fixtures/lab.env` 取（单一事实源），禁止用例内扩散硬编码。

**执行契约**：开工=source lab.env→运行时探测（容器适配规范 §1）→`self_verify all` 基线绿→按队列执行入口映射取件；FAIL 走用例修正指引、环境缺 SKIP 登记观察区、**禁止伪造通过**；SKIP 格环境解锁后由主控改派。

**并行规则**：两轨常并行（主控规划/审计新批 ∥ hermes 执行已入队批）；hermes 轨内独立文件域可并行（B1/B2/B3 内容批），共享环境/端口项串行（A2→A3→A4 因 6379 时段避让），同一文件唯一写者；任何一轨提交前 L1（self_verify）预跑绿，CI 为共同门禁。

**汇报**：hermes 每队列项简报（做了什么/结果/产物路径/下一步）；主控并入用例全景统计 §6/§7 + STATUS 变更记录。

### 4.1 状态与计划

- 项目状态以 [STATUS.md](docs/00-项目总览/STATUS.md) 为唯一权威来源；历史过程性报告已于 2026-11 正式删除（git 历史可查）
- 任务与进度以 [国际前沿对齐与质量治理执行计划](docs/06-扩展计划/国际前沿对齐与质量治理执行计划.md) 为准（P0/P1/第一批/第二批已完成，第三批开放）

### 4.2 禁令（历史教训固化）

1. **禁止新建"完成确认书/最终报告/100%完成"类元文档**——进度一律更新 STATUS.md
2. ~~禁止移动或修改 `archive/` 内文档~~（2026-11 解除：archive 已按维护者决定正式删除，git 历史保留；链接检查对 archive 的排除规则保留为防御）
3. **禁止编造数学公式**——无出处公式一律先查文献；查不到按 C 级登记并声明假设
4. **禁止在 Windows 环境运行依赖 Linux 的示例而不加平台守卫**（`sys.platform` 检查 + 演示退出）
5. **禁止提交测试运行产物**（遵循 [.gitignore](.gitignore)：TLC states/、TTrace、**pycache**、临时输出）

### 4.3 完成定义（DoD）

一个任务只有在以下全部满足时才可标记完成：标准验证命令通过（见 §5）、用户原始场景端到端成立、导航（README/INDEX/子 README）已同步、报告类文件已更新、无新增未声明的临时文件。

## 5. 工具链与验证命令

```bash
# 0. 统一自我验证入口（首选，聚合 1-4 + 结构与运维检查；失败给用例修正指引）
python Testing/self_verify.py all          # 全量；--ci 模式失败非零退出
python Testing/self_verify.py links --path AI_Skill   # 新技能提交前的链接自查

# 1. 文档代码块测试（Python 全量约 1 分钟，目标：0 失败）
python scripts/code_test_framework.py --test python

# 1b. 多语言代码块测试（Go/Rust 编译运行完整程序；Bash 仅语法检查 -- 平台守卫）
python scripts/code_test_framework.py --test go     # 报告 code_test_report_go.md
python scripts/code_test_framework.py --test rust   # 报告 code_test_report_rust.md
python scripts/code_test_framework.py --test bash   # 报告 code_test_report_bash.md

# 2. TLA+ 模型检查（Windows 直接运行；Linux/macOS 用 jar 命令）
scripts/formal/run.bat

# 3. Trace 驱动算法基准（合成 trace，约 10 秒；--trace 支持公开 CSV 格式嗅探加载）
python scripts/benchmark/trace_benchmark.py

# 3b. 一致性/容量工具（C6/D8 可执行验证）
python scripts/consistency_check.py        # Cache-Aside 并发不一致窗口三策略对比
python scripts/capacity_calculator.py      # 容量与成本估算（C 级参数，压测校准）
python scripts/assertion_check.py        # 技能-正文一致性巡检（事实断言清单驱动）
python scripts/benchmark/suite/bench_suite.py  # 场景化基准套件+回归检测（TC-BENCH-005）

# 4. 链接自查（新文档提交前）
#    用脚本检查新文档内全部 .md 相对链接可解析（参照历次验证做法）
python Testing/self_verify.py links --path <目录>

# 5. 文档统计口径
find docs -name "*.md" -not -path "*/archive/*" | wc -l   # 当前 259（含 STATUS 等）

# 依赖：requirements.txt 锁定（requests/PyYAML）；文档构建依赖 requirements-dev.txt（mkdocs）
```

## 6. 当前进度（截至 2026-01，详见 STATUS.md）

- **已完成**：P0 质量治理（元文档收敛/公式审计/代码测试 100%/结构修复）、P1 前沿对齐（LLM KV Cache/学习驱动算法/现代内核/Redis 8 生态/缓存安全/理论深化 7 项）、第一批深化（TLA+ 可执行化/代码块清零/公式对照表/KV 实验）、第二批广度（S3-FIFO/SIEVE、新存储栈、云数据库缓存、trace 基准）
- **第三批开放**：季度前沿评审机制化、Go/Rust/Bash 代码测试、英文 README、Coq/Isabelle 机械化证明、LLM 推理部署实践篇（04.03.15 补充）

## 7. 变更同步义务

对项目做出以下变更后，必须同步更新对应文件（"达成一致"的维护责任）：

| 变更 | 必须同步更新 |
| ---- | ------------ |
| 新增/移动/重命名文档 | 所属子目录 README.md、docs/INDEX.md（正文与目录区）、必要时 STATUS.md 计数 |
| 新增数学公式 | 公式-文献对照表.md + 所在文档出处标注 |
| 新增/归档文档 | STATUS.md（状态/计数/变更记录）、ARCHIVE.md（归档时） |
| 工作队列项增删/状态流转 | Testing/hermes-queue.md（执行轨唯一入口） |
| 实验室环境值变更（运行时/镜像/密码/端口/容器名） | Testing/fixtures/lab.env（单一事实源）+ 用例全景统计 §8 快照 + STATUS 变更记录 |
| 新增脚本/工具 | scripts 相关 README、§5 工具链、code_test_framework 兼容性 |
| 批次任务完成 | 国际前沿对齐与质量治理执行计划.md（结果列） |
| 目录结构变化 | 本文件 §2、根 README 结构图 |
| 质量规范变化 | 本文件 §3/§4、[文档质量标准](docs/00-项目总览/文档质量标准.md) |

## 8. 变更记录

- **2026-11**：建立 AI_Skill/（16 个 SKILL.md 兼容技能 + 规范/模板/示例/用例/权威来源索引）与 Testing/（五组 15 用例 + self_verify.py 统一入口，验证→纠正→修正→回归→登记闭环）；self_verify 上线时全库链接体检并纠正存量死链 65 处（导航层级错误与旧文件名遗留）；2026-11 archive 正式删除；版本事实季度对齐（Redis 8.10、Valkey 9.1.3、Linux 7.2、vLLM-Mooncake 集成）登记于 AI_Skill 权威来源索引。
- **2026-01**：建立本文件。固化 2026-01 全面分析与四批执行形成的规范、工具链、禁令与进度。
