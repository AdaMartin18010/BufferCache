# TC-CLUS-006 备份恢复演练（RPO 验证）

- **用例ID**：TC-CLUS-006 | **优先级**：P1 | **自动化**：半自动（Docker 步骤脚本化，月轮换执行）
- **目的**：验证 RPO——备份文件在"环境全毁"场景下真实可恢复、数据完整、恢复可计时（补 RTO 之外的另一半灾备验证）
- **关联**：[07.04.03 应急预案](../../../docs/07-运维与部署/07.04-故障处理/07.04.03-应急预案.md) §5；[07.05.03](../../../docs/07-运维与部署/07.05-集群管理/07.05.03-集群故障处理.md)；[03.02 持久化机制](../../../docs/03-Redis组件/03.02-持久化机制/)

## 前置条件

`Testing/fixtures/redis-lab/sentinel-compose.yml` 全环境（redis-m 已挂数据卷 `./redis-m-data`）。

## 步骤（2026-11-17 实测通过）

```bash
cd Testing/fixtures/redis-lab
# 1. 造数 + 双备份（RDB 时点快照 + AOF 增量）
for i in 1 2 3 4 5; do docker exec redis-lab-sentinel-redis-m-1 redis-cli SET drill:item:$i "value-$i"; done
docker exec redis-lab-sentinel-redis-m-1 redis-cli SAVE            # RDB（实测 0.19s）
mkdir -p /tmp/redis-backup-drill
docker cp redis-lab-sentinel-redis-m-1:/data/dump.rdb /tmp/redis-backup-drill/
docker cp redis-lab-sentinel-redis-m-1:/data/appendonlydir /tmp/redis-backup-drill/   # AOF 目录必整拷

# 2. 模拟灾难：连卷销毁重建
docker compose down -v && rm -rf redis-m-data && docker compose up -d redis-m
# 预期：DBSIZE=0（空实例）

# 3. 恢复：AOF 目录 + RDB 拷回数据卷，重启
docker compose stop redis-m
cp -r /tmp/redis-backup-drill/appendonlydir /tmp/redis-backup-drill/dump.rdb redis-m-data/
docker compose start redis-m

# 4. 验证
docker exec redis-lab-sentinel-redis-m-1 redis-cli DBSIZE   # 预期 = 造数 key 数
docker exec redis-lab-sentinel-redis-m-1 redis-cli GET drill:item:3   # 抽样值校验
```

## 实测结果（2026-11-17 基线）

| 阶段 | 耗时 | 说明 |
| ---- | ---- | ---- |
| SAVE（RDB 快照） | 0.19s | 小数据量；大实例以 fork 时间为准 |
| 全毁→空实例可服务 | 8.0s | 含镜像命中下的容器重建 |
| 拷贝备份→完全恢复 | 8.0s | 停→拷→起→加载（AOF 优先） |
| 数据完整性 | 5/5 keys，抽样值正确 | RPO=0（备份点后零写入） |

## 预期结果

恢复后 DBSIZE 等于备份点 key 数，抽样值一致；恢复总耗时（拷贝+加载）进入 07.04.03 演练记录。

## 失败纠正与修正指引

1. 恢复后 DBSIZE=0：九成是**只拷了 dump.rdb 没拷 appendonlydir**——Redis 8 开启 AOF 时 AOF 目录优先加载，空 AOF 目录会盖过 RDB。修正：整目录拷回（本用例步骤已固化）。
2. 数据丢失超 1s 写入量：备份频率不足，按 RPO 目标调整 SAVE 周期/AOF fsync 策略。
3. RDB 加载慢：大实例 fork+加载分钟级，预案中明确加载期降级策略。
4. 修正：本用例纳入月度轮换；新环境上线前必须先通过一次本演练。
