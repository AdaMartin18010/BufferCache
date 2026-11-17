---
name: cache-architecture-patterns
description: 缓存架构模式（Cache-Aside/Read-Through/Write-Through/Write-Behind/Refresh-Ahead）与三大击穿问题（穿透/雪崩/击穿）治理；用于应用缓存设计评审
---

# 缓存架构模式与治理

> 覆盖六种缓存读写模式、一致性问题族与生产治理方案，是应用层缓存设计的模式库。

## 1. 概述与适用场景

- **覆盖**：Cache-Aside、Read-Through、Write-Through、Write-Behind、Refresh-Ahead；穿透/雪崩/击穿/热点/大 Key 治理。
- **适用**：应用缓存方案设计；评审 04.01/04.04 文档；故障复盘归因。
- **不适用**：单节点算法（→ cache-algorithms-fundamentals / cache-algorithms-advanced）；部署运维（→ cache-operations-testing）。

## 2. 核心要点

1. Cache-Aside（旁路）是最常用模式：读miss→回源→回填；写→更新DB后删缓存。一致性由"删缓存"保证，缺点是首次 miss 风暴需额外防护（逻辑过期、预热）。
2. Read-Through/Write-Through 把一致性责任交给缓存层（如 RedisGears、CDN），适合多应用共享同一数据视图。
3. Write-Behind（异步写）吞吐最高但有丢失窗口，适合可容忍秒级不一致的计数/日志场景。
4. Refresh-Ahead 在过期前主动刷新，把尾延迟转化为后台流量；需防刷新风暴（加抖动）。
5. 穿透（查不存在的 Key）：布隆过滤器/空值缓存/接口层校验；雪崩（大面积同时过期）：过期时间加随机抖动、多级缓存、熔断降级；击穿（单热点过期）：互斥重建（分布式锁 + 逻辑过期）、热点预热、请求合并（singleflight）。
6. 热点 Key：本地缓存兜底（caffeine/ristretto）+ 副本分散 + 提前识别（访问倾斜度监控，见 04.04.07 指标体系）。
7. 大 Key：拆分（hash 分桶）、压缩（snappy/zstd）、异步删除（unlink），扫描用 `SCAN` 不用 `KEYS`。

## 3. 权威速查

| 模式 | 一致性 | 写放大 | 典型场景 |
| ---- | ------ | ------ | -------- |
| Cache-Aside | 中（删缓存窗口） | 低 | 通用读多 |
| Read-Through | 中 | 低 | 共享数据视图 |
| Write-Through | 高 | 高 | 强一致读路径 |
| Write-Behind | 低 | 低 | 计数/日志 |
| Refresh-Ahead | 中 | 中 | 热点稳定 |
| （多级缓存） | 中 | 低 | 高 QPS 读 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| Cache-Aside | [04.01.01](../../../docs/04-架构设计/04.01-缓存架构模式/04.01.01-Cache-Aside旁路缓存.md) |
| Read-Through | [04.01.02](../../../docs/04-架构设计/04.01-缓存架构模式/04.01.02-Read-Through透读缓存.md) |
| Write-Through | [04.01.03](../../../docs/04-架构设计/04.01-缓存架构模式/04.01.03-Write-Through透写缓存.md) |
| Write-Behind | [04.01.04](../../../docs/04-架构设计/04.01-缓存架构模式/04.01.04-Write-Behind异步写缓存.md) |
| 穿透/雪崩/击穿 | [04.04.01](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.01-缓存穿透.md) / [04.04.02](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.02-缓存雪崩.md) / [04.04.03](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.03-缓存击穿.md) |
| 热点/大Key | [04.04.04](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.04-热点Key问题.md) / [04.04.05](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.05-大Key问题.md) |
| 监控指标 | [04.04.07](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.07-缓存监控指标体系.md) |
| 行业场景 | [04.03 README](../../../docs/04-架构设计/04.03-行业应用场景/README.md) |
| 成本 | [04.05.05](../../../docs/04-架构设计/04.05-成本优化/04.05.05-成本优化策略.md) |
| 失效传播与一致性链路 | [04.44.08](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.08-缓存失效传播与一致性链路.md) |
| 预热与冷启动治理 | [04.44.09](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.09-缓存预热与冷启动治理.md) |
| 多副本读一致性 | [04.44.10](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.10-多副本读一致性与修复机制.md) |
| 数据对账与校验 | [04.44.11](../../../docs/04-架构设计/04.04-缓存问题与治理/04.04.11-缓存数据对账与校验.md) |

## 5. 常见任务工作流

### 任务 A：方案设计评审清单

1. 读写模式是否显式声明并说明一致性窗口？
2. 击穿防护：热点 key 互斥重建是否实现（锁+逻辑过期）？
3. 雪崩防护：过期抖动、多级缓存、回源限流是否就位？
4. 监控：命中率、回源 QPS、重建延迟是否入指标体系（04.04.07）？

### 任务 B：故障归因

按"过期模式→击穿；不存在 key 风暴→穿透；集中失效→雪崩；单 key 倾斜→热点"对照复盘，修订防护参数。

## 6. 国际前沿对齐（截至 2026-11）

- LLM 场景引入新变体：提示词结果缓存（语义缓存如 GPTCache）、KV Cache 前缀缓存（→ llm-kv-cache），Cache-Aside 思想被复用。
- 一致性增强：CDC（Debezium 等）驱动缓存失效成为 Write-Through 的主流实现方式，降低应用侵入。
- 行业基准：caffeine（本地）+ Redis（远程）两级为 Java 生态默认；Go 生态 ristretto/ristretto-z 类似。

## 7. 验证命令

```bash
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
python Testing/self_verify.py structure               # 预期：04 文档链接完整（TC-LINK-001）
```

## 8. 权威参考

- **A 学术**：Nishtala et al., NSDI 2013（Scaling Memcache at Facebook，模式实践源头）；Atikoglu et al., SIGMETRICS 2012（memcached 工作负载分析）
- **B 官方**：Redis 官方文档 Caching patterns；Caffeine Wiki；CDN 文档（CloudFront/Cloudflare 缓存行为）
- **C 工程**：GPTCache 文档；singleflight 模式（Go blog）
