# TC-CLUS-005 自愈恢复计时演练

- **用例ID**：TC-CLUS-005 | **优先级**：P1 | **自动化**：人工（需 Docker/K8s 环境）；Docker 步骤可用 Testing/fixtures/redis-lab
- **目的**：实测各层自愈的检测与恢复时间，验证 RTO 预算（07.09.02 §5）并把分布回填应急预案
- **关联**：[07.09.02 自愈机制](../../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.02-自愈机制实践.md)；[07.04.03 演练记录](../../../docs/07-运维与部署/07.04-故障处理/07.04.03-应急预案.md)

## 场景与步骤

### 场景 A：L3 实例自愈（Docker，月度执行）

复用 TC-CLUS-003/004 步骤（Sentinel pause 假死 / Cluster kill 主节点），重点**计时**：注入时刻→新主可写时刻。已有基线：Sentinel ~10s、Cluster 25-40s（2026-11-17 实测）。

### 场景 B：L1/L2 进程与容器自愈（Docker restart 策略）

```bash
cd Testing/fixtures/redis-lab
docker compose -f sentinel-compose.yml up -d
T0=$(date +%s); docker kill redis-lab-sentinel-redis-s1-1     # 杀死从实例进程
sleep 1; docker start redis-lab-sentinel-redis-s1-1            # 模拟 L1 自动重启（生产为 supervisor/systemd/K8s）
T1=$(date +%s)
docker exec redis-lab-sentinel-redis-s1-1 redis-cli INFO replication | grep -E "^role|master_link"
# 预期：role:slave 且 master_link_status:up；记录 T1-T0 与同步方式（partial sync 偏移）
```

### 场景 C：L2 Pod 自愈（K8s 环境，季度执行）

```bash
kubectl apply -f <含 restartPolicy+探针的 Redis Pod 清单>   # 参照 07.09.02 §2.1
T0=$(date +%s); kubectl delete pod <redis-pod>
# 观察：Pending→ContainerCreating→Ready 全程计时；Ready 前 Service 不得分发流量（readiness 生效验证）
kubectl get events --field-selector reason=Killing --sort-by=.lastTimestamp | head -3
```

## 预期结果

- 场景 A：恢复时间 ≤ 40s（Cluster）/ ≤15s（Sentinel）
- 场景 B：实例重启后自动归队，复制恢复（部分重同步优先）
- 场景 C：Pod 自动重建，重建期间服务无不可用窗口（多副本 + readiness 摘除）

## 失败纠正与修正指引

1. 恢复超时：查探针阈值/选举参数/镜像拉取耗时，分层归因（07.09.02 §5 时间账逐项对表）。
2. 重建期间流量打入未就绪副本：readinessProbe 缺失或过小，按 07.09.02 §2.1 修正。
3. 反复全量重同步：扩 repl-backlog-size（07.05.02）。
4. 修正：实测 P50/P95 回填 07.04.03 演练记录表；超预算场景生成防护改造项。
