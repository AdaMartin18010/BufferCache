# TC-MXC-R28-B64K-SUITE 读写比 读写 2:8 × 对象 64KB × 场景化基准套件 基线采集与回归对比

- **用例ID**：TC-MXC-R28-B64K-SUITE | **优先级**：P1 | **矩阵格**：MX-C / R28 / B64K / SUITE
- **自动化**：剧本型（gen 铺底） | **批次**：M2+ gen 2026-11-21
- **运行时**：DOCKER+PODMAN｜ANY（按手段）
- **目的**：读写比 读写 2:8 × 对象 64KB × 场景化基准套件 基线采集与回归对比
- **关联**：bench_suite SCENARIOS / MX-C 扩展 / scripts/benchmark/suite/bench_suite.py（维度定义 TSV 行；enrich 批从源文档派生具体数值断言）

## 前置条件

- 按关联源文档准备环境/参考实现；运行时按容器适配规范 §1 探测适配

## 步骤（GWT 五段式）

```text
# Given lab redis 温机（预热一轮）
# When 场景化基准套件 按 读写 2:8/64KB 参数采集（--save-baseline 首采，其后对比）
# Then RPS/延迟落库 baseline.json；复跑偏差 >15% 触发 REGRESSION 需复测确认
# And 宿主负载记录（共跑栈披露）
```

## 预期结果

- 各 Then/And 断言成立（具体判定值 enrich 批充实）

## 通过标准

- gen 铺底件的通过标准 = 关联源文档的机制定义；enrich 批补充数值阈值

## 失败纠正与修正指引

1. 环境缺：SKIP 语义登记（测试框架规范铁律），解锁后重跑。
2. 机制断言 fail：先核对参考实现/配置与源文档定义的一致性（定义漂移走文档变更流程）。
3. 本文档为生成器铺底件（Mq gen→enrich 生命周期）；充实=主控 enrich 批或 hermes 执行回填，执行权归 hermes。
