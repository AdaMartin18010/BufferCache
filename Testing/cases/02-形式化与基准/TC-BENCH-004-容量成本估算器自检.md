# TC-BENCH-004 容量成本估算器自检

- **用例ID**：TC-BENCH-004 | **优先级**：P2 | **自动化**：self_verify 已覆盖（`bench` 组）
- **目的**：scripts/capacity_calculator.py 可运行、输出结构完整、C 级假设显式声明（05.06/07.05.04 公式的可执行化验证）
- **关联**：[scripts/capacity_calculator.py](../../../scripts/capacity_calculator.py)；[07.05.04 §3 实测基线](../../../docs/07-运维与部署/07.05-集群管理/07.05.04-集群容量规划.md)

## 步骤

```bash
python scripts/capacity_calculator.py                 # 文本报告
python scripts/capacity_calculator.py --json          # 结构化输出
python scripts/capacity_calculator.py --qps 120000 --keys 50000000 --json   # 压力参数
```

## 预期结果

输出含：数据内存（含碎片）、含副本总内存、实例档位、主分片数、总实例数、读带宽、核数需求、月成本、假设声明（元数据/碎片/安全水位/单核吞吐/单价）。

## 失败纠正与修正指引

1. 输出缺字段：公式改动后未同步自检断言，更新 check_capacity 字段清单。
2. 实例数为 0 或负数：分档/取整逻辑错误。
3. 成本量级异常：单价参数被改动——单价属 C 级经验值，改动需同步 AI_Skill 权威来源索引与 04.05 成本文档。
4. 修正：用 redis-benchmark 实测（TC-OPS 配套）校准 `--qps-per-core` 后，把新基线登记到 07.05.04 §3 实测段。
