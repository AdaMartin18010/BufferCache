---
name: db-cloud-cache
description: 数据库缓存（InnoDB Buffer Pool/PostgreSQL/MongoDB）与云数据库缓存架构（Aurora/PolarDB/Neon 存算分离）；用于 DB 缓存调参与云上选型
---

# 数据库与云数据库缓存

> 覆盖单机数据库缓冲管理与云数据库的共享/分层缓存架构，是"缓存作为数据库性能层"的完整视角。

## 1. 概述与适用场景

- **覆盖**：InnoDB Buffer Pool、MySQL Query Cache（已废弃）、PostgreSQL Shared Buffer、MongoDB WiredTiger Cache、数据库替换策略；Aurora/PolarDB/Neon 云缓存架构。
- **适用**：DBA 调参；云上数据库选型；评审 02.03 文档。
- **不适用**：应用侧缓存设计（→ cache-architecture-patterns）；LLM 推理缓存（→ llm-kv-cache）。

## 2. 核心要点

1. InnoDB Buffer Pool 是页缓存（16 KB 页），LRU 变种（ midpoint insertion：新页插 5/8 处，分为 new/old 子链）防扫描污染；脏页由 flush list 管理，`innodb_buffer_pool_size` 通常为物理内存 50-70%（MySQL 官方手册口径）。
2. PostgreSQL 是双缓存架构：shared_buffers（默认 128 MB，建议 25% 内存）+ OS Page Cache；有效缓存 = 两者之和，`pg_buffercache`/`pg_prewarm` 扩展支持检查与预热。
3. MySQL Query Cache 在 8.0 移除：写失效粒度过粗（任何表更新全部失效）在高写负载下成为瓶颈——这是"缓存失效一致性成本"的经典反面教材。
4. WiredTiger Cache 默认约为 (RAM - 1 GB) × 50%（MongoDB 3.4+ 口径）；采用近似 LRU + eviction trigger（cache full 时前台线程参与驱逐）。
5. 存算分离重构了缓存层：计算节点本地缓存（ephemeral）+ 共享存储层缓存 + 跨节点共享缓存池；缓存正确性核心从"驱逐策略"转向"版本/一致性仲裁"（缓存失效必须由存储层日志位点/页版本裁决）。
6. Aurora 预热：通过 Heat Map（页访问统计）在实例重启/故障转移后按热度异步拉取页；PolarDB 共享内存池（Shared Buffer Pool 跨计算节点共享，RDMA 访问）；Neon 分层：计算节点本地缓存 + Pageserver（对象存储）+ L0/L1 层。
7. 云上要点：serverless 实例的缓存是瞬时的（弹性伸缩即冷启动），预热能力决定尾延迟。

## 3. 权威速查

| 系统 | 缓存层 | 默认/推荐大小 | 替换策略 | 特色机制 |
| ---- | ------ | ------------- | -------- | -------- |
| InnoDB | Buffer Pool | 内存 50-70% | midpoint LRU | flush list、change buffer |
| PostgreSQL | shared_buffers + OS | 25% 内存 | Clock-Sweep（近似 LRU） | pg_prewarm、双缓存 |
| WiredTiger | WiredTiger Cache | (RAM-1G)×50% | 近似 LRU | eviction worker |
| Aurora | 本地+共享存储缓存 | 实例级调 | 热度驱动 | Heat Map 预热、日志仲裁 |
| PolarDB | 共享内存池 | 池化 | 全局管理 | RDMA 共享、一致性版本 |
| Neon | 本地缓存+Pageserver | 分层 | 分层 LRU | 对象存储后端、branch |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| InnoDB Buffer Pool | [02.03.01](../../../docs/02-系统实现/02.03-数据库缓存/02.03.01-InnoDB-Buffer-Pool.md) |
| Query Cache | [02.03.02](../../../docs/02-系统实现/02.03-数据库缓存/02.03.02-MySQL-Query-Cache.md) |
| PostgreSQL | [02.03.03](../../../docs/02-系统实现/02.03-数据库缓存/02.03.03-PostgreSQL-Shared-Buffer.md) |
| 替换策略 | [02.03.04](../../../docs/02-系统实现/02.03-数据库缓存/02.03.04-数据库缓存替换策略.md) |
| MongoDB | [02.03.05](../../../docs/02-系统实现/02.03-数据库缓存/02.03.05-MongoDB缓存机制.md) |
| 云数据库 | [02.03.06](../../../docs/02-系统实现/02.03-数据库缓存/02.03.06-云数据库缓存架构.md) |

## 5. 常见任务工作流

### 任务 A：InnoDB 缓冲池调优

1. 采集 `SHOW ENGINE INNODB STATUS`（BUFFER POOL AND MEMORY 段）与 `sys.schema_table_statistics`。
2. 命中率 <99% 且磁盘读高→扩大 pool；扫描型负载→确认 midpoint insertion 生效。
3. 大实例开启多个 pool instance（`innodb_buffer_pool_instances`）降低锁竞争。
4. 变更后跑 `sysbench oltp_read_only` 对比。

### 任务 B：云数据库选型

1. 确定是否需要跨节点共享缓存（高并发读写混合→PolarDB 类共享池）。
2. 评估 serverless 冷启动影响（预热能力、连接保持）。
3. 用 [02.03.06](../../../docs/02-系统实现/02.03-数据库缓存/02.03.06-云数据库缓存架构.md) 的延迟账对照表估算。

## 6. 国际前沿对齐（截至 2026-11）

- 存算分离+共享缓存池成为云数据库默认架构（Aurora/PolarDB/Neon 持续迭代；AlloyDB 提供列存缓存对照）。
- Neon 分层 Pageserver 与对象存储分层策略被多个开源数据库（如 FerretDB 生态、TiKV 云原生部署）参照。
- 学术：使用 AI 预测预取（如 PALM 类）在 DB 缓冲池预取上的探索持续，但生产仍以热度驱动为主（C 级判断）。

## 7. 验证命令

```bash
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
# 人工（需 MySQL 实例）：
SHOW ENGINE INNODB STATUS\G    # 预期：Buffer Pool 命中率与脏页状态（TC-DB-001）
```

## 8. 权威参考

- **A 学术**：DeWitt et al., "Operating Systems Support for Database Management"（缓冲区管理经典）；Aurora 论文 Verbitski et al., SIGMOD 2017；PolarDB 论文 Cai et al., ICDE 2020；Neon 技术博客/论文
- **B 官方**：MySQL Reference Manual（InnoDB Buffer Pool）；PostgreSQL Documentation（Resource Consumption）；MongoDB Docs（WiredTiger）；各云服务文档
- **C 工程**：Aiven/Percona 缓冲池调优指南
