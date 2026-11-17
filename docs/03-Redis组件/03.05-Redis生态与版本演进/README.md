# 03.05 Redis版本演进与开源生态

## 目录

- [03.05 Redis版本演进与开源生态](#0305-redis版本演进与开源生态)
  - [目录](#目录)
  - [1. 概述](#1-概述)
  - [2. 许可变迁时间线](#2-许可变迁时间线)
  - [3. Redis 8：整合与新特性](#3-redis-8整合与新特性)
    - [3.1 AGPLv3 三重许可](#31-agplv3-三重许可)
    - [3.2 模块整合进核心](#32-模块整合进核心)
    - [3.3 向量支持（Vector Set）](#33-向量支持vector-set)
    - [3.4 其他重要改进](#34-其他重要改进)
    - [3.5 Redis 8.2 与 8.4（2025-11 GA）](#35-redis-82-与-842025-11-ga)
  - [4. 分叉生态](#4-分叉生态)
    - [4.1 Valkey（Linux 基金会）](#41-valkeylinux-基金会)
    - [4.2 Redict（LGPL 独立分支）](#42-redictlgpl-独立分支)
    - [4.3 KeyDB（多线程路线）](#43-keydb多线程路线)
    - [4.4 Dragonfly（C++ 重写）](#44-dragonflyc-重写)
    - [4.5 Garnet（微软 RESP 实现）✨ **前沿更新（2026-11）**](#45-garnet微软-resp-实现-前沿更新2026-11)
  - [5. 生态对比矩阵](#5-生态对比矩阵)
  - [6. 选型决策指南](#6-选型决策指南)
  - [7. 对本项目文档的影响](#7-对本项目文档的影响)
  - [8. 扩展阅读](#8-扩展阅读)
  - [9. 权威参考](#9-权威参考)

---

## 1. 概述

2024-2025 年的许可变迁使 Redis 生态发生了自 2009 年项目诞生以来最大的分裂与重组：Redis 公司（Redis Ltd.）变更许可证引发社区反弹，Linux 基金会主导的 Valkey 分叉诞生；随后 Redis 8 以 AGPLv3 回归 OSI 认可的开源许可，并将原 Redis Stack 模块整合进核心。本节记录这一完整脉络，并给出各替代实现的技术对比与选型建议。

## 2. 许可变迁时间线

| 时间 | 事件 | 影响 |
| ---- | ---- | ---- |
| 2024-03-20 | Redis 宣布从 BSD 改为 **RSALv2 + SSPLv1** 双许可（7.4 起） | 两种许可均非 OSI 认可；目的为限制云厂商托管转售 |
| 2024-03-22 | Drew DeVault 宣布 **Redict**（LGPLv3 独立分支） | 保留"真开源"传统 |
| 2024-03-28 | Linux 基金会联合 AWS、Google、Oracle 等宣布 **Valkey** | 获得主流云厂商与 Linux 发行版支持 |
| 2024-04-03 | Redict 7.3.0 首个稳定版 | 基于 Redis 7.2 代码 |
| 2024 年内 | Fedora、Debian、Ubuntu 等发行版陆续用 Valkey 替换 Redis | 生态重心转移 |
| 2025-05-01 | **Redis 8.0 发布**，新增 **AGPLv3** 作为第三许可选项 | "重归开源"（OSI 认可），保留 RSALv2/SSPLv1 选项；antirez 回归 |
| 2025 年后 | Valkey 持续重写底层（异步删除、io_uring、新复制等），版本基线停在 7.2.4 | 双生态长期并存格局确立 |

**背景知识**：RSALv2（Redis 源可用许可）禁止将软件作为托管服务提供给第三方；SSPLv1 要求提供服务的开源全部栈代码——两者都针对云厂商，但触发 OSI"开源定义"第 6 条（不得歧视领域）争议。AGPLv3 是 OSI 认可的强 copyleft 许可，网络服务使用即触发源代码提供义务——对多数企业内部使用无实质负担，但进入法律审查清单。

## 3. Redis 8：整合与新特性

### 3.1 AGPLv3 三重许可

Redis 8 起，用户可在 **RSALv2 / SSPLv1 / AGPLv3** 三选一：

- **AGPLv3**：OSI 认可的开源选项；内部使用与大多数 SaaS 场景可接受，对外提供网络服务需开放修改后的源码
- **RSALv2/SSPLv1**：保留给需要避免 AGPLv3 copyleft 义务的商业场景
- **实践影响**：企业选型需过法律审查；追求"纯开源供应链"的组织仍可能偏好 Valkey/Redict

### 3.2 模块整合进核心

原 Redis Stack 的商业/增值模块在 Redis 8 中整合进开源核心：

| 原模块 | Redis 8 状态 | 能力 |
| ------ | ------------ | ---- |
| RediSearch | 整合为核心搜索能力 | 全文检索、二级索引、向量检索（早期） |
| RedisJSON | 整合 | JSON 数据类型与路径查询 |
| RedisTimeSeries | 整合 | 时序数据类型、降采样、聚合 |
| RedisBloom | 整合 | Bloom/Cuckoo/Count-Min/Top-K 过滤器 |

**架构意义**：模块 API（Redis Modules API）仍是扩展机制，但"常用数据结构全家桶"不再需要单独安装 Stack——与本项目 [03.01 核心数据结构](../03.01-核心数据结构/) 的关系需要以"6.x 独立模块 / 8.x 内置"两个口径理解。

### 3.3 向量支持（Vector Set）

Redis 8.0 将**向量集（Vector Set）**做进内核：`VADD`、`VSIM` 等命令原生支持向量存储与相似度检索（HNSW 索引），面向"缓存旁挂向量库"的 AI 应用模式。这是当前与 Valkey 最实的功能分水岭之一（Valkey 源码树尚无 vector set）。

### 3.4 其他重要改进

- **性能**：多种命令路径优化、内存效率提升
- **RDB 版本演进**：持久化格式版本更新
- **安全与运维**：ACL、TLS 持续增强
- **注意**：部分企业版功能（如 Redis on Flash 系列路线）与开源版的能力边界需以官方文档为准；Redis on Flash 已退役，由 Auto-Tiering（企业版）接替

### 3.5 Redis 8.2 与 8.4（2025-11 GA）

- **Redis 8.2**：向量集能力增强（GA 化路线）、性能持续优化
- **Redis 8.4**（2025-11-25 GA）：
  - **混合全文 + 向量检索**：Search 与 Vector Set 的统一查询路径，AI 检索场景的原生支持
  - **吞吐提升**：官方公布缓存与搜索场景 30%+ 吞吐改进
  - **原子操作改进**：多步操作的原子化增强
  - 注意：8.4 早期版本修复了 Vector Set 从 RDB 加载的越界访问、VREM 释放后使用等安全缺陷（升级前阅读 release notes）

## 4. 分叉生态

### 4.1 Valkey（Linux 基金会）

- **背景**：2024 年许可变更后由 Linux 基金会托管，AWS、Google Cloud、Oracle、Ericsson 等参与
- **许可证**：BSD 3-Clause（继承 Redis 7.2 的许可）
- **技术路线**：以 7.2.4 为基线，系统性重写底层：
  - 异步删除（lazyfree 增强）
  - 新复制实现（磁盘负载降低）
  - io_uring 批量写（roadmap）
  - Active/Active 双活（高需求，开发中）
  - 线程化 I/O 持续增强
- **短板**：尚无 vector set；版本号长期保持 7.2.x（语义：与 Redis 7.2 协议/API 兼容基线），功能差异通过 release notes 说明
- **生态地位**：多数 Linux 发行版的默认 redis 替代品；云厂商托管服务逐步转向 Valkey

### 4.2 Redict（LGPL 独立分支）

- **背景**：Drew DeVault（SourceHut 创始人）主导，2024-03-22 宣布
- **许可证**：LGPLv3——比 BSD 更严格的 copyleft，确保分支自身永远开源
- **定位**：保守稳定路线，跟随修复，不追求大规模重写
- **现状**：维护节奏平稳，社区规模小于 Valkey

### 4.3 KeyDB（多线程路线）

- **背景**：早于许可变更（2019 年，Snap 公司），多线程 Redis 分支
- **特点**：多线程处理命令（shared-nothing 数据分片 + 全局锁细化）、Active Replica 多主
- **与主线的关系**：Redis 6 引入 I/O threading 后部分价值被稀释；仍作为多线程路线的参考实现

### 4.4 Dragonfly（C++ 重写）

- **定位**：C++ 全新实现的内存数据存储，兼容 Redis 协议子集
- **架构**：shared-nothing 线程模型（每核分片）、无 fork 的持久化（shared-nothing snapshot）、密集内存优化（小对象紧凑布局）
- **性能**：宣称高吞吐（多核线性扩展），适合纯缓存大 keyspace 场景
- **注意**：API 兼容性非 100%（模块、部分命令与 Lua 语义差异需验证）

### 4.5 Garnet（微软 RESP 实现）✨ **前沿更新（2026-11）**

> Garnet 已由工程作品升级为顶会论文：Chandramouli et al., "Garnet: A Next-Generation Cache-Store for Accelerating Applications and Services", **VLDB 2026**；NuGet 最新 2.2.0。从数据库视角重构缓存存储（大于内存的缓存 / AOF / 检查点三层存储用途 + IDevice 抽象），RESP 协议兼容。


- **定位**：微软研究院 C#/.NET 实现的 RESP 协议缓存存储
- **特点**：与 Azure 生态集成、分片集群支持、Lua 兼容层
- **场景**：.NET 技术栈与 Azure 部署优先考虑

## 5. 生态对比矩阵

| 维度 | Redis 8 | Valkey | Redict | KeyDB | Dragonfly | Garnet |
| ---- | ------- | ----- | ------ | ----- | --------- | ------ |
| 许可 | AGPLv3/RSALv2/SSPLv1 | BSD-3 | LGPLv3 | BSD-3 | BSL（转 OSS） | MIT |
| 基线 | 8.x（持续演进） | 7.2.4 基线+重写 | 7.2 基线 | 7.x 基线 | 全新 C++ | 全新 C# |
| 多线程 | I/O threading | I/O threading | I/O threading | 全命令多线程 | 全命令多线程 | async/线程池 |
| 向量检索 | ✅ 内置 Vector Set | ❌（roadmap 讨论中） | ❌ | ❌ | ❌ | ❌ |
| 模块生态 | ✅ 完整 | 兼容 | 兼容 | 部分 | ❌ | 部分 |
| 云厂商托管 | Redis Cloud/各云 | AWS ElastiCache(for Valkey)等 | 少 | 少 | 部分 | Azure |
| 协议兼容 | RESP2/3 | RESP2/3 | RESP2 | RESP2 | RESP2 子集 | RESP2/3 |

## 6. 选型决策指南

```text
是否需要向量检索（VADD/VSIM）？
├── 是 → Redis 8（唯一内置向量集的主流选项）
└── 否 → 是否有强烈的"OSI 纯开源供应链"要求？
    ├── 是 → 发行版兼容性优先选 Valkey；copyleft 洁癖选 Redict
    └──── 否 → 需要最大化多核吞吐（大 keyspace 纯缓存）？
        ├── 是 → 评估 Dragonfly / KeyDB（先验证命令兼容）
        └── 否 → 传统场景继续 Redis 8（功能最全）或 Valkey（成本与治理友好）
```

**迁移注意事项**：

1. RDB/AOF 文件在 Redis 7.2 基线产品间可互导（高版本向低版本导出需验证）
2. 模块依赖（如 RedisJSON 独立模块）在整合版中的命令行为可能有细微差异
3. 客户端库（redis-py 等）对各分叉的兼容性需逐版本验证
4. 监控指标命名、INFO 字段在不同实现间存在差异

## 7. 对本项目文档的影响

本项目的 Redis 深度文档（[03.01-03.07](../)）主要基于 Redis 6.x/7.x 源码与行为撰写，使用时请注意：

- **数据结构**（SDS/ziplist/quicklist/listpack/skiplist）：7.x 中 listpack 已全面替代 ziplist；8.x 延续，机制描述仍有效
- **持久化**（RDB/AOF）：机制与权衡不变；具体格式版本与工具链以所用版本为准
- **高可用**（主从/Cluster/Sentinel）：协议与 failover 语义不变
- **模块文档**（RedisJSON/TimeSeries/Graph）：Graph 模块已停止开发（Redis 转向 vector set 与 Search 内置）；JSON/TimeSeries 在 8.x 进入核心
- **命令行为**：新增命令（如 VADD/VSIM）与变更以官方 changelog 为准

## 8. 扩展阅读

- [核心数据结构](../03.01-核心数据结构/) - Redis 数据结构深度分析
- [高可用架构](../03.03-高可用架构/) - 主从、Cluster、Sentinel
- [RESP3协议分析](../03.06-网络通信/03.06.05-RESP3协议分析.md) - 协议演进
- [成本优化策略](../../04-架构设计/04.05-成本优化/) - 许可成本与云托管成本

## 9. 权威参考

- Redis 官方博客：Redis 8.0 发布公告与许可说明（2025-05）
- Valkey 项目：<https://valkey.io/>；GitHub: <https://github.com/valkey-io/valkey>
- Redict: <https://redict.io/>
- KeyDB: <https://docs.keydb.dev/>
- Dragonfly: <https://www.dragonflydb.io/>
- Garnet: <https://github.com/microsoft/garnet>
- antirez 博客：关于 SSPL 与 AGPLv3 转变的说明（2025）
- OSI Open Source Definition: <https://opensource.org/osd>
