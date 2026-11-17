---
name: cache-algorithms-fundamentals
description: 基础缓存替换算法（LRU/LFU/FIFO/MRU/Random）的原理、复杂度、命中率分析与选型判断；用于缓存算法入门、方案评审与文档核对
---

# 基础缓存替换算法（LRU / LFU / FIFO / MRU / Random）

> 覆盖五种经典替换算法及其命中率分析工具，是全部缓存算法的公共基础层。

## 1. 概述与适用场景

- **覆盖**：LRU、LFU、FIFO、MRU、Random 的机制、复杂度、典型命中率行为、Che 近似分析。
- **适用**：为新系统设计选择基线算法；评审文档中算法结论；用 trace 或合成负载快速估算命中率。
- **不适用**：需要扫描抵抗/准入控制的场景（→ cache-algorithms-advanced）；学习型策略（→ learning-driven-cache）；分布式放置（→ distributed-cache-algorithms）。

## 2. 核心要点

1. LRU 在 IRM 下的命中率可用 Che et al. 闭式近似：`hit ≈ Σ p_i`，`p_i` 由不动点迭代求得（推导自 Che, Wang & Tung, INFOCOM 2003；项目公式对照表 B 级）。
2. LRU 实现为哈希表 + 双向链表：命中/插入/驱逐均 O(1)；精确 LFU 维护频率计数，工程实现多用近似结构（Redis 对数计数 + 时间衰减，见 05.05.02）。
3. FIFO 命中不提升对象位置，扫描负载下抗污染优于 LRU——这是 S3-FIFO/SIEVE 复兴的动机（SOSP'23/NSDI'24）。
4. MRU 仅在"刚被访问者最先驱逐"的循环扫描负载下有效，典型业务负载下接近最差，仅作理论对照。
5. Random 实现最简单且天然无锁，常作为低并发基线；其期望命中率与 FIFO 接近。
6. 常数因子差异主要来自指针追逐与缓存局部性，不是渐近复杂度（见 02.02 CPU 缓存与 05.05 算法实现）。
7. 驱逐窗口内的并发读写需锁或无锁设计；Redis 用采样驱逐缩短锁持有时间。

## 3. 权威速查

| 算法 | 数据结构 | 命中 | 插入 | 驱逐 | 扫描抵抗 | IRM 最优性 |
| ---- | -------- | ---- | ---- | ---- | -------- | ---------- |
| LRU | Hash+双向链表 | O(1) | O(1) | O(1) | 差 | 近似最优（Che 近似） |
| LFU | Hash+频率桶 | O(1) 近似 | O(1) | O(1) | 好 | 频率静态分布下最优 |
| FIFO | Hash+队列 | O(1) | O(1) | O(1) | 中 | 否 |
| MRU | 同 LRU | O(1) | O(1) | O(1) | 最差 | 否 |
| Random | Hash+数组 | O(1) | O(1) | O(1) | 中 | 否 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| LRU 原理与实现 | [01.01.01](../../../docs/01-理论基础/01.01-基础替换算法/01.01.01-LRU算法原理与实现.md) |
| LFU 原理与实现 | [01.01.02](../../../docs/01-理论基础/01.01-基础替换算法/01.01.02-LFU算法原理与实现.md) |
| FIFO / MRU / Random | [01.01.03](../../../docs/01-理论基础/01.01-基础替换算法/01.01.03-FIFO算法原理与实现.md) / [01.01.04](../../../docs/01-理论基础/01.01-基础替换算法/01.01.04-MRU算法原理与实现.md) / [01.01.05](../../../docs/01-理论基础/01.01-基础替换算法/01.01.05-Random随机替换算法.md) |
| 命中率近似公式出处 | [公式-文献对照表](../../../docs/00-项目总览/公式-文献对照表.md)（Che 近似，B 级） |
| Redis 近似 LRU/LFU | [05.05.01](../../../docs/05-全栈分析/05.05-算法层实现/05.05.01-近似LRU算法.md) / [05.05.02](../../../docs/05-全栈分析/05.05-算法层实现/05.05.02-LFU算法实现.md) |
| 基准测试方法 | [01.05.04](../../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) |

## 5. 常见任务工作流

### 任务 A：为新业务选基线算法

1. 判断负载：重用距离短尾→LRU；重尾+强热点→LFU；含扫描→FIFO 系。
2. 运行 `python scripts/benchmark/trace_benchmark.py` 跑合成 Zipf 对比（约 10 秒）。
3. 按 [01.05.04](../../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) §6 接入 MSR/Twitter 公开 trace 复核。
4. 输出：基线算法 + 预期命中率 + 风险，写入设计文档。

### 任务 B：核对文档结论

对照 §2 要点逐条核对 01.01.xx 文档；公式查 [公式-文献对照表](../../../docs/00-项目总览/公式-文献对照表.md) 是否登记；出入登记 STATUS.md 变更记录。

## 6. 国际前沿对齐（截至 2026-11）

- S3-FIFO（SOSP'23）与 SIEVE（NSDI'24）确立"FIFO 系可超越 LRU"的结论，Harvard Systems Group 2026-07 博客重申该谱系为当前默认推荐（https://systems.seas.harvard.edu/blog/fifo-is-all-you-need/）。
- libCacheSim PrefixSim（2026-11）把驱逐策略对比扩展到 LLM KV-block 前缀缓存（https://github.com/1a1a11a/libCacheSim）。
- 教学结论稳定：LRU/LFU 仍是基线与理论分析基准。

## 7. 验证命令

```bash
python scripts/benchmark/trace_benchmark.py            # 预期：LRU/LFU/S3-FIFO 命中率表（TC-BENCH-001）
python scripts/code_test_framework.py --test python    # 预期：0 失败（TC-DOC-001）
```

## 8. 权威参考

- **A 学术**：Che, Wang & Tung, INFOCOM 2003（Che 近似）；Albers, "Online Algorithms: A Study of Graph-Theoretic Concepts", 1996（竞争比）；Megiddo & Modha, FAST 2003（ARC 对照）
- **B 官方**：S3-FIFO SOSP'23（https://dl.acm.org/doi/10.1145/3600006.3613147）；SIEVE NSDI'24（https://www.usenix.org/conference/nsdi24/presentation/zhang-yazhuo）
- **C 工程**：cachemon 研究组（https://cachemon.github.io/）；libCacheSim（https://github.com/1a1a11a/libCacheSim）
