# TC-BENCH-005 标准化基准套件与回归检测

- **用例ID**：TC-BENCH-005 | **优先级**：P1 | **自动化**：部分（脚本自动；需本地 Redis 实例，无则 SKIP）
- **目的**：把单发 redis-benchmark 升级为场景化矩阵（读写比×对象大小）+ 基线入库 + **回归检测**（与历史基线偏差 >15% 告警）
- **关联**：[scripts/benchmark/suite/bench_suite.py](../../scripts/benchmark/suite/bench_suite.py)；[07.05.04 §3 实测基线](../../docs/07-运维与部署/07.05-集群管理/07.05.04-集群容量规划.md)

## 步骤

```bash
# 宿主已装 redis-benchmark：
python scripts/benchmark/suite/bench_suite.py --host 127.0.0.1 --port 6379 --password lab-password --save-baseline
# 宿主未装（容器内执行）：
python scripts/benchmark/suite/bench_suite.py --host redis-m --port 6379 --password lab-password \
    --bench-cmd "docker exec redis-lab-sentinel-redis-m-1 redis-benchmark" --save-baseline
# 后续运行自动对比基线（不加 --save-baseline）
python scripts/benchmark/suite/bench_suite.py --scenarios get_heavy_small   # 单场景
```

## 场景矩阵

| 场景 | 参数 | 对应负载 |
| ---- | ---- | -------- |
| balanced_small | 读写 5:5，256B | 一般 API |
| get_heavy_small | 读写 9:1，256B | Web 读多（项目已实测锚点） |
| set_heavy_small | 读写 2:8，256B | 计数器/写密集 |
| get_heavy_large | 读写 9:1，8KB | 大对象详情页 |

## 预期结果

- 有实例：输出各场景 set/get RPS + 基线偏差百分比；`REGRESSION` 时退出码 1
- 无实例/benchmark 工具：SKIP（退出码 2），不阻断 CI

## 失败纠正与修正指引

1. 疑似回归：先复测确认（基准波动常见来源：宿主机负载、Docker 资源限额、CPU 降频）；确认回归后走性能变更二分（最近变更的代码/配置/版本）。
2. 基线失效提示：硬件更换、版本升级、迁移宿主机后必须 `--save-baseline` 重建（旧基线比对无意义）。
3. 场景扩充：新负载形态加入 SCENARIOS 字典并同步本文档矩阵。
4. 修正：回归阈值 15% 为 C 级经验值，按环境波动收敛后可在脚本顶部 REGRESS_THRESHOLD 调整。
