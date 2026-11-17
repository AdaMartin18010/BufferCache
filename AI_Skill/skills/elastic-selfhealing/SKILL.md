---
name: elastic-selfhealing
description: 弹性伸缩（HPA/VPA/KEDA/Karpenter、缓存内存水位伸缩）与自愈（探针/自动转移/修复闭环）及混沌工程验证；用于弹性设计、RTO 预算与韧性演练
---

# 弹性伸缩与自愈

> 覆盖缓存系统的弹性双能力：负载驱动的自动伸缩（三层控制回路）与故障驱动的自愈（五层模型），以及混沌工程验证方法论。

## 1. 概述与适用场景

- **覆盖**：伸缩三层面（Pod/节点/集群）、HPA/VPA/KEDA/Karpenter、缓存内存水位驱动伸缩、K8s 探针自愈原语、缓存层自愈机制、修复闭环、混沌工程。
- **适用**：弹性架构设计评审；RTO 预算制定；韧性演练计划；评审 07.09 系列文档。
- **不适用**：具体监控指标配置（→ cache-operations-testing）；故障发生后的手工处置（→ 07.04 文档）；应用级熔断（→ 02.06 / distributed-architecture）。

## 2. 核心要点

1. 伸缩是三个独立控制回路：L1 Pod（HPA/KEDA，15s-2min）、L2 节点（Karpenter/CA，40s-5min）、L3 集群分片（reshard，分钟级且通常只自动扩、人工审缩）；选错层面工具正确也无效。
2. HPA 缩容稳定窗口与不对称阈值（扩 70% 缩 30%）是防 flapping 核心；K8s 1.37 起 HPA 原生 scale-to-zero，之前用 KEDA（70+ scaler、Redis Streams lag 驱动消费者伸缩）。
3. 缓存伸缩信号是内存水位而非 CPU：`redis_memory_used_bytes/maxmemory` 经 Prometheus Adapter 成为 external metric；数据路径扩缩 = 新分片 + reshard（双轨策略）。
4. Karpenter（AWS）胜在 per-batch 选型号 + consolidation 持续省成本；Cluster Autoscaler 胜在云无关与成熟度；VPA 与 HPA 不可同指标并用。
5. 自愈五层：进程→Pod→实例（Sentinel/Cluster 转移）→应用（熔断）→机房（预案）；下层是上层的前提，实测 RTO：Sentinel ~10s、Cluster 25-40s、Pod 重建 <2min。
6. 探针三件套执行顺序 startup→readiness/liveness；startupProbe 防慢启动误杀，readiness 防冷启动 miss 风暴接入流量；liveness 必须"真死才失败"。
7. 修复闭环五环：检测→决策（runbook）→执行（幂等）→验证（指标回归）→学习（归档）；L1-L2 全自动、L3 自动+审计、L4-L5 人工门禁；执行层保持确定性 runbook，AI 只做检测与建议。
8. 混沌工程四原则：稳态假设、真实事件、生产运行（控爆炸半径）、持续自动化；稳态用命中率/延迟分布而非"无报错"。

## 3. 权威速查

| 项 | 关键值 | 说明 |
| -- | ------ | ---- |
| HPA 控制循环 | 默认 15s | 指标窗口同 15s |
| KEDA | CNCF Graduated，70+ scaler | scale-to-zero 原生 |
| 平均 CPU 利用率 | ~8%（2026 报告） | 缩容速度是首要收益 |
| Sentinel 转移实测 | ~10s | down-after 5s 配置 |
| Cluster 转移实测 | 25-40s | node-timeout 15s 默认 |
| 演练覆盖度目标 | ≥80% 风险场景 | 07.09.03 §6 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 伸缩三层面与延迟账 | [07.09.01](../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.01-自动伸缩实践.md) |
| 自愈五层与探针 | [07.09.02](../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.02-自愈机制实践.md) |
| 混沌工程 | [07.09.03](../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.03-混沌工程与韧性演练.md) |
| 实例级自愈实测 | [07.05.03](../../docs/07-运维与部署/07.05-集群管理/07.05.03-集群故障处理.md) §7.2 |
| RTO 演练登记 | [07.04.03](../../docs/07-运维与部署/07.04-故障处理/07.04.03-应急预案.md) §5 |
| 应用级容错 | [02.06.01](../../docs/02-系统实现/02.06-程序设计实践/02.06.01-容错机制设计.md) |
| 演练环境 | [Testing/fixtures/redis-lab](../../Testing/fixtures/redis-lab/README.md) |

## 5. 常见任务工作流

### 任务 A：弹性方案评审

1. 负载形态：稳态→HPA；事件/队列→KEDA；批量潮汐→KEDA cron+缩零。
2. 缓存数据路径是否允许自动扩？缩容是否有人工门禁？
3. 冷启动防护：readiness 预热门 + 回源合并是否就位？
4. 输出：三层伸缩矩阵 + RTO 预算表 + 冷却参数。

### 任务 B：韧性演练计划

1. 从 07.09.03 §4 场景清单选 1-2 个（月度），预发先行。
2. 写稳态假设与中止条件，爆炸半径最小化（mode: one）。
3. 执行计时（TC-CLUS-005），P50/P95 回填 07.04.03。
4. 失败场景转防护改造项，更新 runbook。

## 6. 国际前沿对齐（截至 2026-11）

- HPA 1.37 scale-to-zero、KEDA 2.16（2026-09 文件认证）；Karpenter consolidation 与 spot 预建替代节点为成本优化主力。
- 生产集群平均 CPU 利用率 ~8%（Cast AI 2026）——缩容速度比扩容速度更影响成本。
- 自愈研究共识：K8s 自愈约减半事件响应时间；有效性前提是实时可观测 + 动作幂等。
- 混沌工程向 CI 化（发布前最小混沌套件）与 AI 辅助稳态分析演进，执行层保持确定性。

## 7. 验证命令

```bash
python Testing/self_verify.py ops      # 预期：07.09 配置静态检查通过（TC-OPS-004）
docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml up -d   # 场景 A/B 演练环境（TC-CLUS-005）
```

## 8. 权威参考

- **B 官方**：Kubernetes HPA/VPA/探针/PDB 文档；KEDA 文档（keda.sh）；Karpenter 文档（karpenter.sh）；Chaos Mesh 文档（chaos-mesh.org）；Redis Sentinel/Cluster 文档
- **C 工程**：[Autoscaling 2026 in Concert（saaro）](https://blog.saaro.net/en/kubernetes-autoscaling-2026-hpa-vpa-keda-und-karpenter-im-zu)；[Autoscaling Tools Compared（Control Plane 2026-11）](https://controlplane.com/blog/post/kubernetes-autoscaling-tools)；[自愈与混沌验证（ISTC 2026）](https://iststc.com/wp-content/uploads/2026/06/ISTC2026-Aktas%CC%A7-Tuzlutas%CC%A7-FINAL.pdf)；[K8s 自愈与 MTTR（IJSET 2026）](https://www.ijset.in/wp-content/uploads/IJSET_V11_issue6_679.pdf)
