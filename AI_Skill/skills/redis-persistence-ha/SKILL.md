---
name: redis-persistence-ha
description: Redis 持久化（RDB/AOF/混合/Multi-Part-AOF）与高可用（复制/Sentinel/Cluster）机制及运维要点；用于数据可靠性设计与故障演练
---

# Redis 持久化与高可用

> 覆盖持久化三模式、复制链路、Sentinel 与 Cluster 高可用，是 Redis 数据可靠性设计的核心。

## 1. 概述与适用场景

- **覆盖**：RDB、AOF、混合持久化、Multi-Part AOF、主从复制、Sentinel、Cluster、分片路由。
- **适用**：持久化策略选型；主从/集群部署设计；故障转移演练；评审 03.02/03.03 文档。
- **不适用**：数据结构（→ redis-data-structures）；版本选型（→ redis-ecosystem-versions）；部署自动化（→ cache-operations-testing）。

## 2. 核心要点

1. RDB 是时点快照（fork + COW）：恢复速度快、文件紧凑；代价是 fork 停顿与数据丢失窗口（两次快照间）。`save` 配置点多快照频率权衡。
2. AOF 记录写命令（RESP 协议），刷盘策略 `appendfsync always/everysec/no`；everysec 是生产默认（最多丢 1s）。AOF 重写（rewrite）压缩历史命令，避免无限增长。
3. 混合持久化（4.0+，aof-use-rdb-preamble）：AOF 重写时以 RDB 内容开头 + 增量 AOF 尾部，兼顾恢复速度与重写成本。
4. Multi-Part AOF（7.0+）：目录式结构（manifest + incr + base），消除重写期间的磁盘翻倍与阻塞窗口。
5. 复制：全量（RDB 传输）+ 增量（replication backlog，默认 1 MB，repl-backlog-size 按写入量调整）；无盘复制（diskless）减少主库磁盘压力；PSYNC2（4.0+）支持部分重同步断点续传。
6. Sentinel：3 节点起步的法定人数架构，负责故障检测（主观/客观下线）、自动转移、配置提供；`min-replicas-to-write` 配合防脑裂丢数据。
7. Cluster：16384 固定槽，Gossip 心跳与纪元（epoch）仲裁；failover 由从节点发起选举（cluster-require-full-coverage 影响分区行为）；跨槽多键命令受限制（hash tag 规避）。
8. 延迟来源：fork（大实例秒级）、AOF everysec fsync、keys/slow-command 阻塞、swap；用 `latency doctor` 与 `INFO persistence` 定位。

## 3. 权威速查

| 项 | 推荐值 | 说明 |
| -- | ------ | ---- |
| appendfsync | everysec | 最多丢 1s 数据 |
| AOF 重写阈值 | auto-aof-rewrite-percentage 100 | 按需 |
| repl-backlog-size | 写入速率×重连窗口 | 默认 1 MB 偏小 |
| min-replicas-to-write | ≥1 | 防脑裂 |
| Cluster 节点 | ≥3 主 | 奇数法定人数 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| RDB | [03.02.01](../../../docs/03-Redis组件/03.02-持久化机制/03.02.01-RDB快照机制.md) |
| AOF | [03.02.02](../../../docs/03-Redis组件/03.02-持久化机制/03.02.02-AOF日志机制.md) |
| 混合持久化 | [03.02.03](../../../docs/03-Redis组件/03.02-持久化机制/03.02.03-混合持久化.md) |
| Multi-Part AOF | [03.02.04](../../../docs/03-Redis组件/03.02-持久化机制/03.02.04-Multi-Part-AOF.md) |
| 持久化优化 | [03.02.05](../../../docs/03-Redis组件/03.02-持久化机制/03.02.05-持久化性能优化.md) |
| 主从复制 | [03.03.01](../../../docs/03-Redis组件/03.03-高可用架构/03.03.01-主从复制机制.md) |
| Sentinel | [03.03.02](../../../docs/03-Redis组件/03.03-高可用架构/03.03.02-Sentinel哨兵机制.md) |
| Cluster | [03.03.03](../../../docs/03-Redis组件/03.03-高可用架构/03.03.03-Cluster集群模式.md) |
| 分片路由 | [03.03.04](../../../docs/03-Redis组件/03.03-高可用架构/03.03.04-分片策略与路由.md) |
| 故障案例 | [04.07.02](../../../docs/04-架构设计/04.07-生产案例/04.07.02-故障案例和解决方案.md) |
| 事务与隔离语义 | [03.03.05](../../../docs/03-Redis组件/03.03-高可用架构/03.03.05-事务与隔离语义论证.md) |
| Lua 脚本治理 | [03.03.06](../../../docs/03-Redis组件/03.03-高可用架构/03.03.06-Lua脚本治理与调试.md) |
| 驱逐策略决策 | [03.04.05](../../../docs/03-Redis组件/03.04-内存管理/03.04.05-驱逐策略决策与近似误差.md) |
| 过期删除机制 | [03.04.06](../../../docs/03-Redis组件/03.04-内存管理/03.04.06-过期删除机制与成本模型.md) |

## 5. 常见任务工作流

### 任务 A：持久化策略选型

数据可重建（纯缓存）→关 AOF 或 everysec + RDB 低频；数据不可丢→AOF everysec + 混合持久化 + 跨机房副本；大实例→关注 fork 延迟，考虑 diskless 与 no-appendfsync-on-rewrite no。

### 任务 B：故障转移演练

1. 主库 `DEBUG SLEEP 30` 或 kill -STOP 模拟故障。
2. Sentinel：观察客观下线（down-after-milliseconds）→选举→转移；验证从库提升与 VIP/DNS 切换。
3. Cluster：`CLUSTER FAILOVER`（从库主动）或杀主验证选举；检查槽位覆盖（cluster info）。
4. 回切：旧主恢复后作为从库重同步（避免 split-brain 双写）。
5. 全部用例登记 Testing/cases/CLUS。

## 6. 国际前沿对齐（截至 2026-11）

- Redis 8.x 强化多 AOF 管理与 RDB 加载性能；Valkey 9.x 引入新复制优化（如 batch replication 改进）。
- 跨机房强一致仍是社区未解难题（Redis 无 Paxos/Raft 原生共识），企业多用 CRDT/异步多主或外部仲裁。
- 新硬件路径：SPDK/io_uring 化的持久化后端在专用场景出现（实验性）。

## 7. 验证命令

```bash
redis-cli INFO persistence    # 人工：rdb_bgsave_in_progress/aof_rewrite_in_progress（TC-DB-003）
redis-cli INFO replication    # 人工：master_link_status、slave_read_repl_offset（TC-CLUS-002）
```

## 8. 权威参考

- **A 学术**：无直接会议论文（工程系统）；理论基础见 Gray & Reuter《Transaction Processing》（持久性语义）
- **B 官方**：Redis Persistence 文档（https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/）；Redis Cluster 规范；Sentinel 文档
- **C 工程**：valkey-io/valkey 复制优化说明；生产故障复盘（04.07.02 汇总）
