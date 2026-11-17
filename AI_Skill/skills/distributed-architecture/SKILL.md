---
name: distributed-architecture
description: 分布式架构核心协议（Raft/Paxos/2PC/TCC/Saga/分布式锁/限流/配置中心）的机制、正确性条件与工程实践；用于分布式方案设计与评审
---

# 分布式架构与协调

> 覆盖一致性、事务、协调、限流、配置五类分布式基础设施协议，是缓存系统水平扩展的架构底座。

## 1. 概述与适用场景

- **覆盖**：Raft、Paxos、2PC、TCC、Saga、分布式锁（Redlock）、协调服务（ZK/etcd/Consul）、限流（四算法）、配置中心。
- **适用**：分布式方案选型与评审；协议正确性条件核对；故障场景推演。
- **不适用**：缓存放置算法（→ distributed-cache-algorithms）；具体产品运维（→ cache-operations-testing）。

## 2. 核心要点

1. Raft（ATC 2014）以"领导选举 + 日志复制 + 安全性约束"换取可理解性；关键参数：election timeout 随机化防选票瓜分，commit 需多数派，leader 完整性保证已提交日志不丢失。
2. Paxos（Lamport 2001 通俗版）是理论基准：单决议 Basic Paxos 两阶段，多决议需 Multi-Paxos 的 leader 稳定优化；工程复杂度高于 Raft，现代系统（etcd/Consul/TiKV）多选 Raft 系。
3. 2PC（两阶段提交）是阻塞协议：协调者宕机 + 参与者处于 ready 状态会锁资源直至恢复；生产多用超时+人工介入或改 TCC/Saga。
4. TCC（Try-Confirm-Cancel）把事务拆为资源预留与确认，要求业务幂等（防重复 confirm）与空回滚（cancel 先于 try 到达）；Saga 用补偿链处理长事务，隔离性弱需业务防脏读。
5. 分布式锁：单实例 Redis SET NX PX + 唯一值 + Lua 释放是基线；Redlock（多实例多数派）存在争议（Antirez 2016 提出，Kleppmann 2016 质疑时钟与 GC 停顿），高风险资金场景选 ZK/etcd 的临时顺序节点（共识保证）而非 Redis。
6. 限流四算法：固定窗口（临界突发）、滑动窗口（内存精度）、令牌桶（允许突发、匀速产出）、漏桶（严格匀速）；分布式限流用中心化令牌服务或本地估算+周期校准（梯度下降校准为 C 级经验）。
7. 配置中心三要素：一致性推送（长连接/watch）、灰度发布（按节点/标签分批）、版本回滚与审计；配置变更必须可观测（变更事件 + 生效确认）。

## 3. 权威速查

| 协议 | 类型 | 一致性 | 阻塞性 | 出处 |
| ---- | ---- | ------ | ------ | ---- |
| Raft | 共识 | 线性一致（多数派） | 选举期短暂不可用 | ATC 2014 |
| Paxos | 共识 | 线性一致 | 活性复杂 | SIGACT 2001 |
| 2PC | 提交协议 | 强一致 | 协调者宕机阻塞 | Gray & Reuter 1993 |
| TCC | 补偿事务 | 最终一致 | 非阻塞（要求幂等） | 阿里工程实践 |
| Saga | 补偿链 | 最终一致 | 非阻塞 | Garcia-Molina 1987 |
| Redlock | 锁 | — | — | Antirez 2016（争议） |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| Raft/Paxos | [08.01.01](../../../docs/08-分布式架构/08.01-分布式一致性/08.01.01-Raft协议实践.md) / [08.01.02](../../../docs/08-分布式架构/08.01-分布式一致性/08.01.02-Paxos协议实践.md) |
| 2PC/TCC/Saga | [08.02.01](../../../docs/08-分布式架构/08.02-分布式事务/08.02.01-2PC两阶段提交实践.md) / [08.02.02](../../../docs/08-分布式架构/08.02-分布式事务/08.02.02-TCC补偿事务实践.md) / [08.02.03](../../../docs/08-分布式架构/08.02-分布式事务/08.02.03-Saga长事务实践.md) |
| 分布式锁 | [08.03.01](../../../docs/08-分布式架构/08.03-分布式协调/08.03.01-分布式锁实践.md) |
| 协调服务 | [08.03.02](../../../docs/08-分布式架构/08.03-分布式协调/08.03.02-分布式协调服务实践.md) |
| 限流 | [08.04.01](../../../docs/08-分布式架构/08.04-分布式限流/08.04.01-分布式限流实践.md) |
| 配置中心 | [08.05.01](../../../docs/08-分布式架构/08.05-分布式配置/08.05.01-分布式配置中心实践.md) |
| 容错设计 | [02.06.04](../../../docs/02-系统实现/02.06-程序设计实践/02.06.04-全局系统容错.md) |
| 客户端行为治理 | [03.06.07](../../../docs/03-Redis组件/03.06-网络通信/03.06.07-客户端连接与重试行为矩阵.md) |

## 5. 常见任务工作流

### 任务 A：方案选型

强一致元数据（≤5 节点）→Raft 系（etcd）；跨服务长事务→Saga+补偿表；短事务强资源预留→TCC；锁（非资金）→Redis SET NX PX；锁（资金/强安全）→ZK/etcd。

### 任务 B：协议正确性核对

Raft：日志匹配特性、leader 完备性是否被实现改动破坏（如 pre-vote、lease read 的时钟假设）；TCC：幂等、空回滚、悬挂三防线是否齐全。

## 6. 国际前沿对齐（截至 2026-11）

- Raft 扩展：etcd/Consul 的快照与联邦持续演进；异构共识（异步 BFT 混合）研究活跃。
- 分布式事务：Percolator 模型（TiDB 采用）与 Calvin 模型（确定性事务）持续影响新系统设计。
- Redlock 争议未终结：2024-2026 仍有分析指出 fencing token 必要性；工程共识倾向"Redis 锁只用于效率，正确性用共识"。
- 限流前沿：自适应限流（CoDel 启发、AIMD）与 eBPF 内核态限流（Cilium）兴起。

## 7. 验证命令

```bash
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
python Testing/self_verify.py structure               # 预期：08 文档链接完整（TC-LINK-001）
```

## 8. 权威参考

- **A 学术**：Lamport, "Paxos Made Simple", 2001；Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm", USENIX ATC 2014；Garcia-Molina & Salem, "Sagas", SIGMOD 1987；Gray & Reuter, "Transaction Processing", 1993
- **B 官方**：etcd 文档（一致性读/lease）；Consul 文档；Redis 分布式锁官方说明（含 Redlock 与争议链接）
- **C 工程**：Kleppmann, "How to do distributed locking", 2016；Martin Kleppmann《DDIA》第 8-9 章
