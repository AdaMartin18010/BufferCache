# SKILL 用例与用法说明

> 本文档说明人（读者/贡献者/评审者）与 AI agent 如何使用本技能库，按典型场景给出调用示例。技能的 frontmatter 与目录布局兼容 SKILL.md 生态（Kimi Code / Claude Code 等），将 `AI_Skill/skills` 加入工具 skill 扫描路径即可被 agent 自动发现。

## 1. 使用主体与入口

| 主体 | 入口 | 说明 |
| ---- | ---- | ---- |
| 人（速查） | 打开 `skills/<name>/SKILL.md` | §3 权威速查 + §4 正文链接 |
| 人（学习） | §4 文档映射 → docs/ 正文 | skill 是索引，不是教材 |
| AI agent（自动） | 工具按 description 匹配加载 | 指令命中关键词即触发 |
| AI agent（显式） | 指令中点名技能名 | 见 §2 用例 |

## 2. 典型用例

### 用例 1：评审新写的算法文档（agent）

```text
使用 cache-algorithms-advanced 技能评审 docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md：
核对机制描述与 SOSP'23/NSDI'24 原文是否一致，检查命中率结论是否注明 trace 来源，
最后给出修订清单并标注每条修订的权威出处。
```

要点：agent 按技能 §2 要点核对、§6 前沿出处仲裁、§8 参考补引用。

### 用例 2：为部署方案选 Redis 版本（人 + agent 协作）

```text
使用 redis-ecosystem-versions 技能：生产环境新集群，要求 BSD/AGPL 合规、
需要 200 万 QPS 单节点能力、2028 年前持续安全更新，给出 Redis/Valkey 选型结论与风险。
```

要点：技能 §3 版本速查表 + §6 前沿（8.x 线支持周期、Valkey 9.x I/O 线程）支撑决策。

### 用例 3：验证文档变更是否引入回归（CI / 本地）

```bash
python Testing/self_verify.py all        # 全量：代码块/链接/结构/基准
python Testing/self_verify.py links --path AI_Skill   # 只查新增技能链接
```

要点：技能 §7 列出的每条验证命令都对应 Testing 中用例 ID，失败时按用例的"修正指引"处理。

### 用例 4：前沿对齐季度评审（agent 批量）

```text
按 cache-operations-testing、modern-storage-stack、llm-kv-cache 三个技能的"国际前沿对齐"节
逐条核验：版本号是否过期、会议引用是否准确、是否漏掉本季度新进展。
输出：逐技能更新建议（新增/修订/删除条目 + 出处 URL）。
```

要点：这是执行计划第三批"季度前沿评审"的操作化，产出直接修订 §6。

### 用例 5：新人快速进入缓存领域（人）

1. `cache-algorithms-fundamentals` 建立基线认知 → 2. `docs/01-理论基础` 正文精读 → 3. `cache-architecture-patterns` 看工程形态 → 4. `cache-operations-testing` 跑通本地基准。

## 3. 组合关系（常见技能链）

| 场景 | 技能链 |
| ---- | ------ |
| 新缓存系统设计 | cache-algorithms-fundamentals → cache-algorithms-advanced → cache-architecture-patterns → cache-operations-testing |
| LLM 推理平台 | llm-kv-cache → modern-storage-stack → distributed-architecture → cache-operations-testing |
| Redis 生产运维 | redis-data-structures → redis-persistence-ha → redis-ecosystem-versions → cache-operations-testing |
| 文档质量治理 | 任意技能（核对事实）→ Testing 用例（验证）→ STATUS.md（登记） |

## 4. 反模式（禁止用法）

1. **把 skill 当教材通读**：skill 是速查/流程，系统学习走 docs/ 学习路径（[INDEX.md](../docs/INDEX.md) §学习路径）。
2. **在 skill 里写进度/结论性总结**：进度归 STATUS.md，总结性元文档被 [AGENTS.md](../AGENTS.md) §4.2.1 禁止。
3. **绕过 Testing 直接宣称"验证通过"**：任何"已验证"表述必须有 self_verify 或对应用例的实际运行输出支撑。
4. **复制 skill 内容进 docs/ 正文**：正文与 skill 单一事实源应保持一致；如需沉淀，改写为正文并回链，删除 skill 重复段。

## 5. 反馈与修订

使用中发现 skill 错误/过期：按 [SKILL规范.md](SKILL规范.md) §4 流程修订，或在 [STATUS.md](../docs/00-项目总览/STATUS.md) 变更记录中登记待办。

---

**最后更新**：2026-11
