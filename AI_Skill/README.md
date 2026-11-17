# AI_Skill — BufferCache 项目 AI 协作技能库

> 本目录是 BufferCache 知识体系面向 **AI 协作者（agent）与人** 的任务导向技能库。每个技能是一份 `SKILL.md`（SKILL.md 兼容格式：YAML frontmatter + Markdown 正文），把项目 `docs/` 的体系化知识转化为**可执行的协作能力**：何时使用、核心要点、权威速查、验证命令、前沿对齐。

## 1. 定位与边界

| 维度 | `docs/`（知识体系正文） | `AI_Skill/skills/`（本库） |
| ---- | ---------------------- | -------------------------- |
| 组织方式 | 主题编号体系（01-08），体系化、完整性优先 | 任务/场景导向，按需加载，速查优先 |
| 内容深度 | 完整原理、证明、推导 | 决策要点 + 权威出处 + 指向正文的链接 |
| 使用主体 | 人（学习/研究） | AI agent（协作/验证/对齐）+ 人（速查） |
| 更新频率 | 稳定 | 随国际前沿季度评审滚动更新 |

**边界规则**：

- skill 不复制正文内容，只做摘要与导航；深入内容一律链接 `docs/` 具体文档。
- skill 中每个事实性论断必须带出处（论文含会议/年份，在线资源含 URL），与 [质量门禁](../docs/06-扩展计划/国际前沿对齐与质量治理执行计划.md#6-质量门禁) 一致。
- skill 不作为项目状态的记录场所，状态一律见 [STATUS.md](../docs/00-项目总览/STATUS.md)。

## 2. 目录结构

```text
AI_Skill/
├── README.md                     # 本文件：总览、清单、用法
├── SKILL规范.md                  # 技能制作规范（结构/命名/质量门禁/评审流程）
├── SKILL模板.md                  # 空白模板（复制后填充）
├── 示例模型.md                   # 参考模型：一个完整达标的技能样板
├── SKILL用例与用法.md            # 人/agent 的使用场景与调用示例
├── 权威来源索引.md               # 国际权威来源分级索引（会议/官方文档/工具链）
└── skills/                       # 技能本体（16 个，按项目主题映射 + 前沿专项）
    ├── cache-algorithms-fundamentals/       # 01 理论基础：LRU/LFU/FIFO/MRU/Random
    ├── cache-algorithms-advanced/           # 01.02：ARC/2Q/SLRU/CLOCK-Pro/LHD/W-TinyLFU/S3-FIFO/SIEVE
    ├── learning-driven-cache/               # 01.04 ✨前沿：LeCaR→3L-Cache/KV驱逐RL
    ├── distributed-cache-algorithms/        # 01.03：一致性哈希/Rendezvous
    ├── os-kernel-cache/                     # 02.01/02.04：PageCache/MGLRU/DAMON/folio/PSI
    ├── cpu-cache-architecture/              # 02.02：MESI/CacheLine/伪共享/ARM
    ├── db-cloud-cache/                      # 02.03：InnoDB/PG/MongoDB/云数据库
    ├── modern-storage-stack/                # 02.04.01 ✨前沿：ZNS/KVSSD/io_uring/SPDK/FarMemory
    ├── redis-data-structures/               # 03.01：SDS/dict/quicklist/ziplist/HLL/Stream
    ├── redis-persistence-ha/                # 03.02/03.03：RDB/AOF/复制/Sentinel/Cluster
    ├── redis-ecosystem-versions/            # 03.05 ✨前沿：Redis 8.x/Valkey/Dragonfly/Garnet
    ├── cache-architecture-patterns/         # 04.01/04.04：六大模式/穿透/雪崩/击穿/热点
    ├── llm-kv-cache/                        # 04.03.15 ✨前沿：PagedAttention/RadixAttention/P-D分离/Mooncake
    ├── cache-security/                      # 04.02 ✨前沿：侧信道/CPDoS/防护体系
    ├── cache-operations-testing/            # 07+Testing：部署/监控/集群运维验证
    ├── distributed-architecture/            # 08：Raft/Paxos/2PC/TCC/Saga/锁/限流/配置
    ├── cloud-native-cache/                  # 04.03.16 ✨新增：云缓存服务/K8s Operator/Docker 构建缓存
    └── elastic-selfhealing/                 # 07.09 ✨新增：伸缩(HPA/KEDA/Karpenter)/自愈/混沌工程
```

## 3. 技能清单与主题映射

| # | 技能 | 对齐项目主题 | 对齐国际前沿（示例） | 状态 |
| - | ---- | ----------- | ------------------ | ---- |
| 1 | cache-algorithms-fundamentals | 01.01 | Che et al. (IMC'03) 近似、IRM 分析 | ✅ |
| 2 | cache-algorithms-advanced | 01.02/01.05 | S3-FIFO (SOSP'23)、SIEVE (NSDI'24)、TLA+ 验证 | ✅ |
| 3 | learning-driven-cache | 01.04 ✨ | Hawkeye (ISCA'16)、CACHEUS (FAST'21)、3L-Cache (FAST'25) | ✅ |
| 4 | distributed-cache-algorithms | 01.03 | 一致性哈希 (Karger STOC'97)、Rendezvous (IEEE TPDS'96) | ✅ |
| 5 | os-kernel-cache | 02.01/02.04 | MGLRU (Linux 6.1+)、DAMON (5.15+)、folio (5.16) | ✅ |
| 6 | cpu-cache-architecture | 02.02 | MESI、ARM 一致性、伪共享消除 | ✅ |
| 7 | db-cloud-cache | 02.03 | Aurora/PolarDB/Neon 存算分离缓存 | ✅ |
| 8 | modern-storage-stack | 02.04.01 ✨ | ZNS (NVMe 1.4)、io_uring、SPDK、CXL Far Memory | ✅ |
| 9 | redis-data-structures | 03.01 | Redis 8 数据结构、listpack、compact 系列 | ✅ |
| 10 | redis-persistence-ha | 03.02/03.03 | Multi-Part AOF、RLA、Cluster 缩放 | ✅ |
| 11 | redis-ecosystem-versions | 03.05 ✨ | Redis 8.10 (2026-11)、Valkey 9.1、Dragonfly/Garnet | ✅ |
| 12 | cache-architecture-patterns | 04.01/04.04 | Cache-Aside 系列、三大击穿问题治理 | ✅ |
| 13 | llm-kv-cache | 04.03.15 ✨ | vLLM V1 (SOSP'23)、SGLang EPD、Mooncake (FAST'25→PyTorch 生态) | ✅ |
| 14 | cache-security | 04.02 ✨ | Prime+Probe、CacheWarp (USENIX Sec'23)、CPDoS | ✅ |
| 15 | cache-operations-testing | 07/Testing | Ansible/Terraform/Helm/Prometheus、Redis Cluster 验证 | ✅ |
| 16 | distributed-architecture | 08 | Raft (ATC'14)、Redlock 争议、令牌桶 | ✅ |
| 17 | cloud-native-cache | 04.03.16 ✨ | 云厂商默认 Valkey、K8s Operator 谱系、BuildKit 缓存 | ✅ |
| 18 | elastic-selfhealing | 07.09 ✨ | HPA/VPA/KEDA/Karpenter、自愈五层、混沌工程 | ✅ |

**前沿更新时间**：2026-11（对齐执行计划第三批"季度前沿评审"）。

## 4. 用法

### 4.1 人工速查

直接打开对应 `skills/<name>/SKILL.md`，看"核心要点"与"权威速查"节；需要深入时点击"项目文档映射"链接进入 `docs/` 正文。

### 4.2 AI agent 协作（SKILL.md 兼容工具）

将本目录加入工具的 skill 扫描路径（如 Kimi Code / Claude Code 的 skill roots），agent 会按 frontmatter `description` 自动匹配加载。也可在指令中显式点名：

```text
使用 cache-algorithms-advanced 技能，检查 docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md 的实验结论是否与 SOSP'23/NSDI'24 原文一致。
```

### 4.3 与质量门禁联动

任何 skill 的"验证命令"节给出的命令，都是 [Testing](../Testing/README.md) 已登记的自动化用例；`python Testing/self_verify.py all` 可全量执行（详见 [Testing/README.md](../Testing/README.md)）。

## 5. 新增/修订技能

必须遵循 [SKILL规范.md](SKILL规范.md)：复制 [SKILL模板.md](SKILL模板.md) → 填充 → 对照规范自检 → 更新本 README 清单 → 运行 `python Testing/self_verify.py all` 确认无回归。参考样板：[示例模型.md](示例模型.md)。

## 6. 维护责任

- 前沿事实（版本号/会议出处）季度核验一次，更新到对应 skill 的"国际前沿对齐"节，并登记 [权威来源索引.md](权威来源索引.md) 的更新记录。
- 与 [AGENTS.md](../AGENTS.md) §5 工具链、[STATUS.md](../docs/00-项目总览/STATUS.md) 变更记录保持同步。

---

**创建**：2026-11 | **格式版本**：SKILL.md v1 | **最后对齐**：2026-11-17
