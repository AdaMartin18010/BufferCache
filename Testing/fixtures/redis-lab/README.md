# Redis 集群演练环境（Testing fixtures）

> 本地 Docker 演练环境，对应用例：TC-CLUS-001（Cluster 部署与槽覆盖）、TC-CLUS-002（复制链路）、TC-CLUS-003（Sentinel 故障转移）、TC-CLUS-004（Cluster 故障转移）。按 [自我验证修正机制](../../自我验证修正机制.md) §3 每月轮换执行。

## 组成

| 文件 | 内容 | 端口映射 |
| ---- | ---- | -------- |
| `cluster-compose.yml` | 3 主 3 从 Redis 8 Cluster + 初始化器 | 宿主 7001-7006 |
| `sentinel-compose.yml` | 1 主 2 从 + 3 Sentinel（quorum=2）+ **Toxiproxy 混沌代理** + redis-m 数据卷（备份演练） | 6379/6380-6381/26379-26381/**36379+8474** |
| `monitoring-compose.yml` | Prometheus + redis_exporter + Grafana（exporter 镜像已本地验证；prometheus/grafana 需 Docker Hub 认证） | 19121（exporter）/9090/3000 |
| `prometheus.yml` `alert-rules.yml` | 监控栈配置（07.03.03 核心规则提取实载） | — |

## 快速开始

```bash
# 1. Cluster 环境（TC-CLUS-001/004）
docker compose -f Testing/fixtures/redis-lab/cluster-compose.yml up -d
docker exec -it rl-c1 redis-cli --cluster check redis-c1:7000

# 2. Sentinel 环境（TC-CLUS-002/003/006/007）
docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml up -d
docker exec redis-lab-sentinel-sentinel-1-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
docker pause redis-lab-sentinel-redis-m   # 假死演练（勿用 kill——DNS 消失致 Sentinel tilt）

# 3. 备份恢复（TC-CLUS-006，数据卷 ./redis-m-data）
docker exec redis-lab-sentinel-redis-m-1 redis-cli SAVE
docker cp redis-lab-sentinel-redis-m-1:/data/dump.rdb /tmp/bk/          # RDB
docker cp redis-lab-sentinel-redis-m-1:/data/appendonlydir /tmp/bk/     # AOF 目录必须整拷
# 灾难+恢复见 TC-CLUS-006 步骤

# 4. 混沌注入（TC-CLUS-007）
curl -X POST http://localhost:8474/proxies -H 'Content-Type: application/json' \
  -d '{"name":"redis","listen":"0.0.0.0:36379","upstream":"redis-m:6379","enabled":true}'
docker run --rm redis:8-alpine redis-cli -h host.docker.internal -p 36379 PING   # 经代理
curl -X POST http://localhost:8474/proxies/redis/toxics -H 'Content-Type: application/json' \
  -d '{"type":"latency","name":"l1","attributes":{"latency":400},"toxicity":1.0,"stream":"downstream"}'

# 5. 监控栈（TC-OPS-005）
docker compose -f Testing/fixtures/redis-lab/monitoring-compose.yml up -d redis-exporter
curl -s http://localhost:19121/metrics | grep redis_up
# 全栈需 docker login 后 up prometheus/grafana
```

## 演练后登记

每次演练把实测 RTO/RPO 回填 [07.04.03 应急预案](../../../docs/07-运维与部署/07.04-故障处理/07.04.03-应急预案.md) 与 [07.05.03 集群故障处理](../../../docs/07-运维与部署/07.05-集群管理/07.05.03-集群故障处理.md) 的"已验证场景"表，并在用例文件记录执行日期。

## 清理

```bash
docker compose -f Testing/fixtures/redis-lab/cluster-compose.yml down -v
docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml down -v
```
