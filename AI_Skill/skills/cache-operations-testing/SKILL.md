---
name: cache-operations-testing
description: 缓存运维与测试体系（Ansible/Terraform/Helm 部署验证、Prometheus 监控、Redis Cluster 集群测试、故障演练、CI 集成）；用于部署验证与变更防护
---

# 缓存运维、部署与测试

> 覆盖部署自动化验证、监控告警、集群管理测试与 CI 集成，是项目 Testing 体系在运维侧的落点。

## 1. 概述与适用场景

- **覆盖**：Ansible/Terraform/Helm 部署验证、GitLab CI/Jenkins/GitHub Actions、Prometheus/Grafana 监控、集群部署/运维/故障/容量、可观测性。
- **适用**：执行部署验证；运行故障演练；评审 07 文档；接入 CI。
- **不适用**：应用缓存模式设计（→ cache-architecture-patterns）；纯算法实验（→ cache-algorithms-fundamentals / cache-algorithms-advanced）。

## 2. 核心要点

1. 部署验证三层：静态检查（`terraform validate`/`ansible-playbook --syntax-check`/`helm lint`/`kubeval`）、本地干跑（`terraform plan`/`ansible --check`/`helm template`）、运行时冒烟（端口/角色/复制状态）。
2. 变更安全：Terraform 计划必须人工 review state 变更；Ansible 变更分批 canary；Helm 升级用 `--dry-run` + 差分。
3. 监控三支柱：metrics（Prometheus：redis_exporter 的 `redis_memory_used_bytes`、`redis_keyspace_hits/misses` 派生命中率）、logs（结构化 + 采样）、traces（缓存调用作为 span）。
4. Redis Cluster 验证基线：`cluster info` 状态/槽覆盖、`cluster nodes` 全互联、failover 演练（`CLUSTER FAILOVER` 与 kill -9 两路径）、reshard 期间可用性。
5. 告警质量：命中率突降（短窗口 vs 基线）、内存达 maxmemory 80%、持久化 fork 阻塞 >1s、复制偏移差持续增长；每条告警必须有 runbook 链接（见 07.04 应急预案）。
6. 容量规划：按对象平均大小 × key 数 + 碎片率（mem_fragmentation_ratio）+ 增长余量 30%；实例上限参考 CPU 单核事件循环瓶颈（约 100K QPS/核，C 级经验）。
7. 与 Testing 的衔接：07 文档中的部署/演练步骤已用例化到 Testing/cases（TC-OPS/TC-CLUS 系列），变更前必须跑 `python Testing/self_verify.py all`。

## 3. 权威速查

| 工具 | 验证命令 | 预期 |
| ---- | -------- | ---- |
| Terraform | `terraform validate && terraform plan` | 0 错误 |
| Ansible | `ansible-playbook --syntax-check --check site.yml` | 0 failed |
| Helm | `helm lint . && helm template . > /dev/null` | 0 错误 |
| Redis | `redis-cli -a $PWD --cluster check host:6379` | All 16384 slots covered |
| Prometheus | `promtool check rules *.yml` | 语法通过 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 部署自动化 | [07.01 README](../../docs/07-运维与部署/07.01-部署自动化/) |
| CI/CD | [07.02 README](../../docs/07-运维与部署/07.02-CI-CD实践/) |
| 监控告警 | [07.03.01](../../docs/07-运维与部署/07.03-监控告警/07.03.01-Prometheus监控体系.md) / [07.03.03](../../docs/07-运维与部署/07.03-监控告警/07.03.03-告警规则与通知.md) |
| 集群管理 | [07.05 README](../../docs/07-运维与部署/07.05-集群管理/) |
| 可观测性 | [07.06 README](../../docs/07-运维与部署/07.06-可观测性/) |
| 自动化运维 | [07.07](../../docs/07-运维与部署/07.07-自动化运维/) |
| 多租户 | [07.08](../../docs/07-运维与部署/07.08-多租户管理/) |
| 测试用例库 | [Testing/cases](../Testing/cases/) |

## 5. 常见任务工作流

### 任务 A：部署前验证

1. 静态检查（§3 速查）；2. 干跑审 plan 输出；3. 应用变更；4. 冒烟（§2-1 第三层）；5. 更新 runbook。

### 任务 B：月度故障演练

按 Testing/cases/CLUS 清单轮换：主库宕机、网络分区、慢查询堆积、内存打满；记录 RTO/RPO 实测值回填 07.04.03。

## 6. 国际前沿对齐（截至 2026-11）

- GitOps（ArgoCD/Flux）成为集群配置发布默认；Terraform 1.6+ 引入声明式资源销毁计划改进。
- eBPF 可观测性（Pixie/Cilium Hubble）可观测缓存调用链；OpenTelemetry 指标与 Prometheus 互通（OTLP 直写）成熟。
- Valkey 9.x 与 Redis 8.x 的新监控指标（I/O 线程饱和度）进入 exporter。

## 7. 验证命令

```bash
python Testing/self_verify.py ops     # 预期：部署配置静态检查通过（TC-OPS-001 起）
python Testing/self_verify.py all     # 全量无回归（TC-INT-001）
```

## 8. 权威参考

- **A 学术**：Google SRE 丛书（Beyer et al., 2016）（SLO/错误预算方法论）
- **B 官方**：Prometheus 文档（https://prometheus.io/docs/）；Ansible/Terraform/Helm 官方文档；redis_exporter README
- **C 工程**：GitOps 工作组白皮书；OpenTelemetry 缓存语义约定
