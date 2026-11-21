# TC-BENCH-005 标准化基准套件与回归检测

- **用例ID**：TC-BENCH-005 | **优先级**：P1 | **自动化**：部分（脚本自动；需本地 Redis 实例，无则 SKIP）
- **目的**：把单发 redis-benchmark 升级为场景化矩阵（读写比×对象大小）+ 基线入库 + **回归检测**（与历史基线偏差 >15% 告警）
- **关联**：[scripts/benchmark/suite/bench_suite.py](../../../scripts/benchmark/suite/bench_suite.py)；[07.05.04 §3 实测基线](../../../docs/07-运维与部署/07.05-集群管理/07.05.04-集群容量规划.md)

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

| 场景 | 参数（真实 flags） | 对应负载 |
| ---- | ---- | -------- |
| balanced_small | `-d 256 -r 100000` | 一般 API |
| get_heavy_small | `-d 256 -r 100000` | Web 读多（项目已实测锚点） |
| set_heavy_small | `-d 256 -r 100000` | 计数器/写密集 |
| get_heavy_large | `-d 8192 -r 10000` | 大对象详情页 |

> **参数口径（批次198 实证修正）**：redis-benchmark 无读写比参数，`-r` 为随机键空间（keyspacelen）；读写比为场景文档层语义（`-t set,get` 分项满速压测，set/get RPS 分别上报即写/读容量上限）。大对象场景键空间收敛至 1 万。

## 执行记录

- **2026-11-21（A1 首批实测）**：运行时= PODMAN（docker 守护进程未运行，适配规范 §1 探测锁定）；镜像 redis:8-alpine 拉取失败（registry mirror docker.m.daocloud.io DNS 失效 + registry-1.docker.io 直连超时）→ 降级本地 redis:7-alpine，基线版本口径以 7-alpine 记录，镜像恢复后须重建基线（修正指引 #2）。
- 容器：`podman run -d --name redis-bench-lab -p 6379:6379 -v redis-bench-data:/data redis:7-alpine redis-server --appendonly yes --requirepass lab-password`（独立基准容器，与哨兵演练栈分离）。
- 基线（温机口径，宿主有 kafka 栈共跑）：balanced_small set=235294/get=253165；get_heavy_small 256410/229885；set_heavy_small 240964/259740；get_heavy_large 76046/124224（RPS）。
- 回归检测双向实证：冷基线复跑 set_heavy_small.get -15.2% 触发 REGRESSION（RC=1）→ 温基线（预热一轮后存基线）复跑 PASS——证实检测器可 firing 且温基线口径必要；冷/温差 +30~60% 为首次分配/AOF 预热所致（修正指引 #1 宿主机负载口径内）。
- **顺手修复 bench_suite.py 潜伏缺陷 4 项（本用例从未真跑过故从未暴露）**：① `--bench-cmd` 解析后未传 run_bench（main 调用缺参，永远用默认 redis-benchmark）② 对 benchmark 误加 redis-cli 专属 `--no-auth-warning`（Invalid option）③ 场景参数 `-r 0.5` 误用（-r 为 keyspacelen 非读写比）④ 输出解析未区分 live 行（`SET: rps=0.0 (overall…)`）致 float 崩溃；另错误路径补 cmd 回显（检查器失败必须发声）。

## 预期结果

- 有实例：输出各场景 set/get RPS + 基线偏差百分比；`REGRESSION` 时退出码 1
- 无实例/benchmark 工具：SKIP（退出码 2），不阻断 CI

## 失败纠正与修正指引

1. 疑似回归：先复测确认（基准波动常见来源：宿主机负载、Docker 资源限额、CPU 降频）；确认回归后走性能变更二分（最近变更的代码/配置/版本）。
2. 基线失效提示：硬件更换、版本升级、迁移宿主机后必须 `--save-baseline` 重建（旧基线比对无意义）。
3. 场景扩充：新负载形态加入 SCENARIOS 字典并同步本文档矩阵。
4. 修正：回归阈值 15% 为 C 级经验值，按环境波动收敛后可在脚本顶部 REGRESS_THRESHOLD 调整。
