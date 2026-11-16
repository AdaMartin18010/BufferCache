# 02.04 现代内核缓存机制

## 目录

- [02.04 现代内核缓存机制](#0204-现代内核缓存机制)
  - [目录](#目录)
  - [1. 概述](#1-概述)
    - [1.1 演进时间线](#11-演进时间线)
    - [1.2 与传统机制的衔接](#12-与传统机制的衔接)
  - [2. Folio：页缓存的统一抽象](#2-folio页缓存的统一抽象)
  - [3. MGLRU：多代 LRU 替换](#3-mglru多代-lru-替换)
    - [3.1 设计动机](#31-设计动机)
    - [3.2 核心机制](#32-核心机制)
    - [3.3 工作流](#33-工作流)
    - [3.4 关键参数](#34-关键参数)
    - [3.5 性能特征](#35-性能特征)
  - [4. DAMON/DAMOS：数据访问监控与自动操作](#4-damondamos数据访问监控与自动操作)
    - [4.1 设计动机](#41-设计动机)
    - [4.2 基于采样的访问监控](#42-基于采样的访问监控)
    - [4.3 DAMOS：访问模式驱动的自动化](#43-damos访问模式驱动的自动化)
    - [4.4 自适应分层（Self-tuned Tiering）](#44-自适应分层self-tuned-tiering)
  - [5. 内存分层与 NUMA 优化](#5-内存分层与-numa-优化)
    - [5.1 内核 NUMA 均衡与 demotion](#51-内核-numa-均衡与-demotion)
    - [5.2 CXL 内存分层](#52-cxl-内存分层)
    - [5.3 AutoNUMA 的局限与演进](#53-autonuma-的局限与演进)
  - [6. 配套机制](#6-配套机制)
    - [6.1 PSI 内存压力检测](#61-psi-内存压力检测)
    - [6.2 zswap 与 swap 演进](#62-zswap-与-swap-演进)
    - [6.3 io\_uring 与 Buffered I/O](#63-io_uring-与-buffered-io)
  - [7. 观测与调优](#7-观测与调优)
  - [8. 经典缓存理论在内核中的映射](#8-经典缓存理论在内核中的映射)
  - [9. 扩展阅读](#9-扩展阅读)
  - [10. 权威参考](#10-权威参考)
    - [10.1 内核文档与论文](#101-内核文档与论文)
    - [10.2 在线资源](#102-在线资源)

---

## 1. 概述

### 1.1 演进时间线

Linux 内核页面缓存（Page Cache）与内存回收机制在 2021-2025 年发生了系统性重构：

| 时间 | 内核版本 | 机制 | 影响 |
| ---- | -------- | ---- | ---- |
| 2021 | 5.15 | NUMA demotion、swap 优化 | 内存分层的基础 |
| 2021 | 5.16 | **folio** 抽象引入 | page cache 数据结构的根基重构 |
| 2022 | 6.1 | **MGLRU**（Multi-Gen LRU）合入、maple tree | 默认页面替换算法的代际更替 |
| 2022+ | 6.x | DAMON/DAMOS 持续增强 | 访问监控驱动的自动内存管理 |
| 2024 | 6.11+ | MM 子系统大页缓存优化 | 大 folio、回收路径加速 |
| 2025 | 6.14+ | Uncached Buffered I/O、DAMON 自适应分层 | 缓存与分层策略自动化 |

### 1.2 与传统机制的衔接

[02.01 操作系统缓存](../02.01-操作系统缓存/02.01.01-Linux-Page-Cache机制.md) 描述的是经典的 LRU 双链表（active/inactive）+ rmap 回收机制（2.6 至 5.x 年代的设计）。本节聚焦其继任者：

- **替换算法**：active/inactive LRU → MGLRU（多代）
- **数据抽象**：struct page 单页 → folio（复合页）
- **访问理解**：无监控 → DAMON 低开销访问模式采集
- **分层管理**：手动 + 启发式 → DAMON/DAMOS + NUMA demotion 自动化

## 2. Folio：页缓存的统一抽象

**Folio** 将一组物理连续的 page 封装为单一管理单元，统一了 page cache、anonymous memory、buffer head 三条历史上分裂的路径：

- **Large folio**：page cache 可以按 2MB（PMD 级）大单元缓存文件数据，减少页表遍历与元数据开销，提升大顺序 I/O 性能
- **去 buffer head 化**：folio 内部直接管理块偏移，逐步淘汰 buffer head 层
- **对 MGLRU 的支撑**：MGLRU 的批量操作以 folio 为单位，大 folio 显著降低扫描开销

**工程意义**：传统上"页缓存单元 = 4KB page"的假设被打破，缓存管理的粒度成本（每页元数据、每页 rmap）随大 folio 摊薄——这是现代内核能在更大数据集上维持替换算法高效的前提。

## 3. MGLRU：多代 LRU 替换

### 3.1 设计动机

经典 LRU（内核的 active/inactive 双链表实现）的问题：

1. **链表维护开销**：每次访问都要把 page 移到 LRU 头部（内存中的链表操作），在大量页面上成为显著 CPU 开销
2. **不区分访问模式**：一次顺序扫描（如备份任务）即可污染整个 inactive 链表，驱逐真正热的数据
3. **与交换设备脱节**：回收决策不考虑交换设备的速度（NVMe swap 与 HDD swap 应有不同策略）
4. **rmap 遍历低效**：回收时按 rmap 顺序遍历，无访问信息利用

### 3.2 核心机制

MGLRU（Multi-Generation LRU，Yu Zhao，Linux 6.1 合入）将页面组织为 **4 个代（generation）**：

```
gen 3（最年轻） ← 最近被多次访问的页面
gen 2
gen 1
gen 0（最老）  ← 最久未访问，首先被回收
```

**核心操作**：

- **aging（老化）**：把各代的访问位批量收集，达到阈值的年轻代页面晋升（promotion），最老代无访问位则淘汰出代
- **eviction（驱逐）**：从最老代开始扫描，利用 rmap 检查 PTE Accessed bit，二次机会——被引用的页面晋升到最年轻代，未被引用的回收
- **访问感知免链表移动**：页面访问只设置硬件 Accessed bit，**不移动链表节点**——批量在 aging 时处理，大幅降低热路径开销

### 3.3 工作流

1. 访问发生 → 硬件置 PTE Accessed 位（零软件开销）
2. aging 触发（kswapd 或 direct reclaim）→ 扫描各代，按 Accessed 位决定晋升/驻留/驱逐
3. 驱逐优先选择：最老代 × 未被访问 × 干净的页（无回写成本）
4. 交换设备感知：swappiness 与交换带宽动态调整回收积极性

### 3.4 关键参数

| sysfs 接口 | 含义 | 调优 |
| ---------- | ---- | ---- |
| `/sys/kernel/mm/lru_gen/enabled` | 开关（0x0001=单调时钟, 0x0002=主开关, 0x0004=切页, 0x0008=写回） | 默认 0x7 |
| `min_ttl_ms` | 页面最短驻留时间 | 防止抖动场景的快速驱逐 |
| `swappiness` | 匿名页 vs 文件页回收倾向 | MGLRU 下语义更精确 |

### 3.5 性能特征

- **Web 服务器/数据库负载**：命中率提升，回收 CPU 开销下降（active/inactive 链表操作消除）
- **扫描抵抗**：顺序读不再大规模污染（代际结构天然隔离）
- **Android/ChromeOS**：已默认启用多年，改善内存压力下的卡顿（jank）
- **已知边界**：极小内存（<1GB）嵌入式场景收益有限；与HugeTLB路径交互仍需关注

## 4. DAMON/DAMOS：数据访问监控与自动操作

### 4.1 设计动机

内核长期缺乏**低开销的访问模式观测手段**：精确页级追踪（如 perf、BPF 遍历页表）开销 5-30%，无法生产常驻。DAMON（Data Access MONitor）目标：以 **<1% 开销**获得"足够好"的访问热度图。

### 4.2 基于采样的访问监控

DAMON 的核心是**区域采样（region-based sampling）**：

1. 将目标地址空间划分为区域（region）
2. 定期采样各区域的访问位（Accessed bit）——**不追踪单个页面**
3. 根据访问密度自动调整区域划分（访问密集区细分、稀疏区合并）
4. 输出：各区域的访问频率统计（冷热图）

开销分析：采样频率低（默认可配置）、粒度粗（区域而非页）、无需页表遍历之外的结构——合计 <1% CPU。精度损失（区域平均）对"冷热分层"决策是可接受的。

### 4.3 DAMOS：访问模式驱动的自动化

DAMOS（DAMon-based OperationS）将监控接入动作管线：

```
访问监控（DAMON）→ 模式匹配（如"3 秒内访问 < N 次的区域"）→ 动作执行
动作类型：
- pageout：回收冷页（先于 LRU 压力触发，主动腾出内存）
- pageout+activate：特殊激活语义
- promotion/demotion：分层内存间迁移
- huge page 管理：大页拆分/合成决策
```

**生产案例**：Amazon（EC2）公开报告将 DAMON 用于实例内存分层与回收优化，显著降低 OOM 与回收抖动。

### 4.4 自适应分层（Self-tuned Tiering）

2025 年的重要演进（Linux 6.15 前后）：DAMON-based tiering 支持**自调参**——无需手动配置冷热阈值，根据分层效果反馈自动调整 promotion/demotion 策略参数（LWN: "DAMON self-tuned memory tiering"，生产服务器上显示出显著收益）。

## 5. 内存分层与 NUMA 优化

### 5.1 内核 NUMA 均衡与 demotion

传统 NUMA 均衡（AutoNUMA）将页迁移到访问它的节点（promotion 到本地）。5.15+ 引入 **demotion 路径**：当本地节点内存不足时，优先将冷页**降级**到其他节点的内存（而非直接 swap 到磁盘）：

- demotion 目标节点按"距离 + 空闲量"选择
- 与 MGLRU 集成：驱逐候选页优先 demotion 而非 swap-out
- 效果：多路服务器上 swap 流量大幅下降（内存即缓存的层级扩大）

### 5.2 CXL 内存分层

CXL（Compute Express Link）内存的上线使"内存分层"从 NUMA 间扩展为机架级：

- CXL 内存呈现为慢速 NUMA 节点（带宽约为本地 DDR 的 1/2 到 1/4，延迟 +50-200ns）
- 内核视角：DRAM = 快层，CXL = 慢层，SSD swap = 最慢层
- DAMON tiering 自动管理 DRAM↔CXL 间的 promotion/demotion
- 详见 [02.02.06 新型存储介质缓存架构](../02.02-CPU缓存架构/02.02.06-新型存储介质缓存架构.md)

### 5.3 AutoNUMA 的局限与演进

AutoNUMA（地址采样 + unmapping 压力迁移）的开销与"错误迁移"长期受诟病。现代替代路径：

- DAMON tiering：更细粒度、更明确的冷热语义
- 分层 demotion：接受"页留在远端"而非强制回迁（带宽换容量）
- 应用层 hint（`madvise` NUMA hinting）：与内核策略协同

## 6. 配套机制

### 6.1 PSI 内存压力检测

PSI（Pressure Stall Information）提供"某任务因内存回收等待的时间占比"（/proc/pressure/memory），是 MGLRU/DAMOS 调优与容器内存限流（cgroup v2 memory.high 配合）的核心观测指标。

### 6.2 zswap 与 swap 演进

- **zswap**：swap 前的压缩层（RAM 中的压缩缓存），对冷页先压缩驻留内存，再决定是否落盘——"缓存层级"思维进入 swap 路径
- **zram**：压缩内存块设备，嵌入式/桌面默认
- **MGLRU 与 zswap 协同**：MGLRU 的代际信息可用于选择"值得压缩驻留"的页

### 6.3 io_uring 与 Buffered I/O

io_uring 最初面向直接 I/O 的异步化；2025 年（6.14+）的 uncached buffered I/O 等工作将异步接口扩展到页缓存路径，减少对 buffered read/write 的 syscall 轮询。详见 [05.02.04 io_uring异步IO](../../05-全栈分析/05.02-网络通信层/05.02.04-io_uring异步IO.md)。

## 7. 观测与调优

```bash
# MGLRU 状态
cat /sys/kernel/mm/lru_gen/enabled
cat /sys/kernel/debug/lru_gen  # 各代页面数

# DAMON 工具（damo）
damo record --output access_pattern.data <pid>
damo report access_pattern.data
damo tune --demo  # 自适应分层演示

# PSI
cat /proc/pressure/memory

# 回收统计
grep -E "pgscan|pgsteal|pgdemote" /proc/vmstat
```

**调优决策树**：

1. 内存充足但回收抖动 → 检查 MGLRU min_ttl_ms、PSI 指标
2. 多节点服务器 swap 高 → 启用 demotion、DAMON tiering
3. CXL/分层部署 → DAMON self-tuned tiering（内核 6.15+）
4. 容器密集 → PSI + cgroup v2 memory.high

## 8. 经典缓存理论在内核中的映射

| 经典理论 | 内核实现 |
| -------- | -------- |
| 工作集模型 | MGLRU 代际 ≈ 多窗口工作集估计 |
| LRU 竞争比 | MGLRU 仍受 $k$ 界约束，但扫描抵抗性远超双链表 LRU |
| 分层缓存理论（穿透/本地性） | DRAM/CXL/swap 三级与 demotion/promotion |
| 访问驱动驱逐（LFU 谱系） | DAMON 访问密度 ≈ 区域级频率统计 |
| 准入控制（TinyLFU 思想） | DAMOS "冷页提前 pageout" ≈ 主动准入管理 |
| 懒惰晋升（S3-FIFO/SIEVE） | MGLRU 免热路径链表移动、批量晋升 |

## 9. 扩展阅读

- [Linux Page Cache机制](../02.01-操作系统缓存/02.01.01-Linux-Page-Cache机制.md) - 经典双链表机制
- [新型存储介质缓存架构](../02.02-CPU缓存架构/02.02.06-新型存储介质缓存架构.md) - PMem/CXL
- [NUMA架构优化](../02.05-系统级优化/02.05.01-NUMA架构优化.md) - NUMA 基础
- [内存管理] - 程序设计实践中的内存层次
- [LLM KV Cache分层](../../04-架构设计/04.03-行业应用场景/04.03.15-大模型推理缓存架构.md) - 同样的分层思想在推理系统

## 10. 权威参考

### 10.1 内核文档与论文

- Yu Zhao, "Multi-Gen LRU Framework" 系列补丁与文档：`Documentation/mm/multigen_lru.rst`（Linux 内核源码）
- DAMON 官方文档：`Documentation/mm/damon/index.rst`；项目站 <https://damonitor.github.io/>
- SeongJae Park (DAMON 作者), "Preparing DAMON for future memory-management problems," *LWN.net*, 2025-04
- "DAMON Self-Tuned Memory Tiering Shows Nice Improvement For Linux Servers," *Phoronix*, 2025-03
- LWN: "MGLRU" 系列报道（2021-2023）；Linux 6.1/6.14/6.15 release notes

### 10.2 在线资源

- LWN.net MM 子系统报道： <https://lwn.net/Kernel/Index/>
- DAMO 用户空间工具： <https://github.com/damonitor/damo>
