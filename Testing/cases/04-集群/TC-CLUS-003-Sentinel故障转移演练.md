# TC-CLUS-003 Sentinel 故障转移演练

- **用例ID**：TC-CLUS-003 | **优先级**：P1 | **自动化**：人工（每月轮换执行）
- **目的**：验证 Sentinel 自动转移、VIP/DNS 切换、脑裂防护三项能力
- **关联**：[03.03.02](../../docs/03-Redis组件/03.03-高可用架构/03.03.02-Sentinel哨兵机制.md)；[07.05.03](../../docs/07-运维与部署/07.05-集群管理/07.05.03-集群故障处理.md)

## 前置条件

3 Sentinel + 1主2从；`min-replicas-to-write 1` 已配置。

## 步骤

```bash
# 1. 记录基线
redis-cli -p 6379 INFO replication > /tmp/before.txt
# 2. 制造主库故障（用 docker pause 模拟"假死"：容器网络标识保留，DNS 可解析——
#    生产语义；docker kill 会移除 DNS 条目使 resolve-hostnames 的 Sentinel 反复进入
#    tilt 模式永不转移，该发现已登记 07.05.03）
docker pause redis-lab-sentinel-redis-m
# 3. 观察（另一终端）
redis-cli -p 26379 SENTINEL masters
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
# 4. 恢复旧主
docker unpause redis-lab-sentinel-redis-m
redis-cli -p <旧主端口> REPLICAOF <新主IP> 6379   # 以从库身份归队
```

## 预期结果

`down-after-milliseconds` 内标记主观下线，法定人数后客观下线并选举；新主可写；恢复后旧主作为从库重同步；全程无双主写入窗口。

## 失败纠正与修正指引

1. 不转移：查 quorum 是否 > Sentinel 存活数；网络分区模拟方式。
2. 双主窗口：补 min-replicas-to-write；客户端写入增加主节点身份校验（ROLE 命令）。
3. 选举抖动：调大 failover-timeout 与 parallel-syncs。
4. 修正：演练结果（RTO/RPO 实测）回填 07.05.03 与 07.04.03；失败场景进入预案库。
