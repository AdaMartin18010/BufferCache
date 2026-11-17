---
name: redis-data-structures
description: Redis 核心数据结构（SDS/dict/quicklist/intset/skiplist/ziplist/listpack/HyperLogLog/Stream）与 8.x 变化的实现要点；用于 Redis 开发与容量评估
---

# Redis 数据结构与内核实现

> 覆盖 Redis 内存数据结构的实现机制、复杂度与内存特征，含 Redis 8.x 的编码演进。

## 1. 概述与适用场景

- **覆盖**：SDS、dict、quicklist、intset、skiplist、ziplist/listpack、HyperLogLog、Stream、扩展模块（JSON/Graph/TimeSeries）。
- **适用**：选择数据结构控内存；预估容量；评审 03.01 文档；面试/教学。
- **不适用**：持久化与高可用（→ redis-persistence-ha）；版本与生态（→ redis-ecosystem-versions）。

## 2. 核心要点

1. 字符串用 SDS（simple dynamic string）：O(1) 取长度、二进制安全、预分配（buf 冗余 <1 MB 时翻倍，≥1 MB 加 1 MB）；`OBJ_ENCODING_EMBSTR` 小字符串（≤44 B）一次性分配。
2. dict 是渐进式 rehash 哈希表：两张表渐进迁移（定时/每次访问搬 1 个桶），扩缩容避免全量停顿；负载因子 ≥1 扩（bgsave 时 ≥5），≤0.1 缩。
3. ziplist 被 listpack 全面替代（7.0+）：ziplist 连锁更新（级联重分配）风险由 listpack 的每节点独立长度解决；hash/zset/list 小对象默认 listpack。
4. 哈希对象编码路径：listpack（entries<128 且值<64 B，默认阈值）→ hashtable；zset：listpack（<128 或值<64 B）→ skiplist+dict 双结构。
5. 跳表：平均 O(log n)，zset 按 score+member 排序；与 dict 双索引实现"按成员查分"与"按序遍历"。
6. Stream 用 radix tree（RAX）索引消息 ID + listpack 打包消息，支持消费者组与 pending list（PEL）。
7. HyperLogLog 用稀疏/稠密两种编码，标准误差 0.81%，核心为 6 bit 寄存器 + hash 前导零估计基数。
8. 模块：RedisJSON（文档模型+RediSearch 索引）、RedisTimeSeries、RedisGraph；8.x 中部分模块整合进 Redis Open Source（见 redis-ecosystem-versions）。

## 3. 权威速查

| 对象 | 编码演进 | 小对象默认 | 大对象升级 | 复杂度要点 |
| ---- | -------- | ---------- | ---------- | ---------- |
| string | raw/embstr/int | embstr(≤44 B) | raw | O(1) |
| hash | listpack→hashtable | entries<128 & val<64B | hashtable | rehash 渐进 |
| list | quicklist（listpack 节点） | — | — | 节点级 O(log N) |
| set | intset/listpack/hashtable | intset（整数） | hashtable | 整数压缩 |
| zset | listpack/skiplist+dict | 同上阈值 | 双索引 | 跳表 O(log N) |
| stream | RAX+listpack | — | — | 追加 O(1) |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| SDS | [03.01.01](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.01-SDS简单动态字符串.md) |
| dict | [03.01.02](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.02-哈希表dict实现.md) |
| quicklist | [03.01.03](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.03-列表quicklist实现.md) |
| intset | [03.01.04](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.04-集合intset实现.md) |
| skiplist | [03.01.05](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.05-有序集合skiplist实现.md) |
| ziplist | [03.01.06](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.06-压缩编码ziplist.md) |
| HyperLogLog/Stream | [03.01.07](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.07-HyperLogLog基数统计.md) / [03.01.08](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.08-Stream流数据结构.md) |
| 模块 | [03.01.09](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.09-RedisJSON模块分析.md) / [03.01.10](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.10-RedisGraph模块分析.md) / [03.01.11](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.11-RedisTimeSeries模块分析.md) |
| 源码逐行 | [03.07.01](../../../docs/03-Redis组件/03.07-源码分析/03.07.01-Redis关键路径源码逐行分析.md) |
| 操作复杂度论证 | [03.01.12](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.12-数据类型操作算法与复杂度论证.md) |
| 序列化与布局 | [03.01.13](../../../docs/03-Redis组件/03.01-核心数据结构/03.01.13-序列化编码与内存布局权衡.md) |

## 5. 常见任务工作流

### 任务 A：容量预估

1. 定对象类型与规模；2. 查 §3 编码路径确定小/大对象编码；3. 按编码内存模型（listpack 节点 ~128 B 内；skiplist 节点 ~指针×层数）估算；4. 加 10-20% 元数据冗余；5. 用 `MEMORY USAGE key` 抽样校准。

### 任务 B：大 Key 诊断

`redis-cli --bigkeys` + `MEMORY USAGE`；编码升级后（如 hashtable）内存突增是否可接受；ziplist/listpack 阈值是否需显式收紧（hash-max-listpack-entries）。

## 6. 国际前沿对齐（截至 2026-11）

- listpack 全面替代 ziplist 已在 7.x/8.x 完成；后续方向是压缩列表内存布局继续紧凑化与 SIMD 解析。
- Redis 8.x 整合多模块能力（JSON/Search/TimeSeries 部分进入核心发行），见 redis-ecosystem-versions。
- Valkey 9.x 重构 I/O 线程模型（2026-10 发布 9.1.3），数据结构层兼容 Redis 协议与编码。

## 7. 验证命令

```bash
redis-cli MEMORY USAGE <key>     # 人工/需实例（TC-DB-002）
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
```

## 8. 权威参考

- **A 学术**：Pugh, "Skip Lists: A Probabilistic Alternative to Balanced Trees", CACM 1990（跳表）；Flajolet et al., "HyperLogLog", AofA 2007
- **B 官方**：Redis 官方文档 Data types（https://redis.io/docs/latest/develop/data-types/）；Redis 源码（github.com/redis/redis，src/t_*.c、src/listpack.c）
- **C 工程**：listpack 设计说明（antirez 博客）；Memory optimization 文档
