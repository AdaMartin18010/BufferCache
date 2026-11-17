# TC-CLUS-009 集群升级与引擎迁移演练

- **用例ID**：TC-CLUS-009 | **优先级**：P1 | **自动化**：人工（Docker 环境半年轮换）
- **目的**：实测滚动升级与 Redis→Valkey 引擎迁移全流程（07.05.05 的运维落地），验证升级窗口、切换无损与回滚有效性
- **关联**：[07.05.05 升级与迁移演练](../../../docs/07-运维与部署/07.05-集群管理/07.05.05-集群升级与迁移演练.md)；[TC-CLUS-006 备份恢复](TC-CLUS-006-备份恢复演练.md)；[TC-CLUS-003 故障转移](TC-CLUS-003-Sentinel故障转移演练.md)

## 前置条件

sentinel 环境在跑（Redis 8）；本机或拉取 valkey:8 镜像（ghcr.io/valkey-io/valkey 或 Docker Hub valkey）。

## 场景 A：补丁级滚动升级（季度）

```bash
# 对每个节点（从库先行）：停旧容器 → 起新版本（compose 改 image tag 后 up -d <svc>）
# 每步验证：
docker exec redis-lab-sentinel-redis-s1-1 redis-cli -a lab-password --no-auth-warning INFO server | grep redis_version
docker exec redis-lab-sentinel-redis-m-1 redis-cli -a lab-password --no-auth-warning INFO replication | grep -E "connected_slaves|master_link"
# 主库切换（用 TC-CLUS-003 的 pause 法），升级旧主，切回；记录每节点耗时（目标 ≤2min）
```

## 场景 B：引擎迁移 Redis → Valkey（半年）

```bash
# 1. 起 Valkey 实例作 Redis 从库（协议兼容，直接 replicaof）
docker run -d --name valkey-r --network redis-lab-sentinel_default valkey/valkey:8 \
  valkey-server --port 6379 --requirepass lab-password --masterauth lab-password --replicaof redis-m 6379
sleep 10
docker exec valkey-r valkey-cli -a lab-password --no-auth-warning INFO replication | grep -E "role|master_link_status"
# 2. 数据校验：抽样 key 双端比对（redis-cli GET vs valkey-cli GET，抽 100 个）
# 3. 主库切换：pause redis-m → Sentinel 选举（注意：Sentinel 监控的是 redis-m，切换后需评估监控目标调整）
# 4. 观测 10min：命中率/延迟/慢查询；回滚=切回原主（双写期已过则按预案声明损失窗口）
```

## 预期结果

- 滚动升级：全程业务无中断（演练中以连续 PING/GET 探针验证），单节点 ≤2min
- 引擎迁移：抽样比对 100% 一致；切换后 10min 内指标平稳；Valkey 版本确认

## 失败纠正与修正指引

1. 从库升级后不同步：检查 masterauth/认证与版本协议差异（7↔8 大版本滚动需先验证 PSYNC 兼容性）。
2. 引擎迁移切换后客户端报错：命令功能分叉（Redis 8 的 vector set 等 Valkey 无）——客户端依赖清单核对（升级前检查清单第 2 项）。
3. 回滚失败：确认持久化文件方向兼容（8.x AOF 目录格式 6.x 不认，回滚前导出转换）。
4. 修正：演练结果（窗口/步骤缺陷）回填 07.05.05 清单；新发现的检查项加入升级前检查表。
