---
name: cache-algorithms-advanced
description: 高级缓存替换算法（ARC/2Q/SLRU/CLOCK-Pro/LHD/W-TinyLFU/S3-FIFO/SIEVE）的机制、场景与形式化验证；用于扫描抵抗设计、准入控制选型与 TLA+ 规约评审
---

# 高级缓存替换算法

> 覆盖带准入控制、分层、扫描抵抗的高级算法与 TLA+ 形式化验证，是生产缓存的选型层。

## 1. 概述与适用场景

- **覆盖**：ARC、2Q、SLRU、CLOCK-Pro、LHD、W-TinyLFU、S3-FIFO、SIEVE；项目 TLA+ 规约方法。
- **适用**：需要扫描抵抗、准入控制或自适应调参的生产选型；评审 01.02 系列文档；写/改 TLA+ 规约。
- **不适用**：基线概念（→ cache-algorithms-fundamentals）；学习型策略（→ learning-driven-cache）；命中率快速估算（→ §5 任务 B）。

## 2. 核心要点

1. 准入控制是抗扫描的第一道闸门：W-TinyLFU 用 Count-Min Sketch 门控 admission（窗口 LRU + 主段 SLRU + TinyLFU 计数，Caffeine 实现）；S3-FIFO 用 S（small FIFO）做隐式准入（SOSP'23）。
2. ARC 用 T1/T2/B1/B2 四结构自适应平衡 recency 与 frequency，O(1) 操作，对扫描鲁棒（FAST 2003）。
3. 2Q（VLDB 1994）与 SLRU 是 FIFO/LRU 的分层组合：2Q 用 Kin/Kout 队列缓解 LRU 的扫描污染；SLRU 用 probation/protected 两段。
4. CLOCK-Pro 把 CLOCK 变体推向 O(1) 近似 LFU 行为，是 Linux 页缓存时钟框架的算法参照（ATC 2005）。
5. LHD 以"命中密度 = 命中次数 / 字节秒占用"为优化目标，适合异构大小对象缓存（NSDI 2018）。
6. SIEVE 单队列 + 单指针 + visited bit，命中仅置位，驱逐从队尾扫描淘汰未访问者；工程上以 ~100-150 LOC 实现，ScyllaDB 2026-03 评估后选其替代 SLRU（NSDI 2024）。
7. 形式化：项目 LRU/ARC 规约（01.05.06）已 TLC 验证通过（LRU 69 状态、ARC 1909 状态）；活性性质需用强公平性（SF）假设，弱公平性（WF）会漏报（项目实测结论，登记 01.05.06）。

## 3. 权威速查

| 算法 | 准入控制 | 扫描抵抗 | 元数据/对象 | 代表实现 |
| ---- | -------- | -------- | ----------- | -------- |
| ARC | 自适应双链 | 好 | 4 指针/对象 | Linux?（思想参照）、ZFS ARC |
| 2Q | Kin/Kout | 好 | 2 队列+指针 | PostgreSQL（Clock-Sweep 变体） |
| SLRU | 分段提升 | 中-好 | 2 段指针 | varnish、ScyllaDB（原方案） |
| CLOCK-Pro | 引用位周期 | 好 | 1 bit+指针 | Linux 时钟框架参照 |
| LHD | 命中密度排序 | 中 | 大小+年龄 | Cassandra 思路 |
| W-TinyLFU | CMS 计数门控 | 好 | sketch 计数 | Caffeine |
| S3-FIFO | S 段隐式 | 好 | 3 FIFO 指针 | Google/VMware/Redpanda |
| SIEVE | visited bit | 好 | 1 bit+指针 | ScyllaDB（2026） |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| ARC | [01.02.04](../../../docs/01-理论基础/01.02-高级替换算法/01.02.04-ARC自适应替换缓存.md) |
| LRU-K / 时钟 | [01.02.05](../../../docs/01-理论基础/01.02-高级替换算法/01.02.05-LRU-K算法.md) / [01.02.06](../../../docs/01-理论基础/01.02-高级替换算法/01.02.06-Clock时钟扫描算法.md) |
| W-TinyLFU | [01.02.07](../../../docs/01-理论基础/01.02-高级替换算法/01.02.07-W-TinyLFU算法分析.md) |
| SLRU/2Q | [01.02.08](../../../docs/01-理论基础/01.02-高级替换算法/01.02.08-SLRU与2Q算法.md) |
| CLOCK-Pro/LHD | [01.02.09](../../../docs/01-理论基础/01.02-高级替换算法/01.02.09-CLOCK-Pro与LHD算法.md) |
| S3-FIFO/SIEVE 深度篇 | [01.02.10](../../../docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md) |
| TLA+ 规约与验证 | [01.05.06](../../../docs/01-理论基础/01.05-算法对比与决策/01.05.06-缓存算法TLA形式化规约.md)；[scripts/formal/](../../../scripts/formal/) |
| 数学证明 | [01.05.05](../../../docs/01-理论基础/01.05-算法对比与决策/01.05.05-算法实现的数学证明.md) |

## 5. 常见任务工作流

### 任务 A：生产选型

1. 对象大小是否异构？是→LHD 或分桶缓存。
2. 是否有批量扫描（报表/全量遍历）？是→必须有准入或 FIFO 系（S3-FIFO/SIEVE/W-TinyLFU）。
3. 更新率极高、写多？→SIEVE（hit 仅置位，写放大最小）。
4. 内存极受限元数据？→SIEVE（24 B/对象，ScyllaDB 实测对比）或 CLOCK 系。
5. 用 [01.05.04](../../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) 的 trace 框架跑候选集，输出命中率-延迟权衡表。

### 任务 B：TLA+ 规约评审

1. 对照 [01.05.06](../../../docs/01-理论基础/01.05-算法对比与决策/01.05.06-缓存算法TLA形式化规约.md) 检查状态变量与不变量。
2. 活性性质确认 SF 假设；WF 假设漏报已在 ARC 验证中发现并修正。
3. 改规约后运行 `scripts/formal/run.bat`（Windows）或 tlc2tools.jar（跨平台）。

## 6. 国际前沿对齐（截至 2026-11）

- S3-FIFO 已部署于 Google、VMware、Redpanda；SIEVE 进入 ScyllaDB prepared-statement cache（2026-03 评估，SIEVE 以零命中路径开销胜出）；两算法已进入多语言标准库（Go/Python/Rust/Java 等）。
- libCacheSim PrefixSim（2026-11）支持 40+ 驱逐策略在 LLM 前缀缓存上的对比（https://github.com/1a1a11a/libCacheSim）。
- 学术谱系综述确认"FIFO 系 + 轻量元数据"为 2023-2026 主流演进方向（Harvard Systems Group, 2026-07）。

## 7. 验证命令

```bash
scripts/formal/run.bat                 # 预期：LRU/ARC TLC 全性质通过（TC-FORM-001）
python scripts/benchmark/trace_benchmark.py   # 预期：S3-FIFO 扫描负载下优于 LRU（TC-BENCH-001）
```

## 8. 权威参考

- **A 学术**：Megiddo & Modha, FAST 2003（ARC）；Johnson & Shasha, VLDB 1994（2Q）；Karedla et al., IEEE Computer 1994（SLRU）；Jiang et al., USENIX ATC 2005（CLOCK-Pro）；Beckmann et al., NSDI 2018（LHD）；Einziger et al., ICDCS 2017（TinyLFU）；Yang et al., SOSP 2023（S3-FIFO）；Zhang et al., USENIX NSDI 2024（SIEVE）
- **B 官方**：USENIX NSDI'24 SIEVE 论文页；ScyllaDB issue #29047 评估记录（https://github.com/scylladb/scylladb/issues/29047）
- **C 工程**：Caffeine（https://github.com/ben-manes/caffeine）；libCacheSim；cachemon（https://cachemon.github.io/）
