---
name: cpu-cache-architecture
description: CPU 缓存层次（L1/L2/L3/MESI/CacheLine/伪共享/ARM）与缓存一致性原理；用于性能分析、锁与数据结构设计
---

# CPU 缓存架构

> 覆盖 CPU 缓存层次、一致性协议、Cache Line 局部性与伪共享，是性能优化与并发设计的硬件基础。

## 1. 概述与适用场景

- **覆盖**：L1/L2/L3 层次、MESI/MOESI、Cache Line 对齐、伪共享、ARM 缓存特性、新型存储介质缓存架构。
- **适用**：分析热点数据结构；评审并发组件设计；解释缓存命中/失效的性能数据。
- **不适用**：OS 页缓存（→ os-kernel-cache）；分布式一致性（→ distributed-architecture）。

## 2. 核心要点

1. 典型 x86 服务器：L1d 32-48 KB/core、L2 1-2 MB/core、L3 共享数十 MB；L1 命中约 4 周期，DRAM 约 200-400 周期（Intel/AMD 优化手册口径，C 级经验值）。
2. Cache Line 主流 64 B（x86/ARM64 均 64 B）；伪共享即多核写同一 Line 的不同字节引发 RFO（Read For Ownership）乒乓，吞吐可退化一个数量级（见 02.02.04）。
3. MESI 四状态（Modified/Exclusive/Shared/Invalid）是写失效协议标准模型；Intel 用 MESIF（F=Forward）、AMD 用 MOESI（O=Owned 减少回写）；ARM big.LITTLE 与 CCI/CMN 一致性网格扩展了跨簇一致性（见 02.02.05）。
4. 消除伪共享三板斧：按 Line 填充（padding）、按核分片（per-core shard）、无锁/RCU 降低写竞争；Go 的 `runtime/internal/cache`、Java `@Contended`、C++ `alignas(64)` 是语言层手段。
5. 缓存友好数据结构：数组优于链表（顺序预取）；热点字段集中放置；读多写少结构分离冷热字段。
6. NUMA 下 L3 不跨 socket 一致，跨节点访问走 UPI/Infinity Fabric，延迟约为节点内 1.5-2.5 倍（C 级经验，压测确认）。
7. 新型介质：HBM/MRAM/3D XPoint 类介质介于 DRAM 与 SSD 之间，作为 L4/近内存缓存需要新的替换粒度（block vs page）与磨损感知策略（见 02.02.06）。

## 3. 权威速查

| 项 | 典型值 | 说明 |
| -- | ------ | ---- |
| Cache Line | 64 B | x86/ARM64 |
| L1 延迟 | ~4 周期 | 约 1-2 ns |
| L2 延迟 | ~12-14 周期 | 约 4-7 ns |
| L3 延迟 | ~40-70 周期 | 共享 |
| DRAM | ~200-400 周期 | 约 60-120 ns |
| MESI 写失效 | RFO | 多核写同一 Line 串行化 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| L1/L2/L3 层次 | [02.02.01](../../docs/02-系统实现/02.02-CPU缓存架构/02.02.01-L1-L2-L3缓存层次.md) |
| MESI | [02.02.02](../../docs/02-系统实现/02.02-CPU缓存架构/02.02.02-MESI缓存一致性协议.md) |
| Cache Line 对齐 | [02.02.03](../../docs/02-系统实现/02.02-CPU缓存架构/02.02.03-Cache-Line对齐优化.md) |
| 伪共享 | [02.02.04](../../docs/02-系统实现/02.02-CPU缓存架构/02.02.04-伪共享问题与解决.md) |
| ARM 特性 | [02.02.05](../../docs/02-系统实现/02.02-CPU缓存架构/02.02.05-ARM架构缓存特性.md) |
| 新型介质 | [02.02.06](../../docs/02-系统实现/02.02-CPU缓存架构/02.02.06-新型存储介质缓存架构.md) |
| 全栈分析 | [05.01.01](../../docs/05-全栈分析/05.01-硬件层深度剖析/05.01.01-CPU缓存与伪共享.md) |

## 5. 常见任务工作流

### 任务 A：热点结构体诊断

1. `perf stat -e L1-dcache-load-misses,cache-misses` 定位。
2. `perf c2c`（Linux）或 VTune 定位跨核 Line 竞争。
3. 按 §2 第 4 条改造，重测吞吐。

### 任务 B：并发计数器/队列设计评审

核对：共享写变量是否同 Line；是否 per-core 分片；是否有 false sharing 测试（多线程写相邻字段）。

## 6. 国际前沿对齐（截至 2026-11）

- 内核 6.16 引入 perf c2c 对 HBM/CXL 的分类支持，CXL 内存作为近端缓存的一致性管理成为研究热点（kernelnewbies 6.16 条目）。
- 异构大小核（Intel P/E、ARM big.LITTLE）使缓存感知调度复杂化，硬件线程放置影响 L2/L3 亲和（见 Linux 6.14 amd-pstate/EPP 演进）。
- 学术侧：缓存侧信道防护（Flush+Reload 检测）推动缓存索引随机化与分区（CAT）研究，见 cache-security。

## 7. 验证命令

```bash
perf stat -e cycles,cache-misses <程序>    # 人工/环境依赖（TC-OPS-性能前提）
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
```

## 8. 权威参考

- **A 学术**：Papamarcos & Patel, "A Low-overhead Coherence Solution for Multiprocessors with Private Cache Memories", ISCA 1984（MESI 源头）；Hennessy & Patterson《Computer Architecture》（缓存层次标准教材）
- **B 官方**：Intel 64 and IA-32 Optimization Reference Manual；ARM Architecture Reference Manual（ARMv8/9）
- **C 工程**：perf c2c 文档；Linux kernel Documentation/admin-guide/mm/numa
