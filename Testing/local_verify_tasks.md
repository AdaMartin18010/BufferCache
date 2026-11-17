# 本地持续验证任务卡（hermes 自主接续执行）

> 本文件是 [测试与验证执行计划](测试与验证执行计划.md) 的**本地执行附页**：总纲定义四层模型与分工，本卡只记录"需要 Docker 环境的待办段"的详细步骤与执行留痕。hermes 每次会话按总纲 §3 手册开工，到期任务按本卡步骤执行。

## 任务 1：基准基线实测与回归基线入库（TC-BENCH-005 待办段）

- **触发条件**：`docker ps` 可用且 redis-lab sentinel 环境可起
- **状态**：⏳ 待执行
- **步骤**：
  1. `docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml up -d`
  2. `python scripts/benchmark/suite/bench_suite.py --host 127.0.0.1 --port 6379 --password lab-password --save-baseline`
  3. 再次运行不带 `--save-baseline` 验证回归检测路径（期望 PASS，偏差 <15%）
- **回填**：基线 JSON 在 `Testing/output/bench_suite/baseline.json`（gitignore，不入库）；结果摘要记入 `docs/07-运维与部署/07.05-集群管理/07.05.04-集群容量规划.md` §3 实测段（若数值与 2026-11-17 基线差异 >10%，更新断言清单 C2）
- **完成判据**：两次运行均输出场景 RPS + 基线偏差 <15%

## 任务 2：监控栈全栈验证（TC-OPS-005 待办段 C）

- **触发条件**：任务 1 完成 + `docker login` 可用（prom/prometheus、grafana/grafana 镜像需认证拉取；无认证时仅执行任务 3 的 exporter 部分）
- **状态**：⏳ 待执行
- **步骤**：
  1. `docker compose -f Testing/fixtures/redis-lab/monitoring-compose.yml up -d`
  2. `curl -s http://localhost:9090/api/v1/query?query=redis_up` → 值为 1
  3. 触发 RedisReplicationBroken 告警演练：`docker compose -f sentinel-compose.yml stop redis-s1 redis-s2` → 30s 内 Prometheus Alerts 出现该告警（阈值 connected_slaves==0 且 for 30s）
  4. 恢复从库，告警消除
  5. Grafana（admin/admin）→ 加 Prometheus 数据源 → 导入 redis 面板（可选）
- **回填**：演练结果与告警触发时延记入 TC-OPS-005 用例文件"实测记录"节
- **完成判据**：告警按预期触发与消除，时延记录入库

## 任务 3：演练环境健康巡检（常态化，每次会话可顺手执行）

- **触发条件**：Docker 可用
- **状态**：🔁 常态化
- **步骤**：`python Testing/self_verify.py lab`（exporter 指标可达）+ `python Testing/self_verify.py security`（未授权探测）
- **完成判据**：两项 PASS

## 执行记录

| 日期 | 执行任务 | 结果 | 执行者 |
| ---- | -------- | ---- | ------ |
| 2026-11-17 | 任务 3 | exporter 带认证 up=1 PASS；未授权探测 NOAUTH 正常 | hermes |
| 2026-11-17 | 任务 1 | 环境就绪（sentinel 3 节点双副本）；**redis-benchmark 宿主未装**→已给 bench_suite 加 --bench-cmd 支持容器内执行；基线实测留待下轮 hermes 按 --bench-cmd "docker exec redis-lab-sentinel-redis-m-1 redis-benchmark" 执行 | hermes |
