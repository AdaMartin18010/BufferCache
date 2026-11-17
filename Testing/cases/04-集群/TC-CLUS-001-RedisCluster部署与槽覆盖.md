# TC-CLUS-001 Redis Cluster 部署与槽覆盖验证

- **用例ID**：TC-CLUS-001 | **优先级**：P1 | **自动化**：人工（需实例）；self_verify 导出步骤清单（`cluster`）
- **目的**：新集群交付或扩缩容后，槽位全覆盖、主从配对正确、Gossip 收敛
- **关联**：[07.05.01](../../docs/07-运维与部署/07.05-集群管理/07.05.01-集群部署实践.md)；[03.03.03](../../docs/03-Redis组件/03.03-高可用架构/03.03.03-Cluster集群模式.md)

## 前置条件

≥3 主节点（建议 3主3从）；redis-cli 与集群同版本。

## 步骤

```bash
redis-cli --cluster check <任一节点>:6379        # 槽覆盖与主从映射
redis-cli -c -p 6379 CLUSTER INFO                # cluster_state:ok
redis-cli -c -p 6379 CLUSTER NODES               # 全互联、无 fail 标记
redis-cli -c -p 6379 -c SET foo bar && GET foo   # 跨槽路由正确（-c 自动 redirect）
```

## 预期结果

`[OK] All 16384 slots covered`；cluster_state:ok；所有节点 handshake 完成；跨槽命令由 -c 模式正确转发。

## 失败纠正与修正指引

1. 槽未覆盖：对缺失槽执行 `redis-cli --cluster reshard` 或 `add-node` 后 rebalance。
2. 主从未配对：`redis-cli --cluster replicate <主节点ID>`。
3. Gossip 不收敛：查 cluster-announce-ip/port（NAT/容器环境）、防火墙、bind 地址。
4. 修正：部署文档 07.05.01 增补本节四步为"交付检查清单"。
5. 登记实测 RTO 于 07.04.03。
