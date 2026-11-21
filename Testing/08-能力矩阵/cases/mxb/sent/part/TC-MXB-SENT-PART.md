# TC-MXB-SENT-PART 哨兵脑裂防护演练（quorum 隔离）

- **用例ID**：TC-MXB-SENT-PART | **优先级**：P1 | **矩阵格**：MX-B / SENT / PART
- **自动化**：L2 剧本型 | **种子**：M2+ 补批 2026-11-21（裁定升级：○N→●——脑裂防护与 07.09.02 脑裂防护设计直接呼应，有验证价值）
- **运行时**：DOCKER+PODMAN
- **目的**：Sentinel 多数派被网络分区隔离时**不得**发起故障转移（quorum 不可达→不选新主）；分区恢复后集群自愈——验证脑裂防护的第一道闸
- **关联**：MX-B 维度定义 SENT×PART / docs/07-运维与部署 07.09.02 脑裂防护 / 剧本 S3（分区剧本的哨兵变体）

## 前置条件

- 哨兵栈在跑（sentinel-compose 的 podman 等价形；3 哨兵+主+2 从；quorum=2 默认）
- 网络隔离手段：toxiproxy（栈内含）或独立网络命名空间

## 步骤（GWT 五段式）

```bash
# Given 哨兵栈健康（sentinel master 视图=1 主 2 从；quorum 2）
# When 隔离 sentinel-1 与另两个哨兵的网络（toxiproxy toxic 100% 或网络断开）
curl -X POST localhost:8474/proxies/sentinel-1/toxics -d '{"type":"timeout","attributes":{"timeout":0}}'   # 具体代理名以 toxiproxy API 实际为准
# Then 15s 内观察：被隔离的 sentinel-1 独自无法达 quorum → 无 failover 发生
redis-cli -p 26379 -a lab-password --no-auth-warning SENTINEL masters   # 主仍原位
# And 隔离期主写正常（多数派哨兵虽在网内，但主未被判死——除非另注入主侧故障）
# When 解除隔离
curl -X DELETE localhost:8474/proxies/sentinel-1/toxics/timeout
# Then 哨兵视图收敛回 3 哨兵互联；全程无新主产生（no-brain-split 断言）
```

## 预期结果

- 隔离窗口：无 failover（sentinel-1 单派不选举）
- 恢复窗口：哨兵互联收敛，master 未变

## 通过标准

隔离期 `SENTINEL get-master-addr-by-name` 返回地址不变；哨兵日志（`odown` 状态可出现但无 switch-master）。

## 失败纠正与修正指引

1. 误判：sentinel-1 也判主 odown 是正常（sdown/odown 语义），关键是**无新主**。
2. failover 发生=quorum 或配置漂移（检查 sentinel.conf 的 quorum 与 announce-ip）。
3. 修正：结论回填 07.09.02 脑裂防护节"实载验证"注记。
