---
name: os-kernel-cache
description: 操作系统页缓存与现代内核机制（PageCache/BufferCache/Slab/MGLRU/DAMON/folio/PSI）的原理与调优；用于 OS 层缓存分析、内核版本选型
---

# 操作系统与内核缓存

> 覆盖经典 OS 缓存机制与 2022-2026 现代内核演进（MGLRU/DAMON/folio/PSI/io_uring buffered I/O）。

## 1. 概述与适用场景

- **覆盖**：Linux Page Cache/Buffer Cache/Slab/VFS；MGLRU、DAMON/DAMOS、folio、内存分层、PSI、zswap；Windows 缓存机制。
- **适用**：分析数据库/缓存在 OS 层的交互；选择内核版本与调优参数；评审 02.01/02.04 文档。
- **不适用**：用户态缓存设计（→ cache-architecture-patterns）；存储硬件栈（→ modern-storage-stack）。

## 2. 核心要点

1. Page Cache 以 folio（Linux 5.16+）为基本单元管理文件页，buffer_head 逐步退化为元数据角色；写回由 flusher 线程按 dirty 比例/时限触发（`vm.dirty_ratio`/`dirty_background_ratio`）。
2. MGLRU（Yu Zhao，合入 Linux 6.1）把 LRU 改为 4 代（young/old × file/anonymous），回收按代批量进行，内存压力下降频与老化更平滑；Android 与桌面是主要受益方。调优接口：`/sys/kernel/debug/lru_gen`（CONFIG_LRU_GEN）。
3. MGLRU 已知权衡：anonymous 页聚集在最新两代导致 swap 倾向偏高——2026 LSFMM 仍就此讨论（Honor/Android 工程师报告），生产用 swappiness 经验值需压测确定（C 级经验）。
4. DAMON（合入 5.15）提供启发式访问采样框架，DAMOS（5.16+）在其上执行回收/预读/分层策略，是"内核自治缓存策略"的载体；KVM 热页检测、CXL 分层是其落地场景。
5. PSI（Pressure Stall Information，4.20+）给内存/CPU/IO 压力提供十毫秒级 stall 指标，是缓存型服务 SLO 化调优的推荐输入（`pressure stall avg`）。
6. 分层内存：NUMA demotion + CXL 内存池 + zswap 构成"DRAM→zswap(CXL)→磁盘"多级缓存；分层介质下驱逐时机可用 DAMOS 触发。
7. Windows：Standby List/SuperFetch（SysMain）管理逻辑与 Linux 的 inactive/active 链表不同，内存分析要用 `RAMMap`/`poolmon` 工具链（见 02.01.05）。

## 3. 权威速查

| 机制 | 合入版本 | 关键接口/参数 | 状态（2026-11） |
| ---- | -------- | ------------- | --------------- |
| folio | 5.16 | address_space→i_mapping | 主线默认 |
| MGLRU | 6.1 | CONFIG_LRU_GEN, /sys/kernel/debug/lru_gen | 7.2 继续优化回收环与脏回写 |
| DAMON/DAMOS | 5.15/5.16 | CONFIG_DAMON, damo 工具 | 活跃演进 |
| PSI | 4.20 | /proc/pressure/* | 生产标配 |
| zswap | 3.11+ | zswap.enabled, compressor | 与 CXL 组合使用 |
| io_uring buffered I/O | 5.x-6.x 逐步 | IORING_OP_READ/WRITE | Linux 7.x 持续增强（FUSE over io_uring 6.17、bpf-ops） |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| Page Cache | [02.01.01](../../../docs/02-系统实现/02.01-操作系统缓存/02.01.01-Linux-Page-Cache机制.md) |
| Buffer Cache | [02.01.02](../../../docs/02-系统实现/02.01-操作系统缓存/02.01.02-Buffer-Cache实现.md) |
| Slab/VFS | [02.01.03](../../../docs/02-系统实现/02.01-操作系统缓存/02.01.03-Slab分配器.md) / [02.01.04](../../../docs/02-系统实现/02.01-操作系统缓存/02.01.04-VFS文件系统缓存.md) |
| Windows | [02.01.05](../../../docs/02-系统实现/02.01-操作系统缓存/02.01.05-Windows系统缓存机制.md) |
| 现代内核总览 | [02.04 README](../../../docs/02-系统实现/02.04-现代内核缓存机制/README.md) |
| 新存储栈 | [02.04.01](../../../docs/02-系统实现/02.04-现代内核缓存机制/02.04.01-新存储栈缓存技术.md) |
| NUMA/HugePages | [02.05.01](../../../docs/02-系统实现/02.05-系统级优化/02.05.01-NUMA架构优化.md) / [02.05.02](../../../docs/02-系统实现/02.05-系统级优化/02.05.02-HugePages大页内存.md) |
| NUMA 影响分析 | [05.01.02](../../../docs/05-全栈分析/05.01-硬件层深度剖析/05.01.02-NUMA架构影响.md) |

## 5. 常见任务工作流

### 任务 A：内核缓存性能分析

1. 采集：`vmstat 1`、`/proc/meminfo`（Active/Inactive/Dirty/Writeback）、PSI `/proc/pressure/memory`。
2. 若 MGLRU 开启，读 `lru_gen` 代数分布判断老化是否充分。
3. 脏页积压→调 `dirty_background_ratio` 与 flusher 间隔；匿名页挤占→调 `swappiness` 并验证。
4. 输出：参数变更 + 压测前后 stall 对比。

### 任务 B：内核版本选型

对照 §3 速查表确认目标功能（MGLRU/DAMOS/PSI）的合入版本；LTS 线 6.12 起包含全部现代机制；6.18 为新 GKI 基线，7.0（2026-04）/7.2（2026-08）含 MGLRU 改进（来源：kernelnewbies LinuxChanges）。

## 6. 国际前沿对齐（截至 2026-11）

- Linux 7.0（2026-04-12）与 7.2（2026-08-16）发布；7.2 清理并改进 MGLRU 回收环与脏回写处理（kernelnewbies.org/LinuxChanges）。
- 2026 LSFMM 讨论焦点：MGLRU anonymous-vs-file 平衡、MGLRU 的 cgroup 扩展（tux.fan 2026-07 综述）。
- DAMON 应用场景扩展到 CXL 分层与虚拟机热页检测（lkml 持续 patch）。

## 7. 验证命令

```bash
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
uname -r    # 人工：确认目标主机内核 ≥6.1（TC-OPS-内核前提）
```

## 8. 权威参考

- **A 学术**：Zhao et al., MGLRU 报告（2021, Linux 6.1）；Seo et al., "DAMON: Data Access Monitoring"（2021, 5.15）；O'Neil et al., SIGMOD 1993（LRU-K，页缓存理论源头）
- **B 官方**：kernelnewbies LinuxChanges（https://kernelnewbies.org/LinuxChanges）；LKML/LSFMM 纪要（https://lore.kernel.org/lkml/）；内核文档 admin-guide/mm
- **C 工程**：tux.fan MGLRU 状态综述（2026-07）；Android GKI 说明
