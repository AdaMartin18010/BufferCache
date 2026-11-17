# TC-CLUS-004 Cluster 故障转移与恢复

- **用例ID**：TC-CLUS-004 | **优先级**：P1 | **自动化**：人工（每月轮换执行）
- **目的**：验证 Cluster 选举转移、槽覆盖保持、节点恢复重同步
- **关联**：[03.03.03](../../../docs/03-Redis组件/03.03-高可用架构/03.03.03-Cluster集群模式.md)；[07.05.03](../../../docs/07-运维与部署/07.05-集群管理/07.05.03-集群故障处理.md)

## 步骤

```bash
# 1. 基线
redis-cli --cluster check <节点>:6379 > /tmp/cluster_before.txt
# 2. 杀掉一个主节点
kill -9 <主库PID>
# 3. 观察选举与提升
watch -n1 "redis-cli -c -p 6379 CLUSTER NODES | grep -E 'fail|master'"
redis-cli --cluster check <节点>:6379
# 4. 恢复旧主为从
redis-cli -p <旧主端口> CLUSTER MEET <新主IP> 6379
redis-cli -p <旧主端口> CLUSTER REPLICATE <新主节点ID>
# 5. 可选：槽再平衡演练（低峰）
redis-cli --cluster rebalance <节点>:6379 --cluster-use-empty-masters
```

## 预期结果

故障主被标记 fail；其从节点自动提升；`All 16384 slots covered` 始终成立（cluster-require-full-covery 配置符合预案）；恢复节点以从库身份 rejoin，无 split-brain。

## 失败纠正与修正指引

1. 从不提升：查 `cluster-replica-validity-factor` 与 repl_offset 差；cluster-migration-barrier。
2. 槽覆盖中断：确认 cluster-require-full-coverage yes 下短暂全拒为预期；若否配置下数据不可达，记录并按预案处理。
3. 恢复节点拒为从：先 MEET 清旧配置，必要时空数据启动触发全量重同步。
4. 修正：每次演练更新 07.05.03 的"已验证场景"表；新故障模式补入 07.04.03。
