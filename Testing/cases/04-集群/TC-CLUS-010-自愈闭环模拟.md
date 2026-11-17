# TC-CLUS-010 自愈闭环模拟（预算回归）

- **用例ID**：TC-CLUS-010 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`selfheal` 组）
- **目的**：自愈逻辑的常态自动化验证——`scripts/selfheal_sim.py` 模拟 L1-L3 注入→自愈→计时，对照 07.09.2 §5 RTO 预算表自动判定（预算数值变更即红，防静默漂移）
- **关联**：[scripts/selfheal_sim.py](../../../scripts/selfheal_sim.py)；[07.09.2 §5](../../../docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.02-自愈机制实践.md)；真实演练 TC-CLUS-003~007

## 步骤

```bash
python scripts/selfheal_sim.py        # 三场景
python scripts/selfheal_sim.py --injected l3 --json
```

## 预期结果

L1 进程自愈 / L2 Pod 重建 / L3 实例转移 三场景实测 ≤ 预算（当前基线：1.5s≤30s / 22s≤120s / 9s≤40s，模拟时序值）。

## 失败纠正与修正指引

1. FAIL：先判是模拟器时序值变了还是预算表变了——预算表变更必须同步 07.09.2 §5 与本用例（双向锚定）。
2. 模拟器是 Docker 真实演练的补充而非替代：真实 RTO 实测仍以 TC-CLUS-003~007 回填 07.04.3 为准。
3. 修正：新增自愈层（L0/L4）时扩展 BUDGET 表+模拟函数+预算文档三处。
