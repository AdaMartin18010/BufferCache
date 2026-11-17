# Redis 集群演练环境（Testing fixtures）

> 本地 Docker 演练环境，对应用例：TC-CLUS-001（Cluster 部署与槽覆盖）、TC-CLUS-002（复制链路）、TC-CLUS-003（Sentinel 故障转移）、TC-CLUS-004（Cluster 故障转移）。按 [自我验证修正机制](../../自我验证修正机制.md) §3 每月轮换执行。

## 组成

| 文件 | 内容 | 端口映射 |
| ---- | ---- | -------- |
| `cluster-compose.yml` | 3 主 3 从 Redis 8 Cluster + 初始化器 | 宿主 7001-7006 |
| `sentinel-compose.yml` | 1 主 2 从 + 3 Sentinel（quorum=2） | 宿主 6379/6380-6381/26379-26381 |

## 快速开始

```bash
# 1. Cluster 环境
docker compose -f Testing/fixtures/redis-lab/cluster-compose.yml up -d
# 等待 cluster-init 完成（自动执行 --cluster create）
docker compose -f Testing/fixtures/redis-lab/cluster-compose.yml logs cluster-init
# 执行 TC-CLUS-001/TC-CLUS-004：
docker exec -it rl-c1 redis-cli --cluster check redis-c1:7000
docker exec -it rl-c1 redis-cli -c -p 7000 -c SET foo bar

# 2. Sentinel 环境（另一终端，可并存）
docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml up -d
# 执行 TC-CLUS-002/TC-CLUS-003：
docker exec -it rl-sentinel-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
docker kill rl-redis-m        # 制造主库故障，观察转移
```

## 演练后登记

每次演练把实测 RTO/RPO 回填 [07.04.03 应急预案](../../../docs/07-运维与部署/07.04-故障处理/07.04.03-应急预案.md) 与 [07.05.03 集群故障处理](../../../docs/07-运维与部署/07.05-集群管理/07.05.03-集群故障处理.md) 的"已验证场景"表，并在用例文件记录执行日期。

## 清理

```bash
docker compose -f Testing/fixtures/redis-lab/cluster-compose.yml down -v
docker compose -f Testing/fixtures/redis-lab/sentinel-compose.yml down -v
```
