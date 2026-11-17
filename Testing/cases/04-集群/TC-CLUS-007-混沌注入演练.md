# TC-CLUS-007 混沌注入演练（Toxiproxy 网络故障）

- **用例ID**：TC-CLUS-007 | **优先级**：P1 | **自动化**：半自动（延迟注入已实测基线；全场景月轮换人工执行）
- **目的**：用 Toxiproxy 在 Docker 环境注入真实网络故障（延迟/中断/分区），验证客户端超时行为与缓存层防护（07.09.03 §4 场景的本地可执行子集）
- **关联**：[07.09.03 混沌工程](../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.03-混沌工程与韧性演练.md)；[07.09.02 自愈机制](../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.02-自愈机制实践.md)

## 环境与准备

```bash
docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml up -d toxiproxy
# proxy 定义（容器重启后需重建——proxy 是内存态）
curl -X POST http://localhost:8474/proxies -H 'Content-Type: application/json' \
  -d '{"name":"redis","listen":"0.0.0.0:36379","upstream":"redis-m:6379","enabled":true}'
# 客户端连接串：host.docker.internal:36379（数据面）；控制面 :8474
```

## 场景与实测（2026-11-17 基线）

### 场景 A：延迟注入（★已实测）

```bash
# 基线
docker run --rm redis:8-alpine sh -c 'time redis-cli -h host.docker.internal -p 36379 PING'   # 0.00s
# 注入 +400ms
curl -X POST http://localhost:8474/proxies/redis/toxics -H 'Content-Type: application/json' \
  -d '{"type":"latency","name":"lat400","attributes":{"latency":400},"toxicity":1.0,"stream":"downstream"}'
# 复测：PONG 耗时 0.40s（注入精确生效）
# 清理
curl -X DELETE http://localhost:8474/proxies/redis/toxics/lat400
```

### 场景 B：主从分区（脑裂防护验证）

```bash
# 对 slave 连接注入 timeout（半开连接挂起），模拟主从分区
# 观测：redis-m 的 connected_slaves 下降 → min-replicas-to-write 拒写生效（07.09.02 §3 表）
docker exec redis-lab-sentinel-redis-m-1 redis-cli INFO replication | grep connected_slaves
```

### 场景 C：慢网络下的客户端熔断

```bash
# 注入 bandwidth toxic 限速 + latency 组合，压测经代理的请求
# 观测：应用侧超时率上升 → 熔断器半开探测（02.06.01）；窗口恢复后流量回归
```

## 预期结果

- 注入与恢复可逆（T1≈0 → T2=注入值 → T3≈0）
- 分区场景：防护配置（min-replicas）按文档生效

## 失败纠正与修正指引

1. 8474 控制面不可达：容器未起（`compose ps`）或 proxy 未重建（重启即失）。
2. 端口冲突：数据面 36379/控制面 8474 必须避开 sentinel 的 26379-26381。
3. 注入未生效：检查 toxicity（0=不生效）与 stream（upstream/downstream 方向）。
4. 修正：新 toxic 类型验证后补入本用例场景清单；故障域清单与 07.09.03 §4 表保持同步。

## 已知边界

Windows Docker Desktop 下 toxiproxy 控制面偶发不可达（重启容器可恢复）；K8s 环境 Chaos Mesh 为完整形态（07.09.03 §3）。
