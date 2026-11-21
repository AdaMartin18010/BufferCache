# TC-MXC-R55-B256-MTIER 读写比 读写 5:5 × 对象 256B × memtier 压测 基线采集与回归对比

- **用例ID**：TC-MXC-R55-B256-MTIER | **优先级**：P1 | **矩阵格**：MX-C / R55 / B256 / MTIER
- **自动化**：剧本型（gen 铺底） | **批次**：M2+ gen 2026-11-21
- **运行时**：DOCKER+PODMAN｜ANY（按手段）
- **环境阻塞声明**：本格执行依赖外部资产（镜像/GPU/工具链等），未就绪时按测试框架规范 SKIP 不 FAIL，解锁后 hermes 执行
- **目的**：读写比 读写 5:5 × 对象 256B × memtier 压测 基线采集与回归对比
- **关联**：bench_suite SCENARIOS / bench_suite / MX-C 扩展（镜像就绪后）（维度定义 TSV 行；enrich 批从源文档派生具体数值断言）

## 前置条件

- 按关联源文档准备环境/参考实现；运行时按容器适配规范 §1 探测适配

## 步骤（GWT 五段式）

```text
# Given lab redis 温机（预热一轮）
# When memtier 压测 按 读写 5:5/256B 参数采集（--save-baseline 首采，其后对比）
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
