# TC-BENCH-001 Trace 驱动算法基准

- **用例ID**：TC-BENCH-001 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`bench`）
- **目的**：LRU/LFU/S3-FIFO 在合成 Zipf/扫描 trace 与公开格式 CSV 上的命中率回归基线不失效
- **关联**：[scripts/benchmark/trace_benchmark.py](../../scripts/benchmark/trace_benchmark.py)；[01.05.04](../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) §6.0；fixture `Testing/fixtures/traces/`

## 步骤

```bash
python scripts/benchmark/trace_benchmark.py                                   # 合成 trace
python scripts/benchmark/trace_benchmark.py --trace Testing/fixtures/traces/sample_trace.csv --capacity 80 --ops 3000
python scripts/benchmark/trace_benchmark.py --trace Testing/fixtures/traces/sample_msr_trace.csv --capacity 60 --ops 2000
```

## 预期结果

三种运行均输出 miss ratio 对照表；合成 trace 基线：含 20% 扫描负载下 S3-FIFO 稳定优于 LRU（01.05.04 §6.0 登记）；CSV fixture 两种格式（通用 key 列 / MSR Disk+Offset）均正确加载。运行时间合计约 2 秒。

## 失败纠正与修正指引

1. 脚本运行失败（依赖/路径）：修脚本，不改文档结论。
2. 合成 trace 结论倒挂（S3-FIFO 不如 LRU）：先查 trace 生成参数是否被改动；确需变更时更新 01.05.04 §6.0 登记数据并注明原因。
3. CSV fixture 加载失败：检查 loader 列嗅探逻辑（`load_csv_trace` 支持 key/Key/obj_id、MSR Disk+Offset 4KB 聚合、无表头单列三类）。
4. 修正：基准参数与种子写死并注释；新 trace 格式支持时补 fixture 并更新本用例。
