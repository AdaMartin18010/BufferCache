---
name: redis-ecosystem-versions
description: Redis 版本演进与开源生态（Redis 8.x 各线、Valkey、Redict、KeyDB、Dragonfly、Garnet）的许可、特性与选型；用于版本升级与合规决策
---

# Redis 生态与版本演进

> 覆盖 Redis 7.4→8.x 版本线、AGPL 许可变迁与 Valkey/Redict/KeyDB/Dragonfly/Garnet 生态选型。

## 1. 概述与适用场景

- **覆盖**：Redis 8.x 版本线、许可变迁、替代实现对比、升级路径。
- **适用**：版本升级决策；合规审查（许可证）；替代实现选型；评审 03.05 文档。
- **不适用**：具体机制（→ redis-data-structures / redis-persistence-ha）。

## 2. 核心要点

1. 许可变迁：Redis 7.2.4（2024-03）为最后 BSD 版本；7.4 与 8.0 起改为 RSALv2/SSPLv1 双许可（2024-05 公告），8.0 后追加 AGPLv3 选项（2025-05 公告）；Linux Foundation 于 2024-03 创立 Valkey（BSD 分叉）。
2. 8.0（2025-05）：模块化整合（RedisJSON/Search/TimeSeries/Bloom 部分进入核心）、字典表内存优化、新 `HASH` 字段过期、`I/O threads` 增强；AGPLv3 成为核心选项。
3. 版本线现状（2026-11，来源：redis.io 与 endoflife.date 交叉核验）：8.10 为最新 GA 线（8.10.2，2026-09-17）；8.2 为 Extended Release（支持至 2030-09）；8.0 将于 2026-12-01 EOL；8.12 RC3 已发布（2026-11-12）。
4. Valkey：Linux Foundation 主导，BSD 许可；9.1.3（2026-10-26）引入重构 I/O 线程模型，宣称单服务器 210 万 RPS；与 Redis 协议兼容，为主要合规替代。
5. 其他分支：Redict（7.2 BSD 维护线，社区化）；KeyDB（Snap 多线程）；Dragonfly（C++ 全新实现，线程共享内存，宣称高吞吐）；Garnet（微软 Research，C# RESP 实现，兼容 Redis 协议）。
6. 选型维度：许可证合规（AGPL 接受度）、生态（客户端/工具链兼容）、性能特征（I/O 模型）、运维熟悉度、商业支持。
7. 升级风险：RDB/AOF 格式跨版本兼容（一般向后读）、模块 API 变更、命令行为差异（如 `SINTERCARD`、过期精度）、最大内存策略语义。

## 3. 权威速查

| 产品 | 许可 | 最新（2026-11） | 特点 | 适用 |
| ---- | ---- | -------------- | ---- | ---- |
| Redis OSS | AGPLv3（8.0+） | 8.10.2 | 模块整合、功能最全 | 接受 AGPL/商业授权 |
| Valkey | BSD | 9.1.3 | 高性能 I/O 线程、社区治理 | 合规敏感/高 QPS |
| Redict | BSD | 7.2 系 | 稳定保守 | 冻结需求 |
| KeyDB | BSD | 6.x 系 | 多线程 | 存量 |
| Dragonfly | BSL（转 Apache） | 1.x | 高吞吐、线程共享 | 大实例密度 |
| Garnet | MIT | 1.x | C#、协议兼容 | .NET 生态 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 生态与版本总览 | [03.05 README](../../docs/03-Redis组件/03.05-Redis生态与版本演进/README.md) |
| 版本更新策略 | [Redis版本更新计划](../../docs/00-项目总览/Redis版本更新计划.md) |
| 对比基准 | [01.05.04](../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) |

## 5. 常见任务工作流

### 任务 A：版本升级决策

1. 确认许可合规路径；2. 查 §3 速查确认目标线支持周期；3. 用 `redis-check-rdb`/`redis-check-aof` 验证数据文件兼容；4. 按 redis-persistence-ha 任务 B 演练回切；5. 灰度 1 主 1 从观察 `info` 指标。

### 任务 B：生态选型评审

输出：许可风险 + 性能需求匹配 + 迁移成本（协议兼容性测试、运维工具链）。

## 6. 国际前沿对齐（截至 2026-11）

- Redis 8.12 RC3 发布（2026-11-12，github releases）；8.0 EOL 逼近（2026-12-01），升级窗口紧迫。
- Valkey 9.1.3 发布（2026-10-26），I/O 线程重构带来约 2.1M RPS 单节点能力（valkey.io）。
- 云厂商普遍双轨支持 Redis/Valkey（AWS ElastiCache for Valkey 等）。

## 7. 验证命令

```bash
python scripts/version_monitor.py --check redis   # 预期：输出最新版本与本地记录差异（TC-INT-002）
redis-cli INFO server    # 人工：确认运行版本（TC-DB-004）
```

## 8. 权威参考

- **A 学术**：无（工程生态）
- **B 官方**：Redis Release Notes（https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/release-notes/）；redis/redis GitHub Releases；Valkey 官网（https://valkey.io/）；Redis 许可公告（2024-05、2025-05）
- **C 工程**：endoflife.date（版本支持周期交叉核验）；Dragonfly/Garnet 官方基准说明（注意厂商基准偏差）
