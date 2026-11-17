# TC-CLUS-008 分片伸缩演练（reshard 与节点增删）

- **用例ID**：TC-CLUS-008 | **优先级**：P1 | **自动化**：人工（Docker 环境月轮换）
- **目的**：实测 Cluster 分片级伸缩全流程（07.09.04 的运维落地）：新节点入簇、reshard 迁移、缩容排空，验证迁移期间服务连续性并计时
- **关联**：[07.09.04 分片级弹性伸缩](../../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.04-分片级弹性伸缩与分区迁移.md)；[01.03.05 分片数学](../../../docs/01-理论基础/01.03-分布式缓存算法/01.03.05-数据分片数学与再平衡模型.md)

## 前置条件

`cluster-compose.yml` 环境（3主3从）在跑，已造测试数据。

## 步骤（扩容路径）

```bash
cd Testing/fixtures/redis-lab
# 1. 起两个新节点（主+未来从）
docker run -d --name rl-c7 --network redis-lab-cluster_default redis:8-alpine \
  redis-server --port 7000 --cluster-enabled yes --cluster-announce-ip rl-c7 --cluster-announce-port 7000 --appendonly yes
docker run -d --name rl-c8 --network redis-lab-cluster_default redis:8-alpine \
  redis-server --port 7000 --cluster-enabled yes --cluster-announce-ip rl-c8 --cluster-announce-port 7000 --appendonly yes
# 2. 入簇
docker exec redis-lab-cluster-redis-c1-1 redis-cli -c -p 7000 CLUSTER MEET 172.18.0.7 7000   # rl-c7 的实际 IP 用 docker inspect 查
docker exec redis-lab-cluster-redis-c1-1 redis-cli -c -p 7000 CLUSTER MEET <rl-c8-ip> 7000
# 3. reshard：迁 1000 槽给新主（从 c1 迁出）
T0=$(date +%s)
docker exec redis-lab-cluster-redis-c1-1 sh -c 'yes | head -1' | docker exec -i redis-lab-cluster-redis-c1-1 redis-cli -c -p 7000 --cluster reshard redis-c1:7000 \
  --cluster-from $(docker exec redis-lab-cluster-redis-c1-1 redis-cli -p 7000 CLUSTER MYID) \
  --cluster-to <新主节点ID> --cluster-slots 1000 --cluster-yes
T1=$(date +%s); echo "reshard 耗时: $((T1-T0))s"
# 4. 验证
docker exec redis-lab-cluster-redis-c1-1 redis-cli --cluster check redis-c1:7000   # All 16384 slots covered
# 迁移期间（另终端）持续读写抽查：docker exec redis-lab-cluster-redis-c1-1 redis-cli -c -p 7000 SET chk:v $RANDOM
```

## 预期结果

- reshard 后 `All 16384 slots covered`；新主承载 1000 槽
- 迁移期间已迁移槽段的 key 经 ASK 重定向可读写（客户端 -c 模式）
- 记录 reshard 耗时回填 07.09.04 §6 延迟账实测列

## 缩容路径（恢复环境）

```bash
# 把槽迁回原主后剔除节点（排空 → CLUSTER FORGET）
docker exec redis-lab-cluster-redis-c1-1 redis-cli -c -p 7000 --cluster reshard redis-c1:7000 \
  --cluster-from <新主ID> --cluster-to <c1-ID> --cluster-slots 1000 --cluster-yes
docker exec redis-lab-cluster-redis-c1-1 redis-cli -p 7000 CLUSTER FORGET <新主ID>
docker stop rl-c7 rl-c8 && docker rm rl-c7 rl-c8
```

## 失败纠正与修正指引

1. MEET 后不握手：检查网络（同 compose 网络）与 announce IP 可达性。
2. reshard 中途失败：`CLUSTER SETSLOT <slot> STABLE` 清理 importing/migrating 标记后重试。
3. 迁移期间数据不可读：客户端未走 -c 模式或 ASK 未处理——补客户端重定向支持。
4. 修正：实测耗时与 01.03.05 成本模型对照，偏差 >2× 时校准模型参数（带宽/fork 项）。
