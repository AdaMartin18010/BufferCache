# TC-CLUS-002 复制链路健康验证

- **用例ID**：TC-CLUS-002 | **优先级**：P1 | **自动化**：人工（需实例）
- **目的**：主从复制无延迟风暴、backlog 充足、部分重同步可用
- **关联**：[03.03.01](../../docs/03-Redis组件/03.03-高可用架构/03.03.01-主从复制机制.md)；[07.05.02](../../docs/07-运维与部署/07.05-集群管理/07.05.02-集群运维实践.md)

## 步骤

```bash
redis-cli INFO replication      # master_link_status:up；slave_repl_offset 与主 master_repl_offset 差小
redis-cli CONFIG GET repl-backlog-size
redis-cli CONFIG GET repl-backlog-ttl
# 写压测期间观察：
redis-cli INFO stats            # master_repl_offset 增速；sync_full 计数不异常增长
```

## 预期结果

master_link_status:up；offset 差稳定在低水位（写压测下 <backlog 的 10%）；无反复全量同步（sync_full 稳定）。

## 失败纠正与修正指引

1. offset 持续拉大：扩 repl-backlog-size（写入速率 × 故障窗口）；查网络带宽与 rdb 传输时间。
2. 周期性全量同步：同上；并查 `repl-timeout` 是否过短（大实例 rdb 传输慢被误判超时）。
3. 写放大/缓冲积压：监控 client-output-buffer-limit 是否触发断连循环。
4. 修正：把 backlog 容量公式写入 07.05.04 容量规划检查表。
