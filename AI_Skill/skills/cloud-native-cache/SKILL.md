---
name: cloud-native-cache
description: 云原生缓存（云托管服务/Kubernetes Operator/Docker 构建缓存/serverless 计费）的选型与部署；用于云缓存选型、K8s 部署与成本决策
---

# 云原生缓存（云缓存 · K8s · Docker）

> 覆盖 2024-2026 云原生缓存格局：托管服务引擎默认切换、K8s Operator 谱系、Docker 构建缓存与成本结构。

## 1. 概述与适用场景

- **覆盖**：云厂商托管缓存（ElastiCache/Memorystore/Azure）、serverless 缓存、K8s 部署模式（Operator/Helm/sidecar）、Docker 构建缓存、选型决策。
- **适用**：云缓存服务选型与成本评估；K8s 缓存部署设计；CI 构建加速；评审 04.03.16 文档。
- **不适用**：自建集群的协议与故障转移细节（→ redis-persistence-ha / cache-operations-testing）；架构模式（→ cache-architecture-patterns）。

## 2. 核心要点

1. 许可变迁重塑云默认值：Redis 7.4 改 RSALv2/SSPLv1 后，AWS ElastiCache 与 GCP Memorystore 新集群默认引擎切换为 Valkey（2024-10 起）；Azure 无托管 Valkey，主推 Azure Managed Redis。
2. 服务模式二分：Serverless（按用量，流量波动/连接受限场景）vs 节点式（按规格，稳定高负载）；serverless 在低频波动负载通常更省，稳态高负载节点式单位成本更低。
3. K8s Operator 生态已收敛：KubeBlocks（AGPL，Sentinel/Cluster 双架构 + OpsRequest 统一运维，故障转移 Cluster 4-6s）与 OT-CONTAINER-KIT redis-operator（Apache 2.0，轻量）为社区主选；Spotahome 已归档勿用于新项目。
4. Bitnami chart 生态收缩（redis-cluster 冻结于 13.0.4、镜像收费化），Valkey 官方 Helm chart 成为 BSD 路线默认。
5. K8s 三要件：announce 地址与 Service/Pod IP 策略匹配（Operator 自动化）、Guaranteed QoS + maxmemory 留 20-25% 余量、topologySpread 打散。
6. Docker 构建缓存：层缓存（锁文件先行）+ BuildKit cache mount（编译缓存目录持久化）+ 外部 cache-to/from（CI 跨构建复用）为 2026 标准组合。
7. 构建缓存安全：共享缓存命名空间隔离 + 不可变 key + provenance 验证，防 CI 缓存投毒（见 cache-security）。

## 3. 权威速查

| 项 | 2026 事实 | 来源 |
| -- | --------- | ---- |
| AWS/GCP 默认引擎 | Valkey（新集群，2024-10 起） | redisvsmemcached 时间线 |
| KubeBlocks | AGPLv3，OpsRequest 统一 CRD | kubeblocks.io |
| OT-CONTAINER-KIT | Apache 2.0，v0.27.0（2026-10） | opstree 文档 |
| Spotahome | **archived** | JusDB 2026-11 |
| Upstash 差异化 | REST 端点 + per-request 计费 | upstash 2026-06 对比 |
| Dragonfly 宣称 | 3.82M ops/s @64核（第三方，C 级） | Wise Hustlers 2026-10 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 总览与决策树 | [04.03.16](../../../docs/04-架构设计/04.03-行业应用场景/04.03.16-云原生缓存趋势与实践.md) |
| 架构模式对照 | [04.03.13](../../../docs/04-架构设计/04.03-行业应用场景/04.03.13-云原生缓存架构.md) |
| 版本与许可事实 | [03.05 README](../../../docs/03-Redis组件/03.05-Redis生态与版本演进/README.md) |
| 部署自动化 | [07.01](../../../docs/07-运维与部署/07.01-部署自动化/) |
| 集群运维 | [07.05](../../../docs/07-运维与部署/07.05-集群管理/) |
| 本地演练环境 | [Testing/fixtures/redis-lab](../../../Testing/fixtures/redis-lab/README.md) |

## 5. 常见任务工作流

### 任务 A：云缓存选型

1. 合规红线：AGPLv3 可接受？否→Valkey 引擎（AWS/GCP 默认即省 20% 左右）；可接受→Redis OSS 8.x。
2. 流量形态：波动/无连接池→Serverless 或 Upstash；稳态高负载→节点式。
3. 特殊能力：向量/模块/Active-Active→Redis Cloud/Azure Managed Redis。
4. 输出：引擎 + 服务模式 + 月成本估算（对照 04.03.16 §5.2）。

### 任务 B：K8s 部署落地

1. 选 Operator：功能全→KubeBlocks；许可保守→OT-CONTAINER-KIT。
2. 核对 QoS/拓扑/announce 三要件（§2.5）。
3. 演练：本地 Testing/fixtures/redis-lab 先行验证故障转移，再上生产。

## 6. 国际前沿对齐（截至 2026-11）

- AWS/GCP 默认 Valkey 格局稳定；Azure Managed Redis 持续替代 Azure Cache for Redis。
- Operator 生态：Spotahome 归档（2026 确认），KubeBlocks 与 OT-CONTAINER-KIT 二分天下；Valkey Helm 成为无 Operator 首选。
- Sidecar cache 模式（代理旁路拦截读）在无客户端改造场景兴起（oneuptime 2026-03）。
- serverless 缓存定价持续走低，per-request 模式边缘场景渗透。

## 7. 验证命令

```bash
python Testing/self_verify.py links --path AI_Skill   # 预期：0 死链（TC-DOC-003）
python Testing/self_verify.py ops                     # 预期：YAML/规则/基线通过（TC-OPS-001）
```

## 8. 权威参考

- **B 官方**：AWS ElastiCache/GCP Memorystore/Azure Managed Redis 文档；KubeBlocks 文档；OT-CONTAINER-KIT redis-operator 文档；Docker BuildKit 缓存文档
- **C 工程**：[Redis 许可时间线与云默认](https://redisvsmemcached.com/redis-license-timeline/)；[2026 托管 Redis 定价对比（Upstash）](https://upstash.com/blog/redis-pricing-comparison-every-major-provider-in-2026-with-numbers)；[K8s Redis Operator 实测](https://mdnice.com/writing/b075bead240a4aa4925fddf096c3262a)；[Valkey/Redis Operator 对比 2026-11](https://www.jusdb.com/blog/valkey-redis-operators-kubernetes-compared)；[Redis on K8s 盘点 2026-10](https://acemq.com/blogs/redis-on-kubernetes/)
