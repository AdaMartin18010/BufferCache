# TC-STAT-002 稳态漂移检测

- **用例ID**：TC-STAT-002 | **优先级**：P2 | **自动化**：self_verify 已覆盖（`steady` 组）
- **目的**：混沌工程稳态假设（07.9.3 §2.1）的自动化判定——持续比对命中率/内存水位/键空间命中比与基线，漂移即告警（L4 验收与演练中止条件的数据源）
- **关联**：[scripts/steady_state_check.py](../../../scripts/steady_state_check.py)；[07.9.3](../../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.03-混沌工程与韧性演练.md)

## 步骤

```bash
python scripts/steady_state_check.py              # 自动探测 :19121 exporter
python scripts/steady_state_check.py --simulate   # 合成数据（演示/降级）
```

## 预期结果

exporter 可用：真实指标判定；不可用：合成数据默认稳态（`--simulate` 注入漂移用于演练告警链路）。

## 失败纠正与修正指引

1. DRIFT：按 07.9.3 §2.2 中止条件/调查流程处置；基线调整用 `--baseline-hit` 并登记事实断言清单。
2. exporter 探测失败且未指定 --simulate：SKIP（正常降级）。
3. 修正：稳态指标项变更需同步 07.9.3 §2.1 表与本脚本 BASELINES。
