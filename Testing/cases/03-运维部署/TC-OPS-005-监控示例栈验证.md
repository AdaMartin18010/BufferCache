# TC-OPS-005 监控示例栈验证

- **用例ID**：TC-OPS-005 | **优先级**：P1 | **自动化**：部分（exporter 指标自动验证；全栈运行需 Docker Hub 认证，人工执行）
- **目的**：07.03 的告警规则与监控配置从纸面落到实载验证：redis_exporter 指标真实可达、规则文件结构合法、全栈（Prometheus+Grafana）可运行
- **关联**：[07.03 监控告警](../../../docs/07-运维与部署/07.03-监控告警/)；`Testing/fixtures/redis-lab/monitoring-compose.yml`

## 步骤

### A. exporter 指标验证（自动，不依赖镜像拉取）

```bash
docker compose -f Testing/fixtures/redis-lab/monitoring-compose.yml up -d redis-exporter
curl -s http://localhost:19121/metrics | grep -E "^redis_up|^redis_memory_used_bytes |^redis_keyspace_hits_total|^redis_connected_slaves"
```

预期（2026-11-17 实测）：`redis_up 1`、`redis_memory_used_bytes` 有值、`redis_keyspace_hits_total` 有值、`redis_connected_slaves 0/1/2`——四条核心告警规则的指标全部可达。

### B. 规则文件静态验证（自动，随 self_verify ops）

`alert-rules.yml` 走 ops 组 YAML 解析 + 告警结构检查（alert/expr/for/annotations 齐全，TC-OPS-002 同款）；PromQL 语法验证由 CI 中 promtool 执行（`.github/workflows/verify.yml`）。

### C. 全栈运行验证（人工，需 Docker Hub 可拉取镜像）

```bash
docker login   # 前置：prom/prometheus 与 grafana/grafana 镜像需认证拉取
docker compose -f Testing/fixtures/redis-lab/monitoring-compose.yml up -d
# 1. Prometheus http://localhost:9090/targets → redis-lab job UP
# 2. 查询 redis_up == 1
# 3. 触发告警演练：往 redis-m 灌入数据使内存水位 >50% 或断开从库 → Status/Alerts 出现 RedisMemoryHigh / RedisReplicationBroken
# 4. Grafana http://localhost:3000（admin/admin）→ 加 Prometheus 数据源 → 命中率面板
```

## 预期结果

A 通过（指标可达）；B 通过（静态检查）；C 全栈 UP 且告警可触发。

## 失败纠正与修正指引

1. exporter 指标缺失：检查 REDIS_ADDR（host.docker.internal 需 Docker Desktop 的 host 网关）与密码环境变量。
2. 告警不触发：用 promtool query 手动验证 expr（规则阈值是否被当前指标值越过；演练阈值内存 50% 需足够数据量）。
3. 镜像拉取认证失败：见用例 C 前置 docker login；不影响 A/B 自动化部分。
4. 修正：规则变更必须同时更新本用例实测段与 07.03.03 文档。
