# TC-BENCH-001 Trace 驱动算法基准

- **用例ID**：TC-BENCH-001 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`bench`）
- **目的**：LRU/LFU/S3-FIFO 在合成 Zipf/扫描 trace 下的命中率回归基线不失效
- **关联**：[scripts/benchmark/trace_benchmark.py](../scripts/benchmark/trace_benchmark.py)；[01.05.04](../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) §6

## 步骤

```bash
python scripts/benchmark/trace_benchmark.py
```

## 预期结果

脚本正常输出命中率对比表；已知基线：含 20% 扫描负载下 S3-FIFO 稳定优于 LRU（01.05.04 §6.0 登记的实测结论）。运行时间约 10 秒。

## 失败纠正与修正指引

1. 脚本运行失败（依赖/路径）：修脚本，不改文档结论。
2. 结论倒挂（S3-FIFO 不如 LRU）：先查 trace 生成参数是否被改动；参数确需变更时，更新 01.05.04 §6.0 的登记数据并注明变更原因。
3. 修正：基准参数与种子写死并注释；新算法加入时同步登记基线表。
4. 复跑 `python Testing/self_verify.py bench` 转绿。
